# Code Quality Benchmark Rubric

Use this rubric when tuning `SKILL.md`, targeted skill prompts, remodel markup,
supporting heuristics, or agent instructions. A candidate refactor should pass
the behavior tests and improve maintainability without overfitting to the
benchmark fixture.

## Core Score

The automated runner reports:

- Expected smell coverage: bad fixture triggers the expected scanner findings.
- Expected remodel friction: bad fixture triggers the intended structural model pressure.
- Expected remodel markup: bad fixture renders the expected remodel syntax, so
  the model itself exposes bad placement, branch growth, unowned indirection, or
  silent failure.
- Expected lens pressure: bad fixture maps to the intended high-level quality frame.
- Reference implementation gate: gold refactor passes behavior tests and scanner thresholds.
- Candidate implementation gate: optional agent output passes the same tests and thresholds.
- Source-size gate: reference and candidate code must stay compact enough for
  the task when the case declares a line budget.
- Function-shape gate: reference and candidate code must keep individual
  functions short and low-branch when the case declares function budgets.

Treat the score as a regression signal, not a complete proof. A prompt change that improves one case while weakening another should be studied before shipping.

## Manual Review Dimensions

Score each candidate from 0 to 2:

- Task fit: solves the real behavior, including varied inputs and failure cases.
- Locality: keeps data, invariant, and behavior close enough to inspect.
- Function shape: no single function becomes the new hiding place for many
  decisions or phases.
- Abstraction judgment: removes unearned layers while preserving real boundaries.
- Adaptive reuse: uses existing repo concepts instead of inventing parallel helpers.
- Remodel quality: the agent-authored model clearly separates current ownership,
  intended ownership, useful boundaries, bad pressure, candidate moves, and proof
  needs.
- Source-backed idiom fit: uses current language, framework, field, and pattern guidance when local context is not enough.
- Test value: tests assert behavior, not private generated structure.
- Performance shape: chooses a better data structure or algorithm before adding machinery.
- Compactness: the rewrite removes accidental complexity without turning a small
  problem into a local framework.

Suggested interpretation:

- 0: AI-shaped or brittle; either over-engineered, under-specified, or prompt-hacked.
- 1: acceptable but still carries avoidable indirection, weak names, or test fragility.
- 2: code a strong maintainer would likely keep after review.

## Tuning Workflow

1. Run the benchmark before changing prompts or skills.
2. Change one prompt, remodel rule, skill, or support heuristic at a time.
3. Generate candidate refactors for the cases into a candidate root.
4. Run `quality_benchmark.py benchmarks --candidate-root <candidate-root>`.
5. For candidates involving framework, protocol, security, performance, or domain-specific idioms, check current primary sources before scoring style or architecture.
6. Write or inspect the candidate's before/after remodel before scoring the
   source rewrite.
7. Manually review candidates with this rubric.
8. Promote prompt changes only when automated scores and manual review both improve or stay stable.
