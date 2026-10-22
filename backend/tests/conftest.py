"""The tests use the file store and the JSON catalogue.

Neither touches the network: the suite has to pass on a machine with no
Supabase credentials, and it has to be fast. The environment is set before the
app is imported, because the settings are built at import time.
"""

import os
import tempfile
from pathlib import Path

os.environ["STATE_FILE"] = str(
    Path(tempfile.mkdtemp(prefix="resolve-tests-")) / "state.json"
)
os.environ["PRACTICE_STORE"] = "file"
os.environ["RESOLVE_CATALOGUE"] = "json"
os.environ["TRUST_CLIENT_USER_ID"] = "true"
