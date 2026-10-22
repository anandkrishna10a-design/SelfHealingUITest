
from playwright.sync_api import Page, expect

import healing.healing_engine as healing_engine
from healing.actions import self_healing_click


BASE_URL = "http://localhost:8080"


def test_self_healing_recovers_add_to_cart_button(
    page: Page,
    monkeypatch,
):
    """Recover a broken Add to Cart locator and verify the action."""

    page.goto(f"{BASE_URL}/products.html")

    # Start with an empty cart for a predictable test.
    page.evaluate("localStorage.removeItem('smartkart_cart')")
    page.reload()

    # Simulate an AI suggestion deterministically.
    # This tests the healing and validation flow without depending
    # on Ollama's response for this particular test.
    monkeypatch.setattr(
        healing_engine,
        "analyze_locator_failure",
        lambda failed_locator, element_information: "#add-laptop",
    )

    healed_locator = self_healing_click(
        page=page,
        original_locator="#old-add-laptop",
        expected_tag="button",
    )

    # Verify that the correct replacement locator was selected.
    assert healed_locator == "#add-laptop"

    # Verify that the recovered button performed its real action.
    expect(page.locator("#cart-count")).to_have_text("Cart (1)")
    expect(page.locator("#cart-message")).to_have_text(
        "Laptop added to cart"
    )
