---
name: source-aligned-change-plan-coverage
description: Use before openspec propose when the user wants a source-doc-first OpenSpec change/capability plan with obligation atom coverage, source anchor traceability, gap analysis, and a final plan refit where every production-meaningful source obligation is owned by exactly one change/capability atom or explicitly gap-classified.
---

# Source-Aligned Change Plan Coverage

Create a globally source-aligned OpenSpec change plan before any individual `openspec-propose` change is created.

This skill turns full-source documents into a normalized obligation atom index, then derives the final change/capability plan from that stable atom set. An obligation atom is the smallest source-backed production obligation that should survive into later `openspec-propose` artifacts. It may represent a page state, trigger, display rule, primary action, disabled action, recovery path, data fact, auth/privacy rule, failure path, responsive behavior, verification requirement, architecture/runtime dependency, preserve constraint, or explicit non-goal. A contextual atom is a source-backed fact or future obligation that a change must know about to avoid bad design, but does not directly implement or count as current capability advancement. Source anchors and line ranges are trace evidence for atoms; they are not the coverage goal.

Artifact projection is separate from atom existence and final change ownership. Each atom must carry an artifact projection that says how downstream OpenSpec artifacts consume it: `spec-requirement` for normative user/system behavior, `spec-guard` for preserve or forbidden-drift constraints that specs must not accidentally violate, `design-obligation` for architecture/runtime/data/API/module/provider/deployment shape, `verification-obligation` for proof/evidence strategy, or `contextual-only` for non-direct context. Final direct atoms must use `spec-requirement`, `spec-guard`, `design-obligation`, or `verification-obligation`; `contextual-only` is reserved for non-direct context rows. Phase 2 may record a candidate projection, Phase 3 normalizes it in the global atom index, and Phase 4 finalizes it in change packets. A direct atom must not be forced into specs as a requirement merely because it is direct.

Phase 1 creates an initial change/capability framework from a full-source read. That framework is a slicing hypothesis, not the final authority. It may cite coarse source hints for human orientation, but it must not create obligation atoms, pending evidence inventories, line-range anchors, coverage statuses, or Phase 2 work queues.

Phase 2 is source-first obligation atom extraction plus a separate Phase 2 aggregation pass. Each source document is read once for canonical extraction, using the Phase 1 framework only as candidate ownership context. Phase 2 must not run one independent extraction pass per planned change. A source-backed atom may be assigned to a candidate change/capability, left unassigned, marked as candidate-new-change/capability, classified as contextual/non-production/non-goal, and assigned a candidate artifact projection. After source extraction subagents finish, a fresh independent Phase 2 index/report subagent writes the Phase 2 aggregate `source-obligation-atoms/index.md` and `reports/phase-2-agent-report.md` from the raw extraction files. That aggregate is a Phase 2 inventory only, not Phase 3 global deduplication, coverage closure, final ownership judgment, or final projection judgment. The Phase 2 source atom files are immutable raw extraction evidence after the phase completes.

Phase 3 is coverage normalization and gap audit. It consumes the Phase 2 source atom files, reviews remaining source content semantically, adds source-backed missing atoms to the normalized global index when evidence is precise, splits broad atoms, resolves duplicates, assigns normalized artifact projection, and ensures every production-meaningful obligation has one normalized global atom, a justified non-direct/non-coverage status, or an explicit Phase 4 placement handoff. Phase 3 may use deterministic line-range helpers only to find mechanical candidates; semantic review is the gate.

Phase 4 is plan refit from the stable atom set. It evaluates the initial change order, capability progression, dependency graph, artifact projection, and change complexity after the atom granularity is clear. Phase 4 may accept the Phase 1 framework or refactor changes/capabilities by splitting, merging, reordering, renaming, remapping atom ownership, or adjusting final artifact projection. Every refit decision must preserve atom-level traceability: each global atom is mapped to its final change/capability, final artifact projection, contextual status, non-goal, or blocker. Phase 4 must preserve the distinction between implementation units and long-lived behavior boundaries; it must not refit the plan into a diagonal or same-name change/capability matrix merely to satisfy implementation complexity budgets.

