# Phase 4: Atom-Driven Change and Capability Plan Refit

Phase 4 runs after Phase 3 returns `Decision: coverage-complete`. At this point the obligation atom granularity is stable enough to evaluate whether the Phase 1 change/capability framework is scientifically reasonable.

Phase 4 exists to refit the plan from the normalized global atom index. It evaluates change order, capability progression, dependencies, artifact projection, and change complexity using concrete atom groups rather than the initial slicing hypothesis. It may accept the Phase 1 framework or restructure changes/capabilities. Every decision must preserve atom-level traceability and ensure each final direct atom has a downstream artifact projection.

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

## Artifact Language Gate

Apply the skill-level Artifact Language Gate to every Phase 4 output. Keep fixed table headers, field names, enum/status values, atom ids, paths, line ranges, capability ids, change slugs, relation tokens, and exact source phrases as required, but write all agent-authored explanatory content in Simplified Chinese.

In particular, closed-loop outcomes, behavior-boundary descriptions, roadmap values, capability progression narratives, complexity decisions, split/defer analyses, context handling, blockers, plan-decision reasons, evidence-burden descriptions, human review notes, and report summaries must be Chinese unless the entire value is only a fixed enum, ID, path, command, relation token, proof-type token, or exact source term.

After writing each Phase 4 artifact, perform the language self-check from the skill gate. If any explanation sentence remains English-dominant after ignoring IDs, paths, commands, code, fixed enum/status values, relation tokens, proof-type tokens, and exact source phrases, rewrite it before finishing Phase 4.

## Scope Rules

Phase 4 may:

- accept the Phase 1 framework when global atoms prove it is coherent
- add, remove, split, merge, reorder, or rename changes when atom groups and dependencies require it
- add, remove, split, merge, or rename capabilities when atoms reveal a durable behavior boundary gap
- move a global atom to a different owner change/capability when Phase 3 left placement to refit or when sequencing proves the initial candidate owner was wrong
- reclassify a global atom as contextual future-compatibility, dependency, preserve, reference, later-change, or explicit non-goal when it constrains design but is not current direct scope
- resolve final owner placement for atoms marked `phase-4-refit-required`
- adjust final artifact projection when Phase 3's projection is too broad, too narrow, or no longer matches final change packet use
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
- leave any direct global atom without final artifact projection
- force a `design-obligation` or `verification-obligation` atom into specs as a `spec-requirement` merely because it is direct
- leave duplicated direct ownership unresolved
- create one capability per page, table, SDK, queue, external service, component, or source document section
- hide future obligations inside early changes unless they affect current design as contextual or preserve constraints

If an adjustment cannot be made from Phase 3 findings plus targeted source context, return `blocked` or `needs-coverage-recheck` and explain which phase must run next.

## Refit Method

Phase 4 must first build an atom-driven planning graph:

| Global Atom ID | Source Obligation | Current Candidate Owner Change | Current Candidate Owner Capability | Current Artifact Projection | Dependency Atoms | Candidate Final Change | Candidate Final Capability | Candidate Final Artifact Projection | Sequence Impact | Complexity Impact | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Use these rules:

- A final change should represent a reviewable, implementable, verifiable user/system loop or a valid foundation exception.
- A final change is also the unit a later AI agent will implement in one focused `openspec-apply-change` pass. Closed-loop coherence alone does not justify a large change.
- Attach an atom to an existing change only when that change owns the same coherent loop: entry, fact, projection, failure path, and verification surface.
- Add or split a change when atom groups reveal an independently verifiable loop that can be implemented, verified, reviewed, and archived separately.
- Merge changes only when atoms show they split one indivisible closed loop and neither side can be archived truthfully without the other.
- Reorder changes when atom dependencies show a later change depends on prerequisites currently introduced too late.
- Keep an atom in the existing capability when it strengthens the same durable behavior boundary.
- Add, split, merge, or rename a capability when atoms reveal a durable behavior boundary that is missing, conflated, too technical, or assigned to the wrong long-lived behavior boundary.
- Do not add, split, merge, or rename capabilities merely to reduce how many capability columns a change touches. A refit that turns durable behavior boundaries into one-change aliases is invalid even when each individual change remains small.
- Resolve duplicate direct atoms by choosing the owner change that first implements the production obligation. Later changes may only keep a direct atom when they add a source-backed delta; otherwise they become preserve/dependency/reference/context.
- Represent staged maturity as distinct atoms. Do not repeat the same atom across changes to simulate progression.
- Treat earlier changes as realized baseline providers, not global-context catchalls.
- Treat future domain behavior as contextual or downstream constraints until the first change that directly implements it. Do not make an early change own direct atoms simply because later changes depend on their contracts.
- Preserve artifact projection independently from final owner placement. A direct atom can be implementation-owned by a change while projecting to design, tasks/proof, or spec guard rather than becoming a spec requirement.
- Prefer staged slices such as input preparation -> confirmed domain fact -> async execution -> external integration -> result projection -> hardening/delivery/operations when each slice can be verified truthfully.
- Preserve directly necessary cross-capability increments inside the same change when they share the same entry, fact, projection, failure path, and verification truth. Do not move identity, privacy, realtime state, versioning, entitlement, export, failure recovery, or observability atoms into artificial standalone changes solely to narrow the matrix row.

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

