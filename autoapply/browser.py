"""Browser driver factory.

Turns the browser choice stored in a :class:`~autoapply.profile.Profile` into a
live Selenium WebDriver. Selenium 4's built-in Selenium Manager downloads the
matching driver automatically, so the user doesn't have to install
chromedriver/geckodriver by hand.
"""

from __future__ import annotations

import os
import sys
import tempfile


def _default_user_data_dir(browser: str) -> str | None:
    """Best-effort path to the user's real browser profile directory.

    Reusing this lets the automated browser keep the user logged in to job
    sites (LinkedIn, Workday, Greenhouse, etc.). Returns ``None`` when we can't
    confidently locate it for the current OS/browser.
    """
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        roaming = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        return {
            "chrome": os.path.join(local, "Google", "Chrome", "User Data"),
            "edge": os.path.join(local, "Microsoft", "Edge", "User Data"),
            "firefox": os.path.join(roaming, "Mozilla", "Firefox"),
        }.get(browser)
    if sys.platform == "darwin":
        support = os.path.join(home, "Library", "Application Support")
        return {
            "chrome": os.path.join(support, "Google", "Chrome"),
            "edge": os.path.join(support, "Microsoft Edge"),
            "firefox": os.path.join(support, "Firefox"),
        }.get(browser)
    # Linux
    return {
        "chrome": os.path.join(home, ".config", "google-chrome"),
        "edge": os.path.join(home, ".config", "microsoft-edge"),
        "firefox": os.path.join(home, ".mozilla", "firefox"),
    }.get(browser)


def create_driver(browser: str, use_existing_profile: bool = False):
    """Create and return a Selenium WebDriver for ``browser``.

    Args:
        browser: one of ``chrome``, ``firefox``, ``edge``.
        use_existing_profile: when True, point the browser at the user's real
            profile directory so existing logins carry over.

    Raises:
        ValueError: if ``browser`` is not supported.
        RuntimeError: if Selenium is not installed.
    """
    try:
        from selenium import webdriver
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "Selenium is not installed. Run: pip install -r requirements.txt"
        ) from exc

    browser = browser.lower().strip()
    profile_dir = _default_user_data_dir(browser) if use_existing_profile else None

    if browser == "chrome":
        opts = webdriver.ChromeOptions()
        if profile_dir:
            opts.add_argument(f"--user-data-dir={profile_dir}")
        # Keep the window open after the script ends so the user can review/submit.
        opts.add_experimental_option("detach", True)
        return webdriver.Chrome(options=opts)

    if browser == "edge":
        opts = webdriver.EdgeOptions()
        if profile_dir:
            opts.add_argument(f"--user-data-dir={profile_dir}")
        opts.add_experimental_option("detach", True)
        return webdriver.Edge(options=opts)

    if browser == "firefox":
        opts = webdriver.FirefoxOptions()
        if profile_dir:
            opts.add_argument("-profile")
            opts.add_argument(profile_dir)
        return webdriver.Firefox(options=opts)

    raise ValueError(f"Unsupported browser: {browser!r}. Choose chrome, firefox, or edge.")