Final changes are implementation units for later `openspec-propose` and `openspec-apply-change`, not only conceptual product loops. A final change must be small enough for one AI implementation pass to reason about, implement, verify, and archive without absorbing future behavior. Closed-loop coherence is necessary but not sufficient: a large "one loop" must still be split when it contains independently useful subloops, many direct atom families, broad cross-surface evidence, or functional/domain capabilities that can be deferred without lying about the current outcome. Capability count is a complexity signal only when the involved capability deltas are unrelated or not required for the same truthful loop; it is not a standalone reason to split a cross-cutting loop into artificial one-capability changes. Design-dominated or verification-dominated direct atom groups may belong in design/tasks/proof rather than specs, and final packets must state that projection explicitly.

After Phase 4 changes the change/capability model, capability progression labels must be recomputed from final direct atom ownership rather than inherited from Phase 1. For each capability, the `First change` is the earliest final roadmap change whose packet directly owns at least one non-contextual atom for that capability; that same change must be the first non-empty matrix cell, the first roadmap `New` entry, and the first occurrence in `change-capability-anchors/index.md`. Later direct owners are `Modified` only when they own additional source-backed deltas. Dependency-only, preserve-only, upstream-baseline, downstream-constraint, contextual, evidence-only, or non-goal mentions must not be counted as capability advancement. Phase 4 must repair stale labels or return `needs-coverage-recheck`/`blocked` if final ownership itself is ambiguous.

Phase 4 must treat pre-business foundation as a narrow exception, not a planning style. By default, a final plan may have at most one foundation change before the first production business/user workflow. That foundation may establish the minimum runtime, repository/package boundaries, configuration, migrations, local dependencies, smoke tests, and empty adapter seams required for the first workflow to run. After that point, runtime, async, UI state, object state, design-system, responsive, observability, entitlement, privacy, recovery, and verification capabilities should advance inside the first business change that directly needs them. Phase 4 must not create a sequence of foundation/governance/harness changes that are only validated by internal contracts, specimens, or visual proof before any real business workflow exists. If source evidence appears to require a later standalone system change, Phase 4 must prove it has an independently runnable user/system or operational loop with concrete failure paths and archive-ready evidence; otherwise it must move those atoms into a business change as direct deltas, contextual constraints, or evidence burden.

Later `openspec-propose` and `openspec-apply-change` work must not consume isolated source atom rows alone. A completed workflow provides a change packet for each final change: direct owning atoms with final artifact projection, contextual atoms, capability progression notes, upstream realized baseline from earlier changes, downstream constraints that affect current design, non-goals, and links to the global atom index. Earlier changes provide baseline contracts for later changes, but they must not absorb all future global obligations. Future obligations belong in an earlier change only as contextual or preserve constraints when they affect current data model, API contract, state machine, auth/privacy boundary, worker boundary, persistence format, or verification truthfulness.

## Artifact Language Gate

All artifacts written by this workflow under `openspec/orchestrate/**` must be readable by Chinese reviewers.

- Fixed artifact structure may stay English: headings, table headers, field labels, trace field names, enum/status values, IDs, paths, commands, code/API/DB/package symbols, filenames, module/function/type names, capability ids, change slugs, and exact source-document terms or quotes.
- The exemption above does not apply to agent-authored explanatory content. Sentences, table-cell explanations, reasons, judgments, rationale, notes, proof/evidence descriptions, risk descriptions, split analyses, handoff explanations, and report summaries must be written in Simplified Chinese.
- English instructional wording in this skill or its phase references is not fixed artifact structure. Do not copy those English bullets or prose into generated artifacts as agent-authored content; translate or rewrite them as Chinese reviewer-facing content.
- Technical English can remain as identifiers or noun phrases, but the surrounding semantic sentence must be Chinese. For example, `browser-e2e` is allowed as an evidence type; an evidence explanation must say why that proof is needed in Chinese.
- `Source Phrase` values and exact quotations may preserve the original source wording. Interpretation, `Source Fact`, `Rationale`, `Propose Use`, `Review Judgment`, and similar explanation fields must be Chinese unless the entire value is only a fixed enum, ID, path, command, or exact source term.
- After writing or revising each artifact, the writing agent must perform a language self-check: temporarily ignore backticked IDs/paths/commands/code and fixed enum/status values; any remaining natural-language sentence that is English-dominant fails the gate and must be rewritten before the phase can finish.

## Required Inputs

- Source document roots or exact source document paths.
- Optional existing change plan to refine.

All workflow artifacts belong under `openspec/orchestrate/`.

## Output Layout

Keep only core orchestration artifacts at the root:

