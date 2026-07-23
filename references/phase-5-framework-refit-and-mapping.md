# Phase 5：最终 Framework Refit 与逐 GA Mapping

Phase 5基于冻结evidence和共享framework标准，对Phase 1 framework做最小source-backed refit；为每个GA生成唯一terminal mapping，并由该mapping裁决Phase 3 potential mapping ambiguity；最后完成baseline、overlay与final plan的一致性冻结。

Writer必须完整读取`references/cross-phase-contract.md`、`references/change-capability-framework-principles.md`、本文件和`references/trace-sidecar-contract.md`。

## 目标与非目标

- 默认保留initial framework，只在frozen evidence支持时执行最小split、merge、add、remove、rename、reorder或scope adjustment。
- 检查全部GA并完成唯一final mapping；Phase 3 ambiguity只是输入观察，不是检查范围上限。
- 不执行semantic dedup，不按GA数量、source heading、技术层或矩阵形状调整framework。
- 不重新读取source，不创建replacement source window，不在review mirror复制final mapping。

## 输入与语义权威

- 输入：Phase 1 initial plan、Phase 2/3 semantic JSON、global index、potential ambiguities、Phase 4 collections/index，以及只读`openspec/specs/<capability>/spec.md` baseline。
- Refit语义权威：`framework-refit-trace.json`，schema为`source-aligned-framework-refit-trace-v4`。
- Final mapping语义权威：`atom-plan-mapping.json`，继续使用`source-aligned-atom-plan-mapping-v4`。
- `atom-plan-mapping.json.artifact-path`固定为repository-relative `openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.md`；它标识确定性Markdown mirror，不改变JSON的语义权威地位，也不得指向JSON自身。
- Final plan内容权威：`phase-works/phase-5/change-plan.md`；根`change-plan.md`必须与其逐字节一致。
- Review、mapping mirror、baseline、change source、Capability slices、bundle index与anchor index均由helper确定性生成，不得反向恢复语义。

## Semantic flow

1. 按Phase 1顺序复审每个initial Capability、initial Change及Phase 4 `unassigned-and-gap` GA，记录initial gate与最小refit理由。
2. 形成provisional final Change/Capability、hard dependency和roadmap，不先冻结overlay或`new|modified`。
3. 为全部GA建立完整terminal mapping；用同GA row裁决已记录ambiguity，并在reason中裁决late-discovered ambiguity。Candidate owner/target与final值不一致是正常裁决，不回写Phase 2/3。
4. 读取mapped target的repository baseline；由final Change order、direct mapping和baseline统一推导edge impact、overlay及baseline rows。
5. 使用共享原则校验minimality、dependency、final Change/Capability和最终顺序；确保plan、refit、mapping与推导结果一致。
6. 一致后原子冻结refit JSON、mapping JSON和final plan；helper先校验完整envelope与canonical mirror path，再生成全部派生物。

任一步需要产品决定、无法形成唯一mapping、baseline不可访问或共享原则冲突时返回`blocked`，不得启动Phase reviewer或repair loop。

## Initial review 与最小 refit

Capability review完整且按固定顺序记录8项`initial-gate-results[]`：`domain-basis`、`purpose`、`behavior-first`、`cohesion`、`owns-excludes`、`implementation-substitution`、`archive-durability`、`delta-feasibility`。

Change review完整且按固定顺序记录6项：`one-intent`、`scope-cohesion`、`independent-decision-archive`、`indivisibility`、`acceptance`、`implementation-readiness`。

- 每个gate row只含`gate`、`result: passed|failed`和非空简体中文`note`。
- `keep`要求全部initial gate通过、final ID只含自身，且`supporting-global-atom-ids[]`为空。
- 非`keep`通常必须引用按global index排序、属于该initial unit Phase 4 collection的supporting GA。
- `remove|merge`只有在该collection为零GA且至少一个initial gate失败时，才允许空supporting list。
- Initial gate失败可以由最小refit解决；任何含failed gate的review不得使用`keep`。
- New final unit只能由initial review lineage或`supports-adjustment` gap/mapping实际产生，不得凭空添加。
- Final framework是否通过共享标准由final plan语义和一次性final integration reviewer确认；不得复制第二套final gate数组。

## Unassigned/gap review

每个Phase 4 unassigned/gap GA恰好一行，且只包含：

```text
global-atom-id
evidence-ref
framework-impact: none | supports-adjustment
reason
```

- `evidence-ref`与global index逐字一致；reason使用简体中文。
- `supports-adjustment`必须机械关联到非`keep` review的supporting GA、映射到Phase 1不存在的final ID，或产生Phase 1不存在的advancement edge。
- `accepted`时所有row必须为`none`。
- Gap review不保存owner、relation、projection、target或Capability impact；这些final值只存在mapping v4。

