
import json
import re

from healing.ollama_client import ask_ollama


SUPPORTED_TAGS = {
    "a",
    "button",
    "input",
    "select",
    "textarea",
}

TAG_WORDS = {
    "a": ("<a", "tag a", "tag 'a'", "anchor", "link element"),
    "button": ("<button", "tag button", "button element"),
    "input": ("<input", "tag input", "input element"),
    "select": ("<select", "tag select", "select element"),
    "textarea": ("<textarea", "tag textarea", "textarea element"),
}


def _parse_evidence(candidate_evidence):
    """Convert supplied evidence into a dictionary when possible."""

    if isinstance(candidate_evidence, dict):
        return candidate_evidence

    if isinstance(candidate_evidence, str):
        try:
            parsed = json.loads(candidate_evidence)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return {}


def _get_attempts(evidence):
    """Return valid attempt records."""

    attempts = evidence.get("attempts", [])

    if not isinstance(attempts, list):
        return []

    return [
        attempt
        for attempt in attempts
        if isinstance(attempt, dict)
    ]


def _find_candidate(locator, evidence, attempt=None):
    """Find candidate information for a suggested CSS ID locator."""

    if not isinstance(locator, str) or not locator.startswith("#"):
        return None

    element_id = locator[1:]
    candidate_groups = []

    if isinstance(attempt, dict):
        candidate_groups.append(
            attempt.get("available_candidates", [])
        )

    candidate_groups.append(
        evidence.get("initial_candidates", [])
    )

    for candidates in candidate_groups:
        if not isinstance(candidates, list):
            continue

        for candidate in candidates:
            if (
                isinstance(candidate, dict)
                and candidate.get("id") == element_id
            ):
                return candidate

    return None


def _summarize_attempts(evidence):
    """Build concise summaries of recorded validation attempts."""

    summaries = []

    for attempt in _get_attempts(evidence):
        number = attempt.get("attempt", "unknown")
        suggestion = attempt.get("suggestion")
        reason = attempt.get("rejection_reason")
        checks = attempt.get("validation_checks", {})

        if not isinstance(checks, dict):
            checks = {}

        candidate = _find_candidate(
            suggestion,
            evidence,
            attempt,
        )

        summary = {
            "attempt": number,
            "suggestion": suggestion,
            "rejection_reason": reason,
            "validation_checks": checks,
        }

        if candidate:
            summary["observed_candidate"] = {
                "tag": candidate.get("tag"),
                "id": candidate.get("id"),
                "text": candidate.get("text"),
                "type": candidate.get("type"),
                "placeholder": candidate.get("placeholder"),
                "visible": candidate.get("visible"),
            }
        elif checks.get("observed_tag"):
            summary["observed_candidate"] = {
                "tag": checks["observed_tag"],
                "id": (
                    suggestion[1:]
                    if isinstance(suggestion, str)
                    and suggestion.startswith("#")
                    else None
                ),
            }

        summaries.append(summary)

    return summaries