```text
openspec/orchestrate/
├── change-plan.md                         # latest effective plan; Phase 1 creates it, Phase 4 may refit it
├── source-doc-manifest.md                 # Phase 1 enumerates and reads; Phase 3 enriches coverage review
├── source-obligation-atoms/
│   ├── index.md                           # Phase 2 index/report subagent summary of per-source extraction files
│   ├── work-queue.md                      # Phase 2A lightweight batching plan; not coverage evidence
│   └── <source-relative-path>.atoms.md     # Phase 2 canonical source-first raw atom extraction
├── source-doc-coverage/
│   └── <source-relative-path>.coverage.md  # Phase 3 per-source-doc semantic coverage audit
├── change-capability-anchors/
│   ├── index.md                           # Phase 4 index of final change packets
│   ├── obligation-atom-index.md            # Phase 3 normalized global atom registry
│   └── <change-slug>/
│       ├── <change-slug>.md                # Phase 4 final change packet derived from global atoms
│       └── capability-anchors/
│           └── <capability-slug>.md        # Phase 4 final capability view scoped to this change
├── phase-4-plan-refit/
│   └── pass-<NN>/
│       ├── input-change-plan.md
│       ├── change-plan.md
│       ├── atom-plan-mapping.md
│       └── phase-4-agent-report.md
├── reviews/
│   ├── phase-3-trace/
│   │   ├── source-to-global-atom-map.md
│   │   ├── source-remainder-review.md
│   │   ├── duplicate-ownership-review.md
│   │   └── atom-normalization-decision-log.md
│   ├── phase-4-trace/
│   │   ├── capability-progression-review.md
│   │   ├── change-complexity-review.md
│   │   └── plan-refit-decision-log.md
│   ├── coverage-review.md
│   └── change-plan-adjustments.md          # only when Phase 4 adjusts, needs recheck, or blocks
└── reports/
    ├── phase-1-agent-report.md
    ├── phase-2-agent-report.md            # Phase 2 index/report subagent report
    ├── phase-3-agent-report.md
    ├── phase-4-agent-report.md
    ├── change-capability-human-plan.md     # final human reading aid, not source of truth
    └── alignment-final-report.md
```

Use single-level filenames under `source-obligation-atoms/` and `source-doc-coverage/`: derive the name from the source document path, remove the extension, replace path separators with `--`, and add `.atoms.md` or `.coverage.md`.

Optional bundled helper:

```text
.codex/skills/source-aligned-change-plan-coverage/scripts/
└── phase3_line_range_audit.py   # mechanical Phase 3 candidate uncovered/overlap helper
```

Phase 2 source atom files are immutable raw extraction evidence. Phase 3's `change-capability-anchors/obligation-atom-index.md` is the normalized global uniqueness and ownership registry. Phase 4 derives final change packets and capability views from that global index; it must not invent atoms without source evidence. `reports/change-capability-human-plan.md` is a human-facing synthesis of the final change packets and capability progression; it must not replace the source atom ledgers or global atom index as source of truth.

## Reference Files

Read these references only when entering the matching phase:

- Phase 1 initial plan: `references/phase-1-initial-change-plan.md`
- Phase 2 source-first atom extraction: `references/phase-2-source-anchor-coverage.md`
- Phase 3 coverage normalization: `references/phase-3-coverage-review-iteration.md`
- Phase 4 plan refit: `references/phase-4-targeted-plan-adjustment.md`

## Subagent Rule

This workflow is subagent-based.

- Phase 1: use a fresh independent subagent for full-source initial change/capability framework generation.
- Phase 2: first build a lightweight `source-obligation-atoms/work-queue.md` from the manifest, source roles, paths, document names, and line counts. This overview is only for batching and parallelization; it must not extract atoms, decide coverage, or classify source obligations. Build an initial semantic split, then perform an explicit merge review before spawning extraction subagents. By default, keep Phase 2 extraction batches at or below five total batches unless the source set is genuinely large or context pressure would make merged batches unsafe; document every exception in the work queue. Then use fresh source-extraction subagents partitioned by source document or source-document batch. Each source document must have one canonical Phase 2 extraction owner. After all extraction subagents finish, spawn a fresh independent Phase 2 index/report subagent to read the manifest, work queue, and generated source atom files, then write `source-obligation-atoms/index.md` and `reports/phase-2-agent-report.md`. The index/report subagent must not extract new atoms, edit source atom files, perform global duplicate resolution, decide final ownership, or do Phase 3 coverage closure. Do not spawn one Phase 2 subagent per planned change, and do not ask multiple subagents to independently extract the same source document unless Phase 3 explicitly requests targeted validation.
- Phase 3: use a fresh independent subagent for source coverage normalization, gap audit, duplicate review, and global atom index generation.
- Phase 4: use a fresh independent subagent for atom-driven change/capability plan refit, capability progression review, change complexity review, and final change packet generation.
- Every phase subagent prompt must include the Artifact Language Gate or an explicit instruction to follow it. If the phase reference uses English table headers or field labels, the subagent may keep that structure but must fill explanation content in Simplified Chinese.

