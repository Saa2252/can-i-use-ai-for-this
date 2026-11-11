"""What the tool tiers mean, for pages that show the grid or the tool picker.

B.1.2 states the nine Tier A conditions as one semicolon-separated sentence.
That reads badly on a phone, so this module splits that sentence into its
items. Splitting is not paraphrasing: every item is the clause's own words,
sliced out of the parsed policy, so a reworded policy changes this list
instead of leaving a stale copy behind (BUILD_SPEC 0.5).
"""

from __future__ import annotations

import re

from engine.policy_parser import load_policy

#: The run-in list in B.1.2 begins after this, and ends at the sentence stop.
_LIST_START = re.compile(r"only with all of:\s*(?P<items>[^.]+)\.", re.IGNORECASE)


def tier_a_conditions(version: str = "v1_5") -> list[str]:
    """The Tier A conditions from B.1.2, one per item, in the policy's words.

    Returns an empty list if B.1.2 no longer has that shape, so a caller can
    fall back to showing the clause whole rather than printing nothing.
    """
    clause = load_policy(version).clauses.get("B.1.2")
    if clause is None:
        return []

    match = _LIST_START.search(clause.text)
    if match is None:
        return []

    items = []
    for raw in match.group("items").split(";"):
        item = raw.strip()
        # The clause writes the final item as "and advance notice ...".
        item = re.sub(r"^and\s+", "", item)
        if item:
            items.append(item)
    return items


#: One line per tier. These are glosses, not policy text: the pages that use
#: them say so, and render the clauses themselves alongside. The Tier C line
#: is the glossary's own sentence, and the Check page's tool help uses it too.
TIER_GLOSS: tuple[tuple[str, str], ...] = (
    ("Tier A", "Assessed and approved. Meets every condition in B.1.2:"),
    ("Tier B", "Vetted, but missing one or more of those conditions."),
    ("Tier C", "Anything not assessed, including personal accounts."),
)

#: The clauses that define the tiers, shown in full on request.
TIER_CLAUSES = ["B.1.1", "B.1.2", "B.1.3"]
