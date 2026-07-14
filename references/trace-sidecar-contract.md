# Trace sidecar contract

JSON sidecar是validator的canonical输入；renderer-backed Markdown只是review mirror。

## 全局规则

- trace contract：`source-aligned-trace-v2`
- render contract：`source-aligned-render-v5`
- JSON key使用kebab-case；ID不含Markdown反引号；多ID使用array。
- canonical line evidence为`line-ranges: [{"start": 1, "end": 2}]`。
- Phase 2 atom和Phase 3 gap atom各包含一个连续range及frozen`source-fact`；Phase 3 global index和Phase 4/5 projection不复制evidence内容。
- canonical JSON变化后必须重新渲染mirror。

旧Phase 4 source-window schema/artifact、Phase 5 atom mapping v1–v3和已删除Phase 5报告不兼容；发现时必须拒绝并从Phase 4重新执行。Phase 1–3 schema保持兼容。

## 必需布局

```text
openspec/orchestrate/
├── change-plan.md
├── trace/
│   ├── manifest.json
│   └── phase-1.trace.json ... phase-5.trace.json
├── change-capability-anchors/
│   ├── obligation-atom-index.json|md
│   ├── index.md
│   └── <change>/...
└── phase-works/
    ├── phase-1/...
    ├── phase-2/source-obligation-atoms/<source>.atoms.json|md
    ├── phase-3/coverage-review.json|md
    ├── phase-4/source-evidence-collections/
    │   ├── evidence-collection-index.json
    │   ├── index.md
    │   ├── by-input-change/*.md
    │   ├── by-input-capability/*.md
    │   └── unassigned-and-gap.md
    └── phase-5/
        ├── change-plan.md
        ├── plan-refit-review.md
        ├── atom-plan-mapping.json|md
        ├── capability-baseline-reconciliation.json|md
        └── final-packet-index.json
```

## Schema

Phase trace：

- `source-aligned-phase-1-trace-v2`
- `source-aligned-phase-2-trace-v3`
- `source-aligned-phase-3-trace-v2`
- `source-aligned-phase-4-trace-v2`
- `source-aligned-phase-5-trace-v2`

Artifact：

- `source-aligned-source-atoms-v4`
- `source-aligned-global-atom-index-v3`
- `source-aligned-phase-3-coverage-review-v1`
- `source-aligned-evidence-collection-index-v1`
- `source-aligned-atom-plan-mapping-v4`
- `source-aligned-capability-baseline-v1`
- `source-aligned-final-packet-index-v2`

## Manifest

`trace/manifest.json` 使用`source-aligned-orchestrate-manifest-v1`，包含`trace-schema`、`trace-contract-version`、`orchestrate-dir`、`phase-statuses`和`artifacts[]`。

每个artifact row包含`artifact-path`、`trace-path`、`trace-schema`、`sha256`、`phase`和`role`。manifest只列现有canonical JSON且恰好一次。

每次validator前刷新digest；validator/reviewer通过后刷新canonical Phase status。Phase 1/2读取trace`status`，Phase 3读取`decision`，Phase 4/5读取`status`。

## Evidence resolver

- Phase 2 evidence ref按`source-document + source-atom-id`加载source path、range、source-fact、type、normativity和candidate hint。
- Phase 3 evidence ref按`gap-atom-id`从coverage review加载source path、range、source-fact、type、normativity和review judgment。
- ref不存在、重复或类型不匹配是blocker。
- resolver不得读取source document，不比较不同evidence的语义。

## Phase 4 evidence collection index

`evidence-collection-index.json` 使用`source-aligned-evidence-collection-index-v1`，顶层只包含`trace-schema`、`trace-contract-version`、`status`、`rows[]`、`issues[]`、`language-self-check`。

每行只包含`global-atom-id`、`evidence-ref`、`change-bucket`、`capability-bucket`。每个GA恰好一行，不复制任何resolved evidence字段。

`phase-4.trace.json`只包含schema/version、`status`、collection index path/SHA和`renderer-result-summary`；summary固定包含render contract、rendered file数量和global atom数量。

## Phase 5 atom plan mapping v4

顶层包含`trace-schema`、`trace-contract-version`、`artifact-path`和`rows[]`。每个GA恰好一行，只包含：

- `global-atom-id`
- `evidence-ref`
- `final-owner-change`
- `final-relation`
- `final-artifact-projection`
- `final-capability-impact`
- `final-target-capability`
- `related-capabilities[]`
- 简体中文`reason`

mapping不复制source path/range/fact，也不包含owner type、plan decision、equivalence、canonical GA、duplicate status或delivery group。

terminal `phase-5.trace.json`只包含schema/version、`status`，以及final plan、plan refit review、mapping JSON、baseline JSON和packet index JSON各自的path/SHA。`needs-coverage-recheck|blocked`只记录plan refit review path/SHA和非空`issues[]`，不得引用不存在的terminal artifact。

## Renderer

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact all-supported \
  --write
```

支持Phase 2 source atoms、Phase 3 global index/coverage review、Phase 4 evidence collections、Phase 5 atom mapping和Capability baseline。

## Validation与handoff

- validator检查schema、digest、ID、reference cardinality、frozen source quote、coverage complement、bucket、mirror drift和跨artifact一致性。
- Phase 4 renderer/validator不得读取source document；source quote验证只属于Phase 2/3。
- validator不检查semantic duplicate，也不因GA数量发出framework warning。
- final packet和plan必须声明它是完整evidence mapping，不是经过语义去重的requirement inventory。
