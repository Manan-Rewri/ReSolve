"""Load the catalogue into Postgres.

The JSON in this folder is the source of truth for the catalogue. This script
is the transfer: it reads the JSON and writes the rows the schema in
`../migrations/0001_catalogue.sql` expects.

    .\\.venv\\Scripts\\python.exe supabase\\seed\\seed.py --dry-run
    .\\.venv\\Scripts\\python.exe supabase\\seed\\seed.py

It needs the service-role key, which is the one credential that must never
reach a `VITE_` variable or the browser bundle:

    SUPABASE_URL=https://<project-ref>.supabase.co
    SUPABASE_SERVICE_ROLE_KEY=<service role key>

`--dry-run` reports what would be written and touches nothing.

The load is idempotent: problems are matched on `slug` and updated in place,
test cases are replaced wholesale for each problem, and sheets are matched on
`id`. Running it twice does not duplicate anything.
"""

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBLEMS = HERE / "problems.json"
SHEETS = HERE / "sheets.json"
BACKEND_ENV = HERE.parents[1] / "backend" / ".env"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_problems() -> list[dict]:
    data = load_json(PROBLEMS)
    if not isinstance(data, list):
        raise SystemExit(f"{PROBLEMS} should hold a list of problems.")
    return data


def load_sheets() -> list[dict]:
    data = load_json(SHEETS)
    sheets = data.get("sheets") if isinstance(data, dict) else None
    if not isinstance(sheets, list):
        raise SystemExit(f"{SHEETS} should hold a list of sheets under 'sheets'.")
    return sheets


def load_backend_env() -> None:
    """Read backend/.env for the two credentials, without printing them."""
    if not BACKEND_ENV.exists():
        return
    for line in BACKEND_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if value and not os.environ.get(key):
            os.environ[key] = value


def env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"{name} is not set. It belongs in backend/.env or your shell.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report only. Write nothing.")
    args = parser.parse_args()

    problems = load_problems()
    sheets = load_sheets()
    total_cases = sum(len(p["test_cases"]) for p in problems)

    print(f"{len(problems)} problems, {total_cases} test cases in {PROBLEMS}")
    print(f"{len(sheets)} sheets in {SHEETS}")
    for problem in problems:
        print(
            f"  {problem['slug']:45} {problem['difficulty']:6} "
            f"{len(problem['test_cases']):>3} cases"
        )
    for sheet in sheets:
        print(f"  {sheet['id']:45} {len(sheet['problems']):>3} problems")

    if args.dry_run:
        print("\nDry run. Nothing was written.")
        return

    try:
        import httpx
    except ImportError:
        raise SystemExit("httpx is not installed. Run this with backend\\.venv\\Scripts\\python.exe.")

    load_backend_env()
    url = env("SUPABASE_URL").rstrip("/")
    key = env("SUPABASE_SERVICE_ROLE_KEY")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }

    with httpx.Client(timeout=60.0) as client:
        for problem in problems:
            row = {
                "slug": problem["slug"],
                "title": problem["title"],
                "difficulty": problem["difficulty"],
                "tags": problem["tags"],
                "statement": problem["statement"],
                "examples": problem["examples"],
                "constraints": problem["constraints"],
                "signature": problem["signature"],
                "params": problem["params"],
                "reference_solution": problem["reference_solution"],
                "prefix": problem["prefix"],
                "suffix": problem["suffix"],
                "editor_start": problem["editor_start"],
                "print_param": problem.get("print_param"),
            }

            # `slug` is the conflict target, so re-running updates in place.
            response = client.post(
                f"{url}/rest/v1/problems?on_conflict=slug",
                headers=headers,
                json=row,
            )
            response.raise_for_status()
            saved = response.json()[0]

            # Test cases are replaced wholesale: the positions are meaningful.
            client.delete(
                f"{url}/rest/v1/test_cases?problem_id=eq.{saved['id']}",
                headers=headers,
            ).raise_for_status()

            if problem["test_cases"]:
                cases = [
                    {
                        "problem_id": saved["id"],
                        "position": index,
                        "args": case["args"],
                        "expected": case["expected"],
                        "note": case.get("note", ""),
                    }
                    for index, case in enumerate(problem["test_cases"])
                ]
                client.post(
                    f"{url}/rest/v1/test_cases",
                    headers=headers,
                    json=cases,
                ).raise_for_status()

            print(f"  wrote {problem['slug']}")

        for position, sheet in enumerate(sheets):
            client.post(
                f"{url}/rest/v1/sheets?on_conflict=id",
                headers=headers,
                json={
                    "id": sheet["id"],
                    "name": sheet["name"],
                    "blurb": sheet.get("blurb", ""),
                    "tier": sheet.get("tier", ""),
                    "position": position,
                },
            ).raise_for_status()

            # The positions are the curriculum, so replace the whole list.
            client.delete(
                f"{url}/rest/v1/sheet_problems?sheet_id=eq.{sheet['id']}",
                headers=headers,
            ).raise_for_status()

            rows = [
                {
                    "sheet_id": sheet["id"],
                    "problem_slug": slug,
                    "position": index,
                }
                for index, slug in enumerate(sheet["problems"])
            ]
            if rows:
                client.post(
                    f"{url}/rest/v1/sheet_problems",
                    headers=headers,
                    json=rows,
                ).raise_for_status()

            print(f"  wrote sheet {sheet['id']} ({len(rows)} problems)")

    print(f"\nDone. {len(problems)} problems and {len(sheets)} sheets loaded.")


if __name__ == "__main__":
    sys.exit(main())
