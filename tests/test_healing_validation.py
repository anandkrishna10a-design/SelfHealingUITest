
from playwright.sync_api import Page

import healing.healing_engine as healing_engine
from healing.healing_engine import heal_locator


BASE_URL = "http://localhost:8080"


def test_rejects_locator_not_in_live_candidates(page: Page, monkeypatch):
    """Reject an AI suggestion that is not a live candidate."""

    page.goto(f"{BASE_URL}/products.html")

    monkeypatch.setattr(
        healing_engine,
        "analyze_locator_failure",
        lambda failed_locator, element_information: "#fake-button",
    )

    result = heal_locator(
        page=page,
        failed_locator="#old-search-box",
        expected_tag="input",
    )

    assert result is None


def test_rejects_wrong_element_tag(page: Page, monkeypatch):
    """Reject a button when an input is expected."""

    page.goto(f"{BASE_URL}/products.html")

    monkeypatch.setattr(
        healing_engine,
        "analyze_locator_failure",
        lambda failed_locator, element_information: "#search-btn",
    )

    result = heal_locator(
        page=page,
        failed_locator="#old-search-box",
        expected_tag="input",
    )

    assert result is None


def test_retries_after_invalid_suggestion(page: Page, monkeypatch):
    """Reject an invalid suggestion, then accept a valid input."""

    page.goto(f"{BASE_URL}/products.html")

    suggestions = iter([
        "#fake-search-box",
        "#search-box",
    ])

    monkeypatch.setattr(
        healing_engine,
        "analyze_locator_failure",
        lambda failed_locator, element_information: next(suggestions),
    )

    result = heal_locator(
        page=page,
        failed_locator="#old-search-box",
        expected_tag="input",
    )

    assert result == "#search-box"
