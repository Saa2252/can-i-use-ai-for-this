"""Parse a policy markdown file into clauses, tables and the staff summary.

The policy text is the source of truth (BUILD_SPEC 0.5), so this module only
ever slices the file. It never rewrites or summarises a clause.

Two document shapes are supported, because v1.0 predates the Part A-D
restructure introduced in v1.1:

======================  =========================  ============================
                        v1.0                       v1.5
======================  =========================  ============================
Part headers            none                       ``# Part A:`` ... ``# Part D:``
Annexes                 ``# Sector annexes`` +     ``# Part D`` +
                        ``## Annex: ...``          ``## D.1 ...``
Clause ids              ``7.4`` only               ``7.4``, ``B.1.3``, ``C.2``, ``FS.1``
Front matter            bold key/value lines       a markdown table
======================  =========================  ============================
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from engine.models import Clause, Policy, StaffSummary, Table

POLICY_DIR = Path(__file__).resolve().parent.parent / "policy"

VERSION_FILES: dict[str, str] = {
    "v1_0": "AI_Acceptable_Use_Policy_v1.0.md",
    "v1_4": "AI_Acceptable_Use_Policy_v1.4.md",
    "v1_5": "AI_Acceptable_Use_Policy_v1.5.md",
}

# A citable clause id. Deliberately strict: it has to reject bold prose such as
# "**Always**" in the staff summary and "**Version:**" in v1.0's front matter.
CLAUSE_ID_RE = re.compile(
    r"""^(?:
        \d{1,2}\.\d{1,2}            # Part A:            6.3, 11.3
      | [BC]\.\d{1,2}(?:\.\d{1,2})? # Parts B and C:      B.1.3, C.4.2
      | [A-Z]{2,3}\.\d{1,2}         # Part D annexes:     FS.1, INS.1, HC.3
    )$""",
    re.VERBOSE,
)

_PART_RE = re.compile(r"^#\s+Part\s+([A-Z])\s*:\s*(.*)$")
_SECTOR_ANNEXES_RE = re.compile(r"^#\s+Sector annexes\s*$")
_SECTION_RE = re.compile(r"^##\s+(.*?)\s*$")
_CLAUSE_RE = re.compile(r"^\*\*([^*]+?)\*\*\s*(.*)$")
_HRULE_RE = re.compile(r"^-{3,}\s*$")

_SECTION_ID_PATTERNS = (
    re.compile(r"^(\d{1,2})\.\s+(.*)$"),  # "7. Data rules"
    re.compile(r"^([BC]\.\d{1,2})\s+(.*)$"),  # "B.1 Tool tiers", "C.2 Action limits"
    re.compile(r"^(D\.\d{1,2})\s+(.*)$"),  # "D.1 Financial services"
)

# Sections that hold no clauses and must be kept out of clause parsing.
_NON_CLAUSE_PREFIXES = ("Staff summary", "Changes in version")

_CHANGELOG_RE = re.compile(r"^Changes in version ([\d.]+)\s*$")


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


@lru_cache(maxsize=8)
def load_policy(version: str = "v1_5") -> Policy:
    """Parse and cache a policy version.

    `lru_cache` keeps the engine importable without Streamlit; the app layer
    wraps this in `st.cache_data` (BUILD_SPEC 4).
    """
    if version not in VERSION_FILES:
        raise KeyError(f"unknown policy version {version!r}; have {sorted(VERSION_FILES)}")
    path = POLICY_DIR / VERSION_FILES[version]
    return parse_policy(path.read_text(encoding="utf-8"), version=version)


def parse_policy(text: str, *, version: str) -> Policy:
    """Parse policy markdown into a `Policy`."""
    lines = [line.rstrip() for line in text.splitlines()]
    sections, preamble = _split_sections(lines)

    clauses: dict[str, Clause] = {}
    tables: dict[str, list[Table]] = {}
    staff_summary = StaffSummary()
    changelogs: dict[str, Table] = {}

    for section in sections:
        if section.title.startswith(_NON_CLAUSE_PREFIXES):
            if section.title.startswith("Staff summary"):
                staff_summary = _parse_staff_summary(section.lines)
            elif match := _CHANGELOG_RE.match(section.title):
                found = _parse_tables(section.lines)
                if found:
                    changelogs[match.group(1)] = found[0]
            continue

        found = _parse_clauses(section)
        if found:
            for clause in found:
                clauses[clause.id] = clause
                found_tables = _parse_tables(clause.text.splitlines())
                if found_tables:
                    tables.setdefault(clause.id, []).extend(found_tables)
        elif section.id:
            # A leaf section: no numbered sub-clauses, so the section id is
            # itself citable (B.3, B.4, B.8-B.10, C.2, C.3, and Section 4).
            body = _strip_body(section.lines)
            if body:
                clauses[section.id] = Clause(
                    id=section.id,
                    part=section.part,
                    section=section.id,
                    section_title=section.title,
                    text=body,
                )

        section_tables = _parse_tables(section.lines)
        if section_tables and section.id:
            existing = tables.setdefault(section.id, [])
            for table in section_tables:
                if table not in existing:
                    existing.append(table)

    return Policy(
        version=version,
        clauses=clauses,
        tables=tables,
        staff_summary=staff_summary,
        changelogs=changelogs,
        front_matter=_parse_front_matter(preamble),
    )


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------


class _Section:
    __slots__ = ("id", "lines", "part", "title")

    def __init__(self, *, id: str | None, title: str, part: str | None) -> None:
        self.id = id
        self.title = title
        self.part = part
        self.lines: list[str] = []


def _split_sections(lines: list[str]) -> tuple[list[_Section], list[str]]:
    """Walk the file once, grouping lines under their `##` heading.

    Also returns the preamble: everything before the first `##`, which is
    where the document's own header fields live.
    """
    sections: list[_Section] = []
    current: _Section | None = None
    part: str | None = None
    preamble: list[str] = []

    for line in lines:
        if part_match := _PART_RE.match(line):
            part = part_match.group(1)
            current = None
            continue
        if _SECTOR_ANNEXES_RE.match(line):
            # v1.0's annexes are Part D's ancestor.
            part = "D"
            current = None
            continue
        if line.startswith("# "):
            # The document title, or any other top-level heading.
            current = None
            continue
        if section_match := _SECTION_RE.match(line):
            heading = section_match.group(1)
            section_id, title = _section_id_and_title(heading)
            current = _Section(id=section_id, title=title, part=part)
            sections.append(current)
            continue
        if current is not None:
            current.lines.append(line)
        elif not sections:
            preamble.append(line)

    return sections, preamble


def _section_id_and_title(heading: str) -> tuple[str | None, str]:
    for pattern in _SECTION_ID_PATTERNS:
        if match := pattern.match(heading):
            return match.group(1), match.group(2).strip()
    if match := re.match(r"^Annex:\s*(.*)$", heading):
        return None, match.group(1).strip()
    return None, heading.strip()


# --------------------------------------------------------------------------
# Clauses
# --------------------------------------------------------------------------


def _parse_clauses(section: _Section) -> list[Clause]:
    """Extract every `**id** text` clause in a section."""
    marker_positions: list[tuple[int, str, str]] = []
    for index, line in enumerate(section.lines):
        match = _CLAUSE_RE.match(line)
        if match and CLAUSE_ID_RE.match(match.group(1).strip()):
            marker_positions.append((index, match.group(1).strip(), match.group(2)))

    clauses: list[Clause] = []
    for position, (start, clause_id, first_line) in enumerate(marker_positions):
        hard_stop = (
            marker_positions[position + 1][0]
            if position + 1 < len(marker_positions)
            else len(section.lines)
        )
        body = _collect_clause_body(section.lines, start + 1, hard_stop)
        text = "\n".join([first_line, *body]).strip()
        clauses.append(
            Clause(
                id=clause_id,
                part=section.part,
                section=section.id,
                section_title=section.title,
                text=text,
            )
        )
    return clauses


def _collect_clause_body(lines: list[str], start: int, hard_stop: int) -> list[str]:
    """Collect a clause's continuation lines.

    A clause keeps a bullet list or table that follows it, including across a
    single blank line, because 10.2, B.1.3 and 7.1 all carry one. It stops at a
    blank line followed by ordinary prose, which is what keeps B.1.3 from
    swallowing the "Self-hosting removes vendor risk..." paragraph that follows
    its bullets.
    """
    body: list[str] = []
    index = start
    while index < hard_stop:
        line = lines[index]
        if _HRULE_RE.match(line):
            break
        if line.strip():
            body.append(line)
            index += 1
            continue

        look = index
        while look < hard_stop and not lines[look].strip():
            look += 1
        if look >= hard_stop:
            break
        nxt = lines[look].lstrip()
        if _HRULE_RE.match(lines[look]) or not nxt.startswith(("-", "|", "*")):
            break
        body.extend(lines[index:look])
        index = look

    while body and not body[-1].strip():
        body.pop()
    return body


def _strip_body(lines: list[str]) -> str:
    """A leaf section's body, without horizontal rules or blank padding."""
    kept = [line for line in lines if not _HRULE_RE.match(line)]
    return "\n".join(kept).strip()


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------


