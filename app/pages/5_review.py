"""v1.0 to v1.5: how the policy changed, and why (BUILD_SPEC 9.5).

The "verdict changed" list is computed by running every scenario through both
rulesets. The "how it changed" cards come from the policy's own change log
tables. Nothing here is a hand-maintained summary that could drift.
"""

from __future__ import annotations

import streamlit as st

from app.components.clause_drawer import render_clause_drawer
from app.components.footer import render_footer
from app.components.scenario_text import describe_scenario
from app.components.shell import escape, inject_styles, page_header
from app.components.verdict_card import render_compact_verdict
from app.styles.tokens import style_for
from engine.policy_parser import load_policy
from engine.review import changed_verdicts, compare, compare_all
from engine.scenarios import load_scenarios

#: Two comparisons, and they answer different questions. v1.0 to v1.5 is where
#: the answers themselves moved. v1.5 to v1.6 is where no answer moved at all
#: and the obligations behind them grew, which is what closing a legal gap
#: usually looks like: staff notice nothing, the organization owes more.
COMPARISONS: dict[str, tuple[str, str]] = {
    "v1.0 → v1.5": ("v1_0", "v1_5"),
    "v1.5 → v1.6": ("v1_5", "v1_6"),
}
PAIR_KEY = "cu_review_pair"
CURRENT = "v1_6"
PICKED = "cu_review_scenario"


def _version_label(version: str) -> str:
    """ "v1_5" -> "v1.5". Not to be confused with _label, which formats a verdict."""
    return version.replace("v1_", "v1.")


def _pair() -> tuple[str, str]:
    chosen = st.session_state.get(PAIR_KEY) or next(iter(COMPARISONS))
    return COMPARISONS.get(chosen, next(iter(COMPARISONS.values())))


def _render_pair_picker() -> tuple[str, str]:
    st.segmented_control(
        "Which comparison",
        options=list(COMPARISONS),
        key=PAIR_KEY,
        default=next(iter(COMPARISONS)),
        width="stretch",
        label_visibility="collapsed",
    )
    return _pair()


#: Four points the policy could have settled either way. Each is reconstructed
#: from the policy's own text and change log, which is the only record this
#: app has: it holds no transcript of the review itself, so these set out the
#: two readings and where the decision is recorded, not who argued what.
DISPUTED: tuple[dict[str, str], ...] = (
    {
        "title": "Fatigue detection",
        "question": "Is detecting a driver's fatigue the same as emotion recognition at work?",
        "one": (
            "It reads a human state from a person's face or body while they work, which "
            "is the shape of the practice 6.1 prohibits. Read that way, no approval "
            "route exists and the answer is simply no."
        ),
        "other": (
            "Fatigue is a physical state rather than an emotion, and safety is one of "
            "the uses the law's own exclusions contemplate. Read that way it belongs "
            "with employee monitoring and safety-critical operations, which need "
            "approval rather than a ban."
        ),
        "settled": (
            "Approval, under 8.7 and 8.8. v1.1 made 6.1 defer to the legal text and its "
            "exclusions, and pointed lawful uses near the line at 8.8, which is the "
            "route v1.0 never spelled out."
        ),
        "recorded": "Change log 1.1, Article 5",
        "clauses": ["6.1", "8.7", "8.8"],
    },
    {
        "title": "The absolute ban on secrets",
        "question": "Should 6.3 ever bend, for instance for a self-hosted model with no egress?",
        "one": (
            "A model running on our own hardware with no outbound traffic cannot leak a "
            "key anywhere. A narrow, well-scoped exception would cost nothing and would "
            "stop people working around the rule."
        ),
        "other": (
            "The ban is worth having precisely because it needs no judgement. Any "
            "exception makes every user assess their own tool's egress, which is "
            "exactly the assessment they are least equipped to make."
        ),
        "settled": (
            "It stays absolute. Instead of an exception, v1.1 added controls around it: "
            "tools are configured to keep secret files out of context, and an accidental "
            "exposure is an incident to report and a key to rotate."
        ),
        "recorded": "Change log 1.1, Secrets",
        "clauses": ["6.3", "B.5.1", "B.5.2"],
    },
    {
        "title": "Platform labelling",
        "question": "Must reviewed AI-assisted content carry a label anyway?",
        "one": (
            "If a named person reviewed it and takes editorial responsibility, the "
            "organization's default is that no label is needed. Labelling everything "
            "makes the label meaningless."
        ),
        "other": (
            "A contract or a law can require a label whatever our default says, and so "
            "can the rules of the platform it is published on. Leaving platform rules "
            "out invites a breach nobody checked for."
        ),
        "settled": (
            "The point was taken. v1.2 added platform rules alongside contracts and law "
            "as something that can require a label despite the default."
        ),
        "recorded": "Change log 1.2, Small edits",
        "clauses": ["10.2"],
    },
    {
        "title": "The R1 to R9 codes",
        "question": "Should the uses in Section 8 keep short labels like R1?",
        "one": (
            "Short codes are quick to cite in a form or a register entry, and people "
            "learn them. Clause numbers are longer and easier to mistype."
        ),
        "other": (
            '"Restricted" was doing two jobs at once: a data class in Section 7 and a '
            "category of use in Section 8. The codes kept that confusion alive, and the "
            "clause numbers already identify each use."
        ),
        "settled": (
            'The codes went. v1.3 renamed Section 8 to "Uses that need approval" so '
            "Restricted names only the data class, and v1.4 removed R1 to R9 entirely."
        ),
        "recorded": "Change logs 1.3 and 1.4, Approval codes",
        "clauses": ["8.1", "7.4"],
    },
)


