# Phase 1：Capability-first、Sequence-independent 初始计划

Phase 1完整阅读用户指定的source document，先形成candidate Capability topology，再独立形成source delivery semantics、outcome-sliced Change与dependency hypothesis。该产物是供Phase 2–5验证和refit的framework hypothesis，不是requirement inventory、coverage结论或final plan。

Writer必须直接完整读取：

- `references/cross-phase-contract.md`
- `references/change-capability-framework-principles.md`
- 本文件
- `references/trace-sidecar-contract.md`

Change/Capability定义、8项Change gate、foundation-like审查、dependency proof、排序和overlay只以共享原则为准。

## 目标与边界

Phase 1只负责：

- 枚举并完整阅读用户指定source set中的每份source document；
- 建立coarse semantic landscape与当前baseline/目标milestone；
- 按共享原则推导candidate Capability topology；
- 单独建立coarse Source Delivery Semantics；
- 隐藏Capability名称，按source-backed outcome生成candidate Change；
- 把当前outcome所需的最小enabler与guard纳入同一个Change；
- 在Change已形成后证明hard dependency并检查每个roadmap prefix；
- 建立coarse Change-Capability advancement hypothesis；
- 编写`initial-framework.json`语义权威、确定性`initial-change-plan.md` mirror、source manifest、noncanonical report和control trace。

Phase 1不得：

- 提取、枚举、规范化或计数obligation atom；
- 创建atom ID、GA、line-level trace、coverage ledger或unique owner；
- 将coarse delivery semantics伪装为冻结`delivery-directives[]`；
- 从Capability、架构层级、复用、guard或实现常识推断hard dependency；
- 决定requirement-level operation或Capability-level`New|Modified`；
- 创建proposal、design、spec、task或verification artifact。

所有initial Change、Capability、advancement、dependency与order必须标为hypothesis；Phase 2–5可以根据完整冻结evidence调整。

## 输入权威

- 只使用用户指定的文档或目录作为production obligation与delivery semantics的source authority。
- 必须枚举并完整阅读每份有意义的source document；不得抽样或只浏览文件名。
- 除非用户明确纳入input，不读取或依赖现有OpenSpec spec/Change/archive，因此不得输出`New|Modified`。
- 无法安全完成full-source read时返回blocker，不得写成功态plan或trace。

## 产出

```text
phase-works/phase-1/
├── initial-framework.json
├── initial-change-plan.md  # 确定性 mirror
├── source-doc-manifest.md
├── phase-1-agent-report.md
├── phase-1-reviewer-report.md
└── phase-1-repair-report.md  # 仅发生repair时

trace/phase-1.trace.json
```

Phase 1不得创建或更新根`change-plan.md`。

`initial-framework.json`使用`source-aligned-initial-framework-v1`，是Phase 1唯一语义权威。`initial-change-plan.md`必须由renderer从当前JSON逐字节确定性生成，禁止手写或从Markdown恢复语义。两个artifact的path/digest与bounded review gate由`phase-1.trace.json`绑定；JSON以`phase: phase-1`、`role: initial-framework`、`authority: semantic`进入manifest，Markdown不进入manifest。Agent/reviewer/repair report是noncanonical流程证据。

## 规划方法

严格按以下顺序：

1. 枚举source set，完整阅读正文并写source manifest。
2. 建立coarse semantic landscape、current baseline与target milestone，不转写为atom ledger。
3. 使用Capability gate推导candidate Capability topology。
4. 单独建立Source Delivery Semantics，只登记source明示的milestone、precedence和deferred语义。
5. 隐藏Capability名称，从actor journey、system outcome、acceptance与显式milestone生成candidate Change。
6. 为每个Change吸收当前结果所需的最小runtime、data、security、compatibility与verification slice。
7. 对每个Change执行8项gate、foundation-like审查、Hide Future Consumers与Consumer Closure。
8. 只有Change均已形成后，才建立typed hard dependency edges；逐条证明predecessor outcome、stable consumption、co-delivery rejection与evidence necessity。
9. 对hard dependency DAG拓扑排序；eligible候选先遵循显式source directive，再选择最薄真实反馈或合法risk-retirement outcome。
10. 按顺序检查每个roadmap prefix的可部署性、guard完整性、consumer closure与无dormant substrate。
11. 最后使用overlay规则叠加Change与Capability。
12. 写入assumption、conflict、non-goal、deferred content和语言自检，并声明framework是hypothesis。
13. 原子写入`initial-framework.json`，运行`phase1-initial-framework` renderer生成mirror；不得先写Markdown再反向恢复JSON。

