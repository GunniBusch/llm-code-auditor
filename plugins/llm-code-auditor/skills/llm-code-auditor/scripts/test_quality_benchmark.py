#!/usr/bin/env python3
"""Regression test for the LLM code quality benchmark harness."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).with_name("quality_benchmark.py")
BENCHMARKS = ROOT / "benchmarks"


def test_reference_benchmark_suite_passes() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), str(BENCHMARKS)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert "Benchmark cases: 3" in result.stdout
    assert "Expected smell coverage: PASS" in result.stdout
    assert "Reference implementations: PASS" in result.stdout


def main() -> int:
    test_reference_benchmark_suite_passes()
    print("ok test_reference_benchmark_suite_passes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
