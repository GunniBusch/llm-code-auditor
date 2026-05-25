# Senior Refactor Playbook

Use this when the user asks for code to stop looking AI-written, over-engineered, duplicated, brittle, verbose, or "vibe coded." The target is not minimal code. The target is code a strong maintainer would keep because it is direct, adaptive, testable, efficient enough, and shaped by the domain.

## Research Anchors

- Tambon et al. identify recurring LLM-generated bug patterns: misinterpretation, prompt-biased code, missing corner cases, wrong input type, hallucinated object, wrong attribute, incomplete generation, and non-prompted consideration. https://arxiv.org/abs/2403.08937
- De-Hallucinator shows that grounding generation in project-specific API references improves generated code and fixes many hallucination-driven test failures. https://arxiv.org/abs/2401.01701
- SlopCodeBench shows coding agents can pass checkpoints while producing code that becomes more verbose and structurally eroded under repeated extension. https://arxiv.org/abs/2603.24755
- SpecBench shows agents can optimize for visible tests while missing the real specification, especially as task size grows. https://arxiv.org/abs/2605.21384
- Google Engineering Practices emphasize maintainability, understandability, useful tests, good names, and avoiding speculative complexity. https://google.github.io/eng-practices/review/reviewer/looking-for.html

## What "Human-Quality" Means

Human-quality code is:

- Fit for the actual task: it solves the real product case, not a prompt-shaped demo.
- Locally obvious: a reader can inspect data, invariant, and side effects without jumping through generic layers.
- Adaptive: it reuses existing repo concepts and bends them to the new case instead of cloning or inventing parallel structure.
- Economical: it has the fewest moving parts that still express the real boundaries.
- Efficient by shape: it chooses the right data model and algorithm before adding caches, concurrency, pools, retries, or framework machinery.
- Verifiable: tests and types protect behavior while allowing good refactors.

## The Maintainer Pass

1. Read the surrounding code before editing. Search for the same domain noun, route, table, schema, event, config key, lifecycle hook, or test fixture.
2. State the invariant in plain language. If the invariant is vague, rename nothing yet.
3. Mark trust boundaries: user input, network, filesystem, database, queue, env, public API, auth, and serialization.
4. Assign each invariant one owner. Good owners are parsers, constructors, schemas, state machines, route boundaries, or persistence adapters.
5. Delete repeated checks, wrappers, and options only after the owner is clear.
6. Rename from ownership. Better names usually appear after code moves to the right place.
7. Stop when the remaining issue is taste rather than behavior, maintainability, performance, or reviewability.

## Adaptive Reuse

LLMs often generate new code beside existing code because they do not notice the repo's internal language. A strong developer searches for a near miss and adapts it.

Prefer:

- extending an existing parser over adding a second validator
- adding a case to an existing domain table over adding mirrored branches
- using the framework lifecycle already in the repo over custom orchestration
- reusing a tested adapter over inventing an import that sounds right
- moving behavior to the module that owns the data over adding another service layer

Avoid:

- copying a nearby function and changing names without consolidating the invariant
- adding a generic helper because two call sites share two lines
- introducing a factory/strategy/plugin before the second real participant exists
- wrapping an existing API only to rename methods or forward unchanged arguments

## Abstraction Judgment

Keep an abstraction when it protects a current boundary:

- external service, filesystem, clock, database, queue, browser, subprocess, or network
- public API, plugin contract, protocol/schema vocabulary, generated client, or serialized format
- security, authorization, transaction, concurrency, lifecycle, observability, or retry/idempotency policy
- two real implementations with meaningful differences now
- a domain concept that makes call sites clearer even if it has one implementation

Remove or inline an abstraction when it is only:

- one interface, one implementation, one caller
- a wrapper that forwards the same arguments
- a factory around simple construction
- a strategy map with one strategy
- a config/options object with unused future fields
- a manager/service/processor name hiding mixed or trivial work

## Structural Erosion Checks

Before adding another branch, flag, or helper, ask:

- Is this function accumulating unrelated product cases?
- Would a table, parser, state machine, or domain object express the variation better?
- Are visible tests encouraging hard-coded paths?
- Does the next feature require touching the same growing function again?
- Can the branch become impossible by validating earlier or changing the data shape?

Do not split a branch-heavy function mechanically. First identify whether the branches are one cohesive decision table, several domain policies, or a missing state model.

## Tests That Support Refactoring

Good cleanup often requires test repair before production changes.

Prefer tests that:

- assert observable behavior, boundary effects, and failure semantics
- vary prompt examples with empty, duplicate, invalid, reordered, and larger inputs
- use real collaborators or small fakes when mocks only restate implementation
- keep exact strings, timestamps, IDs, and call order strict only when they are the contract

Reject tests that:

- hard-code demo fixtures as the only behavior
- assert private helper calls or internal data layout
- snapshot unreadable blobs
- pass after deleting the real behavior
- force every future refactor to preserve generated structure

## Performance Discipline

Efficient code is usually simpler after the right data shape is chosen.

Use:

- maps/indexes instead of repeated scans when matching by key
- streaming or chunking when full materialization is unnecessary and data may be large
- existing framework batching/backpressure before custom queues
- bounded retries only when operations are idempotent and failures are observable

Avoid:

- caches without invalidation or lifetime
- parallelism without limits, cancellation, ordering semantics, or backpressure
- retries around non-idempotent writes
- micro-optimizations in cold paths
- hiding validation errors with defaults to keep benchmarks green

## Final Review

Before handing back a cleanup, verify:

- What behavior stayed the same?
- What behavior intentionally changed?
- Which abstractions were kept, and what boundary do they protect?
- Which abstractions/options/checks were removed, and what made them unnecessary?
- Which tests now prove behavior instead of structure?
- Which commands were run, and what did they prove?
