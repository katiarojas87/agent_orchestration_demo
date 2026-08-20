#!/usr/bin/env python3
"""End-to-end tests for the agent orchestration pipeline (CLI + API)."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_BASE = "http://127.0.0.1:8765"
INTAKE_ID = "INTAKE-2026-07-18-004"
REQUIREMENT_ID = "REQ-ATO-014"
EXECUTION_ID = "EXEC-ATO-014-004"
DEFECT_ID = "DEF-ATO-014-001"


class TestFailure(Exception):
    """Raised when an end-to-end assertion fails."""


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run main.py with the project venv Python."""
    python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if not python.exists():
        python = Path(sys.executable)
    return subprocess.run(
        [str(python), "main.py", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def api_post(path: str, payload: dict[str, object]) -> dict[str, object]:
    """POST JSON to the FastAPI test server."""
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def api_get(path: str) -> dict[str, object]:
    """GET JSON from the FastAPI test server."""
    with urllib.request.urlopen(f"{API_BASE}{path}", timeout=30) as response:
        return json.loads(response.read())


def wait_for_api(timeout_seconds: float = 15.0) -> None:
    """Wait until the API health endpoint responds."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{API_BASE}/api/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.25)
    raise TestFailure(f"API did not become ready at {API_BASE}")


def assert_cli_clean_pipeline() -> None:
    """CLI mock_clean run completes successfully."""
    result = run_cli(["--mode", "mock_clean", "--auto-approve"])
    if result.returncode != 0:
        raise TestFailure(f"CLI mock_clean failed:\n{result.stdout}\n{result.stderr}")
    if "Pipeline completed successfully." not in result.stdout:
        raise TestFailure("CLI mock_clean did not print success message")
    print("PASS  CLI mock_clean pipeline")


def assert_cli_violation_stops() -> None:
    """CLI mock_violation stops at requirements guardrail."""
    result = run_cli(["--mode", "mock_violation"])
    if result.returncode != 0:
        raise TestFailure(f"CLI mock_violation errored:\n{result.stderr}")
    if "GUARDRAIL FAILURE" not in result.stdout:
        raise TestFailure("CLI mock_violation did not report guardrail failure")
    if "status must be 'draft'" not in result.stdout:
        raise TestFailure("CLI mock_violation missing expected failure detail")
    print("PASS  CLI mock_violation guardrail stop")


def assert_api_clean_pipeline() -> None:
    """API happy path through all four stages."""
    draft = api_post(
        "/api/requirements/draft",
        {"intake_id": INTAKE_ID, "mode": "mock_clean"},
    )
    guardrails = draft["guardrail_result"]
    if not guardrails["passed"]:
        raise TestFailure(f"Requirements guardrails failed: {guardrails}")

    req = api_post("/api/requirements/approve", {"requirement_id": REQUIREMENT_ID})
    if req["status"] != "approved":
        raise TestFailure(f"Requirement not approved: {req['status']}")

    tests = api_post(
        "/api/test-design/draft",
        {"requirement_id": REQUIREMENT_ID, "mode": "mock_clean"},
    )
    if not tests["guardrail_result"]["passed"]:
        raise TestFailure(f"Test design guardrails failed: {tests['guardrail_result']}")
    if len(tests["tests"]) < 4:
        raise TestFailure(f"Expected at least 4 tests, got {len(tests['tests'])}")

    approved_tests = api_post(
        "/api/test-design/approve",
        {"requirement_id": REQUIREMENT_ID},
    )
    if not approved_tests["tests"]:
        raise TestFailure("Test design approve returned no tests")

    defect = api_post(
        "/api/defect-analysis/draft",
        {"execution_id": EXECUTION_ID, "mode": "mock_clean"},
    )
    if not defect["guardrail_result"]["passed"]:
        raise TestFailure(f"Defect guardrails failed: {defect['guardrail_result']}")

    confirmed = api_post("/api/defect-analysis/confirm", {"defect_id": DEFECT_ID})
    if confirmed["defect_id"] != DEFECT_ID:
        raise TestFailure(f"Unexpected defect id: {confirmed['defect_id']}")

    doc = api_get(f"/api/documentation/{REQUIREMENT_ID}?mode=mock_clean")
    trace = doc["trace_record"]
    if not doc["guardrail_result"]["passed"]:
        raise TestFailure(f"Documentation guardrails failed: {doc['guardrail_result']}")
    if not trace["gaps"]:
        raise TestFailure("Expected TC-ATO-014-02 gap in documentation")
    if "TC-ATO-014-02" not in trace["gaps"][0]:
        raise TestFailure(f"Unexpected gap: {trace['gaps']}")

    print("PASS  API mock_clean pipeline")


def assert_api_violation() -> None:
    """API violation mode fails requirements guardrails with detail."""
    draft = api_post(
        "/api/requirements/draft",
        {"intake_id": INTAKE_ID, "mode": "mock_violation"},
    )
    guardrails = draft["guardrail_result"]
    if guardrails["passed"]:
        raise TestFailure("Expected requirements violation guardrails to fail")
    failed = [check for check in guardrails["checks"] if not check["passed"]]
    if not failed:
        raise TestFailure("No failed checks in violation response")
    print(f"PASS  API mock_violation ({len(failed)} failing check(s))")


def assert_frontend_build() -> None:
    """Frontend TypeScript build succeeds."""
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=PROJECT_ROOT / "frontend",
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise TestFailure(f"Frontend build failed:\n{result.stderr}")
    print("PASS  Frontend production build")


def main() -> int:
    """Run all end-to-end checks."""
    print("=== Agent Orchestration Demo — E2E Tests ===\n")

    server = subprocess.Popen(
        [
            str(PROJECT_ROOT / ".venv" / "bin" / "python"),
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
        ],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    failures: list[str] = []
    try:
        wait_for_api()
        for test in (
            assert_cli_clean_pipeline,
            assert_cli_violation_stops,
            assert_api_clean_pipeline,
            assert_api_violation,
            assert_frontend_build,
        ):
            try:
                test()
            except TestFailure as exc:
                failures.append(str(exc))
                print(f"FAIL  {exc}")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    print()
    if failures:
        print(f"FAILED — {len(failures)} test(s)")
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
