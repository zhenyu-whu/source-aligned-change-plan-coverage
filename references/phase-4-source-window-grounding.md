# Phase 4: Source-Window Dossier and Semantic Profile Grounding

Phase 4 runs after Phase 3 returns `Decision: coverage-complete`. It is an independent source-grounding phase, not a plan-refit phase.

Phase 4 exists because Phase 2/3 atom rows are sufficient for coverage and traceability, but they are often too compressed for engineering delivery judgment. This phase uses Phase 2/3 atom line ranges as an index to copy the original source windows into reviewer-facing dossiers grouped by input change and input capability. It then writes semantic profiles that preserve the actual source meaning needed by Phase 5 plan refit and by human reviewers.

Phase 4 MUST be performed by a fresh independent subagent. It must not rerun Phase 2 extraction, normalize atoms, decide final ownership, split/merge/reorder changes, or invent source obligations. If source windows reveal a missing, conflicting, or over-broad obligation that cannot be explained by existing Phase 3 atoms, Phase 4 must return `needs-coverage-recheck`.

## Inputs

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/phase-works/phase-1/change-plan.md`
- `openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/index.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/*.atoms.md`
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`
- `openspec/orchestrate/phase-works/phase-3/coverage-review.md`
- `openspec/orchestrate/phase-works/phase-3/source-doc-coverage/*.coverage.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/*.md`
- Original source document roots or exact source paths.

## Outputs

Write Phase 4 artifacts directly under `openspec/orchestrate/phase-works/phase-4/`. Do not create `pass-*`, `iteration-*`, attempt-numbered, or similarly iterative subdirectories.

- `openspec/orchestrate/phase-works/phase-4/input-change-plan.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/index.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-change/<input-change-slug>.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-capability/<input-capability-slug>.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-grounding-issues.md`
- `openspec/orchestrate/phase-works/phase-4/phase-4-agent-report.md`

`phase-works/phase-4/source-window-dossiers/` is copied review evidence. It is not a new extraction pass and must not replace the original source documents, source atom ledgers, global atom index, or Phase 5 final packets as source of truth.

## Artifact Language Gate

Apply the skill-level Artifact Language Gate to every Phase 4 output. Keep fixed headings, table headers, enum/status values, atom ids, source paths, line ranges, capability ids, change slugs, code symbols, and exact source quotes as needed. Agent-authored semantic notes, judgments, rationale, issue descriptions, and report summaries must be Simplified Chinese.

## Scope Rules

Phase 4 may:

- copy original source windows selected from Phase 2/3 atom line ranges and nearby semantic context
- group copied source windows by input change and input capability
- cite Phase 2 source atom ids, `GA-####` ids, Phase 3 status/projection/owner, duplicate/remainder/contextual notes, and Phase 5 handoff markers
- write source-window semantic profiles for every input change and input capability
- record suspected split, merge, reorder, rename, foundation, capability-boundary, contextual, dependency, evidence-burden, or non-goal pressure for Phase 5
- report missing or ambiguous source windows as grounding issues

Phase 4 must not:

- rerun Phase 2 extraction or Phase 3 normalization
- edit source documents, Phase 2 source atom files, Phase 3 coverage files, or the global atom index
- create, split, merge, delete, or renumber atoms
- decide final owner change/capability, final atom relation, or final artifact projection
- update root `openspec/orchestrate/change-plan.md`
- generate final change packets, final capability views, or `change-capability-anchors/index.md`
- decide that the initial plan is accepted or adjusted
- use copied source windows as permission to invent source obligations outside Phase 3

If Phase 4 cannot ground a source-window dossier because line ranges, source paths, or atom mappings are missing or contradictory, it must record the issue. If targeted inspection cannot resolve the issue without changing Phase 3 normalization, return `needs-coverage-recheck`.

## Source-Window Dossier Method

For every input change and input capability named by the current change plan or Phase 3 candidate ownership, collect the relevant Phase 2/3 atoms and copy their original source windows into dossier files. Group by input ownership before Phase 5 refit so a reviewer can see what the initial plan meant before any atoms move.

Window selection rules:

- Include exact atom line ranges.
- Include the nearest section heading/path when available.
- Include adjacent lines needed to understand entry, fact, projection, failure/recovery, verification, auth/privacy, data, API, UI, worker, persistence, or external integration semantics.
- Include neighboring contextual, duplicate, remainder, or Phase 5 handoff evidence when it affects the same local source meaning.
- Prefer compact windows that preserve semantic completeness; do not copy an entire large source document unless the section is too interdependent to review safely in a smaller window.
- Preserve line numbers and original wording. Add Chinese semantic notes beside copied windows, not inside the quoted source text.

Each `by-input-change/<input-change-slug>.md` dossier must include:

- input change id/name and Phase 1 closed-loop hypothesis
- related input capabilities
- source-window inventory grouped by source document and source section
- copied original line-numbered source windows with exact line ranges and local context
- linked `GA-####` ids and Phase 2 source atom ids when available
- Phase 3 status/projection/owner for each atom
- neighboring contextual, duplicate, remainder, or Phase 5 handoff evidence
- preliminary semantic profile: business outcome, entry, fact, projection, failure/recovery, verification surface, manual acceptance scenario, and suspected Phase 5 refit pressure

Each `by-input-capability/<input-capability-slug>.md` dossier must include:

- input capability id/name and Phase 1 behavior-boundary hypothesis
- related input changes in roadmap order
- copied source windows grouped by change and source document
- direct, contextual, dependency, evidence, and non-goal atom groupings
- behavior-boundary semantic profile: what behavior it owns, what it must not own, where it first becomes directly testable, and which later changes appear to add source-backed deltas

## Semantic Profile Review

Write `source-window-semantic-profile-review.md` with one row per input change and input capability:

| Input Unit | Unit Type | Source Windows | Atom Groups | Actual Source Semantics | Engineering Delivery Signal | Manual Acceptance Scenario | Phase 5 Refit Pressure |
| --- | --- | --- | --- | --- | --- | --- | --- |

Rules:

- Derive each semantic profile from copied source windows, not only `Source Fact` summaries.
- For an input change, identify whether the source windows describe a reviewable implementation unit: entry, fact, projection, failure path, and verification truth can be delivered together.
- For an input capability, identify whether the source windows describe a durable behavior boundary rather than a temporary implementation module, page, source section, or one-change alias.
- If source windows show several capabilities are directly required for one truthful business loop, record that Phase 5 should keep those deltas together unless a source-window-backed split preserves independent acceptance.
- If source windows show one input change mixes multiple independently acceptable business outcomes, record split pressure for Phase 5.
- If source windows show technical preparation without an independently runnable operational loop, record foundation/fold-in/context/evidence pressure for Phase 5.
- If a profile cannot be safely derived because the evidence is missing, broad, conflicting, or unclear, record a grounding issue instead of guessing.

## Grounding Issues

Write `source-window-grounding-issues.md`:

| Issue | Source Evidence | Affected Input Unit | Affected Atoms | Impact on Phase 5 | Required Next Step |
| --- | --- | --- | --- | --- | --- |

Use this file for:

- source path or line range mismatches
- missing source windows
- source windows that imply a missing global atom
- broad atoms whose original source window contains multiple obligations that Phase 3 did not split
- contradictory candidate ownership evidence
- input changes/capabilities with no source-window support
- cases where a human product decision is required before Phase 5 can refit safely

## Phase 4 Report

`phase-works/phase-4/phase-4-agent-report.md` must include:

| Grounding Finding | Source Ranges or Atoms | Input Unit | Files Written | Phase 5 Impact | Remaining Gap or Blocker |
| --- | --- | --- | --- | --- | --- |

It must also include:

- source documents read
- input changes and input capabilities covered
- source-window dossier counts by input change and capability
- atom coverage count represented in dossiers
- semantic profile summary
- grounding issues summary
- confirmation that Phase 4 did not edit Phase 2/3 evidence or the global atom index
- confirmation that Phase 4 did not decide final change/capability ownership
- confirmation that every Phase 4 artifact passed the Artifact Language Gate
- next required step: `Start Phase 5`, `Run Phase 3 again`, or `Blocked`

## Completion

Phase 4 ends with exactly one status in `phase-works/phase-4/phase-4-agent-report.md`:

- `Phase 4 Status: grounded`
- `Phase 4 Status: needs-coverage-recheck`
- `Phase 4 Status: blocked`

Use `grounded` when every input change and input capability has reviewer-facing source-window dossiers, semantic profiles are written, grounding issues are either absent or safe for Phase 5 to consider, and no Phase 3 normalization recheck is required.

Use `needs-coverage-recheck` when source windows expose missing, over-broad, conflicting, or semantically unclear source obligations that Phase 3 must normalize before plan refit can be final.

Use `blocked` when source boundaries, missing source documents, product decisions, or broad reanalysis prevent safe source-window grounding.

After `grounded`, Phase 5 may start. After `needs-coverage-recheck`, the main agent must spawn a fresh Phase 3 review subagent, then a fresh Phase 4 grounding subagent. Do not start Phase 5 directly from `needs-coverage-recheck` or `blocked`.
