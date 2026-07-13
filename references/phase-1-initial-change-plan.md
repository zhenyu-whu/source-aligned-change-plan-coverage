# Phase 1：Capability-first 初始 Change 框架

Phase 1 完整阅读用户指定的 source document，先形成稳定的 candidate Capability topology，再按 source 支撑的产品/系统结果与交付依赖形成初始 Change roadmap。该产物是供 Phase 2–5 检验和 refit 的 framework hypothesis，不是 requirement inventory、obligation atom index、coverage 结论或 final plan。

执行前，writer 必须直接完整读取 `references/cross-phase-contract.md` 和 `references/trace-sidecar-contract.md`；prompt 摘要、转述或继承上下文不能替代直接读取。

## 目录

- 目标与边界
- 输入权威
- 产出
- 核心模型
- 规划方法
- Capability 原则
- Change 原则
- 排序原则
- Source evidence hint
- 输出模板
- Phase 报告与完成条件

## 目标与边界

Phase 1 只负责：

- 枚举并完整阅读用户指定 source set 中的每份 source document。
- 建立 coarse semantic landscape：actor、长期 domain object、lifecycle、responsibility、contract、constraint、architecture decision 和 major outcome。
- 先推导 candidate Capability topology，说明每个 Capability 的 Purpose、Owns、Excludes 和边界理由。
- 再从 source-backed outcome、行为成熟度和不可绕过的依赖切分、排序 candidate Change。
- 将 Change 与 Capability 叠加为 coarse、non-canonical advancement hypothesis。
- 写入初始框架、source manifest、Phase report 和 canonical trace。

Phase 1 明确不负责：

- 不提取、枚举、规范化或计数 semantic obligation atom。
- 不创建 atom ID、line-level trace、coverage ledger、unique obligation owner 或 exhaustive completeness claim。
- 不决定 requirement-level `ADDED` / `MODIFIED` / `REMOVED` / `RENAMED` operation。
- 不按 roadmap 首次出现位置猜测 OpenSpec Capability relation `New` / `Modified`。
- 不创建 proposal、design、spec、task 或 verification artifact。

“不提取 obligation”不等于“不做语义分析”。writer 必须理解 source 的领域结构、主要结果和约束，才能形成有依据的 Capability 与 Change hypothesis；但不得把这种 coarse 理解伪装成逐项 obligation coverage。

所有初始 Change、Capability、advancement、source hint 和排序必须明确标为 hypothesis。Phase 2–5 可以根据 obligation atom 和 source-window evidence 调整、拆分、合并、重命名或重排。

## 输入权威

- 只使用用户指定的文档或目录作为 production obligation 的 source authority。
- 生成框架前，必须枚举并完整阅读 source set 中每份有意义的 source document；不得抽样、仅浏览文件名或跳过正文。
- 指定目录中的非 source artifact 可以在 manifest 中标记为 `non-source-artifact`，但有意义的 source document 不得归入此类。
- 除非用户明确纳入 input，不得读取或依赖当前 `openspec/`、现有 spec、现有 Change、archive history 或 custom artifact。Phase 1 因此不得输出 OpenSpec `New` / `Modified` 结论。
- 如果无法安全完成 full-source read，返回 blocker。不得创建或更新成功态 `initial-change-plan.md`、`initial-plan-written` trace 或其他完成声明。

## 产出

成功时只写入以下 Phase 1 artifact：

```text
openspec/orchestrate/phase-works/phase-1/
├── initial-change-plan.md
├── source-doc-manifest.md
└── phase-1-agent-report.md

openspec/orchestrate/trace/phase-1.trace.json
```

Phase 1 不得创建或更新根 `openspec/orchestrate/change-plan.md`。

writer 完成后返回 main agent。validator、reviewer、repair 和状态推进由 main agent 按 `references/reviewer-repair-loop.md` 执行；Phase 1 writer 不得自行 reviewer、repair 或推进工作流。

## Artifact 语言门禁

继承 `references/cross-phase-contract.md` 的 Artifact Language Gate。assumption、conflict、semantic landscape、Capability Purpose/Owns/Excludes、Change intent/outcome、roadmap value、risk-check answer、source-evidence hint、archive-readiness note 和 report 都必须使用简体中文。

