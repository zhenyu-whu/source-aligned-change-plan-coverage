# Phase 3: Source Document Obligation Coverage and Uniqueness Review

Phase 3 consumes the independent per-change, per-source-document obligation atom analyses from Phase 2 and audits them globally by source document, change, and capability. Phase 2 subagents are intentionally independent across changes, so local atom ids, anchor names, and line ranges for the same source fact may differ across changes. Phase 3 resolves that independence into a global obligation atom index and a framework-level assessment of whether the initial change/capability plan is still scientifically coherent.

Phase 3 is not a new propose-writing pass and must not invent production requirements without source evidence. Its job is to answer:

1. Does every production-meaningful source obligation have an atom?
2. Is every direct atom owned by exactly one change and one capability?
3. Are repeated atoms truly preserve/dependency/context, or are changes duplicating scope?
4. Did any broad anchor compress UI/flow obligations that must be split?
5. Does each capability's atom sequence progress in a reasonable order across changes?
6. Is each change's atom load, capability span, evidence burden, and implementation surface small enough to be reviewable?
7. Are all source ranges without atoms genuinely non-production, reference-only, formatting, background, or otherwise safe to ignore?

Source anchors and line ranges remain useful for navigation and mechanical checks, but semantic obligation coverage, capability progression coherence, and change complexity are the quality gates.

## Inputs

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/source-doc-manifest.md` from Phase 1.
- User-specified source document roots or exact source paths, for manifest verification and targeted semantic reads.
- `openspec/orchestrate/change-capability-anchors/<change-slug>/<change-slug>.md` canonical per-change obligation atom files.
- `openspec/orchestrate/change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` derived per-change/per-capability atom files.
- `openspec/orchestrate/reports/phase-2-agent-report.md`
- If Phase 4 has already run, the latest `openspec/orchestrate/phase-4-adjustments/pass-<NN>/phase-4-adjustment-index.md`, adjusted `change-plan.md` snapshot, adjusted atom file copies, and `phase-2-agent-report-addendum.md`. Apply this latest adjustment packet conceptually to the immutable Phase 2 outputs to form the effective artifact set for review.
- Optional mechanical helper: `.codex/skills/source-aligned-change-plan-coverage/scripts/phase3_line_range_audit.py`

## Outputs

Write current copies only:

- `openspec/orchestrate/source-doc-manifest.md`
- `openspec/orchestrate/source-doc-coverage/<source-relative-path-without-extension>.coverage.md` for every source document listed in the manifest
- `openspec/orchestrate/change-capability-anchors/index.md`
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`
- `openspec/orchestrate/reviews/phase-3-trace/local-to-global-atom-map.md`
- `openspec/orchestrate/reviews/phase-3-trace/source-remainder-review.md`
- `openspec/orchestrate/reviews/phase-3-trace/duplicate-ownership-review.md`
- `openspec/orchestrate/reviews/phase-3-trace/capability-change-scope-review.md`
- `openspec/orchestrate/reviews/phase-3-trace/adjustment-decision-log.md`
- `openspec/orchestrate/reviews/coverage-review.md`
- `openspec/orchestrate/reviews/change-plan-adjustments.md` only when the decision is `adjust` or `blocked`
- `openspec/orchestrate/reports/phase-3-agent-report.md`
- `openspec/orchestrate/reports/change-capability-human-plan.md` only when the decision is `complete`
- `openspec/orchestrate/reports/alignment-final-report.md` only when the decision is `complete`

Use a single-level filename for per-source files. Derive it from the source document path as listed in the manifest, remove the file extension, and replace path separators with `--`. Do not create nested directories under `source-doc-coverage/`.

Phase 3 proposes adjustments in `reviews/change-plan-adjustments.md`; it does not update `change-plan.md` or Phase 2 per-change/capability atom files. Targeted adjustment packets belong to Phase 4, and Phase 4 must not mutate the immutable Phase 2 files.

`reviews/phase-3-trace/` records the current Phase 3 pass's intermediate audit trail. These files are review aids, not source of truth. They must be overwritten on each fresh Phase 3 pass and must be consistent with the final `obligation-atom-index.md`, per-source coverage files, and `coverage-review.md`.

