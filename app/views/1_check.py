"""The hero page: "Can I use AI for this?"

The page is one sentence and its answer. "I want to draft or summarize
client or HR information using a personal or free AI account" is how a
colleague would actually ask; four labelled dropdowns are how a form asks.
Each part of the sentence is a chip, and tapping one opens its options
directly underneath, so the thing being changed never leaves the screen.

Order is: the real situations, the sentence, the answer, the further
questions. The verdict is rendered into a container reserved between the
sentence and More detail, because it has to sit directly under the line that
produced it while the questions that refine it sit below.

The verdict reproduces from its URL, and nothing the visitor enters is
stored.
"""

from __future__ import annotations

import streamlit as st

from app.components.footer import render_footer
from app.components.inputs import (
    INPUT_KEYS,
    SEEDED_FLAG,
    apply_example,
    close_slots,
    missing_prompt,
    missing_required,
    render_detail,
    render_question,
    share_url,
    write_query_params,
)
from app.components.legend import render_data_class_key
from app.components.risk import option_styles
from app.components.shell import escape, inject_styles, page_header
from app.components.tiers import render_tier_key
from app.components.verdict_card import (
    render_safe_way,
    render_share_link,
    render_sticky_verdict,
    render_verdict,
    render_waiting,
)
from app.styles.tokens import STATUS_STYLES
from engine.models import Status
from engine.rules import evaluate
from engine.scenarios import scenario

VERSION = "v1_6"

#: Six golden scenarios, each a situation a reader will recognise and each
#: landing somewhere different in the policy: a tool question, a decision
#: about a person, an agent, a prohibited practice, a confidentiality
#: question, and a secret. The label is what fits on a card; the scenario's
#: own sentence is the tooltip, so nothing here restates the scenario file.
EXAMPLES: tuple[tuple[int, str], ...] = (
    (2, "Client contract"),
    (5, "CV screening"),
    (8, "Agent emails"),
    (13, "Emotion detection"),
    (19, "Legal meeting"),
    (12, "API key"),
)

#: What loads when the URL carries no answer of its own. Scenario 2 is the
#: one most people have already done, and it is Prohibited, so the page opens
#: on the answer that is worth arriving at rather than on a safe default.
OPENING_SCENARIO = 2

#: The scenario waiting for a guess, and the guess that was made.
GUESS_FOR = "_cu_guess_for"
GUESS_RESULT = "_cu_guess_result"

#: The four answers, in severity order, as the guess buttons offer them.
CHOICES: tuple[Status, ...] = (
    Status.ALLOWED,
    Status.NEEDS_APPROVAL,
    Status.NOT_PERMITTED,
    Status.PROHIBITED,
)


# --------------------------------------------------------------------------
# Callbacks. These run before the rerun, so assigning to session state here
# is safe wherever the control that calls them is rendered.
# --------------------------------------------------------------------------


def _ask_for_a_guess(number: int) -> None:
    """Tapping a card asks before it tells."""
    st.session_state[GUESS_FOR] = number
    st.session_state[GUESS_RESULT] = None
    close_slots()


def _submit_guess(number: int, picked: Status) -> None:
    apply_example(scenario(number).inputs)
    st.session_state[GUESS_RESULT] = (number, picked)
    st.session_state[GUESS_FOR] = None


def _skip_guess(number: int) -> None:
    apply_example(scenario(number).inputs)
    st.session_state[GUESS_RESULT] = None
    st.session_state[GUESS_FOR] = None


def _apply_route(route) -> None:
    for change in route.changes:
        st.session_state[change.field] = change.value
    st.session_state[GUESS_RESULT] = None
    close_slots()


def _seed_once() -> None:
    """Fill the inputs for this session, before anything reads them.

    A shared link carries its own answer and wins. Anything else — a bare
    visit, or `?demo=1` for a screen recording — opens on the example. It
    runs once per session, so the page never snaps back while being used.
    """
    if st.session_state.get(SEEDED_FLAG):
        return
    if any(key in st.query_params for key in INPUT_KEYS):
        from app.components.inputs import seed_from_query_params

        seed_from_query_params()
    else:
        apply_example(scenario(OPENING_SCENARIO).inputs)


# --------------------------------------------------------------------------
# The real situations
# --------------------------------------------------------------------------


def _seeded(example, field):
    """The value `apply_example` would put in session state for this field."""
    value = getattr(example, field.key)
    return field.default if value is None else value


