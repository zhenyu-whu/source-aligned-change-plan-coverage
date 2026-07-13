# Phase 5: Atom-Driven Change and Capability Plan Refit

Phase 5 runs after Phase 3 returns `Decision: coverage-complete` and Phase 4 returns `Phase 4 Status: grounded`. At this point the obligation atom granularity is stable and the original source windows behind the initial change/capability framework have been copied into Phase 4 reviewer-facing dossiers. Phase 5 must not make plan-refit judgments from atom summaries alone: it must consume the Phase 4 source-window dossiers and semantic profiles as the grounding evidence for every split, merge, reorder, rename, ownership move, relation change, and complexity decision.

Phase 5 exists to refit the plan from the normalized global atom index and Phase 4 source-window semantic dossiers. It evaluates change order, spec capability progression, dependencies, artifact projection, and change complexity using concrete source-backed atom groups and their original source context rather than the initial slicing hypothesis. It may accept the Phase 1 framework or restructure changes/capabilities. Every decision must preserve atom-level traceability, give each executable direct atom exactly one owner Change, and ensure each final direct atom has a downstream artifact projection. Capability impact is orthogonal metadata, not co-ownership.

Phase 5 MUST be performed by a fresh independent subagent. It must not rerun Phase 2 extraction and must not invent new source obligations. If Phase 5 discovers a missing or over-broad source obligation, it must return `needs-coverage-recheck` instead of silently creating new atoms outside Phase 3.

