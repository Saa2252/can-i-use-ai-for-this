"""The custom footer (BUILD_SPEC 8 and 7).

No Streamlit chrome, and it states plainly that nothing the visitor enters is
stored, because this is a governance app making a claim about itself.
"""

from __future__ import annotations

import streamlit as st

from app.components.shell import escape
from engine.policy_parser import load_policy

#: BUILD_SPEC 7: every basis entry is checked on this date.
STATUS_CHECKED = "22 Oct 2026"

#: From the policy's own front matter.
POLICY_ID = "AIG-POL-001"
VERSION_DATE = "9 Nov 2026"


def render_footer(version: str = "v1_5") -> None:
    policy = load_policy(version)
    label = policy.version.replace("v1_", "1.")

    st.html(
        '<div class="cu-footer">'
        '<span class="cu-footer__row">'
        "<strong>Model policy, not legal advice.</strong> "
        "Legal references are for context only. "
        f"Status checked {escape(STATUS_CHECKED)}."
        "</span>"
        '<span class="cu-footer__row">'
        "<strong>Nothing you enter is stored.</strong> "
        "There is no database, no logging of your choices, and no LLM in the "
        "decision path. Every verdict comes from the policy text and a set of "
        "rules you can read."
        "</span>"
        '<span class="cu-footer__row">'
        f"{escape(POLICY_ID)} · version {escape(label)} · "
        f"policy dated {escape(VERSION_DATE)}"
        "</span>"
        "</div>"
    )
