---
name: source-aligned-change-plan-coverage
description: 当用户明确要求从指定 source document 出发，在 openspec-propose 之前建立具备 Capability/sequence 分离、显式 delivery directive、evidence occurrence 覆盖、final roadmap、terminal mapping 与 workflow completion 的 OpenSpec Change/Capability 全局计划时使用；确保每个 extracted evidence occurrence 拥有独立 GA，并进入 v7 handoff。
---

# source-aligned-change-plan-coverage：v7 五阶段编排协议

从完整 source document 先建立稳定 Capability topology，再独立建立从当前 baseline 到目标状态的 delivery sequence；随后完成自然语义单位提取、显式 delivery directive 冻结、source coverage 闭合、中性 evidence 汇总，以及 Phase 5 final-roadmap 重算与逐 GA terminal mapping。本技能不识别或消除 semantic duplicate。

Capability-first 只表示先确定长期 normative boundary，不表示 Capability 是实施单元、依赖节点或建设顺序。任何 Change 顺序都必须由 source 明示的 delivery directive、真实 acceptance precondition、prefix utility 与 consumer closure 独立证明。

## 输入与授权

- 必需输入是 source document 根目录或精确 path；可选输入是 Phase 1 candidate Change 计划。
- 所有 workflow artifact 写入用户授权的 generation output root；默认仍为 `openspec/orchestrate/`。
- 只有用户明确要求对指定 source 执行本技能时才启动工作流；审阅、修改或安装技能本身不构成执行授权。
- 执行授权包括必需的 Phase worker、Phase 1 bounded reviewer/repair worker、Phase 2/3 evidence-freeze reviewer/repair worker、Phase 5 bounded reviewer/repair worker，以及一次 final integration reviewer。
- 已存在的非 v7 generation 是只读历史结果。不得因技能升级自动验证、渲染、迁移、删除、覆盖或重跑。

## Reference 路由

所有 worker 必须直接读取对应文件；prompt 摘要不能替代原文。

- `references/cross-phase-contract.md`：所有 worker 的跨 Phase 不变量。
- `references/trace-sidecar-contract.md`：v7机器接口、schema、renderer、validator 与 authority。
- `references/change-capability-framework-principles.md`：Phase 1 与 Phase 5 共用的唯一 framework 与 sequencing 标准。
- `references/review-gates.md`：Phase 1、Phase 2/3、Phase 5 bounded gate 与 workflow terminal integration gate。

| Phase | 唯一任务 contract |
| --- | --- |
| Phase 1 | `references/phase-1-initial-change-plan.md` |
| Phase 2 | `references/phase-2-source-anchor-coverage.md` |
| Phase 3 | `references/phase-3-coverage-review-iteration.md` |
| Phase 4 | `references/phase-4-frozen-evidence-collections.md` |
| Phase 5 | `references/phase-5-framework-refit-and-mapping.md` |

加载规则：

- Phase 1/5 writer、reviewer和repair writer额外加载共享 framework 原则。
- Phase 2/3 reviewer与repair writer必须加载cross-phase、review gate及Phase 2/3 task contract。
- Final integration reviewer加载cross-phase、共享原则、review gate及Phase 3–5 task contract。

`evals/`只用于技能发布前的中性盲测，不是generation runtime输入。发布候选必须按`evals/README.md`对全部case执行三次fresh独立判断并达到逐case 3/3；Phase worker不得读取oracle。

## Agent 拓扑

- main agent 只负责编排、work queue、interface gate、manifest/validator 与状态转换，不代写 Phase 语义。
- Phase 1、Phase 3、Phase 5 使用 fresh independent semantic writer；Phase 4 使用确定性 assembler。
- Phase 2 按 source document 或 coherent batch 分配 fresh extraction writer；每份 source 恰好一个 canonical owner。全部完成后再启动 independent index/report writer。
- Phase 1、联合Phase 2/3 evidence-freeze gate、Phase 5各自最多两轮repair、三轮fresh review；三个gate的预算和身份记录互不复用。
- Phase 2 extraction在Phase 3 evidence-freeze gate通过前都是provisional。
- Phase 5 reviewer只读最终候选framework、roadmap、mapping，以及可由这些authority确定性重算的handoff；repair writer只修改Phase 5 authority，不得回写冻结evidence。
- Final integration reviewer 是一次性 workflow-level 只读 gate，不属于 Phase 5 bounded reviewer。
- 所有 worker 都是 leaf，不启动 nested agent、`codex exec` 或其他 agentic child process。

