"""Entry point: `streamlit run app/main.py`.

Streamlit puts this file's directory on `sys.path`, not the project root, so
the root is added here before anything imports `engine` or `app`. Pages are
registered with `st.Page`, which makes Streamlit ignore the `pages/`
directory's automatic navigation.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st  # noqa: E402  (must follow the sys.path bootstrap)

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
    st.Page("pages/1_check.py", title="Check", icon=":material/rule:", default=True),
    st.Page("pages/2_matrix.py", title="Matrix", icon=":material/grid_on:", url_path="matrix"),
    st.Page(
        "pages/3_agent_builder.py",
        title="Agents",
        icon=":material/smart_toy:",
        url_path="agents",
    ),
    st.Page("pages/4_scenarios.py", title="Quiz", icon=":material/quiz:", url_path="quiz"),
    st.Page("pages/5_review.py", title="Changes", icon=":material/history:", url_path="changes"),
    st.Page("pages/6_policy.py", title="Policy", icon=":material/menu_book:", url_path="policy"),
    st.Page("pages/7_limits.py", title="Limits", icon=":material/warning:", url_path="limits"),
]

# Top navigation rather than a sidebar: this is read mostly on phones, where a
# sidebar is a hidden drawer.
st.navigation(PAGES, position="top").run()
