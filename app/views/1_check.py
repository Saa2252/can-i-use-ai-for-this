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
from app.components.shell import escape, inject_styles
from app.components.tiers import render_tier_strip
from app.components.verdict_card import (
    render_alternatives,
    render_answer,
    render_reasoning,
    render_safe_way,
    render_share_link,
    render_sticky_verdict,
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
EXAMPLES: tuple[tuple[int, str, str], ...] = (
    (2, "Client contract", ":material/description:"),
    (5, "CV screening", ":material/person_search:"),
    (8, "Agent emails", ":material/smart_toy:"),
    (13, "Emotion detection", ":material/videocam:"),
    (19, "Legal meeting", ":material/gavel:"),
    (12, "API key", ":material/key:"),
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

    for number, _label, _icon in EXAMPLES:
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
        for number, label, icon in EXAMPLES:
            st.button(
                f"{label} ✓" if number == active else label,
                key=f"cu_example_{number}",
                icon=icon,
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


def _render_hero() -> None:
    """The band at the top: the policy, the question, and what kind of answer
    this gives. One sentence and one link; the numbers live on How it works.

    The heading stays a markdown h1, so it is the page's heading and not a
    picture of one.
    """
    with st.container(key="cu_hero"):
        st.markdown("# AI Acceptable Use Policy")
        st.html(
            '<p class="cu-hero__question">Can I use AI for this?</p>'
            '<p class="cu-hero__lede">Write the sentence and read the verdict, with the '
            "clause it rests on. No AI model decides anything here.</p>"
            '<p class="cu-hero__more"><a class="cu-hero__link" href="how" target="_self">'
            "How it works</a></p>"
        )


def main() -> None:
    inject_styles()
    _render_hero()

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

    # The page under the sentence, in reading order: the answer, then three
    # tabs for the evidence, then the terms. The answer's slot and the
    # what-if slot are reserved first and filled once the further questions
    # have been read, because those questions change the answer.
    answer_slot = st.container()
    why_tab, change_tab, share_tab = st.tabs(["Why this answer", "What if", "Share"])

    with change_tab:
        whatif_slot = st.container()
        inputs, included, changeable = render_detail()

    with answer_slot:
        if inputs is None:
            render_waiting(missing_prompt(missing_required()))
        else:
            verdict = evaluate(inputs, VERSION)
            _render_guess_result(verdict.status)
            render_answer(verdict)
            # The way out sits with the answer: someone who has just been
            # told no wants the route before anything else.
            render_safe_way(inputs, VERSION, changeable, _apply_route)

    with why_tab:
        if inputs is None:
            st.html('<p class="cu-hint">Finish the sentence and the reasoning appears here.</p>')
        else:
            render_reasoning(verdict, VERSION, inputs)

    with whatif_slot:
        if inputs is not None:
            st.html(
                '<p class="cu-hint">The same question with one answer changed, run '
                "through the rules again. Below it, the further questions this "
                "combination turns on.</p>"
            )
            render_alternatives(inputs, VERSION, changeable)

    with share_tab:
        st.html(
            '<p class="cu-hint">Your answers travel in the link and nowhere else. '
            "Anyone who opens it sees this same verdict.</p>"
        )
        render_share_link(share_url(included))

    st.markdown("## The three tool tiers")
    st.html(
        '<p class="cu-hint">The policy sorts every AI tool into one of three tiers, '
        "and the tier decides what data may go in.</p>"
    )
    render_tier_strip(VERSION)
    render_data_class_key(VERSION)

    write_query_params(included)

    if inputs is not None:
        render_sticky_verdict(evaluate(inputs, VERSION))

    render_footer(VERSION)


main()
