"""The model behind the 7.1 grid: what each square is, and what it says.

Kept out of the page so it can be tested without rendering one, and so the
Matrix and anything else that shows the grid cannot end up with two ideas of
what a square means. Nothing here decides anything: every answer comes from
`evaluate`, which is what stops the grid drifting from the Check page.
"""

from __future__ import annotations

from engine.models import Activity, DataClass, Host, Inputs, Status, Tool
from engine.policy_parser import load_policy
from engine.rules import evaluate
from engine.scenarios import scenario

VERSION = "v1_6"

GRID_TIERS: tuple[Tool, ...] = (Tool.TIER_A, Tool.TIER_B, Tool.TIER_C)

#: What a cell says. Not the policy's own word — 7.1 writes "Yes", "No",
#: "Never" and "Approved use case only", and two different "No"s mean two
#: different things, one with a route and one without. The detail card still
#: quotes 7.1 verbatim; the grid says what to do about it.
CELL_LABELS: dict[Status, str] = {
    Status.ALLOWED: "Yes",
    Status.NEEDS_APPROVAL: "With approval",
    Status.NOT_PERMITTED: "Use a safer tool",
    Status.PROHIBITED: "Never",
}

#: Column headings in the words a colleague would use, with the policy's term
#: underneath, because the term is what the clauses and the Matrix will say.
TOOL_COLUMNS: tuple[tuple[Tool, str, str], ...] = (
    (Tool.TIER_A, "Company-approved AI", "Tier A"),
    (Tool.TIER_B, "Vetted, with gaps", "Tier B"),
    (Tool.TIER_C, "Personal or free AI", "Tier C"),
)

#: Row headings: the plain name, the policy's term where it differs, and a
#: short example. The examples are illustrative, like the cell examples
#: below: 7.4 defines Restricted and 6.3 names what a secret is, so those two
#: are the clause's own cases, while Public, Internal and Confidential are
#: set by the organization's own Data Classification Standard, which 7.5
#: points to rather than restates. The key under the grid says so and cites
#: the clauses.
ROW_LABELS: dict[DataClass, tuple[str, str, str]] = {
    DataClass.PUBLIC: ("Public", "", "Anything already published"),
    DataClass.INTERNAL: ("Internal", "", "A memo, an org chart"),
    DataClass.CONFIDENTIAL: ("Confidential", "", "A client contract, an HR file"),
    DataClass.RESTRICTED: ("Sensitive personal", "Restricted", "Health, biometric or ID data"),
    DataClass.SECRETS: ("Passwords & keys", "Secrets", "An API key, a token"),
}

#: The three hosts B.1.3 distinguishes, behind the Self-hosted toggle. Where a
#: model runs decides its tier, so one column could not answer it.
HOSTS: tuple[tuple[Host, str], ...] = (
    (Host.ORG_CLOUD, "Our servers or cloud"),
    (Host.MANAGED_LAPTOP, "A managed laptop"),
    (Host.PERSONAL_DEVICE, "A personal device"),
)

#: Illustrative examples, not policy text. They show what each cell looks like
#: in practice; several are the golden scenarios of BUILD_SPEC 6.
EXAMPLES: dict[tuple[DataClass, Tool], str] = {
    (DataClass.PUBLIC, Tool.TIER_A): "Summarising your own published press release.",
    (DataClass.PUBLIC, Tool.TIER_B): "The same press release in a vetted Tier B tool.",
    (DataClass.PUBLIC, Tool.TIER_C): "Summarising a public news article in personal ChatGPT.",
    (DataClass.INTERNAL, Tool.TIER_A): "Drafting an internal memo in the approved tool.",
    (DataClass.INTERNAL, Tool.TIER_B): "Tidying an internal process note in a Tier B tool.",
    (DataClass.INTERNAL, Tool.TIER_C): "Pasting the internal org chart into a personal account.",
    (DataClass.CONFIDENTIAL, Tool.TIER_A): "Drafting a client deliverable in the approved tool.",
    (DataClass.CONFIDENTIAL, Tool.TIER_B): "A document naming a client, in a Tier B tool.",
    (DataClass.CONFIDENTIAL, Tool.TIER_C): "Pasting a client contract into personal ChatGPT.",
    (DataClass.RESTRICTED, Tool.TIER_A): "Uploading sick-leave notes for a summary.",
    (DataClass.RESTRICTED, Tool.TIER_B): "Health data in a vetted but not Tier A tool.",
    (DataClass.RESTRICTED, Tool.TIER_C): "Health data in a personal AI account.",
    (DataClass.SECRETS, Tool.TIER_A): "Pasting an API key into the approved tool to debug.",
    (DataClass.SECRETS, Tool.TIER_B): "An API key in a Tier B tool.",
    (DataClass.SECRETS, Tool.TIER_C): "An API key in a personal AI account.",
}

_SEVERITY: dict[Status, int] = {
    Status.ALLOWED: 0,
    Status.NEEDS_APPROVAL: 1,
    Status.NOT_PERMITTED: 2,
    Status.PROHIBITED: 3,
}


# --------------------------------------------------------------------------
# The engine behind every cell
# --------------------------------------------------------------------------


def cell_inputs(data_class: DataClass, tool: Tool, host: Host | None = None) -> Inputs:
    """The neutral question each cell asks: this data, this tool, plain drafting."""
    return Inputs(data_class=data_class, tool=tool, activity=Activity.DRAFTING, host=host)


def cell_status(data_class: DataClass, tool: Tool, host: Host | None = None) -> Status:
    return evaluate(cell_inputs(data_class, tool, host), VERSION).status


def policy_word(data_class: DataClass, tool: Tool) -> str:
    """The policy's own word for this cell of the 7.1 table."""
    table = load_policy(VERSION).table("7.1")
    words = {row[0]: row[1:] for row in table.rows}
    return words.get(data_class.value, ("", "", ""))[GRID_TIERS.index(tool)]


def safer_route(data_class: DataClass, tool: Tool) -> tuple[Tool, Status] | None:
    """The nearest cell in the same row with a better answer, or None.

    Computed, never written down: each candidate goes through `evaluate` the
    way the cell itself did. Where a row has an allowed cell that is the
    route; where it has none — Restricted, and Secrets, which has nothing
    anywhere — the least severe cell is offered instead, and only if it is
    actually better than where you are.
    """
    statuses = {candidate: cell_status(data_class, candidate) for candidate in GRID_TIERS}
    here = _SEVERITY[statuses[tool]]
    if here == 0:
        return None

    allowed = [candidate for candidate in GRID_TIERS if statuses[candidate] is Status.ALLOWED]
    if allowed:
        return allowed[0], Status.ALLOWED

    best = min(GRID_TIERS, key=lambda candidate: _SEVERITY[statuses[candidate]])
    if _SEVERITY[statuses[best]] < here:
        return best, statuses[best]
    return None


#: Eight everyday things, each one a golden scenario's data. The phrase is
#: what fits on a chip; the scenario supplies the class, so the right answer
#: is computed rather than recorded here.
ITEMS: tuple[tuple[int, str], ...] = (
    (1, "A public news article"),
    (3, "An internal memo"),
    (4, "An email naming colleagues"),
    (18, "Notes from a team meeting"),
    (2, "A client contract"),
    (15, "A document naming a client"),
    (7, "A sick-leave note"),
    (12, "An API key"),
)


def item_class(number: int) -> DataClass:
    return scenario(number).inputs.data_class


def best_tools(data_class: DataClass) -> list[Tool]:
    return [tool for tool in GRID_TIERS if cell_status(data_class, tool) is Status.ALLOWED]
