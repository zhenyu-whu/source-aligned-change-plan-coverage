# Phase 3: Global Assembly, Coverage Statistics, and Iteration Decision

Phase 3 consumes all independent per-change anchor analyses from Phase 2 and reviews them from a global perspective. It assembles source-document, change, and capability indexes; runs line-span coverage checks; summarizes coverage statistics; identifies source-backed spans that no change covered; and adjusts the plan when coverage evidence shows a real gap or bad slicing.

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

If the plan changes, update `openspec/orchestrate/change-plan.md` in place and summarize the change in `reviews/change-plan-adjustments.md`. Do not create `iterations/` or preserve old plan copies.

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
5. Build `source-anchors/<source-doc-slug>.md` reverse indexes from per-change source and capability anchors, and from source documents that need explicit non-coverage or unclassified rows.
6. Build `source-anchors/index.md` and `source-anchor-index.md`.
7. Build `change-source-map.md` and `capability-source-map.md`.
8. Run deterministic line-span coverage checks.
9. Build global statistics across changes, source documents, capabilities, statuses, gaps, and conflicts.
10. Identify source-backed semantic spans not covered by any change or planned capability increment.
11. Identify changes with weak, missing, overly broad, or overly narrow source/capability support.
12. Decide whether the current change plan is coherent, needs iteration, or is blocked.

The Phase 3 subagent may normalize paths, stable anchor names, line ranges, duplicate source-anchor rows, and table formatting so the combined result is reviewable. It must preserve each per-change subagent's source judgment when building global indexes; plan-level interpretation belongs in `coverage-review.md` and `change-plan-adjustments.md`.

## Per-Document Reverse Indexes

Each per-document file must include:

- source document metadata line
- source classification
- mechanical coverage summary
- full reverse-index table for that source document

Use this exact source metadata format near the top of each per-document file:

```markdown
Source Document: `docs/prototype/pages/editor.md`
```

Each `source-anchors/<source-doc-slug>.md` file must include:

| Anchor | Lines | Source Phrase | Coverage Status | Changes | Capabilities | Roles | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |

If semantic source lines are not present in any per-change output, add reverse-index rows for those spans so mechanical coverage remains reviewable. Mark them `unclassified` unless there is explicit source evidence for a non-coverage status.

## Line-Span Coverage

For Markdown or text source files, Phase 3 must support a mechanical coverage check:

- Every non-empty semantic line in required or conditionally read documents must belong to exactly one source anchor row in the per-document reverse index, unless it is classified as `non-semantic-formatting`.
- Table separator rows, blank lines, generated table-of-contents lines, and purely decorative separators may be grouped with adjacent anchors or classified as `non-semantic-formatting`.
- A heading line belongs to the section anchor it opens.
- A table row with source meaning should normally be its own anchor or part of a small contiguous table-row range.
- Do not use a single broad document-level anchor when the document contains multiple sections, rows, states, routes, decisions, requirements, or verification obligations.
- Record uncovered semantic line ranges, overlapping anchor line ranges, and bad line ranges in `coverage-review.md` and `phase-3-agent-report.md`.

After writing per-document anchor files, run the bundled checker when available:

```sh
node .codex/skills/source-aligned-change-plan-coverage/scripts/check-anchor-coverage.mjs .
```

If the skill lives outside the repository root, run the same script by its absolute path and pass the repository root as the argument. Paste the checker totals into `phase-3-agent-report.md`. A failed checker result is a Phase 3 blocker unless corrected or reclassified with evidence.

## Required Index Tables

`change-capability-anchors/index.md` must include:

| Change | Change Directory | Source Anchor File | Capability Anchor Files | Source Documents Read | Anchors | Capability Gaps | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- |

`source-anchors/index.md` must include:

| Source Document | Anchor File | Classification | Line Span Coverage | Anchors | Unclassified | Unresolved Conflicts | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |

`source-anchor-index.md` must include a compact navigational summary only:

| Source Document | Anchor File | Classification | Anchor Count | Coverage Summary | Notes |
| --- | --- | --- | --- | --- | --- |

Do not duplicate the full per-anchor table in `source-anchor-index.md`.

`source-doc-manifest.md` must include:

