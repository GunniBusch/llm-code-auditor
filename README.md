# LLM Code Auditor

Codex plugin for refactoring AI-shaped code into compact, readable, efficient, task-fit code with senior maintainer judgment.

This repository is the plugin root. It is not a marketplace repository and does not contain a nested `plugins/llm-code-auditor` wrapper.

## What It Provides

- an umbrella `llm-code-auditor` skill for generated or agent-written code cleanup
- targeted skills for abstraction pruning, boundary invariants, readability, generated tests, dependency/API hallucinations, and performance simplicity
- a quality-lens tool that gives the agent a higher-level model of code quality pressure
- a dependency-free scanner for concrete generated-code review leads
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

Use `--candidate-root <path>` to evaluate agent-produced refactors against behavior tests and scanner thresholds.

## Validation

Run the full local validation suite:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache uv run python scripts/validate.py
```

The validation runner checks:

- plugin manifest JSON
- Python compilation
- scanner regression tests
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
