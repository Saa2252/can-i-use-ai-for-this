"""The agent permission builder (BUILD_SPEC 9.3).

Switch on what the agent may do and the required controls appear, worked out
by the rules engine from 11.x and C.x. The two irreversible-action exceptions
are shown with the conditions that make them available, because they are the
only two things an agent may do irreversibly without a human each time.

The page answers before it is touched: an agent with nothing switched on is
still an agent, and 11.3 has an answer for it, so the verdict card is on
screen from the first paint rather than appearing once a toggle is flipped.
"""

from __future__ import annotations

import streamlit as st

from app.components.clause_drawer import render_clause_chips, render_clause_drawer
from app.components.footer import render_footer
from app.components.shell import escape, inject_styles, page_header
from app.styles.tokens import APPROVAL_LABELS, style_for
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

#: Three agents a reader will recognise. Without these the page opens as seven
#: unlabelled switches and a reader has to guess which combinations are
#: interesting; each of these lands on a different verdict.
PRESETS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Support agent", "Reads tickets and replies to customers", ("read", "message_external")),
    ("Invoice agent", "Reads invoices and pays suppliers", ("read", "pay")),
    ("Deploy bot", "Edits records and ships to production", ("read", "write", "production_change")),
)

#: Calling other agents is a new use case rather than an action the engine
#: scores, so it contributes these clauses directly (11.9, C.6.1).
MULTI_AGENT_CLAUSES = ["11.9", "C.6.1"]
MULTI_AGENT_CONTROLS = [
    "Connecting agents to each other is a new use case and goes through approval",
    "Connected agents are assessed as one system, and no agent gains rights through another",
]


def _inputs_for(action: AgentAction | None, **flags) -> Inputs:
    return Inputs(
        data_class=DataClass.CONFIDENTIAL,
        tool=Tool.TIER_A,
        activity=Activity.AGENT,
        agent_action=action,
        **flags,
    )


def _enabled() -> list[tuple[str, AgentAction | None, str]]:
    return [cap for cap in CAPABILITIES if st.session_state.get(f"cu_cap_{cap[0]}")]


def _load_preset(keys: tuple[str, ...]) -> None:
    """Button callback: set every switch, so a preset replaces rather than adds."""
    for key, _action, _label in CAPABILITIES:
        st.session_state[f"cu_cap_{key}"] = key in keys


def _clear() -> None:
    _load_preset(())


def _consequence(action: AgentAction | None) -> str:
    """What switching this one on does on its own, straight from the engine."""
    if action is None:
        return "A new use case on its own: goes through approval (11.9)."
    verdict = evaluate(_inputs_for(action), VERSION)
    word = style_for(verdict.status).word
    extra = APPROVAL_LABELS.get(verdict.approval_kind, "")
    return f"On its own: {word}{f' ({extra})' if extra else ''}."


def _render_presets() -> None:
    st.html('<p class="cu-label">Start from an example</p>')
    with st.container(horizontal=True, gap="small"):
        for label, description, keys in PRESETS:
            st.button(
                label,
                key=f"cu_preset_{label.replace(' ', '_').lower()}",
                on_click=_load_preset,
                args=(keys,),
                help=description,
                width="content",
            )
        st.button("Clear", key="cu_preset_clear", on_click=_clear, width="content")


def _render_toggles() -> None:
    st.markdown("## What may the agent do?")
    for key, action, label in CAPABILITIES:
        st.toggle(label, key=f"cu_cap_{key}", help=_consequence(action))


