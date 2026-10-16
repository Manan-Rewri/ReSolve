# Resolve - DSA & LeetCode Spaced Repetition Backend

**Resolve** is a spaced repetition backend inspired by **Anki** designed specifically for mastering Data Structures and Algorithms (DSA) and LeetCode problems. It helps software engineers systematically retain problem patterns and solutions through scheduled revisions based on their struggle ratings.

Built with **Python**, **FastAPI**, and **Supabase PostgreSQL**.

---

## 🚀 Key Features

1. **User Authentication & Data Isolation**:
   - Secure signup and login with bcrypt-hashed passwords and signed JWT tokens (`HS256`).
   - Strict user-level data isolation: users can only view, modify, delete, and review their own problems.
2. **LeetCode Problem Tracking**:
   - Save problem URL, title, topic (e.g., Arrays, Dynamic Programming), difficulty (Easy, Medium, Hard), personal notes, and optimal solutions or hints.
   - Preserves user-provided URLs without brittle web scraping or dependency on unofficial APIs.
3. **Anki-Inspired Spaced Repetition Scheduler (SM-2)**:
   - Categorize problem struggle into 4 distinct ratings:
     - `Easy`: Solved effortlessly; rewards an aggressive interval jump (+15% ease factor).
     - `Medium`: Solved with standard effort; standard SM-2 expansion (1d -> 3d -> interval * EF).
     - `Hard`: Solved with significant struggle; small interval growth, decreases ease factor (-15%).
     - `Couldn't Write a Line`: Complete lapse; resets repetitions to 0 and schedules review for tomorrow (1 day).
4. **Rich Dashboard API**:
   - Consolidated statistics: problems due today, overdue problems, upcoming revisions timeline grouped by date, and category breakdowns.
5. **Full CRUD & History APIs**:
   - Filter problems by topic, difficulty, status, search keyword, and due-only status.
   - Comprehensive revision log history for each problem.
