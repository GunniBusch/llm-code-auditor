#!/usr/bin/env python3
"""Regression tests for llm_code_smell_scan.py."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("llm_code_smell_scan.py")


def run_scan(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["python3", str(SCRIPT), *args, str(root)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def test_lsp_capability_names_are_not_naming_inflation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "server.ts").write_text(
            """
export const serverCapabilities = {
  codeActionProvider: true,
  hoverProvider: true,
  completionProvider: { resolveProvider: true },
};
""",
            encoding="utf-8",
        )

        output = run_scan(root, "--min-severity", "medium")
        assert "codeActionProvider" not in output
        assert "hoverProvider" not in output
        assert "completionProvider" not in output
        assert "naming-inflation" not in output


def test_generic_provider_name_is_still_reported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "generated.ts").write_text(
            """
export function userProvider(data) {
  return data;
}
""",
            encoding="utf-8",
        )

        output = run_scan(root, "--min-severity", "medium")
        assert "userProvider" in output
        assert "naming-inflation" in output


def test_lsp_connection_without_transport_arg_is_reported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "server.ts").write_text(
            """
import { createConnection, ProposedFeatures } from "vscode-languageserver/node";

createConnection(ProposedFeatures.all);
""",
            encoding="utf-8",
        )

        output = run_scan(root, "--min-severity", "high")
        assert "lsp-transport-contract" in output
        assert "--stdio" in output


def test_lsp_connection_with_wrapper_transport_arg_is_not_reported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "server.ts").write_text(
            """
import { createConnection, ProposedFeatures } from "vscode-languageserver/node";

createConnection(ProposedFeatures.all);
""",
            encoding="utf-8",
        )
        (root / "lib.rs").write_text(
            """
fn language_server_args() -> Vec<String> {
    vec!["server/out/server.cjs".to_string(), "--stdio".to_string()]
}
""",
            encoding="utf-8",
        )

        output = run_scan(root, "--min-severity", "high")
        assert "lsp-transport-contract" not in output


def test_broad_exception_with_empty_fallback_is_reported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "invoice_loader.py").write_text(
            """
def load_invoice(path):
    try:
        return parse_invoice(path)
    except Exception:
        return {}
""",
            encoding="utf-8",
        )

        output = run_scan(root, "--min-severity", "high")
        assert "silent-fallback" in output
        assert "load_invoice" in output


def test_branch_heavy_function_is_reported_as_structural_erosion() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "search_rules.py").write_text(
            """
def match_rule(rule, candidate):
    score = 0
    if rule.name == candidate.name:
        score += 1
    if rule.kind == candidate.kind:
        score += 1
    if rule.owner == candidate.owner:
        score += 1
    if rule.status == candidate.status:
        score += 1
    if rule.region == candidate.region:
        score += 1
    if rule.source == candidate.source:
        score += 1
    if rule.target == candidate.target:
        score += 1
    if rule.priority == candidate.priority:
        score += 1
    if rule.tag == candidate.tag:
        score += 1
    return score
""",
            encoding="utf-8",
        )

        output = run_scan(root, "--min-severity", "medium")
        assert "structural-erosion" in output
        assert "match_rule" in output


def test_builtin_object_type_annotation_is_not_generic_language() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "api_result.py").write_text(
            """
def result_to_json(result: CaseResult) -> dict[str, object]:
    return {"name": result.name}
""",
            encoding="utf-8",
        )

        output = run_scan(root, "--min-severity", "medium")
        assert "generic-abstraction-language" not in output


def test_gitignore_excludes_generated_python_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".gitignore").write_text("generated/\n", encoding="utf-8")
        generated = root / "generated"
        generated.mkdir()
        (generated / "helpers.py").write_text(
            """
def processData(data):
    return data
""",
            encoding="utf-8",
        )

        output = run_scan(root, "--min-severity", "medium")
        assert "processData" not in output
        assert "generic-abstraction-language" not in output


def test_project_config_can_add_contractual_names() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".llm-code-auditor.json").write_text(
            '{"contractual_names": ["customProvider"]}\n',
            encoding="utf-8",
        )
        (root / "plugin_contract.py").write_text(
            """
class customProvider:
    pass
""",
            encoding="utf-8",
        )

        output = run_scan(root, "--min-severity", "medium")
        assert "customProvider" not in output
        assert "naming-inflation" not in output


def test_project_config_can_override_generic_suffixes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".llm-code-auditor.json").write_text(
            '{"generic_suffixes": ["Thingy"]}\n',
            encoding="utf-8",
        )
        (root / "names.py").write_text(
            """
class DataManager:
    pass

class BillingThingy:
    pass
""",
            encoding="utf-8",
        )

        output = run_scan(root, "--min-severity", "medium")
        assert "DataManager" not in output
        assert "BillingThingy" in output
        assert "naming-inflation" in output


def main() -> int:
    tests = [
        test_lsp_capability_names_are_not_naming_inflation,
        test_generic_provider_name_is_still_reported,
        test_lsp_connection_without_transport_arg_is_reported,
        test_lsp_connection_with_wrapper_transport_arg_is_not_reported,
        test_broad_exception_with_empty_fallback_is_reported,
        test_branch_heavy_function_is_reported_as_structural_erosion,
        test_builtin_object_type_annotation_is_not_generic_language,
        test_gitignore_excludes_generated_python_files,
        test_project_config_can_add_contractual_names,
        test_project_config_can_override_generic_suffixes,
    ]
    for test in tests:
        test()
        print(f"ok {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
