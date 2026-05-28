---
name: source-aligned-change-plan-coverage
description: Use before openspec propose when the user wants a source-doc-first OpenSpec change/capability plan with obligation atom coverage, source anchor traceability, gap analysis, and a final plan refit where every production-meaningful source obligation is owned by exactly one change/capability atom or explicitly gap-classified.
---

# Source-Aligned Change Plan Coverage

Create a globally source-aligned OpenSpec change plan before any individual `openspec-propose` change is created. This skill turns full-source documents into a normalized obligation atom index, then derives the final change/capability plan from that stable atom set. An obligation atom is the smallest source-backed production obligation that should survive into later `openspec-propose` artifacts. It may represent a page state, trigger, display rule, primary action, disabled action, recovery path, data fact, auth/privacy rule, failure path, responsive behavior, verification requirement, architecture/runtime dependency, preserve constraint, or explicit non-goal. A contextual atom is a source-backed fact or future obligation that a change must know about to avoid bad design, but does not directly implement or count as current capability advancement. Source anchors and line ranges are trace evidence for atoms; they are not the coverage goal.

The canonical Global Atom ID prefix for this workflow is `GA-####`. Phase 3 must assign normalized global atom IDs such as `GA-0001`, and Phase 4, Phase 5, plus later `openspec-propose` / `openspec-apply-change` work must preserve those exact `GA-####` IDs from `obligation-atom-index.md`; do not rewrite them to any other global prefix or to source-local atom IDs.

Artifact projection is separate from atom existence and final change ownership. Each atom must carry an artifact projection that says how downstream OpenSpec artifacts consume it: `spec-requirement` for normative user/system behavior, `spec-guard` for preserve or forbidden-drift constraints that specs must not accidentally violate, `design-obligation` for architecture/runtime/data/API/module/provider/deployment shape, `verification-obligation` for proof/evidence strategy, or `contextual-only` for non-direct context. Final direct atoms must use `spec-requirement`, `spec-guard`, `design-obligation`, or `verification-obligation`; `contextual-only` is reserved for non-direct context rows. Phase 2 may record a candidate projection, Phase 3 normalizes it in the global atom index, and Phase 5 finalizes it in change packets. A direct atom must not be forced into specs as a requirement merely because it is direct.

Phase responsibilities:

- Phase 1 creates an initial change/capability framework from a full-source read. It is a slicing hypothesis, not final authority, and must not create obligation atoms, line-range anchors, coverage statuses, or Phase 2 work queues.
- Phase 2 performs source-first atom extraction, Phase 2 aggregation, and reviewer-facing visualization. Each source document has one canonical extraction owner; Phase 2 raw atom files are immutable evidence after the phase completes.
- Phase 3 normalizes coverage into the global atom index, closes semantic gaps, resolves duplicates, assigns normalized artifact projection, and either completes coverage or blocks.
- Phase 4 copies source-window dossiers and writes semantic profiles from Phase 2/3 atom line ranges. It may identify refit pressure, but must not decide final ownership or produce final packets.
- Phase 5 refits the final plan from stable global atoms plus Phase 4 source-window semantics. It may accept or adjust the Phase 1 framework, but every refit decision must preserve atom-level traceability.

Final plan invariants:

- Final changes are implementation units for later `openspec-propose` and `openspec-apply-change`, not only conceptual product loops. Closed-loop coherence is necessary but not sufficient; implementation-ready complexity must pass Phase 5 rules.
- Capability progression labels must be recomputed from final direct atom ownership. Dependency-only, preserve-only, upstream-baseline, downstream-constraint, contextual, evidence-only, and non-goal mentions do not count as capability advancement.
- Non-direct atoms still survive into downstream work. Any atom classified as dependency, contextual, evidence-burden, preserve/reference, later-change, explicit non-goal, or another non-direct relation must be preserved as an explicit `GA-####` row in the owning final change packet's context/evidence/dependency/non-goal handling, unless it has no final owner change and is globally contextual/non-coverage. Non-direct rows must not be lost, truncated, represented only by `atom-plan-mapping.md`, or collapsed into summary rows such as `additional-context`.
- Pre-business foundation is a narrow exception. A final plan may have at most one zero-domain engineering bootstrap before the first production business/user workflow by default; later standalone non-business changes need an independently runnable operational loop.
- Later `openspec-propose` and `openspec-apply-change` work must consume final change packets, not isolated source atom rows. Earlier changes provide realized baseline contracts for later changes, but must not absorb all future global obligations.
- Capability views are direct-advancement views only. They may not contain dependency-only, contextual-only, evidence-burden, preserve/reference, later-change, explicit non-goal, or upstream-baseline rows; those rows belong in final change packets and the full `atom-plan-mapping.md`.

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

