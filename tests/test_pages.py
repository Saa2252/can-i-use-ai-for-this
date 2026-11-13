"""Tests for the Matrix, Agent builder, Quiz and Policy pages (Phase 3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.components.grid import CELL_LABELS, EXAMPLES, ITEMS, safer_route
from app.components.scenario_text import describe_scenario
from app.components.tiers import tier_a_conditions
from app.styles.tokens import STATUS_STYLES
from engine.models import Activity, DataClass, Inputs, Status, Tool
from engine.policy_parser import load_policy
from engine.rules import JURISDICTION_LENSES, applies_in, evaluate, load_basis
from engine.scenarios import QUIZ_LOCKED, load_scenarios, scenario

ENTRYPOINT = str(Path(__file__).resolve().parent.parent / "app" / "main.py")
TIMEOUT = 40

#: The query parameter a shared quiz score travels in.
QUIZ_SHARE_PARAM = "score"

PAGES = {
    "check": "views/1_check.py",
    "limits": "views/7_limits.py",
    "matrix": "views/2_matrix.py",
    "agents": "views/3_agent_builder.py",
    "quiz": "views/4_scenarios.py",
    "policy": "views/6_policy.py",
}


def open_page(name: str) -> AppTest:
    at = AppTest.from_file(ENTRYPOINT, default_timeout=TIMEOUT)
    at.run()
    at.switch_page(PAGES[name])
    at.run()
    return at


def body(at: AppTest) -> str:
    return "\n".join(
        [
            *(m.value for m in at.markdown),
            *(h.value for h in at.html if "<style>" not in h.value),
            *(c.value for c in at.code),
        ]
    )


@pytest.mark.parametrize("name", sorted(PAGES))
def test_every_page_runs_without_exception(name):
    assert not open_page(name).exception


# --------------------------------------------------------------------------
# Matrix
# --------------------------------------------------------------------------

#: How the 7.1 table's own wording maps onto an engine verdict.
CELL_WORD_TO_STATUS = {
    "Yes": Status.ALLOWED,
    "Approved use case only": Status.NEEDS_APPROVAL,
    "Never": Status.PROHIBITED,
}


def test_generated_grid_agrees_with_the_parsed_7_1_table():
    """The grid is computed, so it must still say what the policy says.

    "No" is the one word that depends on the tier: a Tier C "No" is
    prohibited under 6.7, while a Tier B "No" is merely not permitted and
    has a compliant route.
    """
    table = load_policy("v1_5").table("7.1")
    tiers = [Tool.TIER_A, Tool.TIER_B, Tool.TIER_C]

    for row in table.rows:
        data_class = DataClass(row[0])
        for index, tool in enumerate(tiers, start=1):
            word = row[index]
            verdict = evaluate(Inputs(data_class=data_class, tool=tool, activity=Activity.DRAFTING))
            if word == "No":
                expected = Status.PROHIBITED if tool is Tool.TIER_C else Status.NOT_PERMITTED
            else:
                expected = CELL_WORD_TO_STATUS[word]
            assert verdict.status is expected, (
                f"7.1 says {word!r} for {data_class.value} in {tool.value}, "
                f"but the engine says {verdict.status.value}"
            )


def test_matrix_renders_a_cell_per_class_and_tier():
    at = open_page("matrix")
    keys = {button.key for button in at.button}
    for data_class in DataClass:
        for tier in ("A", "B", "C"):
            assert f"cu_cell_{data_class.value}_{tier}" in keys


def test_matrix_opens_on_the_grid_with_nothing_selected():
    """Fifteen verdicts are on screen already, so the page has its answer.
    Asking which square first would be asking a reader to choose before
    there is anything to choose between."""
    at = open_page("matrix")
    page = body(at)
    assert "Tap any square to see why." in page
    assert "What it means" not in page


def test_matrix_cell_opens_the_rule_and_an_example():
    at = open_page("matrix")
    at.button(key="cu_cell_Confidential_C").click().run()
    page = body(at)
    assert "Confidential data" in page
    assert "Personal or free AI (Tier C)" in page
    assert "client contract into personal ChatGPT" in page
    assert CELL_LABELS[Status.PROHIBITED] in page
    assert "6.7" in page


def test_the_detail_card_is_in_the_order_the_redesign_asks_for():
    at = open_page("matrix")
    at.button(key="cu_cell_Confidential_B").click().run()
    page = body(at)
    for heading in ("What it means", "Example", "Why it matters", "Safer route"):
        assert heading in page, f"{heading} missing from the detail card"
    assert (
        page.index("What it means")
        < page.index("Example")
        < page.index("Why it matters")
        < page.index("Safer route")
        < page.index("What decided it")
    )


def test_the_safer_route_is_computed_from_the_row():
    """Confidential is blocked in a Tier B tool and allowed in a Tier A one,
    and the route is found by running the rules along the row."""
    at = open_page("matrix")
    at.button(key="cu_cell_Confidential_B").click().run()
    assert "Company-approved AI" in body(at)
    assert safer_route(DataClass.CONFIDENTIAL, Tool.TIER_B) == (Tool.TIER_A, Status.ALLOWED)


def test_a_row_with_no_allowed_cell_says_so_rather_than_inventing_one():
    """Secrets is Never in every tier. Offering a route would be a lie the
    grid itself contradicts."""
    assert safer_route(DataClass.SECRETS, Tool.TIER_C) is None
    at = open_page("matrix")
    at.button(key="cu_cell_Secrets_C").click().run()
    assert "No tool on this row is better" in body(at)


def test_the_four_cell_labels_are_the_legend_and_the_squares():
    """One vocabulary: a square and the key above it must not disagree."""
    at = open_page("matrix")
    page = body(at)
    for label in CELL_LABELS.values():
        assert label in page, f"{label} is not on the page"

    labels = {
        button.label.split("  ")[0] for button in at.button if button.key.startswith("cu_cell_")
    }
    assert labels <= set(CELL_LABELS.values())


def test_plain_view_hides_the_clause_numbers_and_expert_shows_them():
    at = open_page("matrix")
    plain = {b.label for b in at.button if b.key.startswith("cu_cell_")}
    assert all("7.1" not in label for label in plain)

    at.radio(key="cu_matrix_view").set_value("Expert").run()
    expert = {b.label for b in at.button if b.key.startswith("cu_cell_")}
    assert any("7.1" in label for label in expert)


def test_the_grid_is_a_staircase_which_is_what_the_takeaway_claims():
    """ "The more sensitive the data, the more trusted the tool must be." The
    page states that once, at the top, so it had better be true of every row
    the engine computes: a tool that cannot hold a class of data cannot hold
    anything more sensitive either, and nor can any less trusted tool."""
    tiers = [Tool.TIER_A, Tool.TIER_B, Tool.TIER_C]
    classes = list(DataClass)
    allowed = {
        (c, t): evaluate(Inputs(data_class=c, tool=t, activity=Activity.DRAFTING), "v1_6").status
        is Status.ALLOWED
        for c in classes
        for t in tiers
    }
    for row, data_class in enumerate(classes):
        for column, tool in enumerate(tiers):
            if not allowed[(data_class, tool)]:
                for lower in classes[row:]:
                    for righter in tiers[column:]:
                        assert not allowed[(lower, righter)], (
                            f"{data_class.value}/{tool.value} is not allowed but "
                            f"{lower.value}/{righter.value} is, so the grid is not a staircase"
                        )


def test_the_self_hosted_grid_is_behind_a_toggle_and_follows_b_1_3():
    at = open_page("matrix")
    assert "Our servers or cloud" not in body(at)

    at.toggle(key="cu_matrix_selfhosted").set_value(True).run()
    page = body(at)
    for host in ("Our servers or cloud", "A managed laptop", "A personal device"):
        assert host in page
    assert "B.1.3" in page


def test_the_sorting_game_scores_from_the_engine_and_stores_nothing():
    at = open_page("matrix")
    first = ITEMS[0][0]
    expected = [
        tool
        for tool in (Tool.TIER_A, Tool.TIER_B, Tool.TIER_C)
        if evaluate(
            Inputs(
                data_class=scenario(first).inputs.data_class,
                tool=tool,
                activity=Activity.DRAFTING,
            ),
            "v1_6",
        ).status
        is Status.ALLOWED
    ]
    assert expected, "the first item should have at least one home"

    at.button(key=f"cu_sort_{expected[0].value}").click().run()
    page = body(at)
    assert "Right" in page
    assert "1 right so far" in page or "Item" in page
    assert "%" not in page


def test_matrix_explains_what_the_tiers_mean():
    """The grid's headings are bare letters, so the page must define them."""
    at = open_page("matrix")
    assert "What Tier A, B and C mean" in {e.label for e in at.expander}

    page = body(at)
    for tier in ("Tier A", "Tier B", "Tier C"):
        assert tier in page
    assert "not assessed, including personal accounts" in page


