# Phase 5：atom-driven Change/Capability 计划 refit

Phase 3 返回 `Decision: coverage-complete` 且 Phase 4 返回 `Phase 4 Status: grounded` 后运行 Phase 5。此时 obligation atom granularity 已稳定，初始 Change/Capability framework 背后的原始 source window 已复制到 Phase 4 reviewer-facing dossier。Phase 5 不得仅根据 atom summary 作出 plan-refit judgment：必须消费 Phase 4 source-window dossier 和 semantic profile，将其作为每项 split、merge、reorder、rename、ownership move、relation change 和 complexity decision 的 grounding evidence。

执行本 Phase 前，writer 必须直接完整读取 `references/cross-phase-contract.md`；prompt 摘要、转述或继承上下文不能替代直接读取。

Phase 5 根据规范化 global atom index 和 Phase 4 source-window semantic dossier 重整计划。它使用具体的 source-backed atom group 及其原始 source context，而不是初始 slicing hypothesis，评估 Change order、spec Capability progression、dependency、artifact projection 和 Change complexity。它可以接受 Phase 1 framework，也可以重构 Change/Capability。每项 decision 都必须保持 atom-level traceability，为每个 executable direct atom 分配且只分配一个 owner Change，并确保每个 final direct atom 具有下游 artifact projection。Capability impact 是正交 metadata，不是 co-ownership。

Phase 5 必须由 fresh independent subagent 执行。不得重新运行 Phase 2 extraction，也不得发明新的 source obligation。如果 Phase 5 发现 missing 或 over-broad source obligation，必须返回 `needs-coverage-recheck`，而不是在 Phase 3 之外静默创建新 atom。

## 输入

