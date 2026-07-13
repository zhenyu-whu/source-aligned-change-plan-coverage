# Phase 4：Source-Window Dossier 与 Semantic Profile Grounding

Phase 3 返回 `Decision: coverage-complete` 后运行 Phase 4。它是独立的 source-grounding Phase，不是 plan-refit Phase。

设置 Phase 4 的原因是：Phase 2/3 atom 行足以支持 coverage 和 traceability，但对于工程交付判断往往过于压缩。本 Phase 以 Phase 2/3 atom 行范围为索引，将原始 source window 复制到面向 reviewer 的 dossier，并按 input Change 和稳定的 input spec Capability 分组。随后编写 semantic profile，保留 Phase 5 plan refit 和人工 reviewer 所需的实际 source 含义。Capability dossier 只是辅助 semantic view，绝不是 ownership surface。

Phase 4 必须由 fresh independent subagent 执行。不得重新运行 Phase 2 extraction、规范化 atom、决定 final ownership、拆分/合并/重排 Change，也不得发明 source obligation。如果 source window 暴露出既有 Phase 3 atom 无法解释的 missing、conflicting 或 over-broad obligation，Phase 4 必须返回 `needs-coverage-recheck`。

## 输入

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/phase-works/phase-1/change-plan.md`
- `openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/index.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/*.atoms.json`，作为 canonical extraction evidence
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/*.atoms.md`，作为 reviewer mirror
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.json`，作为 canonical global atom index
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`，作为 reviewer mirror
- `openspec/orchestrate/phase-works/phase-3/coverage-review.md`
- `openspec/orchestrate/phase-works/phase-3/source-doc-coverage/*.coverage.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/*.json`，作为 canonical Phase 3 trace sidecar
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/*.md`，作为 reviewer mirror
- 原始 source document 根目录或精确 source path。

## 输出

将 Phase 4 artifact 直接写入 `openspec/orchestrate/phase-works/phase-4/`。不得创建 `pass-*`、`iteration-*`、attempt-numbered 或类似的迭代子目录。

- `openspec/orchestrate/phase-works/phase-4/input-change-plan.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/index.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/source-window-index.json`
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-change/<input-change-slug>.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-capability/<input-capability-slug>.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-grounding-issues.md`
- `openspec/orchestrate/phase-works/phase-4/phase-4-agent-report.md`
- `openspec/orchestrate/trace/phase-4.trace.json`

以下 scope rule 明确 authority boundary：`phase-works/phase-4/source-window-dossiers/` 是复制得到的 review evidence，不能替代原始 source document、source atom ledger、global atom index 或 Phase 5 final packet。

writer 完成后，Phase 4 必须通过 `references/reviewer-repair-loop.md` 定义的 reviewer/repair loop：main agent 刷新 `trace/manifest.json`、运行 Phase validator、启动 fresh independent grounding reviewer subagent；如果需要修改 artifact，则启动 fresh independent Phase 4 repair-writer subagent；刷新 manifest 后重新运行 validator，repair 后再次启动 fresh independent reviewer；只有通过后才能继续。

## Artifact 语言门禁

对每项 Phase 4 output 应用 skill-level Artifact Language Gate。按需保留固定 heading、table header、enum/status value、atom ID、source path、行范围、Capability ID、Change slug、code symbol 和精确 source quote。agent 编写的 semantic note、judgment、rationale、issue description 和 report summary 必须使用简体中文。

## Scope 规则

Phase 4 可以：

- 从 Phase 2/3 atom 行范围及附近 semantic context 中选择并复制原始 source window
- 按 input Change 和符合条件的 input Capability 对复制的 source window 分组
- 引用 Phase 2 source atom ID、`GA-####` ID、Phase 3 status/projection/owner Change/capability impact/target/related Capability、duplicate/remainder/contextual note 和 Phase 5 handoff marker
- 为每个 input Change 和 input Capability 编写 source-window semantic profile
- 记录供 Phase 5 处理的 suspected split、merge、reorder、rename、foundation、capability-boundary、contextual、dependency、evidence-burden 或 non-goal pressure
- 将缺失或含糊的 source window 报告为 grounding issue

Phase 4 不得：

- 重新运行 Phase 2 extraction 或 Phase 3 normalization
- 编辑 source document、Phase 2 source atom file、Phase 3 coverage file 或 global atom index
- 创建、拆分、合并、删除 atom 或重新编号
- 决定 final owner Change、final capability impact/target/related Capability、final atom relation 或 final artifact projection
- 更新根 `openspec/orchestrate/change-plan.md`
- 生成 final Change packet、final Capability view 或 `change-capability-anchors/index.md`
- 决定接受或调整初始计划
- 将复制的 source window 视为可以在 Phase 3 范围外发明 source obligation 的授权

如果行范围、source path 或 atom mapping 缺失或相互矛盾，导致 Phase 4 无法 grounding 某个 source-window dossier，必须记录该问题。如果 targeted inspection 无法在不修改 Phase 3 normalization 的前提下解决问题，返回 `needs-coverage-recheck`。

## Source-Window Dossier 方法

只能根据以下内容创建 Capability dossier 集合：Phase 1/当前 Capability Map 中的 Capability、Phase 3 的具体 `target-capability` 值，以及引用 source window 明确表达的 Phase 3 `related-capabilities[]` 链接。不得根据 module/provider/storage/deployment/verification label、推断的关联、仅归属 Change 的 `none` target 或自由文本提及创建 Capability dossier。

对每个 input Change 和符合条件的 input Capability，收集相关 Phase 2/3 atom，并将其原始 source window 复制到 dossier file。Phase 5 refit 前，按 candidate Change ownership 对 Change dossier 分组。Capability dossier 优先按 target impact 分组，其次按 source-explicit related evidence 分组；显式将 related-only 行标记为 `non-owning-supporting-evidence`，使 reviewer 能看清初始计划的含义，又不会把关联误解为 ownership 或 progression。

window selection 规则：

- 包含精确的 atom 行范围。
- 如果存在，包含最近的 section heading/path。
- 包含理解 entry、fact、projection、failure/recovery、verification、auth/privacy、data、API、UI、worker、persistence 或 external integration semantics 所需的相邻行。
- 当邻近的 contextual、duplicate、remainder 或 Phase 5 handoff evidence 影响同一局部 source 含义时，将其纳入。
- 优先使用保持语义完整的紧凑 window；除非 section 之间高度耦合、无法在更小 window 中安全 review，否则不要复制整份大型 source document。
- 保留行号和原始措辞。将中文 semantic note 写在复制 window 旁边，不得写入引用的 source text 内部。

每个 `by-input-change/<input-change-slug>.md` dossier 必须包含：

- input Change ID/name 和 Phase 1 closed-loop hypothesis
- 相关 input Capability
- 按 source document 和 source section 分组的 source-window inventory
- 复制的、带原始行号和精确行范围及局部 context 的 source window
- 可用时关联 `GA-####` ID 和 Phase 2 source atom ID
- 每个 atom 的 Phase 3 status/projection/owner
- 每个 atom 的 Phase 3 capability impact、target Capability 和 source-explicit related Capability
- 邻近 contextual、duplicate、remainder 或 Phase 5 handoff evidence
- preliminary semantic profile：business outcome、entry、fact、projection、failure/recovery、verification surface、manual acceptance scenario 和 suspected Phase 5 refit pressure

每个 `by-input-capability/<input-capability-slug>.md` dossier 必须包含：

- input Capability ID/name 和 Phase 1 behavior-boundary hypothesis
- 按 roadmap 顺序排列的相关 input Change
- 按 Change 和 source document 分组的复制 source window
- target `new` / `modified` spec atom 分组，以及单独标注的 contextual、dependency、evidence、non-goal 和 `non-owning-supporting-evidence` related atom 分组
- behavior-boundary semantic profile：它拥有何种行为、不得拥有何种行为、何时首次可直接测试，以及哪些后续 Change 看起来增加了 source-backed delta
- 显式确认 related-only 行不会产生 ownership、progression、Capability view 或 advanced-Capability complexity count

同时按照 `references/trace-sidecar-contract.md` 写入 `source-window-dossiers/source-window-index.json`。它是 dossier window、关联 `GA-####` ID、source hash、行范围、window text hash、semantic profile、grounding issue 和 Phase 4 status 的 canonical machine-readable index。

Phase 4 status 为 `grounded` 时，`source-window-index.json` 必须包含非空 `windows[]` array，且每个 window 都指向现有 dossier。status 为 `needs-coverage-recheck` 或 `blocked` 时，`windows[]` 可以为空，但 `grounding-issues[]` 必须非空，并说明本 Phase 无法安全生成 grounded dossier 的 source-backed 原因。

## semantic profile 审阅

编写 `source-window-semantic-profile-review.md`，每个 input Change 和 input Capability 各占一行：

| Input Unit | Unit Type | Source Windows | Atom Groups | Actual Source Semantics | Engineering Delivery Signal | Manual Acceptance Scenario | Phase 5 Refit Pressure |
| --- | --- | --- | --- | --- | --- | --- | --- |

规则：

- 根据复制的 source window 推导每个 semantic profile，不得只依赖 `Source Fact` summary。
- 对 input Change，判断 source window 是否描述了可 review 的 implementation unit：entry、fact、projection、failure path 和 verification truth 能否一并交付。
- 对 input Capability，判断 source window 描述的是持久 behavior boundary，还是临时 implementation module、页面、source section 或 one-Change alias。
- 如果 source window 表明一个真实 business loop 直接需要多个 Capability，记录 Phase 5 应保留这些 delta 的整体性；只有 source-window-backed split 能保持独立 acceptance 时才可拆分。
- 如果 source window 表明一个 input Change 混合了多个可独立 acceptance 的 business outcome，记录 Phase 5 split pressure。
- 如果 source window 只显示 technical preparation，而没有可独立运行的 operational loop，记录供 Phase 5 处理的 foundation/fold-in/context/evidence pressure。
- 如果 evidence 缺失、过宽、冲突或不明确，无法安全推导 profile，则记录 grounding issue，不得猜测。

## grounding 问题

编写 `source-window-grounding-issues.md`：

| Issue | Source Evidence | Affected Input Unit | Affected Atoms | Impact on Phase 5 | Required Next Step |
| --- | --- | --- | --- | --- | --- |

使用该文件记录：

- source path 或行范围不匹配
- source window 缺失
- source window 暗示缺少 global atom
- 原始 source window 包含多个 obligation、但 Phase 3 未拆分的 broad atom
- 相互矛盾的 candidate Change placement、Capability target 或 source-explicit related-Capability evidence
- 没有 source-window 支撑的 input Change/Capability
- Phase 5 能够安全 refit 前需要人工 product decision 的情形

## Phase 4 报告

`phase-works/phase-4/phase-4-agent-report.md` 必须包含：

| Grounding Finding | Source Ranges or Atoms | Input Unit | Files Written | Phase 5 Impact | Remaining Gap or Blocker |
| --- | --- | --- | --- | --- | --- |

还必须包含：

- 已阅读的 source document
- 已覆盖的 input Change 和 input Capability
- 按 input Change 和 Capability 统计的 source-window dossier 数量
- dossier 中表示的 atom coverage count
- semantic profile 摘要
- grounding 问题摘要
- 确认 Phase 4 未编辑 Phase 2/3 evidence 或 global atom index
- 确认 Phase 4 未决定 final Change ownership 或 final capability impact/target/related field
- 确认每项 Phase 4 artifact 都通过 Artifact Language Gate
- 确认已写入 `source-window-index.json` 和 `trace/phase-4.trace.json` 并通过 validator
- 下一必需步骤：`Start Phase 5`、`Run Phase 3 again` 或 `Blocked`

## 完成条件

Phase 4 结束时，`phase-works/phase-4/phase-4-agent-report.md` 必须且只能包含以下一个 status：

- `Phase 4 Status: grounded`
- `Phase 4 Status: needs-coverage-recheck`
- `Phase 4 Status: blocked`

如果每个 input Change 和 input Capability 都具有面向 reviewer 的 source-window dossier，semantic profile 已写入，grounding issue 不存在或可由 Phase 5 安全处理，并且无需 Phase 3 normalization recheck，使用 `grounded`。

如果 source window 暴露出 missing、over-broad、conflicting 或语义不清的 source obligation，必须先由 Phase 3 规范化才能最终完成 plan refit，使用 `needs-coverage-recheck`。

如果 source boundary、缺失的 source document、product decision 或广泛 reanalysis 阻止安全的 source-window grounding，使用 `blocked`。

达到 `grounded` 后可以启动 Phase 5。出现 `needs-coverage-recheck` 后，main agent 必须先启动 fresh Phase 3 review subagent，再启动 fresh Phase 4 grounding subagent。不得从 `needs-coverage-recheck` 或 `blocked` 直接启动 Phase 5。
