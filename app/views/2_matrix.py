"""The data class x tool tier grid (BUILD_SPEC 9.2).

Every cell is computed by the rules engine, not transcribed from the policy,
so the grid cannot drift from the verdicts the Check page gives. A test
asserts the generated grid still agrees with the parsed 7.1 table.

The grid is the answer on this page: fifteen verdicts are on screen at once,
which is why nothing is selected on arrival. Everything that reacts to a
selection — the detail panel, the thick outline, the bottom sheet on a phone
— is a second layer over an answer that is already there.

Three things on this page are drawn rather than written, and all three are
generated from `evaluate` for the same reason: a cell's colour, the icon in
it and the staircase along the frontier would otherwise be a second opinion
about the policy, kept by hand, free to drift.
"""

from __future__ import annotations

import streamlit as st

from app.components.basis_badges import render_basis_row
from app.components.clause_drawer import render_citations
from app.components.footer import render_footer
from app.components.grid import (
    CELL_LABELS,
    EXAMPLES,
    GRID_TIERS,
    HOSTS,
    ITEMS,
    ROW_LABELS,
    TOOL_COLUMNS,
    best_tools,
    cell_inputs,
    cell_status,
    item_class,
    policy_word,
    safer_route,
)
from app.components.icons import data_uri
from app.components.icons import rule as icon_rule
from app.components.legend import render_data_class_key
from app.components.shell import escape, inject_styles, page_header
from app.components.tiers import render_tier_key
from app.styles.tokens import TOKENS, style_for
from engine.models import DataClass, Status, Tool
from engine.rules import evaluate
from engine.scenarios import scenario

VERSION = "v1_6"

SELECTED = "cu_matrix_cell"
EXPERT = "cu_matrix_view"
SELF_HOSTED = "cu_matrix_selfhosted"
ROW_LENS = "cu_matrix_row_lens"
COLUMN_LENS = "cu_matrix_column_lens"

# --------------------------------------------------------------------------
# Generated CSS: colour, icon, frontier, lens, selection
# --------------------------------------------------------------------------


def _cell_key(data_class: DataClass, tool: Tool) -> str:
    return f"cu_cell_{data_class.value}_{tool.value}"


def _grid_styles(selected: tuple[str, str] | None, row_lens, column_lens, expert: bool) -> str:
    """Every rule the grid needs, written from the verdicts themselves.

    The colour, the icon and the staircase all come out of `evaluate`, so a
    cell cannot look like one answer and open onto another.
    """
    # This page is the one that needs more than the reading measure: a grid
    # beside a detail panel does not fit 720px without truncating every
    # square. Widened only where there is room for it, so the phone layout,
    # where the panel becomes a sheet, is untouched.
    rules: list[str] = [
        "@media (min-width: 1000px){.block-container{max-width:1080px;}}",
    ]
    status = {
        (data_class, tool): cell_status(data_class, tool)
        for data_class in DataClass
        for tool in GRID_TIERS
    }

    for (data_class, tool), cell in status.items():
        slug = style_for(cell).slug
        selector = f".st-key-{_cell_key(data_class, tool)} .stButton button"
        rules.append(
            f"{selector}{{"
            f"background:var(--{slug}-tint);"
            f"border:1px solid var(--{slug});"
            f"color:var(--text);"
            f"background-image:{data_uri(slug, TOKENS[slug])};"
            f"background-repeat:no-repeat;"
            f"background-position:0.5rem center;"
            f"padding-left:2rem;"
            f"text-align:left;"
            f"}}"
        )

        # The frontier: a cell that is allowed and whose neighbour is not
        # carries the step between them. Drawn on the allowed side so the
        # line reads as the edge of what is permitted.
        edges: list[str] = []
        right = GRID_TIERS.index(tool) + 1
        if cell is Status.ALLOWED:
            if right < len(GRID_TIERS) and status[(data_class, GRID_TIERS[right])] is not (
                Status.ALLOWED
            ):
                edges.append("inset -4px 0 0 0 var(--text)")
            below = list(DataClass).index(data_class) + 1
            if below < len(DataClass) and status[(list(DataClass)[below], tool)] is not (
                Status.ALLOWED
            ):
                edges.append("inset 0 -4px 0 0 var(--text)")
        if edges:
            rules.append(f"{selector}{{box-shadow:{','.join(edges)};}}")

        if selected == (data_class.value, tool.value):
            rules.append(f"{selector}{{border-width:3px;font-weight:600;}}")

        dimmed = (row_lens is not None and data_class is not row_lens) or (
            column_lens is not None and tool is not column_lens
        )
        if dimmed:
            rules.append(f"{selector}{{opacity:0.3;}}")

    # The icons on the legend, the self-hosted squares and the detail card.
    # Same drawings as the squares, same source, so one set cannot fall out
    # of step with another.
    for status in Status:
        slug = style_for(status).slug
        rules.append(icon_rule(f".cu-key--{slug} .cu-key__icon", slug, TOKENS[slug], size=15))
        rules.append(
            icon_rule(f".cu-hostcell--{slug} .cu-hostcell__icon", slug, TOKENS[slug], size=16)
        )
        rules.append(icon_rule(f".cu-icon--{slug}", slug, TOKENS[slug], size=22))

    if not expert:
        rules.append(".cu-grid-clauses{display:none;}")

    return "".join(rules)


