#!/usr/bin/env python3
"""Regression tests for the remodel-first agent framework docs."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
FRAMEWORK = ROOT / "references/remodel-first-framework.md"
MARKUP = ROOT / "references/code-remodel-markup.md"
BENCHMARK_CASES = ROOT / "benchmarks/cases"


def test_skill_leads_with_remodel_first_protocol() -> None:
    text = SKILL.read_text(encoding="utf-8")
    protocol_index = text.index("## Remodel-First Protocol")
    scanner_index = text.index("Run the heuristic scanner only")
    assert protocol_index < scanner_index
    assert "The bundled scripts are support tools, not the core workflow." in text
    assert "references/remodel-first-framework.md" in text


def test_framework_defines_manual_remodel_contract() -> None:
    text = FRAMEWORK.read_text(encoding="utf-8")
    for required in (
        "The LLM is the modeling tool",
        "The Python tools are support machinery",
        "Explicit human feedback is a secondary source of truth",
        "## Manual Remodel Contract",
        "`@context`",
        "`@feedback`",
        "`@module`",
        "`@flow`",
        "`@decision`",
        "`@rewrite_pressure`",
        "`@refactor_moves`",
        "`@after_remodel`",
        "`@remodel_passes`",
        "Good Structure Signals",
        "Bad Structure Signals",
    ):
        assert required in text


def test_markup_reference_includes_after_remodel_and_public_code_guardrail() -> None:
    text = MARKUP.read_text(encoding="utf-8")
    assert "@after_remodel" in text
    assert "@feedback" in text
    assert "@remodel_passes" in text
    assert "What The Syntax Should Reveal" in text
    assert "secondary leads, not authority" in text
    assert "Do not copy source snippets" in text
    assert "domain names" in text
    assert "identifiers into benchmark fixtures" in text


def test_benchmark_cases_gate_remodel_markup_terms() -> None:
    missing: list[str] = []
    for case_file in sorted(BENCHMARK_CASES.glob("*/case.json")):
        case = json.loads(case_file.read_text(encoding="utf-8"))
        terms = case.get("expected_remodel_markup")
        if not terms:
            missing.append(case["id"])
    assert not missing, f"cases missing expected_remodel_markup: {missing}"


def main() -> int:
    test_skill_leads_with_remodel_first_protocol()
    print("ok test_skill_leads_with_remodel_first_protocol")
    test_framework_defines_manual_remodel_contract()
    print("ok test_framework_defines_manual_remodel_contract")
    test_markup_reference_includes_after_remodel_and_public_code_guardrail()
    print("ok test_markup_reference_includes_after_remodel_and_public_code_guardrail")
    test_benchmark_cases_gate_remodel_markup_terms()
    print("ok test_benchmark_cases_gate_remodel_markup_terms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
