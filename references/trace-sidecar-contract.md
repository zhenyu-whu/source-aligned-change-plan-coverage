# Trace sidecar contract

本技能采用Phase-specific authority。JSON用于精确校验、检索和跨产物映射，但并非每个Phase的内容权威；Markdown是否为权威由下表决定。

## 全局版本与权威边界

- trace contract：`source-aligned-trace-v2`
- render contract：`source-aligned-render-v6`
- JSON key使用kebab-case；ID不含Markdown反引号；多ID使用array。
- canonical line evidence为`line-ranges: [{"start": 1, "end": 2}]`。
- Phase 2 atom和Phase 3 gap atom各包含一个连续range及冻结的`source-fact`；后续索引和mapping只保存reference。

| Phase | 内容权威 | 机器校验与派生产物 |
| --- | --- | --- |
| Phase 1 | `initial-change-plan.md` | Phase trace中的source manifest数据、source digest与plan digest |
| Phase 2 | 每份`.atoms.json` | 每份atoms Markdown mirror、由work queue/atoms/Phase trace渲染的`index.md` |
| Phase 3 | global atom index JSON与coverage review JSON | 对应Markdown mirror |
| Phase 4 | 由确定性assembler直接生成的evidence collection Markdown | 派生`evidence-collection-index.json` |
| Phase 5 | final `change-plan.md`、`framework-refit-trace.json`、`atom-plan-mapping.json` | review mirror、baseline、packet、Capability view、anchor index |

work queue、agent report、reviewer report和repair report是非canonical流程证据，直接写Markdown，不进入manifest。

