# v8 跨 Phase 共享语义契约

本文件只定义产品与 framework 的正向语义，不包含 review 检查枚举、预算、状态机或 repair 指令。它可由所有角色读取。

## Authority 与派生面

- JSON authority 是唯一语义权威；Markdown、index、packet、report 都是确定性派生面。
- 每个 source occurrence 在冻结前获得唯一稳定身份；冻结后不得修改原文证据、directive、reference 或 GA 编号。
- Change、Capability、outcome thread、dependency edge、guard link 与 terminal mapping 必须从同一组冻结证据形成闭合链。
- 派生面不得反向覆盖 authority，也不得成为后续 worker 的隐藏语义输入。

## 五阶段接口

1. Phase 1 建立初始 Change/Capability framework，不决定最终 evidence mapping。
2. Phase 2 按 source occurrence 提取义务原子和显式 delivery directive。
3. Phase 3 形成全局 GA index，闭合原文覆盖并冻结 evidence authority。
4. Phase 4 只从冻结 authority 确定性组装中性 evidence collections。
5. Phase 5 重新审视 framework，形成 final roadmap、terminal mapping 与最终 Change plan。

下游只能消费已声明的上游 authority；任何未声明、未冻结或来自 report/mirror 的信息都不是有效输入。

## Evidence occurrence

- occurrence 是“source document + line range + source fact”的具体出现，不按相似文本合并。
- 每个 occurrence 必须恰有一个 source atom，冻结后恰有一个 GA，并在 terminal mapping 中恰有一个处置。
- 同一事实在不同位置重复出现时保留多个 occurrence。
- coverage closure 必须以全文 line range 的机械补集为基础；未覆盖范围必须有明确处置。
- `milestone-scope`、`explicit-precedence`、`explicit-deferred` 是 source-facing directive；不得由后续规划猜测补写或删除。

## Change、Capability 与依赖

- Capability 是长期稳定的责任边界；Change 是一次可交付、可验收的结果增量。
- Capability adjacency 不等于 Change sequence，Capability 层级也不暗示 Change hard dependency。
- typed hard dependency 只有在四项同时成立时才合法：
  1. predecessor 产生独立、稳定、可命名的 outcome；
  2. consumer Change 的行为或验收实际消费该 outcome；
  3. 没有 predecessor 时 consumer 无法正确完成；
  4. 该关系不是共享 schema/runtime/infrastructure、相邻顺序或同一 Change 内 co-delivery。
- 完整性不变量：所有真实稳定 outcome consumption 都必须进入 typed edge set；不得只验证已声明 edge 的 soundness。
- 对每个消费关系，typed edge、existing baseline、same-change co-delivery 三者必须恰有一个成立。
- 共享 schema、library、runtime node 或 infrastructure 若不消费稳定业务 outcome，不产生 hard dependency。

## Freeze 与 terminal handoff

- Phase 3 freeze 后，Phase 4/5 不得回写 Phase 2/3 evidence。
- Phase 5 authority repair 只能重建完整 Phase 5 authority 与派生面。
- 根 `change-plan.md`、public anchors、final packet 与 workflow completion 只能从同一 terminal authority 原子发布。
- `status.isComplete`、artifact `done` 或结构 validator 通过，不等于语义 `apply-ready`。

## 语言与路径

- 所有 explanation、finding、warning、rationale、note 与 report 使用简体中文。
- 标识符、schema、枚举、路径和 source 原文保持原样。
- 所有 canonical path 必须是 repository-relative、无 symlink 穿越的普通文件路径。

## v8 硬切换

- v8 generation 使用 `source-aligned-trace-v8`，必须从新的干净 output root 开始。
- v7 generation 是只读历史；v8 validator、renderer、helper 必须 fail closed，且不得迁移、覆盖、删除或补写。
- 不提供 v7 migration 或兼容写入路径。
