from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:8080"


# Test 7
# Check that the login page loads correctly
def test_login_page_loads(page: Page):

    page.goto(BASE_URL)

    expect(page.locator("#username")).to_be_visible()
    expect(page.locator("#password")).to_be_visible()
    expect(page.locator("#login-btn")).to_be_visible()


# Test 8
# Login should fail when username is empty
def test_empty_username(page: Page):

    page.goto(BASE_URL)

    page.locator("#password").fill("vs12345")
    page.locator("#login-btn").click()

    expect(page.locator("#message")).to_have_text(
        "Invalid username or password"
    )


# Test 9
# Login should fail when password is empty
def test_empty_password(page: Page):

    page.goto(BASE_URL)

    page.locator("#username").fill("testacc")
    page.locator("#login-btn").click()

    expect(page.locator("#message")).to_have_text(
        "Invalid username or password"
    )


# Test 10
# Login should fail when both fields are empty
def test_empty_username_and_password(page: Page):

    page.goto(BASE_URL)

    page.locator("#login-btn").click()

    expect(page.locator("#message")).to_have_text(
        "Invalid username or password"
    )


# Test 11
# Password should be hidden/masked
def test_password_field_is_masked(page: Page):

    page.goto(BASE_URL)

    expect(page.locator("#password")).to_have_attribute(
        "type",
        "password"
    )