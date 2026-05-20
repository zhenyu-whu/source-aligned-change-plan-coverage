# Phase 1: Initial Source-Aligned Change Plan

Phase 1 creates the initial top-level OpenSpec change/capability framework from the user-specified source documents. It must enumerate and read every source document under the user-specified source roots before slicing the plan. The Phase 1 framework is a source-informed slicing hypothesis that Phase 4 may refit after obligation atoms are normalized. It does not create concrete OpenSpec changes, proposals, specs, designs, tasks, acceptance artifacts, obligation atom ledgers, line-range anchors, coverage statuses, or a backlog of evidence items waiting for Phase 2.

Write the Phase 1 plan snapshot to:

```text
openspec/orchestrate/phase-works/phase-1/change-plan.md
```

Also promote the same initial latest-effective plan to:

```text
openspec/orchestrate/change-plan.md
```

Write the initial full-source manifest to:

```text
openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md
```

Write the Phase 1 report to:

```text
openspec/orchestrate/phase-works/phase-1/phase-1-agent-report.md
```

## Artifact Language Gate

Apply the skill-level Artifact Language Gate to every Phase 1 output. Keep fixed headings, table headers, field labels, capability ids, change slugs, paths, commands, and exact source terms as required, but write all agent-authored explanations in Simplified Chinese. This includes assumptions, conflicts, behavior-boundary descriptions, capability increment cells, roadmap field values, risk-check answers, source-evidence hint explanations, archive-readiness notes, and the Phase 1 report.

After writing each Phase 1 artifact, perform the language self-check from the skill gate. If any explanation sentence remains English-dominant after ignoring IDs, paths, commands, code, and fixed terms, rewrite it before finishing Phase 1.

## Goal

Plan a set of scientific, verifiable, iterative OpenSpec changes from a full reading of the user-specified source documents.

Each change should represent a reviewable, implementable, verifiable, archivable system behavior change. Do not mechanically split by technical module, database table, page, component, SDK, queue, or prototype scenario.

Use only the documents or directories the user specifies. For every specified source root, enumerate all source documents and read every source document body before producing the initial framework. Do not read or rely on the current `openspec/` directory, existing specs, existing changes, archive history, or custom artifacts unless the user explicitly includes them as input.

If the specified source set is too large to read safely, return a blocker instead of sampling. The Phase 1 framework is only valid when it is based on a full-source read.

## Change-Capability Model

Use this model throughout the plan:

- A change is a vertical business or system loop. It should move the product or system through a concrete, reviewable outcome.
- A capability is a long-lived behavior boundary. It usually matures across multiple changes.
- A change may advance multiple capabilities when those increments are required by the same functional loop. The goal is not to maximize capability coverage per change.
- A capability is usually advanced by multiple changes over time.
- Do not create a one-to-one roadmap where each change merely implements one capability. If a candidate roadmap trends that way, reslice changes around user/system loops and keep capabilities as cross-cutting behavior boundaries.
- The anti one-to-one rule prevents capability-driven roadmaps. It does not forbid small focused vertical changes that primarily advance one capability when they are derived from a real user or system loop.
- A capability id must not merely restate a single change outcome. If a capability is advanced by only one change and its id shares the dominant nouns or verbs of that change slug, treat it as a boundary smell: merge it into a broader durable capability, rename it around a long-lived behavior boundary, or record a source-backed reason why it is genuinely terminal.
- Do not split or rename capabilities to make each change advance only one capability. Cross-cutting capabilities such as identity, privacy, realtime state, version history, entitlement, failure recovery, export delivery, or observability should remain visible across multiple loops when the same loop directly changes them.
- Each change implements only the capability increments needed for that change's closed loop. Later changes may strengthen, broaden, or harden the same capability.
- A change-capability relation has only two allowed values:
  - `New`: the change first creates that capability/spec boundary.
  - `Modified`: the change changes requirements or scenarios for an existing capability/spec boundary.
- Do not model consumed, preserved, reused, or dependency-only capabilities as change-capability relations. Mention them in dependencies or notes only when useful, not in the capability progression matrix.
- Name capabilities as stable English kebab-case ids, such as `account-access-continuity` or `async-work-execution-recovery`. Do not use module names, table names, page names, external-service names, or localized display names as capability ids.

## Change Complexity Calibration

Do not optimize for either the fewest changes or the most changes. Optimize for reviewable implementation complexity.

A change should deliver one clear, verifiable functional point or system behavior point. It may touch multiple capabilities only when those capability increments are directly necessary for that functional point. Do not treat the number of capability columns touched by a change as implementation cost by itself; split by independently verifiable functional points, not by capability columns.

Split a candidate change when it contains multiple functional points that can each be implemented, verified, reviewed, and archived independently while still satisfying the Closed-loop Test.

A smaller change is valid even if it primarily advances one capability, as long as it is derived from a user/system loop rather than mechanically from the capability list.

Do not merge independently verifiable behavior merely to avoid a one-to-one appearance in the capability matrix.

For the first feature change after a foundation change, prefer the thinnest real product or system loop that can be archived without pretending later infrastructure is complete.

### Split Challenge

