# Phase 1：初始 source-aligned Change 计划

Phase 1 在完整阅读用户指定的 source document 后，创建初始顶层 OpenSpec Change/Capability framework。该 framework 是由 source 支撑的 slicing hypothesis；obligation atom 完成规范化且 Phase 4 source-window grounding 完成后，Phase 5 可以对其 refit。Phase 1 不得创建具体 OpenSpec Change、proposal、spec、design、task、acceptance artifact、obligation atom ledger、line-range anchor、coverage status，也不得建立等待 Phase 2 处理的 evidence item backlog。

将 Phase 1 plan snapshot 写入：

```text
openspec/orchestrate/phase-works/phase-1/change-plan.md
```

同时将同一份初始 latest-effective plan 提升到：

```text
openspec/orchestrate/change-plan.md
```

将初始 full-source manifest 写入：

```text
openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md
```

将 Phase 1 report 写入：

```text
openspec/orchestrate/phase-works/phase-1/phase-1-agent-report.md
```

将 canonical Phase 1 trace sidecar 写入：

```text
openspec/orchestrate/trace/phase-1.trace.json
```

writer 完成后，Phase 1 必须通过 `references/reviewer-repair-loop.md` 定义的 reviewer/repair loop：main agent 运行 Phase validator、启动 fresh independent Phase 1 reviewer subagent；如果需要修改 artifact，则启动 fresh independent Phase 1 repair-writer subagent；重新运行 validator，repair 后再次启动 fresh independent reviewer；只有通过后才能继续。

## Artifact 语言门禁

对每项 Phase 1 output 应用 skill-level Artifact Language Gate。按需保留固定 heading、table header、field label、Capability ID、Change slug、path、command 和精确 source term，但所有 agent 编写的 explanation 都必须使用简体中文。这包括 assumption、conflict、behavior-boundary description、Capability increment cell、roadmap field value、risk-check answer、source-evidence hint explanation、archive-readiness note 和 Phase 1 report。

每次写入 Phase 1 artifact 后，执行 skill gate 中的 language self-check。忽略 ID、path、command、code 和固定 term 后，如果仍存在英文主导的 explanation sentence，必须在 Phase 1 结束前改写。

## 目标

完整阅读用户指定的 source document，并规划一组科学、可验证、可迭代的 OpenSpec Change。

每个 Change 都应表示可 review、可实现、可验证、可 archive 的系统行为变化。不得按 technical module、database table、页面、component、SDK、queue 或 prototype scenario 机械拆分。

只使用用户指定的文档或目录。生成初始 framework 前，枚举并阅读每份 source document 的正文。除非用户明确将其纳入 input，否则不得读取或依赖当前 `openspec/` 目录、现有 spec、现有 Change、archive history 或 custom artifact。

如果指定 source set 过大，无法安全完整阅读，则返回 blocker，不得抽样。Phase 1 framework 只有在基于 full-source read 时才有效。

## Change/Capability 模型

在整个计划中使用以下模型：

- Change 是 vertical business/system loop，应推动产品或系统达到具体且可 review 的 outcome。
- Capability 是长期存在的 spec behavior boundary；多个 Change 实现并 archive 后，它仍应作为 `openspec/specs/<capability>/spec.md` 保持意义。Capability 通常会跨多个 Change 逐步成熟。
- repository/module boundary、storage/provider/deployment choice、internal API organization、migration mechanics 和 verification strategy 本身都不是 Capability。除非 source 定义了适合作为 spec boundary 的持久 normative system behavior，否则将这些 technical architecture 内容保留在 owner Change 的 design/task/evidence scope 中。
- 先发现 Capability，再规划 Change，但不得根据 Capability list 机械生成 Change。依据真实的 user/system loop 切分 Change，然后只投影每个 loop 创建或修改的 spec delta。
- 当多个 Capability increment 都是同一 functional loop 的直接必要条件时，一个 Change 可以推进多个 Capability。目标不是最大化每个 Change 的 Capability coverage。
- 一个 Capability 通常会随时间由多个 Change 推进。
- 不得创建每个 Change 只实现一个 Capability 的 one-to-one roadmap。如果 candidate roadmap 出现这种趋势，围绕 user/system loop 重新切分 Change，并将 Capability 保持为 cross-cutting behavior boundary。
- anti one-to-one 规则用于防止 capability-driven roadmap；它不禁止来源于真实 user/system loop、主要推进一个 Capability 的小型聚焦 vertical Change。
- Capability ID 不得只是改写单个 Change outcome。如果某 Capability 仅由一个 Change 推进，且其 ID 与该 Change slug 共享主要名词或动词，将其视为 boundary smell：合并进更宽泛、持久的 Capability，围绕长期 behavior boundary 重命名，或记录 source-backed 原因说明它为何确实是 terminal boundary。
- 不得通过拆分或重命名 Capability，让每个 Change 只推进一个 Capability。当同一 loop 直接改变 identity、privacy、realtime state、version history、entitlement、failure recovery、export delivery 或 observability 等 cross-cutting Capability 时，它们应在多个 loop 中持续可见。
- 每个 Change 只实现其 closed loop 所需的 Capability increment；后续 Change 可以继续增强、扩展或 harden 同一 Capability。
- Change/Capability relation 只允许两个值：
  - `New`：该 Change 首次创建此 Capability/spec boundary。
  - `Modified`：该 Change 修改现有 Capability/spec boundary 的 requirement 或 scenario。
