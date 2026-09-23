from playwright.sync_api import Page, expect


def login(page: Page):
    page.goto("http://localhost:8080")
    page.locator("#username").fill("testacc")
    page.locator("#password").fill("vs12345")
    page.locator("#login-btn").click()

    expect(page).to_have_url(
        "http://localhost:8080/products.html"
    )


def test_products_are_visible(page: Page):
    login(page)

    expect(page.get_by_text("Laptop", exact=True)).to_be_visible()
    expect(page.get_by_text("Headphones", exact=True)).to_be_visible()
    expect(page.get_by_text("Keyboard", exact=True)).to_be_visible()


def test_search_product(page: Page):
    login(page)

    page.locator("#search-box").fill("Laptop")
    page.locator("#search-btn").click()

    expect(page.get_by_text("Laptop", exact=True)).to_be_visible()
    expect(page.get_by_text("Headphones", exact=True)).to_be_hidden()
    expect(page.get_by_text("Keyboard", exact=True)).to_be_hidden()


def test_add_laptop_to_cart(page: Page):
    login(page)

    page.locator("#add-laptop").click()

    expect(page.locator("#cart-count")).to_have_text("Cart (1)")
    expect(page.locator("#cart-message")).to_have_text(
        "Laptop added to cart"
    )


def test_logout(page: Page):
    login(page)

    page.locator("#logout-btn").click()

    expect(page).to_have_url(
        "http://localhost:8080/index.html"
    )