6. **Supabase PostgreSQL Ready**:
   - Complete `supabase/schema.sql` script with performance indexes and Row Level Security (RLS) policies.
   - Never exposes Supabase service-role keys in frontend code.

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py                     # App wiring: middleware, routers, /assets mount
│   ├── paths.py                    # FRONTEND_DIR / ASSETS_DIR resolution
│   ├── migrations.py               # Additive column migrations for old databases
│   ├── config.py                   # Pydantic-settings configuration & env variables
│   ├── database.py                 # SQLAlchemy engine & session dependency
│   ├── dependencies.py             # Auth dependency injection (get_current_user)
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── user.py                 # User model
│   │   ├── problem.py              # Problem model with spaced repetition state
│   │   └── review_log.py           # Review history log model
│   ├── schemas/                    # Pydantic v2 schemas
│   │   ├── auth.py                 # Signup, login, profile and token schemas
│   │   ├── problem.py              # Problem CRUD schemas & enums
│   │   ├── review.py               # Review submission schemas
│   │   ├── dashboard.py            # Dashboard metrics & upcoming timeline schemas
│   │   ├── leetcode.py             # LeetCode fetch & autocomplete schemas
│   │   └── execution.py            # Code execution request/result schemas
│   ├── services/                   # Business logic, split by concern
│   │   ├── auth_service.py         # Password hashing & JWT
│   │   ├── scheduler_service.py    # Anki / SM-2 spaced repetition engine
│   │   ├── problem_service.py      # Problem CRUD
│   │   ├── review_service.py       # Review submission & history
│   │   ├── analytics_service.py    # Dashboard & daily-practice aggregates
│   │   ├── problem_mapper.py       # Problem -> response + practice priority
│   │   ├── leetcode_service.py     # LeetCode fetch/search orchestration
│   │   ├── leetcode_client.py      # LeetCode GraphQL transport
│   │   └── judge0_service.py       # Sandboxed compile & run via Judge0
│   ├── routers/                    # REST API route handlers
│   │   ├── auth.py                 # /api/v1/auth (signup, login, me)
│   │   ├── problems.py             # /api/v1/problems (CRUD, review, search)
│   │   ├── dashboard.py            # /api/v1/dashboard
│   │   ├── execute.py              # /api/v1/execute (compile & run)
│   │   └── web.py                  # /, /register, /login, /home, /learn, /settings
│   └── utils/                      # Shared helpers
│       ├── time.py                 # utc_now, as_utc, start_of_day
│       └── text.py                 # slug + HTML-to-text conversion
├── supabase/
│   └── schema.sql                  # Supabase PostgreSQL DDL with RLS policies & indexes
├── tests/                          # offline pytest suite (in-memory SQLite)
│   ├── conftest.py                 # Pytest fixtures & in-memory test database
│   ├── test_auth.py                # Registration, login, profile and auth failures
│   ├── test_problems_crud.py       # Problem CRUD & validation tests
│   ├── test_data_isolation.py      # Cross-user isolation tests
│   ├── test_scheduler.py           # Anki / SM-2 algorithm progression tests
│   ├── test_dashboard.py           # Due today, overdue, and upcoming analytics
│   ├── test_leetcode_and_practice.py  # LeetCode fetch & daily-practice tests
│   ├── test_execute.py             # Code runner tests (Judge0 mocked)
│   ├── test_migrations.py          # Stale-schema migration regression tests
│   └── test_web_app_and_search.py  # Search endpoint & page/asset serving
├── .env.example                    # Template environment variables
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Pytest configuration
├── CODE_EXECUTION.md               # Deep dive on the code-runner feature
├── AGENTS.md                       # Guide for AI agents / contributors
└── README.md                       # Documentation & setup guide
```

---

## 🧠 Database Schema Design

### 1. `users` Table
| Column | Type | Constraints / Description |
|---|---|---|
| `id` | `UUID / String(36)` | Primary Key |
| `email` | `VARCHAR(255)` | Unique, Not Null |
| `hashed_password` | `VARCHAR(255)` | Not Null (Bcrypt hashed) |
| `full_name` | `VARCHAR(255)` | Optional |
| `created_at` | `TIMESTAMPTZ` | Default: `NOW()` |
| `updated_at` | `TIMESTAMPTZ` | Default: `NOW()` |

### 2. `problems` Table
| Column | Type | Constraints / Description |
|---|---|---|
| `id` | `UUID / String(36)` | Primary Key |
| `user_id` | `UUID / String(36)` | Foreign Key -> `users(id)` ON DELETE CASCADE |
| `url` | `TEXT` | Not Null (User-provided problem URL) |
| `title` | `VARCHAR(255)` | Not Null |
| `topic` | `VARCHAR(100)` | Not Null (e.g., Arrays, Graphs, DP) |
| `difficulty` | `VARCHAR(32)` | Check: `'Easy'`, `'Medium'`, `'Hard'` |
| `notes` | `TEXT` | Personal thoughts and edge case notes |
| `solution_or_hints` | `TEXT` | Personal solution snippet or key hints |
| `status` | `VARCHAR(32)` | Default: `'active'` (`'active'`, `'mastered'`, `'archived'`) |
| `current_interval_days`| `INTEGER` | Days until next scheduled review (Default: `1`) |
| `ease_factor` | `FLOAT` | SM-2 ease factor (Default: `2.5`, Min: `1.3`) |
| `repetitions` | `INTEGER` | Consecutive successful reviews (Default: `0`) |
| `last_struggle_rating` | `VARCHAR(64)` | `'Easy'`, `'Medium'`, `'Hard'`, `'Couldn''t Write a Line'` |
| `last_reviewed_at` | `TIMESTAMPTZ` | Timestamp of last review |
| `next_review_due` | `TIMESTAMPTZ` | Due timestamp for next review (Default: `NOW()`) |
| `created_at` | `TIMESTAMPTZ` | Default: `NOW()` |
| `updated_at` | `TIMESTAMPTZ` | Default: `NOW()` |

### 3. `review_logs` Table
| Column | Type | Constraints / Description |
|---|---|---|
| `id` | `UUID / String(36)` | Primary Key |
| `problem_id` | `UUID / String(36)` | Foreign Key -> `problems(id)` ON DELETE CASCADE |
| `user_id` | `UUID / String(36)` | Foreign Key -> `users(id)` ON DELETE CASCADE |
| `struggle_rating` | `VARCHAR(64)` | Struggle rating submitted in review session |
| `scheduled_days` | `INTEGER` | Calculated interval for the next review |
| `notes` | `TEXT` | Optional session reflection notes |
| `reviewed_at` | `TIMESTAMPTZ` | Timestamp of review |

---

## 📈 Spaced Repetition Scheduling Algorithm

Resolve uses an algorithm derived from the SuperMemo SM-2 model, tailored for algorithmic problem retention:

1. **"Couldn't Write a Line"**:
   - `repetitions` = `0` (lapsed memory)
   - `interval_days` = `1` (review again tomorrow)
   - `ease_factor` = `max(1.3, ease_factor - 0.20)`
2. **"Hard"**:
   - `repetitions` = `repetitions + 1`
   - `interval_days` = `1` (if rep 0), `2` (if rep 1), `max(1, round(interval * 1.2))` (if rep >= 2)
   - `ease_factor` = `max(1.3, ease_factor - 0.15)`
3. **"Medium"** (Standard recall):
   - `repetitions` = `repetitions + 1`
   - `interval_days` = `1` (if rep 0), `3` (if rep 1), `round(interval * ease_factor)` (if rep >= 2)
   - `ease_factor` = unchanged
4. **"Easy"** (Flawless recall):
   - `repetitions` = `repetitions + 1`
   - `interval_days` = `3` (if rep 0), `7` (if rep 1), `round(interval * ease_factor * 1.3)` (if rep >= 2)
   - `ease_factor` = `min(3.5, ease_factor + 0.15)`

---

## 🛠️ API Reference

All protected endpoints require the header:
```
Authorization: Bearer <access_token>
```

### Authentication
- `POST /api/v1/auth/signup`: Create a new user account and return a token.
- `POST /api/v1/auth/login`: Authenticate and receive a JWT bearer token.
- `GET /api/v1/auth/me`: Retrieve current authenticated user profile.
- `PUT /api/v1/auth/me`: Update profile fields (`full_name`).

### Problems CRUD & Revisions
- `POST /api/v1/problems`: Save a new problem (optional `initial_struggle_rating`).
- `GET /api/v1/problems`: List problems with filtering (`topic`, `difficulty`, `status`, `search`, `due_only`, `skip`, `limit`).
- `GET /api/v1/problems/{id}`: Get a single problem by ID.
- `PUT /api/v1/problems/{id}`: Update problem details or status.
- `DELETE /api/v1/problems/{id}`: Delete a problem and its revision logs.
- `POST /api/v1/problems/{id}/review`: Submit a struggle rating review to recalculate schedule.
- `GET /api/v1/problems/{id}/reviews`: View complete revision history for a problem.
- `GET /api/v1/problems/daily-practice`: Prioritised revision queue (optional `topic`, `due_only`, `limit`).

### LeetCode
- `POST /api/v1/problems/fetch-leetcode`: Fetch a full problem (statement, difficulty, topics, hints) by title, slug, or URL.
- `GET /api/v1/problems/search?q=&limit=`: Autocomplete suggestions for the search bar.

### Code Execution
- `POST /api/v1/execute`: Compile and run a snippet in a sandboxed Judge0 instance; returns stdout/stderr/compile output and timing.
- `GET /api/v1/execute/languages`: Supported languages for the editor.

### Dashboard
- `GET /api/v1/dashboard`: Returns due today items, overdue problems, upcoming revision groups by date, and topic/difficulty breakdown.

### Web Interface
- `GET /`: Landing page (redirects signed-in users to `/home`).
- `GET /register`, `GET /login`: Auth pages.
- `GET /home`, `GET /learn`, `GET /settings`: App pages (redirect to `/login` without a token).
- `GET /assets/*`: Static CSS and JavaScript.

---

## ⚡ How to Start the Server Locally

### 1. Prerequisites
- Python 3.10+ (Python 3.11 recommended)

### 2. Activate Virtual Environment
In the `backend` directory:
```powershell
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Or run directly using the venv python:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### 3. Environment Variables
By default, the backend runs seamlessly with zero setup using a local SQLite database (`resolve.db`).
To configure custom settings or connect to Supabase:
```powershell
cp .env.example .env
```

### 4. Run the Uvicorn Server
```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:
- **API Base**: `http://127.0.0.1:8000`
- **Interactive Swagger Documentation**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
- **Health Check**: `http://127.0.0.1:8000/health`

---

## 🗄️ Connecting to Supabase PostgreSQL

1. Open your [Supabase Dashboard](https://supabase.com/dashboard).
2. Go to **SQL Editor** -> Create a new query.
3. Paste the contents of `supabase/schema.sql` into the editor and click **Run**.
4. Retrieve your database connection string under **Project Settings -> Database**:
   ```
   postgresql://postgres.[your-project-ref]:[your-password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
5. Update `DATABASE_URL` in your `.env` file:
   ```env
   DATABASE_URL="postgresql://postgres.[your-project-ref]:[your-password]@aws-0-[region].pooler.supabase.com:6543/postgres"
   ```
6. Security Note: Always keep your `SUPABASE_SERVICE_ROLE_KEY` inside `.env` on your backend server. Never include service role keys in frontend bundles.

---

## 🧪 Running the Automated Tests

Resolve includes a test suite covering authentication, validation, data isolation, spaced repetition calculations, and dashboard aggregations.

Run tests using pytest:
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The full suite runs offline against an isolated in-memory database. The single
live Judge0 test is skipped unless `RUN_LIVE_JUDGE0=1` is set (a sample run):
```
======================== 81 passed, 1 skipped ========================
```
