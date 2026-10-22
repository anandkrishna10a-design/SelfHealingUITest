
import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path

from healing.report_generator import parse_execution_log


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_json_file(path):
    """Load a JSON list, returning an empty list when the file is absent."""
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not read {path}: {error}") from error


def safe(value):
    """Escape values before displaying them in HTML."""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, indent=2)
    return html.escape(str(value if value is not None else ""))


def normalise_status(value):
    """Convert recorded event statuses into readable categories."""
    status = str(value or "unknown").strip().lower().replace("_", " ")
    status = re.sub(r"\s+", " ", status)

    if "accept" in status or "success" in status or status == "healed":
        return "Accepted"
    if "reject" in status or "invalid" in status:
        return "Rejected"
    if "fail" in status or "error" in status:
        return "Failed"
    return status.title() or "Unknown"


def read_run_exit_status(report_dir):
    """Read the recorded pytest exit status, if available."""
    log_path = report_dir / "execution.log"

    if not log_path.exists():
        return None

    try:
        log_text = log_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None

    matches = re.findall(
        r"(?im)^\s*Exit status:\s*(-?\d+)\s*$",
        log_text,
    )
    return int(matches[-1]) if matches else None


def read_test_counts(report_dir):
    """Use the project's existing parser to count unique test outcomes."""
    parsed = parse_execution_log(Path(report_dir))

    return {
        "available": parsed.get("available", False),
        "passed": len(parsed.get("passed", [])),
        "failed": len(parsed.get("failed", [])),
        "errors": len(parsed.get("errors", [])),
        "exit_status": read_run_exit_status(report_dir),
    }


def get_event_metrics(events):
    """Calculate suggestion and event metrics from recorded JSON events."""
    suggestions = [
        event
        for event in events
        if str(event.get("ollama_suggestion") or "").strip()
    ]

    status_counts = Counter(
        normalise_status(event.get("status")) for event in events
    )

    return {
        "events": len(events),
        "suggestions": len(suggestions),
        "accepted": status_counts.get("Accepted", 0),
        "rejected": status_counts.get("Rejected", 0),
        "failed": status_counts.get("Failed", 0),
        "status_counts": status_counts,
    }


def build_event_rows(event, index):
    """Build a main event row and a separate full-width evidence row."""
    status = normalise_status(event.get("status"))
    test_name = event.get("test", "Unknown test")
    original = event.get("failed_locator", "")
    suggestion = event.get("ollama_suggestion", "")
    reason = event.get("reason", "")
    attempt = event.get("attempt", "")

    searchable = " ".join(
        str(event.get(key, ""))
        for key in (
            "test",
            "failed_locator",
            "ollama_suggestion",
            "status",
            "reason",
            "evidence",
            "attempt",
        )
    ).lower()

    evidence = event.get("evidence", "")

    if isinstance(evidence, (dict, list)):
        evidence_text = json.dumps(
            evidence,
            ensure_ascii=False,
            indent=2,
        )
    else:
        evidence_text = str(evidence or "")

    suggestion_text = (
        safe(suggestion)
        if str(suggestion or "").strip()
        else "No suggestion recorded"
    )

    main_row = f"""
    <tr class="event-main-row"
        data-event-index="{index}"
        data-status="{safe(status)}"
        data-search="{safe(searchable)}">
      <td class="number-cell">{index}</td>
      <td class="test-cell">{safe(test_name)}</td>
      <td class="locator-cell"><code>{safe(original)}</code></td>
      <td class="locator-cell"><code>{suggestion_text}</code></td>
      <td class="attempt-cell">{safe(attempt)}</td>
      <td class="status-cell">
        <span class="status status-{safe(status.lower())}">
          {safe(status)}
        </span>
      </td>
      <td class="reason-cell">{safe(reason)}</td>
      <td class="details-control-cell">
        <button
          type="button"
          class="details-toggle"
          aria-expanded="false"
          aria-controls="evidence-{index}"
          data-target="evidence-{index}">
          <span class="toggle-icon">▶</span>
          View details
        </button>
      </td>
    </tr>
    """

    evidence_row = f"""
    <tr class="evidence-row"
        data-parent-index="{index}"
        hidden>
      <td colspan="8" class="evidence-full-cell">
        <div class="evidence-panel" id="evidence-{index}">
          <div class="evidence-heading">Recorded evidence — event {index}</div>
          <pre>{safe(evidence_text)}</pre>
        </div>
      </td>
    </tr>
    """

    return main_row + evidence_row


