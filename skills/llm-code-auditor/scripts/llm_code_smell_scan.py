#!/usr/bin/env python3
"""Heuristic scanner for common LLM-generated code smells.

This is intentionally conservative and dependency-free. It finds review leads,
not proof. Codex should confirm each finding from local context before editing.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rb",
    ".rs",
    ".php",
    ".cs",
}

DEFAULT_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".next",
    ".turbo",
    "coverage",
}

DEFAULT_GENERIC_SUFFIXES = (
    "Manager",
    "Service",
    "Processor",
    "Handler",
    "Provider",
    "Factory",
    "Controller",
    "Engine",
    "Coordinator",
    "Orchestrator",
    "Resolver",
    "Executor",
    "Helper",
)

DEFAULT_GENERIC_WORDS = {
    "entity",
    "item",
    "object",
    "data",
    "info",
    "payload",
    "context",
}

DEFAULT_CONTRACTUAL_NAMES = {
    # Language Server Protocol capability names. These are protocol vocabulary,
    # not naming-inflation evidence.
    "callHierarchyProvider",
    "codeActionProvider",
    "codeLensProvider",
    "colorProvider",
    "completionProvider",
    "declarationProvider",
    "definitionProvider",
    "diagnosticProvider",
    "documentFormattingProvider",
    "documentHighlightProvider",
    "documentLinkProvider",
    "documentOnTypeFormattingProvider",
    "documentRangeFormattingProvider",
    "documentSymbolProvider",
    "executeCommandProvider",
    "foldingRangeProvider",
    "hoverProvider",
    "implementationProvider",
    "inlayHintProvider",
    "inlineValueProvider",
    "linkedEditingRangeProvider",
    "monikerProvider",
    "referencesProvider",
    "renameProvider",
    "resolveProvider",
    "selectionRangeProvider",
    "semanticTokensProvider",
    "signatureHelpProvider",
    "typeDefinitionProvider",
    "typeHierarchyProvider",
    "workspaceSymbolProvider",
    # Python AST node names. These are stdlib vocabulary, not generated naming.
    "ExceptHandler",
}

GENERIC_FUNCTION_RE = re.compile(
    r"\b(processData|handleRequest|executeTask|performAction|doStuff|handleData|processItem)\b"
)
GENERIC_DECLARATION_RE = re.compile(
    r"\b(class|interface|type|function|def|const|let|var|public|private|protected)\b"
)
COMMENT_RE = re.compile(r"^\s*(#|//|/\*|\*)\s*(.+?)\s*(?:\*/)?\s*$")
NARRATION_RE = re.compile(
    r"^(increment|decrement|set|get|return|check|create|update|delete|loop|iterate|initialize|assign|call)\b",
    re.IGNORECASE,
)
TRY_LOG_RETHROW_RE = re.compile(
    r"(catch\s*\([^)]*\)\s*\{[^{}]*(?:console\.(?:log|error|warn)|logger\.\w+)[^{}]*(?:throw\b)[^{}]*\})",
    re.DOTALL,
)
JS_PASS_THROUGH_RE = re.compile(
    r"\b(?:function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*\(([^)]*)\)\s*=>)\s*\{?\s*return\s+([A-Za-z_$][\w$.]*)\(([^)]*)\)",
    re.DOTALL,
)
LSP_CREATE_CONNECTION_RE = re.compile(r"\bcreateConnection\s*\(")
LSP_TRANSPORT_ARG_RE = re.compile(r"--(?:stdio|node-ipc|socket(?:=|\b))")

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    code: str
    message: str
    action: str
    severity: str = "medium"
    confidence: float = 0.5
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScannerConfig:
    skip_dirs: frozenset[str]
    ignore_patterns: tuple[str, ...]
    utility_module_names: frozenset[str]
    generic_suffixes: tuple[str, ...]
    generic_words: frozenset[str]
    contractual_names: frozenset[str]
    generic_suffix_re: re.Pattern[str]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan for likely LLM-generated code smells."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--max-findings", type=int, default=200)
    parser.add_argument(
        "--min-severity",
        choices=("low", "medium", "high"),
        default="low",
        help="Lowest severity to print. Default keeps weak review leads visible.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional JSON config. Defaults to .llm-code-auditor.json near scanned roots.",
    )
    args = parser.parse_args()

    config = load_config(args.paths, args.config)
    files = sorted(
        {file for path in args.paths for file in iter_code_files(path, config)}
    )
    findings: list[Finding] = []
    file_texts: dict[Path, str] = {}
    for file in files:
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = file.read_text(encoding="utf-8", errors="replace")
        file_texts[file] = text
        findings.extend(scan_text(file, text, config))
        if file.suffix == ".py":
            findings.extend(scan_python_ast(file, text, config))

    findings.extend(scan_file_shape(files))
    findings.extend(scan_lsp_transport_contract(file_texts))
    findings = [
        finding
        for finding in findings
        if SEVERITY_ORDER[finding.severity] <= SEVERITY_ORDER[args.min_severity]
    ]
    findings = sorted(
        findings,
        key=lambda item: (
            SEVERITY_ORDER[item.severity],
            str(item.path),
            item.line,
            item.code,
        ),
    )

    for finding in findings[: args.max_findings]:
        evidence = (
            f" Evidence: {'; '.join(finding.evidence)}" if finding.evidence else ""
        )
        print(
            f"{finding.path}:{finding.line}: {finding.severity.upper()} "
            f"{finding.confidence:.2f} {finding.code}: {finding.message}"
            f"{evidence} Action: {finding.action}"
        )

    hidden = max(0, len(findings) - args.max_findings)
    if hidden:
        print(f"... {hidden} more findings hidden by --max-findings")

    print(f"\nScanned {len(files)} files; found {len(findings)} heuristic leads.")
    return 0


def load_config(paths: list[Path], config_path: Path | None) -> ScannerConfig:
    roots = [path if path.is_dir() else path.parent for path in paths]
    data: dict[str, object] = {}
    discovered = config_path or discover_config(roots)
    if discovered is not None:
        try:
            loaded = json.loads(discovered.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit(f"Invalid scanner config {discovered}: {error}") from error
        if not isinstance(loaded, dict):
            raise SystemExit(f"Invalid scanner config {discovered}: root must be an object")
        data = loaded

    skip_dirs = string_set(data.get("skip_dirs"), DEFAULT_SKIP_DIRS)
    utility_module_names = string_set(
        data.get("utility_module_names"),
        {"utils", "helpers", "common", "shared", "base", "misc", "general"},
    )
    generic_suffixes = string_tuple(data.get("generic_suffixes"), DEFAULT_GENERIC_SUFFIXES)
    generic_words = string_set(data.get("generic_words"), DEFAULT_GENERIC_WORDS)
    contractual_names = string_set(
        data.get("contractual_names"),
        DEFAULT_CONTRACTUAL_NAMES,
    )
    ignore_patterns = tuple(sorted(set(gitignore_patterns(roots) + string_list(data.get("ignore_patterns")))))
    suffix_pattern = "|".join(re.escape(suffix) for suffix in generic_suffixes)
    generic_suffix_re = re.compile(
        r"\b[A-Za-z_][A-Za-z0-9_]*(?:" + suffix_pattern + r")\b"
        if suffix_pattern
        else r"a\A"
    )
    return ScannerConfig(
        skip_dirs=frozenset(skip_dirs),
        ignore_patterns=ignore_patterns,
        utility_module_names=frozenset(utility_module_names),
        generic_suffixes=generic_suffixes,
        generic_words=frozenset(generic_words),
        contractual_names=frozenset(contractual_names),
        generic_suffix_re=generic_suffix_re,
    )


def discover_config(roots: list[Path]) -> Path | None:
    for root in roots:
        for directory in (root, *root.parents):
            candidate = directory / ".llm-code-auditor.json"
            if candidate.exists():
                return candidate
    return None


def string_set(value: object, default: set[str] | frozenset[str] | tuple[str, ...]) -> set[str]:
    return set(string_list(value)) if value is not None else set(default)


def string_tuple(value: object, default: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(string_list(value)) if value is not None else default


def string_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit("Scanner config lists must contain only strings")
    return value


def gitignore_patterns(roots: list[Path]) -> list[str]:
    patterns: list[str] = []
    seen: set[Path] = set()
    for root in roots:
        for directory in (root, *root.parents):
            ignore_file = directory / ".gitignore"
            if ignore_file in seen or not ignore_file.exists():
                continue
            seen.add(ignore_file)
            for line in ignore_file.read_text(encoding="utf-8", errors="replace").splitlines():
                pattern = line.strip()
                if pattern and not pattern.startswith("#") and not pattern.startswith("!"):
                    patterns.append(pattern)
    return patterns


def iter_code_files(path: Path, config: ScannerConfig):
    if path.is_file():
        if path.suffix in CODE_EXTENSIONS:
            yield path
        return

    for child in path.rglob("*"):
        if child.is_dir():
            continue
        if is_ignored_path(child, config):
            continue
        if child.suffix in CODE_EXTENSIONS:
            yield child


def is_ignored_path(path: Path, config: ScannerConfig) -> bool:
    if any(part in config.skip_dirs for part in path.parts):
        return True
    display_path = "/".join(display_parts(path))
    for pattern in config.ignore_patterns:
        normalized = pattern.strip("/")
        if not normalized:
            continue
        if pattern.endswith("/") and normalized in path.parts:
            return True
        if fnmatch.fnmatch(display_path, normalized) or fnmatch.fnmatch(path.name, normalized):
            return True
        if display_path.startswith(f"{normalized}/"):
            return True
    return False


def scan_text(path: Path, text: str, config: ScannerConfig) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(scan_path_findings(path, config))
    for index, line in enumerate(text.splitlines(), start=1):
        findings.extend(scan_line_patterns(path, index, line, config))
    findings.extend(scan_text_patterns(path, text))
    return findings


def scan_path_findings(path: Path, config: ScannerConfig) -> list[Finding]:
    findings: list[Finding] = []
    if path.stem.lower() in config.utility_module_names:
        findings.append(
            Finding(
                path,
                1,
                "utility-dumping",
                f"Generic module name `{path.name}` can hide unrelated behavior.",
                "Move functions near their usage or split by domain concept.",
                severity="high",
                confidence=0.85,
                evidence=("filename is a known utility-dump name",),
            )
        )

    if len(display_parts(path)) >= 8:
        findings.append(
            Finding(
                path,
                1,
                "over-fragmentation",
                "Deep path may indicate pattern-driven decomposition.",
                "Check whether directories map to real domain boundaries; merge if not.",
                severity="low",
                confidence=0.25,
                evidence=("path has at least 8 segments",),
            )
        )
    return findings


def scan_line_patterns(
    path: Path,
    index: int,
    line: str,
    config: ScannerConfig,
) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(scan_generic_names(path, index, line, config))
    comment = COMMENT_RE.match(line)
    if comment and NARRATION_RE.search(comment.group(2)):
        findings.append(
            Finding(
                path,
                index,
                "comment-narration",
                "Comment appears to narrate code.",
                "Delete unless it explains a non-obvious constraint.",
                severity="medium",
                confidence=0.65,
                evidence=("comment starts with a code-action verb",),
            )
        )
    return findings


def scan_generic_names(
    path: Path,
    index: int,
    line: str,
    config: ScannerConfig,
) -> list[Finding]:
    findings: list[Finding] = []
    for match in config.generic_suffix_re.finditer(line):
        if is_contractual_name(match.group(0), config):
            continue
        findings.append(
            Finding(
                path,
                index,
                "naming-inflation",
                f"Generic role name `{match.group(0)}` found.",
                "Rename to a concrete domain noun if the role is not a real boundary.",
                severity="medium",
                confidence=0.6,
                evidence=("name uses a generic architecture/job-title suffix",),
            )
        )

    if GENERIC_FUNCTION_RE.search(line) and not is_scanner_pattern_definition(line):
        findings.append(
            Finding(
                path,
                index,
                "generic-abstraction-language",
                "Generic function name found.",
                "Rename from the domain operation or data invariant.",
                severity="medium",
                confidence=0.7,
                evidence=("name matches a generated-code placeholder verb",),
            )
        )

    if GENERIC_DECLARATION_RE.search(line):
        for word in config.generic_words:
            if re.search(rf"\b{word}\b", line, flags=re.IGNORECASE):
                if is_builtin_type_annotation(line, word):
                    continue
                findings.append(
                    Finding(
                        path,
                        index,
                        "generic-abstraction-language",
                        f"Generic term `{word}` found in a declaration/API surface.",
                        "Replace with domain language when this is not a boundary type.",
                        severity="medium",
                        confidence=0.55,
                        evidence=(
                            "generic noun appears in a declaration or API surface",
                        ),
                    )
                )
                break
    return findings


def is_builtin_type_annotation(line: str, word: str) -> bool:
    if word != "object":
        return False
    return bool(re.search(r"(->|:)\s*[^#=]*\bobject\b", line))


def scan_text_patterns(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for match in TRY_LOG_RETHROW_RE.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        findings.append(
            Finding(
                path,
                line,
                "faux-robustness",
                "Catch block appears to log and rethrow without recovery.",
                "Remove it or add meaningful context/recovery.",
                severity="high",
                confidence=0.8,
                evidence=("catch block logs and rethrows",),
            )
        )

    for match in JS_PASS_THROUGH_RE.finditer(text):
        params = split_args(match.group(2) or match.group(4))
        forwarded = split_args(match.group(6))
        if params and params == forwarded:
            line = text.count("\n", 0, match.start()) + 1
            findings.append(
                Finding(
                    path,
                    line,
                    "pass-through-layer",
                    "Function forwards unchanged arguments.",
                    "Inline or move real validation/mapping into this layer.",
                    severity="high",
                    confidence=0.85,
                    evidence=("parameters and forwarded arguments match exactly",),
                )
            )

    return findings


def scan_python_ast(path: Path, text: str, config: ScannerConfig) -> list[Finding]:
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        return [
            Finding(
                path,
                error.lineno or 1,
                "incomplete-generation",
                f"Python syntax error: {error.msg}.",
                "Repair before deeper refactoring.",
            )
        ]

    function_defs, pass_through_lines, findings = collect_python_functions(path, tree)
    calls = collect_python_calls(tree)
    findings.extend(
        scan_single_use_functions(path, function_defs, calls, pass_through_lines, config)
    )

    return findings


def collect_python_functions(
    path: Path,
    tree: ast.AST,
) -> tuple[dict[str, ast.FunctionDef | ast.AsyncFunctionDef], set[int], list[Finding]]:
    function_defs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    pass_through_lines: set[int] = set()
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        function_defs[node.name] = node
        function_findings, is_pass_through = scan_python_function(path, node)
        findings.extend(function_findings)
        if is_pass_through:
            pass_through_lines.add(node.lineno)
    return function_defs, pass_through_lines, findings


def collect_python_calls(tree: ast.AST) -> Counter[str]:
    calls: Counter[str] = Counter()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = called_name(node.func)
        if name:
            calls[name] += 1
    return calls


def scan_single_use_functions(
    path: Path,
    function_defs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    calls: Counter[str],
    pass_through_lines: set[int],
    config: ScannerConfig,
) -> list[Finding]:
    findings: list[Finding] = []
    for name, node in function_defs.items():
        if name == "main" or node.lineno in pass_through_lines:
            continue
        if calls[name] == 1:
            findings.append(classify_single_use_function(path, name, node, config))
    return findings


def scan_python_function(
    path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[list[Finding], bool]:
    findings: list[Finding] = []
    is_pass_through = is_python_pass_through(node)
    if is_pass_through:
        findings.append(
            Finding(
                path,
                node.lineno,
                "pass-through-layer",
                f"`{node.name}` forwards unchanged arguments.",
                "Inline if no boundary, validation, or mapping is added.",
                severity="high",
                confidence=0.9,
                evidence=(
                    "single return statement delegates same parameters unchanged",
                ),
            )
        )

    silent_fallback = broad_silent_fallback(node)
    if silent_fallback is not None:
        findings.append(
            Finding(
                path,
                silent_fallback,
                "silent-fallback",
                f"`{node.name}` catches a broad exception and returns an empty fallback.",
                "Define failure semantics; recover explicitly or let the exception propagate.",
                severity="high",
                confidence=0.85,
                evidence=("broad exception handler returns pass/None/empty literal",),
            )
        )

    erosion = structural_erosion(node)
    if erosion is not None:
        branch_count, line_span = erosion
        findings.append(
            Finding(
                path,
                node.lineno,
                "structural-erosion",
                f"`{node.name}` concentrates {branch_count} branches across {line_span} lines.",
                "Look for a domain table, state model, or split by real invariant before adding more branches.",
                severity="medium",
                confidence=0.7,
                evidence=(
                    "branch-heavy function is a common long-horizon agent degradation shape",
                ),
            )
        )

    return findings, is_pass_through


def broad_silent_fallback(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int | None:
    for child in ast.walk(node):
        if not isinstance(child, ast.Try):
            continue
        for handler in child.handlers:
            if catches_broad_exception(handler) and all(
                is_empty_fallback(statement) for statement in handler.body
            ):
                return handler.lineno
    return None


def catches_broad_exception(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Name):
        return handler.type.id in {"Exception", "BaseException"}
    if isinstance(handler.type, ast.Tuple):
        return any(
            isinstance(exception, ast.Name)
            and exception.id in {"Exception", "BaseException"}
            for exception in handler.type.elts
        )
    return False


def is_empty_fallback(statement: ast.stmt) -> bool:
    if isinstance(statement, ast.Pass):
        return True
    if not isinstance(statement, ast.Return):
        return False
    value = statement.value
    if value is None:
        return True
    if isinstance(value, ast.Constant):
        return value.value in {None, False, "", 0}
    if isinstance(value, ast.Dict):
        return not value.keys
    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        return not value.elts
    return False


def structural_erosion(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[int, int] | None:
    line_span = (node.end_lineno or node.lineno) - node.lineno + 1
    branch_nodes = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.IfExp)
    match_node = getattr(ast, "Match", None)
    if match_node is not None:
        branch_nodes = (*branch_nodes, match_node)
    branch_count = sum(1 for child in ast.walk(node) if isinstance(child, branch_nodes))
    if branch_count >= 8 and line_span >= 15:
        return branch_count, line_span
    return None


def scan_lsp_transport_contract(file_texts: dict[Path, str]) -> list[Finding]:
    findings: list[Finding] = []
    lsp_sites = [
        (path, line_number(text, match.start()))
        for path, text in file_texts.items()
        for match in LSP_CREATE_CONNECTION_RE.finditer(text)
    ]
    if not lsp_sites:
        return findings

    has_transport_arg = any(
        LSP_TRANSPORT_ARG_RE.search(text) for text in file_texts.values()
    )
    if has_transport_arg:
        return findings

    path, line = lsp_sites[0]
    findings.append(
        Finding(
            path,
            line,
            "lsp-transport-contract",
            "LSP server creates a connection, but scanned launcher code has no explicit transport argument.",
            "Verify the wrapper or package script launches the server with --stdio, --node-ipc, or --socket.",
            severity="high",
            confidence=0.8,
            evidence=(
                "createConnection found",
                "no --stdio/--node-ipc/--socket found in scanned files",
            ),
        )
    )
    return findings


def is_python_pass_through(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = [
        statement
        for statement in node.body
        if not isinstance(statement, ast.Expr) or not is_docstring(statement)
    ]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return False
    call = body[0].value
    if not isinstance(call, ast.Call):
        return False

    params = [arg.arg for arg in node.args.args]
    if params and params[0] in {"self", "cls"}:
        params = params[1:]
    forwarded = [arg.id for arg in call.args if isinstance(arg, ast.Name)]
    return bool(params) and params == forwarded and len(call.args) == len(params)


def classify_single_use_function(
    path: Path,
    name: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    config: ScannerConfig,
) -> Finding:
    lowered = name.lower()
    evidence = ["called once in this file"]
    action = "Check repo-wide usage; inline if it is not a real concept."
    severity = "low"
    confidence = 0.25
    message = f"`{name}` is a single-use helper; this may be fine if the name carries a real concept."

    if name.startswith("_"):
        evidence.append("private helper")
        confidence -= 0.05

    if GENERIC_FUNCTION_RE.search(name):
        evidence.append("generic generated-style function name")
        severity = "medium"
        confidence = 0.75
        message = f"`{name}` is single-use and generically named."
    elif any(lowered.endswith(suffix.lower()) for suffix in config.generic_suffixes):
        evidence.append("generic architecture/job-title suffix")
        severity = "medium"
        confidence = 0.65
        message = f"`{name}` is single-use and uses a generic role suffix."
    elif any(word in lowered for word in config.generic_words):
        evidence.append("generic noun in helper name")
        severity = "medium"
        confidence = 0.6
        message = f"`{name}` is single-use and uses generic language."
    elif executable_statement_count(node) <= 2:
        evidence.append("tiny helper body")
        confidence = 0.35

    return Finding(
        path,
        node.lineno,
        "single-use-abstraction",
        message,
        action,
        severity=severity,
        confidence=max(0.0, min(confidence, 1.0)),
        evidence=tuple(evidence),
    )


def is_contractual_name(name: str, config: ScannerConfig) -> bool:
    return name in config.contractual_names


def executable_statement_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return sum(
        1
        for statement in node.body
        if not isinstance(statement, ast.Expr) or not is_docstring(statement)
    )


def is_scanner_pattern_definition(line: str) -> bool:
    stripped = line.strip()
    return "_RE =" in line or "GENERIC_" in line or stripped.startswith(('r"', "r'"))


def is_docstring(statement: ast.Expr) -> bool:
    return isinstance(statement.value, ast.Constant) and isinstance(
        statement.value.value, str
    )


def called_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def split_args(raw: str | None) -> list[str]:
    if raw is None:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def display_parts(path: Path) -> tuple[str, ...]:
    try:
        return path.relative_to(Path.cwd()).parts
    except ValueError:
        return path.parts


def scan_file_shape(files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    by_dir: dict[Path, list[Path]] = defaultdict(list)
    for file in files:
        by_dir[file.parent].append(file)

    for directory, siblings in by_dir.items():
        if len(siblings) < 4:
            continue
        line_counts = []
        for file in siblings:
            try:
                line_counts.append(
                    (
                        file,
                        len(
                            file.read_text(
                                encoding="utf-8", errors="replace"
                            ).splitlines()
                        ),
                    )
                )
            except OSError:
                continue
        counts = Counter(count for _, count in line_counts)
        repeated = [
            count for count, amount in counts.items() if amount >= 3 and count > 20
        ]
        for count in repeated:
            names = [
                file.name for file, line_count in line_counts if line_count == count
            ][:5]
            findings.append(
                Finding(
                    directory,
                    1,
                    "ai-symmetry",
                    f"{len(names)} sibling files have exactly {count} lines: {', '.join(names)}.",
                    "Check for mechanically mirrored structure; consolidate or specialize.",
                )
            )

    return findings


if __name__ == "__main__":
    raise SystemExit(main())