# --------------------------------------------------------------------------
# The grid
# --------------------------------------------------------------------------


def _select(data_class: DataClass, tool: Tool) -> None:
    st.session_state[SELECTED] = (data_class.value, tool.value)


def _clear_selection() -> None:
    st.session_state[SELECTED] = None


def _render_takeaway() -> None:
    st.html(
        '<p class="cu-takeaway">The more sensitive the data, the more trusted '
        "the tool must be.</p>"
        '<p class="cu-meta">The step line on the grid is where that stops being '
        "true of a tool: everything left of it is allowed outright.</p>"
    )


def _render_legend() -> None:
    """The four answers, above the grid, in the words the cells use."""

    def chip(status: Status) -> str:
        slug = style_for(status).slug
        return (
            f'<span class="cu-key cu-key--{slug}">'
            f'<span class="cu-key__icon"></span>'
            f"{escape(CELL_LABELS[status])}</span>"
        )

    chips = "".join(chip(status) for status in Status)
    st.html(f'<div class="cu-keyrow">{chips}</div>')


def _render_lenses() -> None:
    left, right = st.columns(2, gap="small")
    with left:
        st.selectbox(
            "Where can I use this data?",
            options=[None, *DataClass],
            format_func=lambda value: "Any data" if value is None else ROW_LABELS[value][0],
            key=ROW_LENS,
        )
    with right:
        st.selectbox(
            "What can I put in this tool?",
            options=[None, *GRID_TIERS],
            format_func=lambda value: (
                "Any tool"
                if value is None
                else next(name for tool, name, _ in TOOL_COLUMNS if tool is value)
            ),
            key=COLUMN_LENS,
        )


def _render_grid(expert: bool) -> None:
    # The key puts `.st-key-cu_matrix` on the wrapper, which is what stops the
    # columns stacking at phone width (see app.css).
    with st.container(key="cu_matrix"):
        header = st.columns([1.25, 1, 1, 1], gap="small")
        header[0].html('<p class="cu-grid-head">Data</p>')
        for index, (_tool, plain, term) in enumerate(TOOL_COLUMNS, start=1):
            header[index].html(
                f'<p class="cu-grid-head">{escape(plain)}'
                f'<span class="cu-grid-term">{escape(term)}</span></p>'
            )

        for data_class in DataClass:
            plain, term, example = ROW_LABELS[data_class]
            row = st.columns([1.25, 1, 1, 1], gap="small")
            row[0].html(
                f'<p class="cu-grid-row">{escape(plain)}'
                f"{f'<span class="cu-grid-term">{escape(term)}</span>' if term else ''}"
                f'<span class="cu-grid-eg">{escape(example)}</span></p>'
            )
            for index, (tool, _plain, _term) in enumerate(TOOL_COLUMNS, start=1):
                verdict = evaluate(cell_inputs(data_class, tool), VERSION)
                label = CELL_LABELS[verdict.status]
                if expert and verdict.decisive_clauses:
                    label = f"{label}  {' '.join(verdict.decisive_clauses[:2])}"
                row[index].button(
                    label,
                    key=_cell_key(data_class, tool),
                    on_click=_select,
                    args=(data_class, tool),
                    help=f"7.1 says: {policy_word(data_class, tool)}. "
                    f"{EXAMPLES[(data_class, tool)]}",
                    width="stretch",
                )


