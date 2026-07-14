# Phase 4：逐 GA source-window grounding

Phase 4 在 Phase 3 `coverage-complete` 后运行。它通过 evidence resolver为每个 GA 加载 Phase 2 atom或 Phase 3 gap atom，再复制足以理解 evidence 的 source window。它不改变 extraction identity，也不判断语义重复。

writer 必须完整读取 `references/cross-phase-contract.md`、本文件和 `references/trace-sidecar-contract.md`。

## 输入

- Phase 1 `initial-change-plan.md`
- Phase 2 source atom JSON
- Phase 3 `obligation-atom-index.json`
- Phase 3 `coverage-review.json`
- 用户指定的原始 source document

不得依赖已移除的 Phase 3 manifest、per-document coverage、source map、remainder或 normalization artifact。

## 输出

- `phase-works/phase-4/input-change-plan.md`
- `phase-works/phase-4/source-window-dossiers/source-window-index.json`
- `phase-works/phase-4/source-window-dossiers/by-input-change/*.md`
- `phase-works/phase-4/source-window-dossiers/by-input-capability/*.md`
- `phase-works/phase-4/source-window-semantic-profile-review.md`
- `phase-works/phase-4/source-window-grounding-issues.md`
- `phase-works/phase-4/phase-4-agent-report.md`
- `trace/phase-4.trace.json`

`input-change-plan.md` 必须与 Phase 1 snapshot逐字节一致。

## Evidence resolver

对每个 global index row：

- `phase-2-source-atom`：从对应 Phase 2 JSON加载 source document、range、source-fact、type、normativity和 candidate hint。
- `phase-3-gap-atom`：从 Phase 3 coverage review加载 source document、range、source-fact、type和 normativity。

每个 GA 必须独立进入 grounding。不得比较两个 GA/window 是否表达相同语义，不得创建 equivalence、canonical或 duplicate finding。

完全相同的 source path和展示 window range可以共用一个 window，但 `linked-global-atom-ids[]` 必须列出所有关联 GA。这只是机械展示复用；不能改变 GA 数量、identity或 Phase 5 mapping cardinality。

## Window 选择

- 必须覆盖 resolved evidence range。
- 只扩展理解 trigger、behavior、outcome/invariant、exception、acceptance、auth/privacy、data、UI、API、worker或 external integration所需的最小局部上下文。
- 保留原始行号和原文；中文 semantic note写在 quote之外。
- 不得因为 source fact与另一 GA相同而跳过、合并或缩减 coverage。

`source-window-index.json` 必须使每个 GA至少出现一次。window source digest、range和 text digest必须可重算。

每个 window row必须严格使用 trace contract列出的十个字段，不得加入 duplicate/equivalence/canonical/delivery-unit metadata。`window-text-sha256` 必须等于按 `line-ranges[]` 顺序从原始 source取出并以换行连接后的文本 SHA-256；`context-line-ranges[]` 只作上下文索引，不混入该 digest。

## Scope

Phase 4 可以按 input Change/Capability组织 window和编写 semantic profile，并记录 split、merge、reorder、rename、dependency、boundary、evidence或 non-goal pressure。

Phase 4 不得：

- 修改 Phase 2/3 evidence或 GA identity；
- 创建、拆分、合并、删除、归组 GA；
- 判断 semantic duplicate；
- 决定 final owner、projection、relation或 Capability mapping；
- 发布 final Change packet或根 `change-plan.md`。

Phase 2 candidate hint只帮助导航，不是 Phase 4/5 authority。Phase 3 不含 planning metadata。

## Dossier 与 semantic profile

每个 input Change dossier至少包含：intent/outcome hypothesis、相关 source windows、GA/evidence ref、source range、原文 window、中文 semantic profile和 Phase 5 refit pressure。

Capability dossier只能依据 Phase 1 declared Capability和 source window中明确的 behavior boundary建立；不得从 atom数量或技术 label机械创造 Capability。

semantic profile检查：

- Change是否具有单一 intent、coherent outcome、可独立 acceptance/archive和必要 dependency；
- Capability是否具有稳定 Purpose/Owns/Excludes，且实现替换后仍成立；
- 异常、preserve/non-goal、verification和 source-window context如何影响 final mapping。

GA 数量只是 trace volume，不能作为 split/merge/complexity判断。

## Status

- `grounded`：每个 GA都有有效 resolver evidence和至少一个 source window，semantic profile足够供 Phase 5使用。
- `needs-coverage-recheck`：resolver暴露 missing evidence，或发现 Phase 2 atom broad/抽取不完整。main agent按 affected source targeted回到 Phase 2/3，再重跑 Phase 4。
- `blocked`：source缺失、digest/range冲突、需要用户决定或无法安全 grounding。

`source-window-grounding-issues.md` 必须记录 affected GA/source/range、影响和最小下一步。达到 `grounded` 后才能进入 Phase 5。
