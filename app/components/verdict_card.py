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
from engine.explain import Route, best_flips, is_hard_line, nearest_stricter, safe_route
from engine.gates import Gate, GateState, gates
from engine.models import ApprovalKind, Inputs, Status, Verdict
from engine.rules import evaluate


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

    _render_stakes(verdict)

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
        render_gate_trail(inputs, version)
        # A hard line has no way round it, and a row of chips saying "it
        # would be allowed if it were something else" next to "no route"
        # would be the card arguing with itself.
        if not is_hard_line(inputs, version):
            render_what_if(inputs, version, changeable or [])
        render_why_not_stricter(inputs, version)

    if share_url:
        render_share_link(share_url)


def render_share_link(url: str) -> None:
    """The URL that reproduces this verdict, on its own so a page can decide
    what comes before it."""
    st.html('<p class="cu-label">Copy link</p>')
    st.code(url, language=None, wrap_lines=True)


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


# --------------------------------------------------------------------------
# Stakes and the next move
# --------------------------------------------------------------------------


def _render_stakes(verdict: Verdict) -> None:
    """What is at stake, and what to do about it.

    Both come from the rule that gave the reason line, so a card never
    explains one rule's answer with another rule's consequences. A ruleset
    that carries neither simply shows neither.
    """
    blocks = []
    if verdict.why_it_matters:
        blocks.append(
            '<p class="cu-label">Why it matters</p>'
            f'<p class="cu-stake">{escape(verdict.why_it_matters)}</p>'
        )
    if verdict.next_step:
        blocks.append(
            '<p class="cu-label">Do this next</p>'
            f'<p class="cu-next">{escape(verdict.next_step)}</p>'
        )
    if blocks:
        st.html("".join(blocks))


# --------------------------------------------------------------------------
# The gate trail
# --------------------------------------------------------------------------

_GATE_MARK: dict[GateState, tuple[str, str]] = {
    GateState.PASSED: ("✓", "passed"),
    GateState.FAILED: ("✕", "failed"),
    GateState.NOT_REACHED: ("·", "not reached"),
}


def _gate_row(gate: Gate) -> str:
    icon, word = _GATE_MARK[gate.state]
    chips = "".join(f'<span class="cu-gate__clause">{escape(cid)}</span>' for cid in gate.clauses)
    # A gate that was never reached says so once, in its state chip. The same
    # sentence repeated down three rows reads as an error, not as a trail.
    detail = ""
    if gate.state is not GateState.NOT_REACHED and gate.reason:
        detail = f'<p class="cu-gate__why">{escape(gate.reason)}</p>'

    return (
        f'<li class="cu-gate cu-gate--{gate.state.value}">'
        f'<span class="cu-gate__mark" aria-hidden="true">{icon}</span>'
        f'<span class="cu-gate__body">'
        f'<span class="cu-gate__head">{escape(gate.name)}'
        f'<span class="cu-gate__section">Section {escape(gate.section)}</span>'
        f'<span class="cu-gate__state">{escape(word)}</span></span>'
        f"{detail}"
        f'<span class="cu-gate__clauses">{chips}</span>'
        f"</span></li>"
    )


def render_gate_trail(inputs: Inputs, version: str) -> None:
    """The four gates the question passed through, and where it stopped."""
    trail = gates(inputs, version)
    rows = "".join(_gate_row(gate) for gate in trail)
    st.html(
        '<p class="cu-label">How it got here</p>'
        f'<ol class="cu-gates">{rows}</ol>'
        '<p class="cu-meta">Four gates, in the policy\'s own order: Section 6, then '
        "7, then 8, then 9. Each one is read from the rules that fired.</p>"
    )


# --------------------------------------------------------------------------
# The safe way
# --------------------------------------------------------------------------

#: How a change reads as advice rather than as a field assignment. The engine
#: returns a field and a value; this is the UI putting it in the imperative.
ROUTE_PHRASES: dict[str, str] = {
    "tool": "Move the work into {value}",
    "host": "Run the model on {value}",
    "data_class": "Use {value} instead",
    "data_kind": "Take out what makes it {value}",
    "agent_action": "Limit the agent to: {value}",
    "meeting_type": "Use it in {value}",
    "human_review": "Put a human in the loop who can overrule it",
    "client_contract_allows": "Get the client contract to allow it",
    "payee_on_allowlist": "Put the payee on the allowlist",
    "recipient_on_allowlist": "Put the recipient on the allowlist",
    "within_caps": "Bring it inside the caps",
    "training_or_finetuning": "Do not use it for training or fine-tuning",
}


