# Phase 5：framework refit、final roadmap 与 terminal mapping authoring

这是 Phase 5 writer 的角色专用 contract。不得向 writer 暴露 review gate、repair contract、trace 状态机、检查项枚举、预算或历史 review。

## Writer 输入

- Phase 1 initial framework；
- Phase 3 frozen global atom index 与 coverage authority；
- Phase 4 中性 evidence collections；
- 全部 source document；
- `change-capability-framework-principles.md`；
- `cross-phase-contract.md`；
- 本文件。

Writer 不读取 `review-gates.md`、`bounded-repair-contract.md`、`trace-sidecar-contract.md`、manifest、任何 `reviews/` 文件或 reviewer/repair report。

## Writer 输出

只写 Phase 5 candidate authority：

- `phase-works/phase-5/framework-refit-trace.json`
- `phase-works/phase-5/final-roadmap.json`
- `phase-works/phase-5/atom-plan-mapping.json`
- `phase-works/phase-5/phase-5-agent-report.md`

Writer 不创建或更新 Phase 5 trace，不发布根 `change-plan.md`、public anchors、packet、baseline 或 workflow completion。

## Framework refit

逐个初始 Capability 与 Change 作出 keep、split、merge、remove、rename 或 scope-adjusted 判断，并绑定冻结 GA。判断必须回答：

- 边界是否仍代表稳定、独立责任；
- Change 是否产生单一可验收 outcome；
- acceptance 是否验证行为结果而非内部动作；
- capability overlay 是否只表达推进关系；
- guard 是否与首次受保护 outcome 共同交付；
- foundation 是否只承载真实共享 baseline。

`framework-refit-trace.json` 必须绑定 initial framework 与 final roadmap digest；blocked 时不得伪造 final roadmap。

## Final roadmap

`final-roadmap.json` 是最终计划语义 authority，保持现有 v8 contract shape。它必须完整描述：

- final capabilities、changes 与 overlay；
- outcome threads；
- typed dependency edges；
- guard links；
- change order 与 ordering rationale；
- optional foundation；
- semantic landscape；
- source-backed evidence GA。

### Dependency edge soundness

每条 edge 分别证明 predecessor stable outcome、consumer consumption、反事实必要性，以及不是共享 infrastructure 或 same-change co-delivery。

### Dependency set completeness

逐 Change 从 normative behavior、acceptance、outcome threads 与 consumer closure 反查全部稳定消费。每项 consumption 必须由下列恰好一项解释：

1. typed dependency edge；
2. existing baseline；
3. same-change co-delivery。

仅共享 schema、runtime node、library 或 infrastructure，不消费稳定业务 outcome 时不得创建 edge。

## Terminal mapping

`atom-plan-mapping.json` 必须让每个 GA 恰有一行 terminal disposition：

- `direct`
- `context`
- `dependency`
- `preserve`
- `reference`
- `non-goal`

Direct obligation 必须落到最终 Change 与 artifact projection；Capability impact 必须与 overlay 一致。Dependency evidence 必须绑定现有 typed edge，不得用 mapping 临时创建关系。显式 delivery directive 必须在 terminal Change/order 中得到可验证 resolution。

## Authoring 完成条件

- refit、roadmap、mapping 三份 JSON 内部一致；
- 每个 GA 唯一处置；
- 每个 final Change 有 source-backed outcome、acceptance 与 archive condition；
- dependency soundness 与 set completeness 同时成立；
- 无未解决 issue；
- 所有解释字段使用简体中文。

达到上述条件后停止，由 main agent 使用 helper 生成 candidate mirrors、七项 digest、trace、validator 与独立 bounded review。
