"""Test-session setup.

The entry script drops every `app.*` and `engine.*` module from
`sys.modules` when the files behind them have changed, so a deploy that
lands under a running process heals itself instead of serving a stale
import until someone reboots it. That is right for a server and wrong
here: a test session imports those modules at collection and holds class
objects from them, and an `AppTest` run that purged them mid-session would
leave half the suite comparing enum members across two copies of the same
class — which does not raise, it quietly stops matching.

So the purge is switched off for the session. The mechanism itself is
covered by tests/test_reload_guard.py, which drives the real functions out
of the real file and runs the destructive case in a subprocess.
"""

from __future__ import annotations

import os

os.environ["CU_RELOAD_GUARD"] = "off"
