"""CLI entry point for the fraud-detection requirements pipeline demo."""

from __future__ import annotations

import argparse
from pathlib import Path

from orchestrator import run_pipeline
from utils import SEED_DIR

DEFAULT_INTAKE = SEED_DIR / "ato_incident.json"


def main() -> None:
    """Parse arguments and run the pipeline."""
    parser = argparse.ArgumentParser(
        description="Run the 4-agent fraud-detection requirements pipeline demo.",
    )
    parser.add_argument(
        "--intake",
        type=Path,
        default=DEFAULT_INTAKE,
        help="Path to raw intake JSON (default: seed/ato_incident.json)",
    )
    parser.add_argument(
        "--mode",
        choices=["mock_clean", "mock_violation", "live"],
        default="mock_clean",
        help="LLM response mode for agents",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Automatically approve human gates (non-interactive runs)",
    )
    parser.add_argument(
        "--violation-case",
        choices=["requirements", "test_design", "defect_analysis", "documentation"],
        default=None,
        help="With mock_violation, run a specific agent's violation fixture",
    )
    args = parser.parse_args()

    run_pipeline(
        intake_path=str(args.intake),
        mode=args.mode,
        auto_approve=args.auto_approve,
        violation_case=args.violation_case,
    )


if __name__ == "__main__":
    main()