Keep the root small and proposal-facing. The proposal-facing root entries are the latest effective plan and the final atom/change packets; `phase-works/` is the single trace container for phase work. Later `openspec-propose` should normally read `change-plan.md` and the relevant `change-capability-anchors/` packet, and only follow `phase-works/` links when it needs trace evidence. All phase working documents, reports, reviews, raw extraction ledgers, and intermediate manifests live under `phase-works/`, with one subdirectory per phase.

```text
openspec/orchestrate/
├── change-plan.md                         # latest effective plan for openspec-propose
├── change-capability-anchors/
│   ├── index.md                           # final index of change packets
│   ├── obligation-atom-index.md            # normalized global atom registry
│   └── <change-slug>/
│       ├── <change-slug>.md                # final change packet derived from global atoms
│       └── capability-anchors/
│           └── <capability-slug>.md        # direct-atom capability view scoped to this change
└── phase-works/
    ├── phase-1/
    │   ├── change-plan.md                  # Phase 1 snapshot; root change-plan.md is the promoted latest copy
    │   ├── source-doc-manifest.md
    │   └── phase-1-agent-report.md
    ├── phase-2/
    │   ├── source-obligation-atoms/
    │   │   ├── index.md                    # Phase 2 index/report subagent summary
    │   │   ├── work-queue.md               # lightweight batching plan; not coverage evidence
    │   │   └── <source-relative-path>.atoms.md
    │   ├── source-obligation-review/
    │   │   └── index.html                  # static human review app for source lines and atom annotations
    │   └── phase-2-agent-report.md
    ├── phase-3/
    │   ├── source-doc-manifest.md          # enriched Phase 3 review copy
    │   ├── source-doc-coverage/
    │   │   └── <source-relative-path>.coverage.md
    │   ├── phase-3-trace/
    │   │   ├── source-to-global-atom-map.md
    │   │   ├── source-remainder-review.md
    │   │   ├── duplicate-ownership-review.md
    │   │   └── atom-normalization-decision-log.md
    │   ├── coverage-review-app/
    │   │   └── index.html                  # static human review app for Phase 3 normalization and risks
    │   ├── coverage-review.md
    │   └── phase-3-agent-report.md
    ├── phase-4/
    │   ├── input-change-plan.md
    │   ├── source-window-dossiers/
    │   │   ├── index.md                   # source-window dossier index for human review and refit grounding
    │   │   ├── by-input-change/
    │   │   │   └── <input-change-slug>.md # original source windows grouped by initial change
    │   │   └── by-input-capability/
    │   │       └── <input-capability-slug>.md # original source windows grouped by initial capability
    │   ├── source-window-semantic-profile-review.md
    │   ├── source-window-grounding-issues.md
    │   └── phase-4-agent-report.md
    └── phase-5/
        ├── input-change-plan.md
        ├── source-window-refit-trace.md
        ├── change-plan.md                  # Phase 5 snapshot; promoted to root after accepted/adjusted
        ├── atom-plan-mapping.md
        ├── capability-progression-review.md
        ├── change-complexity-review.md
        ├── plan-refit-decision-log.md
        ├── change-plan-adjustments.md      # only when Phase 5 adjusts, needs recheck, or blocks
        ├── phase-5-agent-report.md
        ├── change-capability-human-plan.md # final human reading aid, not source of truth
        └── alignment-final-report.md
```

Use single-level filenames under `phase-works/phase-2/source-obligation-atoms/` and `phase-works/phase-3/source-doc-coverage/`: derive the name from the source document path, remove the extension, replace path separators with `--`, and add `.atoms.md` or `.coverage.md`.