def _collect_observations(failed_locator, expected_tag, evidence):
    """Build factual observations from runtime evidence."""

    observations = []

    original_count = evidence.get("original_locator_count")
    candidates = evidence.get("initial_candidates", [])

    if original_count is not None:
        observations.append(
            f"Original locator {failed_locator!r} matched "
            f"{original_count} element(s) at inspection time."
        )
    else:
        observations.append(
            "The original locator match count was not recorded."
        )

    if evidence.get("original_locator_error"):
        observations.append(
            "Original locator inspection error: "
            f"{evidence['original_locator_error']}"
        )

    if evidence.get("candidate_collection_error"):
        observations.append(
            "Candidate collection error: "
            f"{evidence['candidate_collection_error']}"
        )

    observations.append(f"Expected tag: {expected_tag}.")

    if isinstance(candidates, list):
        observations.append(
            f"Initial supported candidate count: {len(candidates)}."
        )

    for attempt in _summarize_attempts(evidence):
        number = attempt["attempt"]
        suggestion = attempt.get("suggestion")
        reason = attempt.get("rejection_reason")
        candidate = attempt.get("observed_candidate")

        if reason:
            observations.append(
                f"Attempt {number}: {suggestion!r} was rejected. "
                f"Recorded reason: {reason}"
            )
        elif attempt.get("validation_checks", {}).get("accepted"):
            observations.append(
                f"Attempt {number}: {suggestion!r} passed the "
                "recorded locator validation checks."
            )

        if candidate:
            observations.append(
                f"Attempt {number}: recorded candidate details: "
                f"tag={candidate.get('tag', 'unknown')}, "
                f"id={candidate.get('id') or '(no ID)'}, "
                f"text={candidate.get('text') or '(empty)'!r}, "
                f"visible={candidate.get('visible', 'unknown')}."
            )

        checks = attempt.get("validation_checks", {})

        if "match_count" in checks:
            observations.append(
                f"Attempt {number}: locator match count was "
                f"{checks['match_count']}."
            )

        if "visible" in checks:
            observations.append(
                f"Attempt {number}: visibility check was "
                f"{checks['visible']}."
            )

    return observations


