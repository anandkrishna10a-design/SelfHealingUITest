from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from healing.healing_engine import heal_locator


def self_healing_click(
    page: Page,
    original_locator: str,
    expected_tag: str = "button",
):
    """Click an element and attempt self-healing if its locator fails."""

    try:
        page.locator(original_locator).click(timeout=3000)
        print(f"\nOriginal locator worked: {original_locator}")
        return original_locator

    except PlaywrightTimeoutError:
        print("\nPLAYWRIGHT LOCATOR FAILURE DETECTED")
        print(f"Original locator failed: {original_locator}")

        healed_locator = heal_locator(
            page=page,
            failed_locator=original_locator,
            expected_tag=expected_tag,
        )

        if healed_locator is None:
            raise AssertionError(
                f"Self-healing failed for {original_locator}"
            )

        print(f"Retrying with healed locator: {healed_locator}")

        try:
            page.locator(healed_locator).click(timeout=5000)
        except PlaywrightTimeoutError as error:
            raise AssertionError(
                f"Healed locator could not be clicked: {healed_locator}"
            ) from error

        print("Healed locator clicked successfully.")
        return healed_locator


def self_healing_fill(
    page: Page,
    original_locator: str,
    value: str,
    expected_tag: str = "input",
):
    """
    Fill an input and attempt self-healing if its locator fails.

    The replacement locator is validated by the healing engine.
    The replacement must also be an editable input before filling.
    """

    try:
        page.locator(original_locator).fill(
            value,
            timeout=3000,
        )
        print(f"\nOriginal input locator worked: {original_locator}")
        return original_locator

    except PlaywrightTimeoutError:
        print("\nPLAYWRIGHT INPUT LOCATOR FAILURE DETECTED")
        print(f"Original locator failed: {original_locator}")

        healed_locator = heal_locator(
            page=page,
            failed_locator=original_locator,
            expected_tag=expected_tag,
        )

        if healed_locator is None:
            raise AssertionError(
                f"Self-healing failed for input {original_locator}"
            )

        candidate = page.locator(healed_locator)

        try:
            candidate.wait_for(state="visible", timeout=5000)

            is_editable = candidate.evaluate(
                """
                element =>
                    !element.disabled &&
                    !element.readOnly &&
                    (
                        element.tagName.toLowerCase() === "textarea" ||
                        (
                            element.tagName.toLowerCase() === "input" &&
                            !["button", "submit", "reset", "checkbox",
                              "radio", "file", "hidden"].includes(
                                (element.type || "text").toLowerCase()
                            )
                        )
                    )
                """
            )

        except Exception as error:
            raise AssertionError(
                f"Could not validate healed input: {healed_locator}"
            ) from error

        if not is_editable:
            raise AssertionError(
                f"Healed element is not an editable text field: "
                f"{healed_locator}"
            )

        try:
            candidate.fill(value, timeout=5000)
        except PlaywrightTimeoutError as error:
            raise AssertionError(
                f"Could not fill healed input: {healed_locator}"
            ) from error

        print(f"Healed input filled successfully: {healed_locator}")
        return healed_locator