---
name: source-aligned-change-plan-coverage
description: 当用户明确要求从指定 source document 出发，在 openspec-propose 之前建立具备 evidence occurrence 覆盖、source trace、mapping ambiguity 和最终 plan refit 的 OpenSpec Change/Capability 全局计划时使用；确保每个 extracted evidence occurrence 拥有独立 GA 并映射到 final Change/Capability framework。
---

# source-aligned-change-plan-coverage：五阶段编排协议

先从完整 source document 建立 Capability-first initial Change/Capability framework，再完成 source-first extraction、coverage closure，并以 GA 为键记录实际存在的 mapping ambiguity，随后确定性汇总冻结原文，并用与 Phase 1 相同的 framework 标准完成最小 plan refit。本技能不执行 semantic duplicate 识别或去重。

本工作流遵循 `Capability-first、Outcome-sliced、Obligation-later`：Phase 1 建立 initial framework；Phase 2/3 形成完整 evidence occurrence 与 coverage closure；Phase 4 直接重排冻结 `source-fact`；Phase 5 复审 initial framework、裁决全部 mapping ambiguity、完成 baseline reconciliation 和 final mapping。

## 输入与执行授权

- 必需：source document 根目录或精确 source document path。
- 可选：作为 Phase 1 candidate input 的现有 Change 计划。
- 所有 workflow artifact 写入 `openspec/orchestrate/`；具体布局由 Phase reference 和 trace contract 定义。
- 只有用户明确要求使用本技能处理指定 source document 时，才启动五阶段工作流。解释、审阅或修改本技能本身不构成执行授权。
- 用户明确要求执行本技能后，视为已授权启动必需的 Phase worker、Phase 1 bounded reviewer/repair worker 和一次 final integration reviewer；不得为 Phase 2–5 启动独立 reviewer 或 repair-writer。

## Reference 路由

共享 contract：

- `references/cross-phase-contract.md`：所有 Phase worker、Phase 1 reviewer/repair 和 final integration reviewer 必须直接加载的跨 Phase 语义。
- `references/change-capability-framework-principles.md`：Phase 1 和 Phase 5 必须直接加载的唯一 Change/Capability 标准。
- `references/trace-sidecar-contract.md`：Phase-specific authority、manifest、renderer、validator、checkpoint 和 schema。
- `references/review-gates.md`：Phase 1 bounded review/repair 与 workflow terminal integration gate。

每个 Phase 使用下表中的唯一任务 contract：

| Phase | Reference |
| --- | --- |
| Phase 1 | `references/phase-1-initial-change-plan.md` |
| Phase 2 | `references/phase-2-source-anchor-coverage.md` |
| Phase 3 | `references/phase-3-coverage-review-iteration.md` |
| Phase 4 | `references/phase-4-frozen-evidence-collections.md` |
| Phase 5 | `references/phase-5-targeted-plan-adjustment.md` |

## Agent 拓扑

- main agent 只负责编排和 interface gate，包括初始化、调度、Phase 2 work queue、manifest/validator、checkpoint 和状态转换。不得代写 Phase 内容或代替 Phase 1 repair-writer。
- Phase 1、Phase 3、Phase 5 各由 fresh independent semantic writer 完成；Phase 4 由确定性 assembler 生成。
- Phase 2 按 source document 或 coherent batch 启动一个或多个 fresh extraction writer；每份 source document 恰好一个 canonical extraction owner。全部完成后，再启动 fresh independent index/report writer。不得按 planned Change 分配 extraction。
- 只有 Phase 1 存在 independent reviewer/repair：initial review 后最多两轮 repair，每轮 repair 后使用 fresh independent reviewer；第二轮 repair 后仍不通过即 `blocked`。
- Phase 2–5 不启动 independent Phase reviewer 或 repair-writer。validator 只能 `pass` 或使当前 Phase `blocked`；失败后不得自动重启 producer、重复当前 Phase 或就地修正。唯一例外是 Phase 5 合法启动的一次 targeted evidence patch 状态机。
- final integration reviewer 是一次性 workflow-level 只读 gate，不属于 Phase 5 reviewer；失败直接阻止 handoff，不启动 repair loop。
- 所有 worker 都是单层 leaf worker，不得启动 nested subagent、`codex exec`、multi-agent worker 或其他 agentic child process，也不得自行进入另一 Phase。
- main agent 必须要求每个 worker 直接完整读取 `references/cross-phase-contract.md` 和对应 Phase reference；Phase 1/5 worker、Phase 1 reviewer/repair 还必须读取共享 framework 原则。final integration reviewer 必须读取 cross-phase contract、共享原则及 Phase 3–5 reference。

## Phase 状态机

