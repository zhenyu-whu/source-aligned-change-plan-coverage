# Change/Capability Framework 与 Delivery Sequence 共享原则

本文件是 Phase 1 初次生成 framework 与 Phase 5 最终复审/refit、dependency proof和roadmap selection的唯一语义标准。两阶段不得复制、改写或另建第二套 gate。

## 核心模型

- Capability 是可跨 Change 演进的稳定 behavior/spec boundary，回答“哪类持久 normative behavior 被放在一起维护”。
- Change 是有期限、可独立决策、验收和归档的 outcome slice，回答“为了一个什么 intent，独立改变并交付什么结果”。
- Capability 与 Change 多对多；一个 Change 可以推进多个 Capability，一个 Capability 可以被多个 Change 增量推进。
- 使用 `Capability-first、Outcome-sliced、Sequence-independent`：先建立稳定 Capability topology，再隐藏 Capability 名称，独立按 outcome、cohesion、acceptance、prefix utility和真实dependency切分及排序Change。
- Capability topology不是WBS、依赖图或建设顺序。Capability的基础性、复用范围、名称、首次出现或被多少Change使用，都不得形成顺序。
- 一个Capability无需在消费者之前完整建立；首个适用Change只推进当前outcome安全成立所需的最小normative slice，后续Change继续演进。
- Obligation evidence用于验证和调整framework与roadmap，不得从atom/GA数量、table形状或重复evidence数量推断boundary或order。

## Capability gate

每个Capability必须同时通过：

1. **Domain Basis**：基于稳定feature area、component contract或bounded context，而不是临时实现目录。
2. **Purpose**：隐藏Change名称后，仍能用一句话说明该spec规定什么持久行为。
3. **Behavior-first**：至少拥有一组可写成normative requirement/scenario的行为；只有design、test或task时不建Capability。
4. **Cohesion**：候选行为共享同一语义主体、责任、owner或invariant。
5. **Owns / Excludes**：明确拥有与不拥有的行为，相邻Capability不争夺同一normative clause。
6. **Implementation-substitution**：替换内部class、module、table、provider或部署方式后，Purpose与contract仍成立。
7. **Archive Durability**：隐藏roadmap后仍可独立阅读，不是one-Change alias、phase/version label或临时实现名。
8. **Delta Feasibility**：Change–Capability edge能落成具体requirement/scenario delta；implementation-only内容不建立edge。

`module`、`table`、`page`、`component`、`provider`、`deployment`是implementation-leakage signal，不是绝对黑名单；source明确规定的稳定component/interface contract可以成为Capability，但这仍不赋予其任何交付顺序。

## Change gate

每个Change必须同时通过：

1. **One-intent**：用一句话说明本次改变的目的与结果。
2. **Scope Cohesion**：所有范围服务同一intent，没有可独立批准的“顺便再做”。
3. **Independent Decision/Archive**：可以独立批准、推迟、实现、验证、完成和archive；完成不能只表示“未来Change现在可以开始”。
4. **Indivisibility**：拆分不会破坏当前暴露的同一transaction、invariant、protocol、security/consistency boundary或compatibility contract，也不会产生虚假half-state。
5. **Acceptance**：存在source-backed、具体、可观察或可验证的完成证据。
6. **Implementation-readiness**：范围足够聚焦，可由一次focused `openspec-apply-change` pass合理推进。
7. **Prefix Utility**：隐藏全部未来Change后，本Change仍使当前roadmap prefix进入新的、连贯、可部署且可验证的产品或系统状态。
8. **Consumer Closure**：本Change引入的substrate、contract、guard或抽象已在同一Change或当前prefix被真实消费；除合法foundation外，不留下只供未来Change使用的dormant substrate。

拆分只在子集具有不同intent，或可独立批准、推迟、实现、验收和archive，且各archive state都真实连贯时成立。

合并在以下任一情形成立：

- 拆分会破坏同一transaction/invariant/protocol/security/compatibility truth；
- 任一侧无法独立验收或产生source不支持的half-state；
- 候选子集只为另一个Change准备enabler/guard，且不能独立改善当前baseline；
- 将所需最小enabler/guard纳入consumer后仍可保持focused implementation。

共享infrastructure、相同团队、相同Capability、相邻页面、最终架构层级或table形状都不足以作为合并或排序理由。

## Behavior completeness profile

业务行为类Change在boundary确定后使用以下profile检查完整性，不使用它机械生成Change：

```text
trigger/context -> normative behavior -> observable outcome or invariant
-> important exception/error semantics -> acceptance evidence
```

- failure/recovery只有source明确要求或当前outcome真实成立所必需时才进入。
- acceptance evidence是完成证明，不与runtime behavior混为同一个obligation。
- architecture、performance、migration、tooling或纯内部implementation Change只有在改善当前baseline的可部署性、性能、可靠性、迁移、合规或运维结果时，才可使用相应engineering outcome。
- 仅有空应用启动、接口可调用、内部边界测试或“后续可复用”不构成普通Change的Prefix Utility；它们只能进入合法foundation或首个consumer。

## Source delivery semantics

Phase 2 source atom与Phase 3 gap atom只在source明示时记录以下`delivery-directives[]`：

- `milestone-scope`：明确把行为纳入某个阶段、版本、里程碑或当前交付目标。
- `explicit-precedence`：明确规定某结果必须在另一结果之前、之后或已存在。
- `explicit-deferred`：明确说明某行为不阻塞当前目标、稍后交付或当前排除。

规则：