When Phase 3 completes, `reports/change-capability-human-plan.md` is the human-facing synthesis for later `openspec-propose` and `openspec-apply-change` work. It must group atoms into readable change packets and capability progression narratives, while linking back to the effective canonical atom ledgers and global atom index. It is not a source of truth and must not replace atom-level coverage artifacts.

## Global Atom Index

`change-capability-anchors/obligation-atom-index.md` is the global review registry. It does not replace per-change atom ledgers, but it resolves global uniqueness and ownership.

It must include:

| Global Atom ID | Owner Change | Owner Capability | Source Document | Lines | Atom Type | Source Fact | Normativity | Coverage Status | Effective Atom IDs / Origins | Atom Relation | Propose Use | Evidence Need | Review Judgment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Rules:

- Assign exactly one `Global Atom ID` to each direct production obligation.
- If two effective atom rows describe the same source obligation, pick one direct owner and classify the others as preserve/dependency/reference/context. Do not allow two direct current-change atoms for the same obligation.
- If a later change genuinely strengthens or narrows an earlier obligation, create a new atom only for the additional source-backed delta and set `Atom Relation` to `refines:<global-atom-id>` or `modifies:<global-atom-id>`.
- If a source fact only preserves or depends on another change's atom, use `Atom Relation` such as `preserves:<global-atom-id>` or `depends-on:<global-atom-id>` and do not count it as duplicate direct coverage.
- If a source fact is needed only to keep the current design compatible with a later obligation, classify it as contextual future-compatibility and link it to the future or candidate global atom when known. Do not count it as current direct ownership.
- Earlier changes may provide baseline contracts for later changes, but they must not absorb all future global obligations. Later changes should depend on realized baseline atoms and own only source-backed deltas.
- `duplicate` is not a complete rationale unless it names the duplicated `Global Atom ID` and explains semantic equivalence.

## Source Discovery and Reading Boundary

Read the Phase 1 `source-doc-manifest.md`, verify it still matches the user-specified source roots, and enrich it with Phase 3 classifications. If Phase 1 did not list every source document or did not mark source documents as read in full, return `Decision: blocked` unless the issue can be corrected in the same Phase 3 pass without changing the Phase 1 framework. For every manifest row, write a matching per-source review file under `source-doc-coverage/`, even when the final classification is `reference-only`, `intentionally-not-read`, or `non-source-artifact`.

Classify each document as:

- `covered-by-atoms`
- `candidate-missing-atoms`
- `reference-only`
- `intentionally-not-read`
- `non-source-artifact`

Use effective atom rows, Phase 2 source-doc traces, Phase 4 addenda when present, Phase 1 source hints, file path/name, and source-root scope to classify documents first. Read source file contents when one of these is true:

- a source section is likely obligation-bearing and needs atom completeness review
- a candidate uncovered line range must be semantically reviewed
- a document has no effective atoms and may contain meaningful product/system obligations
- a duplicate/ownership conflict is unclear without local context
- a broad anchor appears to cover a page/object/flow section without decomposing its obligations
- path/name/Phase 2 or Phase 4 traces are insufficient to justify a non-source or reference-only classification

For UI, object, flow, interaction, state, fixture, scene, verification, and design-system documents, targeted semantic reading must cover the obligation-bearing sections, not only the lines outside Phase 2 ranges. If this requires broad reading and the source set is too large to safely review, return `Decision: blocked` and explain why Phase 2 or the input source set is insufficient.

Each per-source review file must make the reading boundary explicit. If the document was not read in full, list the ranges that were read and explain why those ranges were sufficient. If the document has no effective atoms and was classified as reference-only or non-source, record the minimum evidence used to justify that classification.

## Audit Workflow

Evaluate the current effective artifact set in this order. If no Phase 4 pass exists, the effective set is the original Phase 2 outputs and root `change-plan.md`. If one or more Phase 4 passes exist, use the latest pass's adjusted plan snapshot and `phase-4-adjustment-index.md` to replace, add, supersede, or remove only the artifacts named by that pass; all unaffected Phase 2 artifacts remain part of the effective set.