## 核心模型

Phase 1 使用两个正交坐标：

- Capability 是稳定的 spec/domain topology，回答“哪类持久 normative behavior 被放在一起维护”。
- Change 是有期限的 delivery/evolution slice，回答“本次为了一个什么 intent，独立改变并交付什么结果”。

两者构成多对多关系：一个 Change 可以直接推进多个 Capability；一个 Capability 可以被多个 Change 持续演进；没有 spec-level behavior delta 的 Change 可以不推进任何 Capability。Capability 数量、名称或列布局不得决定 Change boundary。

Phase 1 的总原则是：`Capability-first、Outcome-sliced、Obligation-later`。

## 规划方法

严格按以下顺序形成初始框架：

1. 枚举 source set，完整阅读正文，并写入 source manifest。
2. 建立 coarse semantic landscape，只记录 actor、domain object、lifecycle、responsibility、contract、constraint、architecture decision 和 major outcome；不得转写为 atom ledger。
3. 从长期 Purpose 与 normative behavior grouping 推导 candidate Capability topology；为每个 candidate 写明 Owns、Excludes、相邻边界和 coarse source hint。
4. 根据 source 中的 outcome、state transition、contract dependency 和 acceptance dependency 建立 behavior-maturity / hard-dependency graph。典型项目推进顺序只能作为同等候选之间的 ordering heuristic，不得发明 source 未要求的工作。
5. 独立于 Capability 列表，围绕 source-backed intent 与 outcome 生成 candidate Change；依次应用 one-intent、scope-cohesion、independent-decision/archive、indivisibility、acceptance 和 implementation-readiness gate。
6. 将 candidate Change 叠加到 candidate Capability：只有 coarse analysis 判断 Change 将直接改变该 Capability 的 normative behavior 时才建立 advancement edge；dependency、reuse、preserve、related-only 或 implementation-only 内容不建立 edge。
7. 先按不可绕过的 hard-dependency DAG 排序；在所有已满足 hard dependency 的 Change 中，优先最薄、真实、可观察、可独立验收并可 archive 的 outcome。
8. 写入 coarse、non-canonical source hint、assumption、conflict、non-goal、deferred content、边界理由和风险检查结果，并明确 Phase 2–5 需要用 atom/source-window evidence refit。

不得使用以下替代流程：

- 先列 Capability 名称，再为每列机械创建一个同名 Change。
- 先按技术层拆成 database -> repository -> service -> API -> UI -> test。
- 先把每个 source heading、page、table、component、provider 或 deployment unit 变成 Capability/Change。
- 在 Phase 1 提前执行 obligation atomization、逐行 coverage 或 final ownership assignment。

## Capability 原则

Capability 是 `openspec/specs/<id>/spec.md` 的 candidate logical domain boundary：它以一个清晰 Purpose 聚合内聚、可验证的 normative behavior，并在任一单独 Change archive 后仍具有独立意义。组织依据可以是 feature area、stable component 或 bounded context；只有纯实现构件且没有独立行为契约时才应拒绝。

每个 candidate Capability 必须通过：

1. Domain Basis：明确说明它基于 feature area、stable component 或 bounded context 中的哪一种稳定 grouping。
2. Purpose：不引用 Change 名称，也能用一句话说明该 spec 规定什么持久行为。
3. Behavior-first：source 至少支持一组可写成 normative requirement/scenario 的行为；只有 design、test 或 implementation 内容时不建 Capability。
4. Implementation-substitution：替换内部 class、module、table、provider 或部署方式后，Purpose 与 contract 仍成立；若 component 本身就是稳定、可观察的公开/系统 contract，可以保留。
5. Cohesion：候选行为共享同一语义主体、责任、owner 或 invariant；不得使用 `platform-core`、`misc-management` 等宽泛垃圾桶聚合。
6. Owns / Excludes：明确拥有与不拥有的行为，相邻 Capability 不争夺同一 normative clause。
7. Archive Durability：隐藏 Change 名称和 roadmap 后，Capability 仍可独立阅读，而不是 one-Change alias、phase/version label 或临时实现名。
8. Delta Feasibility：后续若建立 Change–Capability edge，该 edge 应能落成具体 requirement/scenario delta；只有 implementation/task/test 内容时不建立 edge。

