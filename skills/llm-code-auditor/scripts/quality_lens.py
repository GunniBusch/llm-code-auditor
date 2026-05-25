#!/usr/bin/env python3
"""Build an agent-facing quality model from code and scanner evidence.

The smell scanner is deliberately concrete: it points at likely review leads.
This script is deliberately less literal. It turns those leads and a few
structural metrics into a small set of quality lenses an agent can reason with
before editing code.
"""

from __future__ import annotations

import argparse
import ast
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import llm_code_smell_scan as smell


SEVERITY_WEIGHT = {"low": 1.0, "medium": 2.5, "high": 4.5}


@dataclass(frozen=True)
class Lens:
    name: str
    question: str
    preferred_move: str
    avoid: str


@dataclass(frozen=True)
class FunctionMetric:
    path: Path
    name: str
    line: int
    line_span: int
    branches: int
    statements: int


LENSES = {
    "domain-fit": Lens(
        "Domain fit",
        "Does the code speak in the repo's product, protocol, and data vocabulary?",
        "Rename or move code toward the domain concept it actually owns.",
        "Do not rename framework, protocol, schema, or public API vocabulary without proof it is local.",
    ),
    "economy": Lens(
        "Economy",
        "Does every layer, helper, option, and type earn its current place?",
        "Inline, delete, move, or collapse machinery that owns no current responsibility.",
        "Do not delete a boundary just because it has one implementation; first identify what invariant it protects.",
    ),
    "invariant-ownership": Lens(
        "Invariant ownership",
        "Is each validation, normalization, and state rule owned once at the right boundary?",
        "Move checks to the trust boundary or model that can make invalid states hard to express.",
        "Do not scatter the same guard across helpers after a boundary has already proven it.",
    ),
    "failure-semantics": Lens(
        "Failure semantics",
        "Are errors explicit enough that callers can recover or fail honestly?",
        "Replace silent fallbacks and decorative catches with defined failure behavior.",
        "Do not return empty defaults for unexpected failures unless that is the documented contract.",
    ),
    "change-shape": Lens(
        "Change shape",
        "Will the next feature add one local change or another branch/layer across the system?",
        "Convert branch accretion into a table, parser, state model, or a few real domain paths.",
        "Do not add another flag or branch before naming the domain distinction it represents.",
    ),
    "proof-readiness": Lens(
        "Proof readiness",
        "Can behavior be verified from tests, types, boundaries, or a precise manual trace?",
        "Add or repair behavior-level proof before deeper rewrites.",
        "Do not trust green visible tests when they only mirror private structure or prompt examples.",
    ),
}


DEFAULT_CODE_WEIGHTS: dict[str, dict[str, float]] = {
    "ai-symmetry": {"economy": 0.7, "change-shape": 0.5},
    "comment-narration": {"domain-fit": 0.3, "economy": 0.3},
    "faux-robustness": {"failure-semantics": 0.9, "proof-readiness": 0.4},
    "generic-abstraction-language": {"domain-fit": 0.8, "economy": 0.2},
    "incomplete-generation": {"proof-readiness": 1.0, "failure-semantics": 0.5},
    "lsp-transport-contract": {"invariant-ownership": 0.7, "failure-semantics": 0.7},
    "naming-inflation": {"domain-fit": 0.5, "economy": 0.5},
    "over-fragmentation": {"economy": 0.6, "change-shape": 0.4},
    "pass-through-layer": {"economy": 1.0, "invariant-ownership": 0.4},
    "silent-fallback": {"failure-semantics": 1.0, "proof-readiness": 0.6},
    "single-use-abstraction": {"economy": 0.15, "domain-fit": 0.05},
    "structural-erosion": {"change-shape": 1.0, "invariant-ownership": 0.5},
    "utility-dumping": {"domain-fit": 0.6, "invariant-ownership": 0.5},
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize code quality pressure as agent-facing lenses."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional JSON config. Uses scanner config plus optional lens_weights.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable quality model.",
    )
    parser.add_argument(
        "--evidence-limit",
        type=int,
        default=8,
        help="Maximum concrete leads to print in text output.",
    )
    args = parser.parse_args()

    model = build_quality_model(args.paths, args.config)
    if args.json:
        print(json.dumps(model, indent=2, sort_keys=True))
    else:
        print_text_model(model, args.evidence_limit)
    return 0


