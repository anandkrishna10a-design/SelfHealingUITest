from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:8080"


def login(page: Page):
    page.goto(BASE_URL)

    page.locator("#username").fill("testacc")
    page.locator("#password").fill("vs12345")
    page.locator("#login-btn").click()

    expect(page).to_have_url(
        "http://localhost:8080/products.html"
    )


# Test 12
# SmartKart should display the expected products
def test_all_products_are_displayed(page: Page):

    login(page)

    expect(page.get_by_text("Laptop", exact=True)).to_be_visible()
    expect(page.get_by_text("Headphones", exact=True)).to_be_visible()
    expect(page.get_by_text("Keyboard", exact=True)).to_be_visible()
    expect(page.get_by_text("Gaming Monitor", exact=True)).to_be_visible()
    expect(page.get_by_text("SSD 1TB", exact=True)).to_be_visible()


# Test 13
# Product search should be case-insensitive
def test_search_is_case_insensitive(page: Page):

    login(page)

    page.locator("#search-box").fill("laptop")
    page.locator("#search-btn").click()

    expect(
        page.get_by_text("Laptop", exact=True)
    ).to_be_visible()


# Test 14
# Partial product names should work in search
def test_partial_product_search(page: Page):

    login(page)

    page.locator("#search-box").fill("Lap")
    page.locator("#search-btn").click()

    expect(
        page.get_by_text("Laptop", exact=True)
    ).to_be_visible()


# Test 15
# A nonexistent product should not be displayed
def test_search_nonexistent_product(page: Page):

    login(page)

    page.locator("#search-box").fill("PlayStation")
    page.locator("#search-btn").click()

    expect(
        page.get_by_text("Laptop", exact=True)
    ).to_be_hidden()

    expect(
        page.get_by_text("Headphones", exact=True)
    ).to_be_hidden()


# Test 16
# Clearing search should restore the products
def test_empty_search_displays_all_products(page: Page):

    login(page)

    page.locator("#search-box").fill("Laptop")
    page.locator("#search-btn").click()

    expect(
        page.get_by_text("Laptop", exact=True)
    ).to_be_visible()

    expect(
        page.get_by_text("Headphones", exact=True)
    ).to_be_hidden()

    page.locator("#search-box").fill("")
    page.locator("#search-btn").click()

    expect(
        page.get_by_text("Laptop", exact=True)
    ).to_be_visible()

    expect(
        page.get_by_text("Headphones", exact=True)
    ).to_be_visible()

    expect(
        page.get_by_text("Keyboard", exact=True)
    ).to_be_visible()


# Test 17
# Computers category should display computer products
def test_computers_category_filter(page: Page):

    login(page)

    page.get_by_role("button", name="Computers", exact=True).click()

    expect(page.get_by_text("Laptop", exact=True)).to_be_visible()
    expect(page.get_by_text("Gaming Monitor", exact=True)).to_be_visible()
    expect(page.get_by_text("Headphones", exact=True)).to_be_hidden()


# Test 18
# Audio category should display audio products
def test_audio_category_filter(page: Page):

    login(page)

    page.get_by_role("button", name="Audio", exact=True).click()

    expect(page.get_by_text("Headphones", exact=True)).to_be_visible()
    expect(page.get_by_text("Bluetooth Speaker", exact=True)).to_be_visible()
    expect(page.get_by_text("Microphone", exact=True)).to_be_visible()
    expect(page.get_by_text("Laptop", exact=True)).to_be_hidden()


# Test 19
# Accessories category should display accessory products
def test_accessories_category_filter(page: Page):

    login(page)

    page.get_by_role("button", name="Accessories", exact=True).click()

    expect(page.get_by_text("Keyboard", exact=True)).to_be_visible()
    expect(page.get_by_text("Wireless Mouse", exact=True)).to_be_visible()
    expect(page.get_by_text("Webcam", exact=True)).to_be_visible()
    expect(page.get_by_text("USB Hub", exact=True)).to_be_visible()
    expect(page.get_by_text("Laptop Stand", exact=True)).to_be_visible()
    expect(page.get_by_text("Laptop", exact=True)).to_be_hidden()


# Test 20
# Storage category should display storage products
def test_storage_category_filter(page: Page):

    login(page)

    page.get_by_role("button", name="Storage", exact=True).click()

    expect(page.get_by_text("SSD 1TB", exact=True)).to_be_visible()
    expect(page.get_by_text("External Hard Drive", exact=True)).to_be_visible()
    expect(page.get_by_text("Laptop", exact=True)).to_be_hidden()


# Test 21
# Adding two different products should increase cart count to 2
def test_add_two_products_to_cart(page: Page):

    login(page)

    page.locator("#add-laptop").click()
    page.locator("#add-headphones").click()

    expect(page.locator("#cart-count")).to_have_text("Cart (2)")


# Test 22
# Adding the same product twice should increase cart count to 2
def test_add_same_product_twice(page: Page):

    login(page)

    page.locator("#add-laptop").click()
    page.locator("#add-laptop").click()

    expect(page.locator("#cart-count")).to_have_text("Cart (2)")


# Test 23
# Cart message should show the name of the added product
def test_cart_message_for_headphones(page: Page):

    login(page)

    page.locator("#add-headphones").click()

    expect(page.locator("#cart-message")).to_have_text(
        "Headphones added to cart"
    )

# Test 24
# Clicking the SmartKart logo should return to the login/home page
def test_smartkart_logo_navigation(page: Page):

    login(page)

    page.locator("#store-title").click()

    expect(page).to_have_url(
        "http://localhost:8080/index.html"
    )


# Test 25
# Logout should return the user to the login page
def test_logout_navigation(page: Page):

    login(page)

    page.locator("#logout-btn").click()

    expect(page).to_have_url(
        "http://localhost:8080/index.html"
    )

    expect(page.locator("#username")).to_be_visible()
    expect(page.locator("#password")).to_be_visible()