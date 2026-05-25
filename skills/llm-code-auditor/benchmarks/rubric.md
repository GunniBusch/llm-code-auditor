# Code Quality Benchmark Rubric

Use this rubric when tuning `SKILL.md`, targeted skill prompts, scanner heuristics, or agent instructions. A candidate refactor should pass the behavior tests and improve maintainability without overfitting to the benchmark fixture.

## Core Score

The automated runner reports:

- Expected smell coverage: bad fixture triggers the expected scanner findings.
- Reference implementation gate: gold refactor passes behavior tests and scanner thresholds.
- Candidate implementation gate: optional agent output passes the same tests and thresholds.

Treat the score as a regression signal, not a complete proof. A prompt change that improves one case while weakening another should be studied before shipping.

## Manual Review Dimensions

Score each candidate from 0 to 2:

- Task fit: solves the real behavior, including varied inputs and failure cases.
- Locality: keeps data, invariant, and behavior close enough to inspect.
- Abstraction judgment: removes unearned layers while preserving real boundaries.
- Adaptive reuse: uses existing repo concepts instead of inventing parallel helpers.
- Test value: tests assert behavior, not private generated structure.
- Performance shape: chooses a better data structure or algorithm before adding machinery.

Suggested interpretation:

- 0: AI-shaped or brittle; either over-engineered, under-specified, or prompt-hacked.
- 1: acceptable but still carries avoidable indirection, weak names, or test fragility.
- 2: code a strong maintainer would likely keep after review.

## Tuning Workflow

1. Run the benchmark before changing prompts or skills.
2. Change one prompt/skill/scanner rule at a time.
3. Generate candidate refactors for the cases into a candidate root.
4. Run `quality_benchmark.py benchmarks --candidate-root <candidate-root>`.
5. Manually review candidates with this rubric.
6. Promote prompt changes only when automated scores and manual review both improve or stay stable.