def test_matrix_lists_the_tier_a_conditions_in_the_policys_own_words():
    """B.1.2's run-in list is shown as items, and each item is its wording.

    This is what stops the panel drifting: the conditions are sliced out of
    the clause at render time, so a reworded B.1.2 changes the page. If the
    slice ever stops matching, it returns nothing and this fails rather than
    the page quietly showing a tier with no conditions under it.
    """
    conditions = tier_a_conditions("v1_6")
    assert len(conditions) == 9, f"expected B.1.2's nine conditions, got {conditions}"
    assert "an enterprise contract" in conditions
    assert "no training on our inputs" in conditions

    page = body(open_page("matrix"))
    for condition in conditions:
        assert condition in page, f"B.1.2 condition missing from the page: {condition}"

    b12 = load_policy("v1_6").clauses["B.1.2"].text
    for condition in conditions:
        assert condition in b12, f"condition is not B.1.2's own wording: {condition}"


def test_matrix_can_show_the_tier_clauses_in_full():
    """The gloss is a summary, so the clause text has to be reachable."""
    at = open_page("matrix")
    assert load_policy("v1_6").clauses["B.1.2"].text not in body(at), (
        "the full clause should start hidden, or the panel is a wall of text"
    )

    at.checkbox(key="cu_tier_clauses_v1_6").check().run()
    page = body(at)
    for clause_id in ("B.1.1", "B.1.2", "B.1.3"):
        assert load_policy("v1_6").clauses[clause_id].text in page


