from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)

from failure_analyzer import analyze_locator_failure


# -------------------------------------------------
# CONFIGURATION
# -------------------------------------------------

OLD_LOCATOR = "#login-btn"
URL = "http://localhost:8080"


def run_self_healing_demo():

    print("=" * 60)
    print("SMARTKART SELF-HEALING TEST")
    print("=" * 60)

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        try:

            # -------------------------------------------------
            # 1. OPEN SMARTKART
            # -------------------------------------------------

            print("\nOpening SmartKart...")

            page.goto(URL)

            print(f"Testing original locator: {OLD_LOCATOR}")


            # -------------------------------------------------
            # 2. TRY ORIGINAL LOCATOR
            # -------------------------------------------------

            try:

                page.locator(
                    OLD_LOCATOR
                ).click(timeout=3000)

                print("\nOriginal locator still works.")

                return

            except PlaywrightTimeoutError:

                print("\n❌ ORIGINAL LOCATOR FAILED")
                print(f"Failed locator: {OLD_LOCATOR}")


            # -------------------------------------------------
            # 3. CAPTURE LIVE BUTTONS
            # -------------------------------------------------

            # Because the failed Playwright operation was a
            # CLICK on a button, we only collect buttons.
            #
            # This reduces unnecessary information sent to
            # the AI model.

            elements = page.locator(
                "button"
            ).evaluate_all(
                """
                elements => elements.map(el => ({
                    tag: el.tagName.toLowerCase(),
                    id: el.id || "",
                    name: el.getAttribute("name") || "",
                    type: el.getAttribute("type") || "",
                    text: (el.innerText || "").trim(),
                    placeholder: el.getAttribute("placeholder") || "",
                    ariaLabel: el.getAttribute("aria-label") || ""
                }))
                """
            )

            print("\nLive button elements captured:")

            for element in elements:
                print(element)


            # -------------------------------------------------
            # 4. PREPARE ELEMENT DATA FOR OLLAMA
            # -------------------------------------------------

            dom_information = "\n".join(
                str(element)
                for element in elements
            )


            # -------------------------------------------------
            # 5. SEND FAILURE INFORMATION TO OLLAMA
            # -------------------------------------------------

            print("\nSending LIVE buttons to Ollama...")

            suggested_locator = analyze_locator_failure(
                OLD_LOCATOR,
                dom_information
            )

            print("\nOllama suggested:")
            print(suggested_locator)


            # -------------------------------------------------
            # 6. REJECT THE ORIGINAL FAILED LOCATOR
            # -------------------------------------------------

            if suggested_locator == OLD_LOCATOR:

                print("\n❌ REJECTED")

                print(
                    "Ollama returned the same locator "
                    "that already failed."
                )

                return


            # -------------------------------------------------
            # 7. VALIDATE AI LOCATOR
            # -------------------------------------------------

            print("\nValidating suggested locator...")

            candidate = page.locator(
                suggested_locator
            )

            count = candidate.count()


            # -------------------------------------------------
            # 8. CHECK LOCATOR UNIQUENESS
            # -------------------------------------------------

            if count != 1:

                print(
                    f"\n❌ REJECTED: Suggested locator "
                    f"matched {count} elements."
                )

                return

            print("✅ Suggested locator exists.")
            print("✅ Suggested locator is unique.")


            # -------------------------------------------------
            # 9. CHECK VISIBILITY
            # -------------------------------------------------

            candidate.wait_for(
                state="visible",
                timeout=5000
            )

            print("✅ Suggested element is visible.")


            # -------------------------------------------------
            # 10. CHECK ELEMENT TYPE
            # -------------------------------------------------

            tag_name = candidate.evaluate(
                "element => element.tagName.toLowerCase()"
            )

            if tag_name != "button":

                print(
                    f"\n❌ REJECTED: Expected a button, "
                    f"but Ollama selected <{tag_name}>."
                )

                return

            print("✅ Suggested element is a button.")


            # -------------------------------------------------
            # 11. RECREATE ORIGINAL LOGIN TEST CONDITIONS
            # -------------------------------------------------

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
            # 12. CLICK AI-SUGGESTED ELEMENT
            # -------------------------------------------------

            candidate.click(
                timeout=5000
            )

            print("✅ Suggested element is clickable.")


            # -------------------------------------------------
            # 13. VERIFY ORIGINAL BEHAVIOUR
            # -------------------------------------------------

            try:

                page.wait_for_url(
                    "**/products.html",
                    timeout=5000
                )

            except PlaywrightTimeoutError:

                print(
                    "\n❌ REJECTED: Locator was clickable, "
                    "but login behaviour was not restored."
                )

                return


            print("✅ Expected navigation restored.")


            # -------------------------------------------------
            # 14. FINAL SELF-HEALING RESULT
            # -------------------------------------------------

            print("\n" + "=" * 60)

            print(
                "SELF-HEALING RESULT: SUCCESS"
            )

            print("=" * 60)

            print(
                f"Old locator: {OLD_LOCATOR}"
            )

            print(
                f"New locator: {suggested_locator}"
            )


        # -------------------------------------------------
        # UNEXPECTED ERROR
        # -------------------------------------------------

        except Exception as error:

            print(
                "\n❌ SELF-HEALING RESULT: FAILED"
            )

            print(
                f"Reason: {error}"
            )


        # -------------------------------------------------
        # CLEANUP
        # -------------------------------------------------

        finally:

            browser.close()


# -------------------------------------------------
# PROGRAM ENTRY POINT
# -------------------------------------------------

if __name__ == "__main__":

    run_self_healing_demo()