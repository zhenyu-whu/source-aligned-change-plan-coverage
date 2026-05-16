---
name: source-aligned-change-plan-coverage
description: Use before openspec propose when the user wants a global, source-doc-aligned OpenSpec change plan with source anchor coverage, change/capability mapping, gap analysis, and iterative refinement until every source document's meaningful content is covered by Phase 2 anchor line ranges or explicitly gap-classified.
---

# Source-Aligned Change Plan Coverage

Create a globally source-aligned OpenSpec change plan before any individual `openspec-propose` change is created.

This skill turns an initial change plan into independently gathered per-change source and capability evidence, then reviews and assembles the combined results globally. Phase 2 is per-change and subagent-isolated: each planned change gets a fresh subagent that reads source documents globally, finds anchors for that change alone, and maps those anchors to the capability increments that the change plan says this change must deliver. Because Phase 2 subagents are independent, their anchor names and line ranges may differ for the same source content. Phase 3 must not normalize those differences away as the primary task. Instead, Phase 3 groups all Phase 2 anchors by source document, unions their line ranges, and evaluates whether each source document contains meaningful content not covered by any Phase 2 anchor. As a secondary human-review aid, Phase 3 lists cross-change anchor range overlaps and explains why they overlap. Phase 3 must not run bundled coverage scripts.

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
    ├── phase-4-agent-report.md        # only when Phase 4 is invoked
    └── alignment-final-report.md
```

Do not create `iterations/`. When Phase 4 adjusts the plan or Phase 2-derived artifacts, update the current files in place. Reports may summarize the latest pass, but they should not preserve every intermediate attempt.

## Reference Files

Read these references only when entering the matching phase:

- Phase 1 initial plan: `references/phase-1-initial-change-plan.md`
- Phase 2 source coverage: `references/phase-2-source-anchor-coverage.md`
- Phase 3 source document coverage review: `references/phase-3-coverage-review-iteration.md`
- Phase 4 targeted plan adjustment: `references/phase-4-targeted-plan-adjustment.md`

## Subagent Rule

This workflow is subagent-based. Phase 1 and Phase 3 MUST each be performed by a fresh independent subagent. Phase 2 MUST use fresh independent subagents for each planned change. Phase 4 MUST use a fresh independent targeted-adjustment subagent when Phase 3 finds source-backed meaningful content that requires plan or Phase 2 artifact updates.

- Phase 1: initial change plan generation.
- Phase 2 change analysis: one source/capability anchor analysis subagent per planned change; do not use one subagent to analyze multiple changes.
- Phase 3: global assembly, per-source-document line-range coverage review, cross-change overlap review, and adjustment decision.
- Phase 4: targeted change-plan and Phase 2 artifact adjustment using Phase 3 findings; do not rerun the full Phase 2 workflow.

If Phase 3 returns `adjust`, spawn a fresh Phase 4 subagent, then run Phase 3 again with a fresh review subagent. Do not reuse prior phase or per-change agents. Do not rerun all Phase 2 subagents unless Phase 4 reports that targeted adjustment is insufficient and the user explicitly requests a full Phase 2 rerun.

Using this skill explicitly authorizes its required subagent workflow. Do not ask for additional confirmation solely to spawn the phase or per-change subagents. If subagents are unavailable or disallowed by the runtime, stop and report a blocker instead of doing the phase in the main agent.

The main agent only orchestrates, checks interface-level outputs, and starts the next phase. It should not silently redo a phase's content work.

## Workflow

1. Create `openspec/orchestrate/`, `openspec/orchestrate/reviews/`, and `openspec/orchestrate/reports/`.
2. Phase 1: if there is no current `change-plan.md`, spawn a fresh subagent to generate it using the Phase 1 reference.
3. Phase 2 change analysis: for every planned change, spawn a fresh independent subagent. Each subagent uses only that change's name, plan definition, planned capability increments, and the source document roots to simulate the later `openspec-propose` source search for that change, then writes `change-capability-anchors/<change-slug>/<change-slug>.md` and `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md`.
4. Phase 3: spawn a fresh subagent to assemble all Phase 2 per-change outputs into `source-doc-manifest.md`, `change-capability-anchors/index.md`, `source-anchors/`, `source-anchor-index.md`, `change-source-map.md`, and `capability-source-map.md`; for each source document, union Phase 2 anchor line ranges to find meaningful source content not covered by any anchor; list cross-change/capability line-range overlaps for human review; and decide:
   - `complete`: every source document's meaningful content is covered by at least one Phase 2 anchor line range or has a justified non-coverage status, and the plan is coherent.
   - `adjust`: uncovered meaningful source content, overlap conflicts, or bad slicing require targeted plan and Phase 2 artifact updates.
   - `blocked`: source docs, change boundaries, conflicts, or coverage evidence are insufficient.
5. Phase 4: if Phase 3 returns `adjust`, spawn a fresh targeted-adjustment subagent. It updates `change-plan.md`, `reviews/change-plan-adjustments.md`, and only the affected Phase 2 output files in place. It must not rerun the full Phase 2 workflow and must not use coverage scripts.
6. Continue Phase 3 -> Phase 4 -> Phase 3 until Phase 3 returns `complete` or `blocked`.

## Main-Agent Gates

After each phase, check only interface facts:

- Required files exist under `openspec/orchestrate/`.
- Phase reports state the input docs, output files, and blockers.
- Phase 2 outputs contain one `change-capability-anchors/<change-slug>/<change-slug>.md` file and one `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` file for each planned capability increment in that change.
- Phase 2 reports include a per-change subagent trace showing source documents read, anchors found, capability increments mapped, gaps, and blockers for each planned change.
- Phase 3 outputs contain `change-capability-anchors/index.md`, `source-doc-manifest.md`, `source-anchors/index.md`, one per-document reverse-index file for each required or conditionally read source document, `source-anchor-index.md`, `change-source-map.md`, and `capability-source-map.md`.
- Phase 3 reports include per-source-document Phase 2 anchor line-range coverage summaries, uncovered meaningful source ranges, cross-change/capability overlap findings, non-coverage classifications, and source-backed ranges not mapped to any change or capability.
- Phase 3 reports must not include bundled-script results as quality gates. Line ranges are allowed and expected as the Phase 3 coverage mechanism, but raw line counts alone are not sufficient without semantic review of the uncovered ranges.
- Phase 3 outputs contain a decision of `complete`, `adjust`, or `blocked`.
- If Phase 4 is invoked, its report states which Phase 3 findings were addressed, which files were updated, which new or changed per-change/capability anchor files were written, and whether targeted adjustment was sufficient.

Do not start `openspec-propose` from this workflow until Phase 3 reports `complete`.
