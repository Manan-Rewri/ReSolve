"""Start the API server.

Run the server with this, not with `uvicorn app.main:app` directly.

    .\\.venv\\Scripts\\python.exe run.py

Two things are set up here that cannot live in `app/main.py`:

- The event loop. Uvicorn builds it from a factory, not the policy, and its
  Windows default can crash on accept. See `app/loop.py`.
- No `--reload`. Reloader children get orphaned across restarts and fight over
  the port. See AGENTS.md.
"""

import uvicorn

PORT = 8000


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=PORT,
        loop="app.loop:selector_loop_factory",
        log_level="info",
    )


if __name__ == "__main__":
    main()