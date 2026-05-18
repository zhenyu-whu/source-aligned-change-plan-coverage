---
name: source-aligned-change-plan-coverage
description: Use before openspec propose when the user wants a global, source-doc-aligned OpenSpec change/capability plan with obligation atom coverage, source anchor traceability, gap analysis, and iterative refinement until every production-meaningful source obligation is owned by exactly one change/capability atom or explicitly gap-classified.
---

# Source-Aligned Change Plan Coverage

Create a globally source-aligned OpenSpec change plan before any individual `openspec-propose` change is created.

This skill turns a full-source initial change/capability framework into per-change, per-source-document obligation atom ledgers, then reviews the combined atom corpus globally and adjusts the framework. An obligation atom is the smallest source-backed production obligation that should survive into later `openspec-propose` artifacts. It may represent a page state, trigger, display rule, primary action, disabled action, recovery path, data fact, auth/privacy rule, failure path, responsive behavior, verification requirement, preserve constraint, or explicit non-goal. A contextual atom is a source-backed fact or future obligation that the current change must know about to avoid bad design, but does not directly implement or count as current capability advancement. Source anchors and line ranges are trace evidence for atoms; they are not the coverage goal.

Phase 1 is a full-source planning pass: it enumerates and reads every source document under the user-specified roots, then produces the first scientific change/capability framework. It may cite coarse source hints for human orientation, but it must not create obligation atoms, pending evidence inventories, line-range anchors, coverage statuses, or Phase 2 work queues. Phase 2 is the first phase that extracts source-backed candidate direct obligation atoms and necessary contextual atoms. It is per-change and subagent-isolated: each planned change gets a fresh subagent that reads every source document listed in the Phase 1 manifest and independently decides which direct atoms in each document belong to that change, which contextual atoms should accompany it without ownership, and which documents have no current-change obligation for that change. Capability mappings are ownership tags on direct atoms. Nested capability files are derived capability views for that same change, not independent second-pass source searches.

Because Phase 2 subagents are independent across changes, their local atom ids, anchor names, and line ranges may differ for the same source content across different changes. Within one change, however, the per-change file is canonical for that change: every nested capability atom row must derive from a row in that change's obligation atom ledger, and every direct capability-owned atom must appear in that capability's nested file. Phase 3 audits Phase 2 outputs across changes, source documents, and capabilities: it builds a global obligation atom index, detects missing atoms, duplicate atoms, ambiguous ownership, broad anchors that compress obligations, and source ranges whose remaining content is non-production or non-meaningful. It also evaluates whether each capability's atoms progress in a coherent order across changes and whether each change's atom load is reviewably small. Phase 4 uses that global analysis to scientifically adjust the change/capability framework, atom ownership, capability sequencing, and change granularity. Existing Phase 2 atoms are treated as source-backed candidate facts by default; Phase 4 should reassign ownership or contextual status unless Phase 3 proves that an atom is too broad, unsupported, or semantically wrong. As a secondary aid, Phase 3 still reviews line-range coverage and cross-change overlaps. Phase 3 may use the bundled deterministic line-range helper for mechanical candidate ranges, but final coverage decisions require semantic obligation review and must not be made from raw line counts alone.

Later `openspec-propose` and `openspec-apply-change` work must not consume isolated atom rows alone. A completed workflow should provide a change packet for each change: direct owning atoms, contextual atoms, capability progression notes, upstream realized baseline from earlier changes, downstream constraints that affect current design, non-goals, and links to the global atom index. Earlier changes provide baseline contracts for later changes, but they must not absorb all future global obligations. Future obligations belong in an earlier change only as contextual or preserve constraints when they affect current data model, API contract, state machine, auth/privacy boundary, worker boundary, persistence format, or verification truthfulness.

## Required Inputs

- Source document roots or exact source document paths.
- Optional existing change plan to refine.

All workflow artifacts belong under `openspec/orchestrate/`.