Do not create `pass-*`, `iteration-*`, or similarly numbered Phase 4 or Phase 5 subdirectories. Phase 4 writes one current source-window grounding packet directly under `phase-works/phase-4/`. Phase 5 writes one current refit packet directly under `phase-works/phase-5/`. If Phase 4 or Phase 5 returns `needs-coverage-recheck`, the fresh Phase 3, Phase 4, and Phase 5 runs update the current phase work directories; introduce archival history only if the user explicitly asks for it.

Optional bundled helper:

```text
.codex/skills/source-aligned-change-plan-coverage/scripts/
├── phase2_obligation_review_app.py # mechanical Phase 2 static review app generator
├── phase3_coverage_review_app.py # mechanical Phase 3 static review app generator
├── phase3_line_range_audit.py   # mechanical Phase 3 candidate uncovered/overlap helper
└── phase5_plan_refit.py         # mechanical Phase 5 renderer/checker from reviewed mapping + JSON config
```

## Artifact Authority

- Phase 2 source atom files are immutable raw extraction evidence.
- Phase 3's `change-capability-anchors/obligation-atom-index.md` is the normalized global uniqueness and ownership registry promoted to the proposal-facing root.
- `phase-works/phase-4/source-window-dossiers/` is copied source-window review evidence, not a new extraction pass or source of truth replacement.
- Phase 5 derives final change packets and capability views from the global index and Phase 4 source-window semantic profiles; it must not invent atoms without source evidence.
- Final change packets are the proposal-facing source of truth for both direct scope and non-direct constraints. If a non-direct atom has a final owner change in `atom-plan-mapping.md`, the corresponding final change packet must list that atom explicitly by `GA-####` in the context/dependency/evidence/preserve/non-goal table; a packet may split this into multiple relation-specific tables, but it must not replace explicit atom rows with a count, summary, or link-only placeholder.
- Final capability views are derived direct-scope views, not complete implementation packets. Later `openspec-propose` must not use a capability view alone to determine scope because non-direct constraints are intentionally excluded from capability advancement.
- `phase-works/phase-5/change-capability-human-plan.md` is a human-facing synthesis, not a replacement for source-window dossiers, source atom ledgers, the global atom index, or final change packets.

## Reference Files

Read these references only when entering the matching phase:

- Phase 1 initial plan: `references/phase-1-initial-change-plan.md`
- Phase 2 source-first atom extraction: `references/phase-2-source-anchor-coverage.md`
- Phase 3 coverage normalization: `references/phase-3-coverage-review-iteration.md`
- Phase 4 source-window grounding: `references/phase-4-source-window-grounding.md`
- Phase 5 plan refit: `references/phase-5-targeted-plan-adjustment.md`

## Subagent Rule

This workflow is subagent-based.

- Subagent topology is single-level. Only the main orchestrating agent may spawn phase subagents. A phase subagent is a leaf worker: once it has been started for Phase 1, Phase 2 extraction, Phase 2 index/report, Phase 3, Phase 4, or Phase 5, it must perform its assigned phase work directly and must not spawn, invoke, or delegate to any additional AI subagent, `codex exec`, multi-agent worker, nested workflow agent, or child process whose purpose is agentic reasoning.
- Instructions in this skill or phase references that say to spawn a fresh subagent are instructions for the main orchestrating agent only. When a phase subagent reads those instructions, it must interpret them as boundary context, not as permission to launch another subagent or advance the workflow itself.
- Phase 1: use a fresh independent subagent for full-source initial change/capability framework generation.
- Phase 2: build the lightweight work queue first, then use fresh source-extraction subagents partitioned by source document or source-document batch. Each source document must have one canonical Phase 2 extraction owner. After extraction, use a fresh Phase 2 index/report subagent, then generate the Phase 2 review app. Follow the detailed batching, aggregation, and read-only review-app boundaries in `references/phase-2-source-anchor-coverage.md`; do not spawn one Phase 2 subagent per planned change or ask multiple subagents to independently extract the same source document unless Phase 3 explicitly requests targeted validation.
- Phase 3: use a fresh independent subagent for source coverage normalization, gap audit, duplicate review, and global atom index generation.
- Phase 4: use a fresh independent subagent for source-window dossier generation, input change/capability semantic profiling, grounding issue review, and Phase 5 handoff preparation.
- Phase 5: use a fresh independent subagent for source-window-grounded atom-driven change/capability plan refit, capability progression review, change complexity review, and final change packet generation.
- Every phase subagent prompt must include the Artifact Language Gate or an explicit instruction to follow it, and must explicitly state that the phase subagent is a leaf worker that must not spawn nested subagents or advance to another phase. If the phase reference uses English table headers or field labels, the subagent may keep that structure but must fill explanation content in Simplified Chinese.

