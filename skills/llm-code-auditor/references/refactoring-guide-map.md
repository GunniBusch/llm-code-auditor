# Refactoring Guide Map

Use this map when Code Remodel Markup exposes structural pressure and the agent
needs a refactoring family, not a detector verdict. The references are
calibration sources:

- Martin Fowler, Code Smell: https://martinfowler.com/bliki/CodeSmell.html
- Fowler, Refactoring 2nd edition catalog changes: https://martinfowler.com/articles/refactoring-2nd-changes.html
- Refactoring Guru, Code Smells: https://refactoring.guru/refactoring/smells
- Refactoring Guru, Composing Methods: https://refactoring.guru/refactoring/techniques/composing-methods

Fowler's important constraint is that a smell is an indicator, not proof. Use
the guide names to ask better questions; do not apply a catalog move blindly.

## Remodel Pressure To Refactoring Families

| Remodel pressure | Guide analogy | First moves to consider | Guardrail |
| --- | --- | --- | --- |
| `branch-hub` | Long Method, Switch Statements, Divergent Change | Extract Function, Decompose Conditional, Replace Conditional with Polymorphism, Replace Function with Command, Split Phase, Substitute Algorithm | Name the real domain distinction before splitting. |
| `unowned-forwarder` | Middle Man, Speculative Generality | Inline Function/Method, Remove Middle Man, Inline Class, Move Statements to Callers | Keep wrappers that protect protocols, lifecycle, policy, or readability. |
| `generic-boundary` | Lazy Class, Speculative Generality, Primitive Obsession | Rename from ownership, Inline Class, Collapse Hierarchy, Replace Primitive with Object | Do not rename external framework, schema, or protocol vocabulary. |
| `spread-concept` | Feature Envy, Divergent Change, Data Clumps | Move Function, Extract Class, Introduce Parameter Object, Combine Functions into Class, Split Phase | Repeated words can be healthy locality; move only when ownership is unclear. |
| `silent-boundary` | Error Code, hidden failure policy | Replace Error Code with Exception, Replace Exception with Precheck, Introduce Special Case, Separate Query from Modifier | Recover locally only when fallback is a documented contract. |
| `module-shape-friction` | Large Class, Lazy Class, Shotgun Surgery | Extract Module/Class, Inline Module/Class, Move Function, Remove Dead Code | Respect public exports, migrations, generated code, and framework layout. |

## How To Use The Map

1. Pick the remodel pressure that best explains the structure.
2. Compare it with the guide analogy, then write why the analogy fits or fails.
3. Choose the smallest behavior-preserving move family.
4. State the guardrail before editing.
5. Prove behavior with tests, types, or a precise manual trace.

Good remodel output should name both sides: the likely move and the reason not
to use it. That keeps the agent from turning every long function into a pile of
helpers or every single-use class into inline code.
