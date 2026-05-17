---
name: source-aligned-change-plan-coverage
description: Use before openspec propose when the user wants a global, source-doc-aligned OpenSpec change plan with source anchor coverage, change/capability mapping, gap analysis, and iterative refinement until every source document's meaningful content is covered by Phase 2 anchor line ranges or explicitly gap-classified.
---

# Source-Aligned Change Plan Coverage

Create a globally source-aligned OpenSpec change plan before any individual `openspec-propose` change is created.

This skill turns an initial change plan into independently gathered per-change source evidence, then reviews and adjusts the combined results globally. Phase 1 is a planning pass only: it may cite coarse source hints for human orientation, but it must not create a pending evidence inventory, line-range anchors, coverage statuses, or Phase 2 work queues. Phase 2 is the first phase that extracts canonical source anchors. It is per-change and subagent-isolated: each planned change gets a fresh subagent that reads source documents globally and extracts canonical anchors for that change's full vertical slice. Capability mappings are refinement tags on those canonical change anchors. The nested capability files are derived capability views for that same change, not independent second-pass anchor searches.

Because Phase 2 subagents are independent across changes, their anchor names and line ranges may differ for the same source content across different changes. Within one change, however, the per-change anchor file is canonical: every nested capability anchor row must derive from a row in that change's canonical anchor table, and every canonical row that names a direct capability must appear in that capability's nested file. Phase 3 audits Phase 2 outputs by source document: it groups canonical Phase 2 anchors by source document, unions their line ranges, writes one per-source-document review file that records the local audit process, reads only uncovered candidate ranges plus necessary local context, and evaluates whether each source document contains meaningful content not covered by any Phase 2 anchor. As a secondary human-review aid, Phase 3 lists cross-change anchor range overlaps and explains why they overlap. Phase 3 may use the bundled deterministic line-range helper for mechanical candidate ranges, but final coverage decisions require semantic review and must not be made from raw line counts alone.

## Required Inputs

- Source document roots or exact source document paths.
- Optional existing change plan to refine.

All workflow artifacts belong under `openspec/orchestrate/`.

## Output Layout

Keep only core orchestration artifacts at the root:

```text
openspec/orchestrate/
├── change-plan.md
├── source-doc-manifest.md
├── source-doc-coverage/
│   └── <source-relative-path-without-extension>.coverage.md # single-level Phase 3 per-source-doc audit file; replace path separators with "--"
├── change-capability-anchors/
│   ├── index.md                    # Phase 3 index of per-change anchor directories
│   └── <change-slug>/
│       ├── <change-slug>.md         # one independent source anchor analysis per change
│       └── capability-anchors/
│           └── <capability-slug>.md # capability anchors scoped to this change
├── reviews/
│   ├── coverage-review.md
│   └── change-plan-adjustments.md   # only when Phase 3 decides adjust or blocked
└── reports/
    ├── phase-1-agent-report.md
    ├── phase-2-agent-report.md
    ├── phase-3-agent-report.md
    ├── phase-4-agent-report.md        # only when Phase 4 is invoked
    └── alignment-final-report.md
```

Optional bundled helper:

```text
.codex/skills/source-aligned-change-plan-coverage/scripts/
└── phase3_line_range_audit.py   # mechanical Phase 3 candidate uncovered/overlap helper
```

Phase 2 per-change anchor files are the canonical source inputs for later `openspec-propose` work, and Phase 3 review files are audit outputs. The `source-doc-coverage/` directory records Phase 3 per-document audit process notes, not a canonical anchor corpus or later `openspec-propose` input. When Phase 4 adjusts the plan or Phase 2-derived artifacts, update the current files in place. Reports summarize the latest pass instead of preserving every intermediate attempt.

## Reference Files

Read these references only when entering the matching phase:

- Phase 1 initial plan: `references/phase-1-initial-change-plan.md`
- Phase 2 source coverage: `references/phase-2-source-anchor-coverage.md`
- Phase 3 source document coverage review: `references/phase-3-coverage-review-iteration.md`
- Phase 4 targeted plan adjustment: `references/phase-4-targeted-plan-adjustment.md`

## Subagent Rule

This workflow is subagent-based. Phase 1 and Phase 3 MUST each be performed by a fresh independent subagent. Phase 2 MUST use fresh independent subagents for each planned change. Phase 4 MUST use a fresh independent targeted-adjustment subagent when Phase 3 finds source-backed meaningful content that requires plan or Phase 2 artifact updates.

- Phase 1: initial change plan generation.
- Phase 2 change analysis: one canonical change-anchor analysis subagent per planned change; do not use one subagent to analyze multiple changes. Nested capability files are derived views from that change's canonical anchor table.
- Phase 3: per-source-document line-range coverage review, cross-change overlap review, and adjustment decision using Phase 2 anchors as the source of truth.
- Phase 4: targeted change-plan and Phase 2 artifact adjustment using Phase 3 findings; do not rerun the full Phase 2 workflow.

