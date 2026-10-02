from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:8080"


def test_cart_page_opens():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{BASE_URL}/products.html")

        page.locator("#cart-count").click()

        page.wait_for_url("**/cart.html")

        assert page.locator("h1").inner_text() == "Your Shopping Cart"

        browser.close()


def test_add_product_and_display_in_cart():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{BASE_URL}/products.html")

        page.evaluate("localStorage.removeItem('smartkart_cart')")
        page.reload()

        page.locator(".product-card").first.locator(
            "button[id^='add-']"
        ).click()

        assert page.locator("#cart-count").inner_text() == "Cart (1)"

        page.locator("#cart-count").click()

        page.wait_for_url("**/cart.html")

        assert page.locator(".cart-item").count() == 1

        browser.close()


def test_cart_quantity_controls():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{BASE_URL}/products.html")

        page.evaluate("localStorage.removeItem('smartkart_cart')")
        page.reload()

        page.locator(".product-card").first.locator(
            "button[id^='add-']"
        ).click()

        page.locator("#cart-count").click()

        page.wait_for_url("**/cart.html")

        assert page.locator(".qty-value").inner_text() == "1"

        page.locator(".qty-btn").last.click()

        assert page.locator(".qty-value").inner_text() == "2"

        page.locator(".qty-btn").first.click()

        assert page.locator(".qty-value").inner_text() == "1"

        browser.close()


def test_remove_item_from_cart():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{BASE_URL}/products.html")

        page.evaluate("localStorage.removeItem('smartkart_cart')")
        page.reload()

        page.locator(".product-card").first.locator(
            "button[id^='add-']"
        ).click()

        page.locator("#cart-count").click()

        page.wait_for_url("**/cart.html")

        assert page.locator(".cart-item").count() == 1

        page.locator(".remove-btn").click()

        assert page.locator(".cart-item").count() == 0

        assert page.locator(".empty-cart").is_visible()

        browser.close()


def test_order_now():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{BASE_URL}/products.html")

        page.evaluate("localStorage.removeItem('smartkart_cart')")
        page.reload()

        page.locator(".product-card").first.locator(
            "button[id^='add-']"
        ).click()

        page.locator("#cart-count").click()

        page.wait_for_url("**/cart.html")

        page.locator("#order-now-btn").click()

        message = page.locator("#order-message")

        assert message.is_visible()

        assert "Order placed successfully" in message.inner_text()

        browser.close()