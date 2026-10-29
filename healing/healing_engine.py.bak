
from healing.failure_analyzer import analyze_locator_failure
from healing.healing_logger import record_healing_event


MAX_HEALING_ATTEMPTS = 3

SUPPORTED_TAGS = {
    "button",
    "input",
    "a",
    "select",
    "textarea",
}

ALL_CANDIDATE_TAGS = "button, input, a, select, textarea"


def heal_locator(page, failed_locator, expected_tag="button"):
    """
    Find and validate a replacement for a failed locator.

    Ollama proposes candidates, but deterministic validation
    decides whether the locator is safe to accept.

    Supported elements:
        button, input, a, select, textarea

    Only unique, visible elements with a matching live ID
    can be accepted.
    """

    print("\n" + "=" * 60)
    print("SELF-HEALING ENGINE ACTIVATED")
    print("=" * 60)
    print(f"Failed locator: {failed_locator}")
    print(f"Expected element: {expected_tag or 'any supported tag'}")

    # -------------------------------------------------
    # 1. SELECT CANDIDATE ELEMENTS
    # -------------------------------------------------

    if expected_tag in SUPPORTED_TAGS:
        selector = expected_tag
    else:
        selector = ALL_CANDIDATE_TAGS

    elements = page.locator(selector).evaluate_all(
        """
        elements => elements.map(el => ({
            tag: el.tagName.toLowerCase(),
            id: el.id || "",
            name: el.getAttribute("name") || "",
            type: el.getAttribute("type") || "",
            text: (el.innerText || "").trim(),
            value: el.value || "",
            placeholder: el.getAttribute("placeholder") || "",
            ariaLabel: el.getAttribute("aria-label") || "",
            role: el.getAttribute("role") || ""
        }))
        """
    )

    print("\nLive candidates:")
    for element in elements:
        print(element)

    if not elements:
        print("No candidate elements found.")

        record_healing_event(
            failed_locator,
            None,
            0,
            "failed",
            "No candidate elements found",
        )
        return None

    rejected_locators = set()

    # -------------------------------------------------
    # 2. ASK OLLAMA FOR REPLACEMENTS
    # -------------------------------------------------

    for attempt in range(1, MAX_HEALING_ATTEMPTS + 1):

        print("\n" + "-" * 60)
        print(f"HEALING ATTEMPT {attempt}/{MAX_HEALING_ATTEMPTS}")
        print("-" * 60)

        available_elements = [
            element
            for element in elements
            if element.get("id")
            and f"#{element['id']}" not in rejected_locators
        ]

        if not available_elements:
            print("No candidates remain.")
            break

        print("\nCandidates available:")
        for element in available_elements:
            print(element)

        element_information = "\n".join(
            str(element) for element in available_elements
        )

        print("\nSending candidates to Ollama...")

        suggested_locator = analyze_locator_failure(
            failed_locator,
            element_information,
        )

        print(f"\nOllama suggested: {suggested_locator}")

        # -------------------------------------------------
        # 3. REJECTION HELPER
        # -------------------------------------------------

        def reject(reason):
            print(f"\nREJECTED: {reason}")

            record_healing_event(
                failed_locator,
                suggested_locator,
                attempt,
                "rejected",
                reason,
            )

            if suggested_locator:
                rejected_locators.add(suggested_locator)

        # -------------------------------------------------
        # 4. VALIDATE MODEL OUTPUT
        # -------------------------------------------------

        if not suggested_locator:
            reject("Ollama returned an empty locator")
            continue

        if suggested_locator == failed_locator:
            reject("Ollama returned the original failed locator")
            continue

        if not suggested_locator.startswith("#"):
            reject("Suggestion is not a CSS ID locator")
            continue

        available_ids = {
            f"#{element['id']}"
            for element in available_elements
        }

        if suggested_locator not in available_ids:
            reject("Suggestion is not in the live candidate list")
            continue

        # -------------------------------------------------
        # 5. CHECK LOCATOR UNIQUENESS
        # -------------------------------------------------

        try:
            candidate = page.locator(suggested_locator)
            count = candidate.count()
        except Exception as error:
            reject(f"Invalid locator: {error}")
            continue

        if count != 1:
            reject(f"Locator matched {count} elements")
            continue

        print("Suggested locator exists.")
        print("Suggested locator is unique.")

        # -------------------------------------------------
        # 6. CHECK VISIBILITY
        # -------------------------------------------------

        try:
            candidate.wait_for(
                state="visible",
                timeout=5000,
            )
        except Exception:
            reject("Suggested element is not visible")
            continue

        print("Suggested element is visible.")

        # -------------------------------------------------
        # 7. INSPECT THE SELECTED ELEMENT
        # -------------------------------------------------

        try:
            candidate_data = candidate.evaluate(
                """
                element => ({
                    tag: element.tagName.toLowerCase(),
                    id: element.id || "",
                    name: element.getAttribute("name") || "",
                    type: element.getAttribute("type") || "",
                    text: (element.innerText || "").trim(),
                    value: element.value || "",
                    placeholder:
                        element.getAttribute("placeholder") || "",
                    ariaLabel:
                        element.getAttribute("aria-label") || "",
                    role: element.getAttribute("role") || ""
                })
                """
            )
        except Exception as error:
            reject(f"Could not inspect element: {error}")
            continue

        tag_name = candidate_data["tag"]

        if (
            expected_tag in SUPPORTED_TAGS
            and tag_name != expected_tag
        ):
            reject(
                f"Expected <{expected_tag}> but got <{tag_name}>"
            )
            continue

        print(f"Suggested element is a <{tag_name}>.")

        # -------------------------------------------------
        # 8. SEMANTIC VALIDATION FOR INPUT FIELDS
        # -------------------------------------------------

        if tag_name == "input":

            input_information = " ".join([
                candidate_data.get("id", ""),
                candidate_data.get("name", ""),
                candidate_data.get("placeholder", ""),
                candidate_data.get("ariaLabel", ""),
                candidate_data.get("type", ""),
            ]).lower()

            failed_lower = failed_locator.lower()

            if "search" in failed_lower:
                if not any(
                    term in input_information
                    for term in ("search", "query", "product")
                ):
                    reject(
                        "Candidate does not appear to be a search input"
                    )
                    continue

            elif (
                "username" in failed_lower
                or "user-name" in failed_lower
            ):
                if not any(
                    term in input_information
                    for term in (
                        "username",
                        "user-name",
                        "user_name",
                    )
                ):
                    reject(
                        "Candidate does not appear to be a username input"
                    )
                    continue

            elif "password" in failed_lower:
                if "password" not in input_information:
                    reject(
                        "Candidate does not appear to be a password input"
                    )
                    continue

            print("Input semantic validation passed.")

        # -------------------------------------------------
        # 9. SEMANTIC VALIDATION FOR LOGIN BUTTONS/LINKS
        # -------------------------------------------------

        failed_lower = failed_locator.lower()

        if (
            "login" in failed_lower
            and tag_name in ("button", "a")
        ):
            visible_text = candidate_data["text"].lower()
            element_id = candidate_data["id"].lower()
            aria_label = candidate_data["ariaLabel"].lower()
            role = candidate_data["role"].lower()

            candidate_information = " ".join([
                visible_text,
                element_id,
                aria_label,
                role,
            ])

            registration_terms = [
                "signup",
                "sign up",
                "register",
                "registration",
                "create account",
            ]

            login_terms = [
                "login",
                "log in",
                "signin",
                "sign in",
            ]

            if any(
                term in candidate_information
                for term in registration_terms
            ):
                reject(
                    "Registration element selected instead of Login"
                )
                continue

            if not any(
                term in candidate_information
                for term in login_terms
            ):
                reject(
                    "Candidate does not represent Login or Sign In"
                )
                continue

            print("Semantic validation passed.")
            print("Candidate represents Login / Sign In.")

        # -------------------------------------------------
        # 10. ACCEPT THE REPLACEMENT
        # -------------------------------------------------

        print("\n" + "=" * 60)
        print("SELF-HEALING RESULT: ACCEPTED")
        print("=" * 60)

        print(f"Old locator: {failed_locator}")
        print(f"New locator: {suggested_locator}")
        print(f"Healing attempt: {attempt}")

        record_healing_event(
            failed_locator,
            suggested_locator,
            attempt,
            "accepted",
            "Passed locator validation",
        )

        return suggested_locator

    # -------------------------------------------------
    # 11. ALL ATTEMPTS FAILED
    # -------------------------------------------------

    print("\n" + "=" * 60)
    print("SELF-HEALING RESULT: FAILED")
    print("=" * 60)

    print(f"Original locator: {failed_locator}")

    if rejected_locators:
        print("Rejected locators:")
        for locator in sorted(rejected_locators):
            print(f"  - {locator}")

    record_healing_event(
        failed_locator,
        None,
        MAX_HEALING_ATTEMPTS,
        "failed",
        "No valid replacement found",
    )

    return None