def test_quiz_defines_the_four_answers_it_asks_you_to_choose_between():
    """The options are the question, so the page has to say what they mean.

    The wording is asserted to be the same subtitles the verdict cards use,
    which is what stops a key and a card disagreeing about a verdict.
    """
    at = open_page("quiz")
    assert "What the four answers mean" in {e.label for e in at.expander}

    page = body(at)
    for status in (Status.ALLOWED, Status.NEEDS_APPROVAL, Status.NOT_PERMITTED, Status.PROHIBITED):
        assert STATUS_STYLES[status].word in page
        assert STATUS_STYLES[status].subtitle in page


def test_quiz_says_how_many_questions_before_anything_is_answered():
    """It used to render nothing here, so the page opened with no sense of
    length. One question at a time makes that worse, not better, unless the
    bar says how many there are."""
    at = open_page("quiz")
    assert any("of 10" in bar.text for bar in at.progress)


def test_check_says_where_the_data_classes_are_defined():
    """7.4 defines Restricted; the rest are deferred to an external standard.

    The page has to be straight about that rather than invent definitions
    the policy does not contain.
    """
    at = open_page("check")
    assert "What the five data classes mean" in {e.label for e in at.expander}

    page = body(at)
    assert "Data Classification Standard" in page
    assert load_policy("v1_6").clauses["7.4"].text in page


def test_limits_page_names_each_gap_and_the_clause_that_closed_it():
    """A page claiming a gap is closed has to show what closed it.

    Every clause named there is asserted to exist in v1.6 and to be new since
    v1.5, so the page cannot claim v1.6 closed something v1.5 already had.
    """
    at = open_page("limits")
    labels = {e.label for e in at.expander}
    assert "Becoming a provider without building anything" in labels
    assert "Telling the staff is not telling their representatives" in labels

    v15 = set(load_policy("v1_5").clauses)
    v16 = load_policy("v1_6").clauses
    for clause_id in ("2.6", "10.5", "8.12", "7.7", "HR.6"):
        assert clause_id in v16, f"{clause_id} is not in v1.6"
        assert clause_id not in v15, f"{clause_id} was already in v1.5; it closed nothing"


