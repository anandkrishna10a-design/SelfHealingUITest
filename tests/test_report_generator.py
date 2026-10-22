
from pathlib import Path

from healing.report_generator import parse_execution_log


def write_execution_log(report_dir: Path, content: str) -> None:
    """Create a temporary execution log for parser testing."""
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "execution.log").write_text(
        content,
        encoding="utf-8",
    )


def test_counts_each_test_once_across_all_phases(tmp_path):
    """Setup, call, and teardown must count as one passed test."""
    write_execution_log(
        tmp_path,
        """
Test: tests/test_login.py::test_login
Phase: setup
Result: PASSED
Duration: 0.100 seconds

Test: tests/test_login.py::test_login
Phase: call
Result: PASSED
Duration: 0.200 seconds

Test: tests/test_login.py::test_login
Phase: teardown
Result: PASSED
Duration: 0.050 seconds
""",
    )

    result = parse_execution_log(tmp_path)

    assert result["available"] is True
    assert result["passed"] == [
        "tests/test_login.py::test_login"
    ]
    assert result["failed"] == []
    assert result["errors"] == []


def test_detects_failed_call_phase(tmp_path):
    """A failed test call must be reported as failed."""
    test_name = "tests/test_login.py::test_invalid_login"

    write_execution_log(
        tmp_path,
        f"""
Test: {test_name}
Phase: setup
Result: PASSED

Test: {test_name}
Phase: call
Result: FAILED

Test: {test_name}
Phase: teardown
Result: PASSED
""",
    )

    result = parse_execution_log(tmp_path)

    assert result["passed"] == []
    assert len(result["failed"]) == 1
    assert test_name in result["failed"][0]
    assert result["errors"] == []


def test_detects_setup_error_without_call_phase(tmp_path):
    """A setup error must not be counted as a passed test."""
    test_name = "tests/test_login.py::test_login"

    write_execution_log(
        tmp_path,
        f"""
Test: {test_name}
Phase: setup
Result: ERROR
""",
    )

    result = parse_execution_log(tmp_path)

    assert result["passed"] == []
    assert result["failed"] == []
    assert len(result["errors"]) == 1
    assert test_name in result["errors"][0]


def test_detects_teardown_error_after_passed_call(tmp_path):
    """A teardown error must remain visible after a passing call."""
    test_name = "tests/test_cart.py::test_cart"

    write_execution_log(
        tmp_path,
        f"""
Test: {test_name}
Phase: setup
Result: PASSED

Test: {test_name}
Phase: call
Result: PASSED

Test: {test_name}
Phase: teardown
Result: ERROR
""",
    )

    result = parse_execution_log(tmp_path)

    assert result["passed"] == [test_name]
    assert result["failed"] == []
    assert len(result["errors"]) == 1
    assert test_name in result["errors"][0]


def test_does_not_count_interrupted_test_as_passed(tmp_path):
    """An incomplete test with no call result is not a pass."""
    test_name = "tests/test_products.py::test_search"

    write_execution_log(
        tmp_path,
        f"""
Test: {test_name}
Phase: setup
Result: PASSED
""",
    )

    result = parse_execution_log(tmp_path)

    assert result["passed"] == []
    assert result["failed"] == []
    assert result["errors"] == []


def test_missing_execution_log_returns_empty_results(tmp_path):
    """Missing logs must not crash report parsing."""
    result = parse_execution_log(tmp_path)

    assert result["available"] is False
    assert result["passed"] == []
    assert result["failed"] == []
    assert result["errors"] == []
    assert result["tracebacks"] == {}
