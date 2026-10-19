# ReSolve

**A coding practice platform built around spaced repetition.**

You don't fail DSA because you lack problems. You fail because you forget the
ones you already solved. ReSolve is a memory system, not a content library.

Every problem you attempt gets rated and scheduled, and it comes back before
you forget it.

---

## The loop

This is the whole product:

1. You open a practice session. It serves the problems that are **due today**.
2. You attempt one in the editor.
3. You rate how it felt — and this is the part that matters:

   | Rating | What it means |
   | --- | --- |
   | `again` | Could not solve it. |
   | `hard` | Solved, but slowly, or with heavy hints. |
   | `easy` | Solved cleanly and confidently. |
   | `done` | Recognised it immediately. Already solved before. |

4. That rating drives a spaced repetition schedule for that problem, and the
   problem goes back into your rotation.

Note the axis. The problem's difficulty is a community-wide tag — Easy, Medium,
Hard. Your rating is how *this attempt felt for you*. A Medium problem you
solved in ten minutes is `easy` for you; the same problem taking you two hours
is `hard`. Those are two different things, and the app keeps them apart.

---

## What works today

| | |
| --- | --- |
| **Landing** | An animated monochrome wordmark that grows a plant from every letter, types the wrong word, then deletes it and types the right one. |
| **Accounts** | Email and Google sign-in against Supabase. |
| **Learn** | Search that filters as you type, and a list of problems below it. |
| **Problem screen** | The statement on the left; the editor and the test cases on the right. |
| **Compiler** | A free-form C++ workspace that runs on Judge0. |
| **Home / Practice / Settings** | Navbar entries. The analytics are not built yet. |

### The problem screen

The editor holds **only the function**, pre-filled with the signature:

```cpp
vector<int> twoSum(vector<int>& nums, int target) {
    
}
```

No includes. No `main`. The includes, the printers and a `main` that drives
every test case are stored with the problem and spliced around your function on
the server, exactly like a real judge.

### The test cases

Every problem ships with **20-30 test cases**, and **every one of them is
visible** — the input, the expected output, and what your code actually
produced. A failing row is tinted red; a passing one, green. Nothing is
hidden, because a hidden case is a hidden bug.

The expected outputs are **measured, not predicted**: each one was produced by
compiling and running the problem's own reference solution on Judge0. Two
checks back that — the reference has to reproduce the worked example printed in
the statement, and every stored answer has to match a fresh run.

---

## Running it

Two processes, in two terminals.

**Backend, port 8000:**

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

**Frontend, port 5173:**

```bash
cd frontend
npm install
npm run dev
```

Then open <http://localhost:5173>.

> On Windows, start the backend with `run.py` — not `uvicorn app.main:app`.
> It passes a custom event-loop factory that works around a crash in uvicorn's
> Windows default. The reason is in [`AGENTS.md`](./AGENTS.md) §9.

### Configuration

Copy the two templates and fill them in:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

`frontend/.env` wants your Supabase URL and anon key:

```ini
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key>
```

**No API keys are needed to run the app.** Judge0's public community instance is
key-free, so the compiler works out of the box. The anon key is designed to be
public — it ships in the browser bundle and is protected by row-level security.
The service-role key is not, and must never go in `frontend/.env`.

---

## The stack

| | |
| --- | --- |
| **Frontend** | Vite 8, React 19, TypeScript 6, Tailwind CSS 4, Monaco for the editor |
| **Backend** | FastAPI, Pydantic, Supabase (Postgres + auth) |
| **Judging** | Judge0 — C++ is `language_id=54` |

```text
browser ──> Vite :5173
              ├── /api/* ──> FastAPI :8000 ──> Judge0
              │                   │
              │                   └──> backend/data/problems.json
              └── static assets

browser ──> Supabase  (auth only, directly)
```

---

## Layout

```text
ReSolve/
├── AGENTS.md            <- the source of truth for the product and the code
├── backend/
│   ├── data/problems.json  <- the 50-problem catalogue
│   ├── scripts/             <- tooling for maintaining the catalogue
│   ├── app/                 <- FastAPI
│   └── run.py               <- start the server with this
└── frontend/
    └── src/
        ├── index.css        <- every design token lives here
        ├── lib/             <- supabase, auth, navigation, compiler client
        ├── components/      <- app shell, guards, code editor, markdown
        └── pages/           <- one file per surface
```

The problem catalogue is a JSON file for now and a stand-in for the database.
When the Postgres tables exist, `backend/app/core/problems.py` is the only file
that has to change.

---

## Working on it

Read [`AGENTS.md`](./AGENTS.md) first — in full. It is the single source of
truth for the product, the architecture and the conventions, and it is written
for whoever picks this up next.

Before you call anything done:

```bash
cd frontend && npm run lint      # clean
cd frontend && npm run build     # succeeds
cd backend  && .\.venv\Scripts\python.exe -m ruff check .   # clean
cd backend  && .\.venv\Scripts\python.exe -m pytest -q      # passes
```

If you touched the catalogue, also run `backend/scripts/check_examples.py` and
`backend/scripts/verify.py`. `backend/scripts/README.md` explains the loop.

---

## Where it is going

The catalogue is the beginning, not the product. The spaced repetition
scheduler is the thing that has to exist: it is the entire thesis, and it is
still just a design. Practice, the Home analytics, and the Postgres tables all
follow from it.

Open questions live in [`AGENTS.md`](./AGENTS.md) §11 — chiefly the scheduling
algorithm (SM-2 or FSRS) and whether a problem is one language or several.

---

## Licence and attribution

Problem titles and sheet membership are transcribed from publicly published
problem lists (NeetCode, Blind 75, Striver SDE, Love Babbar 450). Every
problem statement is original to this project.