def _render_changed_list(before: str, after: str) -> None:
    changes = changed_verdicts(before, after)
    everything = compare_all(before, after)
    total = len(everything)
    before_label, after_label = _version_label(before), _version_label(after)

    st.markdown("## Scenarios whose verdict changed")
    st.html(
        f'<p class="cu-hint">{len(changes)} of {total} scenarios get a different '
        f"answer under {after_label} than they did under {before_label}. "
        "Each version is encoded as a rulebook in which every rule cites the "
        "clause it comes from; the same scenarios run through both, and this "
        "list is whatever came out. The encoding of each version is a reading "
        "of its text, so the clause on every card is the thing to check.</p>"
    )

    if not changes:
        gained = [c for c in everything if c.added_clauses]
        st.html(
            f'<div class="cu-card cu-card--allowed">'
            f'<p class="cu-status"><span class="cu-status__icon" aria-hidden="true">'
            f"&#10003;</span><span>No answer changed</span></p>"
            f'<p class="cu-reason">Every one of the {total} scenarios gets the same '
            f"verdict under {escape(after_label)} as under {escape(before_label)}."
            "</p></div>"
            f'<p class="cu-hint">That is the finding, not a gap in the comparison. '
            f"{len(gained)} scenarios now cite clauses that {escape(before_label)} "
            "had no clause for, so what a person may do is unchanged while what the "
            "organization owes has grown. Closing a legal gap usually looks like "
            "this: nothing visible at the desk, more to evidence at an audit.</p>"
        )
        for change in gained:
            st.html(
                f'<div class="cu-change">'
                f'<p class="cu-change__title">{escape(change.scenario.title)}</p>'
                f'<p class="cu-route">adds {escape(", ".join(change.added_clauses))}</p>'
                f"</div>"
            )
            render_clause_drawer(change.added_clauses, after, label="Read what was added")
        return

    for change in changes:
        before, after = change.before, change.after
        before_style, after_style = style_for(before.status), style_for(after.status)
        detail = (
            "the kind of approval changed"
            if not change.status_changed
            else "the answer itself changed"
        )
        st.html(
            f'<div class="cu-change">'
            f'<p class="cu-change__title">{escape(change.scenario.title)}</p>'
            f'<p class="cu-change__flow">'
            f'<span class="cu-pill cu-pill--{before_style.slug}">'
            f"{before_style.icon} {escape(_label(before))}</span>"
            f'<span class="cu-arrow">&rarr;</span>'
            f'<span class="cu-pill cu-pill--{after_style.slug}">'
            f"{after_style.icon} {escape(_label(after))}</span></p>"
            f'<p class="cu-meta">{escape(detail)}</p></div>'
        )