Coarse source hint只使用source path、heading、section、decision ID、route/page/object/API/command/entity/job/event等locator；不得包含line range、atom ID、GA或coverage status。

## 输出模板

### Source manifest

`source-doc-manifest.md`使用：

| Source Document | Read Status | Source Role | Coarse Topics / Paths | Notes |
| --- | --- | --- | --- | --- |

每份source恰好一行；成功态全部`read-full`。

### Initial framework v1

`initial-framework.json`顶层必须且只能包含：

```text
trace-schema
trace-contract-version
artifact-path
delivery-semantics[]
semantic-landscape[]
capabilities[]
outcome-threads[]
changes[]
dependency-edges[]
guard-links[]
change-order[]
overlay[]
foundation
assumptions[]
conflicts[]
non-goals[]
deferred[]
language-self-check
```

`artifact-path`指向repository-relative `phase-works/phase-1/initial-change-plan.md` mirror。

Delivery semantics row只含：

```text
source-backed-statement
delivery-directive
affected-outcome-thread-ids[]
planning-effect
source-hint
```

Directive只允许`explicit-deferred|explicit-precedence|milestone-scope|none`。`none`表示该source statement不产生顺序，不得把architecture、guard、layer或reuse自动写成directive。

Semantic landscape row只含`semantic-area`、`source-backed-understanding`、`planning-relevance`、`source-hints[]`，只作coarse synthesis，不拆成obligation。

Capability row只含：

```text
capability
purpose
owns
excludes
boundary-rationale
source-hints[]
```

Outcome thread row只含：

```text
outcome-thread-id
beneficiary
trigger
observable-result
acceptance-signal
primary
source-hints[]
```

至少一个outcome thread必须为`primary: true`。

Change row只含：

```text
change
intent
scope-in
scope-out
behavior-profile
realizes-outcome-thread-ids[]
usable-postcondition
consumer-closure
independent-archive
split-merge-judgment
source-hints[]
```

`behavior-profile`只含`trigger-context`、`normative-behavior`、`observable-outcome-invariant`、`important-exception-error-semantics`、`acceptance-evidence`。`consumer-closure`只含`mode`与`ref`；mode只允许`existing-baseline|foundation-first-outcome|same-change-outcome`。

Dependency edge row只含：

```text
dependency-id
prerequisite-change
dependent-change
kind
contract-id
produced-contract
consumed-contract
counterfactual-failure
co-delivery-rejection
source-hints[]
```

Kind只允许`behavior-availability|compatibility-contract|lifecycle-state|safety-invariant`。每条edge必须通过四项hard dependency gate，不能使用implementation layering、共享基础设施或未来复用代替稳定contract。

Guard link row只含`guard-link-id`、`guarding-change`、`guarded-outcome-thread-id`、`surface-state`、`source-hints[]`。Surface state只允许`existing|planned`；planned guard必须与该outcome的首个realizing Change共交付。

Overlay row只含`change`与`capability`，仅表达candidate direct advancement hypothesis。Phase 1不读取repository Capability baseline，因此不得保存`new|modified` impact；该impact只在Phase 5由terminal mapping与baseline推导。`foundation`为`null`或只含`change`、`first-consumer-change`、`source-hints[]`。Foundation必须是roadmap首项、紧邻first consumer、不realize outcome、使用`foundation-first-outcome` closure且无overlay。

