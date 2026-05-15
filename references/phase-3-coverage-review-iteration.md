# Phase 3: Coverage Review and Iteration Decision

Phase 3 reviews Phase 2 outputs, decides whether source coverage is complete, and adjusts the change plan when coverage evidence shows a real gap.

## Inputs

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/source-doc-manifest.md`
- `openspec/orchestrate/source-anchor-index.md`
- `openspec/orchestrate/change-source-map.md`
- `openspec/orchestrate/capability-source-map.md`
- `openspec/orchestrate/reports/phase-2-agent-report.md`

## Outputs

Write current copies only:

- `openspec/orchestrate/reviews/coverage-review.md`
- `openspec/orchestrate/reviews/change-plan-adjustments.md`
- `openspec/orchestrate/reports/phase-3-agent-report.md`
- `openspec/orchestrate/reports/alignment-final-report.md` only when the decision is `complete`

If the plan changes, update `openspec/orchestrate/change-plan.md` in place and summarize the change in `reviews/change-plan-adjustments.md`. Do not create `iterations/` or preserve old plan copies.

## Review Questions

Evaluate:

1. Does every source anchor have a non-`unclassified` status?
2. Do all required or conditionally read Markdown/text documents report no uncovered semantic line ranges?
3. Are any `no-product-or-system-impact`, `prototype-only-not-production`, `superseded`, or `duplicate` classifications unsupported by source evidence?
4. Does every `current-change` anchor map to a concrete change?
5. Does every durable behavior boundary map to a capability?
6. Are any source anchors mapped only as `reference` when they actually constrain implementation, verification, privacy, security, data, ops, or failure behavior?
7. Are any change scopes too broad because they merge independently verifiable loops?
8. Are any change scopes too narrow because they omit a source-backed failure, verification, data, auth, privacy, deployment, or preserve boundary?
9. Are any capabilities technical modules instead of long-lived behavior boundaries?
10. Are duplicate mappings harmless, or do they indicate ambiguous ownership?
11. Are there unresolved conflicts that block a coherent change plan?

## Adjustment Rules

Adjust `change-plan.md` only when coverage evidence requires it.

Add or split a change only when a source-backed user/system loop has its own entry, fact, projection, failure path, and verification surface.

Add or rename a capability only when source anchors reveal a durable behavior boundary that is not represented by the current capability map.

Move an anchor out of a change only when the source evidence supports `reference-only`, `prototype-only-not-production`, `superseded`, `duplicate`, `explicit-non-goal`, or `later-change`.

Do not create changes for background prose, repeated summaries, discarded options, pure implementation details, or prototype demo mechanics unless they define a production behavior, boundary, or verification obligation.

## Decision Values

`coverage-review.md` must end with exactly one decision:

- `Decision: complete`
- `Decision: iterate`
- `Decision: blocked`

Use `complete` only when there are no unclassified anchors, no uncovered semantic line ranges, no blocking conflicts, and the change/capability plan covers all source-backed product and system obligations or classifies them with a justified non-coverage status.

Use `iterate` when the plan was adjusted or should be adjusted, then run Phase 2 again with a fresh subagent.

Use `blocked` when source documents conflict, source roots are incomplete, or the user must decide a boundary before coverage can close.

## Final Report

When complete, `alignment-final-report.md` must summarize:

- source documents classified
- source anchors indexed
- changes covered
- capabilities covered
- non-coverage classifications
- conflicts resolved or remaining
- confirmation that no required or conditionally read Markdown/text source document has uncovered semantic line ranges
- confirmation that no source anchor remains unclassified

The final agent reply should be short and include the decision, changed files, remaining blockers, and whether another iteration is required.
