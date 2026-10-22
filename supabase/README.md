# The Supabase folder

Everything that belongs in Postgres: the schema, the catalogue, and the script
that loads it. At runtime the API reads from the database; the JSON is the seed,
not a second source.

```text
supabase/
├── README.md                  <- this file
├── migrations/
│   └── 0001_catalogue.sql     <- catalogue, practice state, profiles, RPCs
└── seed/
    ├── problems.json          <- 119 problems and their test cases
    ├── sheets.json            <- the sheets, and the order
    └── seed.py                <- the transfer
```

## Tables

| Table | Holds |
| --- | --- |
| `problems` | One row per problem: statement, examples, constraints, signature, reference solution, prefix/suffix. |
| `test_cases` | Every case, in order. `expected` was measured by running the reference. |
| `sheets` | A course: a named group of problems. Currently Git Gud (119) and LeetCode 75. |
| `sheet_problems` | Which problems are in a sheet, and in what order. |
| `profiles` | One row per user who has asked for a share link: username, random token, `is_public`. |
| `card_state` | The SRS card: stability, due date, reps, lapses, last rating. |
| `solved_problems` | Problems the user has got fully right. Drives the tick. |
| `review_logs` | Every graded review. The dashboard reads it; the scheduler does not. |

`problems.difficulty` is the community tag. `review_logs.rating` is how the
attempt felt *for that user*. They are different axes and stay apart.

Two `security definer` functions do the multi-row writes atomically:

- `record_review(...)` upserts the card and inserts the review log together, so
  a card never exists without its log or the other way round.
- `import_practice_state(...)` moves a browser's old localStorage bucket in
  once, and refuses if the user already has rows.

Both are executable only by `service_role`; the browser has no execute grant.

## Applying the schema

Paste `migrations/0001_catalogue.sql` into the Supabase SQL editor, or run it
through the Management API with a personal access token. The file is
idempotent (`create table if not exists`, `drop policy if exists`), so running
it twice is safe. It creates the tables, indexes, RLS policies, grants and both
functions.

Row level security is on everywhere. The catalogue is readable by anyone;
everything that belongs to a user is readable only by that user. The API uses
the service-role key, so those policies are the second line of defence.

## Seeding

`seed.py` reads `backend/.env` if the environment does not already have the two
variables it needs:

```ini
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service role key>
```

Then:

```bash
# See what would be written. Touches nothing.
.\backend\.venv\Scripts\python.exe supabase\seed\seed.py --dry-run

# Actually load it.
.\backend\.venv\Scripts\python.exe supabase\seed\seed.py
```

The service-role key is the one credential that must never reach a `VITE_`
variable or the browser bundle. The anon key is fine — it is designed to be
public, and row-level security is what protects the data.

The load is idempotent: problems are matched on `slug` and updated in place,
their test cases are replaced wholesale, sheets are matched on `id`, and their
problem lists are replaced. Running it twice does not duplicate anything.

**Restart the backend after re-seeding.** `backend/app/core/problems.py` caches
the catalogue in process; there is no `--reload`.

## The shape of a problem

```json
{
  "slug": "two-sum",
  "title": "Two Sum",
  "difficulty": "Easy",
  "tags": ["array", "hash map"],
  "statement": "Given an array of integers `nums` ...",
  "examples": [{ "input": "nums = [2, 7, 11, 15], target = 9", "output": "[0, 1]" }],
  "constraints": ["2 <= nums.length <= 10^4"],
  "signature": "vector<int> twoSum(vector<int>& nums, int target)",
  "params": [["vector<int>", "nums"], ["int", "target"]],
  "reference_solution": "vector<int> twoSum(vector<int>& nums, int target){...}",
  "prefix": "#include <bits/stdc++.h>\nusing namespace std;\n...",
  "suffix": "\nint main() {\n...\n}\n",
  "editor_start": "vector<int> twoSum(vector<int>& nums, int target) {\n    \n}",
  "print_param": null,
  "test_cases": [{ "args": ["{2,7,11,15}", "9"], "expected": "[0,1]", "note": "..." }]
}
```

Two things to keep in mind:

- **`args` is a list, not a joined string.** An argument can contain a comma —
  a `vector<string>` of six words has five — so splitting a joined string is
  lossy. It silently corrupted every `vector<string>` case when it was one.
- **The expected output is measured, never predicted.** Each one was produced
  by compiling and running the problem's own reference solution on Judge0.

## After the transfer

`backend/app/core/problems.py` is the only module that knows where the
catalogue lives. It queries `problems`, `test_cases`, `sheets` and
`sheet_problems` when Supabase is configured, and falls back to these JSON files
when it is not (`RESOLVE_CATALOGUE=json` forces the fallback; the test suite
uses it).

`backend/app/core/store.py` is the only module that knows where the practice
state lives. It writes `card_state`, `solved_problems` and `review_logs` with
the service-role key, and keeps the old JSON file store as the offline/test
fallback (`PRACTICE_STORE=file`).