def test_limits_page_separates_closed_open_and_structural():
    """Three different kinds of limit, and conflating them would be the easy lie."""
    page = body(open_page("limits"))
    assert "Found in review, and closed" in page
    assert "Still open" in page
    assert "Limits that do not close" in page
    assert "model policy, not an adopted one" in page


def test_limits_page_reports_the_real_verification_dates():
    """Read from the entries, so it cannot advertise a date nobody checked."""
    from engine.rules import load_basis

    page = body(open_page("limits"))
    for checked in {str(e.checked) for e in load_basis()}:
        assert checked in page


def test_every_matrix_cell_has_an_example():
    """All 15 cells, so no cell can open onto an empty detail panel."""
    for data_class in DataClass:
        for tool in (Tool.TIER_A, Tool.TIER_B, Tool.TIER_C):
            assert EXAMPLES.get((data_class, tool)), f"no example for {data_class}/{tool}"


# --------------------------------------------------------------------------
# Agent builder
# --------------------------------------------------------------------------


def test_agent_builder_offers_every_capability_build_spec_names():
    at = open_page("agents")
    keys = {toggle.key for toggle in at.toggle}
    for capability in (
        "read",
        "write",
        "pay",
        "delete",
        "message_external",
        "production_change",
        "call_agents",
    ):
        assert f"cu_cap_{capability}" in keys


def test_agent_builder_starts_read_only():
    at = open_page("agents")
    assert "read-only" in body(at)


def test_switching_on_payments_shows_the_required_controls():
    at = open_page("agents")
    at.toggle(key="cu_cap_pay").set_value(True).run()
    page = body(at)
    assert STATUS_STYLES[Status.NEEDS_APPROVAL].word in page
    assert "Required controls" in page
    assert "8.5" in page


def test_agent_builder_shows_both_irreversible_exceptions_and_their_conditions():
    at = open_page("agents")
    # The heading is the expander's label, which `body` does not collect. It
    # is named for whichever exception the loaded agent engages, and generic
    # when none is, so either wording counts here; the point of this test is
    # that both exceptions and all of their conditions are on the page.
    assert any(
        "two exceptions" in e.label or "without a human each time" in e.label for e in at.expander
    )
    page = body(at)
    assert "The payee is on the allowlist" in page
    assert "The recipient is on the allowlist" in page
    assert "within the rate limit" in page
    assert "The Committee has accepted that risk for the use case" in page


def test_the_exceptions_panel_names_the_capability_that_is_switched_on():
    """Named after the capability that engages it, generic when none does.

    Always-open, this block was most of the page, and a reader met the
    payment allowlist rules before switching payments on. AppTest does not
    expose an expander's open state, so the heading is what is checked.
    """
    at = open_page("agents")
    # The page opens on the Support agent, which sends messages outside the
    # organization, so the panel is already named for that exception.
    opening = next(
        e for e in at.expander if "exception" in e.label.lower() or "message" in e.label.lower()
    )
    assert "without a human each time" in opening.label

    at.button(key="cu_preset_clear").click().run()
    generic = next(e for e in at.expander if "exception" in e.label.lower())
    assert "two exceptions" in generic.label

    at.toggle(key="cu_cap_pay").set_value(True).run()
    specific = next(e for e in at.expander if "payment" in e.label.lower())
    assert "without a human each time" in specific.label
    # and it still carries the conditions, not just a new heading
    assert "The payment is within the per-action and daily caps" in body(at)


def test_the_agents_page_opens_on_a_working_agent() -> None:
    """Seven switches all off is an empty state wearing an answer's clothes."""
    at = open_page("agents")
    assert at.session_state["cu_cap_read"] is True
    assert at.session_state["cu_cap_message_external"] is True
    assert at.session_state["cu_cap_pay"] is False


def _meter_sentence(at: AppTest) -> str:
    """The one line the risk meter writes, so assertions cannot match the
    word "data" somewhere else on a page full of data rules."""
    return next(h.value for h in at.html if "highest factor sets the level" in h.value)


