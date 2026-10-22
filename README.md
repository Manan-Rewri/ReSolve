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

   | Rating | What it means | What happens |
   | --- | --- | --- |
   | `very easy` | I do not need to practise this again. | never — and taken out if it was |
   | `medium` | I solved it, but it was work. | the interval **doubles** |
   | `hard` | I struggled, or nearly failed it. | the interval **halves** |
   | `extreme` | I read the solution. | back in **ten minutes** |

4. The problem goes into your practice sheet, and comes back on that schedule.

The question is asked **whether or not you got it right**. A problem you
attempted and got wrong is exactly the one you need to practise, so it is not
dropped — it goes in as `hard` and comes back sooner. Only a full pass earns
the tick in the Learn list.

If a rating cannot be saved, the app says so. It will never quietly do
nothing.

**The memory curve.** Every card carries a stability: the number of days until
your chance of recalling that problem has decayed to **90%**.

```
recall(t) = 0.9 ** (t / stability)
```

The card is scheduled for exactly `t = stability` — the edge of forgetting.
A rating then updates the estimate:

| Rating | What happens to stability |
| --- | --- |
| `medium` | × 2, at least one day |
| `hard` | × 0.5, at least ten minutes |
| `extreme` | reset to ten minutes, counts a lapse |

A clean solve says the memory is stronger than we thought, so it lasts twice as
long. A shaky solve says it is weaker than we thought, so it lasts half as long
— the card comes back sooner until a clean pass raises the estimate. Reading
the solution is not a retrieval at all, so the estimate is replaced. The first
review sets the estimate: one day for a clean solve, six hours for a shaky one,
ten minutes if you read the solution.

When a clean solve pushes stability to **90 days (three months)**, the card
retires and leaves the sheet. If a retired problem comes back and you rate it
`hard` or `extreme`, it returns — the estimate was wrong.

**The problem's Easy / Medium / Hard tag is not an input.** It is a community
label; it says nothing about how hard the problem was *for you*. A problem
tagged Hard that you keep solving cleanly retires just like an Easy one, and a
problem tagged Easy that you keep fumbling stays in rotation. The rating is the
only evidence the scheduler trusts. That is what makes the sheet
**self-selecting**: doubles push comfortable problems out, halves keep shaky
ones close.

---

## The algorithm, in plain terms

Think of every problem as having **one number** attached to it:

> "How many days until I would probably forget this?"

That number is the card's **stability**. That is the whole idea.

### The forgetting rule

If a card's stability is **4 days**, then after 4 days your chance of
remembering it is **90%**. After that it keeps getting worse:

| Days since review | Chance you remember |
| --- | --- |
| 4 | 90% |
| 8 | 81% |
| 12 | 73% |
| 16 | 66% |

So the app brings the problem back **exactly when you hit 90%** — right before
you start forgetting it. Nothing else decides when a problem comes back.

### How a rating changes the number

| You say | What it means | What happens to the number |
| --- | --- | --- |
| **Medium** | "I solved it, but it was work." | **Doubles.** You knew it better than we thought. |
| **Hard** | "I barely got it." | **Halves.** You knew it worse than we thought. |
| **Extreme** | "I read the solution." | **Reset to 10 minutes.** You did not really remember it. |
| **Very easy** | "I do not need this again." | **Not scheduled.** It leaves the practice sheet. |

Good recall buys more time. Bad recall brings the card back sooner.

### The first review is special

There is no number to double or halve yet, so the first rating **sets** it:

- First **Medium** → comes back **tomorrow**
- First **Hard** → comes back in **6 hours**
- First **Extreme** → comes back in **10 minutes**

### A real example

You solve **Two Sum** and rate it **Medium** every time:

| When | Rating | Stability | Comes back |
| --- | --- | --- | --- |
| Day 0 | Medium (first) | 1 day | Day 1 |
| Day 1 | Medium | 2 days | Day 3 |
| Day 3 | Medium | 4 days | Day 7 |
| Day 7 | Medium | 8 days | Day 15 |
| Day 15 | Medium | 16 days | Day 31 |
| Day 31 | Medium | 32 days | Day 63 |
| Day 63 | Medium | 64 days | Day 127 |
| Day 127 | Medium | 128 days | **Retired** |

