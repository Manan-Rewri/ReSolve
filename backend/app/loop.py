"""The event loop the API server runs on.

uvicorn picks the loop for us in `uvicorn/loops/asyncio.py`:

    if sys.platform == "win32" and not use_subprocess:
        return asyncio.ProactorEventLoop

On Windows that Proactor loop can fail an accept with
`OSError: [WinError 64] The specified network name is no longer available`,
which takes the whole server down. It did so repeatedly here, always during a
long request. `set_event_loop_policy` does not help: uvicorn 0.36+ builds the
loop from a factory rather than the policy, and the policy setter is deprecated
in Python 3.16 anyway.

So `run.py` passes this factory to `uvicorn.run(loop=...)`, which it imports by
path. Nothing here needs subprocess support — every outbound call is plain HTTP —
so the Selector loop is a straight swap.
"""

import asyncio
import sys


def selector_loop_factory() -> asyncio.AbstractEventLoop:
    """Zero-argument loop factory, which is the shape uvicorn expects here."""
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop()
    return asyncio.new_event_loop()