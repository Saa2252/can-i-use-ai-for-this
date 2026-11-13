"""The reload guard in `app/main.py`.

A hosted Streamlit re-executes the entry script and the page scripts from
source on every run but keeps imported modules in `sys.modules` for the life
of the process. A deploy therefore runs new page scripts against the previous
commit's modules. Three times running, that took this app down: an
`ImportError` for a name the cached module did not have yet.

These tests drive the real functions out of the real file, so they cannot
pass against a copy of the logic that the entry script does not use. The
destructive one runs in a subprocess, because purging `sys.modules` under a
test session would pull the engine out from under every other test.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAIN = PROJECT_ROOT / "app" / "main.py"

#: The guard has to run before anything of ours is imported, so it lives
#: above this line in the entry script. Everything below it is the app.
BOUNDARY = "BUILD = reload_if_source_changed()"


def load_guard() -> dict:
    """Execute the entry script's guard, and nothing else in it."""
    source = MAIN.read_text(encoding="utf-8")
    assert BOUNDARY in source, (
        "the entry script no longer calls reload_if_source_changed() where "
        "this test expects it; the guard must run before any of our imports"
    )
    prefix = source.split(BOUNDARY)[0]
    namespace: dict = {"__file__": str(MAIN), "__name__": "cu_guard_under_test"}
    exec(compile(prefix, str(MAIN), "exec"), namespace)  # noqa: S102 - our own file
    return namespace


def make_tree(root: Path, value: int) -> None:
    """A miniature of the real layout: the folders the guard watches."""
    for folder in ("app", "engine", "policy"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / "engine" / "__init__.py").write_text("", encoding="utf-8")
    (root / "engine" / "thing.py").write_text(f"VALUE = {value}\n", encoding="utf-8")
    (root / "app" / "__init__.py").write_text("", encoding="utf-8")


# --------------------------------------------------------------------------
# The fingerprint
# --------------------------------------------------------------------------


def test_the_guard_watches_everything_a_process_can_cache():
    """Modules go stale, and so do the rulesets and policy files that
    `lru_cache` holds inside them."""
    guard = load_guard()
    watched = set(guard["SOURCES"])
    assert ("app", "*.py") in watched
    assert ("engine", "*.py") in watched
    assert ("engine", "*.yaml") in watched, "a rules change must force a reload"
    assert ("policy", "*.md") in watched, "a policy change must force a reload"


def test_the_fingerprint_moves_when_a_watched_file_does(tmp_path: Path):
    guard = load_guard()
    make_tree(tmp_path, 1)
    before = guard["source_fingerprint"](tmp_path)

    target = tmp_path / "engine" / "thing.py"
    target.write_text("VALUE = 2\n", encoding="utf-8")
    import os

    os.utime(target, (0, float(before) + 10))

    assert guard["source_fingerprint"](tmp_path) != before


def test_the_fingerprint_is_steady_when_nothing_changes(tmp_path: Path):
    """A rerun must not look like a deploy, or every click reloads the app."""
    guard = load_guard()
    make_tree(tmp_path, 1)
    assert guard["source_fingerprint"](tmp_path) == guard["source_fingerprint"](tmp_path)


def test_only_our_own_packages_are_ever_dropped():
    guard = load_guard()
    assert set(guard["OURS"]) == {"app", "engine"}


def test_the_real_project_has_a_fingerprint():
    guard = load_guard()
    assert float(guard["source_fingerprint"]()) > 0


# --------------------------------------------------------------------------
# The reload itself, in a process of its own
# --------------------------------------------------------------------------

SCRIPT = textwrap.dedent(
    """
    import sys
    from pathlib import Path

    project, sandbox = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(project))
    sys.path.insert(0, str(sandbox))

    source = (project / "app" / "main.py").read_text()
    prefix = source.split("BUILD = reload_if_source_changed()")[0]
    ns = {"__file__": str(project / "app" / "main.py"), "__name__": "guard"}
    exec(compile(prefix, "main.py", "exec"), ns)

    import json
    import engine.thing

    assert engine.thing.VALUE == 1, engine.thing.VALUE

    # First sight records the build and drops nothing: a process that has
    # just started already holds the current files.
    ns["reload_if_source_changed"](sandbox)
    assert "engine.thing" in sys.modules, "first sight must not purge"
    first = sys.modules["engine"].__source_fingerprint__

    # Nothing changed: a rerun must not reload the world.
    ns["reload_if_source_changed"](sandbox)
    assert "engine.thing" in sys.modules, "an unchanged build must not purge"

    # Now a deploy lands under the running process.
    target = sandbox / "engine" / "thing.py"
    target.write_text("VALUE = 2\\n")
    import os
    os.utime(target, (0, float(first) + 10))

    ns["reload_if_source_changed"](sandbox)
    assert "engine.thing" not in sys.modules, "a changed build must purge our modules"
    assert "json" in sys.modules, "nothing outside our packages may be touched"
    assert sys.modules["engine"].__source_fingerprint__ != first

    import engine.thing as healed
    assert healed.VALUE == 2, "the reload must pick up the new source"

    print("OK")
    """
)


@pytest.mark.parametrize("run", [1])
def test_a_deploy_under_a_running_process_heals_itself(tmp_path: Path, run: int):
    """The whole point, end to end: old module imported, files replaced, the
    guard runs, and the next import sees the new code."""
    sandbox = tmp_path / "sandbox"
    make_tree(sandbox, 1)
    script = tmp_path / "drive.py"
    script.write_text(SCRIPT, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-I", str(script), str(PROJECT_ROOT), str(sandbox)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


# --------------------------------------------------------------------------
# The session that straddles a deploy
# --------------------------------------------------------------------------


def test_the_entry_script_clears_a_session_built_by_the_old_modules():
    """Enum members from a dropped module are a different class from the new
    one, and the matcher compares with `type(a) is type(value)`. A session
    carrying them would not fail: it would quietly match no rule."""
    source = MAIN.read_text(encoding="utf-8")
    tail = source.split(BOUNDARY)[1]
    assert 'st.session_state.get("_cu_build") != BUILD' in tail
    assert "st.session_state.clear()" in tail
    assert tail.index("st.session_state.clear()") < tail.index("st.navigation")
