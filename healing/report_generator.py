
import json
import re
from pathlib import Path

from healing.diagnostic_analyzer import diagnose_healing_failure


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_ROOT = PROJECT_ROOT / "test_reports"


def find_latest_report_dir() -> Path:
    """Find the most recent report directory containing report data."""

    if not REPORTS_ROOT.exists():
        raise FileNotFoundError(
            f"Report directory does not exist: {REPORTS_ROOT}"
        )

    report_dirs = [
        folder
        for folder in REPORTS_ROOT.iterdir()
        if folder.is_dir()
        and (
            (folder / "healing_events.json").exists()
            or (folder / "execution.log").exists()
        )
    ]

    if not report_dirs:
        raise FileNotFoundError(
            f"No report folders containing event or execution logs "
            f"were found in {REPORTS_ROOT}"
        )

    return max(
        report_dirs,
        key=lambda folder: folder.stat().st_mtime,
    )


def load_healing_events(report_dir: Path) -> list:
    """Load healing events from the selected report directory."""

    events_file = report_dir / "healing_events.json"

    if not events_file.exists():
        return []

    try:
        with events_file.open("r", encoding="utf-8") as file:
            events = json.load(file)
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError(
            f"Could not read {events_file}: {error}"
        ) from error

    if not isinstance(events, list):
        raise ValueError(
            f"Expected a JSON list in {events_file}"
        )

    return [
        event for event in events
        if isinstance(event, dict)
    ]


def event_value(event, key, default="unknown"):
    """Read a value from an event, supporting older event formats."""

    if key in event:
        return event[key]

    aliases = {
        "test": ("test_name",),
        "failed_locator": ("original_locator", "locator"),
        "ollama_suggestion": ("suggested_locator", "suggestion"),
        "reason": ("failure_reason",),
    }

    for alias in aliases.get(key, ()):
        if alias in event:
            return event[alias]

    return default


def event_status(event) -> str:
    """Normalize event status."""

    status = str(event_value(event, "status", default="unknown"))
    return status.strip().lower()


def event_test_name(event) -> str:
    """Get the test name from an event."""

    test_name = event_value(event, "test", default="unknown")
    return str(test_name)


def event_locator(event) -> str:
    """Get the original failed locator from an event."""

    locator = event_value(event, "failed_locator", default="unknown")
    return str(locator)


def event_suggestion(event) -> str:
    """Get the suggested replacement locator."""

    suggestion = event_value(
        event,
        "ollama_suggestion",
        default="none",
    )
    return str(suggestion)


def event_reason(event) -> str:
    """Get the event's recorded reason."""

    reason = event_value(event, "reason", default="No reason recorded")
    return str(reason)


def parse_execution_log(report_dir: Path) -> dict:
    """
    Parse pytest execution.log when available.

    Returns test outcomes and failure tracebacks without assuming
    that every report directory contains an execution log.
    """

    log_file = report_dir / "execution.log"

    result = {
        "available": log_file.exists(),
        "passed": [],
        "failed": [],
        "errors": [],
        "tracebacks": {},
        "raw_text": "",
    }

    if not log_file.exists():
        return result

    try:
        log_text = log_file.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        result["errors"].append(
            f"Could not read execution.log: {error}"
        )
        return result

    result["raw_text"] = log_text

    current_failure = None
    traceback_lines = []

    for line in log_text.splitlines():
        stripped = line.strip()

        # Collect traceback text when pytest marks a test as failed.
        if stripped.startswith("FAILED ") or stripped.startswith("ERROR "):
            if current_failure and traceback_lines:
                result["tracebacks"][current_failure] = "\n".join(
                    traceback_lines
                )

            current_failure = stripped
            traceback_lines = [line]
            result["failed" if stripped.startswith("FAILED ") else "errors"].append(
                stripped
            )
            continue

        if current_failure is not None:
            traceback_lines.append(line)

        # Capture simple pytest progress tokens where present.
        match = re.search(
            r"(?P<test>[A-Za-z_][\w.:/\[\]-]*)\s+PASSED\b",
            stripped,
        )
        if match:
            result["passed"].append(match.group("test"))

    if current_failure and traceback_lines:
        result["tracebacks"][current_failure] = "\n".join(
            traceback_lines
        )

    return result


