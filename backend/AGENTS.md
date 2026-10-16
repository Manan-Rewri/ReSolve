# AGENTS.md — Resolve

Guidance for AI coding agents (and humans) working on the **Resolve** project.
This file lives in `backend/`; paths below are relative to the **repository
root** unless noted.

---

## 1. What Resolve is

Resolve is a spaced-repetition platform for **LeetCode / DSA problems**. Instead
of solving a problem once and forgetting it, users save problems, record how
hard each attempt felt, and revisit them on a schedule (Anki-style SM-2).

The product includes a **practice workspace** where a user loads a LeetCode
problem and **writes and runs code** beside the statement.

**Stack:** Python + FastAPI (backend) · Supabase PostgreSQL (production DB) ·
SQLite (local dev) · plain HTML/CSS/ES-modules frontend served by the backend.

---

## 2. Repository layout

```
ReSolve/
├── README.md
├── backend/                          # this folder (AGENTS.md lives here)
│   ├── AGENTS.md                     # this file
│   ├── README.md                     # backend setup + schema + SM-2 docs
│   ├── CODE_EXECUTION.md             # deep dive on the code runner
│   ├── app/
│   │   ├── main.py                   # app wiring: middleware, routers, /assets
│   │   ├── paths.py                  # FRONTEND_DIR / ASSETS_DIR resolution
│   │   ├── migrations.py             # additive column migrations for old DBs
│   │   ├── config.py                 # pydantic-settings from env
│   │   ├── database.py               # engine, session factory, init_db
│   │   ├── dependencies.py           # get_current_user (JWT bearer)
│   │   ├── models/                   # SQLAlchemy: user, problem, review_log
│   │   ├── schemas/                  # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── auth_service.py       # bcrypt + JWT + profile
│   │   │   ├── scheduler_service.py  # SM-2 spaced repetition
│   │   │   ├── problem_service.py    # problem CRUD
│   │   │   ├── review_service.py     # review submission + history
│   │   │   ├── analytics_service.py  # dashboard + daily-practice queue
│   │   │   ├── leetcode_service.py   # fetch/search orchestration
│   │   │   ├── leetcode_client.py    # LeetCode GraphQL transport
│   │   │   └── judge0_service.py     # sandboxed compile & run
│   │   ├── routers/                  # auth, problems, dashboard, execute, web
│   │   └── utils/                    # time + text helpers
│   ├── tests/                        # pytest suite (in-memory SQLite)
│   ├── supabase/schema.sql
│   ├── requirements.txt
│   └── pyproject.toml
└── frontend/                         # served by the backend, no build step
    ├── index.html · register.html · login.html · home.html · learn.html · settings.html
    └── assets/{css,js}
```

---

## 3. Running

```powershell
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

- Web app: **http://127.0.0.1:8000/** · Swagger: **/docs** · Health: **/health**

Tests:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q                 # fast, no network
$env:RUN_LIVE_JUDGE0="1"; .\.venv\Scripts\python.exe -m pytest -q -k live
```

---

## 4. Conventions

- **Layering:** routers (`app/routers/`) handle HTTP + validation only; business
  logic lives in **services**; data shapes in **schemas**; shared helpers in
  `app/utils/`.
- **Services are split by concern, not by entity.** `problem_service` does CRUD,
  `review_service` does reviews, `analytics_service` does aggregates. Cross-
  service reuse goes through explicit imports, never a circular import.
- **Comments:** keep comments that explain *why* (security constraints, the SM-2
  rationale, timezone normalisation). Remove comments that restate the code.
- **Auth:** protected endpoints use `Depends(get_current_user)`. All problem
  data is isolated per user via `get_owned_problem`.
- **Config:** never hardcode secrets; add fields to `app/config.py` and document
  them in `.env.example`.
- **Tests:** use the shared `client` fixture in `tests/conftest.py`. Monkeypatch
  network calls so the suite stays offline and deterministic.
- **Style:** small modules, explicit names, no unnecessary abstraction.

---

