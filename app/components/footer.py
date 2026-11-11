"""The custom footer (BUILD_SPEC 8 and 7).

No Streamlit chrome, and it states plainly that nothing the visitor enters is
stored, because this is a governance app making a claim about itself.
"""

from __future__ import annotations

import streamlit as st

from app.components.shell import escape
from engine.policy_parser import load_policy

#: Fallbacks only. These used to be the source of truth and had to be edited by
#: hand whenever the policy was revised, which is exactly how a footer ends up
#: claiming a date the document no longer carries. They are now read from the
#: policy's own front matter, and these values are used only if a future policy
#: file drops those rows.
STATUS_CHECKED = "11 Nov 2026"
POLICY_ID = "AIG-POL-001"
VERSION_DATE = "12 Nov 2026"


def render_footer(version: str = "v1_6") -> None:
    policy = load_policy(version)
    label = policy.version.replace("v1_", "1.")

    fields = policy.front_matter
    policy_id = fields.get("Policy ID") or POLICY_ID
    version_date = fields.get("Version date") or VERSION_DATE
    status_checked = fields.get("Regulatory status checked") or STATUS_CHECKED

    st.html(
        '<div class="cu-footer">'
        '<span class="cu-footer__row">'
        "<strong>Model policy, not legal advice.</strong> "
        "Legal references are for context only. "
        f"Status checked {escape(status_checked)}."
        "</span>"
        '<span class="cu-footer__row">'
        "<strong>Nothing you enter is stored.</strong> "
        "There is no database, no logging of your choices, and no LLM in the "
        "decision path. Every verdict comes from the policy text and a set of "
        "rules you can read."
        "</span>"
        '<span class="cu-footer__row">'
        f"{escape(policy_id)} · version {escape(label)} · "
        f"policy dated {escape(version_date)}"
        "</span>"
        "</div>"
    )