| Change | Direct Atom Count | Artifact Projection Mix | Atom Groups | New Capabilities | Modified Capabilities | Primary Functional Points | Entry/Fact/Projection Count | Failure/Recovery Count | Evidence Types | Surface Families | Budget Status | Complexity Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Use direct atom count as a complexity signal, not as a source coverage goal. Fine-grained atoms are expected, but a final change with many direct atoms still creates implementation, review, and archival risk.

Rules:

- Target budget: 20-60 direct atoms, one primary functional point, directly necessary capability deltas only, at most two primary surface families, and a compact evidence burden. More than one new or modified capability is acceptable when those deltas are required for the same truthful loop.
- Over-budget trigger: any change with more than 80 direct atoms, more than 4 unrelated directly advanced capabilities, an incoherent artifact projection mix, more than 12 failure/recovery atoms, more than 2 primary entry points, more than 2 fact families, more than 2 projection families, more than 3 evidence types, or more than 3 surface families must be split, deferred, or justified with concrete indivisibility evidence. Related cross-cutting capability deltas are not an over-budget trigger by count alone.
- Hard split/blocker trigger: any change with more than 120 direct atoms or more than 6 unrelated directly advanced capabilities that do not share the same entry/fact/projection/failure truth must not be marked `accepted` or `adjusted` as-is. Phase 4 must split it, move atoms to later changes/context, or return `blocked` for a user slicing decision.
- A `Keep` decision for an over-budget change must list rejected split candidates and explain why each would break truthfulness. "One coherent loop", "shared infrastructure", or "packet-level evidence grouping" is not sufficient.
- Split a change when it contains multiple atom groups that can pass the Closed-loop Test independently.
- Split a change when it advances many capabilities only because shared infrastructure made grouping convenient.
- Split a change when the evidence burden spans many unrelated proof surfaces and would make review/archival ambiguous.
- Keep a change together when splitting would force fake stubs, break one user/system loop, or make either side unverifiable.
- Prefer the earliest minimal runnable loop after a foundation change; defer only atoms that are not required for that loop's production truth.
- Split input preparation from downstream execution when the preparation state can be saved, revisited, validated, and verified without executing the downstream job.
- Split external integration from command/job/result semantics when an adapter contract, deterministic sandbox, or integration-disabled path can be verified truthfully and the concrete integration can be added as a later direct change.
- Split result projection, history, or interaction surfaces from upstream execution when the durable result fact can be verified independently of the richer projection loop.
- Split access/quota enforcement, delivery, observability, and operations atoms out of a feature change unless they are required to make the current feature's behavior truthful rather than merely production-complete in a future sense.
- Do not split a change solely because it advances several capabilities. If the split would create a diagonal matrix where each new change mostly owns one capability with a similar name, keep or redesign the vertical loop instead and record the reason.

### Foundation Scope Gate

Foundation changes are valid only as minimal enabling scaffolds. Evaluate them with a stricter budget:

- A foundation change should directly own only runtime/repository skeleton, package/app boundaries, configuration loading, migration/test harnesses, empty adapter seams, environment/deploy conventions, and smoke proof.
- These foundation direct atoms often project to `design-obligation`, `verification-obligation`, or `spec-guard`; only externally meaningful runtime contracts should project to `spec-requirement`.
- A foundation change should not directly advance user/domain capabilities such as access/session flows, input preparation, domain-work execution, interactive state projection, result history, collection management, quota/accounting, delivery, privacy workflows, or operational observability. Those are direct scope in the first feature change that needs them.
- Direct domain atoms in a foundation change must be moved to later changes or reclassified as contextual/downstream constraints unless Phase 4 proves no later closed-loop change can start without implementing them now.
- A foundation change with more than 40 direct atoms, more than 2 capabilities advanced, or any direct domain behavior requires split/defer analysis. If it remains over budget, return `blocked` or record a user-facing exception with rejected split options.

### Required Split Analysis

For every over-budget trigger, write a split analysis before the final decision:

| Change | Trigger | Candidate Split | Atoms / Capabilities Moved | New Closed-loop Outcome | Verification Surface | Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

Candidate split patterns include:

