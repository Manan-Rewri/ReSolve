# Code Execution (Run C++ / DSA Practice)

Resolve lets a user write and run code and see the output — useful for
re-attempting a problem during review without leaving the app.

- **Endpoint:** `POST /api/v1/execute`
- **Supported:** C++ (default), C, Python, Java, JavaScript
- **Frontend:** the `/learn` page at `../frontend/learn.html` (search, statement,
  editor, stdin and output). The designer's React app will replace it.

---

## Why we don't compile code on our own server

Running submitted code by shelling out to `g++` on our backend is a
**remote-code-execution vulnerability**: a submitted program could read our
`SECRET_KEY` / Supabase credentials from the environment, delete files,
fork-bomb the host, or mine crypto.

So this feature **never executes code locally**. The backend relays the code to
a sandboxed [Judge0](https://judge0.com) instance which compiles and runs it in
isolation and returns the output.

### Why Judge0 and not Piston

As of **15 Feb 2026**, Piston's public API is no longer freely available and its
maintainer explicitly does **not** grant keys for college/university,
individual, or portfolio projects — so it is not usable for Resolve. Judge0
offers free hosted access that does **not** require Docker.

| Backend | Free without Docker? | Notes |
|---|---|---|
| **Judge0 — public `ce.judge0.com`** | Yes, no key | Default. Great for dev/demo. Shared, no SLA. |
| **Judge0 — RapidAPI / Sulu** | Yes, free tier + key | Recommended for production. |
| Piston public API | No | Closed to college/individual projects since Feb 2026. |
| Self-hosted Judge0 / Piston | Yes, but needs Docker | Fallback if we outgrow hosted tiers. |

---

## Flow

```
Frontend (editor + stdin + Run)
      |  POST /api/v1/execute { language, source_code, stdin }
      v
FastAPI  ->  Judge0 sandbox  ->  stdout / stderr / compile error / time
      |
      v
{ status, succeeded, stdout, stderr, compile_output, time, memory }
```

---

## API

### `POST /api/v1/execute`

```json
{
  "language": "cpp",
  "source_code": "#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b; }",
  "stdin": "3 4"
}
```

- `language`: `cpp` | `c` | `python` | `java` | `javascript` (default `cpp`).
- `source_code`: 1-20000 characters (env-configurable).
- `stdin`: optional, max 10000 characters.

Response `200`:

```json
{
  "language": "cpp",
  "status": { "id": 3, "description": "Accepted" },
  "succeeded": true,
  "stdout": "7\n",
  "stderr": null,
  "compile_output": null,
  "message": null,
  "time": 0.003,
  "memory": 1160,
  "exit_code": 0
}
```

`status.id`: `3` Accepted, `5` Time Limit Exceeded, `6` Compilation Error,
`7`/`11` Runtime Error, `13` Internal Error. `succeeded` is `true` only for `3`.

Errors: `422` invalid payload, `429` upstream rate limit, `502`/`503` upstream
error/unreachable, `504` timed out waiting for a result.

### `GET /api/v1/execute/languages`

Returns the supported languages for the UI dropdown.

---

## Configuration

Set in `.env` (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `JUDGE0_BASE_URL` | `https://ce.judge0.com` | Execution endpoint. |
| `JUDGE0_API_KEY` | *(empty)* | RapidAPI key or `X-Auth-Token`. |
| `JUDGE0_API_HOST` | *(empty)* | Set only for RapidAPI (`X-RapidAPI-Host`). |
| `MAX_SOURCE_CODE_LENGTH` | `20000` | Reject oversized submissions. |
| `MAX_STDIN_LENGTH` | `10000` | Reject oversized stdin. |
| `DEFAULT_CPU_TIME_LIMIT` | `3.0` | Seconds. |
| `DEFAULT_MEMORY_LIMIT_KB` | `128000` | Per-run memory cap. |

**Production:** sign up for Judge0 on RapidAPI or Sulu and set:

```
JUDGE0_BASE_URL=https://judge0-ce.p.rapidapi.com
JUDGE0_API_KEY=<your-key>
JUDGE0_API_HOST=judge0-ce.p.rapidapi.com
```

No code changes required.

---

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q -k execute          # fast, no network
$env:RUN_LIVE_JUDGE0="1"; .\.venv\Scripts\python.exe -m pytest -q -k live
```

---

## Security / hardening follow-ups

- The public `ce.judge0.com` instance has **no SLA** — fine for a class project
  and demos, not for real traffic. Add a Judge0 key before launch.
- Consider adding `Depends(get_current_user)` to the endpoint (i.e. require
  login to run code) and a **per-user rate limit** before exposing it publicly.
- Judge0 itself provides the sandbox (CPU/memory/time limits, no network).