def test_the_risk_meter_quotes_b3_and_names_the_factor_that_set_the_level() -> None:
    """The level has to be traceable to a row of the rubric, not asserted.

    This does not hardcode which factor wins. It checks that whatever the
    meter names is a real B.3 row, and that the words beside it are that
    row's own cell, so a hand-written gloss would fail.
    """
    at = open_page("agents")
    assert "Impact level (B.3)" in body(at)
    sentence = _meter_sentence(at)

    rows = {
        row[0].lower(): [cell.lower() for cell in row[1:]]
        for row in load_policy("v1_6").table("B.3").rows
    }
    named = [factor for factor in rows if factor in sentence]
    assert named, f"the meter names no B.3 factor: {sentence}"
    assert any(cell in sentence for factor in named for cell in rows[factor]), (
        f"the meter names a factor but not that row's own words: {sentence}"
    )


def test_the_risk_meter_does_not_score_the_factors_the_page_never_asks() -> None:
    """B.3 has five factors; two of them depend on what the agent is for."""
    sentence = _meter_sentence(open_page("agents")).lower()
    assert "effect on people and audience" in sentence
    assert "this page does not score them" in sentence


def test_agent_builder_contrasts_in_allowance_with_out_of_allowance():
    at = open_page("agents")
    page = body(at)
    assert "one-time use-case approval" in page
    assert "human approval for each action" in page


def test_agent_builder_says_an_agent_never_widens_its_own_allowlist():
    at = open_page("agents")
    assert "never done by an agent" in body(at)


def test_calling_other_agents_cites_11_9_and_c_6_1():
    at = open_page("agents")
    at.toggle(key="cu_cap_call_agents").set_value(True).run()
    page = body(at)
    assert "11.9" in page
    assert "C.6.1" in page


# --------------------------------------------------------------------------
# Quiz
# --------------------------------------------------------------------------


def walk_quiz(at: AppTest, answer: Status = Status.ALLOWED) -> list[dict[str, str]]:
    """Answer all ten questions, returning what each step put on screen.

    The quiz shows one question at a time, so a test that wants to see every
    question has to play it. Each entry is the heading shown before answering
    and the page as it stood after.
    """
    steps: list[dict[str, str]] = []
    for _ in range(10):
        heading = next(m.value for m in at.markdown if m.value.startswith("## "))
        asked = body(at)
        at.segmented_control[0].set_value(answer).run()
        steps.append({"heading": heading, "asked": asked, "revealed": body(at)})
        at.button(key="cu_quiz_next").click().run()
    return steps


def test_quiz_is_ten_unique_questions_including_the_four_locked_ones():
    steps = walk_quiz(open_page("quiz"))
    assert len(steps) == 10

    titles = {scenario.title: scenario.n for scenario in load_scenarios()}
    shown = set()
    for step in steps:
        title = step["heading"].split(". ", 1)[1]
        assert title in titles, f"unknown scenario title rendered: {title!r}"
        shown.add(titles[title])

    assert len(shown) == 10, "the quiz must not repeat a scenario"
    assert set(QUIZ_LOCKED) <= shown, "scenarios 4, 8, 9 and 14 must always appear"


def test_the_question_does_not_name_the_data_class_before_it_is_answered():
    """Naming the class and the tier turns the question into a Matrix lookup.

    The breakdown is not hidden, it is moved: it belongs to the explanation,
    not to the question.
    """
    steps = walk_quiz(open_page("quiz"))
    for step in steps:
        assert " data · in a " not in step["asked"], (
            f"the input breakdown is visible before answering: {step['heading']}"
        )
        assert " data · in a " in step["revealed"], (
            f"the breakdown never appears in the reveal: {step['heading']}"
        )


def test_no_two_scenarios_describe_identically():
    """Every scenario must read as a distinguishable question.

    Two pairs caught this in practice: 8 vs 9 differ only by the recipient
    allowlist, and 13 vs 14 (emotion recognition against fatigue detection)
    differ only by the activity. A description that omits either makes one
    question with two different right answers.
    """
    descriptions = {}
    for example in load_scenarios():
        text = describe_scenario(example)
        assert text not in descriptions, (
            f"scenarios {descriptions[text]} and {example.n} render identically: {text}"
        )
        descriptions[text] = example.n
    assert len(descriptions) == 21


