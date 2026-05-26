---
name: llm-code-auditor
description: Use when asked to audit, review, clean up, de-AI, simplify, harden, or improve code that may be AI-generated, agent-written, over-engineered, redundant, brittle, too generic, too strict, too defensive, hard to read, inefficient, or likely to hide bugs.
---

# LLM Code Auditor

Use this umbrella skill to turn "plausible generated code" into code a sharp maintainer would accept. Treat LLM-ness as a hypothesis, not a verdict: prove issues from local context, tests, types, call sites, and runtime behavior.

The goal is not to abolish abstraction or compress code at any cost. The goal is code that is compact enough, readable, efficient, locally idiomatic, and fit for the task. Good cleanup preserves useful boundaries and removes machinery that does not earn its keep.

## Easy Entry

When the user asks to "run the code auditor", "clean up AI code", "de-AI this",
"make this human-quality", or uses one of the prompts in
`references/easy-entry-prompts.md`, enter remodel-first mode:

```text
Run a remodel-first code quality pass: model behavior, ownership, and maintainer
feedback first in strict CMML, treat static findings as secondary, then make
compact behavior-preserving improvements with proof.
```

The easy prompt is only an entry point. Once the work is non-trivial, write the
strict Code Remodel Markup model before deciding edits.

## Remodel-First Protocol

For substantial cleanup, do not start by hunting individual static findings. Use
the LLM as the modeling tool:

1. Inspect the changed files, surrounding call sites, tests, and nearby repo patterns before editing.
2. State the behavior, invariants, side effects, and compatibility constraints that must remain true. If you cannot say what the code is for, do not judge its shape yet.
3. Search for the existing repo concept that should own the work: parser, schema, route, command registry, state model, adapter, lifecycle hook, domain module, or tested helper.
4. When idioms, performance expectations, security posture, or framework patterns matter, look up current best practices for the specific language, framework, field, subtopic, and pattern. Prefer primary sources: official docs, language references, framework guides, standards, release notes, and well-established project docs. Use those sources to calibrate judgment; do not copy generic advice or impose patterns that do not fit the local code.
5. Write a compact manual remodel when structure is unclear, duplicated, over-layered, squeezed into the wrong file, or hard to reason about. Use `references/remodel-first-framework.md` and `references/code-remodel-markup.md` for the syntax. Prefer strict CMML fact lines such as `@file`, `@sym`, `@pressure`, `@move_rule`, `@pass`, and `@after`. The model should show current ownership, intended ownership, misplaced responsibilities, additive paths, useful abstractions, candidate moves, guardrails, and proof needs through typed fields rather than loose paragraphs.
6. Run more than one modeling pass when the code is messy or the user gives critique. First model source and tests, then model explicit human feedback as evidence, then use static findings only as weak supporting leads.
7. Read the remodel before choosing edits. Too many `unowned-forwarder`, `branch-hub`, `silent-boundary`, `generic-boundary`, `spread-concept`, or `module-friction` entries should make the bad shape visible without needing an exact detector verdict.
8. Rewrite only after the ownership move is clear. Prefer moving behavior to the owner, splitting real phases, converting additive branches into a table/state/parser where appropriate, deleting unearned wrappers, and preserving boundaries that earn their place.
9. Verify with behavior tests, types, runtime checks, or a precise manual trace. For non-trivial cleanups, write a short after-remodel: what pressure was removed, what boundary was preserved, and what proof covers the rewrite.

The bundled scripts are support tools, not the core workflow.

Use the remodel script as a seed or sanity check when a local tree is available:

```bash
python3 scripts/code_remodel.py <path>
```

The generated remodel is not truth. Rewrite it manually when local ownership,
placement, or domain pressure is clearer than the heuristic output.

Run the quality lens when you need a coarse direction check:

```bash
python3 scripts/quality_lens.py <path>
```

The lens gives a fault-tolerant code-quality view across domain fit, economy, invariant ownership, failure semantics, change shape, and proof readiness. Use its primary frame to inspect the code, not as an edit checklist.

Run the heuristic scanner only when you need concrete leads beneath the model or a regression check. Do not let it override behavior, local ownership, or explicit maintainer feedback:

```bash
python3 scripts/llm_code_smell_scan.py <path>
```

The scanner prints severity, confidence, and evidence. Treat `HIGH` as an actionable lead, `MEDIUM` as likely worth inspection, and `LOW` as a weak review signal that may be legitimate human code. Use `--min-severity medium` to hide weak leads.

