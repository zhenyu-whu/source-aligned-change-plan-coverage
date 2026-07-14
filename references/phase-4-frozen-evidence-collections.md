# Phase 4：冻结原文集合汇总

Phase 4 在 Phase 3 `coverage-complete` 后运行。它通过 evidence resolver直接读取 Phase 2 atom和 Phase 3 gap atom中已经冻结的 `source-fact`，按 Phase 1 initial Change、initial Capability和 `unassigned-and-gap` 三个维度机械汇总原文。本 Phase 不读取原始 source document、不扩展 source window、不执行 framework判断。

writer 必须完整读取 `references/cross-phase-contract.md`、本文件和 `references/trace-sidecar-contract.md`。Phase 4 不加载 Change/Capability共享原则，因为它不得执行 refit。

## 输入

- Phase 1 `initial-change-plan.md`
- Phase 2 frozen source atom JSON
- Phase 3 `obligation-atom-index.json`
- Phase 3 `coverage-review.json`

不得读取原始 source document，也不得依赖旧 Phase 4 source-window artifact。

## 输出

```text
phase-works/phase-4/
├── source-evidence-collections/
│   ├── evidence-collection-index.json
│   ├── index.md
│   ├── by-input-change/<change>.md
│   ├── by-input-capability/<capability>.md
│   └── unassigned-and-gap.md
├── phase-4-agent-report.md
└── phase-4-reviewer-report.md

trace/phase-4.trace.json
```

只有 `evidence-collection-index.json` 是 canonical Phase 4 content；所有 Markdown collection都由 renderer生成。

禁止创建或保留：`input-change-plan.md`、`source-window-dossiers/`、`source-window-semantic-profile-review.md`、`source-window-grounding-issues.md`。

## Evidence resolver

对 global index中每个 GA：

- `phase-2-source-atom`：从对应 Phase 2 JSON加载 source document、唯一 range、`source-fact`、atom type、normativity、candidate status/projection/owner/target。
- `phase-3-gap-atom`：从 Phase 3 coverage review加载 source document、唯一 range、`source-fact`、atom type、normativity和 review judgment。

Phase 4信任经过 Phase 2/3 validator/reviewer冻结的 `source-fact`，不按 range重新读取 source。resolver ref不存在、重复或类型不匹配时不得猜测或重新提取。

## Canonical index

`evidence-collection-index.json` 使用 `source-aligned-evidence-collection-index-v1`，顶层字段必须且只能包含：

- `trace-schema`
- `trace-contract-version`
- `status`
- `rows[]`
- `issues[]`
- `language-self-check`

每个 `rows[]` item必须且只能包含：

- `global-atom-id`
- `evidence-ref`
- `change-bucket`
- `capability-bucket`

每个 GA恰好一行，`evidence-ref` 必须与 global index完全相同。不得复制 source fact、path、range、type、normativity、candidate metadata、source digest或任何 semantic grouping字段。

## Bucket规则

`change-bucket`：

- Phase 2 `candidate-owner-change` 精确引用 Phase 1 Change：使用该 Change slug。
- 其他 Phase 2 atom：使用 `unassigned-and-gap`。
- 所有 Phase 3 gap atom：使用 `unassigned-and-gap`。

`capability-bucket`：

- Phase 2 `candidate-target-capability` 精确引用 Phase 1 Capability：使用该 Capability slug。
- 其他 Phase 2 atom和所有 Phase 3 gap atom：使用 `none`。

Phase 4不得根据语义修正 candidate hint。一个 GA在 Change维度只有一个 primary bucket；它可以同时投影到一个 Capability collection，但不产生 final ownership或Capability advancement。

## Renderer

writer 写完 canonical index后必须运行：

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact phase4-evidence-collections \
  --write
```

renderer必须：

- 从 Phase 1 plan取得 Change intent/outcome和 Capability Purpose/Owns/Excludes；
- 从 resolver直接取得 frozen `source-fact`；
- 按 source document、range起点、GA ID稳定排序；
- 使用长度大于原文最大连续反引号长度的 code fence，使 fence内部文本逐字符不变；
- 显示 GA、evidence ref、source path/range、type、normativity和 Phase 2 candidate metadata或 Phase 3 gap provenance；
- 为每个 Phase 1 Change/Capability生成 collection；没有 GA时明确写 `无关联 evidence occurrence`；
- 在 `unassigned-and-gap.md` 中区分 Phase 2 unassigned、unresolved/contextual和 Phase 3 gap atom；
- 保留每个 evidence occurrence，绝不合并语义相同或原文相同的 GA。

## Status

- `assembled`：每个 GA恰好一个有效 row，resolver成功，bucket符合机械规则，所有 collection与renderer一致，`issues[]` 为空。
- `needs-coverage-recheck`：evidence ref缺失、frozen evidence不完整，或发现 broad/missing extraction。
- `blocked`：Phase 2/3 artifact或digest冲突，无法建立可信 resolver结果。

非 `assembled` 状态必须提供非空 `issues[]`，记录 affected GA/evidence ref、影响和最小下一步。

Phase 4不得记录 split、merge、rename、reorder、boundary、owner、projection或Capability impact判断。

## 完成条件

- canonical index、trace和agent report存在；
- scoped renderer无drift；
- validator通过；
- fresh independent reviewer确认 frozen source fact逐字呈现、empty initial unit collection存在、bucket机械正确且没有refit判断；
- trace使用 `source-aligned-phase-4-trace-v2` 并记录 collection index path/SHA；`renderer-result-summary`固定包含`render-contract-version`、`rendered-files`和`global-atoms`。