def _label(verdict) -> str:
    from app.styles.tokens import APPROVAL_LABELS

    word = style_for(verdict.status).word
    extra = APPROVAL_LABELS.get(verdict.approval_kind, "")
    return f"{word} ({extra})" if extra else word


def _render_scenario_toggle(before: str, after: str) -> None:
    before_label, after_label = _version_label(before), _version_label(after)
    st.markdown("## Run a scenario through both versions")
    scenarios = load_scenarios()
    labels = {scenario.n: f"{scenario.n}. {scenario.title}" for scenario in scenarios}

    picked = st.selectbox(
        "Scenario",
        options=[scenario.n for scenario in scenarios],
        format_func=labels.get,
        key=PICKED,
    )
    scenario = next(s for s in scenarios if s.n == picked)
    change = compare(scenario, before, after)

    st.html(f'<p class="cu-hint">{escape(describe_scenario(scenario))}</p>')
    render_compact_verdict(change.before, heading=f"Under {before_label}")
    render_compact_verdict(change.after, heading=f"Under {after_label}")

    if change.added_clauses:
        st.html(
            f'<p class="cu-label">Clauses {after_label} adds</p>'
            f'<p class="cu-route">{escape(", ".join(change.added_clauses))}</p>'
        )
        render_clause_drawer(change.added_clauses, after, label="Read what was added")
    if change.dropped_clauses:
        st.html(
            f'<p class="cu-label">Clauses {before_label} cited that {after_label} '
            f"does not</p>"
            f'<p class="cu-route">{escape(", ".join(change.dropped_clauses))}</p>'
            '<p class="cu-meta">Clause numbers moved between versions, so a dropped '
            "number is often the same rule under a new number rather than a rule "
            "that went away.</p>"
        )
    if not change.changed and not change.citations_changed:
        st.html(
            '<p class="cu-hint">This one reads the same in both versions, clause for clause.</p>'
        )


def _render_changelogs() -> None:
    st.markdown("## How the policy changed")
    st.html('<p class="cu-hint">Straight from the change log tables in the policy itself.</p>')
    changelogs = load_policy(CURRENT).changelogs
    for version, table in changelogs.items():
        count = len(table.rows)
        with st.expander(f"Version {version} — {count} change{'s' if count != 1 else ''}"):
            for row in table.rows:
                area, change = row[0], row[1]
                st.html(
                    f'<div class="cu-clause">'
                    f'<span class="cu-clause__id">{escape(area)}</span></div>'
                    f'<p class="cu-clause__text">{escape(change)}</p>'
                )


def _render_disputed() -> None:
    st.markdown("## Where it could have gone the other way")
    st.html(
        '<p class="cu-hint">Four points the policy settled in one direction and '
        "could have settled in the other. Reconstructed from the policy text and "
        "its change log, which is the only record here: this app holds no "
        "transcript of the review itself, so these set out the two readings and "
        "where the decision is recorded, not who argued what.</p>"
    )

    for point in DISPUTED:
        with st.expander(point["title"]):
            st.html(
                f'<p class="cu-reason"><strong>{escape(point["question"])}</strong></p>'
                f'<p class="cu-label">One reading</p>'
                f'<p class="cu-clause__text">{escape(point["one"])}</p>'
                f'<p class="cu-label">The other</p>'
                f'<p class="cu-clause__text">{escape(point["other"])}</p>'
                f'<p class="cu-label">How it was settled</p>'
                f'<p class="cu-route">{escape(point["settled"])}</p>'
                f'<p class="cu-meta">Recorded in: {escape(point["recorded"])}</p>'
            )
            render_clause_drawer(point["clauses"], CURRENT, label="The clauses this turns on")


def main() -> None:
    inject_styles()
    page_header(
        "What changed between versions",
        "Six revisions, the verdicts that flipped, and the arguments behind them.",
    )
    before, after = _render_pair_picker()
    _render_changed_list(before, after)
    _render_scenario_toggle(before, after)
    _render_changelogs()
    _render_disputed()
    render_footer(CURRENT)


main()