def _render_self_hosted() -> None:
    """A model the organization runs itself, where the host decides the tier."""
    st.markdown("### A model we run ourselves")
    st.html(
        '<p class="cu-hint">B.1.3 does not give self-hosting a tier of its own: '
        "where the model runs decides it. Only our own servers or cloud tenancy "
        "can reach Tier A, a managed laptop stops at Tier B, and an unmanaged "
        "device is not a work tool at all (2.3).</p>"
    )
    with st.container(key="cu_matrix_hosts"):
        header = st.columns([1.25, 1, 1, 1], gap="small")
        header[0].html('<p class="cu-grid-head">Data</p>')
        for index, (_host, name) in enumerate(HOSTS, start=1):
            header[index].html(f'<p class="cu-grid-head">{escape(name)}</p>')

        for data_class in DataClass:
            plain, _term, _example = ROW_LABELS[data_class]
            row = st.columns([1.25, 1, 1, 1], gap="small")
            row[0].html(f'<p class="cu-grid-row">{escape(plain)}</p>')
            for index, (host, _name) in enumerate(HOSTS, start=1):
                status = cell_status(data_class, Tool.SELF_HOSTED, host)
                style = style_for(status)
                row[index].html(
                    f'<div class="cu-hostcell cu-hostcell--{style.slug}">'
                    f'<span class="cu-hostcell__icon"></span>'
                    f"{escape(CELL_LABELS[status])}</div>"
                )


# --------------------------------------------------------------------------
# The detail card
# --------------------------------------------------------------------------


def _render_waiting() -> None:
    st.html(
        '<div class="cu-card cu-card--waiting">'
        '<p class="cu-status"><span class="cu-status__icon" aria-hidden="true">?</span>'
        "<span>Tap any square to see why.</span></p>"
        '<p class="cu-subtitle">Every square is worked out by the same rules the '
        "Check page uses, and opens onto the clauses behind it.</p>"
        "</div>"
    )


def _render_detail(data_class: DataClass, tool: Tool, expert: bool) -> None:
    verdict = evaluate(cell_inputs(data_class, tool), VERSION)
    style = style_for(verdict.status)
    plain_row = ROW_LABELS[data_class][0]
    plain_tool = next(name for candidate, name, _ in TOOL_COLUMNS if candidate is tool)
    term = next(t for candidate, _n, t in TOOL_COLUMNS if candidate is tool)

    st.html(
        f'<div class="cu-card cu-card--{style.slug}">'
        f'<p class="cu-status">'
        f'<span class="cu-status__icon cu-status__icon--svg '
        f'cu-icon cu-icon--{style.slug}"></span>'
        f"<span>{escape(CELL_LABELS[verdict.status])}</span></p>"
        f'<p class="cu-subtitle">{escape(plain_row)} data '
        f"&middot; {escape(plain_tool)} ({escape(term)})</p>"
        f'<p class="cu-reason">{escape(verdict.reasons[0] if verdict.reasons else "")}</p>'
        f"</div>"
    )

    st.html(
        '<p class="cu-label">What it means</p>'
        f'<p class="cu-route">7.1 says <strong>{escape(policy_word(data_class, tool))}</strong>. '
        f"{escape(style.subtitle)}</p>"
        '<p class="cu-label">Example</p>'
        f'<p class="cu-stake">{escape(EXAMPLES[(data_class, tool)])}</p>'
    )

    if verdict.why_it_matters:
        st.html(
            '<p class="cu-label">Why it matters</p>'
            f'<p class="cu-stake">{escape(verdict.why_it_matters)}</p>'
        )

    _render_safer_route(data_class, tool, verdict.status)

    render_citations(verdict.decisive_clauses, verdict.clauses, VERSION)
    if expert:
        render_basis_row(verdict.basis)


def _render_safer_route(data_class: DataClass, tool: Tool, status: Status) -> None:
    """Where this data *can* go, found by running the same rules along the row."""
    if status is Status.ALLOWED:
        return

    route = safer_route(data_class, tool)
    if route is None:
        st.html(
            '<p class="cu-label">Safer route</p>'
            '<p class="cu-noroute__body">No tool on this row is better. '
            f"{escape(ROW_LABELS[data_class][0])} data has no home here.</p>"
        )
        return

    destination, reached = route
    plain = next(name for candidate, name, _ in TOOL_COLUMNS if candidate is destination)
    reached_style = style_for(reached)
    st.html(
        '<p class="cu-label">Safer route</p>'
        f'<p class="cu-route">Move it to <strong>{escape(plain)}</strong>'
        f'<span class="cu-whatif__to cu-whatif__to--{reached_style.slug}"> '
        f"{escape(CELL_LABELS[reached])}</span></p>"
        '<p class="cu-meta">Found by running the same rules across this row, not '
        "written down.</p>"
    )


# --------------------------------------------------------------------------
# Where does it go?
# --------------------------------------------------------------------------

GAME_AT = "cu_sort_at"
GAME_SCORE = "cu_sort_score"
GAME_LAST = "cu_sort_last"

NOWHERE = "nowhere"


def _answer(choice: str) -> None:
    number, _phrase = ITEMS[st.session_state.get(GAME_AT, 0)]
    data_class = item_class(number)
    allowed = best_tools(data_class)
    right = (choice == NOWHERE and not allowed) or (choice != NOWHERE and Tool(choice) in allowed)
    st.session_state[GAME_LAST] = (number, choice, right)
    if right:
        st.session_state[GAME_SCORE] = st.session_state.get(GAME_SCORE, 0) + 1


