
import json
import os
from pathlib import Path

_PROGRESS_FILE = None
_TOTAL_TESTS = 0
_RESULTS = {}
_CURRENT_TEST = None


def _progress_path():
    configured_path = os.environ.get("SELF_HEALING_PROGRESS_FILE")

    if not configured_path:
        return None

    return Path(configured_path)


def _write_progress(status=None, exit_code=None):
    global _PROGRESS_FILE

    if _PROGRESS_FILE is None:
        _PROGRESS_FILE = _progress_path()

    if _PROGRESS_FILE is None:
        return

    completed = len(_RESULTS)
    passed = sum(value == "passed" for value in _RESULTS.values())
    failed = sum(value == "failed" for value in _RESULTS.values())
    errors = sum(value == "error" for value in _RESULTS.values())
    skipped = sum(value == "skipped" for value in _RESULTS.values())

    percent = (
        round(completed * 100 / _TOTAL_TESTS)
        if _TOTAL_TESTS
        else 0
    )

    if status == "completed":
        percent = 100

    payload = {
        "status": status or "running",
        "total": _TOTAL_TESTS,
        "completed": completed,
        "remaining": max(0, _TOTAL_TESTS - completed),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "percent": min(100, percent),
        "current_test": _CURRENT_TEST,
        "exit_code": exit_code,
    }

    try:
        _PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)

        temporary_file = _PROGRESS_FILE.with_suffix(".tmp")
        temporary_file.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        temporary_file.replace(_PROGRESS_FILE)

    except OSError:
        # Progress reporting must never interrupt pytest.
        pass


def pytest_configure(config):
    global _PROGRESS_FILE
    global _TOTAL_TESTS
    global _RESULTS
    global _CURRENT_TEST

    _PROGRESS_FILE = _progress_path()
    _TOTAL_TESTS = 0
    _RESULTS = {}
    _CURRENT_TEST = None

    _write_progress(status="starting")


def pytest_collection_finish(session):
    global _TOTAL_TESTS

    _TOTAL_TESTS = len(session.items)
    _write_progress(status="running")


def pytest_runtest_logreport(report):
    global _CURRENT_TEST

    node_id = report.nodeid
    _CURRENT_TEST = node_id

    # A failed setup can prevent the test's call phase from running.
    if report.when == "setup" and report.failed:
        _RESULTS[node_id] = "error"

    # Count each test once, when its call phase completes.
    elif report.when == "call":
        if report.passed:
            _RESULTS[node_id] = "passed"
        elif report.failed:
            _RESULTS[node_id] = "failed"
        elif report.skipped:
            _RESULTS[node_id] = "skipped"

    _write_progress(status="running")


def pytest_sessionfinish(session, exitstatus):
    if exitstatus == 0:
        final_status = "completed"
    else:
        final_status = "failed"

    _write_progress(
        status=final_status,
        exit_code=int(exitstatus),
    )
