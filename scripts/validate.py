#!/usr/bin/env python3
"""Run the repository's local validation checks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
PLUGIN = ROOT
AUDITOR = ROOT / "skills" / "llm-code-auditor"
SYSTEM_SKILLS = Path.home() / ".codex" / "skills" / ".system"


def main() -> int:
    checks = [
        (
            "python compile",
            [
                PYTHON,
                "-m",
                "py_compile",
                str(AUDITOR / "scripts/llm_code_smell_scan.py"),
                str(AUDITOR / "scripts/code_remodel.py"),
                str(AUDITOR / "scripts/quality_lens.py"),
                str(AUDITOR / "scripts/quality_benchmark.py"),
                str(AUDITOR / "scripts/test_llm_code_smell_scan.py"),
                str(AUDITOR / "scripts/test_code_remodel.py"),
                str(AUDITOR / "scripts/test_quality_lens.py"),
                str(AUDITOR / "scripts/test_quality_benchmark.py"),
                str(AUDITOR / "scripts/test_remodel_first_framework.py"),
                str(ROOT / "scripts/validate.py"),
            ],
        ),
        ("scanner tests", [PYTHON, str(AUDITOR / "scripts/test_llm_code_smell_scan.py")]),
        ("code remodel tests", [PYTHON, str(AUDITOR / "scripts/test_code_remodel.py")]),
        ("quality lens tests", [PYTHON, str(AUDITOR / "scripts/test_quality_lens.py")]),
        ("benchmark tests", [PYTHON, str(AUDITOR / "scripts/test_quality_benchmark.py")]),
        ("remodel framework tests", [PYTHON, str(AUDITOR / "scripts/test_remodel_first_framework.py")]),
        ("quality benchmark", [PYTHON, str(AUDITOR / "scripts/quality_benchmark.py"), str(AUDITOR / "benchmarks")]),
    ]

    validate_json(ROOT / ".codex-plugin/plugin.json")
    for name, command in checks:
        run(name, command)

    run_optional_codex_validators()
    print("validation-ok")
    return 0


def validate_json(path: Path) -> None:
    with path.open(encoding="utf-8") as handle:
        json.load(handle)


def run(name: str, command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        print(result.stdout, end="")
        raise SystemExit(f"{name} failed")
    if result.stdout.strip():
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")


def run_optional_codex_validators() -> None:
    plugin_validator = SYSTEM_SKILLS / "plugin-creator/scripts/validate_plugin.py"
    skill_validator = SYSTEM_SKILLS / "skill-creator/scripts/quick_validate.py"
    validator_python = yaml_python()
    if not plugin_validator.exists() or not skill_validator.exists() or validator_python is None:
        print("codex-validator-skip")
        return

    run("plugin validator", [validator_python, str(plugin_validator), str(PLUGIN)])
    for skill in sorted((PLUGIN / "skills").iterdir()):
        if skill.is_dir():
            run(f"skill validator {skill.name}", [validator_python, str(skill_validator), str(skill)])


def yaml_python() -> str | None:
    candidates = [
        PYTHON,
        "/Applications/Xcode.app/Contents/Developer/usr/bin/python3",
        "python3",
    ]
    for candidate in candidates:
        result = subprocess.run(
            [candidate, "-c", "import yaml"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return candidate
    return None


if __name__ == "__main__":
    raise SystemExit(main())
