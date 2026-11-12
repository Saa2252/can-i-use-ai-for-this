"""What this policy and this tool do not cover.

Every other page answers a question. This one lists the questions it cannot
answer, which is the part of a governance artefact that is usually missing.

Three kinds of limit, kept apart because they are not the same thing:
gaps that were found and closed, gaps that are open, and limits that are
structural and will not close.
"""

from __future__ import annotations

import streamlit as st

from app.components.clause_drawer import render_clause_drawer
from app.components.footer import render_footer
from app.components.shell import escape, inject_styles, page_header
from engine.rules import load_basis

VERSION = "v1_6"

#: Found by reading v1.5 against the adopted Digital Omnibus on AI in November
#: 2026, and closed in v1.6. Each names the clause that closed it, so the claim
#: is checkable rather than asserted.
CLOSED: tuple[dict[str, object], ...] = (
    {
        "title": "Becoming a provider without building anything",
        "gap": (
            "v1.5 said the organization stays accountable for vendor AI, which is "
            "true but is about accountability, not legal role. It never said that "
            "putting our name on a high-risk system, substantially modifying one, "
            "or repurposing one so it becomes high-risk converts us from the user "
            "of that system into its provider, with a far wider duty set that a "
            "contract cannot hand back."
        ),
        "why": (
            "Nobody has to build anything to trip this. Fine-tuning a vendor's "
            "screening model, or white-labelling a chatbot, feels like ordinary "
            "configuration and is not."
        ),
        "clauses": ["2.6", "8.1"],
    },
    {
        "title": "Telling the staff is not telling their representatives",
        "gap": (
            "v1.5 told individuals when AI was used on them, and told staff what "
            "was monitored. Neither is the duty to inform workers' representatives "
            "before high-risk AI is put into use at work, which is a separate step "
            "owed to a different party."
        ),
        "why": (
            "In several jurisdictions that body can delay or block a deployment, "
            "so finding out about it after the tool is bought is expensive."
        ),
        "clauses": ["10.5", "HR.6"],
    },
    {
        "title": "Doing the assessment without filing the named one",
        "gap": (
            "The B.3 rubric sizes an impact assessment well. It did not say that "
            "for some uses the law names a specific assessment, and that producing "
            "an excellent assessment of your own does not satisfy a requirement "
            "for that named one."
        ),
        "why": (
            "Credit scoring, insurance pricing, public services and public bodies "
            "are exactly the uses this policy's own annexes cover, so the "
            "obligation was in scope while the name was absent."
        ),
        "clauses": ["8.12"],
    },
    {
        "title": "Rights that stop at the system of record",
        "gap": (
            "v1.5 was careful about retention everywhere, and said nothing about "
            "what happens when a person asks to see or delete their data. Agent "
            "memory, meeting transcripts and derived indexes are precisely where "
            "personal data ends up and is hardest to find."
        ),
        "why": "A deletion request that misses the agent's memory has not been honoured.",
        "clauses": ["7.7", "C.4.2"],
    },
)

#: Open. Recorded rather than resolved, because resolving them means choosing
#: a reading of the policy, which is the organization's call and not this app's.
OPEN: tuple[dict[str, object], ...] = (
    {
        "title": "A self-hosted model on a personal device",
        "question": (
            "Is it Tier C, which makes it prohibited, or is it outside the tier "
            "system, which makes it not permitted with a route back?"
        ),
        "matters": (
            "The two readings give a user opposite advice about whether any "
            "compliant path exists. This app takes the second reading, and the "
            "verdict card says so."
        ),
        "clauses": ["2.3", "6.7", "B.1.3"],
    },
    {
        "title": "Three of the five data classes are defined elsewhere",
        "question": (
            "7.4 defines Restricted. Public, Internal and Confidential are set by "
            "the organization's own Data Classification Standard, which this "
            "policy points to and does not contain."
        ),
        "matters": (
            "An adopter has to map them to their own scheme, and this tool cannot "
            "check that mapping. It is a real dependency of a model policy, not an "
            "oversight, but it is load-bearing."
        ),
        "clauses": ["7.4", "7.5", "B.2.3"],
    },
    {
        "title": "The arguments behind the revisions are reconstructed",
        "question": (
            "The Changes page sets out four points that could have gone the other "
            "way. They come from the policy text and its change log."
        ),
        "matters": (
            "No transcript of the actual review exists, so those pages show the "
            "two readings and where the decision is recorded, never who argued "
            "what. Treat them as reconstruction."
        ),
        "clauses": [],
    },
)

