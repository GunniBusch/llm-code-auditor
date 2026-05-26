# Remodel-First Agent Framework

Use this framework when code quality is the actual task, not just one local
warning. The LLM is the modeling tool: it should redraw the codebase in compact
Code Remodel Markup, use that alternate view to see structural pressure, then
rewrite source only after ownership and proof are clear.

The Python tools are support machinery. They can seed a model, catch benchmark
regressions, or provide concrete evidence, but they are not the product and they
are not the main reasoning path.

Explicit human feedback is a secondary source of truth after source behavior and
repo constraints. If a maintainer says a reference refactor is worse, an
abstraction is useful, a file is misplaced, or a pattern is too verbose, model
that feedback in the next pass instead of arguing from static findings.

## Research Calibration

Use these sources as calibration, then reconcile them with local repo evidence:

- Google Engineering Practices: review design first, then functionality,
  complexity, tests, naming, comments, style, consistency, documentation, every
  line, and broader context. https://google.github.io/eng-practices/review/reviewer/looking-for.html
- Google code review standard: improve code health without chasing perfection.
  https://google.github.io/eng-practices/review/reviewer/standard.html
- Martin Fowler, Code Smell: smells are surface indicators that require deeper
  investigation. https://martinfowler.com/bliki/CodeSmell.html
- Fowler refactoring catalog changes: modern move vocabulary includes Extract
  Function, Move Function, Split Phase, and Change Function Declaration.
  https://martinfowler.com/articles/refactoring-2nd-changes.html
- Refactoring Guru: smell families include bloaters, change preventers,
  dispensables, couplers, and conditional/object-orientation misuse.
  https://refactoring.guru/refactoring/smells
- PEP 8: project style takes precedence, readability and local consistency
  matter, and obvious comments are distracting. https://peps.python.org/pep-0008/
- Rust API Guidelines: good APIs are predictable, interoperable, type-safe,
  dependable, debuggable, and future-proof. https://rust-lang.github.io/api-guidelines/checklist.html
- SlopCodeBench: repeated agent edits can pass checkpoints while increasing
  verbosity and structural erosion. https://arxiv.org/abs/2603.24755
- SpecBench: visible tests can encourage reward hacking instead of genuine
  working systems. https://arxiv.org/abs/2605.21384
- Bugs in LLM Generated Code: recurring patterns include misinterpretation,
  prompt-biased code, missing corner cases, wrong input type, hallucinated
  object, wrong attribute, incomplete generation, and non-prompted behavior.
  https://arxiv.org/abs/2403.08937

When a language, framework, protocol, security domain, performance topic, or UI
pattern matters, research the current primary source before deciding that code is
good or bad. Local code still wins when the external guide and the repo disagree
for a reason.

## Core Protocol

1. **Scope the behavior.** State the user-visible operation, call path, inputs,
   outputs, side effects, and compatibility constraints.
2. **Find local precedent.** Search for nearby parsers, schemas, adapters,
   state models, command registries, route handlers, lifecycle hooks, and tests.
3. **Research the specific idiom.** Check current primary sources for the
   language/framework/subtopic when local precedent is weak or high-stakes.
4. **Write a compact manual remodel.** Model only the files, flows, decisions, and
   symbols that explain the shape problem. Do not list every line.
5. **Run multiple modeling passes.** First model source and tests, then reconcile
   explicit human feedback if present, then use static analyzer output only as a
   weak check for missed pressure.
6. **Read the remodel as structure.** Look for too many
   `unowned-forwarder`, `branch-hub`, `silent-boundary`, `generic-boundary`,
   `spread-concept`, and `module-friction` entries. The syntax should make the
   bad shape visible before an exact edit is chosen.
7. **Name the intended ownership.** For each pressure point, state where the
   responsibility should live and why the current location fights that shape.
8. **Choose move families.** Pick Extract Function, Inline Function, Move
   Function, Split Phase, Introduce Parameter Object, table-driven dispatch,
   state model, or direct deletion only after the guardrail is written.
9. **Rewrite with proof.** Add or repair tests when behavior risk is meaningful.
   Use types, test output, or a precise manual trace as evidence.
10. **Remodel the result.** The after-remodel should have fewer pressures, clearer
   owners, preserved useful boundaries, and no new speculative machinery.

## Manual Remodel Contract

A useful manual remodel is compact and opinionated. It should contain:

- `@context` with behavior, invariants, constraints, and proof surface.
- `@feedback` when a maintainer gave explicit critique, constraints, examples,
  or preferences that should influence the rewrite.
- `@module` entries with current ownership, intended ownership, misplaced
  responsibilities, and additive paths.
- `@flow` entries for user-visible operations, with the overgrown step named.
- `@decision` entries for branch hubs, including what the variation is really
  about.
- `@rewrite_pressure` that separates bad indirection from useful abstraction.
- `@refactor_moves` with candidate moves, guardrails, and required proof.
- `@after_remodel` after the rewrite, showing what pressure disappeared and
  what proof covers the result.
- `@remodel_passes` showing source/test, human-feedback, static-lead, and
  after-rewrite passes.

It should not:

- repeat scanner findings without adding ownership judgment
- treat analyzer output as more authoritative than code behavior or maintainer
  critique
- model perfect program logic
- copy source code from public projects or docs
- turn every long function into helpers
- inline every one-use abstraction
- remove framework, protocol, schema, security, transaction, lifecycle, or test
  boundaries just because they are single-use

## Good Structure Signals

- The next similar feature changes one owner instead of many branches.
- Parsing, validation, authorization, persistence, rendering, and side effects
  are distinguishable phases when the domain needs those phases.
- Abstractions protect current boundaries or name dense phases; they are not
  placeholders for imaginary future variants.
- Names come from the repo's domain, protocol, schema, CLI, UI, or data model.
- Failure behavior is explicit enough for callers and tests.
- Tests assert observable behavior and edge cases without freezing private
  generated structure.
- Performance comes from the right data shape first, not from decorative caches,
  retries, pooling, or concurrency.
- The remodel is short enough to reread in one pass while still naming behavior,
  owners, pressure, move, guardrail, and proof.

## Bad Structure Signals

- Additive drift: each new requirement adds another branch, option, or wrapper to
  the same place.
- Unowned indirection: a class, service, helper, or function forwards work
  without owning mapping, policy, validation, lifecycle, or a named phase.
- Wrong placement: code repeatedly reaches into another object, module, schema,
  or state shape to do work that belongs there.
- Squeezed file: one file owns unrelated parse, policy, storage, rendering,
  retry, and orchestration concerns.
- Symmetric generated shape: repeated files or methods have the same skeleton
  even though the domain cases should differ.
- Silent failure: broad fallback returns empty data or default success without a
  documented contract.
- Test reward hacking: code satisfies visible examples while missing composed,
  invalid, duplicate, larger, or partial-failure cases.

## After-Remodel Check

Before calling a cleanup good, write a short after-remodel:

```text
@after_remodel
  behavior: "same observable contract or intentionally changed contract"
  owners: "one owner per invariant"
  preserved-boundaries: "real protocol, lifecycle, state, security, or phase boundaries kept"
  removed-pressure: "branch-hub | unowned-forwarder | silent-boundary | generic-boundary"
  remaining-pressure: "what is still imperfect and why it is acceptable"
  proof: "tests/types/manual trace"
```

If the after-remodel is longer than the before-remodel or needs more excuses,
the refactor probably made the code worse.