`module`、`table`、`page`、`component`、`provider`、`deployment` 等词是 implementation-leakage warning signal，不是绝对黑名单。若名称只表达当前代码目录、类、表或可替换 adapter，应重命名或拒绝；若 source 明确规定稳定 component/interface contract，则可以成为合法 Capability。

Capability ID 使用 source/team 的稳定 domain vocabulary 和英文 kebab-case。不得使用 Change action alias、phase/version、临时实现选择、宽泛垃圾桶或单一交互场景作为 ID。

## Change 原则

一个 Change 是围绕一个清晰、source-backed intent 的最小独立决策/归档单元，也是保持交付内聚性的最大实现单元。它必须能形成自洽 proposal，并可独立 review、implement、verify、complete 和 archive。

每个 candidate Change 必须通过：

1. One-intent Test：能否用一句话说明本次改变的目的与结果？
2. Scope Cohesion Test：所有范围是否服务同一 intent，没有“顺便再做”的独立结果？
3. Independent Decision/Archive Test：该单元能否被独立批准、推迟、完成、验证和 archive，并在历史中形成清晰 why/what？
4. Indivisibility Test：若拆分，是否会破坏同一 transaction、invariant、protocol、security/consistency boundary、compatibility contract 或产生无意义半状态？
5. Acceptance Test：是否存在 source-backed、具体且可观察/可验证的完成证据？
6. Implementation-readiness Test：范围是否足够聚焦，可由后续一次 focused `openspec-apply-change` pass 合理推进？

拆分条件：子集具有不同 intent，或可以在不依赖其余内容的情况下独立批准、推迟、实现、验收和 archive，且拆分后的每个 archive state 都保持真实、连贯。

合并条件：拆分会破坏同一 transaction/invariant/protocol/security/compatibility truth，使任一侧无法独立验收，或产生 source 不支持的 stub/half-state。共享 infrastructure、相同团队、相同 Capability、相邻页面或矩阵外观都不足以作为合并理由。

业务行为类 Change 在 boundary 确定后使用以下 behavior completeness profile 做完整性检查，而不是用它生成 Change：

```text
trigger/context -> normative behavior -> observable outcome or invariant
-> important exception/error semantics -> acceptance evidence
```

- `system fact` 只是 observable outcome/invariant 的一种可能形式，不是必填项。
- failure recovery 只有 source 明确要求或当前 intent 的真实完成条件需要时才进入该 Change；不得为填模板发明恢复流程。
- acceptance evidence 是完成证明；不得与 runtime behavior 混为同一个 obligation。
- architecture、performance、migration、tooling、documentation 或纯内部 implementation Change 可以使用与其 intent 相符的 system/engineering outcome，不强制伪造 user entry、持久 fact 或 user-facing projection。

### Foundation 例外

最多允许一个 pre-delivery foundation candidate，并将它视为 roadmap anti-bloat 例外，而不是所有 OpenSpec Change 的通用定义。它必须同时满足：

- 缺少它时，首个真实、可验收 outcome 无法合理启动。
- 只包含 zero-domain engineering substrate，例如目录、根脚本、lint/typecheck/test harness、环境校验、依赖 manifest、migration tooling、空 smoke entry 或无 domain 语义的 adapter seam。
- 产生稳定、可复用且可通过 runtime/integration proof 验证的工程结果。
- 明确指出首个消费该 substrate 的 outcome Change。

Foundation 不得吸收 domain schema、entity、command、policy、repository、user-facing API、domain worker/state machine、business queue/event、identity/authorization/tenancy、entitlement、accounting、delivery、export、history/versioning、privacy、recovery、responsive、design-system、observability 或其他 workflow-specific behavior。纯 technical enabler 默认并入首个 consumer Change 的 design/tasks；只有存在独立 deployment、risk、rollback、ownership 或 review boundary 时，才可保留为独立 Change。

## 排序原则

排序分两层：

1. Hard dependency：先满足 source-backed、不可绕过的 runtime/behavior prerequisite，并保持 DAG 无环。
2. Outcome maturity：在当前所有 eligible Change 中，优先最薄、真实、可观察、可独立验收和 archive 的结果。

