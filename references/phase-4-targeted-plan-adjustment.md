# Phase 4: Targeted Change Plan and Phase 2 Artifact Adjustment

Phase 4 runs only after Phase 3 returns `Decision: adjust`. It applies targeted changes to the current change plan and the affected Phase 2 output files using Phase 3's per-source-document coverage gaps and overlap findings. It exists to avoid rerunning the expensive Phase 2 workflow when Phase 3 has already identified precise source-backed uncovered ranges, problematic overlaps, or capability-boundary issues.

Phase 4 MUST be performed by a fresh independent subagent. It must not rerun all Phase 2 per-change subagents, run bundled coverage scripts, or perform a new global source search for every change.

## Inputs

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/reviews/coverage-review.md`
- `openspec/orchestrate/reviews/change-plan-adjustments.md`
- `openspec/orchestrate/source-anchors/`
- `openspec/orchestrate/source-anchor-index.md`
- `openspec/orchestrate/change-source-map.md`
- `openspec/orchestrate/capability-source-map.md`
- affected `openspec/orchestrate/change-capability-anchors/<change-slug>/` directories
- `openspec/orchestrate/reports/phase-2-agent-report.md`
- User-specified source document roots or exact source paths, for targeted context reads only

## Outputs

Update current files in place:

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/reviews/change-plan-adjustments.md`
- affected `openspec/orchestrate/change-capability-anchors/<change-slug>/<change-slug>.md`
- affected `openspec/orchestrate/change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md`
- new per-change or per-capability anchor files when the adjusted plan adds them
- `openspec/orchestrate/reports/phase-2-agent-report.md`, preserving unaffected rows and marking targeted Phase 4 updates
- `openspec/orchestrate/reports/phase-4-agent-report.md`

Do not write Phase 3 assembly outputs in Phase 4 except where they are needed as read-only inputs. A fresh Phase 3 pass rebuilds global indexes after Phase 4 finishes.

## Scope Rules

Phase 4 may:

- add, remove, split, merge, or rename changes when Phase 3's source-range or overlap evidence requires it
- add, remove, split, merge, or rename capabilities when Phase 3 identifies durable behavior-boundary gaps
- attach meaningful uncovered source ranges to an existing change when the existing change already owns the same user/system loop
- create new per-change and per-capability anchor files for new changes or capability increments
- update affected existing per-change and per-capability anchor files so they match the adjusted plan
- read targeted source context around Phase 3's uncovered ranges or overlap findings when needed to verify wording or line ranges

Phase 4 must not:

- rerun Phase 2 globally
- ask one subagent to reanalyze every planned change from scratch
- rewrite unaffected per-change directories
- invent new anchors without source evidence
- use raw uncovered line counts as a plan-adjustment driver without semantic review of the uncovered ranges
- run deleted or legacy coverage scripts

If an adjustment cannot be made from Phase 3 findings plus targeted source context, return `blocked` and explain why a full Phase 2 rerun or user decision is required.

## Workflow

1. Read Phase 3's `coverage-review.md` decision and plan-impact table.
2. Read `reviews/change-plan-adjustments.md` and extract each required adjustment.
3. Build a targeted update set: affected changes, affected capabilities, source ranges or anchors, and output files.
4. Update `change-plan.md` using the smallest coherent change that covers the source-backed obligation or fixes the slicing issue.
5. For each affected existing change, update its per-change source anchor file:
   - preserve the original Phase 2 anchor evidence that still applies
   - add Phase 3's meaningful uncovered source ranges where the adjusted change now owns them
   - remove or reclassify anchors that moved to another change
   - keep line ranges as navigation hints
   - record gaps and blockers explicitly
6. For each affected capability increment, update or create its nested capability anchor file using the same Phase 2 table format.
7. If the plan adds a new change, create its `change-capability-anchors/<change-slug>/<change-slug>.md` and nested capability anchor files from the Phase 3 source-range or overlap evidence and targeted source context.
8. Update `reports/phase-2-agent-report.md` in place:
   - preserve unaffected Phase 2 rows
   - mark affected rows as `Phase 4 targeted update`
   - add rows for new changes or capability files
   - list removed stale change directories or files if any
9. Update `reviews/change-plan-adjustments.md` with an applied-adjustments section.
10. Write `reports/phase-4-agent-report.md`.

## Phase 4 Report

`reports/phase-4-agent-report.md` must include:

| Phase 3 Finding | Source Ranges or Anchors | Plan Change Applied | Phase 2 Files Updated | Remaining Gap or Blocker |
| --- | --- | --- | --- | --- |

It must also include:

- whether `change-plan.md` changed
- affected changes and capabilities
- new or removed change/capability anchor files
- targeted source documents read, if any
- confirmation that no full Phase 2 rerun was performed
- confirmation that no coverage script was run
- next required step: `Run Phase 3 again`, or `Blocked`

## Completion

Phase 4 ends with exactly one status in `phase-4-agent-report.md`:

- `Phase 4 Status: adjusted`
- `Phase 4 Status: blocked`

Use `adjusted` when all Phase 3 adjustment findings have been applied to the current plan and affected Phase 2 artifacts.

Use `blocked` when the adjustment needs source boundaries, product decisions, or broad reanalysis that Phase 4 is not allowed to perform.

After `adjusted`, the main agent must spawn a fresh Phase 3 review subagent. Do not start `openspec-propose` directly from Phase 4.