## Phase 状态机

| Phase | 职责 | 成功状态 | 下一步 |
| --- | --- | --- | --- |
| 1 | Capability topology、coarse delivery semantics、outcome-sliced Change 与依赖假设 | `initial-plan-written` | Phase 2 |
| 2 | 自然语义 occurrence、显式 `delivery-directives[]` 与 existing-framework candidate hint | `source-atoms-written` | Phase 3，尚未冻结 |
| 3 | coverage闭合、GA identity、directive核对与联合 bounded review | `coverage-complete` | evidence freeze 后进入 Phase 4 |
| 4 | 建立all-evidence、by-source与delivery-directive neutral collections | `assembled` | Phase 5 |
| 5 | boundary refit、全量 final-roadmap 重算、逐GA mapping、bounded review与handoff | `accepted` / `adjusted` | complete validation |

Phase 1/2/3/4/5的source、authority、schema、validator或用户决策blocker，任一bounded gate耗尽repair预算，或无法可信闭合，都使当前generation `blocked`。冻结后发现evidence integrity defect直接`blocked`；不得回写Phase 2/3或启动patch/checkpoint链。

## 工作流

1. 验证 source path 与 generation output root。若目录含非 v7 generation，停止并请求用户选择干净output root或明确授权替换；不得自动清理。
2. 读取共享 contract，初始化 v7 manifest skeleton，并按恢复规则定位第一个失效 interface。
3. Phase 1先提炼 Capability，再独立生成 Change；依赖只能在 Change 已形成后证明。Writer发布`initial-framework.json`语义权威并确定性渲染`initial-change-plan.md`后，运行validator与bounded review。
4. Phase 2 writer提取provisional occurrence；只有source明示时序时才写`delivery-directives[]`，不得从架构、Capability或实现常识推断。
5. Phase 3机械闭合coverage、补提取gap、核对显式directive并建立provisional GA；联合Phase 2/3 gate通过后最后发布`coverage-complete`，同时冻结evidence、directive与GA。
6. Phase 4从冻结authority全量确定性生成all-evidence、by-source与delivery-directive neutral collections；不得按initial Change/Capability或candidate mapping分桶。
7. Phase 5先形成候选boundary与terminal mapping，再全量裁决directive、证明hard dependency、检查每个roadmap prefix并选择最终顺序；“最小refit”不保护Phase 1顺序。
8. Phase 5 helper先校验完整candidate envelope，并从相同authority在私有staging中生成、逐字节自检完整handoff，随后生成Phase 5 plan/refit-review mirror与pending trace。Review绑定七项digest：四份candidate artifact、frozen evidence authority、Phase 3 freeze trace和完整candidate handoff。Repair后必须用`--refresh-review-candidate`原子刷新mirror与全部七项digest，重跑preflight后才可启动fresh reviewer。
9. Phase 5 bounded gate通过后才发布根`change-plan.md`与terminal trace；随后先做pre-handoff validation，再由final integration reviewer写canonical review。Finalizer必须先原子锁定首次review提交的path/raw-bytes SHA，再做语义校验并一次性写passed或blocked attempt result；只有合法review终态化后才发布review mirror与workflow completion，最后运行complete validator。Manifest v3的`workflow-status`达到`integration-passed`后才handoff。

Phase 5至workflow completion的命令顺序固定如下。`${SOURCE_ALIGNED_SKILL_DIR}`是本技能根目录的绝对路径，`${ORCHESTRATE_DIR}`是当前generation output root的绝对路径；不得交换、跳过或把后一步提前执行。

```bash
python3 "${SOURCE_ALIGNED_SKILL_DIR}/scripts/phase5_plan_refit.py" --orchestrate-dir "${ORCHESTRATE_DIR}" --prepare-review --writer-id "<writer-id>"
python3 "${SOURCE_ALIGNED_SKILL_DIR}/scripts/validate_source_aligned_orchestrate.py" --orchestrate-dir "${ORCHESTRATE_DIR}" --phase phase-5 --preflight
python3 "${SOURCE_ALIGNED_SKILL_DIR}/scripts/phase5_plan_refit.py" --orchestrate-dir "${ORCHESTRATE_DIR}" --write
python3 "${SOURCE_ALIGNED_SKILL_DIR}/scripts/validate_source_aligned_orchestrate.py" --orchestrate-dir "${ORCHESTRATE_DIR}" --pre-handoff
python3 "${SOURCE_ALIGNED_SKILL_DIR}/scripts/finalize_source_aligned_orchestrate.py" --orchestrate-dir "${ORCHESTRATE_DIR}" --write
python3 "${SOURCE_ALIGNED_SKILL_DIR}/scripts/validate_source_aligned_orchestrate.py" --orchestrate-dir "${ORCHESTRATE_DIR}" --complete
```

