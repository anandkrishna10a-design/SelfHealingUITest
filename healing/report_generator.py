
import json
from collections import Counter
from pathlib import Path
from datetime import datetime


def find_latest_report_dir() -> Path:
    """Find the latest test report directory containing healing events."""

    project_root = Path(__file__).resolve().parent.parent
    reports_dir = project_root / "test_reports"

    if not reports_dir.exists():
        raise FileNotFoundError(
            f"Report directory not found: {reports_dir}"
        )

    report_dirs = [
        path
        for path in reports_dir.iterdir()
        if path.is_dir()
        and (path / "healing_events.json").exists()
    ]

    if not report_dirs:
        raise FileNotFoundError(
            "No report directory containing healing_events.json was found."
        )

    return max(report_dirs, key=lambda path: path.stat().st_mtime)


def load_events(events_file: Path) -> list:
    """Load healing events from the JSON report."""

    with events_file.open("r", encoding="utf-8") as file:
        events = json.load(file)

    if not isinstance(events, list):
        raise ValueError(
            "Expected healing_events.json to contain a JSON list."
        )

    return events


def generate_summary(report_dir: Path, events: list) -> str:
    """Build a readable summary of the healing events."""

    total_events = len(events)

    statuses = Counter(
        str(event.get("status", "unknown")).lower()
        for event in events
    )

    accepted = statuses.get("accepted", 0)
    rejected = statuses.get("rejected", 0)
    failed = statuses.get("failed", 0)

    other_statuses = sum(
        count
        for status, count in statuses.items()
        if status not in {"accepted", "rejected", "failed"}
    )

    test_names = {
        event.get("test")
        for event in events
        if event.get("test")
    }

    attempts = [
        event.get("attempt")
        for event in events
        if isinstance(event.get("attempt"), (int, float))
    ]

    lines = [
        "SELF-HEALING UI TEST AUTOMATION REPORT",
        "=" * 45,
        "",
        f"Report folder: {report_dir}",
        f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "OVERALL SUMMARY",
        "-" * 45,
        f"Total healing events: {total_events}",
        f"Accepted suggestions: {accepted}",
        f"Rejected suggestions: {rejected}",
        f"Failed healing events: {failed}",
        f"Other statuses: {other_statuses}",
        f"Distinct test names recorded: {len(test_names)}",
    ]

    if attempts:
        lines.append(f"Highest recorded attempt number: {max(attempts)}")

    lines.extend([
        "",
        "STATUS BREAKDOWN",
        "-" * 45,
    ])

    if statuses:
        for status, count in sorted(statuses.items()):
            lines.append(f"{status}: {count}")
    else:
        lines.append("No healing events were recorded.")

    lines.extend([
        "",
        "EVENT DETAILS",
        "-" * 45,
    ])

    if not events:
        lines.append("No events available.")
    else:
        for index, event in enumerate(events, start=1):
            lines.extend([
                "",
                f"Event {index}",
                f"  Timestamp: {event.get('timestamp', 'N/A')}",
                f"  Test: {event.get('test', 'N/A')}",
                f"  Original locator: {event.get('failed_locator', 'N/A')}",
                f"  Suggested locator: {event.get('ollama_suggestion', 'N/A')}",
                f"  Attempt: {event.get('attempt', 'N/A')}",
                f"  Status: {event.get('status', 'N/A')}",
                f"  Reason: {event.get('reason', 'N/A')}",
            ])

    lines.extend([
        "",
        "=" * 45,
        "End of report",
    ])

    return "\n".join(lines) + "\n"


def main() -> None:
    """Generate healing_summary.txt in the latest report directory."""

    try:
        report_dir = find_latest_report_dir()
        events_file = report_dir / "healing_events.json"
        events = load_events(events_file)

        summary = generate_summary(report_dir, events)
        summary_file = report_dir / "healing_summary.txt"

        summary_file.write_text(summary, encoding="utf-8")

        print("Healing summary generated successfully.")
        print(f"Events processed: {len(events)}")
        print(f"Summary saved to: {summary_file}")

    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Could not generate healing summary: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