## Output Layout

Keep only core orchestration artifacts at the root:

```text
openspec/orchestrate/
├── change-plan.md
├── source-doc-manifest.md          # Phase 1 enumerates and reads; Phase 3 enriches coverage review
├── source-doc-coverage/
│   └── <source-relative-path-without-extension>.coverage.md # single-level Phase 3 per-source-doc audit file; replace path separators with "--"
├── change-capability-anchors/
│   ├── index.md                    # Phase 3 index of per-change atom directories
│   ├── obligation-atom-index.md     # Phase 3 global unique atom registry for propose/source review
│   └── <change-slug>/
│       ├── <change-slug>.md         # one independent obligation atom + source anchor analysis per change
│       └── capability-anchors/
│           └── <capability-slug>.md # capability atom view scoped to this change
├── reviews/
│   ├── phase-3-trace/
│   │   ├── local-to-global-atom-map.md       # Phase 3 mapping from every local Phase 2 atom/context row to a global atom id or relation
│   │   ├── source-remainder-review.md        # Phase 3 semantic review of source ranges not covered by atom rows
│   │   ├── duplicate-ownership-review.md     # Phase 3 duplicate, overlap, and unique-owner resolution ledger
│   │   ├── capability-change-scope-review.md # Phase 3 capability progression and change complexity working review
│   │   └── adjustment-decision-log.md        # Phase 3 candidate findings and final decision rationale
│   ├── coverage-review.md
│   └── change-plan-adjustments.md   # only when Phase 3 decides adjust or blocked
└── reports/
    ├── phase-1-agent-report.md
    ├── phase-2-agent-report.md
    ├── phase-3-agent-report.md
    ├── phase-4-agent-report.md        # only when Phase 4 is invoked
    ├── change-capability-human-plan.md # only when Phase 3 completes; human reading aid, not source of truth
    └── alignment-final-report.md
```

Optional bundled helper:

```text
.codex/skills/source-aligned-change-plan-coverage/scripts/
└── phase3_line_range_audit.py   # mechanical Phase 3 candidate uncovered/overlap helper
```

Phase 2 per-change files are the canonical per-change source inputs for later `openspec-propose` work because they contain the obligation atom ledger and supporting source anchors. Phase 3's `change-capability-anchors/obligation-atom-index.md` is the global uniqueness and ownership registry for those same atoms. The `source-doc-coverage/` directory records Phase 3 per-document audit process notes, not a replacement for the per-change atom ledgers. `reviews/phase-3-trace/` records the current Phase 3 pass's intermediate review trail so humans can audit how local atoms became global atoms, how duplicate ownership was resolved, how uncovered source ranges were classified, and why the final decision was reached. These trace files are not source of truth and must be regenerated or overwritten on each fresh Phase 3 pass. `reports/change-capability-human-plan.md` is a human-facing synthesis of the final change packets and capability progression; it must not replace the atom ledgers or global atom index as source of truth. When Phase 4 adjusts the plan or Phase 2-derived artifacts, update the current files in place. Reports summarize the latest pass instead of preserving every intermediate attempt.

## Reference Files

Read these references only when entering the matching phase:

- Phase 1 initial plan: `references/phase-1-initial-change-plan.md`
- Phase 2 source coverage: `references/phase-2-source-anchor-coverage.md`
- Phase 3 source document coverage review: `references/phase-3-coverage-review-iteration.md`
- Phase 4 targeted plan adjustment: `references/phase-4-targeted-plan-adjustment.md`

## Subagent Rule

This workflow is subagent-based. Phase 1 and Phase 3 MUST each be performed by a fresh independent subagent. Phase 2 MUST use fresh independent subagents for each planned change. Phase 4 MUST use a fresh independent targeted-adjustment subagent when Phase 3 finds source-backed missing obligations, duplicate atom ownership, broad-anchor compression, or other findings that require plan or Phase 2 artifact updates.