def _next_item() -> None:
    st.session_state[GAME_AT] = st.session_state.get(GAME_AT, 0) + 1
    st.session_state[GAME_LAST] = None


def _restart_game() -> None:
    st.session_state[GAME_AT] = 0
    st.session_state[GAME_SCORE] = 0
    st.session_state[GAME_LAST] = None


def _render_game() -> None:
    at = st.session_state.get(GAME_AT, 0)
    score = st.session_state.get(GAME_SCORE, 0)

    if at >= len(ITEMS):
        st.html(
            f'<p class="cu-score">{score} / {len(ITEMS)}</p>'
            '<p class="cu-hint">Nothing was stored. Reload and the score is gone.</p>'
        )
        st.button("Play again", key="cu_sort_restart", on_click=_restart_game, type="primary")
        return

    number, phrase = ITEMS[at]
    st.html(
        f'<p class="cu-meta">Item {at + 1} of {len(ITEMS)} · {score} right so far</p>'
        f'<div class="cu-card cu-card--waiting"><p class="cu-reason">{escape(phrase)}</p>'
        '<p class="cu-subtitle">Which tools may hold this?</p></div>'
    )

    last = st.session_state.get(GAME_LAST)
    if last is None:
        with st.container(horizontal=True, gap="small", key="cu_sort_choices"):
            for tool, plain, _term in TOOL_COLUMNS:
                st.button(
                    plain,
                    key=f"cu_sort_{tool.value}",
                    on_click=_answer,
                    args=(tool.value,),
                )
            st.button("Nowhere", key="cu_sort_nowhere", on_click=_answer, args=(NOWHERE,))
        st.html(f'<p class="cu-meta" title="{escape(scenario(number).title)}">&nbsp;</p>')
        return

    _, choice, right = last
    data_class = item_class(number)
    allowed = best_tools(data_class)
    verdict = evaluate(
        cell_inputs(data_class, Tool(choice) if choice != NOWHERE else Tool.TIER_C), VERSION
    )
    names = (
        ", ".join(
            next(name for candidate, name, _ in TOOL_COLUMNS if candidate is tool)
            for tool in allowed
        )
        or "nothing on this grid"
    )
    st.html(
        f'<p class="cu-guessed cu-guessed--{"right" if right else "wrong"}">'
        f"{'✓ Right' if right else '✕ Not quite'}. It is "
        f"{escape(ROW_LABELS[data_class][0])} data, so it may go in "
        f"{escape(names)}.</p>"
        f'<p class="cu-stake">{escape(verdict.reasons[0] if verdict.reasons else "")}</p>'
    )
    st.button(
        "Next item" if at + 1 < len(ITEMS) else "See your score",
        key="cu_sort_next",
        on_click=_next_item,
        type="primary",
    )


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------


def main() -> None:
    inject_styles()
    page_header(
        "Which tools may hold which data",
        "The 7.1 grid. Every square is worked out by the same rules the Check page uses.",
    )

    view = st.radio(
        "View",
        options=("Plain", "Expert"),
        horizontal=True,
        key=EXPERT,
        label_visibility="collapsed",
        help="Expert adds the deciding clause to each square, and the backing behind it.",
    )
    expert = view == "Expert"

    _render_takeaway()
    _render_legend()
    _render_lenses()

    selected = st.session_state.get(SELECTED)
    st.html(
        "<style>"
        + _grid_styles(
            selected,
            st.session_state.get(ROW_LENS),
            st.session_state.get(COLUMN_LENS),
            expert,
        )
        + "</style>"
    )

    grid_column, detail_column = st.columns([1.55, 1], gap="medium")
    with grid_column:
        _render_grid(expert)
        if st.toggle("Add a model we run ourselves", key=SELF_HOSTED):
            _render_self_hosted()

    with detail_column:
        if selected is None:
            with st.container(key="cu_matrix_hint"):
                _render_waiting()
        else:
            with st.container(key="cu_matrix_detail"):
                st.button(
                    "Close",
                    key="cu_matrix_close",
                    on_click=_clear_selection,
                    type="tertiary",
                )
                _render_detail(DataClass(selected[0]), Tool(selected[1]), expert)

    render_data_class_key(VERSION)
    render_tier_key(VERSION)

    with st.expander("Where does it go?"):
        st.html(
            '<p class="cu-hint">Eight everyday things. Pick the tools that may '
            "hold each one. Nothing you tap is stored.</p>"
        )
        _render_game()

    render_footer(VERSION)


main()
