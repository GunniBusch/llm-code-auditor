---
name: domain-readability-refactor
description: Use when code is hard to read, vague, generic, comment-heavy, utility-dumped, poorly named, over-fragmented, feature-envious, or does not use the domain language and local style of the surrounding codebase.
---

# Domain Readability Refactor

Use this skill to make code read like a domain expert wrote it. Good readability is not prettier wording over the same shape; it is better ownership, locality, and adaptation to the existing codebase.

## Workflow

1. Read surrounding code, tests, schema names, route names, UI labels, protocol docs, and logs before renaming.
2. Search for existing repo vocabulary and near-miss implementations; adapt them instead of creating parallel names or helpers.
3. Replace job-title names with owned domain concepts.
4. Move behavior near the data/invariant it changes most.
5. Delete narration comments; keep comments for constraints, protocol quirks, performance tradeoffs, or bug history.
6. Merge tiny files and directories when they do not represent a real module boundary.
7. Preserve strategic duplication when abstraction would erase meaning or the cases are likely to diverge.

## Naming Targets

Replace vague terms:
- `Manager`, `Service`, `Processor`, `Handler`, `Provider`, `Factory`, `Engine`
- `data`, `payload`, `item`, `entity`, `object`, `context`, `info`
- `processData`, `handleRequest`, `executeTask`, `performAction`

With names from:
- product vocabulary
- domain schemas and database tables
- protocol objects and external API docs
- user-visible workflows
- business invariants

Do not rename contractual framework/protocol names. Examples: LSP capability names such as `codeActionProvider`, `hoverProvider`, `completionProvider`, and `resolveProvider` are external vocabulary, not generic naming inflation.

When a contractual name is unclear, improve the surrounding local name instead of the contract field. For example, keep `codeActionProvider` but name the enclosing object `serverCapabilities` or `formulaEditCapabilities` if that better describes ownership.

Read `../llm-code-auditor/references/human-code-quality.md` for locality and reviewability principles.
Read `../llm-code-auditor/references/senior-refactor-playbook.md` for adaptive reuse and stopping criteria during deep cleanup.
