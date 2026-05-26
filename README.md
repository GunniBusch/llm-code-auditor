# LLM Code Auditor

Codex plugin for refactoring AI-shaped code into compact, readable, efficient, task-fit code with senior maintainer judgment.

This repository is the plugin root. It is not a marketplace repository and does not contain a nested `plugins/llm-code-auditor` wrapper.

## What It Provides

- an umbrella `llm-code-auditor` skill for generated or agent-written code cleanup
- targeted skills for abstraction pruning, boundary invariants, readability, generated tests, dependency/API hallucinations, and performance simplicity
- a remodel-first agent framework that uses manual Code Remodel Markup as the primary cleanup interface
- a code-remodel markup tool that can seed or sanity-check the manual model
- a quality-lens tool that gives the agent a higher-level model of code quality pressure
- a dependency-free scanner for concrete generated-code review leads and regression checks
- repeatable quality benchmarks for prompt and skill tuning
- a `uv`-backed validation command for the plugin, tools, and benchmark suite

## Layout

```text
.codex-plugin/plugin.json
assets/
skills/
scripts/validate.py
pyproject.toml
```

The marketplace repo should include this repository as the plugin source instead of copying the plugin into a nested local folder.

## Remodel-First Framework

The plugin is centered on the agent-authored remodel, not static analysis. For
substantial cleanup, the agent should read the code, write a compact model of
ownership and pressure, then use that alternate view to decide what to move,
inline, preserve, or rewrite.

The framework is documented in
`skills/llm-code-auditor/references/remodel-first-framework.md`. It teaches the
agent to:

- scope behavior, invariants, side effects, and compatibility before editing
- search for local owners such as parsers, schemas, route boundaries, command
  registries, state models, adapters, lifecycle hooks, and tested helpers
- use current primary sources when language, framework, security, performance,
  protocol, or field-specific idioms matter
- write manual `@context`, `@module`, `@flow`, `@decision`,
  `@feedback`, `@rewrite_pressure`, `@refactor_moves`, `@remodel_passes`, and
  `@after_remodel` entries
- run multiple modeling passes, using explicit maintainer feedback as evidence
  and static analyzer output only as a secondary check
- preserve useful abstraction while removing unowned indirection, additive
  branch growth, wrong placement, silent failure, and squeezed files

The scripts are support machinery. They make tuning repeatable and can seed a
model, but the intended interface is the remodel the agent writes after reading
the code.

## Code Remodel

Use Code Remodel when exact findings are too narrow and the agent needs to see
the shape of the codebase. The primary artifact is a short manual remodel
written by the agent after reading the code; the script below is a seed and
sanity check:

```bash
python3 skills/llm-code-auditor/scripts/code_remodel.py <path>
python3 skills/llm-code-auditor/scripts/code_remodel.py --json <path>
```

The remodel output is a custom post-code markup. It represents modules, symbols, ownership, calls, repeated concepts, unowned forwarders, branch hubs, generic boundaries, silent failure boundaries, wrong placement, guide-backed refactor move candidates, and additive drift. Its purpose is not to perfectly model program logic; it makes structural problems visible so the agent can decide how to reshape the code.

Abstraction is treated as neutral. A one-use helper, class, or service can be the right code when it names a phase, protects a boundary, or makes an invariant readable. The remodel is meant to expose unowned indirection, redundant one-time methods, squeezed files, and code that keeps growing through branches and wrappers instead of being reconnected.

Version 3 of the markup is compact by default: it keeps behavior, owner,
pressure, move, guardrail, feedback, and proof information in short named
attributes so an agent can reread the whole model before editing.

The remodel language is calibrated against Fowler and Refactoring Guru references. It maps structural pressure to move families such as Extract Function, Inline Function, Move Function, Split Phase, Decompose Conditional, and Introduce Parameter Object while preserving the guardrail that smells are leads, not proof.

## Quality Lens

Run the quality lens first when the agent needs direction rather than a list of exact findings:

```bash
python3 skills/llm-code-auditor/scripts/quality_lens.py <path>
python3 skills/llm-code-auditor/scripts/quality_lens.py --json <path>
```

The lens summarizes pressure across domain fit, economy, invariant ownership, failure semantics, change shape, and proof readiness. It consumes scanner evidence, Python structure, and optional project configuration, then gives the agent a refactor frame instead of treating every exact match as a mandatory edit.

The skill explicitly allows source-backed research. When quality depends on a language, framework, field, subtopic, or pattern, the agent should consult current primary sources such as official docs, language references, standards, and well-established project guidance before deciding what good code looks like.

## Scanner

```bash
python3 skills/llm-code-auditor/scripts/llm_code_smell_scan.py <path>
python3 skills/llm-code-auditor/scripts/llm_code_smell_scan.py --min-severity medium <path>
```

Use the scanner for concrete evidence under a remodel or for regression checks.
It is intentionally not the main product: a finding is a lead, missing a finding
does not prove code is good, and explicit maintainer feedback can override the
shape suggested by a static lead.

Project-specific scanner configuration can be placed in `.llm-code-auditor.json`:

```json
{
  "ignore_patterns": ["generated/"],
  "contractual_names": ["customProvider"],
  "generic_suffixes": ["Manager", "Service", "Processor"],
  "lens_weights": {
    "naming-inflation": {
      "domain-fit": 0.8,
      "economy": 0.4
    }
  }
}
```

## Benchmarks

```bash
python3 skills/llm-code-auditor/scripts/quality_benchmark.py \
  skills/llm-code-auditor/benchmarks
```

Use `--candidate-root <path>` to evaluate agent-produced refactors against
behavior tests, remodel markup expectations, lens pressure, and scanner
thresholds.

## Validation

Run the full local validation suite:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache uv run python scripts/validate.py
```

The validation runner checks:

- plugin manifest JSON
- Python compilation
- scanner regression tests
- code-remodel regression tests
- quality-lens regression tests
- benchmark regression tests
- benchmark score
- Codex plugin and skill validators when available locally

## Marketplace Entry

The verified Codex marketplace entry shape uses a local plugin path. In the marketplace repository, include this repository as a submodule at `plugins/llm-code-auditor` and keep the entry local:

```json
{
  "name": "llm-code-auditor",
  "source": {
    "source": "local",
    "path": "./plugins/llm-code-auditor"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Coding"
}
```

## License

BSD 3-Clause. See `LICENSE`.
