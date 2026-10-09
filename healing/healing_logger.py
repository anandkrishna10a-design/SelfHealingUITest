
import json
import os
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_ROOT = PROJECT_ROOT / "test_reports"


def get_report_folder():
    """Find the report folder for the current test run."""

    configured = os.environ.get("SMARTKART_REPORT_DIR")

    if configured:
        return Path(configured)

    if not REPORTS_ROOT.exists():
        return None

    folders = [
        folder
        for folder in REPORTS_ROOT.iterdir()
        if folder.is_dir()
    ]

    if not folders:
        return None

    return max(folders, key=lambda folder: folder.name)


def record_healing_event(
    failed_locator,
    suggested_locator,
    attempt,
    status,
    reason
):
    """Save an Ollama healing event to the current report."""

    report_folder = get_report_folder()

    if report_folder is None:
        return

    report_folder.mkdir(parents=True, exist_ok=True)

    event_file = report_folder / "healing_events.json"

    test_name = os.environ.get(
        "PYTEST_CURRENT_TEST",
        "Standalone healing execution"
    )

    event = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "test": test_name,
        "failed_locator": failed_locator,
        "ollama_suggestion": suggested_locator,
        "attempt": attempt,
        "status": status,
        "reason": reason
    }

    events = []

    if event_file.exists():
        try:
            with event_file.open("r", encoding="utf-8") as file:
                events = json.load(file)
        except (json.JSONDecodeError, OSError):
            print("Warning: Could not read previous healing events.")
            return

    events.append(event)

    with event_file.open("w", encoding="utf-8") as file:
        json.dump(events, file, indent=4)

    print(f"Healing event recorded: {status}")