Before accepting each candidate change, ask:

1. What is the single functional point this change proves?
2. Does the change include another behavior that could be shipped and verified separately?
3. Can part of this change be archived earlier without fake stubs or low-level-only proof?
4. Are multiple entry points, failure modes, or projections being combined only because they share infrastructure?
5. Is the change introducing infrastructure-heavy concerns before the functional point actually needs their full behavior?

If the answer to 2, 3, 4, or 5 is yes, split the change unless the plan explains why the combined scope is necessary for one coherent closed loop.

### Capability Shape Challenge

Before accepting the initial framework, review the capability map and progression matrix as a whole:

1. Does each capability describe a durable behavior boundary that can plausibly mature across multiple changes?
2. Do more than half of the planned changes have exactly one non-empty capability cell? If yes, inspect whether the roadmap has become capability-driven and reslice unless each exception is source-backed.
3. Do many capabilities have exactly one owning change, or does a capability slug paraphrase its first change slug? If yes, merge, rename, or broaden those capabilities unless they are genuinely terminal source-backed boundaries.
4. Did any user/system loop lose directly necessary identity, privacy, realtime, versioning, entitlement, failure recovery, export, or observability increments only to make the row narrower? If yes, restore those direct increments to the loop.
5. Would the same source obligation be easier for a later `openspec-propose` agent to understand as one vertical loop with several capability deltas? If yes, keep the loop and document the cross-capability coupling.

## Change Slicing

Prefer changes sliced by verifiable business or system loops.

Every non-foundation change must satisfy the Closed-loop Test:

- Entry: a clear entry point such as page, API, CLI, worker job, webhook, admin operation, or scheduled task.
- Fact: a clear system fact is created or changed, such as data record, file, event, state, ledger entry, or external receipt.
- Projection: the result is observable through UI, API response, stream event, notification, download link, log, or audit view.
- Failure: at least one failure path is explicit, with explainable, recoverable, or blocked state.
- Verification: executable proof exists, such as unit, contract, integration, E2E, visual smoke, manual checklist, fixture replay, or dry run.

If a candidate change only proves that a low-level component exists, it cannot stand alone unless it qualifies as a foundation exception.

## Foundation Exception

A foundation change is allowed only when all conditions hold:

1. Without it, no later closed-loop change can reasonably start.
2. It is the only pre-business foundation candidate in the initial roadmap.
3. It is a zero-domain engineering bootstrap.
4. It produces a stable reusable engineering boundary.
5. It has runtime or integration-level proof.
6. It names the first closed-loop business/user workflow that will build on it.
7. The plan does not contain consecutive pure foundation changes.

The Phase 1 foundation candidate may include only engineering substrate needed before the first real workflow:

- repository/package directories
- root scripts
- lint/typecheck/test harness
- env validation
- local dependency manifests
- migration tooling, but not business schema
- empty web/worker smoke entrypoints
- empty adapter seams whose behavior is not yet domain-specific

The Phase 1 foundation candidate must not include:

- business/domain table creation or table ownership beyond migration tooling
- domain commands, use-cases, policies, or repositories
- user-facing API routes or DTOs
- worker action semantics, job state machines, recovery loops, or business queues
- SSE/outbox business events
- auth/business identity mapping
- assets, subscriptions, entitlements, usage, export, project, figure, brief, thread, message, or version design
- observability, privacy, recovery, responsive, design-system, or verification behavior that belongs to the first workflow that needs it

Source-backed domain behavior found during Phase 1 should be sliced into business change candidates or recorded as non-canonical ownership hints for Phase 2. Do not hide it inside a foundation/spine change.

## Workflow

1. Enumerate every source document under the user-specified roots or exact paths.
2. Read every enumerated source document body. Do not sample, skim only filenames, or defer full reading to Phase 2.
3. Write `phase-works/phase-1/source-doc-manifest.md` with every source document, read status, high-level source role, and coarse topic/path hints.
4. Extract core user or system paths.
5. Express each path as: entry -> behavior -> system fact -> visible result -> failure recovery.
6. Identify long-lived behavior capabilities with English kebab-case ids. Capabilities should be broader than one implementation unit unless the source set proves a terminal boundary.
7. Generate candidate vertical changes from user/system loops, not from the capability list.
8. For each candidate change, identify the direct increment it contributes to each involved capability, and classify that relation as `New` or `Modified`.
9. Filter, merge, or reslice candidates using the Closed-loop Test, Change Complexity Calibration, the Split Challenge, the Capability Shape Challenge, and the anti one-to-one mapping rule.
10. Order changes by real behavior dependencies, prioritizing the earliest minimal runnable loop.
11. Build a capability progression matrix that shows how each change advances each capability.
12. Mark key scenarios, non-goals, risks, conflicts, and deferred content from the input documents.
13. Add concise `Source evidence` hints only to justify the planned slice. These hints may name source paths, headings, section numbers, decision IDs, route/page/object names, APIs, commands, DTOs, entities, tables, jobs, events, assets, environments, or verification anchors.
14. Do not extract or enumerate every source-backed requirement in Phase 1. Do not create obligation atom ledgers, line ranges, anchor tables, coverage statuses, "pending Phase 2" evidence lists, or evidence counts. If a hint is only semantic, keep it as a short non-canonical plan clue; Phase 2 owns source-first atom extraction, Phase 3 owns coverage normalization, and Phase 4 owns final plan refit.