def generate_html_report(report_dir, output_path=None):
    """Generate a simplified HTML report for one test run."""
    report_dir = Path(report_dir).resolve()

    events = load_json_file(report_dir / "healing_events.json")
    test_counts = read_test_counts(report_dir)
    metrics = get_event_metrics(events)

    passed = test_counts["passed"]
    failed_tests = test_counts["failed"]
    errors = test_counts["errors"]
    exit_status = test_counts["exit_status"]

    if not test_counts["available"]:
        run_status = "Execution log unavailable"
    elif (
        exit_status == 5
        and passed == 0
        and failed_tests == 0
        and errors == 0
    ):
        run_status = "No tests collected"
    elif exit_status not in (None, 0):
        run_status = "Run did not complete successfully"
    elif failed_tests or errors:
        run_status = "Completed with failures"
    elif passed > 0:
        run_status = "Completed successfully"
    else:
        run_status = "No test outcomes found"

    event_rows = "".join(
        build_event_rows(event, index)
        for index, event in enumerate(events, start=1)
    )

    if not event_rows:
        event_rows = """
        <tr class="empty-event-row">
          <td colspan="8" class="empty-row">
            No healing events were recorded for this run.
          </td>
        </tr>
        """

    report_name = safe(report_dir.name)

    if not events:
        healing_note = (
            "No healing events were recorded. This does not necessarily "
            "mean that tests passed or that no tests were collected."
        )
    else:
        healing_note = (
            "Counts are based on recorded events. A single healing operation "
            "may produce multiple events, and accepted events are not proof "
            "of a permanent code change."
        )

    statuses = sorted(
        set(normalise_status(event.get("status")) for event in events)
    )

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Self-Healing UI Test Report</title>
<style>
:root {{
  font-family: "Segoe UI", Arial, sans-serif;
  color: #1e293b;
  background: #f3f6fb;
}}
* {{
  box-sizing: border-box;
}}
body {{
  margin: 0;
}}
header {{
  background: #12233f;
  color: white;
  padding: 26px max(20px, calc((100% - 1320px) / 2));
}}
header h1 {{
  margin: 0 0 8px;
  font-size: 26px;
}}
header p {{
  margin: 0;
  color: #c8d5e8;
}}
main {{
  max-width: 1440px;
  margin: 24px auto;
  padding: 0 20px 40px;
}}
h2 {{
  margin: 28px 0 12px;
  font-size: 20px;
}}
.muted {{
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}}
.metrics {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 13px;
  margin: 15px 0;
}}
.metric {{
  background: white;
  border: 1px solid #e1e8f0;
  border-radius: 12px;
  padding: 18px;
}}
.metric span {{
  display: block;
  color: #64748b;
  font-size: 13px;
}}
.metric strong {{
  display: block;
  font-size: 29px;
  margin-top: 8px;
}}
.run-status {{
  display: inline-block;
  padding: 7px 11px;
  border-radius: 7px;
  background: #e8eef7;
  color: #243b5a;
  font-weight: 600;
  font-size: 13px;
}}
.panel {{
  background: white;
  border: 1px solid #e1e8f0;
  border-radius: 12px;
  padding: 16px;
  margin: 14px 0;
}}
.toolbar {{
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}}
input, select {{
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px;
  font: inherit;
  background: white;
}}
input {{
  flex: 1;
  min-width: 220px;
}}
.table-wrap {{
  width: 100%;
  overflow-x: auto;
  border: 1px solid #e7edf4;
  border-radius: 8px;
}}
table {{
  width: 100%;
  min-width: 1250px;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
  font-size: 13px;
}}
thead th {{
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f8fafc;
  color: #475569;
}}
th, td {{
  text-align: left;
  vertical-align: top;
  padding: 13px 12px;
  border-bottom: 1px solid #e7edf4;
  overflow-wrap: break-word;
}}
th {{
  font-weight: 700;
}}
.event-main-row:last-child td {{
  border-bottom: none;
}}
.event-main-row:hover {{
  background: #fafcff;
}}
th:nth-child(1), td.number-cell {{
  width: 48px;
}}
th:nth-child(2), td.test-cell {{
  width: 270px;
}}
th:nth-child(3), td:nth-child(3) {{
  width: 145px;
}}
th:nth-child(4), td:nth-child(4) {{
  width: 145px;
}}
th:nth-child(5), td.attempt-cell {{
  width: 75px;
}}
th:nth-child(6), td.status-cell {{
  width: 105px;
}}
th:nth-child(7), td.reason-cell {{
  width: 240px;
}}
th:nth-child(8), td.details-control-cell {{
  width: 150px;
}}
.number-cell, .attempt-cell {{
  white-space: nowrap;
}}
.test-cell, .reason-cell {{
  overflow-wrap: anywhere;
  line-height: 1.55;
}}
.locator-cell code {{
  display: inline-block;
  max-width: 100%;
  white-space: normal;
  overflow-wrap: anywhere;
  background: #eef2f7;
  padding: 5px 6px;
  border-radius: 5px;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
}}
.status {{
  display: inline-block;
  border-radius: 6px;
  padding: 5px 8px;
  background: #eef2f7;
  font-weight: 600;
  white-space: nowrap;
}}
.status-accepted {{
  background: #dcfce7;
  color: #166534;
}}
.status-rejected, .status-failed {{
  background: #fee2e2;
  color: #991b1b;
}}
.status-unknown {{
  background: #e2e8f0;
  color: #334155;
}}
.details-control-cell {{
  white-space: nowrap;
}}
.details-toggle {{
  border: 0;
  border-radius: 6px;
  padding: 7px 8px;
  background: transparent;
  color: #0f766e;
  cursor: pointer;
  font: inherit;
  font-weight: 600;
  text-align: left;
}}
.details-toggle:hover {{
  background: #e6f5f2;
}}
.details-toggle:focus-visible {{
  outline: 2px solid #0f766e;
  outline-offset: 2px;
}}
.toggle-icon {{
  display: inline-block;
  margin-right: 5px;
  font-size: 10px;
  transition: transform 0.15s ease;
}}
.details-toggle[aria-expanded="true"] .toggle-icon {{
  transform: rotate(90deg);
}}
.evidence-row[hidden] {{
  display: none;
}}
.evidence-full-cell {{
  padding: 14px 18px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #dbe5ef;
}}
.evidence-panel {{
  width: 100%;
  min-width: 0;
  border: 1px solid #dbe5ef;
  border-radius: 9px;
  background: white;
  overflow: hidden;
}}
.evidence-heading {{
  padding: 12px 15px;
  background: #eef3f9;
  border-bottom: 1px solid #dbe5ef;
  color: #334155;
  font-weight: 600;
}}
.evidence-panel pre {{
  margin: 0;
  padding: 16px;
  max-height: 460px;
  overflow: auto;
  white-space: pre;
  overflow-wrap: normal;
  word-break: normal;
  tab-size: 2;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.6;
}}
.empty-row {{
  padding: 22px;
  color: #64748b;
  text-align: center;
}}
footer {{
  color: #64748b;
  font-size: 12px;
  margin-top: 28px;
  line-height: 1.6;
}}
@media (max-width: 600px) {{
  header h1 {{
    font-size: 22px;
  }}
  main {{
    padding: 0 12px 28px;
  }}
  .panel {{
    padding: 10px;
  }}
  .evidence-full-cell {{
    padding: 8px;
  }}
}}
</style>
</head>
<body>
<header>
  <h1>Self-Healing UI Test Automation</h1>
  <p>Test results and locator-healing history</p>
