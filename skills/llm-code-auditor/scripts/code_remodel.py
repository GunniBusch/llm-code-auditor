#!/usr/bin/env python3
"""Render code as post-hoc structural markup for LLM refactoring.

This is not a compiler IR and not another smell report. It deliberately redraws
written code as ownership, boundaries, flows, repeated concepts, and friction so
an agent can see whether the structure of the program matches the shape of the
domain before it edits source.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import llm_code_smell_scan as smell
import quality_lens


GENERIC_ROLE_WORDS = {
    "base",
    "common",
    "controller",
    "coordinator",
    "engine",
    "executor",
    "factory",
    "general",
    "handler",
    "helper",
    "manager",
    "misc",
    "processor",
    "provider",
    "resolver",
    "service",
    "shared",
    "utils",
}

GUIDE_SOURCES = (
    {
        "id": "fowler-code-smell",
        "name": "Martin Fowler: Code Smell",
        "url": "https://martinfowler.com/bliki/CodeSmell.html",
        "use": "Treat smells as quick indicators that require deeper inspection, not proof.",
    },
    {
        "id": "refactoring-guru-smells",
        "name": "Refactoring Guru: Code Smells",
        "url": "https://refactoring.guru/refactoring/smells",
        "use": "Map pressure to smell families: bloaters, change preventers, dispensables, couplers.",
    },
    {
        "id": "refactoring-guru-composing-methods",
        "name": "Refactoring Guru: Composing Methods",
        "url": "https://refactoring.guru/refactoring/techniques/composing-methods",
        "use": "Choose extract, inline, split variable, method object, or substitute algorithm moves.",
    },
    {
        "id": "fowler-refactoring-2e",
        "name": "Fowler: Refactoring 2nd Edition catalog changes",
        "url": "https://martinfowler.com/articles/refactoring-2nd-changes.html",
        "use": "Prefer modern generalized move names such as Extract Function, Move Function, and Split Phase.",
    },
)

PRESSURE_REFACTOR_MAP = {
    "empty_boundaries": {
        "pressure": "unowned-forwarder",
        "guide_smells": ("Middle Man", "Speculative Generality"),
        "candidate_moves": (
            "Inline Function/Method",
            "Remove Middle Man",
            "Inline Class",
            "Move Statements to Callers",
        ),
        "guardrail": "Keep the boundary when it owns protocol, lifecycle, policy, test seam, or phase readability.",
        "sources": ("fowler-code-smell", "refactoring-guru-smells", "fowler-refactoring-2e"),
    },
    "branch_hubs": {
        "pressure": "branch-hub",
        "guide_smells": ("Long Method", "Switch Statements", "Divergent Change"),
        "candidate_moves": (
            "Extract Function",
            "Decompose Conditional",
            "Replace Conditional with Polymorphism",
            "Replace Function with Command",
            "Split Phase",
            "Substitute Algorithm",
        ),
        "guardrail": "Do not split mechanically; first name the domain distinction or data shape.",
        "sources": ("refactoring-guru-smells", "refactoring-guru-composing-methods", "fowler-refactoring-2e"),
    },
    "generic_boundaries": {
        "pressure": "generic-boundary",
        "guide_smells": ("Lazy Class", "Speculative Generality", "Primitive Obsession"),
        "candidate_moves": (
            "Rename Function/Class from owned concept",
            "Inline Class",
            "Collapse Hierarchy",
            "Replace Primitive with Object",
        ),
        "guardrail": "Do not rename framework, schema, protocol, or public API vocabulary.",
        "sources": ("fowler-code-smell", "refactoring-guru-smells", "fowler-refactoring-2e"),
    },
    "silent_boundaries": {
        "pressure": "silent-boundary",
        "guide_smells": ("Error Code", "Hidden Failure Policy"),
        "candidate_moves": (
            "Replace Error Code with Exception",
            "Replace Exception with Precheck",
            "Introduce Special Case",
            "Separate Query from Modifier",
        ),
        "guardrail": "Only recover locally when the fallback is an explicit domain contract.",
        "sources": ("fowler-code-smell", "fowler-refactoring-2e"),
    },
    "repeated_names": {
        "pressure": "repeated-operation-name",
        "guide_smells": ("Duplicate Code", "Shotgun Surgery"),
        "candidate_moves": (
            "Extract Function",
            "Pull Up Function",
            "Change Function Declaration",
            "Combine Functions into Transform",
        ),
        "guardrail": "Keep deliberate protocol hooks or domain-specific duplicates that are likely to diverge.",
        "sources": ("refactoring-guru-smells", "fowler-refactoring-2e"),
    },
    "repeated_concepts": {
        "pressure": "spread-concept",
        "guide_smells": ("Feature Envy", "Divergent Change", "Data Clumps"),
        "candidate_moves": (
            "Move Function",
            "Extract Class",
            "Introduce Parameter Object",
            "Combine Functions into Class",
            "Split Phase",
        ),
        "guardrail": "Repeated domain words can be healthy locality; move only when ownership is unclear.",
        "sources": ("fowler-code-smell", "refactoring-guru-smells", "fowler-refactoring-2e"),
    },
    "module_friction": {
        "pressure": "module-shape-friction",
        "guide_smells": ("Large Class", "Lazy Class", "Shotgun Surgery"),
        "candidate_moves": (
            "Extract Class/Module",
            "Inline Class/Module",
            "Move Function",
            "Remove Dead Code",
        ),
        "guardrail": "Respect package boundaries, public exports, migrations, generated code, and framework layout.",
        "sources": ("refactoring-guru-smells", "fowler-refactoring-2e"),
    },
}


@dataclass(frozen=True)
class SymbolModel:
    path: Path
    kind: str
    name: str
    line: int
    end_line: int
    role: str
    owns: str
    calls: tuple[str, ...]
    concepts: tuple[str, ...]
    branches: int
    statements: int
    findings: tuple[smell.Finding, ...]

    @property
    def span(self) -> int:
        return self.end_line - self.line + 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a codebase as Code Remodel Markup."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional scanner/lens JSON config.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the remodel as machine-readable data instead of markup.",
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=80,
        help="Maximum symbols to include in text markup.",
    )
    args = parser.parse_args()

    model = build_remodel(args.paths, args.config)
    if args.json:
        print(json.dumps(model_to_json(model), indent=2, sort_keys=True))
    else:
        print(render_markup(model, args.max_symbols))
    return 0


def build_remodel(paths: list[Path], config_path: Path | None = None) -> dict[str, Any]:
    scanner_config = smell.load_config(paths, config_path)
    files = sorted({file for path in paths for file in smell.iter_code_files(path, scanner_config)})
    file_texts = quality_lens.read_files(files)
    findings = quality_lens.collect_findings(file_texts, scanner_config)
    lens_model = quality_lens.build_quality_model(paths, config_path)
    symbols = collect_symbols(file_texts, findings, scanner_config)
    friction = friction_model(symbols, findings)
    return {
        "paths": [str(path) for path in paths],
        "files": files,
        "line_counts": line_counts(file_texts),
        "lens": lens_model,
        "symbols": symbols,
        "friction": friction,
        "concept_map": concept_map(symbols),
        "guide_sources": list(GUIDE_SOURCES),
        "refactor_moves": refactor_move_model(friction),
    }


def collect_symbols(
    file_texts: dict[Path, str],
    findings: list[smell.Finding],
    config: smell.ScannerConfig,
) -> list[SymbolModel]:
    by_path: dict[Path, list[smell.Finding]] = defaultdict(list)
    for finding in findings:
        by_path[finding.path].append(finding)

    symbols: list[SymbolModel] = []
    for path, text in file_texts.items():
        if path.suffix == ".py":
            symbols.extend(python_symbols(path, text, by_path[path], config))
        else:
            symbols.extend(generic_symbols(path, text, by_path[path], config))
    return sorted(symbols, key=lambda symbol: (str(symbol.path), symbol.line, symbol.name))


def python_symbols(
    path: Path,
    text: str,
    findings: list[smell.Finding],
    config: smell.ScannerConfig,
) -> list[SymbolModel]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    models: list[SymbolModel] = []
    class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    for node in top_level_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_findings = containing_findings(findings, node.lineno, node.end_lineno or node.lineno)
            models.append(
                SymbolModel(
                    path=path,
                    kind="class",
                    name=node.name,
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    role=class_role(node.name, class_findings, config),
                    owns=class_ownership(node, class_findings, config),
                    calls=tuple(sorted(calls_in(node))),
                    concepts=concepts_for(node.name, config),
                    branches=branch_count(node),
                    statements=statement_count(node),
                    findings=tuple(class_findings),
                )
            )
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    models.append(python_function_symbol(path, child, findings, config, node.name, class_names))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            models.append(python_function_symbol(path, node, findings, config, None, class_names))
    return models


def top_level_nodes(tree: ast.Module) -> list[ast.stmt]:
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def python_function_symbol(
    path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    findings: list[smell.Finding],
    config: smell.ScannerConfig,
    parent_class: str | None,
    class_names: set[str],
) -> SymbolModel:
    start = node.lineno
    end = node.end_lineno or node.lineno
    contained_findings = containing_findings(findings, start, end)
    calls = calls_in(node)
    branches = branch_count(node)
    statements = statement_count(node)
    pass_through = smell.is_python_pass_through(node)
    silent_fallback = smell.broad_silent_fallback(node) is not None
    qualname = f"{parent_class}.{node.name}" if parent_class else node.name

    return SymbolModel(
        path=path,
        kind="method" if parent_class else "function",
        name=qualname,
        line=start,
        end_line=end,
        role=function_role(node.name, pass_through, silent_fallback, branches, statements),
        owns=function_ownership(node.name, pass_through, silent_fallback, branches, calls, class_names, config),
        calls=tuple(sorted(calls)),
        concepts=concepts_for(node.name, config),
        branches=branches,
        statements=statements,
        findings=tuple(contained_findings),
    )


def generic_symbols(
    path: Path,
    text: str,
    findings: list[smell.Finding],
    config: smell.ScannerConfig,
) -> list[SymbolModel]:
    models: list[SymbolModel] = []
    declaration_re = re.compile(
        r"\b(?:class|interface|type|function|def|const|let|var)\s+([A-Za-z_$][\w$]*)"
    )
    for index, line in enumerate(text.splitlines(), start=1):
        match = declaration_re.search(line)
        if match is None:
            continue
        name = match.group(1)
        line_findings = [finding for finding in findings if finding.line == index]
        models.append(
            SymbolModel(
                path=path,
                kind="symbol",
                name=name,
                line=index,
                end_line=index,
                role=generic_role(name, line_findings, config),
                owns=generic_ownership(name, line_findings),
                calls=(),
                concepts=concepts_for(name, config),
                branches=0,
                statements=1,
                findings=tuple(line_findings),
            )
        )
    return models


def containing_findings(
    findings: list[smell.Finding],
    start: int,
    end: int,
) -> list[smell.Finding]:
    return [finding for finding in findings if start <= finding.line <= end]


def class_role(
    name: str,
    findings: list[smell.Finding],
    config: smell.ScannerConfig,
) -> str:
    if generic_suffix(name, config) and not concepts_for(name, config):
        return "generic-container"
    if has_finding(findings, "naming-inflation"):
        return "named-boundary"
    return "domain-container"


def class_ownership(
    node: ast.ClassDef,
    findings: list[smell.Finding],
    config: smell.ScannerConfig,
) -> str:
    methods = [child for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if methods and all(smell.is_python_pass_through(method) for method in methods):
        return "delegation-only"
    if has_finding(findings, "naming-inflation") and not concepts_for(node.name, config):
        return "unclear-boundary"
    if methods:
        return "owned-responsibility"
    return "type-or-boundary"


def function_role(
    name: str,
    pass_through: bool,
    silent_fallback: bool,
    branches: int,
    statements: int,
) -> str:
    if pass_through:
        return "thin-boundary"
    if silent_fallback:
        return "silent-boundary"
    if branches >= 8:
        return "branch-hub"
    if statements <= 2 and name not in {"main", "__repr__", "__str__"}:
        return "tiny-helper"
    return "operation"


def function_ownership(
    name: str,
    pass_through: bool,
    silent_fallback: bool,
    branches: int,
    calls: set[str],
    class_names: set[str],
    config: smell.ScannerConfig,
) -> str:
    if pass_through:
        return "delegation-only"
    if silent_fallback:
        return "implicit-failure-policy"
    if branches >= 8:
        return "mixed-decision-set"
    if any(call in class_names for call in calls):
        return "object-construction"
    if calls:
        return "coordination"
    if not concepts_for(name, config):
        return "unnamed-concept"
    return "local-operation"


def generic_role(
    name: str,
    findings: list[smell.Finding],
    config: smell.ScannerConfig,
) -> str:
    concepts = concepts_for(name, config)
    if has_finding(findings, "naming-inflation") or generic_suffix(name, config):
        if concepts:
            return "named-boundary"
        return "generic-symbol"
    return "symbol"


def generic_ownership(name: str, findings: list[smell.Finding]) -> str:
    if has_finding(findings, "generic-abstraction-language"):
        return "unclear-concept"
    if has_finding(findings, "naming-inflation"):
        return "unknown-boundary"
    return "unknown"


def has_finding(findings: list[smell.Finding], code: str) -> bool:
    return any(finding.code == code for finding in findings)


def generic_suffix(name: str, config: smell.ScannerConfig) -> bool:
    lowered = name.lower()
    return any(lowered.endswith(suffix.lower()) for suffix in config.generic_suffixes)


def calls_in(node: ast.AST) -> set[str]:
    collector = CallCollector()
    for child in ast.iter_child_nodes(node):
        collector.visit(child)
    return collector.calls


class CallCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_Call(self, node: ast.Call) -> None:
        name = call_name(node.func)
        if name:
            self.calls.add(name)
        self.generic_visit(node)


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


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


def concepts_for(name: str, config: smell.ScannerConfig) -> tuple[str, ...]:
    words = split_name_words(name)
    generic_words = {word.lower() for word in config.generic_words} | GENERIC_ROLE_WORDS
    concepts = [
        word
        for word in words
        if word not in generic_words and not word.startswith("__")
    ]
    return tuple(concepts[:6])


def split_name_words(name: str) -> list[str]:
    raw = name.replace(".", "_")
    pieces: list[str] = []
    for part in re.split(r"[_\W]+", raw):
        if not part:
            continue
        pieces.extend(
            item.lower()
            for item in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", part)
        )
    return pieces


def line_counts(file_texts: dict[Path, str]) -> dict[Path, int]:
    return {path: len(text.splitlines()) for path, text in file_texts.items()}


def friction_model(
    symbols: list[SymbolModel],
    findings: list[smell.Finding],
) -> dict[str, list[dict[str, Any]]]:
    repeated_names = [
        {"name": name, "count": count}
        for name, count in Counter(symbol.name.split(".")[-1] for symbol in symbols).items()
        if count > 1 and name not in {"__init__", "main"}
    ]
    repeated_concepts = [
        {"concept": concept, "count": count}
        for concept, count in Counter(
            concept for symbol in symbols for concept in symbol.concepts
        ).items()
        if count >= 3
    ]
    empty_boundaries = [
        symbol_ref(symbol)
        for symbol in symbols
        if symbol.owns == "delegation-only" or symbol.role == "thin-boundary"
    ]
    branch_hubs = [
        symbol_ref(symbol) | {"branches": symbol.branches}
        for symbol in symbols
        if symbol.role == "branch-hub" or symbol.branches >= 8
    ]
    generic_boundaries = [
        symbol_ref(symbol)
        for symbol in symbols
        if symbol.role in {"generic-container", "generic-symbol"}
        or symbol.owns in {"unclear-boundary", "unclear-concept", "unnamed-concept"}
    ]
    silent_boundaries = [
        symbol_ref(symbol)
        for symbol in symbols
        if symbol.role == "silent-boundary" or symbol.owns == "implicit-failure-policy"
    ]
    module_findings = [
        {
            "path": str(finding.path),
            "line": finding.line,
            "code": finding.code,
            "severity": finding.severity,
        }
        for finding in findings
        if finding.code in {"utility-dumping", "ai-symmetry", "over-fragmentation"}
    ]
    return {
        "empty_boundaries": empty_boundaries,
        "branch_hubs": branch_hubs,
        "generic_boundaries": generic_boundaries,
        "silent_boundaries": silent_boundaries,
        "repeated_names": repeated_names,
        "repeated_concepts": repeated_concepts,
        "module_friction": module_findings,
    }


def concept_map(symbols: list[SymbolModel]) -> list[dict[str, Any]]:
    counts = Counter(concept for symbol in symbols for concept in symbol.concepts)
    concepts: list[dict[str, Any]] = []
    for concept, count in counts.most_common(16):
        if count < 3:
            continue
        owners = [
            symbol
            for symbol in symbols
            if concept in symbol.concepts
            and symbol.owns not in {"delegation-only", "unclear-concept"}
            and symbol.role not in {"thin-boundary", "generic-symbol"}
        ]
        owner_refs = [
            {
                "name": owner.name,
                "path": str(owner.path),
                "line": owner.line,
                "owns": owner.owns,
                "role": owner.role,
            }
            for owner in sorted(
                owners,
                key=lambda item: (
                    item.role == "branch-hub",
                    item.span,
                    item.statements,
                ),
                reverse=True,
            )[:4]
        ]
        concepts.append(
            {
                "concept": concept,
                "count": count,
                "owner_candidates": owner_refs,
                "question": "Should this concept have one owner, or is the spread healthy locality?",
            }
        )
    return concepts


def refactor_move_model(
    friction: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    moves: list[dict[str, Any]] = []
    for kind, guide in PRESSURE_REFACTOR_MAP.items():
        count = len(friction.get(kind, []))
        if count == 0:
            continue
        moves.append(
            {
                "friction": kind,
                "pressure": guide["pressure"],
                "count": count,
                "guide_smells": list(guide["guide_smells"]),
                "candidate_moves": list(guide["candidate_moves"]),
                "guardrail": guide["guardrail"],
                "sources": list(guide["sources"]),
            }
        )
    return moves


def symbol_ref(symbol: SymbolModel) -> dict[str, Any]:
    return {
        "path": str(symbol.path),
        "line": symbol.line,
        "name": symbol.name,
        "kind": symbol.kind,
        "role": symbol.role,
        "owns": symbol.owns,
    }


def model_to_json(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "paths": model["paths"],
        "files": [str(path) for path in model["files"]],
        "line_counts": {str(path): count for path, count in model["line_counts"].items()},
        "lens": {
            "overall_pressure": model["lens"]["overall_pressure"],
            "primary_frame": model["lens"]["primary_frame"],
            "agent_protocol": model["lens"]["agent_protocol"],
            "lenses": model["lens"]["lenses"],
        },
        "symbols": [symbol_to_json(symbol) for symbol in model["symbols"]],
        "friction": model["friction"],
        "concept_map": model["concept_map"],
        "guide_sources": model["guide_sources"],
        "refactor_moves": model["refactor_moves"],
    }


def symbol_to_json(symbol: SymbolModel) -> dict[str, Any]:
    return {
        "path": str(symbol.path),
        "kind": symbol.kind,
        "name": symbol.name,
        "line": symbol.line,
        "span": symbol.span,
        "role": symbol.role,
        "owns": symbol.owns,
        "calls": list(symbol.calls),
        "concepts": list(symbol.concepts),
        "branches": symbol.branches,
        "statements": symbol.statements,
        "guide_hint": symbol_refactor_hint(symbol),
        "pressure": [
            {
                "code": finding.code,
                "severity": finding.severity,
                "line": finding.line,
            }
            for finding in symbol.findings
        ],
    }


def render_markup(model: dict[str, Any], max_symbols: int) -> str:
    lines = [
        "@remodel version=3 format=compact",
        '  purpose="post-code structural model for refactoring"',
        '  authority="manual multi-pass model; human feedback outranks static leads"',
        f"  files={len(model['files'])}",
    ]
    lines.extend(render_refactor_guide(model["guide_sources"]))
    lines.extend(render_lens(model["lens"]))
    lines.extend(render_concept_map(model["concept_map"]))
    lines.extend(render_modules(model, max_symbols))
    lines.extend(render_friction(model["friction"]))
    lines.extend(render_refactor_moves(model["refactor_moves"]))
    lines.extend(render_questions())
    return "\n".join(lines)


def render_refactor_guide(sources: list[dict[str, str]]) -> list[str]:
    source_refs = "; ".join(
        f"{source['name']} <{source['url']}>" for source in sources
    )
    return [
        "@refactor_guide",
        f"  sources={quote(source_refs)}",
        '  principle="A smell is a lead. Prove the deeper structural problem before editing."',
    ]


def render_lens(lens: dict[str, Any]) -> list[str]:
    lines = [
        "@lens",
        f"  overall={quote(str(lens['overall_pressure']))}",
        f"  primary={quote(str(lens['primary_frame']))}",
    ]
    active_lenses = [
        item for item in lens["lenses"] if isinstance(item, dict) and item["pressure"] > 0
    ]
    if active_lenses:
        pressure = " ".join(
            f"{item['id']}={item['label']}({item['pressure']:.2f})"
            for item in active_lenses
        )
        lines.append(f"  pressure: {pressure}")
    protocol = lens["agent_protocol"]
    lines.append(
        "  protocol "
        f"mode={quote(protocol['mode'])} "
        f"inspect={quote(' | '.join(protocol['inspect']))} "
        f"move={quote(' | '.join(protocol['move']))} "
        f"avoid={quote(' | '.join(protocol['avoid']))}"
    )
    return lines


def render_concept_map(concepts: list[dict[str, Any]]) -> list[str]:
    lines = ["@concept_map"]
    if not concepts:
        lines.append("  none")
        return lines
    for concept in concepts[:12]:
        owners = concept.get("owner_candidates", [])
        if isinstance(owners, list) and owners:
            owner_names = ", ".join(
                str(owner.get("name"))
                for owner in owners
                if isinstance(owner, dict) and owner.get("name")
            )
        else:
            owner_names = "none"
        lines.append(
            f"  concept={quote(str(concept['concept']))} count={concept['count']} "
            f"owners={quote(owner_names)} question={quote(str(concept['question']))}"
        )
    return lines


def render_modules(model: dict[str, Any], max_symbols: int) -> list[str]:
    symbols_by_path: dict[Path, list[SymbolModel]] = defaultdict(list)
    for symbol in model["symbols"][:max_symbols]:
        symbols_by_path[symbol.path].append(symbol)

    lines: list[str] = []
    for path in model["files"]:
        symbols = symbols_by_path.get(path, [])
        line_count = model["line_counts"].get(path, 0)
        lines.append(f"@module {quote(str(path))} lines={line_count} symbols={len(symbols)}")
        for symbol in symbols:
            lines.extend(render_symbol(symbol))
    hidden = max(0, len(model["symbols"]) - max_symbols)
    if hidden:
        lines.append(f"@truncated hidden_symbols={hidden}")
    return lines


def render_symbol(symbol: SymbolModel) -> list[str]:
    pressure = ",".join(f"{finding.code}:{finding.severity}" for finding in symbol.findings)
    parts = [
        f"  @symbol {symbol.kind} {quote(symbol.name)} line={symbol.line} "
        f"span={symbol.span} role={quote(symbol.role)} owns={quote(symbol.owns)}"
    ]
    if symbol.concepts:
        parts.append(f"concepts={quote(','.join(symbol.concepts))}")
    if symbol.calls:
        parts.append(f"calls={quote(','.join(symbol.calls))}")
    if symbol.branches:
        parts.append(f"branches={symbol.branches}")
    if pressure:
        parts.append(f"pressure={quote(pressure)}")
    hint = symbol_refactor_hint(symbol)
    if hint is not None:
        smells = ", ".join(hint["guide_smells"])
        moves = "; ".join(hint["candidate_moves"][:3])
        guide = f"pressure={hint['pressure']} smells={smells} moves={moves}"
        parts.append(f"guide={quote(guide)}")
    return [" ".join(parts)]


def symbol_refactor_hint(symbol: SymbolModel) -> dict[str, Any] | None:
    if symbol.owns == "delegation-only" or symbol.role == "thin-boundary":
        return PRESSURE_REFACTOR_MAP["empty_boundaries"]
    if symbol.role == "branch-hub" or symbol.branches >= 8:
        return PRESSURE_REFACTOR_MAP["branch_hubs"]
    if symbol.role == "silent-boundary" or symbol.owns == "implicit-failure-policy":
        return PRESSURE_REFACTOR_MAP["silent_boundaries"]
    if symbol.role in {"generic-container", "generic-symbol"} or symbol.owns in {
        "unclear-boundary",
        "unclear-concept",
        "unnamed-concept",
    }:
        return PRESSURE_REFACTOR_MAP["generic_boundaries"]
    return None


def render_friction(friction: dict[str, list[dict[str, Any]]]) -> list[str]:
    lines = ["@friction"]
    for item in friction["empty_boundaries"][:12]:
        lines.append(
            f"  unowned-forwarder name={quote(item['name'])} path={quote(item['path'])}:{item['line']}"
        )
    for item in friction["branch_hubs"][:12]:
        lines.append(
            f"  branch-hub name={quote(item['name'])} branches={item['branches']} path={quote(item['path'])}:{item['line']}"
        )
    for item in friction["silent_boundaries"][:12]:
        lines.append(
            f"  silent-boundary name={quote(item['name'])} path={quote(item['path'])}:{item['line']}"
        )
    for item in friction["generic_boundaries"][:12]:
        lines.append(
            f"  generic-boundary name={quote(item['name'])} role={quote(item['role'])} owns={quote(item['owns'])}"
        )
    for item in friction["repeated_names"][:12]:
        lines.append(f"  repeated-name name={quote(item['name'])} count={item['count']}")
    for item in friction["repeated_concepts"][:12]:
        lines.append(f"  repeated-concept concept={quote(item['concept'])} count={item['count']}")
    for item in friction["module_friction"][:12]:
        lines.append(
            f"  module-friction code={quote(item['code'])} severity={quote(item['severity'])} path={quote(item['path'])}:{item['line']}"
        )
    if len(lines) == 1:
        lines.append("  none")
    return lines


def render_refactor_moves(moves: list[dict[str, Any]]) -> list[str]:
    lines = ["@refactor_moves"]
    if not moves:
        lines.append("  none")
        return lines
    for move in moves:
        lines.append(
            f"  pressure={quote(str(move['pressure']))} count={move['count']} "
            f"friction={quote(str(move['friction']))} "
            f"guide_smells={quote(', '.join(move['guide_smells']))} "
            f"candidate_moves={quote('; '.join(move['candidate_moves']))} "
            f"guardrail={quote(str(move['guardrail']))} "
            f"sources={quote(', '.join(move['sources']))}"
        )
    return lines


def render_questions() -> list[str]:
    return [
        "@remodel_passes",
        '  pass=1 source="code+tests" goal="model current ownership and behavior"',
        '  pass=2 source="human-feedback" goal="treat explicit maintainer feedback as evidence"',
        '  pass=3 source="static-leads" goal="use analyzer output only as weak supporting leads"',
        '  pass=4 source="after-rewrite" goal="prove pressure was removed without losing behavior"',
        "@remodel_questions",
        '  - "Which guide smell is the closest analogy, and where does the local code disagree with that analogy?"',
        '  - "Which symbols own only delegation, and can the caller or callee own that directly?"',
        '  - "Which abstractions earn their place by naming a phase, boundary, invariant, or domain concept?"',
        '  - "Which generic names are hiding missing domain concepts, and which are contractual vocabulary?"',
        '  - "Which branch hubs are additive accretion, and which are really a table, parser, state model, or separate domain paths?"',
        '  - "Which repeated concepts need an owner, and which are healthy locality?"',
        '  - "Which failure policies are implicit defaults instead of caller-visible behavior?"',
        '  - "Where should code be moved so the next requirement changes one owner instead of another branch or wrapper?"',
        '  - "What behavior proof is needed before rewriting the structure?"',
    ]


def quote(value: str) -> str:
    return json.dumps(value)


if __name__ == "__main__":
    raise SystemExit(main())