Phase 1–3 JSON schema保持兼容。旧Phase 4 index v1、Phase 4 trace v2、Phase 5 trace v2及缺少framework refit JSON的Phase 5输出一律拒绝；不提供迁移脚本，恢复时从Phase 4重建，并以v6 renderer刷新Phase 2/3 Markdown。

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
    ├── phase-1/
    │   ├── initial-change-plan.md
    │   ├── source-doc-manifest.md
    │   └── phase-1-agent-report.md
    ├── phase-2/
    │   ├── source-obligation-atoms/work-queue.md
    │   ├── source-obligation-atoms/index.md
    │   ├── source-obligation-atoms/<source>.atoms.json|md
    │   └── phase-2-agent-report.md
    ├── phase-3/coverage-review.json|md
    ├── phase-4/
    │   ├── phase-4-agent-report.md
    │   └── source-evidence-collections/
    │       ├── evidence-collection-index.json
    │       ├── index.md
    │       ├── by-input-change/*.md
    │       ├── by-input-capability/*.md
    │       └── unassigned-and-gap.md
    └── phase-5/
        ├── change-plan.md
        ├── framework-refit-trace.json
        ├── plan-refit-review.md
        ├── atom-plan-mapping.json|md
        ├── capability-baseline-reconciliation.json|md
        ├── final-packet-index.json
        └── phase-5-agent-report.md
```

## Schema

Phase trace：

- `source-aligned-phase-1-trace-v2`
- `source-aligned-phase-2-trace-v3`
- `source-aligned-phase-3-trace-v2`
- `source-aligned-phase-4-trace-v3`
- `source-aligned-phase-5-trace-v3`

Artifact：

- `source-aligned-source-atoms-v4`
- `source-aligned-global-atom-index-v3`
- `source-aligned-phase-3-coverage-review-v1`
- `source-aligned-evidence-collection-index-v2`
- `source-aligned-framework-refit-trace-v1`
- `source-aligned-atom-plan-mapping-v4`
- `source-aligned-capability-baseline-v1`
- `source-aligned-final-packet-index-v2`

## Manifest v2

`trace/manifest.json`使用`source-aligned-orchestrate-manifest-v2`，顶层必须且只能包含`trace-schema`、`trace-contract-version`、`authority: control`、`orchestrate-dir`、`phase-statuses`和`artifacts[]`。

每个artifact row必须且只能包含：

- `json-path`
- `trace-schema`
- `sha256`
- `phase`
- `role`
- `authority`

`authority`枚举：

- `semantic`：Phase 2 atoms、Phase 3 global index/coverage review、Phase 5 refit trace/mapping。
- `derived`：Phase 4 index、Phase 5 baseline/packet index。
- `control`：各Phase trace；manifest自身通过顶层`authority`声明，不自列以避免digest循环。

Markdown不进入manifest。manifest只列当前存在且应登记的JSON，每份恰好一次；每次validator前刷新digest，validator/reviewer通过后刷新Phase status。Phase 1/2读取trace`status`，Phase 3读取`decision`，Phase 4/5读取`status`。

## Evidence resolver

- Phase 2 evidence ref按`source-document + source-atom-id`加载source path、唯一range、`source-fact`、type、normativity和candidate hint。
- Phase 3 evidence ref按`gap-atom-id`从coverage review加载同类字段和review judgment。
- ref不存在、重复或类型不匹配是blocker。
- resolver不得读取source document，不比较不同evidence的语义。

## Phase 2/3 JSON渲染

- Phase 2每份`.atoms.md`完全由对应`.atoms.json`渲染。
- Phase 2 `index.md`由work queue、全部atoms JSON和`phase-2.trace.json`聚合渲染；agent report保持非canonical Markdown。
- Phase 3 global index与coverage review Markdown完全由对应JSON渲染；covered、uncovered和recheck range统一从`{start,end}`生成`Lx-Ly`。
- coverage Markdown必须呈现`language-self-check`。
- validator对上述Markdown逐字重渲染比较；任何手改都属于drift。

## Phase 4 assembler与派生index v2

Phase 4 assembler只读Phase 1 initial plan、Phase 2 atoms JSON、Phase 3 global index/coverage review，依次解析全部GA/evidence ref、机械计算Change/Capability/unassigned bucket、生成所有collection Markdown，最后生成派生index。不得从index反向生成Markdown，不得引入语义判断。

`evidence-collection-index.json`顶层只包含：

- `trace-schema`
- `trace-contract-version`
- `generated-from[]`：每行`artifact-path`、`sha256`
- `rows[]`
- `rendered-artifacts[]`

每个`rows[]` item只包含`global-atom-id`、`evidence-ref`、`change-bucket`、`capability-bucket`、`rendered-collection-paths[]`。每个GA恰好一行。

每个`rendered-artifacts[]` item只包含`artifact-path`、`sha256`、`collection-kind`、`owner-id`。

terminal `phase-4.trace.json`使用：

```json
{
  "trace-schema": "source-aligned-phase-4-trace-v3",
  "trace-contract-version": "source-aligned-trace-v2",
  "status": "assembled",
  "assembled": {
    "evidence-collection-index-path": "...",
    "evidence-collection-index-sha256": "...",
    "renderer-result-summary": {
      "render-contract-version": "source-aligned-render-v6",
      "rendered-files": 0,
      "global-atoms": 0
    }
  }
}
```

`needs-coverage-recheck|blocked` trace只包含schema/version、status和非空`issues[]`；不得保留index或collection Markdown。

validator从Phase 1–3重新计算全部Markdown和派生index，并检查缺失、篡改、stale文件、GA基数、上游digest和`source-fact`逐字一致性。

## Phase 5 framework refit trace v1

`framework-refit-trace.json`顶层必须且只能包含：

- `trace-schema`、`trace-contract-version`、`status`
- `initial-plan-ref`
- `capability-reviews[]`
- `change-reviews[]`
- `unassigned-and-gap-reviews[]`
- `final-framework`
- `issues[]`
- `language-self-check`

每个initial Capability和initial Change必须按原顺序恰好一行；每个Phase 4 unassigned/gap GA必须恰好一行。review row记录input unit、evidence collection、decision、final IDs、结构化`gate-results[]`和简体中文reason；gap row记录GA、evidence ref、disposition、final Change/Capability和reason。

terminal `final-framework`包含`change-order[]`、`capabilities[]`和`overlay[]`；每个overlay row包含`change`、`capability`、`capability-impact: new|modified`。

- `accepted`：所有initial unit为`keep`，所有gate通过，final framework及其语义与Phase 1实质一致。
- `adjusted`：所有gate通过，且至少一个split/merge/add/remove/rename/reorder/scope adjustment可追溯。
- `needs-coverage-recheck|blocked`：`final-framework: null`、非空`issues[]`，并禁止terminal artifact。

`plan-refit-review.md`完全由refit JSON渲染。final `change-plan.md`继续直接编写；validator校验其Change/Capability集合、顺序和overlay与`final-framework`一致，并对`accepted`执行Phase 1语义等价检查。

## Phase 5 mapping、派生物与trace

atom mapping v4顶层包含`trace-schema`、`trace-contract-version`、`artifact-path`和`rows[]`。每个GA恰好一行，只包含：

- `global-atom-id`、`evidence-ref`
- `final-owner-change`、`final-relation`、`final-artifact-projection`
- `final-capability-impact`、`final-target-capability`、`related-capabilities[]`
- 简体中文`reason`

mapping不复制source path/range/fact，也不包含equivalence、duplicate status或delivery group。validator交叉校验refit gap disposition的owner/target以及mapping推导的overlay advancement。

Phase 5 helper只读final plan、refit JSON、mapping JSON及Phase 2/3 resolver；不得从review Markdown取得语义。它确定性生成review mirror、mapping mirror、baseline、packet、Capability view、anchor index和packet index，validator逐字或逐结构重算全部派生产物。

terminal `phase-5.trace.json`记录final plan、refit JSON、review mirror、mapping、baseline和packet index各自的path/SHA。非终态trace只记录refit JSON、review mirror、与refit一致的非空`issues[]`，不得引用或保留terminal artifact。

## Renderer

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact all-supported \
  --write
```

支持Phase 2 atoms/index、Phase 3 global index/coverage review、Phase 4 assembler/index、Phase 5 refit review/mapping/baseline。

## Validation与handoff

- validator检查schema、digest、ID、reference cardinality、frozen source quote、coverage complement、render drift和跨artifact一致性。
- Phase 4 assembler/validator及Phase 5 helper不得读取source document；source quote验证只属于Phase 2/3。
- validator不检查semantic duplicate，也不因GA数量推断framework。
- final packet和plan必须声明它是完整evidence mapping，不是经过语义去重的requirement inventory。