#: Structural. These do not close with another revision.
STRUCTURAL: tuple[tuple[str, str], ...] = (
    (
        "It is a model policy, not an adopted one",
        "No organization has approved this. The committees, roles and service "
        "targets describe a shape that works, not one that has been run. Adapt it "
        "with counsel before it governs anything.",
    ),
    (
        "The legal layer explains, it never decides",
        "A verdict never changes with jurisdiction, because 1.2 already applies "
        "whichever requirement is stricter. The badges say why a rule exists. They "
        "are not advice about your obligations.",
    ),
    (
        "The crosswalk is a fixed list, not a survey",
        "It holds only the entries it was seeded with. Nothing is added when a new "
        "law appears; a gap goes on this page instead. So absence here is not "
        "evidence that nothing applies.",
    ),
    (
        "Each ruleset is a reading of its policy",
        "Every rule cites its clause so the reading can be checked. That is the "
        "point of the citation, and the reason to check it rather than trust it.",
    ),
)


def _render_closed() -> None:
    st.markdown("## Found in review, and closed")
    st.html(
        '<p class="cu-hint">v1.5 was read against the adopted Digital Omnibus on '
        "AI in November 2026. These four gaps were procedural: the policy did the "
        "thinking and did not name the procedure that carries it. v1.6 closed "
        "them, and changed no verdict in doing so.</p>"
    )
    for item in CLOSED:
        with st.expander(str(item["title"])):
            st.html(
                f'<p class="cu-label">What was missing</p>'
                f'<p class="cu-clause__text">{escape(str(item["gap"]))}</p>'
                f'<p class="cu-label">Why it matters</p>'
                f'<p class="cu-route">{escape(str(item["why"]))}</p>'
            )
            clauses = list(item["clauses"])  # type: ignore[arg-type]
            if clauses:
                render_clause_drawer(clauses, VERSION, label="The clauses that close it")


def _render_open() -> None:
    st.markdown("## Still open")
    st.html(
        '<p class="cu-hint">Recorded rather than resolved. Each needs a reading of '
        "the policy to settle, and that is the adopting organization's call.</p>"
    )
    for item in OPEN:
        with st.expander(str(item["title"])):
            st.html(
                f'<p class="cu-clause__text">{escape(str(item["question"]))}</p>'
                f'<p class="cu-label">Why it matters</p>'
                f'<p class="cu-route">{escape(str(item["matters"]))}</p>'
            )
            clauses = list(item["clauses"])  # type: ignore[arg-type]
            if clauses:
                render_clause_drawer(clauses, VERSION, label="The clauses this turns on")


def _render_structural() -> None:
    st.markdown("## Limits that do not close")
    for title, body in STRUCTURAL:
        st.html(
            f'<p class="cu-limit">{escape(title)}</p><p class="cu-clause__text">{escape(body)}</p>',
        )


def _render_checked() -> None:
    """When the legal layer was last read, straight from the entries."""
    dates = sorted({str(entry.checked) for entry in load_basis()})
    st.html(
        f'<p class="cu-meta">Legal citations last verified: {escape(", ".join(dates))}. '
        "An entry older than 90 days carries a re-check tag on the verdict card.</p>"
    )


def main() -> None:
    inject_styles()
    page_header(
        "What this does not cover",
        "The gaps found, the questions left open, and the limits that stay.",
    )
    _render_closed()
    _render_open()
    _render_structural()
    _render_checked()
    render_footer(VERSION)


main()