If Phase 4 returns `needs-coverage-recheck`, spawn a fresh Phase 3 subagent, then a fresh Phase 4 subagent. If Phase 5 returns `needs-coverage-recheck`, spawn a fresh Phase 3 subagent, then fresh Phase 4 and Phase 5 subagents. Do not rerun Phase 2 unless Phase 3, Phase 4, or Phase 5 reports that targeted review is insufficient and the user explicitly requests a full source extraction rerun.

Using this skill explicitly authorizes its required subagent workflow. Do not ask for additional confirmation solely to spawn the phase subagents. If subagents are unavailable or disallowed by the runtime, stop and report a blocker instead of doing the phase in the main agent.

The main agent only orchestrates, checks interface-level outputs, and starts the next phase. It should not silently redo a phase's content work, and it must not synthesize the Phase 2 aggregate index/report itself when the Phase 2 index/report subagent is available.

## Workflow

1. Create `openspec/orchestrate/`, `change-capability-anchors/`, `phase-works/phase-1/`, `phase-works/phase-2/source-obligation-atoms/`, `phase-works/phase-2/source-obligation-review/`, `phase-works/phase-3/source-doc-coverage/`, `phase-works/phase-3/phase-3-trace/`, `phase-works/phase-3/coverage-review-app/`, `phase-works/phase-4/source-window-dossiers/by-input-change/`, `phase-works/phase-4/source-window-dossiers/by-input-capability/`, and `phase-works/phase-5/`.
2. Phase 1: if there is no current `change-plan.md`, spawn a fresh subagent to enumerate and read every source document, write `phase-works/phase-1/source-doc-manifest.md`, write `phase-works/phase-1/change-plan.md`, promote the latest effective plan to root `change-plan.md`, and generate the initial change/capability framework using the Phase 1 reference.
3. Phase 2: create the lightweight work queue, spawn source-extraction subagents by source document or source-document batch, write one `<source>.atoms.md` file per read-full source document, run the fresh Phase 2 index/report subagent, then generate `phase-works/phase-2/source-obligation-review/index.html` as the deterministic static review app.
4. Phase 3: spawn a fresh subagent to normalize Phase 2 atoms into `change-capability-anchors/obligation-atom-index.md`, audit source remainders, add precise missing atoms to the global index, split broad atoms, resolve duplicates/ambiguous ownership, assign normalized artifact projection, write all per-source coverage files and Phase 3 trace files under `phase-works/phase-3/`, then generate `phase-works/phase-3/coverage-review-app/index.html` as a deterministic static review app for source coverage, source-to-global mapping, risk queue, and global registry review, and decide:
   - `coverage-complete`: every production-meaningful source obligation is represented by exactly one direct global atom or has a justified non-direct/non-coverage status.
   - `blocked`: source docs, atom evidence, ownership boundaries, or conflicts are insufficient for a stable global atom index.
5. Phase 4: after `coverage-complete`, spawn a fresh subagent to generate source-window dossiers and semantic profiles from the stable global atom index and the original source documents. It writes `phase-works/phase-4/source-window-dossiers/` for every input change and input capability by copying the original source windows referenced by Phase 2/3 atoms, then writes `source-window-semantic-profile-review.md`, `source-window-grounding-issues.md`, and `phase-4-agent-report.md`, and ends with:
   - `grounded`: source-window dossiers and semantic profiles are complete enough for Phase 5.
   - `needs-coverage-recheck`: grounding exposed missing/broad/conflicting source obligations that require a fresh Phase 3 pass.
   - `blocked`: source documents, source boundaries, or product decisions are insufficient for safe grounding.
