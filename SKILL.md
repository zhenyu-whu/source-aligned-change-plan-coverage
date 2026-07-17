---
name: source-aligned-change-plan-coverage
description: 当用户明确要求从指定 source document 出发，在 openspec-propose 之前建立具备 evidence occurrence 覆盖、source trace、potential mapping ambiguity 裁决和最终 framework refit 的 OpenSpec Change/Capability 全局计划时使用；确保每个 extracted evidence occurrence 拥有独立 GA，并映射到 final Change/Capability framework。
---

# source-aligned-change-plan-coverage：五阶段编排协议

从完整 source document 建立 Capability-first initial framework，再依次完成自然语义单位提取、source coverage 闭合、冻结 evidence 的确定性汇总，以及最小 framework refit 与逐 GA final mapping。本技能不识别或消除 semantic duplicate。

## 输入与授权

- 必需输入是 source document 根目录或精确 path；可选输入是 Phase 1 candidate Change 计划。
- 所有 workflow artifact 写入 `openspec/orchestrate/`。
- 只有用户明确要求对指定 source 执行本技能时才启动工作流；审阅或修改技能本身不构成执行授权。
- 执行授权包括必需的 Phase worker、Phase 1 bounded reviewer/repair worker、Phase 2/3 evidence-freeze reviewer/repair worker，以及一次 final integration reviewer。

## Reference 路由

所有 worker 必须直接读取对应文件；prompt 摘要不能替代原文。

- `references/cross-phase-contract.md`：所有 worker 的跨 Phase 不变量。
- `references/trace-sidecar-contract.md`：机器接口、schema、renderer、validator 与 authority。
- `references/change-capability-framework-principles.md`：Phase 1 与 Phase 5 共用的唯一 framework 标准。
- `references/review-gates.md`：Phase 1 bounded review、Phase 2/3 evidence-freeze gate 与 workflow terminal integration gate。

| Phase | 唯一任务 contract |
| --- | --- |
| Phase 1 | `references/phase-1-initial-change-plan.md` |
| Phase 2 | `references/phase-2-source-anchor-coverage.md` |
| Phase 3 | `references/phase-3-coverage-review-iteration.md` |
| Phase 4 | `references/phase-4-frozen-evidence-collections.md` |
| Phase 5 | `references/phase-5-framework-refit-and-mapping.md` |

加载规则：

- Initial Phase 1/5 writer 额外加载共享 framework 原则；Phase 1 reviewer/repair 同样加载。
- Phase 2/3 reviewer与repair writer必须加载cross-phase、review gate及Phase 2/3 task contract；prompt摘要不能替代原文。
- Final integration reviewer加载cross-phase、共享原则、review gate及Phase 3–5 task contract。

## Agent 拓扑

- main agent 只负责编排、work queue、interface gate、manifest/validator 与状态转换，不代写 Phase 语义。
- Phase 1、Phase 3、Phase 5 使用 fresh independent semantic writer；Phase 4 使用确定性 assembler。
- Phase 2 按 source document 或 coherent batch 分配 fresh extraction writer；每份 source 恰好一个 canonical owner。全部完成后再启动 independent index/report writer。
- Phase 1 与联合Phase 2/3 evidence-freeze gate各自最多两轮repair、三轮fresh review；两个gate的预算和身份记录互不复用。
- Phase 2 extraction在Phase 3 evidence-freeze gate通过前都是provisional；Phase 4–5无Phase reviewer或repair loop。
- Final integration reviewer 是一次性 workflow-level 只读 gate，不属于 Phase 5 reviewer。
- 所有 worker 都是 leaf，不启动 nested agent、`codex exec` 或其他 agentic child process。

## Phase 状态机