If Phase 3 returns `adjust`, spawn a fresh Phase 4 subagent, then run Phase 3 again with a fresh review subagent. Do not reuse prior phase or per-change agents. Do not rerun all Phase 2 subagents unless Phase 4 reports that targeted adjustment is insufficient and the user explicitly requests a full Phase 2 rerun.

Using this skill explicitly authorizes its required subagent workflow. Do not ask for additional confirmation solely to spawn the phase or per-change subagents. If subagents are unavailable or disallowed by the runtime, stop and report a blocker instead of doing the phase in the main agent.

The main agent only orchestrates, checks interface-level outputs, and starts the next phase. It should not silently redo a phase's content work.

## Workflow

1. Create `openspec/orchestrate/`, `openspec/orchestrate/reviews/`, and `openspec/orchestrate/reports/`.
2. Phase 1: if there is no current `change-plan.md`, spawn a fresh subagent to generate it using the Phase 1 reference.
3. Phase 2 change analysis: for every planned change, spawn a fresh independent subagent. Each subagent uses only that change's name, plan definition, planned capability increments, and the source document roots to simulate the later `openspec-propose` source search for that change. It writes `change-capability-anchors/<change-slug>/<change-slug>.md` as the canonical anchor table for the change, then derives `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` files from that canonical table.
4. Phase 3: spawn a fresh subagent to audit all Phase 2 per-change outputs into `source-doc-manifest.md`, `source-doc-coverage/<source-relative-path-without-extension>.coverage.md` files, `change-capability-anchors/index.md`, `reviews/coverage-review.md`, and, only when needed, `reviews/change-plan-adjustments.md`; for each source document, union canonical Phase 2 change-anchor line ranges to find candidate source content not covered by any anchor; write a per-source-doc audit file that records range coverage, candidate uncovered ranges, read scope, semantic classifications, overlap findings, and judgment; read only candidate ranges plus necessary local context for semantic review; list cross-change/capability line-range overlaps for human review; and decide:
   - `complete`: every source document's meaningful content is covered by at least one Phase 2 anchor line range or has a justified non-coverage status, and the plan is coherent.
   - `adjust`: uncovered meaningful source content, overlap conflicts, or bad slicing require targeted plan and Phase 2 artifact updates.
   - `blocked`: source docs, change boundaries, conflicts, or coverage evidence are insufficient.
5. Phase 4: if Phase 3 returns `adjust`, spawn a fresh targeted-adjustment subagent. It updates `change-plan.md`, `reviews/change-plan-adjustments.md`, and only the affected Phase 2 output files in place. It must not rerun the full Phase 2 workflow. For every affected change, it updates the canonical change anchor table first, then regenerates or synchronizes the affected nested capability files from that canonical table.
6. Continue Phase 3 -> Phase 4 -> Phase 3 until Phase 3 returns `complete` or `blocked`.

## Main-Agent Gates

After each phase, check only interface facts:

- Required files exist under `openspec/orchestrate/`.
- Phase reports state the input docs, output files, and blockers.
- Phase 2 outputs contain one `change-capability-anchors/<change-slug>/<change-slug>.md` file and one `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` file for each planned capability increment in that change.
- Phase 2 nested capability files are consistent derived views: every capability anchor row exists in the same change's canonical anchor table, and every canonical anchor row that directly names a planned capability exists in that capability's nested file.
- Phase 2 reports include a per-change subagent trace showing source documents read, anchors found, capability increments mapped, gaps, and blockers for each planned change.
- Phase 3 outputs contain `change-capability-anchors/index.md`, `source-doc-manifest.md`, one `source-doc-coverage/<source-relative-path-without-extension>.coverage.md` file for every source document listed in the manifest, `reviews/coverage-review.md`, `reports/phase-3-agent-report.md`, and `reviews/change-plan-adjustments.md` only when adjustment or blocking findings exist.
- Phase 3 reports include per-source-document Phase 2 anchor line-range coverage summaries, uncovered meaningful source ranges, cross-change/capability overlap findings, non-coverage classifications, and source-backed ranges not mapped to any change or capability.
- Phase 3 reports may include deterministic line-range helper results as mechanical candidates, but must not use helper output as the quality gate. Raw line counts or uncovered ranges alone are not sufficient without semantic review.
- Phase 3 outputs contain a decision of `complete`, `adjust`, or `blocked`.
- If Phase 4 is invoked, its report states which Phase 3 findings were addressed, which files were updated, which new or changed per-change/capability anchor files were written, and whether targeted adjustment was sufficient.

Do not start `openspec-propose` from this workflow until Phase 3 reports `complete`.
