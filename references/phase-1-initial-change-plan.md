# Phase 1：初始 source-aligned Change 计划

Phase 1 完整阅读用户指定的 source document，形成初始 Change/Capability slicing hypothesis。该计划用于表达 source 支撑的业务与系统闭环、持久 Capability boundary 和初始 roadmap，不是 final plan。

执行前，writer 必须直接完整读取 `references/cross-phase-contract.md` 和 `references/trace-sidecar-contract.md`；prompt 摘要、转述或继承上下文不能替代直接读取。

## 目录

- 目标与边界
- 输入权威
- 产出
- 规划方法
- Change 与 Capability 规则
- Source evidence hint
- 输出模板
- Phase 报告与完成条件

## 目标与边界

Phase 1 只负责：

- 枚举并完整阅读用户指定 source set 中的每份 source document。
- 识别真实的 user/system loop、长期 normative behavior、constraint 和 architecture decision。
- 从 loop 切分可 review、可实现、可验证、可 archive 的初始 Change。
- 将 Change 对持久 spec Capability 的直接增量投影为 `New` 或 `Modified`。
- 写入初始计划、source manifest、Phase report 和 canonical trace。

初始 Change/Capability boundary 必须明确标为 hypothesis。不得把 candidate Change、Capability relation、source hint 或排序假设提升为 final authority。

## 输入权威

- 只使用用户指定的文档或目录作为 source authority。
- 生成计划前，必须枚举并完整阅读 source set 中每份有意义的 source document；不得抽样、仅浏览文件名或跳过正文。
- 指定目录中的非 source artifact 可以在 manifest 中标记为 `non-source-artifact`，但有意义的 source document 不得归入此类。
- 除非用户明确纳入 input，不得读取或依赖当前 `openspec/`、现有 spec、现有 Change、archive history 或 custom artifact。
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

继承 `references/cross-phase-contract.md` 的 Artifact Language Gate。assumption、conflict、behavior boundary、Capability increment、roadmap value、risk-check answer、source-evidence hint、archive-readiness note 和 report 都必须使用简体中文。

## 规划方法

严格按以下顺序形成初始计划：

1. 枚举 source set，完整阅读正文，并写入 source manifest。
2. 识别 source 中的 user/system loop；将每条 loop 表达为 entry -> behavior -> system fact -> visible result -> failure recovery -> verification。
3. 从长期 normative behavior 推导稳定 Capability boundary；拒绝 module、table、page、component、provider、deployment 或 verification-only label。
4. 从 user/system loop 切分 candidate Change；不得从 Capability list 机械生成 Change。
5. 使用 Closed-loop Test、Change 粒度门禁、Capability 持久性门禁和 foundation 例外门禁过滤、拆分、合并或重命名 candidate。
6. 将每个 Change 实际创建或修改的 spec Capability delta 显式标为 `New` 或 `Modified`；不产生 spec delta 时两者均为 `None`。
7. 先按 behavior maturity 安排最薄真实闭环，再用不可绕过的运行时硬依赖约束顺序。不得因未来治理、运营或 infrastructure 需求提前安排尚无行为对象的 Change。
8. 写入 coarse、non-canonical source hint、assumption、conflict、non-goal、deferred content 和风险检查结果。

## Change 与 Capability 规则

### Change closed loop

每个 executable business Change 必须交付一个清晰的 functional point，并通过 Closed-loop Test：

- Entry：页面、API、CLI、worker job、webhook、admin operation 或 scheduled task 等明确入口。
- Fact：创建或改变 data record、file、event、state、ledger entry 或 external receipt 等 system fact。
- Projection：通过 UI、API response、stream event、notification、download、log 或 audit view 观察结果。
- Failure：至少一个可解释、可恢复或明确 blocked 的失败路径。
- Verification：unit、contract、integration、E2E、visual smoke、manual checklist、fixture replay 或 dry run 等 executable proof。

如果一个 candidate 包含多个可独立实现、验证、review 和 archive 的 functional point，应拆分。不得仅因共享 infrastructure 合并独立 entry point、failure mode 或 projection，也不得仅为改善 Capability matrix 外观而合并真实行为。

### Capability boundary

- Capability 是长期存在的 spec behavior boundary；多个 Change archive 后，`openspec/specs/<capability>/spec.md` 仍应有独立意义。
- Capability 使用稳定的英文 kebab-case ID，不得以 module、table、page、provider、deployment choice 或单个 Change outcome 命名。
- Change 从 loop 产生，Capability 从持久行为边界产生；两者不得机械一一对应。
- 同一 loop 直接改变多个持久行为边界时，一个 Change 可以推进多个 Capability。
- `New` 表示首次创建 Capability/spec boundary；`Modified` 表示修改既有 requirement 或 scenario。
- 仅消费、preserve、复用或依赖某 Capability 不构成 relation，不得填入 progression matrix。
- architecture、design 或 verification-only Change 不产生 spec delta 时，roadmap 中 `New` 与 `Modified` 均写 `None`，matrix 行保持为空。

### Foundation 例外

最多允许一个 pre-business foundation candidate，且必须同时满足：

