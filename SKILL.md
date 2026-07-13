---
name: source-aligned-change-plan-coverage
description: 当用户希望先从 source document 出发，为 OpenSpec 制定具备 obligation atom 覆盖、source anchor 可追溯性、gap 分析和最终 plan refit 的 Change/Capability 计划时，在 openspec propose 之前使用本技能；确保每项具有生产意义且可执行的 obligation 都恰好归属于一个 Change，仅在适用时推进 spec Capability，否则显式完成 gap 分类。
---

# source-aligned-change-plan-coverage：来源对齐的 Change 计划覆盖

在创建任何单独的 `openspec-propose` Change 之前，先建立全局 source-aligned OpenSpec Change 计划。本技能将完整 source document 转换为规范化 obligation atom index，再从稳定的 atom 集合推导最终 Change/Capability 计划。obligation atom 是应延续到后续 `openspec-propose` artifact 中、由 source 支撑的最小生产 obligation。它可以表示页面状态、触发条件、显示规则、主操作、禁用操作、恢复路径、数据事实、auth/privacy 规则、失败路径、响应式行为、验证要求、架构/runtime 依赖、preserve 约束或显式 non-goal。contextual atom 是 Change 为避免错误设计而必须了解、但不会直接实现或计入当前 Capability advancement 的 source-backed 事实或未来 obligation。source anchor 和行范围是 atom 的 trace evidence，不是覆盖目标本身。

本工作流统一使用 `GA-####` 作为 canonical Global Atom ID 前缀。Phase 3 必须分配如 `GA-0001` 的规范化 global atom ID；Phase 4、Phase 5 以及后续 `openspec-propose` / `openspec-apply-change` 工作必须保留 `obligation-atom-index.md` 中完全相同的 `GA-####` ID，不得改写为其他 global 前缀或 source-local atom ID。

artifact projection 与 atom 是否存在及最终 Change ownership 相互独立。每个 atom 必须携带 artifact projection，说明下游 OpenSpec artifact 如何消费它：`spec-requirement` 表示规范性的用户/系统行为，`spec-guard` 表示 spec 不得意外违反的 preserve 或 forbidden-drift 约束，`design-obligation` 表示架构/runtime/data/API/module/provider/deployment 形态，`verification-obligation` 表示 proof/evidence 策略，`contextual-only` 表示 non-direct context。最终 direct atom 必须使用 `spec-requirement`、`spec-guard`、`design-obligation` 或 `verification-obligation`；`contextual-only` 只用于 non-direct context 行。Phase 2 可以记录 candidate projection，Phase 3 在 global atom index 中将其规范化，Phase 5 在 Change packet 中完成最终定案。不得仅因 atom 为 direct，就强制将其写成 spec requirement。

在整个工作流中遵循四项原则：capability-first discovery、loop-first Change slicing、Change-first atom ownership 和 spec-only Capability advancement。Change 是 direct atom 唯一的可执行 ownership 单元。Capability metadata 只描述是否创建或修改 spec boundary，不是第二个 owner。普通 `design-obligation` 和 `verification-obligation` atom 只归属 Change，使用 capability impact `none` 和 target capability `none`。可以在 `related-capabilities[]` 中保留 source 明确表达的 Capability 关联，但该列表只是非 ownership 的辅助 evidence，绝不产生 progression、Capability view 或 Capability complexity 计数。

capability-impact 字段使用 v2 contract。Phase 2 使用 `candidate-capability-impact`、`candidate-target-capability` 和 `candidate-related-capabilities[]`；Phase 3 使用 `capability-impact`、`target-capability` 和 `related-capabilities[]`；Phase 5 使用 `final-capability-impact`、`final-target-capability` 和 `related-capabilities[]`。Phase 2/3 的 impact 为 `new`、`modified`、`none` 或 `unresolved`；Phase 5 的 impact 为 `new`、`modified`、`none`，或仅供 foundation 使用的 `foundation-substrate`。`new` / `modified` 要求具体 target Capability，且只适用于 `spec-requirement` 或 `spec-guard`。`none` 要求 target 为 `none`。`unresolved` 必须附带 rationale，并在 Phase 5 返回 `accepted` 或 `adjusted` 前解决。related Capability array 默认为空，只包含 source window 明确支撑且已声明、互不重复的 Capability ID，排除 target Capability，并且不能替代必需的 target。

各 Phase 职责：

- Phase 1 从完整 source 阅读结果建立初始 Change/Capability framework。先识别持久的 spec Capability，再按用户/系统 loop 切分 Change，依据行为成熟度和工程依赖排序，并投影明确的 `New` / `Modified` spec delta。它只是 slicing hypothesis，不是最终 authority；不得创建 obligation atom、行范围 anchor、coverage status 或 Phase 2 work queue。
- Phase 2 执行 source-first atom extraction 和 Phase 2 aggregation。每份 source document 只有一个 canonical extraction owner；Phase 结束后，Phase 2 raw atom file 即成为不可变 evidence。
- Phase 3 将覆盖结果规范化到 global atom index，闭合 semantic gap、处理 duplicate、分配规范化 artifact projection，并完成覆盖或返回阻塞。
- Phase 4 根据 Phase 2/3 atom 行范围复制 source-window dossier 并编写 semantic profile。它可以识别 refit pressure，但不得决定最终 ownership 或生成 final packet。
- Phase 5 基于稳定的 global atom 和 Phase 4 source-window semantics 重整最终计划。它可以接受或调整 Phase 1 framework，但每项 refit decision 都必须保持 atom-level traceability。

