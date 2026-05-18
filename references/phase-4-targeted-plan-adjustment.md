# Phase 4: Atom-Driven Change and Capability Plan Refit

Phase 4 runs after Phase 3 returns `Decision: coverage-complete`. At this point the obligation atom granularity is stable enough to evaluate whether the Phase 1 change/capability framework is scientifically reasonable.

Phase 4 exists to refit the plan from the normalized global atom index. It evaluates change order, capability progression, dependencies, and change complexity using concrete atom groups rather than the initial slicing hypothesis. It may accept the Phase 1 framework or restructure changes/capabilities. Every decision must preserve atom-level traceability.

Phase 4 MUST be performed by a fresh independent subagent. It must not rerun Phase 2 extraction and must not invent new source obligations. If Phase 4 discovers a missing or over-broad source obligation, it must return `needs-coverage-recheck` instead of silently creating new atoms outside Phase 3.

## Inputs

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/source-doc-manifest.md`
- `openspec/orchestrate/source-obligation-atoms/index.md`
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`
- `openspec/orchestrate/reviews/coverage-review.md`
- `openspec/orchestrate/reviews/phase-3-trace/*.md`
- User-specified source document roots or exact source paths, for targeted context reads only when a Phase 3 handoff needs local wording.

## Outputs

Write the next monotonically increasing refit directory under `openspec/orchestrate/phase-4-plan-refit/`, such as `pass-01`, `pass-02`, and so on. Never overwrite an existing pass directory.

- `openspec/orchestrate/phase-4-plan-refit/pass-<NN>/input-change-plan.md`
- `openspec/orchestrate/phase-4-plan-refit/pass-<NN>/change-plan.md`
- `openspec/orchestrate/phase-4-plan-refit/pass-<NN>/atom-plan-mapping.md`
- `openspec/orchestrate/phase-4-plan-refit/pass-<NN>/phase-4-agent-report.md`
- `openspec/orchestrate/reviews/phase-4-trace/capability-progression-review.md`
- `openspec/orchestrate/reviews/phase-4-trace/change-complexity-review.md`
- `openspec/orchestrate/reviews/phase-4-trace/plan-refit-decision-log.md`
- `openspec/orchestrate/reviews/change-plan-adjustments.md` only when the status is `adjusted`, `needs-coverage-recheck`, or `blocked`
- `openspec/orchestrate/reports/phase-4-agent-report.md`
- `openspec/orchestrate/reports/alignment-final-report.md`

When the status is `accepted` or `adjusted`, also write final consume-ready artifacts:

- `openspec/orchestrate/change-capability-anchors/index.md`
- `openspec/orchestrate/change-capability-anchors/<change-slug>/<change-slug>.md`
- `openspec/orchestrate/change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md`
- `openspec/orchestrate/reports/change-capability-human-plan.md`

If Phase 4 accepts the input plan unchanged, still write the pass directory and final change packets. If Phase 4 adjusts the plan, write the adjusted snapshot to the pass directory and update root `openspec/orchestrate/change-plan.md` to the latest effective plan only after the pass directory records the input plan, output plan, and atom-plan mapping.

`source-obligation-atoms/` and `change-capability-anchors/obligation-atom-index.md` are upstream evidence. Do not edit them in Phase 4.

## Scope Rules

Phase 4 may:

- accept the Phase 1 framework when global atoms prove it is coherent
- add, remove, split, merge, reorder, or rename changes when atom groups and dependencies require it
- add, remove, split, merge, or rename capabilities when atoms reveal a durable behavior boundary gap
- move a global atom to a different owner change/capability when Phase 3 left placement to refit or when sequencing proves the initial candidate owner was wrong
- reclassify a global atom as contextual future-compatibility, dependency, preserve, reference, later-change, or explicit non-goal when it constrains design but is not current direct scope
- resolve final owner placement for atoms marked `phase-4-refit-required`
- stage capability maturity as baseline -> refinement/hardening/extension using distinct source-backed atom deltas
- derive final per-change and per-capability atom files from the global atom index
- read targeted source context around Phase 3 handoff items when needed to verify wording or dependency rationale

Phase 4 must not:

- rerun Phase 2 globally
- edit Phase 2 source atom files
- edit Phase 3 coverage outputs or the global atom index
- invent new atoms without Phase 3 normalization
- use raw uncovered line counts as a plan-adjustment driver without semantic review
- leave any direct global atom without exactly one final owner change/capability unless it is non-direct, non-coverage, or blocked
- leave duplicated direct ownership unresolved
- create one capability per page, table, SDK, queue, provider, component, or source document section
- hide future obligations inside early changes unless they affect current design as contextual or preserve constraints

If an adjustment cannot be made from Phase 3 findings plus targeted source context, return `blocked` or `needs-coverage-recheck` and explain which phase must run next.

## Refit Method

Phase 4 must first build an atom-driven planning graph:

| Global Atom ID | Source Obligation | Current Candidate Owner Change | Current Candidate Owner Capability | Dependency Atoms | Candidate Final Change | Candidate Final Capability | Sequence Impact | Complexity Impact | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Use these rules:

- A final change should represent a reviewable, implementable, verifiable user/system loop or a valid foundation exception.
- Attach an atom to an existing change only when that change owns the same coherent loop: entry, fact, projection, failure path, and verification surface.
- Add or split a change when atom groups reveal an independently verifiable loop that can be implemented, verified, reviewed, and archived separately.
- Merge changes only when atoms show they split one indivisible closed loop and neither side can be archived truthfully without the other.
- Reorder changes when atom dependencies show a later change depends on prerequisites currently introduced too late.
- Keep an atom in the existing capability when it strengthens the same durable behavior boundary.
- Add, split, merge, or rename a capability when atoms reveal a durable behavior boundary that is missing, conflated, too technical, or assigned to the wrong long-lived behavior boundary.
- Resolve duplicate direct atoms by choosing the owner change that first implements the production obligation. Later changes may only keep a direct atom when they add a source-backed delta; otherwise they become preserve/dependency/reference/context.
- Represent staged maturity as distinct atoms. Do not repeat the same atom across changes to simulate progression.
- Treat earlier changes as realized baseline providers, not global-context catchalls.

## Capability Progression Review

Before editing final plan artifacts, evaluate capability atom progression:

| Capability | Atom Families | Current Change Sequence | Required Order | Sequence Problem | Adjustment |
| --- | --- | --- | --- | --- | --- |

Rules:

- Baseline atoms that create the behavior boundary must appear before refinement, hardening, extension, or preserve-only atoms.
- Failure, recovery, verification, auth/privacy, and data integrity atoms must appear in the first change that needs them for a truthful closed loop.
- Later changes may refine or harden prior atoms only with a source-backed delta.
- Later changes that only preserve or depend on prior atoms must not list that capability as advanced.
- If a capability has multiple unrelated atom families, split the capability only when they are durable behavior boundaries rather than temporary implementation areas.

## Change Complexity Review

Evaluate change complexity before finalizing:

| Change | Atom Groups | Capabilities Advanced | Entry/Fact/Projection Count | Failure/Recovery Count | Evidence Types | UI/Data/Worker/API Surfaces | Complexity Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |

Rules:

- Split a change when it contains multiple atom groups that can pass the Closed-loop Test independently.
- Split a change when it advances many capabilities only because shared infrastructure made grouping convenient.
- Split a change when the evidence burden spans many unrelated proof surfaces and would make review/archival ambiguous.
- Keep a change together when splitting would force fake stubs, break one user/system loop, or make either side unverifiable.
- Prefer the earliest minimal runnable loop after a foundation change; defer only atoms that are not required for that loop's production truth.

## Effective Change Plan Requirements

The final `change-plan.md` must include:

### Inputs

- Source documents read
- Phase 3 global atom index path
- Phase 4 pass path
- Assumptions and conflicts

### Capability Map

| Capability | Behavior boundary | First change | Later expansion |
| --- | --- | --- | --- |

Rules:

- Capability ids must be stable English kebab-case ids.
- Behavior boundary explains durable behavior, not implementation module.
- First and later changes must be backed by direct global atoms.

### Capability Progression Matrix

| Change | `capability-a` | `capability-b` | `capability-c` |
| --- | --- | --- | --- |
| `change-name` | Concrete atom-backed increment |  | Concrete atom-backed increment |

Rules:

- Only direct `New` or `Modified` advancement belongs in matrix cells.
- Dependency, preserve, reference-only, and contextual relations belong in notes, not matrix cells.
- Each non-empty cell must be backed by one or more global atom ids.

### Change Roadmap

For each final change:

- Change name:
- Closed-loop outcome:
- Direct atom groups:
- Capability changes:
  - New:
  - Modified:
- In scope:
- Out of scope:
- Vertical slice:
  - Entry:
  - Fact:
  - Projection:
  - Failure:
  - Verification:
- Dependencies:
- Contextual atoms / downstream design constraints:
- Non-goals:
- Complexity budget:
- Archive readiness:

## Final Change Packets

Each `change-capability-anchors/<change-slug>/<change-slug>.md` final packet must include:

- change name
- closed-loop outcome
- final direct owner atoms grouped by capability
- contextual atoms and future constraints that affect current design
- upstream realized baseline atoms from earlier changes
- downstream constraints that must not be designed out
- explicit non-goals
- evidence burden
- source atom and global atom index links
- blockers, or `None`

Direct atom table:

| Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Owner Capability | Atom Relation | Roles | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Context table:

| Global Atom ID / Relation | Source Document | Lines | Context Type | Affects Current Design Because | Handling |
| --- | --- | --- | --- | --- | --- |

Each `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` file is a derived view. It must include only atoms from the final change packet that directly advance or materially constrain that capability.

Capability atom table:

| Capability | Change | Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Relation | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Derived-view invariants:

