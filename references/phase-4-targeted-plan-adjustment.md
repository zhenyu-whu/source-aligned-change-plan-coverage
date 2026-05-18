# Phase 4: Targeted Change Plan and Obligation Atom Artifact Adjustment

Phase 4 runs only after Phase 3 returns `Decision: adjust`. It applies targeted changes to the current change/capability framework and the affected Phase 2 output files using Phase 3's exhaustive adjustment ledger, per-source-document missing atoms, duplicate/ownership findings, broad-anchor compression findings, capability progression findings, change complexity findings, overlap findings, and capability-view consistency findings.

Phase 4 exists to scientifically recalibrate the initial framework without rerunning the expensive Phase 2 workflow when Phase 3 has already identified precise source-backed missing obligations, ownership problems, sequencing problems, or over-complex change slices.

Phase 4 MUST be performed by a fresh independent subagent. It must not rerun all Phase 2 per-change subagents or perform a new global source search for every change.

## Inputs

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/reviews/coverage-review.md`
- `openspec/orchestrate/reviews/change-plan-adjustments.md`, especially the exhaustive adjustment ledger
- `openspec/orchestrate/source-doc-manifest.md`
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`, when present, as Phase 3's global review result
- affected `openspec/orchestrate/change-capability-anchors/<change-slug>/` directories
- `openspec/orchestrate/reports/phase-2-agent-report.md`
- User-specified source document roots or exact source paths, for targeted context reads only

## Outputs