| Phase | 职责 | 成功状态 | 下一步 |
| --- | --- | --- | --- |
| 1 | coarse semantic landscape、initial Capability topology 与 outcome-sliced roadmap | `initial-plan-written` | Phase 2 |
| 2 | 按自然语义单位提取 provisional evidence occurrence 和 existing-framework candidate hint | `source-atoms-written` | Phase 3，尚未冻结 |
| 3 | 闭合 source coverage、分配 provisional GA、执行联合 bounded review | `coverage-complete` | evidence freeze 后进入 Phase 4 |
| 4 | 按 initial bucket 确定性重排冻结 evidence，不作语义判断 | `assembled` | Phase 5 |
| 5 | 最小 refit、逐 GA final mapping、ambiguity 裁决与 baseline reconciliation | `accepted` / `adjusted` | complete validation |

Phase 1、Phase 4、Phase 5的source、authority、schema、validator或用户决策blocker，以及Phase 2/3联合gate耗尽repair预算或无法可信闭合，都使当前generation `blocked`。冻结后发现evidence integrity defect直接`blocked`；不得回写Phase 2/3或启动patch/checkpoint链。

## 工作流

1. 验证 source path，读取共享 contract，初始化目录与 manifest skeleton。
2. 按恢复规则定位第一个失效 interface，并加载当前 Phase task contract。
3. 按 Agent 拓扑启动 worker；Phase 2 先创建 work queue，再分配 extraction。
4. Phase 1 writer 发布可校验 authority 后运行 validator 与 bounded review；最多两轮定向 repair。两者最终均通过才进入 Phase 2。
5. Phase 2 writer发布provisional atoms后先运行`--phase phase-2 --preflight`；聚合trace/mirror/index并通过普通Phase 2 validator后进入Phase 3，但不得声明evidence已冻结。
6. Phase 3机械闭合coverage并建立provisional GA，随后按review gate运行Phase 2/3 validator、fresh reviewer和最多两轮定向repair。repair后必须重算Phase 3并重跑两个validator；terminal review通过后最后发布`coverage-complete` commit marker，同时冻结Phase 2/3与GA。
7. Phase 4从冻结authority全量确定性生成；Phase 5只生成final refit/mapping，不回写candidate mapping。Phase 5 helper必须先校验refit/mapping envelope与canonical mirror path，再生成派生物；helper或validator失败即`blocked`，不得自动normalize、repair或重跑当前Phase。
8. Phase 5 terminal 后运行 all-phase complete validator 与一次 final integration reviewer；全部通过后才 handoff。

## 恢复与版本规则

- 从 Phase 1 起核对 manifest、canonical trace、authority digest 和 validator result；Phase 1与Phase 3还必须有有效bounded review evidence。
- Phase 1 只发布 `phase-works/phase-1/initial-change-plan.md`；根 `change-plan.md` 只由 Phase 5 terminal 状态发布。
- 最早失效authority之后的派生物均为stale。Phase 2/3未冻结时从当前未完成review round恢复，保留既有review/repair历史和预算；已冻结后不得修改evidence或GA。
- Phase 4只允许从冻结Phase 1–3全量重建派生surface；Phase 5只恢复或重建其final authority，不存在targeted、incremental或checkpoint resume模式。
- 旧workflow generation不迁移、不原地升级；`source-aligned-trace-v4`及更早generation保持原状态，新执行必须使用`source-aligned-trace-v5`并从Phase 1开始。

## 完成与 handoff

- `phase-works/phase-5/change-plan.md` 与根 `change-plan.md` 必须逐字节一致。
- Complete validator 与 final integration reviewer核对每个 occurrence 的 GA、Phase 4 collection、terminal mapping、baseline、packet、Capability view、anchor index和final plan一致性。
- Reviewer 必须确认所有 final Change/Capability 通过共享原则，全部已记录或 late-discovered ambiguity 只由同 GA mapping row裁决，且未执行 semantic dedup 或基于 GA 数量推断 framework。
- 失败时 workflow `blocked`，不自动repair、重新refit或修改冻结evidence。
- Handoff 声明 final packet 是未语义去重的完整 evidence mapping；下游可综合多个 GA，但必须保留多对一 trace。