If Phase 4 returns `needs-coverage-recheck`, spawn a fresh Phase 3 subagent, then a fresh Phase 4 subagent. Do not rerun Phase 2 unless Phase 3 or Phase 4 reports that targeted review is insufficient and the user explicitly requests a full source extraction rerun.

Using this skill explicitly authorizes its required subagent workflow. Do not ask for additional confirmation solely to spawn the phase subagents. If subagents are unavailable or disallowed by the runtime, stop and report a blocker instead of doing the phase in the main agent.

The main agent only orchestrates, checks interface-level outputs, and starts the next phase. It should not silently redo a phase's content work, and it must not synthesize the Phase 2 aggregate index/report itself when the Phase 2 index/report subagent is available.

## Workflow

1. Create `openspec/orchestrate/`, `source-obligation-atoms/`, `source-doc-coverage/`, `change-capability-anchors/`, `reviews/phase-3-trace/`, `reviews/phase-4-trace/`, and `reports/`.
2. Phase 1: if there is no current `change-plan.md`, spawn a fresh subagent to enumerate and read every source document, write `source-doc-manifest.md`, and generate the initial change/capability framework using the Phase 1 reference.
3. Phase 2: create `source-obligation-atoms/work-queue.md` by lightly surveying the manifest, source roles, paths, document names, and line counts for batching only. Start with a semantic split, then merge compatible small/medium batches so the default extraction queue is no more than five batches unless the source set is genuinely large or context pressure justifies more. Then spawn source-extraction subagents partitioned by source document or source-document batch. Each subagent reads its assigned source document bodies in full, uses the Phase 1 plan only as candidate ownership context, extracts canonical source-backed atom candidates, records candidate artifact projection, records source remainder notes, and writes `source-obligation-atoms/<source>.atoms.md`. After extraction outputs exist, spawn a fresh Phase 2 index/report subagent to aggregate only Phase 2 raw extraction evidence and write `source-obligation-atoms/index.md` and `reports/phase-2-agent-report.md`.
4. Phase 3: spawn a fresh subagent to normalize Phase 2 atoms into `change-capability-anchors/obligation-atom-index.md`, audit source remainders, add precise missing atoms to the global index, split broad atoms, resolve duplicates/ambiguous ownership, assign normalized artifact projection, write all per-source coverage files and Phase 3 trace files, and decide:
   - `coverage-complete`: every production-meaningful source obligation is represented by exactly one direct global atom or has a justified non-direct/non-coverage status.
   - `blocked`: source docs, atom evidence, ownership boundaries, or conflicts are insufficient for a stable global atom index.
5. Phase 4: after `coverage-complete`, spawn a fresh subagent to refit the change/capability plan from the stable global atom index. It finalizes artifact projection for each direct atom, writes the next `phase-4-plan-refit/pass-<NN>/` packet, updates the latest effective `change-plan.md` when needed, derives final `change-capability-anchors/<change-slug>/` packets, writes Phase 4 trace files, and ends with:
   - `accepted`: the Phase 1 framework remains coherent after atom-level review.
   - `adjusted`: the framework was refit and all atom mappings remain traceable.
   - `needs-coverage-recheck`: the refit exposed missing/broad/conflicting source obligations that require a fresh Phase 3 pass.
   - `blocked`: a user decision or broad reanalysis is required.
6. Continue Phase 3 -> Phase 4 until Phase 4 returns `accepted`, `adjusted`, or `blocked`.

Do not start `openspec-propose` from this workflow until Phase 4 returns `accepted` or `adjusted` and final change packets exist.

## Main-Agent Gates

After each phase, check only interface facts:

