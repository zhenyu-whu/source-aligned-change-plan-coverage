# Phase 1：初始 Change / Capability framework authoring

这是 Phase 1 writer 的角色专用 authoring contract。不得把 review gate、repair、trace 状态机、检查项枚举、轮次预算或历史结果提供给 writer。

## Writer 输入

- 用户指定的全部 source document；
- `change-capability-framework-principles.md`；
- `cross-phase-contract.md`；
- 本文件。

Writer 不读取 `review-gates.md`、`bounded-repair-contract.md`、`trace-sidecar-contract.md`、manifest、任何 `reviews/` 文件或历史 reviewer/repair report。

## Writer 输出

只写：

- `phase-works/phase-1/initial-framework.json`
- `phase-works/phase-1/initial-change-plan.md`
- `phase-works/phase-1/source-doc-manifest.md`
- `phase-works/phase-1/phase-1-agent-report.md`

Writer 不创建或更新 `review-pending` trace，不写 manifest。

## Source reading

- 全量读取每份 source；记录 path、read status、source role、coarse topics、line count 与 SHA-256。
- 不得只依据标题、摘要或关键词决定框架。
- source 之间冲突时保留冲突，不擅自选择业务策略。
- source occurrence 的细粒度提取属于 Phase 2；Phase 1 只建立 source-backed 初始 framework。

## Initial framework

`initial-framework.json` 是唯一语义 authority，schema 为 `source-aligned-initial-framework-v1`，并声明 `source-aligned-trace-v8`。

顶层保持现有 schema shape：

- `trace-schema`
- `trace-contract-version`
- `artifact-path`
- `changes`
- `capabilities`
- `overlay`
- `outcome-threads`
- `dependency-edges`
- `guard-links`
- `change-order`
- `foundation`
- `semantic-landscape`
- `issues`
- `language-self-check`

每个 Change 必须表达 intent、stable outcome、trigger、normative behavior、observable outcome、exception semantics、acceptance、scope、dependency、ordering reason、archive condition 与 split/merge judgment。

每个 Capability 必须表达 purpose、owns、excludes 与 boundary rationale。`overlay` 只表达 Change 对 Capability 的推进，不表达时序。

## Dependency authoring

Writer 必须同时满足：

- edge soundness：每条已声明 edge 符合共享四项条件；
- set completeness：逐 Change 从 behavior、acceptance 与已知 consumer 反查真实稳定 outcome consumption；
- 每个 consumption 在 typed edge、existing baseline、same-change co-delivery 中恰有一个解释；
- 仅共享 schema/runtime/infrastructure 不创建 edge。

若 source 只支持候选关系或存在业务决策缺口，在 `issues` 中明确阻断，不伪造 edge。

## Mirror 与报告

- `initial-change-plan.md` 必须由 JSON authority 确定性渲染。
- source manifest 只记录 source 读取事实。
- agent report 说明 authoring 选择、source 冲突与未决问题，不包含自评 gate 结论。
- 所有解释字段使用简体中文。

完成 writer 输出后立即停止，由 main agent 接管渲染校验、trace 与独立 review。
