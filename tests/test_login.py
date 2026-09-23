from playwright.sync_api import Page, expect


def test_successful_login(page: Page):

    # Open Test Login Page
    page.goto("http://localhost:8080")

    # Enter valid credentials
    page.locator("#username").fill("testacc")
    page.locator("#password").fill("vs12345")

    # Click Login
    page.locator("#login-btn").click()

    # Verify that the Products page opened
    expect(page).to_have_url("http://localhost:8080/products.html")

    # Verify welcome message
    expect(page.locator("#welcome-message")).to_have_text(
        "Welcome, testacc"
    )

def test_invalid_login(page: Page):

    # Open HealCart
    page.goto("http://localhost:8080")

    # Enter incorrect credentials
    page.locator("#username").fill("wronguser")
    page.locator("#password").fill("wrongpassword")

    # Click Login
    page.locator("#login-btn").click()

    # Verify error message
    expect(page.locator("#message")).to_have_text(
        "Invalid username or password"
    )