- Required directories and reports exist under `openspec/orchestrate/`.
- Phase reports state the input docs, output files, and blockers.
- Generated artifacts pass the Artifact Language Gate. If a phase output fails only the language gate, treat the phase as interface-incomplete and run a targeted language repair that preserves IDs, paths, enum/status values, line ranges, atom mappings, ownership decisions, and source quotes.
- Phase 1 outputs contain `change-plan.md`, `source-doc-manifest.md`, and `reports/phase-1-agent-report.md`; the manifest lists every source document under the specified roots with full-read status, or Phase 1 reports a blocker.
- Phase 2 outputs contain `source-obligation-atoms/work-queue.md`, `source-obligation-atoms/index.md`, one `source-obligation-atoms/<source>.atoms.md` file for every source document listed as `read-full`, and `reports/phase-2-agent-report.md`.
- Phase 2 reports include the Phase 2 index/report subagent identity/status, a work queue summary, and a source-extraction trace showing every manifest source document was assigned exactly one canonical extraction owner, read in full by that owner, atom candidates found, candidate artifact projections recorded, source remainders recorded, candidate ownership mappings, unassigned atoms, gaps, duplicate-risk notes, and blockers.
- Phase 3 outputs contain `change-capability-anchors/obligation-atom-index.md`, `source-doc-manifest.md`, one `source-doc-coverage/<source>.coverage.md` file for every source document listed in the manifest, all `reviews/phase-3-trace/*.md` files, `reviews/coverage-review.md`, and `reports/phase-3-agent-report.md`.
- Phase 3 reports include per-source-document obligation coverage summaries, normalized global atom synthesis, normalized artifact projection distribution, missing atom findings, duplicate/ownership resolutions, broad-atom split decisions, non-coverage classifications, and source-backed obligations not mapped to any change or capability.
- Phase 3 outputs contain `Decision: coverage-complete` or `Decision: blocked`.
- Phase 4 outputs contain the latest `phase-4-plan-refit/pass-<NN>/` packet, `reviews/phase-4-trace/*.md`, `reports/phase-4-agent-report.md`, and `reports/alignment-final-report.md`; when the status is `accepted` or `adjusted`, they also contain final `change-capability-anchors/index.md`, final per-change packets, final capability views, and `reports/change-capability-human-plan.md`.
- Phase 4 reports state whether the initial plan was accepted or adjusted, which atom groups drove plan changes, how artifact projection was finalized, how capability progression was evaluated, how implementation-ready change complexity was evaluated, how the change/capability coupling audit was evaluated, which over-budget triggers were split/deferred/blocked, which atoms moved or changed status/projection, and whether a Phase 3 recheck is required.
- Final change packets contain direct owning atoms, final artifact projection, contextual atoms, upstream realized baseline, downstream constraints, non-goals, evidence burden, and links back to the global atom index and source atom files.
- No final direct atom lacks artifact projection; no final direct atom uses `contextual-only`; `design-obligation` and `verification-obligation` atoms must not be treated as `spec-requirement` merely because they are direct.
- No final direct atom is owned by multiple changes/capabilities.
- For every final capability, Capability Map `First change`, the first non-empty progression-matrix cell, the first roadmap `New` entry, the first direct owner in final change packets, the first occurrence in `change-capability-anchors/index.md`, capability views, and `reports/change-capability-human-plan.md` must agree. No capability may be `Modified` before it is `New`.
- No dependency-only, preserve-only, upstream-baseline, downstream-constraint, contextual, evidence-only, or non-goal mention may appear as a capability advancement in final matrix cells, roadmap `New`/`Modified` lists, or final anchor index capabilities.
- No final change exceeds the implementation-ready complexity budget unless Phase 4 records a specific indivisibility rationale, the rejected split options, and why the user must accept or decide the larger unit. A generic "one coherent loop" rationale is not sufficient.
- No final effective plan collapses into a capability-driven one-to-one roadmap. A mostly diagonal matrix, many single-change capabilities, or capability ids that paraphrase change slugs requires an explicit Phase 4 correction or a blocker with concrete source-backed exceptions.
- No pure foundation change directly owns domain behavior that can be deferred to the first feature change needing it; such atoms must be moved to later direct scope or kept only as contextual/preserve constraints.
- No final effective plan contains multiple pre-business foundation/governance changes by default. If any standalone non-business system change remains after the first foundation, Phase 4 must record its independently runnable user/system or operational loop, failure path, evidence burden, and why it cannot be advanced inside the first business workflow that needs it.
- No `openspec-propose` run starts before Phase 4 reaches `accepted` or `adjusted`.