| Source Document | Classification | Anchor File | Line Span Coverage | Uncovered Semantic Lines | Reason |
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
3. Do all required or conditionally read Markdown/text documents report no uncovered semantic line ranges, no overlapping anchor line ranges, and no bad line ranges?
4. Did the bundled anchor coverage checker pass, or does the report include an equivalent deterministic check with no failures?
5. Does every source anchor have a non-`unclassified` status, or is each `unclassified` anchor listed as a concrete blocker?
6. Does every planned capability increment in every change have source anchors or an explicit capability gap?
7. Which source documents, sections, anchors, statuses, and capabilities are concentrated in each change?
8. Which source anchors or source sections appear across multiple changes or capability increments, and is that pattern reasonable for the current plan?
9. Are any source-backed spans not covered by any change or planned capability increment and not justified by `reference-only`, `prototype-only-not-production`, `superseded`, `duplicate`, `explicit-non-goal`, `no-product-or-system-impact`, or another explicit non-coverage status?
10. Are any non-coverage classifications unsupported by source evidence?
11. Does every durable behavior boundary map to a capability?
12. Are any planned capability increments missing, overstated, or assigned to the wrong change?
13. Are any change scopes too broad because they merge independently verifiable loops?
14. Are any change scopes too narrow because they omit a source-backed failure, verification, data, auth, privacy, deployment, or preserve boundary?
15. Are any capabilities technical modules instead of long-lived behavior boundaries?
16. Are there unresolved conflicts that block a coherent change plan?

## Required Review Tables

`coverage-review.md` must include a per-change coverage table:

| Change | Anchor Files | Source Documents | Anchors | Capabilities | Gaps | Review Judgment |
| --- | --- | --- | --- | --- | --- | --- |

It must include a per-source-document coverage table:

| Source Document | Anchor Coverage Summary | Changes Referencing It | Uncovered Source-Backed Spans | Non-Coverage Statuses | Review Judgment |
| --- | --- | --- | --- | --- | --- |

It must include a per-capability coverage table:

| Capability | Planned Increments | Source Anchors | Changes | Capability Gaps | Review Judgment |
| --- | --- | --- | --- | --- | --- |

It must include a global statistics table:

| Metric | Value | Evidence | Interpretation |
| --- | --- | --- | --- |

It must include a plan-impact table:

| Finding | Source Anchors | Affected Changes | Plan Impact | Required Adjustment |
| --- | --- | --- | --- | --- |

## Adjustment Rules

Adjust `change-plan.md` only when global coverage evidence requires it.

Add or split a change only when a source-backed user/system loop has its own entry, fact, projection, failure path, and verification surface.

Add or rename a capability only when source anchors reveal a durable behavior boundary that is not represented by the current capability map.

Keep a source-backed span out of all changes only if the non-coverage rationale is source-backed and production-safe.

Attach a source-backed span to an existing change only if that change's scope already owns the same user/system loop in the plan.

Do not create changes for background prose, repeated summaries, discarded options, pure implementation details, or prototype demo mechanics unless they define a production behavior, boundary, or verification obligation.

If `change-plan.md` changes, the next Phase 2 pass must rerun with fresh independent subagents for the current planned changes.

## Decision Values

`coverage-review.md` must end with exactly one decision:

- `Decision: complete`
- `Decision: iterate`
- `Decision: blocked`

Use `complete` only when every planned change has a per-change source anchor file and one nested capability anchor file per planned capability increment, all required Phase 3 assembly outputs exist, every planned capability increment is source-backed or has a justified non-coverage/gap rationale, there are no unclassified anchors, no uncovered semantic line ranges, no overlapping anchor line ranges, no bad line ranges, no failed deterministic checker result, no missing per-document reverse-index files, no blocking conflicts, and the change/capability plan covers all source-backed product and system obligations or classifies them with a justified non-coverage status.

Use `iterate` when the plan was adjusted or should be adjusted, then run Phase 2 again with fresh independent per-change subagents.

Use `blocked` when source documents conflict, source roots are incomplete, or the user must decide a boundary before coverage can close.

## Final Report

When complete, `alignment-final-report.md` must summarize:

- planned changes analyzed
- per-change source anchor files consumed
- per-change capability anchor files consumed
- source documents classified
- source anchors indexed
- changes covered
- capabilities covered
- planned capability increments covered or gap-classified
- global coverage statistics
- source-backed spans not covered by any change, or confirmation that none remain
- non-coverage classifications
- conflicts resolved or remaining
- confirmation that every required or conditionally read source document has a per-document reverse-index file
- confirmation that no required or conditionally read Markdown/text source document has uncovered semantic line ranges, overlapping anchor line ranges, or bad line ranges
- confirmation that the bundled anchor coverage checker or equivalent deterministic check passed
- confirmation that no source anchor remains unclassified

The final agent reply should be short and include the decision, changed files, remaining blockers, and whether another iteration is required.
