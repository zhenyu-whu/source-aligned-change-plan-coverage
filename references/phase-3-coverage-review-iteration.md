# Phase 3: Source Document Coverage and Overlap Review

Phase 3 consumes all independent per-change anchor analyses from Phase 2 and reviews them by source document. Phase 2 subagents are intentionally independent, so anchor names and line ranges for the same source document may differ across changes. Phase 3 should not treat those naming differences as a problem. Its primary task is to answer, for each source document: after unioning all Phase 2 anchor line ranges for this document, does any meaningful source content remain uncovered by every change and capability?

The secondary task is to list cross-change or cross-capability anchor line-range overlaps for each source document and explain why the overlap exists. This overlap review is for human audit and plan-boundary judgment; it is not the primary coverage gate.

Phase 3 must not run bundled coverage scripts or recreate a deleted checker. It may use line ranges from Phase 2 outputs as the coverage mechanism, but uncovered ranges must be reviewed semantically before they are treated as plan gaps.

## Inputs

- `openspec/orchestrate/change-plan.md`
- User-specified source document roots or exact source paths.
- `openspec/orchestrate/change-capability-anchors/<change-slug>/<change-slug>.md` per-change source anchor files
- `openspec/orchestrate/change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` per-change/per-capability anchor files
- `openspec/orchestrate/reports/phase-2-agent-report.md`

## Outputs

Write current copies only:

- `openspec/orchestrate/source-doc-manifest.md`
- `openspec/orchestrate/change-capability-anchors/index.md`
- `openspec/orchestrate/source-anchor-index.md`
- `openspec/orchestrate/source-anchors/index.md`
- `openspec/orchestrate/source-anchors/<source-doc-slug>.md` per required or conditionally read source document
- `openspec/orchestrate/change-source-map.md`
- `openspec/orchestrate/capability-source-map.md`
- `openspec/orchestrate/reviews/coverage-review.md`
- `openspec/orchestrate/reviews/change-plan-adjustments.md`
- `openspec/orchestrate/reports/phase-3-agent-report.md`
- `openspec/orchestrate/reports/alignment-final-report.md` only when the decision is `complete`

Phase 3 proposes adjustments in `reviews/change-plan-adjustments.md`; it does not update `change-plan.md` or Phase 2 per-change/capability anchor files. Targeted updates belong to Phase 4.

## Source Discovery

Enumerate every source document under the user-specified roots. Classify each as:

- `required`
- `conditionally relevant and read`
- `reference-only`
- `intentionally not read`
- `non-source artifact`

`intentionally not read` requires a concrete no-relevance reason. Convenience, large file size, or expected irrelevance is not enough.

Write the result to `source-doc-manifest.md`.

## Assembly Workflow

Evaluate Phase 2 outputs in this order:

1. Confirm every planned change has exactly one per-change source anchor file and one nested capability anchor file per planned capability increment.
2. Confirm Phase 2 used a fresh independent subagent for each planned change.
3. Build `change-capability-anchors/index.md` from the per-change directories.
4. Read nested capability anchor files and group them by `capability-slug` across all changes.
5. Extract every Phase 2 anchor row with its source document, original anchor name, line range, source phrase, coverage status, change, capabilities, roles, and rationale. Preserve the original anchor names and ranges from each change.
6. For each source document, union all Phase 2 anchor line ranges from per-change and per-capability files. The union is the coverage basis for that source document.
7. Compare the unioned coverage ranges with the source document. Identify source ranges outside every Phase 2 anchor range, then review those ranges semantically:
   - ignore blank lines, table separators, decorative separators, generated table-of-contents lines, and pure formatting
   - ignore background prose, repeated summaries, discarded options, and purely explanatory text unless it defines a production behavior, boundary, data fact, verification obligation, deployment requirement, auth/privacy rule, failure path, or preserve constraint
   - record each remaining meaningful uncovered range as a coverage gap
8. Build `source-anchors/<source-doc-slug>.md` reverse indexes from the original Phase 2 anchor rows plus any meaningful uncovered source ranges. Do not require Phase 2 anchors from different changes to share the same stable anchor name.
9. For each source document, detect cross-change and cross-capability overlaps by intersecting Phase 2 anchor line ranges. List overlaps when ranges intersect or one range contains another; preserve all participating original anchor names.
10. Explain each overlap as one of: valid shared source context, dependency/preserve evidence, same user/system loop split across changes, duplicated scope, conflicting ownership, broad anchor range, or unclear.
11. Build `source-anchors/index.md` and `source-anchor-index.md`.
12. Build `change-source-map.md` and `capability-source-map.md`.
13. Build global statistics across source documents, changes, capabilities, covered ranges, meaningful uncovered ranges, overlap findings, gaps, and conflicts.
14. Decide whether the current change plan is coherent, needs targeted Phase 4 adjustment, or is blocked.

