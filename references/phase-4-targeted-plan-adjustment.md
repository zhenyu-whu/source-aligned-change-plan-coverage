# Phase 4: Atom-Driven Change and Capability Plan Refit

Phase 4 runs after Phase 3 returns `Decision: coverage-complete`. At this point the obligation atom granularity is stable enough to evaluate whether the Phase 1 change/capability framework is scientifically reasonable.

Phase 4 exists to refit the plan from the normalized global atom index. It evaluates change order, capability progression, dependencies, artifact projection, and change complexity using concrete atom groups rather than the initial slicing hypothesis. It may accept the Phase 1 framework or restructure changes/capabilities. Every decision must preserve atom-level traceability and ensure each final direct atom has a downstream artifact projection.

Phase 4 MUST be performed by a fresh independent subagent. It must not rerun Phase 2 extraction and must not invent new source obligations. If Phase 4 discovers a missing or over-broad source obligation, it must return `needs-coverage-recheck` instead of silently creating new atoms outside Phase 3.

## Inputs

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/index.md`
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`
- `openspec/orchestrate/phase-works/phase-3/coverage-review.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/*.md`
- User-specified source document roots or exact source paths, for targeted context reads only when a Phase 3 handoff needs local wording.

## Outputs

Write the current refit packet directly under `openspec/orchestrate/phase-works/phase-4/`. Do not create `pass-*`, `iteration-*`, attempt-numbered, or similarly iterative subdirectories for Phase 4. If Phase 4 must run again after `needs-coverage-recheck`, update the current Phase 4 packet in place unless the user explicitly requests historical archival.

- `openspec/orchestrate/phase-works/phase-4/input-change-plan.md`
- `openspec/orchestrate/phase-works/phase-4/change-plan.md`
- `openspec/orchestrate/phase-works/phase-4/atom-plan-mapping.md`
- `openspec/orchestrate/phase-works/phase-4/capability-progression-review.md`
- `openspec/orchestrate/phase-works/phase-4/change-complexity-review.md`
- `openspec/orchestrate/phase-works/phase-4/plan-refit-decision-log.md`
- `openspec/orchestrate/phase-works/phase-4/change-plan-adjustments.md` only when the status is `adjusted`, `needs-coverage-recheck`, or `blocked`
- `openspec/orchestrate/phase-works/phase-4/phase-4-agent-report.md`
- `openspec/orchestrate/phase-works/phase-4/alignment-final-report.md`

When the status is `accepted` or `adjusted`, also write final consume-ready artifacts:

- `openspec/orchestrate/change-capability-anchors/index.md`
- `openspec/orchestrate/change-capability-anchors/<change-slug>/<change-slug>.md`
- `openspec/orchestrate/change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md`
- `openspec/orchestrate/phase-works/phase-4/change-capability-human-plan.md`

If Phase 4 accepts the input plan unchanged, still write the current Phase 4 packet and final change packets. If Phase 4 adjusts the plan, write the adjusted snapshot to `phase-works/phase-4/change-plan.md` and update root `openspec/orchestrate/change-plan.md` to the latest effective plan only after the Phase 4 packet records the input plan, output plan, and atom-plan mapping.

`phase-works/phase-2/source-obligation-atoms/` and `change-capability-anchors/obligation-atom-index.md` are upstream evidence. Do not edit them in Phase 4.

## Recommended Mechanical Helper

For reruns or large Phase 4 refits, prefer the bundled deterministic renderer instead of pasting a long one-off Python heredoc. The Phase 4 subagent still owns the semantic decisions: it must review the global atom index, decide the final roadmap, write or update the reviewed `atom-plan-mapping.md`, and prepare a JSON config that states final changes, capabilities, split analyses, decisions, adjustments, and report findings. The helper only validates and renders mechanical artifacts from those reviewed inputs.

Suggested flow:

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase4_plan_refit.py \
  --orchestrate-dir openspec/orchestrate \
  --mapping openspec/orchestrate/phase-works/phase-4/atom-plan-mapping.md \
  --print-config-template > openspec/orchestrate/phase-works/phase-4/phase4-refit.config.json
