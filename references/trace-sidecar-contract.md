# trace sidecar contract

JSON sidecar 是 validator 的 canonical 输入；renderer-backed Markdown 只是 review mirror。

## 全局规则

- trace contract：`source-aligned-trace-v2`
- render contract：`source-aligned-render-v5`
- JSON key 使用 kebab-case；ID 不含 Markdown 反引号；多 ID 使用 array。
- canonical line evidence 为 `line-ranges: [{"start": 1, "end": 2}]`。
- Phase 2 atom和 Phase 3 gap atom各包含一个连续 range。Phase 3 global index不保存 range；Phase 4/5 通过 evidence resolver取得。
- canonical JSON 变化后必须重新渲染 mirror；不得只手改 Markdown。

本契约不兼容旧 Phase 3 global index v1/v2、Phase 3 trace v1、source-to-global map、source remainder review、atom-plan mapping v1/v2 和 render v1–v4。canonical layout 中出现这些旧 Phase 3 artifact 时必须拒绝。

## 必需布局

```text
openspec/orchestrate/
├── change-plan.md
├── trace/
│   ├── manifest.json
│   ├── phase-1.trace.json
│   ├── phase-2.trace.json
│   ├── phase-3.trace.json
│   ├── phase-4.trace.json
│   └── phase-5.trace.json
├── change-capability-anchors/
│   ├── obligation-atom-index.json
│   └── obligation-atom-index.md
└── phase-works/
    ├── phase-1/...
    ├── phase-2/source-obligation-atoms/<source>.atoms.json|md
    ├── phase-3/
    │   ├── coverage-review.json
    │   └── coverage-review.md
    ├── phase-4/source-window-dossiers/source-window-index.json
    └── phase-5/
        ├── atom-plan-mapping.json|md
        ├── capability-baseline-reconciliation.json|md
        └── final-packet-index.json
```

Phase 3 恰好拥有五个产物：上图两个 global index、两个 coverage review及 `trace/phase-3.trace.json`。

## Schema

Phase trace：

- `source-aligned-phase-1-trace-v2`
- `source-aligned-phase-2-trace-v3`
- `source-aligned-phase-3-trace-v2`
- `source-aligned-phase-4-trace-v1`
- `source-aligned-phase-5-trace-v1`

Artifact：

- `source-aligned-source-atoms-v4`
- `source-aligned-global-atom-index-v3`
- `source-aligned-phase-3-coverage-review-v1`
- `source-aligned-source-window-index-v1`
- `source-aligned-atom-plan-mapping-v3`
- `source-aligned-capability-baseline-v1`
- `source-aligned-final-packet-index-v2`

Phase 3 exact schema见 `references/phase-3-coverage-review-iteration.md`。

## Manifest

`trace/manifest.json` 使用 `source-aligned-orchestrate-manifest-v1`，包含：

- `trace-schema`
- `trace-contract-version`
- `orchestrate-dir`
- `phase-statuses`
- `artifacts[]`

每个 artifact row包含 `artifact-path`、`trace-path`、`trace-schema`、`sha256`、`phase`、`role`。manifest 只列出现有 canonical JSON，且恰好一次。Phase 3 只列 global index、coverage review 和 Phase 3 trace；不得列出已移除的 Phase 3 sidecar。

每次 validator 前刷新 digest；validator/reviewer 通过后再刷新 canonical Phase status。Phase 1/2 读取 trace `status`，Phase 3 读取 `decision`，Phase 4/5 读取相应 terminal field。

## Phase 2 source atom v4

顶层字段：`source-document`、`source-sha256`、`read-status`、`canonical-owner`、`source-role`、`phase-1-candidate-changes-capabilities-considered`、`source-atoms[]`、`blockers[]`、`language-self-check`。

每个 source atom只包含：`source-atom-id`、`line-ranges[]`、`atom-type`、`source-fact`、`normativity`、`candidate-status`、`candidate-artifact-projection`、`candidate-owner-change`、`candidate-target-capability`、`rationale`。`source-fact` 必须是唯一 range内的连续原文。

## Evidence resolver

resolver 输入 global index row：

- `phase-2-source-atom`：按 `source-document + source-atom-id` 从对应 Phase 2 JSON 加载 source path、range、source-fact、type、normativity 和 candidate hint。
- `phase-3-gap-atom`：按 `gap-atom-id` 从 `phase-works/phase-3/coverage-review.json` 加载 source path、range、source-fact、type 和 normativity。

不存在、重复或类型不匹配的 ref 是 blocker。resolver 不比较不同 evidence 的语义。

## Phase 4 source-window index

`source-window-index.json` 包含 `windows[]`、`semantic-profiles[]`、`grounding-issues[]`、`status`。每个 window包含 `window-id`、`input-unit`、`unit-type`、`source-document`、`line-ranges[]`、`context-line-ranges[]`、`linked-global-atom-ids[]`、`dossier-path`、`source-sha256` 和 `window-text-sha256`。

每个 GA 至少出现在一个 window。只有 source path和有效展示 range完全相同时，多个 GA 才可机械共用 window，并必须全部列入 `linked-global-atom-ids[]`。该复用不是 semantic dedup。

## Phase 5 atom-plan mapping v3

顶层包含 `trace-schema`、`trace-contract-version`、`artifact-path`、`rows[]`。每个 GA 恰好一行，包含：

- `global-atom-id`
- `evidence-ref`
- `source-document`
- 长度为 1 的 `line-ranges[]`
- `final-owner-type`
- `final-owner-change`
- `final-capability-impact`
- `final-target-capability`
- `related-capabilities[]`
- `final-artifact-projection`
- `final-relation`
- `plan-decision`
- 简体中文 `reason`

`evidence-ref` 必须与 global index相同；source/range 必须与 resolver output相同。mapping 不包含 Phase 3 owner/status/projection，也不包含 equivalence key、canonical GA、duplicate status 或 delivery-unit group。

## Renderer

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact all-supported --write
```

支持 Phase 2 source atoms、Phase 3 global index、Phase 3 coverage review、Phase 5 atom-plan mapping和 Capability baseline reconciliation。每个 mirror末尾必须包含 trace path、schema、digest 和 render contract。

## Validation 与 handoff

- validator 检查 schema、digest、ID、reference cardinality、range/source quote、coverage complement、mirror drift和跨 artifact一致性。
- validator 不检查 semantic duplicate，也不因 GA 数量发出 framework complexity warning。
- final packet和 human plan必须明确：这是完整 evidence mapping，不是经过语义去重的 requirement inventory；后续流程若综合多个 GA，必须保留多对一 trace。