## Inputs

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/index.md`
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.json` as canonical global atom index
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.md` as reviewer mirror
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/index.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/source-window-index.json` as canonical Phase 4 source-window index
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-change/*.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-capability/*.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-grounding-issues.md`
- `openspec/orchestrate/phase-works/phase-4/phase-4-agent-report.md`
- `openspec/orchestrate/phase-works/phase-3/coverage-review.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/*.json` as canonical Phase 3 trace sidecars
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/*.md` as reviewer mirrors
- User-specified source document roots or exact source paths, for targeted context reads only when a Phase 4 dossier cites a window that must be verified locally.

## Outputs

Write the current refit packet directly under `openspec/orchestrate/phase-works/phase-5/`. Do not create `pass-*`, `iteration-*`, attempt-numbered, or similarly iterative subdirectories for Phase 5. If Phase 5 must run again after `needs-coverage-recheck`, update the current Phase 5 packet in place unless the user explicitly requests historical archival.

- `openspec/orchestrate/phase-works/phase-5/source-window-refit-trace.md`
- `openspec/orchestrate/phase-works/phase-5/change-plan-adjustments.md` only when the status is `adjusted`, `needs-coverage-recheck`, or `blocked`
- `openspec/orchestrate/phase-works/phase-5/phase-5-agent-report.md`
- `openspec/orchestrate/trace/phase-5.trace.json`

When the status is `accepted` or `adjusted`, also write terminal mapping and final consume-ready artifacts:

- `openspec/orchestrate/phase-works/phase-5/change-plan.md`
- `openspec/orchestrate/phase-works/phase-5/input-change-plan.md`
- `openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json`
- `openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.md` rendered from the matching JSON
- `openspec/orchestrate/phase-works/phase-5/final-packet-index.json`
- `openspec/orchestrate/phase-works/phase-5/capability-progression-review.md`
- `openspec/orchestrate/phase-works/phase-5/change-complexity-review.md`
- `openspec/orchestrate/phase-works/phase-5/plan-refit-decision-log.md`
- `openspec/orchestrate/phase-works/phase-5/alignment-final-report.md`
- `openspec/orchestrate/change-capability-anchors/index.md`
- `openspec/orchestrate/change-capability-anchors/<change-slug>/<change-slug>.md`
- `openspec/orchestrate/change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md`
- `openspec/orchestrate/phase-works/phase-5/change-capability-human-plan.md`

When the status is `needs-coverage-recheck` or `blocked`, do not fabricate terminal mapping or final packet artifacts. Write `trace/phase-5.trace.json`, `phase-5-agent-report.md`, `source-window-refit-trace.md`, and `change-plan-adjustments.md` with the source-window-backed reason for the recheck or blocker.

If Phase 5 accepts the input plan unchanged, still write the current Phase 5 packet and final change packets. If Phase 5 adjusts the plan, write the adjusted snapshot to `phase-works/phase-5/change-plan.md` and update root `openspec/orchestrate/change-plan.md` to the latest effective plan only after the Phase 5 packet records the input plan, output plan, and atom-plan mapping.

`phase-works/phase-2/source-obligation-atoms/`, canonical `change-capability-anchors/obligation-atom-index.json` plus its Markdown mirror, and `phase-works/phase-4/source-window-dossiers/` are upstream evidence. Do not edit them in Phase 5.

After the writer finishes, Phase 5 must pass the reviewer/repair loop from `references/reviewer-repair-loop.md`: the main agent refreshes `trace/manifest.json`, runs the phase validator, spawns a fresh independent refit reviewer subagent, spawns a fresh independent Phase 5 repair-writer subagent if artifact changes are needed, reruns validator after refreshing the manifest, spawns a fresh independent reviewer again after repair, then spawns a fresh independent final integration reviewer before handing off to `openspec-propose`.

Phase 4 source-window dossiers and semantic profiles are the source-grounding input for Phase 5. `source-window-refit-trace.md` is the Phase 5 decision trace that explains how those input source-window profiles were transformed into final changes/capabilities: which original atoms stayed together, moved, split, merged, became contextual/dependency/evidence/non-goal, and why the adjusted unit remains a truthful engineering delivery slice.

## Recommended Mechanical Helper

For reruns or large Phase 5 refits that can produce `accepted` or `adjusted`, prefer the bundled deterministic helper instead of pasting a long one-off Python heredoc. The Phase 5 subagent still owns the semantic decisions: it must review the Phase 4 source-window dossiers, review the global atom index, decide the final roadmap, write or update the reviewed canonical `atom-plan-mapping.json`, and prepare a JSON config that states final changes, capabilities, split analyses, decisions, adjustments, and report findings. The helper renders `atom-plan-mapping.md` from JSON and renders mechanical final artifacts from those reviewed inputs. If the reviewed status is `needs-coverage-recheck` or `blocked`, do not run the final-packet renderer to fabricate terminal artifacts.

Do not run the helper as a substitute for Phase 4 source-window grounding. `phase-works/phase-4/source-window-dossiers/`, `phase-works/phase-4/source-window-semantic-profile-review.md`, and `phase-works/phase-5/source-window-refit-trace.md` must be written and reviewed before helper-rendered final packets are treated as valid.

Suggested flow:

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase5_plan_refit.py \
  --orchestrate-dir openspec/orchestrate \
  --mapping openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json \
  --print-config-template > openspec/orchestrate/phase-works/phase-5/phase5-refit.config.json
```

Then edit `phase5-refit.config.json` so every final change has the reviewed Chinese title/outcome/kind, every capability has the reviewed Chinese behavior boundary, and the reviewed decisions/split analyses/adjustments/report findings are recorded. `capabilities` may be `[]` when no business spec delta exists; in that case the generated Capability Map and Matrix must retain their headings and state `无业务 Capability delta` without malformed empty tables. After that, run:

```bash
python3 -m py_compile .codex/skills/source-aligned-change-plan-coverage/scripts/phase5_plan_refit.py

python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase5_plan_refit.py \
  --orchestrate-dir openspec/orchestrate \
  --mapping openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json \
  --config openspec/orchestrate/phase-works/phase-5/phase5-refit.config.json

python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase5_plan_refit.py \
  --orchestrate-dir openspec/orchestrate \
  --mapping openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json \
  --config openspec/orchestrate/phase-works/phase-5/phase5-refit.config.json \
  --write \
  --validate-rendered
```

Use `--output-orchestrate-dir /tmp/phase5-check/openspec/orchestrate` for a dry render into a temporary tree when reviewing the generated files before overwriting the active orchestration outputs. Do not treat the helper output as valid unless the subagent has reviewed the config and the main-agent gates pass. If validation fails, repair the mapping/config or return `needs-coverage-recheck`/`blocked`; do not weaken checks in the script.

After helper render, run:

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/validate_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --phase phase-5 \
  --complete \
  --json
```

## Artifact Language Gate

Apply the skill-level Artifact Language Gate to every Phase 5 output. Keep fixed table headers, field names, enum/status values, atom ids, paths, line ranges, capability ids, change slugs, relation tokens, and exact source phrases as required, but write all agent-authored explanatory content in Simplified Chinese.

In particular, closed-loop outcomes, behavior-boundary descriptions, roadmap values, capability progression narratives, complexity decisions, split/defer analyses, context handling, blockers, plan-decision reasons, evidence-burden descriptions, human review notes, and report summaries must be Chinese unless the entire value is only a fixed enum, ID, path, command, relation token, proof-type token, or exact source term.

After writing each Phase 5 artifact, perform the language self-check from the skill gate. If any explanation sentence remains English-dominant after ignoring IDs, paths, commands, code, fixed enum/status values, relation tokens, proof-type tokens, and exact source phrases, rewrite it before finishing Phase 5.

## Scope Rules

Phase 5 may:

- accept the Phase 1 framework when global atoms prove it is coherent
- add, remove, split, merge, reorder, or rename changes when atom groups and dependencies require it
- emit one qualifying pre-business foundation candidate as the first executable foundation change
- add, remove, split, merge, or rename capabilities when atoms reveal a durable behavior boundary gap
- move a global atom to a different owner Change when Phase 3 left placement to refit or when sequencing proves the initial candidate Change was wrong
- assign or revise `final-capability-impact`, `final-target-capability`, and source-explicit `related-capabilities[]` when source windows prove the Phase 3 metadata was unresolved or incorrect
- reclassify a global atom as contextual future-compatibility, dependency, preserve, reference, later-change, or explicit non-goal when it constrains design but is not current direct scope
- resolve final owner placement for atoms marked `phase-5-refit-required`
- adjust final artifact projection when Phase 3's projection is too broad, too narrow, or no longer matches final change packet use
- stage capability maturity as baseline -> refinement/hardening/extension using distinct source-backed atom deltas
- derive final per-change and per-capability atom files from the global atom index
- cite Phase 4 source-window dossier evidence when deciding plan refit
- read targeted source context around Phase 3/4 handoff items when needed to verify wording or dependency rationale already cited by Phase 4 dossiers

Phase 5 must not:

- rerun Phase 2 globally
- edit Phase 2 source atom files
- edit Phase 3 coverage outputs or the global atom index
- edit Phase 4 source-window dossier outputs
- generate replacement source-window dossiers that bypass Phase 4
- invent new atoms without Phase 3 normalization
- emit more than one pre-business foundation/governance candidate, place a foundation change after a business change, or keep a standalone low-level business change without an independently runnable user/system or operational loop
- use raw uncovered line counts as a plan-adjustment driver without semantic review
- treat Phase 4 source-window dossiers as permission to extract, rewrite, merge, split, or invent new obligation atoms outside Phase 3
- decide change splits, merges, reorders, capability boundaries, or foundation executable handling from atom counts or summaries alone when the corresponding Phase 4 source windows are available
- leave any executable direct global atom without exactly one final owner Change, unless it is non-direct, non-coverage, or blocked
- leave any direct global atom without final artifact projection
- leave any final direct global atom with `contextual-only`; contextual-only atoms must be moved to the context table, non-direct handling, or blocker status
- force a `design-obligation` or `verification-obligation` atom into specs as a `spec-requirement` merely because it is direct
- give an ordinary `design-obligation` or `verification-obligation` anything other than `final-capability-impact: none` and `final-target-capability: none`; such atoms remain direct and Change-owned
- return `accepted` or `adjusted` while any row has `final-capability-impact: unresolved`
- use `related-capabilities[]` as a target substitute, ownership surface, progression input, capability-view input, or advanced-capability complexity input
- leave duplicated direct ownership unresolved
- create one capability per page, table, SDK, queue, external service, component, or source document section
- hide future obligations inside early changes unless they affect current design as contextual or preserve constraints

If an adjustment cannot be made from Phase 3 findings plus targeted source context, return `blocked` or `needs-coverage-recheck` and explain which phase must run next.

## Refit Method

Phase 5 must first review Phase 4 source-window dossiers and semantic profiles, then build the atom-driven planning graph.

Phase 5 refit is not atom-count-based splitting. Atom count is a later complexity signal only. The required order is:

```text
Phase 4 source-window dossiers and semantic profiles
-> engineering delivery judgment for input changes/capabilities
-> final change order and capability boundary decisions
-> GA-#### final Change ownership/projection/relation/capability-impact mapping
-> atom-count and complexity budget review
```

Phase 5 must not start by clustering atoms, sorting by atom counts, or splitting oversized input changes mechanically. It must first decide what source-window-backed business/system outcomes are implementable, testable, manually acceptable, and archive-ready.

### Source-Window Profile Intake

Before changing the plan, read:

- `phase-works/phase-4/source-window-dossiers/index.md`
- all `phase-works/phase-4/source-window-dossiers/by-input-change/*.md`
- all `phase-works/phase-4/source-window-dossiers/by-input-capability/*.md`
- `phase-works/phase-4/source-window-semantic-profile-review.md`
- `phase-works/phase-4/source-window-grounding-issues.md`
- `phase-works/phase-4/phase-4-agent-report.md`

Rules:

- Treat Phase 4 dossiers as immutable grounding evidence.
- Every accepted, adjusted, split, merge, reorder, rename, moved atom, contextual downgrade, dependency classification, evidence-burden classification, or non-goal classification must cite a Phase 4 dossier or semantic profile row.
- If Phase 4 reports `Phase 4 Status: needs-coverage-recheck` or `blocked`, stop; Phase 5 must not run.
- If Phase 4 reports `grounded` but a required source-window profile is missing for an input change/capability that Phase 5 must judge, return `blocked` or ask for a fresh Phase 4 grounding pass. Do not silently regenerate the missing dossier inside Phase 5.
- If Phase 4 source windows show several capabilities are directly required for one truthful business loop, keep those capability deltas together even when the atom count is high, unless a source-window-backed split preserves independent acceptance.
- If Phase 4 source windows show one input change mixes multiple independently acceptable business outcomes, split, defer, or record why the source windows prove indivisibility.
- If Phase 4 source windows show technical preparation without an independently runnable operational loop, apply the Foundation Executable Gate instead of treating it as ordinary business direct scope.

### Source Window Semantic Grounding Gate

Before building final atom ownership, Phase 5 must judge the initial change plan and every candidate final change from Phase 4 source-window semantics.

For the initial change plan, answer:

- Does the input change describe a complete business/system loop whose entry, fact, projection, failure path, and verification truth can be delivered together?
- Does it mix multiple business outcomes that can be independently implemented, manually accepted, and archived?
- Does it split capabilities that the source windows show must be delivered together for one truthful loop?
- Does it package pure technical preparation as a business change without an independently runnable operational loop?
- Does it move domain behavior, user-facing API contracts, business worker semantics, entitlement/export concepts, project/figure/version semantics, or recovery/privacy behavior into a foundation change instead of the first business change that needs it?
- Does any later change depend on a fact, state, contract, entitlement, version, asset, or lifecycle rule that is not established by an earlier direct owner?
- Is each capability a durable behavior boundary, or is it only a temporary implementation module, page, table, source section, SDK, queue, provider, component, or one-change alias?
- Does the roadmap order follow behavior maturity, or does any early change mainly collect future prerequisites?
- For web-system sources, does the early product sequence produce a thin end-to-end user-visible behavior rather than only a page shell or setup/governance bundle?

Only after these questions are answered may Phase 5 map `GA-####` rows to final ownership. At that point each relevant global atom must be assigned:

- final owner type
- exactly one final executable Change when the row is executable/direct
- final artifact projection
- final relation: `direct`, contextual, dependency, evidence-burden, preserve/reference, explicit non-goal, later-change, or blocker
- `final-capability-impact`: `new`, `modified`, `none`, or foundation-only `foundation-substrate`
- `final-target-capability`: a concrete declared capability for `new` / `modified`, `none` for `none`, or `runtime-substrate-foundation` for `foundation-substrate`
- `related-capabilities[]`: unique declared, source-explicit, non-owning supporting associations; default `[]` and exclude the target capability

Every final change must pass this reviewer-facing gate:

| Gate Question | Required Evidence |
| --- | --- |
| Which source windows does this final change cite? | Phase 4 dossier paths and line ranges. |
| What business/system semantics do those source windows express together? | Chinese source-window semantic profile summary. |
| Why should these atoms be delivered in one change? | Entry/fact/projection/failure/verification cohesion. Foundation atoms belong only in the first executable foundation packet when they are zero-domain engineering substrate. |
| Why does this change appear at this point in the roadmap? | Upstream realized baseline and downstream dependency explanation. |
| How can a human manually accept this completed change? | Concrete acceptance scenario and observable result. |
| Which source obligations were made contextual, dependency, evidence-burden, preserve/reference, later-change, or non-goal, and why are they not direct scope? | `source-window-refit-trace.md`, `atom-plan-mapping.md`, and final packet context/non-goal/evidence tables. |

If a final change cannot answer all gate questions, Phase 5 must split, merge, reorder, rename, reclassify atoms, return `needs-coverage-recheck`, or return `blocked`. A final change must not be accepted merely because its atom count falls within the target budget.

After final refit decisions, write `source-window-refit-trace.md` using the table defined in Required Mapping Tables. The trace must make it clear which Phase 4 source-window-backed atoms were reconstructed into each adjusted final Change and, for spec deltas, target capability. Any split, merge, reorder, rename, moved atom, contextual downgrade, dependency classification, evidence-burden classification, or non-goal classification must cite the relevant Phase 4 source-window dossier.

### Behavior Maturity Ordering Gate

Before accepting final order, judge whether the roadmap follows behavior maturity rather than prerequisite availability.

For typical web systems, early product changes should create the thinnest end-to-end user-visible behavior: a real page or user-facing entry point with action, system fact, visible result, basic failure handling, and verification. A static UI shell or standalone prerequisite collection does not satisfy this gate.

A support, governance, or operation-heavy change may appear before the behavior it supports only when it is strictly necessary for truthful acceptance of the next behavior, or when it is independently acceptable as an operational/system loop with its own entry, fact, projection, failure, and verification.

If a change is ordered early mainly because later changes will need it, move its atoms into the first behavior that needs them as direct/design/evidence burden, defer them as contextual/later-change, or record a blocker with source-backed rationale.

### Atom-Driven Planning Graph

After source-window profile intake, build an atom-driven planning graph:

| Global Atom ID | Source Obligation | Current Candidate Owner Change | Current Capability Impact | Current Target Capability | Current Related Capabilities | Current Artifact Projection | Dependency Atoms | Candidate Final Change | Candidate Final Capability Impact | Candidate Final Target Capability | Candidate Final Related Capabilities | Candidate Final Artifact Projection | Sequence Impact | Complexity Impact | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Use these rules:

- A final executable change should represent a reviewable, implementable, verifiable user/system loop.
- A final change is also the unit a later AI agent will implement in one focused `openspec-apply-change` pass. Closed-loop coherence alone does not justify a large change.
- Foundation handling must pass the Foundation Executable Gate, and business sequencing must start after any first executable foundation change.
- Do not split reusable contracts, UI state vocabularies, object specimens, design token systems, visual harnesses, or async scaffolds into standalone changes merely because they can be unit-tested. They need real business/user/system loops or must become part of a business change's design/tasks/evidence burden.
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
- Preserve artifact projection independently from final owner Change placement. A direct atom can be implementation-owned by a Change while projecting to design, tasks/proof, or spec guard rather than becoming a spec requirement; it cannot remain `contextual-only` in the final direct table.
- Assign `new` / `modified` only to direct `spec-requirement` / `spec-guard` rows with a concrete target capability. Assign `none` / `none` to ordinary direct design/verification rows and all non-direct rows without downgrading their Change ownership.
- Keep `related-capabilities[]` only when the cited source window explicitly associates the atom with those stable capability ids. Related ids never affect Change ownership, progression, capability views, or complexity counts.
- Prefer staged slices such as input preparation -> confirmed domain fact -> async execution -> external integration -> result projection -> hardening/delivery/operations when each slice can be verified truthfully.
- Preserve directly necessary cross-capability increments inside the same change when they share the same entry, fact, projection, failure path, and verification truth. Do not move identity, privacy, realtime state, versioning, entitlement, export, failure recovery, or observability atoms into artificial standalone changes solely to narrow the matrix row.
- Apply the Capability Relation Invariants below when rebuilding `New`/`Modified` labels and capability advancement surfaces.

### Capability Relation Invariants

After final refit, discard Phase 1 `New`/`Modified` labels and rebuild capability advancement from explicit Phase 5 `final-capability-impact` plus `final-target-capability` values. Do not infer impact from Change ownership, artifact counts, related capabilities, or renderer order.

- Business progression consumes only direct `spec-requirement` / `spec-guard` rows whose impact is `new` or `modified` and whose target is a concrete declared business capability.
- For each `(final-owner-change, final-target-capability)` pair, all contributing rows must use the same impact. Mixed `new` / `modified` values for one pair are invalid.
- In roadmap order, the first Change with a spec delta for a target capability must explicitly use `new`; every later Change with an additional source-backed spec delta for the same target must explicitly use `modified`.
- A renderer or reviewer must validate these explicit values, not derive or repair them silently from first occurrence.
- Dependency-only, preserve-only, upstream-baseline, downstream-constraint, contextual, evidence-burden, reference, later-change, and non-goal relations do not count as capability advancement.
- Ordinary direct `design-obligation` / `verification-obligation` rows use `none` / `none`; source-explicit `related-capabilities[]` remain non-owning and do not count as advancement.
- `foundation-substrate` with target `runtime-substrate-foundation` is the only non-spec special case. It receives its dedicated foundation view but stays outside business `New` / `Modified` progression.
- Capability Map `First change`, the first non-empty matrix cell, the first roadmap `New` entry, final packet target/impact metadata, the first anchor-index occurrence, capability views, and the human plan must all agree.
- If stale labels are the only problem, repair the Phase 5 canonical mapping/config and rerender. If the mismatch reflects ambiguous final Change ownership or capability target/impact, return `needs-coverage-recheck` or `blocked`.

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
- `Current Change Sequence` must be computed from explicit final `new` / `modified` target-capability pairs in roadmap order. Exclude change-only design/verification rows, related-only mentions, dependency-only rows, and contextual mentions.
- `Required Order` must apply the Capability Relation Invariants and identify the baseline direct owner.
- If plan surfaces disagree, repair the canonical mapping/config and rerender before returning `accepted` or `adjusted`; if final Change ownership or spec target/impact is unclear, return `needs-coverage-recheck` or `blocked`.

## Change Complexity Review

Evaluate change complexity before finalizing:

| Change | Direct Atom Count | Artifact Projection Mix | Atom Groups | New Capabilities | Modified Capabilities | Primary Functional Points | Entry/Fact/Projection Count | Failure/Recovery Count | Evidence Types | Surface Families | Foundation/Business Gate Status | Budget Status | Complexity Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Use direct atom count as a complexity signal, not as a source coverage goal. Fine-grained atoms are expected, but a final change with many direct atoms still creates implementation, review, and archival risk.

Rules:

- Target budget: 20-60 direct atoms, one primary functional point, directly necessary capability deltas only, at most two primary surface families, and a compact evidence burden. More than one new or modified capability is acceptable when those deltas are required for the same truthful loop.
- Count `New Capabilities`, `Modified Capabilities`, and unrelated capability over-budget triggers only from distinct explicit `new` / `modified` target capabilities. Exclude `none`, `foundation-substrate`, and every `related-capabilities[]` entry.
- Over-budget trigger: any change with more than 80 direct atoms, more than 4 unrelated directly advanced capabilities, an incoherent artifact projection mix, more than 12 failure/recovery atoms, more than 2 primary entry points, more than 2 fact families, more than 2 projection families, more than 3 evidence types, or more than 3 surface families must be split, deferred, or justified with concrete indivisibility evidence. Related cross-cutting capability deltas are not an over-budget trigger by count alone.
- Hard split/blocker trigger: any change with more than 120 direct atoms or more than 6 unrelated directly advanced capabilities that do not share the same entry/fact/projection/failure truth must not be marked `accepted` or `adjusted` as-is. Phase 5 must split it, move atoms to later changes/context, or return `blocked` for a user slicing decision.
- A `Keep` decision for an over-budget change must list rejected split candidates and explain why each would break truthfulness. "One coherent loop", "shared infrastructure", or "packet-level evidence grouping" is not sufficient.
- Do not split a change merely because direct atom count exceeds the target range. Split only when the Source Window Semantic Grounding Gate shows independently acceptable business/system outcomes, invalid sequencing, false foundation ownership, non-durable capability boundaries, incoherent evidence surfaces, or unrelated entry/fact/projection/failure truth.
- Split a change when it contains multiple atom groups that can pass the Closed-loop Test independently.
- Split a change when it advances many capabilities only because shared infrastructure made grouping convenient.
- Split a change when the evidence burden spans many unrelated proof surfaces and would make review/archival ambiguous.
- Keep a change together when splitting would force fake stubs, break one user/system loop, or make either side unverifiable.
- Prefer the earliest minimal runnable production business loop as the first executable change; defer only atoms that are not required for that loop's production truth.
- Split input preparation from downstream execution when the preparation state can be saved, revisited, validated, and verified without executing the downstream job.
- Split external integration from command/job/result semantics when an adapter contract, deterministic sandbox, or integration-disabled path can be verified truthfully and the concrete integration can be added as a later direct change.
- Split result projection, history, or interaction surfaces from upstream execution when the durable result fact can be verified independently of the richer projection loop.
- Split access/quota enforcement, delivery, observability, and operations atoms out of a feature change unless they are required to make the current feature's behavior truthful rather than merely production-complete in a future sense.
- Do not split a change solely because it advances several capabilities. If the split would create a diagonal matrix where each new change mostly owns one capability with a similar name, keep or redesign the vertical loop instead and record the reason.

### Foundation Executable Gate

Foundation candidates are valid only as minimal enabling scaffolds and may be emitted only as the first executable final change. Treat this as a hard gate for Phase 5 plan acceptance:

- A terminal Phase 5 plan may have at most one foundation candidate. If it qualifies, Phase 5 writes it as the first final packet and the first `final-packet-index.json` row with `change-kind: foundation`.
- Business changes use `change-kind: business`. The technical foundation capability `runtime-substrate-foundation` may appear in the foundation packet and capability view, but it must not count as business capability `New` / `Modified` progression.
- Foundation direct rows in `atom-plan-mapping.json` must use `final-owner-type: executable-change`, `final-owner-change: <foundation-change-slug>`, `final-capability-impact: foundation-substrate`, `final-target-capability: runtime-substrate-foundation`, and `final-relation: direct`. Their `related-capabilities[]` follows the same source-explicit, non-owning structural rule as all other rows.
- `foundation-substrate` is the sole exception that allows `design-obligation` / `verification-obligation` rows to receive a non-`none` capability impact. It exists only to derive the dedicated foundation view and never enters business progression or advanced-capability counts.
- A foundation change may include only zero-domain engineering substrate: repository/package skeleton, package/app boundaries, root scripts, lint/typecheck/test harnesses, configuration loading, local dependency manifests, migration tooling without business schema, empty adapter seams, empty web/worker smoke entrypoints, environment/deploy conventions, and smoke/conformance proof expectations.
- Foundation atoms keep their original source trace and artifact projection, often `design-obligation`, `verification-obligation`, or `spec-guard`. Later proposal artifacts may generate specs, runtime acceptance, verification, and tasks only when those artifacts express current observable engineering substrate facts for the foundation change.
- Direct domain behavior, business table creation, user-facing API contracts, worker or async business semantics, identity/authorization/tenancy mappings, entitlement/accounting/delivery/export concepts, lifecycle/versioning rules, operational observability, privacy workflows, recovery behavior, responsive behavior, visual quality, or design-system behavior must move to the first business change that directly needs them.
- Low-level or governance-heavy atom groups such as action/job runtime, UI stage/overlay contracts, object disabled-state governance, design tokens, responsive proof, observability, privacy, or quota policy must be attached to the first business workflow that directly needs them unless source evidence requires an independently runnable operational loop.
- A plan with multiple pre-business foundation/governance candidates must merge them into the single executable foundation change, move them into business changes, defer them as contextual/evidence burden, or return `blocked`.

### Required Split Analysis

For every over-budget trigger, write a split analysis before the final decision:

| Change | Trigger | Candidate Split | Atoms / Capabilities Moved | New Closed-loop Outcome | Verification Surface | Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

Candidate split patterns include:

- scaffold-only foundation candidate -> executable foundation change + first production business workflow
- domain foundation/spine candidate -> zero-domain executable foundation change + first business workflows that own the domain atoms
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
- The Phase 5 report must summarize this audit with counts or qualitative findings sufficient for a reviewer to see why the plan did not collapse into change/capability one-to-one mapping.

## Effective Change Plan Requirements

The final `change-plan.md` must include:

### Inputs

- Source documents read
- Phase 3 global atom index path
- Phase 5 work path
- Assumptions and conflicts

### Capability Map

| Capability | Behavior boundary | First change | Later expansion |
| --- | --- | --- | --- |

Rules:

- Capability ids must be stable English kebab-case ids.
- Behavior boundary explains durable behavior, not implementation module.
- `First change` and `Later expansion` must follow the Capability Relation Invariants and be backed by direct global atoms.
- Capability ids must not merely paraphrase final change slugs. When a capability has only one final direct change, record why it is a durable terminal boundary or refit it.
- A plan with no business spec delta may use `capabilities: []`. Keep the `Capability Map` heading and write `无业务 Capability delta`; do not emit a malformed empty table or invent a technical capability. A qualifying foundation remains the separate special case.

### Capability Progression Matrix

| Change | `capability-a` | `capability-b` | `capability-c` |
| --- | --- | --- | --- |
| `change-name` | Concrete atom-backed increment |  | Concrete atom-backed increment |

Rules:

- Only direct `New` or `Modified` advancement belongs in matrix cells.
- Dependency, preserve, reference-only, and contextual relations belong in notes, not matrix cells.
- Matrix exclusion is not coverage exclusion. Every excluded non-direct atom that has a final owner change must still appear explicitly in that change's final packet context/dependency/evidence/preserve/non-goal handling.
- Each non-empty cell must be backed by one or more global atom ids.
- First and later non-empty cells must follow the Capability Relation Invariants and match roadmap relation labels plus final packet ownership.
- The matrix must pass the Change/Capability Coupling Gate. A mostly diagonal matrix requires source-backed exceptions, not silence.
- When `capabilities: []`, keep the `Capability Progression Matrix` heading and write `无业务 Capability delta`; do not emit capability columns or infer progression from change-only rows.

### Change Roadmap

For each final change:

- Change name:
- Closed-loop outcome:
- Source-window grounding:
  - Input source-window dossiers:
  - Source-backed semantic profile:
  - Refit trace:
- Source Window Semantic Grounding Gate:
  - Source windows cited:
  - Combined business/system semantics:
  - Why these atoms belong together:
  - Why this roadmap position is valid:
  - Manual acceptance scenario:
  - Non-direct obligation handling:
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

- `New` and `Modified` lists must be derived from explicit `final-capability-impact` / `final-target-capability` pairs, follow the Capability Relation Invariants, and match final packets plus `change-capability-anchors/index.md`.
- When Phase 5 splits, merges, renames, reorders, or remaps atom ownership, it must regenerate all roadmap relation labels after final packets are derived. Do not carry forward Phase 1 labels.
- Every final change must cite the input source-window dossiers and refit trace rows that justify its closed-loop outcome and ordering. A final change with only atom-count or capability-count rationale is incomplete.

## Final Change Packets

Each `change-capability-anchors/<change-slug>/<change-slug>.md` final packet must include:

- change name
- closed-loop outcome
- source-window grounding links and semantic profile summary
- Source Window Semantic Grounding Gate answer summary
- final direct owner atoms grouped by spec target capability or change-only artifact projection
- final artifact projection for every direct atom
- contextual atoms and future constraints that affect current design
- upstream realized baseline atoms from earlier changes
- downstream constraints that must not be designed out
- explicit non-goals
- complexity budget status, over-budget triggers, and split/defer decisions
- executable roadmap status and foundation executable handling summary
- evidence burden
- source atom, source-window dossier, source-window refit trace, and global atom index links
- blockers, or `None`

Direct atom table:

| Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Artifact Projection | Projection Rationale | Capability Impact | Target Capability | Related Capabilities | Atom Relation | Roles | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

All final packet `Global Atom ID` values must preserve the exact `GA-####` IDs from `change-capability-anchors/obligation-atom-index.md`; Phase 5 must not rewrite them to another global prefix or source-local atom id.

Direct table rows must use `spec-requirement`, `spec-guard`, `design-obligation`, or `verification-obligation`. `contextual-only` belongs only in the context table or non-direct classifications.

Direct table capability fields must match canonical `atom-plan-mapping.json`. Business `new` / `modified` rows must be spec projections with a concrete target; ordinary design/verification rows must display `none` / `none`; related capabilities must be source-explicit, unique, and non-owning. Render empty related arrays as `None`.

Context table:

| Global Atom ID / Relation | Source Document | Lines | Context Type | Affects Current Design Because | Handling |
| --- | --- | --- | --- | --- | --- |

The context table, or relation-specific equivalent tables in the same final packet, must include every non-direct row from `atom-plan-mapping.md` whose `Final Owner Change` is this change. This includes contextual, dependency, evidence-burden, preserve/reference, explicit non-goal, later-change, and other non-direct relations. Each such atom must appear as its own explicit `GA-####` row with source document, line range, relation/context type, why it affects the current design or scope, and handling. Do not truncate, summarize, aggregate, or replace explicit non-direct atom rows with count-only rows, `additional-context`, or link-only placeholders. If the table is large, split it by relation type inside the same packet while preserving one explicit row per atom.

Each business `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` file is a derived spec-advancement view. It must include only direct `spec-requirement` / `spec-guard` atoms from the final change packet whose `final-target-capability` is this capability and whose `final-capability-impact` is `new` or `modified`. Change-only design/verification rows, related-only associations, and non-direct constraints stay in the final change packet, not in capability views. The one exception is the dedicated `runtime-substrate-foundation` view containing direct `foundation-substrate` rows for the first foundation Change.

Capability atom table:

| Capability | Change | Capability Impact | Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Artifact Projection | Relation | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Derived-view invariants:

- Every capability row must have a matching direct row in the final change packet.
- Every direct spec atom whose target capability is this capability and whose impact is `new` or `modified` must appear in the business capability file; every direct `foundation-substrate` atom must appear in the dedicated foundation view.
- Capability files must not rename atoms, change source line ranges, change artifact projection, or independently split/merge source facts.
- The set of business capability files under a Change must exactly match its distinct explicit `new` / `modified` target capabilities. Extra files for change-only design/verification rows, related-only, dependency-only, preserve-only, or contextual-only capabilities are not allowed. The foundation Change may add only the dedicated `runtime-substrate-foundation` view.
- Capability files must not contain related-only, contextual, dependency, evidence-burden, preserve/reference, explicit non-goal, later-change, upstream-baseline, or other non-direct rows. Business views must also exclude change-only design/verification rows. Those rows are excluded from capability advancement but must remain explicit in the owning final change packet.

## Final Capability Relation Consistency Check

Before returning `accepted` or `adjusted`, Phase 5 must run a consistency check across the final plan and derived anchors. Write the result into `phase-works/phase-5/alignment-final-report.md` and summarize it in `phase-works/phase-5/phase-5-agent-report.md`. For `needs-coverage-recheck` or `blocked`, do not write `alignment-final-report.md`; record the source-window-backed recheck or blocker reason in `phase-5-agent-report.md` and `change-plan-adjustments.md`.

Required comparison:

| Capability | Capability Map First Change | First Explicit `new` Target From Packets | First Matrix Cell | First Roadmap `New` | First Anchor Index Occurrence | Later Explicit `modified` Targets | Result | Repair If Failed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

Rules:

- All comparison columns must satisfy the Capability Relation Invariants.
- No business capability may appear in `change-capability-anchors/index.md` unless at least one direct spec atom in that Change packet has it as `final-target-capability` with impact `new` or `modified`. The only exception is `runtime-substrate-foundation` for direct `foundation-substrate` rows.
- Packet-level non-direct coverage must be checked before Phase 5 can return `accepted` or `adjusted`: every non-direct `atom-plan-mapping.md` row with a real `Final Owner Change` must be present as an explicit `GA-####` row in that change's final packet context/dependency/evidence/preserve/non-goal handling.
- Capability-view purity must be checked before Phase 5 can return `accepted` or `adjusted`: every business view row must be direct, spec-projected, and match the view target with impact `new` / `modified`; every foundation view row must use `foundation-substrate`; every row must have a matching direct packet row; no change-only, related-only, or non-direct atom may appear only in a capability view.
- If stale labels are the only problem, repair the Phase 5 artifacts without changing Phase 2 or Phase 3 evidence.
- If the mismatch shows that final Change ownership or spec target/impact is ambiguous or contradictory, return `needs-coverage-recheck` or `blocked`; do not mark Phase 5 `accepted` or `adjusted`.

## Workflow

1. Read Phase 3's `phase-works/phase-3/coverage-review.md` decision and global atom index.
2. Read Phase 4's `phase-works/phase-4/phase-4-agent-report.md` and confirm `Phase 4 Status: grounded`.
3. Read Phase 4 source-window dossiers, semantic profiles, and grounding issues.
4. Read Phase 3 handoff items, especially atoms marked `phase-5-refit-required`, ownership ambiguities, and source-backed non-direct constraints.
5. Ensure `phase-works/phase-5/` exists. For `accepted` or `adjusted` terminal output, write `input-change-plan.md` directly in that directory; for `needs-coverage-recheck` or `blocked`, record the input plan reference in `source-window-refit-trace.md` instead of requiring the terminal input snapshot.
6. Build the atom-driven planning graph using the global atom index and Phase 4 source-window semantic profiles.
7. Apply the implementation-ready complexity gate, Foundation Executable Gate, required split analysis, and Change/Capability Coupling Gate to every candidate final change.
8. Decide whether the Phase 1 framework is accepted, adjusted, needs coverage recheck, or blocked.
9. Write `phase-works/phase-5/source-window-refit-trace.md` to explain how Phase 4 input change/capability source windows and atoms were reconstructed into final changes/capabilities.
10. If accepted or adjusted, write `phase-works/phase-5/change-plan.md`, canonical `phase-works/phase-5/atom-plan-mapping.json`, rendered `phase-works/phase-5/atom-plan-mapping.md`, and `phase-works/phase-5/final-packet-index.json`. If status is `needs-coverage-recheck` or `blocked`, skip terminal mapping/final packet artifacts and write the blocker or recheck rationale in `change-plan-adjustments.md`.
11. If adjusted, update root `openspec/orchestrate/change-plan.md` to the latest effective plan after the Phase 5 snapshot and mapping are written.
12. If accepted or adjusted, write `phase-works/phase-5/capability-progression-review.md`, `change-complexity-review.md`, and `plan-refit-decision-log.md`.
13. If the status is `adjusted`, `needs-coverage-recheck`, or `blocked`, write `phase-works/phase-5/change-plan-adjustments.md` with the plan-impact and next-action summary.
14. Derive final `change-capability-anchors/<change-slug>/` packets and capability views from the global atom index, source-window refit trace, and final plan when the status is `accepted` or `adjusted`. Final change packets must explicitly list every Change-owned direct atom and every owner-scoped non-direct atom. Business capability views include only direct `new` / `modified` spec atoms for their target; the dedicated foundation view includes only `foundation-substrate` rows for `runtime-substrate-foundation`.
15. If accepted or adjusted, write `change-capability-anchors/index.md`.
16. If accepted or adjusted, run the Final Capability Relation Consistency Check and packet-level non-direct coverage check. Repair canonical mapping/config values, then rerender stale `First change`, matrix cells, roadmap `New`/`Modified` labels, final anchors index rows, capability views, final packet context/evidence/dependency/non-goal rows, and human-plan summaries before proceeding. Do not let the renderer infer `new` / `modified` from order.
17. Write `phase-works/phase-5/change-capability-human-plan.md` as a readable synthesis of final change packets and capability progression when the status is `accepted` or `adjusted`.
18. Always write `phase-works/phase-5/phase-5-agent-report.md`. Write `phase-works/phase-5/alignment-final-report.md` only when the status is `accepted` or `adjusted`.
19. Run a local artifact consistency check by inspection or deterministic parsing before finishing.

## Required Mapping Tables

`phase-works/phase-5/source-window-refit-trace.md` must include:

| Input Change / Capability | Source Window Evidence | Input Atoms | Final Change / Target Capability | Atom Movement | Relation Changes | Engineering Reason |
| --- | --- | --- | --- | --- | --- | --- |

Canonical `phase-works/phase-5/atom-plan-mapping.json` must include every global atom mapping row. Rendered `phase-works/phase-5/atom-plan-mapping.md` must use this table:

| Global Atom ID | Source Document | Lines | Phase 3 Owner / Status | Phase 3 Artifact Projection | Final Owner Type | Final Owner Change | Final Capability Impact | Final Target Capability | Related Capabilities | Final Artifact Projection | Final Relation | Plan Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

The rendered mirror must also include `Trace Appendix` with trace file, trace schema, trace sha256, and render contract `source-aligned-render-v2`.

`phase-works/phase-5/plan-refit-decision-log.md` must include:

| Decision Item | Input Evidence | Candidate Options | Decision | Output Artifact | Reason |
| --- | --- | --- | --- | --- | --- |

`change-capability-anchors/index.md` must include:

| Change | Change Packet | Capability Views | Direct Atoms | Contextual Atoms | Capabilities Advanced | Complexity Budget | Evidence Burden | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

`phase-works/phase-5/change-capability-human-plan.md` must include readable change packets:

| Change | Closed-loop Outcome | Source-Window Grounding | Direct Atom Groups | Complexity Budget | Contextual Atoms / Future Constraints | Upstream Realized Baseline | Downstream Constraints | Non-Goals | Evidence Burden | Ledger Links |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

It must also include a capability progression narrative:

| Capability | Baseline Change | Refinement / Hardening / Extension Changes | Atom Progression Summary | Human Review Notes |
| --- | --- | --- | --- | --- |

## Phase 5 Report

`phase-works/phase-5/phase-5-agent-report.md` must include:

| Refit Finding | Source Ranges or Atoms | Plan Decision | Files Written | Atom Resolution | Remaining Gap or Blocker |
| --- | --- | --- | --- | --- | --- |

It must also include:

- whether the initial plan was accepted or adjusted
- Phase 4 source-window dossier intake summary, including input changes/capabilities covered and any grounding issues that affected refit
- Phase 4 source-window semantic profile usage summary, including which original source semantics drove split, merge, reorder, rename, contextualization, dependency, evidence-burden, or non-goal decisions
- Source Window Semantic Grounding Gate summary for final changes, including any rejected split/merge/reorder options and why atom count was or was not a valid complexity concern
- atom-driven planning graph summary
- capability progression recalibration summary
- change complexity recalibration summary
- change/capability coupling gate summary, including whether the final matrix avoided capability-driven one-to-one slicing
- new, split, merged, removed, reordered, or renamed changes
- new, split, merged, removed, or renamed capabilities
- atoms moved, reclassified, or left as contextual
- confirmation that every executable direct global atom has exactly one final owner Change; ordinary design/verification atoms use `none` / `none`; and every foundation direct atom is owned by the first executable foundation Change with `foundation-substrate` / `runtime-substrate-foundation`
- confirmation that every direct global atom has final artifact projection
- confirmation that `design-obligation` and `verification-obligation` atoms were not forced into `spec-requirement`
- confirmation that `new` / `modified` occur only for direct spec projections with concrete targets, every `(Change, target capability)` pair has one consistent impact, each capability route begins with explicit `new` then uses explicit `modified`, and no accepted/adjusted row remains `unresolved`
- confirmation that `related-capabilities[]` values are unique, declared, source-explicit, distinct from the target, and excluded from ownership, progression, capability views, and advanced-capability complexity counts
- confirmation that every owner-scoped non-direct atom in `atom-plan-mapping.md` appears explicitly in the owning final change packet and was not represented only by a count, summary, `additional-context`, capability view, or link-only placeholder
- confirmation that business capability views contain only direct `new` / `modified` spec atoms for their target, the foundation view contains only `foundation-substrate` rows, and change-only/non-direct constraints are preserved in final change packets rather than capability views
- confirmation that final business capability relations are explicit `New` or `Modified` spec advancement only and the renderer did not infer them from order
- confirmation that Capability Map `First change`, progression matrix first cells, roadmap `New`/`Modified` labels, final packet capability impact/target, capability views, anchor index, and human plan all agree after the refit
- confirmation that the final plan is not a diagonal or same-name change/capability roadmap unless every exception is source-backed and recorded
- confirmation that change packets contain upstream baseline and downstream design context without pulling future scope into current direct ownership
- confirmation that final change complexity is implementation-ready or explicitly blocked with split options
- confirmation that every over-budget trigger was split, deferred, or justified with concrete indivisibility analysis
- confirmation that any foundation candidate was converted into the first executable foundation packet with `change-kind: foundation`, or that no foundation change was needed
- confirmation that foundation atoms do not count as business capability progression and that later runtime acceptance / Proof Slices are generated only for current observable engineering substrate facts
- confirmation that deferrable domain behavior and post-foundation low-level capability deltas are advanced inside the first business workflow that needs them
- confirmation that the final roadmap order follows the Behavior Maturity Ordering Gate and that support/governance/operation-heavy changes are not placed early solely because future changes will need them
- confirmation that source atom files and the Phase 3 global atom index were not modified
- confirmation that refit decisions cite Phase 4 source-window dossier evidence rather than relying only on atom count, capability count, or atom summaries
- confirmation that every final change answers the Source Window Semantic Grounding Gate questions before atom ownership is finalized
- confirmation that every Phase 5 artifact passed the Artifact Language Gate
- next required step: `Start openspec-propose`, `Run Phase 3 again`, or `Blocked`

## Completion

Phase 5 ends with exactly one status in `phase-works/phase-5/phase-5-agent-report.md`:

- `Phase 5 Status: accepted`
- `Phase 5 Status: adjusted`
- `Phase 5 Status: needs-coverage-recheck`
- `Phase 5 Status: blocked`

Use `accepted` when the Phase 1 framework remains coherent after source-window and atom-level review, final packets were derived, and all Phase 5 gates pass.

Use `adjusted` when the framework was refit from source-window semantic profiles, all final atom mappings remain traceable, final packets were derived, and all Phase 5 gates pass.

Use `needs-coverage-recheck` when Phase 5 exposes missing, over-broad, conflicting, or semantically unclear source obligations that Phase 3 must normalize before the plan can be final.

Use `blocked` when the adjustment needs source boundaries, product decisions, or broad reanalysis that Phase 5 is not allowed to perform.

After `accepted` or `adjusted`, run `validate_source_aligned_orchestrate.py --phase all --complete --json`; only then may `openspec-propose` start from the final change packets. After `needs-coverage-recheck`, the main agent must spawn a fresh Phase 3 review subagent, then fresh Phase 4 grounding and Phase 5 refit subagents. Do not start `openspec-propose` directly from `needs-coverage-recheck` or `blocked`.

For `openspec-propose` handoff, write the final Phase 5 decision to both `trace/phase-5.trace.json.status` and `trace/manifest.json` `phase-statuses.phase-5`. These two values must match exactly. `phase-statuses.phase-5` is the Phase 5 final handoff decision, not the validator/reviewer/repair-loop workflow state.