`change-order[]`恰好覆盖全部Change。除可选foundation外，每个Change必须realize至少一个outcome thread、使用当前consumer closure并推进至少一个Capability。无foundation时首项必须realize primary outcome。

### Deterministic initial plan mirror

Renderer从JSON固定生成`initial-change-plan.md`的输入、semantic landscape、delivery semantics、Capability map、outcome threads、Change roadmap、foundation、overlay、风险检查与语言自检章节。Markdown只供人工阅读；任何repair必须先修改JSON，再完整重渲染并校验逐字节一致。不得直接编辑mirror，也不得从mirror恢复JSON。

## Bounded review gate

Writer先发布可校验JSON authority、Markdown mirror与`status: review-pending` trace；此时`review-gate.status`为`pending`且可以是`reviews: []`、`repairs: []`。main agent随后运行Phase 1 validator，再按`review-gates.md`执行最多三次fresh review、两次repair。只有最后validator与review均通过并把trace terminalize为`initial-plan-written`后才进入Phase 2。Manifest可在未完成generation中如实记录`phase-1: review-pending`，complete workflow只接受terminal `initial-plan-written`。

`phase-1.trace.json`使用`source-aligned-phase-1-trace-v4`。`review-gate`只包含：

- `status: pending|passed|blocked`
- `writer-id`
- `reviews[]`
- `repairs[]`

`phase-1.trace.json`顶层精确为`trace-schema`、`trace-contract-version`、`status`、`source-documents[]`、`initial-framework`、`initial-change-plan`与`review-gate`。顶层`status`只允许`review-pending|initial-plan-written|blocked`，并分别要求gate为`pending|passed|blocked`。两个artifact ref都只含`artifact-path`与`sha256`。

Review row只含`round`、`reviewer-id`、`validator-status`、`initial-framework-sha256`、`initial-change-plan-sha256`、固定顺序`semantic-checks[]`和`finding-fingerprints[]`。每个semantic check row只含`check`与`result: passed|failed`：

1. `capability-change-independence`
2. `source-delivery-semantics`
3. `prefix-utility`
4. `consumer-closure`
5. `hard-dependency-proof`
6. `guard-co-delivery`
7. `foundation-like-content`
8. `order-selection`
9. `overlay-directness`

Repair row只含`round`、`repair-writer-id`、`finding-fingerprints[]`、`before-initial-framework-sha256`和`after-initial-framework-sha256`。Repair只修改JSON authority，并在下一轮validator/review前完整重渲染mirror；每个review row同时绑定当轮JSON与mirror digest。

`pending`允许0..3条review与0..2条repair，且只能处于两种可恢复中间点：

- `reviews == repairs`：authority刚发布或刚完成repair，等待fresh review；若非零，最后repair的after digest必须绑定当前JSON。
- `reviews == repairs + 1`：刚完成review，等待repair或terminalization；最后review的JSON与mirror digest必须绑定当前artifact。

任意两轮review之间必须恰好存在对应repair。`passed`与通常的`blocked`都要求`reviews == repairs + 1`且至少一轮review；只有触发立即blocked的terminal no-op repair允许blocked两者等长。Review最多三行、repair最多两行；repeated fingerprint、JSON no-op repair、mirror drift、身份复用或第三次review不通过立即blocked，禁止以`pending`继续或越过forced block追加repair/review。

## Phase报告与完成条件

`phase-1-agent-report.md`简要列出已读source、artifact path、baseline/milestone、assumption/conflict、candidate Capability/Change/dependency数量、Phase边界、语言门禁和blocker。

成功态必须：

- source set完整读取；
- initial framework符合exact schema与共享原则，mirror可从JSON逐字节重渲染；
- trace使用v4且source/authority/mirror digest与bounded review gate有效；
- validator通过，review gate为`passed`；
- 任何非v7 generation都未被修改、复用或迁移。

若在initial framework与review gate可建立之前无法完整读取source，只记录noncanonical orchestration stop并停止。已有可校验authority后gate无法满足时使用canonical`blocked`并停止。