def _parse_tables(lines: list[str]) -> list[Table]:
    """Parse every markdown table in a run of lines."""
    tables: list[Table] = []
    index = 0
    while index < len(lines):
        if not lines[index].lstrip().startswith("|"):
            index += 1
            continue
        block: list[str] = []
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            block.append(lines[index].strip())
            index += 1
        if table := _parse_table_block(block):
            tables.append(table)
    return tables


def _parse_table_block(block: list[str]) -> Table | None:
    if len(block) < 2:
        return None
    headers = _split_row(block[0])
    if not re.fullmatch(r"\|[\s:|-]+\|", block[1]):
        return None
    rows = [_split_row(line) for line in block[2:]]
    return Table(headers=headers, rows=rows)


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


# --------------------------------------------------------------------------
# Staff summary
# --------------------------------------------------------------------------


_FRONT_MATTER_BOLD_RE = re.compile(r"^\*\*([^*:]+):\*\*\s*(.*)$")


def _parse_front_matter(lines: list[str]) -> dict[str, str]:
    """The document header, from either shape.

    v1.5 states it as a Field/Value table; v1.0 as bold `**Key:** value`
    lines. Several values are template placeholders such as
    `[Organization name]`, which the policy page marks as such.
    """
    for table in _parse_tables(lines):
        if [h.lower() for h in table.headers] == ["field", "value"]:
            return {row[0]: row[1] for row in table.rows if len(row) >= 2}

    fields: dict[str, str] = {}
    for line in lines:
        if match := _FRONT_MATTER_BOLD_RE.match(line.strip()):
            fields[match.group(1).strip()] = match.group(2).strip()
    return fields


_SUMMARY_BUCKETS = {
    "Always": "always",
    "Ask first": "ask_first",
    "Never": "never",
}


def _parse_staff_summary(lines: list[str]) -> StaffSummary:
    """Parse the Always / Ask first / Never lists (absent in v1.0)."""
    buckets: dict[str, list[str]] = {name: [] for name in _SUMMARY_BUCKETS.values()}
    current: str | None = None
    footer = ""

    for line in lines:
        stripped = line.strip()
        if match := re.match(r"^\*\*([^*]+)\*\*", stripped):
            label = match.group(1).strip()
            current = next(
                (key for name, key in _SUMMARY_BUCKETS.items() if label.startswith(name)),
                None,
            )
            continue
        if current and stripped.startswith("- "):
            buckets[current].append(stripped[2:].strip())
        elif stripped.startswith("Questions:"):
            footer = stripped

    return StaffSummary(**buckets, footer=footer)
