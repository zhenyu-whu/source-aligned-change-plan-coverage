# Phase 2：source-first obligation atom 提取

Phase 2 直接从 source document 提取 source-backed obligation atom candidate。analysis unit 是 source document，不是 planned Change。Phase 1 framework 提供 candidate Change context 和 candidate stable-Capability map；它不得妨碍发现 unassigned、cross-cutting，或为 new/refit Change 或 spec Capability 提供 evidence 的 atom。

Phase 2 生成不可变 raw extraction evidence 和独立的 Phase 2 aggregate inventory。Phase 3 负责 normalization、missing-atom gap closure、duplicate resolution、candidate Change ownership 和规范化 capability-impact metadata。Phase 4 负责 input Change/Capability 的 source-window grounding。Phase 5 负责 final Change ownership、spec-Capability impact、plan refit 和 per-Change packet generation。

## 输入

- `openspec/orchestrate/change-plan.md`
- `openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md`
- 用户指定的 source document 根目录或精确 source path，仅用于解析 manifest path 和行引用。

## 输出

只写入以下 Phase 2 artifact：

- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/work-queue.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/index.md`
- 为 manifest 中每份 `Read Status: read-full` source document 写入 `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/<source-relative-path-without-extension>.atoms.json`
- 为 manifest 中每份 `Read Status: read-full` source document，从匹配 JSON 渲染 `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/<source-relative-path-without-extension>.atoms.md`
- `openspec/orchestrate/trace/phase-2.trace.json`
- `openspec/orchestrate/phase-works/phase-2/phase-2-agent-report.md`

在 `phase-works/phase-2/source-obligation-atoms/` 下使用单层 filename：根据 manifest 中列出的 source document path 生成名称，移除 extension，将 path separator 替换为 `--`，再添加 `.atoms.md` 和 `.atoms.json`。

Phase 2 完成后，`.atoms.json` file 不可修改。其 `.atoms.md` file 是 renderer mirror，只能从 JSON 刷新。如果后续 Phase 发现 missing atom、duplicate fact、source-window grounding issue 或 ownership change，应将其记录在 Phase 3 global atom index、Phase 4 grounding artifact 和 Phase 5 refit artifact 中；不得改写原始 Phase 2 source atom JSON。

writer 完成后，Phase 2 必须通过 `references/reviewer-repair-loop.md` 定义的 reviewer/repair loop：main agent 运行 Phase validator、启动 fresh independent source extraction reviewer subagent；如果需要修改 artifact，则启动 fresh independent Phase 2 repair-writer subagent；重新运行 validator，repair 后再次启动 fresh independent reviewer；只有通过后才能冻结 raw `.atoms.json` evidence 及其 rendered `.atoms.md` mirror。如果 validator 报告 `rendered-markdown-drift`，repair 必须重新渲染或修复 JSON；不得手工编辑 Markdown。

## 输出所有权

Phase 2 output responsibility 分为 orchestration、source extraction 和 aggregation：

- main orchestrating agent 可以在 Phase 2A 编写 `phase-works/phase-2/source-obligation-atoms/work-queue.md`，因为这是轻量 scheduling，而不是 source obligation extraction。
- source-extraction subagent 只能写入分配给自己的 canonical `phase-works/phase-2/source-obligation-atoms/<source>.atoms.json` sidecar。随后 main orchestrating agent 或 writer 运行 `scripts/render_source_aligned_orchestrate.py --artifact phase2-source-atoms --write`，生成匹配的 `.atoms.md` mirror。
- 所有 extraction subagent 完成后，启动 fresh independent Phase 2 index/report subagent。该 subagent 只能写入 `phase-works/phase-2/source-obligation-atoms/index.md`、`phase-works/phase-2/phase-2-agent-report.md` 和 `trace/phase-2.trace.json`。
- Phase 2 index/report subagent 可以读取 `change-plan.md`、`phase-works/phase-1/source-doc-manifest.md`、`phase-works/phase-2/source-obligation-atoms/work-queue.md` 和所有生成的 `phase-works/phase-2/source-obligation-atoms/*.atoms.json` file。它可以检查 rendered `.atoms.md` mirror 是否便于 reviewer 阅读，但 count、status distribution、required section、line-range format 和 missing output 必须从 JSON 推导。
- Phase 2 index/report subagent 不得提取新 atom、编辑 source atom file、重新读取 source 正文以创建新 evidence、执行 global duplicate resolution、决定 final atom ownership、闭合 semantic coverage，也不得读取 Phase 3/Phase 4/Phase 5 output。
- 如果 aggregation pass 发现缺失、格式错误或不完整的 extraction output，必须在 `phase-works/phase-2/phase-2-agent-report.md` 中记录 blocker，并继续把 aggregate 严格限制在 Phase 2 scope。
`phase-works/phase-2/source-obligation-atoms/index.md` 和 `phase-works/phase-2/phase-2-agent-report.md` 仅作为 Phase 2 summary/review aid，不得成为规范化 global atom index 或 final plan ownership map。

## Artifact 语言门禁

对每项 Phase 2 output 应用 skill-level Artifact Language Gate。按需保留固定 table header、field name、enum/status value、atom ID、path、行范围、Capability ID、Change slug、proof-type token 和精确 source phrase，但所有 agent 编写的 explanatory content 都必须使用简体中文。

尤其是 `Source Fact`、`Rationale`、`Propose Use`、`Reason`、ownership ambiguity note、candidate missing boundary note、blocker、report summary 和 table cell 中的任何 explanation 都必须使用中文；只有整个值仅包含固定 enum、ID、path、command、proof-type token 或精确 source term 时例外。`Source Phrase` 可以保留原始措辞。

每次写入 Phase 2 artifact 后，执行 skill gate 中的 language self-check。忽略 ID、path、command、code、固定 enum/status value 和精确 source phrase 后，如果仍存在英文主导的 explanation sentence，必须在 Phase 2 结束前改写。

## Obligation Atom 模型

obligation atom 是应延续到后续 `openspec-propose` artifact 中、由 source 支撑的最小 production obligation。后续 proposal/spec/design/task file 应能直接消费一个 atom，而无需重新解释宽泛的 source 段落。

candidate artifact projection 记录 atom 预期进入的下游位置。它只是一项 candidate；Phase 3 将其规范化，Phase 5 完成最终定案。不得推断每个 `direct-candidate` 都是 spec requirement。architecture、runtime、package、provider、deployment、schema 和 verification atom 往往投影到 design 或 task/proof，而不是 normative spec。

将提取出的 source fact 分类到以下 bucket：

- direct candidate atom：可能由某个 Change 实现、preserve、验证或显式排除的 source-backed production behavior。
- contextual candidate atom：可能约束 design 的 source-backed fact 或未来 obligation；除非 Phase 3 将其重新分类并规范化为 direct，否则不计入 direct Capability advancement。Phase 4 可以增加 grounding evidence，但不分配 impact 或 target。
- unassigned atom：Phase 1 framework 无法明确 candidate owner Change 的 source-backed production obligation。
- candidate new Change atom：提示 Phase 1 framework 可能缺少 executable loop 或切分错误的 source-backed obligation。
- candidate new Capability atom：提示缺少持久 spec behavior boundary 的 `spec-requirement` 或 `spec-guard` obligation。不得对 `design-obligation` 或 `verification-obligation` atom 使用此分类。
- non-coverage classification：reference-only、prototype-only、non-production、superseded、no-impact 或 blocked/conflicting 的 source-backed material。

direct candidate atom 只有在具备 source 支撑、与实现相关、足够小而能独立验证或排除，且不只是宽泛 summary 时才有效。一个 atom 应表示一个 condition、state、action、display rule、data fact、transition、failure path、preserve boundary、verification requirement 或显式 non-goal。如果 source 段落包含多个此类 obligation，将其拆成多个 atom。

atom type：

- `page-role`
- `route`
- `entry`
- `exit`
- `state`
- `trigger`
- `display`
- `primary-action`
- `disabled-action`
- `recovery`
- `interaction-rule`
- `data-fact`
- `auth-privacy-rule`
- `failure-path`
- `responsive`
- `architecture-runtime`
- `verification`
- `acceptance`
- `preserve-boundary`
- `explicit-non-goal`
- `dependency`
- `reference`

使用稳定、可读的 source-local ID，例如：

- `intake-form.state.valid.submit-enabled`
- `approval-flow.interaction.edit-overwrites-pending-state`
- `async-job.failure-no-result`

Phase 3 建立规范化 global obligation atom index 时，可以重命名 ID 或添加 global qualifier。不得假设 Phase 2 ID 在全局唯一。

candidate artifact projection value：

- `spec-requirement`：应成为 requirement/scenario content 的 normative user/system behavior。
- `spec-guard`：spec 必须保护、但不得转化成新 positive behavior 的 preserve boundary、显式 non-goal、forbidden drift 或 must-not scope。
- `design-obligation`：design 必须消费的 architecture/runtime/data/API/module/provider/deployment shape。
- `verification-obligation`：task/proof 必须消费的 proof、fixture、visual、smoke 或 evidence strategy。
- `contextual-only`：应约束解释但不应成为下游 implementation scope 的 non-direct context。
- `unsure`：仅在 source semantics 不足时使用；Phase 3 必须解决或阻塞。

`contextual-only` 必须与 contextual、reference、non-production、non-goal 或其他 non-direct candidate status 配对。如果某行为 `direct-candidate`，不得分配 `contextual-only`；应选择 `spec-requirement`、`spec-guard`、`design-obligation` 或 `verification-obligation`。如果 source fact 更像 contextual 而非 direct，将 candidate status 改为 `contextual-candidate`；如果无法安全决定 projection，使用 `unsure` 并说明 Phase 3 为何必须解决它。

candidate Capability field 使用以下 v2 contract：

- `candidate-capability-impact`：`new`、`modified`、`none` 或 `unresolved`。
- `candidate-target-capability`：由 impact 允许的 Phase 1 Capability ID、`candidate-new-capability`、`none` 或 `unresolved`。
- `candidate-related-capabilities[]`：引用 source window 明确表达关联的唯一 Phase 1 Capability ID array。默认为 `[]`，排除 target Capability，只作为 non-owning supporting evidence。

规则：

- direct `spec-requirement` 或 `spec-guard` 行使用具有具体 target 的 `new` / `modified`；Phase 2 无法安全决定时，使用具有非空 rationale 的 `unresolved`。`candidate-new-capability` 只允许与 impact `new` 及上述 spec projection 之一配对。
- direct `design-obligation` 或 `verification-obligation` 行始终使用 impact `none` 和 target `none`。它仍是 direct 且由 Change candidate-own；不得仅因没有 target Capability 而将其降级为 contextual。
- non-direct/contextual 行使用 impact `none` 和 target `none`。
- impact `none` 要求 target `none`。impact `unresolved` 允许已知 target 或 `unresolved`，要求 rationale，并且必须在 Phase 3 规范化或阻塞。
- related Capability 绝不替代必需 target，也绝不代表 `new` / `modified`、progression、ownership 或未来 Capability view。

## Phase 2A：work queue 规划

启动 extraction subagent 前，创建 `phase-works/phase-2/source-obligation-atoms/work-queue.md`。

这是轻量 scheduling step。可以读取 `change-plan.md`、`phase-works/phase-1/source-doc-manifest.md`、source path、document name、source role、directory grouping、file size 和 line count。不得提取 obligation atom、决定 coverage、分类 source obligation，也不得使用 filename/path heuristic 证明某 document 不含 production obligation。

使用此 step 保持 context quality 并提高 parallelism：

- 先按 source family、document role、line count 和预期 extraction difficulty 建立初始 semantic split。
- 启动 subagent 前执行 merge review。small/medium candidate batch 共享 source family 或 extraction discipline，且合并后的 context 仍便于 review 时，将其合并。
- 默认目标：Phase 2 extraction batch 总数不超过五个。只有 source set 确实很大、包含多份超大 document，或合并 batch 会产生不安全 context pressure 或降低 extraction quality 时，才能超过五个；在 work queue 中记录例外 rationale。
- 如果最大化 parallelism 会产生许多小 extraction batch，则不要这样优化。优先使用数量更少、coherent 的 canonical owner，而不是松散地为每个小 cluster 分配一个 subagent。
- small document 可以按 directory、source role 或 doc type 分批。
- medium document 的合计 line count 合理时，可以用小 batch 分配。
- large document 通常应分配 dedicated extraction subagent。
- very large document 仍只允许一个 canonical extraction owner；该 owner 可以按 section 组织 output，但 Phase 2 不得将同一 source document 的 canonical extraction 拆给多个 subagent。
- prototype page、prototype object、system contract、architecture/product doc 和 verification matrix 应按 coherent source domain 分批，而不是按任意 filename 顺序。
- batch 只是 scheduling unit；batch 中每份 source document 仍需要独立 `<source>.atoms.md` file。

`phase-works/phase-2/source-obligation-atoms/work-queue.md` 必须包含：

| Batch | Source Documents | Line Counts | Source Roles / Doc Types | Assignment Rationale | Extraction Mode | Canonical Owner |
| --- | --- | --- | --- | --- | --- | --- |

规则：

- manifest 中每份 `Read Status: read-full` source document 必须恰好出现在一个 batch 中。
- `Extraction Mode` 应为 `single-doc`、`small-doc-batch`、`medium-doc-batch` 或 `large-doc-dedicated`。
- `Assignment Rationale` 可以引用 line count、source role、path domain、doc type 和预期 context pressure。
- work queue 必须在 table 后包含简短 `Batch Merge Review` section，说明 initial candidate batch count、final batch count、合并了哪些 candidate batch，以及为何 final queue 超过五个 batch。
- work queue 不是 source coverage evidence，不得包含 atom count、coverage judgment 或 no-obligation conclusion。

## Phase 2B：source-first subagent 约束

Phase 2 必须能够作为一组 source document extraction 接受 review。

1. 阅读 `change-plan.md`，了解 candidate Change、Capability、sequencing assumption 和当前 planned boundary。
2. 阅读 `phase-works/phase-1/source-doc-manifest.md`，列出每份 `Read Status: read-full` source document。
3. 使用 Phase 2A scheduling rule 建立 `phase-works/phase-2/source-obligation-atoms/work-queue.md`。
4. 每个 work queue batch 启动一个 fresh source-extraction subagent。
5. 每个 source-extraction subagent 必须完整阅读分配给自己的 source document 正文。
6. 每个 subagent 先从 source 提取 atom candidate；只有 source-backed atom list 明确后，才分配 candidate owner Change 和 capability-impact metadata。
7. `Candidate Owner Change` 可以是 planned Change、`unassigned`、`candidate-new-change`、`contextual` 或 `non-direct`。Capability field 遵循上述 v2 contract；Capability 绝不作为 co-owner。
8. 不得要求 subagent 跨所有 source document 模拟一个 planned Change。Phase 2 不得生成 per-Change canonical atom ledger。
9. 所有 source-extraction subagent 完成后，运行 Output Ownership 中说明的 fresh Phase 2 index/report subagent。
10. index/report subagent 可以针对缺失或格式错误的 file 报告 blocker，但不得 repair、重新解释或扩展 atom content。
11. 确认每个 source-extraction owner 已写入 source atom JSON sidecar，再让 Phase 2 index/report subagent 按 `references/trace-sidecar-contract.md` 写入 `trace/phase-2.trace.json`。
12. main orchestrating agent 刷新 `trace/manifest.json`、运行 `validate_source_aligned_orchestrate.py --phase phase-2`，随后使用 independent reviewer 和 repair-writer subagent 运行 Phase 2 reviewer/repair loop，再冻结 Phase 2。
13. 执行 Phase 2 extraction 或 aggregation 时，不得读取 Phase 3、Phase 4 或 Phase 5 output。

使用确定性的 source filename：

- 来源 `docs/product/pages/settings.md` -> `docs--product--pages--settings.atoms.md`
- 来源 `docs/architecture/runtime-design.md` -> `docs--architecture--runtime-design.atoms.md`

## UI 与 flow atom 提取规则

对于 page doc、object/component doc、flow contract、interaction map、state vocabulary、fixture contract、scenario registry、verification matrix 和 design-system document，不得将页面或对象细节压缩为一个 broad atom。

强制 extraction 规则：

- 每个具有 production effect 的 page/object route、duty、entry 或 exit 都必须有 atom。
- 每个具名 state 至少有一个 `state` atom。
- 每个 state trigger、display content、primary action、disabled action 和 recovery rule 都必须由 atom 表示，或显式分类为 non-production/no-impact。
- 每个会改变 persistence、navigation、action submission、blocking、recovery、language、access/quota behavior、privacy 或 state derivation 的 interaction rule 都必须有 atom。
- responsive requirement 影响用户完成 workflow 或检查必需 state 的能力时，必须有 `responsive` atom。
- 每个 acceptance criterion 必须有 `acceptance` 或 `verification` atom，或引用其 duplicate atom ID。
- 当 `do not`、`non-goal` 或 `out of scope` item 可防止后续 Change scope creep 时，必须将其保留为 `explicit-non-goal` atom。
- 纯 cosmetic text label 可以是 contextual；定义 action、state name、error copy 或 required affordance 的 label 必须成为 atom。

不得把 UI content 以通用 "duplicate page detail" 结束处理。如果确实 duplicate，在已知时列出被重复的 source-local atom ID，并说明 semantic equivalence。

## 每份来源的 atom 文件

每个 rendered `phase-works/phase-2/source-obligation-atoms/<source>.atoms.md` mirror 必须包含：

- 来源文档路径
- Phase 1 manifest 中的 source document role
- source document 是否已完整阅读
- 纳入考虑的 Phase 1 candidate Change/Capability
- 来源章节清单
- obligation atom 候选台账
- 来源剩余内容说明
- 所有权歧义说明
- candidate missing plan boundary（如有）
- blocker，或 `None`
- `Trace Appendix`，其中包含 trace file、trace schema、trace sha256 和 render contract `source-aligned-render-v2`

### 来源章节清单

每个 source atom file 必须包含 section inventory：

| Source Section or Range | Read Status | Production Meaning | Atom IDs | Non-Atom Classification | Reason |
| --- | --- | --- | --- | --- | --- |

规则：

- source document 必须完整阅读。
- section/range 行应足够小，使 Phase 3 无需盲目重读整个 document 就能验证 coverage。
- `Production Meaning` 可以为 `obligation-bearing`、`contextual`、`reference-only`、`prototype-only`、`background`、`formatting`、`conflict` 或 `unclear`。
- 如果某 section 没有 atom，reason 必须说明其为何没有 production obligation 或为何 blocked。

### obligation atom 候选台账

每个 source atom file 必须包含：

| Source Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Candidate Status | Candidate Artifact Projection | Candidate Owner Change | Candidate Capability Impact | Candidate Target Capability | Candidate Related Capabilities | Roles | Rationale | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

规则：

- `Lines` 必须使用 `L<start>-L<end>` 格式；多个范围使用 `; ` 连接。
- `Normativity` 必须是 `must`、`must-not`、`should`、`context` 之一。
- `Candidate Status` 必须是 `direct-candidate`、`contextual-candidate`、`unassigned`、`candidate-new-change`、`candidate-new-capability`、`explicit-non-goal`、`reference-only`、`prototype-only-not-production`、`superseded`、`duplicate-candidate`、`no-product-or-system-impact`、`unresolved-conflict` 或 `unclassified` 之一。
- `Candidate Artifact Projection` 必须是 `spec-requirement`、`spec-guard`、`design-obligation`、`verification-obligation`、`contextual-only` 或 `unsure` 之一。
- `Candidate Owner Change` 可以是 Phase 1 Change、`unassigned`、`candidate-new-change`、`contextual` 或 `none`；不得包含 Capability ID。
- `Candidate Capability Impact`、`Candidate Target Capability` 和 `Candidate Related Capabilities` 必须遵循上述 v2 contract。在 Markdown 中将空 related array 渲染为 `None`，同时在 JSON 中保留 `[]`。
- `Propose Use` 必须说明 atom 通过 Phase 3/4 后，应如何进入 proposal、spec、design、task、evidence、non-goal 或 preserve constraint；内容必须与 candidate artifact projection 一致。
- `Evidence Need` 必须列出后续预期 proof type，例如 `unit`、`contract`、`integration`、`worker`、`browser-e2e`、`visual`、`fixture`、`manual` 或 `none`。

### source anchor 表

每个 source atom file 还必须包含 supporting source anchor：

| Source Document | Anchor | Lines | Source Phrase | Candidate Status | Source Atom IDs | Candidate Owner Changes | Roles | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

source anchor 可以支撑一个或多个 source atom ID。anchor title 主要用于人工导航，应使用简洁的 semantic title；不得使用 `A01` 等 local numbering prefix。

## Mapping 角色

每个 atom mapping 记录一个或多个 role：

- `primary`
- `modified`
- `preserve`
- `verification`
- `acceptance`
- `non-goal`
- `dependency`
- `later-expansion`
- `future-compatibility`
- `reference`
- `superseded-by`
- `conflict`

在 Phase 1 framework 中，不得将 `preserve`、`dependency`、`future-compatibility` 或 `reference` 视为 direct Capability advancement。Phase 5 根据规范化 atom index 和 Phase 4 source-window semantic profile 决定 final advancement。

## Phase 2 索引与报告

所有 source-extraction subagent 返回后，本节由 fresh Phase 2 index/report subagent 负责。main agent 应对这些 output 执行 interface check，不得自行合成。

`phase-works/phase-2/source-obligation-atoms/index.md` 必须包含：

| Source Document | Work Queue Batch | Canonical Owner | Source Atom File | Read Status | Atom Candidates | Candidate Artifact Projection Summary | Candidate Capability Impact Summary | Contextual Candidates | Unassigned Atoms | Candidate New Boundaries | Remainder Notes | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

`phase-works/phase-2/phase-2-agent-report.md` 必须包含：

简短的 `Index/Report Generation` section，列出 fresh aggregation subagent、它读取的 input、执行的 read-only check、写入的 output 和所有 blocker。

| Batch | Source Documents | Line Counts | Extraction Mode | Canonical Owner | Work Queue Rationale | Extraction Status |
| --- | --- | --- | --- | --- | --- | --- |

| Batch | Source Documents | Source Atom Files | Subagent Status | Docs Read Full | Atom Candidates | Candidate Artifact Projection Summary | Candidate Capability Impact Summary | Contextual Candidates | Unassigned Atoms | Duplicate Risks | Candidate New Boundaries | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

此处不得包含 global coverage statistic。Phase 3 负责 semantic coverage closure、duplicate resolution、global uniqueness 和 final ownership。

## 质量门禁

Phase 2 结束前：

- 确认 `phase-works/phase-2/source-obligation-atoms/work-queue.md` 存在，且每份 `Read Status: read-full` manifest source document 恰好列出一次。
- 确认 work queue 只包含 batching rationale，不包含 atom extraction、coverage judgment 或 no-obligation conclusion。
- 确认每份 `Read Status: read-full` manifest source document 都恰好有一个 canonical `phase-works/phase-2/source-obligation-atoms/<source>.atoms.json` file 和一个 rendered `.atoms.md` mirror。
- 确认 rendered mirror 与 `scripts/render_source_aligned_orchestrate.py` output 相等；任何 drift 都必须通过 JSON repair 或重新渲染解决。
- 确认每份 source document 恰好有一个 canonical extraction owner，并在 work queue 和 Phase 2 report 中列出。
- 确认 extraction subagent 完成后，`phase-works/phase-2/source-obligation-atoms/index.md` 和 `phase-works/phase-2/phase-2-agent-report.md` 由 fresh Phase 2 index/report subagent 生成。
- 确认 Phase 2 index/report subagent 未编辑 source atom file、提取新 atom、执行 global duplicate resolution、决定 final ownership、闭合 semantic coverage 或读取 Phase 3/Phase 4/Phase 5 output。
- 确认每个 source atom file 都声明 source document 已完整阅读。
- 确认每个 source atom file 都包含 source section inventory、obligation atom candidate ledger、source anchor table、ownership ambiguity note、candidate missing plan boundary 和 blocker。
- 确认每个 source atom ledger 行都有非空 `Candidate Artifact Projection`，且没有 direct candidate 仅因 direct 就被假定为 `spec-requirement`。
- 确认每行都有 v2 candidate Capability field；`new` / `modified` 只出现在具有 target 的 `spec-requirement` / `spec-guard` 行，`none` 只与 target `none` 配对，`unresolved` 具有 rationale。
- 确认每个 direct `design-obligation` / `verification-obligation` 行保持 direct，并使用 `Candidate Capability Impact: none` 和 `Candidate Target Capability: none`。
- 确认 `Candidate Related Capabilities` 是唯一的 source-explicit array，排除 target，默认为空，并且绝不替代 target 或计入 candidate advancement。
- 确认 `candidate-new-capability` 只出现在 impact 为 `new` 的 `spec-requirement` / `spec-guard` 行。
- 确认 UI 和 flow document 使用上述 mandatory extraction rule 完成分解；不允许 broad "page detail" compression。
- 确认每个 atom 和 anchor 都具有 `L<start>-L<end>` 格式的规范化 `Lines` 值。
- 确认 candidate Change mapping 和 capability-impact metadata 明确标为 candidate 而非 final，且没有 Capability field 被视为 co-ownership。
- 确认 Phase 2 report 列出 unassigned、candidate-new-change、candidate-new-capability、duplicate-candidate、unresolved-conflict 和 unclassified 行。
- 确认 Phase 2 只生成或重写当前 Phase 2 output。
- 确认每项 Phase 2 artifact 都通过 Artifact Language Gate。

final reply 应为简短中文 report，包含 work queue batch、已提取的 source document、已写入的 source atom file、Phase 2 index/report subagent status、找到的 atom candidate、unassigned atom、candidate new boundary、duplicate risk、unresolved conflict、language-gate result 和 blocker。