- 缺少它时，首个真实 closed-loop Change 无法合理启动。
- 只包含 zero-domain engineering substrate，例如目录、根脚本、lint/typecheck/test harness、环境校验、依赖 manifest、migration tooling、空 smoke entry 或无 domain 语义的 adapter seam。
- 产生稳定、可复用且可通过 runtime/integration proof 验证的工程边界。
- 明确指出首个消费该 substrate 的真实业务或用户闭环。

Foundation 不得包含 domain schema、entity、command、policy、repository、user-facing API、domain worker/state machine、business queue/event、identity/authorization/tenancy、entitlement、accounting、delivery、export、history/versioning、privacy、recovery、responsive、design-system、observability 或其他 workflow-specific behavior。不得出现连续的纯 foundation Change。

## Source evidence hint

每个 Change 只添加足以解释切分依据的 coarse locator，例如 source path、heading、section number、decision ID、route/page/object name、API、command、entity、job、event、asset 或 environment。

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

#### `## 切分原则`

- 本计划实际采用的 loop-based slicing principle。
- 被拒绝的 slicing approach 及原因。
- 明确说明 Change 是 vertical loop，Capability 是长期 behavior boundary，当前 boundary 为初始 hypothesis。

#### `## Capability Map`

| Capability | Behavior boundary | First change | Later expansion |
| --- | --- | --- | --- |

- Capability 使用反引号包裹的英文 kebab-case ID。
- Behavior boundary 描述持久 normative behavior，不得描述 implementation module。
- First change 与 roadmap 中的首次 `New` 一致。
- Later expansion 说明后续成熟方向；确属 terminal boundary 时说明 source-backed 原因。
- 没有业务 Capability delta 时，保留 heading 并写 `无业务 Capability delta`，不得输出空表或发明 technical Capability。

#### `## Capability Progression Matrix`

| Change | `capability-a` | `capability-b` |
| --- | --- | --- |
| `change-name` | 该 Change 交付的具体 Capability increment |  |

- 每行对应一个 Change，每列对应 Capability Map 中一个 Capability。
- 非空 cell 只描述 direct Capability advancement；不创建或修改时留空。
- roadmap 中 `New: None` 且 `Modified: None` 的 Change 使用全空行。
- relation authority 是 roadmap 的显式 `New` / `Modified` list；首次 delta 必须为 `New`，后续 delta 必须为 `Modified`。
- 不存在 Capability 时，保留 heading 并写 `无业务 Capability delta`。

#### `## Change Roadmap`

每个 Change 使用以下结构：

- Change 名称：英文 kebab-case slug。
- 闭环结果：唯一 functional point。
- 来源 evidence hint：coarse、non-canonical locator。
- Capability 变更：
  - New：Capability ID，或 `None`。
  - Modified：Capability ID，或 `None`。
- 范围内：
- 范围外：
- vertical slice：
  - 入口：
  - 事实：
  - projection：
  - 失败：
  - 验证：
- 硬依赖：只列不可绕过的 runtime/behavior prerequisite，或 `无`。
- 归档就绪性：说明为何可独立 propose、实现、验证和 archive。

#### `## Phase 1 风险检查`

必须逐项回答：

1. Source 完整性：manifest 是否覆盖 source set，且每份 source document 均为 `read-full`？
2. Closed loop：每个 executable business Change 是否具有 entry、fact、projection、failure 和 verification？
3. Change 粒度：是否合并了可独立交付的 functional point，或仅因共享 infrastructure/矩阵外观而合并？
4. Capability 持久性：Capability 是否为长期 behavior boundary，并避免 technical label、single-Change alias 和 capability-driven slicing？
5. Relation 一致性：Capability Map、matrix 与 roadmap 的 `New` / `Modified` / `None` 是否一致？
6. Foundation 合法性：是否至多一个、严格 zero-domain，且未吸收任何 workflow-specific behavior？
7. Roadmap 顺序：是否以 behavior maturity 为主，并只受真实硬依赖约束，没有提前安排未来治理或 infrastructure concern？
8. Phase 1 边界：是否避免 atom、line range、coverage、evidence backlog、work queue、具体 OpenSpec artifact 和 final decision？

#### `## Phase 1 语言自检`

确认忽略固定 heading、field label、enum/status、ID、path、command、code/API/DB/package symbol、filename 和精确 source quote 后，agent 编写的解释内容均为简体中文。

## Phase 报告与完成条件

`openspec/orchestrate/phase-works/phase-1/phase-1-agent-report.md` 必须简要列出：

- 已完整阅读的 source document。
- initial plan 和 source manifest path。
- candidate plan 的 assumption 处理结果。
- 值得注意的 conflict 或 `无`。
- 确认未创建 prohibited Phase 1 artifact。
- 确认 artifact 通过语言门禁。
- blocker，或 `无`。

Phase 1 只有同时满足以下条件才可写入 `trace/phase-1.trace.json`，并使用 `status: initial-plan-written`：

- source set 已完整读取，manifest 与 canonical trace 一致。
- `initial-change-plan.md` 存在并符合固定输出模板。
- trace 使用 `source-aligned-phase-1-trace-v2`，且 plan path/digest 当前有效。
- agent report 的 blocker 为 `无`。

任一条件不满足时不得声明 Phase 1 完成。成功 output 返回 main agent 后，按共享 contract 运行 validator 和 independent reviewer。
