# Phase 3: Coverage Normalization and Gap Audit

Phase 3 consumes the source-first Phase 2 atom files and produces the normalized global obligation atom index. Its job is to close source coverage and atom identity, not to refit the final change plan. Phase 4 performs plan sequencing and granularity decisions after Phase 3 has made atom granularity stable.

Phase 3 is not a new propose-writing pass and must not invent production requirements without source evidence. It answers:

1. Does every production-meaningful source obligation have an atom?
2. Is each atom small enough, source-backed, and semantically valid?
3. Are broad atoms compressing multiple UI/flow/data/verification obligations?
4. Are repeated atoms true duplicates, refinements, preserve/dependency/context, or conflicts?
5. Can each production obligation be assigned exactly one candidate/final owner change/capability, or does it require Phase 4 refit?
6. Are all source ranges without atoms genuinely non-production, reference-only, formatting, background, or otherwise safe to ignore?
7. Does each atom have the right artifact projection (`spec-requirement`, `spec-guard`, `design-obligation`, `verification-obligation`, or `contextual-only`) based on source semantics?

Source anchors and line ranges remain useful for navigation and mechanical checks, but semantic obligation coverage is the quality gate.

## Inputs

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/work-queue.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/index.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/<source>.atoms.md`
- User-specified source document roots or exact source paths, for manifest verification and targeted semantic reads.
- Optional mechanical helper: `.codex/skills/source-aligned-change-plan-coverage/scripts/phase3_line_range_audit.py`

## Outputs

Write current copies only:

- `openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md`
- `openspec/orchestrate/phase-works/phase-3/source-doc-coverage/<source-relative-path-without-extension>.coverage.md` for every source document listed in the manifest
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/source-to-global-atom-map.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/source-remainder-review.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/duplicate-ownership-review.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/atom-normalization-decision-log.md`
- `openspec/orchestrate/phase-works/phase-3/coverage-review.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-agent-report.md`

Use a single-level filename for per-source files. Derive it from the source document path as listed in the manifest, remove the file extension, replace path separators with `--`, and add `.coverage.md`. Do not create nested directories under `phase-works/phase-3/source-doc-coverage/`.

Phase 3 may add precise missing source-backed atoms to `obligation-atom-index.md`, but it must not edit Phase 2 source atom files. If missing obligations are too broad or require rereading many documents beyond targeted semantic review, return `Decision: blocked` and state whether a full Phase 2 rerun is required.

`phase-works/phase-3/phase-3-trace/` records the current Phase 3 intermediate audit trail. These files are review aids, not source of truth. They must be overwritten on each fresh Phase 3 run and must be consistent with the final `obligation-atom-index.md`, per-source coverage files, and `phase-works/phase-3/coverage-review.md`.

## Artifact Language Gate

Apply the skill-level Artifact Language Gate to every Phase 3 output. Keep fixed table headers, field names, enum/status values, atom ids, paths, line ranges, capability ids, change slugs, relation tokens, and exact source phrases as required, but write all agent-authored explanatory content in Simplified Chinese.

In particular, `Source Fact`, `Review Judgment`, `Reason`, `Interpretation`, semantic classifications that are not fixed enum values, duplicate/ownership resolutions, non-atom range reasons, handoff explanations, metric interpretations, and report summaries must be Chinese unless the entire value is only a fixed enum, ID, path, command, relation token, or exact source term.

After writing each Phase 3 artifact, perform the language self-check from the skill gate. If any explanation sentence remains English-dominant after ignoring IDs, paths, commands, code, fixed enum/status values, relation tokens, and exact source phrases, rewrite it before finishing Phase 3.

## Global Atom Index

`change-capability-anchors/obligation-atom-index.md` is the normalized global review registry. It resolves global uniqueness, artifact projection, candidate/final ownership, source traceability, and non-direct relations.

It must include:

| Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Coverage Status | Artifact Projection | Owner Change | Owner Capability | Source Atom Origins | Atom Relation | Propose Use | Evidence Need | Review Judgment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Rules:

