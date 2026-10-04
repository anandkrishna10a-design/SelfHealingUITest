from playwright.sync_api import Page, expect

from healing.actions import self_healing_click


# =========================================================
# TEST 1 - SUCCESSFUL LOGIN
# =========================================================

def test_successful_login(page: Page):

    # Open SmartKart
    page.goto(
        "http://localhost:8080"
    )

    # Enter valid credentials
    page.locator(
        "#username"
    ).fill(
        "testacc"
    )

    page.locator(
        "#password"
    ).fill(
        "vs12345"
    )

    # -------------------------------------------------
    # SELF-HEALING LOGIN CLICK
    # -------------------------------------------------

    self_healing_click(
        page=page,
        original_locator="#login-btn",
        expected_tag="button"
    )

    # -------------------------------------------------
    # ORIGINAL ASSERTIONS
    # -------------------------------------------------

    expect(
        page
    ).to_have_url(
        "http://localhost:8080/products.html"
    )

    expect(
        page.locator("#welcome-message")
    ).to_have_text(
        "Welcome, testacc"
    )


# =========================================================
# TEST 2 - INVALID LOGIN
# =========================================================

def test_invalid_login(page: Page):

    # Open SmartKart
    page.goto(
        "http://localhost:8080"
    )

    # Enter incorrect credentials
    page.locator(
        "#username"
    ).fill(
        "wronguser"
    )

    page.locator(
        "#password"
    ).fill(
        "wrongpassword"
    )

    # -------------------------------------------------
    # SELF-HEALING LOGIN CLICK
    # -------------------------------------------------

    self_healing_click(
        page=page,
        original_locator="#login-btn",
        expected_tag="button"
    )

    # -------------------------------------------------
    # ORIGINAL ASSERTION
    # -------------------------------------------------

    expect(
        page.locator("#message")
    ).to_have_text(
        "Invalid username or password"
    )