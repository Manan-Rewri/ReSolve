# ReSolve API

FastAPI + Supabase. Serves the ReSolve web client on `http://localhost:5173`.

## Setup (Windows)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env   # then fill in your Supabase keys
```

> On some machines PowerShell blocks `python.ps1`. If you see
> *"running scripts is disabled on this system"*, either call the interpreter by
> its full path as above, or run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/v1/health

The Vite dev server proxies `/api/*` to port 8000, so the frontend can just call
relative `/api/v1/...` paths.

## Checks

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q
```

## Layout

```
app/
  main.py            FastAPI app factory, CORS, router mounting
  core/
    config.py        Settings from .env (pydantic-settings)
    supabase.py      service-role + anon clients
  api/
    deps.py          bearer-token auth dependency
    v1/
      router.py      v1 router aggregation
      health.py      liveness probe
  schemas/           Pydantic request/response models
  models/            reserved for domain models / table definitions
tests/               pytest suite
```

## Notes

- Do **not** install `fastapi[standard]` or `uvicorn[standard]` on Python 3.15.
  They pull PyYAML, which has no 3.15 wheel and needs MSVC build tools.
- `get_supabase_admin()` uses the service-role key and bypasses Row Level
  Security. It is server-side only. Every query you write with it is your
  responsibility to scope to the current user.