- `openspec/orchestrate/phase-works/phase-4/input-change-plan.md`
- `openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/index.md`
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.json`，作为 canonical global atom index
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`，作为 reviewer mirror
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/index.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/source-window-index.json`，作为 canonical Phase 4 source-window index
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-change/*.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-capability/*.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md`
- `openspec/orchestrate/phase-works/phase-4/source-window-grounding-issues.md`
- `openspec/orchestrate/phase-works/phase-4/phase-4-agent-report.md`
- `openspec/orchestrate/phase-works/phase-3/coverage-review.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/*.json`，作为 canonical Phase 3 trace sidecar
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/*.md`，作为 reviewer mirror
- 用户指定的 source document 根目录或精确 source path；仅在 Phase 4 dossier 引用了必须本地验证的 window 时，用于 targeted context read。
- 当前 `openspec/specs/` inventory 及 final target 对应的 `openspec/specs/<capability>/spec.md`，只作为 repository baseline identity/existence/comparison evidence；不得把现有 spec 当作 production obligation authority。

## 输出

将当前 refit packet 直接写入 `openspec/orchestrate/phase-works/phase-5/`。Phase 5 不得创建 `pass-*`、`iteration-*`、attempt-numbered 或类似的迭代子目录。如果 `needs-coverage-recheck` 后必须重新运行 Phase 5，原地更新当前 Phase 5 packet；除非用户明确要求 historical archival。

- `openspec/orchestrate/phase-works/phase-5/source-window-refit-trace.md`
- 仅在 status 为 `adjusted`、`needs-coverage-recheck` 或 `blocked` 时写入 `openspec/orchestrate/phase-works/phase-5/change-plan-adjustments.md`
- `openspec/orchestrate/phase-works/phase-5/phase-5-agent-report.md`
- `openspec/orchestrate/trace/phase-5.trace.json`

status 为 `accepted` 或 `adjusted` 时，还要写入 terminal mapping 和 final consume-ready artifact：

- `openspec/orchestrate/phase-works/phase-5/change-plan.md`
- `openspec/orchestrate/phase-works/phase-5/input-change-plan.md`
- `openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json`
- 从匹配 JSON 渲染的 `openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.md`
- `openspec/orchestrate/phase-works/phase-5/final-packet-index.json`
- `openspec/orchestrate/phase-works/phase-5/capability-progression-review.md`
- `openspec/orchestrate/phase-works/phase-5/capability-baseline-reconciliation.md`
- `openspec/orchestrate/phase-works/phase-5/capability-baseline-reconciliation.json`
- `openspec/orchestrate/phase-works/phase-5/change-complexity-review.md`
- `openspec/orchestrate/phase-works/phase-5/plan-refit-decision-log.md`
- `openspec/orchestrate/phase-works/phase-5/alignment-final-report.md`
- `openspec/orchestrate/change-capability-anchors/index.md`
- `openspec/orchestrate/change-capability-anchors/<change-slug>/<change-slug>.md`
- `openspec/orchestrate/change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md`
- `openspec/orchestrate/phase-works/phase-5/change-capability-human-plan.md`
- `openspec/orchestrate/change-plan.md`

status 为 `needs-coverage-recheck` 或 `blocked` 时，不得伪造或保留 terminal plan、mapping、Capability baseline reconciliation、final packet、Capability view、alignment report、human plan 或根 `change-plan.md`。如果当前目录来自较早 terminal run，先删除这些 stale terminal artifact，再写入 `trace/phase-5.trace.json`、`phase-5-agent-report.md`、`source-window-refit-trace.md` 和 `change-plan-adjustments.md`，其中包含 recheck 或 blocker 的 source-window-backed 原因。Phase 3 global atom index 及其他 upstream evidence 必须保留。

即使 Phase 5 原样接受 input plan，也必须写入当前 Phase 5 packet 和 final Change packet。Phase 5 的 `input-change-plan.md` 必须每次从 Phase 4 input snapshot 覆盖生成；不得复用旧 snapshot。只有 Phase 5 packet 记录 input plan、output plan 和 atom-plan mapping 后，才能同时写入 `phase-works/phase-5/change-plan.md` 与根 `openspec/orchestrate/change-plan.md`。两个 final plan 必须逐字节一致。

`phase-works/phase-2/source-obligation-atoms/`、canonical `change-capability-anchors/obligation-atom-index.json` 及其 Markdown mirror、`phase-works/phase-4/source-window-dossiers/` 都是 upstream evidence。Phase 5 不得编辑。

writer 完成后返回 main agent，由 main agent 完整执行 `references/reviewer-repair-loop.md`。Phase 5 writer 不得自行 reviewer、repair 或 handoff。

Phase 4 source-window dossier 和 semantic profile 是 Phase 5 的 source-grounding input。`source-window-refit-trace.md` 是 Phase 5 decision trace，用于说明这些 input source-window profile 如何转换为 final Change/Capability：哪些原始 atom 保持同组、移动、拆分、合并或变为 contextual/dependency/evidence/non-goal，以及 adjusted unit 为何仍是真实的 engineering delivery slice。

## 推荐的 mechanical helper

对可生成 `accepted` 或 `adjusted` 的 rerun 或大型 Phase 5 refit，优先使用 bundled deterministic helper，不要粘贴很长的一次性 Python heredoc。Phase 5 subagent 仍负责 semantic decision：必须 review Phase 4 source-window dossier 和 global atom index，决定 final roadmap，写入或更新经过 review 的 canonical `atom-plan-mapping.json`，并准备 JSON config，列出 final Change、Capability、split analysis、decision、adjustment 和 report finding。helper 从 JSON 渲染 `atom-plan-mapping.md`，再根据这些 reviewed input 渲染 mechanical final artifact。如果 reviewed status 为 `needs-coverage-recheck` 或 `blocked`，不得运行 final-packet renderer 伪造 terminal artifact。

不得用 helper 替代 Phase 4 source-window grounding。只有 `phase-works/phase-4/source-window-dossiers/`、`phase-works/phase-4/source-window-semantic-profile-review.md` 和 `phase-works/phase-5/source-window-refit-trace.md` 均已写入并完成 review，helper-rendered final packet 才可视为有效。

建议流程：

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase5_plan_refit.py \
  --orchestrate-dir openspec/orchestrate \
  --mapping openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json \
  --print-config-template > openspec/orchestrate/phase-works/phase-5/phase5-refit.config.json
```

然后编辑 `phase5-refit.config.json`：每个 final Change 都要有经过 review 的中文 title/intent/outcome/kind；每个 active business Capability 都要有经过 review 的中文 Purpose/Owns/Excludes，以及与精确 `openspec/specs/<capability>/spec.md` 一致的 `baseline_status: existing | absent` 和 `baseline_evidence`。同时记录经过 review 的 decision/split analysis/adjustment/report finding。不存在 business spec delta 时，`capabilities` 可以为 `[]`；此时生成的 Capability Map 和 Matrix 必须保留 heading 并写入 `无业务 Capability delta`，不得产生格式错误的空表。随后运行：

```bash
python3 -m py_compile .codex/skills/source-aligned-change-plan-coverage/scripts/phase5_plan_refit.py

python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase5_plan_refit.py \
  --orchestrate-dir openspec/orchestrate \
  --mapping openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json \
  --config openspec/orchestrate/phase-works/phase-5/phase5-refit.config.json

python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase5_plan_refit.py \
  --orchestrate-dir openspec/orchestrate \
  --mapping openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json \
  --config openspec/orchestrate/phase-works/phase-5/phase5-refit.config.json \
  --write \
  --validate-rendered
```

覆盖 active orchestration output 前 review 生成 file 时，使用 `--output-orchestrate-dir /tmp/phase5-check/openspec/orchestrate` 在临时 tree 中执行 dry render。`--no-root-update` 只允许用于此类暂存检查；使用该参数的 output 不满足 terminal artifact contract。只有 subagent 已 review config 且 main-agent gate 通过，helper output 才有效。如果 validation 失败，repair mapping/config 或返回 `needs-coverage-recheck`/`blocked`；不得削弱 script 中的 check。

helper render 后，按 `references/trace-sidecar-contract.md` 运行 Phase 5 validator；不得在本文件复制或分叉 validator 命令契约。

## Artifact 语言门禁

继承 `references/cross-phase-contract.md` 的 Artifact Language Gate。Phase 5 的 intent/outcome、behavior boundary、baseline reconciliation、roadmap value、Capability progression、complexity decision、split/defer analysis、context handling、blocker、plan-decision reason、evidence burden、human review note 和 report summary 必须使用简体中文。

## Scope 规则

Phase 5 可以：

- global atom 证明 Phase 1 framework coherent 时接受该 framework
- atom group 和 dependency 要求时，添加、移除、拆分、合并、重排或重命名 Change
- 将一个符合条件的 pre-business foundation candidate 作为第一个 executable foundation Change 输出
- atom 暴露持久 behavior boundary gap 时，添加、移除、拆分、合并或重命名 Capability
- Phase 3 将 placement 留给 refit，或 sequence 证明初始 candidate Change 错误时，将 global atom 移到不同 owner Change
- source window 证明 Phase 3 metadata unresolved 或错误时，分配或修订 `final-capability-impact`、`final-target-capability` 和 source-explicit `related-capabilities[]`
- global atom 约束 design 但不属于当前 direct scope 时，将其重新分类为 contextual future-compatibility、dependency、preserve、reference、later-change 或显式 non-goal
- 解决标记为 `phase-5-refit-required` 的 atom final owner placement
- Phase 3 projection 过宽、过窄或不再匹配 final Change packet 用途时，调整 final artifact projection
- 使用不同的 source-backed atom delta，将 Capability maturity 分阶段表示为 baseline -> refinement/hardening/extension
- 根据 global atom index 派生 final per-Change 和 per-Capability atom file
- 决定 plan refit 时引用 Phase 4 source-window dossier evidence
- 需要验证 Phase 4 dossier 已引用的措辞或 dependency rationale 时，读取 Phase 3/4 handoff item 周围的 targeted source context
- 只读检查 `openspec/specs/<capability>/spec.md` 是否存在，并在必要时比较已有 requirement identity，以决定 Capability-level `New` / `Modified`；该 baseline lane 不得改变 source obligation、final Change intent 或 target Capability 的 source-backed 语义

Phase 5 不得：

- 全局重新运行 Phase 2
- 编辑 Phase 2 source atom file
- 编辑 Phase 3 coverage output 或 global atom index
- 编辑 Phase 4 source-window dossier output
- 生成绕过 Phase 4 的 replacement source-window dossier
- 在未经 Phase 3 normalization 时发明新 atom
- 从 roadmap 首次出现位置、Phase 1 `first-advancement`、Change 名称或 renderer order 猜测 OpenSpec `New` / `Modified`
- 把 repository baseline spec 中额外出现、但 source document 未要求的行为变成当前 production obligation
- 输出多个 pre-business foundation/governance candidate、把 foundation Change 放在 business Change 之后，或保留没有独立 intent、可验收 outcome 与独立生命周期边界的 standalone low-level business Change
- 在没有 semantic review 时，使用 raw uncovered line count 驱动 plan adjustment
- 将 Phase 4 source-window dossier 视为可以在 Phase 3 之外提取、改写、合并、拆分或发明新 obligation atom 的授权
- 对应 Phase 4 source window 可用时，仅根据 atom count 或 summary 决定 Change split、merge、reorder、Capability boundary 或 foundation executable handling
- 让任何 executable direct global atom 缺少唯一 final owner Change；除非它是 non-direct、non-coverage 或 blocked
- 让任何 direct global atom 缺少 final artifact projection
- 让任何 final direct global atom 保持 `contextual-only`；contextual-only atom 必须移入 context table、non-direct handling 或 blocker status
- 仅因 atom 为 direct，便强制把 `design-obligation` 或 `verification-obligation` 写入 spec 成为 `spec-requirement`
- 为普通 `design-obligation` 或 `verification-obligation` 分配 `final-capability-impact: none`、`final-target-capability: none` 之外的值；这些 atom 继续保持 direct 且归属 Change
- 任何行仍为 `final-capability-impact: unresolved` 时返回 `accepted` 或 `adjusted`
- 将 `related-capabilities[]` 用作 target substitute、ownership surface、progression input、Capability-view input 或 advanced-Capability complexity input
- 留下 unresolved 的 duplicate direct ownership
- 为每个 page、table、SDK、queue、external service、component 或 source document section 创建一个 Capability
- 将未来 obligation 隐藏在早期 Change 中；除非其作为 contextual 或 preserve constraint 影响当前 design

如果无法根据 Phase 3 finding 和 targeted source context 完成 adjustment，返回 `blocked` 或 `needs-coverage-recheck`，并说明下一步必须运行哪个 Phase。

## refit 方法

Phase 5 必须先 review Phase 4 source-window dossier 和 semantic profile，再建立 atom-driven planning graph。

Phase 5 refit 不是按 atom count 拆分；atom count 只作为后续 complexity signal。必需顺序为：

```text
Phase 4 source-window dossier 与 semantic profile
-> 对 input Change/Capability 作出工程交付判断
-> 确定 final Change 顺序和 Capability 边界
-> 建立 GA-#### final Change ownership/projection/relation/capability-impact mapping
-> 执行 atom count 与 complexity budget 审阅
```

Phase 5 不得从 atom clustering、按 atom count 排序或机械拆分 oversized input Change 开始。必须先判断哪些 source-window-backed business/system outcome 可实现、可测试、可人工 acceptance 且 archive-ready。

### source-window profile 接收

修改计划前读取：

- `phase-works/phase-4/source-window-dossiers/index.md`
- 所有 `phase-works/phase-4/source-window-dossiers/by-input-change/*.md`
- 所有 `phase-works/phase-4/source-window-dossiers/by-input-capability/*.md`
- `phase-works/phase-4/source-window-semantic-profile-review.md`
- `phase-works/phase-4/source-window-grounding-issues.md`
- `phase-works/phase-4/phase-4-agent-report.md`

规则：

- 将 Phase 4 dossier 视为不可变 grounding evidence。
- 每项 accepted、adjusted、split、merge、reorder、rename、moved atom、contextual downgrade、dependency classification、evidence-burden classification 或 non-goal classification 都必须引用 Phase 4 dossier 或 semantic profile 行。
- 如果 Phase 4 报告 `Phase 4 Status: needs-coverage-recheck` 或 `blocked`，停止；不得运行 Phase 5。
- 如果 Phase 4 报告 `grounded`，但 Phase 5 必须判断的 input Change/Capability 缺少必需 source-window profile，则返回 `blocked` 或要求 fresh Phase 4 grounding pass。不得在 Phase 5 中静默重新生成缺失 dossier。
- 如果 Phase 4 source window 表明一个真实 outcome 的 transaction/invariant/protocol/security/compatibility truth 直接需要多个 Capability，即使 atom count 很高，也要保持这些 Capability delta 同组；除非 source-window-backed split 能保持独立 intent、acceptance 和 coherent archive state。
- 如果 Phase 4 source window 表明一个 input Change 混合多个可独立 acceptance 的 business outcome，执行 split、defer，或记录 source window 为何证明不可拆分。
- 如果 Phase 4 source window 显示 technical preparation 但没有可独立验收的 system/engineering outcome 或独立 lifecycle boundary，应用 Foundation Executable Gate，不得将其视为普通 business direct scope。

### source window semantic grounding 门禁

建立 final atom ownership 前，Phase 5 必须根据 Phase 4 source-window semantics 判断初始 Change plan 和每个 candidate final Change。

对初始 Change plan 回答：

- input Change 是否只有一个清晰、source-backed intent，并形成可独立决策、实现、验收和 archive 的 outcome？
- 是否混合了多个可独立批准、推迟、实现、人工 acceptance 并 archive 的 outcome？
- 是否拆开了 source window 表明必须共享同一 transaction、invariant、protocol、security/consistency boundary 或 compatibility contract 的 Capability delta？
- 是否把纯 technical preparation 包装成 business Change，却没有可独立验收的 system/engineering outcome 或独立 deployment/risk/rollback/ownership/review boundary？
- 是否将 domain behavior、user-facing API contract、business worker semantics、entitlement/export concept、project/figure/version semantics 或 recovery/privacy behavior 移入 foundation Change，而不是首个需要它的 business Change？
- 是否有后续 Change 依赖尚未由较早 direct owner 建立的 fact、state、contract、entitlement、version、asset 或 lifecycle rule？
- 每个 Capability 是否具有清晰 Purpose、Owns/Excludes 与 archive durability，还是仅属于临时 implementation-only module、page、table、source section、SDK、queue、provider 或 one-Change alias？stable component/interface contract 不得仅因技术名称被拒绝。
- roadmap order 是否遵循 behavior maturity，还是某个早期 Change 主要收集未来 prerequisite？
- 对 web-system source，早期 product sequence 是否生成薄的 end-to-end user-visible behavior，而不只是 page shell 或 setup/governance bundle？

只有回答这些问题后，Phase 5 才能将 `GA-####` 行映射到 final ownership。此时每个相关 global atom 必须分配：

- `final-owner-type`
- 行为 executable/direct 时恰好一个 final executable Change
- `final-artifact-projection`
- final relation：`direct`、contextual、dependency、evidence-burden、preserve/reference、显式 non-goal、later-change 或 blocker
- `final-capability-impact`：`new`、`modified`、`none` 或仅限 foundation 的 `foundation-substrate`
- `final-target-capability`：`new` / `modified` 使用具体、已声明 Capability，`none` 使用 `none`，`foundation-substrate` 使用 `runtime-substrate-foundation`
- `related-capabilities[]`：唯一、已声明、source-explicit、non-owning supporting association；默认为 `[]` 并排除 target Capability

每个 final Change 都必须通过以下 reviewer-facing gate：

| Gate Question | Required Evidence |
| --- | --- |
| 该 final Change 引用了哪些 source window？ | Phase 4 dossier path 和行范围。 |
| 这些 source window 共同表达了哪些 business/system semantics？ | 中文 source-window semantic profile summary。 |
| 这些 atom 为何应在一个 Change 中交付？ | one-intent、scope cohesion、transaction/invariant/protocol/security/compatibility indivisibility 与 acceptance evidence。zero-domain engineering substrate 的 foundation atom 只属于第一个 executable foundation packet。 |
| 该 Change 为何处在 roadmap 的这个位置？ | upstream realized baseline 和 downstream dependency explanation。 |
| 人工如何 acceptance 已完成的 Change？ | 具体 acceptance scenario 和 observable result。 |
| 哪些 source obligation 被设为 contextual、dependency、evidence-burden、preserve/reference、later-change 或 non-goal，它们为何不属于 direct scope？ | `source-window-refit-trace.md`、`atom-plan-mapping.md` 和 final packet context/non-goal/evidence table。 |

如果 final Change 无法回答全部 gate question，Phase 5 必须 split、merge、reorder、rename、重新分类 atom，或返回 `needs-coverage-recheck` / `blocked`。不得仅因 atom count 位于 target budget 内就接受 final Change。

final refit decision 完成后，使用 Required Mapping Tables 中定义的 table 写入 `source-window-refit-trace.md`。trace 必须明确哪些 Phase 4 source-window-backed atom 被重构到每个 adjusted final Change 中；对 spec delta，还要明确 target Capability。任何 split、merge、reorder、rename、moved atom、contextual downgrade、dependency classification、evidence-burden classification 或 non-goal classification 都必须引用相关 Phase 4 source-window dossier。

### 行为成熟度排序门禁

接受 final order 前，判断 roadmap 遵循的是 behavior maturity，而不是 prerequisite availability。

对典型 web system，早期 product Change 应创建最薄、真实、可观察且可独立验收的 end-to-end behavior。它通常具有 trigger/context、normative behavior、observable outcome/invariant、当前 intent 必需的重要异常语义和 acceptance evidence；不得强制所有 Change 创建持久 fact 或 user-facing projection。静态 UI shell 或 standalone prerequisite collection 通常不满足此 gate。

support、governance 或 operation-heavy Change 只有在下一行为的真实 acceptance 严格需要它，或它本身具有独立 intent、可观察/可验证 outcome 和独立 deployment/risk/rollback/ownership/review boundary 时，才能先于它所支持的行为出现。

如果 Change 主要因后续 Change 将需要它而提前排序，将其 atom 作为 direct/design/evidence burden 移入首个需要它的行为，defer 为 contextual/later-change，或记录具有 source-backed rationale 的 blocker。

### atom-driven 规划图

完成 source-window profile intake 后，建立 atom-driven planning graph：

| Global Atom ID | Source Obligation | Current Candidate Owner Change | Current Capability Impact | Current Target Capability | Current Related Capabilities | Current Artifact Projection | Dependency Atoms | Candidate Final Change | Candidate Final Capability Impact | Candidate Final Target Capability | Candidate Final Related Capabilities | Candidate Final Artifact Projection | Sequence Impact | Complexity Impact | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

使用以下规则：

- final executable Change 应围绕一个 source-backed intent，形成可 review、可实现、可验证、可独立完成和 archive 的 outcome。
- final Change 也是后续 AI agent 在一次聚焦 `openspec-apply-change` pass 中实现的单元。仅有行为相关性不足以证明大型 Change 合理。
- foundation handling 必须通过 Foundation Executable Gate；如果存在第一个 executable foundation Change，business sequence 必须从其后开始。
- 不得仅因可 unit-test，就把 reusable contract、UI state vocabulary、object specimen、design token system、visual harness 或 async scaffold 拆成 standalone Change。它们需要独立 intent、可验收 system/engineering outcome 与独立生命周期边界，或成为 consumer Change 的 design/task/evidence burden 一部分。
- 只有 atom 服务同一 intent、scope cohesive，并共享不可分割的 transaction/invariant/protocol/security/compatibility truth 或 acceptance evidence 时，才将 atom 附加到同一 Change。
- atom group 暴露可独立批准、推迟、实现、验证、review 和 archive 的 outcome 时，添加或拆分 Change。
- 只有 atom 表明多个 Change 拆开了不可分割的 transaction/invariant/protocol/security/compatibility truth，且任何一侧缺少另一侧都会形成无意义 half-state 或无法真实 archive 时，才合并 Change。
- atom dependency 表明后续 Change 依赖当前引入过晚的 prerequisite 时，重排 Change。
- atom 增强同一持久 behavior boundary 时，将其保留在现有 Capability 中。
- atom 暴露缺失、混合、过于技术化或分配给错误长期 behavior boundary 的持久 behavior boundary 时，添加、拆分、合并或重命名 Capability。
- 不得仅为减少 Change 涉及的 Capability column 数量而添加、拆分、合并或重命名 Capability。即使每个 Change 仍很小，把持久 behavior boundary 变成 one-Change alias 的 refit 也无效。
- 选择最早实现 production obligation 的 owner Change，解决 duplicate direct atom。后续 Change 只有在增加 source-backed delta 时才能保留 direct atom；否则转为 preserve/dependency/reference/context。
- 用不同 atom 表示 staged maturity；不得跨 Change 重复同一 atom 来模拟 progression。
- 将较早 Change 视为 realized baseline provider，而不是 global-context catchall。
- 在首个直接实现未来 domain behavior 的 business Change 前，将其视为 contextual 或 downstream constraint。不得仅因后续 Change 依赖 contract，就让 foundation 或早期 technical Change 拥有 direct atom。
- 独立于 final owner Change placement 保留 artifact projection。direct atom 可以由 Change implementation-own，同时投影到 design、task/proof 或 spec guard，而不是成为 spec requirement；final direct table 中不得继续为 `contextual-only`。
- 只为具有具体 target Capability 的 direct `spec-requirement` / `spec-guard` 行分配 `new` / `modified`。普通 direct design/verification 行和所有 non-direct 行分配 `none` / `none`，但不得降低其 Change ownership。
- 只有引用 source window 明确将 atom 与稳定 Capability ID 关联时，才保留 `related-capabilities[]`。related ID 绝不影响 Change ownership、progression、Capability view 或 complexity count。
- 如果每个 slice 都具有 source-backed intent、独立 acceptance 和 coherent archive state，可优先采用 input preparation -> core result/state transition -> async execution -> external integration -> richer projection -> hardening/delivery/operations 等 staged slice；该顺序只是 source-constrained heuristic。
- 多个 cross-Capability increment 共享同一 intent 和不可分割的 transaction/invariant/protocol/security/compatibility truth 时，将直接必需的 increment 保留在同一 Change 中。不得仅为缩窄 matrix 行，把 identity、privacy、realtime state、versioning、entitlement、export、failure recovery 或 observability atom 移入人为 standalone Change。
- 重建 `New`/`Modified` label 和 Capability advancement surface 时，应用以下 Capability Relation Invariant。

### Capability relation 不变量

final refit 后，丢弃 Phase 1 `first-advancement` / `later-advancement` hypothesis，先确定 source-backed final target Capability，再只读核对当前 repository baseline，最后写入显式 Phase 5 `final-capability-impact` 和 `final-target-capability`。不得从 Change ownership、artifact count、related Capability、Phase 1 roadmap role 或 renderer order 推断 impact。

- business progression 只消费 impact 为 `new` 或 `modified`、target 为具体已声明 business Capability 的 direct `spec-requirement` / `spec-guard` 行。
- 每个 `(final-owner-change, final-target-capability)` pair 的所有 contributing 行必须使用相同 impact。一个 pair 混用 `new` / `modified` 无效。
- 对每个 final target 必须记录 `Repository Baseline: existing | absent` 和可复查 evidence。`existing` 表示当前存在精确路径 `openspec/specs/<capability>/spec.md`；`absent` 表示只读 inventory 后该精确 target 不存在。
- baseline 为 `existing` 时，roadmap 中首次及后续每个 source-backed delta 都必须使用 `modified`。
- baseline 为 `absent` 时，roadmap 中首次 source-backed delta 必须使用 `new`；只有在 roadmap 明确要求前序 Change 先 sync/archive 后，后续 delta 才使用 `modified`。
- 同一 target 最多出现一个 `new`；若出现，必须位于该 target 的第一个 advancement。向 existing Capability 新增 requirement 仍是 Capability-level `modified`，requirement-level operation 可以是 `ADDED`。
- renderer 或 reviewer 必须验证这些显式值，不得根据首次出现位置静默推导或修复。
- dependency-only、preserve-only、upstream-baseline、downstream-constraint、contextual、evidence-burden、reference、later-change 和 non-goal relation 不计入 Capability advancement。
- 普通 direct `design-obligation` / `verification-obligation` 行使用 `none` / `none`；source-explicit `related-capabilities[]` 保持 non-owning，不计入 advancement。
- target 为 `runtime-substrate-foundation` 的 `foundation-substrate` 是唯一 non-spec special case。它拥有专用 foundation view，但不进入 business `New` / `Modified` progression。
- Capability Map `First Advancement`、第一个非空 matrix cell、第一个 roadmap advancement、baseline reconciliation、final packet target/impact metadata、第一个 anchor-index occurrence、Capability view 和 human plan 必须全部一致；只有 absent baseline 的首次 advancement 才应显示 `New`。
- 如果唯一问题是 stale label，repair Phase 5 canonical mapping/config 并重新渲染。如果 mismatch 反映 final Change ownership 或 Capability target/impact 含糊，返回 `needs-coverage-recheck` 或 `blocked`。

## Capability progression 审阅

编辑 final plan artifact 前，先完成 repository baseline reconciliation，再评估 Capability atom progression：

| Capability | Repository Baseline | Baseline Evidence | Atom Families | Current Change Sequence | Required Relation Sequence | Sequence Problem | Adjustment |
| --- | --- | --- | --- | --- | --- | --- | --- |

规则：

- absent Capability 中创建 behavior boundary 的 baseline atom 必须先于 refinement、hardening、extension 或 preserve-only atom 出现；existing Capability 不得重新标为 `new`。
- 当前 outcome 真实成立所必需的 exception/error、acceptance、auth/privacy、security、compatibility 和 data integrity atom 必须出现在首个适用 Change 中。
- 后续 Change 只有具备 source-backed delta 时，才可 refine 或 harden 早期 atom。
- 只 preserve 或依赖早期 atom 的后续 Change 不得把该 Capability 列为 advanced。
- 如果 Capability 包含多个无关 atom family，只有它们属于持久 behavior boundary、而不是临时 implementation area 时，才拆分 Capability。
- `Current Change Sequence` 必须按 roadmap 顺序，根据显式 final `new` / `modified` target-Capability pair 计算。排除仅归属 Change 的 design/verification 行、related-only mention、dependency-only 行和 contextual mention。
- `Required Relation Sequence` 必须应用 repository baseline：`existing -> modified+`；`absent -> new, modified*`。
- 如果 plan surface 不一致，在返回 `accepted` 或 `adjusted` 前 repair canonical mapping/config 并重新渲染；如果 final Change ownership 或 spec target/impact 不明确，返回 `needs-coverage-recheck` 或 `blocked`。

## Change complexity 审阅

最终定案前评估 Change complexity：

| Change | Direct Atom Count | Artifact Projection Mix | Atom Groups | New Capabilities | Modified Capabilities | Primary Intent/Outcome Count | Trigger/Outcome/Invariant Families | Exception/Error Families | Evidence Types | Surface Families | Foundation/Business Gate Status | Budget Status | Complexity Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

将 direct atom count 用作 complexity signal，而不是 source coverage goal。fine-grained atom 是预期结果，但包含大量 direct atom 的 final Change 仍会带来 implementation、review 和 archival risk。

规则：

- target budget：20–60 个 direct atom、一个 primary intent/outcome、仅包含直接必需的 Capability delta、最多两个 primary surface family，以及紧凑 evidence burden。当多个 new/modified Capability delta 都是同一不可分割 outcome 的必需项时，可以超过一个。
- `New Capabilities`、`Modified Capabilities` 和 unrelated Capability over-budget trigger 只根据互不相同的显式 `new` / `modified` target Capability 计数。排除 `none`、`foundation-substrate` 和所有 `related-capabilities[]` entry。
- over-budget trigger：任何 Change 包含超过 80 个 direct atom、超过 4 个无关且被直接推进的 Capability、incoherent artifact projection mix、超过 12 个 exception/error atom、超过 2 个 independent trigger/outcome family、超过 3 个 evidence type 或超过 3 个 surface family 时，必须拆分、defer，或用具体 indivisibility evidence 证明合理。related cross-cutting Capability delta 不会仅因数量触发 over-budget。
- hard split/blocker trigger：任何 Change 包含超过 120 个 direct atom，或超过 6 个不共享同一 intent、transaction/invariant/protocol/security/compatibility truth 的无关且被直接推进 Capability，都不得原样标记为 `accepted` 或 `adjusted`。Phase 5 必须拆分、把 atom 移到后续 Change/context，或返回 `blocked` 由用户决定 slicing。
- over-budget Change 的 `Keep` decision 必须列出被拒绝的 split candidate，并解释各自为何破坏 truthfulness。"One coherent outcome"、"shared infrastructure" 或 "packet-level evidence grouping" 本身都不足以作为理由；必须给出具体 indivisibility evidence。
- 不得仅因 direct atom count 超出 target range 就拆分 Change。只有 Source Window Semantic Grounding Gate 显示存在不同 intent、可独立 decision/acceptance/archive 的 outcome、invalid sequencing、false foundation ownership、non-durable Capability boundary、incoherent evidence surface 或无关 transaction/invariant/protocol/security/compatibility truth 时才拆分。
- Change 包含多个可独立通过 one-intent、independent decision/archive 和 acceptance gate 的 atom group 时拆分。
- Change 仅因 shared infrastructure 便于分组而推进许多 Capability 时拆分。
- evidence burden 跨越许多无关 proof surface、会导致 review/archive 含糊时拆分。
- 拆分会强制产生虚假 stub、破坏同一 transaction/invariant/protocol/security/compatibility truth、产生无意义 half-state 或使任一侧无法独立验收时，保持 Change 整体。
- 将最早的 minimal runnable、可独立验收 production outcome 作为第一个 executable Change；只 defer 不属于该 outcome production truth 必需项的 atom。
- preparation state 无需执行 downstream job 就能保存、再次访问、验证和检查时，将 input preparation 与 downstream execution 拆开。
- adapter contract、deterministic sandbox 或 integration-disabled path 可真实验证，且 concrete integration 可作为后续 direct Change 添加时，将 external integration 与 command/job/result semantics 拆开。
- durable result/state transition 可独立于更丰富 projection outcome 验证时，将 result projection、history 或 interaction surface 与 upstream execution 拆开。
- 除非 access/quota enforcement、delivery、observability 和 operation atom 是使当前 feature 行为真实所必需，而不只是使未来 production-complete 所需，否则将其从 feature Change 中拆出。
- 不得仅因 Change 推进多个 Capability 就拆分。如果拆分会让每个新 Change 只成为名称相似 Capability 的别名，应保留真实不可分割 outcome 或重新设计 boundary，并记录原因。

### Foundation 可执行性门禁

foundation candidate 仅可作为 minimal enabling scaffold，并且只能作为第一个 executable final Change 输出。将以下规则作为 Phase 5 plan acceptance 的 hard gate：

- terminal Phase 5 plan 最多包含一个 foundation candidate。符合条件时，Phase 5 将其写为第一个 final packet 和 `final-packet-index.json` 第一行，并使用 `change-kind: foundation`。
- business Change 使用 `change-kind: business`。technical foundation Capability `runtime-substrate-foundation` 可以出现在 foundation packet 和 Capability view 中，但不得计入 business Capability `New` / `Modified` progression。
- `atom-plan-mapping.json` 中 foundation direct 行必须使用 `final-owner-type: executable-change`、`final-owner-change: <foundation-change-slug>`、`final-capability-impact: foundation-substrate`、`final-target-capability: runtime-substrate-foundation` 和 `final-relation: direct`。其 `related-capabilities[]` 遵循与其他行相同的 source-explicit、non-owning 结构规则。
- `foundation-substrate` 是允许 `design-obligation` / `verification-obligation` 行获得非 `none` capability impact 的唯一例外。它只用于派生专用 foundation view，绝不进入 business progression 或 advanced-Capability count。
- foundation Change 只能包含 zero-domain engineering substrate：repository/package skeleton、package/app boundary、root script、lint/typecheck/test harness、configuration loading、local dependency manifest、不含 business schema 的 migration tooling、空 adapter seam、空 web/worker smoke entrypoint、environment/deploy convention 和 smoke/conformance proof expectation。
- foundation atom 保留原始 source trace 和 artifact projection，通常为 `design-obligation`、`verification-obligation` 或 `spec-guard`。只有后续 proposal artifact 表达 foundation Change 当前可观察的 engineering substrate fact 时，才能生成相应 spec、runtime acceptance、verification 和 task。
- direct domain behavior、business table creation、user-facing API contract、worker/async business semantics、identity/authorization/tenancy mapping、entitlement/accounting/delivery/export concept、lifecycle/versioning rule、operational observability、privacy workflow、recovery behavior、responsive behavior、visual quality 或 design-system behavior 必须移入首个直接需要它们的 business Change。
- action/job runtime、UI stage/overlay contract、object disabled-state governance、design token、responsive proof、observability、privacy 或 quota policy 等 low-level/governance-heavy atom group 必须附加到首个直接需要它们的 business outcome；除非 source evidence 支持独立 intent、可验收 operational/system outcome 和独立 lifecycle boundary。
- 如果计划包含多个 pre-business foundation/governance candidate，必须将其合并到唯一 executable foundation Change、移入 business Change、defer 为 contextual/evidence burden，或返回 `blocked`。

### 必需拆分分析

对每个 over-budget trigger，在 final decision 前编写 split analysis：

| Change | Trigger | Candidate Split | Atoms / Capabilities Moved | Resulting Intent/Outcome | Acceptance Evidence | Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

candidate split pattern 包括：

- 仅含 scaffold 的 foundation candidate -> executable foundation Change + 首个 production 业务 workflow
- domain foundation/spine candidate -> zero-domain executable foundation Change + 拥有 domain atom 的首批业务 workflow
- 输入采集/校验/准备 -> 下游执行
- command/job contract -> 具体 executor 或外部 integration
- durable result fact 创建 -> 结果 projection/history/interaction surface
- 核心 outcome -> 可独立决策/部署的 access control、quota、delivery、observability 或 hardening outcome
- 面向用户的 workflow -> 具有独立 intent/acceptance 的 admin、reconciliation、maintenance 或 operations outcome
- 同步 happy path -> async processing、retry、recovery 或 audit trail

禁止的 split pattern 包括：

- Capability-column split：仅因 atom 属于多个 Capability，就把一个不可分割 outcome 拆成多个独立 Change
- same-name alias split：创建语义互为改写的新 Change 和新 Capability
- cross-cutting concern evacuation：仅为减少 Capability count，把 identity、privacy、realtime state、versioning、entitlement、export、failure recovery 或 observability atom 移出直接需要它们的 outcome

## Change/Capability 耦合门禁

最终确定 `accepted` 或 `adjusted` 前，audit final matrix shape：

| Check | Signal | Required Action |
| --- | --- | --- |
| 对角 roadmap | 大多数 Change row 恰好只有一个非空 Capability cell | 作为 diagnostic 重新评估 Change 是否按 Capability 列机械切分；只有 one-intent/cohesion/independent archive gate 失败时才调整，不能仅为改变矩阵形状而改写真实 boundary。 |
| 单一 Change 的 Capability | 许多 Capability 恰好只由一个 Change 推进 | 重新执行 Purpose、Owns/Excludes、implementation-substitution 和 archive-durability gate；一个 source-backed、持久但当前只推进一次的 Capability 可以合法保留。 |
| 名称别名 | Capability id 改写了推进它的唯一或首个 Change | 围绕持久行为边界重命名、合并到更广的 Capability，或记录 blocker。 |
| 丢失横切 delta | 某个 outcome 不再直接推进其真实成立所必需的 auth/privacy/realtime/versioning/entitlement/failure/export/observability 行为 | 将这些 atom 作为 direct delta 移回 outcome Change，除非它们仅为 contextual 或 preserve constraint。 |
| budget 导致的对角化 | 拆分决策减少 Capability 数量，却使 Change 成为 Capability 别名或破坏 source-backed indivisibility | 拒绝拆分；保留跨 Capability outcome，并提供具体的不可拆分分析。 |

规则：

- single-Capability Change 可以合法存在；其 boundary 仍必须由 source-backed intent、cohesion、independent archive 和 acceptance 解释，而不是由 Capability 名称解释。
- 只由一个 Change 推进的 Capability 可以合法存在；progression review 必须说明其持久 Purpose 与 archive durability，不得为证明“未来还会变化”而发明 later expansion。
- diagonal matrix 只是需要复核的形状，不是 blocker。只有具体 Change/Capability gate 失败、且无法 source-backed refit 时，才返回 `blocked`。
- Phase 5 report 必须概括此 audit，明确矩阵形状是否来自真实 boundary；不得把“非对角”本身当作质量目标。

## 有效 Change 计划要求

final `change-plan.md` 必须包含：

### 输入

- 已阅读的 source document
- Phase 3 global atom index 路径
- Phase 5 工作路径
- assumption 和 conflict

### Capability Map

| Capability | Purpose | Owns | Excludes | Repository Baseline | Baseline Evidence | First Advancement | Source-backed Later Advancement |
| --- | --- | --- | --- | --- | --- | --- | --- |

规则：

- Capability ID 必须是稳定的英文 kebab-case ID。
- Purpose、Owns 和 Excludes 说明持久行为边界，而不是 implementation-only module。
- `Repository Baseline` 与 `Baseline Evidence` 必须来自只读 `openspec/specs/` reconciliation。
- `First Advancement` 和 `Source-backed Later Advancement` 必须遵循 Capability Relation Invariant，并由 direct global atom 支撑；没有 later delta 时明确写 `无已知 source-backed later delta`，不得发明未来 Change。
- Capability ID 不得只是改写 final Change slug。如果 Capability 只有一个 final direct Change，记录它为何是持久 terminal boundary，或执行 refit。
- 不含 business spec delta 的计划可以使用 `capabilities: []`。保留 `Capability Map` heading 并写入 `无业务 Capability delta`；不得输出格式错误的空表或发明 technical Capability。符合条件的 foundation 仍是单独 special case。

### Capability Progression Matrix

| Change | `capability-a` | `capability-b` | `capability-c` |
| --- | --- | --- | --- |
| `change-name` | 具体 atom-backed increment |  | 具体 atom-backed increment |

规则：

- matrix cell 只包含 direct `New` 或 `Modified` advancement。
- dependency、preserve、reference-only 和 contextual relation 属于 note，不属于 matrix cell。
- matrix exclusion 不等于 coverage exclusion。每个被排除且具有 final owner Change 的 non-direct atom 仍必须显式出现在该 Change final packet 的 context/dependency/evidence/preserve/non-goal handling 中。
- 每个非空 cell 必须由一个或多个 global atom ID 支撑。
- 首个和后续非空 cell 必须遵循 Capability Relation Invariant，并与 roadmap relation label 和 final packet ownership 匹配。
- matrix 必须通过 Change/Capability Coupling Gate。大部分为 diagonal 时必须执行 diagnostic，但只要每个独立 boundary gate 通过即可保留。
- `capabilities: []` 时，保留 `Capability Progression Matrix` heading 并写入 `无业务 Capability delta`；不得输出 Capability column，也不得从仅归属 Change 的行推断 progression。

### Change Roadmap

每个 final Change 包含：

- Change 名称：
- 单一 intent：
- source-backed outcome：
- source-window grounding：
  - 输入 source-window dossier：
  - source-backed semantic profile：
  - refit trace：
- source window semantic grounding 门禁：
  - 引用的 source window：
  - 合并后的 business/system 语义：
  - 这些 atom 应归在一起的原因：
  - 该 roadmap 位置有效的原因：
  - 人工 acceptance scenario：
  - non-direct obligation 的处理方式：
- direct atom 分组：
- Capability 变更：
  - New:
  - Modified:
- 范围内：
- 范围外：
- behavior completeness profile：
  - trigger/context：
  - normative behavior：
  - observable outcome / invariant：
  - important exception / error semantics：
  - acceptance evidence：
- 依赖：
- contextual atom / downstream design constraint：
- 非目标：
- complexity budget：
  - direct atom 数量：
  - 推进的 Capability：
  - surface family：
  - 证据类型：
  - foundation/business 门禁状态：
  - budget 状态：
  - split/defer 分析：
- 归档就绪性：

roadmap relation 规则：

- `New` 和 `Modified` list 必须从显式 `final-capability-impact` / `final-target-capability` pair 推导，遵循 Capability Relation Invariant，并与 final packet 和 `change-capability-anchors/index.md` 匹配。
- Phase 5 split、merge、rename、reorder 或重新映射 atom ownership 时，必须在 final packet 派生后重新生成所有 roadmap relation label。不得沿用 Phase 1 label。
- 每个 final Change 必须引用证明其 intent、source-backed outcome、independent archive boundary 和 order 合理的 input source-window dossier 和 refit trace 行。仅含 atom-count 或 Capability-count rationale 的 final Change 不完整。

## final Change packet

每个 `change-capability-anchors/<change-slug>/<change-slug>.md` final packet 必须包含：

- Change 名称
- 单一 intent 与 source-backed outcome
- source-window grounding 链接和 semantic profile 摘要
- source window semantic grounding 门禁回答摘要
- 按 spec target Capability 或仅归属 Change 的 artifact projection 分组的 final direct owner atom
- 每个 direct atom 的 final artifact projection
- 影响当前 design 的 contextual atom 和 future constraint
- 较早 Change 的 upstream realized baseline atom
- 不得在 design 中移除的 downstream constraint
- 显式 non-goal
- complexity budget status、over-budget trigger 和 split/defer decision
- executable roadmap status 和 foundation executable handling summary
- 证据负担
- source atom、source-window dossier、source-window refit trace 和 global atom index link
- blocker，或 `None`

direct atom table：

| Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Artifact Projection | Projection Rationale | Capability Impact | Target Capability | Related Capabilities | Atom Relation | Roles | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

所有 final packet `Global Atom ID` 值都必须保留 `change-capability-anchors/obligation-atom-index.md` 中完全相同的 `GA-####` ID；Phase 5 不得改写为其他 global 前缀或 source-local atom ID。

direct table 行必须使用 `spec-requirement`、`spec-guard`、`design-obligation` 或 `verification-obligation`。`contextual-only` 只属于 context table 或 non-direct classification。

direct table Capability field 必须与 canonical `atom-plan-mapping.json` 匹配。business `new` / `modified` 行必须是具有具体 target 的 spec projection；普通 design/verification 行必须显示 `none` / `none`；related Capability 必须 source-explicit、唯一且 non-owning。空 related array 渲染为 `None`。

context table：

| Global Atom ID / Relation | Source Document | Lines | Context Type | Affects Current Design Because | Handling |
| --- | --- | --- | --- | --- | --- |

context table 或同一 final packet 内按 relation 划分的等效 table，必须包含 `atom-plan-mapping.md` 中 `Final Owner Change` 为此 Change 的每个 non-direct 行。这包括 contextual、dependency、evidence-burden、preserve/reference、显式 non-goal、later-change 和其他 non-direct relation。每个 atom 必须作为独立显式 `GA-####` 行出现，包含 source document、行范围、relation/context type、影响当前 design 或 scope 的原因及 handling。不得截断、summary、aggregate，也不得用 count-only 行、`additional-context` 或 link-only placeholder 替代显式 non-direct atom 行。table 很大时，可在同一 packet 内按 relation type 拆分，但每个 atom 仍必须保留一条显式行。

每个 business `change-capability-anchors/<change-slug>/capability-anchors/<capability-slug>.md` file 都是派生 spec-advancement view。它只能包含 final Change packet 中 `final-target-capability` 为该 Capability、`final-capability-impact` 为 `new` 或 `modified` 的 direct `spec-requirement` / `spec-guard` atom。仅归属 Change 的 design/verification 行、related-only association 和 non-direct constraint 保留在 final Change packet 中，不进入 Capability view。唯一例外是专用 `runtime-substrate-foundation` view，其中包含第一个 foundation Change 的 direct `foundation-substrate` 行。

Capability atom table：

| Capability | Change | Capability Impact | Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Artifact Projection | Relation | Propose Use | Evidence Need |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

derived-view invariant：

- 每个 Capability 行必须在 final Change packet 中有匹配的 direct 行。
- target Capability 为该 Capability 且 impact 为 `new` 或 `modified` 的每个 direct spec atom，都必须出现在 business Capability file 中；每个 direct `foundation-substrate` atom 都必须出现在专用 foundation view 中。
- Capability file 不得重命名 atom、改变 source 行范围、改变 artifact projection，或独立拆分/合并 source fact。
- 一个 Change 下的 business Capability file 集合，必须与其互不相同且显式的 `new` / `modified` target Capability 完全匹配。不得为仅归属 Change 的 design/verification 行、related-only、dependency-only、preserve-only 或 contextual-only Capability 添加额外 file。foundation Change 只能添加专用 `runtime-substrate-foundation` view。
- Capability file 不得包含 related-only、contextual、dependency、evidence-burden、preserve/reference、显式 non-goal、later-change、upstream-baseline 或其他 non-direct 行。business view 还必须排除仅归属 Change 的 design/verification 行。这些行不计入 Capability advancement，但必须显式保留在所属 final Change packet 中。

## final Capability relation 一致性检查

返回 `accepted` 或 `adjusted` 前，Phase 5 必须跨 final plan 和 derived anchor 运行 consistency check。将结果写入 `phase-works/phase-5/alignment-final-report.md`，并在 `phase-works/phase-5/phase-5-agent-report.md` 中概括。对于 `needs-coverage-recheck` 或 `blocked`，不得写入 `alignment-final-report.md`；在 `phase-5-agent-report.md` 和 `change-plan-adjustments.md` 中记录 source-window-backed recheck 或 blocker 原因。

必需 comparison：

| Capability | Repository Baseline | Baseline Evidence | Capability Map First Advancement | First Explicit Impact From Packets | First Matrix Cell | First Roadmap Advancement | First Anchor Index Occurrence | Later Explicit Impacts | Result | Repair If Failed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

规则：

- 所有 comparison column 必须满足 Capability Relation Invariant。
- 除非 Change packet 中至少一个 direct spec atom 将某 business Capability 设为 `final-target-capability` 且 impact 为 `new` 或 `modified`，否则该 Capability 不得出现在 `change-capability-anchors/index.md` 中。唯一例外是 direct `foundation-substrate` 行对应的 `runtime-substrate-foundation`。
- Phase 5 返回 `accepted` 或 `adjusted` 前必须检查 packet-level non-direct coverage：每个具有真实 `Final Owner Change` 的 non-direct `atom-plan-mapping.md` 行，都必须作为显式 `GA-####` 行出现在该 Change final packet 的 context/dependency/evidence/preserve/non-goal handling 中。
- Phase 5 返回 `accepted` 或 `adjusted` 前必须检查 Capability-view purity：每个 business view 行必须为 direct、spec-projected，并以 `new` / `modified` impact 匹配 view target；每个 foundation view 行必须使用 `foundation-substrate`；每行都必须有匹配 direct packet 行；任何仅归属 Change、related-only 或 non-direct atom 都不得只出现在 Capability view 中。
- 如果唯一问题是 stale label，在不修改 Phase 2/Phase 3 evidence 的情况下 repair Phase 5 artifact。
- 如果 mismatch 表明 final Change ownership 或 spec target/impact 含糊或矛盾，返回 `needs-coverage-recheck` 或 `blocked`；不得把 Phase 5 标为 `accepted` 或 `adjusted`。

## 工作流

1. 读取 Phase 3 `phase-works/phase-3/coverage-review.md` decision 和 global atom index。
2. 读取 Phase 4 `phase-works/phase-4/phase-4-agent-report.md`，确认 `Phase 4 Status: grounded`。
3. 读取 Phase 4 source-window dossier、semantic profile 和 grounding issue。
4. 读取 Phase 3 handoff item，尤其是标记为 `phase-5-refit-required` 的 atom、ownership ambiguity 和 source-backed non-direct constraint。
5. 确保 `phase-works/phase-5/` 存在。对 `accepted` 或 `adjusted` terminal output，将 Phase 4 `input-change-plan.md` 覆盖复制到该目录；对 `needs-coverage-recheck` 或 `blocked`，在 `source-window-refit-trace.md` 中记录 input plan reference，不要求 terminal input snapshot。
6. 使用 global atom index 和 Phase 4 source-window semantic profile 建立 atom-driven planning graph。
7. 对每个 candidate final Change 应用 implementation-ready complexity gate、Foundation Executable Gate、必需 split analysis 和 Change/Capability Coupling Gate。
8. 决定 Phase 1 framework 是 accepted、adjusted、needs coverage recheck 还是 blocked。
9. 写入 `phase-works/phase-5/source-window-refit-trace.md`，说明 Phase 4 input Change/Capability source window 和 atom 如何重构为 final Change/Capability。
10. accepted 或 adjusted 时，写入 `phase-works/phase-5/change-plan.md`、canonical `phase-works/phase-5/atom-plan-mapping.json`、rendered `phase-works/phase-5/atom-plan-mapping.md` 和 `phase-works/phase-5/final-packet-index.json`。status 为 `needs-coverage-recheck` 或 `blocked` 时，跳过 terminal mapping/final packet artifact，在 `change-plan-adjustments.md` 中写入 blocker 或 recheck rationale。
11. accepted 或 adjusted 时，在 Phase 5 snapshot 和 mapping 写入后，将相同内容写入根 `openspec/orchestrate/change-plan.md`，作为 latest effective plan。
12. accepted 或 adjusted 时，写入 `phase-works/phase-5/capability-progression-review.md`、`change-complexity-review.md` 和 `plan-refit-decision-log.md`。
13. status 为 `adjusted`、`needs-coverage-recheck` 或 `blocked` 时，写入 `phase-works/phase-5/change-plan-adjustments.md`，包含 plan-impact 和 next-action summary。
14. status 为 `accepted` 或 `adjusted` 时，根据 global atom index、source-window refit trace 和 final plan 派生 final `change-capability-anchors/<change-slug>/` packet 和 Capability view。final Change packet 必须显式列出每个归属 Change 的 direct atom 和 owner-scoped non-direct atom。business Capability view 只包含对应 target 的 direct `new` / `modified` spec atom；专用 foundation view 只包含 `runtime-substrate-foundation` 的 `foundation-substrate` 行。
15. accepted 或 adjusted 时，写入 `change-capability-anchors/index.md`。
16. accepted 或 adjusted 时，写入 canonical `capability-baseline-reconciliation.json` 并渲染 matching Markdown，运行 Final Capability Relation Consistency Check 和 packet-level non-direct coverage check。repair canonical mapping/config value，再重新渲染 stale baseline、`First Advancement`、matrix cell、roadmap `New`/`Modified` label、final anchor index 行、Capability view、final packet context/evidence/dependency/non-goal 行和 human-plan summary。不得让 renderer 根据 order 推断 `new` / `modified`。
17. status 为 `accepted` 或 `adjusted` 时，将 `phase-works/phase-5/change-capability-human-plan.md` 写成 final Change packet 和 Capability progression 的可读 synthesis。
18. 始终写入 `phase-works/phase-5/phase-5-agent-report.md`。仅在 status 为 `accepted` 或 `adjusted` 时写入 `phase-works/phase-5/alignment-final-report.md`。
19. 结束前，通过 inspection 或 deterministic parsing 运行 local artifact consistency check。

## 必需 mapping 表

`phase-works/phase-5/source-window-refit-trace.md` 必须包含：

| Input Change / Capability | Source Window Evidence | Input Atoms | Final Change / Target Capability | Atom Movement | Relation Changes | Engineering Reason |
| --- | --- | --- | --- | --- | --- | --- |

canonical `phase-works/phase-5/atom-plan-mapping.json` 必须包含每个 global atom mapping 行。rendered `phase-works/phase-5/atom-plan-mapping.md` 必须使用以下 table：

| Global Atom ID | Source Document | Lines | Phase 3 Owner / Status | Phase 3 Artifact Projection | Final Owner Type | Final Owner Change | Final Capability Impact | Final Target Capability | Related Capabilities | Final Artifact Projection | Final Relation | Plan Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

rendered mirror 还必须包含 `Trace Appendix`，其中列出 trace file、trace schema、trace sha256 和 render contract `source-aligned-render-v2`。

`phase-works/phase-5/plan-refit-decision-log.md` 必须包含：

| Decision Item | Input Evidence | Candidate Options | Decision | Output Artifact | Reason |
| --- | --- | --- | --- | --- | --- |

`change-capability-anchors/index.md` 必须包含：

| Change | Change Packet | Capability Views | Direct Atoms | Contextual Atoms | Capabilities Advanced | Complexity Budget | Evidence Burden | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

`phase-works/phase-5/change-capability-human-plan.md` 必须包含可读的 Change packet：

| Change | Intent / Outcome | Source-Window Grounding | Direct Atom Groups | Complexity Budget | Contextual Atoms / Future Constraints | Upstream Realized Baseline | Downstream Constraints | Non-Goals | Evidence Burden | Ledger Links |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

还必须包含 Capability progression narrative：

| Capability | Repository Baseline | First Advancement | Source-backed Later Advancements | Atom Progression Summary | Human Review Notes |
| --- | --- | --- | --- | --- | --- |

## Phase 5 报告

`phase-works/phase-5/phase-5-agent-report.md` 必须包含：

| Refit Finding | Source Ranges or Atoms | Plan Decision | Files Written | Atom Resolution | Remaining Gap or Blocker |
| --- | --- | --- | --- | --- | --- |

还必须包含：

- 初始计划是 accepted 还是 adjusted
- Phase 4 source-window dossier intake summary，包括覆盖的 input Change/Capability 和影响 refit 的 grounding issue
- Phase 4 source-window semantic profile usage summary，包括哪些原始 source semantics 驱动 split、merge、reorder、rename、contextualization、dependency、evidence-burden 或 non-goal decision
- 面向 final Change 的 Source Window Semantic Grounding Gate summary，包括被拒绝的 split/merge/reorder option，以及 atom count 为何构成或不构成有效 complexity concern
- atom-driven planning graph 摘要
- Capability progression 重新校准摘要
- Change complexity 重新校准摘要
- Change/Capability coupling gate summary，包括 final matrix 是否避免 capability-driven one-to-one slicing
- new、split、merged、removed、reordered 或 renamed Change
- new、split、merged、removed 或 renamed Capability
- moved、reclassified 或保持 contextual 的 atom
- 确认每个 executable direct global atom 都恰好有一个 final owner Change；普通 design/verification atom 使用 `none` / `none`；每个 foundation direct atom 都由第一个 executable foundation Change 以 `foundation-substrate` / `runtime-substrate-foundation` 拥有
- 确认每个 direct global atom 都有 final artifact projection
- 确认没有把 `design-obligation` 和 `verification-obligation` atom 强制改为 `spec-requirement`
- 确认 `new` / `modified` 只出现在具有具体 target 的 direct spec projection；每个 `(Change, target Capability)` pair 都有一个一致 impact；existing baseline 使用 `modified+`，absent baseline 使用 `new, modified*`；accepted/adjusted 行中没有剩余 `unresolved`
- 确认 `related-capabilities[]` 值唯一、已声明、source-explicit、不同于 target，并排除在 ownership、progression、Capability view 和 advanced-Capability complexity count 之外
- 确认 `atom-plan-mapping.md` 中每个 owner-scoped non-direct atom 都显式出现在所属 final Change packet 中，没有仅通过 count、summary、`additional-context`、Capability view 或 link-only placeholder 表示
- 确认 business Capability view 只包含对应 target 的 direct `new` / `modified` spec atom，foundation view 只包含 `foundation-substrate` 行；仅归属 Change/non-direct constraint 保留在 final Change packet，而不是 Capability view 中
- 确认 final business Capability relation 只包含显式 `New` / `Modified` spec advancement，renderer 未根据 order 推断
- 确认 refit 后 Capability Map `Repository Baseline` / `First Advancement`、progression matrix 首个 cell、roadmap `New`/`Modified` label、final packet capability impact/target、Capability view、anchor index 和 human plan 全部一致
- 确认 diagonal matrix 已作为 diagnostic 审阅，且没有 capability-driven/same-name slicing；矩阵形状本身未被当作 blocker 或优化目标
- 确认 Change packet 包含 upstream baseline 和 downstream design context，且没有把 future scope 拉入当前 direct ownership
- 确认 final Change complexity 为 implementation-ready，或已提供 split option 并显式 blocked
- 确认每个 over-budget trigger 都已 split、defer，或具有具体 indivisibility analysis
- 确认 foundation candidate 已转换为使用 `change-kind: foundation` 的第一个 executable foundation packet，或无需 foundation Change
- 确认 foundation atom 不计入 business Capability progression，且后续 runtime acceptance / Proof Slice 只为当前可观察 engineering substrate fact 生成
- 确认 deferrable domain behavior 和 post-foundation low-level Capability delta 在首个需要它们的 business workflow 中推进
- 确认 final roadmap order 遵循 Behavior Maturity Ordering Gate，且 support/governance/operation-heavy Change 不会仅因未来 Change 需要就提前排序
- 确认 source atom file 和 Phase 3 global atom index 未修改
- 确认 refit decision 引用 Phase 4 source-window dossier evidence，而不是只依赖 atom count、Capability count 或 atom summary
- 确认每个 final Change 在 atom ownership 最终确定前回答 Source Window Semantic Grounding Gate question
- 确认每项 Phase 5 artifact 都通过 Artifact Language Gate
- 下一必需步骤：`Start openspec-propose`、`Run Phase 3 again` 或 `Blocked`

## 完成条件

Phase 5 结束时，`phase-works/phase-5/phase-5-agent-report.md` 必须且只能包含以下一个 status：

- `Phase 5 Status: accepted`
- `Phase 5 Status: adjusted`
- `Phase 5 Status: needs-coverage-recheck`
- `Phase 5 Status: blocked`

如果 Phase 1 framework 在 source-window 和 atom-level review 后仍保持 coherent、已派生 final packet 且所有 Phase 5 gate 通过，使用 `accepted`。

如果 framework 已根据 source-window semantic profile 完成 refit、所有 final atom mapping 保持 traceable、已派生 final packet 且所有 Phase 5 gate 通过，使用 `adjusted`。

如果 Phase 5 暴露 missing、over-broad、conflicting 或语义不清的 source obligation，必须先由 Phase 3 规范化才能最终确定计划，使用 `needs-coverage-recheck`。

如果 adjustment 需要 Phase 5 无权执行的 source boundary、product decision 或广泛 reanalysis，使用 `blocked`。

达到 `accepted` 或 `adjusted` 后，按 `references/trace-sidecar-contract.md` 执行 all-phase complete validation，并按 `references/reviewer-repair-loop.md` 执行 final integration review；只有两者通过后才能从 final Change packet 启动 `openspec-propose`。出现 `needs-coverage-recheck` 后，main agent 必须启动 fresh Phase 3 review subagent，再启动 fresh Phase 4 grounding 和 Phase 5 refit subagent。不得从 `needs-coverage-recheck` 或 `blocked` 直接启动 `openspec-propose`。

handoff 给 `openspec-propose` 时，将 final Phase 5 decision 同时写入 `trace/phase-5.trace.json.status` 和 `trace/manifest.json` 的 `phase-statuses.phase-5`。两个值必须完全匹配。`phase-statuses.phase-5` 是 Phase 5 final handoff decision，不是 validator/reviewer/repair-loop workflow state。
