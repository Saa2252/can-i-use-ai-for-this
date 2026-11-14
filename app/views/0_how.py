"""How it works: the method, for a reader who governs rather than uses.

Every other page answers a question for someone at a desk. This one is for
the policy lead, the auditor or the regulator who wants to know what kind of
thing they are looking at before they trust an answer from it: policy as
data, every verdict citing its clause, a crosswalk to the law, and a test
suite that fails when a citation points at nothing.

Nothing on this page is typed in. The numbers, the sample rule, the
crosswalk and the coverage table are read from the same files the engine
runs on, so the page cannot describe a version of the project that no
longer exists.
"""

from __future__ import annotations

import streamlit as st

from app.components.footer import render_footer
from app.components.method import (
    basis_counts,
    beyond_the_law,
    coverage,
    crosswalk,
    describe_pattern,
    figures,
    rule_source,
    whole_policy_basis,
)
from app.components.shell import escape, inject_styles, page_header
from app.styles.tokens import BASIS_ICONS, BASIS_LABELS, STATUS_STYLES
from engine.models import BasisType, Status

VERSION = "v1_6"
REPO = "https://github.com/Saa2252/can-i-use-ai-for-this"
REPO_LABEL = REPO.removeprefix("https://")

#: The rule shown verbatim. It is the one with the most going on in a few
#: lines: four conditions, an approval kind, two clauses from different
#: parts of the policy, and requirements that follow from them.
SAMPLE_RULE = "agent_payment_in_cap_to_allowlisted_payee"

#: Most severe first, which is the order the engine resolves a verdict in.
SEVERITY: tuple[Status, ...] = (
    Status.PROHIBITED,
    Status.NOT_PERMITTED,
    Status.NEEDS_APPROVAL,
    Status.ALLOWED,
)

#: The pages that read the engine. Named so the claim "they cannot drift
#: from each other" is specific.
CONSUMERS: tuple[str, ...] = ("Check", "Matrix", "Agents", "Quiz", "Changes")


# --------------------------------------------------------------------------
# One picture
# --------------------------------------------------------------------------


def _box(kicker: str, title: str, body: str, *, modifier: str = "") -> str:
    classes = "cu-flow__box" + (f" cu-flow__box--{modifier}" if modifier else "")
    kicker_html = f'<span class="cu-flow__kicker">{escape(kicker)}</span>' if kicker else ""
    return (
        f'<div class="{classes}">{kicker_html}'
        f"<strong>{escape(title)}</strong><span>{escape(body)}</span></div>"
    )


def _render_flow() -> None:
    f = figures(VERSION)
    st.markdown("## In one picture")
    st.html(
        '<p class="cu-hint">Three files go in. One engine reads them. Every page '
        "shows what comes out.</p>"
    )
    arrow = '<div class="cu-flow__arrow" aria-hidden="true"></div>'
    pages = "".join(f'<li class="cu-chip">{escape(name)}</li>' for name in CONSUMERS)
    st.html(
        '<div class="cu-flow">'
        '<div class="cu-flow__row">'
        + _box(
            "policy/*.md",
            "The policy, as written",
            f"{f.clauses} clauses, sliced out of the document by a parser and shown "
            "word for word. No clause text lives in the code.",
        )
        + _box(
            "engine/rules_v1_6.yaml",
            "The rules, as data",
            f"{f.rules} rules. Each says when it fires and which clauses it rests on. "
            "A governance reviewer can read them without reading Python.",
        )
        + _box(
            "engine/basis.yaml",
            "Why a rule exists",
            f"{f.basis_entries} entries, each a law, a standard or our own choice, "
            "with the date it was last checked.",
        )
        + "</div>"
        + arrow
        + _box(
            "engine/rules.py",
            "The engine",
            "Every rule is tested against the question. Every rule that fires adds "
            "its clauses. The most severe status wins. No model is consulted at any "
            "point.",
            modifier="engine",
        )
        + arrow
        + _box(
            "",
            "One verdict",
            "A status, the clauses behind it in the policy's own words, what is at "
            "stake, what to do next, and the law or standard the rule answers to.",
            modifier="verdict",
        )
        + arrow
        + f'<ul class="cu-chips cu-flow__pages">{pages}</ul>'
        + '<p class="cu-meta cu-flow__caption">Five pages read the same engine, so '
        "a square on the Matrix cannot disagree with the Check page.</p>"
        "</div>"
    )


# --------------------------------------------------------------------------
# By the numbers
# --------------------------------------------------------------------------