- scaffold-only foundation -> first behavior slice
- input capture/validation/preparation -> downstream execution
- command/job contract -> concrete executor or external integration
- durable result fact creation -> result projection/history/interaction surface
- core feature loop -> access control, quota, delivery, observability, or hardening
- user-facing workflow -> admin, reconciliation, maintenance, or operations loop
- synchronous happy path -> async processing, retry, recovery, or audit trail

Forbidden split patterns include:

- capability-column split: one vertical loop is divided into separate changes only because its atoms belong to multiple capabilities
- same-name alias split: a new change and a new capability are created as semantic paraphrases of each other
- cross-cutting concern evacuation: identity, privacy, realtime state, versioning, entitlement, export, failure recovery, or observability atoms are moved away from the loop that directly needs them only to reduce capability count

## Change/Capability Coupling Gate

Before finalizing `accepted` or `adjusted`, audit the final matrix shape:

| Check | Signal | Required Action |
| --- | --- | --- |
| Diagonal roadmap | Most change rows have exactly one non-empty capability cell | Re-evaluate whether changes were sliced by capability instead of user/system loop; reslice or justify each focused loop. |
| Single-change capabilities | Many capabilities are advanced by exactly one change | Merge, broaden, or rename capabilities unless source evidence proves terminal behavior boundaries. |
| Name aliasing | A capability id paraphrases the only or first change that advances it | Rename around a durable behavior boundary, merge into a broader capability, or record a blocker. |
| Lost cross-cutting deltas | A loop no longer directly advances necessary auth/privacy/realtime/versioning/entitlement/failure/export/observability behavior | Move those atoms back into the loop as direct deltas unless they are only contextual or preserve constraints. |
| Budget-induced diagonalization | Split decisions reduce capability count but make the matrix less source-faithful | Reject the split and keep the cross-capability loop with concrete indivisibility analysis. |

Rules:

- A single-capability change is allowed only when its entry, fact, projection, failure path, and verification truly do not directly change another durable capability.
- A capability advanced by one change is allowed only when the source set makes it a terminal first-version boundary or later expansion is explicitly out of scope; this must be stated in the progression review.
- If the final plan has a mostly diagonal matrix and the coupling gate cannot justify it from source evidence, return `blocked` instead of `accepted` or `adjusted`.
- The Phase 4 report must summarize this audit with counts or qualitative findings sufficient for a reviewer to see why the plan did not collapse into change/capability one-to-one mapping.

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
- Capability ids must not merely paraphrase final change slugs. When a capability has only one final direct change, record why it is a durable terminal boundary or refit it.

### Capability Progression Matrix

| Change | `capability-a` | `capability-b` | `capability-c` |
| --- | --- | --- | --- |
| `change-name` | Concrete atom-backed increment |  | Concrete atom-backed increment |

Rules:

- Only direct `New` or `Modified` advancement belongs in matrix cells.
- Dependency, preserve, reference-only, and contextual relations belong in notes, not matrix cells.
- Each non-empty cell must be backed by one or more global atom ids.
- The matrix must pass the Change/Capability Coupling Gate. A mostly diagonal matrix requires source-backed exceptions, not silence.

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
  - Direct atom count:
  - Capabilities advanced:
  - Surface families:
  - Evidence types:
  - Budget status:
  - Split/defer analysis:
- Archive readiness:

## Final Change Packets

Each `change-capability-anchors/<change-slug>/<change-slug>.md` final packet must include:

- change name
- closed-loop outcome
- final direct owner atoms grouped by capability
- final artifact projection for every direct atom
- contextual atoms and future constraints that affect current design
- upstream realized baseline atoms from earlier changes
- downstream constraints that must not be designed out
- explicit non-goals
- complexity budget status, over-budget triggers, and split/defer decisions
- evidence burden
- source atom and global atom index links
- blockers, or `None`

Direct atom table:

| Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Artifact Projection | Projection Rationale | Owner Capability | Atom Relation | Roles | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Context table:

| Global Atom ID / Relation | Source Document | Lines | Context Type | Affects Current Design Because | Handling |
| --- | --- | --- | --- | --- | --- |

Each `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` file is a derived view. It must include only atoms from the final change packet that directly advance or materially constrain that capability.

Capability atom table:

| Capability | Change | Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Artifact Projection | Relation | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Derived-view invariants:

- Every capability row must have a matching row or context relation in the final change packet.
- Every direct atom whose owner capability is this capability must appear in the capability file.
- Capability files must not rename atoms, change source line ranges, change artifact projection, or independently split/merge source facts.

## Workflow

