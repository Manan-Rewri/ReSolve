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
   - `again` — could not solve it
   - `hard` — solved, but slowly / with heavy hints / shaky
   - `easy` — solved cleanly and confidently
   - `done` — already solved before / recognised immediately
5. That rating drives a **spaced repetition schedule** for that
   (user, problem) pair.
6. The problem is added to the user's **practice sheet** — the deck that keeps
   resurfacing it.

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
| **Card state**       | The per-(user, problem) SRS record: due date, interval, ease factor, reps, lapses. |
| **Due queue**        | Cards whose `due_at <= now`, ordered for a practice session.                |
| **Rating**           | `again` / `hard` / `easy` / `done` — the post-attempt self-assessment.        |
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
| @supabase/supabase-js | 2.118.0 | Browser client (anon key only). ~200kB, loads at startup |
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

- **Supabase** is both the database *and* the auth provider. Postgres + GoTrue.
- The browser talks to Supabase directly for auth (login/signup/session refresh).
- The FastAPI backend talks to Supabase with the service-role key.
- **Judge0** runs the C++. The public community instance `ce.judge0.com` needs
  no API key.
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

Neither `.env` file is committed. Copy the templates:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

`frontend/.env` needs the Supabase URL and anon key, or the auth screens
render an explanation instead of a white screen:

```ini
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key>
```

The anon key is designed to be public — it ships in the browser bundle and is
gated by row-level security. The **service-role key is not** and must never go
in `frontend/.env` or any `VITE_` variable.

`backend/.env` is optional. **The compiler works with no keys at all**, because
`ce.judge0.com` is key-free.

---

## 5. Current features

What exists and works today.

| Surface | State | Where |
| --- | --- | --- |
| Landing page (`/`) | Built | `src/pages/landing-page.tsx` |
| Register | Built, live against Supabase | `src/pages/register-page.tsx` |
| Login | Built, live against Supabase | `src/pages/login-page.tsx` |
| 404 | Built | `src/pages/not-found-page.tsx` |
| Home | **Default view, no content yet** | `src/pages/home-page.tsx` |
| Learn | Built | `src/pages/learn-view.tsx` |
| Problem screen | Built | `src/pages/problem-view.tsx` |
| Compiler | Built | `src/pages/compiler-view.tsx` |
| Practice | **Not built** — navbar entry only | — |
| Settings | **Not built** — navbar entry only | — |

### Where a signed-in user lands

**Home.** A signed-in user opening the site is sent from `/` to `/home`, and
`/home` opens on the Home view. Home is where the analytics are going; it has
no content yet. Learn and the Compiler are one click away in the drawer.

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

Every password field has a reveal button — an eye drawn inline in
`auth-field.tsx`, not from an icon library — and a placeholder. A field with
something to fix gets a red border, and the message under it is red too.

Route guards in `src/components/guards.tsx`: `RedirectIfAuthed` sends signed-in
users from `/`, `/register`, `/login` to `/home`; `RequireAuth` bounces anyone
without a session from `/home` back to `/`. A missing `.env` renders an
explanation rather than a white screen.

### Learn