def _render_figures() -> None:
    f = figures(VERSION)
    st.markdown("## By the numbers")
    tiles = (
        (f.clauses, "clauses in the policy"),
        (f.rules, "rules, each citing its clause"),
        (f.clauses_cited, "clauses a rule rests on"),
        (f.scenarios, "scenarios with an agreed verdict"),
        (f.versions, "policy versions encoded and compared"),
        (f.basis_entries, "crosswalk entries"),
        (f.sources, "laws and standards cited"),
        (f.test_functions, "test functions; one checks every citation"),
    )
    html = "".join(
        f'<div class="cu-figure"><span class="cu-figure__n">{n}</span>'
        f'<span class="cu-figure__l">{escape(label)}</span></div>'
        for n, label in tiles
    )
    st.html(f'<div class="cu-figures">{html}</div>')
    st.html(
        '<p class="cu-meta">Counted from the files at the moment this page loaded, '
        "not typed in.</p>"
    )


# --------------------------------------------------------------------------
# A rule, verbatim
# --------------------------------------------------------------------------


def _render_rule() -> None:
    st.markdown("## A rule, as it is written")
    st.html(
        '<p class="cu-hint">This is the whole grammar: field and value pairs, '
        "and <code>all_of</code>, <code>any_of</code>, <code>none_of</code> to "
        "combine them. There is no <code>eval()</code>, so the engine is "
        "deterministic and the rule reads the same to a lawyer and to the "
        "machine.</p>"
    )
    st.code(rule_source(SAMPLE_RULE, VERSION), language="yaml")

    st.html('<p class="cu-label">When more than one rule fires</p>')
    keys = []
    for index, status in enumerate(SEVERITY):
        style = STATUS_STYLES[status]
        keys.append(
            f'<span class="cu-key cu-key--{style.slug}">{escape(style.icon)} '
            f"{escape(style.word)}</span>"
        )
        if index < len(SEVERITY) - 1:
            keys.append('<span class="cu-flow__beats">wins over</span>')
    st.html(f'<div class="cu-keyrow cu-flow__severity">{"".join(keys)}</div>')
    st.html(
        '<p class="cu-clause__text">All of them count. The verdict takes the most '
        "severe status, and every rule that fired contributes its clauses. That is "
        "why asking about webcam emotion detection of staff cites both 6.1, which "
        "prohibits it, and 8.6, which would otherwise have required approval.</p>"
    )


# --------------------------------------------------------------------------
# Guarantees
# --------------------------------------------------------------------------


GUARANTEES: tuple[tuple[str, str], ...] = (
    (
        "The clause you read is the clause in the file",
        "Clause text is never written into the code. A parser slices it out of "
        "the policy markdown, so the app cannot quietly paraphrase a rule.",
    ),
    (
        "A citation that points at nothing fails the build",
        "A test asserts that every clause id used in the rules, the crosswalk "
        "and the page code exists in the parsed policy. Renumber a section and "
        "the suite says which rules broke.",
    ),
    (
        "Each version is read against its own text",
        "Clause numbers mean different things between versions: v1.0's 7.3 is the "
        "special-category clause, v1.5's 7.3 is minimisation. Each ruleset is "
        "checked only against the policy it encodes.",
    ),
    (
        "The law explains, it never decides",
        "A verdict never changes with jurisdiction, because clause 1.2 already "
        "applies whichever requirement is stricter. The backing layer says why a "
        "rule exists, not what you may do.",
    ),
)


def _render_guarantees() -> None:
    st.markdown("## What you can check")
    for title, body in GUARANTEES:
        st.html(
            f'<p class="cu-limit">{escape(title)}</p><p class="cu-clause__text">{escape(body)}</p>'
        )


# --------------------------------------------------------------------------
# The crosswalk
# --------------------------------------------------------------------------


