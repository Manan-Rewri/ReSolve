# AGENTS.md — ReSolve

> **Read this file completely before writing any code.**
> It is the single source of truth. If this file and your memory disagree, this
> file wins. If you are about to assume something that is not written here,
> verify it in the repo or ask a human. Do not invent it.

---

## 1. What ReSolve is

ReSolve is a coding practice platform. It has problems and a code editor, like
LeetCode — and that is exactly where the similarity ends.

LeetCode optimises for a one-shot solve-and-forget dopamine hit. ReSolve is built
around **spaced repetition**: the Anki phenomenon, transplanted to algorithms.
Every problem a user attempts gets rated, scheduled, and brought back until it
sticks.

**The thesis:** you do not fail at DSA because you lack problems, you fail
because you forget the ones you already solved. ReSolve is a memory system, not
a content library.

**One-line pitch:** *Solve a problem. Rate how it felt. We decide when it comes
back.*

---

## 2. The core loop (the most important product primitive)

This is the mechanic the whole product hangs off. Do not change it casually.

1. User opens a **practice session**.
2. Session serves problems that are **due** today (Anki-style queue).
3. User attempts a problem in the editor.
4. On submit, the user **rates the problem**:
   - `very easy` — I do not need to practise this again, so it does not enter
     the practice sheet at all
   - `medium` — I solved it, but it was work
   - `hard` — I struggled, or nearly failed it
   - `extreme` — I read the solution, so I did not really do it myself
5. That rating drives a **spaced repetition schedule** for that
   (user, problem) pair.
6. The problem is added to the user's **practice sheet** — the deck that keeps
   resurfacing it.

The ratings were originally `again` / `hard` / `easy` / `done`. A human changed
them twice: first to separate "shaky but finished it" from "failed it", and
then to `very easy` / `medium` / `hard` / `extreme`, because `very easy` is not a
schedule at all — it is a decision not to add the problem to the sheet.

### Key insight to preserve

Difficulty is **not** an input the user picks from the problem metadata. The
user rates **how that attempt felt for them**. "Hard" means *this was hard for
me*, which is a completely different axis from the problem's official Easy /
Medium / Hard tag. Conflating these two axes is the single biggest modelling
mistake you can make in this codebase.

Both axes exist and are stored separately:

| Concept                     | Meaning                        | Stored as            |
| --------------------------- | ------------------------------ | -------------------- |
| **Problem difficulty**      | Community-wide tag (Easy/Med/Hard) | `problems.difficulty` |
| **Personal rating**         | How that attempt felt *for me* | `review_logs.rating`    |

---

## 3. Domain glossary

Keep these terms stable in code, schema, types and UI copy.

| Term                 | Definition                                                                 |
| -------------------- | -------------------------------------------------------------------------- |
| **Problem**          | A single coding challenge. Immutable content: statement, tests, tags.        |
| **Attempt**          | One submission of code against a problem by one user.                        |
| **Review log**       | A graded review event: problem + user + rating + timestamp. Drives scheduling. |
| **Practice sheet**   | A user's deck of problems scheduled for spaced repetition.                   |
| **Card state**       | The per-(user, problem) SRS record: stability (days until 90% recall), due date, reps, lapses. |
| **Due queue**        | Cards whose `due_at <= now`, ordered for a practice session.                |
| **Rating**           | `medium` / `hard` / `extreme` — the post-attempt self-assessment. `very easy` is a fourth option, but it is a decision not to schedule the problem at all. |
| **New**              | Problem never attempted by this user.                                       |
| **Learning**         | Card currently in its first few reps (still fragile).                        |
| **Review**           | Mature card being re-tested at increasing intervals.                         |
| **Relearning**       | A mature card that was failed and is being rebuilt.                          |

---

## 4. Tech stack — verified, do not "correct" these

These versions are what is actually installed and verified working as of
2026-10-19. Do not upgrade them casually and do not assume different versions.

### Frontend — `frontend/`

| Thing             | Version  | Notes                                                        |
| ----------------- | -------- | ------------------------------------------------------------ |
| Node              | v24.19.0 |                                                              |
| npm               | 11.17.0  |                                                              |
| Vite              | 8.3.4    |                                                              |
| React             | 19.3.1   |                                                              |
| @supabase/supabase-js | 2.118.0 | Browser client (anon key only). Auth only — state goes through the API |
| TypeScript        | 6.0.3    | `erasableSyntaxOnly` is on — no enums, no parameter properties |
| Tailwind CSS      | 4.3.3    | **v4, CSS-first config.** No `tailwind.config.js`            |
| ESLint            | 10.13.0  | Flat config only (`eslint.config.js`)                         |
| @vitejs/plugin-react | 6.1.2 |                                                            |
| react-router-dom  | 7.18.4   | Routing                                                           |
| monaco-editor     | —        | Lazy-loaded; see §9                                            |

### Backend — `backend/`

| Thing       | Version  | Notes                                                       |
| ----------- | -------- | ----------------------------------------------------------- |
| Python      | 3.15.0   | System Python; venv at `backend/.venv`                      |
| FastAPI     | 0.143.3  |                                                              |
| Uvicorn     | 0.54.0   | Plain uvicorn, **not** `uvicorn[standard]` — see §9          |
| Pydantic    | 2.14.1   |                                                              |
| supabase-py | 2.33.0   | Sync client only                                             |
| pytest      | 9.1.1    |                                                              |
| ruff        | 0.17.1   | Config in `backend/pyproject.toml`                           |

### Infrastructure

- **Supabase is the auth provider and the database.** The browser signs in
  against it directly (email + password, Google OAuth) and has the anon key.
- **Practice state lives in Postgres.** `card_state`, `solved_problems` and
  `review_logs` hold each user's cards, sheet and history. The browser reads
  them through the API and keeps only an in-memory copy.
- **The catalogue lives in Postgres too.** `problems`, `test_cases`, `sheets`
  and `sheet_problems` are seeded from `supabase/seed/`. The JSON files are the
  seed, not a second runtime source.
- The FastAPI backend talks to Supabase with the service-role key. The browser
  never does; it sends its Supabase access token to our API, which verifies it.
- **The old localStorage bucket is imported once.** `practice-store.ts` reads
  `resolve.practice.v2:<user-id>` if the account has no rows yet, POSTs it to
  `/practice/import`, and deletes it on success. The server refuses a second
  import into a non-empty account.
- **A local g++ runs the C++.** `backend/app/core/judge.py` compiles and runs
  submissions on this machine (`RESOLVE_CXX`, default
  `C:\w64devkit\bin\g++.exe`), which is fast and needs no network.
