# LLM Code Auditor Benchmarks

These benchmarks make plugin tuning repeatable. Each case contains:

- `before/`: intentionally AI-shaped code that should trigger scanner findings.
- `after_good/`: a compact reference refactor that preserves behavior.
- `tests/`: behavior tests used to evaluate `after_good` and optional candidate refactors.
- `case.json`: expected scanner findings, remodel friction, remodel markup terms, lens pressure, and reference quality thresholds.

Run all cases:

```bash
python3 scripts/quality_benchmark.py benchmarks
```

Evaluate an agent output directory:

```bash
python3 scripts/quality_benchmark.py benchmarks --candidate-root /path/to/candidates
```

The candidate root should contain one subdirectory per case id. A passing
candidate must pass the behavior tests and stay within the case's quality
thresholds, including source-size, maximum function length, and maximum branch
concentration limits where the reference would otherwise become more verbose or
harder to inspect than the bad fixture. Passing this benchmark does not prove
production quality; it provides a stable tuning signal for prompts, remodel
wording, skill wording, and supporting heuristics.

Run the quality lens on any individual case when tuning the higher-level agent frame:

```bash
python3 scripts/quality_lens.py benchmarks/cases/pass-through-service-stack/before
```

The benchmark gates still use concrete thresholds so regressions are
deterministic. The remodel markup gate checks that the language exposes the
structural pressure in its own syntax; the scanner and lens are supporting
signals. Each case can declare expected remodel friction, expected remodel
markup terms, expected lens pressure for bad code, and maximum lens pressure for
the reference refactor. The runner also compares each reference against its own
bad fixture and fails it when medium/high findings, core remodel friction, or
maximum lens pressure do not materially improve.

Some cases are calibrated from public-code structure studies. Their fixtures are
original neutral code: no copied source, no original domain names, and no
project-specific identifiers.

## Scoring Dimensions

- Expected smell coverage: the scanner catches known high-value problems in bad code.
- Expected remodel friction: the post-code model exposes structural pressure such as unowned forwarders, branch hubs, and silent boundaries.
- Expected remodel markup: the text model uses the remodel language to make those pressures visible to the agent.
- Expected lens pressure: the quality lens maps bad code to the intended abstract pressure, such as economy, failure semantics, or change shape.
- Behavior preservation: reference and candidate code pass hidden/varied tests, not just prompt examples.
- Maintainability gate: reference and candidate code avoid unresolved high/medium findings and remodel pressure according to case thresholds.
- Source-size gate: references and candidates stay compact enough for the task instead of replacing branchy code with a larger framework.
- Function-shape gate: references and candidates keep each function short and low-branch enough to inspect locally.
- Relative-improvement gate: each reference must improve over its own bad fixture on medium/high findings, core remodel friction, and maximum lens pressure.
- Tuneability: failures are reported per case so skill text, lens weights, and scanner heuristics can be adjusted without changing the benchmark goal.