最终计划必须满足以下 invariant：

- final Change 是供后续 `openspec-propose` 和 `openspec-apply-change` 使用的 implementation unit，而不只是概念性的产品 loop。closed-loop coherence 是必要条件，但还必须通过 Phase 5 的 implementation-ready complexity 规则。
- 每个可执行 direct atom 必须恰好有一个 final owner Change。仅根据 `final-capability-impact` 为 `new` 或 `modified` 的 final direct spec atom 重新计算 Capability progression；Change ownership 本身不代表 Capability advancement。仅 dependency、preserve、upstream-baseline、downstream-constraint、contextual、evidence、design、verification 或 non-goal 的引用不得计入 Capability advancement。
- non-direct atom 仍必须进入下游工作。除非 atom 没有 final owner Change 且属于全局 contextual/non-coverage，否则任何被归类为 dependency、contextual、evidence-burden、preserve/reference、later-change、显式 non-goal 或其他 non-direct relation 的 atom，都必须以显式 `GA-####` 行保留在所属 final Change packet 的 context/evidence/dependency/non-goal 处理中。不得丢失、截断 non-direct 行，不得仅在 `atom-plan-mapping.md` 中表示，也不得折叠成 `additional-context` 等汇总行。
- Phase 1 可以包含一个 zero-domain foundation candidate，辅助 slicing 和 grounding。Phase 5 最多生成一个可执行 foundation Change；它必须位于 roadmap 首位，其 direct atom 必须使用 `final-capability-impact: foundation-substrate` 和 `final-target-capability: runtime-substrate-foundation`。它拥有专用 foundation Capability view，但不得吸收 domain behavior，也不得计入 business Capability 的 `New` / `Modified` progression。
- 后续 `openspec-propose` 和 `openspec-apply-change` 必须消费 final Change packet，而不是孤立的 source atom 行。较早的 Change 为较晚 Change 提供已实现的 baseline contract，但不得吸收所有未来 global obligation。
- business Capability view 只用于 spec advancement。它必须且只能包含对应 Change/target-Capability 组合中，`final-capability-impact` 为 `new` 或 `modified` 的 direct `spec-requirement` / `spec-guard` 行。仅归属 Change 的 design/verification 行以及所有 non-direct 行继续保留在 final Change packet 和完整 `atom-plan-mapping.md` 中。唯一例外是面向 `foundation-substrate` 行的专用 `runtime-substrate-foundation` view。

## Artifact 语言门禁

本工作流写入 `openspec/orchestrate/**` 的所有 artifact 都必须便于中文 reviewer 阅读。

- 固定 artifact 结构可以保留英文：heading、table header、field label、trace field name、enum/status value、ID、path、command、code/API/DB/package symbol、filename、module/function/type name、Capability ID、Change slug，以及 source document 中的精确术语或引用。
- 上述豁免不适用于 agent 编写的解释性内容。sentence、table cell explanation、reason、judgment、rationale、note、proof/evidence description、risk description、split analysis、handoff explanation 和 report summary 必须使用简体中文。
- 本技能或各 Phase reference 中的英文说明不属于固定 artifact 结构。不得把其中的英文 bullet 或 prose 原样复制为 agent 编写内容；必须翻译或改写为面向中文 reviewer 的内容。
- 技术英文可以作为 identifier 或 noun phrase 保留，但周围的语义句必须为中文。例如，`browser-e2e` 可以作为 evidence type；evidence explanation 必须用中文说明为何需要该 proof。
- `Source Phrase` 值和精确引用可以保留 source 原文。`Source Fact`、`Rationale`、`Propose Use`、`Review Judgment` 等解释字段必须使用中文，除非整个值只包含固定 enum、ID、path、command 或 source 中的精确术语。
- 每次写入或修改 artifact 后，writer agent 必须执行 language self-check：暂时忽略反引号内的 ID/path/command/code 和固定 enum/status value；任何剩余的英文主导自然语言句都不通过此 gate，必须在该 Phase 结束前改写。

## 必需输入

- source document 根目录或精确 source document path。
- 可选的、需要继续完善的现有 Change 计划。

所有 workflow artifact 都放在 `openspec/orchestrate/` 下。

## 输出布局

保持根目录精简并面向 proposal。根目录只放最新有效计划和最终 atom/Change packet；`trace/` 保存用于 validation/debugging 的 canonical JSON sidecar；`phase-works/` 保存面向 reviewer 的 Phase 工作结果。后续 `openspec-propose` 通常读取 `change-plan.md` 和相关 `change-capability-anchors/` packet，仅在需要 trace evidence 时继续查看 `trace/` 或 `phase-works/` 链接。所有 Phase 工作文档、report、review、raw extraction ledger 和 intermediate manifest 都放在 `phase-works/` 下，每个 Phase 使用一个子目录。