Once stability passes **90 days**, the app decides you know it and the card
leaves the sheet.

Now imagine you keep rating it **Hard** instead:

> 8 days → 4 → 2 → 1 → 12 hours → 6 hours → 10 minutes

It keeps coming back faster until you get it cleanly. That is the point.

### What the queue orders on

**Most forgotten first**, not "oldest first". A 1-day card that is 2 days late
is in worse shape than a 30-day card that is 1 day late, so the app computes
predicted recall for every due card and serves the lowest one first. The
Practice bar shows that percentage ("85% recalled"), and after a rating it says
when the card is coming back.

### What does not matter

The problem's official **Easy / Medium / Hard** tag is **not** an input. That
tag says how hard the problem is for the community; your rating says how hard
it was **for you**. A problem tagged Hard that you keep solving cleanly retires
just like an Easy one; a problem tagged Easy that you keep fumbling stays in
rotation. Your rating is the only evidence the app trusts.

### The one-sentence version

> Every problem has a "days until you would forget it" number. Rate the
> attempt, the number doubles or halves, and the problem comes back exactly
> when your memory is about to hit 90%.

---

## What works today

| | |
| --- | --- |
| **Landing** | An animated monochrome wordmark that grows a plant from every letter, types the wrong word, then deletes it and types the right one. |
| **Accounts** | Email and Google sign-in against Supabase. |
| **Learn** | The catalogue as **sheets** — a named group of problems, in the order to do them, each with a progress bar. Search narrows to the sheet that has the question. |
| **Problem screen** | The statement, its worked examples and its constraints on the left; the editor and the test cases on the right. |
| **Practice** | The due queue, one problem at a time, rated after each. Shows predicted recall and when the card comes back. |
| **Home** | The dashboard: due today, memory strength, a twelve-week review chart, up next, rating mix, recent reviews, and the tags behind shaky attempts. |
| **Profile** | Your account and numbers, plus a **shareable public profile** at `/p/:token` that opens without an account. |
| **Compiler** | A free-form C++ workspace that runs on a local `g++` (Judge0 is the fallback). |

### The sheets

The catalogue is split into two sheets — **Git Gud Sheet** (all 119 problems,
in the order that builds on itself: arrays and hashing first, then two pointers,
then dynamic programming, then the rest) and **LeetCode 75** (the classic
curated list).

A sheet is a course. Each one shows a progress bar of how many of its problems
you have solved, and its problems are **numbered**, because a course has a
sequence. Searching narrows to the sheet that has the question, and the sheet's
own list narrows to the matching problem. An open sheet has a **Continue**
button that jumps to the first problem you have not ticked off.

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

### Practice

The due queue. Problems come back **most forgotten first** — ordered by
predicted recall, not by how overdue the clock says they are — one at a time.
You attempt it, rate it, and it goes back out to when it is next due. The bar
shows the card's predicted recall, and after each rating it says when the
problem comes back, or that it has retired. When nothing is due you get a
**Practise again** button that runs the rest of the sheet ahead of schedule.

A problem you have already got right carries a tick in the Learn list, and the
list filters by done / not done and by difficulty.

The scheduling rules live on the server, in `backend/app/core/scheduler.py`, and
they are covered by tests. The cards, the solved list and the review log live in
Supabase; the browser loads them through `/api/v1/practice/state` and keeps an
in-memory copy for rendering. The client never computes an interval.

### Home and Profile

Home is the dashboard. It reads the review log from the API and turns it into
the numbers you would want after a week of practice: due today, memory strength,
a review chart, what is next, how the attempts have felt, and the last few
reviews. The AI coach is listed there and explicitly marked **not in this
build** — it is the next thing, not a shipped feature dressed up as one.

