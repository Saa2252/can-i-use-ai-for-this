"""Tests for the Matrix, Agent builder, Quiz and Policy pages (Phase 3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.components.scenario_text import describe_scenario
from app.components.tiers import tier_a_conditions
from app.styles.tokens import STATUS_STYLES
from engine.models import Activity, DataClass, Inputs, Status, Tool
from engine.policy_parser import load_policy
from engine.rules import JURISDICTION_LENSES, applies_in, evaluate, load_basis
from engine.scenarios import QUIZ_LOCKED, load_scenarios

ENTRYPOINT = str(Path(__file__).resolve().parent.parent / "app" / "main.py")
TIMEOUT = 40

PAGES = {
    "check": "pages/1_check.py",
    "matrix": "pages/2_matrix.py",
    "agents": "pages/3_agent_builder.py",
    "quiz": "pages/4_scenarios.py",
    "policy": "pages/6_policy.py",
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


def test_matrix_cell_opens_the_rule_and_an_example():
    at = open_page("matrix")
    at.button(key="cu_cell_Confidential_C").click().run()
    page = body(at)
    assert "Confidential data in a Tier C tool" in page
    assert "client contract into personal ChatGPT" in page
    assert STATUS_STYLES[Status.PROHIBITED].word in page
    assert "6.7" in page


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
    conditions = tier_a_conditions("v1_5")
    assert len(conditions) == 9, f"expected B.1.2's nine conditions, got {conditions}"
    assert "an enterprise contract" in conditions
    assert "no training on our inputs" in conditions

    page = body(open_page("matrix"))
    for condition in conditions:
        assert condition in page, f"B.1.2 condition missing from the page: {condition}"

    b12 = load_policy("v1_5").clauses["B.1.2"].text
    for condition in conditions:
        assert condition in b12, f"condition is not B.1.2's own wording: {condition}"


def test_matrix_can_show_the_tier_clauses_in_full():
    """The gloss is a summary, so the clause text has to be reachable."""
    at = open_page("matrix")
    assert load_policy("v1_5").clauses["B.1.2"].text not in body(at), (
        "the full clause should start hidden, or the panel is a wall of text"
    )

    at.checkbox(key="cu_matrix_tier_clauses").check().run()
    page = body(at)
    for clause_id in ("B.1.1", "B.1.2", "B.1.3"):
        assert load_policy("v1_5").clauses[clause_id].text in page


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
    """It used to render nothing here, so the page opened with no sense of length."""
    page = body(open_page("quiz"))
    assert "10 questions" in page


def test_check_says_where_the_data_classes_are_defined():
    """7.4 defines Restricted; the rest are deferred to an external standard.

    The page has to be straight about that rather than invent definitions
    the policy does not contain.
    """
    at = open_page("check")
    assert "What the five data classes mean" in {e.label for e in at.expander}

    page = body(at)
    assert "Data Classification Standard" in page
    assert load_policy("v1_5").clauses["7.4"].text in page


def test_every_matrix_cell_has_an_example():
    """All 15 cells, so no cell can open onto an empty detail panel."""
    source = (Path(__file__).resolve().parent.parent / "app" / "pages" / "2_matrix.py").read_text(
        encoding="utf-8"
    )
    for data_class in DataClass:
        for tier in ("TIER_A", "TIER_B", "TIER_C"):
            assert f"(DataClass.{data_class.name}, Tool.{tier})" in source


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
    # The heading is the expander's label, which `body` does not collect.
    assert any("two exceptions" in e.label for e in at.expander)
    page = body(at)
    assert "The payee is on the allowlist" in page
    assert "The recipient is on the allowlist" in page
    assert "within the rate limit" in page
    assert "The Committee has accepted that risk for the use case" in page


def test_the_exceptions_panel_names_the_capability_that_is_switched_on():
    """Generic by default, and named after the capability once it applies.

    Always-open, this block was most of the page, and a reader met the
    payment allowlist rules before switching payments on. AppTest does not
    expose an expander's open state, so the heading is what is checked.
    """
    at = open_page("agents")
    generic = next(e for e in at.expander if "exception" in e.label.lower())
    assert "two exceptions" in generic.label

    at.toggle(key="cu_cap_pay").set_value(True).run()
    specific = next(e for e in at.expander if "payment" in e.label.lower())
    assert "without a human each time" in specific.label
    # and it still carries the conditions, not just a new heading
    assert "The payment is within the per-action and daily caps" in body(at)


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


def test_quiz_is_ten_unique_questions_including_the_four_locked_ones():
    at = open_page("quiz")
    headings = [m.value for m in at.markdown if m.value.startswith("## ") and m.value[3].isdigit()]
    assert len(headings) == 10

    titles = {scenario.title: scenario.n for scenario in load_scenarios()}
    shown = set()
    for heading in headings:
        title = heading.split(". ", 1)[1]
        assert title in titles, f"unknown scenario title rendered: {title!r}"
        shown.add(titles[title])

    assert len(shown) == 10, "the quiz must not repeat a scenario"
    assert set(QUIZ_LOCKED) <= shown, "scenarios 4, 8, 9 and 14 must always appear"


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
    at = open_page("quiz")
    descriptions = [
        line
        for line in body(at).splitlines()
        if 'class="cu-hint"' in line and " data · in a " in line
    ]
    assert len(descriptions) == 10
    assert len(set(descriptions)) == 10, "two questions render identically"


def test_agent_message_questions_state_the_allowlist_condition():
    at = open_page("quiz")
    page = body(at)
    assert "recipient is on the allowlist" in page
    assert "recipient is not on the allowlist" in page


def test_quiz_offers_the_four_statuses_for_each_question():
    at = open_page("quiz")
    assert len(at.segmented_control) == 10


def test_answering_reveals_the_clauses_and_marks_the_answer():
    at = open_page("quiz")
    control = at.segmented_control[0]
    control.set_value(Status.ALLOWED).run()
    page = body(at)
    assert ("✓ Correct" in page) or ("✕ Not quite" in page)
    assert "Your score" in page


def test_score_counts_only_answered_questions():
    at = open_page("quiz")
    at.segmented_control[0].set_value(Status.ALLOWED).run()
    assert "/ 1" in body(at)


def test_restart_button_is_offered():
    at = open_page("quiz")
    at.segmented_control[0].set_value(Status.ALLOWED).run()
    assert "cu_quiz_restart" in {button.key for button in at.button}


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
