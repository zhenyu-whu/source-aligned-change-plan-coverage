# Reviewer/Repair Loop 规范

本文件定义每个 Phase 的 validator/reviewer/repair 闭环。进入 workflow 前必须读取。

每个 Phase reviewer 和 repair-writer 在开始任务前，必须直接完整读取 `references/cross-phase-contract.md` 和当前 Phase reference。Phase 1与Phase 5 reviewer/repair还必须直接完整读取 `references/change-capability-framework-principles.md`。final integration reviewer必须读取cross-phase contract、共享framework原则以及Phase 3–5 reference。main agent prompt摘要、转述或继承上下文不能替代直接读取。

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

- Reviewer subagent 必须与 phase writer subagent 不同；repair-writer subagent 必须与 phase writer subagent、所有 reviewer subagent 都不同。
- Final integration reviewer 必须是 fresh leaf subagent，且不同于 Phase 5 writer、Phase 5 reviewer 和 Phase 5 repair-writer。
- Writer subagent 的自检、最终回复、agent report、trace 字段或 “reviewer passed” 文案不满足 reviewer 步骤。
- Validator 通过不满足 reviewer 步骤；validator 只提供 reviewer 输入之一。
- Reviewer subagent 对被审 artifact 只读，只能写入或追加本 Phase 的 reviewer report，不得修改被审 artifact，不得执行 repair，不得推进下一 Phase。Phase 3 reviewer保持完全只读，只在最终回复返回结构化 review evidence；由 main agent机械记录到 `phase-3.trace.json.reviewer-loop`，reviewer本身不得写 trace。
- Repair-writer subagent 只能根据 validator issues 和 reviewer evidence修改本 Phase允许的 artifact，并写入或追加本 Phase的 repair report；不得重新解释上游 frozen evidence，不得推进下一 Phase。Phase 3 repair-writer在最终回复返回结构化 repair evidence，由 main agent机械记录到 trace，不另建 report。
- Reviewer 和 repair-writer 都是 leaf worker，不得 spawn、调用、委派任何嵌套 AI subagent、`codex exec`、multi-agent worker 或其他 agentic reasoning 子进程。
- 每次 repair 后必须重新运行 validator，并重新 spawn fresh independent reviewer subagent。不得复用同一个 reviewer subagent 通过 `send_input` 进行复审。
- Final integration reviewer 对 Phase 3/4/5 和 final handoff surface 只读，只能在 `phase-works/phase-5/phase-5-reviewer-report.md` 中追加 integration review 记录；不得修改 artifact 或执行 repair。

## 必需证据

每个 Phase 在进入下一 Phase 前必须有可审计 evidence。Phase 3 为保持固定五产物，使用下述例外：

- `phase-works/phase-<n>/phase-<n>-reviewer-report.md`：必需。每次 reviewer run 必须保留 reviewer subagent identity、writer subagent identity 或 writer 来源、validator input status、只读检查范围、findings、accepted warnings、是否需要 repair、最终 pass/block 决定。
- `phase-works/phase-<n>/phase-<n>-repair-report.md`：仅当发生 artifact 修改时必需。每次 repair run 必须保留 repair subagent identity、被消费的 validator/reviewer findings、修改文件、保留的不变量、未修复项和 blockers。
- Phase 3 不创建 reviewer/repair report文件；reviewer/repair worker在只读审查或允许的 repair完成后通过最终回复返回结构化 evidence，main agent只做机械转录，将 reviewer identity、writer identity、validator status、finding、repair和 pass/block evidence写入 `trace/phase-3.trace.json.reviewer-loop`。不得因此新增第六个 Phase 3产物。
- Phase 1–3 trace按各自schema记录reviewer/repair摘要；Phase 4/5 trace保持其精简固定字段，reviewer/repair evidence只保存在对应report中。任何trace摘要都不能替代reviewer report或repair report。
- `trace/manifest.json` 可以在 validator 前创建或刷新，用于提供当前 trace sidecar digest。只有 validator 和 independent reviewer 均通过后，才可以在 reviewer report、phase trace summary 和 manifest canonical phase decision 中记录该 Phase 可进入下一阶段。
- Phase 5 handoff 前，`phase-works/phase-5/phase-5-reviewer-report.md` 还必须记录 final integration reviewer identity、all-phase complete validator status、跨 artifact 检查范围、finding、accepted warning 和 pass/block decision。

## 权威性规则

- Validator 只检查结构、trace、digest、schema、ID、coverage、mirror drift 和跨 artifact 一致性；不替代语义判断。
- reviewer/repair/agent report和Phase 2 work queue都是非canonical流程证据，不进入manifest；它们不能覆盖Phase-specific authority。
- Reviewer 只读，不直接改 artifact。
- Reviewer 必须处理 validator warnings；warnings 可以接受，但必须有 reviewer 判断或修复计划。
- Repair-writer 只能修改本 Phase 允许的 artifact。
- Phase 2 完成后 raw `.atoms.md/.json` 冻结。Phase 3 只在 uncovered range创建 gap atom；broad Phase 2 atom必须 targeted回 Phase 2重新提取。
- Phase 5 发现缺失或过宽 source obligation 时返回 `needs-coverage-recheck`，不得在 Phase 5 发明或合并 atom。