- 合法的 technical 或 architecture-oriented Change 在不产生 spec delta 时，可以同时使用 `New: None` 和 `Modified: None`。它仍必须可实现、可验证、archive-ready，并且不得为了填充 matrix 而发明 Capability。
- 不得把仅消费、preserve、复用或 dependency-only 的 Capability 建模为 Change/Capability relation。仅在有用时在 dependency 或 note 中提及，不得写入 Capability progression matrix。
- Capability 使用稳定的英文 kebab-case ID，例如 `account-access-continuity` 或 `async-work-execution-recovery`。不得使用 module name、table name、page name、external-service name 或本地化 display name 作为 Capability ID。

## Change complexity 校准

既不要追求最少 Change，也不要追求最多 Change；应针对可 review 的 implementation complexity 优化。

一个 Change 应交付一个清晰、可验证的 functional point 或 system behavior point。只有当多个 Capability increment 是该 functional point 的直接必要条件时，Change 才可以涉及多个 Capability。不得把 Change 涉及的 Capability column 数量本身当作 implementation cost；应按可独立验证的 functional point 拆分，而不是按 Capability column 拆分。

如果 candidate Change 包含多个 functional point，且每个 point 都能独立实现、验证、review 和 archive，同时仍满足 Closed-loop Test，则拆分该 Change。

只要小型 Change 来源于 user/system loop，而不是由 Capability list 机械生成，即使它主要推进一个 Capability 也仍然有效。

不得仅为避免 Capability matrix 呈现 one-to-one 外观而合并可独立验证的行为。

对 foundation candidate 之后的第一个 feature Change，优先选择最薄但真实、可 archive 的产品或系统 loop，不得假装后续 infrastructure 已完成。

### Change 排序原则

按 behavior maturity 排序 Change，而不是按 prerequisite availability 排序。

对典型 web system，优先安排最早的薄 user-visible behavior loop：真实页面或 user-facing entry point 可以端到端使用，包含 user action、system fact、visible result、基本 failure handling 和 verification。它不能只是静态 UI shell，必须是人工可 acceptance 的最小真实行为。

较早 Change 只建立使当前行为真实所需的 fact、contract 和 support。后续 Change 再扩展、自动化、集成、harden、治理、观测或运营已存在的行为。

在尚无具体行为可供保护、治理、限制、审计、运营或观测前，不得先实现复杂 permission model、governance workflow、quota policy、audit system、admin operation 或 observability layer。

只引入使当前行为真实所需的最小 access/context assumption。supporting Capability 只有在当前行为的真实 acceptance 确实需要它，或它本身就是可独立 acceptance 的 operational/system behavior 时，才应更早出现。

### 拆分质询

接受每个 candidate Change 前，回答：

1. 该 Change 证明的唯一 functional point 是什么？
2. 该 Change 是否包含可单独交付和验证的其他行为？
3. 是否可以在不使用虚假 stub 或仅低层 proof 的情况下，更早 archive 该 Change 的一部分？
4. 是否仅因共享 infrastructure，便把多个 entry point、failure mode 或 projection 合并在一起？
5. 该 Change 是否在 functional point 真正需要完整行为前，提前引入 infrastructure-heavy concern？

如果第 2、3、4 或 5 项答案为是，拆分该 Change；除非计划能说明合并 scope 为何是形成 coherent closed loop 的必要条件。

### Capability 形态质询

接受初始 framework 前，整体 review Capability map 和 progression matrix：