6. Phase 5: after Phase 4 returns `grounded`, spawn a fresh subagent to refit the change/capability plan from the stable global atom index and Phase 4 source-window semantic profiles. It finalizes artifact projection for each direct atom, writes the current `phase-works/phase-5/` refit packet without any pass/iteration subdirectory, updates the latest effective root `change-plan.md` when needed, derives final `change-capability-anchors/<change-slug>/` packets, explicitly carries every owner-scoped non-direct atom into the relevant final change packet, writes Phase 5 trace files under `phase-works/phase-5/`, and ends with:
   - `accepted`: the Phase 1 framework remains coherent after source-window and atom-level review.
   - `adjusted`: the framework was refit and all atom mappings remain traceable.
   - `needs-coverage-recheck`: the refit exposed missing/broad/conflicting source obligations that require a fresh Phase 3 pass.
   - `blocked`: a user decision or broad reanalysis is required.
7. Continue Phase 3 -> Phase 4 -> Phase 5 until Phase 5 returns `accepted`, `adjusted`, or `blocked`, or Phase 4 returns `blocked`.

Do not start `openspec-propose` from this workflow until Phase 5 returns `accepted` or `adjusted` and final change packets exist.

## Main-Agent Gates

After each phase, check only interface facts:

- Required directories and reports exist under `openspec/orchestrate/`.
- Phase reports state the input docs, output files, and blockers.
- Generated artifacts pass the Artifact Language Gate. If a phase output fails only the language gate, treat the phase as interface-incomplete and run a targeted language repair that preserves IDs, paths, enum/status values, line ranges, atom mappings, ownership decisions, and source quotes.
- Phase 1 outputs contain root `change-plan.md`, `phase-works/phase-1/change-plan.md`, `phase-works/phase-1/source-doc-manifest.md`, and `phase-works/phase-1/phase-1-agent-report.md`; the manifest lists every source document under the specified roots with full-read status, or Phase 1 reports a blocker.
- Phase 2 outputs contain `phase-works/phase-2/source-obligation-atoms/work-queue.md`, `phase-works/phase-2/source-obligation-atoms/index.md`, one `phase-works/phase-2/source-obligation-atoms/<source>.atoms.md` file for every source document listed as `read-full`, `phase-works/phase-2/source-obligation-review/index.html`, and `phase-works/phase-2/phase-2-agent-report.md`.
- Phase 2 reports include the Phase 2 index/report subagent identity/status, a work queue summary, and a source-extraction trace showing every manifest source document was assigned exactly one canonical extraction owner, read in full by that owner, atom candidates found, candidate artifact projections recorded, source remainders recorded, candidate ownership mappings, unassigned atoms, gaps, duplicate-risk notes, and blockers.
- The Phase 2 review app is self-contained or otherwise directly openable from disk, includes every manifest `read-full` source document, renders source paths as a document tree, renders original source content with line numbers, and renders annotation cards or margin notes for every parsed obligation atom row with `Source Atom ID`, `Lines`, `Atom Type`, candidate status/projection/owner fields, and `Source Fact` as the reviewer-facing summary.
- Phase 3 outputs contain `change-capability-anchors/obligation-atom-index.md`, `phase-works/phase-3/source-doc-manifest.md`, one `phase-works/phase-3/source-doc-coverage/<source>.coverage.md` file for every source document listed in the manifest, all `phase-works/phase-3/phase-3-trace/*.md` files, `phase-works/phase-3/coverage-review-app/index.html`, `phase-works/phase-3/coverage-review.md`, and `phase-works/phase-3/phase-3-agent-report.md`.
- The Phase 3 review app is self-contained or otherwise directly openable from disk, includes every Phase 3 source document, renders original source content with line numbers and effective `GA-####` annotations, includes source-to-global mapping filters, a risk queue for duplicate/broad/ownership/Phase 5 refit handoff items, and a searchable global atom registry. The app is only a review aid and must not replace `obligation-atom-index.md`, per-source coverage files, trace files, or `coverage-review.md` as source of truth.
- Every Phase 3 global atom ID in `obligation-atom-index.md` must match `GA-####`; no alternate global prefix or source-local ID may be used as a `Global Atom ID`.
- Phase 3 reports include per-source-document obligation coverage summaries, normalized global atom synthesis, normalized artifact projection distribution, missing atom findings, duplicate/ownership resolutions, broad-atom split decisions, non-coverage classifications, and source-backed obligations not mapped to any change or capability.
- Phase 3 outputs contain `Decision: coverage-complete` or `Decision: blocked`.
- Phase 4 outputs contain the current `phase-works/phase-4/` grounding packet, including `input-change-plan.md`, `source-window-dossiers/index.md`, source-window dossier files for every input change and input capability with atom-backed source windows, `source-window-semantic-profile-review.md`, `source-window-grounding-issues.md`, and `phase-4-agent-report.md`.
- Phase 4 reports state whether source-window grounding completed, which input changes/capabilities were covered, which atom-backed source windows were copied, which source semantics create Phase 5 refit pressure, whether grounding issues remain, and whether a Phase 3 recheck is required.
- Phase 4 must not write final change packets, final capability views, `atom-plan-mapping.md`, final `change-plan.md`, or root `openspec/orchestrate/change-plan.md`.
- Phase 5 outputs contain the current `phase-works/phase-5/` refit packet, including `input-change-plan.md`, `source-window-refit-trace.md`, `change-plan.md`, `atom-plan-mapping.md`, `capability-progression-review.md`, `change-complexity-review.md`, `plan-refit-decision-log.md`, `phase-5-agent-report.md`, and `alignment-final-report.md`; when the status is `accepted` or `adjusted`, they also contain final `change-capability-anchors/index.md`, final per-change packets, final capability views, and `phase-works/phase-5/change-capability-human-plan.md`.
- Phase 5 reports state whether the initial plan was accepted or adjusted, which Phase 4 source-window semantic profiles and atom groups drove plan changes, how artifact projection was finalized, how capability progression was evaluated, how implementation-ready change complexity was evaluated, how the change/capability coupling audit was evaluated, which over-budget triggers were split/deferred/blocked, which atoms moved or changed status/projection, and whether a Phase 3 recheck is required.
- Phase 5 refit decisions cite Phase 4 source-window dossier evidence when changing, splitting, merging, reordering, or renaming changes/capabilities. A decision justified only by atom count, capability count, or terse atom summaries fails the gate unless the relevant source windows are explicitly cited as not adding further semantic distinction.
- Every Phase 5 final change must pass the Source Window Semantic Grounding Gate: cite source windows, summarize their combined business/system semantics, explain why the atoms belong together, justify roadmap order, state a manual acceptance scenario, and explain all contextual/dependency/evidence/non-goal handling before atom ownership is finalized.
- Final change packets contain direct owning atoms, final artifact projection, contextual atoms, upstream realized baseline, downstream constraints, non-goals, evidence burden, and links back to the global atom index and source atom files.
- Every non-direct atom row in `atom-plan-mapping.md` whose `Final Owner Change` is a real final change must appear explicitly by `GA-####` in that change's final packet context/dependency/evidence/preserve/non-goal handling. No final packet may replace owner-scoped non-direct atoms with only a count, summary row, `additional-context`, or a link back to the mapping.
- Final packets, capability views, Phase 5 mapping, and root `change-plan.md` preserve `GA-####` IDs, direct atom projection, unique direct ownership, and non-`contextual-only` direct rows.
- Final capability advancement surfaces agree: Capability Map `First change`, progression matrix, roadmap `New`/`Modified`, final packets, `change-capability-anchors/index.md`, capability views, and human plan. Non-direct relations must not appear as capability advancement.
- Final capability view files exist exactly for direct capabilities advanced by each change. They must include all and only direct atoms for that change/capability pair; dependency-only, contextual-only, evidence-burden, preserve/reference, later-change, explicit non-goal, and upstream-baseline atoms must stay out of capability views and remain explicit in the final change packet.
- Phase 5's final consistency checks must verify packet-level non-direct coverage: for every `atom-plan-mapping.md` row with a non-direct relation and real `Final Owner Change`, the corresponding final change packet contains that exact `GA-####` row; for every capability view, every row is direct and has a matching direct row in the final change packet.
- Phase 5 complexity, source-window grounding, capability-coupling, and foundation/business-first gates pass according to `references/phase-5-targeted-plan-adjustment.md`, or Phase 5 records a blocker or explicit source-backed exception where that reference allows one.
- No `openspec-propose` run starts before Phase 5 reaches `accepted` or `adjusted`.
