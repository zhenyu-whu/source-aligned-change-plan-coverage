# Phase 2: Independent Per-Change Obligation Atom Analysis

Phase 2 analyzes the current change plan one change at a time. Each planned change is handled by a fresh independent subagent that reads every source document listed in the Phase 1 manifest, finds the source-backed obligation atoms that would support a later `openspec-propose` for that single change, and maps those atoms to the capability increments assigned to that change.

The primary Phase 2 analysis unit is one change. The per-change file is the canonical obligation atom ledger for that change. Source anchors are trace evidence for atoms; they are not the coverage target. Capability files are derived views from the canonical atom ledger; they must not be independent second-pass source searches and must not introduce atoms or anchors that are absent from the canonical change file.

## Inputs

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/source-doc-manifest.md`
- User-specified source document roots or exact source paths, only to resolve manifest paths and targeted line references.

## Outputs

Write Phase 2 pass artifacts only:

- `openspec/orchestrate/change-capability-anchors/<change-slug>/<change-slug>.md` for each planned change.
- `openspec/orchestrate/change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` for each planned capability increment in that change.
- `openspec/orchestrate/reports/phase-2-agent-report.md`

These files are immutable after Phase 2 completes. If Phase 4 applies targeted adjustments, it must write adjusted copies and supersession/removal mappings under `openspec/orchestrate/phase-4-adjustments/pass-<NN>/`; it must not edit, delete, or rewrite the original Phase 2 files or `reports/phase-2-agent-report.md`.

Phase 2 writes only the outputs listed above. Phase 1 owns the initial source manifest. Phase 3 enriches the manifest with global coverage review and owns the global obligation atom index, per-source coverage notes, review files, and `change-capability-anchors/index.md`.

## Obligation Atom Model

An obligation atom is the smallest source-backed production obligation that should survive into later `openspec-propose` artifacts. A later proposal/spec/design/tasks file should be able to consume an atom directly without reinterpreting a broad source paragraph.

For each source document and each planned change, Phase 2 must classify extracted source facts into one of three buckets:

- Direct obligation atom: the current change must implement, preserve, verify, or explicitly exclude this source-backed production obligation. It must affect the current change's UI behavior, data fact, API or worker behavior, auth/privacy boundary, failure/recovery path, verification requirement, preserve constraint, or non-goal boundary.
- Contextual atom: the current change does not directly implement this source-backed fact or future obligation, but must know it to avoid a bad design. Use this when later obligations affect the current data model, API contract, state machine, auth/privacy boundary, worker boundary, persistence format, verification truthfulness, or capability sequencing. Contextual atoms are non-owning and must not count as direct capability advancement.
- No-current-change-obligation: the document was read in full and has no source fact that the current change directly owns or needs as contextual design information. The reason may point to another change, a later change, prototype-only material, or no production/system impact.

A direct obligation atom is valid only when it is source-backed, implementation-relevant, small enough to be independently verified or excluded, and assignable to exactly one current owner change/capability. One atom should represent one condition, state, action, display rule, data fact, transition, failure path, preserve boundary, verification requirement, or explicit non-goal. If a source paragraph contains multiple such obligations, split it into multiple atoms.

Contextual atoms should be retained in the canonical per-change ledger when they protect downstream design coherence, but they are not coverage ownership. If a future atom has no current design impact, classify the source row as `later-change` or `no-current-change-obligation` instead of carrying it as context.

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

Every direct atom must have exactly one owner change and one direct owner capability, except change-wide context atoms may use `change-level-context`. Preserve, dependency, reference, future-compatibility, explicit non-goal, prototype-only, superseded, and no-impact facts may be recorded as contextual atoms, but they must not be counted as direct capability advancement.

Atom ids are local candidate ids in Phase 2 because per-change subagents are independent. Use stable, readable ids such as:

- `figure-new.state.filled.continue-enabled`
- `figure-brief.interaction.item-edit-overwrites-brief`
- `first-draft.worker.failure-no-version`

Phase 3 may rename or globally qualify ids when it builds the global unique obligation atom index. Do not rely on Phase 2 ids being globally unique.

## Per-Change Subagent Discipline

Phase 2 must be reviewable as a set of independent change analyses.

1. Read the current `change-plan.md` and list planned changes in order.
2. Read `source-doc-manifest.md` and list every source document with `Read Status: read-full`.
3. For each planned change, spawn a fresh independent subagent:
   - Give it the change name, that change's full definition, and that change's planned capability increments from `change-plan.md`.
   - Give it the Phase 1 source document manifest and source roots needed to resolve paths.
   - Ask it to simulate the later `openspec-propose` source search for only that change, but across every source document in the manifest.
   - Ask it to read every source document body listed in the manifest, even when the document appears unlikely to apply to that change.
- Ask it to extract obligation atoms for the whole change vertical slice first: entry, fact, projection, failure path, verification, dependency, preserve boundary, explicit non-goal, and archive readiness.
- Ask it to distinguish direct owning atoms from contextual atoms. A future or later-change source fact belongs in this change only when it constrains the current design; otherwise it should be recorded as another-change/later-change/no-current-change-obligation rationale.
- Ask it to map each direct production atom to the specific capability increment it supports for that change.
   - Ask it to produce a per-source-document extraction ledger: each source document must have atoms, contextual atoms, or an explicit `no-current-change-obligation` / `reference-only-for-this-change` classification.
   - Ask it to write supporting source anchors after the obligation atom ledger is complete.
   - Ask it to derive nested capability files from the canonical atom ledger after the canonical ledger is complete.
   - It must not read other `change-capability-anchors/<other-change-slug>/` directories, prior Phase 2 summaries, or Phase 3 review files.
   - It must write only inside `openspec/orchestrate/change-capability-anchors/<change-slug>/`.

Use deterministic change slugs:

- change `editor-canvas-first-loop` -> `editor-canvas-first-loop.md`
- change `auth: session hardening` -> `auth-session-hardening.md`
- capability `identity-session-continuity` -> `identity-session-continuity.md`

## UI and Flow Atom Extraction Rules

For `docs/prototype/pages/*`, `docs/prototype/objects/*`, flow contracts, interaction maps, state vocabulary, fixture contracts, scene registry, verification matrix, and design-system documents, do not compress page or object details into a single broad atom.

Mandatory extraction rules:

- Each page or object route/duty/entry/exit with production effect must have an atom.
- Each named state must have at least one `state` atom.
- Each state trigger, display content, primary action, disabled action, and recovery rule must be represented by an atom or explicitly classified as non-production/no-impact.
- Each interaction rule that changes persistence, navigation, action submission, blocking, recovery, language, entitlement, privacy, or state derivation must have an atom.
- Each responsive requirement must have a `responsive` atom when it affects a user's ability to complete the workflow or inspect a required state.
- Each acceptance criterion must have an `acceptance` or `verification` atom, or must cite the atom id it duplicates.
- Each `不做` / non-goal item must be retained as an `explicit-non-goal` atom when it prevents scope creep in later changes.
- Text labels may be contextual when purely cosmetic, but labels that define actions, state names, error copy, or required affordances must be atoms.

Do not close UI content as generic "duplicate page detail". If it is duplicate, name the duplicated atom id and explain semantic equivalence.

## Per-Change Files

Each `change-capability-anchors/<change-slug>/<change-slug>.md` file must include:

- change name
- change definition excerpt used
- planned capability increments used
- full source manifest used
- source documents read, which must include every `read-full` source document from `source-doc-manifest.md`
- per-source-document extraction ledger
- obligation atom ledger
- source anchor table
- atom gaps where the change appears to need source evidence but no precise atom was found
- duplicate-risk notes where the same source fact may belong to another change
- blockers, or `None`

This file is canonical for the change. It should include all atoms and anchors that later nested capability files use. Capability files may shorten prose or add capability-specific rationale, but they must not change the canonical `Atom ID`, `Source Document`, `Lines`, `Atom Type`, `Source Fact`, `Coverage Status`, or owner capability enough to break traceability.

### Per-Source-Document Extraction Ledger

Each per-change file must include one row for every source document in the Phase 1 manifest:

| Source Document | Read Status | Atoms Extracted For This Change | Contextual Atoms | No-Atom Classification | Reason |
| --- | --- | --- | --- | --- | --- |

Rules:

- `Read Status` must be `read-full` for every source document from the Phase 1 manifest.
- `Atoms Extracted For This Change` lists direct atom ids, or `None`.
- `Contextual Atoms` lists preserve/dependency/reference/non-goal atom ids, or `None`.
- `No-Atom Classification` may be `has-current-change-atoms`, `reference-only-for-this-change`, `later-change`, `no-current-change-obligation`, `prototype-only-not-production`, `no-product-or-system-impact`, `unresolved-conflict`, or `blocked`.
- A document cannot be omitted because it seems irrelevant; it must have a row and a reason.
- If a document has no direct atoms for this change, the reason must explain why its source obligations belong to another change, are contextual, or do not affect production.
- If a document contains later obligations that would affect the current change's data model, API contract, state machine, permission boundary, worker boundary, persistence format, or verification truthfulness, record contextual atoms instead of only `later-change`.

### Obligation Atom Ledger

Each per-change file must include:

| Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Coverage Status | Owner Capability | Roles | Rationale | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Rules:

- `Atom ID` is a readable local candidate id.
- `Lines` must be in `L<start>-L<end>` format; for multiple ranges, join them with `; `.
- `Normativity` must be one of `must`, `must-not`, `should`, `context`.
- `Owner Capability` must name one planned capability increment for direct atoms, or `change-level-context` for contextual atoms.
- `Propose Use` must say how the atom should enter proposal, spec, design, tasks, evidence, non-goals, or preserve constraints.
- `Evidence Need` must name the proof type expected later, such as `unit`, `contract`, `integration`, `worker`, `browser-e2e`, `visual`, `fixture`, `manual`, or `none`.
- Contextual atoms must have `Normativity: context`, a non-direct `Coverage Status` such as `later-change`, `preserve-existing`, `reference-only`, or `capability-boundary`, and `Propose Use` wording that explains how they constrain design without becoming current scope.

### Source Anchor Table

Each per-change file must also include supporting source anchors:

| Source Document | Anchor | Lines | Source Phrase | Coverage Status | Atom IDs | Capabilities | Roles | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

Source anchors may support one or more atom ids. Anchor titles are primarily for human navigation. Prefer concise semantic titles; do not use local numbering prefixes such as `A01`.

Line ranges are navigation hints, not the only identity. Every Markdown or text anchor must include a `Lines` value in `L<start>-L<end>` format. For multiple ranges, join them with `; `.

## Per-Change Capability Atom Files

Each `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` file is scoped to one change and one capability. It must include:

- change name
- capability id
- planned capability increment from `change-plan.md`
- capability obligation atom table
- supporting anchor summary
- capability atom gaps where a planned increment lacks precise source support
- candidate new or renamed capabilities suggested by source atoms, if any
- blockers, or `None`

Each per-change capability atom table must include:

| Capability | Planned Increment In This Change | Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Coverage Status | Roles | Rationale | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Capability files are derived views. Apply these invariants:

- Every row in a capability file must have a matching canonical atom row in the same change file with the same `Atom ID`, `Source Document`, `Lines`, `Atom Type`, `Source Fact`, `Normativity`, `Coverage Status`, and direct owner capability.
- Every canonical atom row whose `Owner Capability` directly names a planned capability must appear in that capability's nested file.
- A capability file may add capability-specific rationale and propose-use wording, but it must not rename the atom, change the line range, or split/merge source documents independently.
- If a narrower capability-specific line range seems useful, keep the canonical line range unchanged and explain the narrower relevance in `Rationale`; do not create a second atom identity.
- If a row is only `change-level-context`, it does not need to appear in a capability file unless it is needed as preserve, dependency, reference, or non-goal evidence for that capability.

## Coverage Status

Every atom and source anchor in a per-change file must have exactly one primary status:

- `current-change`
- `capability-boundary`
- `preserve-existing`
- `later-change`
- `explicit-non-goal`
- `reference-only`
- `prototype-only-not-production`
- `superseded`
- `duplicate-candidate`
- `no-product-or-system-impact`
- `unresolved-conflict`
- `unclassified`

`unclassified` is allowed only as a Phase 2 finding and is a Phase 3 blocker candidate. `duplicate-candidate` is a Phase 2 risk note; Phase 3 must resolve it to one direct owner atom plus contextual preserve/dependency/reference rows, or mark it as a blocker.

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

Do not treat `preserve`, `dependency`, `future-compatibility`, or `reference` as direct capability advancement in the change plan matrix.

## Phase 2 Report

`reports/phase-2-agent-report.md` is an orchestration trace, not a global coverage report. It must include:

| Order | Change | Change Directory | Source Atom File | Subagent Status | Manifest Source Docs | Source Docs Read | Per-Source Rows | Direct Atoms | Contextual Atoms | Anchors | Atom Gaps | Duplicate Risks | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

| Order | Change | Capability Atom Files | Capability Increments | Capability Atom Gaps | Blockers |
| --- | --- | --- | --- | --- | --- |

Do not include per-source-document global coverage statistics here. Phase 3 owns per-source obligation coverage, global atom uniqueness, cross-change overlap review, and compact adjustment review.

The report must state that nested capability files were derived from canonical change atoms and summarize any derivation exceptions. Exceptions are allowed only as explicit capability atom gaps or blockers.

## Quality Gate

Before finishing Phase 2:

- Confirm every planned change has exactly one `change-capability-anchors/<change-slug>/<change-slug>.md`.
- Confirm every planned capability increment has exactly one `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md`.
- Confirm every per-change file and nested capability atom files were produced by the same fresh independent subagent for that change.
- Confirm every per-change subagent read every source document listed as `read-full` in the Phase 1 manifest.
- Confirm every per-change file includes the change definition excerpt used, planned capability increments used, full source manifest used, per-source-document extraction ledger, obligation atom ledger, source anchor table, atom gaps, duplicate-risk notes, and blockers.
- Confirm the per-source-document extraction ledger has exactly one row for every Phase 1 manifest source document.
- Confirm every direct production atom has one owner capability or an explicit gap/blocker.
- Confirm contextual atoms are non-owning design context and are not counted as current capability advancement.
- Confirm every nested capability file covers its planned capability increment with source atoms or an explicit capability atom gap.
- Confirm every nested capability atom row exists in that change's canonical atom ledger with the same `Atom ID`, `Source Document`, `Lines`, `Atom Type`, `Source Fact`, `Normativity`, `Coverage Status`, and direct owner capability.
- Confirm every canonical atom row that directly names a planned capability appears in that capability's nested file.
- Confirm capability files do not introduce independent atoms, narrower line ranges, merged source rows, or renamed atoms that break traceability to the canonical change ledger.
- Confirm every atom and anchor in each per-change file has a primary coverage status.
- Confirm Markdown/text anchors use concise human-readable semantic titles and normalized `Lines` values in `L<start>-L<end>` format.
- Confirm UI and flow documents were decomposed using the mandatory extraction rules above; broad "page detail" compression is not allowed.
- List all per-change `unclassified`, `unresolved-conflict`, and `duplicate-candidate` atoms in the Phase 2 report.
- List all capability atom gaps in the Phase 2 report.
- Confirm Phase 2 generated or rewrote only current Phase 2 outputs.

Final reply should be a short report: changes analyzed, per-change atom files written, per-change capability atom files written, confirmation that every change read every source doc, per-change source gaps, capability atom gaps, duplicate risks, unclassified atoms, unresolved conflicts, and blockers.