```

Then edit `phase4-refit.config.json` so every final change has the reviewed Chinese title/outcome/kind, every capability has the reviewed Chinese behavior boundary, and the reviewed decisions/split analyses/adjustments/report findings are recorded. After that, run:

```bash
python3 -m py_compile .codex/skills/source-aligned-change-plan-coverage/scripts/phase4_plan_refit.py

python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase4_plan_refit.py \
  --orchestrate-dir openspec/orchestrate \
  --mapping openspec/orchestrate/phase-works/phase-4/atom-plan-mapping.md \
  --config openspec/orchestrate/phase-works/phase-4/phase4-refit.config.json

python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase4_plan_refit.py \
  --orchestrate-dir openspec/orchestrate \
  --mapping openspec/orchestrate/phase-works/phase-4/atom-plan-mapping.md \
  --config openspec/orchestrate/phase-works/phase-4/phase4-refit.config.json \
  --write
```

Use `--output-orchestrate-dir /tmp/phase4-check/openspec/orchestrate` for a dry render into a temporary tree when reviewing the generated files before overwriting the active orchestration outputs. Do not treat the helper output as valid unless the subagent has reviewed the config and the main-agent gates pass. If validation fails, repair the mapping/config or return `needs-coverage-recheck`/`blocked`; do not weaken checks in the script.

## Artifact Language Gate

Apply the skill-level Artifact Language Gate to every Phase 4 output. Keep fixed table headers, field names, enum/status values, atom ids, paths, line ranges, capability ids, change slugs, relation tokens, and exact source phrases as required, but write all agent-authored explanatory content in Simplified Chinese.

In particular, closed-loop outcomes, behavior-boundary descriptions, roadmap values, capability progression narratives, complexity decisions, split/defer analyses, context handling, blockers, plan-decision reasons, evidence-burden descriptions, human review notes, and report summaries must be Chinese unless the entire value is only a fixed enum, ID, path, command, relation token, proof-type token, or exact source term.

After writing each Phase 4 artifact, perform the language self-check from the skill gate. If any explanation sentence remains English-dominant after ignoring IDs, paths, commands, code, fixed enum/status values, relation tokens, proof-type tokens, and exact source phrases, rewrite it before finishing Phase 4.

## Scope Rules

Phase 4 may:

- accept the Phase 1 framework when global atoms prove it is coherent
- add, remove, split, merge, reorder, or rename changes when atom groups and dependencies require it
- keep one narrow pre-business foundation change only when the first production business workflow cannot run without minimal zero-domain engineering scaffolding
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
- create a sequence of pre-business foundation, governance, state-contract, design-system, harness, or platform-hardening changes before the first production business/user workflow
- keep a pre-business domain foundation/spine change that creates domain-specific schemas or entities, domain commands/use-cases/policies, user-facing API contracts, worker or async business semantics, domain events/streams/outbox messages, identity/authorization/tenancy mappings, entitlement/accounting/delivery/export concepts, lifecycle/versioning rules, or workflow-specific observability, privacy, recovery, responsive, design-system, or verification behavior
- keep a standalone post-foundation technical change unless it has an independently runnable user/system or operational loop with concrete failure paths and archive-ready evidence
- use raw uncovered line counts as a plan-adjustment driver without semantic review
- leave any direct global atom without exactly one final owner change/capability unless it is non-direct, non-coverage, or blocked
- leave any direct global atom without final artifact projection
- leave any final direct global atom with `contextual-only`; contextual-only atoms must be moved to the context table, non-direct handling, or blocker status
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
- A valid foundation exception is normally only the first final change. It establishes only zero-domain engineering scaffolding required for the first production business workflow to run, then stops.
- After the first foundation, use business-first sequencing: advance runtime, async, UI state, object state, design-system, responsive, observability, entitlement, privacy, recovery, and verification capabilities inside the first production workflow that directly needs them.
- Do not split a reusable contract, UI state vocabulary, object specimen, design token system, visual harness, or async scaffold into its own change merely because it can be unit-tested. It needs a real business/user/system loop or must become part of a business change's design/tasks/evidence burden.
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
- Treat future domain behavior as contextual or downstream constraints until the first business change that directly implements it. Do not make a foundation or early technical change own direct atoms simply because later changes depend on their contracts.
- Preserve artifact projection independently from final owner placement. A direct atom can be implementation-owned by a change while projecting to design, tasks/proof, or spec guard rather than becoming a spec requirement; it cannot remain `contextual-only` in the final direct table.
- Prefer staged slices such as input preparation -> confirmed domain fact -> async execution -> external integration -> result projection -> hardening/delivery/operations when each slice can be verified truthfully.
- Preserve directly necessary cross-capability increments inside the same change when they share the same entry, fact, projection, failure path, and verification truth. Do not move identity, privacy, realtime state, versioning, entitlement, export, failure recovery, or observability atoms into artificial standalone changes solely to narrow the matrix row.
- After the final change/capability refit, discard Phase 1 `New`/`Modified` labels and rebuild them from final direct atom ownership. The first final change in roadmap order that directly owns at least one non-contextual atom for a capability is `New`; every later final change that directly owns a source-backed delta for that capability is `Modified`.
- A capability cannot be `Modified` before it is `New`. If an earlier change appears to modify a capability that is declared as first created later, either move the `First change` to the earlier direct owner, move those atoms to the later owner, or reclassify the earlier relation as contextual/dependency/preserve-only. Do not finish Phase 4 with a "pre-baseline Modified" relation.
- Capability relations must be derived from final packets, not from dependency notes. If a change only consumes, preserves, depends on, or evidences a capability without directly owning a source-backed atom for that capability, it must not appear as advancing that capability in the matrix, roadmap `New`/`Modified` lists, final anchors index, or human plan.

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
- `Current Change Sequence` must be computed from final direct ownership in roadmap order: include every final change whose packet directly owns at least one atom for the capability, and exclude dependency-only or contextual mentions.
- `Required Order` must name the first direct owner as the capability baseline. The same first direct owner must match the Capability Map `First change`, the first non-empty matrix cell for that capability, the first `New` entry in the Change Roadmap, and the first occurrence of that capability in `change-capability-anchors/index.md`.
- If those five surfaces disagree, Phase 4 must repair the plan artifacts before returning `accepted` or `adjusted`. If the disagreement reflects unclear atom ownership rather than stale labels, return `needs-coverage-recheck` or `blocked`.
- `New`/`Modified` labels are final-plan labels, not historical labels from Phase 1. Renaming, splitting, or moving changes/capabilities requires recomputing all labels and rewriting affected capability views.

## Change Complexity Review

Evaluate change complexity before finalizing:

| Change | Direct Atom Count | Artifact Projection Mix | Atom Groups | New Capabilities | Modified Capabilities | Primary Functional Points | Entry/Fact/Projection Count | Failure/Recovery Count | Evidence Types | Surface Families | Foundation/Business Gate Status | Budget Status | Complexity Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

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
- Prefer the earliest minimal runnable production business loop immediately after the single foundation change; defer only atoms that are not required for that loop's production truth.
- Split input preparation from downstream execution when the preparation state can be saved, revisited, validated, and verified without executing the downstream job.
- Split external integration from command/job/result semantics when an adapter contract, deterministic sandbox, or integration-disabled path can be verified truthfully and the concrete integration can be added as a later direct change.
- Split result projection, history, or interaction surfaces from upstream execution when the durable result fact can be verified independently of the richer projection loop.
- Split access/quota enforcement, delivery, observability, and operations atoms out of a feature change unless they are required to make the current feature's behavior truthful rather than merely production-complete in a future sense.
- Do not split a change solely because it advances several capabilities. If the split would create a diagonal matrix where each new change mostly owns one capability with a similar name, keep or redesign the vertical loop instead and record the reason.

### Single Foundation and Business-First Gate

Foundation changes are valid only as minimal enabling scaffolds. Treat this as a hard gate for Phase 4 plan acceptance:

- A final plan should have at most one foundation change before the first production business/user workflow. The default valid foundation is the first final change.
- A foundation change must be a zero-domain engineering bootstrap. It should directly own only repository/package skeleton, package/app boundaries, root scripts, lint/typecheck/test harnesses, configuration loading, local dependency manifests, migration tooling without business schema, empty adapter seams, empty web/worker smoke entrypoints, environment/deploy conventions, and smoke proof.
- These foundation direct atoms often project to `design-obligation`, `verification-obligation`, or `spec-guard`; only externally meaningful runtime contracts should project to `spec-requirement`.
- A foundation change must prove itself with executable checks such as dependency startup, empty migration tooling smoke, env schema validation, package/build/typecheck, and a minimal empty health/API or worker probe. "Types exist", "contract exists", "specimen renders", or "visual harness exists" is not sufficient by itself.
- A foundation change must not directly advance user/domain capabilities or business capability baselines. It must not create domain-specific schemas or entities, domain commands/use-cases/policies, user-facing API contracts, worker or async business semantics, domain events/streams/outbox messages, identity/authorization/tenancy mappings, entitlement/accounting/delivery/export concepts, lifecycle/versioning rules, operational observability, privacy workflows, recovery behavior, responsive behavior, visual quality, or design-system behavior.
- Direct domain atoms in a foundation change must be moved to the first business change that needs them or reclassified as contextual/downstream constraints. Phase 4 must not keep them in foundation by arguing that later changes will depend on their contracts; dependency is not direct ownership.
- Low-level or governance-heavy atom groups that appear after the foundation, such as action/job runtime, UI stage/overlay contracts, object disabled-state governance, design tokens, responsive proof, observability, privacy, or quota policy, must be attached to the first business workflow that directly needs them as direct deltas, design obligations, task obligations, or evidence burden unless they qualify as an independently runnable operational loop.
- A standalone post-foundation non-business change is allowed only when source evidence requires an independently runnable user/system or operational loop whose entry, fact, projection, failure path, and evidence can be archived without waiting for a later business workflow. The Phase 4 report must name that loop and explain why embedding it in the first dependent business change would be less truthful.
- A foundation change with any direct domain behavior, business table creation, or business capability advancement must be refit. Move those atoms to business changes or return `blocked`; do not record a domain-spine exception.
- A foundation change with more than 35 direct atoms or more than 1 capability advanced requires split/defer analysis. If it remains over budget, return `blocked` or record a user-facing exception with rejected split options.
- A plan with multiple pre-business foundation/governance changes must not return `accepted` or `adjusted`; Phase 4 must merge them into the single foundation, move them into the first dependent business change, defer them as contextual/evidence burden, or return `blocked`.

### Required Split Analysis

For every over-budget trigger, write a split analysis before the final decision:

| Change | Trigger | Candidate Split | Atoms / Capabilities Moved | New Closed-loop Outcome | Verification Surface | Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

Candidate split patterns include:

- scaffold-only foundation -> first production business workflow
- domain foundation/spine -> zero-domain bootstrap + first business workflows that own the domain atoms
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
- Phase 4 work path
- Assumptions and conflicts

### Capability Map

| Capability | Behavior boundary | First change | Later expansion |
| --- | --- | --- | --- |

Rules:

- Capability ids must be stable English kebab-case ids.
- Behavior boundary explains durable behavior, not implementation module.
- `First change` must be the earliest final roadmap change that directly owns at least one non-contextual global atom for the capability in its final change packet.
- `Later expansion` must summarize later final changes that directly own source-backed deltas for the same capability, or record a source-backed terminal-boundary reason when no later direct owner exists.
- First and later changes must be backed by direct global atoms. Dependency-only, preserve-only, contextual, or upstream-baseline references do not count as first or later capability advancement.
- Capability ids must not merely paraphrase final change slugs. When a capability has only one final direct change, record why it is a durable terminal boundary or refit it.

### Capability Progression Matrix

| Change | `capability-a` | `capability-b` | `capability-c` |
| --- | --- | --- | --- |
| `change-name` | Concrete atom-backed increment |  | Concrete atom-backed increment |

Rules:

- Only direct `New` or `Modified` advancement belongs in matrix cells.
- Dependency, preserve, reference-only, and contextual relations belong in notes, not matrix cells.
- Each non-empty cell must be backed by one or more global atom ids.
- The first non-empty cell in each capability column must be the same change listed as that capability's `First change`; its roadmap `Capability changes` entry must list that capability under `New`.
- Every later non-empty cell in that capability column must have a matching roadmap `Modified` entry and at least one matching direct atom in that change packet's capability ownership table.
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
  - Foundation/business gate status:
  - Budget status:
  - Split/defer analysis:
- Archive readiness:

Roadmap relation rules:

- `New` must list only capabilities whose earliest final direct owner is the current change.
- `Modified` must list only capabilities that already have an earlier final direct owner and for which the current change directly owns at least one additional source-backed atom.
- A capability listed under `New` or `Modified` must also appear in this change's final packet capability ownership table and in `change-capability-anchors/index.md`.
- A capability present only as dependency, preserve-only relation, upstream realized baseline, downstream constraint, contextual atom, evidence burden, or non-goal must not appear under `New` or `Modified`.
- When Phase 4 splits, merges, renames, reorders, or remaps atom ownership, it must regenerate all roadmap relation labels after final packets are derived. Do not carry forward Phase 1 labels.

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
- foundation/business gate status and any exception rationale
- evidence burden
- source atom and global atom index links
- blockers, or `None`

Direct atom table:

| Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Artifact Projection | Projection Rationale | Owner Capability | Atom Relation | Roles | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

All final packet `Global Atom ID` values must preserve the exact `GA-####` IDs from `change-capability-anchors/obligation-atom-index.md`; Phase 4 must not rewrite them to another global prefix or source-local atom id.

