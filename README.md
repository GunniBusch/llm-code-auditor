# LLM Code Auditor

Dedicated Codex plugin repository for `llm-code-auditor`.

The plugin helps coding agents refactor AI-shaped code into compact, readable, efficient, task-fit code with senior maintainer judgment. It focuses on:

- preserving real abstractions and removing unearned machinery
- adapting existing repo concepts instead of inventing parallel helpers
- detecting generated-code smells and long-horizon structural erosion
- repairing brittle or reward-hacked tests
- verifying dependency/API surfaces before trusting generated code
- benchmarking prompt and skill changes against repeatable quality cases

## Repository Layout

```text
.agents/plugins/marketplace.json
plugins/llm-code-auditor/
  .codex-plugin/plugin.json
  assets/
  skills/
```

Codex discovers the repo-local marketplace at `.agents/plugins/marketplace.json`. The marketplace includes only `llm-code-auditor` and points to `./plugins/llm-code-auditor`.

## Validation

Run the plugin checks:

```bash
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 -m json.tool plugins/llm-code-auditor/.codex-plugin/plugin.json >/dev/null
python3 -m py_compile \
  plugins/llm-code-auditor/skills/llm-code-auditor/scripts/llm_code_smell_scan.py \
  plugins/llm-code-auditor/skills/llm-code-auditor/scripts/quality_benchmark.py
python3 plugins/llm-code-auditor/skills/llm-code-auditor/scripts/test_llm_code_smell_scan.py
python3 plugins/llm-code-auditor/skills/llm-code-auditor/scripts/test_quality_benchmark.py
python3 plugins/llm-code-auditor/skills/llm-code-auditor/scripts/quality_benchmark.py \
  plugins/llm-code-auditor/skills/llm-code-auditor/benchmarks
```

If the local Codex validation scripts are available:

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/llm-code-auditor
for d in plugins/llm-code-auditor/skills/*; do
  python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$d"
done
```

## Publishing

Intended GitHub repository:

```text
https://github.com/GunniBusch/llm-code-auditor
```

After the GitHub repo exists:

```bash
git remote set-url origin https://github.com/GunniBusch/llm-code-auditor.git
git push -u origin main
```

## License

BSD 3-Clause. See `LICENSE`.
