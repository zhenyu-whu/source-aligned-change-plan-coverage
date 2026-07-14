---
name: source-aligned-change-plan-coverage
description: 当用户明确要求从指定 source document 出发，在 openspec-propose 之前建立具备 evidence occurrence 覆盖、source trace、gap 分类和最终 plan refit 的 OpenSpec Change/Capability 全局计划时使用；确保每个 extracted evidence occurrence 拥有独立 GA 并映射到 final Change/Capability framework。
---

# source-aligned-change-plan-coverage：五阶段编排协议

先从完整source document建立Capability-first初始Change/Capability framework，再提取source atom、审计覆盖补集、为每个evidence occurrence建立独立GA，随后直接汇总Phase 2/3冻结的原文并用与Phase 1相同的framework标准完成最小plan refit。本技能不执行semantic duplicate识别或去重。

本工作流遵循`Capability-first、Outcome-sliced、Obligation-later`：Phase 1使用共享标准建立initial framework；Phase 2/3完成obligation extraction和coverage closure；Phase 4直接重排冻结`source-fact`；Phase 5复用同一标准复审initial framework、完成baseline reconciliation和final mapping。

## 输入与执行授权

- 必需：source document 根目录或精确 source document path。
- 可选：作为 Phase 1 candidate input 的现有 Change 计划。
- 所有 workflow artifact 写入 `openspec/orchestrate/`；具体布局由 Phase reference 和 trace contract 定义。
- 只有用户明确要求使用本技能处理指定 source document 时，才启动五阶段工作流。解释、审阅或修改本技能本身不构成执行授权。
- 用户明确要求执行本技能后，视为已授权启动必需的 Phase、reviewer 和 repair subagent，无需为每次 spawn 重复确认。

## Reference 路由

共享 contract：

- `references/cross-phase-contract.md`：所有 Phase 和 reviewer/repair 必须直接加载的跨 Phase 语义。
- `references/change-capability-framework-principles.md`：Phase 1和Phase 5必须直接加载的唯一Change/Capability标准。
- `references/trace-sidecar-contract.md`：Phase-specific authority、manifest、renderer、validator 和 schema。
- `references/reviewer-repair-loop.md`：统一 writer/reviewer/repair/final-integration 闭环。

每个 Phase 使用下表中的唯一任务 contract：

| Phase | Reference |
| --- | --- |
| Phase 1 | `references/phase-1-initial-change-plan.md` |
| Phase 2 | `references/phase-2-source-anchor-coverage.md` |
| Phase 3 | `references/phase-3-coverage-review-iteration.md` |
| Phase 4 | `references/phase-4-frozen-evidence-collections.md` |
| Phase 5 | `references/phase-5-targeted-plan-adjustment.md` |

## Agent 拓扑与运行时

- main agent 只负责编排和 interface gate，包括初始化、调度、Phase 2 work queue、manifest/validator 和状态转换。不得代写、重做或修复 Phase 内容。
- Phase 1、Phase 3、Phase 4、Phase 5 各由 fresh independent writer subagent 完成。
- Phase 2 按 source document 或 coherent batch 启动一个或多个 fresh extraction writer；每份 source document 恰好一个 canonical extraction owner。全部完成后，再启动 fresh independent index/report writer。不得按 planned Change 分配 extraction。
- writer、reviewer 和 repair-writer 都是单层 leaf worker，不得启动 nested subagent、`codex exec`、multi-agent worker 或其他 agentic child process，也不得自行进入另一 Phase。
- reviewer 必须不同于 writer；repair-writer 必须不同于 writer 和所有 reviewer。validator 或 writer self-check 不能替代 independent reviewer。
- 所有 Phase writer、index/report writer、reviewer 和 repair-writer 必须使用 `model=GPT-5.5`、`reasoningEffort=xhigh`。runtime 无法保证时立即返回 blocker，不得降级或由 main agent 代做。
- main agent必须在每个worker prompt中要求直接完整读取`references/cross-phase-contract.md`和对应Phase reference；Phase 1/5 worker还必须读取共享framework原则。final integration reviewer必须读取共享原则及Phase 3–5 reference。prompt摘要不能替代原文件。

## Phase 状态机

| Phase | 内容责任 | Canonical terminal status | 下一步 |
| --- | --- | --- | --- |
| Phase 1 | 完整阅读 source，先形成 candidate Capability topology，再形成 outcome-sliced Change roadmap；不提取 obligation | `initial-plan-written` | Phase 2 |
| Phase 2 | source-first atom extraction 与独立 aggregation | `source-atoms-written` | Phase 3 |
| Phase 3 | 机械 complement、遗漏补提取与 evidence occurrence GA index | `coverage-complete` | Phase 4 |
| Phase 3 | broad/失效 extraction | `needs-extraction-recheck` | targeted Phase 2，再执行 Phase 3 |
| Phase 3 | 无法稳定 coverage/evidence identity | `blocked` | 停止并报告 |
| Phase 4 | 确定性assembler按initial Change/Capability和unassigned/gap生成冻结原文Markdown，再生成派生index | `assembled` | Phase 5 |
| Phase 4 | 暴露 missing/broad/conflicting extraction | `needs-coverage-recheck` | 按 finding targeted Phase 2/3，再执行 Phase 4 |
| Phase 4 | 无法解析冻结evidence | `blocked` | 停止并报告 |
| Phase 5 | 使用共享标准完成initial framework逐项复审与最小refit | `accepted` 或 `adjusted` | final validation 与 handoff |
| Phase 5 | 暴露 missing/broad/conflicting extraction | `needs-coverage-recheck` | 按 finding targeted Phase 2/3，再执行 Phase 4、Phase 5 |
| Phase 5 | 需要用户决定或越权 reanalysis | `blocked` | 停止并报告 |

