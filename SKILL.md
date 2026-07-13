---
name: source-aligned-change-plan-coverage
description: 当用户明确要求从指定 source document 出发，在 openspec-propose 之前建立具备 obligation atom 覆盖、source trace、gap 分类和最终 plan refit 的 OpenSpec Change/Capability 全局计划时使用；确保每项可执行 production obligation 恰好归属于一个 final Change，并仅由适用的 direct spec atom 推进 Capability。
---

# source-aligned-change-plan-coverage：五阶段编排协议

将完整 source document 转换为规范化 global obligation atom index，再从稳定 atom 和原始 source-window semantics 推导可供 `openspec-propose` 消费的 final Change packet。本文件只定义 main agent 的编排协议；每个 Phase 的具体任务、artifact 和完成条件由对应 reference 定义。

## 输入与执行授权

- 必需：source document 根目录或精确 source document path。
- 可选：作为 Phase 1 candidate input 的现有 Change 计划。
- 所有 workflow artifact 写入 `openspec/orchestrate/`；具体布局由 Phase reference 和 trace contract 定义。
- 只有用户明确要求使用本技能处理指定 source document 时，才启动五阶段工作流。解释、审阅或修改本技能本身不构成执行授权。
- 用户明确要求执行本技能后，视为已授权启动必需的 Phase、reviewer 和 repair subagent，无需为每次 spawn 重复确认。

## Reference 路由

共享 contract：

- `references/cross-phase-contract.md`：所有 Phase 和 reviewer/repair 必须直接加载的跨 Phase 语义。
- `references/trace-sidecar-contract.md`：canonical JSON、manifest、renderer、validator 和 schema。
- `references/reviewer-repair-loop.md`：统一 writer/reviewer/repair/final-integration 闭环。

每个 Phase 使用下表中的唯一任务 contract：

| Phase | Reference |
| --- | --- |
| Phase 1 | `references/phase-1-initial-change-plan.md` |
| Phase 2 | `references/phase-2-source-anchor-coverage.md` |
| Phase 3 | `references/phase-3-coverage-review-iteration.md` |
| Phase 4 | `references/phase-4-source-window-grounding.md` |
| Phase 5 | `references/phase-5-targeted-plan-adjustment.md` |

## Agent 拓扑与运行时

- main agent 只负责编排和 interface gate，包括初始化、调度、Phase 2 work queue、manifest/validator 和状态转换。不得代写、重做或修复 Phase 内容。
- Phase 1、Phase 3、Phase 4、Phase 5 各由 fresh independent writer subagent 完成。
- Phase 2 按 source document 或 coherent batch 启动一个或多个 fresh extraction writer；每份 source document 恰好一个 canonical extraction owner。全部完成后，再启动 fresh independent index/report writer。不得按 planned Change 分配 extraction。
- writer、reviewer 和 repair-writer 都是单层 leaf worker，不得启动 nested subagent、`codex exec`、multi-agent worker 或其他 agentic child process，也不得自行进入另一 Phase。
- reviewer 必须不同于 writer；repair-writer 必须不同于 writer 和所有 reviewer。validator 或 writer self-check 不能替代 independent reviewer。
- 所有 Phase writer、index/report writer、reviewer 和 repair-writer 必须使用 `model=GPT-5.5`、`reasoningEffort=xhigh`。runtime 无法保证时立即返回 blocker，不得降级或由 main agent 代做。
- main agent 必须在每个 worker prompt 中要求直接完整读取 `references/cross-phase-contract.md` 和对应 Phase reference，并明确允许读写范围、runtime 要求和 leaf boundary；final integration reviewer 必须读取 Phase 3–5 reference。prompt 摘要不能替代原文件。

## Phase 状态机

