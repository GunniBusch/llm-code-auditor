# LLM Code Auditor

Codex plugin for refactoring AI-shaped code into compact, readable, efficient, task-fit code with senior maintainer judgment. It bundles an umbrella skill plus targeted skills for focused cleanup.

The bundled skill teaches Codex to audit code for patterns such as:

- single-use abstractions
- inflated generic naming
- utility dumping
- narration comments
- pass-through layers
- speculative extensibility
- AI symmetry
- excessive defensive programming
- hallucinated APIs and attributes
- prompt-biased or incomplete code

It also includes a dependency-free heuristic scanner:

```bash
python3 plugins/llm-code-auditor/skills/llm-code-auditor/scripts/llm_code_smell_scan.py <path>
```

Scanner output includes severity, confidence, and evidence. Low-severity findings are review leads, not automatic refactor instructions:

```bash
python3 plugins/llm-code-auditor/skills/llm-code-auditor/scripts/llm_code_smell_scan.py --min-severity medium <path>
```

Run scanner regression tests:

```bash
python3 plugins/llm-code-auditor/skills/llm-code-auditor/scripts/test_llm_code_smell_scan.py
```

Run code-quality benchmarks:

```bash
python3 plugins/llm-code-auditor/skills/llm-code-auditor/scripts/quality_benchmark.py \
  plugins/llm-code-auditor/skills/llm-code-auditor/benchmarks
```

Use `--candidate-root <path>` to evaluate agent-produced refactors against the benchmark behavior tests and scanner thresholds.

## Targeted Skills

- `llm-code-auditor`: umbrella audit for generated or agent-written code.
- `abstraction-pruner`: remove speculative abstractions and pass-through layers.
- `boundary-invariant-auditor`: fix redundant checks, missing boundary validation, and too-strict validation.
- `domain-readability-refactor`: improve naming, locality, comments, and domain language.
- `generated-test-auditor`: repair brittle, over-mocked, weak, or implementation-detail tests.
- `dependency-api-hallucination-check`: verify packages, imports, methods, attributes, and config.
- `performance-simplicity-auditor`: improve efficiency without fake optimization or excess machinery.

## Quality Goal

The plugin is not meant to remove every abstraction. It teaches the agent to keep real boundaries, reuse existing repo concepts, collapse unearned machinery, repair brittle tests, verify dependency/API surfaces, and stop when the next change would be taste rather than code health.