1. 每个 Capability 是否描述可跨多个 Change 合理成熟的持久 behavior boundary？
2. 是否超过一半的 planned Change 恰好只有一个非空 Capability cell？如果是，检查 roadmap 是否已变成 capability-driven；除非每个例外都有 source 支撑，否则重新切分。
3. 是否有许多 Capability 只有一个 advancing/baseline Change，或 Capability slug 只是改写其第一个 advancing Change slug？如果是，合并、重命名或扩展这些 Capability；除非它们确实是 source-backed terminal boundary。
4. 是否有 user/system loop 仅为缩窄 matrix 行，丢失了直接必要的 identity、privacy、realtime、versioning、entitlement、failure recovery、export 或 observability increment？如果是，将这些 direct increment 恢复到 loop 中。
5. 如果把同一 source obligation 表示为具有多个 Capability delta 的一个 vertical loop，后续 `openspec-propose` agent 是否更容易理解？如果是，保留该 loop 并记录 cross-Capability coupling。

## Change 切分

优先按可验证的 business/system loop 切分 Change。

每个 executable business Change candidate 都必须满足 Closed-loop Test：

- Entry：具有清晰 entry point，例如页面、API、CLI、worker job、webhook、admin operation 或 scheduled task。
- Fact：创建或改变清晰的 system fact，例如 data record、file、event、state、ledger entry 或 external receipt。
- Projection：可通过 UI、API response、stream event、notification、download link、log 或 audit view 观察结果。
- Failure：至少明确一个 failure path，且具备可解释、可恢复或 blocked state。
- Verification：存在 executable proof，例如 unit、contract、integration、E2E、visual smoke、manual checklist、fixture replay 或 dry run。

如果 candidate Change 只能证明 low-level component 存在，它就不能作为独立 executable business Change。可以将其记录为供 Phase 2/3 slicing 和 Phase 4 grounding 使用的 foundation candidate，但由 Phase 5 决定它是否符合第一个 executable foundation Change 的条件。它必须保持 zero-domain engineering substrate，且不得计入 business Capability 的 `New` / `Modified` progression。

## Foundation 候选项

只有同时满足以下条件时才允许 foundation candidate：

1. 缺少它时，任何后续 closed-loop Change 都无法合理启动。
2. 它是初始 roadmap 中唯一的 pre-business foundation candidate。
3. 它是 zero-domain engineering bootstrap。
4. 它产生稳定、可复用的 engineering boundary。
5. 它说明实现后用于验证 substrate 的 runtime 或 integration-level proof expectation。
6. 它指出第一个构建在其上的 closed-loop business/user workflow。
7. 计划中不存在连续的纯 foundation candidate。

Phase 1 foundation candidate 只能包含第一个真实 workflow 之前必需的 engineering substrate：

- repository/package 目录
- 根级脚本
- lint/typecheck/test harness
- env 校验
- 本地依赖 manifest
- migration 工具，但不包括业务 schema
- 空的 web/worker smoke 入口
- 行为尚未体现 domain 特性的空 adapter seam

Phase 1 foundation candidate 不得包含：

- 超出 migration 工具范围的 business/domain table 创建或 table ownership
- domain command、use case、policy 或 repository
- 面向用户的 API route 或 DTO
- domain-specific worker 或 async 语义、job state machine、recovery loop 或业务 queue
- domain event、stream message、outbox event 或 realtime 业务消息
- 与 domain 语义绑定的 identity、authorization、tenancy、entitlement 或 account mapping
- domain entity、lifecycle object、collection/accounting/delivery/export 概念或 history/versioning 规则
- 属于首个需要它的 workflow 的专用 observability、privacy、recovery、responsive、design-system 或 verification 行为

Phase 1 发现的 source-backed domain behavior 应切分到 business Change candidate，或记录为 Phase 2 的 non-canonical ownership hint。不得将其隐藏在 foundation/spine Change 内。

Phase 1 不得承诺 foundation candidate 会成为 executable final Change，该 decision 属于 Phase 5。如果符合条件，Phase 5 将其渲染为第一个 executable foundation Change packet，并使用 `change-kind: foundation`、`final-target-capability: runtime-substrate-foundation` 和 `final-capability-impact: foundation-substrate`；否则 Phase 5 必须移动、defer、contextualize 或阻塞它。business roadmap progression 从第一个 `change-kind: business` packet 开始。

## 工作流

