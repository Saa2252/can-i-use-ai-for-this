"""One inline-SVG icon set, drawn the same way for every status.

The app used text glyphs — ✓ ! ⊘ ✕ — which are four different typefaces'
idea of a symbol: they sit at different heights, carry different weights,
and ⊘ is missing from some Android fonts. These are four circles drawn with
the same radius and the same stroke, so the row reads as one set, and the
mark inside each is different enough to carry the meaning on its own:

    allowed         a tick
    needs approval  a clock, because the answer is "not yet"
    not permitted   a diagonal bar, the "no entry" sign
    prohibited      a cross

BUILD_SPEC 8, "Never color alone": the shape is the signal and the colour
agrees with it, so the grid survives greyscale and colour blindness. The
word beside it is the third signal.

Every icon reaches the page as CSS, never as markup. `st.html` strips an
inline `<svg>` out of whatever you hand it — the element survives, the
drawing does not, and the result is an empty span that looks like a
styling bug rather than a sanitiser. So there is no inline helper here to
reach for by mistake: `data_uri` wraps the drawing for a stylesheet, and
`rule` writes the whole declaration for a given selector. A Streamlit
button, which takes a text label and no HTML at all, needs that route
anyway.
"""

from __future__ import annotations

from urllib.parse import quote

#: The inside of each 24x24 box. Every path is stroked, never filled, so one
#: `stroke` attribute colours the whole set.
MARKS: dict[str, str] = {
    "allowed": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.5 2.5L16 9.5"/>',
    "needs-approval": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.2l3.2 1.9"/>',
    "not-permitted": '<circle cx="12" cy="12" r="9"/><path d="M5.6 18.4L18.4 5.6"/>',
    "prohibited": '<circle cx="12" cy="12" r="9"/><path d="M8.5 8.5l7 7M15.5 8.5l-7 7"/>',
    # Used by the page furniture rather than by a verdict.
    "row": '<path d="M3 12h18M14 7l5 5-5 5"/>',
    "column": '<path d="M12 3v18M7 14l5 5 5-5"/>',
    "grid": (
        '<rect x="3" y="3" width="18" height="18" rx="2"/>'
        '<path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>'
    ),
}

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'width="{size}" height="{size}" fill="none" stroke="{colour}" '
    'stroke-width="{weight}" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true" focusable="false">{marks}</svg>'
)


def data_uri(name: str, colour: str, *, size: int = 18, weight: float = 2) -> str:
    """The same drawing as a `url(...)` value for CSS.

    A Streamlit button renders its label as text, so a cell's icon cannot be
    inlined with it. It arrives as a background image on a generated rule
    instead, which is the same route the cell colours already take.
    """
    svg = _SVG.format(size=size, colour=colour, weight=weight, marks=MARKS[name])
    return f'url("data:image/svg+xml,{quote(svg, safe="")}")'


def rule(selector: str, name: str, colour: str, *, size: int = 18) -> str:
    """A CSS declaration that paints `name` onto an otherwise empty element.

    The element supplies the box and the icon arrives as its background, so
    the markup stays a span and the drawing cannot be stripped out of it.
    """
    return (
        f"{selector}{{"
        f"display:inline-block;"
        f"width:{size}px;height:{size}px;"
        f"flex:0 0 auto;"
        f"background-image:{data_uri(name, colour, size=size)};"
        f"background-repeat:no-repeat;"
        f"background-position:center;"
        f"background-size:{size}px {size}px;"
        f"}}"
    )