- Assign exactly one `Global Atom ID` to each production obligation.
- If two source atom rows describe the same source obligation, keep one global atom and map the other rows to the same global atom or a non-direct relation.
- If a later obligation genuinely strengthens or narrows an earlier obligation, create a new atom only for the additional source-backed delta and set `Atom Relation` to `refines:<global-atom-id>` or `modifies:<global-atom-id>`.
- If a source fact only preserves or depends on another atom, use `Atom Relation` such as `preserves:<global-atom-id>` or `depends-on:<global-atom-id>` and do not count it as duplicate direct coverage.
- If a source fact is needed only to keep current design compatible with a later obligation, classify it as contextual future-compatibility and link it to the future or candidate global atom when known.
- `Owner Change` and `Owner Capability` may remain `phase-4-refit-required` when coverage is complete but final placement depends on sequencing or granularity decisions. Phase 4 must resolve these before final output.
- `Artifact Projection` must follow source semantics independently from `Coverage Status`: direct architecture/runtime/package/schema/provider/deployment atoms may be `design-obligation`; test strategy, fixture, visual, smoke, and evidence atoms may be `verification-obligation`; preserve and explicit non-goal atoms may be `spec-guard`.
- `contextual-only` is reserved for non-direct context, reference, future-compatibility, or non-coverage rows. If an atom is still a direct candidate or `phase-4-refit-required`, assign `spec-requirement`, `spec-guard`, `design-obligation`, or `verification-obligation`; if no non-context projection is safe, mark the row `blocked` instead of letting a direct atom proceed as `contextual-only`.
- `duplicate` is not a complete rationale unless it names the duplicated `Global Atom ID` and explains semantic equivalence.

Artifact projection values:

- `spec-requirement`
- `spec-guard`
- `design-obligation`
- `verification-obligation`
- `contextual-only`
- `blocked`

Coverage statuses:

- `direct`
- `contextual`
- `preserve-existing`
- `later-change`
- `explicit-non-goal`
- `reference-only`
- `prototype-only-not-production`
- `superseded`
- `no-product-or-system-impact`
- `phase-4-refit-required`
- `unresolved-conflict`
- `blocked`

## Source Discovery and Reading Boundary

Read the Phase 1 `phase-works/phase-1/source-doc-manifest.md`, verify it still matches the user-specified source roots, and write the enriched Phase 3 review copy to `phase-works/phase-3/source-doc-manifest.md`. If Phase 1 did not list every source document or Phase 2 did not write a source atom file for every `read-full` source document, return `Decision: blocked` unless the issue can be corrected through targeted Phase 3 review without invalidating Phase 1 or Phase 2.

For every manifest row, write a matching per-source review file under `phase-works/phase-3/source-doc-coverage/`, even when the final classification is `reference-only`, `intentionally-not-read`, or `non-source-artifact`.

Classify each document as:

- `covered-by-atoms`
- `candidate-missing-atoms`
- `reference-only`
- `intentionally-not-read`
- `non-source-artifact`
- `blocked`

Use Phase 2 source atom files, Phase 2 source remainder notes, Phase 1 source hints, file path/name, source-root scope, and targeted source reads to classify documents. Read source file contents when one of these is true:

- a source section is likely obligation-bearing and needs atom completeness review
- a candidate uncovered line range must be semantically reviewed
- a document has no atom candidates and may contain meaningful product/system obligations
- a duplicate/ownership conflict is unclear without local context
- a broad atom appears to cover a page/object/flow section without decomposing its obligations
- path/name/Phase 2 traces are insufficient to justify a non-source or reference-only classification

For UI, object/component, flow, interaction, state, fixture, scenario, verification, and design-system documents, targeted semantic reading must cover obligation-bearing sections, not only lines outside Phase 2 ranges.

## Audit Workflow

Evaluate in this order:

