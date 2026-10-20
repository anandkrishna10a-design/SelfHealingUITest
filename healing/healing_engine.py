
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

    Collect all supported interactive elements so that explicit
    expected-tag validation can reject a real but incorrect element.

    Ollama proposes candidates; deterministic validation decides
    whether a replacement is safe to accept.
    """

    print("\n" + "=" * 60)
    print("SELF-HEALING ENGINE ACTIVATED")
    print("=" * 60)
    print(f"Failed locator: {failed_locator}")
    print(f"Expected element: {expected_tag or 'any supported tag'}")

    evidence = {
        "original_locator": failed_locator,
        "expected_tag": expected_tag,
        "original_locator_count": None,
        "original_locator_error": None,
        "candidate_selector": ALL_CANDIDATE_TAGS,
        "candidate_collection_error": None,
        "initial_candidates": [],
        "attempts": [],
    }

    # -------------------------------------------------
    # 1. INSPECT THE ORIGINAL LOCATOR
    # -------------------------------------------------

    try:
        evidence["original_locator_count"] = (
            page.locator(failed_locator).count()
        )
        print(
            "Original locator matches: "
            f"{evidence['original_locator_count']}"
        )
    except Exception as error:
        evidence["original_locator_error"] = (
            f"{type(error).__name__}: {error}"
        )
        print(f"Could not inspect original locator: {error}")

    # -------------------------------------------------
    # 2. COLLECT ALL SUPPORTED INTERACTIVE ELEMENTS
    # -------------------------------------------------

    # Important: Do not filter this collection by expected_tag.
    # Otherwise, a real button cannot reach the explicit tag
    # validation when the caller expects an input.
    try:
        elements = page.locator(
            ALL_CANDIDATE_TAGS
        ).evaluate_all(
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
                role: el.getAttribute("role") || "",
                visible: !!(
                    el.getClientRects().length &&
                    getComputedStyle(el).visibility !== "hidden" &&
                    getComputedStyle(el).display !== "none"
                )
            }))
            """
        )

        evidence["initial_candidates"] = elements

    except Exception as error:
        evidence["candidate_collection_error"] = (
            f"{type(error).__name__}: {error}"
        )
        elements = []

        print(f"Could not collect DOM candidates: {error}")

    print("\nLive candidates:")
    for element in elements:
        print(element)

    if not elements:
        reason = (
            "No supported candidate elements were found, or "
            "candidate collection failed."
        )

        print(f"\nHEALING FAILED: {reason}")

        record_healing_event(
            failed_locator,
            None,
            0,
            "failed",
            reason,
            evidence=evidence,
        )
        return None

    # Only candidates with IDs can be proposed as CSS ID locators.
    rejected_locators = set()

    # -------------------------------------------------
    # 3. ASK THE ANALYZER FOR REPLACEMENTS
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

        # Preserve the original analyzer's expected string interface.
        element_information = "\n".join(
            str(element) for element in available_elements
        )

        attempt_evidence = {
            "attempt": attempt,
            "suggestion": None,
            "available_candidates": available_elements,
            "rejection_reason": None,
            "validation_checks": {},
        }
        evidence["attempts"].append(attempt_evidence)

        # -------------------------------------------------
        # 4. REJECTION HELPER
        # -------------------------------------------------

        suggested_locator = None

        def reject(reason):
            """Record a rejected suggestion and its evidence."""

            print(f"\nREJECTED: {reason}")

            attempt_evidence["rejection_reason"] = reason

            if suggested_locator:
                rejected_locators.add(suggested_locator)

            record_healing_event(
                failed_locator,
                suggested_locator,
                attempt,
                "rejected",
                reason,
                evidence=evidence,
            )

        # -------------------------------------------------
        # 5. REQUEST A SUGGESTION FROM THE EXISTING ANALYZER
        # -------------------------------------------------

        try:
            suggested_locator = analyze_locator_failure(
                failed_locator,
                element_information,
            )
        except Exception as error:
            reject(
                "Locator analysis raised "
                f"{type(error).__name__}: {error}"
            )
            continue

        if isinstance(suggested_locator, str):
            suggested_locator = suggested_locator.strip()
        else:
            suggested_locator = None

        attempt_evidence["suggestion"] = suggested_locator

        print(f"\nAnalyzer suggested: {suggested_locator}")

        # -------------------------------------------------
        # 6. VALIDATE THE MODEL OUTPUT
        # -------------------------------------------------

        if not suggested_locator:
            reject("The analyzer returned an empty locator.")
            continue

        if suggested_locator == failed_locator:
            reject("The analyzer returned the original failed locator.")
            continue

        if not suggested_locator.startswith("#"):
            reject("Suggestion is not a CSS ID locator.")
            continue

        available_ids = {
            f"#{element['id']}"
            for element in available_elements
        }

        if suggested_locator not in available_ids:
            reject("Suggestion is not in the live candidate list.")
            continue

        # -------------------------------------------------
        # 7. CHECK UNIQUENESS
        # -------------------------------------------------

        try:
            candidate = page.locator(suggested_locator)
            count = candidate.count()

            attempt_evidence["validation_checks"]["match_count"] = count

        except Exception as error:
            reject(
                f"Invalid locator: {type(error).__name__}: {error}"
            )
            continue

        if count != 1:
            reject(f"Locator matched {count} elements.")
            continue

        print("Suggested locator exists and is unique.")

        # -------------------------------------------------
        # 8. CHECK VISIBILITY
        # -------------------------------------------------

        try:
            candidate.wait_for(
                state="visible",
                timeout=5000,
            )
            attempt_evidence["validation_checks"]["visible"] = True

        except Exception:
            attempt_evidence["validation_checks"]["visible"] = False
            reject("Suggested element is not visible.")
            continue

        print("Suggested element is visible.")

        # -------------------------------------------------
        # 9. INSPECT THE SELECTED ELEMENT
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
                    role: element.getAttribute("role") || "",
                    visible: !!(
                        element.getClientRects().length &&
                        getComputedStyle(element).visibility !== "hidden" &&
                        getComputedStyle(element).display !== "none"
                    )
                })
                """
            )

            attempt_evidence["validation_checks"][
                "observed_tag"
            ] = candidate_data["tag"]

        except Exception as error:
            reject(
                "Could not inspect element: "
                f"{type(error).__name__}: {error}"
            )
            continue

        tag_name = candidate_data["tag"]

        # -------------------------------------------------
        # 10. VALIDATE THE EXPECTED ELEMENT TAG
        # -------------------------------------------------

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
        # 11. SEMANTIC VALIDATION FOR INPUT FIELDS
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

            if any(
                term in failed_lower
                for term in ("search", "query", "filter")
            ):
                if not any(
                    term in input_information
                    for term in ("search", "query", "filter", "product")
                ):
                    reject(
                        "Candidate does not appear to be a "
                        "search/filter input."
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
                        "Candidate does not appear to be "
                        "a username input."
                    )
                    continue

            elif "password" in failed_lower:
                if "password" not in input_information:
                    reject(
                        "Candidate does not appear to be "
                        "a password input."
                    )
                    continue

            print("Input semantic validation passed.")

        # -------------------------------------------------
        # 12. SEMANTIC VALIDATION FOR LOGIN BUTTONS/LINKS
        # -------------------------------------------------

        failed_lower = failed_locator.lower()

        if "login" in failed_lower and tag_name in ("button", "a"):

            candidate_information = " ".join([
                candidate_data.get("text", ""),
                candidate_data.get("id", ""),
                candidate_data.get("ariaLabel", ""),
                candidate_data.get("role", ""),
            ]).lower()

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
                    "Registration element selected instead of Login."
                )
                continue

            if not any(
                term in candidate_information
                for term in login_terms
            ):
                reject(
                    "Candidate does not represent Login or Sign In."
                )
                continue

            print("Login semantic validation passed.")

        # -------------------------------------------------
        # 13. ACCEPT THE REPLACEMENT
        # -------------------------------------------------

        attempt_evidence["validation_checks"]["accepted"] = True
        attempt_evidence["rejection_reason"] = None
        attempt_evidence["selected_candidate"] = candidate_data

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
            "Passed locator validation.",
            evidence=evidence,
        )

        return suggested_locator

    # -------------------------------------------------
    # 14. ALL ATTEMPTS FAILED
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
        "No valid replacement found.",
        evidence=evidence,
    )

    return None