def _mid_sentence(words: str) -> str:
    """A control's label, dropped into the middle of a sentence.

    Option labels are written to start a line ("An ordinary meeting"), and
    "Use it in An ordinary meeting" reads as a typo. Only a first word that
    is otherwise lowercase is lowered, so "HR record" and "Tier A" keep their
    capitals.
    """
    first = words.split(" ", 1)[0]
    if first[:1].isupper() and first[1:].islower():
        return words[:1].lower() + words[1:]
    return words


def route_sentence(route: Route) -> str:
    """One imperative sentence per change, joined."""
    from app.components.inputs import DATA_SENTENCE, TOOL_SENTENCE

    plain = {"tool": TOOL_SENTENCE, "data_class": DATA_SENTENCE}
    parts: list[str] = []
    for change in route.changes:
        words = plain.get(change.field, {}).get(change.value)
        if words is None:
            words = _mid_sentence(_value_phrase(change.field, change.value))
        template = ROUTE_PHRASES.get(change.field, "Change {field} to {value}")
        parts.append(template.format(value=words, field=change.field.replace("_", " ")))
    return ", and ".join(parts) + "."


def render_safe_way(
    inputs: Inputs,
    version: str,
    changeable: list[str],
    on_apply,
) -> None:
    """The smallest change that reaches a better answer, as a button.

    The route is searched with `evaluate`, one change before two, so the
    button cannot promise an answer the engine would refuse to give. Where
    the activity itself is a Section 6 prohibition there is nothing to
    search: the card says so instead of implying a way round it.
    """
    verdict = evaluate(inputs, version)
    if verdict.status is Status.ALLOWED:
        return

    if is_hard_line(inputs, version):
        cites = ", ".join(verdict.decisive_clauses) or "Section 6"
        st.html(
            '<div class="cu-noroute">'
            '<p class="cu-noroute__head">No route: this is a hard line.</p>'
            f'<p class="cu-noroute__body">Section 6 rules this out as a use, not as a '
            f"way of working. Nothing you change about the data or the tool reaches a "
            f'different answer. <span class="cu-cite">{escape(cites)}</span></p>'
            "</div>"
        )
        return

    route = safe_route(inputs, version, changeable)
    if route is None:
        return

    style = style_for(route.status)
    sentence = route_sentence(route)
    st.html(
        '<p class="cu-label">Show me the safe way</p>'
        f'<p class="cu-hint">The smallest change that reaches '
        f"<strong>{escape(style.word.lower())}</strong>, found by running the same "
        f"rules over every one- and two-answer change.</p>"
    )
    st.button(
        f"{sentence.rstrip('.')}  {style.icon} {style.word}",
        key="cu_safe_way",
        on_click=on_apply,
        args=(route,),
        type="primary",
        help="Applies this change and answers again.",
    )


# --------------------------------------------------------------------------
# The sticky bar
# --------------------------------------------------------------------------


def render_sticky_verdict(verdict: Verdict) -> None:
    """The answer, pinned to the foot of a narrow screen.

    On a phone the picker fills the screen, which is exactly when the answer
    matters most and is exactly when it is scrolled away. This is a summary
    of the card above, not a second card: the word, and on tap the sentence
    and the clauses that decided it. The stylesheet shows it below 640px and
    hides it everywhere else.
    """
    style = style_for(verdict.status)
    headline = verdict.reasons[0] if verdict.reasons else ""
    chips = "".join(
        f'<span class="cu-gate__clause">{escape(cid)}</span>' for cid in verdict.decisive_clauses
    )
    st.html(
        f'<details class="cu-sticky cu-sticky--{style.slug}">'
        f"<summary>"
        f'<span class="cu-sticky__icon" aria-hidden="true">{escape(style.icon)}</span>'
        f'<span class="cu-sticky__word">{escape(style.word)}</span>'
        f'<span class="cu-sticky__more">tap for why</span>'
        f"</summary>"
        f'<p class="cu-sticky__reason">{escape(headline)}</p>'
        f'<p class="cu-sticky__clauses">{chips}</p>'
        f"</details>"
    )