A search bar that filters the catalogue as you type, over the title, the
difficulty and the tags. The list sits below it.

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
              ├── /api/*  ──proxied──> FastAPI :8000 ──> Judge0
              │                            │
              │                            └──> backend/data/problems.json
              │
              └── everything else ──> static assets

browser ──> Supabase  (auth only, directly, never through the API)
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

Both write endpoints are unauthenticated. Judge0 gives us no per-user quota
either way, so gating them buys nothing but friction. **Re-add
`Depends(get_current_user)` before exposing this publicly** — an open proxy to
a code runner is a known abuse vector (cryptomining, spam).

### The catalogue

`backend/data/problems.json` holds 50 problems. Each one carries:

- a statement, 2-3 worked examples, and constraints
- a C++ signature and its parameter list
- a reference solution
- the C++ that goes before and after the user's function
- 20-30 test cases, each with its input and its expected output

`app/core/problems.py` is the only module that knows where the data lives. It
is a stand-in for the database: when the Postgres tables exist, that one file
changes and nothing above it does.

### The function-only editor

Each problem stores the C++ that goes around the user's function:

```
prefix + the user's function + suffix
```

The **prefix** is the includes, the namespace, and the printers. The **suffix**
is a `main` that runs every stored case and prints the result after a marker,
so one run carrying every case can be split back apart.

`POST /api/v1/judge` splices the two, runs the result on Judge0, splits the
output by the marker, and compares each piece against the stored expected
output.

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
├── frontend/          <- Vite + React + TS + Tailwind
│   ├── eslint.config.js
│   ├── vite.config.ts <- Tailwind plugin + `@` alias + /api proxy + strictPort
│   ├── index.html     <- Google Fonts live here
│   └── src/
│       ├── index.css  <- ALL design tokens (@theme block) + every page's styles
│       ├── lib/       <- supabase, auth, navigation, compiler client, problems
│       ├── components/<- app shell, guards, code editor, markdown, garden
│       └── pages/     <- one file per surface
└── backend/           <- FastAPI
    ├── run.py         <- START THE SERVER WITH THIS. See §9.
    ├── .env.example
    ├── pyproject.toml <- ruff + pytest config only
    ├── requirements.txt <- pinned via pip freeze
    ├── data/
    │   └── problems.json  <- the catalogue
    ├── scripts/       <- catalogue tooling, see scripts/README.md
    ├── app/
    │   ├── main.py
    │   ├── loop.py    <- the Windows event-loop workaround
    │   ├── core/      <- config, supabase, problems
    │   ├── api/v1/    <- health, compiler, problems
    │   └── schemas/   <- Pydantic I/O models
    └── tests/
```

### Conventions

- Import paths in React use the `@/` alias → `frontend/src`.
- Backend Python packages are `app.*`.
- Both stacks have a `lint`/`check` script. Run them before you claim done.
- Pages are **views** under `/home`, not routes. Switching sections does not
  change the URL. `src/lib/navigation.ts` is the list.
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
| Supabase = Postgres + Auth                 | One service instead of a separate auth backend. Saves a full week of a hackathon build.                            |
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
| The catalogue is a JSON file                | A stand-in for the database. One module reads it, so moving to Postgres is a one-file change.                     |

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

### Judge0

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

1. **Scheduling algorithm.** SM-2 (classic Anki, simple, well understood) or
   FSRS (modern, better, more tuning)? This is the biggest open decision and it
   blocks the card-state schema.
2. **Multi-language.** One language per problem, or several? Affects both schema
   and the editor. A single-language catalogue is much cheaper to author and to
   run.
3. **Where the catalogue lives.** The JSON file is a stand-in. Postgres needs
   the tables written, and the SRS needs them before anything else is worth
   building.

---

## 12. Definition of done

Before you call any task complete:

- [ ] `cd frontend && npm.cmd run lint` — clean
- [ ] `cd frontend && npm.cmd run build` — succeeds
- [ ] `cd backend && .\.venv\Scripts\python.exe -m ruff check .` — clean
- [ ] `cd backend && .\.venv\Scripts\python.exe -m pytest -q` — passes
- [ ] If you touched the catalogue: `scripts\check_examples.py` and
      `scripts\verify.py` both pass
- [ ] No hardcoded hex colours outside `src/index.css` or `PALETTES` in `src/lib/type-garden.ts`
- [ ] No dead code: a file nothing imports, or a CSS class nothing references,
      is a deletion
- [ ] `AGENTS.md` updated if you changed how something works

---

## 13. Working agreement for AI agents

- **Verify, do not assume.** Read the file. Check the installed version. The
  version numbers in §4 were observed, not guessed — keep them that way.
- **When you change something structural, update this file in the same commit.**
  A stale `AGENTS.md` is worse than none.
- **Prefer the boring, verified path.** This is a one-week hackathon. A working
  demo beats an elegant architecture.
- **Say what you did not do.** If part of a task was skipped, state it plainly
  rather than implying completion.