recheck 必须 targeted 到受影响的 Phase 2 source/atom；不得无依据重跑全部 extraction。

## 工作流

1. 验证 source path 和必需 runtime，完整读取三份共享 contract，并按 trace contract 初始化目录及 `trace/manifest.json` skeleton。
2. 按“恢复规则”检查现有 evidence，确定第一个必须执行的 Phase。
3. 完整读取当前 Phase reference，并要求 Phase worker 直接读取 `references/cross-phase-contract.md` 和该 Phase reference。进入 Phase 2 时，main agent 先按其 reference 创建 work queue，再按 queue 调度 extraction。
4. 使用 Agent 拓扑约束构造 prompt，启动对应 writer 并等待完成；Phase 2 依次完成全部 extraction writer 和独立 index/report writer。不得因耗时或 partial output 重复启动、替换或中断 worker。
5. writer 返回后，只按当前 Phase reference 检查必需 interface output、report 和 blocker；main agent 不得自行补写或重做 Phase 内容。
6. 根据当前应登记JSON的digest与authority刷新manifest，按trace contract运行当前Phase validator；先重渲染Phase 2/3 mirror、Phase 4 collection/index及Phase 5派生物。
7. 完整执行 `references/reviewer-repair-loop.md`。若发生 repair，依次重新刷新 manifest、运行 validator 并启动 fresh independent reviewer，直至 pass 或 block。
8. validator 和 reviewer 均通过后，再次刷新 manifest，使 canonical Phase status/decision 和 artifact digest 与 Phase trace 一致。
9. 按“Phase 状态机”推进：正常进入下一 Phase；`needs-extraction-recheck` targeted 回 Phase 2；`needs-coverage-recheck` 根据 missing/broad finding回 Phase 3或 targeted Phase 2；`blocked` 停止并报告。
10. Phase 5 达到 `accepted` 或 `adjusted` 后，进入“完成与 handoff”；不得从普通 Phase pass 直接启动 `openspec-propose`。

## 恢复规则

1. 读取现有 manifest、Phase trace、artifact digest、validator result 和 reviewer evidence，从 Phase 1 起寻找第一个未完成或失效的 Phase。
2. Phase 只有同时满足以下条件才可跳过：Phase trace status/decision正确；manifest status与trace一致且全部登记JSON的digest/authority当前有效；Phase-specific authority与全部派生物通过validator；存在由不同身份完成且明确pass的independent reviewer evidence（Phase 3使用`phase-3.trace.json.reviewer-loop`，其他Phase使用非canonical reviewer report）；所有finding已repair或记录accepted non-blocking warning。
3. Phase 1 只发布 `phase-works/phase-1/initial-change-plan.md`；根 `change-plan.md` 仅由 Phase 5 在 `accepted` 或 `adjusted` 后发布。仅存在根计划、旧文件名的 Phase 1 snapshot 或 v1 Phase 1 trace 均不代表 Phase 1 完成。若缺少有效 Phase 1 evidence，运行 fresh Phase 1，并把用户提供的现有计划作为 candidate input。
4. 缺少有效 writer output 或 Phase trace 时运行 fresh Phase writer；已有完整 writer output 但存在 validator/reviewer finding 时进入 repair loop。最早失效 Phase 之后的 output 均视为 stale，不得用于跳过后续 Phase。
5. source document集合或digest变化使Phase 1及其下游失效；Phase 2 frozen evidence仅在其source digest、canonical owner或必需output本身失效时重建。Phase 1–3 JSON仍有效但render contract过期时只刷新Phase 2/3 Markdown；旧Phase 4/5 schema、旧Phase 4布局或缺少refit JSON时从Phase 4重建，不迁移旧布局。

## 完成与 handoff

- Phase 5 为 `accepted` 或 `adjusted` 后，必须让 `phase-works/phase-5/change-plan.md` 与根 `change-plan.md` 完全一致，再按 trace contract 执行 all-phase complete validation，并运行 fresh independent final integration reviewer。
- final integration reviewer必须核对global atom index、Phase 4 collection Markdown及派生index、framework refit JSON及review mirror、atom-plan mapping、Capability baseline、final Change packet、Capability view、anchor index和根`change-plan.md`的一致性。
- final integration reviewer 必须确认每个 Phase 2/3 evidence occurrence都有独立 GA和独立 Phase 5 mapping，且没有 semantic duplicate处理或基于 GA数量的 framework推断。
- 只有 complete validator 和 final integration reviewer 都通过，且 final Change packet 已存在时，才允许从 packet 启动 `openspec-propose`。
- handoff 必须明确：final packet是未语义去重的完整 evidence mapping；后续规格生成可以综合多个 GA，但必须保留多对一 trace。
- 任一 Phase 返回 `blocked` 时停止工作流，报告 blocker、已验证 evidence 和恢复所需的最小用户决定；main agent 不得越权补做 Phase 内容。
