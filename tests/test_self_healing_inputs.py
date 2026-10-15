from playwright.sync_api import Page, expect

from healing.actions import self_healing_fill
import healing.healing_engine as healing_engine


BASE_URL = "http://localhost:8080"


def test_self_healing_search_input(page: Page, monkeypatch):
    # Open the login page, then navigate to the products page.
    page.goto(BASE_URL)
    page.goto(f"{BASE_URL}/products.html")

    # Make Ollama's suggestion deterministic for this automated test.
    monkeypatch.setattr(
        healing_engine,
        "analyze_locator_failure",
        lambda failed_locator, element_information: "#search-box",
    )

    # Use a deliberately incorrect locator.
    healed_locator = self_healing_fill(
        page=page,
        original_locator="#old-search-box",
        value="laptop",
        expected_tag="input",
    )

    # Verify that self-healing found and filled the real input.
    assert healed_locator == "#search-box"
    expect(page.locator("#search-box")).to_have_value("laptop")

    # Verify that the search still works.
    page.locator("#search-btn").click()
    expect(page.get_by_text("Laptop", exact=True)).to_be_visible()