def build_quality_model(paths: list[Path], config_path: Path | None = None) -> dict[str, Any]:
    scanner_config = smell.load_config(paths, config_path)
    lens_weights = load_lens_weights(paths, config_path)
    files = sorted({file for path in paths for file in smell.iter_code_files(path, scanner_config)})
    file_texts = read_files(files)
    findings = collect_findings(file_texts, scanner_config)
    functions = collect_python_metrics(file_texts)
    lens_scores = score_lenses(findings, functions, lens_weights)
    ranked_lenses = ranked_lens_models(lens_scores, findings, lens_weights)

    return {
        "path_count": len(paths),
        "file_count": len(files),
        "finding_count": len(findings),
        "severity_counts": dict(Counter(finding.severity for finding in findings)),
        "function_count": len(functions),
        "metrics": summarize_metrics(functions),
        "overall_pressure": pressure_label(sum(lens_scores.values()) / max(len(LENSES), 1)),
        "primary_frame": primary_frame(ranked_lenses),
        "agent_protocol": agent_protocol(ranked_lenses),
        "lenses": ranked_lenses,
        "evidence": [finding_model(finding) for finding in top_findings(findings)],
    }


def load_lens_weights(paths: list[Path], config_path: Path | None) -> dict[str, dict[str, float]]:
    discovered = config_path or smell.discover_config(
        [path if path.is_dir() else path.parent for path in paths]
    )
    if discovered is None:
        return DEFAULT_CODE_WEIGHTS
    try:
        data = json.loads(discovered.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_CODE_WEIGHTS
    if not isinstance(data, dict) or "lens_weights" not in data:
        return DEFAULT_CODE_WEIGHTS
    raw_weights = data["lens_weights"]
    if not isinstance(raw_weights, dict):
        raise SystemExit("lens_weights must be an object")

    weights = {code: dict(lenses) for code, lenses in DEFAULT_CODE_WEIGHTS.items()}
    for code, raw_lenses in raw_weights.items():
        if not isinstance(code, str) or not isinstance(raw_lenses, dict):
            raise SystemExit("lens_weights entries must map strings to objects")
        parsed: dict[str, float] = {}
        for lens_id, weight in raw_lenses.items():
            if not isinstance(lens_id, str) or lens_id not in LENSES:
                raise SystemExit(f"Unknown quality lens: {lens_id}")
            if not isinstance(weight, (int, float)):
                raise SystemExit("lens weight values must be numbers")
            parsed[lens_id] = float(weight)
        weights[code] = parsed
    return weights


def read_files(files: list[Path]) -> dict[Path, str]:
    texts: dict[Path, str] = {}
    for file in files:
        try:
            texts[file] = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            texts[file] = file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return texts


def collect_findings(
    file_texts: dict[Path, str],
    config: smell.ScannerConfig,
) -> list[smell.Finding]:
    findings: list[smell.Finding] = []
    for file, text in file_texts.items():
        findings.extend(smell.scan_text(file, text, config))
        if file.suffix == ".py":
            findings.extend(smell.scan_python_ast(file, text, config))
    findings.extend(smell.scan_file_shape(list(file_texts)))
    findings.extend(smell.scan_lsp_transport_contract(file_texts))
    return sorted(
        findings,
        key=lambda finding: (
            smell.SEVERITY_ORDER[finding.severity],
            str(finding.path),
            finding.line,
            finding.code,
        ),
    )


def collect_python_metrics(file_texts: dict[Path, str]) -> list[FunctionMetric]:
    metrics: list[FunctionMetric] = []
    for path, text in file_texts.items():
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            line_span = (node.end_lineno or node.lineno) - node.lineno + 1
            metrics.append(
                FunctionMetric(
                    path=path,
                    name=node.name,
                    line=node.lineno,
                    line_span=line_span,
                    branches=branch_count(node),
                    statements=statement_count(node),
                )
            )
    return metrics


def branch_count(node: ast.AST) -> int:
    branch_nodes: tuple[type[ast.AST], ...] = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.IfExp,
    )
    match_node = getattr(ast, "Match", None)
    if match_node is not None:
        branch_nodes = (*branch_nodes, match_node)
    return sum(1 for child in ast.walk(node) if isinstance(child, branch_nodes))