```text
openspec/orchestrate/
├── change-plan.md                         # openspec-propose 使用的最新有效计划
├── trace/
│   ├── manifest.json                       # canonical trace manifest 与 digest；初始化时创建 skeleton，每次 validator 运行前刷新
│   ├── phase-1.trace.json
│   ├── phase-2.trace.json
│   ├── phase-3.trace.json
│   ├── phase-4.trace.json
│   └── phase-5.trace.json
├── change-capability-anchors/
│   ├── index.md                           # final Change packet index
│   ├── obligation-atom-index.md            # 规范化 global atom registry
│   ├── obligation-atom-index.json          # canonical global atom trace sidecar
│   └── <change-slug>/
│       ├── <change-slug>.md                # 从 global atom 推导的 final Change packet
│       └── capability-anchors/
│           └── <capability-slug>.md        # spec-advancement view 或专用 foundation view
└── phase-works/
    ├── phase-1/
    │   ├── change-plan.md                  # Phase 1 snapshot；根 change-plan.md 是提升后的最新副本
    │   ├── source-doc-manifest.md
    │   └── phase-1-agent-report.md
    ├── phase-2/
    │   ├── source-obligation-atoms/
    │   │   ├── index.md                    # Phase 2 index/report subagent summary
    │   │   ├── work-queue.md               # 轻量 batching plan，不是 coverage evidence
    │   │   ├── <source-relative-path>.atoms.md
    │   │   └── <source-relative-path>.atoms.json
    │   └── phase-2-agent-report.md
    ├── phase-3/
    │   ├── source-doc-manifest.md          # 增强后的 Phase 3 review 副本
    │   ├── source-doc-coverage/
    │   │   └── <source-relative-path>.coverage.md
    │   ├── phase-3-trace/
    │   │   ├── source-to-global-atom-map.md
    │   │   ├── source-to-global-atom-map.json
    │   │   ├── source-remainder-review.md
    │   │   ├── source-remainder-review.json
    │   │   ├── duplicate-ownership-review.md
    │   │   └── atom-normalization-decision-log.md
    │   ├── coverage-review.md
    │   └── phase-3-agent-report.md
    ├── phase-4/
    │   ├── input-change-plan.md
    │   ├── source-window-dossiers/
    │   │   ├── index.md                   # 供人工 review 和 refit grounding 使用的 source-window dossier index
    │   │   ├── source-window-index.json   # canonical source-window trace sidecar
    │   │   ├── by-input-change/
    │   │   │   └── <input-change-slug>.md # 按初始 Change 分组的原始 source window
    │   │   └── by-input-capability/
    │   │       └── <input-capability-slug>.md # 按初始 Capability 分组的原始 source window
    │   ├── source-window-semantic-profile-review.md
    │   ├── source-window-grounding-issues.md
    │   └── phase-4-agent-report.md
    └── phase-5/
        ├── source-window-refit-trace.md
        ├── phase-5-agent-report.md
        ├── change-plan-adjustments.md      # 仅在 Phase 5 adjusted、需要 recheck 或 blocked 时存在
        ├── input-change-plan.md            # 仅 accepted/adjusted
        ├── change-plan.md                  # 仅 accepted/adjusted；随后提升到根目录
        ├── atom-plan-mapping.md            # 仅 accepted/adjusted
        ├── atom-plan-mapping.json          # 仅 accepted/adjusted
        ├── final-packet-index.json         # 仅 accepted/adjusted；可执行计划 Change，若有 foundation 则排在首位
        ├── capability-progression-review.md # 仅 accepted/adjusted
        ├── change-complexity-review.md     # 仅 accepted/adjusted
        ├── plan-refit-decision-log.md      # 仅 accepted/adjusted
        ├── change-capability-human-plan.md # 仅 accepted/adjusted；供人工阅读，不是 source of truth
        └── alignment-final-report.md       # 仅 accepted/adjusted
```

在 `phase-works/phase-2/source-obligation-atoms/` 和 `phase-works/phase-3/source-doc-coverage/` 下使用单层 filename：根据 source document path 生成名称，移除 extension，将 path separator 替换为 `--`，再添加 `.atoms.md` 与 `.atoms.json`，或添加 `.coverage.md`。

不得创建 `pass-*`、`iteration-*` 或类似编号的 Phase 4/Phase 5 子目录。Phase 4 直接在 `phase-works/phase-4/` 中写入一份当前 source-window grounding packet；Phase 5 直接在 `phase-works/phase-5/` 中写入一份当前 refit packet。如果 Phase 4 或 Phase 5 返回 `needs-coverage-recheck`，新一轮 Phase 3、Phase 4 和 Phase 5 必须更新当前 Phase 工作目录；仅在用户明确要求时引入 archive history。

每个完成的 Phase 还必须在自身目录中保存独立 reviewer/repair-loop evidence：

