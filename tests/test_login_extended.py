from playwright.sync_api import Page, expect

from healing.actions import self_healing_click
from healing.healing_engine import heal_locator


BASE_URL = "http://localhost:8080"


# =========================================================
# TEST 7
# Check that the login page loads correctly
# =========================================================

def test_login_page_loads(page: Page):

    page.goto(BASE_URL)

    expect(
        page.locator("#username")
    ).to_be_visible()

    expect(
        page.locator("#password")
    ).to_be_visible()

    # -------------------------------------------------
    # ORIGINAL LOCATOR
    # -------------------------------------------------

    original_locator = "#login-btn"

    login_button = page.locator(
        original_locator
    )

    # -------------------------------------------------
    # CHECK WHETHER ORIGINAL LOCATOR EXISTS
    # -------------------------------------------------

    if login_button.count() == 1:

        expect(
            login_button
        ).to_be_visible()

    else:

        print("\n" + "=" * 60)
        print("PLAYWRIGHT LOCATOR FAILURE DETECTED")
        print("=" * 60)

        print(
            f"Original locator failed: "
            f"{original_locator}"
        )

        # ---------------------------------------------
        # ACTIVATE SELF-HEALING ENGINE
        # ---------------------------------------------

        healed_locator = heal_locator(
            page=page,
            failed_locator=original_locator,
            expected_tag="button"
        )

        if healed_locator is None:

            raise AssertionError(
                "Self-healing failed. "
                "Could not locate the Login button."
            )

        print(
            f"\nUsing healed locator for "
            f"visibility check: {healed_locator}"
        )

        # ---------------------------------------------
        # ORIGINAL TEST INTENT
        # ---------------------------------------------

        expect(
            page.locator(healed_locator)
        ).to_be_visible()


# =========================================================
# TEST 8
# Login should fail when username is empty
# =========================================================

def test_empty_username(page: Page):

    page.goto(BASE_URL)

    page.locator(
        "#password"
    ).fill(
        "vs12345"
    )

    self_healing_click(
        page=page,
        original_locator="#login-btn",
        expected_tag="button"
    )

    expect(
        page.locator("#message")
    ).to_have_text(
        "Please enter username and password"
    )


# =========================================================
# TEST 9
# Login should fail when password is empty
# =========================================================

def test_empty_password(page: Page):

    page.goto(BASE_URL)

    page.locator(
        "#username"
    ).fill(
        "testacc"
    )

    self_healing_click(
        page=page,
        original_locator="#login-btn",
        expected_tag="button"
    )

    expect(
        page.locator("#message")
    ).to_have_text(
        "Please enter username and password"
    )


# =========================================================
# TEST 10
# Login should fail when both fields are empty
# =========================================================

def test_empty_username_and_password(page: Page):

    page.goto(BASE_URL)

    self_healing_click(
        page=page,
        original_locator="#login-btn",
        expected_tag="button"
    )

    expect(
        page.locator("#message")
    ).to_have_text(
        "Please enter username and password"
    )


# =========================================================
# TEST 11
# Password should be hidden/masked
# =========================================================

def test_password_field_is_masked(page: Page):

    page.goto(BASE_URL)

    expect(
        page.locator("#password")
    ).to_have_attribute(
        "type",
        "password"
    )