Update current files in place:

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/reviews/change-plan-adjustments.md`
- affected `openspec/orchestrate/change-capability-anchors/<change-slug>/<change-slug>.md`
- affected `openspec/orchestrate/change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md`
- new per-change or per-capability atom files when the adjusted plan adds them
- `openspec/orchestrate/reports/phase-2-agent-report.md`, preserving unaffected rows and marking targeted Phase 4 updates
- `openspec/orchestrate/reports/phase-4-agent-report.md`

Do not write Phase 3 review outputs in Phase 4 except `reviews/change-plan-adjustments.md` closure status. A fresh Phase 3 pass rebuilds the compact manifest, per-source reviews, and global obligation atom index after Phase 4 finishes.

## Scope Rules

Phase 4 may:

- add, remove, split, merge, or rename changes when Phase 3's source obligation or overlap evidence requires it
- add, remove, split, merge, or rename capabilities when Phase 3 identifies durable behavior-boundary gaps
- attach missing obligation atoms to an existing change when the existing change already owns the same user/system loop
- split a broad Phase 2 atom into multiple smaller atoms when Phase 3 finds compressed UI/flow/data/verification obligations
- resolve duplicate direct atoms by choosing one owner and reclassifying the other rows as preserve, dependency, reference, later-change, or explicit non-goal
- reorder changes when Phase 3 shows capability atoms depend on prerequisites that currently appear too late
- split over-complex changes by coherent atom groups when Phase 3 shows the current change would be too large to implement, review, verify, or archive safely
- narrow a change's capability increments when Phase 3 shows some atoms are preserve/dependency/context rather than direct advancement
- create new per-change and per-capability atom files for new changes or capability increments
- update affected existing per-change and per-capability atom files so they match the adjusted plan and preserve canonical-change/capability-view consistency
- read targeted source context around Phase 3's missing atoms or overlap findings when needed to verify wording or line ranges

Phase 4 must not:

- rerun Phase 2 globally
- ask one subagent to reanalyze every planned change from scratch
- rewrite unaffected per-change directories
- invent new atoms without source evidence
- use raw uncovered line counts as a plan-adjustment driver without semantic review of the uncovered ranges
- update a nested capability atom file without first adding, updating, or confirming the matching canonical row in that change's `<change-slug>.md`
- leave duplicate direct atoms unresolved when Phase 3 has enough evidence to choose an owner
- leave any Phase 3 adjustment ledger row without an explicit closure status

If an adjustment cannot be made from Phase 3 findings plus targeted source context, return `blocked` and explain why a full Phase 2 rerun or user decision is required.

## Change and Capability Adjustment Method

Phase 4 must not treat Phase 3 findings as file-edit instructions only. It must first decide whether the findings prove a change-slicing, capability-boundary, capability-sequencing, or change-complexity problem.

Build a targeted adjustment graph from Phase 3 findings:

| Finding ID | Source Obligation Atoms | Current Owner Change | Current Owner Capability | Candidate Owner Changes | Candidate Owner Capabilities | Loop Impact | Boundary Impact | Sequence Impact | Complexity Impact | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Use these rules to decide the smallest coherent plan adjustment:

- Attach a missing atom to an existing change only when that change already owns the same user/system loop: same entry, fact, projection, failure path, and verification surface.
- Add or split a change when missing atoms reveal an independently verifiable loop that can be implemented, verified, reviewed, and archived separately.
- Merge changes only when Phase 3 shows they split one indivisible closed loop and neither side can be archived truthfully without the other.
- Keep an atom in the existing capability when it strengthens the same durable behavior boundary.
- Add, split, merge, or rename a capability when Phase 3 reveals a durable behavior boundary that is missing, conflated, too technical, or assigned to the wrong long-lived behavior boundary.
- Resolve duplicate direct atoms by choosing the owner change that first implements the production obligation. Later changes may only keep a direct atom when they add a source-backed delta; otherwise they must become `preserves:<global-atom-id>`, `depends-on:<global-atom-id>`, `reference`, or another contextual relation.
- Represent staged capability maturity as distinct atoms: an early change may own a baseline atom, and a later change may own a `refines` or `modifies` delta atom. Do not repeat the same atom across changes to simulate maturity.
- Do not create one capability per page, table, SDK, queue, provider, component, or source document section. Capabilities must remain long-lived behavior boundaries.

Evaluate capability atom progression before editing files:

| Capability | Current Change Sequence | Atom Groups By Change | Required Order | Sequence Problem | Adjustment |
| --- | --- | --- | --- | --- | --- |

Use these rules:

- Baseline atoms that create the behavior boundary must appear before refinement, hardening, extension, or preserve-only atoms.
- Failure, recovery, verification, auth/privacy, and data integrity atoms must appear in the first change that needs them for a truthful closed loop; do not defer them merely to reduce implementation scope if the earlier loop would be fake without them.
- Later changes may refine or harden prior atoms only with a source-backed delta. Otherwise they must be dependency/preserve/context.
- If a capability has multiple unrelated atom families, consider splitting the capability only when they are durable behavior boundaries rather than temporary implementation areas.

Evaluate change complexity before editing files:

| Change | Atom Groups | Capabilities Advanced | Entry/Fact/Projection Count | Failure/Recovery Count | Evidence Types | UI/Data/Worker/API Surfaces | Complexity Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |

Use these rules:

- Split a change when it contains multiple atom groups that can pass the Closed-loop Test independently.
- Split a change when it advances many capabilities only because shared infrastructure made grouping convenient.
- Split a change when the evidence burden spans many unrelated proof surfaces and would make review/archival ambiguous.
- Keep a change together when splitting would force fake stubs, break one user/system loop, or make either side unverifiable.
- Prefer the earliest minimal runnable loop after a foundation change; defer only atoms that are not required for that loop's production truth.

When `change-plan.md` changes, update all affected plan surfaces together:

- `Capability Map`: capability id, behavior boundary, first change, later expansion.
- `Capability Progression Matrix`: cells must describe concrete atom groups or deltas, not generic reuse.
- Affected `Change Roadmap` entries: in scope, out of scope, vertical slice, dependencies, archive readiness.
- Add or update a per-change `Obligation Atom Plan` subsection listing the global or local atom ids owned by the change, grouped by capability.
- Add or update a per-change `Complexity Budget` subsection summarizing direct atom groups, advanced capabilities, proof surfaces, and why the change remains reviewable.
- For every changed capability relation, keep only direct `New` or `Modified` advancement in the matrix; move dependency, preserve, or reference-only relations to notes.

## Workflow

1. Read Phase 3's `coverage-review.md` decision and plan-impact table.
2. Read `reviews/change-plan-adjustments.md` and extract every row from the exhaustive adjustment ledger.
3. Build the targeted adjustment graph required above: affected source atoms, current owner changes, candidate owner changes, current/candidate capabilities, loop impact, boundary impact, sequence impact, complexity impact, and plan decision.
4. Decide whether each finding is only an artifact synchronization issue or requires change/capability plan adjustment:
   - artifact-only: the current change and capability ownership are correct, but atom rows or derived capability views are missing, broad, duplicated, or stale
   - change adjustment: the owner change must be added, removed, split, merged, renamed, or have its vertical slice changed
   - capability adjustment: the owner capability must be added, removed, split, merged, renamed, or have its behavior boundary changed
   - sequence adjustment: the change order or atom delta placement must change so capability atoms advance in a coherent order
   - complexity adjustment: one or more changes must be split, narrowed, or merged because the current atom/evidence load is not reviewable
   - blocked: ownership cannot be resolved from Phase 3 evidence plus targeted source context
5. Update `change-plan.md` using the smallest coherent adjustment that covers the source-backed obligation or fixes the slicing/capability issue. If all findings are artifact-only, do not edit the plan, but state why ownership is already correct.
6. After any plan edit, verify the adjusted plan still passes the Closed-loop Test, foundation exception rules, anti one-to-one capability mapping rule, and split challenge from Phase 1. If not, revise the plan or return `blocked`.
7. Reconcile planned capability increments with the adjusted atom ownership:
   - each direct atom must appear under exactly one owner change and one owner capability
   - each capability matrix cell must be backed by one or more direct atoms or an explicit gap
   - no matrix cell may describe generic reuse, dependency-only behavior, or repeated ownership of the same atom
   - first appearance of a capability remains `New`; later direct deltas are `Modified`
   - later changes that only preserve or depend on prior atoms must not list that capability as advanced
8. Re-evaluate the adjusted change order and complexity budget:
   - every capability's atom sequence is baseline -> refinement/hardening/extension, unless source evidence justifies another order
   - every non-foundation change still has a single closed-loop outcome
   - every split/merge/narrowing decision has a source-backed and reviewability-backed rationale
   - no adjusted change is overloaded with unrelated atom groups or evidence surfaces
9. For each affected existing change, update its canonical per-change file:
   - preserve the original Phase 2 atom evidence that still applies
   - add Phase 3's missing obligation atoms where the adjusted change now owns them
   - split broad atoms into smaller atoms when Phase 3 found compressed obligations
   - remove, reclassify, or relate duplicate direct atoms that moved to another owner
   - keep line ranges as navigation hints using normalized `L<start>-L<end>` formatting
   - record atom gaps and blockers explicitly
   - assign each new or changed canonical atom a concise readable local atom id, source document, line range, atom type, source fact, normativity, owner capability, coverage status, roles, propose use, and evidence need
   - update the supporting source anchor table so every direct atom has traceable source evidence
10. For each affected capability increment, update or create its nested capability atom file by deriving rows from the canonical change ledger:
   - copy the canonical `Atom ID`, `Source Document`, `Lines`, `Atom Type`, `Source Fact`, `Normativity`, `Coverage Status`, owner capability, `Propose Use`, and `Evidence Need`
   - keep capability-specific rationale/propose-use wording only when it does not break traceability
   - ensure every canonical atom that directly names that capability appears in the capability file
   - ensure every capability-file row has a matching canonical atom row
11. If the plan adds a new change, create its `change-capability-anchors/<change-slug>/<change-slug>.md` and nested capability atom files from the Phase 3 source obligation or overlap evidence and targeted source context.
12. If the plan removes, splits, merges, reorders, or renames a change or capability, remove or rewrite stale affected atom files only inside the targeted update set, and record where each prior direct atom moved or how it was reclassified.
13. Update `reports/phase-2-agent-report.md` in place:
   - preserve unaffected Phase 2 rows
   - mark affected rows as `Phase 4 targeted update`
   - add rows for new changes or capability files
   - list removed stale change directories or files if any
   - summarize missing atoms added, broad atoms split, and duplicates reclassified
14. Update `reviews/change-plan-adjustments.md` with an applied-adjustments section. It must preserve the original ledger and add a closure table:

| Finding ID | Closure Status | Plan Adjustment | Canonical Change Atom | Capability View Updates | Duplicate/Relation Resolution | Remaining Gap or Blocker |
| --- | --- | --- | --- | --- | --- | --- |

15. Run a local artifact consistency check by inspection or deterministic parsing before finishing:
    - every ledger row has closure status `applied`, `non-coverage-classified`, `duplicate-resolved`, or `blocked`
    - every plan-changing ledger row has a recorded change/capability adjustment rationale
    - every capability matrix cell for affected changes is backed by direct atoms or explicit gaps
    - every adjusted capability has a coherent atom progression sequence
    - every adjusted change has a complexity budget and remains reviewably scoped
    - every new/changed capability row has a matching canonical atom row
    - every new/changed canonical atom that directly names a capability appears in that capability file
    - no duplicate direct atom remains in the affected files unless it is explicitly marked `blocked`
    - every broad-anchor compression finding resulted in split atoms or a source-backed non-coverage classification
16. Write `reports/phase-4-agent-report.md`.

## Phase 4 Report

`reports/phase-4-agent-report.md` must include:

| Phase 3 Finding | Source Ranges or Atoms | Plan Change Applied | Phase 2 Files Updated | Atom Resolution | Remaining Gap or Blocker |
| --- | --- | --- | --- | --- | --- |

It must also include:

- ledger closure summary with finding ids and closure statuses
- targeted adjustment graph summary: owner change decisions, capability boundary decisions, loop impact, and boundary impact
- capability atom progression recalibration summary
- change complexity recalibration summary
- whether `change-plan.md` changed
- capability map and progression matrix updates, or confirmation that all findings were artifact-only
- affected changes and capabilities
- new, split, removed, or reclassified atoms
- new or removed change/capability atom files
- targeted source documents read, if any
- confirmation that adjusted changes still satisfy the Closed-loop Test or are valid foundation exceptions
- confirmation that adjusted capability relations are direct `New` or `Modified` advancement only
- confirmation that adjusted capability atom sequences are coherent
- confirmation that adjusted change complexity is reviewable
- confirmation that canonical change atom ledgers were updated before nested capability views
- confirmation that affected nested capability views match the canonical change atom rows
- confirmation that duplicate direct atoms were resolved or blocked
- confirmation that no full Phase 2 rerun was performed
- next required step: `Run Phase 3 again`, or `Blocked`

## Completion

Phase 4 ends with exactly one status in `phase-4-agent-report.md`:

- `Phase 4 Status: adjusted`
- `Phase 4 Status: blocked`

Use `adjusted` when every Phase 3 adjustment ledger row has been closed, capability atom progression is coherent, adjusted changes remain reviewably scoped, and all affected Phase 2 artifacts are synchronized through the canonical change atom ledger and derived capability views.

Use `blocked` when the adjustment needs source boundaries, product decisions, or broad reanalysis that Phase 4 is not allowed to perform.

After `adjusted`, the main agent must spawn a fresh Phase 3 review subagent. Do not start `openspec-propose` directly from Phase 4.