def summarize_event_counts(events: list) -> dict:
    """Count healing event outcomes."""

    counts = {
        "total": len(events),
        "accepted": 0,
        "failed": 0,
        "rejected": 0,
        "other": 0,
    }

    for event in events:
        status = event_status(event)

        if status in {"accepted", "healed", "success", "successful"}:
            counts["accepted"] += 1
        elif status == "failed":
            counts["failed"] += 1
        elif status in {"rejected", "invalid", "declined"}:
            counts["rejected"] += 1
        else:
            counts["other"] += 1

    return counts


def generate_diagnostics(report_dir: Path, events: list) -> list:
    """
    Generate an evidence-based diagnosis for each failed healing operation.

    Prefer structured runtime evidence from the latest related event.
    The expected tag is read from recorded evidence rather than guessed.
    """

    failed_groups = {}

    for event in events:
        if event_status(event) != "failed":
            continue

        key = (event_test_name(event), event_locator(event))
        failed_groups.setdefault(key, []).append(event)

    diagnostics = []

    for (test_name, locator), failed_group in failed_groups.items():
        related_events = [
            event
            for event in events
            if event_test_name(event) == test_name
            and event_locator(event) == locator
        ]

        structured_evidence = {}

        # Later snapshots generally contain more completed attempts.
        for event in reversed(related_events):
            evidence = event.get("evidence")

            if isinstance(evidence, dict) and evidence:
                structured_evidence = evidence
                break

        evidence_lines = []

        for event in related_events:
            evidence_lines.append(
                f"Attempt {event_value(event, 'attempt', default='unknown')}: "
                f"status={event_status(event)}; "
                f"suggestion={event_suggestion(event)}; "
                f"reason={event_reason(event)}"
            )

        expected_tag = (
            structured_evidence.get("expected_tag")
            or "Unknown (not recorded)"
        )

        analyzer_evidence = dict(structured_evidence)
        analyzer_evidence["event_history"] = evidence_lines

        try:
            diagnosis = diagnose_healing_failure(
                failed_locator=locator,
                expected_tag=expected_tag,
                candidate_evidence=analyzer_evidence,
            )

            if not isinstance(diagnosis, dict):
                raise TypeError(
                    "Diagnostic analyzer returned an invalid result."
                )

        except Exception as error:
            diagnosis = {
                "root_cause_assessment": (
                    "A healing operation failed, but the underlying "
                    "cause has not been established by recorded evidence."
                ),
                "evidence": evidence_lines or [
                    "No healing event history was available."
                ],
                "recommended_fix": (
                    "Inspect the live DOM, original locator, eligible "
                    "candidate list, and healing validation logic."
                ),
                "confidence": "low",
                "limitations": (
                    f"Diagnostic error: {type(error).__name__}: {error}. "
                    "The cause remains unverified."
                ),
                "llm_opinion": (
                    "No usable Ollama opinion was obtained."
                ),
            }

        diagnosis["test"] = test_name
        diagnosis["failed_locator"] = locator
        diagnosis["expected_tag"] = expected_tag
        diagnostics.append(diagnosis)

    diagnostics_file = report_dir / "diagnostics.json"

    try:
        with diagnostics_file.open("w", encoding="utf-8") as file:
            json.dump(
                diagnostics,
                file,
                indent=4,
                ensure_ascii=False,
            )
    except OSError as error:
        print(f"Warning: Could not save diagnostics.json: {error}")

    return diagnostics


