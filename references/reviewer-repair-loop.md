# Reviewer/Repair Loop 规范

本文件定义每个 Phase 的 validator/reviewer/repair 闭环。进入 workflow 前必须读取。

每个 Phase reviewer 和 repair-writer 在开始任务前，必须直接完整读取 `references/cross-phase-contract.md` 和当前 Phase reference。final integration reviewer 必须直接完整读取 cross-phase contract 以及 Phase 3、Phase 4、Phase 5 reference。main agent prompt 摘要、转述或继承上下文不能替代直接读取。

## 必需顺序

每个 Phase 完成顺序固定为：

```text
Phase writer subagent
-> main agent 运行 Phase validator
-> fresh independent Phase reviewer subagent
-> 若需修改 artifact，则由 fresh independent Phase repair-writer subagent 处理
-> main agent 重新运行 validator
-> 每次 repair 后再次运行 fresh independent Phase reviewer subagent
-> pass 后进入下一 Phase
```

如果 reviewer 判定无修复项，可以跳过 repair-writer subagent，但必须在 reviewer report 和 phase trace 中记录 `repair-not-needed`。一旦需要修改任何 artifact，repair 必须由 fresh independent repair-writer subagent 执行，不能由 writer、reviewer 或主 agent 直接补写。

Phase 5 返回 `accepted` 或 `adjusted` 后，在 handoff 给 `openspec-propose` 前追加固定 terminal 顺序：

```text
main agent 运行 all-phase complete validator
-> fresh independent final integration reviewer subagent
-> integration pass 后 handoff
```

complete validator 或 final integration reviewer 未通过时不得 handoff；根据 finding 进入 Phase 5 repair loop、返回 `needs-coverage-recheck`，或报告 `blocked`。

## 独立性规则

- Reviewer 和 repair-writer 都必须由主 agent 单独 spawn fresh subagent，且必须使用 `model=GPT-5.5` 和 `reasoningEffort=xhigh`。
- Reviewer subagent 必须与 phase writer subagent 不同；repair-writer subagent 必须与 phase writer subagent、所有 reviewer subagent 都不同。
- Final integration reviewer 必须是 fresh leaf subagent，使用相同 runtime，且不同于 Phase 5 writer、Phase 5 reviewer 和 Phase 5 repair-writer。
- Writer subagent 的自检、最终回复、agent report、trace 字段或 “reviewer passed” 文案不满足 reviewer 步骤。
- Validator 通过不满足 reviewer 步骤；validator 只提供 reviewer 输入之一。
- Reviewer subagent 对被审 artifact 只读，只能写入或追加本 Phase 的 reviewer report，不得修改被审 artifact，不得执行 repair，不得推进下一 Phase。
- Repair-writer subagent 只能根据 validator issues 和 reviewer report 修改本 Phase 允许的 artifact，并写入或追加本 Phase 的 repair report；不得重新解释上游 frozen evidence，不得推进下一 Phase。
- Reviewer 和 repair-writer 都是 leaf worker，不得 spawn、调用、委派任何嵌套 AI subagent、`codex exec`、multi-agent worker 或其他 agentic reasoning 子进程。
- 每次 repair 后必须重新运行 validator，并重新 spawn fresh independent reviewer subagent。不得复用同一个 reviewer subagent 通过 `send_input` 进行复审。
- Final integration reviewer 对 Phase 3/4/5 和 final handoff surface 只读，只能在 `phase-works/phase-5/phase-5-reviewer-report.md` 中追加 integration review 记录；不得修改 artifact 或执行 repair。

## 必需证据

每个 Phase 在进入下一 Phase 前必须有可审计 evidence：