Direct table rows must use `spec-requirement`, `spec-guard`, `design-obligation`, or `verification-obligation`. `contextual-only` belongs only in the context table or non-direct classifications.

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
- The set of capability files under a change must exactly match the direct capabilities advanced by that change. Extra files for dependency-only, preserve-only, or contextual-only capabilities are not allowed.

## Final Capability Relation Consistency Check

Before writing final reports, Phase 4 must run a consistency check across the final plan and derived anchors. Write the result into `phase-works/phase-4/alignment-final-report.md` and summarize it in `phase-works/phase-4/phase-4-agent-report.md`.

Required comparison:

| Capability | Capability Map First Change | First Direct Owner From Packets | First Matrix Cell | First Roadmap `New` | First Anchor Index Occurrence | Later Direct Owners | Result | Repair If Failed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

Rules:

- All first-change columns must name the same final change for each capability.
- `Later Direct Owners` must match later non-empty matrix cells, later roadmap `Modified` entries, final packet capability ownership, and capability views.
- No capability may have a roadmap `Modified` entry, matrix `Modified` narrative, or anchor-index occurrence before its first roadmap `New`.
- No capability may appear in `change-capability-anchors/index.md` unless at least one direct atom in that change packet has that capability as final owner.
- If stale labels are the only problem, repair the Phase 4 artifacts without changing Phase 2 or Phase 3 evidence.
- If the mismatch shows that final direct atom ownership itself is ambiguous or contradictory, return `needs-coverage-recheck` or `blocked`; do not mark Phase 4 `accepted` or `adjusted`.