</header>
<main>
  <p class="muted">Run folder: <code>{report_name}</code></p>
  <p><span class="run-status">{safe(run_status)}</span></p>

  <h2>Test results</h2>
  <div class="metrics">
    <div class="metric">
      <span>Tests passed</span>
      <strong>{passed if test_counts["available"] else "—"}</strong>
    </div>
    <div class="metric">
      <span>Tests failed</span>
      <strong>{failed_tests if test_counts["available"] else "—"}</strong>
    </div>
    <div class="metric">
      <span>Test errors</span>
      <strong>{errors if test_counts["available"] else "—"}</strong>
    </div>
  </div>

  <h2>Self-healing summary</h2>
  <div class="metrics">
    <div class="metric">
      <span>Suggestions recorded</span>
      <strong>{metrics["suggestions"]}</strong>
    </div>
    <div class="metric">
      <span>Accepted events</span>
      <strong>{metrics["accepted"]}</strong>
    </div>
    <div class="metric">
      <span>Rejected events</span>
      <strong>{metrics["rejected"]}</strong>
    </div>
    <div class="metric">
      <span>Failed events</span>
      <strong>{metrics["failed"]}</strong>
    </div>
    <div class="metric">
      <span>Total healing events</span>
      <strong>{metrics["events"]}</strong>
    </div>
  </div>
  <p class="muted">{safe(healing_note)}</p>

  <h2>Healing event history</h2>
  <div class="panel">
    <div class="toolbar">
      <input id="search" type="search"
        placeholder="Search tests, locators, reasons, evidence...">
      <select id="statusFilter">
        <option value="">All statuses</option>
        {"".join(f'<option value="{safe(status)}">{safe(status)}</option>' for status in statuses)}
      </select>
    </div>
    <p id="resultCount" class="muted"></p>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Test</th>
            <th>Original locator</th>
            <th>Suggested locator</th>
            <th>Attempt</th>
            <th>Status</th>
            <th>Reason</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody id="eventRows">{event_rows}</tbody>
      </table>
    </div>
  </div>

  <footer>
    Report data is read from this run's saved files. Generating this report
    does not rerun tests. Each run should be reviewed separately.
  </footer>