- Every capability row must have a matching row or context relation in the final change packet.
- Every direct atom whose owner capability is this capability must appear in the capability file.
- Capability files must not rename atoms, change source line ranges, or independently split/merge source facts.

## Workflow

1. Read Phase 3's `coverage-review.md` decision and global atom index.
2. Read Phase 3 handoff items, especially atoms marked `phase-4-refit-required`, ownership ambiguities, and source-backed non-direct constraints.
3. Create the next `phase-4-plan-refit/pass-<NN>/` directory and write `input-change-plan.md`.
4. Build the atom-driven planning graph.
5. Decide whether the Phase 1 framework is accepted, adjusted, needs coverage recheck, or blocked.
6. If accepted or adjusted, write `phase-4-plan-refit/pass-<NN>/change-plan.md` and `atom-plan-mapping.md`.
7. If adjusted, update root `openspec/orchestrate/change-plan.md` to the latest effective plan after the pass snapshot and mapping are written.
8. Write `reviews/phase-4-trace/capability-progression-review.md`, `change-complexity-review.md`, and `plan-refit-decision-log.md`.
9. If the status is `adjusted`, `needs-coverage-recheck`, or `blocked`, write `reviews/change-plan-adjustments.md` with the plan-impact and next-action summary.
10. Derive final `change-capability-anchors/<change-slug>/` packets and capability views from the global atom index and final plan when the status is `accepted` or `adjusted`.
11. Write `change-capability-anchors/index.md`.
12. Write `reports/change-capability-human-plan.md` as a readable synthesis of final change packets and capability progression when the status is `accepted` or `adjusted`.
13. Write `reports/phase-4-agent-report.md` and `reports/alignment-final-report.md`.
14. Run a local artifact consistency check by inspection or deterministic parsing before finishing.

## Required Mapping Tables

`phase-4-plan-refit/pass-<NN>/atom-plan-mapping.md` must include:

| Global Atom ID | Source Document | Lines | Phase 3 Owner / Status | Final Owner Change | Final Owner Capability | Final Relation | Plan Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

`reviews/phase-4-trace/plan-refit-decision-log.md` must include:

| Decision Item | Input Evidence | Candidate Options | Decision | Output Artifact | Reason |
| --- | --- | --- | --- | --- | --- |

`change-capability-anchors/index.md` must include:

| Change | Change Packet | Capability Views | Direct Atoms | Contextual Atoms | Capabilities Advanced | Evidence Burden | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- |

`reports/change-capability-human-plan.md` must include readable change packets:

| Change | Closed-loop Outcome | Direct Atom Groups | Contextual Atoms / Future Constraints | Upstream Realized Baseline | Downstream Constraints | Non-Goals | Evidence Burden | Ledger Links |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

It must also include a capability progression narrative:

| Capability | Baseline Change | Refinement / Hardening / Extension Changes | Atom Progression Summary | Human Review Notes |
| --- | --- | --- | --- | --- |

## Phase 4 Report

`reports/phase-4-agent-report.md` must include:

| Refit Finding | Source Ranges or Atoms | Plan Decision | Files Written | Atom Resolution | Remaining Gap or Blocker |
| --- | --- | --- | --- | --- | --- |

It must also include:

- whether the initial plan was accepted or adjusted
- atom-driven planning graph summary
- capability progression recalibration summary
- change complexity recalibration summary
- new, split, merged, removed, reordered, or renamed changes
- new, split, merged, removed, or renamed capabilities
- atoms moved, reclassified, or left as contextual
- confirmation that every direct global atom has exactly one final owner change/capability
- confirmation that final capability relations are direct `New` or `Modified` advancement only
- confirmation that change packets contain upstream baseline and downstream design context without pulling future scope into current direct ownership
- confirmation that final change complexity is reviewable
- confirmation that source atom files and the Phase 3 global atom index were not modified
- next required step: `Start openspec-propose`, `Run Phase 3 again`, or `Blocked`

## Completion

Phase 4 ends with exactly one status in `reports/phase-4-agent-report.md`:

- `Phase 4 Status: accepted`
- `Phase 4 Status: adjusted`
- `Phase 4 Status: needs-coverage-recheck`
- `Phase 4 Status: blocked`

Use `accepted` when the Phase 1 framework remains coherent after atom-level review, final packets were derived, every capability atom sequence is coherent, and every change remains reviewably scoped.

Use `adjusted` when the framework was refit, all final atom mappings are traceable, every capability atom sequence is coherent, every change remains reviewably scoped, and final packets were derived.

Use `needs-coverage-recheck` when Phase 4 exposes missing, over-broad, conflicting, or semantically unclear source obligations that Phase 3 must normalize before the plan can be final.

Use `blocked` when the adjustment needs source boundaries, product decisions, or broad reanalysis that Phase 4 is not allowed to perform.

After `accepted` or `adjusted`, `openspec-propose` may start from the final change packets. After `needs-coverage-recheck`, the main agent must spawn a fresh Phase 3 review subagent. Do not start `openspec-propose` directly from `needs-coverage-recheck` or `blocked`.