| Phase | 内容责任 | Canonical terminal status | 下一步 |
| --- | --- | --- | --- |
| Phase 1 | 完整阅读 source，形成初始 Change/Capability slicing hypothesis | `initial-plan-written` | Phase 2 |
| Phase 2 | source-first atom extraction 与独立 aggregation | `source-atoms-written` | Phase 3 |
| Phase 3 | global atom normalization、coverage closure 和 gap audit | `coverage-complete` | Phase 4 |
| Phase 3 | 无法稳定 coverage/identity/boundary | `blocked` | 停止并报告 |
| Phase 4 | source-window dossier 与 semantic profile grounding | `grounded` | Phase 5 |
| Phase 4 | 暴露 missing/broad/conflicting obligation | `needs-coverage-recheck` | fresh Phase 3，再执行 Phase 4 |
| Phase 4 | 无法安全 grounding | `blocked` | 停止并报告 |
| Phase 5 | atom-driven plan refit 完成 | `accepted` 或 `adjusted` | final validation 与 handoff |
| Phase 5 | 暴露 missing/broad/conflicting obligation | `needs-coverage-recheck` | fresh Phase 3、Phase 4、Phase 5 |
| Phase 5 | 需要用户决定或越权 reanalysis | `blocked` | 停止并报告 |

除非 Phase 3–5 明确说明 targeted review 不足且用户要求完整 extraction rerun，否则 recheck 不得重新运行 Phase 2。

## 工作流

1. 验证 source path 和必需 runtime，完整读取三份共享 contract，并按 trace contract 初始化目录及 `trace/manifest.json` skeleton。
2. 按“恢复规则”检查现有 evidence，确定第一个必须执行的 Phase。
3. 完整读取当前 Phase reference，并要求 Phase worker 直接读取 `references/cross-phase-contract.md` 和该 Phase reference。进入 Phase 2 时，main agent 先按其 reference 创建 work queue，再按 queue 调度 extraction。
4. 使用 Agent 拓扑约束构造 prompt，启动对应 writer 并等待完成；Phase 2 依次完成全部 extraction writer 和独立 index/report writer。不得因耗时或 partial output 重复启动、替换或中断 worker。
5. writer 返回后，只按当前 Phase reference 检查必需 interface output、report 和 blocker；main agent 不得自行补写或重做 Phase 内容。
6. 根据当前 JSON trace digest 刷新 manifest，按 trace contract 运行当前 Phase validator。
7. 完整执行 `references/reviewer-repair-loop.md`。若发生 repair，依次重新刷新 manifest、运行 validator 并启动 fresh independent reviewer，直至 pass 或 block。
8. validator 和 reviewer 均通过后，再次刷新 manifest，使 canonical Phase status/decision 和 artifact digest 与 Phase trace 一致。
9. 按“Phase 状态机”推进：正常进入下一 Phase，`needs-coverage-recheck` 回到 Phase 3，`blocked` 停止并报告。
10. Phase 5 达到 `accepted` 或 `adjusted` 后，进入“完成与 handoff”；不得从普通 Phase pass 直接启动 `openspec-propose`。

## 恢复规则

1. 读取现有 manifest、Phase trace、artifact digest、validator result 和 reviewer evidence，从 Phase 1 起寻找第一个未完成或失效的 Phase。
2. Phase 只有同时满足以下条件才可跳过：canonical trace status/decision 正确；manifest status 与 trace 一致且 digest 当前有效；Phase validator 通过；存在由不同身份完成且明确 pass 的 independent reviewer report；所有 finding 已 repair 或记录 accepted non-blocking warning。
3. 仅存在根 `change-plan.md` 不代表 Phase 1 完成。若缺少有效 Phase 1 evidence，运行 fresh Phase 1，并把用户提供的现有计划作为 candidate input。
4. 缺少有效 writer output 或 Phase trace 时运行 fresh Phase writer；已有完整 writer output 但存在 validator/reviewer finding 时进入 repair loop。最早失效 Phase 之后的 output 均视为 stale，不得用于跳过后续 Phase。
5. source document 集合或 digest 变化使 Phase 1 及其下游失效；Phase 2 frozen evidence 仅在其 source digest、canonical owner 或必需 output 本身失效时重建。

## 完成与 handoff

- Phase 5 为 `accepted` 或 `adjusted` 后，按 trace contract 执行 all-phase complete validation，再运行 fresh independent final integration reviewer。
- final integration reviewer 必须核对 global atom index、source-window index、atom-plan mapping、final Change packet、Capability view、根 `change-plan.md` 和 human plan 的一致性。
- 只有 complete validator 和 final integration reviewer 都通过，且 final Change packet 已存在时，才允许从 packet 启动 `openspec-propose`。
- 任一 Phase 返回 `blocked` 时停止工作流，报告 blocker、已验证 evidence 和恢复所需的最小用户决定；main agent 不得越权补做 Phase 内容。
