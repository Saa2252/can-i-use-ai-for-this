"""The hero page: "Can I use AI for this?"

The page opens on an answer. A visitor who arrives with nothing in the URL
gets a real situation already loaded, so the first thing on screen is a
verdict with its clauses rather than four empty questions (BUILD_SPEC 1).

Order is examples, then the verdict, then the form. The verdict is rendered
into a container reserved before the inputs exist, because it has to appear
above the controls that produce it: a reader should see what this page
answers before being asked to operate it.

The verdict reproduces from its URL, and nothing the visitor enters is stored.
"""

from __future__ import annotations

import streamlit as st

from app.components.footer import render_footer
from app.components.inputs import (
    INPUT_KEYS,
    SEEDED_FLAG,
    apply_example,
    missing_prompt,
    missing_required,
    render_inputs,
    seed_from_query_params,
    share_url,
    write_query_params,
)
from app.components.legend import render_data_class_key
from app.components.shell import inject_styles, page_header
from app.components.tiers import render_tier_key
from app.components.verdict_card import render_verdict, render_waiting
from engine.rules import evaluate
from engine.scenarios import scenario

VERSION = "v1_6"

#: Six golden scenarios, each a situation a reader will recognise and each
#: landing somewhere different in the policy: a tool question, a decision
#: about a person, an agent, a prohibited practice, a confidentiality
#: question, and a secret. The label is what fits on a chip; the scenario's
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


def _load_example(number: int) -> None:
    """Button callback: callbacks run before the rerun, so assigning to
    widget-keyed session state here is safe wherever the row is rendered."""
    apply_example(scenario(number).inputs)


def _seed_once() -> None:
    """Fill the widgets for this session, before any of them is created.

    A shared link carries its own answer and wins. Anything else — a bare
    visit, or `?demo=1` for a screen recording — opens on the example. It
    runs once per session, so the page never snaps back while being used.
    """
    if st.session_state.get(SEEDED_FLAG):
        return
    if any(key in st.query_params for key in INPUT_KEYS):
        seed_from_query_params()
    else:
        apply_example(scenario(OPENING_SCENARIO).inputs)


def _render_examples() -> None:
    st.html(
        '<p class="cu-label">Start with a real one</p>'
        '<p class="cu-hint">Six situations from the scenario set. One tap loads '
        "it and answers it.</p>"
    )
    with st.container(horizontal=True, gap="small"):
        for number, label in EXAMPLES:
            st.button(
                label,
                key=f"cu_example_{number}",
                on_click=_load_example,
                args=(number,),
                help=scenario(number).title,
                width="content",
            )


def main() -> None:
    inject_styles()
    page_header(
        "Can I use AI for this?",
        "An answer from the AI Acceptable Use Policy, with the clauses it rests on.",
    )

    _seed_once()
    _render_examples()

    # Reserved before the inputs exist, and filled after they are read. The
    # verdict depends on widgets rendered below it, which Streamlit allows
    # only through a container held open like this.
    verdict_slot = st.container()

    st.markdown("## Build your own")
    st.html(
        '<p class="cu-hint">Change any answer and the verdict above updates. '
        "Every question is one the policy actually turns on.</p>"
    )
    inputs, visible = render_inputs()

    with verdict_slot:
        if inputs is None:
            render_waiting(missing_prompt(missing_required()))
        else:
            verdict = evaluate(inputs, VERSION)
            render_verdict(verdict, version=VERSION, share_url=share_url(visible))

    render_data_class_key(VERSION)
    render_tier_key(VERSION)

    write_query_params(visible)
    render_footer(VERSION)


main()