Read the reference that matches the work:
   - `references/easy-entry-prompts.md` for copy-paste prompts that trigger remodel-first mode.
   - `references/remodel-first-framework.md` for the agent workflow that treats manual remodel markup as the main interface.
   - `references/code-remodel-markup.md` for the remodel language and how to use it before rewriting.
   - `references/refactoring-guide-map.md` for mapping remodel pressure to Fowler/Refactoring Guru move families.
   - `references/senior-refactor-playbook.md` for deep cleanup, adaptive reuse, and "make it human-quality" requests.
   - `references/pattern-catalog.md` for generated-code smell families and fixes.
   - `references/llm-failure-taxonomy.md` for correctness risks that clean-looking generated code often hides.
   - `references/human-code-quality.md` for code-review standards and stopping criteria.

When tuning this skill, remodel, lens, or scanner behavior, run `scripts/quality_benchmark.py benchmarks`. To compare agent outputs, place candidate refactors in one directory per benchmark case and run `scripts/quality_benchmark.py benchmarks --candidate-root <path>`.

## Quality Contract

Before editing, hold the code to these standards:

- Fit: it solves the product/repo task, not merely the prompt example.
- Locality: data, invariant, and behavior are close enough to inspect together.
- Economy: every exported type, layer, option, retry, cache, dependency, and branch has a current reason.
- Adaptation: it reuses existing repo concepts, schemas, lifecycle hooks, and helper APIs instead of inventing parallel machinery.
- Proof: tests, types, runtime checks, or a precise trace show behavior stayed correct.

## Forward-Test Lessons

When an agent uses this skill and reports a scanner finding, calibrate it before editing:

- Protocol/framework names are often contractual. Do not rename LSP capabilities such as `codeActionProvider`, even though `Provider` is usually suspicious.
- Protocol/runtime startup requires the launcher to satisfy the runtime contract. If a server says its input stream, socket, IPC channel, working directory, bundle, or generated artifact is missing, inspect the wrapper/package command before changing core business logic.
- Generated build output is not source truth. If tests depend on ignored output such as `server/out`, make scripts deterministic instead of committing stale generated files.
- Process smoke tests need valid exit expectations. A server run with closed stdin may exit nonzero because no protocol session occurred; treat absence of the original crash separately from exit code.
- If a scanner warning is a false positive, improve the scanner or add an exception with evidence. Do not train future agents to ignore scanner output generally.

## Targeted Skills

Use the narrower skill when the task matches a specific smell family:

- `abstraction-pruner`: unowned interfaces, pass-through layers, redundant one-time methods, factories, strategies, event buses, managers.
- `boundary-invariant-auditor`: redundant checks, missing boundary validation, too-strict validation, impossible states, guard clutter.
- `domain-readability-refactor`: vague naming, utility dumping, narration comments, feature envy, poor locality.
- `generated-test-auditor`: brittle LLM tests, duplicated test cases, over-mocking, implementation-detail assertions, weak assertions.
- `dependency-api-hallucination-check`: hallucinated packages, imports, methods, attributes, configuration, examples, docs.
- `performance-simplicity-auditor`: inefficient generated code, fake optimization, caches/retries/parallelism without proof.

## Audit Workflow

### 1. Map intent before judging style

Identify the domain operation, public API boundaries, persistence/network boundaries, and test surface. Do not remove an abstraction until you know whether it encodes a real boundary: external dependency, polymorphism with multiple real implementations, security boundary, transaction boundary, lifecycle boundary, or shared domain vocabulary.

Search for nearby code that already solves a related problem. Generated code often duplicates an existing shape with different names; high-quality cleanup adapts the existing concept instead of creating a second mini-framework.

Check current external guidance when local context is not enough. For example, a Python parser, React component, Rust async path, SQL query builder, LSP server, cryptography helper, or payment workflow may have language- and domain-specific best practices that change what "simple" or "robust" means. Use external guidance as calibration, then reconcile it with the repo's own style and constraints.

When the structure is the problem, remodel before rewriting. The remodel should make bad placement visible indirectly: too many `unowned-forwarder` / `empty-boundary` symbols, generic ownership, repeated operation names, branch hubs, or silent boundaries often show where the source code is fighting the domain shape.

### 2. Search for high-confidence generated-code patterns

Prioritize patterns that have simple fixes and low behavioral risk:

- Unowned indirection: one interface, one implementation, one caller, or wrapper forwarding unchanged arguments without owning a phase, policy, invariant, protocol, or readability improvement.
- Naming inflation: `Manager`, `Service`, `Processor`, `Handler`, `Provider`, `Factory`, `Controller`, `Engine` hiding trivial or mixed responsibilities.
- Utility dumping: `utils`, `helpers`, `common`, `shared`, `base` accumulating unrelated behavior.
- Comment narration: comments that restate the next line.
- Pass-through layers: methods that only delegate with the same arguments.
- Speculative extensibility: plugin/strategy/event/config systems with one real participant.
- AI symmetry: mechanically mirrored CRUD, equally shaped files, or repeated function skeletons where the domain needs specialization.
- Excessive defensive programming: impossible null checks, duplicated validation in every layer, `try/catch` that only logs and rethrows.
- Over-fragmentation: tiny one-class files and deep directories without a real module boundary.
- Generic abstraction language: `entity`, `item`, `object`, `data`, `info`, `processData`, `handleRequest`, `executeTask`.
- Silent broad fallbacks: `catch/except Exception` returning empty data, `None`, or a default that hides failure.
- Structural erosion: one function, class, or file absorbing every new requirement through more branches, flags, wrappers, and special cases instead of reconnecting code to the right owner.

