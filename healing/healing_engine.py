
from healing.failure_analyzer import analyze_locator_failure
from healing.healing_logger import record_healing_event


MAX_HEALING_ATTEMPTS = 3


def heal_locator(page, failed_locator, expected_tag="button"):
    """
    Find and validate a replacement for a failed locator.

    Ollama proposes candidates, but deterministic validation
    decides whether they can be accepted.

    All AI suggestions and validation outcomes are logged.
    """

    print("\n" + "=" * 60)
    print("SELF-HEALING ENGINE ACTIVATED")
    print("=" * 60)
    print(f"Failed locator: {failed_locator}")

    # -------------------------------------------------
    # SELECT CANDIDATE ELEMENTS
    # -------------------------------------------------

    if expected_tag == "button":
        selector = "button"
    elif expected_tag == "input":
        selector = "input"
    else:
        selector = "button, input, a, select, textarea"

    elements = page.locator(selector).evaluate_all(
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
            "No candidate elements found"
        )
        return None

    rejected_locators = set()

    # -------------------------------------------------
    # MULTIPLE OLLAMA ATTEMPTS
    # -------------------------------------------------

    for attempt in range(1, MAX_HEALING_ATTEMPTS + 1):

        print("\n" + "-" * 60)
        print(f"HEALING ATTEMPT {attempt}/{MAX_HEALING_ATTEMPTS}")
        print("-" * 60)

        available_elements = [
            element
            for element in elements
            if (
                f"#{element['id']}" if element.get("id") else ""
            ) not in rejected_locators
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
            element_information
        )

        print(f"\nOllama suggested: {suggested_locator}")

        # -------------------------------------------------
        # REJECTION HELPER
        # -------------------------------------------------

        def reject(reason):
            print(f"\nREJECTED: {reason}")

            record_healing_event(
                failed_locator,
                suggested_locator,
                attempt,
                "rejected",
                reason
            )

            if suggested_locator:
                rejected_locators.add(suggested_locator)

        # -------------------------------------------------
        # BASIC OUTPUT VALIDATION
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
            if element.get("id")
        }

        if suggested_locator not in available_ids:
            reject("Suggestion is not in the live candidate list")
            continue

        # -------------------------------------------------
        # CREATE PLAYWRIGHT LOCATOR
        # -------------------------------------------------

        try:
            candidate = page.locator(suggested_locator)
            count = candidate.count()
        except Exception as error:
            reject(f"Invalid locator: {error}")
            continue

        # -------------------------------------------------
        # UNIQUENESS
        # -------------------------------------------------

        if count != 1:
            reject(f"Locator matched {count} elements")
            continue

        print("Suggested locator exists.")
        print("Suggested locator is unique.")

        # -------------------------------------------------
        # VISIBILITY
        # -------------------------------------------------

        try:
            candidate.wait_for(
                state="visible",
                timeout=5000
            )
        except Exception:
            reject("Suggested element is not visible")
            continue

        print("Suggested element is visible.")

        # -------------------------------------------------
        # INSPECT ELEMENT
        # -------------------------------------------------

        try:
            candidate_data = candidate.evaluate(
                """
                element => ({
                    tag: element.tagName.toLowerCase(),
                    id: element.id || "",
                    text: (element.innerText || "").trim(),
                    ariaLabel:
                        element.getAttribute("aria-label") || ""
                })
                """
            )
        except Exception as error:
            reject(f"Could not inspect element: {error}")
            continue

        tag_name = candidate_data["tag"]

        visible_text = candidate_data["text"].strip().lower()
        element_id = candidate_data["id"].strip().lower()
        aria_label = candidate_data["ariaLabel"].strip().lower()

        # -------------------------------------------------
        # ELEMENT TYPE
        # -------------------------------------------------

        if expected_tag and tag_name != expected_tag:
            reject(
                f"Expected <{expected_tag}> but got <{tag_name}>"
            )
            continue

        print(f"Suggested element is a <{tag_name}>.")

        # -------------------------------------------------
        # SEMANTIC VALIDATION
        # -------------------------------------------------

        failed_lower = failed_locator.lower()

        candidate_information = (
            visible_text + " " + element_id + " " + aria_label
        )

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

            if any(
                term in candidate_information
                for term in registration_terms
            ):
                reject(
                    "Registration button selected instead of Login"
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
        # ACCEPT SUGGESTION
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
            "Passed locator validation"
        )

        return suggested_locator

    # -------------------------------------------------
    # ALL ATTEMPTS FAILED
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
        "No valid replacement found"
    )

    return None