def generate_summary(
    report_dir: Path,
    events: list,
    diagnostics: list,
    execution: dict,
) -> Path:
    """Write the consolidated human-readable diagnostic report."""

    summary_file = report_dir / "healing_summary.txt"
    counts = summarize_event_counts(events)

    lines = [
        "SMARTKART SELF-HEALING DIAGNOSTIC REPORT",
        "=" * 48,
        "",
        f"Report directory: {report_dir}",
        "",
        "1. HEALING EVENT SUMMARY",
        "-" * 30,
        f"Total recorded events: {counts['total']}",
        f"Accepted suggestions: {counts['accepted']}",
        f"Failed healing operations: {counts['failed']}",
        f"Rejected/invalid suggestions: {counts['rejected']}",
        f"Other event statuses: {counts['other']}",
        "",
        "Note: Multiple events may belong to one healing operation "
        "because each retry can produce its own event.",
        "",
        "2. PYTEST EXECUTION SUMMARY",
        "-" * 30,
    ]

    if execution["available"]:
        lines.extend([
            f"Passed tests detected: {len(execution['passed'])}",
            f"Failed tests detected: {len(execution['failed'])}",
            f"Test errors detected: {len(execution['errors'])}",
            "",
        ])

        if execution["failed"]:
            lines.append("Failed test entries:")
            lines.extend(f"- {item}" for item in execution["failed"])
            lines.append("")

        if execution["errors"]:
            lines.append("Test error entries:")
            lines.extend(f"- {item}" for item in execution["errors"])
            lines.append("")

        if execution["tracebacks"]:
            lines.append("Failure tracebacks:")
            for test_name, traceback in execution["tracebacks"].items():
                lines.extend([
                    "",
                    f"Test: {test_name}",
                    traceback,
                ])
    else:
        lines.extend([
            "No execution.log was found in this report directory.",
            "Pytest outcome counts are unavailable.",
        ])

    lines.extend([
        "",
        "3. HEALING EVENT DETAILS",
        "-" * 30,
    ])

    if not events:
        lines.append("No healing events were recorded.")
    else:
        for index, event in enumerate(events, start=1):
            lines.extend([
                "",
                f"Event {index}",
                f"Test: {event_test_name(event)}",
                f"Original locator: {event_locator(event)}",
                f"Suggested locator: {event_suggestion(event)}",
                f"Attempt: {event_value(event, 'attempt')}",
                f"Status: {event_status(event)}",
                f"Reason: {event_reason(event)}",
            ])

            evidence = event.get("evidence")
            if isinstance(evidence, dict) and evidence:
                lines.append("Recorded runtime evidence:")
                lines.append(
                    json.dumps(
                        evidence,
                        indent=2,
                        ensure_ascii=False,
                    )
                )

    lines.extend([
        "",
        "4. EVIDENCE-BASED DIAGNOSTICS",
        "-" * 30,
    ])

    if not diagnostics:
        lines.append("No failed healing operations required diagnosis.")
    else:
        for index, diagnosis in enumerate(diagnostics, start=1):
            lines.extend([
                "",
                f"Diagnosis {index}",
                f"Test: {diagnosis.get('test', 'unknown')}",
                (
                    "Failed locator: "
                    f"{diagnosis.get('failed_locator', 'unknown')}"
                ),
                (
                    "Expected tag: "
                    f"{diagnosis.get('expected_tag', 'unknown')}"
                ),
                (
                    "Root-cause assessment: "
                    f"{diagnosis.get('root_cause_assessment', 'unknown')}"
                ),
                f"Confidence: {diagnosis.get('confidence', 'unknown')}",
                "Evidence:",
            ])

            evidence_items = diagnosis.get("evidence", [])
            if isinstance(evidence_items, list):
                lines.extend(
                    f"- {item}" for item in evidence_items
                )
            else:
                lines.append(f"- {evidence_items}")

            lines.extend([
                "",
                (
                    "Recommended investigation/fix: "
                    f"{diagnosis.get('recommended_fix', 'Not available')}"
                ),
                "",
                (
                    "Ollama opinion (hypothesis, not verified): "
                    f"{diagnosis.get('llm_opinion', 'Not available')}"
                ),
                "",
                (
                    "Limitations: "
                    f"{diagnosis.get('limitations', 'Not recorded')}"
                ),
            ])

    lines.extend([
        "",
        "5. INTERPRETATION NOTES",
        "-" * 30,
        "- Runtime evidence describes what was observed during inspection.",
        "- A rejected suggestion does not automatically identify the "
        "underlying cause of a failure.",
        "- Ollama output is a hypothesis, not independent proof.",
        "- A valid replacement locator does not prove the full UI action "
        "or business behavior succeeded.",
        "- Verify recommended changes against the live DOM and tests.",
        "",
        "End of report.",
    ])

    try:
        summary_file.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )
    except OSError as error:
        raise RuntimeError(
            f"Could not write summary report: {error}"
        ) from error

    return summary_file


def generate_report(report_dir: Path) -> None:
    """Generate diagnostics.json and healing_summary.txt."""

    events = load_healing_events(report_dir)
    execution = parse_execution_log(report_dir)

    diagnostics = generate_diagnostics(report_dir, events)

    summary_file = generate_summary(
        report_dir=report_dir,
        events=events,
        diagnostics=diagnostics,
        execution=execution,
    )

    print("Consolidated diagnostic report generated successfully.")
    print(f"Report directory: {report_dir}")
    print(f"Healing events processed: {len(events)}")
    print(f"Summary saved to: {summary_file}")
    print(f"Diagnoses saved to: {report_dir / 'diagnostics.json'}")


def main():
    """Generate a report for the latest available test report directory."""

    try:
        report_dir = find_latest_report_dir()
        generate_report(report_dir)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"Report generation failed: {error}")


if __name__ == "__main__":
    main()
