from healing.failure_analyzer import analyze_locator_failure


MAX_HEALING_ATTEMPTS = 3


def heal_locator(
    page,
    failed_locator,
    expected_tag="button"
):
    """
    Attempts to find a safe replacement for a failed
    Playwright locator.

    Ollama may make multiple attempts.

    Every suggestion must pass deterministic validation
    before it can be returned.

    Rejected suggestions are removed from subsequent
    attempts so Ollama cannot repeatedly choose the
    same incorrect element.

    Returns:
        Valid healed CSS locator

    Returns None:
        If no safe replacement is found
    """

    print("\n" + "=" * 60)
    print("SELF-HEALING ENGINE ACTIVATED")
    print("=" * 60)

    print(
        f"Failed locator: "
        f"{failed_locator}"
    )

    # =====================================================
    # 1. SELECT CANDIDATE ELEMENT TYPE
    # =====================================================

    if expected_tag == "button":

        selector = "button"

    elif expected_tag == "input":

        selector = "input"

    else:

        selector = (
            "button, input, a, "
            "select, textarea"
        )

    # =====================================================
    # 2. CAPTURE LIVE CANDIDATES
    # =====================================================

    elements = page.locator(
        selector
    ).evaluate_all(
        """
        elements => elements.map(el => ({
            tag: el.tagName.toLowerCase(),
            id: el.id || "",
            name: el.getAttribute("name") || "",
            type: el.getAttribute("type") || "",
            text: (el.innerText || "").trim(),
            placeholder:
                el.getAttribute("placeholder") || "",
            ariaLabel:
                el.getAttribute("aria-label") || ""
        }))
        """
    )

    print("\nLive candidates:")

    for element in elements:

        print(element)

    if not elements:

        print(
            "\n❌ No candidate elements found."
        )

        return None

    # =====================================================
    # 3. TRACK REJECTED LOCATORS
    # =====================================================

    rejected_locators = set()

    # =====================================================
    # 4. MULTIPLE HEALING ATTEMPTS
    # =====================================================

    for attempt in range(
        1,
        MAX_HEALING_ATTEMPTS + 1
    ):

        print("\n" + "-" * 60)

        print(
            f"HEALING ATTEMPT "
            f"{attempt}/{MAX_HEALING_ATTEMPTS}"
        )

        print("-" * 60)

        # -------------------------------------------------
        # Remove rejected candidates
        # -------------------------------------------------

        available_elements = []

        for element in elements:

            element_id = element.get(
                "id",
                ""
            )

            css_locator = (
                f"#{element_id}"
                if element_id
                else ""
            )

            if (
                css_locator
                not in rejected_locators
            ):

                available_elements.append(
                    element
                )

        if not available_elements:

            print(
                "\n❌ No candidates remain "
                "after validation."
            )

            break

        print(
            "\nCandidates available "
            "for this attempt:"
        )

        for element in available_elements:

            print(element)

        # -------------------------------------------------
        # Prepare candidate information
        # -------------------------------------------------

        element_information = "\n".join(
            str(element)
            for element
            in available_elements
        )

        # -------------------------------------------------
        # Ask Ollama
        # -------------------------------------------------

        print(
            "\nSending candidates "
            "to Ollama..."
        )

        suggested_locator = (
            analyze_locator_failure(
                failed_locator,
                element_information
            )
        )

        print(
            f"\nOllama suggested: "
            f"{suggested_locator}"
        )

        # =================================================
        # 5. BASIC OUTPUT VALIDATION
        # =================================================

        if not suggested_locator:

            print(
                "\n❌ Ollama returned "
                "an empty locator."
            )

            continue

        if (
            suggested_locator
            == failed_locator
        ):

            print(
                "\n❌ Ollama returned "
                "the original failed locator."
            )

            rejected_locators.add(
                suggested_locator
            )

            continue

        if not suggested_locator.startswith(
            "#"
        ):

            print(
                "\n❌ Ollama did not return "
                "a CSS ID locator."
            )

            continue

        # -------------------------------------------------
        # Make sure Ollama selected a LIVE candidate
        # -------------------------------------------------

        available_ids = {
            f"#{element['id']}"
            for element
            in available_elements
            if element.get("id")
        }

        if (
            suggested_locator
            not in available_ids
        ):

            print(
                "\n❌ Ollama selected a locator "
                "that is not in the current "
                "candidate list."
            )

            rejected_locators.add(
                suggested_locator
            )

            continue

        # =================================================
        # 6. CREATE PLAYWRIGHT LOCATOR
        # =================================================

        try:

            candidate = page.locator(
                suggested_locator
            )

            count = candidate.count()

        except Exception as error:

            print(
                "\n❌ Invalid locator "
                "returned by Ollama."
            )

            print(
                f"Reason: {error}"
            )

            rejected_locators.add(
                suggested_locator
            )

            continue

        # =================================================
        # 7. CHECK UNIQUENESS
        # =================================================

        if count != 1:

            print(
                f"\n❌ Suggested locator "
                f"matched {count} elements."
            )

            rejected_locators.add(
                suggested_locator
            )

            continue

        print(
            "✅ Suggested locator exists."
        )

        print(
            "✅ Suggested locator is unique."
        )

        # =================================================
        # 8. CHECK VISIBILITY
        # =================================================

        try:

            candidate.wait_for(
                state="visible",
                timeout=5000
            )

        except Exception:

            print(
                "\n❌ Suggested element "
                "is not visible."
            )

            rejected_locators.add(
                suggested_locator
            )

            continue

        print(
            "✅ Suggested element is visible."
        )

        # =================================================
        # 9. INSPECT ELEMENT
        # =================================================

        try:

            candidate_data = (
                candidate.evaluate(
                    """
                    element => ({
                        tag:
                            element.tagName
                            .toLowerCase(),

                        id:
                            element.id || "",

                        text:
                            (element.innerText || "")
                            .trim(),

                        ariaLabel:
                            element.getAttribute(
                                "aria-label"
                            ) || ""
                    })
                    """
                )
            )

        except Exception as error:

            print(
                "\n❌ Could not inspect "
                "suggested element."
            )

            print(
                f"Reason: {error}"
            )

            rejected_locators.add(
                suggested_locator
            )

            continue

        tag_name = (
            candidate_data["tag"]
        )

        visible_text = (
            candidate_data["text"]
            .strip()
            .lower()
        )

        element_id = (
            candidate_data["id"]
            .strip()
            .lower()
        )

        aria_label = (
            candidate_data["ariaLabel"]
            .strip()
            .lower()
        )

        # =================================================
        # 10. CHECK ELEMENT TYPE
        # =================================================

        if (
            expected_tag
            and tag_name != expected_tag
        ):

            print(
                f"\n❌ Expected "
                f"<{expected_tag}> "
                f"but Ollama selected "
                f"<{tag_name}>."
            )

            rejected_locators.add(
                suggested_locator
            )

            continue

        print(
            f"✅ Suggested element is "
            f"a <{tag_name}>."
        )

        # =================================================
        # 11. SEMANTIC VALIDATION
        # =================================================

        failed_lower = (
            failed_locator.lower()
        )

        candidate_information = (
            visible_text
            + " "
            + element_id
            + " "
            + aria_label
        )

        # -------------------------------------------------
        # LOGIN / SIGN-IN
        # -------------------------------------------------

        if "login" in failed_lower:

            login_terms = [
                "login",
                "log in",
                "signin",
                "sign in"
            ]

            registration_terms = [
                "signup",
                "sign up",
                "register",
                "registration",
                "create account"
            ]

            # ---------------------------------------------
            # Reject registration candidate
            # ---------------------------------------------

            if any(
                term
                in candidate_information
                for term
                in registration_terms
            ):

                print(
                    "\n❌ SEMANTIC "
                    "VALIDATION FAILED"
                )

                print(
                    "Ollama selected a "
                    "registration button "
                    "instead of Login."
                )

                print(
                    f"Rejected locator: "
                    f"{suggested_locator}"
                )

                rejected_locators.add(
                    suggested_locator
                )

                print(
                    "\nRetrying healing "
                    "without this candidate..."
                )

                continue

            # ---------------------------------------------
            # Require login meaning
            # ---------------------------------------------

            if not any(
                term
                in candidate_information
                for term
                in login_terms
            ):

                print(
                    "\n❌ SEMANTIC "
                    "VALIDATION FAILED"
                )

                print(
                    "Suggested element does "
                    "not represent Login "
                    "or Sign In."
                )

                print(
                    f"Rejected locator: "
                    f"{suggested_locator}"
                )

                rejected_locators.add(
                    suggested_locator
                )

                continue

            print(
                "✅ Semantic validation passed."
            )

            print(
                "✅ Candidate represents "
                "Login / Sign In."
            )

        # =================================================
        # 12. SUCCESS
        # =================================================

        print(
            "\n" + "=" * 60
        )

        print(
            "SELF-HEALING RESULT: ACCEPTED"
        )

        print(
            "=" * 60
        )

        print(
            f"Old locator: "
            f"{failed_locator}"
        )

        print(
            f"New locator: "
            f"{suggested_locator}"
        )

        print(
            f"Healing attempt: "
            f"{attempt}"
        )

        return suggested_locator

    # =====================================================
    # 13. ALL ATTEMPTS FAILED
    # =====================================================

    print(
        "\n" + "=" * 60
    )

    print(
        "SELF-HEALING RESULT: FAILED"
    )

    print(
        "=" * 60
    )

    print(
        f"Original locator: "
        f"{failed_locator}"
    )

    if rejected_locators:

        print(
            "Rejected locators:"
        )

        for locator in rejected_locators:

            print(
                f"  - {locator}"
            )

    return None