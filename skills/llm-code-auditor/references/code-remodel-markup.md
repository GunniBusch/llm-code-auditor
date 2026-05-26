# Code Remodel Markup

Code Remodel Markup is a compact post-code representation for LLM refactoring.
It is not a source language, not a compiler IR, and not a static analyzer
verdict. Its job is to redraw already-written code so structural quality becomes
easier to reason about.

The most important tool is the model the agent writes after reading the code.
Use `remodel-first-framework.md` for the full workflow. The bundled script is a
seed and sanity check:

```bash
python3 scripts/code_remodel.py <path>
python3 scripts/code_remodel.py --json <path>
```

Do not treat script output as truth. Rewrite or extend the markup manually when
the code's real shape is clearer than the heuristic model. Explicit human
feedback is also evidence: if a maintainer says an abstraction is useful,
misplaced, redundant, too verbose, or worse than the original, model that
feedback as a source and reconcile it against the code. Static findings are
secondary leads, not authority.

Use `refactoring-guide-map.md` as calibration when choosing moves. The remodel
language borrows guide analogies from Fowler and Refactoring Guru, but keeps the
local proof burden: a smell name is a lead, not evidence by itself.

## Reading The Model

Version 4 uses a strict CMML-style fact graph. The structure should come from
tags, ids, enums, metrics, and typed edges, not from long explanatory prose.

Core tags:

- `@remodel`: dialect, version, and strictness.
- `@schema`: the controlled pressure, move, and proof vocabularies.
- `@guide`: external refactoring references and how to use them.
- `@lens` / `@lens_pressure` / `@protocol`: high-level quality pressure and the
  inspection frame.
- `@concept`: repeated domain words and possible ownership candidates.
- `@file`: each scanned file.
- `@sym`: a class, function, method, or generic declaration with role,
  ownership, location, metrics, calls, concepts, pressure, guide moves, and
  guardrail.
- `@pressure`: remodel-visible structure that deserves inspection before
  rewriting.
- `@move_rule`: guide-backed move families suggested by pressure.
- `@pass`: required modeling passes.
- `@after`: after-rewrite pressure diff and proof.

Treat the markup as a map, not a command list. A symbol can have pressure and
still be valid when it represents a real boundary.

## Strict CMML Rules

Each non-empty line is a fact:

```text
@tag key=value key=value
```

Values are one of:

- quoted string: `name="load_config"`
- atom: `role=branch-hub`
- atom list: `pressure=[branch-hub,silent-boundary]`
- quoted list: `calls=["parse","dispatch"]`
- metric map: `metrics={span:35,branches:15,statements:33}`

Free text is allowed only inside quoted values. Do not write paragraphs between
facts. If a judgment matters, encode it as `pressure`, `owner`, `move`, `guard`,
or `proof`.

## Manual Remodel Template

When the structure is subtle, write a compact manual model before editing:

```text
@remodel version=4 dialect=cmml strict=true
@meta purpose="manual structural model before refactor" authority="source+tests first; human feedback outranks static leads"
@schema pressure=[unowned-forwarder,branch-hub,silent-boundary,generic-boundary,repeated-operation,spread-concept,module-friction] move=[InlineFunction,MoveFunction,SplitPhase,DecomposeConditional,IntroduceParameterObject,TableDispatch,StateModel,KeepBoundary] proof=[tests,types,trace]

@context id=CTX behavior="observable behavior that must stay true" invariants=["rules with one owner"] constraints=["public API","schema","protocol","performance","compatibility"] proof=[tests,types,trace]
@feedback id=FB1 source=maintainer accept=["valuable constraints or shapes"] reject=["worse, redundant, or misplaced examples"] reconcile="what source evidence supports, contradicts, or leaves open"

@file id=F001 path="path/to/file.py" owns="current responsibility" should_own="intended owner after cleanup" misplaced=["responsibilities that belong elsewhere"] additive_path=["where requirements became branches or wrappers"]
@sym id=F001.S001 file=F001 kind=function name="name" loc=10..34 role=branch-hub owns=mixed-decision-set metrics={span:25,branches:9,statements:31} concepts=["invoice","state"] calls=["parse","dispatch"] pressure=[branch-hub] keep_if=["names real phase","protects protocol"] reconnect="table, parser, state model, schema, caller, or module that should own it"

@flow id=FL001 name="user-visible operation" steps=[boundary,parse,decide,effect,response] overgrown_step=decide missing_owner="module, data model, or state that should absorb variation"
@decision id=D001 target=F001.S001 varies_by=[type,state,role,source,protocol-case] current=if-chain better=[TableDispatch,StateModel,separate-domain-paths]
@pressure kind=branch-hub target=F001.S001 evidence={branches:9} owner="intended owner" move=[SplitPhase,TableDispatch] guard="first name the domain distinction"
@pressure kind=unowned-forwarder target=F001.S002 evidence={calls:1} owner="caller or callee" move=[InlineFunction,MoveFunction] guard="keep if it owns a phase, boundary, invariant, or test seam"
@keep target=F001.S003 reason=[protocol,lifecycle,security,transaction,test-seam,named-phase,domain-vocabulary]
@move_rule pressure=branch-hub moves=[SplitPhase,DecomposeConditional,TableDispatch] guard="do not split until variation has a real domain name" proof=[tests,types,trace]
@pass n=1 source="code+tests" output=ownership-map
@pass n=2 source="human-feedback" output=constraint-delta
@pass n=3 source="static-leads" output=weak-pressure-check
@pass n=4 source="after-rewrite" output=pressure-diff proof=[tests,types,trace]
@after behavior=same owners=["one owner per invariant"] kept=[F001.S003] removed=[branch-hub,unowned-forwarder] remaining=["accepted tradeoff"] proof=[tests,types,trace]
```

Focus the remodel on structure, not perfect logic. It should help answer "where
should this responsibility live?" and "what must be reconnected before adding
more code?"

## What The Syntax Should Reveal

The syntax should be brief enough for the agent to keep in working memory while
still preserving the important information. Prefer single-line entries with
named attributes over prose paragraphs. The structural problem should be visible
without requiring a separate detector verdict:

- Many `@sym` entries with `owns=delegation-only` usually means indirection
  is standing in for ownership.
- One `@decision` or `@sym role=branch-hub` with many branches means the
  next change will probably add another branch unless variation gets a better
  shape.
- A `@file` with several unrelated `misplaced` entries means the file is a
  container, not an owner.
- `@keep` should name the abstractions to preserve so cleanup does not become
  blind inlining.
- `@move_rule` must name a guardrail. A move without a reason it might be
  wrong is too eager.
- `@after` should be shorter and clearer than the before model. If it
  needs more caveats, the code may have become worse.
- `@feedback` and `@pass` should show when human critique changed the
  model and when static findings were only used as a check.

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
- `repeated-operation`: the same operation name appears in several places. Check
  whether this is duplication, layering, or a deliberate protocol pattern.
- `spread-concept`: the same domain word is spread across several symbols.
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

1. Write or adjust a manual `@context`/`@file`/`@sym`/`@flow` remodel before
   editing when structure is the problem.
2. Read `@lens` to choose the first inspection frame.
3. Read `@guide` and `@move_rule` to choose a move family, then
   state the guardrail.
4. Read `@pressure` to find structural pressure without jumping to exact edits.
5. For each relevant `@sym`, ask what it owns today. If the answer is only
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