Profile is the account, the stats, and a share link. The link is `/p/<token>`,
where the token is a random value on your profile row; it opens with no account
required and renders the **current** numbers from the database. The public
response carries counts only — no email, no user id, no review log — and a
token that is switched off returns 404. Older snapshot links still decode.

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

Both halves need the Supabase project. Copy the examples and fill them in:

```bash
cp frontend/.env.example frontend/.env
cp backend/.env.example backend/.env
```

`frontend/.env` carries the URL and anon key, which auth needs:

```ini
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key>
```

`backend/.env` carries the same URL, the anon key and the **service-role key**,
because the API owns the database writes:

```ini
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_ROLE_KEY=<service role key>
TRUST_CLIENT_USER_ID=false
```

The anon key is designed to be public — it ships in the browser bundle and is
protected by row-level security. The service-role key is not, and must never go
in `frontend/.env` or any `VITE_` variable. `TRUST_CLIENT_USER_ID=false` is what
stops an anonymous caller claiming a user id from a header; the browser sends
its Supabase access token instead.

The compiler needs no keys: it uses the `g++` on this machine, and Judge0's
public instance is the key-free fallback.

### Load the database

Apply `supabase/migrations/0001_catalogue.sql` in the Supabase SQL editor, then
seed the catalogue:

```bash
.\backend\.venv\Scripts\python.exe supabase\seed\seed.py --dry-run
.\backend\.venv\Scripts\python.exe supabase\seed\seed.py
```

That loads 119 problems, 3,153 test cases and both sheets. The script reads
`backend/.env`; `supabase/README.md` has the details. Restart the backend after
re-seeding, because the catalogue is cached in process.

---

## The stack

| | |
| --- | --- |
| **Frontend** | Vite 8, React 19, TypeScript 6, Tailwind CSS 4, Monaco for the editor |
| **Backend** | FastAPI, Pydantic, Supabase auth + Postgres |
| **Judging** | A local `g++` (C++17); Judge0 is the fallback |

```text
browser ──> Vite :5173
              ├── /api/* ──> FastAPI :8000 ──> local g++ (Judge0 fallback)
              │                   │
              │                   ├──> Supabase Postgres
              │                   │    catalogue + practice state
              │                   └──> supabase/seed/*.json  (offline fallback)
              └── static assets

browser ──> Supabase Auth  (sign in only, directly)
```

---

## Layout

```text
ReSolve/
├── AGENTS.md            <- the source of truth for the product and the code
├── supabase/
│   ├── migrations/      <- catalogue, practice state, profiles, RPCs
│   └── seed/            <- the 119-problem catalogue, the sheets, the loader
├── backend/
│   ├── app/             <- FastAPI
│   ├── scripts/         <- tooling for maintaining the catalogue
│   └── run.py           <- start the server with this
└── frontend/
    └── src/
        ├── index.css    <- every design token lives here
        ├── lib/         <- supabase auth, navigation, problems, practice store
        ├── components/  <- app shell, guards, code editor, markdown
        └── pages/       <- one file per surface
```

The catalogue is authored as JSON in `supabase/seed/`, seeded into Postgres,
and read from Postgres at runtime. `backend/app/core/problems.py` is the only
file that knows that; the JSON path remains as the no-credentials fallback for
a fresh clone and for the test suite.

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

The catalogue is the beginning, not the product. The scheduler is the thing
that has to exist: it is the entire thesis, and it is real — a memory curve that
schedules each problem for the moment predicted recall reaches 90%.

The database is now the store: the catalogue, the cards, the review log and the
profiles all live in Supabase. A browser's old `localStorage` bucket is uploaded
once, on the first load after the switch, and deleted when the import succeeds.

The open questions live in [`AGENTS.md`](./AGENTS.md) §11 — chiefly whether to
fit the growth factors from accumulated review logs, whether to add a
sharing-off / token-rotate control, and whether the catalogue stays
single-language.

---

## Licence and attribution

Problem titles and sheet membership are transcribed from publicly published
problem lists (NeetCode, Blind 75, Striver SDE, Love Babbar 450). Every
problem statement is original to this project.
