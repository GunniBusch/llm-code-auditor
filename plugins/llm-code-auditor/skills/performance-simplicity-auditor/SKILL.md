---
name: performance-simplicity-auditor
description: Use when code is inefficient, algorithmically suspicious, micro-optimized, cache-heavy, retry-heavy, parallelized without limits, memory-wasteful, or generated with performance features that may be unnecessary or wrong.
---

# Performance Simplicity Auditor

Use this skill to improve efficiency without making the code harder to reason about.

## Workflow

1. Estimate input sizes and hot paths before optimizing.
2. Look for an existing repo data shape, index, query, or framework primitive before adding custom machinery.
3. Prefer algorithm/data-structure improvements over caches, pools, retries, or concurrency.
4. Remove memoization/caching without invalidation, bounded lifetime, or evidence of repeated expensive work.
5. Remove parallelism without concurrency limits, ordering semantics, cancellation, and backpressure.
6. Replace repeated scans, nested loops, and repeated parsing with simple maps, indexes, precomputation, or streaming only when the data size justifies it.
7. Keep code direct when the bottleneck is not proven or plausible from the workload.
8. Verify with tests plus benchmark/profile/manual complexity reasoning as appropriate.

## Red Flags

- cache added before measuring or estimating repeated work
- retry loop without idempotency
- async/concurrent code for tiny local operations
- full materialization of large data where streaming would be simpler
- O(n^2) matching code where a map would be clearer
- optimization that hides boundary errors or changes failure semantics
- branch-heavy functions that keep absorbing new cases instead of changing the data model

High-quality performance code is usually simpler after the right data shape is chosen.