The Phase 3 subagent may normalize paths, line range formatting, and table formatting so the combined result is reviewable. It must not merge away original Phase 2 anchor names or treat anchor-name mismatch as a coverage issue. Plan-level interpretation belongs in `coverage-review.md` and `change-plan-adjustments.md`.

## Per-Document Reverse Indexes

Each per-document file must include:

- source document metadata line
- source classification
- Phase 2 anchor line-range coverage summary
- original Phase 2 anchor rows grouped by line range
- meaningful uncovered source ranges, if any
- cross-change/capability overlap table

Use this exact source metadata format near the top of each per-document file:

```markdown
Source Document: `docs/prototype/pages/editor.md`
```

Each `source-anchors/<source-doc-slug>.md` file must include a coverage table:

| Range Type | Lines | Source Phrase | Source Anchors | Changes | Capabilities | Coverage Status | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |

`Range Type` should be one of:

- `phase-2-anchor-range`
- `merged-covered-range`
- `meaningful-uncovered-range`
- `non-semantic-uncovered-range`

Use `meaningful-uncovered-range` only after reading the source text and determining that the uncovered range contains product, system, data, auth/privacy, deployment, verification, failure-path, or preserve significance.

Each per-document file must also include an overlap table:

| Overlap Lines | Participating Anchors | Changes | Capabilities | Overlap Reason | Human Review Notes |
| --- | --- | --- | --- | --- | --- |

Overlap rows are expected when independent changes cite the same source context. Do not treat overlap as a blocker unless the reason is duplicated scope, conflicting ownership, or unclear after review.

## Required Index Tables

`change-capability-anchors/index.md` must include:

| Change | Change Directory | Source Anchor File | Capability Anchor Files | Source Documents Read | Anchors | Capability Gaps | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- |

`source-anchors/index.md` must include:

| Source Document | Anchor File | Classification | Phase 2 Range Coverage Summary | Meaningful Uncovered Ranges | Cross-Change Overlaps | Unresolved Conflicts | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |

`source-anchor-index.md` must include a compact navigational summary only:

| Source Document | Anchor File | Classification | Phase 2 Anchor Ranges | Meaningful Uncovered Ranges | Overlap Summary | Notes |
| --- | --- | --- | --- | --- | --- | --- |

Do not duplicate the full per-document coverage or overlap tables in `source-anchor-index.md`.

`source-doc-manifest.md` must include:

| Source Document | Classification | Anchor File | Phase 2 Range Coverage Summary | Meaningful Uncovered Ranges | Reason |
| --- | --- | --- | --- | --- | --- |

`change-source-map.md` must include:

| Change | Source Anchors | Capabilities | Roles | Propose Input Notes | Gaps or Conflicts |
| --- | --- | --- | --- | --- | --- |

`capability-source-map.md` must include:

| Capability | Planned Increments | Source Anchors | Changes | Boundary Notes | Gaps or Adjustments |
| --- | --- | --- | --- | --- | --- |

## Review Questions

Evaluate:

1. Does every planned change have one independent per-change source anchor file and one nested capability anchor file per planned capability increment?
2. Does every required or conditionally read source document have exactly one per-document reverse-index file linked from `source-anchors/index.md`?
3. For each source document, what source ranges are covered by the union of all Phase 2 anchor line ranges?
4. Which uncovered ranges are non-semantic or safe to ignore, and which are meaningful source obligations?
5. Are any meaningful uncovered ranges production obligations rather than `reference-only`, `prototype-only-not-production`, `superseded`, `duplicate`, `explicit-non-goal`, `no-product-or-system-impact`, or another justified non-coverage status?
6. Which Phase 2 anchors from different changes or capabilities overlap by line range in each source document?
7. Are overlaps valid shared context, dependency/preserve evidence, duplicated scope, conflicting ownership, broad anchor ranges, or unclear?
8. Does every source anchor have a non-`unclassified` status, or is each `unclassified` anchor listed as a concrete blocker?
9. Does every planned capability increment in every change have source anchors or an explicit capability gap?
10. Does every durable behavior boundary map to a capability?
11. Are any planned capability increments missing, overstated, or assigned to the wrong change?
12. Are any change scopes too broad because they merge independently verifiable loops?
13. Are any change scopes too narrow because they omit a source-backed failure, verification, data, auth, privacy, deployment, or preserve boundary?
14. Are any capabilities technical modules instead of long-lived behavior boundaries?
15. Are there unresolved conflicts that block a coherent change plan?

