# Catalogue scripts

The problem catalogue is `backend/data/problems.json`. These scripts are how
you know it is right.

## The rule

**The expected output of a test case is whatever the reference solution prints
for it.** It is measured, never predicted, and never typed by hand. A broken
reference is caught by the checks below rather than baked into the catalogue.

## The workflow, when you add or change a problem

```bash
cd backend

# 1. Edit data/problems.json: the statement, the examples, the constraints,
#    the signature, the reference solution, and the test case INPUTS.
#    Leave "expected" alone; the next step fills it in.

# 2. Measure the expected output from the reference solution.
.\.venv\Scripts\python.exe scripts\measure.py

# 3. The reference must reproduce the worked example in the statement.
.\.venv\Scripts\python.exe scripts\check_examples.py

# 4. The stored answers must match a fresh run.
.\.venv\Scripts\python.exe scripts\verify.py
```

Step 3 is the one that catches real mistakes. Everything else agrees with
itself by construction; step 3 compares the reference against something a
human wrote.

`measure.py` and `verify.py` take a slug to work on one problem:

```bash
.\.venv\Scripts\python.exe scripts\measure.py two-sum
```

## What a problem looks like

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
  "print_param": null,
  "prefix": "#include <bits/stdc++.h>\nusing namespace std;\n...",
  "suffix": "\nint main() {\n...\n}\n",
  "editor_start": "vector<int> twoSum(vector<int>& nums, int target) {\n    \n}",
  "test_cases": [{ "args": ["{2,7,11,15}", "9"], "expected": "[0,1]" }]
}
```

- **`args`** is a list, one entry per parameter. It is a list rather than a
  joined string because an argument can contain a comma: a `vector<string>` of
  six words has five. Splitting a joined string is lossy and it silently
  corrupted the `group-anagrams` and `word-break` cases.

- **`prefix` and `suffix`** are the C++ that goes before and after the user's
  function. The editor holds only the function, and the server splices it
  between the two. `measure.py` rebuilds the suffix when it measures.
- **`print_param`** names the parameter that holds the answer when the function
  returns nothing. `void moveZeroes(vector<int>& nums)` has no return value,
  so the harness prints `nums` after the call. Leave it `null` otherwise.
- **`params`** is the parameter list as `[type, name]` pairs. The harness
  declares each one from the matching entry in a test case's `input`.
- **`editor_start`** is what the editor is seeded with: the signature and an
  empty body.

## Rules for the data

- **A test case that proves nothing is not a test case.** An empty expected
  output is an automatic pass for any submission. A case whose arity does not
  match the signature cannot be declared. A duplicate proves the same thing
  twice. All three are dropped.
- **The printers decide what an answer looks like.** A `bool` prints as
  `true`/`false`, a `string` prints with its quotes, a `double` keeps a
  decimal point (`2.0`, not `2`). A case that disagrees with its own
  statement's examples is worse than useless.
- **A reference must be deterministic.** One that returns groups or elements in
  hash-map order gives a different answer every run, and the stored expected
  output would be wrong. Sort the output.
- **The signature comes from our data.** Never let anything invent the
  function.

## These scripts need the network

They compile and run on Judge0's public community instance, `ce.judge0.com`,
which needs no API key. It is shared and can be slow. A full run over 50
problems takes a few minutes.
