# Phase 2: Independent Per-Change Source Anchor Analysis

Phase 2 analyzes the current change plan one change at a time. Each planned change is handled by a fresh independent subagent that reads the source documents globally, finds the anchors that would support a later `openspec-propose` for that single change, and maps those anchors to the capability increments that the change plan assigns to that change.

The primary Phase 2 analysis unit is one change. Do not make a single agent analyze multiple changes. Do not compare a change's anchors with other changes during the change analysis pass. Phase 2 does not rewrite the plan and does not assemble global source indexes.

## Inputs

- `openspec/orchestrate/change-plan.md`
- User-specified source document roots or exact source paths.

## Outputs

Write current Phase 2 copies only:

- `openspec/orchestrate/change-capability-anchors/<change-slug>/<change-slug>.md` for each planned change.
- `openspec/orchestrate/change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` for each planned capability increment in that change.
- `openspec/orchestrate/reports/phase-2-agent-report.md`

Do not create `iterations/`. If Phase 4 applies targeted adjustments, update these files in place and remove stale per-change anchor files whose changes are no longer current.

Do not write these Phase 3 assembly outputs in Phase 2:

- `source-doc-manifest.md`
- `change-capability-anchors/index.md`
- `source-anchor-index.md`
- `source-anchors/`
- `change-source-map.md`
- `capability-source-map.md`

## Per-Change Subagent Discipline

Phase 2 must be reviewable as a set of independent change analyses.

1. Read the current `change-plan.md` and list planned changes in order.
2. For each planned change, spawn a fresh independent subagent:
   - Give it the change name, that change's full definition, and that change's planned capability increments from `change-plan.md`.
   - Give it the source document roots or exact source paths.
   - Ask it to simulate the later `openspec-propose` source search for only that change.
   - Ask it to map each source-backed requirement to the specific capability increment it supports for that change.
   - It may read any source document needed to find precise anchors for that change.
   - It must not read other `change-capability-anchors/<other-change-slug>/` directories, prior Phase 2 summaries, `source-anchors/`, `change-source-map.md`, or `capability-source-map.md`.
   - It must write only inside `openspec/orchestrate/change-capability-anchors/<change-slug>/`.

Use deterministic change slugs:

- change `editor-canvas-first-loop` -> `editor-canvas-first-loop.md`
- change `auth: session hardening` -> `auth-session-hardening.md`
- capability `identity-session-continuity` -> `identity-session-continuity.md`

## Per-Change Anchor Files

Each `change-capability-anchors/<change-slug>/<change-slug>.md` file must include:

- change name
- change definition excerpt used
- planned capability increments used
- source documents read
- source documents intentionally not read, with reasons
- anchor table
- gaps where the change appears to need source evidence but no precise anchor was found
- blockers, or `None`

Each per-change anchor table must include:

| Source Document | Anchor | Lines | Source Phrase | Coverage Status | Capabilities | Roles | Rationale | Propose Use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

For anchors that directly advance the change, `Capabilities` must name the planned capability increment or increments supported by that anchor. Anchors used only as preserve, dependency, reference, non-goal, or later-expansion evidence may list contextual capabilities, but the rationale must say they are not direct capability advancement.

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

Every Markdown or text anchor must include a stable anchor name and a line range. Line ranges are navigation hints, not the only identity.

## Per-Change Capability Anchor Files

Each `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` file is scoped to one change and one capability. It must include:

- change name
- capability id
- planned capability increment from `change-plan.md`
- capability anchor table
- capability gaps where a planned increment lacks precise source support
- candidate new or renamed capabilities suggested by source anchors, if any
- blockers, or `None`

Each per-change capability anchor table must include:

| Capability | Planned Increment In This Change | Source Document | Anchor | Lines | Source Phrase | Coverage Status | Roles | Rationale | Propose Use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Every capability listed in the change plan for this change must have its own file, either with supporting source anchors or with an explicit capability gap. Do not create a global capability map in Phase 2.

## Coverage Status

Every source anchor in a per-change file must have exactly one primary status:

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
- `unresolved-conflict`
- `unclassified`

`unclassified` is allowed only as a Phase 2 finding and is a Phase 3 blocker candidate.

## Mapping Roles

For each anchor mapping, record one or more roles:

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

## Phase 2 Report

`reports/phase-2-agent-report.md` is an orchestration trace, not a global coverage report. It must include:

| Order | Change | Change Directory | Source Anchor File | Subagent Status | Source Documents Read | Anchors | Gaps | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

| Order | Change | Capability Anchor Files | Capability Increments | Capability Gaps | Blockers |
| --- | --- | --- | --- | --- | --- |

Do not include per-source-document coverage statistics here. Phase 3 owns per-source-document Phase 2 anchor line-range coverage, cross-change overlap review, and source/capability/change maps.

## Quality Gate

Before finishing Phase 2:

- Confirm every planned change has exactly one `change-capability-anchors/<change-slug>/<change-slug>.md`.
- Confirm every planned capability increment has exactly one `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md`.
- Confirm every per-change source anchor file and nested capability anchor files were produced by the same fresh independent subagent for that change.
- Confirm every per-change anchor file includes the change definition excerpt used, planned capability increments used, source documents read, anchor table, gaps, and blockers.
- Confirm every nested capability anchor file covers its planned capability increment with source anchors or an explicit capability gap.
- Confirm every anchor in each per-change file has a primary coverage status.
- Confirm Markdown/text anchors include line ranges.
- List all per-change `unclassified` and `unresolved-conflict` anchors in the Phase 2 report.
- List all capability gaps in the Phase 2 report.
- Confirm no Phase 3 assembly outputs were generated or rewritten by Phase 2.

Final reply should be a short report: changes analyzed, per-change anchor files written, per-change capability anchor files written, per-change source gaps, capability gaps, unclassified anchors, unresolved conflicts, and blockers.