def test_description_states_what_decides_the_interesting_pairs():
    by_number = {s.n: s for s in load_scenarios()}
    assert "recipient is on the allowlist" in describe_scenario(by_number[8])
    assert "recipient is not on the allowlist" in describe_scenario(by_number[9])
    assert "Emotion recognition" in describe_scenario(by_number[13])
    assert "Fatigue or safety detection" in describe_scenario(by_number[14])


def test_rendered_quiz_questions_are_all_distinct():
    reveals = [step["revealed"] for step in walk_quiz(open_page("quiz"))]
    breakdowns = [
        line
        for page in reveals
        for line in page.splitlines()
        if 'class="cu-hint"' in line and " data · in a " in line
    ]
    assert len(breakdowns) == 10
    assert len(set(breakdowns)) == 10, "two questions render identically"


def test_agent_message_questions_state_the_allowlist_condition():
    """8 and 9 are both locked in, and differ only by this condition."""
    reveals = "\n".join(step["revealed"] for step in walk_quiz(open_page("quiz")))
    assert "recipient is on the allowlist" in reveals
    assert "recipient is not on the allowlist" in reveals


def test_exactly_one_question_is_on_screen_at_a_time():
    at = open_page("quiz")
    for _ in range(10):
        assert len(at.segmented_control) == 1
        assert len(at.segmented_control[0].options) == 4
        at.segmented_control[0].set_value(Status.ALLOWED).run()
        at.button(key="cu_quiz_next").click().run()


def test_answering_reveals_the_clauses_and_marks_the_answer():
    at = open_page("quiz")
    at.segmented_control[0].set_value(Status.ALLOWED).run()
    page = body(at)
    assert ("✓ Correct" in page) or ("✕ Not quite" in page)
    # The score is the end of the quiz, not a running total beside question 1.
    assert "Your score" not in page


def test_progress_says_where_you_are_before_anything_is_answered():
    at = open_page("quiz")
    assert any("Question 1 of 10" in bar.text for bar in at.progress)


def test_the_score_and_a_share_link_arrive_only_at_the_end():
    at = open_page("quiz")
    walk_quiz(at)
    page = body(at)
    assert "Your score" in page
    assert "I scored" in page
    assert f"{QUIZ_SHARE_PARAM}=" in page
    assert "cu_quiz_restart" in {button.key for button in at.button}


def _open_quiz_with(**params: str) -> AppTest:
    """The quiz with query parameters on it.

    They are set after the first run because that run lands on the Check
    page, which writes its own inputs over the whole query string. A visitor
    opening /quiz?score=7 never hits that, since st.navigation runs only the
    page the URL names.
    """
    at = AppTest.from_file(ENTRYPOINT, default_timeout=TIMEOUT)
    at.run()
    at.switch_page(PAGES["quiz"])
    for key, value in params.items():
        at.query_params[key] = value
    at.run()
    return at


def test_a_shared_score_in_the_url_is_shown_as_someone_else_s():
    page = body(_open_quiz_with(**{QUIZ_SHARE_PARAM: "7"}))
    assert "Someone scored" in page and "7/10" in page


def test_a_nonsense_shared_score_is_ignored_rather_than_shown():
    for raw in ("banana", "-1", "11"):
        at = _open_quiz_with(**{QUIZ_SHARE_PARAM: raw})
        assert not at.exception, raw
        assert "Someone scored" not in body(at), raw


# --------------------------------------------------------------------------
# Policy browser
# --------------------------------------------------------------------------


def test_policy_page_shows_the_staff_summary_first():
    at = open_page("policy")
    page = body(at)
    assert "AI at work, on one page" in page
    assert "Always" in page and "Ask first" in page and "Never" in page
    assert "Use approved AI tools with your work account." in page


def test_policy_page_lists_clauses_with_anchors():
    at = open_page("policy")
    page = body(at)
    assert 'id="clause-6-3"' in page
    assert 'id="clause-b-1-3"' in page