| Phase | 内容责任 | Canonical status / decision | 下一步 |
| --- | --- | --- | --- |
| Phase 1 | 完整阅读 source，先形成 candidate Capability topology，再形成 outcome-sliced Change roadmap；不提取 obligation | `initial-plan-written` | Phase 2 |
| Phase 1 | initial plan/review gate建立前source无法完整读取 | 非canonical orchestration stop | 停止并报告，不伪造canonical trace |
| Phase 1 | 已有可校验initial plan后共享gate无法满足或两轮repair后仍不通过 | `blocked` | 停止并报告 |
| Phase 2 | source-first atom extraction 与独立 aggregation；`trace.mode: initial` | `source-atoms-written` | Phase 3 |
| Phase 2 | 消费唯一 evidence patch request，只执行 `replace-quote`、`adjust-range`、`split` 或 `add`；`trace.mode: targeted-patch` | `source-atoms-written` | Phase 3 incremental reconcile |
| Phase 2 | extraction/patch或validator无法在当前授权边界内完成 | `blocked` | 停止并报告，不重跑 |
| Phase 3 | 机械 complement、遗漏补提取、逐 occurrence GA index，以及以GA为键记录实际存在的mapping ambiguity | `coverage-complete` | Phase 4 |
| Phase 3 | source/artifact/range 无法可信验证 | `blocked` | 停止并报告 |
| Phase 4 | 确定性 assembler 按 initial Change/Capability 和 unassigned/gap 生成冻结原文及派生 index | `assembled` | Phase 5 |
| Phase 4 | resolver 或确定性重算无法建立可信结果 | `blocked` | 停止并报告 |
| Phase 5 | 使用共享标准最小 refit、裁决 mapping ambiguity 并完成 final mapping | `accepted` 或 `adjusted` | complete validation 与 handoff |
| Phase 5 | 发现可定位的 evidence integrity defect，并已冻结 checkpoint | `needs-targeted-evidence-patch` | 唯一增量回补链 |
| Phase 5 | 需要用户决定、patch scope 无法有界、checkpoint 失效或增量影响闭包无法稳定 | `blocked` | 停止并报告 |

## 唯一增量回补链

每个 generation 最多执行一次：

```text
Phase 5 checkpoint
-> Phase 2 targeted evidence patch
-> Phase 3 incremental reconcile
-> Phase 4 deterministic refresh
-> Phase 5 checkpoint resume
```

- Phase 5 只有在首次执行中尚未发布canonical Phase 5 trace、Phase 2–4均为initial success snapshot，且能给出具体 source document、source atom或coverage disposition origin、line range及其row/source/window digest witness时，才可生成唯一 `source-aligned-evidence-patch-request-v1` 并返回 `needs-targeted-evidence-patch`。任何accepted、adjusted、blocked、closed或incremental状态均不得回退为requested。
- Phase 5的mapping/refit不得重读source；仅在已有seed locator后允许对witness预先固定的window做一次只读defect核验。window必须落在immutable locator row ranges的连续闭包内。禁止全文扫描、搜索式发现或扩窗；source/base gate漂移、非原文Phase 2 base、需要二次读取或locator不足时直接`blocked`。`quote-mismatch`只允许原文substring选择错误或截断，不得借request洗白非法base。
- patch 只修复 `quote-mismatch`、`range-mismatch`、`mixed-independent-occurrences` 或 `missing-occurrence`，且只允许 `replace-quote`、`adjust-range`、`split` 或 `add`。禁止删除、合并或重命名 occurrence。candidate mapping、unassigned/gap、final owner/relation/projection/Capability impact 和 framework boundary 不属于 evidence patch，必须由 Phase 5 裁决。
- Phase 5必须检查全部GA，而不只检查Phase 3 ambiguity rows；late-discovered mapping ambiguity直接在terminal mapping裁决，不回写Phase 3。只有确认且可定位的evidence integrity defect可以进入patch链。
- Phase 2 只得修改 patch request 列出的 occurrence 及必要最小局部上下文；不得全量重提取。Phase 3 保留未受影响 GA 和 mapping ambiguity identity，只更新受影响 evidence；Phase 4 只做确定性派生刷新。
- Phase 5 只可在全局review/mapping完成后的`stage: mapping`冻结`source-aligned-phase-5-checkpoint-v1`；pending Capability、Change、mapping和unassigned/gap必须分别精确等于allowed scope中的initial Capability、initial Change、GA及scope GA与unassigned/gap GA的交集。initial review scope非空时必须由target的Phase 4 initial bucket发起，并恰好等于所选root经initial与provisional dependency/overlay拓扑形成的最小连通闭包；为空时仍可由pending GA/unassigned review产生全新final ID，但不得劫持既有provisional unit。provisional final ID通过冻结review/GA lineage反向投影到授权origin。恢复时只重算这些invalidated unit，跨scope overlay/dependency不得改变；不得从Phase 1重新执行全量refit。
- 若需要第二次 patch、相同 finding 在 authority digest 未变化时重现、patch target 无法有界或影响闭包扩张为全 framework，必须 `blocked`。
- 增量链任一Phase失败时不得留下`requested`历史或重跑该Phase：失败Phase trace保留request/checkpoint引用、base digest和已知affected closure；main agent只调用`phase5_plan_refit.py --abort-patch-chain --issue ...`执行机械control transform。该transform保持request/checkpoint和semantic rows不变，只修改refit `status`、`issues[]`及唯一history row的`status`，并发布`execution-mode: checkpoint-resume`的Phase 5 `blocked` trace；它不是semantic writer。abort校验只验证immutable snapshot内部自洽，不依赖已失败/已清理的增量surface，也不把current Phase 1/principles重新与冻结fingerprint比较；fingerprint drift本身可以是blocked原因。