典型顺序可以是 input preparation -> core result/state transition -> async/external integration -> richer projection -> hardening/delivery/operations，但它只是 source-constrained heuristic，不是固定模板。不得因“典型项目通常如此”发明 Change，也不得将技术层级当作 roadmap。

当前行为不可缺少的 authorization、privacy、consistency、security、compatibility 和 data-integrity constraint 必须进入首个适用 Change；不得为了形成漂亮阶段，把当前真实行为所必需的 guard 推迟成未来治理 Change。

## Source evidence hint

每个 Capability 和 Change 只添加足以解释 boundary、intent、outcome 或 order 的 coarse locator，例如 source path、heading、section number、decision ID、route/page/object name、API、command、entity、job、event、asset 或 environment。

Source hint 必须保持简短且 non-canonical。不得包含 line range、atom ID、atom/evidence count、coverage status、完整 requirement 枚举、待后续处理清单或 completeness claim。

## 输出模板

### Source manifest

`openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md` 使用：

| Source Document | Read Status | Source Role | Coarse Topics / Paths | Notes |
| --- | --- | --- | --- | --- |

规则：

- 每份用户指定的 source document 恰好一行。
- 成功态中，每份 source document 的 `Read Status` 必须为 `read-full`。
- 只有确实不属于 source authority 的文件才可标记为 `non-source-artifact`。
- 不得添加 coverage status、atom count 或 line-range coverage。

### Initial change plan

`openspec/orchestrate/phase-works/phase-1/initial-change-plan.md` 必须按顺序包含以下二级 heading。

#### `## 输入`

- 已指定并完整阅读的 source document。
- 用户提供的 non-source candidate plan，或 `无`。
- assumption、conflict 和 blocker；成功态 blocker 必须为 `无`。

不得列出 source set 内“可能相关但未阅读”的 document。无法判定的有意义文档必须先读取或阻塞。

#### `## Source Semantic Landscape`

| Semantic Area | Coarse Source-backed Understanding | Planning Relevance | Source Hint |
| --- | --- | --- | --- |

只记录 actor、domain object/lifecycle、responsibility、contract、constraint、architecture decision 和 major outcome 的 coarse synthesis。不得拆成 obligation 行，不得声称 exhaustive coverage。

#### `## Capability Map`

| Candidate Capability | Grouping Basis | Purpose | Owns | Excludes | Coarse Source Hint | Boundary Rationale |
| --- | --- | --- | --- | --- | --- | --- |

- Candidate Capability 使用反引号包裹的英文 kebab-case ID。
- Purpose、Owns 和 Excludes 描述持久 normative behavior，不得描述临时 implementation module。
- Boundary Rationale 必须说明 Purpose cohesion、implementation-substitution 与 archive durability。
- 没有业务 Capability delta 时，保留 heading 并写 `无 candidate business Capability`，不得输出空表或发明 technical Capability。

#### `## Change 切分原则`

- 写明实际采用的 source-backed outcome slicing principle。
- 写明被拒绝的 slicing approach 及原因。
- 明确说明 Capability topology 先形成，但 Change boundary 独立通过 one-intent / cohesion / independent archive / indivisibility / acceptance gate 决定。
- 明确当前 boundary、advancement 与 order 均为 hypothesis，Phase 1 未执行 obligation extraction。

#### `## Change Roadmap`

每个 Change 使用以下结构：

- Change 名称：英文 kebab-case slug。
- 单一 intent：一句话描述 why/what。
- source-backed outcome：本 Change 完成后新增或改变的可观察/可验证结果。
- 来源 evidence hint：coarse、non-canonical locator。
- 范围内：
- 范围外：
- behavior completeness profile：
  - trigger/context：
  - normative behavior：
  - observable outcome / invariant：
  - important exception / error semantics：source 未规定且当前 intent 不要求时写 `未由 source 指定`。
  - acceptance evidence：
- 硬依赖：只列不可绕过的 runtime/behavior prerequisite，或 `无`。
- 排序理由：说明 hard dependency 与 outcome maturity；不得只写“典型项目顺序”。
- 独立完成与归档：说明为何可独立批准、实现、验收和 archive。
- 拆分/合并判断：列出最接近的替代 boundary，并说明为何保留当前粒度。