1. 枚举用户指定根目录或精确 path 下的每份 source document。
2. 阅读每份已枚举 source document 的正文。不得抽样、只浏览 filename，也不得把完整阅读推迟到 Phase 2。
3. 写入 `phase-works/phase-1/source-doc-manifest.md`，列出每份 source document、read status、high-level source role 和 coarse topic/path hint。
4. 从完整 source 阅读结果中提取核心 user/system path、长期 normative behavior、constraint 和 architecture decision。
5. 将每条 path 表达为：entry -> behavior -> system fact -> visible result -> failure recovery。
6. 先识别稳定的 spec Capability，并使用英文 kebab-case ID。每个 Capability 都必须证明存在持久的 `openspec/specs/<capability>/spec.md` boundary，在多个 Change 后仍有价值；拒绝 module、storage、deployment、provider、component 或 verification-only label。
7. 从 user/system loop 生成 candidate vertical Change，不得从 Capability list 生成。
8. 使用 Closed-loop Test、Change Complexity Calibration、Split Challenge、Capability Shape Challenge 和 anti one-to-one mapping rule 过滤、合并或重新切分 candidate。
9. 按 behavior maturity 和真实 engineering dependency 排序 Change；优先最早的 minimal runnable loop，而不是未来 prerequisite availability。
10. 将每个已排序 Change 投影到 Capability map：把每个实际 spec delta 分类为 `New` 或 `Modified`；如果 Change 仅包含 architecture/design/verification 工作，则两者均使用 `None`。
11. 建立只显示这些 `New` / `Modified` spec delta 的 Capability progression matrix。
12. 标记 input document 中的关键 scenario、non-goal、risk、conflict 和 deferred content。
13. 仅为证明计划切分合理性而添加简洁的 `Source evidence` hint。hint 可以列出 source path、heading、section number、decision ID、route/page/object name、API、command、DTO、entity、table、job、event、asset、environment 或 verification anchor。
14. Phase 1 evidence hint 保持简短且 non-canonical。不得提取或枚举每项 source-backed requirement，不得创建 obligation atom ledger、行范围、anchor table、coverage status、"pending Phase 2" evidence list 或 evidence count。Phase 2 负责 source-first atom extraction，Phase 3 负责 coverage normalization，Phase 4 负责 source-window grounding，Phase 5 负责 final plan refit。
15. 按照 `references/trace-sidecar-contract.md` 写入 `trace/phase-1.trace.json`。writer 完成后，由 main orchestrating agent 刷新 `trace/manifest.json` 并运行 `validate_source_aligned_orchestrate.py --phase phase-1`。

## 输出

生成 `openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md`，其中包含：

| Source Document | Read Status | Source Role | Coarse Topics / Paths | Notes |
| --- | --- | --- | --- | --- |

规则：

- 每份用户指定的 source document 必须恰好出现一次。
- 本工作流使用的 source document，其 `Read Status` 必须为 `read-full`。
- 仅当 non-source artifact 位于指定根目录下且不属于有意义的 source document 时，才可列为 `non-source-artifact`。
- Phase 1 不得添加 coverage status、atom count 或 line-range coverage。

生成 `openspec/orchestrate/phase-works/phase-1/change-plan.md`，再将同一份 latest-effective content 提升到 `openspec/orchestrate/change-plan.md`，内容包括：

### 输入

- 已指定并阅读的 document
- 可能相关但未阅读的 document
- assumption 和 conflict

### 切分原则

- 本计划使用的 Change slicing principle
- 被拒绝的 slicing approach 及原因
- 明确说明 Change 是 vertical loop，Capability 是长期 behavior boundary

### Capability 映射

| Capability | Behavior boundary | First change | Later expansion |
| --- | --- | --- | --- |

规则：

- Capability value 必须是反引号包裹的英文 kebab-case ID。
- Behavior boundary 说明持久 spec behavior，以及为何计划中的 Change 完成后 `openspec/specs/<capability>/spec.md` 仍有价值；不得描述 implementation module。
- Later expansion 应体现 Capability 可在后续 Change 中继续成熟。
- 如果许多 Capability 的 `Later expansion` 为 `None`，或只重复第一个 Change，计划必须解释这些 Capability 为何确实是 terminal boundary，而不是 one-Change alias。
- 如果完整 source set 不包含 business spec delta，保留 `Capability Map` heading 并写入 `无业务 Capability delta`；不得发明 Capability 或渲染格式错误的空表。

### Capability progression 矩阵

在 Capability Map 后创建 matrix：

| Change | `capability-a` | `capability-b` | `capability-c` |
| --- | --- | --- | --- |
| `change-name` | 该 Change 交付的具体 Capability increment |  | 该 Change 交付的具体 Capability increment |

规则：