- **Judge0 is the fallback.** When there is no local compiler, `ce.judge0.com`
  runs it instead. It needs no API key.
- No separate auth service, no custom JWT signing.

### Getting it running

Two processes, in two terminals.

**Backend, port 8000:**

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Expect `{"status":"ok","service":"resolve-api"}`.

**Frontend, port 5173:**

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api/*` to
`http://127.0.0.1:8000`, so the browser never talks to the backend directly.

**Start the backend with `run.py`, never `uvicorn app.main:app`** — see §9.

### Configuration

Neither `.env` file is committed. Both are needed for the real product:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

`frontend/.env` needs the Supabase URL and anon key, or the app renders an
explanation instead of a white screen.

```ini
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key>
```

The anon key is designed to be public — it ships in the browser bundle and is
gated by row-level security. The **service-role key is not** and must never go
in `frontend/.env` or any `VITE_` variable.

`backend/.env` needs the same project and the service-role key, because the API
owns the practice writes:

```ini
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_ROLE_KEY=<service role key>
TRUST_CLIENT_USER_ID=false
```

**`TRUST_CLIENT_USER_ID=false` is not optional once the database is live.** The
`X-Resolve-User` fallback exists for a checkout with no credentials; with the
database configured, trusting it would let an anonymous caller claim somebody
else's `user_id`. The browser sends its access token instead.

The compiler works with no keys at all — a local g++ runs it, and
`ce.judge0.com` is the key-free fallback. `backend/.env` can be left empty for
that, and then the catalogue falls back to the JSON seed and practice state to
`backend/data/state.json`. The test suite forces both (`PRACTICE_STORE=file`,
`RESOLVE_CATALOGUE=json`) so it never touches the network.

---

## 5. Current features

What exists and works today.

| Surface | State | Where |
| --- | --- | --- |
| Landing page (`/`) | Built | `src/pages/landing-page.tsx` |
| Register | Built, live against Supabase | `src/pages/register-page.tsx` |
| Login | Built, live against Supabase | `src/pages/login-page.tsx` |
| 404 | Built | `src/pages/not-found-page.tsx` |
| Home | **Default view — the dashboard.** Due today, memory strength, activity, up next, rating mix, recent reviews. | `src/pages/home-page.tsx`, `src/pages/dashboard-view.tsx` |
| Learn | Built | `src/pages/learn-view.tsx` |
| Problem screen | Built | `src/components/problem-workspace.tsx` |
| **Practice** | **Built.** The due queue, one problem at a time, rated after each. Shows predicted recall. | `src/pages/practice-view.tsx` |
| Compiler | Built | `src/pages/compiler-view.tsx` |
| Profile | Built — account, stats, share link, public profile at `/p/:token` | `src/pages/profile-view.tsx`, `src/pages/public-profile-page.tsx` |

### Where a signed-in user lands

**Home.** A signed-in user opening the site is sent from `/` to `/home`, and
`/home` opens on Home. Home is the **dashboard**: the problems due, the
predicted memory strength of the sheet, a twelve-week review chart, what is
next, how the attempts have felt, the tags behind the shaky attempts, and the
AI coach that is deliberately not part of this build.

The dashboard is computed from the state the API loaded — the cards and review
log in Postgres — and `RequireAuth` waits for that load (`practiceReady`)
before it renders, so the page cannot flash zeros or build a share link from an
empty bucket. It reads `stats()` and `usePracticeState()` from
`practice-store.ts`; it does not recompute any scheduling rule. The AI panel is
labelled **"Not in this build"** on purpose: it is a statement of intent, not a
shipped feature.

### Landing

Full-bleed Type Garden canvas with two calls to action under the wordmark.
Responsive down to mobile and short landscape viewports. The garden is live
canvas text, not a static image — it types the word, so it can be animated and
corrected.

### Auth

Register is a four-step, one-question-at-a-time wizard (username, email,
password, confirm). Login is a single two-field form. Both have "Continue with
Google" and a cross-link. Supabase handles email+password and Google OAuth
directly from the browser.

The **practice state** is Supabase too: the browser sends its access token to
our API, which verifies it and reads the user's rows with the service-role key.
See §6.

Every password field has a reveal button — an eye drawn inline in
`auth-field.tsx`, not from an icon library — and a placeholder. A field with
something to fix gets a red border, and the message under it is red too.

Route guards in `src/components/guards.tsx`: `RedirectIfAuthed` sends signed-in
users from `/`, `/register`, `/login` to `/home`; `RequireAuth` bounces anyone
without a session from `/home` back to `/`. A missing `.env` renders an
explanation rather than a white screen.

### Learn

The catalogue is grouped into **sheets**. A sheet is a course: a named group of
problems, in the order they should be done.

Right now there are two:

| Sheet | Problems |
| --- | --- |
| **Git Gud Sheet** | 119 — every problem in the catalogue |
| **LeetCode 75** | 75 — the classic curated list |

The order is the curriculum: arrays and hashing first, then two pointers, then
dynamic programming, then the rest. Each sheet shows a hairline progress bar of
how far through it you are, because a sheet is progress and a number is not.
Open one and its problems appear **numbered and in order**, with the tick on the
ones you have solved.

**Searching narrows to the sheet that has the question.** Typing "two sum" in
the search leaves the sheet that contains Two Sum, and the sheet's own list
narrows to the matching problem. The matching rule is one function,
`matchesQuery`, used at both levels.

The open sheet and the search both live in the URL — `?view=learn&sheet=…&q=…`
— so a search is a link worth sending, and the back button closes the sheet.

An open sheet also carries a **Continue** button: it opens the first problem in
the sheet you have not ticked off, in curriculum order. A sheet with everything
done says "Sheet complete" and cannot be clicked. The button is the difference
between a catalogue and a course.

The sheets live in `supabase/seed/sheets.json`. A problem may appear in more
than one sheet — Git Gud holds every problem, LeetCode 75 is a curated subset —
but every problem must be in **at least one**. The server refuses to serve a
catalogue where a problem is in no sheet, because that is a silent gap rather
than a course.

### The problem screen

Statement on the left. On the right: the editor above, the test cases below.

**The editor holds only the function.** It is seeded with the signature and an
empty body:

```cpp
vector<int> twoSum(vector<int>& nums, int target) {
    
}
```

No includes, no `main`. The user writes inside the braces.

**The test cases show everything.** For every case: the input, the expected
output, and what the submission actually produced. Failing rows are the only
ones emphasised. Nothing is hidden or sampled — a hidden case is a hidden bug.

Under the statement are the **worked examples** and the **constraints**. They
are in the data and they are on the page — a problem you cannot check the
examples of is a problem you cannot solve.

### Rating

When you have **attempted** a problem, the user is asked how it went. The
answer decides whether the problem joins the practice sheet, and where it
starts on the memory curve.

| Rating      | In the sheet | What it means                              |
| ----------- | ------------ | ------------------------------------------ |
| `very easy` | **No**       | I do not need to practise this again.      |
| `medium`    | Yes          | I solved it, but it was work.              |
| `hard`      | Yes          | I struggled, or nearly failed it.          |
| `extreme`   | Yes          | I read the solution. I did not do it myself. |

`very easy` is not a schedule, it is a decision not to add the problem to the
sheet at all — and if it was already in rotation, `very easy` takes it out. The
other three are the scheduler's three ratings.

**The question is asked whether or not the solution passed.** A problem you
attempted and got wrong is exactly the one you need to practise, so it must not
be silently dropped — and the tick is only given for a full pass. This was a
real bug: the popup used to appear only on a full pass, so a session of work
left the practice sheet empty and the page said "solve some questions in Learn
first" to someone who had just solved a dozen.

The popup asks this after a check in Learn. Practice asks for medium, hard or
extreme after each problem, because nothing is on offer to look up there — if
you could not do it yourself, that is a hard one.

### Never fail silently

A request that cannot be saved must say so. The rating used to `return null` on
a failed POST, which meant: a browser tab still running an older bundle sent
`done`, the new server only accepted `extreme`, it answered 422, and the user
got **no message at all** — the click did nothing visible, the problem never
reached the sheet, and there was no way to tell that from "I rated it very
easy on purpose".

That is how a practice sheet ends up empty with three solved problems in it and
no explanation. A write that fails says so, in the place the user is looking.

The same rule covers the shape of a card. A card that arrives without a
stability is **dropped on read** (`normaliseCard`) rather than coerced into a
stability it never had. A made-up interval is worse than a missing card,
because the user would never know. That applies to the API response and to the
old `resolve.practice.v2:<user-id>` bucket, which is now only a migration
source.

A failed load or write is shown in the shell's `.app-notice` banner, not
swallowed by the store.

### The memory curve

This is the algorithm, and it is deliberately small enough to explain in a
sentence.

**Every card carries a stability: the number of days until your chance of
recalling that problem has decayed to 90%.** Recall is modelled as

```
recall(t) = 0.9 ** (t / stability)
```

and the card is scheduled for exactly `t = stability` — the edge of forgetting.
Nothing else in the product decides when a problem comes back.

**A rating updates the estimate:**

| Rating | Meaning | What happens to stability |
| --- | --- | --- |
| `medium` | you solved it, but it was work | **× 2**, at least one day |
| `hard` | you barely got it | **× 0.5**, at least ten minutes |
| `extreme` | you read the solution | **reset** to ten minutes, counts a lapse |

A clean solve says the memory is stronger than we thought, so it lasts twice as
long. A shaky solve says it is weaker than we thought, so it lasts half as long
— the card comes back sooner until a clean pass raises the estimate. Reading
the solution is not a retrieval at all, so the estimate is replaced.

The **first** review has no estimate to update, so it sets one: a clean first
solve is back tomorrow, a shaky one in six hours, and one that needed the
solution in ten minutes.

**Retirement.** When a `medium` pushes stability to **90 days (three months)**,
the card graduates and leaves the practice sheet. Only a clean solve can retire
a card, and only after it has doubled its way there. If a retired problem is
attempted again and rated `hard` or `extreme`, it comes back: the estimate was
wrong, so it starts over.

**The problem's difficulty is not an input.** The Easy / Medium / Hard tag is a
community label; it says nothing about how hard that problem was *for you*.
Using it to set a ceiling would conflate the two axes §2 warns about. A problem
tagged Hard that you keep solving cleanly retires just like an Easy one; a
problem tagged Easy that you keep fumbling stays on your sheet for as long as
it needs to. The rating is the only evidence the scheduler trusts.

**This is what makes the sheet self-selecting.** Every clean solve doubles the
interval, so a problem you are comfortable with retires in seven or eight
sessions; every shaky solve halves it, so a problem you keep fumbling never
gets far. What is left in the sheet is what you are actually shaky on.

The rules live in `backend/app/core/scheduler.py` as pure logic — a card, a
rating, and the card that comes out the other side. No I/O and no clock of its
own, so it is all testable, and it is covered by tests.

**What a session looks like.** A user solves Two Sum in Learn, rates it medium,
and it comes back tomorrow. Tomorrow they solve it and rate it medium again,
and it comes back in two days, then four, then eight. When a clean solve takes
it past ninety days, it retires: they know Two Sum.

Meanwhile a problem they keep fumbling halves every time it is shaky. It comes
back in hours, over and over, until they get it cleanly — at which point it
starts spacing out. A card that is rated `extreme` is back in ten minutes,
which is why the queue is re-read while the page is open.

**What the queue orders on.** Predicted recall, not the clock. A one-day card
two days late is in worse shape than a thirty-day card one day late, and the
queue should say so.

### Practice

The queue. One problem at a time, the ones that are due, **most forgotten
first** (ordered by predicted recall, not by how overdue the clock says it is).
You attempt it, rate it, and it goes back out to when it is next due.

The bar above the editor shows the current card's **predicted recall**, and
after a rating it says when the problem comes back ("Saved — back in 2 days")
or that it has retired. The algorithm is visible, not implied.

The queue is **re-read every twenty seconds** while the page is open, because
a problem you got wrong comes back in a minute. Without the poll it would sit
there until you reloaded, and the same-day retry would never happen.

When nothing is due, the page says **"Nothing due"** and offers a **Practise
again** button. That runs the rest of the sheet ahead of schedule, one problem
at a time, so the sheet is never a dead end. A problem already done in that run
is left out, so the list always moves on.

A card that has graduated is never in either list.

### Profile

The drawer's last entry is **Profile**, not Settings. It shows the account
(name, email, provider, member since), the numbers from the scheduler (solved,
in rotation, reviews, streak, memory strength, learning/reviewing/retired,
lapses), solved-by-difficulty, strongest tags, and the share link.

**The share link is live.** It is `/p/<token>`, where the token is a random
128-bit value on the owner's `profiles` row (`POST /profile/share` creates it).
The public page fetches `/api/v1/public/profiles/{token}` **without a session**
and renders the counts the API assembled from the database.

The response carries no email, no user id and no review log — only what the
profile displays. The token is not a user id, so it cannot be edited into
somebody else's profile, and `is_public = false` makes the link 404 without
deleting anything. Both the API response and the old snapshot path are clamped
by `normaliseProfile`, so a hostile value cannot inject markup or a 100MB name.

Older links that carry a snapshot still decode (`decodeProfile`), and the
profile page falls back to building one if the share request fails. The layout
is identical either way.

Profile is also where the **AI coach** would eventually surface private
analysis. The dashboard's AI panel is explicitly marked "Not in this build".

### The tick

A problem the user has got fully right carries a tick in the Learn list, so
they can see at a glance what they have already done. The Learn list also
filters by **done / not done** and by **difficulty**, on top of the search box.

### The compiler

Two equal columns. Editor on the left, input over output on the right. The
page fits the viewport; only the panes scroll internally. This is the free-form
compiler: it runs whatever is in the editor, with stdin you type.

---

## 6. Architecture

### The shape of a request

```
browser ──> Vite dev server :5173
              │
              ├── /api/*  ──proxied──> FastAPI :8000 ──> local g++ (Judge0 fallback)
              │                            │
              │                            ├──> Supabase Postgres
              │                            │      catalogue + practice state
              │                            └──> supabase/seed/*.json  (offline fallback)
              │
              └── everything else ──> static assets

browser ──> Supabase Auth  (sign in only, directly)
browser ──> legacy localStorage bucket  (read once, uploaded to the API)
```

The frontend calls the API through a **relative** `/api/v1/...` path. Vite
proxies it. Never hardcode `http://localhost:8000` in component code.

### The API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Liveness. |
| `GET` | `/api/v1/problems` | Every problem, summarised. Enough to render and filter the list. |
| `GET` | `/api/v1/problems/{slug}` | One problem: statement, examples, constraints, signature. |
| `GET` | `/api/v1/problems/{slug}/cases` | Every test case, with its expected output. |
| `POST` | `/api/v1/judge` | `{slug, code}` — run a function against that problem's cases. |
| `POST` | `/api/v1/compile` | Run arbitrary C++. `{source_code, stdin, language_id}`. |
| `POST` | `/api/v1/practice/preview` | `{slug, rating, card?}` — apply a rating, get the next card. Stores nothing. |
| `GET` | `/api/v1/practice/state` | `{cards, sheet, solved, history}` for the signed-in user. |
| `POST` | `/api/v1/practice/schedule` | `{slug, rating}` — apply a rating, save the card and log it. |
| `GET` | `/api/v1/practice/queue` | The problems that are due, most forgotten first. |
| `POST` | `/api/v1/practice/solved` | Record a full pass on a problem. |
| `POST` | `/api/v1/practice/very-easy` | Remove a problem from the sheet; keep the solved tick. |
| `POST` | `/api/v1/practice/import` | Upload a legacy localStorage bucket once. 409 if the account has rows. |
| `POST` | `/api/v1/profile/share` | The owner's share token, created on first use. |
| `GET` | `/api/v1/public/profiles/{token}` | The public counts. No session, no private fields. |

**The API holds the practice state.** Each stateful endpoint verifies the
Supabase access token and reads or writes the user's rows with the
service-role key. The browser keeps only an in-memory copy for rendering; it
does not own the rules and does not touch a table directly.

The rules live in exactly one place: `POST /practice/schedule` runs
`app/core/scheduler.py` on the card the server already has and stores the
result. Two tabs cannot rewind each other, because the previous card is read
server-side rather than sent by the client. `POST /practice/preview` is the
pure version of the same call: no user, nothing read, nothing written.

Every `/practice/*` endpoint that touches a user requires an identified user.
`get_user_id` verifies the bearer token; the `X-Resolve-User` fallback only
works when `TRUST_CLIENT_USER_ID=true`, which must be false once the database
is configured. A request with neither gets 401.

`/api/v1/judge` and `/api/v1/compile` are unauthenticated. **Re-add
`Depends(get_current_user)` before exposing this publicly** — an open proxy to
a code runner is a known abuse vector (cryptomining, spam).

### The catalogue

The catalogue is authored in **`supabase/seed/problems.json`** and
**`sheets.json`**, seeded into Postgres, and read from Postgres at runtime:

```text
supabase/
├── migrations/0001_catalogue.sql  <- catalogue, practice state, profiles, RPCs
└── seed/
    ├── problems.json               <- the 119 problems
    ├── sheets.json                 <- the sheets, and the order
    └── seed.py                     <- the transfer
```

`supabase/README.md` has the details. Each problem carries a statement, worked
examples, constraints, a C++ signature and its parameters, a reference
solution, the C++ that goes before and after the user's function, and 20-30
test cases with their expected output.

`backend/app/core/problems.py` is the only module that knows where the
catalogue lives. It queries Supabase when configured and falls back to the JSON
when not (`RESOLVE_CATALOGUE=json` forces the fallback; the test suite does).
The database results are cached with `lru_cache`, so **restart the backend after
re-seeding** — there is no `--reload`.

### The scheduler

`backend/app/core/scheduler.py` is pure logic: a card, a rating, and the card
that comes out the other side. No I/O and no clock of its own — the caller
passes the time in, so it is all testable.

| Rating   | What happens to stability                  |
| -------- | ------------------------------------------ |
| `medium` | × 2, at least one day.                     |
| `hard`   | × 0.5, at least ten minutes.               |
| `extreme`| Reset to ten minutes; counts a lapse.      |

A first review sets the estimate instead of scaling it: `medium` one day,
`hard` six hours, `extreme` ten minutes. A `medium` that pushes stability to
**90 days** retires the card. See §5 for the whole thing.

The scheduler also exposes `recall(card, now) = 0.9 ** (elapsed / stability)`.
That one formula is used by the queue ordering, the Practice bar and the
dashboard's memory-strength number, so none of them can drift from the model.

The client keeps the cards in memory in `src/lib/practice-store.ts`: it loads
`/practice/state` when the session changes and re-renders subscribers after a
write. The **rules** are not duplicated there — `applyRating` posts
`{slug, rating}` to `/practice/schedule` and keeps the card the server returns.
`refresh()` is what `setUser`/the auth provider call, so signing in as someone
else switches sheets.

The **review log** (slug, rating, timestamp, capped at 5000 events) drives the
dashboard and profile; the scheduler never reads it, because a rating already
carries everything it needs. The server caps it on write/read and `store.py`
keeps both backends (`Supabase` and the file fallback) in one shape.

### The function-only editor

Each problem stores the C++ that goes around the user's function:

```
prefix + the user's function + suffix
```

The **prefix** is the includes, the namespace, and the printers. The **suffix**
is a `main` that runs every stored case and prints the result after a marker,
so one run carrying every case can be split back apart.

`POST /api/v1/judge` splices the two, runs the result locally (or on Judge0 when
there is no compiler), splits the output by the marker, and compares each piece
against the stored expected output.

### Rules for the catalogue

These are not preferences. Each one exists because breaking it produced a
silently wrong answer.

- **The signature comes from our data, never from a model.** A model was once
  asked to write the function for a problem and, given "Best Time to Buy and
  Sell Stock", it returned a complete, self-consistent suite for Two Sum.
  Because the expected output is derived by *running* the reference, nothing
  downstream could have noticed.
- **Expected output is measured, never predicted.** Every stored expected
  output was produced by compiling and running the problem's own reference
  solution on Judge0. Never hand-write an expected output.
- **A test case that proves nothing is not a test case.** An empty expected
  output is an automatic pass for any submission, so it is dropped. A case
  whose arity does not match the signature cannot be declared, so it is
  dropped. A duplicate proves the same thing twice, so it is dropped.
- **The printers decide what an answer looks like.** A `bool` prints as
  `true`/`false`, a `string` prints with its quotes, a `double` keeps a
  decimal point (`2.0`, not `2`). A test case that disagrees with its own
  statement's examples is worse than useless.
- **A problem that returns nothing prints the parameter it changed.**
  `void moveZeroes(vector<int>& nums)` has no return value, so the harness
  prints `nums` after the call. The problem stores which parameter holds the
  answer.
- **Reference solutions must be deterministic.** One that returns groups or
  elements in hash-map order gives a different answer every run, and the
  stored expected output would be wrong. Sort the output.
- **Arguments are stored as a list, not a joined string.** An argument can
  contain a comma — a `vector<string>` of six words has five — so splitting a
  joined string is lossy. It silently corrupted every `vector<string>` case.
- **A problem is either complete or it is not listed.** Never surface an entry
  without a full statement. No "no write-up yet" screens: a human explicitly
  rejected a design where most listed problems were empty.
- **Statements are authored, never scraped.** LeetCode has no free public API
  and scraping breaches their ToS. Titles, difficulty, tags and sheet
  membership may be transcribed from openly published lists (NeetCode
  75/150/250, Blind 75, Striver SDE, Love Babbar 450); every statement must
  be written for ReSolve.

### Maintaining the catalogue

`backend/scripts/` holds the tooling. `README.md` there has the workflow.

```bash
cd backend

# Fill in the expected output from the reference solution.
.\.venv\Scripts\python.exe scripts\measure.py

# The reference must reproduce the worked example in the statement.
.\.venv\Scripts\python.exe scripts\check_examples.py

# The stored answers must match a fresh run.
.\.venv\Scripts\python.exe scripts\verify.py
```

The second is the check that catches real mistakes. Everything else agrees with
itself by construction; that one compares the reference against something a
human wrote.

### Repository layout

```
ReSolve/
├── AGENTS.md          <- you are reading this
├── README.md          <- setup guide for a new contributor
├── .gitignore
├── resolve.html      <- original Type Garden source. Reference only; the ported
│                       engine in frontend/src/lib/type-garden.ts is the truth.
├── supabase/         <- the schema and the seed
│   ├── migrations/   <- catalogue, practice state, profiles, RPCs
│   └── seed/         <- the catalogue, and the script that loads it
├── frontend/          <- Vite + React + TS + Tailwind
│   ├── eslint.config.js
│   ├── vite.config.ts <- Tailwind plugin + `@` alias + /api proxy + strictPort
│   ├── index.html     <- Google Fonts live here
│   └── src/
│       ├── index.css  <- ALL design tokens (@theme block) + every page's styles
│       ├── lib/       <- supabase auth, api client, navigation, problems,
│       │                practice store, public profile codec
│       ├── components/<- app shell, guards, code editor, markdown, garden,
│       │                problem workspace, rating dialog
│       └── pages/     <- one file per surface
└── backend/           <- FastAPI
    ├── run.py         <- START THE SERVER WITH THIS. See §9.
    ├── .env.example
    ├── pyproject.toml <- ruff + pytest config only
    ├── requirements.txt <- pinned via pip freeze
    ├── app/loop.py    <- the Windows event-loop workaround
    ├── app/core/      <- config, supabase, problems, scheduler, judge, store,
    │                      profiles
    ├── app/api/v1/    <- health, compiler, problems, practice, profile
    ├── scripts/       <- catalogue tooling, see scripts/README.md
    └── tests/
```

### Conventions

- Import paths in React use the `@/` alias → `frontend/src`.
- Backend Python packages are `app.*`.
- Both stacks have a `lint`/`check` script. Run them before you claim done.
- Pages are **views** under `/home`, not routes. Switching sections does not
  change the URL. `src/lib/navigation.ts` is the list. The exceptions are the
  public surfaces that are *not* sections: `/`, `/login`, `/register` and
  `/p/:token` (a shared profile).
- **Markdown renders to React elements, never HTML.**
  `src/components/markdown.tsx` handles only what the statements use (fenced
  code, headings, bullets, `code`/`**bold**`/`*italic*`) and there is no
  `dangerouslySetInnerHTML` anywhere. Do not swap in a raw-HTML renderer —
  statements will eventually be user input, and that is an XSS hole.

---

## 7. Brand & design system — NON-NEGOTIABLE

The brand is the product. Judges will judge the UI. These rules are not
suggestions.

| Rule            | Detail                                                                     |
| --------------- | -------------------------------------------------------------------------- |
| **Typeface**    | **Space Grotesk** everywhere. Loaded via Google Fonts in `index.html`.      |
| **Mono font**   | JetBrains Mono, for code editor only.                                      |
| **Colour**      | **Monochrome, plus two state colours.** See below.                          |
| **Theme**       | **Dark only.** There is no light mode.                                     |
| **Style**       | Minimal. High contrast, generous whitespace, restrained motion.            |

### The two state colours

The product is about a verdict: passed or failed, solved or not. A human
reading a test-case table needs to find the failure instantly, and hiding that
behind greyscale is a worse design than the one we had.

So there are exactly two hues, and **colour means state, never decoration**:

| Token                | Value     | Used for                                        |
| -------------------- | --------- | ----------------------------------------------- |
| `--color-success`    | `#4cc38a` | A case that matched. An accepted run. A notice. |
| `--color-danger`     | `#f2555a` | A case that failed. A compiler error. A field to fix. |
| `--color-success-soft` | `#0d1f16` | Shading a row, never text.                    |
| `--color-danger-soft`  | `#2a1013` | Shading a row, never text.                    |

They are desaturated toward the brand's greys on purpose: a saturated mid-tone
on pure black vibrates and reads like a badge, and the site is meant to look
like one system.

**Never colour alone.** Every state carries a word as well — "All 24 passed",
"7 of 24 passed", "Accepted" — so it survives colour blindness and a greyscale
screenshot. Colour is the second signal, not the only one.

### Tokens

All tokens are defined once in the `@theme` block in `frontend/src/index.css`.
**Never hardcode a hex value in a component.** Use the token.

| Token                    | Value     | Utility examples                     |
| ------------------------ | --------- | ------------------------------------ |
| `--color-background`     | `#000000` | `bg-background`                       |
| `--color-foreground`     | `#ffffff` | `text-foreground`, `border-foreground` |
| `--color-card`           | `#0a0a0a` | `bg-card`                             |
| `--color-muted`          | `#171717` | `bg-muted`                            |
| `--color-muted-foreground` | `#a3a3a3` | `text-muted-foreground`             |
| `--color-subtle`         | `#262626` | `bg-subtle`                           |
| `--color-subtle-foreground` | `#737373` | `text-subtle-foreground`           |
| `--color-border`         | `#1f1f1f` | `border-border`                       |
| `--color-ring`           | `#ffffff` | `ring-ring`                           |

Because there are no accent colours, **emphasis is done with weight, size,
contrast and inverted surfaces** — e.g. `bg-foreground text-background` for a
primary button. Do not reach for grey-blue "slate" Tailwind defaults as if they
were brand colours; if you use a raw palette step it must be a true neutral.

### The landing page

- **One prose line and one hairline.** "Problems you've solved come back before
  you forget them." No eyebrow labels, no ALL-CAPS, no mono data labels, no
  middle-dot separators, no `→` on CTA text, and **no second hairline** — two
  rules would tip the page into broadsheet territory.
- **The second CTA is glass, not flat ghost.** `.button-glass` — alpha fill,
  `blur(14px) saturate(120%)`, hairline top highlight. The only "material"
  treatment in the system. Do not flatten it.
- **The wordmark is live canvas text, not a static logo asset.** The garden
  draws the word, which is what lets it be typed and corrected. There is no
  logo SVG in the repo.

### The wordmark

- **Monochrome.** `resolve.html` shipped a colour palette (red roses,
  blue-green leaves). It was recoloured: bg `#000000`, roses `#E8E8E8`,
  stems/leaves `#6E6E6E` (lifted from the ReSolve logo SVG), line `#B8B8B8`,
  text `#FFFFFF`, veins `#242424`. Defined once in `PALETTES` in
  `src/lib/type-garden.ts`. Never reintroduce colour.
- **Space Grotesk Bold**, not Playfair Display. The brand font wins over the
  original Type Garden aesthetic. `GARDEN_FONT` in `src/lib/type-garden.ts` is
  the single place to change it.
- **It types the wrong word, then corrects it once.** The intro types `ReSolvx`
  in full, then deletes the `x` and types `e` → `ReSolve`. The 404 page types
  `405` then corrects to `404`. This is ONE correction, not a
  wrong/right/wrong sequence. Configured with the `word` + `correction` props
  on `TypeGarden`; both strings must share a prefix. Lives in
  `startIntro()` in `src/lib/type-garden.ts`.
- **The correction is typed, not swapped.** The sequence is: type the wrong
  word, let the caret blink for a beat, delete the wrong character, then type
  the right one. The word must not move while that happens — the layout
  centres every line, so `layoutAnchored()` holds each line where it was. A
  text editor does not slide the text sideways when a character is deleted,
  and neither should this.
- **A dying character fades out; it does not vanish.** The render pass used to
  skip dead letters entirely, so the wrong glyph popped out of existence while
  its vine lingered — it read as a glitch. Dead glyphs are now drawn with the
  death alpha, so the character fades with the plant around it.
- **Letters fade in, they never travel.** The garden pins every letter to its
  final slot on first layout (`Letter.placed`) and the entrance is a 700ms
  alpha ramp (`FADE_MS`). An earlier port initialised `x/y` to `0`, which made
  letters fly in from the top-left corner.

### The auth pages

- **One question per screen on `/register`.** Four fixed steps: username →
  email → password → confirm. The field is oversized (72px tall, 19px type)
  because it *is* the page, not a control inside a form. Per-step validation,
  `.auth-slot` reserves error height so the layout never shifts mid-step. Do
  not collapse this into one scrolling form.
- **They must never scroll.** `.auth` is `height: 100svh` — never
  `min-height`, which lets the box grow past the viewport and was the cause of
  the scroll. All vertical rhythm uses `clamp()` against `vh`, and two height
  breakpoints progressively compress the layout: `max-height: 560px` drops the
  hint line, `max-height: 430px` shrinks everything further. `overflow-y: auto`
  is a safety valve only. Do not reintroduce fixed pixel margins here.
- **The panel entrance is direction-aware.** `.auth-panel[data-travel]`
  replays `panel-in` or `panel-in-reverse` so the panel arrives from the way you
  travelled between steps. Keyed on step so it re-runs.
- **The Google "G" mark IS on the Continue with Google button.** It is the one
  place colour appears on the site, and that is fine: it is a third-party brand
  mark, not our UI. The monochrome rule above applies to everything ReSolve
  draws.
- **The tinted near-black is allowed in one place.** `.auth-field input` uses
  `--color-card` so the field has a visible edge against pure black. That is
  affordance, not decoration — do not spread `--color-card` to page surfaces.

### Patterns to avoid

- **No `lucide-react`.** It was installed for icons, then every icon was
  removed as a templated default, so the dependency was uninstalled rather than
  left dangling. Re-add only when a real icon is needed.
- **No bento card grid.** A 1px gap over `--color-border` with
  `--color-background` cells gives hairline dividers rather than floating tiles.
  Zero radius, zero shadow, zero gradient, and only one cell carries large
  type. Labels are sentence case, never ALL-CAPS.
- **No templated defaults.** No eyebrow labels, no ALL-CAPS headings, no mono
  chrome labels, no middle-dot separators, no `→` appended to button text.

### Tailwind v4 specifics

- Config lives in CSS. **There is no `tailwind.config.js`. Do not create one.**
- The Vite plugin `@tailwindcss/vite` is registered in `vite.config.ts`.
- Custom utilities use the `@utility` directive (see `grid-backdrop`).

---

## 8. Architecture decisions and their reasons

Record *why*, so future changes do not silently undo them.

| Decision                                   | Why                                                                                                              |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| Supabase = Postgres + Auth                 | One service instead of a separate auth backend and a separate database. The catalogue, practice state and profiles all live there; the browser only signs in. |
| Service-role client server-side only       | The API is the only place that trusts itself; RLS still protects anything the browser touches directly.            |
| API prefix `/api/v1`                       | Versioning from day one.                                                |
| Auth as a FastAPI dependency               | `get_current_user` (401) and `get_optional_user` (nullable) are already wired in `app/api/deps.py`.               |
| Settings via `pydantic-settings`           | One typed source of truth from `.env`; `is_configured` lets the app boot without Supabase so the health check works on a fresh clone. |
| Tailwind v4                                | CSS-first config keeps design tokens next to the design.                                                        |
| ESLint 10 flat config                      | Matches the current plugin ecosystem.                                                                             |
| Dependencies pinned in `requirements.txt`  | `pip install -r requirements.txt` must just work on a teammate's machine. No build backend required.             |
| Judge0 called from the backend             | The browser never talks to a third party directly, so no RapidAPI key reaches the bundle.                        |
| Monaco lazy-loaded                         | Its ~3.3MB (843kB gzip) chunk only loads when an editor opens; the initial bundle is unaffected.                |
| Curated C++ completions, not clangd        | The only npm clangd is 75MB unpacked, needs `SharedArrayBuffer` (so COOP/COEP headers, which break the Google Fonts), and would not load in time on stage wifi. |
| The catalogue seeds from JSON              | The seed stays readable, diffable and easy to author; Postgres is the runtime source. `problems.py` is still the only module that knows where it lives, and `RESOLVE_CATALOGUE=json` keeps a checkout working with no credentials. |
| The memory curve, not a fixed ladder       | A ladder has one shape for every user, and its ceiling came from the problem's community tag — the two axes §2 says must stay separate. Stability learned from the user's own ratings adapts per card, retires on merit, and produces a number (predicted recall) the UI can show. |
| Ratings, not the problem tag, set the interval | The tag says how hard the problem is for the community; the rating says how hard the attempt was for you. Only the second is evidence about your memory. It also means a custom sheet can be added later without re-tagging anything. |
| Profiles share a random token              | A share link must work for someone without an account, but must not expose a user id that can be edited or enumerated. The token maps to one profile server-side, and the public response is a whitelist of counts. `is_public` can switch it off without deleting the profile. |

---

## 9. Known traps — do not step in these

These cost real time. They are already solved; keep them solved.

### Environment

1. **`npm.ps1` is blocked** by the Windows PowerShell execution policy on this
   machine. Use `npm.cmd run build`, not `npm run build`.
2. **Do not install `fastapi[standard]` or `uvicorn[standard]`.** On Python 3.15
   they pull PyYAML, which has no 3.15 wheel and requires MSVC build tools that
   are not installed. Plain `fastapi` + `uvicorn` is a deliberate choice.
3. **Start the backend with `run.py`, never `uvicorn app.main:app`.** `run.py`
   passes `loop="app.loop:selector_loop_factory"`. Uvicorn builds its loop from
   a *factory*, not the asyncio policy, and its Windows default is the Proactor
   loop, which crashes on accept with `OSError: [WinError 64] The specified
   network name is no longer available` and takes the whole server down. It
   happened repeatedly, always mid-request. `set_event_loop_policy` does not
   help — the policy setter is deprecated in 3.16 and uvicorn ignores it.
4. **Do not add `--reload`.** Reloader child processes get orphaned across
   restarts and fight over port 8000, serving a stale app. Kill every
   `python.exe` running the server before restarting.
5. **`strictPort: true` is on in Vite.** If :5173 is taken the dev server exits
   instead of drifting to :5174+. Kill the stale server rather than removing
   the flag — silent port drift wastes team time.
6. **Vite's watcher misses some file writes on Windows, and the dev server
   then serves stale modules.** This is not hypothetical: it is why a rating
   that the browser sent as `done` was refused by a server that only accepted
   `extreme`, and the click did nothing visible. If the app behaves as though
   your change was ignored, **restart the dev server** before believing the
   code is wrong:
   ```bash
   # Stop it, then start it again.
   npm run dev
   ```
   Check what is actually being served:
   ```bash
   curl http://localhost:5173/src/pages/learn-view.tsx | grep listSheets
   ```

### Judge0

The local compiler is preferred — `backend/app/core/judge.py` runs `g++` when
it exists, and only falls back to Judge0 when it does not. These traps apply to
the fallback path and to anyone who removes the local compiler.

6. **`status` is nested.** The API returns
   `"status": {"id": 3, "description": "Accepted"}`, NOT a bare int. Comparing
   it to `3` always fails, and every successful run looks like a failure. Read
   `data["status"]["id"]` first, exactly as `compiler.py` does.
7. **The plain path (`base64_encoded=false`) rejects some submissions** with
   HTTP 400 "some attributes for this submission cannot be converted to UTF-8",
   which is indistinguishable from a real failure. Use `base64_encoded=true` and
   decode the response fields yourself.
8. **A Judge0 API key does not mean unlimited use.** If a key exists it is a
   RapidAPI key and its free tier is roughly 50 requests/day. The default
   key-free `ce.judge0.com` is shared and can be slow. Either way, rate
   limiting is a demo-day risk — test the compiler on the actual setup machine,
   not just beforehand.
9. **C++ is `language_id=54`** (GCC 9.2.0). `wait=true` avoids a polling loop.

### The local judge

9a. **`asyncio.create_subprocess_exec` does not work on the selector loop.**
    `run.py` installs the selector loop factory (see trap 3), and that loop has
    no subprocess support: `loop.subprocess_exec` raises `NotImplementedError`
    and every run answers HTTP 500. `judge.py` therefore runs `g++` through
    `asyncio.to_thread` with `subprocess.run`. Do not "simplify" it back to an
    async subprocess.
9b. **`RESOLVE_CXX` overrides the compiler path.** The default is
    `C:\w64devkit\bin\g++.exe`. A machine without it still works — the judge
    falls back to Judge0.

### Monaco

10. **Import paths are `monaco-editor/editor/...`** — the package's `exports`
    map already prepends `esm/vs/`. Do **not** write
    `monaco-editor/esm/vs/...`.
11. **The contributions must be imported individually.**
    `monaco-editor/editor/editor.api` is the API only, so the suggest widget,
    folding, find and hover do not exist and `registerCompletionItemProvider`
    silently does nothing. `code-editor.tsx` imports them individually:
    suggestController, findController, `features/find/register`, folding,
    bracketMatching, hoverContribution, contextmenu, comment. Do **not** "fix"
    it by switching to `editor.main` — that pulls in all ~90 languages. This
    caused an hour of silent failure: completions simply never appeared.
12. **The `resolve` theme is monochrome by rule.**
    `monaco.editor.defineTheme` maps C++ tokens to greys and weights only —
    keywords bold white, comments grey. Never add hue to it.

### Frontend

13. **ESLint 10 + `eslint-plugin-react-hooks`**: the top-level
    `configs.recommended` is still eslintrc-format and crashes. The flat variant
    is `configs.flat['recommended-latest']`. Likewise `eslint-plugin-react-refresh`
    is ESM-only and needs a default import.
14. **TypeScript 6 with `erasableSyntaxOnly`** — no `enum`, no parameter
    properties. Use `as const` objects or union types instead.
15. **Tailwind v4 has no JS config file.** If you need a new token, add it to the
    `@theme` block in `src/index.css`.
16. **`baseUrl` is deprecated in TypeScript 6** and errors out. For the `@/` alias,
    declare only `paths` in `tsconfig.app.json` — it resolves relative to the
    tsconfig file. `vite.config.ts` must keep the matching `resolve.alias`.
17. **React 19 lint rules are strict.** `react-hooks/refs` forbids writing
    `ref.current` during render. Sync callback refs inside a `useEffect` with no
    dependency array, not in the component body.
18. **Never commit `.env`** or the Supabase service-role key.

### Backend

19. **The auth dependency must not require a working Supabase client to 401.**
    `supabase_provider` in `backend/app/api/deps.py` returns a *callable*, not a
    client, because FastAPI resolves all sub-dependencies before the endpoint
    body runs. Injecting a client directly made anonymous requests 503 when
    the backend `.env` was missing. A no-token request must always get 401.
20. **The catalogue is cached in process.** `problems.py` uses `lru_cache` for
    the DB summaries, sheets and per-slug problem. After re-seeding, restart the
    backend; there is no `--reload` for a reason (§9.4).
21. **Seeding needs the service-role key, and only that.** `seed.py` reads
    `backend/.env` if the variables are absent. Run it with
    `backend\.venv\Scripts\python.exe supabase\seed\seed.py` (plus `--dry-run`
    first). Never put the service-role key or a Supabase access token in a
    `VITE_` variable.
22. **`TRUST_CLIENT_USER_ID` must be false once the database is configured.**
    Otherwise an anonymous caller can send `X-Resolve-User: <someone else's
    uuid>` and read or rewrite that account's state. The browser sends a
    bearer token; the fallback is only for the offline file-store path.

---

## 10. Hard boundaries

- **There is no design reference any more.** The `figma/` folder was deleted at a
  human's instruction. From here on we design as we go. There is no longer an
  external authority for visual decisions — §7 and the tokens in
  `frontend/src/index.css` are the only reference. If a decision is unclear,
  ask; do not go looking for a design file.
- `resolve.html` in the repo root is the **original** Type Garden, kept only as
  reference. The ported, maintained engine is
  `frontend/src/lib/type-garden.ts`. If they disagree, the port wins.
- Do not rewrite the review/rating vocabulary in §2 without a human agreeing to it.
- **Do not add a colour beyond the two state colours in §7.** They are there
  because a verdict has to be findable. A third hue, or a hue on something
  decorative, breaks the one rule the palette has.
- Do not add a light theme.
- Do not swap the font.
- Do not add an AI dependency to the judging path. Test cases are
  hand-authored and their expected output is measured by running the reference.

---

## 11. Open questions — ask a human, do not guess

1. **Scheduling algorithm.** Resolved for now: the memory curve in §5 replaced
   the fixed ladder. It is a heuristic forgetting curve with a stability
   estimate, not a fitted model (SM-2/FSRS). The next question is whether to
   fit the growth factors from accumulated review logs, and that needs data
   first.
2. **Multi-language.** One language per problem, or several? Affects both schema
   and the editor. A single-language catalogue is much cheaper to author and to
   run.
3. **Where the catalogue lives.** Resolved: authored as JSON in `supabase/seed/`,
   seeded into Postgres, read from Postgres at runtime. The JSON fallback is for
   a checkout with no credentials and for the tests.
4. **Profile visibility.** A profile is created only when its owner asks for a
   share link, and the link is a random token. There is no UI yet to turn
   sharing off or rotate the token, though the schema supports `is_public`.
   Whether that control is needed is a privacy decision, not a UI one.

---

## 12. Versions and pushing

**Push only at a version boundary.** A version is cut when a **major section
is done** — the scheduler, the catalogue, the compiler, the problem screen.
Everything else stays local, no matter how finished it looks.

Between versions, commit locally if you like. Do not push. A pushed commit
that is not a version is a commit somebody has to unpick later.

### What a version looks like

Each version is **one commit on `main` with no parents**, and a tag on it.

```bash
git checkout --orphan release
git add -A
git commit -m "ReSolve v1: <what the section delivered>"
git branch -D main
git branch -M release main
git push origin main --force
git tag -a v1 -m "ReSolve v1"
git push origin v1
```

The tags are the history. `v0` still points at the version-0 tree, `v1` at
version 1, and `main` always holds exactly the current version.

`v0` is the starting point: landing, auth, Learn, the problem screen, the
compiler, and the 50-problem catalogue.

---

## 13. Definition of done

Before you call any task complete:

- [ ] `cd frontend && npm.cmd run lint` — clean
- [ ] `cd frontend && npm.cmd run build` — succeeds
- [ ] `cd backend && .\.venv\Scripts\python.exe -m ruff check .` — clean
- [ ] `cd backend && .\.venv\Scripts\python.exe -m pytest -q` — passes
- [ ] If you touched the catalogue: `scripts\check_examples.py` and
      `scripts\verify.py` both pass
- [ ] If you touched the schema or seed: `supabase\seed\seed.py --dry-run`
      reports the right counts, then reseed and restart the backend
- [ ] No hardcoded hex colours outside `src/index.css` or `PALETTES` in `src/lib/type-garden.ts`
- [ ] No dead code: a file nothing imports, or a CSS class nothing references,
      is a deletion
- [ ] `AGENTS.md` updated if you changed how something works

---

## 14. Working agreement for AI agents

- **Verify, do not assume.** Read the file. Check the installed version. The
  version numbers in §4 were observed, not guessed — keep them that way.
- **Do not push unless a version is being cut.** See §12. Commit locally if
  the work is worth keeping; pushing is a separate decision.
- **When you change something structural, update this file in the same commit.**
  A stale `AGENTS.md` is worse than none.
- **Prefer the boring, verified path.** This is a one-week hackathon. A working
  demo beats an elegant architecture.
- **Say what you did not do.** If part of a task was skipped, state it plainly
  rather than implying completion.
