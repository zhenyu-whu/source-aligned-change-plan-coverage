# Phase 2: Source Anchor Coverage Mapping

Phase 2 maps source documents to the current change plan. It does not rewrite the plan.

## Inputs

- `openspec/orchestrate/change-plan.md`
- User-specified source document roots or exact source paths.
- `openspec/orchestrate/source-doc-manifest.md` if it already exists.

## Outputs

Write current copies only:

- `openspec/orchestrate/source-doc-manifest.md`
- `openspec/orchestrate/source-anchor-index.md`
- `openspec/orchestrate/change-source-map.md`
- `openspec/orchestrate/capability-source-map.md`
- `openspec/orchestrate/reports/phase-2-agent-report.md`

Do not create `iterations/` or preserve old Phase 2 copies. If Phase 3 requests iteration, update these files in place.

## Source Discovery

Enumerate every source document under the user-specified roots. Classify each as:

- `required`
- `conditionally relevant and read`
- `reference-only`
- `intentionally not read`
- `non-source artifact`

`intentionally not read` requires a concrete no-overlap reason. Convenience, large file size, or expected irrelevance is not enough.

## Anchor Granularity

Use source-native anchors. Prefer:

- headings and subheadings
- table rows
- numbered plan rows
- route names
- command/API/DTO/entity/table/job/event identifiers
- decision IDs
- prototype object keys
- verification rows
- deployment or ops anchors

Every anchor must include a stable anchor name and a line range for Markdown or text source files. Line ranges are navigation hints, not the only identity.

## Line-Span Coverage

For Markdown or text source files, Phase 2 must support a mechanical coverage check:

- Every non-empty semantic line must belong to exactly one source anchor row, unless it is classified as `non-semantic-formatting`.
- Table separator rows, blank lines, generated table-of-contents lines, and purely decorative separators may be grouped with adjacent anchors or classified as `non-semantic-formatting`.
- A heading line belongs to the section anchor it opens.
- A table row with source meaning should normally be its own anchor or part of a small contiguous table-row range.
- Do not use a single broad document-level anchor when the document contains multiple sections, rows, states, routes, decisions, requirements, or verification obligations.
- Record any uncovered line ranges in the Phase 2 agent report. Uncovered semantic line ranges are blockers for Phase 3 unless Phase 3 reclassifies them with evidence.

## Coverage Status

Every source anchor must have exactly one primary status:

- `current-change`
- `capability-boundary`
- `preserve-existing`
- `later-change`
- `explicit-non-goal`
- `reference-only`
- `prototype-only-not-production`
- `superseded`
- `duplicate`
- `no-product-or-system-impact`
- `non-semantic-formatting`
- `unresolved-conflict`
- `unclassified`

`unclassified` is allowed only as a Phase 2 finding and is a Phase 3 blocker candidate.

`non-semantic-formatting` is allowed only for blank-equivalent formatting, table separator rows, generated table-of-contents lines, or purely decorative separators. It must not hide source meaning.

## Mapping Roles

An anchor may map to multiple changes or capabilities. For each mapping, record one or more roles:

- `primary`
- `modified`
- `preserve`
- `verification`
- `non-goal`
- `dependency`
- `later-expansion`
- `reference`
- `superseded-by`
- `conflict`

Do not treat `preserve`, `dependency`, or `reference` as direct capability advancement in the change plan matrix.

## Required Tables

`source-anchor-index.md` must include:

| Source Document | Anchor | Lines | Source Phrase | Coverage Status | Changes | Capabilities | Roles | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

`source-doc-manifest.md` must include:

| Source Document | Classification | Line Span Coverage | Uncovered Semantic Lines | Reason |
| --- | --- | --- | --- | --- |

`change-source-map.md` must include:

| Change | Source Anchors | Capabilities | Roles | Coverage Notes |
| --- | --- | --- | --- | --- |

`capability-source-map.md` must include:

| Capability | Source Anchors | Changes | Boundary Notes |
| --- | --- | --- | --- |

## Quality Gate

Before finishing Phase 2:

- Confirm every discovered source document is classified.
- Confirm every required or conditionally read document has anchor-level coverage.
- Confirm every source anchor has a primary coverage status.
- Confirm every required or conditionally read Markdown/text document has no uncovered semantic line ranges.
- Confirm every `current-change`, `capability-boundary`, `preserve-existing`, `later-change`, and `explicit-non-goal` anchor maps to at least one change or capability unless the rationale explains why it cannot.
- List all `unclassified` and `unresolved-conflict` anchors in the agent report.

Final reply should be a short report: documents classified, anchors indexed, mapped changes, mapped capabilities, unclassified anchors, unresolved conflicts, and blockers.