1. Read Phase 3's `coverage-review.md` decision and global atom index.
2. Read Phase 3 handoff items, especially atoms marked `phase-4-refit-required`, ownership ambiguities, and source-backed non-direct constraints.
3. Create the next `phase-4-plan-refit/pass-<NN>/` directory and write `input-change-plan.md`.
4. Build the atom-driven planning graph.
5. Apply the implementation-ready complexity gate, foundation scope gate, required split analysis, and Change/Capability Coupling Gate to every candidate final change.
6. Decide whether the Phase 1 framework is accepted, adjusted, needs coverage recheck, or blocked.
7. If accepted or adjusted, write `phase-4-plan-refit/pass-<NN>/change-plan.md` and `atom-plan-mapping.md`.
8. If adjusted, update root `openspec/orchestrate/change-plan.md` to the latest effective plan after the pass snapshot and mapping are written.
9. Write `reviews/phase-4-trace/capability-progression-review.md`, `change-complexity-review.md`, and `plan-refit-decision-log.md`.
10. If the status is `adjusted`, `needs-coverage-recheck`, or `blocked`, write `reviews/change-plan-adjustments.md` with the plan-impact and next-action summary.
11. Derive final `change-capability-anchors/<change-slug>/` packets and capability views from the global atom index and final plan when the status is `accepted` or `adjusted`.
12. Write `change-capability-anchors/index.md`.
13. Write `reports/change-capability-human-plan.md` as a readable synthesis of final change packets and capability progression when the status is `accepted` or `adjusted`.
14. Write `reports/phase-4-agent-report.md` and `reports/alignment-final-report.md`.
15. Run a local artifact consistency check by inspection or deterministic parsing before finishing.

## Required Mapping Tables

`phase-4-plan-refit/pass-<NN>/atom-plan-mapping.md` must include:

| Global Atom ID | Source Document | Lines | Phase 3 Owner / Status | Phase 3 Artifact Projection | Final Owner Change | Final Owner Capability | Final Artifact Projection | Final Relation | Plan Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

`reviews/phase-4-trace/plan-refit-decision-log.md` must include:

| Decision Item | Input Evidence | Candidate Options | Decision | Output Artifact | Reason |
| --- | --- | --- | --- | --- | --- |

`change-capability-anchors/index.md` must include:

| Change | Change Packet | Capability Views | Direct Atoms | Contextual Atoms | Capabilities Advanced | Complexity Budget | Evidence Burden | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

`reports/change-capability-human-plan.md` must include readable change packets:

| Change | Closed-loop Outcome | Direct Atom Groups | Complexity Budget | Contextual Atoms / Future Constraints | Upstream Realized Baseline | Downstream Constraints | Non-Goals | Evidence Burden | Ledger Links |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

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
- change/capability coupling gate summary, including whether the final matrix avoided capability-driven one-to-one slicing
- new, split, merged, removed, reordered, or renamed changes
- new, split, merged, removed, or renamed capabilities
- atoms moved, reclassified, or left as contextual
- confirmation that every direct global atom has exactly one final owner change/capability
- confirmation that every direct global atom has final artifact projection
- confirmation that `design-obligation` and `verification-obligation` atoms were not forced into `spec-requirement`
- confirmation that final capability relations are direct `New` or `Modified` advancement only
- confirmation that the final plan is not a diagonal or same-name change/capability roadmap unless every exception is source-backed and recorded
- confirmation that change packets contain upstream baseline and downstream design context without pulling future scope into current direct ownership
- confirmation that final change complexity is implementation-ready or explicitly blocked with split options
- confirmation that every over-budget trigger was split, deferred, or justified with concrete indivisibility analysis
- confirmation that foundation changes do not directly own deferrable domain behavior
- confirmation that source atom files and the Phase 3 global atom index were not modified
- confirmation that every Phase 4 artifact passed the Artifact Language Gate
- next required step: `Start openspec-propose`, `Run Phase 3 again`, or `Blocked`

## Completion

Phase 4 ends with exactly one status in `reports/phase-4-agent-report.md`:

- `Phase 4 Status: accepted`
- `Phase 4 Status: adjusted`
- `Phase 4 Status: needs-coverage-recheck`
- `Phase 4 Status: blocked`

Use `accepted` when the Phase 1 framework remains coherent after atom-level review, final packets were derived, every capability atom sequence is coherent, every change satisfies the implementation-ready complexity gate, and the final matrix passes the Change/Capability Coupling Gate.

Use `adjusted` when the framework was refit, all final atom mappings are traceable, every capability atom sequence is coherent, every change satisfies the implementation-ready complexity gate, the final matrix passes the Change/Capability Coupling Gate, and final packets were derived.

Use `needs-coverage-recheck` when Phase 4 exposes missing, over-broad, conflicting, or semantically unclear source obligations that Phase 3 must normalize before the plan can be final.

Use `blocked` when the adjustment needs source boundaries, product decisions, or broad reanalysis that Phase 4 is not allowed to perform.

After `accepted` or `adjusted`, `openspec-propose` may start from the final change packets. After `needs-coverage-recheck`, the main agent must spawn a fresh Phase 3 review subagent. Do not start `openspec-propose` directly from `needs-coverage-recheck` or `blocked`.
