# Trace Sidecar Contract

本文件是 `source-aligned-change-plan-coverage` 的强制 trace sidecar 协议。进入该 workflow 前必须读取。JSON trace 是 validator 的唯一 canonical 输入；Markdown artifact 继续作为中文 reviewer 可读镜像，不作为 validator 的权威数据源。

## Global Rules

- Trace contract version: `source-aligned-trace-v1`。
- 所有 JSON key 必须使用 kebab-case。
- 所有 ID 字段不得包含 Markdown 反引号。
- 多 ID 字段必须使用数组，不得使用逗号字符串。
- Line range 必须保留原始 `lines` 字段，并提供结构化 `line-ranges: [{"start": 1, "end": 2}]`。
- 每个 trace JSON 必须包含 `trace-schema` 和 `trace-contract-version`。
- Markdown mirror 可包含中文解释，但 canonical 字段不得与 JSON 漂移。

## Required Layout

```text
openspec/orchestrate/
├── trace/
│   ├── manifest.json
│   ├── phase-1.trace.json
│   ├── phase-2.trace.json
│   ├── phase-3.trace.json
│   ├── phase-4.trace.json
│   └── phase-5.trace.json
├── change-capability-anchors/
│   ├── obligation-atom-index.md
│   └── obligation-atom-index.json
└── phase-works/
    ├── phase-2/source-obligation-atoms/<source>.atoms.md
    ├── phase-2/source-obligation-atoms/<source>.atoms.json
    ├── phase-3/phase-3-trace/source-to-global-atom-map.json
    ├── phase-3/phase-3-trace/source-remainder-review.json
    ├── phase-4/source-window-dossiers/source-window-index.json
    └── phase-5/
        ├── source-window-refit-trace.md
        ├── atom-plan-mapping.md      # accepted/adjusted only
        ├── atom-plan-mapping.json    # accepted/adjusted only
        └── final-packet-index.json   # accepted/adjusted only
```

## Manifest

`trace/manifest.json` schema is `source-aligned-orchestrate-manifest-v1`.

Manifest lifecycle:

1. During orchestration directory initialization, create or refresh `trace/manifest.json` as a skeleton manifest. Use `missing` for any phase whose trace sidecar does not exist yet, and include only artifact rows whose `trace-path` currently exists.
2. Before every `validate_source_aligned_orchestrate.py --phase ...` run, refresh `trace/manifest.json` so every listed artifact row has the current sha256 of its JSON `trace-path`.
3. After validator and independent reviewer pass, refresh `trace/manifest.json` again so `phase-statuses` records the canonical phase `status` or `decision` from trace sidecars. Do not use reviewer-loop bookkeeping values as phase decisions.

Required fields:

- `trace-schema`
- `trace-contract-version`
- `orchestrate-dir`
- `phase-statuses`
- `artifacts[]`

`phase-statuses` records canonical phase decisions from phase trace sidecars, not reviewer-loop workflow states. It must include `phase-1` through `phase-5`; use `missing` for phases with no trace sidecar. For Phase 1 and Phase 2, use the `status` value from `trace/phase-1.trace.json` and `trace/phase-2.trace.json`. For Phase 3, Phase 4, and Phase 5, use `decision` or `status` from the corresponding phase trace. If a phase trace sidecar exists, its canonical `status` or `decision` is required and `phase-statuses.phase-n` must match it exactly. When `trace/phase-5.trace.json.status` exists, `phase-statuses.phase-5` must be identical to it. For a proposal-ready handoff, both values must be `accepted` or `adjusted`; do not write `reviewer-passed`, `validator-passed`, `repair-not-needed`, `present`, or other workflow/status bookkeeping into any `phase-statuses` value.

Each artifact row must include:

- `artifact-path`
- `trace-path`
- `trace-schema`
- `sha256`
- `phase`
- `role`

`sha256` is computed over the JSON trace file at `trace-path`. `artifacts[]` must list only rows whose `trace-path` exists at the time the manifest is refreshed.

## Phase Schemas

Phase trace schemas:

- `source-aligned-phase-1-trace-v1`
- `source-aligned-phase-2-trace-v1`
- `source-aligned-phase-3-trace-v1`
- `source-aligned-phase-4-trace-v1`
- `source-aligned-phase-5-trace-v1`

Artifact schemas:

- `source-aligned-source-atoms-v1`
- `source-aligned-global-atom-index-v1`
- `source-aligned-source-to-global-map-v1`
- `source-aligned-source-remainder-review-v1`
- `source-aligned-source-window-index-v1`
- `source-aligned-atom-plan-mapping-v1`
- `source-aligned-final-packet-index-v1`

## Required Models

Phase 1 trace:

- `status`: exactly `initial-plan-written`
- `source-documents[]`: `source-document`, `read-status`, `source-role`, `coarse-topics-paths`, `notes`, `line-count`, `source-sha256`
- `change-plan`: `phase-plan-path`, `root-plan-path`, `root-plan-sha256`, `phase-plan-sha256`

Phase 2 trace:

- `status`: exactly `source-atoms-written`
- `work-queue-path`
- `sources[]`
- `phase-report-path`

Phase 2 source atom sidecar:

- `source-document`, `source-sha256`, `read-status`, `canonical-owner`
- `source-atoms[]`: current ledger fields as kebab-case plus `line-ranges[]`
- `source-anchors[]`: current anchor table fields as kebab-case plus `line-ranges[]`
- `section-inventory[]`
- `blockers[]`

Phase 3:

- `obligation-atom-index.json`: `global-atoms[]` with exact `GA-####`, source fields, status, projection, owner, relation, `origins[]`, and `line-ranges[]`
- `source-to-global-atom-map.json`: one row per Phase 2 atom/context row; exactly one mapping outcome: `global-atom-id`, `global-relation`, `non-coverage-status`, or `blocker`
- `source-remainder-review.json`: `audit-documents[]` and `rows[]` for mechanical Phase 2 atom/anchor line coverage and semantic review of every candidate uncovered source range
  - Each `audit-documents[]` row includes `source-document`, `source-sha256`, `line-count`, `evidence-ranges[]`, and `candidate-uncovered-ranges[]`
  - Each `rows[]` row includes `source-document`, `lines`, `line-ranges[]`, `how-found`, `read-scope`, `semantic-classification`, `production-obligation`, `linked-global-atom-ids[]`, `non-coverage-status`, `blocker`, and `reason`
- `phase-3.trace.json`: source classifications, review paths, normalization decisions, remainder review path, and decision value

Phase 4:

- `source-window-index.json`: `windows[]`, `semantic-profiles[]`, `grounding-issues[]`, `status`
- Each window row must include `window-id`, `input-unit`, `unit-type`, `source-document`, `line-ranges[]`, `context-line-ranges[]`, `linked-global-atom-ids[]`, `dossier-path`, `source-sha256`, and `window-text-sha256`

Phase 5:

- `atom-plan-mapping.json`: required for `accepted` or `adjusted`; one row for every global atom with final owner/projection/relation/decision/reason
- `final-packet-index.json`: required for `accepted` or `adjusted`; per change direct atom IDs, owner-scoped non-direct atom IDs, capability view paths, packet path, and packet digest
- `phase-5.trace.json`: final status, complexity summaries, capability progression summaries, reviewer/validator gate outcomes

## Validator Commands

Run after each phase:

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/validate_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --phase phase-<n> \
  --json
```

Run before handoff to `openspec-propose`:

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/validate_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --phase all \
  --complete \
  --json
```

Use `--strict-warnings` when a reviewer wants warning-free output to become a hard gate.