def statement_count(node: ast.AST) -> int:
    return sum(isinstance(child, ast.stmt) for child in ast.walk(node))


def score_lenses(
    findings: list[smell.Finding],
    functions: list[FunctionMetric],
    lens_weights: dict[str, dict[str, float]],
) -> dict[str, float]:
    raw_scores: dict[str, float] = defaultdict(float)
    for finding in findings:
        for lens_id, weight in lens_weights.get(finding.code, {}).items():
            raw_scores[lens_id] += SEVERITY_WEIGHT[finding.severity] * finding.confidence * weight

    for metric in functions:
        if metric.line_span >= 45:
            raw_scores["change-shape"] += min(metric.line_span / 80.0, 1.0)
        if metric.branches >= 5:
            raw_scores["invariant-ownership"] += min(metric.branches / 10.0, 1.0)
            raw_scores["change-shape"] += min(metric.branches / 10.0, 1.0)
        if metric.statements <= 2 and metric.name not in {"main", "__repr__", "__str__"}:
            raw_scores["economy"] += 0.15

    return {
        lens_id: min(raw_scores.get(lens_id, 0.0) / 6.0, 1.0)
        for lens_id in LENSES
    }


def ranked_lens_models(
    lens_scores: dict[str, float],
    findings: list[smell.Finding],
    lens_weights: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    code_counts_by_lens: dict[str, Counter[str]] = {lens_id: Counter() for lens_id in LENSES}
    for finding in findings:
        for lens_id, weight in lens_weights.get(finding.code, {}).items():
            if weight:
                code_counts_by_lens[lens_id][finding.code] += 1

    ranked = sorted(lens_scores.items(), key=lambda item: item[1], reverse=True)
    return [
        {
            "id": lens_id,
            "name": LENSES[lens_id].name,
            "pressure": round(score, 2),
            "label": pressure_label(score),
            "question": LENSES[lens_id].question,
            "preferred_move": LENSES[lens_id].preferred_move,
            "avoid": LENSES[lens_id].avoid,
            "dominant_signals": [
                code for code, _count in code_counts_by_lens[lens_id].most_common(4)
            ],
        }
        for lens_id, score in ranked
    ]


def summarize_metrics(functions: list[FunctionMetric]) -> dict[str, Any]:
    if not functions:
        return {
            "max_function_lines": 0,
            "max_function_branches": 0,
            "long_functions": [],
            "branch_heavy_functions": [],
        }

    long_functions = sorted(functions, key=lambda item: item.line_span, reverse=True)[:5]
    branch_heavy = sorted(functions, key=lambda item: item.branches, reverse=True)[:5]
    return {
        "max_function_lines": max(metric.line_span for metric in functions),
        "max_function_branches": max(metric.branches for metric in functions),
        "long_functions": [function_metric_model(metric) for metric in long_functions if metric.line_span >= 25],
        "branch_heavy_functions": [
            function_metric_model(metric) for metric in branch_heavy if metric.branches >= 4
        ],
    }


def function_metric_model(metric: FunctionMetric) -> dict[str, Any]:
    return {
        "path": str(metric.path),
        "name": metric.name,
        "line": metric.line,
        "line_span": metric.line_span,
        "branches": metric.branches,
        "statements": metric.statements,
    }


def pressure_label(score: float) -> str:
    if score >= 0.67:
        return "high"
    if score >= 0.34:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def primary_frame(ranked_lenses: list[dict[str, Any]]) -> str:
    active = [lens for lens in ranked_lenses if lens["pressure"] > 0]
    if not active:
        return "No strong quality pressure found. Inspect intent and tests before changing style."

    first = active[0]
    second = active[1] if len(active) > 1 else None
    if second is None or second["pressure"] < 0.25:
        return f"Lead with {first['name'].lower()}: {first['preferred_move']}"
    return (
        f"Lead with {first['name'].lower()}, then check {second['name'].lower()}: "
        f"{first['preferred_move']}"
    )


def agent_protocol(ranked_lenses: list[dict[str, Any]]) -> dict[str, Any]:
    active = [lens for lens in ranked_lenses if lens["pressure"] > 0][:3]
    if not active:
        return {
            "mode": "intent-first",
            "inspect": ["Map behavior, boundaries, and tests before changing style."],
            "move": ["Leave code alone when no quality pressure is supported by evidence."],
            "avoid": ["Do not invent cleanup work from taste alone."],
        }
    return {
        "mode": "lens-first",
        "inspect": [lens["question"] for lens in active],
        "move": [lens["preferred_move"] for lens in active],
        "avoid": [lens["avoid"] for lens in active],
    }


def top_findings(findings: list[smell.Finding]) -> list[smell.Finding]:
    return findings[:12]


def finding_model(finding: smell.Finding) -> dict[str, Any]:
    return {
        "path": str(finding.path),
        "line": finding.line,
        "code": finding.code,
        "severity": finding.severity,
        "confidence": finding.confidence,
        "message": finding.message,
        "action": finding.action,
        "evidence": list(finding.evidence),
    }


def print_text_model(model: dict[str, Any], evidence_limit: int) -> None:
    print(
        f"Quality lens: {model['file_count']} files, {model['finding_count']} concrete leads, "
        f"overall pressure {model['overall_pressure']}."
    )
    print(f"Primary frame: {model['primary_frame']}")
    protocol = model["agent_protocol"]
    print(f"Agent mode: {protocol['mode']}")
    print("\nLens pressure:")
    for lens in model["lenses"]:
        if lens["pressure"] == 0:
            continue
        signals = ", ".join(lens["dominant_signals"]) or "structural metrics"
        print(
            f"- {lens['name']}: {lens['label']} ({lens['pressure']:.2f}) | "
            f"{lens['question']} Move: {lens['preferred_move']} Signals: {signals}."
        )

    print("\nAgent protocol:")
    for question in protocol["inspect"]:
        print(f"- Inspect: {question}")
    for move in protocol["move"]:
        print(f"- Move: {move}")
    for avoid in protocol["avoid"]:
        print(f"- Avoid: {avoid}")

    metrics = model["metrics"]
    if metrics["long_functions"] or metrics["branch_heavy_functions"]:
        print("\nStructural pressure:")
        for metric in metrics["long_functions"][:3]:
            print(
                f"- {metric['path']}:{metric['line']} {metric['name']} spans "
                f"{metric['line_span']} lines."
            )
        for metric in metrics["branch_heavy_functions"][:3]:
            print(
                f"- {metric['path']}:{metric['line']} {metric['name']} has "
                f"{metric['branches']} branch points."
            )

    evidence = model["evidence"][:evidence_limit]
    if evidence:
        print("\nEvidence to inspect:")
        for finding in evidence:
            print(
                f"- {finding['path']}:{finding['line']} {finding['severity']} "
                f"{finding['code']}: {finding['message']}"
            )


if __name__ == "__main__":
    raise SystemExit(main())
