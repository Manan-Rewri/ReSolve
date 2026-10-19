"""Re-run the reference solutions and compare against the stored answers.

`measure.py` writes the expected output; this checks that what is stored
still matches what the reference produces. A mismatch means the catalogue and
the reference have drifted apart.

    .\\.venv\\Scripts\\python.exe scripts\\verify.py
    .\\.venv\\Scripts\\python.exe scripts\\verify.py two-sum   # just one
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import load, program_for, run, split_outputs


def main() -> None:
    only = sys.argv[1:] or None
    problems = load()

    checked = 0
    failures = []

    for problem in problems:
        if only and problem["slug"] not in only:
            continue

        cases = [c["args"] for c in problem["test_cases"]]
        status_id, stdout, stderr = run(program_for(problem, cases))
        if status_id != 3:
            failures.append((problem["slug"], f"reference failed: {stderr[:200]}"))
            continue

        outputs = split_outputs(stdout)
        if len(outputs) != len(cases):
            failures.append((problem["slug"], f"{len(outputs)} outputs for {len(cases)} cases"))
            continue

        for case, got in zip(problem["test_cases"], outputs, strict=True):
            checked += 1
            if got.strip() != case["expected"].strip():
                failures.append(
                    (problem["slug"], f"expected {case['expected']!r}, reference says {got!r}")
                )

    print(f"{checked} stored answers re-verified against the reference solutions")
    if failures:
        print(f"\n{len(failures)} MISMATCH:")
        for slug, why in failures:
            print(f"  {slug}: {why}")
        sys.exit(1)
    print("no mismatches")


if __name__ == "__main__":
    main()