1. Confirm every effective planned change has exactly one per-change atom file and one nested capability atom file per planned capability increment.
2. Confirm Phase 2 used a fresh independent subagent for each planned change.
3. Confirm each nested capability atom file is a derived view of its change's canonical atom ledger:
   - every capability row has a matching canonical atom row in the same change file
   - every canonical atom row that directly names a planned capability appears in that capability file
   - capability files do not introduce independent atom ids, changed source documents, changed line ranges, changed source facts, or changed primary coverage statuses
4. Build `change-capability-anchors/index.md` from the effective per-change directories and record whether each file came from the immutable Phase 2 output or the latest Phase 4 adjustment packet.
5. Extract every effective canonical atom row with its source document, local atom id, line range, atom type, source fact, normativity, coverage status, change, owner capability, roles, rationale, propose use, evidence need, and artifact origin.
6. Read nested capability atom files only to verify derived-view consistency and evaluate capability boundaries. Do not count nested capability rows as additional coverage when they duplicate canonical change atoms.
7. Optionally run `scripts/phase3_line_range_audit.py` to mechanically parse source anchors, normalize line ranges, merge ranges, list candidate uncovered intervals, list overlaps, and flag malformed rows or non-canonical line-range formatting warnings. Include a short summary of helper findings in the Phase 3 report if used.
8. Verify effective per-change full-source discipline: every effective per-change file must have one per-source extraction ledger row for every Phase 1 manifest source document, unless a Phase 4 adjustment index explicitly removes that change from the effective plan. Missing per-source rows are blockers or adjustment findings.
9. Build a semantic duplicate/ownership review across extracted atoms. Same source document/range, equivalent source facts, equivalent state/action/verification obligations, or identical propose use across changes are duplicate candidates until reviewed.
10. Build `change-capability-anchors/obligation-atom-index.md` with one global direct owner per production obligation.
11. Write `reviews/phase-3-trace/local-to-global-atom-map.md`, mapping every extracted effective canonical atom/context row to exactly one global atom id, relation, non-direct status, or blocker.
12. Write `reviews/phase-3-trace/duplicate-ownership-review.md`, preserving every duplicate/overlap/broad-anchor candidate considered and its unique-owner, relation, non-coverage, adjust, or blocked decision.
13. For each source document in the manifest, create or update the matching `source-doc-coverage/<source-relative-path-without-extension>.coverage.md` file before writing the final global review.
14. For each source document, inspect obligation-bearing sections and verify atom completeness:
    - For pages/objects: page role, route, entry, exit, layout constraints with behavior impact, every named state, state triggers, display, primary actions, disabled actions, recovery, interaction rules, object dependencies, action labels that define behavior, acceptance criteria, responsive behavior, and non-goals.
    - For flow/state/system docs: lifecycle stages, allowed transitions, overlay/blocking rules, fixture fields, scene ids, verification matrix rows, interaction outcomes, and preserve boundaries.
    - For architecture/product docs: data facts, auth/privacy rules, runtime/deployment requirements, worker/job rules, provider boundaries, failure/recovery rules, observability/audit rules, and verification requirements.
15. Identify source ranges outside every effective atom or source anchor range. Read those candidate ranges plus necessary local context and classify them:
    - ignore blank lines, table separators, decorative separators, generated table-of-contents lines, and pure formatting
    - ignore background prose, repeated summaries, discarded options, and purely explanatory text unless it defines a production behavior, boundary, data fact, verification obligation, deployment requirement, auth/privacy rule, failure path, or preserve constraint
    - record each remaining meaningful uncovered source obligation as a missing atom finding