- `phase-works/phase-<n>/phase-<n>-reviewer-report.md`：进入下一 Phase 前，每个 Phase 都必须具备此文件。每次 reviewer 运行都要追加或保留一条记录，其中包括 reviewer subagent identity、validator input status、已执行的 read-only check、finding、accepted warning 以及 pass/block decision。
- `phase-works/phase-<n>/phase-<n>-repair-report.md`：reviewer finding 或 validator warning/error 导致任何 artifact 被修改时必须存在。每次 repair 都要记录 repair subagent identity、消费的 reviewer finding、修改文件、保留的 invariant 和剩余 blocker。如果不需要 repair，不得创建虚假 repair report；应在 reviewer report 和 Phase trace 中记录 `repair-not-needed`。

可选 bundled helper：

```text
.codex/skills/source-aligned-change-plan-coverage/scripts/
├── source_aligned_trace_lib.py # 共享 trace/parser/digest/issue helper
├── validate_source_aligned_orchestrate.py # canonical trace validator
├── phase3_line_range_audit.py   # Phase 3 candidate uncovered/overlap mechanical helper
├── phase5_plan_refit.py         # 根据 reviewed mapping 与 JSON config 运行的 Phase 5 mechanical renderer/checker
└── render_source_aligned_orchestrate.py # 从 canonical JSON sidecar 生成确定性 Markdown mirror
```

## Artifact 权威性

- JSON trace sidecar 是 canonical validator input。Markdown mirror artifact 是从 JSON 确定性渲染得到、面向 reviewer/proposal 的内容表面；不得通过手工编辑它们来修复 drift。
- 修复 renderer-backed mirror 时，必须更新 canonical JSON sidecar，或重新运行 `scripts/render_source_aligned_orchestrate.py --write`。不得仅手工修改 Markdown 来修复 `rendered-markdown-drift` validator failure。
- Phase 2 source atom JSON sidecar 在 Phase 2 完成后成为不可变 raw extraction evidence；相应 `.atoms.md` 是这些 JSON sidecar 的 renderer mirror。
- Phase 3 的 `change-capability-anchors/obligation-atom-index.json` 是规范化 global uniqueness、candidate Change ownership、capability-impact 和 source-explicit related-capability registry 的 canonical source；`change-capability-anchors/obligation-atom-index.md` 是它的 renderer mirror。
- `phase-works/phase-4/source-window-dossiers/` 是复制得到的 source-window review evidence，不是新的 extraction pass，也不能替代 source of truth。
- Phase 5 根据 global index 和 Phase 4 source-window semantic profile 推导 final Change packet 与 Capability view；不得在没有 source evidence 的情况下发明 atom。
- final Change packet 是 direct scope 和 non-direct constraint 面向 proposal 的 source of truth。如果 non-direct atom 在 canonical `atom-plan-mapping.json` 或其 `atom-plan-mapping.md` mirror 中具有 final owner Change，对应 final Change packet 必须在 context/dependency/evidence/preserve/non-goal 表中按 `GA-####` 显式列出该 atom；packet 可以拆成多个 relation-specific table，但不得用 count、summary 或只含链接的 placeholder 替代显式 atom 行。
- final Capability view 是派生的 spec-advancement view，不是完整 implementation packet。后续 `openspec-propose` 不得单独使用 Capability view 判定 scope，因为其中刻意排除了仅归属 Change 的 design/verification atom 和 non-direct constraint。
- `phase-works/phase-5/change-capability-human-plan.md` 是面向人工的 synthesis，不能替代 source-window dossier、source atom ledger、global atom index 或 final Change packet。

## Reference 文件

进入工作流前始终读取以下两个 reference：

- trace sidecar contract：`references/trace-sidecar-contract.md`
- reviewer/repair loop：`references/reviewer-repair-loop.md`

仅在进入对应 Phase 时读取以下 reference：

- Phase 1 初始计划：`references/phase-1-initial-change-plan.md`
- Phase 2 source-first atom 提取：`references/phase-2-source-anchor-coverage.md`
- Phase 3 覆盖规范化：`references/phase-3-coverage-review-iteration.md`
- Phase 4 source-window grounding：`references/phase-4-source-window-grounding.md`
- Phase 5 plan refit：`references/phase-5-targeted-plan-adjustment.md`

## Subagent 规则

本工作流基于 subagent。