1. Confirm every `read-full` manifest source document appears exactly once in `phase-works/phase-2/source-obligation-atoms/work-queue.md` and has one canonical extraction owner.
2. Confirm every `read-full` manifest source document has one Phase 2 source atom file.
3. Treat `work-queue.md` only as scheduling trace. Do not use its batching rationale, document name, path, role, or line count as coverage evidence.
4. Extract every Phase 2 atom candidate with source document, source-local atom id, line range, atom type, source fact, normativity, candidate status, candidate artifact projection, candidate owner change/capability, roles, rationale, propose use, evidence need, and artifact origin.
5. Optionally run `scripts/phase3_line_range_audit.py` to mechanically parse source atom anchors, normalize line ranges, merge ranges, list candidate uncovered intervals, list overlaps, and flag malformed rows or non-canonical line-range formatting warnings. Include a short summary if used.
6. Build a semantic duplicate review across extracted atoms. Same source document/range, equivalent source facts, equivalent state/action/verification obligations, or identical propose use are duplicate candidates until reviewed.
7. Split broad atoms when one Phase 2 row covers multiple mandatory UI/flow/data/verification obligations. Each split atom must keep source evidence and a source-local origin or Phase 3 missing-atom finding id.
8. Build `change-capability-anchors/obligation-atom-index.md` with one global atom per production obligation and one normalized artifact projection per global atom.
9. Write `phase-works/phase-3/phase-3-trace/source-to-global-atom-map.md`, mapping every Phase 2 atom/context row to exactly one global atom id, relation, non-direct status, or blocker.
10. Write `phase-works/phase-3/phase-3-trace/duplicate-ownership-review.md`, preserving every duplicate, broad-atom, overlap, and ownership candidate considered and its resolution.
11. For each source document in the manifest, create or update the matching `phase-works/phase-3/source-doc-coverage/<source>.coverage.md` file before writing the final global review.
12. For each source document, inspect obligation-bearing sections and verify atom completeness:
    - For pages/objects: page role, route, entry, exit, layout constraints with behavior impact, every named state, state triggers, display, primary actions, disabled actions, recovery, interaction rules, object dependencies, action labels that define behavior, acceptance criteria, responsive behavior, and non-goals.
    - For flow/state/system docs: lifecycle stages, allowed transitions, overlay/blocking rules, fixture fields, scenario ids, verification matrix rows, interaction outcomes, and preserve boundaries.
    - For architecture/product docs: data facts, access/privacy rules, runtime/deployment requirements, background execution rules, external integration boundaries, failure/recovery rules, observability/audit rules, and verification requirements.
13. Identify source ranges outside every Phase 2 atom or source anchor range. Read those candidate ranges plus necessary local context and classify them:
    - ignore blank lines, table separators, decorative separators, generated table-of-contents lines, and pure formatting
    - ignore background prose, repeated summaries, discarded options, and purely explanatory text unless it defines a production behavior, boundary, data fact, verification obligation, deployment requirement, auth/privacy rule, failure path, or preserve constraint
    - record each remaining meaningful uncovered source obligation as a missing atom and add it to the global index when precise enough
14. Write `phase-works/phase-3/phase-3-trace/source-remainder-review.md`, listing every candidate remaining source range reviewed, how it was discovered, read scope, semantic classification, whether it contains a production obligation, and the resulting atom/status/finding.
15. Identify atoms whose owner change/capability cannot be resolved without plan refit. Mark them `phase-4-refit-required` instead of forcing them into the Phase 1 framework.
16. Write `phase-works/phase-3/phase-3-trace/atom-normalization-decision-log.md`, preserving every candidate finding considered, the decision for each, and whether Phase 4 must resolve final placement.
17. Build compact global statistics across source documents, global atoms, meaningful missing atoms, duplicate findings, broad-atom split findings, non-coverage classifications, ownership ambiguities, gaps, and conflicts.
18. Decide whether coverage normalization is complete or blocked.

## Required Tables

`phase-works/phase-3/source-doc-manifest.md` must include:

| Source Document | Classification | Phase 2 Atom File | Review File | Effective Atom Ranges | Missing Obligation Atom Ranges | Non-Atom Ranges | Read Scope | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

Each `phase-works/phase-3/source-doc-coverage/<source>.coverage.md` file must include:

### Source Document

- Source document path
- Classification
- Total lines, if known
- Whether the file was read fully in Phase 2 and whether Phase 3 performed targeted rereads

### Effective Atom Coverage

| Global Atom ID | Source Atom Origins | Lines | Atom Type | Coverage Status | Artifact Projection | Candidate / Owner Change | Candidate / Owner Capability | Source Fact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

### Source Obligation Coverage

| Source Section or Range | Expected Atom Type | Global Atom IDs | Coverage Judgment | Reason |
| --- | --- | --- | --- | --- |

### Non-Atom Range Review

| Candidate Range | Read Scope | Semantic Classification | Production Obligation? | Reason |
| --- | --- | --- | --- | --- |