def _render_crosswalk() -> None:
    rows = crosswalk(VERSION)
    counts = basis_counts()
    st.markdown("## Where the law sits behind the policy")
    st.html(
        f'<p class="cu-hint">{len(rows)} entries over {len({r.clause for r in rows})} '
        f"clauses: {counts[BasisType.LAW]} from law, {counts[BasisType.STANDARD]} from a "
        f"standard, {counts[BasisType.OUR_CHOICE]} the organization's own choice. The "
        "list is fixed and dated. Nothing is added when a new law appears; a gap goes "
        "on the Limits page instead.</p>"
    )

    body = []
    last_clause = None
    for row in rows:
        entry = row.entry
        first = row.clause != last_clause
        last_clause = row.clause
        clause_cell = (
            f'<span class="cu-xwalk__id">{escape(row.clause)}</span>'
            f'<span class="cu-xwalk__where">{escape(row.where)}</span>'
            if first
            else ""
        )
        meta = " · ".join(part for part in (entry.jurisdiction, entry.status) if part)
        meta_html = f'<span class="cu-xwalk__where">{escape(meta)}</span>' if meta else ""
        row_class = "cu-xwalk__first" if first else ""
        body.append(
            f'<tr class="{row_class}">'
            f"<td>{clause_cell}</td>"
            f'<td class="cu-xwalk__type">{BASIS_ICONS[entry.type.value]} '
            f"{escape(BASIS_LABELS[entry.type.value])}</td>"
            f"<td>{escape(entry.source)}{meta_html}</td>"
            f'<td class="cu-xwalk__date">{escape(entry.checked.isoformat())}</td>'
            "</tr>"
        )
    st.html(
        '<div class="cu-xwalk-wrap"><table class="cu-xwalk">'
        "<thead><tr><th>Clause</th><th>Backing</th><th>Source</th><th>Checked</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )

    whole = whole_policy_basis()
    if whole:
        sources = "; ".join(entry.source for entry in whole)
        st.html(
            f'<p class="cu-meta">{escape(describe_pattern("*", VERSION))}: {escape(sources)}.</p>'
        )

    beyond = beyond_the_law()
    if beyond:
        chips = "".join(
            f'<li class="cu-chip">{escape(clause)} · {escape(where)}</li>'
            for clause, where in ((c, describe_pattern(c, VERSION)) for c in beyond)
        )
        st.html(
            '<p class="cu-label">Where the policy asks for more than the law</p>'
            f'<ul class="cu-chips">{chips}</ul>'
            '<p class="cu-clause__text">A clause backed by both a law and our own '
            "choice is one where the law sets a floor and the policy stands above it. "
            "Drawing that line is what the crosswalk is for, and it only becomes "
            "visible when the law moves.</p>"
        )


# --------------------------------------------------------------------------
# Coverage
# --------------------------------------------------------------------------


def _render_coverage() -> None:
    rows = coverage(VERSION)
    f = figures(VERSION)
    st.markdown("## What the rules reach, and what they do not")
    st.html(
        f'<p class="cu-hint">{f.clauses_cited} of {f.clauses} clauses are cited by at '
        "least one rule. The rest are not missing from the rules: they describe "
        "roles, procurement, incidents and records, which are process rather than "
        "a decision anyone takes at a desk. The tool answers the second kind of "
        "question only, and this table shows where that line falls.</p>"
    )
    with st.expander("Coverage by section"):
        body = []
        for row in rows:
            width = round(row.share * 100)
            label = f"Part {row.part} · " if row.part else ""
            body.append(
                "<tr>"
                f'<td><span class="cu-xwalk__id">{escape(row.section)}</span>'
                f'<span class="cu-xwalk__where">{escape(label + row.title)}</span></td>'
                f'<td class="cu-cover__n">{row.cited} / {row.clauses}</td>'
                f'<td><div class="cu-cover__bar"><div class="cu-cover__fill" '
                f'style="width:{width}%"></div></div></td>'
                "</tr>"
            )
        st.html(
            '<div class="cu-xwalk-wrap"><table class="cu-xwalk cu-cover">'
            "<thead><tr><th>Section</th><th>Cited</th><th></th></tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table></div>"
        )


# --------------------------------------------------------------------------
# Adoption
# --------------------------------------------------------------------------


def _render_adopt() -> None:
    st.markdown("## Run your own policy through it")
    st.html(
        '<p class="cu-hint">The app knows nothing about this particular policy. It '
        "knows a document shape and a rule grammar.</p>"
        '<ol class="cu-steps">'
        "<li>Drop your policy in as markdown, with numbered clauses under numbered "
        "section headings. The parser reads that shape and nothing else.</li>"
        "<li>Write the rules as YAML. Each one names the conditions it fires on and "
        "the clause ids it rests on.</li>"
        "<li>Run the tests. The integrity test fails on any clause id that does not "
        "exist in your document, which is the whole point of writing it down.</li>"
        "<li>Add your legal crosswalk, dated. The pages need no change.</li>"
        "</ol>"
        f'<p class="cu-meta">Source, rules and tests: <a href="{REPO}">{escape(REPO_LABEL)}</a>. '
        "The Limits page lists what this approach cannot tell you.</p>"
    )


def main() -> None:
    inject_styles()
    page_header(
        "How it works",
        "A policy turned into a decision engine you can audit. Rules as data, every "
        "verdict citing its clause, and no model in the decision path.",
    )
    _render_flow()
    _render_figures()
    _render_rule()
    _render_guarantees()
    _render_crosswalk()
    _render_coverage()
    _render_adopt()
    render_footer(VERSION)


main()
