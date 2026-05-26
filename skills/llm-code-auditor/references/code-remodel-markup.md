# Code Remodel Markup

Code Remodel Markup is a post-code representation for LLM refactoring. It is
not a source language, not a compiler IR, and not a static analyzer verdict. Its
job is to redraw already-written code so structural quality becomes easier to
reason about.

The most important tool is the model the agent writes after reading the code.
Use `remodel-first-framework.md` for the full workflow. The bundled script is a
seed and sanity check:

```bash
python3 scripts/code_remodel.py <path>
python3 scripts/code_remodel.py --json <path>
```

Do not treat script output as truth. Rewrite or extend the markup manually when
the code's real shape is clearer than the heuristic model. The act of writing
the model is useful because it makes placement, ownership, additive branches,
redundant methods, and squeezed files visible from another view.

Use `refactoring-guide-map.md` as calibration when choosing moves. The remodel
language borrows guide analogies from Fowler and Refactoring Guru, but keeps the
local proof burden: a smell name is a lead, not evidence by itself.

## Reading The Model

The generated output has these sections:

- `@refactor_guide`: external refactoring references and how to use them.
- `@lens`: the high-level pressure model and agent protocol.
- `@concept_map`: repeated domain words and possible ownership candidates.
- `@module`: each scanned file and its structural symbols.
- `@symbol`: a class, function, method, or generic declaration with its role,
  owned responsibility, calls, concepts, branches, pressure signals, and guide
  hints.
- `@friction`: remodel-visible structure that deserves inspection before
  rewriting.
- `@refactor_moves`: guide-backed move families suggested by the pressure.

Treat the markup as a map, not a command list. A symbol can have friction and
still be valid when it represents a real boundary.

## Manual Remodel Template

When the structure is subtle, write a compact manual model before editing:

```text
@remodel version=2
  purpose="manual structural model before refactor"

@refactor_guide
  source: "Fowler Code Smell | Refactoring Guru smells | local framework docs"
  principle: "smells are leads; prove the deeper problem locally"

@context
  behavior: "observable behavior that must stay true"
  invariants: "rules that should have one owner"
  constraints: "public API, schema, protocol, perf, compatibility"

@module "path/to/file.py"
  owns: "what this file is responsible for today"
  should-own: "what it should be responsible for after cleanup"
  misplaced: "responsibilities that belong elsewhere"
  additive-path: "where requirements have been added as branches/wrappers"

  @symbol function "name" line=10
    owns: "current responsibility"
    pressure: "branch accretion | unowned forwarding | silent fallback | mixed policy"
    keep-boundary-if: "why this helper/class would still earn its place"
    reconnect: "caller, callee, parser, state model, table, schema, or module that should own it"
    guide: "Long Method -> Extract Function/Split Phase, but only if phases are real"

@flow "user-visible operation"
  steps: "boundary -> parse -> decide -> side effect -> response"
  overgrown-step: "where new cases are accumulating"
  missing-owner: "module/data/state that should absorb the variation"

@decision "branch hub name"
  varies-by: "type | state | role | source | protocol case"
  current-shape: "if/elif chain | nested guards | flags | duplicated switch"
  better-shape: "table | parser | state object | polymorphism | separate domain paths"

@rewrite_pressure
  squeezed-file: "too many unrelated responsibilities in one file"
  redundant-one-time-methods: "methods that only restate an existing call"
  wrong-placement: "logic living away from the data/invariant it owns"
  useful-abstractions: "boundaries to preserve because they clarify phases or protect contracts"

@refactor_moves
  candidate: "Extract Function | Inline Function | Move Function | Split Phase | Introduce Parameter Object"
  guardrail: "why this move might be wrong here"
  proof: "test/type/manual trace required before edit"

@after_remodel
  behavior: "same observable contract or intentionally changed contract"
  owners: "one owner per invariant after the rewrite"
  preserved-boundaries: "useful abstraction kept because it protects a real boundary"
  removed-pressure: "branch-hub | unowned-forwarder | silent-boundary | generic-boundary"
  remaining-pressure: "accepted tradeoff and why it is not worth more change now"
  proof: "tests/types/manual trace"
```

