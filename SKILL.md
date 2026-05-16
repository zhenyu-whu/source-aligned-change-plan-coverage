---
name: source-aligned-change-plan-coverage
description: Use before openspec propose when the user wants a global, source-doc-aligned OpenSpec change plan with source anchor coverage, change/capability mapping, gap analysis, and iterative refinement until every source span has an explicit coverage status.
---

# Source-Aligned Change Plan Coverage

Create a globally source-aligned OpenSpec change plan before any individual `openspec-propose` change is created.

This skill turns an initial change plan into independently gathered per-change source and capability evidence, then reviews and assembles the combined results globally. Phase 2 is per-change and subagent-isolated: each planned change gets a fresh subagent that reads source documents globally, finds anchors for that change alone, and maps those anchors to the capability increments that the change plan says this change must deliver. Phase 3 consumes all per-change outputs, builds the global source/capability/change indexes, performs coverage statistics, and decides whether uncovered source obligations or distorted change slicing require plan adjustment.

## Required Inputs

- Source document roots or exact source document paths.
- Optional existing change plan to refine.

Do not write outputs under `docs/plans/`. All workflow artifacts belong under `openspec/orchestrate/`.

## Output Layout

Keep only core orchestration artifacts at the root:

```text
openspec/orchestrate/
├── change-plan.md
├── source-doc-manifest.md
├── source-anchor-index.md          # lightweight pointer/summary only
├── change-capability-anchors/
│   ├── index.md                    # Phase 3 index of per-change anchor directories
│   └── <change-slug>/
│       ├── <change-slug>.md         # one independent source anchor analysis per change
│       └── capability-anchors/
│           └── <capability-slug>.md # capability anchors scoped to this change
├── source-anchors/
│   ├── index.md                    # readable index of per-document anchor files
│   └── <source-doc-slug>.md         # one full anchor table per source document
├── change-source-map.md
├── capability-source-map.md
├── reviews/
│   ├── coverage-review.md
│   └── change-plan-adjustments.md
└── reports/
    ├── phase-1-agent-report.md
    ├── phase-2-agent-report.md
    ├── phase-3-agent-report.md
    └── alignment-final-report.md
```

Do not create `iterations/`. When Phase 2 and Phase 3 iterate, update the current files in place. Reports may summarize the latest pass, but they should not preserve every intermediate attempt.

## Reference Files

Read these references only when entering the matching phase:

- Phase 1 initial plan: `references/phase-1-initial-change-plan.md`
- Phase 2 source coverage: `references/phase-2-source-anchor-coverage.md`
- Phase 3 review and iteration: `references/phase-3-coverage-review-iteration.md`

## Subagent Rule

This workflow is subagent-based. Phase 1 and Phase 3 MUST each be performed by a fresh independent subagent. Phase 2 MUST use fresh independent subagents for each planned change:

- Phase 1: initial change plan generation.
- Phase 2 change analysis: one source/capability anchor analysis subagent per planned change; do not use one subagent to analyze multiple changes.
- Phase 3: global assembly, coverage review, scientific synthesis, and iteration decision.

If Phase 2 and Phase 3 iterate, each new Phase 2 pass uses new per-change subagents, and each new Phase 3 pass uses a new review subagent. Do not reuse prior phase or per-change agents.

Using this skill explicitly authorizes its required subagent workflow. Do not ask for additional confirmation solely to spawn the phase or per-change subagents. If subagents are unavailable or disallowed by the runtime, stop and report a blocker instead of doing the phase in the main agent.

The main agent only orchestrates, checks interface-level outputs, and starts the next phase. It should not silently redo a phase's content work.

## Workflow

1. Create `openspec/orchestrate/`, `openspec/orchestrate/reviews/`, and `openspec/orchestrate/reports/`.
2. Phase 1: if there is no current `change-plan.md`, spawn a fresh subagent to generate it using the Phase 1 reference.
3. Phase 2 change analysis: for every planned change, spawn a fresh independent subagent. Each subagent uses only that change's name, plan definition, planned capability increments, and the source document roots to simulate the later `openspec-propose` source search for that change, then writes `change-capability-anchors/<change-slug>/<change-slug>.md` and `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md`.
4. Phase 3: spawn a fresh subagent to assemble all Phase 2 per-change outputs into `source-doc-manifest.md`, `change-capability-anchors/index.md`, `source-anchors/`, `source-anchor-index.md`, `change-source-map.md`, and `capability-source-map.md`; analyze source-document coverage and cross-change statistics; identify source-backed spans not covered by any change; and decide:
   - `complete`: no unclassified source spans remain and the plan is coherent.
   - `iterate`: update the change plan based on coverage gaps, conflicts, or over/under-slicing, then run Phase 2 again.
   - `blocked`: source docs, change boundaries, conflicts, or coverage evidence are insufficient.
5. Continue Phase 2 -> Phase 3 until Phase 3 returns `complete` or `blocked`.

## Main-Agent Gates

After each phase, check only interface facts:

- Required files exist under `openspec/orchestrate/`.
- Phase reports state the input docs, output files, and blockers.
- Phase 2 outputs contain one `change-capability-anchors/<change-slug>/<change-slug>.md` file and one `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` file for each planned capability increment in that change.
- Phase 2 reports include a per-change subagent trace showing source documents read, anchors found, capability increments mapped, gaps, and blockers for each planned change.
- Phase 3 outputs contain `change-capability-anchors/index.md`, `source-doc-manifest.md`, `source-anchors/index.md`, one per-document reverse-index file for each required or conditionally read source document, `source-anchor-index.md`, `change-source-map.md`, and `capability-source-map.md`.
- Phase 3 reports include global coverage statistics and mechanical coverage summary, including uncovered semantic lines, overlapping anchor lines, bad line ranges, and source-backed spans not mapped to any change.
- Phase 3 outputs contain a decision of `complete`, `iterate`, or `blocked`.

Do not start `openspec-propose` from this workflow until Phase 3 reports `complete`.
