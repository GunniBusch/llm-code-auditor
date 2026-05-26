# Human-Quality Code Reference

Use this when a cleanup task asks for code that is readable, efficient, direct, testable, easy to inspect for bugs, and not over-engineered.

## Research Anchors

- Google Engineering Practices: code review should improve code health over time; reviewers should check design, functionality, tests, naming, comments, complexity, and context. https://google.github.io/eng-practices/review/reviewer/looking-for.html
- Google code review standard: prefer improvements that clearly improve maintainability/readability/understandability over perfection-chasing. https://google.github.io/eng-practices/review/reviewer/standard.html
- Martin Fowler: a code smell is a surface indication that often corresponds to a deeper system problem. https://martinfowler.com/bliki/CodeSmell.html
- Refactoring catalog examples: Feature Envy suggests behavior may belong near the data it uses; duplicated code and long methods are refactoring signals, not automatic proof. https://refactoring.guru/smells/feature-envy
- PEP 8: readability, project consistency, and local consistency matter more than mechanically applying a style rule. https://peps.python.org/pep-0008/
- Google Python Style Guide: related classes and top-level functions can live together in one module; Python does not need one class per file. https://google.github.io/styleguide/pyguide.html
- Rust API Guidelines: strong APIs are predictable, interoperable, type-safe, dependable, debuggable, and able to evolve. https://rust-lang.github.io/api-guidelines/checklist.html
- Bugs in LLM Generated Code: recurring LLM bug patterns include prompt-biased code, missing corner cases, wrong input type, hallucinated object, wrong attribute, incomplete generation, and non-prompted behavior. https://arxiv.org/abs/2403.08937
- Investigating The Smells of LLM Generated Code: scenario-based evaluation found LLM outputs can increase implementation and design smells, so cleanup has to measure maintainability, not only test pass rate. https://arxiv.org/abs/2510.03029
- SlopCodeBench: repeated agent extension can increase verbosity and structural erosion even when checkpoint tests pass. Good cleanup must preserve the codebase's ability to absorb the next change. https://arxiv.org/abs/2603.24755
- SpecBench: visible tests can reward benchmark gaming instead of the real specification; good references need hidden/varied behavior and manual quality review. https://arxiv.org/abs/2605.21384

## Research Synthesis

Good code is not "short code" or "abstract code." It is code whose behavior,
ownership, and proof are easy to inspect. The sources above converge on these
rules:

- Design and behavior come before local style. A reference that passes tests but
  makes the next change harder is not good.
- Complexity is contextual. Long, branchy, duplicated, generic, or single-use
  shapes are review leads, not automatic defects.
- Abstraction earns its place by protecting a real boundary, naming a dense
  phase, or giving an invariant one owner. Otherwise it is accidental machinery.
- Consistency with the local project outranks generic taste.
- Tests must fail for real behavior breaks and must not freeze private generated
  structure.
- LLM-specific review must check prompt overfit, missing edge cases, additive
  branch growth, silent fallback, and invented structure.

## Reference Fixture Standard

An `after_good` fixture must be good by human review, not merely by the current
automated gates:

- It must preserve and extend behavior proof with varied edge cases when the bad
  fixture hid an input-shape problem.
- It must lower medium/high static findings, core remodel friction, and lens
  pressure compared with its paired bad fixture.
- It must not become larger, more abstract, or more indirect just to satisfy a
  line-count or branch-count threshold.
- Function-size thresholds should reject new hiding places, not force a clear
  parser, validator, or command table into fragmented helper churn.
- A remaining low scanner lead is acceptable only when the helper, type, or
  boundary names a real phase, invariant, or data model visible in the task.

## What Excellent Human Code Optimizes For

1. Local obviousness: a reader can see the data, invariant, and behavior in one place.
2. Domain language: names come from product concepts, protocols, schemas, UI labels, and user workflows.
3. Small public surface: fewer exported functions, fewer options, fewer states.
4. Boundary discipline: parse, validate, authorize, and sanitize at trust boundaries; internal code receives known-good shapes.
5. Negative space: unused extension points, dead config, generic wrappers, and duplicated guards are deleted.
6. Refactorability: tests pin behavior, not private structure; types make invalid states hard to express.
7. Efficient enough: choose the right algorithm and data shape before adding caches, queues, pools, or concurrency.
8. Reviewability: changes are small enough that another engineer can inspect every meaningful line.
9. Evolutionary fit: the next plausible feature does not have to thread through accidental flags, duplicated branches, and invented layers.

## The Senior Refactor Loop

1. State the behavior that must remain true.
2. Identify the invariant that the current code fails to express.
3. Search for an existing repo concept that should own or influence the invariant.
4. Delete or move code until the invariant has one owner.
5. Rename after moving, because better ownership usually reveals better names.
6. Run tests. If tests are brittle, repair them to assert behavior before continuing.
7. Stop when the next change would be taste, not code health.

## Patterns To Prefer

- Direct function over a class that owns no boundary, state, phase, or invariant.
- Concrete type over interface until there are two real implementations or a true boundary.
- Plain data plus validation at construction over optional fields checked everywhere.
- Existing framework lifecycle over custom orchestration.
- Small table/map for mechanical variation over mirrored methods.
- One cohesive module over many one-class files.
- Domain-specific duplicate code over premature generic abstraction when the cases are likely to diverge.
- Typed results or explicit errors over silent empty fallbacks.
- Existing repo APIs over plausible new dependencies or guessed helper names.

One use is not a defect by itself. Keep a one-use helper, class, or service when
it names a meaningful phase, protects a trust boundary, or makes a dense
operation easier to verify.

## Review Questions

- Can a maintainer predict all side effects from this file?
- What invariant is repeated in prose, checks, tests, and names?
- Is this layer adding mapping, validation, authorization, transactionality, caching, or observability? If not, why does it exist?
- Would a failing test point at the bug, or at a mocked implementation detail?
- Is the strictness protecting a boundary or just making future refactors expensive?
- Is this optimization solving a measured bottleneck or just making simple code harder?
- Will this code be easier or harder to extend after one more real requirement?
- Are the tests strict about behavior while leaving room for better structure?