### Duplicate and Ownership Review

| Source Ranges or Atoms | Candidate Duplicate/Conflict | Resolution | Global Atom ID or Relation | Review Judgment |
| --- | --- | --- | --- | --- |

### Document Judgment

- Missing obligation atoms, or `None`
- Duplicate direct atoms, or `None`
- Broad-atom split findings, or `None`
- Non-coverage statuses used
- Phase 4 placement findings, or `None`
- Judgment: `covered`, `covered-by-classification`, `phase-4-refit-required`, or `blocked`

`phase-works/phase-3/phase-3-trace/source-to-global-atom-map.md` must include one row for every Phase 2 atom/context row:

| Source Document | Source Atom ID | Lines | Candidate Status | Candidate Artifact Projection | Candidate Owner Change | Candidate Owner Capability | Global Atom ID or Relation | Global Coverage Status | Global Artifact Projection | Review Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

`phase-works/phase-3/phase-3-trace/source-remainder-review.md` must include:

| Source Document | Candidate Range | How Found | Read Scope | Semantic Classification | Production Obligation? | Atom / Status / Finding | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

`phase-works/phase-3/phase-3-trace/duplicate-ownership-review.md` must include:

| Candidate ID | Source Ranges or Source Atoms | Candidate Type | Equivalent Obligation? | Resolution | Global Atom ID or Relation | Phase 4 Placement Needed? | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

`phase-works/phase-3/phase-3-trace/atom-normalization-decision-log.md` must include:

| Review Item | Finding Class | Input Evidence | Decision | Output Artifact | Phase 4 Needed? | Reason |
| --- | --- | --- | --- | --- | --- | --- |

`phase-works/phase-3/coverage-review.md` must include:

| Source Document | Review File | Atom Coverage Summary | Missing Obligation Atoms | Duplicate/Ownership Findings | Non-Atom Ranges | Read Scope | Review Judgment |
| --- | --- | --- | --- | --- | --- | --- | --- |

It must also include:

| Metric | Value | Evidence | Interpretation |
| --- | --- | --- | --- |

And a Phase 4 handoff table:

| Handoff Item | Source Ranges or Atoms | Current Candidate Owners | Current Artifact Projection | Why Phase 4 Must Decide | Required Plan Refit Consideration |
| --- | --- | --- | --- | --- | --- |

## Decision Values

`phase-works/phase-3/coverage-review.md` must end with exactly one decision:

- `Decision: coverage-complete`
- `Decision: blocked`

Use `coverage-complete` only when every source document under the specified roots is manifest-classified, every production-meaningful source obligation has exactly one global atom or justified non-coverage status, every source range without atoms is classified as production-safe non-atom content, there are no unclassified atoms, no unresolved duplicate obligations, no broad atom compression findings left unsplit or justified, no blocking conflicts, and every Phase 4 placement question is explicitly handed off.

Additionally, use `coverage-complete` only when every source document listed in `phase-works/phase-3/source-doc-manifest.md` has a matching `phase-works/phase-3/source-doc-coverage/<source>.coverage.md` file and all four `phase-works/phase-3/phase-3-trace/` files exist and reconcile with the final review.

Use `blocked` when source documents conflict, source roots are incomplete, source atom files are missing, atom evidence is too broad to normalize, or the user must decide a boundary before coverage can close.

## Final Report

`phase-works/phase-3/phase-3-agent-report.md` must summarize:

- source documents classified
- per-source-document review files written
- Phase 3 trace files written
- global obligation atoms indexed
- source documents covered by atoms
- missing obligation atoms added, or confirmation that none remain
- source ranges classified as non-atom content
- duplicate and ownership findings
- broad atoms split or justified
- non-coverage classifications
- artifact projection distribution and any projection uncertainties
- Phase 4 placement handoffs
- conflicts resolved or remaining
- confirmation that every production-meaningful obligation under the specified roots is covered by exactly one global atom or justified
- confirmation that no raw helper output was used as a gate
- confirmation that any line-range helper output, if used, was treated only as mechanical candidate input
- confirmation that every Phase 3 artifact passed the Artifact Language Gate

The final agent reply should be short and in Chinese. Include the decision, changed files, missing atoms, duplicate/ownership findings, language-gate result, remaining blockers, and whether Phase 4 may proceed.
