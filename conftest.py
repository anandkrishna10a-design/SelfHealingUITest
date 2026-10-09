
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

import pytest


# -------------------------------------------------
# PROJECT ROOT CONFIGURATION
# -------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REPORTS_ROOT = PROJECT_ROOT / "test_reports"


# -------------------------------------------------
# PYTEST OPTIONS
# -------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--disable-auto-reports",
        action="store_true",
        default=False,
        help="Disable automatic local test reports."
    )


# -------------------------------------------------
# AUTOMATIC REPORT CONFIGURATION
# -------------------------------------------------

def pytest_configure(config):

    if config.getoption("--disable-auto-reports"):
        os.environ.pop("SMARTKART_REPORT_DIR", None)
        return

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S_%f"
    )

    report_folder = REPORTS_ROOT / timestamp
    report_folder.mkdir(parents=True, exist_ok=True)

    config._smartkart_report_folder = report_folder

    os.environ["SMARTKART_REPORT_DIR"] = str(report_folder)

    if config.pluginmanager.hasplugin("html"):
        config.option.htmlpath = str(
            report_folder / "report.html"
        )
        config.option.self_contained_html = True

    if config.pluginmanager.hasplugin("pytest_jsonreport"):
        config.option.json_report = True
        config.option.json_report_file = str(
            report_folder / "results.json"
        )

    print("\nSMARTKART AUTOMATIC TEST REPORTING")
    print(f"Report folder: {report_folder}")


# -------------------------------------------------
# SAVE EXECUTED TEST SCRIPT SNAPSHOTS
# -------------------------------------------------

def pytest_collection_finish(session):

    report_folder = getattr(
        session.config,
        "_smartkart_report_folder",
        None
    )

    if report_folder is None:
        return

    snapshots_folder = report_folder / "test_snapshots"
    snapshots_folder.mkdir(parents=True, exist_ok=True)

    collected_files = set()

    for item in session.items:

        test_file = Path(str(item.path)).resolve()

        if test_file in collected_files:
            continue

        collected_files.add(test_file)

        try:
            relative_path = test_file.relative_to(PROJECT_ROOT)
        except ValueError:
            relative_path = Path(test_file.name)

        destination = snapshots_folder / relative_path
        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(test_file, destination)

    print(f"Saved {len(collected_files)} test script snapshots.")


# -------------------------------------------------
# AUTOMATIC TEST LOGGING
# -------------------------------------------------

@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):

    outcome = yield
    report = outcome.get_result()

    report_folder = getattr(
        item.config,
        "_smartkart_report_folder",
        None
    )

    if report_folder is None:
        return

    log_file = report_folder / "execution.log"

    with log_file.open("a", encoding="utf-8") as log:

        log.write("\n" + "=" * 70 + "\n")
        log.write(f"Test: {item.nodeid}\n")
        log.write(f"Phase: {report.when}\n")
        log.write(f"Result: {report.outcome.upper()}\n")
        log.write(f"Duration: {report.duration:.3f} seconds\n")

        for section_name, section_content in report.sections:
            log.write(f"\n--- {section_name} ---\n")
            log.write(str(section_content) + "\n")

        if report.failed:
            log.write("\n--- Failure details ---\n")
            log.write(str(report.longrepr) + "\n")


# -------------------------------------------------
# SESSION COMPLETION
# -------------------------------------------------

def pytest_sessionfinish(session, exitstatus):

    report_folder = getattr(
        session.config,
        "_smartkart_report_folder",
        None
    )

    if report_folder is None:
        return

    log_file = report_folder / "execution.log"

    with log_file.open("a", encoding="utf-8") as log:
        log.write("\n" + "=" * 70 + "\n")
        log.write("SMARTKART TEST SESSION COMPLETED\n")
        log.write(f"Exit status: {exitstatus}\n")
        log.write(f"Completed: {datetime.now().isoformat()}\n")
        log.write("=" * 70 + "\n")

    print("\nSMARTKART TEST EXECUTION COMPLETED")
    print(f"Reports saved in: {report_folder}")
