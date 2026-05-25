#!/usr/bin/env python3
"""Run code-quality benchmark cases for the LLM Code Auditor plugin."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCANNER = Path(__file__).with_name("llm_code_smell_scan.py")
FINDING_RE = re.compile(r":\d+: (?P<severity>[A-Z]+) [0-9.]+ (?P<code>[a-z0-9-]+):")
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class ScanFinding:
    code: str
    severity: str


@dataclass(frozen=True)
class CaseResult:
    name: str
    expected_findings_ok: bool
    reference_ok: bool
    candidate_ok: bool | None
    score: int
    max_score: int
    notes: tuple[str, ...]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LLM Code Auditor quality benchmarks.")
    parser.add_argument("benchmarks", nargs="?", type=Path, default=ROOT / "benchmarks")
    parser.add_argument(
        "--candidate-root",
        type=Path,
        help="Optional directory containing candidate refactors in one subdirectory per case.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable results.")
    args = parser.parse_args()

    results = [
        run_case(case_file, args.candidate_root)
        for case_file in sorted((args.benchmarks / "cases").glob("*/case.json"))
    ]
    if args.json:
        print(json.dumps([result_to_json(result) for result in results], indent=2))
    else:
        print_summary(results)

    if not results:
        return 1
    if not all(result.expected_findings_ok and result.reference_ok for result in results):
        return 1
    candidate_results = [result.candidate_ok for result in results if result.candidate_ok is not None]
    if candidate_results and not all(candidate_results):
        return 1
    return 0


def run_case(case_file: Path, candidate_root: Path | None) -> CaseResult:
    case = json.loads(case_file.read_text(encoding="utf-8"))
    case_dir = case_file.parent
    notes: list[str] = []

    before_findings = run_scanner(case_dir / case["before"], "low")
    expected_findings_ok = expected_findings_present(case["expected_findings"], before_findings, notes)

    reference = case["reference"]
    reference_dir = case_dir / reference["path"]
    reference_ok = quality_gate(reference_dir, case_dir / reference["tests"], reference, notes, "reference")

    candidate_ok = None
    if candidate_root is not None:
        candidate_dir = candidate_root / case["id"]
        if candidate_dir.exists():
            candidate_ok = quality_gate(candidate_dir, case_dir / reference["tests"], reference, notes, "candidate")
        else:
            notes.append(f"candidate missing: {candidate_dir}")
            candidate_ok = False

    score = int(expected_findings_ok) + int(reference_ok)
    max_score = 2
    if candidate_ok is not None:
        score += int(candidate_ok)
        max_score += 1

    return CaseResult(
        name=case["id"],
        expected_findings_ok=expected_findings_ok,
        reference_ok=reference_ok,
        candidate_ok=candidate_ok,
        score=score,
        max_score=max_score,
        notes=tuple(notes),
    )


def run_scanner(path: Path, min_severity: str) -> list[ScanFinding]:
    result = subprocess.run(
        ["python3", str(SCANNER), "--min-severity", min_severity, str(path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [
        ScanFinding(match.group("code"), match.group("severity").lower())
        for match in FINDING_RE.finditer(result.stdout)
    ]


def expected_findings_present(
    expected: list[dict[str, str]],
    findings: list[ScanFinding],
    notes: list[str],
) -> bool:
    ok = True
    for expectation in expected:
        code = expectation["code"]
        min_severity = expectation.get("min_severity", "low")
        found = any(
            finding.code == code
            and SEVERITY_ORDER[finding.severity] <= SEVERITY_ORDER[min_severity]
            for finding in findings
        )
        if not found:
            notes.append(f"missing expected finding: {code} >= {min_severity}")
            ok = False
    return ok


def quality_gate(
    source_dir: Path,
    tests_dir: Path,
    thresholds: dict[str, object],
    notes: list[str],
    label: str,
) -> bool:
    max_high = int(thresholds.get("max_high_findings", 0))
    max_medium = int(thresholds.get("max_medium_findings", 0))
    high_findings = run_scanner(source_dir, "high")
    medium_findings = run_scanner(source_dir, "medium")
    tests_ok = run_behavior_tests(source_dir, tests_dir)

    ok = True
    if len(high_findings) > max_high:
        notes.append(f"{label} high findings: {len(high_findings)} > {max_high}")
        ok = False
    if len(medium_findings) > max_medium:
        notes.append(f"{label} medium findings: {len(medium_findings)} > {max_medium}")
        ok = False
    if not tests_ok:
        notes.append(f"{label} behavior tests failed")
        ok = False
    return ok


def run_behavior_tests(source_dir: Path, tests_dir: Path) -> bool:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(source_dir)
        if not existing_pythonpath
        else f"{source_dir}{os.pathsep}{existing_pythonpath}"
    )
    result = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", str(tests_dir)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    return result.returncode == 0


def print_summary(results: list[CaseResult]) -> None:
    print(f"Benchmark cases: {len(results)}")
    score = sum(result.score for result in results)
    max_score = sum(result.max_score for result in results)
    print(f"Score: {score}/{max_score}")
    smell_ok = all(result.expected_findings_ok for result in results)
    reference_ok = all(result.reference_ok for result in results)
    print(f"Expected smell coverage: {'PASS' if smell_ok else 'FAIL'}")
    print(f"Reference implementations: {'PASS' if reference_ok else 'FAIL'}")

    candidate_results = [result for result in results if result.candidate_ok is not None]
    if candidate_results:
        candidate_ok = all(result.candidate_ok for result in candidate_results)
        print(f"Candidate implementations: {'PASS' if candidate_ok else 'FAIL'}")

    for result in results:
        status = "PASS" if result.expected_findings_ok and result.reference_ok else "FAIL"
        print(f"- {result.name}: {status} ({result.score}/{result.max_score})")
        for note in result.notes:
            print(f"  {note}")


def result_to_json(result: CaseResult) -> dict[str, object]:
    return {
        "name": result.name,
        "expected_findings_ok": result.expected_findings_ok,
        "reference_ok": result.reference_ok,
        "candidate_ok": result.candidate_ok,
        "score": result.score,
        "max_score": result.max_score,
        "notes": list(result.notes),
    }


if __name__ == "__main__":
    raise SystemExit(main())
