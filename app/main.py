"""Entry point: `streamlit run app/main.py`.

Streamlit puts this file's directory on `sys.path`, not the project root, so
the root is added here before anything imports `engine` or `app`.

The page scripts live in `views/`, and the name matters. If a directory
called `pages/` sits beside this file, Streamlit reads it as a legacy v1
multipage app and runs the matching page script **in lieu of this one**
(`PagesManager.uses_pages_directory` -> `_mpa_v1`). The bootstrap above
never runs, so the page's own `import app...` fails.

That is invisible while the app is warm, because the first visitor to the
root runs this file as the v1 home page, which calls `st.navigation` and
flips the process to v2 for good. It only bites a visitor who opens a deep
link as the first request after the app wakes: they get a traceback, and so
does everyone after them until someone loads the root. Hence `views/`.

This file also carries the reload guard below, because it is the only file
that is certainly current: a hosted Streamlit re-executes the entry script
and the page scripts from source on every run, but keeps imported modules
in `sys.modules` for the life of the process.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

#: Everything whose contents a running process can hold stale: our own
#: modules, the rulesets they cache with `lru_cache`, and the policy files
#: the parser caches the same way. The stylesheet is not here, because
#: `shell._stylesheet` reads it from disk on every run already.
SOURCES: tuple[tuple[str, str], ...] = (
    ("app", "*.py"),
    ("engine", "*.py"),
    ("engine", "*.yaml"),
    ("policy", "*.md"),
)

#: The packages dropped when the source has moved on. Both are ours; nothing
#: from site-packages is ever touched.
OURS: tuple[str, ...] = ("app", "engine")


def source_fingerprint(root: Path = PROJECT_ROOT) -> str:
    """The newest modification time across everything a process can cache."""
    newest = 0.0
    for folder, pattern in SOURCES:
        for path in (root / folder).rglob(pattern):
            newest = max(newest, path.stat().st_mtime)
    return f"{newest:.6f}"


def reload_if_source_changed(root: Path = PROJECT_ROOT) -> str:
    """Drop our own modules when the files behind them have changed.

    A deploy on a hosted Streamlit updates the checkout and re-runs the
    scripts, but the process keeps every module it has already imported. So
    a new page script runs against the previous commit's modules: it asks
    for a name that did not exist yet and the app dies on the import, or
    worse, it calls a function that quietly behaves like the old version.
    Reboot is supposed to prevent that and has not reliably done so.

    The fix is to notice. The fingerprint of the last import is kept on the
    freshly imported `engine` package, so it is dropped and rewritten with
    the modules it describes and cannot outlive them. When it matches, this
    costs one `stat` per file and changes nothing.

    A package carrying *no* fingerprint counts as stale, which is the case
    this got wrong at first. The deploy that introduces this guard lands
    under a process that imported everything before the guard existed:
    exactly the process that needs clearing, and the only one that can
    never have a stamp. Treating it as fresh left the app broken and the
    guard congratulating itself. On a genuinely cold process the test costs
    nothing, because no module of ours has been imported yet and the loop
    deletes nothing.

    `CU_RELOAD_GUARD=off` disables the purge. A test session imports our
    modules before it ever drives this script, and dropping them mid-session
    would pull the engine out from under every test holding a class object.
    The subprocess test in tests/test_reload_guard.py covers the real path.
    """
    fingerprint = source_fingerprint(root)

    engine = sys.modules.get("engine")
    seen = getattr(engine, "__source_fingerprint__", None) if engine is not None else None

    if seen != fingerprint and os.environ.get("CU_RELOAD_GUARD") != "off":
        for name in [
            name
            for name in sys.modules
            if name in OURS or name.startswith(tuple(f"{package}." for package in OURS))
        ]:
            del sys.modules[name]

    import engine as reloaded

    reloaded.__source_fingerprint__ = fingerprint
    return fingerprint


BUILD = reload_if_source_changed()

import streamlit as st  # noqa: E402  (must follow the sys.path bootstrap)

# A session started before a deploy holds values built by the modules that
# have just been dropped: enum members whose class no longer exists. The
# matcher compares with `type(a) is type(value)`, so those would not match
# any rule rather than failing loudly. Clearing the session is the cheap,
# safe answer; the URL still carries the question, so the page re-seeds
# itself from it on the very next line of work.
if st.session_state.get("_cu_build") != BUILD:
    st.session_state.clear()
    st.session_state["_cu_build"] = BUILD

st.set_page_config(
    page_title="Can I use AI for this?",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

PAGES = [
    # No url_path: the default page is always served at the root, and
    # Streamlit ignores a url_path here, so setting one only suggests a
    # /check URL that 404s. Shareable verdict links are /?data_class=...
    st.Page("views/1_check.py", title="Check", icon=":material/rule:", default=True),
    st.Page("views/2_matrix.py", title="Matrix", icon=":material/grid_on:", url_path="matrix"),
    st.Page(
        "views/3_agent_builder.py",
        title="Agents",
        icon=":material/smart_toy:",
        url_path="agents",
    ),
    st.Page("views/4_scenarios.py", title="Quiz", icon=":material/quiz:", url_path="quiz"),
    st.Page("views/5_review.py", title="Changes", icon=":material/history:", url_path="changes"),
    st.Page("views/6_policy.py", title="Policy", icon=":material/menu_book:", url_path="policy"),
    st.Page("views/7_limits.py", title="Limits", icon=":material/warning:", url_path="limits"),
]

# Top navigation rather than a sidebar: this is read mostly on phones, where a
# sidebar is a hidden drawer.
st.navigation(PAGES, position="top").run()