## reviewer 范围

Phase 1 reviewer 检查项：

- 直接使用共享framework原则检查Capability-first顺序、Capability gate、Change gate、foundation例外、排序和Change-Capability overlay；不得在Phase reference中寻找或创建第二套标准。
- 执行 Hide Capability Names、Hide Roadmap 和 post-mapping diagnostic；不得把 diagonal matrix 本身当作失败，也不得为改善形状扭曲真实 boundary。
- 检查 Phase 1 没有提前创建 obligation、atom、coverage status、line-range anchor、unique owner、OpenSpec `New`/`Modified` 或 Phase 2 work queue。

Phase 2 reviewer 检查项：

- 对 source 正文与 atom ledger 做独立语义抽查，检查所有有产品/系统语义的内容是否已提取、每个 atom 是否恰好一个紧凑连续 range、`Source Fact` 是否为该 range 内原文连续摘录、atom 是否 broad，以及 projection/status/现有 framework mapping 是否仅作为候选。全文 remainder disposition 由 Phase 3 独立闭合。
- 检查 Phase 2 未执行 duplicate 判断、new/refit Change 判断、new Capability 判断或 Capability impact 判断。
- 检查每个 `read-full` source 是否正好一个 canonical owner 和一个 `.atoms.md/.json`。

Phase 3 reviewer 检查项：

- 检查每份 `read-full` source都有有效 Phase 2 artifact，covered/complement range可机械重算。
- 检查每个 Phase 2 atom和 Phase 3 gap atom恰好一个独立 `GA-####`，global index row只包含 ID与 evidence ref。
- 检查 Phase 3 artifact没有复制 Phase 2 `source-fact`，且每个 uncovered range都由 gap extraction或 remainder disposition闭合。
- 检查 broad Phase 2 atom被记录为 targeted `needs-extraction-recheck`，没有在 Phase 3拆分。
- 不执行 semantic duplicate、owner、projection、relation或 Capability review。

Phase 4 reviewer 检查项：

- 检查resolver是否为每个GA加载正确的Phase 2/3 frozen evidence，且不读取原始source document。
- 检查assembler直接从Phase 1–3生成collection Markdown，派生index没有反向承载语义；每个GA恰好一个index row，Change/Capability bucket严格来自Phase 2 candidate hint或Phase 3 gap provenance。
- 检查每个initial Change/Capability都有collection，包括空集合；collection中的`source-fact`逐字等于canonical evidence；派生index的collection path/digest与Markdown一致且没有stale文件。
- 检查Phase 4没有semantic profile、refit、final owner/projection/Capability判断；evidence异常时返回targeted recheck或blocker。

Phase 5 reviewer 检查项：

- 使用共享framework原则检查`framework-refit-trace.json`先审Capability、再审Change、再审unassigned/gap，且initial framework默认保留、调整均有frozen source fact支持；确认`plan-refit-review.md`只是逐字重渲染mirror。
- 检查每个initial Capability/Change及每个unassigned/gap GA在refit JSON中恰好一个review disposition，gate result、status与framework实际变化一致。
- 检查每个GA独立的final owner/projection/relation/Capability mapping、non-direct承载和repository baseline reconciliation。
- 检查 final packet 是否显式列出 owner-scoped non-direct atom。
- 检查 capability view 只包含 direct advancement rows。
- 检查framework没有从GA数量、planning graph或complexity budget推断boundary，且没有semantic duplicate resolution。
- 检查 packet/handoff明确声明其为未语义去重的完整 evidence mapping。

final integration reviewer 检查项：

- 对 Phase 3/4/5 做跨 artifact reconciliation。
- 检查global atom index、Phase 4 collection Markdown及派生index、framework refit JSON及review mirror、atom-plan mapping、Capability baseline、final packets、Capability views、anchor index和根`change-plan.md`一致。
- 检查每个evidence occurrence从Phase 2/3 frozen source fact到Phase 4 collection、Phase 5 mapping和packet保持一对一GA identity；语义相同occurrence不得丢失或合并。

## repair 规则

- Repair 必须保留 `GA-####`、evidence ref、source path、line range、source fact 和 upstream evidence，除非本 Phase明确要求 targeted re-extraction。
- Repair 不得通过删除 warning 对应数据来让 validator 通过。
- Repair 后必须重新运行 validator 和 reviewer。
- 若 repair 需要修改冻结上游 evidence，返回 `needs-coverage-recheck` 或 `blocked`，由主 agent 重新启动允许的 Phase。
