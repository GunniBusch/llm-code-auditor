#!/usr/bin/env python3
"""Regression test for the LLM code quality benchmark harness."""

from __future__ import annotations

import subprocess
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).with_name("quality_benchmark.py")
BENCHMARKS = ROOT / "benchmarks"


def test_reference_benchmark_suite_passes() -> None:
    for cache_dir in BENCHMARKS.rglob("__pycache__"):
        shutil.rmtree(cache_dir)

    result = subprocess.run(
        ["python3", str(SCRIPT), str(BENCHMARKS)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert "Benchmark cases: 4" in result.stdout
    assert "Score: 12/12" in result.stdout
    assert "Expected smell coverage: PASS" in result.stdout
    assert "Expected lens pressure: PASS" in result.stdout
    assert "Reference implementations: PASS" in result.stdout
    assert not list(BENCHMARKS.rglob("__pycache__"))


def main() -> int:
    test_reference_benchmark_suite_passes()
    print("ok test_reference_benchmark_suite_passes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