第二步通过后执行Phase 5 bounded review并把结果写回pending trace。若review要求repair，repair writer先修改Phase 5 authority并追加repair row，然后必须运行：

```bash
python3 "${SOURCE_ALIGNED_SKILL_DIR}/scripts/phase5_plan_refit.py" --orchestrate-dir "${ORCHESTRATE_DIR}" --refresh-review-candidate
python3 "${SOURCE_ALIGNED_SKILL_DIR}/scripts/validate_source_aligned_orchestrate.py" --orchestrate-dir "${ORCHESTRATE_DIR}" --phase phase-5 --preflight
```

随后才能启动下一位fresh reviewer。只有gate写成`passed`且绑定当前七项candidate authority digest，第三步`--write`才会从同一authority在私有staging中重新生成并逐字节自检全部Change source、Capability slices、packet、baseline、mirror、根plan与terminal trace，并要求完整handoff digest与review时一致后原子发布；失败不发布handoff。第四步通过后，final integration reviewer必须先写`final-integration-review.json`。第五步finalizer先exclusive atomic create `trace/final-integration-review-attempt.trace.json`，再运行review语义校验并exclusive atomic create terminal attempt result；失败review也会留下blocked result且不能替换或重试，completion只能在合法review result之后发布。

## 恢复与 v7 硬切换

- 从 Phase 1 起核对manifest、canonical trace、authority digest和validator result；Phase 1、Phase 3、Phase 5还必须有有效bounded review evidence。
- Phase 1发布`phase-works/phase-1/initial-framework.json`语义权威及其确定性`initial-change-plan.md` mirror；根`change-plan.md`只由Phase 5 bounded gate通过后的terminal状态发布。
- Phase 2/3未冻结时从当前未完成review round恢复，保留既有review/repair历史和预算；冻结后不得修改evidence、directive或GA。
- Phase 4只允许从冻结Phase 1–3全量重建；Phase 5 repair只重建完整Phase 5 authority和派生surface，不存在targeted、incremental或checkpoint模式。
- `source-aligned-trace-v6`及更早generation保持原状态，不迁移、不原地升级、不重新渲染、不伪装为v7。
- 新执行必须使用`source-aligned-trace-v7`并从Phase 1开始。Renderer、validator与helper必须拒绝非v7 generation；不提供migration script。
- 安装或更新本技能不得触碰现有`openspec/orchestrate/`。在非空legacy output root上不得自动覆盖、归档或删除。

## 完成与 handoff

- `phase-works/phase-5/change-plan.md`与根`change-plan.md`必须逐字节一致。
- Complete validator与final integration reviewer必须核对每个显式delivery directive的terminal resolution、每条hard dependency edge、每个final Change的prefix review与order decision。
- Reviewer必须确认所有final Capability通过8项Capability gate，所有final Change通过8项Change gate；Capability topology没有被用作顺序，guard没有先于其保护对象，foundation-like内容没有借非空overlay逃逸。
- 每个occurrence必须由frozen GA/evidence resolver直接进入terminal mapping；Phase 4 collection只提供中性审阅surface，不是mapping membership、owner或order输入。全部已记录或late-discovered ambiguity只由同GA mapping row裁决。
- Passed integration review必须逐Capability、Change、outcome thread、dependency edge、guard link与occurrence chain记录结果，并绑定固定七份terminal artifact计算的`terminal-authority-sha256`；workflow completion必须绑定review path/digest与同一terminal digest。Selector只接受manifest `workflow-status: integration-passed`。
- 失败时workflow `blocked`，不得回写冻结evidence；Phase 5 gate内只允许预算内的Phase 5 authority repair，final integration gate失败后不自动repair。
- Handoff继续使用`source-aligned-final-packet-index-v3`。每个packet只公开由final dependency edges派生的Change依赖、完整owner-scoped冻结原文及direct spec/guard Capability切片。
- `capability-slices`空数组仍是公开foundation marker，但不是语义豁免。Foundation最多一个、位于首位、无依赖、无Capability overlay，并通过foundation-like审查；其余Change必须至少一个slice。
- Phase 1/5及公开packet均不保存Change类型、业务/技术分类或priority score。内部prefix、consumer closure与foundation-like检查不得泄露到handoff。