- subagent topology 为单层。只有 main orchestrating agent 可以启动 Phase subagent。为 Phase 1、Phase 2 extraction、Phase 2 index/report、Phase 3、Phase 4 或 Phase 5 启动的 subagent 都是 leaf worker：必须直接完成分配的 Phase 工作，不得再启动、调用或委派给任何 AI subagent、`codex exec`、multi-agent worker、nested workflow agent，也不得创建以 agentic reasoning 为目的的 child process。
- 每个 Phase subagent 都必须使用 `model=GPT-5.5` 和 `reasoningEffort=xhigh`。这是不可降低的硬性 runtime constraint，不得因速度、成本、默认值、可用性、模型偏好或任务规模而降级。如果当前 runtime 无法创建 `GPT-5.5` / `xhigh` Phase subagent，停止工作流并报告 blocker，不得改用更低模型。
- 本技能或 Phase reference 中要求启动 fresh subagent 的指令只面向 main orchestrating agent。Phase subagent 读取这些指令时，必须将其视为 boundary context，而不是启动其他 subagent 或自行推进工作流的权限。
- reviewer 和 repair 必须由独立 subagent 担任。writer subagent 的 self-check、final answer、trace field 或 report text 都不能代替 reviewer step；validator 成功也不能代替 reviewer step。
- 每个 Phase writer 完成且 main agent 运行 Phase validator 后，main agent 必须以 `model=GPT-5.5` 和 `reasoningEffort=xhigh` 启动 fresh independent reviewer subagent。reviewer subagent 对所有受审 artifact 只读，只能写入 Phase reviewer report；不得编辑 Phase artifact、执行 repair、启动 nested subagent 或推进工作流。
- 如果 validator 或 independent reviewer 发现需要修改 artifact 的问题，main agent 必须以 `model=GPT-5.5` 和 `reasoningEffort=xhigh` 启动 fresh independent repair-writer subagent。repair subagent 必须不同于 Phase writer 和所有 reviewer subagent；只能修改该 Phase 允许的 artifact 以及 Phase repair report，不得启动 nested subagent 或推进工作流。
- 每次 repair 后，main agent 必须重新运行 validator，再启动另一个 fresh independent reviewer subagent。只有最新 validator 不含 blocking error，且最新 independent reviewer report 明确通过该 Phase，或给出带 rationale 的 accepted non-blocking warning，才能推进 Phase。
- main agent 必须等待每个已启动的 Phase subagent 完成；不得因耗时或暂未出现 partial file 而中断、关闭、替换或重复启动。
- Phase 1：使用 fresh independent subagent，根据完整 source 生成初始 Change/Capability framework。
- Phase 2：先建立轻量 work queue，再按 source document 或 source-document batch 划分 fresh source-extraction subagent。每份 source document 必须只有一个 canonical Phase 2 extraction owner。完成 extraction 后，使用 fresh Phase 2 index/report subagent。遵循 `references/phase-2-source-anchor-coverage.md` 中的详细 batching 和 aggregation boundary；不得为每个 planned Change 启动一个 Phase 2 subagent，也不得让多个 subagent 独立提取同一 source document，除非 Phase 3 明确要求 targeted validation。
- Phase 3：使用 fresh independent subagent 完成 source coverage normalization、gap audit、duplicate review 和 global atom index generation。
- Phase 4：使用 fresh independent subagent 完成 source-window dossier generation、input Change/Capability semantic profiling、grounding issue review 和 Phase 5 handoff preparation。
- Phase 5：使用 fresh independent subagent 完成 source-window-grounded、atom-driven 的 Change/Capability plan refit、Capability progression review、Change complexity review、executable foundation gating 和 executable planned final packet generation。
- 每个 writer、reviewer 和 repair subagent prompt 都必须包含 Artifact Language Gate 或明确要求遵循它；必须包含不可降级的 runtime 要求 `model=GPT-5.5` 和 `reasoningEffort=xhigh`；还必须明确 subagent 是 leaf worker，不得启动 nested subagent 或进入另一 Phase。如果 Phase reference 使用英文 table header 或 field label，subagent 可以保留该结构，但 explanation content 必须填写为简体中文。

如果 Phase 4 返回 `needs-coverage-recheck`，启动 fresh Phase 3 subagent，再启动 fresh Phase 4 subagent。如果 Phase 5 返回 `needs-coverage-recheck`，依次启动 fresh Phase 3、Phase 4 和 Phase 5 subagent。除非 Phase 3、Phase 4 或 Phase 5 报告 targeted review 不足且用户明确要求完整 source extraction rerun，否则不得重新运行 Phase 2。

显式使用本技能即授权执行其必需的 subagent 工作流，不要仅为了启动 Phase subagent 再次请求确认。如果 runtime 无法使用 subagent 或明确禁止使用，停止并报告 blocker，不得由 main agent 代做该 Phase。

main agent 只负责 orchestrate、检查 interface-level output 并启动下一 Phase。不得静默重做某个 Phase 的内容工作；Phase 2 index/report subagent 可用时，也不得自行合成 Phase 2 aggregate index/report。

## 工作流

