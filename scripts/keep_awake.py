"""Visit the live app so Streamlit Community Cloud does not put it to sleep.

Community Cloud sleeps an app that has had no viewers for a while, and the
next visitor meets a "get this app back up" button and a cold start. A
scheduled visit from .github/workflows/keep-awake.yml opens the page in a
real browser, presses that button if it is there, and waits until the page
has rendered something of ours. A plain HTTP request is not enough: the
host answers it with a redirect and never starts the app.

Usage: python scripts/keep_awake.py [URL]
"""

from __future__ import annotations

import re
import sys
import time

from playwright.sync_api import Page, sync_playwright

DEFAULT_URL = "https://can-i-use-ai-for-this-1.streamlit.app/"

#: Text that only appears once the app itself has rendered.
RENDERED = "AI Acceptable Use Policy"

WAKE_BUTTON = re.compile(r"get this app back up", re.IGNORECASE)

RENDER_TIMEOUT_S = 180
POLL_S = 3


def _in_any_frame(page: Page, text: str) -> bool:
    """The host wraps the app in a frame, so every frame is searched."""
    return any(frame.get_by_text(text).count() > 0 for frame in page.frames)


def _press_wake_button(page: Page) -> bool:
    for frame in page.frames:
        button = frame.get_by_role("button", name=WAKE_BUTTON)
        if button.count():
            button.first.click()
            return True
    return False


def visit(url: str) -> bool:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=90_000)

        deadline = time.monotonic() + RENDER_TIMEOUT_S
        woke = False
        while time.monotonic() < deadline:
            if _in_any_frame(page, RENDERED):
                print("awake" + (" (woken)" if woke else ""))
                browser.close()
                return True
            if not woke and _press_wake_button(page):
                woke = True
                print("asleep: pressed the wake button")
            page.wait_for_timeout(POLL_S * 1000)

        print(f"gave up after {RENDER_TIMEOUT_S}s without seeing {RENDERED!r}")
        browser.close()
        return False


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    sys.exit(0 if visit(target) else 1)