16. Write `reviews/phase-3-trace/source-remainder-review.md`, listing every candidate remaining source range reviewed, how it was discovered, read scope, semantic classification, whether it contains a production obligation, and the resulting atom/status/finding.
17. Detect broad-anchor compression: a Phase 2 row covers a line range containing multiple mandatory UI/flow/data/verification obligations, but the atom ledger only records a summary. Record each missing atom separately.
18. Detect cross-change and cross-capability overlaps by intersecting atom and anchor line ranges. List overlaps when ranges intersect or one range contains another; preserve all participating original atom ids and anchor names.
19. Explain each overlap as one of: valid shared source context, dependency/preserve evidence, same user/system loop split across changes, duplicate direct atom, conflicting ownership, broad anchor range, or unclear.
20. Build a capability atom progression review. For each capability, order its global atoms by planned change order and classify each atom as baseline, refinement, hardening, extension, preserve/dependency, or misplaced repeat. Flag atoms that appear before prerequisites, repeat without delta, skip necessary failure/verification boundaries, or stretch a capability beyond its behavior boundary.
21. Build a change complexity review. For each change, count direct atoms, involved capabilities, source documents touched, entry/fact/projection/failure/verification surfaces, expected evidence types, UI states, worker/API/data surfaces, and cross-cutting concerns. Flag changes whose atom load or surface area suggests the implementation would be too complex to review and archive safely.
22. Write `reviews/phase-3-trace/capability-change-scope-review.md`, recording the capability progression review, change complexity review, and any capability-boundary or slicing candidates considered.
23. Build a downstream change packet review. For each change, group direct atoms by capability, list contextual atoms that affect current design, name upstream realized baseline atoms from earlier changes, name downstream constraints that must not be designed out, list non-goals, and link to the effective canonical ledger and global atom ids.
24. Build an exhaustive adjustment ledger for every missing atom, duplicate direct atom, ambiguous ownership, broad-anchor compression finding, blocking capability-view inconsistency, problematic overlap, capability progression issue, change packet gap, or change complexity issue. Do not summarize with `+N more`; each required adjustment needs its own finding id.
25. Write `reviews/phase-3-trace/adjustment-decision-log.md`, preserving all candidate findings considered, the decision for each, whether it became a Phase 4 finding, and the evidence linking it to final `coverage-review.md` or `change-plan-adjustments.md`.
26. Build compact global statistics across source documents, global atoms, changes, capabilities, meaningful missing atoms, duplicate findings, capability progression findings, change complexity findings, change packet gaps, covered non-atom ranges, overlap findings, gaps, and conflicts.
27. Decide whether the current change plan is coherent, needs targeted Phase 4 adjustment, or is blocked.

## Required Tables

`source-doc-manifest.md` must include:

| Source Document | Classification | Review File | Effective Atom Ranges | Missing Obligation Atom Ranges | Non-Atom Ranges | Read Scope | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

Each `source-doc-coverage/<source-relative-path-without-extension>.coverage.md` file must include:

### Source Document

- Source document path
- Classification
- Total lines, if known
- Whether the file was read fully or targeted ranges only

### Effective Atom Coverage

| Change | Local Atom ID | Lines | Atom Type | Coverage Status | Owner Capability | Roles | Source Fact |
| --- | --- | --- | --- | --- | --- | --- | --- |

### Source Obligation Coverage

| Source Section or Range | Expected Atom Type | Global Atom IDs | Owner Changes | Owner Capabilities | Coverage Judgment | Reason |
| --- | --- | --- | --- | --- | --- | --- |

### Non-Atom Range Review

| Candidate Range | Read Scope | Semantic Classification | Production Obligation? | Reason |
| --- | --- | --- | --- | --- |

### Duplicate and Ownership Review

| Source Ranges or Atoms | Candidate Duplicate/Conflict | Resolution | Global Atom ID or Relation | Review Judgment |
| --- | --- | --- | --- | --- |

### Overlap Review

| Overlap Lines | Participating Atoms or Anchors | Changes | Overlap Reason | Review Judgment |
| --- | --- | --- | --- | --- |

### Document Judgment

- Missing obligation atoms, or `None`
- Duplicate direct atoms, or `None`
- Broad-anchor compression findings, or `None`
- Non-coverage statuses used
- Required Phase 4 findings, or `None`
- Judgment: `covered`, `covered-by-classification`, `adjust`, or `blocked`

`change-capability-anchors/index.md` must include:

| Change | Change Directory | Source Atom File | Capability Atom Files | Source Documents Read In Phase 2 | Direct Atoms | Contextual Atoms | Anchors | Capability Atom Gaps | Duplicate Risks | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

