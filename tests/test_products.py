from playwright.sync_api import Page, expect

from healing.actions import self_healing_click


BASE_URL = "http://localhost:8080"


# =========================================================
# REUSABLE LOGIN
# =========================================================

def login(page: Page):

    page.goto(BASE_URL)

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

    self_healing_click(
        page=page,
        original_locator="#login-btn",
        expected_tag="button"
    )

    expect(
        page
    ).to_have_url(
        "http://localhost:8080/products.html"
    )


# =========================================================
# PRODUCTS SHOULD BE VISIBLE
# =========================================================

def test_products_are_visible(page: Page):

    login(page)

    expect(
        page.get_by_text(
            "Laptop",
            exact=True
        )
    ).to_be_visible()

    expect(
        page.get_by_text(
            "Headphones",
            exact=True
        )
    ).to_be_visible()

    expect(
        page.get_by_text(
            "Keyboard",
            exact=True
        )
    ).to_be_visible()


# =========================================================
# PRODUCT SEARCH
# =========================================================

def test_search_product(page: Page):

    login(page)

    page.locator(
        "#search-box"
    ).fill(
        "Laptop"
    )

    page.locator(
        "#search-btn"
    ).click()

    expect(
        page.get_by_text(
            "Laptop",
            exact=True
        )
    ).to_be_visible()

    expect(
        page.get_by_text(
            "Headphones",
            exact=True
        )
    ).to_be_hidden()

    expect(
        page.get_by_text(
            "Keyboard",
            exact=True
        )
    ).to_be_hidden()


# =========================================================
# ADD LAPTOP TO CART
# =========================================================

def test_add_laptop_to_cart(page: Page):

    login(page)

    page.locator(
        "#add-laptop"
    ).click()

    expect(
        page.locator("#cart-count")
    ).to_have_text(
        "Cart (1)"
    )

    expect(
        page.locator("#cart-message")
    ).to_have_text(
        "Laptop added to cart"
    )


# =========================================================
# LOGOUT
# =========================================================

def test_logout(page: Page):

    login(page)

    page.locator(
        "#logout-btn"
    ).click()

    expect(
        page
    ).to_have_url(
        "http://localhost:8080/index.html"
    )