def _render_rollup(enabled: list[tuple[str, AgentAction | None, str]]) -> None:
    """The verdict for the agent as configured, including the empty one."""
    scored = [evaluate(_inputs_for(action), VERSION) for _k, action, _l in enabled if action]
    multi_agent = any(key == "call_agents" for key, _a, _l in enabled)

    if not enabled:
        verdict = evaluate(_inputs_for(None), VERSION)
        statuses = [verdict.status]
        scored = [verdict]
    else:
        statuses = [v.status for v in scored]
        if multi_agent:
            statuses.append(Status.NEEDS_APPROVAL)

    status = most_severe(statuses)
    style = style_for(status)

    doing = ", ".join(label.lower() for _k, _a, label in enabled)
    summary = f"This agent may {doing}." if enabled else "Nothing is switched on yet."
    st.html(
        f'<div class="cu-card cu-card--{style.slug}">'
        f'<p class="cu-status">'
        f'<span class="cu-status__icon" aria-hidden="true">{style.icon}</span>'
        f"<span>{escape(style.word)}</span></p>"
        f'<p class="cu-subtitle">{escape(style.subtitle)}</p>'
        f'<p class="cu-reason">{escape(summary)}</p></div>'
    )

    if not enabled:
        st.html(
            '<p class="cu-hint">A read-only agent is where 11.3 starts: it still '
            "needs the standing controls below, and it needs approval the moment "
            "it can change anything.</p>"
        )

    controls: list[str] = []
    clauses: list[str] = []
    for verdict in scored:
        controls.extend(verdict.requirements)
        clauses.extend(verdict.clauses)
    if multi_agent:
        controls.extend(MULTI_AGENT_CONTROLS)
        clauses.extend(MULTI_AGENT_CLAUSES)

    controls = list(dict.fromkeys(controls))
    clauses = list(dict.fromkeys(clauses))

    if controls:
        rows = "".join(f"<li>{escape(control)}</li>" for control in controls)
        st.html(f'<p class="cu-label">Required controls</p><ul class="cu-list">{rows}</ul>')

    render_clause_chips(clauses)
    render_clause_drawer(clauses, VERSION)


#: The only two irreversible actions an agent may take without a human each
#: time, with the conditions that unlock them.
EXCEPTIONS: tuple[tuple[AgentAction, str, list[str]], ...] = (
    (
        AgentAction.PAY,
        "Payments",
        ["The payee is on the allowlist", "The payment is within the per-action and daily caps"],
    ),
    (
        AgentAction.MESSAGE_EXTERNAL,
        "Messages outside the organization",
        ["The recipient is on the allowlist", "It is within the rate limit"],
    ),
)


def _render_exceptions(enabled: list[tuple[str, AgentAction | None, str]]) -> None:
    """The two exceptions, opened only when one of them is actually switched on.

    Left always-open this was the bulk of the page, and a reader met the
    allowlist rules for payments before switching payments on.
    """
    active = {a for _k, a, _l in enabled if a}
    relevant = [e for e in EXCEPTIONS if e[0] in active]
    heading = (
        f"How {relevant[0][1].lower()} can run without a human each time"
        if len(relevant) == 1
        else "The two exceptions: payments and external messages"
    )

    with st.expander(heading, expanded=bool(relevant)):
        st.html(
            '<p class="cu-hint">Irreversible actions need a human for each action. '
            "There are exactly two exceptions, and each needs the AI Governance "
            "Committee to have accepted that risk for the use case.</p>"
        )

        for action, title, conditions in EXCEPTIONS:
            on = action in active
            inside = evaluate(_inputs_for(action, **_allowance(action, True)), VERSION)
            outside = evaluate(_inputs_for(action, **_allowance(action, False)), VERSION)

            conditions_html = "".join(f"<li>{escape(c)}</li>" for c in conditions)
            state = "on" if on else "not switched on"
            st.html(
                f'<p class="cu-label">{escape(title)} &middot; {escape(state)}</p>'
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


def _allowance(action: AgentAction, inside: bool) -> dict:
    if action is AgentAction.PAY:
        return {"payee_on_allowlist": inside, "within_caps": inside}
    return {"recipient_on_allowlist": inside, "within_caps": inside}


def _approval_phrase(verdict) -> str:
    label = APPROVAL_LABELS.get(verdict.approval_kind, "")
    return label or style_for(verdict.status).word.lower()


def main() -> None:
    inject_styles()
    page_header(
        "What controls does this agent need?",
        "Switch on what it may do, and the answer changes as you go.",
    )
    _render_presets()
    _render_toggles()
    enabled = _enabled()
    _render_rollup(enabled)
    _render_exceptions(enabled)
    render_footer(VERSION)


main()