`reviews/phase-3-trace/local-to-global-atom-map.md` must include one row for every effective canonical atom/context row:

| Change | Local Atom ID | Source Document | Lines | Local Capability | Local Coverage Status | Global Atom ID or Relation | Global Owner Change | Global Owner Capability | Review Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

`reviews/phase-3-trace/source-remainder-review.md` must include every candidate uncovered or non-atom source range that Phase 3 reviewed:

| Source Document | Candidate Range | How Found | Read Scope | Semantic Classification | Production Obligation? | Atom / Status / Finding | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

`reviews/phase-3-trace/duplicate-ownership-review.md` must include every semantic duplicate, overlap, broad-anchor, or ownership candidate considered:

| Candidate ID | Source Ranges or Local Atoms | Candidate Type | Equivalent Obligation? | Direct Owner Decision | Non-Owner Classification or Relation | Phase 4 Finding | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

`reviews/phase-3-trace/capability-change-scope-review.md` must include a capability progression working table:

| Capability | Atom Family / Boundary | Changes Reviewed | Baseline Owner | Later Delta Owners | Repeats / Dependencies / Context | Progression Decision | Phase 4 Finding |
| --- | --- | --- | --- | --- | --- | --- | --- |

It must also include a change complexity working table:

| Change | Direct Atom Groups | Context Groups | Capabilities Advanced | Evidence Surfaces | Complexity Decision | Phase 4 Finding |
| --- | --- | --- | --- | --- | --- | --- |

`reviews/phase-3-trace/adjustment-decision-log.md` must include every candidate adjustment or blocker considered, including candidates closed as safe:

| Review Item | Finding Class | Input Evidence | Decision | Output Artifact | Phase 4 Needed? | Reason |
| --- | --- | --- | --- | --- | --- | --- |

`coverage-review.md` must include a per-change coverage table:

| Change | Atom Files | Source Documents | Direct Atoms | Contextual Atoms | Capabilities | Atom Gaps | Duplicate Risks | Change Packet Gaps | Review Judgment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

It must include a per-source-document coverage table:

| Source Document | Review File | Atom Coverage Summary | Missing Obligation Atoms | Duplicate/Ownership Findings | Non-Atom Ranges | Read Scope | Review Judgment |
| --- | --- | --- | --- | --- | --- | --- | --- |

It must include a per-capability atom coverage table:

| Capability | Planned Increments | Global Atoms | Changes | Capability Atom Gaps | Duplicate/Boundary Findings | Review Judgment |
| --- | --- | --- | --- | --- | --- | --- |

It must include a capability atom progression table:

| Capability | Change Order | Atom Groups / Deltas | Progression Judgment | Required Adjustment |
| --- | --- | --- | --- | --- |

It must include a change complexity table:

| Change | Direct Atoms | Capabilities Advanced | Source Docs With Direct Atoms | Evidence Burden | Surfaces | Complexity Judgment | Required Adjustment |
| --- | --- | --- | --- | --- | --- | --- | --- |

It must include a source-overlap review table:

| Source Document | Overlap Lines | Participating Atoms or Anchors | Changes | Overlap Reason | Review Judgment |
| --- | --- | --- | --- | --- | --- |

It must include a global statistics table:

| Metric | Value | Evidence | Interpretation |
| --- | --- | --- | --- |

It must include a plan-impact table:

| Finding | Source Ranges or Atoms | Affected Changes | Plan Impact | Required Phase 4 Adjustment |
| --- | --- | --- | --- | --- |

`reviews/change-plan-adjustments.md` must include an exhaustive adjustment ledger when the decision is `adjust` or `blocked`:

| Finding ID | Finding Type | Source Ranges or Atoms | Semantic Reason | Recommended Owner Change | Recommended Owner Capabilities | Required Phase 4 Adjustment Outputs | Closure Criteria |
| --- | --- | --- | --- | --- | --- | --- | --- |