## 5. API contract (prefix `/api/v1`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/signup` | – | Register → token |
| POST | `/auth/login` | – | Login → token |
| GET | `/auth/me` | ✔ | Current user |
| PUT | `/auth/me` | ✔ | Update profile (`full_name`) |
| GET | `/problems` | ✔ | List saved problems (filters) |
| POST | `/problems` | ✔ | Save a problem |
| GET | `/problems/{id}` | ✔ | Get one |
| PUT | `/problems/{id}` | ✔ | Update |
| DELETE | `/problems/{id}` | ✔ | Delete |
| POST | `/problems/{id}/review` | ✔ | Record a review (reschedules) |
| GET | `/problems/{id}/reviews` | ✔ | Review history |
| POST | `/problems/fetch-leetcode` | – | Fetch problem by title/URL |
| GET | `/problems/search?q=&limit=` | – | Autocomplete suggestions |
| GET | `/problems/daily-practice` | ✔ | Prioritised revision queue |
| GET | `/dashboard` | ✔ | Dashboard analytics |
| GET | `/execute/languages` | – | Supported languages |
| POST | `/execute` | – | Compile & run a snippet |

### Page routes (no prefix)

| Path | Page |
|---|---|
| `/` | Landing — redirects to `/home` when a token exists |
| `/register`, `/login` | Auth pages — redirect to `/home` when signed in |
| `/home`, `/learn`, `/settings` | App pages — redirect to `/login` without a token |
| `/api`, `/health` | JSON info / health |

Static files are mounted at `/assets`.

### `POST /execute`

```json
{ "language": "cpp", "source_code": "int main(){return 0;}", "stdin": "3 4" }
```
→ `{ language, status: {id, description}, succeeded, stdout, stderr,
compile_output, message, time, memory, exit_code }`

`status.id`: `3` Accepted · `5` TLE · `6` Compilation Error · `7`/`11`
Runtime Error · `13` Internal Error. `succeeded === (status.id === 3)`.

---

## 6. Code execution — the key decision

**Never compile or run user-submitted code on our own server.** Doing so is a
remote-code-execution hole: a submitted program could read `SECRET_KEY` /
Supabase credentials, delete files, fork-bomb the host, or mine crypto.

The backend **relays** code to a sandboxed **[Judge0](https://judge0.com)**
instance which compiles and runs it in isolation.

- **Why Judge0, not Piston:** as of **15 Feb 2026** Piston's public API is no
  longer freely available and it explicitly refuses college / individual /
  portfolio projects. Judge0 works without Docker.
- **Default:** free public `https://ce.judge0.com` (no API key).
- **Production:** set `JUDGE0_BASE_URL` / `JUDGE0_API_KEY` / `JUDGE0_API_HOST`
  — no code changes.

See `backend/CODE_EXECUTION.md` and `.env.example`.

---

## 7. Frontend

Plain HTML + CSS + ES modules. No framework, no bundler, no build step; the
backend serves the files directly.

- Monochrome design system (black / white / greys). **Errors are flagged by
  inversion**, not colour — keep it that way.
- All API access goes through `assets/js/core/api.js`; nothing else calls
  `fetch`.
- Auth token in `localStorage` under `resolve.token`; guards live in
  `core/session.js` (`redirectIfAuthenticated` / `requireAuth`).
- One `pages/*.js` entry module per HTML page; shared code in `core/` and
  `components/`.

Your friend is building the real React frontend — treat the API contract in
section 5 as the source of truth.

---

## 8. Database migrations

`Base.metadata.create_all()` **never adds columns to existing tables**, so a
database created by an older build silently lacks later columns (this already
caused `no such column: problems.content_html` and HTTP 500s on every problem
endpoint).

`app/migrations.py` fixes this with additive `ALTER TABLE ... ADD COLUMN`
backfills, declared in `BACKFILLABLE_COLUMNS` and applied by `init_db()` at
startup. **When you add a nullable column to a model, register it there too**,
otherwise existing databases will break. `tests/test_migrations.py` covers it.

---

## 9. History / notes for the next agent

- The project was accidentally deleted to the Recycle Bin on **2026-10-16
  22:38** and restored from `C:\$Recycle.Bin\...`. The repo had **no commits**.
  **Commit/push regularly.**
- The code-execution feature (Judge0) was added after that recovery.
- `/app`, `/import` and `/runner` were merged into `/` and then replaced
  entirely by the six-page app. They now return 404 **by design**.

### Suggested next steps

- Require auth on `/execute` and add per-user rate limiting before launch.
- Add a Judge0 key for production reliability.
- Wire the React frontend to the API contract in section 5.