## Workflow

1. Read Phase 3's `phase-works/phase-3/coverage-review.md` decision and global atom index.
2. Read Phase 3 handoff items, especially atoms marked `phase-4-refit-required`, ownership ambiguities, and source-backed non-direct constraints.
3. Ensure `phase-works/phase-4/` exists and write `input-change-plan.md` directly in that directory.
4. Build the atom-driven planning graph.
5. Apply the implementation-ready complexity gate, Single Foundation and Business-First Gate, required split analysis, and Change/Capability Coupling Gate to every candidate final change.
6. Decide whether the Phase 1 framework is accepted, adjusted, needs coverage recheck, or blocked.
7. If accepted or adjusted, write `phase-works/phase-4/change-plan.md` and `phase-works/phase-4/atom-plan-mapping.md`.
8. If adjusted, update root `openspec/orchestrate/change-plan.md` to the latest effective plan after the Phase 4 snapshot and mapping are written.
9. Write `phase-works/phase-4/capability-progression-review.md`, `change-complexity-review.md`, and `plan-refit-decision-log.md`.
10. If the status is `adjusted`, `needs-coverage-recheck`, or `blocked`, write `phase-works/phase-4/change-plan-adjustments.md` with the plan-impact and next-action summary.
11. Derive final `change-capability-anchors/<change-slug>/` packets and capability views from the global atom index and final plan when the status is `accepted` or `adjusted`.
12. Write `change-capability-anchors/index.md`.
13. Run the Final Capability Relation Consistency Check. Repair stale `First change`, matrix cells, roadmap `New`/`Modified` labels, final anchors index rows, capability views, and human-plan summaries before proceeding.
14. Write `phase-works/phase-4/change-capability-human-plan.md` as a readable synthesis of final change packets and capability progression when the status is `accepted` or `adjusted`.
15. Write `phase-works/phase-4/phase-4-agent-report.md` and `phase-works/phase-4/alignment-final-report.md`.
16. Run a local artifact consistency check by inspection or deterministic parsing before finishing.

