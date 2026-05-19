# Phase 2: Source-First Obligation Atom Extraction

Phase 2 extracts source-backed obligation atom candidates from the source documents themselves. The analysis unit is a source document, not a planned change. The Phase 1 change/capability framework is only candidate ownership context; it must not prevent discovery of atoms that are unassigned, cross-cutting, or evidence for a new/refit change.

Phase 2 produces immutable raw extraction evidence and a separate Phase 2 aggregate inventory. Phase 3 owns normalization, missing-atom gap closure, duplicate resolution, and final global ownership. Phase 4 owns final change/capability refit and per-change packet generation.

## Inputs

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/source-doc-manifest.md`
- User-specified source document roots or exact source paths, only to resolve manifest paths and line references.

## Outputs

Write Phase 2 artifacts only:

- `openspec/orchestrate/source-obligation-atoms/work-queue.md`
- `openspec/orchestrate/source-obligation-atoms/index.md`
- `openspec/orchestrate/source-obligation-atoms/<source-relative-path-without-extension>.atoms.md` for every manifest source document with `Read Status: read-full`
- `openspec/orchestrate/reports/phase-2-agent-report.md`

Use single-level filenames under `source-obligation-atoms/`: derive the name from the source document path as listed in the manifest, remove the extension, replace path separators with `--`, and add `.atoms.md`.

These files are immutable after Phase 2 completes. If later phases discover missing atoms, duplicate facts, or ownership changes, they record them in the Phase 3 global atom index and Phase 4 refit artifacts; they must not rewrite the original Phase 2 source atom files.

## Output Ownership

Phase 2 output responsibility is split across orchestration, source extraction, and aggregation:

- The main orchestrating agent may write `source-obligation-atoms/work-queue.md` during Phase 2A, because this is lightweight scheduling rather than source obligation extraction.
- Source-extraction subagents write only their assigned `source-obligation-atoms/<source>.atoms.md` files.
- After every extraction subagent finishes, spawn a fresh independent Phase 2 index/report subagent. This subagent writes only `source-obligation-atoms/index.md` and `reports/phase-2-agent-report.md`.
- The Phase 2 index/report subagent may read `change-plan.md`, `source-doc-manifest.md`, `source-obligation-atoms/work-queue.md`, and all generated `source-obligation-atoms/*.atoms.md` files. It may run read-only commands to count ledger rows, status distributions, required sections, line-range formats, and missing outputs.
- The Phase 2 index/report subagent must not extract new atoms, edit source atom files, reread source bodies to create new evidence, perform global duplicate resolution, decide final atom ownership, close semantic coverage, or read Phase 3/Phase 4 outputs.
- If the aggregation pass finds missing, malformed, or incomplete extraction outputs, it must record blockers in `reports/phase-2-agent-report.md` and still keep the aggregate strictly Phase 2-scoped.

`source-obligation-atoms/index.md` and `reports/phase-2-agent-report.md` are Phase 2 summaries only. They must not become the normalized global atom index or final plan ownership map.

## Artifact Language Gate

Apply the skill-level Artifact Language Gate to every Phase 2 output. Keep fixed table headers, field names, enum/status values, atom ids, paths, line ranges, capability ids, change slugs, proof-type tokens, and exact source phrases as required, but write all agent-authored explanatory content in Simplified Chinese.

In particular, `Source Fact`, `Rationale`, `Propose Use`, `Reason`, ownership ambiguity notes, candidate missing boundary notes, blockers, report summaries, and any explanation inside table cells must be Chinese unless the entire value is only a fixed enum, ID, path, command, proof-type token, or exact source term. `Source Phrase` may preserve the original wording.

After writing each Phase 2 artifact, perform the language self-check from the skill gate. If any explanation sentence remains English-dominant after ignoring IDs, paths, commands, code, fixed enum/status values, and exact source phrases, rewrite it before finishing Phase 2.

## Obligation Atom Model

An obligation atom is the smallest source-backed production obligation that should survive into later `openspec-propose` artifacts. A later proposal/spec/design/tasks file should be able to consume an atom directly without reinterpreting a broad source paragraph.

Classify extracted source facts into these buckets:

- Direct candidate atom: source-backed production behavior that appears likely to be implemented, preserved, verified, or explicitly excluded by some change/capability.
- Contextual candidate atom: source-backed fact or future obligation that may constrain design but should not count as direct capability advancement unless Phase 3/4 assign it.
- Unassigned atom: source-backed production obligation whose final owner change/capability is unclear from the Phase 1 framework.
- Candidate new change/capability atom: source-backed obligation that suggests the Phase 1 framework may be missing or mis-slicing a behavior boundary.
- Non-coverage classification: source-backed material that is reference-only, prototype-only, non-production, superseded, no-impact, or blocked/conflicting.

A direct candidate atom is valid only when it is source-backed, implementation-relevant, small enough to be independently verified or excluded, and not merely a broad summary. One atom should represent one condition, state, action, display rule, data fact, transition, failure path, preserve boundary, verification requirement, or explicit non-goal. If a source paragraph contains multiple such obligations, split it into multiple atoms.

Atom types:

- `page-role`
- `route`
- `entry`
- `exit`
- `state`
- `trigger`
- `display`
- `primary-action`
- `disabled-action`
- `recovery`
- `interaction-rule`
- `data-fact`
- `auth-privacy-rule`
- `failure-path`
- `responsive`
- `verification`
- `acceptance`
- `preserve-boundary`
- `explicit-non-goal`
- `dependency`
- `reference`

Use stable, readable source-local ids such as:

- `intake-form.state.valid.submit-enabled`
- `approval-flow.interaction.edit-overwrites-pending-state`
- `async-job.failure-no-result`

Phase 3 may rename or globally qualify ids when it builds the normalized global obligation atom index. Do not rely on Phase 2 ids being globally unique.

## Phase 2A: Work Queue Planning

Before spawning extraction subagents, create `source-obligation-atoms/work-queue.md`.

This is a lightweight scheduling step. It may read `change-plan.md`, `source-doc-manifest.md`, source paths, document names, source roles, directory grouping, file sizes, and line counts. It must not extract obligation atoms, decide coverage, classify source obligations, or use filename/path heuristics as proof that a document has no production obligations.

Use this step to preserve context quality and improve parallelism:

- First create an initial semantic split by source family, document role, line count, and expected extraction difficulty.
- Then perform a merge review before spawning subagents. Merge compatible small or medium candidate batches when they share source family or extraction discipline and their combined context remains reviewable.
- Default target: no more than five Phase 2 extraction batches total. Exceed five only when the source set is genuinely large, contains multiple very large documents, or a merged batch would create unsafe context pressure or weaken extraction quality. Record the exception rationale in the work queue.
- Do not optimize for maximum parallelism when it creates many small extraction batches. Prefer fewer coherent canonical owners over loose one-subagent-per-small-cluster scheduling.
- Small documents may be batched by directory, source role, or doc type.
- Medium documents may be assigned in small batches when their combined line count remains reasonable.
- Large documents should normally receive a dedicated extraction subagent.
- Very large documents still need one canonical extraction owner; that owner may organize its output by section, but Phase 2 must not split canonical extraction of the same source document across multiple subagents.
- Prototype pages, prototype objects, system contracts, architecture/product docs, and verification matrices should be batched by coherent source domain rather than by arbitrary filename order.
- A batch is only a scheduling unit. Each source document in a batch still needs its own `<source>.atoms.md` file.

`source-obligation-atoms/work-queue.md` must include:

| Batch | Source Documents | Line Counts | Source Roles / Doc Types | Assignment Rationale | Extraction Mode | Canonical Owner |
| --- | --- | --- | --- | --- | --- | --- |

Rules:

- Every manifest source document with `Read Status: read-full` must appear in exactly one batch.
- `Extraction Mode` should be `single-doc`, `small-doc-batch`, `medium-doc-batch`, or `large-doc-dedicated`.
- `Assignment Rationale` may cite line count, source role, path domain, doc type, and expected context pressure.
- The work queue must include a short `Batch Merge Review` section after the table. It should state the initial candidate batch count, final batch count, which candidate batches were merged, and why any final queue exceeds five batches.
- The work queue is not source coverage evidence and must not include atom counts, coverage judgments, or no-obligation conclusions.

## Phase 2B: Source-First Subagent Discipline

Phase 2 must be reviewable as a set of source document extractions.

1. Read `change-plan.md` to understand candidate changes, capabilities, sequencing assumptions, and current planned boundaries.
2. Read `source-doc-manifest.md` and list every source document with `Read Status: read-full`.
3. Build `source-obligation-atoms/work-queue.md` using only lightweight scheduling evidence: initial semantic split first, then merge review, with a default target of five or fewer final extraction batches unless the source set is genuinely large or context pressure justifies more.
4. Spawn one fresh source-extraction subagent per work queue batch.
5. Each source-extraction subagent must read its assigned source document bodies in full.
6. Each subagent extracts atom candidates from the source first, then assigns candidate ownership only after the source-backed atom list is clear.
7. Candidate ownership may name a planned change/capability, `unassigned`, `candidate-new-change`, `candidate-new-capability`, `contextual`, or `non-direct`.
8. Do not ask a subagent to simulate one planned change across all source documents. Do not produce per-change canonical atom ledgers in Phase 2.
9. After all source-extraction subagents finish, spawn one fresh Phase 2 index/report subagent to aggregate the Phase 2 extraction outputs into `source-obligation-atoms/index.md` and `reports/phase-2-agent-report.md`.
10. The index/report subagent must treat existing `.atoms.md` files as raw extraction evidence. It may report blockers for missing or malformed files, but it must not repair, reinterpret, or extend their atom content.
11. Do not read Phase 3 or Phase 4 outputs while performing Phase 2 extraction or aggregation.

Use deterministic source filenames:

- source `docs/product/pages/settings.md` -> `docs--product--pages--settings.atoms.md`
- source `docs/architecture/runtime-design.md` -> `docs--architecture--runtime-design.atoms.md`

## UI and Flow Atom Extraction Rules

For page docs, object/component docs, flow contracts, interaction maps, state vocabularies, fixture contracts, scenario registries, verification matrices, and design-system documents, do not compress page or object details into a single broad atom.

Mandatory extraction rules:

- Each page or object route/duty/entry/exit with production effect must have an atom.
- Each named state must have at least one `state` atom.
- Each state trigger, display content, primary action, disabled action, and recovery rule must be represented by an atom or explicitly classified as non-production/no-impact.
- Each interaction rule that changes persistence, navigation, action submission, blocking, recovery, language, access/quota behavior, privacy, or state derivation must have an atom.
- Each responsive requirement must have a `responsive` atom when it affects a user's ability to complete the workflow or inspect a required state.
- Each acceptance criterion must have an `acceptance` or `verification` atom, or must cite the atom id it duplicates.
- Each `do not`, `non-goal`, or `out of scope` item must be retained as an `explicit-non-goal` atom when it prevents scope creep in later changes.
- Text labels may be contextual when purely cosmetic, but labels that define actions, state names, error copy, or required affordances must be atoms.

Do not close UI content as generic "duplicate page detail". If it is duplicate, name the duplicated source-local atom id when known and explain semantic equivalence.

## Per-Source Atom Files

Each `source-obligation-atoms/<source>.atoms.md` file must include:

- source document path
- source document role from the Phase 1 manifest
- whether the source document was read in full
- Phase 1 candidate changes/capabilities considered
- source section inventory
- obligation atom candidate ledger
- source remainder notes
- ownership ambiguity notes
- candidate missing plan boundaries, if any
- blockers, or `None`

### Source Section Inventory

Each source atom file must include a section inventory:

| Source Section or Range | Read Status | Production Meaning | Atom IDs | Non-Atom Classification | Reason |
| --- | --- | --- | --- | --- | --- |

Rules:

- The source document must be read in full.
- Section/range rows should be small enough for Phase 3 to verify coverage without rereading the whole document blindly.
- `Production Meaning` may be `obligation-bearing`, `contextual`, `reference-only`, `prototype-only`, `background`, `formatting`, `conflict`, or `unclear`.
- If a section has no atoms, the reason must explain why it has no production obligation or why it is blocked.

### Obligation Atom Candidate Ledger

Each source atom file must include:

| Source Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Candidate Status | Candidate Owner Change | Candidate Owner Capability | Roles | Rationale | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Rules:

- `Lines` must be in `L<start>-L<end>` format; for multiple ranges, join them with `; `.
- `Normativity` must be one of `must`, `must-not`, `should`, `context`.
- `Candidate Status` must be one of `direct-candidate`, `contextual-candidate`, `unassigned`, `candidate-new-change`, `candidate-new-capability`, `explicit-non-goal`, `reference-only`, `prototype-only-not-production`, `superseded`, `duplicate-candidate`, `no-product-or-system-impact`, `unresolved-conflict`, or `unclassified`.
- Candidate owner fields may name a Phase 1 change/capability, `unassigned`, `candidate-new-change`, `candidate-new-capability`, `contextual`, or `none`.
- `Propose Use` must say how the atom should enter proposal, spec, design, tasks, evidence, non-goals, or preserve constraints if it survives Phase 3/4.
- `Evidence Need` must name the proof type expected later, such as `unit`, `contract`, `integration`, `worker`, `browser-e2e`, `visual`, `fixture`, `manual`, or `none`.

### Source Anchor Table

Each source atom file must also include supporting source anchors:

| Source Document | Anchor | Lines | Source Phrase | Candidate Status | Source Atom IDs | Candidate Owners | Roles | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

Source anchors may support one or more source atom ids. Anchor titles are primarily for human navigation. Prefer concise semantic titles; do not use local numbering prefixes such as `A01`.

## Mapping Roles

For each atom mapping, record one or more roles:

- `primary`
- `modified`
- `preserve`
- `verification`
- `acceptance`
- `non-goal`
- `dependency`
- `later-expansion`
- `future-compatibility`
- `reference`
- `superseded-by`
- `conflict`

Do not treat `preserve`, `dependency`, `future-compatibility`, or `reference` as direct capability advancement in the Phase 1 framework. Phase 4 decides final advancement from the normalized atom index.

## Phase 2 Index and Report

This section is owned by the fresh Phase 2 index/report subagent after all source-extraction subagents have returned. The main agent should interface-check these outputs, not synthesize them.

`source-obligation-atoms/index.md` must include:

| Source Document | Work Queue Batch | Canonical Owner | Source Atom File | Read Status | Atom Candidates | Contextual Candidates | Unassigned Atoms | Candidate New Boundaries | Remainder Notes | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

`reports/phase-2-agent-report.md` must include:

A short `Index/Report Generation` section naming the fresh aggregation subagent, the inputs it read, the read-only checks it ran, outputs it wrote, and any blockers.

| Batch | Source Documents | Line Counts | Extraction Mode | Canonical Owner | Work Queue Rationale | Extraction Status |
| --- | --- | --- | --- | --- | --- | --- |

| Batch | Source Documents | Source Atom Files | Subagent Status | Docs Read Full | Atom Candidates | Contextual Candidates | Unassigned Atoms | Duplicate Risks | Candidate New Boundaries | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Do not include global coverage statistics here. Phase 3 owns semantic coverage closure, duplicate resolution, global uniqueness, and final ownership.

## Quality Gate

Before finishing Phase 2:

- Confirm `source-obligation-atoms/work-queue.md` exists and lists every manifest source document with `Read Status: read-full` exactly once.
- Confirm the work queue contains only batching rationale, not atom extraction, coverage judgments, or no-obligation conclusions.
- Confirm every manifest source document with `Read Status: read-full` has exactly one `source-obligation-atoms/<source>.atoms.md` file.
- Confirm every source document has exactly one canonical extraction owner named in the work queue and Phase 2 report.
- Confirm `source-obligation-atoms/index.md` and `reports/phase-2-agent-report.md` were generated by a fresh Phase 2 index/report subagent after extraction subagents finished.
- Confirm the Phase 2 index/report subagent did not edit source atom files, extract new atoms, perform global duplicate resolution, decide final ownership, close semantic coverage, or read Phase 3/Phase 4 outputs.
- Confirm every source atom file states that the source document was read in full.
- Confirm every source atom file includes the source section inventory, obligation atom candidate ledger, source anchor table, ownership ambiguity notes, candidate missing plan boundaries, and blockers.
- Confirm UI and flow documents were decomposed using the mandatory extraction rules above; broad "page detail" compression is not allowed.
- Confirm every atom and anchor has normalized `Lines` values in `L<start>-L<end>` format.
- Confirm candidate owner mappings are explicitly marked as candidate, not final.
- Confirm unassigned, candidate-new-change, candidate-new-capability, duplicate-candidate, unresolved-conflict, and unclassified rows are listed in the Phase 2 report.
- Confirm Phase 2 generated or rewrote only current Phase 2 outputs.
- Confirm every Phase 2 artifact passed the Artifact Language Gate.

Final reply should be a short Chinese report: work queue batches, source documents extracted, source atom files written, Phase 2 index/report subagent status, atom candidates found, unassigned atoms, candidate new boundaries, duplicate risks, unresolved conflicts, language-gate result, and blockers.