## Mapping 与 ambiguity 裁决

- 每个GA恰好一个mapping row，包含完整final owner、relation、projection、Capability impact/target、related Capability及reason。
- 每个Phase 3 potential ambiguity GA必须由同GA mapping row裁决，evidence ref一致且对应dimension没有placeholder。
- Late-discovered ambiguity不回写Phase 3；在mapping reason中明确记录发现与裁决依据。
- Candidate mapping不一致、`unassigned`、gap、relation选择或framework调整由本Phase terminal mapping/refit直接裁决，不得回写冻结evidence。
- Direct与non-direct evidence均归属一个final Change；只有direct `spec-requirement|spec-guard`推进Capability。
- Design、verification、non-direct和related-only mapping不推进Capability，impact/target按mapping v4约束使用`none`。

## Advancement、baseline 与 overlay

Helper只使用一条推导链：

```text
final Change order + direct spec/guard mapping + repository baseline
-> expected per-edge new/modified -> derived overlay -> baseline rows
```

- Repository已存在的Capability在每条advancement edge均为`modified`。
- Repository absent的Capability在final Change order中的首次advancement为`new`，后续advancement为`modified`。
- 同一Change/Capability的所有direct spec/guard mapping使用该edge的同一impact。
- Mapping impact、refit overlay、final plan overlay和baseline reconciliation必须逐edge等于同一推导结果；任一漂移由helper/validator拒绝。
- Overlay只包含实际advancement edge，不包含dependency、reuse、preserve、related-only、design-only或verification-only relation。

## 冻结 evidence defect

Phase 5若发现quote/range不可信、missing occurrence、mixed independent occurrence或其他需要修改冻结Phase 2/3 authority的evidence integrity defect，必须：

- 在framework refit `issues[]`与Phase 5 blocked trace中记录稳定、可定位的issue；
- 返回`blocked`，不发布Phase 5 terminal mapping、final plan或根`change-plan.md`；
- 不回写Phase 2/3、不创建request/checkpoint、不运行incremental assembler或checkpoint resume。

Candidate mapping不一致、final owner/relation/projection/target选择、related Capability及framework boundary调整都不是evidence defect，直接由terminal mapping/refit表达。

## Status、helper 与 handoff

- `accepted`：全部initial gate通过、全部initial review为`keep`、framework语义与Phase 1一致、所有gap review为`none`，且全部GA已完成mapping与baseline reconciliation。
- `adjusted`：存在可追溯且实际改变framework语义的最小调整；允许initial gate失败，但失败row不得`keep`；全部terminal authority一致且`issues[]`为空。
- `blocked`：存在冻结evidence缺陷、validator失败、需要用户决定或其他无法形成可信terminal authority的blocker。

`phase5_plan_refit.py`先校验refit/mapping envelope与canonical mirror path，再校验语义输入、执行统一advancement推导、生成mirror/派生物并清理不适用surface；envelope失败时必须在写入任何派生物前返回失败，不得自动normalize或补写字段。Helper不得补写Change/Capability语义、代作mapping裁决或读取source。Render contract使用`source-aligned-render-v10`：review mirror显示`Initial Gate Results`、`Supporting GAs`、gap的`Framework Impact`，并将输入观察命名为`Potential Mapping Ambiguities (Input)`；resolution只在mapping mirror。

Helper还从terminal mapping确定性发布公开source bundle：每个Change一个`change-source.md`，每个direct spec/guard advancement edge一个`capability-slices/<capability>.md`。前者包含该owner的全部冻结原文，后者只包含对应Capability的direct spec/guard冻结原文以及final Capability Purpose/Owns/Excludes和`new|modified`。两类文件都按内部source path、range与GA稳定排序，将逐字`source-fact`作为原始Markdown直接排列并以一个空行分隔；不得输出`Source Occurrence`标题、序号、source path/range字段、生成器附加围栏、GA、atom ID、evidence ref、relation、projection或mapping reason。重复occurrence保持独立且不得去重。

`capability-slices`非空即普通Change；显式空数组即foundation。foundation最多一个、必须位于roadmap首位、无硬依赖且无overlay；其余Change必须非空。该判定从terminal mapping与final roadmap重算，不在Phase 1、Phase 5 plan/refit或packet中增加类型字段。

Phase 5 trace使用`source-aligned-phase-5-trace-v5`，只允许`accepted|adjusted|blocked`。Phase 5 validator通过后，main agent运行all-phase complete validator与一次final integration reviewer；reviewer必须确认所有final Change/Capability通过共享原则。两者都通过后才handoff。