## Required Review Tables

`coverage-review.md` must include a per-change coverage table:

| Change | Anchor Files | Source Documents | Anchors | Capabilities | Gaps | Review Judgment |
| --- | --- | --- | --- | --- | --- | --- |

It must include a per-source-document coverage table:

| Source Document | Phase 2 Range Coverage Summary | Changes Referencing It | Meaningful Uncovered Ranges | Cross-Change Overlaps | Non-Coverage Statuses | Review Judgment |
| --- | --- | --- | --- | --- | --- | --- |

It must include a source-overlap review table:

| Source Document | Overlap Lines | Participating Anchors | Changes | Overlap Reason | Review Judgment |
| --- | --- | --- | --- | --- | --- |

It must include a per-capability coverage table:

| Capability | Planned Increments | Source Anchors | Changes | Capability Gaps | Review Judgment |
| --- | --- | --- | --- | --- | --- |

It must include a global statistics table:

| Metric | Value | Evidence | Interpretation |
| --- | --- | --- | --- |

It must include a plan-impact table:

| Finding | Source Ranges or Anchors | Affected Changes | Plan Impact | Required Phase 4 Adjustment |
| --- | --- | --- | --- | --- |

## Adjustment Recommendation Rules

Phase 3 recommends plan changes only when global source-document coverage evidence requires it. It writes recommendations to `reviews/change-plan-adjustments.md` and returns `Decision: adjust`. Phase 3 must not directly edit `change-plan.md` or Phase 2 per-change/capability anchor files.

Recommend adding or splitting a change only when a meaningful uncovered source range or problematic overlap reveals a source-backed user/system loop with its own entry, fact, projection, failure path, and verification surface.

Recommend adding or renaming a capability only when uncovered ranges or overlap analysis reveal a durable behavior boundary that is not represented by the current capability map.

Recommend keeping a source range out of all changes only if the non-coverage rationale is source-backed and production-safe.

Recommend attaching a source range to an existing change only if that change's scope already owns the same user/system loop in the plan.

Do not recommend changes for background prose, repeated summaries, discarded options, pure implementation details, or prototype demo mechanics unless they define a production behavior, boundary, or verification obligation.

If a gap requires broad reanalysis rather than targeted use of Phase 3 source-range findings, return `Decision: blocked` and state that a full Phase 2 rerun would be required only after user confirmation.

## Decision Values

`coverage-review.md` must end with exactly one decision:

- `Decision: complete`
- `Decision: adjust`
- `Decision: blocked`

Use `complete` only when every planned change has a per-change source anchor file and one nested capability anchor file per planned capability increment, all required Phase 3 assembly outputs exist, every planned capability increment is source-backed or has a justified non-coverage/gap rationale, there are no unclassified anchors, no missing per-document reverse-index files, no blocking conflicts, every source document's meaningful content is covered by at least one Phase 2 anchor line range or classified with justified non-coverage, and cross-change overlaps are explained as valid sharing or explicitly non-blocking.

Use `adjust` when meaningful source content is not covered by any Phase 2 anchor range, overlap shows duplicated or distorted scope, capability boundaries need targeted edits, or current Phase 2 artifacts need focused updates. Phase 4 must run next.

Use `blocked` when source documents conflict, source roots are incomplete, the user must decide a boundary before coverage can close, or targeted Phase 4 adjustment is insufficient without a broad Phase 2 rerun.

## Final Report

When complete, `alignment-final-report.md` must summarize:

- planned changes analyzed
- per-change source anchor files consumed
- per-change capability anchor files consumed
- source documents classified
- Phase 2 anchor line ranges indexed by source document
- source documents covered
- meaningful uncovered source ranges, or confirmation that none remain
- cross-change and cross-capability overlap findings
- changes covered
- capabilities covered
- planned capability increments covered or gap-classified
- non-coverage classifications
- conflicts resolved or remaining
- confirmation that every required or conditionally read source document has a per-document reverse-index file
- confirmation that every source document's meaningful content is covered by Phase 2 anchor ranges or justified
- confirmation that no bundled coverage script was used as a gate
- confirmation that no source anchor remains unclassified

The final agent reply should be short and include the decision, changed files, meaningful uncovered ranges, overlap findings, remaining blockers, and whether Phase 4 is required.
