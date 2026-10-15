from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError
)

from healing.healing_engine import heal_locator


def self_healing_click(
    page: Page,
    original_locator: str,
    expected_tag: str = "button"
):
    """
    Attempts to click an element using the original locator.

    If the original locator fails because the element cannot
    be found, the self-healing engine is activated.

    The AI-generated locator is validated before it is used.

    Returns:
        The locator that successfully performed the click.
    """

    # =====================================================
    # 1. TRY ORIGINAL LOCATOR
    # =====================================================

    try:

        page.locator(
            original_locator
        ).click(timeout=3000)

        print(
            f"\n✅ Original locator worked: "
            f"{original_locator}"
        )

        return original_locator

    # =====================================================
    # 2. ORIGINAL LOCATOR FAILED
    # =====================================================

    except PlaywrightTimeoutError:

        print("\n" + "=" * 60)
        print("PLAYWRIGHT LOCATOR FAILURE DETECTED")
        print("=" * 60)

        print(
            f"Original locator failed: "
            f"{original_locator}"
        )

        # =================================================
        # 3. ACTIVATE SELF-HEALING ENGINE
        # =================================================

        healed_locator = heal_locator(
            page=page,
            failed_locator=original_locator,
            expected_tag=expected_tag
        )

        # =================================================
        # 4. CHECK HEALING RESULT
        # =================================================

        if healed_locator is None:

            raise AssertionError(
                "Self-healing failed. "
                f"No valid replacement was found for "
                f"{original_locator}"
            )

        # =================================================
        # 5. RETRY ACTION USING HEALED LOCATOR
        # =================================================

        print(
            f"\nRetrying with healed locator: "
            f"{healed_locator}"
        )

        try:

            page.locator(
                healed_locator
            ).click(timeout=5000)

        except PlaywrightTimeoutError:

            raise AssertionError(
                "Self-healing produced a locator, "
                "but Playwright could not click it: "
                f"{healed_locator}"
            )

        print(
            "✅ Healed locator clicked successfully."
        )

        # =================================================
        # 6. RETURN HEALED LOCATOR
        # =================================================

        return healed_locator