def _active_example() -> int | None:
    """Which example, if any, the inputs currently match.

    Compared field by field against the scenario rather than by verdict: two
    scenarios can share an answer, and the card marked active should be the
    one actually loaded.
    """
    from app.components.inputs import FIELDS

    for number, _label in EXAMPLES:
        example = scenario(number).inputs
        # `apply_example` substitutes the field default wherever a scenario
        # leaves an optional input unset, so this comparison has to do the
        # same or no card is ever the active one.
        if all(st.session_state.get(field.key) == _seeded(example, field) for field in FIELDS):
            return number
    return None


def _render_examples(*, show_active: bool = True) -> None:
    """The six cards, with the loaded one marked.

    While a guess is pending the marker is suppressed: the question on screen
    is a different scenario from the one still loaded, and marking the old
    one would point at the wrong card.
    """
    active = _active_example() if show_active else None
    st.html(
        '<p class="cu-label">Start with a real one</p>'
        '<p class="cu-hint">Six situations from the scenario set. Tap one and it '
        "asks what you think before it answers.</p>"
    )
    with st.container(horizontal=True, gap="small", key="cu_examples"):
        for number, label in EXAMPLES:
            st.button(
                f"{label} ✓" if number == active else label,
                key=f"cu_example_{number}",
                on_click=_ask_for_a_guess,
                args=(number,),
                help=scenario(number).title,
                width="content",
            )
    if active is not None:
        st.html(f'<p class="cu-meta">Loaded: {escape(scenario(active).title)}</p>')


def _render_guess_prompt(number: int) -> None:
    """Ask before revealing. No statistics, and no hint in the wording."""
    example = scenario(number)
    st.html(
        '<p class="cu-label">Guess first</p>'
        f'<div class="cu-card cu-card--waiting">'
        f'<p class="cu-reason">{escape(example.title)}</p>'
        f'<p class="cu-subtitle">What does the policy say?</p>'
        f"</div>"
    )
    with st.container(horizontal=True, gap="small", key="cu_guess"):
        for status in CHOICES:
            st.button(
                STATUS_STYLES[status].word,
                key=f"cu_guess_{status.value}",
                on_click=_submit_guess,
                args=(number, status),
            )
    st.button(
        "Just show me",
        key="cu_guess_skip",
        on_click=_skip_guess,
        args=(number,),
        type="tertiary",
    )


def _render_guess_result(verdict_status: Status) -> None:
    """How the guess did, once the answer is on screen."""
    result = st.session_state.get(GUESS_RESULT)
    if not result:
        return
    _number, picked = result
    right = picked is verdict_status
    mark = "✓ You had it" if right else "✕ Not quite"
    said = STATUS_STYLES[picked].word
    tail = "" if right else f" You said {said}."
    st.html(f'<p class="cu-guessed cu-guessed--{"right" if right else "wrong"}">{mark}.{tail}</p>')


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------


def main() -> None:
    inject_styles()
    page_header(
        "Can I use AI for this?",
        "An answer from the AI Acceptable Use Policy, with the clauses it rests on.",
    )

    _seed_once()

    # The option colours are computed from the 7.1 grid every run, so they
    # follow the rules rather than a hand-kept table.
    st.html(
        "<style>"
        + option_styles(
            VERSION,
            st.session_state.get("data_class"),
            st.session_state.get("tool"),
        )
        + "</style>"
    )

    pending = st.session_state.get(GUESS_FOR)
    _render_examples(show_active=pending is None)

    if pending is not None:
        _render_guess_prompt(pending)
        render_footer(VERSION)
        return

    render_question(VERSION)

    # Reserved between the sentence and the further questions, and filled
    # once they have been read: the answer sits directly under the line that
    # produced it, and what refines it sits under the answer.
    verdict_slot = st.container()

    inputs, included, changeable = render_detail()

    with verdict_slot:
        if inputs is None:
            render_waiting(missing_prompt(missing_required()))
        else:
            verdict = evaluate(inputs, VERSION)
            _render_guess_result(verdict.status)
            render_verdict(
                verdict,
                version=VERSION,
                inputs=inputs,
                # Only what is on screen: offering to change a control the
                # visitor cannot see is a dead end dressed as a suggestion.
                changeable=changeable,
            )
            # The way out comes before the link: someone who has just been
            # told no wants the route, not a URL for the refusal.
            render_safe_way(inputs, VERSION, changeable, _apply_route)
            render_share_link(share_url(included))

    render_data_class_key(VERSION)
    render_tier_key(VERSION)

    write_query_params(included)

    if inputs is not None:
        render_sticky_verdict(evaluate(inputs, VERSION))

    render_footer(VERSION)


main()