## Output

Produce `openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md` with:

| Source Document | Read Status | Source Role | Coarse Topics / Paths | Notes |
| --- | --- | --- | --- | --- |

Rules:

- Every user-specified source document must appear exactly once.
- `Read Status` must be `read-full` for source documents used by this workflow.
- Non-source artifacts may be listed as `non-source-artifact` only when they are under a specified root and are not meaningful source docs.
- Do not add coverage status, atom counts, or line-range coverage in Phase 1.

Produce `openspec/orchestrate/phase-works/phase-1/change-plan.md`, then promote the same latest-effective content to `openspec/orchestrate/change-plan.md`, with:

### Inputs

- Documents specified and read
- Potentially relevant documents not read
- Assumptions and conflicts

### Slicing Principles

- Change slicing principles used for this plan
- Rejected slicing approaches and reasons
- Explicit statement that changes are vertical loops and capabilities are long-lived behavior boundaries

### Capability Map

| Capability | Behavior boundary | First change | Later expansion |
| --- | --- | --- | --- |

Rules:

- Capability values must be English kebab-case ids in backticks.
- Behavior boundary explains the durable behavior, not the implementation module.
- Later expansion should show that the capability can mature across later changes.
- If `Later expansion` is `None` or only repeats the first change for many capabilities, the plan must explain why those capabilities are genuinely terminal instead of one-change aliases.

### Capability Progression Matrix

Create a matrix after the Capability Map:

| Change | `capability-a` | `capability-b` | `capability-c` |
| --- | --- | --- | --- |
| `change-name` | Concrete capability increment delivered by this change |  | Concrete capability increment delivered by this change |

Rules:

- Each row is one change.
- Each column is one capability from the Capability Map.
- Each non-empty cell describes the specific functional increment this change contributes to that capability.
- Leave the cell blank when the change does not create or modify that capability.
- Do not fill cells with generic reuse, generic test coverage, or "uses existing capability"; only direct capability advancement belongs in the matrix.
- Do not prefix matrix cells with `New:` or `Modified:`; first appearance of a capability in the ordered roadmap is implicitly `New`, later appearances are implicitly `Modified`.
- Keep cell text concise enough for review.
- If the matrix is mostly diagonal, has many single-cell rows paired with single-change capabilities, or visually resembles a change list duplicated as capabilities, revise the change/capability model before Phase 1 finishes.

### Change Roadmap

For each change:

- Change name:
- Closed-loop outcome:
- Source evidence hints (Phase 1, non-canonical):
- Capability changes:
  - New: use capability ids from the Capability Map, or write `None`.
  - Modified: use capability ids from the Capability Map, or write `None`.
- In scope:
- Out of scope:
- Vertical slice:
  - Entry:
  - Fact:
  - Projection:
  - Failure:
  - Verification:
- Dependencies:
- Archive readiness:

### Risk Checks

Answer:

1. Are there consecutive low-level changes with no observable behavior?
2. Does every non-foundation change have a closed loop?
3. Are any capabilities named by technical module instead of behavior boundary?
4. Are any key input scenarios unmapped to a change?
5. Can any change only be verified by "code exists" rather than behavior proof?
6. Does the plan imply a one-to-one mapping between changes and capabilities?
7. Does every change-capability relation use only `New` or `Modified`, with blanks where a change does not create or modify a capability?
8. Does any change combine multiple independently verifiable functional points that could be implemented and archived separately?
9. Does the first feature change after a foundation change introduce infrastructure-heavy concerns before its functional point needs their full behavior?
10. Does the plan merge behavior only to avoid a one-to-one appearance in the capability matrix?
11. Are any initial change/capability boundaries marked as hypotheses that may need Phase 4 refit after atom extraction?
12. Do many capability ids paraphrase the change slug that first owns them?
13. Are cross-cutting production concerns being moved into separate capability-shaped changes even though they directly affect the same user/system loop?
14. If more than half of non-foundation changes advance only one capability, is there source-backed evidence that those are genuinely separate loops rather than a diagonalized roadmap?
15. If a foundation candidate exists, is it strictly a zero-domain engineering bootstrap?
16. Did Phase 1 avoid placing business schema, domain commands, user-facing APIs, worker business semantics, SSE/outbox events, auth/business identity, assets, entitlement, usage, export, project, figure, brief, thread, message, version, privacy, recovery, responsive, design-system, or observability behavior into foundation scope?
17. Are source-backed domain obligations represented as business change candidates or Phase 2 ownership context for the first workflow that needs them?

## Phase Report

`phase-works/phase-1/phase-1-agent-report.md` must briefly list:

- source documents read
- generated plan path
- notable assumptions or conflicts
- whether any change lacks useful source hints; do not enumerate every pending evidence item
- confirmation that every source document in the manifest was read in full
- confirmation that the Phase 1 artifacts passed the Artifact Language Gate
- blockers, or `无`