- `phase-works/phase-<n>/phase-<n>-reviewer-report.md`：必需。每次 reviewer run 必须保留 reviewer subagent identity、writer subagent identity 或 writer 来源、validator input status、只读检查范围、findings、accepted warnings、是否需要 repair、最终 pass/block 决定。
- `phase-works/phase-<n>/phase-<n>-repair-report.md`：仅当发生 artifact 修改时必需。每次 repair run 必须保留 repair subagent identity、被消费的 validator/reviewer findings、修改文件、保留的不变量、未修复项和 blockers。
- `trace/phase-<n>.trace.json` 应记录 reviewer/repair loop 摘要，但 trace 摘要不能替代 reviewer report 或 repair report。
- `trace/manifest.json` 可以在 validator 前创建或刷新，用于提供当前 trace sidecar digest。只有 validator 和 independent reviewer 均通过后，才可以在 reviewer report、phase trace summary 和 manifest canonical phase decision 中记录该 Phase 可进入下一阶段。
- Phase 5 handoff 前，`phase-works/phase-5/phase-5-reviewer-report.md` 还必须记录 final integration reviewer identity、all-phase complete validator status、跨 artifact 检查范围、finding、accepted warning 和 pass/block decision。

## 权威性规则

- Validator 只检查结构、trace、digest、schema、ID、coverage、mirror drift 和跨 artifact 一致性；不替代语义判断。
- Reviewer 只读，不直接改 artifact。
- Reviewer 必须处理 validator warnings；warnings 可以接受，但必须有 reviewer 判断或修复计划。
- Repair-writer 只能修改本 Phase 允许的 artifact。
- Phase 2 完成后 raw `.atoms.md/.json` 冻结。后续发现的问题进入 Phase 3 missing/split/recheck，不回改 Phase 2。
- Phase 5 发现缺失或过宽 source obligation 时返回 `needs-coverage-recheck`，不得在 Phase 5 发明新 atom。

## reviewer 范围

Phase 1 reviewer 检查项：

- 检查 Capability-first 顺序、Capability Purpose/Owns/Excludes 与 implementation-substitution、Change one-intent/cohesion/independent archive/indivisibility/acceptance、foundation exception 和 Change–Capability overlay。
- 执行 Hide Capability Names、Hide Roadmap 和 post-mapping diagnostic；不得把 diagonal matrix 本身当作失败，也不得为改善形状扭曲真实 boundary。
- 检查 Phase 1 没有提前创建 obligation、atom、coverage status、line-range anchor、unique owner、OpenSpec `New`/`Modified` 或 Phase 2 work queue。

Phase 2 reviewer 检查项：

- 对 source 正文与 atom ledger 做独立语义抽查，检查所有有产品/系统语义的内容是否已提取、每个 atom 是否恰好一个紧凑连续 range、`Source Fact` 是否为该 range 内原文连续摘录、atom 是否 broad，以及 projection/status/现有 framework mapping 是否仅作为候选。全文 remainder disposition 由 Phase 3 独立闭合。
- 检查 Phase 2 未执行 duplicate 判断、new/refit Change 判断、new Capability 判断或 Capability impact 判断。
- 检查每个 `read-full` source 是否正好一个 canonical owner 和一个 `.atoms.md/.json`。

Phase 3 reviewer 检查项：

- 检查 `GA-####` 归一、每个 global atom 的单一 canonical range 与原文 `Source Fact`、source-to-global 全覆盖、non-coverage 合理性、duplicate/broad split 处理。
- 检查 direct 或 `phase-5-refit-required` atom 没有使用 `contextual-only`。

Phase 4 reviewer 检查项：

- 检查 source-window dossier 是否真实支撑 semantic profile。
- 检查 grounding issue 是否应返回 `needs-coverage-recheck`。

Phase 5 reviewer 检查项：

- 检查 final ownership、non-direct 承载、Capability Purpose/Owns/Excludes、repository baseline reconciliation、capability progression、Change intent/cohesion/indivisibility 和 complexity gate。
- 检查 final packet 是否显式列出 owner-scoped non-direct atom。
- 检查 capability view 只包含 direct advancement rows。

final integration reviewer 检查项：

- 对 Phase 3/4/5 做跨 artifact reconciliation。
- 检查 global atom index、source-window index、atom-plan mapping、Capability baseline reconciliation、final packets、capability views、root `change-plan.md` 和 human plan 是否一致。

## repair 规则

- Repair 必须保留 `GA-####`、source path、line range、source fact 和 upstream evidence，除非本 Phase 明确允许修正。
- Repair 不得通过删除 warning 对应数据来让 validator 通过。
- Repair 后必须重新运行 validator 和 reviewer。
- 若 repair 需要修改冻结上游 evidence，返回 `needs-coverage-recheck` 或 `blocked`，由主 agent 重新启动允许的 Phase。