## 工作流

1. 验证 source path，完整读取共享 contract，并按 trace contract 初始化目录及 `trace/manifest.json` skeleton。
2. 按“恢复规则”检查现有 evidence，确定第一个必须执行的 Phase。
3. 完整读取当前 Phase reference，并构造符合 Agent 拓扑的 worker prompt。进入 Phase 2 时，main agent 先建立 work queue，再按 queue 调度 extraction。
4. Phase 1 writer 发布可校验plan/trace后，main agent运行validator并把结果交给bounded review；reviewer同时检查validator finding与共享gate。initial review后最多两轮定向repair，每轮后重新运行validator。只有最后一次validator与review均通过才进入Phase 2；重复finding、no-op或超限立即`blocked`。
5. Phase 2–5 writer/assembler 返回后，main agent 检查必需 interface output、report 和 blocker，刷新 manifest、运行 renderer 与当前 Phase validator；不得启动 Phase reviewer 或 repair-writer。
6. validator 通过后刷新 manifest，使 canonical Phase status/decision 和 artifact digest 与 trace 一致，再按状态机推进。validator失败则记录issue并`blocked`；不得自动重启producer、修正后重验或重复当前Phase。
7. Phase 5 返回 `needs-targeted-evidence-patch` 时，验证 checkpoint 与唯一 patch request 后严格执行增量回补链；不得重启整个 Phase 2 extraction、Phase 3 全量编号或 Phase 5 全量 refit。
8. Phase 5 达到 `accepted` 或 `adjusted` 后进入“完成与 handoff”；不得从普通 Phase pass 直接启动 `openspec-propose`。

## 恢复规则

1. 读取 manifest、Phase trace、artifact digest、validator result、Phase 1 review evidence，以及可选 checkpoint/patch request，从 Phase 1 起寻找第一个失效 interface。
2. Phase 1 只有 canonical status、manifest/digest、validator 与 bounded review evidence 全部有效才可跳过。Phase 2–5 只要求 canonical status/decision、manifest/digest、Phase-specific authority及派生物通过 validator；不得要求 Phase reviewer evidence。
3. Phase 1 只发布 `phase-works/phase-1/initial-change-plan.md`；根 `change-plan.md` 仅由 Phase 5 terminal 状态发布。缺少有效 Phase 1 evidence 时运行 fresh Phase 1，并把用户提供的现有计划作为 candidate input。
4. 缺少 Phase 2–5 writer output 或 trace 时运行对应 Phase producer；一旦 producer 已发布 output，validator issue 只能使当前 generation `blocked`，不得自动重启或重复 producer。最早失效 authority 之后的派生物视为 stale。
5. 若存在有效 `source-aligned-phase-5-checkpoint-v1` 和唯一 `source-aligned-evidence-patch-request-v1`，必须优先恢复增量回补链；未受影响 input fingerprint 有效的 checkpoint row 不得重算。
6. source set、共享 framework 原则或 initial plan digest 的全局变化使 checkpoint 失效；不得伪装成 targeted patch，必须 `blocked` 并报告重新 generation 所需授权。
7. 旧schema的进行中orchestration artifact不迁移、不原地升级；采用本版本后必须在新的workflow generation中从Phase 1开始，旧artifact只能作为只读candidate input或另行归档。

## 完成与 handoff

- Phase 5 为 `accepted` 或 `adjusted` 后，必须让 `phase-works/phase-5/change-plan.md` 与根 `change-plan.md` 完全一致，再执行 all-phase complete validation，并运行一次 fresh independent final integration reviewer。
- final integration reviewer 核对 global atom index、Phase 3 mapping ambiguity、作为唯一resolution的同GA terminal atom mapping、Phase 4 collection/index、framework refit、Capability baseline、final Change packet、Capability view、anchor index和根 `change-plan.md` 的一致性。
- final integration reviewer 必须确认每个 evidence occurrence 都有独立 GA 和独立 Phase 5 mapping，未受影响 GA 在增量链中保持 identity，且没有 semantic duplicate 处理或基于 GA 数量的 framework 推断。
- final integration reviewer 只读且只运行一次；未通过时 workflow `blocked`，不得自动 repair、重新 refit 或再次生成 evidence patch。
- 只有 complete validator 和 final integration reviewer 都通过，且 final Change packet 已存在时，才允许从 packet 启动 `openspec-propose`。
- handoff 必须声明：final packet 是未语义去重的完整 evidence mapping；后续规格生成可以综合多个 GA，但必须保留多对一 trace。
