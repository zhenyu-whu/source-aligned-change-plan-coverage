# Change/Capability Framework 共享原则

本文件是 Phase 1 初次生成 framework 与 Phase 5 复审/refit framework 的唯一边界标准。两阶段不得复制、改写或另建第二套 Change/Capability gate。

## 核心模型

- Capability 是可跨 Change 演进的稳定 behavior/spec boundary，回答“哪类持久 normative behavior 被放在一起维护”。
- Change 是有期限、可独立决策、验收和归档的 outcome slice，回答“为了一个什么 intent，独立改变并交付什么结果”。
- Capability 与 Change 多对多；一个 Change 可以推进多个 Capability，一个 Capability 可以被多个 Change 持续演进。
- 使用 `Capability-first、Outcome-sliced`：先建立稳定 Capability topology，再独立按 outcome、cohesion、acceptance 和 dependency 切分 Change。
- obligation evidence 用于验证和调整 framework，不得从 atom/GA 数量、表格形状或重复 evidence 数量推断 boundary。

## Capability gate

每个 Capability 必须同时通过：

1. **Domain Basis**：基于稳定 feature area、component contract 或 bounded context，而不是临时实现目录。
2. **Purpose**：隐藏 Change 名称后，仍能用一句话说明该 spec 规定什么持久行为。
3. **Behavior-first**：至少拥有一组可写成 normative requirement/scenario 的行为；只有 design、test 或 task 时不建 Capability。
4. **Cohesion**：候选行为共享同一语义主体、责任、owner 或 invariant。
5. **Owns / Excludes**：明确拥有与不拥有的行为，相邻 Capability 不争夺同一 normative clause。
6. **Implementation-substitution**：替换内部 class、module、table、provider 或部署方式后，Purpose 与 contract 仍成立。
7. **Archive Durability**：隐藏 roadmap 后仍可独立阅读，不是 one-Change alias、phase/version label 或临时实现名。
8. **Delta Feasibility**：Change–Capability edge 能落成具体 requirement/scenario delta；implementation-only 内容不建立 edge。

`module`、`table`、`page`、`component`、`provider`、`deployment` 是 implementation-leakage signal，不是绝对黑名单；source 明确规定的稳定 component/interface contract 可以成为 Capability。

## Change gate

每个 Change 必须同时通过：

1. **One-intent**：用一句话说明本次改变的目的与结果。
2. **Scope Cohesion**：所有范围服务同一 intent，没有可独立批准的“顺便再做”。
3. **Independent Decision/Archive**：可以独立批准、推迟、实现、验证、完成和 archive。
4. **Indivisibility**：拆分不会破坏同一 transaction、invariant、protocol、security/consistency boundary 或 compatibility contract，也不会产生虚假 half-state。
5. **Acceptance**：存在 source-backed、具体、可观察或可验证的完成证据。
6. **Implementation-readiness**：范围足够聚焦，可由一次 focused `openspec-apply-change` pass 合理推进。

拆分只在子集具有不同 intent，或可独立批准、推迟、实现、验收和 archive，且各 archive state 都真实连贯时成立。

合并只在拆分会破坏同一 transaction/invariant/protocol/security/compatibility truth、使任一侧无法独立验收，或产生 source 不支持的 half-state 时成立。共享 infrastructure、相同团队、相同 Capability、相邻页面或表格形状都不足以作为合并理由。

## Behavior completeness profile

业务行为类 Change 在 boundary 确定后使用以下 profile 检查完整性，不使用它机械生成 Change：

```text
trigger/context -> normative behavior -> observable outcome or invariant
-> important exception/error semantics -> acceptance evidence
```

- failure/recovery 只有 source 明确要求或当前 outcome 真实成立所必需时才进入。
- acceptance evidence 是完成证明，不与 runtime behavior 混为同一个 obligation。
- architecture、performance、migration、tooling 或纯内部 implementation Change 使用与其 intent 相符的 engineering outcome，不伪造 user-facing projection。

## Foundation 例外

最多允许一个 pre-delivery foundation Change，并且必须位于 roadmap 第一位。它必须：

- 缺少时首个真实 outcome 无法合理启动；
- 只包含 zero-domain engineering substrate；
- 产生可验证、可复用的工程结果；
- 明确首个消费该 substrate 的 outcome Change。

domain schema、entity、command、policy、user-facing API、business worker、identity/authorization、privacy、recovery、delivery、export、history/versioning、observability 等 domain behavior 不得进入 foundation；普通 technical enabler 默认并入首个 consumer Change。

## 排序原则

1. 先满足 source-backed、不可绕过的 hard dependency，并保持 DAG 无环。
2. 在当前 eligible Change 中，优先最薄、真实、可观察、可独立验收并可 archive 的 outcome。

典型 input preparation -> core result -> async/external integration -> richer projection -> hardening 顺序只能作为同等候选之间的 heuristic，不得发明 source 未要求的 Change，也不得按 database -> service -> API -> UI -> test 技术层排序。

当前行为不可缺少的 authorization、privacy、security、compatibility、consistency 和 data-integrity guard 必须进入首个适用 Change。

## Change-Capability overlay

- 只有 Change 直接改变 Capability normative behavior 时才建立 advancement edge。
- dependency、reuse、preserve、related-only、design-only、task-only 和 verification-only 内容不推进 Capability。
- Capability 数量、名称或矩阵列不得决定 Change boundary。
- single-Capability Change 和只由一个 Change 推进的 Capability 都可以合法存在；合法性只由上述 gate 决定。

## 禁止的机械切分

不得按以下内容生成或调整 Change/Capability：

- source heading、page、table、document 或目录结构；
- database、repository、service、API、UI、test 等技术层；
- module、provider、queue、SDK 或部署单元；
- Capability 列、对角矩阵或同名 alias；
- atom/GA 数量、重复 evidence 数量或固定 complexity threshold。