### 3. Add LLM-specific correctness checks

Look beyond style. LLM-generated code often looks clean while failing at context:

- Missing corner cases: empty input, duplicate input, timezone/locale, pagination, partial failure, cancellation, concurrency, idempotency.
- Wrong input type or shape: code assumes prompt examples are exhaustive.
- Hallucinated object or attribute: API names that compile only in the model's imagination.
- Prompt-biased behavior: hard-coded sample values, demo defaults, or logic that solves the prompt but not the product.
- Incomplete generation: TODO paths, unreachable stubs, no-op catches, half-wired config, missing cleanup.
- Non-prompted consideration: extra behavior the user did not ask for, especially persistence, telemetry, network calls, broad permissions, or retries.
- Security drift: unsafe string construction, path traversal, weak auth checks, leaking secrets in logs, trusting generated input validation.
- Test drift: tests that mirror generated structure, overfit to examples, assert implementation details, or become too strict to allow safe refactoring.
- Reward hacking: code that satisfies visible tests by hard-coding fixtures, memorizing examples, weakening validation, or bypassing real behavior.

### 4. Refactor toward high-quality human code

Apply these transformations:

- Collapse abstractions only when they do not own a current responsibility.
- Keep abstractions that encode real substitution, lifecycle, security, transactions, protocol contracts, named algorithm phases, trust boundaries, or domain vocabulary that makes call sites clearer.
- Rename to domain nouns and verbs visible in product language, schema names, protocols, and user workflows.
- Move behavior to the data or module that owns the invariant.
- Reconnect additive code by moving, merging, or rewriting it so the next requirement changes one owner instead of another scattered branch or wrapper.
- Replace repeated shape with a smaller data model, table-driven mapping, or one specialized path per real domain distinction.
- Centralize validation at trust boundaries; use types and constructors to make invalid states unrepresentable. Remove the 10th repeated `if` when upstream invariants already prove it.
- Prefer standard library and framework idioms already used in the repo.
- Remove comments that narrate; keep comments that explain surprising constraints, tradeoffs, protocol rules, or bug workarounds.
- Delete unused config, optionality, and extension points unless there is a second real use now.
- Stop when the next change is taste, not maintainability, correctness, performance, or reviewability.

## Senior Refactor Loop

Use this loop for substantial cleanup:

1. Name the current behavior and one uncomfortable path: empty input, duplicate input, partial failure, invalid shape, concurrency, localization, or security edge.
2. Find existing repo concepts that should own the work: schema, parser, route, state machine, lifecycle hook, domain model, or tested helper.
3. Decide what each layer earns: mapping, validation, authorization, transaction, caching, lifecycle, observability, polymorphism, or protocol compatibility.
4. Delete, inline, or move code until each invariant has one owner.
5. Rename after movement, using the owning domain concept.
6. Repair tests so they assert observable behavior, not private generated structure.
7. Verify with the narrowest command that proves the changed path, then run broader checks as risk increases.

## Guardrails

- Do not "simplify" public APIs, database schemas, migrations, serialized formats, or plugin interfaces without checking compatibility.
- Do not rename external protocol, schema, framework, or API vocabulary just because it contains words like `Provider`, `Handler`, `Service`, `data`, or `payload`; those names may be contractual.
- Do not rely on stale memory for language, framework, security, performance, accessibility, or protocol guidance when current docs or primary sources can settle the question.
- Do not assume nonzero smoke-test exit means startup failure when the command expects an interactive protocol session; inspect stderr/stdout for the specific failure being tested.
- Do not inline test seams, dependency injection for external services, security boundaries, or concurrency boundaries just because there is one implementation.
- Do not replace domain code with clever abstractions. High-quality code is often boring, direct, and locally obvious.
- Keep a before/after behavior proof: test, type check, static analysis, or a precise manual trace.
- Do not let green tests override clear product mismatch, hard-coded examples, unsafe defaults, or dependency/API guesses.

## Output Shape

For review-only tasks, lead with findings ordered by severity and include file/line references. For fix tasks, summarize the deleted/renamed/collapsed patterns and the verification commands run.