</main>
<script>
const searchBox = document.getElementById("search");
const statusFilter = document.getElementById("statusFilter");
const eventBody = document.getElementById("eventRows");
const mainRows = Array.from(
  eventBody.querySelectorAll(".event-main-row")
);
const resultCount = document.getElementById("resultCount");

function filterRows() {{
  const query = searchBox.value.toLowerCase().trim();
  const status = statusFilter.value;
  let visible = 0;

  for (const row of mainRows) {{
    const matchesSearch = (row.dataset.search || "").includes(query);
    const matchesStatus = !status || row.dataset.status === status;
    const show = matchesSearch && matchesStatus;
    const detailsRow = row.nextElementSibling;

    row.hidden = !show;

    if (detailsRow && detailsRow.classList.contains("evidence-row")) {{
      if (!show) {{
        detailsRow.hidden = true;
        const button = row.querySelector(".details-toggle");
        if (button) {{
          button.setAttribute("aria-expanded", "false");
        }}
      }}
    }}

    if (show) visible++;
  }}

  resultCount.textContent =
    `Showing ${{visible}} of ${{mainRows.length}} events`;
}}

eventBody.addEventListener("click", function (event) {{
  const button = event.target.closest(".details-toggle");
  if (!button) return;

  const mainRow = button.closest(".event-main-row");
  if (!mainRow) return;

  const detailsRow = mainRow.nextElementSibling;
  if (!detailsRow || !detailsRow.classList.contains("evidence-row")) {{
    return;
  }}

  const isExpanded = button.getAttribute("aria-expanded") === "true";
  button.setAttribute("aria-expanded", String(!isExpanded));
  detailsRow.hidden = isExpanded;
}});

searchBox.addEventListener("input", filterRows);
statusFilter.addEventListener("change", filterRows);
filterRows();
</script>
</body>
</html>
"""

    output_path = (
        Path(output_path)
        if output_path
        else report_dir / "report.html"
    )

    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate a simplified self-healing test report."
    )
    parser.add_argument(
        "report_dir",
        nargs="?",
        default=str(PROJECT_ROOT / "test_reports"),
        help="A report folder or the test_reports root directory",
    )
    parser.add_argument(
        "--output",
        help="Optional output HTML path",
    )
    args = parser.parse_args()

    report_dir = Path(args.report_dir).resolve()

    if not report_dir.exists() or not report_dir.is_dir():
        parser.error(f"Report folder does not exist: {report_dir}")

    if not (report_dir / "execution.log").exists():
        candidates = [
            path
            for path in report_dir.iterdir()
            if path.is_dir()
            and (
                (path / "execution.log").exists()
                or (path / "healing_events.json").exists()
            )
        ]

        if not candidates:
            parser.error(
                f"No report run found in {report_dir} or its immediate "
                "subfolders."
            )

        report_dir = max(
            candidates,
            key=lambda path: path.stat().st_mtime,
        )

    output = generate_html_report(report_dir, args.output)
    print(f"HTML report created: {output}")


if __name__ == "__main__":
    main()