- 空数组表示source未明示交付时序。
- steady-state architecture、security invariant、component layering、调用关系、数据流、复用关系或实现常识不得自动成为directive。
- 同一occurrence可以拥有多个不重复directive；必须由Phase 2/3 reviewer在freeze前核对。
- Phase 5必须为每个非空directive occurrence建立唯一terminal resolution。
- 显式milestone、precedence与deferred scope优先于AI推断的roadmap heuristic；若source自身冲突且无法裁决，workflow `blocked`。

## Foundation 与 foundation-like 内容

最多允许一个pre-delivery foundation Change，并且必须位于roadmap第一位。它必须：

- 缺少时首个真实outcome无法合理启动；
- 只包含zero-domain engineering substrate；
- 产生可验证、可复用的工程结果；
- 明确首个消费该substrate的outcome Change；
- 不声明硬依赖，也不建立任何Change-Capability advancement edge。

domain schema、entity、command、policy、user-facing API、business worker、identity/authorization、privacy、recovery、delivery、export、history/versioning、observability等domain behavior不得进入foundation；普通technical enabler默认并入首个consumer Change。

任何主要完成条件是“使未来Change可以开始”的候选都必须接受foundation-like语义审查。非空technical/security/governance Capability edge、direct evidence或可独立运行的空骨架，均不能豁免该审查。

公开handoff仍以`capability-slices: []`机械标记foundation；该marker不是语义充分条件。除了通过语义审查的唯一首项，所有Change必须至少产生一个direct spec/guard advancement edge并通过Prefix Utility与Consumer Closure。Phase 1、Phase 5及公开handoff均不增加Change类型字段。

## Hard dependency gate

只有候选`A -> B`同时满足以下四项，才能成为roadmap hard dependency：

1. **Independent predecessor outcome**：A在当前baseline上自身形成可部署、可验收、可archive的结果。
2. **Stable outcome consumption**：B消费A已经完成的稳定外部或normative outcome，不只是内部module、table、schema、service、runtime slot或代码复用。
3. **Co-delivery rejection**：把A的最小必要部分纳入B后，B仍无法保持真实、focused且安全的Change；必须写明原因。
4. **Evidence necessity**：source显式precedence或B的acceptance truth证明A必须先完成；只写“后续都需要”“先建立更稳妥”不成立。

下列关系不得成为hard dependency：

- package/import/build/schema/table/database/service/API/UI/test等实现层先后；
- shared infrastructure、未来复用、团队分工、readiness或一般风险降低愿望；
- Capability之间的基础/高级关系；
- steady-state architecture中的调用、部署或数据流方向；
- 某行为必须受authorization/privacy/security/compatibility/consistency/data-integrity guard保护。

最后一类默认是co-delivery invariant：把当前行为安全成立所需的最小guard放入同一个Change。

## 排序原则

严格按以下顺序确定roadmap：

1. 先建立source delivery directive视图与目标milestone。
2. 隐藏Capability名称，按真实outcome生成Change并通过全部8项gate。
3. 为每个Change吸收当前outcome所需的最小runtime、data、security、compatibility与verification slice。
4. 只在Change均已形成后建立typed hard dependency edges，并逐条通过四项dependency gate。
5. 对hard dependency DAG执行拓扑排序。
6. 在当前eligible Change中依次优先：
   - source显式milestone/precedence/deferred约束；
   - 最薄、真实、可观察、可独立验收并可archive的端到端outcome；
   - 能尽早获得真实反馈或消除关键不确定性、同时仍通过Prefix Utility的outcome。
7. 每加入一个Change，重新检查整个prefix的可部署性、guard完整性、consumer closure与无dormant substrate。

典型`input preparation -> core result -> async/external integration -> richer projection -> hardening`只能作为同等eligible候选之间的heuristic，不得发明source未要求的Change，也不得按`database -> service -> API -> UI -> test`排序。

## Guard allocation

- 当前行为不可缺少的authorization、privacy、security、compatibility、consistency和data-integrity guard必须进入首次暴露该行为的同一个Change。
- “首次适用”表示同Change交付，不表示在其之前创建完整guard framework。
- 独立guard Change只有在它保护当前baseline中已经存在的运行表面，并且自身产生可测风险降低、合规或运营结果时成立。
- 共享security bounded context不意味着未来全部角色、策略或高风险能力不可增量切分；Indivisibility只保护当前暴露行为的最小完整安全边界。

## Change-Capability overlay

- 只有Change直接改变Capability normative behavior时才建立advancement edge。
- dependency、reuse、preserve、related-only、design-only、task-only和verification-only内容不推进Capability。
- Capability数量、名称、首次出现或矩阵列不得决定Change boundary或order。
- single-Capability Change和只由一个Change推进的Capability都可以合法存在；合法性只由上述gate决定。
- 非空overlay不构成Prefix Utility、Consumer Closure或非foundation-like的证明。

## 禁止的机械切分与排序

不得按以下内容生成或调整Change/Capability/order：

- source heading、page、table、document或目录结构；
- database、repository、service、API、UI、test等技术层；
- module、provider、queue、SDK或部署单元；
- Capability列、对角矩阵、同名alias、首次出现或复用数量；
- atom/GA数量、重复evidence数量或固定complexity threshold；
- “所有后续都会需要”“先打基础”“先把安全做完整”等没有dependency proof的抽象理由；
- 通过新增technical/security Capability edge把第二个foundation-like候选伪装成普通Change；
- 把steady-state architecture或guard obligation解释为显式交付顺序。
