"""The verdict card (BUILD_SPEC 8).

Status line, one-sentence reason, clause chips, "Backed by" badges,
requirements or try-instead, and Copy link.
"""

from __future__ import annotations

import streamlit as st

from app.components.basis_badges import render_basis_row
from app.components.clause_drawer import render_citations, render_clause_chips
from app.components.shell import escape
from app.styles.tokens import APPROVAL_LABELS, style_for
from engine.explain import best_flips, nearest_stricter
from engine.models import ApprovalKind, Inputs, Status, Verdict


def render_waiting(prompt: str) -> None:
    """The card shown when a required answer has been cleared.

    A segmented control deselects when its chosen chip is clicked again, so a
    visitor can empty an answer the engine needs. Before this, that reached
    pydantic as None and Streamlit printed a ValidationError traceback to
    someone who had done nothing wrong.
    """
    st.html(
        '<div class="cu-card cu-card--waiting">'
        '<p class="cu-status">'
        '<span class="cu-status__icon" aria-hidden="true">?</span>'
        f"<span>{escape(prompt)}</span></p>"
        '<p class="cu-subtitle">Clicking a chosen chip again clears it. '
        "Pick one and the answer comes straight back.</p>"
        "</div>"
    )


def render_verdict(
    verdict: Verdict,
    *,
    version: str = "v1_5",
    share_url: str | None = None,
    inputs: Inputs | None = None,
    changeable: list[str] | None = None,
) -> None:
    """Render one verdict, top to bottom.

    Pass `inputs` and the fields currently on screen to get the two computed
    panels underneath: what one change would do, and what nearly happened.
    Both re-run the engine rather than describing it, so neither can claim a
    rule the rulebook does not have.
    """
    style = style_for(verdict.status)

    approval = ""
    if verdict.approval_kind is not ApprovalKind.NONE:
        approval = f'<p class="cu-approval">{escape(APPROVAL_LABELS[verdict.approval_kind])}</p>'

    headline = verdict.reasons[0] if verdict.reasons else ""

    st.html(
        f'<div class="cu-card cu-card--{style.slug}">'
        f'<p class="cu-status">'
        f'<span class="cu-status__icon" aria-hidden="true">{style.icon}</span>'
        f"<span>{escape(style.word)}</span></p>"
        f'<p class="cu-subtitle">{escape(style.subtitle)}</p>'
        f"{approval}"
        f'<p class="cu-reason">{escape(headline)}</p>'
        f"</div>"
    )

    if verdict.status is Status.NOT_PERMITTED and verdict.try_instead:
        st.html(
            '<p class="cu-label">Try instead</p>'
            f'<p class="cu-route">{escape(verdict.try_instead)}</p>'
        )

    if verdict.status is Status.NEEDS_APPROVAL and verdict.requirements:
        _render_list("What is required", verdict.requirements)

    _render_supporting_reasons(verdict)

    render_citations(verdict.decisive_clauses, verdict.clauses, version)
    render_basis_row(verdict.basis)

    if inputs is not None:
        render_what_if(inputs, version, changeable or [])
        render_why_not_stricter(inputs, version)

    if share_url:
        st.html('<p class="cu-label">Copy link</p>')
        st.code(share_url, language=None, wrap_lines=True)


def render_compact_verdict(verdict: Verdict, *, heading: str) -> None:
    """A short card for side-by-side comparison, without the drawer or badges."""
    style = style_for(verdict.status)
    approval = ""
    if verdict.approval_kind is not ApprovalKind.NONE:
        approval = f'<p class="cu-approval">{escape(APPROVAL_LABELS[verdict.approval_kind])}</p>'
    chips = "".join(f'<li class="cu-chip">{escape(cid)}</li>' for cid in verdict.clauses)
    st.html(
        f'<div class="cu-card cu-card--{style.slug}">'
        f'<p class="cu-label">{escape(heading)}</p>'
        f'<p class="cu-status cu-status--compact">'
        f'<span class="cu-status__icon" aria-hidden="true">{style.icon}</span>'
        f"<span>{escape(style.word)}</span></p>"
        f"{approval}"
        f'<p class="cu-reason">{escape(verdict.reasons[0] if verdict.reasons else "")}</p>'
        f'<ul class="cu-chips">{chips}</ul>'
        f"</div>"
    )


def _render_supporting_reasons(verdict: Verdict) -> None:
    """Everything else that fired, after the decisive reason."""
    rest = verdict.reasons[1:]
    if not rest:
        return
    _render_list("Also applies", rest)