def _build_deterministic_diagnosis(
    failed_locator,
    expected_tag,
    evidence,
):
    """Determine the diagnosis using recorded facts, not model output."""

    original_count = evidence.get("original_locator_count")
    candidates = evidence.get("initial_candidates", [])
    attempts = _get_attempts(evidence)

    rejected_attempts = [
        attempt
        for attempt in attempts
        if attempt.get("rejection_reason")
    ]

    accepted_attempts = [
        attempt
        for attempt in attempts
        if attempt.get("validation_checks", {}).get("accepted")
    ]

    # Check specific rejection evidence FIRST. Otherwise, a zero match
    # count can hide a more actionable wrong-tag validation result.
    wrong_tag_attempt = next(
        (
            attempt
            for attempt in rejected_attempts
            if str(attempt.get("rejection_reason", "")).startswith(
                "Expected <"
            )
            and " but got <" in str(
                attempt.get("rejection_reason", "")
            )
        ),
        None,
    )

    if wrong_tag_attempt:
        reason = str(wrong_tag_attempt["rejection_reason"])
        suggestion = wrong_tag_attempt.get("suggestion")

        assessment = (
            f"The original locator {failed_locator!r} matched "
            f"{original_count} element(s) at inspection time. "
            f"The replacement {suggestion!r} was rejected because "
            f"its element type did not match the expected type: {reason}. "
            "The rejected candidate must not be treated as a valid replacement."
        )

        recommended_fix = (
            f"Do not use {suggestion!r} as the replacement for this "
            f"{expected_tag!r} target. Inspect the live DOM for the "
            "intended control, confirm its purpose and tag, and ask the "
            "healing analyzer to propose a candidate of the correct type. "
            "Retest the resulting locator before accepting it."
        )

        confidence = "high"
        limitations = (
            "The expected-versus-observed tag mismatch is directly "
            "recorded. The evidence does not establish why the original "
            "locator stopped matching or whether the rejected element "
            "serves a related purpose."
        )

    elif original_count == 0 and isinstance(candidates, list) and candidates:
        assessment = (
            f"The original locator {failed_locator!r} matched zero "
            "elements at inspection time, while supported DOM candidates "
            "were present. A locator-to-DOM mismatch is established, "
            "but its underlying cause is not."
        )

        recommended_fix = (
            "Inspect the intended control in the live DOM. Verify its "
            "role, accessible name, label, stable attributes, and purpose "
            "before updating the original locator."
        )

        confidence = "moderate"
        limitations = (
            "A single DOM inspection cannot establish whether the mismatch "
            "resulted from a code change, navigation, dynamic content, "
            "timing, or another cause."
        )

    elif original_count == 0:
        assessment = (
            f"The original locator {failed_locator!r} matched zero "
            "elements at inspection time. The available evidence does "
            "not establish the cause or verify a replacement."
        )

        recommended_fix = (
            "Reproduce the failure and inspect the current page state, "
            "navigation, timing, and intended DOM element before changing "
            "the locator."
        )

        confidence = "low"
        limitations = (
            "No sufficient candidate evidence was recorded to establish "
            "a safe replacement."
        )

    elif isinstance(original_count, int) and original_count > 1:
        assessment = (
            f"The original locator {failed_locator!r} matched "
            f"{original_count} elements at inspection time and was "
            "therefore not unique."
        )

        recommended_fix = (
            "Narrow the locator using verified semantic information or "
            "stable attributes, then assert that it identifies exactly "
            "one intended element."
        )

        confidence = "moderate"
        limitations = (
            "The match count alone does not establish which element "
            "was intended."
        )

    elif accepted_attempts:
        assessment = (
            "At least one suggested replacement passed the recorded "
            "validation checks. This confirms locator validation, not "
            "the success of the complete UI action."
        )

        recommended_fix = (
            "Verify that the accepted locator identifies the intended "
            "control and that the subsequent interaction and expected "
            "application behavior succeed."
        )

        confidence = "moderate"
        limitations = (
            "Locator validation does not prove that a click, submission, "
            "or business operation completed successfully."
        )

    elif rejected_attempts:
        first = rejected_attempts[0]
        reason = str(first.get("rejection_reason", "")).strip()
        suggestion = first.get("suggestion")

        assessment = (
            "The healing validator rejected one or more replacement "
            "suggestions. The recorded rejection reason describes a "
            "validation outcome and does not independently establish "
            "the cause of the original failure."
        )

        if "not in the live candidate list" in reason.lower():
            recommended_fix = (
                f"The suggestion {suggestion!r} was not present in the "
                "eligible candidate list for that attempt. Inspect the "
                "recorded candidate list and select a unique, verified "
                "element that serves the intended purpose."
            )
        elif "not visible" in reason.lower():
            recommended_fix = (
                "Inspect the candidate's visibility and page state. "
                "Do not accept it until it is visible and confirmed "
                "to be the intended control."
            )
        else:
            recommended_fix = (
                "Review the recorded rejection reason and candidate "
                "attributes. Verify the intended control before using "
                "a replacement locator."
            )

        confidence = "low"
        limitations = (
            "Rejected suggestions do not by themselves establish why the "
            "original locator failed or whether the application is defective."
        )

    else:
        assessment = (
            "The recorded evidence is insufficient to determine "
            "the underlying cause."
        )

        recommended_fix = (
            "Capture the original locator count, relevant live candidates, "
            "and validation outcomes during a reproducible failure."
        )

        confidence = "low"
        limitations = (
            "The recorded evidence is incomplete for a definitive diagnosis."
        )

    return {
        "root_cause_assessment": assessment,
        "recommended_fix": recommended_fix,
        "confidence": confidence,
        "limitations": limitations,
    }