`Finding Type` should be one of `missing-obligation-atom`, `duplicate-direct-atom`, `ambiguous-atom-ownership`, `broad-anchor-compression`, `problematic-overlap`, `capability-view-inconsistency`, `capability-boundary-gap`, `capability-progression-issue`, `change-packet-context-gap`, `change-complexity-issue`, `change-slicing-issue`, or `blocked-decision`. Every ledger row must be actionable without rereading the whole Phase 3 report.

When the decision is `complete`, `reports/change-capability-human-plan.md` must include readable change packets:

| Change | Closed-loop Outcome | Direct Atom Groups | Contextual Atoms / Future Constraints | Upstream Realized Baseline | Downstream Constraints | Non-Goals | Evidence Burden | Ledger Links |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

It must also include a capability progression narrative:

| Capability | Baseline Change | Refinement / Hardening / Extension Changes | Atom Progression Summary | Human Review Notes |
| --- | --- | --- | --- | --- |

Rules:

- Group atoms into readable atom groups instead of dumping every atom row again.
- Link each group back to the canonical per-change ledger and `obligation-atom-index.md`.
- State which earlier change becomes realized baseline for each later change dependency.
- Include future constraints only when they affect current design; otherwise leave future obligations to their owning later change.
- Keep this document human-facing. Do not use it as coverage source of truth.

## Review Questions

Evaluate:

1. Does every planned change have one independent per-change atom file and one nested capability atom file per planned capability increment?
2. Is every nested capability file a derived view of the same change's canonical atom ledger?
3. Is every source document under the specified roots listed in `source-doc-manifest.md` with a justified classification?
4. What production-meaningful obligation atoms exist in each source document?
5. Does each source obligation have exactly one direct owner change and owner capability?
6. Are any direct atoms duplicated across changes or capabilities?
7. Are later changes adding a source-backed delta, or merely repeating an earlier atom?
8. Which source ranges are non-semantic or safe to ignore, and why?
9. Did any broad source anchor compress page states, actions, disabled actions, recovery, responsive behavior, acceptance criteria, data facts, failure paths, or verification requirements?
10. Does every durable behavior boundary map to a capability?
11. Are any planned capability increments missing, overstated, or assigned to the wrong change?
12. Are any change scopes too broad because they merge independently verifiable loops?
13. Are any change scopes too narrow because they omit a source-backed failure, verification, data, auth, privacy, deployment, responsive, or preserve boundary?
14. Are any capabilities technical modules instead of long-lived behavior boundaries?
15. Are there unresolved conflicts that block a coherent change plan?
16. For each capability, do its atoms advance in a coherent sequence from baseline to refinement/hardening/extension?
17. Are any later-change atoms repeating an earlier atom without a source-backed delta?
18. Does any change advance too many capability atom groups, touch too many surfaces, or require too many evidence types to remain reviewable?
19. Does each later change rely on earlier realized baseline atoms instead of restating them as direct ownership?
20. Does each change packet include the contextual future constraints needed to avoid bad current design, without pulling future scope into the change?
21. Should any change be split, merged, reordered, or narrowed before `openspec-propose` starts?

## Adjustment Recommendation Rules

Phase 3 recommends plan changes only when global source-document obligation evidence requires it. It writes recommendations to `reviews/change-plan-adjustments.md` and returns `Decision: adjust`. Phase 3 must not directly edit `change-plan.md` or Phase 2 per-change/capability atom files.

Recommend adding or splitting a change only when missing atoms or problematic overlaps reveal a source-backed user/system loop with its own entry, fact, projection, failure path, and verification surface.

Recommend adding or renaming a capability only when missing atoms or duplicate/ownership analysis reveal a durable behavior boundary that is not represented by the current capability map.

Recommend attaching a source atom to an existing change only if that change's scope already owns the same user/system loop in the plan. The ledger must name the original or effective canonical change file, the derived capability files involved, and the Phase 4 adjustment packet outputs that should carry the adjusted copies.

Recommend reordering or splitting capability increments when atom progression shows a later change depends on atoms not yet introduced, repeats prior atoms without delta, or mixes baseline, refinement, hardening, and extension in a way that would make propose artifacts ambiguous.

Recommend splitting a change when the complexity review shows the change has multiple independently verifiable atom groups, too many direct capability advances, too many source/UI/data/worker surfaces, or an evidence burden too large for a focused reviewable implementation.

