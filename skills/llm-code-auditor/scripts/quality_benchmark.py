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
REMODEL = Path(__file__).with_name("code_remodel.py")
QUALITY_LENS = Path(__file__).with_name("quality_lens.py")
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
    expected_remodel_ok: bool
    expected_markup_ok: bool
    expected_lenses_ok: bool
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
    if not all(
        result.expected_findings_ok
        and result.expected_remodel_ok
        and result.expected_markup_ok
        and result.expected_lenses_ok
        and result.reference_ok
        for result in results
    ):
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
    before_remodel = run_remodel(case_dir / case["before"])
    before_markup = run_remodel_markup(case_dir / case["before"])
    expected_findings_ok = expected_findings_present(case["expected_findings"], before_findings, notes)
    expected_remodel_ok = expected_remodel_present(
        case.get("expected_remodel_friction", []),
        before_remodel,
        notes,
    )
    expected_markup_ok = expected_markup_present(
        case.get("expected_remodel_markup", []),
        before_markup,
        notes,
    )
    expected_lenses_ok = expected_lenses_present(
        case.get("expected_lenses", []),
        run_quality_lens(case_dir / case["before"]),
        notes,
    )

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

    score = (
        int(expected_findings_ok)
        + int(expected_remodel_ok)
        + int(expected_markup_ok)
        + int(expected_lenses_ok)
        + int(reference_ok)
    )
    max_score = 5
    if candidate_ok is not None:
        score += int(candidate_ok)
        max_score += 1

    return CaseResult(
        name=case["id"],
        expected_findings_ok=expected_findings_ok,
        expected_remodel_ok=expected_remodel_ok,
        expected_markup_ok=expected_markup_ok,
        expected_lenses_ok=expected_lenses_ok,
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


def run_remodel(path: Path) -> dict[str, object]:
    result = subprocess.run(
        ["python3", str(REMODEL), "--json", str(path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    model = json.loads(result.stdout)
    if not isinstance(model, dict):
        raise SystemExit("code remodel output must be an object")
    return model


def run_remodel_markup(path: Path) -> str:
    result = subprocess.run(
        ["python3", str(REMODEL), str(path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def run_quality_lens(path: Path) -> dict[str, object]:
    result = subprocess.run(
        ["python3", str(QUALITY_LENS), "--json", str(path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    model = json.loads(result.stdout)
    if not isinstance(model, dict):
        raise SystemExit("quality lens output must be an object")
    return model


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


def expected_remodel_present(
    expected: list[dict[str, object]],
    model: dict[str, object],
    notes: list[str],
) -> bool:
    if not expected:
        return True
    friction = friction_counts(model)
    ok = True
    for expectation in expected:
        kind = str(expectation["kind"])
        min_count = int(expectation.get("min_count", 1))
        count = friction.get(kind, 0)
        if count < min_count:
            notes.append(f"remodel friction too low: {kind} {count} < {min_count}")
            ok = False
    return ok


def expected_markup_present(
    expected: list[str],
    markup: str,
    notes: list[str],
) -> bool:
    ok = True
    for term in expected:
        if term not in markup:
            notes.append(f"remodel markup missing: {term}")
            ok = False
    return ok


def expected_lenses_present(
    expected: list[dict[str, object]],
    model: dict[str, object],
    notes: list[str],
) -> bool:
    if not expected:
        return True
    lenses = lens_pressure(model)
    ok = True
    for expectation in expected:
        lens_id = expectation["id"]
        min_pressure = float(expectation["min_pressure"])
        pressure = lenses.get(str(lens_id), 0.0)
        if pressure < min_pressure:
            notes.append(
                f"lens pressure too low: {lens_id} {pressure:.2f} < {min_pressure:.2f}"
            )
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
    max_source_lines = thresholds.get("max_source_lines")
    max_function_lines = thresholds.get("max_function_lines")
    max_function_branches = thresholds.get("max_function_branches")
    high_findings = run_scanner(source_dir, "high")
    medium_findings = run_scanner(source_dir, "medium")
    remodel_model = run_remodel(source_dir)
    lens_model = run_quality_lens(source_dir)
    tests_ok = run_behavior_tests(source_dir, tests_dir)

    ok = True
    if len(high_findings) > max_high:
        notes.append(f"{label} high findings: {len(high_findings)} > {max_high}")
        ok = False
    if len(medium_findings) > max_medium:
        notes.append(f"{label} medium findings: {len(medium_findings)} > {max_medium}")
        ok = False
    if max_source_lines is not None:
        lines = source_line_count(source_dir)
        allowed_lines = int(max_source_lines)
        if lines > allowed_lines:
            notes.append(f"{label} source lines: {lines} > {allowed_lines}")
            ok = False
    metrics = quality_metrics(lens_model)
    if max_function_lines is not None:
        allowed_lines = int(max_function_lines)
        if metrics["max_function_lines"] > allowed_lines:
            notes.append(
                f"{label} max function lines: {metrics['max_function_lines']} > {allowed_lines}"
            )
            ok = False
    if max_function_branches is not None:
        allowed_branches = int(max_function_branches)
        if metrics["max_function_branches"] > allowed_branches:
            notes.append(
                f"{label} max function branches: {metrics['max_function_branches']} > {allowed_branches}"
            )
            ok = False
    max_lens_pressure = thresholds.get("max_lens_pressure")
    if max_lens_pressure is not None:
        highest_lens_pressure = max(lens_pressure(lens_model).values(), default=0.0)
        allowed = float(max_lens_pressure)
        if highest_lens_pressure > allowed:
            notes.append(
                f"{label} lens pressure: {highest_lens_pressure:.2f} > {allowed:.2f}"
            )
            ok = False
    max_remodel_friction = thresholds.get("max_remodel_friction")
    if max_remodel_friction is not None:
        if not isinstance(max_remodel_friction, dict):
            raise SystemExit("max_remodel_friction must be an object")
        friction = friction_counts(remodel_model)
        for kind, raw_limit in max_remodel_friction.items():
            limit = int(raw_limit)
            count = friction.get(str(kind), 0)
            if count > limit:
                notes.append(f"{label} remodel friction {kind}: {count} > {limit}")
                ok = False
    if not tests_ok:
        notes.append(f"{label} behavior tests failed")
        ok = False
    return ok


def source_line_count(source_dir: Path) -> int:
    total = 0
    for path in source_dir.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            total += len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            continue
    return total


def quality_metrics(model: dict[str, object]) -> dict[str, int]:
    raw_metrics = model.get("metrics")
    if not isinstance(raw_metrics, dict):
        return {"max_function_lines": 0, "max_function_branches": 0}
    return {
        "max_function_lines": int(raw_metrics.get("max_function_lines", 0)),
        "max_function_branches": int(raw_metrics.get("max_function_branches", 0)),
    }


def lens_pressure(model: dict[str, object]) -> dict[str, float]:
    raw_lenses = model.get("lenses", [])
    if not isinstance(raw_lenses, list):
        return {}
    pressures: dict[str, float] = {}
    for raw_lens in raw_lenses:
        if not isinstance(raw_lens, dict):
            continue
        lens_id = raw_lens.get("id")
        pressure = raw_lens.get("pressure")
        if isinstance(lens_id, str) and isinstance(pressure, (int, float)):
            pressures[lens_id] = float(pressure)
    return pressures


def friction_counts(model: dict[str, object]) -> dict[str, int]:
    raw_friction = model.get("friction", {})
    if not isinstance(raw_friction, dict):
        return {}
    counts: dict[str, int] = {}
    for kind, values in raw_friction.items():
        if isinstance(kind, str) and isinstance(values, list):
            counts[kind] = len(values)
    return counts


def run_behavior_tests(source_dir: Path, tests_dir: Path) -> bool:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(source_dir)
        if not existing_pythonpath
        else f"{source_dir}{os.pathsep}{existing_pythonpath}"
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
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
    remodel_ok = all(result.expected_remodel_ok for result in results)
    markup_ok = all(result.expected_markup_ok for result in results)
    lens_ok = all(result.expected_lenses_ok for result in results)
    reference_ok = all(result.reference_ok for result in results)
    print(f"Expected smell coverage: {'PASS' if smell_ok else 'FAIL'}")
    print(f"Expected remodel friction: {'PASS' if remodel_ok else 'FAIL'}")
    print(f"Expected remodel markup: {'PASS' if markup_ok else 'FAIL'}")
    print(f"Expected lens pressure: {'PASS' if lens_ok else 'FAIL'}")
    print(f"Reference implementations: {'PASS' if reference_ok else 'FAIL'}")

    candidate_results = [result for result in results if result.candidate_ok is not None]
    if candidate_results:
        candidate_ok = all(result.candidate_ok for result in candidate_results)
        print(f"Candidate implementations: {'PASS' if candidate_ok else 'FAIL'}")

    for result in results:
        status = (
            "PASS"
            if result.expected_findings_ok
            and result.expected_remodel_ok
            and result.expected_markup_ok
            and result.expected_lenses_ok
            and result.reference_ok
            else "FAIL"
        )
        print(f"- {result.name}: {status} ({result.score}/{result.max_score})")
        for note in result.notes:
            print(f"  {note}")


def result_to_json(result: CaseResult) -> dict[str, object]:
    return {
        "name": result.name,
        "expected_findings_ok": result.expected_findings_ok,
        "expected_remodel_ok": result.expected_remodel_ok,
        "expected_markup_ok": result.expected_markup_ok,
        "expected_lenses_ok": result.expected_lenses_ok,
        "reference_ok": result.reference_ok,
        "candidate_ok": result.candidate_ok,
        "score": result.score,
        "max_score": result.max_score,
        "notes": list(result.notes),
    }


if __name__ == "__main__":
    raise SystemExit(main())