- Phase 1: full-source initial change/capability framework generation.
- Phase 2 change analysis: one canonical obligation atom analysis subagent per planned change; each subagent must read every source document from the Phase 1 manifest and produce a per-source direct-atom/contextual-atom/no-atom decision for that change. Do not use one subagent to analyze multiple changes. Nested capability files are derived views from that change's canonical atom ledger.
- Phase 3: cross-change/global obligation atom synthesis, source-document coverage review, duplicate atom/ownership review, capability atom progression review, change complexity review, line-range coverage review, cross-change overlap review, and adjustment decision using Phase 2 atom ledgers as the source of truth.
- Phase 4: scientific change/capability framework adjustment plus targeted Phase 2 artifact synchronization using Phase 3 findings; do not rerun the full Phase 2 workflow.

If Phase 3 returns `adjust`, spawn a fresh Phase 4 subagent, then run Phase 3 again with a fresh review subagent. Do not reuse prior phase or per-change agents. Do not rerun all Phase 2 subagents unless Phase 4 reports that targeted adjustment is insufficient and the user explicitly requests a full Phase 2 rerun.

Using this skill explicitly authorizes its required subagent workflow. Do not ask for additional confirmation solely to spawn the phase or per-change subagents. If subagents are unavailable or disallowed by the runtime, stop and report a blocker instead of doing the phase in the main agent.

The main agent only orchestrates, checks interface-level outputs, and starts the next phase. It should not silently redo a phase's content work.

## Workflow

1. Create `openspec/orchestrate/`, `openspec/orchestrate/reviews/`, `openspec/orchestrate/reviews/phase-3-trace/`, and `openspec/orchestrate/reports/`.
2. Phase 1: if there is no current `change-plan.md`, spawn a fresh subagent to enumerate and read every source document, write the initial `source-doc-manifest.md`, and generate the initial change/capability framework using the Phase 1 reference.
3. Phase 2 change analysis: for every planned change, spawn a fresh independent subagent. Each subagent uses only that change's name, plan definition, planned capability increments, and the Phase 1 source document manifest to independently read every source document and extract that change's direct obligation atoms, contextual atoms, or an explicit no-current-change-obligation classification for each document. It writes `change-capability-anchors/<change-slug>/<change-slug>.md` as the canonical per-change/per-source obligation atom ledger and source anchor table for the change, then derives `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` files from that canonical atom ledger.
4. Phase 3: spawn a fresh subagent to synthesize all Phase 2 per-change outputs into `source-doc-manifest.md`, `source-doc-coverage/<source-relative-path-without-extension>.coverage.md` files, `change-capability-anchors/index.md`, `change-capability-anchors/obligation-atom-index.md`, `reviews/phase-3-trace/*.md`, `reviews/coverage-review.md`, `reports/change-capability-human-plan.md` only when complete, and, only when needed, `reviews/change-plan-adjustments.md`; for each source document, review all production-meaningful obligation-bearing content, verify that each obligation atom is owned by exactly one change/capability or has a justified non-coverage status, detect duplicate atoms and broad anchors that compress UI/flow obligations, analyze each capability's atom progression order across changes, evaluate each change's atom load and implementation complexity, union line ranges only as secondary coverage evidence, list cross-change/capability overlaps for human review, record the intermediate local-to-global mapping/remainder/duplicate/progression/decision trace files for human audit, and decide:
   - `complete`: every production-meaningful source obligation is represented by exactly one current direct obligation atom or has a justified non-coverage status, every source document's non-atom content is production-safe to ignore, every capability's atom progression order is coherent, every change remains reviewably scoped, and the plan is coherent.
   - `adjust`: uncovered obligation atoms, duplicate/ambiguous atom ownership, broad anchor compression, incoherent capability progression, over-complex change scope, overlap conflicts, or bad slicing require framework and Phase 2 artifact updates.
   - `blocked`: source docs, change boundaries, conflicts, or coverage evidence are insufficient.