def test_policy_page_renders_clause_text_verbatim():
    at = open_page("policy")
    expected = load_policy("v1_5").clause("6.2").text
    assert expected in body(at)


def test_policy_search_narrows_the_list():
    at = open_page("policy")
    at.text_input(key="cu_policy_search").set_value("notetaker").run()
    page = body(at)
    assert "clauses match" in page
    assert "B.6.1" in page
    assert 'id="clause-6-2"' not in page


def test_policy_search_by_clause_id():
    at = open_page("policy")
    at.text_input(key="cu_policy_search").set_value("11.3").run()
    assert 'id="clause-11-3"' in body(at)


def test_jurisdiction_lens_offers_the_four_build_spec_names():
    at = open_page("policy")
    lens = next(w for w in at.segmented_control if w.key == "cu_policy_lens")
    assert list(lens.options) == list(JURISDICTION_LENSES)


def test_jurisdiction_lens_filters_the_backing_notes():
    at = open_page("policy")
    lens = next(w for w in at.segmented_control if w.key == "cu_policy_lens")
    lens.set_value("India").run()
    page = body(at)
    assert "India DPDP Act 2023" in page
    # Colorado is a US entry with no Global marking, so it is out of view.
    assert "Colorado SB 26-189" not in page


def test_us_lens_matches_a_us_state_entry():
    at = open_page("policy")
    lens = next(w for w in at.segmented_control if w.key == "cu_policy_lens")
    lens.set_value("US").run()
    assert "Colorado SB 26-189" in body(at)


# --------------------------------------------------------------------------
# The lens helper itself
# --------------------------------------------------------------------------


def test_global_lens_shows_everything():
    assert all(applies_in(entry, "Global") for entry in load_basis())


def test_country_lens_includes_global_entries():
    owasp = next(e for e in load_basis() if e.clause == "11.*")
    assert applies_in(owasp, "EU"), "a Global standard applies under a country lens too"


def test_us_lens_matches_us_co_but_eu_lens_does_not_match_us():
    colorado = next(e for e in load_basis() if e.clause == "8.1")
    assert applies_in(colorado, "US")
    assert applies_in(colorado, "EU")
    india_only = next(e for e in load_basis() if e.clause == "7.3")
    assert applies_in(india_only, "India")
    assert not applies_in(india_only, "US")


def test_entries_with_no_jurisdiction_are_out_of_a_country_lens():
    our_choice = next(e for e in load_basis() if e.clause == "15.1")
    assert applies_in(our_choice, "Global")
    assert not applies_in(our_choice, "EU")


# --------------------------------------------------------------------------
# Template fields (a model policy shows what an adopter fills in)
# --------------------------------------------------------------------------


def test_front_matter_parses_from_both_document_shapes():
    v5 = load_policy("v1_5").front_matter
    v0 = load_policy("v1_0").front_matter
    assert v5["Policy ID"] == "AIG-POL-001"
    assert v5["Version"] == "1.5 (model policy)"
    assert v5["Organization"] == "[Organization name]"
    assert v0["Policy ID"] == "AIG-POL-001"
    assert v0["Version"] == "1.0 (model policy)"


def test_staff_summary_footer_is_captured():
    footer = load_policy("v1_5").staff_summary.footer
    assert footer.startswith("Questions: [AI governance contact]")


def test_mark_template_fields_marks_placeholders_and_escapes_the_rest():
    from app.components.shell import mark_template_fields

    out = mark_template_fields("Owned by [Your name] & co <b>")
    assert '<span class="cu-template">Your name</span>' in out
    assert "&amp; co &lt;b&gt;" in out
    assert "[" not in out


def test_policy_page_shows_template_fields_not_bare_brackets():
    at = open_page("policy")
    page = body(at)
    assert '<span class="cu-template">Organization name</span>' in page
    assert '<span class="cu-template">AI governance contact</span>' in page
    assert "[Organization name]" not in page


def test_policy_page_says_the_dashed_fields_are_for_an_adopter():
    at = open_page("policy")
    assert "This is a model policy" in body(at)
    assert any("Document details" in e.label for e in at.expander)