def _render_list(label: str, items: list[str]) -> None:
    rows = "".join(f"<li>{escape(item)}</li>" for item in items)
    st.html(f'<p class="cu-label">{escape(label)}</p><ul class="cu-list">{rows}</ul>')


#: How each changeable field is named in a "What if" chip. The engine returns
#: a field and a value; turning those into English is the UI's job, and the
#: import sits here rather than at the top because `inputs` imports this
#: module for `escape` only through `shell`, not the other way round.
FIELD_PHRASES = {
    "data_class": "the data were",
    "tool": "the tool were",
    "activity": "it were",
    "data_kind": "it involved",
    "host": "it ran on",
    "meeting_type": "the meeting were",
    "agent_action": "the agent would",
}


#: The same fields as nouns, for the near-miss list, which reads as a
#: statement about the input rather than as a clause of a sentence.
FIELD_NOUNS = {
    "data_class": "the data class",
    "tool": "the tool",
    "activity": "the activity",
    "data_kind": "what it involves",
    "host": "where it runs",
    "meeting_type": "the meeting",
    "agent_action": "the agent action",
}


def _value_phrase(field: str, value) -> str:
    """The value in the words the form uses for it."""
    from app.components.inputs import (
        ACTIVITY_LABELS,
        AGENT_ACTION_LABELS,
        DATA_CLASS_LABELS,
        DATA_KIND_LABELS,
        HOST_LABELS,
        MEETING_TYPE_LABELS,
        TOOL_LABELS,
    )

    maps = {
        "data_class": DATA_CLASS_LABELS,
        "tool": TOOL_LABELS,
        "activity": ACTIVITY_LABELS,
        "data_kind": DATA_KIND_LABELS,
        "host": HOST_LABELS,
        "meeting_type": MEETING_TYPE_LABELS,
        "agent_action": AGENT_ACTION_LABELS,
    }
    if isinstance(value, bool):
        return "yes" if value else "no"
    label = maps.get(field, {}).get(value, str(value).replace("_", " "))
    # The form shows "plain English · Official term"; a chip has room for the
    # plain half only, and the official term is on the control itself.
    return label.split(" · ")[0]


def render_what_if(inputs: Inputs, version: str, changeable: list[str]) -> None:
    """One-input changes that land on a different answer.

    Computed by re-running `evaluate` with that one field altered, so a chip
    cannot promise an answer the engine would not give. Only changes that
    move the status appear: "still prohibited" is not a what-if.
    """
    found = best_flips(inputs, version, changeable)
    if not found:
        return

    chips = "".join(
        f'<span class="cu-whatif cu-whatif--{style_for(flip.status).slug}">'
        f"{escape(FIELD_PHRASES.get(flip.field, 'it were'))} "
        f"<strong>{escape(_value_phrase(flip.field, flip.value))}</strong>"
        f'<span class="cu-whatif__to">{escape(style_for(flip.status).icon)} '
        f"{escape(style_for(flip.status).word)}</span></span>"
        for flip in found
    )
    st.html(
        '<p class="cu-label">What if…</p>'
        f'<div class="cu-whatifs">{chips}</div>'
        '<p class="cu-meta">Each one is this same question with a single answer '
        "changed, run through the rules again.</p>"
    )


def render_why_not_stricter(inputs: Inputs, version: str) -> None:
    """The stricter rule that came closest, and the condition that stopped it.

    "Why is this not prohibited?" is the question an auditor asks, and a
    policy that cannot answer it is being trusted rather than read. The rule
    and the condition are both computed: nothing here is written down.
    """
    near = nearest_stricter(inputs, version)
    if near is None:
        return

    style = style_for(near.rule.status)
    conditions = "".join(
        f"<li>{escape(FIELD_NOUNS.get(condition.field, condition.field.replace('_', ' ')))} "
        f"would have to be "
        f"{escape(' or '.join(_value_phrase(condition.field, v) for v in condition.accepted))}"
        f"</li>"
        for condition in near.missing
    )
    with st.expander(f"Why is this not {style.word.lower()}?"):
        st.html(
            f'<p class="cu-hint">The nearest stricter rule is <code>{escape(near.rule.id)}</code>. '
            f"It did not fire, and this is what it wanted:</p>"
            f'<ul class="cu-list">{conditions}</ul>'
            f'<p class="cu-route">{escape(near.rule.reason)}</p>'
        )
        render_clause_chips(near.rule.clauses, label="It would cite")