#### `## Change-Capability Overlay`

使用稀疏 edge table 作为 Phase 1 唯一 advancement authority：

| Change | Candidate Capability | Roadmap Role | Direct Behavior Delta Hypothesis | Coarse Source Hint |
| --- | --- | --- | --- | --- |

- `Roadmap Role` 只能使用 `first-advancement` 或 `later-advancement`；它只表示本计划中的成熟顺序，不等于 OpenSpec `New` / `Modified`。
- 只有 coarse analysis 判断 Change 直接改变 Capability normative behavior 时才添加 edge。
- dependency、reuse、preserve、related-only、design-only、task-only 或 verification-only 内容不添加 edge。
- 没有 spec-level advancement 时，保留 heading 并写 `无 candidate Capability advancement`。
- 宽 matrix 可以作为从 edge table 派生的 reviewer view，但不得成为独立 relation authority，也不得为形成对角线而改写 Change/Capability boundary。

#### `## Phase 1 风险检查`

必须逐项回答：

1. Source 完整性：manifest 是否覆盖 source set，且每份 source document 均为 `read-full`？
2. Phase 边界：是否只形成 coarse semantic landscape，而未提取 obligation、atom、line range、coverage、unique owner 或 final artifact operation？
3. Capability 稳定性：每个 candidate 是否通过 Purpose、Behavior-first、Implementation-substitution、Owns/Excludes 和 Archive Durability gate？
4. Change 粒度：每个 candidate 是否通过 One-intent、Scope Cohesion、Independent Decision/Archive、Indivisibility、Acceptance 和 Implementation-readiness gate？
5. Behavior 完整性：profile 是否只表达 source-backed outcome/invariant、重要异常和 acceptance evidence，没有强制发明 fact、projection 或 recovery？
6. Overlay 合法性：edge 是否只表达 direct behavior advancement，并使用 roadmap-neutral `first-advancement` / `later-advancement`？
7. Roadmap 顺序：是否先满足 hard dependency，再选择最薄可验收 outcome，没有按技术层排序或提前安排未来 concern？
8. Foundation 合法性：是否至多一个、严格 zero-domain，并明确首个 consumer；纯 enabler 是否默认并入 consumer？
9. Hide Capability Names：隐藏 Capability Map 后，Change 仍能仅由 source-backed intent、outcome、cohesion 和 dependency 解释吗？
10. Hide Roadmap：隐藏 Change Roadmap 后，Capability 仍具有稳定 Purpose、Owns/Excludes 和独立 archive 后意义吗？
11. Post-mapping audit：overlay 是否自然反映多对多关系，而不是被设计成一 Change 一 Capability 的机械对角线？

#### `## Phase 1 语言自检`

确认忽略固定 heading、field label、enum/status、ID、path、command、code/API/DB/package symbol、filename 和精确 source quote 后，agent 编写的解释内容均为简体中文。

## Phase 报告与完成条件

`openspec/orchestrate/phase-works/phase-1/phase-1-agent-report.md` 必须简要列出：

- 已完整阅读的 source document。
- initial framework 和 source manifest path。
- candidate plan 的 assumption 处理结果。
- candidate Capability 数量、candidate Change 数量和 coarse advancement edge 数量；这些数量不得解释为 obligation coverage。
- 值得注意的 conflict 或 `无`。
- 确认未执行 obligation extraction，未创建 prohibited Phase 1 artifact。
- 确认 artifact 通过语言门禁。
- blocker，或 `无`。

Phase 1 只有同时满足以下条件才可写入 `trace/phase-1.trace.json`，并使用 `status: initial-plan-written`：

- source set 已完整读取，manifest 与 canonical trace 一致。
- `initial-change-plan.md` 存在并符合固定输出模板。
- trace 使用 `source-aligned-phase-1-trace-v2`，且 plan path/digest 当前有效。
- agent report 的 blocker 为 `无`。

任一条件不满足时不得声明 Phase 1 完成。成功 output 返回 main agent 后，按共享 contract 运行 validator 和 independent reviewer。
