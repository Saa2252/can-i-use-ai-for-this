"""Page shell: the stylesheet, the header, and the shared page setup."""

from __future__ import annotations

import html
import re
from pathlib import Path

import streamlit as st

from app.styles.tokens import css_variables

CSS_FILE = Path(__file__).resolve().parent.parent / "styles" / "app.css"


def _stylesheet() -> str:
    """The token `:root` block followed by the one stylesheet.

    Read on every run rather than cached: a few KB of file I/O is nothing
    beside a stale stylesheet surviving an edit until the server restarts.
    """
    return f"{css_variables()}\n\n{CSS_FILE.read_text(encoding='utf-8')}"


def inject_styles() -> None:
    """Apply the stylesheet. Safe to call on every page."""
    st.html(f"<style>\n{_stylesheet()}\n</style>")


def page_header(title: str, lede: str) -> None:
    st.markdown(f"# {title}")
    st.html(f'<p class="cu-lede">{escape(lede)}</p>')


def escape(text: str) -> str:
    """Escape text going into one of our own HTML blocks."""
    return html.escape(str(text), quote=True)


#: `[Organization name]`, `[Your name]`, `[AI governance contact]` — the
#: fields an adopting organization fills in.
_TEMPLATE_FIELD_RE = re.compile(r"\[([^\]]+)\]")


def mark_template_fields(text: str) -> str:
    """Escape text, and mark any `[bracketed]` placeholder as a template field.

    The placeholders stay in the policy file because it is a model policy.
    Showing them as deliberate fields, rather than as stray brackets, is what
    makes that legible.
    """
    out: list[str] = []
    last = 0
    for match in _TEMPLATE_FIELD_RE.finditer(text):
        out.append(escape(text[last : match.start()]))
        out.append(f'<span class="cu-template">{escape(match.group(1))}</span>')
        last = match.end()
    out.append(escape(text[last:]))
    return "".join(out)
