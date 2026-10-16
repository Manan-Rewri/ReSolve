# ReSolve 🧠

> An Anki-inspired spaced-repetition platform for DSA & LeetCode — with a
> built-in practice workspace that compiles and runs your code.

---

## 📂 Layout

```
ReSolve/
├── backend/                     # Python · FastAPI · Supabase PostgreSQL
│   ├── app/
│   │   ├── main.py              # app factory, middleware, router wiring
│   │   ├── paths.py             # frontend/asset path resolution
│   │   ├── migrations.py        # additive column migrations for old DBs
│   │   ├── config.py            # env-driven settings
│   │   ├── database.py          # engine, session, init
│   │   ├── dependencies.py      # JWT auth dependency
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # business logic
│   │   ├── routers/             # HTTP layer (auth, problems, dashboard, execute, web)
│   │   └── utils/               # time + text helpers
│   ├── tests/                   # pytest suite
│   ├── supabase/schema.sql
│   ├── CODE_EXECUTION.md
│   ├── AGENTS.md
│   └── README.md
└── frontend/                    # static UI served by the backend (no build step)
    ├── index.html               # landing          → /
    ├── register.html            #                  → /register
    ├── login.html               #                  → /login
    ├── home.html                # analytics        → /home
    ├── learn.html               # search + runner  → /learn
    ├── settings.html            #                  → /settings
    └── assets/
        ├── css/                 # base + one sheet per page
        └── js/
            ├── core/            # api, session, dom, format
            ├── components/      # navbar, problem-search
            └── pages/           # one entry script per page
```

## 🚀 Run it

```powershell
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

- **Web app:** http://127.0.0.1:8000/
- **API docs:** http://127.0.0.1:8000/docs
- **Health:** http://127.0.0.1:8000/health

## 🗺️ Pages

| Route | Purpose |
|---|---|
| `/` | Landing. Redirects to `/home` if already signed in. |
| `/register` | Create an account. |
| `/login` | Sign in. |
| `/home` | Analytics: due, overdue, upcoming, breakdowns. |
| `/learn` | Search LeetCode, read the statement, write and run code. |
| `/settings` | Profile and session. |

`/home`, `/learn` and `/settings` require a token; without one the browser is
sent to `/login`. Design is Space Grotesk on a black-and-white palette.

## ▶️ Code execution

Submitted code is **never run on this server** — it is relayed to a sandboxed
[Judge0](https://judge0.com) instance to avoid remote-code-execution risk.

- `POST /api/v1/execute` — compile & run a snippet; returns stdout/stderr.
- `GET /api/v1/execute/languages` — supported languages.

See [`backend/CODE_EXECUTION.md`](backend/CODE_EXECUTION.md).

## 🧪 Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q     # 81 passed, 1 skipped (offline)
```