- 每行对应一个 Change。
- 每列对应 Capability Map 中的一个 Capability。
- 每个非空 cell 描述该 Change 为对应 Capability 提供的具体 functional increment。
- Change 不创建或修改某 Capability 时，将 cell 留空。
- `New: None` 且 `Modified: None` 的 Change 使用全空 matrix 行；不得为 architecture、design 或 verification 工作合成 Capability。
- 不存在 Capability 时，保留 `Capability Progression Matrix` heading 并写入 `无业务 Capability delta`，不得输出空 Capability table。
- 不得使用通用 reuse、通用 test coverage 或 "uses existing capability" 填充 cell；matrix 只包含 direct Capability advancement。
- 不得在 matrix cell 前添加 `New:` 或 `Modified:`；以每个 Change Roadmap 条目显式的 `New` / `Modified` list 作为 Phase 1 relation source。某 Capability 首次列出的 delta 必须为 `New`，后续 delta 必须为 `Modified`；任何 renderer 都不得根据 matrix 顺序猜测或静默修复 label。
- cell text 应足够简洁，便于 review。
- 如果 matrix 大部分呈 diagonal、包含许多与 single-Change Capability 配对的 single-cell 行，或视觉上像是把 Change list 复制成 Capability，应在 Phase 1 结束前修订 Change/Capability 模型。

### Change roadmap

每个 Change 包含：

- Change 名称：
- 闭环结果：
- 来源 evidence hint（Phase 1，non-canonical）：
- Capability 变更：
  - New：使用 Capability Map 中的 Capability ID，或写入 `None`。
  - Modified：使用 Capability Map 中的 Capability ID，或写入 `None`。
- 范围内：
- 范围外：
- vertical slice：
  - 入口：
  - 事实：
  - projection：
  - 失败：
  - 验证：
- 依赖：
- 归档就绪性：

### 风险检查

回答：

1. 是否存在连续的、没有 observable behavior 的 low-level Change？
2. 每个 executable business Change 是否都有 closed loop？
3. 是否有 Capability 按 technical module、storage/provider/deployment choice 或 verification strategy 命名，而不是持久的 `openspec/specs/<capability>/spec.md` behavior boundary？
4. 是否有关键 input scenario 未映射到 Change？
5. 是否有 Change 只能通过“code 存在”验证，而无法通过 behavior proof 验证？
6. 计划是否暗示 Change 与 Capability 之间存在 one-to-one mapping？
7. 每个 Change/Capability relation 是否只使用 `New` 或 `Modified`，且 Change 不创建或修改 spec Capability 时使用空 cell 和 roadmap `None`？
8. 是否有 Change 合并了多个可独立验证、实现并 archive 的 functional point？
9. foundation candidate 后的第一个 feature Change 是否在 functional point 需要完整行为前引入 infrastructure-heavy concern？
10. 计划是否仅为避免 Capability matrix 呈现 one-to-one 外观而合并行为？
11. 是否将初始 Change/Capability boundary 标为 hypothesis，说明 atom extraction 和 Phase 4 source-window grounding 后可能需要 Phase 5 refit？
12. 是否有许多 Capability ID 只是改写首次建立其 spec baseline 的 Change slug？
13. cross-cutting production concern 是否被移入独立的 capability-shaped Change，尽管它们直接影响同一 user/system loop？
14. 如果超过一半 executable business Change 只推进一个 Capability，是否有 source-backed evidence 证明它们确实是独立 loop，而不是 diagonalized roadmap？
15. 如果存在 foundation candidate，它是否严格属于 zero-domain engineering bootstrap？
16. Phase 1 是否避免将 domain-specific schema、entity、command、user-facing API、worker/async business semantics、domain event、identity/authorization/account mapping、entitlement/accounting/delivery/export concept、lifecycle/versioning rule、privacy、recovery、responsive、design-system、observability 或其他 workflow-specific behavior 放入 foundation scope？
17. source-backed domain obligation 是否表示为 business Change candidate，或首个需要它的 workflow 的 Phase 2 ownership context？
18. roadmap 是否在具体行为存在前安排 permission、governance、quota、audit、admin、observability 或 operation Capability，却没有证明该 Capability 可独立 acceptance？
19. 对典型 web system，早期 roadmap 是否生成薄的 user-visible end-to-end behavior，而不是静态 UI shell 或 prerequisite collection？
20. Phase 1 是否在切分 loop-based Change 前识别稳定 Capability，同时避免从 Capability list 本身生成 Change？
21. 是否有仅归属 Change 的 architecture/design/verification scope 导致计划发明 Capability，而不是让 `New` 和 `Modified` 都保持 `None`？

## Phase 报告

`phase-works/phase-1/phase-1-agent-report.md` 必须简要列出：

- 已阅读的 source document
- 生成的 plan path
- 值得注意的 assumption 或 conflict
- 是否有 Change 缺少有用的 source hint；不得枚举每项 pending evidence item
- 确认 manifest 中每份 source document 均已完整阅读
- 确认 Phase 1 artifact 通过 Artifact Language Gate
- blocker，或 `无`