## Required Mapping Tables

`phase-works/phase-4/atom-plan-mapping.md` must include:

| Global Atom ID | Source Document | Lines | Phase 3 Owner / Status | Phase 3 Artifact Projection | Final Owner Change | Final Owner Capability | Final Artifact Projection | Final Relation | Plan Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

`phase-works/phase-4/plan-refit-decision-log.md` must include:

| Decision Item | Input Evidence | Candidate Options | Decision | Output Artifact | Reason |
| --- | --- | --- | --- | --- | --- |

`change-capability-anchors/index.md` must include:

| Change | Change Packet | Capability Views | Direct Atoms | Contextual Atoms | Capabilities Advanced | Complexity Budget | Evidence Burden | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

`phase-works/phase-4/change-capability-human-plan.md` must include readable change packets:

| Change | Closed-loop Outcome | Direct Atom Groups | Complexity Budget | Contextual Atoms / Future Constraints | Upstream Realized Baseline | Downstream Constraints | Non-Goals | Evidence Burden | Ledger Links |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

It must also include a capability progression narrative:

| Capability | Baseline Change | Refinement / Hardening / Extension Changes | Atom Progression Summary | Human Review Notes |
| --- | --- | --- | --- | --- |

## Phase 4 Report

`phase-works/phase-4/phase-4-agent-report.md` must include:

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
- confirmation that Capability Map `First change`, progression matrix first cells, roadmap `New`/`Modified` labels, final packet capability ownership, capability views, anchor index, and human plan all agree after the refit
- confirmation that the final plan is not a diagonal or same-name change/capability roadmap unless every exception is source-backed and recorded
- confirmation that change packets contain upstream baseline and downstream design context without pulling future scope into current direct ownership
- confirmation that final change complexity is implementation-ready or explicitly blocked with split options
- confirmation that every over-budget trigger was split, deferred, or justified with concrete indivisibility analysis
- confirmation that the final plan has at most one pre-business foundation change, or records a blocker/explicit exception with an independently runnable loop
- confirmation that foundation changes do not directly own deferrable domain behavior and that post-foundation low-level capability deltas are advanced inside the first business workflow that needs them
- confirmation that source atom files and the Phase 3 global atom index were not modified
- confirmation that every Phase 4 artifact passed the Artifact Language Gate
- next required step: `Start openspec-propose`, `Run Phase 3 again`, or `Blocked`