1. 创建 `openspec/orchestrate/`、`trace/`、`change-capability-anchors/`、`phase-works/phase-1/`、`phase-works/phase-2/source-obligation-atoms/`、`phase-works/phase-3/source-doc-coverage/`、`phase-works/phase-3/phase-3-trace/`、`phase-works/phase-4/source-window-dossiers/by-input-change/`、`phase-works/phase-4/source-window-dossiers/by-input-capability/` 和 `phase-works/phase-5/`。同时创建或刷新 `trace/manifest.json`，将其作为 canonical trace manifest skeleton，尚无 trace sidecar 的 Phase 使用 `missing`。
2. Phase 1：如果当前没有 `change-plan.md`，启动 fresh writer subagent，枚举并完整阅读所有 source document，写入 `phase-works/phase-1/source-doc-manifest.md`、`phase-works/phase-1/change-plan.md` 和 `trace/phase-1.trace.json`，将最新有效计划提升到根 `change-plan.md`；先识别持久 spec Capability，再使用 Phase 1 reference 切分并排序 loop-based Change，从而生成初始 framework。随后 main agent 刷新 `trace/manifest.json`、运行 validator、启动 independent Phase 1 reviewer subagent；若必须修改 artifact，则启动 independent repair subagent；再次刷新 manifest 并运行 validator，然后在进入 Phase 2 前再启动 fresh independent reviewer。
3. Phase 2：建立轻量 work queue，按 source document 或 source-document batch 启动 source-extraction writer subagent，为每份 `read-full` source document 写入一个 canonical `<source>.atoms.json`，从 JSON 渲染对应 `<source>.atoms.md` mirror，再运行 fresh Phase 2 index/report writer subagent 并写入 `trace/phase-2.trace.json`。随后 main agent 刷新 `trace/manifest.json`、运行 validator、启动 independent Phase 2 reviewer subagent；如果必须修改 artifact，则启动 independent repair subagent；修复后再次刷新 manifest、运行 validator 并启动 fresh independent reviewer。通过后冻结 raw `.atoms.json` evidence 及其 rendered mirror。
4. Phase 3：启动 fresh writer subagent，将 Phase 2 atom 规范化到 canonical `change-capability-anchors/obligation-atom-index.json`；审计 source remainder、向 global index 添加精确的 missing atom、拆分过宽 atom、解决 duplicate/ambiguous ownership、分配规范化 artifact projection；在 `phase-works/phase-3/` 下写入所有 per-source coverage file 和 Phase 3 trace file；写入 `phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json`，以及包含 mechanical uncovered source range 和 semantic review row 的 canonical `phase-works/phase-3/phase-3-trace/source-remainder-review.json`；渲染 JSON-backed Markdown mirror 并写入 `trace/phase-3.trace.json`。随后 main agent 刷新 `trace/manifest.json`、运行 validator、启动 independent Phase 3 reviewer subagent；如需修改，启动 independent repair subagent；修复后再次刷新 manifest、运行 validator、启动 fresh independent reviewer，并作出以下决定：
   - `coverage-complete`：每项具有生产意义的 source obligation 都由唯一 direct global atom 表示，或具有合理的 non-direct/non-coverage status。
   - `blocked`：source document、atom evidence、ownership boundary 或 conflict 不足以形成稳定 global atom index。
5. Phase 4：在 `coverage-complete` 后，启动 fresh writer subagent，根据稳定 global atom index 和原始 source document 生成 source-window dossier 与 semantic profile。按 Phase 2/3 atom 引用的原始 source window，为每个 input Change 和 input Capability 写入 `phase-works/phase-4/source-window-dossiers/`，然后写入 `source-window-index.json`、`source-window-semantic-profile-review.md`、`source-window-grounding-issues.md`、`phase-4-agent-report.md` 和 `trace/phase-4.trace.json`。随后 main agent 刷新 `trace/manifest.json`、运行 validator、启动 independent Phase 4 reviewer subagent；如需修改，启动 independent repair subagent；修复后再次刷新 manifest、运行 validator、启动 fresh independent reviewer，并以以下状态结束：
   - `grounded`：source-window dossier 和 semantic profile 足以进入 Phase 5。
   - `needs-coverage-recheck`：grounding 暴露出 missing/broad/conflicting source obligation，需要 fresh Phase 3 pass。
   - `blocked`：source document、source boundary 或 product decision 不足以安全 grounding。
6. Phase 5：Phase 4 返回 `grounded` 后，启动 fresh writer subagent，根据稳定 global atom index 和 Phase 4 source-window semantic profile 重整 Change/Capability 计划。为每个 direct atom 最终确定 Change ownership、artifact projection、capability impact/target 和 source-explicit related Capability；直接在当前 `phase-works/phase-5/` 中写入 refit packet，不创建 pass/iteration 子目录；符合条件时最多生成一个 foundation candidate，作为第一个 executable foundation Change；状态为 `accepted` 或 `adjusted` 时写入 terminal mapping 和 executable planned final packet artifact；始终写入 `trace/phase-5.trace.json`。必要时更新根目录最新有效 `change-plan.md`，为 accepted/adjusted handoff 派生 final `change-capability-anchors/<change-slug>/` packet，并将每个 owner-scoped non-direct atom 显式带入相关 final Change packet。随后 main agent 刷新 `trace/manifest.json`、运行 validator、启动 independent Phase 5 reviewer subagent；如需修改，启动 independent repair subagent；修复后再次刷新 manifest、运行 validator、启动 fresh independent reviewer，并以以下状态结束：
   - `accepted`：经过 source-window 和 atom-level review 后，Phase 1 framework 仍保持 coherent。
   - `adjusted`：framework 已完成 refit，且所有 atom mapping 保持 traceable。
   - `needs-coverage-recheck`：refit 暴露出 missing/broad/conflicting source obligation，需要 fresh Phase 3 pass。
   - `blocked`：需要用户决定或广泛 reanalysis。
7. 持续执行 Phase 3 -> Phase 4 -> Phase 5，直到 Phase 5 返回 `accepted`、`adjusted` 或 `blocked`，或 Phase 4 返回 `blocked`。

