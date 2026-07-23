# Phase 3：coverage closure authoring

这是 Phase 3 writer 的角色专用 contract。它不包含 reviewer oracle、repair 指令、预算或 trace 状态机。

## Writer 输入

- 全部 source document；
- Phase 2 canonical `.atoms.json`；
- `change-capability-framework-principles.md`；
- `cross-phase-contract.md`；
- 本文件。

Writer 不读取 `review-gates.md`、`bounded-repair-contract.md`、`trace-sidecar-contract.md`、manifest、任何历史 review/repair result 或 report。

## Writer 输出

只写：

- `change-capability-anchors/obligation-atom-index.json`
- `change-capability-anchors/obligation-atom-index.md`
- `phase-works/phase-3/coverage-review.json`
- `phase-works/phase-3/coverage-review.md`

Writer 不创建或更新 Phase 3 trace，不写 manifest。

## Global occurrence index

- 按 source path、line range、source atom ID 的稳定顺序分配 GA。
- 每个 Phase 2 occurrence 恰好对应一个 GA；重复文本 occurrence 不合并。
- GA row 保留 source document、line ranges、source fact、atom type、normativity、directive、candidate routing 与 Phase 2 authority digest。
- Markdown 由 JSON 确定性渲染。

## Coverage closure

- 对每份 read-full source，以全文 line range 减去所有 covered ranges 得到机械补集。
- 每个补集范围必须分类为 `missing-obligation`、`safe-non-obligation` 或 `blocked`。
- `missing-obligation` 必须回到 provisional Phase 2 authority 新增或拆分 occurrence；不得只在 coverage report 中补文字。
- `safe-non-obligation` 必须给出 source-backed 中文判断。
- `blocked` 必须说明缺少的 source、schema 或用户决策。
- 所有显式 delivery directive 必须保持 occurrence-level 完整性。

## Freeze candidate

只有以下事实同时成立，writer authority 才可交给 main agent：

- Phase 2 occurrence 与 global GA 双射；
- 每份 source 的 coverage 补集为空或全部有合法处置；
- delivery directive 无遗漏、无猜测补写；
- canonical JSON 与 Markdown mirror 一致；
- `issues` 为空且 decision 为 `coverage-complete`。

这只是 authoring candidate，不是 freeze marker，也不表示 review 已通过。由 main agent 执行 validator、trace 与独立 gate。
