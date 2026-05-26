# Easy Entry Prompts

Use these prompts when you want the agent to enter remodel-first cleanup mode
without knowing the markup syntax.

## Quick Fix Mode

```text
Use LLM Code Auditor. Run a remodel-first code quality pass on the changed code.
First model behavior, ownership, pressure, useful boundaries, and proof needs in
strict CMML. Treat static findings as secondary leads. Then make only
behavior-preserving improvements that reduce structural pressure, and show the
proof.
```

## Review-Only Mode

```text
Use LLM Code Auditor in review-only mode. Do not edit yet. Build a strict CMML
remodel of the relevant files and flows, then report the smallest set of
high-confidence cleanup findings. Static findings are secondary. Separate
unearned indirection from useful abstraction, and name the proof needed before a
rewrite.
```

## Deep Cleanup Mode

```text
Use LLM Code Auditor for a deep behavior-preserving cleanup. Read nearby call
sites, tests, and repo patterns first. If framework or language idioms matter,
check current primary sources. Write a strict CMML remodel, reconcile any human
feedback as evidence, choose ownership moves from the remodel, refactor, and
prove the result with tests, types, or a precise trace.
```

## Benchmark Candidate Mode

```text
Use LLM Code Auditor to produce a benchmark candidate. Start with a strict CMML
remodel of the before code. Refactor only after the target owner, pressure, move,
guardrail, and proof are explicit. Keep the result compact, behavior-preserving,
and lower-pressure than the original. Run the benchmark and report the score.
```

## Minimal Trigger

```text
Run a remodel-first code quality pass: model behavior, ownership, and maintainer
feedback first in strict CMML, treat static findings as secondary, then make
compact behavior-preserving improvements with proof.
```