5. Phase 4: if Phase 3 returns `adjust`, spawn a fresh targeted-adjustment subagent. It updates `change-plan.md`, `reviews/change-plan-adjustments.md`, and only the affected Phase 2 output files in place. It must not rerun the full Phase 2 workflow. For every affected change, it updates the canonical obligation atom ledger first, then regenerates or synchronizes the affected nested capability files from that canonical ledger.
6. Continue Phase 3 -> Phase 4 -> Phase 3 until Phase 3 returns `complete` or `blocked`.

## Main-Agent Gates

After each phase, check only interface facts:

- Required files exist under `openspec/orchestrate/`.
- Phase reports state the input docs, output files, and blockers.
- Phase 1 outputs contain `change-plan.md`, `source-doc-manifest.md`, and `reports/phase-1-agent-report.md`; the manifest lists every source document under the specified roots with full-read status, or Phase 1 reports a blocker.
- Phase 2 outputs contain one `change-capability-anchors/<change-slug>/<change-slug>.md` file and one `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` file for each planned capability increment in that change.
- Phase 2 per-change files contain an obligation atom ledger and a supporting source anchor table; nested capability files are consistent derived views: every capability atom row exists in the same change's canonical atom ledger, and every canonical atom row that directly names a planned capability exists in that capability's nested file.
- Phase 2 reports include a per-change subagent trace showing every manifest source document was read for that change, per-source direct-atom/contextual-atom/no-atom decisions, obligation atoms found, anchors used, capability increments mapped, gaps, duplicate-risk notes, and blockers for each planned change.
- Phase 3 outputs contain `change-capability-anchors/index.md`, `change-capability-anchors/obligation-atom-index.md`, `source-doc-manifest.md`, one `source-doc-coverage/<source-relative-path-without-extension>.coverage.md` file for every source document listed in the manifest, `reviews/phase-3-trace/local-to-global-atom-map.md`, `reviews/phase-3-trace/source-remainder-review.md`, `reviews/phase-3-trace/duplicate-ownership-review.md`, `reviews/phase-3-trace/capability-change-scope-review.md`, `reviews/phase-3-trace/adjustment-decision-log.md`, `reviews/coverage-review.md`, `reports/phase-3-agent-report.md`, and `reviews/change-plan-adjustments.md` only when adjustment or blocking findings exist.
- Phase 3 reports include per-source-document obligation atom coverage summaries, global atom synthesis, capability atom progression findings, change complexity findings, source ranges whose content has no production obligation, missing or duplicate atom findings, broad-anchor compression findings, cross-change/capability overlap findings, non-coverage classifications, and source-backed obligations not mapped to any change or capability.
- Phase 3 trace files expose the intermediate reasoning path: every local Phase 2 atom/context row maps to a global atom id or non-direct relation; every uncovered source range reviewed has a semantic classification; every duplicate/overlap candidate has a unique-owner or relation decision; every capability/change scope concern has a progression or complexity judgment; every candidate finding has a final decision and, when applicable, a Phase 4 handoff.
- Phase 3 reports may include deterministic line-range helper results as mechanical candidates, but must not use helper output as the quality gate. Raw line counts or uncovered ranges alone are not sufficient without semantic review.
- Phase 3 outputs contain a decision of `complete`, `adjust`, or `blocked`.
- When Phase 3 returns `complete`, outputs contain `reports/change-capability-human-plan.md` with human-readable change packets, capability progression, upstream baseline, downstream design constraints, non-goals, and links back to atom ledgers and the global atom index.
- If Phase 4 is invoked, its report states which Phase 3 findings were addressed, which files were updated, which new or changed per-change/capability atom files were written, how duplicate or missing atoms were resolved, and whether targeted adjustment was sufficient.

Do not start `openspec-propose` from this workflow until Phase 3 reports `complete`.