Focus the remodel on structure, not perfect logic. It should help answer "where
should this responsibility live?" and "what must be reconnected before adding
more code?"

## What The Syntax Should Reveal

The syntax should make the structural problem visible without requiring a
separate detector verdict:

- Many `@symbol` entries with `owns="delegation-only"` usually means indirection
  is standing in for ownership.
- One `@decision` or `@symbol role="branch-hub"` with many branches means the
  next change will probably add another branch unless variation gets a better
  shape.
- A `@module` with several unrelated `misplaced` entries means the file is a
  container, not an owner.
- A `@rewrite_pressure useful-abstractions` entry should name the abstractions to
  keep so cleanup does not become blind inlining.
- `@refactor_moves` must name a guardrail. A move without a reason it might be
  wrong is too eager.
- `@after_remodel` should be shorter and clearer than the before model. If it
  needs more caveats, the code may have become worse.

When using public code or framework docs for calibration, copy only the
structural lesson: phase boundaries, dispatch shape, ownership placement,
failure contracts, or module layout. Do not copy source snippets, domain names,
or identifiers into benchmark fixtures.

## Friction Vocabulary

- `unowned-forwarder` / `empty-boundary`: a symbol mostly delegates. Inline or
  move it only when it owns no invariant, phase name, mapping, failure policy,
  protocol, dependency, lifecycle, authorization, or test seam.
- `generic-boundary`: the local name says architecture job title more than
  domain concept. Rename or move only after checking whether the word is
  framework or protocol vocabulary.
- `branch-hub`: one place absorbs many distinctions. Look for a table, parser,
  state model, or a few real domain paths.
- `silent-boundary`: failure behavior is hidden by broad fallback. Make the
  contract explicit or let unexpected failure surface.
- `repeated-name`: the same operation name appears in several places. Check
  whether this is duplication, layering, or a deliberate protocol pattern.
- `repeated-concept`: the same domain word is spread across several symbols.
  This can reveal an owned concept, but it can also be healthy locality.
- `module-friction`: file or directory shape points to utility dumping,
  mechanical symmetry, or fragmentation.

## Guide-Backed Move Vocabulary

- `Extract Function` when a coherent phase needs a name and can be tested or
  understood independently.
- `Inline Function/Method` when the body is clearer than the name and no
  boundary is protected.
- `Move Function` when behavior cares more about another module's data or
  invariant than its current home.
- `Split Phase` when one operation mixes parsing, decision, side effects, and
  rendering.
- `Replace Function with Command` / method object when local variables are too
  intertwined for simple extraction and the algorithm has real state.
- `Decompose Conditional` when a decision has independent parts that can be
  named.
- `Replace Conditional with Polymorphism` only when the variation is a stable
  domain type, not a one-off branch.
- `Introduce Parameter Object` when repeated parameter/data clusters represent
  a real concept.

## Refactor Use

1. Write or adjust a manual `@context`/`@module`/`@symbol`/`@flow` remodel before
   editing when structure is the problem.
2. Read `@lens` to choose the first inspection frame.
3. Read `@refactor_guide` and `@refactor_moves` to choose a move family, then
   state the guardrail.
4. Read `@friction` to find structural pressure without jumping to exact edits.
5. For each relevant `@symbol`, ask what it owns today. If the answer is only
   delegation, naming, or future flexibility, collapse or move it.
6. Preserve boundaries that encode external contracts, security, lifecycle,
   persistence, concurrency, transactionality, real substitution, a named phase,
   or domain vocabulary that makes the caller clearer.
7. Rewrite code only after behavior proof is clear.

The remodel should make bad placement and redundant structure visible by the
shape of the representation itself. If it only repeats scanner findings, improve
the model.

Single use is not evidence by itself. A one-use helper, service, or class can be
the right code when it names a phase, isolates a trust boundary, makes a dense
algorithm readable, or gives an invariant one owner. The problem is unowned
indirection, wrong placement, and additive structure that keeps growing instead
of being reconnected.