## Completion

Phase 4 ends with exactly one status in `phase-works/phase-4/phase-4-agent-report.md`:

- `Phase 4 Status: accepted`
- `Phase 4 Status: adjusted`
- `Phase 4 Status: needs-coverage-recheck`
- `Phase 4 Status: blocked`

Use `accepted` when the Phase 1 framework remains coherent after atom-level review, final packets were derived, every capability atom sequence is coherent, every change satisfies the implementation-ready complexity gate, the final plan passes the Single Foundation and Business-First Gate, and the final matrix passes the Change/Capability Coupling Gate.

Use `adjusted` when the framework was refit, all final atom mappings are traceable, every capability atom sequence is coherent, every change satisfies the implementation-ready complexity gate, the final plan passes the Single Foundation and Business-First Gate, the final matrix passes the Change/Capability Coupling Gate, and final packets were derived.

Use `needs-coverage-recheck` when Phase 4 exposes missing, over-broad, conflicting, or semantically unclear source obligations that Phase 3 must normalize before the plan can be final.

Use `blocked` when the adjustment needs source boundaries, product decisions, or broad reanalysis that Phase 4 is not allowed to perform.

After `accepted` or `adjusted`, `openspec-propose` may start from the final change packets. After `needs-coverage-recheck`, the main agent must spawn a fresh Phase 3 review subagent. Do not start `openspec-propose` directly from `needs-coverage-recheck` or `blocked`.