Recommend targeted Phase 4 adjustment when a change packet lacks necessary upstream baseline context, downstream design constraints, or non-goal exclusions needed for later `openspec-propose` to produce coherent artifacts.

Recommend classifying a range as non-atom content only if the non-coverage rationale is source-backed and production-safe.

Do not recommend changes for background prose, repeated summaries, discarded options, pure implementation details, or prototype demo mechanics unless they define a production behavior, boundary, or verification obligation.

If a gap requires broad reanalysis rather than targeted use of Phase 3 source-range findings, return `Decision: blocked` and state that a full Phase 2 rerun would be required only after user confirmation.

## Decision Values

`coverage-review.md` must end with exactly one decision:

- `Decision: complete`
- `Decision: adjust`
- `Decision: blocked`

Use `complete` only when every planned change has a per-change atom file and one nested capability atom file per planned capability increment, all nested capability files are consistent derived views of their canonical change files, every source document under the specified roots is manifest-classified, every production-meaningful source obligation has exactly one direct global atom or justified non-coverage status, every source range without atoms is classified as production-safe non-atom content, there are no unclassified atoms, no unresolved duplicate-direct atoms, no broad-anchor compression findings, no blocking conflicts, every planned capability increment is source-backed or has a justified gap rationale, every capability's atom sequence is coherent across changes, every change's atom load and evidence burden is reviewably scoped, every adjustment ledger item is closed or non-blocking, and cross-change overlaps are explained as valid sharing or explicitly non-blocking.

Additionally, use `complete` only when every source document listed in `source-doc-manifest.md` has a matching `source-doc-coverage/<source-relative-path-without-extension>.coverage.md` file with document-specific atom coverage, non-atom range classifications, duplicate/ownership review, overlap review, and judgment. Missing per-source review files are a Phase 3 artifact blocker and require `Decision: blocked` unless they can be produced in the same Phase 3 pass.

Also use `complete` only when all five `reviews/phase-3-trace/` files exist and reconcile with the final review: every local canonical row in `local-to-global-atom-map.md` appears in `obligation-atom-index.md` or has a justified non-direct relation, every candidate range in `source-remainder-review.md` has a semantic classification, every duplicate/overlap candidate in `duplicate-ownership-review.md` has a resolution, every capability/change scope candidate in `capability-change-scope-review.md` has a judgment, and every candidate finding in `adjustment-decision-log.md` is closed, classified, or handed to Phase 4.

Use `adjust` when meaningful source obligations are not represented by atoms, direct atoms are duplicated, ownership is ambiguous, broad anchors compress obligations, overlap shows duplicated or distorted scope, capability boundaries need targeted edits, capability atom progression is incoherent, a change is too complex or badly sliced, or the effective artifact set needs focused Phase 4 adjustment outputs. Phase 4 must run next, using the exhaustive adjustment ledger.

Use `blocked` when source documents conflict, source roots are incomplete, the user must decide a boundary before coverage can close, or targeted Phase 4 adjustment is insufficient without a broad Phase 2 rerun.

## Final Report

When complete, `alignment-final-report.md` must summarize:

- planned changes analyzed
- per-change atom files consumed
- per-change capability atom files consumed
- source documents classified
- per-source-document review files written
- Phase 3 trace files written
- global obligation atoms indexed
- source documents covered by atoms
- missing obligation atoms, or confirmation that none remain
- source ranges classified as non-atom content
- duplicate and ownership findings
- cross-change and cross-capability overlap findings
- changes covered
- capabilities covered
- planned capability increments covered or gap-classified
- capability atom progression findings
- change complexity findings
- non-coverage classifications
- conflicts resolved or remaining
- confirmation that every production-meaningful obligation under the specified roots is covered by exactly one direct atom or justified
- confirmation that no raw helper output was used as a gate
- confirmation that any line-range helper output, if used, was treated only as mechanical candidate input
- confirmation that no source atom remains unclassified

The final agent reply should be short and include the decision, changed files, missing atoms, duplicate/ownership findings, overlap findings, remaining blockers, and whether Phase 4 is required.
