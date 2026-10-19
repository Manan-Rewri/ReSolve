"""Measure the expected output for every test case.

The expected output of a case is whatever the problem's own reference solution
prints for it. That makes the stored answer a fact rather than a prediction,
and it means a broken reference is caught rather than baked in.

Run this after editing a problem's cases or its reference solution:

    .\\.venv\\Scripts\\python.exe scripts\\measure.py
    .\\.venv\\Scripts\\python.exe scripts\\measure.py two-sum   # just one
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import DATA_FILE, load, program_for, run, save, split_outputs


def main() -> None:
    only = sys.argv[1:] or None
    problems = load()

    changed = 0
    for problem in problems:
        if only and problem["slug"] not in only:
            continue

        cases = [c["args"] for c in problem["test_cases"]]
        status_id, stdout, stderr = run(program_for(problem, cases))

        if status_id != 3:
            print(f"{problem['slug']}: reference failed ({status_id})")
            print("  " + (stderr or "").replace("\n", "\n  ")[:800])
            continue

        outputs = split_outputs(stdout)
        if len(outputs) != len(cases):
            print(
                f"{problem['slug']}: {len(outputs)} outputs for {len(cases)} cases. "
                "One of the cases probably crashed the program."
            )
            continue

        for case, output in zip(problem["test_cases"], outputs, strict=True):
            if case.get("expected") != output:
                changed += 1
                case["expected"] = output

        print(f"{problem['slug']}: {len(cases)} cases measured")

    save(problems)
    print(f"\n{changed} expected output(s) changed. {DATA_FILE} written.")


if __name__ == "__main__":
    main()
