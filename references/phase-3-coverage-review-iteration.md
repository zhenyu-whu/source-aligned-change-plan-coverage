# Phase 3: Source Document Coverage and Overlap Review

Phase 3 consumes the independent per-change anchor analyses from Phase 2 and audits them by source document. Phase 2 subagents are intentionally independent across changes, so anchor names and line ranges for the same source document may differ across different changes. Phase 3 should not treat cross-change naming differences as a problem. Within each change, however, the per-change file is canonical and nested capability files must be derived views of that canonical table.

Phase 3 is not a second source-extraction pass and must not create an alternate source-anchor corpus for later `openspec-propose` work. Phase 2 per-change anchor files are the canonical propose input. Phase 3's job is to answer: after unioning all canonical Phase 2 change-anchor line ranges for each source document, does any meaningful source content remain uncovered by every change, and do any overlaps reveal duplicated ownership, conflicting boundaries, or broad/imprecise anchors?

Phase 3 may use `scripts/phase3_line_range_audit.py` as a deterministic mechanical helper to parse line ranges, merge ranges, list candidate uncovered intervals, list overlap clusters, and flag malformed anchor rows. This helper is not a semantic judge and its output is not a quality gate. Phase 3 must not run legacy/deleted coverage checkers or use raw line counts as the decision basis.

## Inputs

- `openspec/orchestrate/change-plan.md`
- User-specified source document roots or exact source paths, for manifest enumeration and targeted semantic reads only.
- `openspec/orchestrate/change-capability-anchors/<change-slug>/<change-slug>.md` canonical per-change source anchor files
- `openspec/orchestrate/change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` derived per-change/per-capability anchor files
- `openspec/orchestrate/reports/phase-2-agent-report.md`
- Optional mechanical helper: `.codex/skills/source-aligned-change-plan-coverage/scripts/phase3_line_range_audit.py`

## Outputs

Write current copies only:

- `openspec/orchestrate/source-doc-manifest.md`
- `openspec/orchestrate/change-capability-anchors/index.md`
- `openspec/orchestrate/reviews/coverage-review.md`
- `openspec/orchestrate/reviews/change-plan-adjustments.md` only when the decision is `adjust` or `blocked`
- `openspec/orchestrate/reports/phase-3-agent-report.md`
- `openspec/orchestrate/reports/alignment-final-report.md` only when the decision is `complete`

Do not create default `source-anchors/`, `source-anchor-index.md`, `change-source-map.md`, or `capability-source-map.md` files. Those duplicate Phase 2 anchors and make human review harder. If the user explicitly requests an auxiliary export, write it outside the default workflow and state that it is not a canonical propose input.

Phase 3 proposes adjustments in `reviews/change-plan-adjustments.md`; it does not update `change-plan.md` or Phase 2 per-change/capability anchor files. Targeted updates belong to Phase 4.

## Source Discovery and Reading Boundary

Enumerate every candidate source document under the user-specified roots and write the result to `source-doc-manifest.md`. Enumeration means listing paths and classifications; it does not require reading every file body.

Classify each document as:

- `covered-by-phase-2`
- `candidate-uncovered`
- `reference-only`
- `intentionally-not-read`
- `non-source-artifact`

Use Phase 2 canonical anchor rows, Phase 2 source-doc traces, Phase 1 source hints, file path/name, and source-root scope to classify documents first. Read source file contents only when one of these is true:

- a candidate uncovered line range must be semantically reviewed
- a document has no Phase 2 anchor ranges and may contain meaningful product/system obligations
- an overlap is unclear without local context
- path/name/Phase 2 traces are insufficient to justify a non-source or reference-only classification

When reading is needed, read the smallest useful range: the candidate uncovered range plus nearby headings or local context. Do not reread all source documents end-to-end as a default Phase 3 step. If broad reading is required to make a safe decision, return `Decision: blocked` and explain why Phase 2 or the input source set is insufficient.

## Audit Workflow

Evaluate Phase 2 outputs in this order:

1. Confirm every planned change has exactly one per-change source anchor file and one nested capability anchor file per planned capability increment.
2. Confirm Phase 2 used a fresh independent subagent for each planned change.
3. Confirm each nested capability anchor file is a derived view of its change's canonical anchor table:
   - every capability row has a matching canonical row in the same change file
   - every canonical row that directly names a planned capability appears in that capability file
   - capability files do not introduce independent anchor names, changed source documents, changed line ranges, or changed primary coverage statuses
4. Build `change-capability-anchors/index.md` from the per-change directories.
5. Extract every canonical Phase 2 change-anchor row with its source document, original anchor name, line range, source phrase, coverage status, change, capabilities, roles, and rationale. Preserve the original anchor names and ranges from each change.
6. Read nested capability anchor files only to verify derived-view consistency and evaluate capability boundaries. Do not count nested capability rows as additional coverage when they duplicate canonical change anchors.
7. Optionally run `scripts/phase3_line_range_audit.py` to mechanically parse canonical rows, normalize line ranges, merge ranges, list candidate uncovered intervals, list overlaps, and flag malformed rows. Include a short summary of helper findings in the Phase 3 report if used.
8. For each source document in the manifest, union all canonical Phase 2 change-anchor line ranges. The union is the coverage basis for that source document.
9. Identify ranges outside every canonical Phase 2 anchor range. Read only those candidate ranges plus necessary local context and classify them:
   - ignore blank lines, table separators, decorative separators, generated table-of-contents lines, and pure formatting
   - ignore background prose, repeated summaries, discarded options, and purely explanatory text unless it defines a production behavior, boundary, data fact, verification obligation, deployment requirement, auth/privacy rule, failure path, or preserve constraint
   - record each remaining meaningful uncovered range as a coverage gap
10. Treat a source document with no canonical Phase 2 anchor ranges as a whole-document `candidate-uncovered` item until targeted reading proves it is reference-only, intentionally not read, a non-source artifact, or meaningful uncovered content.
11. For each source document, detect cross-change and cross-capability overlaps by intersecting canonical Phase 2 anchor line ranges. List overlaps when ranges intersect or one range contains another; preserve all participating original anchor names.
12. Explain each overlap as one of: valid shared source context, dependency/preserve evidence, same user/system loop split across changes, duplicated scope, conflicting ownership, broad anchor range, or unclear.
13. Build an exhaustive adjustment ledger for every meaningful uncovered range, blocking capability-view inconsistency, or problematic overlap. Do not summarize with `+N more`; each required adjustment needs its own finding id.
14. Build compact global statistics across source documents, changes, capabilities, covered ranges, meaningful uncovered ranges, overlap findings, gaps, and conflicts.
15. Decide whether the current change plan is coherent, needs targeted Phase 4 adjustment, or is blocked.

The Phase 3 subagent may normalize paths, line range formatting, and table formatting in its review files so the result is readable. It must not merge away original Phase 2 anchor names or treat cross-change anchor-name mismatch as a coverage issue. Within one change, capability-view mismatch against the canonical change table is an artifact consistency issue and must be listed in the adjustment ledger or blockers.

## Required Tables

`source-doc-manifest.md` must include:

| Source Document | Classification | Phase 2 Anchor Ranges | Meaningful Uncovered Ranges | Read Scope | Reason |
| --- | --- | --- | --- | --- | --- |

`change-capability-anchors/index.md` must include:

| Change | Change Directory | Source Anchor File | Capability Anchor Files | Source Documents Read In Phase 2 | Anchors | Capability Gaps | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- |

`coverage-review.md` must include a per-change coverage table:

| Change | Anchor Files | Source Documents | Anchors | Capabilities | Gaps | Review Judgment |
| --- | --- | --- | --- | --- | --- | --- |

It must include a per-source-document coverage table:

| Source Document | Phase 2 Range Coverage Summary | Meaningful Uncovered Ranges | Cross-Change Overlaps | Read Scope | Non-Coverage Statuses | Review Judgment |
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

`reviews/change-plan-adjustments.md` must include an exhaustive adjustment ledger when the decision is `adjust` or `blocked`:

| Finding ID | Finding Type | Source Ranges or Anchors | Semantic Reason | Recommended Owner Change | Recommended Owner Capabilities | Required Phase 4 File Updates | Closure Criteria |
| --- | --- | --- | --- | --- | --- | --- | --- |

`Finding Type` should be one of `meaningful-uncovered-range`, `problematic-overlap`, `capability-view-inconsistency`, `capability-boundary-gap`, or `blocked-decision`. Every ledger row must be actionable without rereading the whole Phase 3 report.

## Review Questions

Evaluate:

1. Does every planned change have one independent per-change source anchor file and one nested capability anchor file per planned capability increment?
2. Is every source document under the specified roots listed in `source-doc-manifest.md` with a justified classification?
3. For each source document, what source ranges are covered by the union of all canonical Phase 2 anchor line ranges?
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

## Adjustment Recommendation Rules

Phase 3 recommends plan changes only when global source-document coverage evidence requires it. It writes recommendations to `reviews/change-plan-adjustments.md` and returns `Decision: adjust`. Phase 3 must not directly edit `change-plan.md` or Phase 2 per-change/capability anchor files.

Recommend adding or splitting a change only when a meaningful uncovered source range or problematic overlap reveals a source-backed user/system loop with its own entry, fact, projection, failure path, and verification surface.

Recommend adding or renaming a capability only when uncovered ranges or overlap analysis reveal a durable behavior boundary that is not represented by the current capability map.

Recommend keeping a source range out of all changes only if the non-coverage rationale is source-backed and production-safe.

Recommend attaching a source range to an existing change only if that change's scope already owns the same user/system loop in the plan. The ledger must name both the canonical change file and the derived capability files that Phase 4 must update.

Do not recommend changes for background prose, repeated summaries, discarded options, pure implementation details, or prototype demo mechanics unless they define a production behavior, boundary, or verification obligation.

If a gap requires broad reanalysis rather than targeted use of Phase 3 source-range findings, return `Decision: blocked` and state that a full Phase 2 rerun would be required only after user confirmation.

## Decision Values

`coverage-review.md` must end with exactly one decision:

- `Decision: complete`
- `Decision: adjust`
- `Decision: blocked`

Use `complete` only when every planned change has a per-change source anchor file and one nested capability anchor file per planned capability increment, all nested capability files are consistent derived views of their canonical change files, every source document under the specified roots is manifest-classified, every planned capability increment is source-backed or has a justified non-coverage/gap rationale, there are no unclassified anchors, no blocking conflicts, every source document's meaningful content is covered by at least one canonical Phase 2 change-anchor line range or classified with justified non-coverage, every adjustment ledger item is closed or non-blocking, and cross-change overlaps are explained as valid sharing or explicitly non-blocking.

Use `adjust` when meaningful source content is not covered by any canonical Phase 2 change-anchor range, overlap shows duplicated or distorted scope, capability boundaries need targeted edits, or current Phase 2 artifacts need focused updates. Phase 4 must run next, using the exhaustive adjustment ledger.

Use `blocked` when source documents conflict, source roots are incomplete, the user must decide a boundary before coverage can close, or targeted Phase 4 adjustment is insufficient without a broad Phase 2 rerun.

## Final Report

When complete, `alignment-final-report.md` must summarize:

- planned changes analyzed
- per-change source anchor files consumed
- per-change capability anchor files consumed
- source documents classified
- Phase 2 anchor line ranges reviewed by source document
- source documents covered
- meaningful uncovered source ranges, or confirmation that none remain
- cross-change and cross-capability overlap findings
- changes covered
- capabilities covered
- planned capability increments covered or gap-classified
- non-coverage classifications
- conflicts resolved or remaining
- confirmation that every source document under the specified roots is covered by Phase 2 anchor ranges or justified
- confirmation that no Phase 3 reverse-index or duplicate map artifacts were created by default
- confirmation that no legacy/deleted coverage checker or raw helper output was used as a gate
- confirmation that any line-range helper output, if used, was treated only as mechanical candidate input
- confirmation that no source anchor remains unclassified

The final agent reply should be short and include the decision, changed files, meaningful uncovered ranges, overlap findings, remaining blockers, and whether Phase 4 is required.
