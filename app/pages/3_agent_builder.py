"""The agent permission builder (BUILD_SPEC 9.3).

Switch on what the agent may do and the required controls appear, worked out
by the rules engine from 11.x and C.x. The two irreversible-action exceptions
are shown with the conditions that make them available, because they are the
only two things an agent may do irreversibly without a human each time.
"""

from __future__ import annotations

import streamlit as st

from app.components.clause_drawer import render_clause_chips, render_clause_drawer
from app.components.footer import render_footer
from app.components.shell import escape, inject_styles, page_header
from app.styles.tokens import style_for
from engine.models import (
    Activity,
    AgentAction,
    DataClass,
    Inputs,
    Status,
    Tool,
    most_severe,
)
from engine.rules import evaluate

VERSION = "v1_5"

#: The capabilities BUILD_SPEC 9.3 asks for, in order.
CAPABILITIES: tuple[tuple[str, AgentAction | None, str], ...] = (
    ("read", AgentAction.READ, "Read data"),
    ("write", AgentAction.WRITE, "Write or change records"),
    ("pay", AgentAction.PAY, "Make payments"),
    ("delete", AgentAction.DELETE, "Delete things"),
    ("message_external", AgentAction.MESSAGE_EXTERNAL, "Send messages outside the org"),
    ("production_change", AgentAction.PRODUCTION_CHANGE, "Change production systems"),
    ("call_agents", None, "Call other agents"),
)

#: Calling other agents is a new use case rather than an action the engine
#: scores, so it contributes these clauses directly (11.9, C.6.1).
MULTI_AGENT_CLAUSES = ["11.9", "C.6.1"]
MULTI_AGENT_CONTROLS = [
    "Connecting agents to each other is a new use case and goes through approval",
    "Connected agents are assessed as one system, and no agent gains rights through another",
]


def _inputs_for(action: AgentAction, **flags) -> Inputs:
    return Inputs(
        data_class=DataClass.CONFIDENTIAL,
        tool=Tool.TIER_A,
        activity=Activity.AGENT,
        agent_action=action,
        **flags,
    )


def _enabled() -> list[tuple[str, AgentAction | None, str]]:
    return [cap for cap in CAPABILITIES if st.session_state.get(f"cu_cap_{cap[0]}")]


def _render_toggles() -> None:
    st.markdown("## What may the agent do?")
    for key, _action, label in CAPABILITIES:
        # No `value=`: with a key present, Streamlit warns when a default is
        # also passed, and a toggle already defaults to off.
        st.toggle(label, key=f"cu_cap_{key}")


def _render_rollup(enabled: list[tuple[str, AgentAction | None, str]]) -> None:
    if not enabled:
        st.html(
            '<p class="cu-hint">An agent with nothing switched on is read-only '
            "by default, which is where 11.3 starts.</p>"
        )
        return

    verdicts = [
        evaluate(_inputs_for(action), VERSION) for _key, action, _label in enabled if action
    ]
    statuses = [verdict.status for verdict in verdicts]
    if any(key == "call_agents" for key, _a, _l in enabled):
        statuses.append(Status.NEEDS_APPROVAL)

    status = most_severe(statuses)
    style = style_for(status)
    st.html(
        f'<div class="cu-card cu-card--{style.slug}">'
        f'<p class="cu-status">'
        f'<span class="cu-status__icon" aria-hidden="true">{style.icon}</span>'
        f"<span>{escape(style.word)}</span></p>"
        f'<p class="cu-subtitle">{escape(style.subtitle)}</p></div>'
    )

    controls: list[str] = []
    clauses: list[str] = []
    for verdict in verdicts:
        controls.extend(verdict.requirements)
        clauses.extend(verdict.clauses)
    if any(key == "call_agents" for key, _a, _l in enabled):
        controls.extend(MULTI_AGENT_CONTROLS)
        clauses.extend(MULTI_AGENT_CLAUSES)

    controls = list(dict.fromkeys(controls))
    clauses = list(dict.fromkeys(clauses))

    rows = "".join(f"<li>{escape(control)}</li>" for control in controls)
    st.html(f'<p class="cu-label">Required controls</p><ul class="cu-list">{rows}</ul>')

    render_clause_chips(clauses)
    render_clause_drawer(clauses, VERSION)


def _render_exceptions(enabled: list[tuple[str, AgentAction | None, str]]) -> None:
    """The only two irreversible actions an agent may take on its own."""
    st.markdown("## The two exceptions")
    st.html(
        '<p class="cu-hint">Irreversible actions need a human for each action. '
        "There are exactly two exceptions, and each needs the AI Governance "
        "Committee to have accepted that risk for the use case.</p>"
    )

    for action, title, conditions in (
        (
            AgentAction.PAY,
            "Payments",
            [
                "The payee is on the allowlist",
                "The payment is within the per-action and daily caps",
            ],
        ),
        (
            AgentAction.MESSAGE_EXTERNAL,
            "Messages outside the organization",
            ["The recipient is on the allowlist", "It is within the rate limit"],
        ),
    ):
        active = any(a is action for _k, a, _l in enabled)
        inside = evaluate(_inputs_for(action, **_allowance(action, True)), VERSION)
        outside = evaluate(_inputs_for(action, **_allowance(action, False)), VERSION)

        conditions_html = "".join(f"<li>{escape(c)}</li>" for c in conditions)
        state = "" if active else " (not switched on)"
        st.html(
            f'<p class="cu-label">{escape(title)}{escape(state)}</p>'
            f'<ul class="cu-list">{conditions_html}'
            f"<li>The Committee has accepted that risk for the use case</li></ul>"
            f'<p class="cu-route"><strong>All three met:</strong> '
            f"{escape(_approval_phrase(inside))}. "
            f"<strong>Any one missing:</strong> {escape(_approval_phrase(outside))}.</p>"
        )

    st.html(
        '<p class="cu-hint">Adding a payee or a recipient to an allowlist is '
        "never done by an agent. A human adds it, and it is logged.</p>"
    )
    render_clause_chips(["11.3", "C.2"])
    render_clause_drawer(["11.3", "C.2"], VERSION, label="Read 11.3 and C.2 in full")


def _allowance(action: AgentAction, inside: bool) -> dict:
    if action is AgentAction.PAY:
        return {"payee_on_allowlist": inside, "within_caps": inside}
    return {"recipient_on_allowlist": inside, "within_caps": inside}


def _approval_phrase(verdict) -> str:
    from app.styles.tokens import APPROVAL_LABELS

    label = APPROVAL_LABELS.get(verdict.approval_kind, "")
    return label or style_for(verdict.status).word.lower()


def main() -> None:
    inject_styles()
    page_header(
        "What controls does this agent need?",
        "Switch on what it may do. The controls come from Section 11 and Part C.",
    )
    _render_toggles()
    enabled = _enabled()
    _render_rollup(enabled)
    _render_exceptions(enabled)
    render_footer(VERSION)


main()