def _response_is_consistent(opinion, expected_tag, evidence):
    """Reject model opinions that contradict recorded candidate evidence."""

    if not isinstance(opinion, str) or not opinion.strip():
        return False

    normalized = opinion.lower()
    attempts = _summarize_attempts(evidence)

    known_ids = set()

    failed_locator = evidence.get("original_locator", "")
    if isinstance(failed_locator, str) and failed_locator.startswith("#"):
        known_ids.add(failed_locator[1:])

    candidates = evidence.get("initial_candidates", [])
    if isinstance(candidates, list):
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("id"):
                known_ids.add(str(candidate["id"]))

    for attempt in attempts:
        suggestion = attempt.get("suggestion")
        if isinstance(suggestion, str) and suggestion.startswith("#"):
            known_ids.add(suggestion[1:])

    mentioned_ids = set(
        re.findall(r"#([A-Za-z_][\w-]*)", opinion)
    )

    if not mentioned_ids.issubset(known_ids):
        return False

    relevant_tags = (
        {expected_tag}
        if expected_tag in SUPPORTED_TAGS
        else set()
    )

    for attempt in attempts:
        reason = str(attempt.get("rejection_reason") or "")
        candidate = attempt.get("observed_candidate")

        if not candidate:
            continue

        observed_tag = candidate.get("tag")

        if reason and observed_tag in SUPPORTED_TAGS:
            relevant_tags.add(observed_tag)

    for word, tag in {
        "anchor": "a",
        "link element": "a",
    }.items():
        if word in normalized and tag not in relevant_tags:
            return False

    for tag, phrases in TAG_WORDS.items():
        if tag in relevant_tags:
            continue

        if any(phrase in normalized for phrase in phrases):
            return False

    return True


def _get_llm_opinion(failed_locator, expected_tag, evidence):
    """Request a brief hypothesis and reject unsupported model claims."""

    relevant_facts = {
        "failed_locator": failed_locator,
        "expected_tag": expected_tag,
        "original_locator_count": evidence.get(
            "original_locator_count"
        ),
        "candidate_collection_error": evidence.get(
            "candidate_collection_error"
        ),
        "attempts": _summarize_attempts(evidence),
    }

    fallback = (
        "The recorded evidence establishes the validation outcome, "
        "but does not establish an additional underlying cause."
    )

    prompt = f"""
You are assisting with Playwright locator-failure diagnosis.

Use only the facts below. Do not infer unrecorded facts.

FACTS:
{json.dumps(relevant_facts, indent=2, ensure_ascii=False)}

Return exactly one JSON object:
{{"llm_opinion": "one or two concise sentences"}}

Rules:
- Describe the recorded validation outcome accurately.
- For a wrong-tag rejection, state the expected and observed tags exactly.
- Never replace an observed tag with another tag.
- Do not invent candidate IDs, attributes, visibility states, or behaviors.
- Do not claim the application is broken without evidence.
- Do not claim a fix was applied or an action succeeded.
- If the cause is unknown, say it is unknown.
- Return JSON only.
"""

    try:
        response = ask_ollama(prompt)
    except Exception:
        return fallback

    if not response or response.startswith("ERROR:"):
        return fallback

    cleaned = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        response.strip(),
        flags=re.IGNORECASE,
    )

    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return fallback

    if not isinstance(parsed, dict):
        return fallback

    opinion = parsed.get("llm_opinion")

    if not isinstance(opinion, str) or not opinion.strip():
        return fallback

    opinion = opinion.strip()

    if not _response_is_consistent(opinion, expected_tag, evidence):
        return (
            "Ollama's proposed explanation was omitted because it could "
            "not be verified against the recorded candidate evidence. "
            "Use the deterministic assessment and recorded validation "
            "reason above."
        )

    return opinion


def diagnose_healing_failure(
    failed_locator,
    expected_tag,
    candidate_evidence,
):
    """Return an evidence-based diagnosis and a separate AI hypothesis."""

    evidence = _parse_evidence(candidate_evidence)
    evidence.setdefault("original_locator", failed_locator)

    observations = _collect_observations(
        failed_locator,
        expected_tag,
        evidence,
    )

    diagnosis = _build_deterministic_diagnosis(
        failed_locator,
        expected_tag,
        evidence,
    )

    llm_opinion = _get_llm_opinion(
        failed_locator,
        expected_tag,
        evidence,
    )

    return {
        "root_cause_assessment": diagnosis["root_cause_assessment"],
        "evidence": observations,
        "recommended_fix": diagnosis["recommended_fix"],
        "confidence": diagnosis["confidence"],
        "limitations": diagnosis["limitations"],
        "llm_opinion": llm_opinion,
    }
