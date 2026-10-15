from playwright.sync_api import Page, expect

from healing.actions import self_healing_fill


BASE_URL = "http://localhost:8080"


def test_real_ollama_heals_search_input(page: Page):
    page.goto(f"{BASE_URL}/products.html")

    healed_locator = self_healing_fill(
        page=page,
        original_locator="#old-search-box",
        value="laptop",
        expected_tag="input",
    )

    assert healed_locator == "#search-box"
    expect(page.locator("#search-box")).to_have_value("laptop")

    page.locator("#search-btn").click()
    expect(page.get_by_text("Laptop", exact=True)).to_be_visible()
