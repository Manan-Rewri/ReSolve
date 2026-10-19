# ReSolve — Frontend

Vite + React + TypeScript + Tailwind CSS v4 + ESLint.

## Setup (Windows)

```powershell
cd frontend
npm install
```

> `npm.ps1` is blocked by the Windows execution policy on some machines.
> If `npm run dev` fails with *"running scripts is disabled"*, use
> `npm.cmd run dev` instead.

## Run

```powershell
npm.cmd run dev     # http://localhost:5173
```

Start the API separately (`cd backend` →
`.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`).
Vite proxies `/api/*` to `http://127.0.0.1:8000`, so the client only ever
calls relative `/api/v1/...` paths.

## Checks

```powershell
npm.cmd run lint
npm.cmd run build
```

## Brand rules

Space Grotesk, monochrome, dark only, no accent colours. Every colour comes
from a token in the `@theme` block in `src/index.css` — never hardcode a hex
value in a component. See `../AGENTS.md` §6 for the full design system.