每次运行 validator 前，使用现有 JSON trace sidecar 及其当前 digest 刷新 `trace/manifest.json`。每次 Phase validator/reviewer pass 后，再次使用 Phase trace sidecar 中的 canonical Phase decision 与 artifact digest 刷新它。`phase-statuses` 不得保存 `present`、`reviewer-passed`、`validator-passed` 或 `repair-not-needed` 等 reviewer-loop workflow state。尤其是 `phase-statuses.phase-5` 必须与 `trace/phase-5.trace.json.status` 一致；proposal-ready handoff 要求两者都为 `accepted` 或 `adjusted`。

在 Phase 5 返回 `accepted` 或 `adjusted` 且 final Change packet 已存在之前，不得从本工作流启动 `openspec-propose`。

## Main agent 门禁

每个 Phase 结束后，只检查以下 interface fact：

- `openspec/orchestrate/` 下存在必需目录和 report。
- 必需 JSON sidecar 存在，并针对已完成 Phase 通过 `validate_source_aligned_orchestrate.py`。
- 已完成 Phase 存在 `phase-works/phase-<n>/phase-<n>-reviewer-report.md`，其中记录了 fresh independent reviewer subagent identity，且该 identity 与 Phase writer 不同。writer self-check、writer final reply、validator output 或 trace field 都不能替代它。
- reviewer finding 已处理 validator warning，或记录显式 accepted warning rationale。若 reviewer/validator finding 后任何 artifact 被修改，则必须存在 `phase-works/phase-<n>/phase-<n>-repair-report.md`，并记录与 writer、reviewer 都不同的 fresh independent repair subagent identity。
- Phase report 说明 input document、output file 和 blocker。
- 生成的 artifact 通过 Artifact Language Gate。如果 Phase output 仅因 language gate 失败，将该 Phase 视为 interface-incomplete，并执行 targeted language repair；repair 必须保留 ID、path、enum/status value、行范围、atom mapping、ownership decision 和 source quote。
- Phase 1 output 包含根 `change-plan.md`、`phase-works/phase-1/change-plan.md`、`phase-works/phase-1/source-doc-manifest.md` 和 `phase-works/phase-1/phase-1-agent-report.md`；manifest 列出指定根目录下每份 source document 及其 full-read status，否则 Phase 1 必须报告 blocker。
- Phase 2 output 包含 `phase-works/phase-2/source-obligation-atoms/work-queue.md`、`phase-works/phase-2/source-obligation-atoms/index.md`、manifest 中每份 `read-full` source document 对应的 `phase-works/phase-2/source-obligation-atoms/<source>.atoms.md` 与 `.atoms.json`、`trace/phase-2.trace.json` 和 `phase-works/phase-2/phase-2-agent-report.md`。
- Phase 2 report 包含 Phase 2 index/report subagent identity/status、work queue summary 和 source-extraction trace；trace 必须表明每份 manifest source document 恰好分配给一个 canonical extraction owner、由该 owner 完整阅读，并记录找到的 atom candidate、candidate artifact projection、source remainder、candidate Change mapping、candidate capability impact/target/related field、unassigned atom、gap、duplicate-risk note 和 blocker。
- Phase 3 output 包含 `change-capability-anchors/obligation-atom-index.md`、`change-capability-anchors/obligation-atom-index.json`、`phase-works/phase-3/source-doc-manifest.md`、manifest 中每份 source document 对应的 `phase-works/phase-3/source-doc-coverage/<source>.coverage.md`、所有 `phase-works/phase-3/phase-3-trace/*.md`、`phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json`、`phase-works/phase-3/phase-3-trace/source-remainder-review.json`、`trace/phase-3.trace.json`、`phase-works/phase-3/coverage-review.md` 和 `phase-works/phase-3/phase-3-agent-report.md`。
- Phase 3 validator 必须确认 Phase 1 中每份 `read-full` source document 都出现在 Phase 3 manifest 中且有匹配的 per-source coverage file；每个 mechanically uncovered Phase 2 atom/anchor 行范围，都在 `source-remainder-review.json` 中由 semantic row 覆盖，并关联已知 `GA-####`、non-coverage status 或 blocker。存在仍含 blocker 的 remainder row 时，`coverage-complete` 无效。
- `obligation-atom-index.md` 中每个 Phase 3 global atom ID 都必须匹配 `GA-####`；不得使用其他 global 前缀或 source-local ID 作为 `Global Atom ID`。
- Phase 3 report 包含 per-source-document obligation coverage summary、规范化 global atom synthesis、规范化 artifact projection 与 capability-impact distribution、missing atom finding、duplicate/Change-ownership resolution、broad-atom split decision、non-coverage classification，以及未映射到 Change 或未解析 spec target Capability 的 source-backed obligation。
- Phase 3 output 包含 `Decision: coverage-complete` 或 `Decision: blocked`。
- Phase 4 output 包含当前 `phase-works/phase-4/` grounding packet，其中包括 `input-change-plan.md`、`source-window-dossiers/index.md`、`source-window-dossiers/source-window-index.json`、每个具备 atom-backed source window 的 input Change 和 input Capability 对应 dossier、`source-window-semantic-profile-review.md`、`source-window-grounding-issues.md`、`trace/phase-4.trace.json` 和 `phase-4-agent-report.md`。
- Phase 4 report 说明 source-window grounding 是否完成、覆盖了哪些 input Change/Capability、复制了哪些 atom-backed source window、哪些 source semantics 产生 Phase 5 refit pressure、是否仍存在 grounding issue，以及是否需要 Phase 3 recheck。
- Phase 4 不得写入 final Change packet、final Capability view、`atom-plan-mapping.md`、final `change-plan.md` 或根 `openspec/orchestrate/change-plan.md`。
- Phase 5 output 始终包含当前 `phase-works/phase-5/` refit packet，其中包括 `source-window-refit-trace.md`、`phase-5-agent-report.md` 和 `trace/phase-5.trace.json`；状态为 `needs-coverage-recheck` 或 `blocked` 时，还包含 `change-plan-adjustments.md`，且不要求 terminal mapping/final packet artifact；状态为 `accepted` 或 `adjusted` 时，包含 `input-change-plan.md`、`change-plan.md`、`atom-plan-mapping.md`、`atom-plan-mapping.json`、`final-packet-index.json`、`capability-progression-review.md`、`change-complexity-review.md`、`plan-refit-decision-log.md`、`alignment-final-report.md`、final `change-capability-anchors/index.md`、final per-Change packet、final Capability view 和 `phase-works/phase-5/change-capability-human-plan.md`。如果 foundation candidate 符合条件，其 packet 必须以 `change-kind: foundation` 位于 `final-packet-index.json` 首位；business packet 使用 `change-kind: business`。
- Phase 5 report 说明初始计划是 accepted 还是 adjusted、哪些 Phase 4 source-window semantic profile 和 atom group 驱动了计划变化、如何最终确定 artifact projection、如何评估 Capability progression、implementation-ready Change complexity 和 Change/Capability coupling audit、哪些 over-budget trigger 被 split/defer/block、哪些 atom 移动或改变 status/projection，以及是否需要 Phase 3 recheck。
- Phase 5 refit decision 在更改、拆分、合并、重新排序或重命名 Change/Capability 时引用 Phase 4 source-window dossier evidence。仅依赖 atom count、Capability count 或简短 atom summary 的 decision 不通过 gate，除非显式说明相关 source window 没有提供更多 semantic distinction。
- 每个 Phase 5 final Change 都必须通过 Source Window Semantic Grounding Gate：引用 source window，概括它们组合后的 business/system semantics，解释 atom 为何属于同一组，说明 roadmap order，给出 manual acceptance scenario，并在最终确定 atom ownership 前说明全部 contextual/dependency/evidence/non-goal handling。
- final Change packet 包含 direct owning atom、final artifact projection、contextual atom、upstream realized baseline、downstream constraint、non-goal、evidence burden，以及返回 global atom index 和 source atom file 的链接。
- `atom-plan-mapping.md` 中每个 `Final Owner Change` 为真实 final Change 的 non-direct atom 行，都必须按 `GA-####` 显式出现在该 Change final packet 的 context/dependency/evidence/preserve/non-goal 处理中。任何 final packet 都不得仅用 count、summary row、`additional-context` 或返回 mapping 的链接替代 owner-scoped non-direct atom。
- final packet、Capability view、Phase 5 mapping 和根 `change-plan.md` 保留 `GA-####` ID、direct atom projection、唯一 direct Change ownership、v2 capability impact/target/related field，以及非 `contextual-only` 的 direct 行。
- final business Capability advancement 各 surface 必须一致：Capability Map `First change`、progression matrix、roadmap `New`/`Modified`、final packet、`change-capability-anchors/index.md`、Capability view 和 human plan 都只从 `new` / `modified` target-Capability pair 推导。related Capability 和仅归属 Change 的 design/verification 行不得显示为 advancement。foundation special view 保持在 business progression 之外。
- final business Capability view file 必须严格对应各 Change 推进的 `new` / `modified` target Capability。它只能包含该 Change/target-Capability pair 的 direct spec atom；仅归属 Change 的 design/verification atom，以及 related-Capability mention、仅 dependency、contextual-only、evidence-burden、preserve/reference、later-change、显式 non-goal 和 upstream-baseline atom 必须排除在 Capability view 外，并继续显式保留在 final Change packet。唯一允许的额外 view 是面向 `foundation-substrate` 行的 `runtime-substrate-foundation`。
- Phase 5 final consistency check 必须验证 packet-level non-direct coverage：对 `atom-plan-mapping.md` 中每个 relation 为 non-direct 且 `Final Owner Change` 为真实 Change 的行，对应 final Change packet 包含完全相同的 `GA-####` 行；每个 business Capability-view 行都对应 final packet 中匹配的 direct `new` / `modified` spec 行；每个 foundation-view 行都对应 direct `foundation-substrate` 行。
- Phase 5 complexity、source-window grounding、Capability-coupling、executable-roadmap 和 foundation-executable gate 根据 `references/phase-5-targeted-plan-adjustment.md` 通过；如果该 reference 允许 blocker，则记录 blocker。
- Phase 5 达到 `accepted` 或 `adjusted` 前，不得启动 `openspec-propose`。
