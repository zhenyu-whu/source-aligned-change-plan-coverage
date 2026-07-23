# 跨 Phase 语义契约

本文件只定义Phase 1–5、Phase 1 bounded review、Phase 2/3 evidence-freeze gate和final integration gate共同遵守的不变量。Phase-specific语义由对应task contract定义，机器字段由`references/trace-sidecar-contract.md`定义，Change/Capability boundary只以共享framework原则为准。

## 权威边界

- Source document 是 production obligation 的原始语义来源。
- Phase 2/3读取source并建立provisional evidence；只有Phase 3 `coverage-complete` commit marker与`review-gate.status: passed`同时成立时，`source-fact`、evidence ref和GA才作为一个authority set冻结。
- Phase 4 assembler、Phase 5 refit/mapping及helper只通过evidence resolver消费冻结evidence，不重新读取source。
- Phase 1 initial plan和Phase 5 final plan以Markdown为内容权威；Phase 2/3以JSON为语义权威；Phase 4 collection Markdown是确定性内容权威；Phase 5 refit与mapping JSON是语义权威。
- Mirror、派生index和report不得成为第二份语义权威。Work queue、agent/reviewer/repair/final integration report均不进入manifest。
- Phase 2/3共享一个bounded semantic review/repair gate；Phase 4/5没有独立Phase reviewer或repair loop。冻结后发现evidence integrity defect、contract冲突或validator失败时停止，不弱化规则。

## Evidence occurrence 与 GA identity

- Phase 2 source atom和Phase 3 gap atom各代表一个独立 evidence occurrence，并恰好获得一个 `GA-####`。
- GA不是去重后的requirement。语义相同、原文相同或range重叠的occurrence仍保留独立GA。
- Global index只保存GA和evidence ref；后续通过resolver取得frozen evidence。
- 本技能不识别、标记、合并、归组或消除semantic duplicate。
- Duplicate ID、dangling ref和identity cardinality错误由validator拒绝。
- Evidence freeze前repair可以split/add occurrence，并按稳定排序重新确定性分配provisional GA；freeze后任何evidence ref、GA或row都不可修改或重编号。

## Coverage 与 potential mapping ambiguity

- Phase 3 coverage closure是covered range的机械补集与每个uncovered range的处置，并由联合reviewer全文核对production obligation completeness；它不是mapping语义唯一性证明。
- `coverage-complete`允许非空potential mapping ambiguity；source/artifact/range不可信则`blocked`。
- Phase 3 ambiguity以GA为键，只记录`owner-change`、`relation`、`artifact-projection`、`target-capability`中实际不唯一的维度，不填写final value。
- `unassigned`、gap、candidate hint缺失或GA数量不自动构成ambiguity。
- Phase 5检查全部GA。每个GA的terminal mapping row是唯一final owner/relation/projection/target authority，也是已记录或late-discovered ambiguity的唯一resolution。
- Late-discovered ambiguity不回写Phase 3；在mapping reason中记录裁决。需要产品决定且无法唯一映射时`blocked`。
- Candidate mapping不一致、final mapping选择或framework boundary调整都不是evidence defect。

## Framework 与 Phase 职责

- Phase 1和Phase 5直接读取同一份`change-capability-framework-principles.md`，不得复制或创建第二套gate。
- Phase 1建立coarse initial hypothesis，不执行atom extraction、coverage、unique mapping或`new|modified`判断。
- Phase 2按自然语义单位提取provisional occurrence，只给出existing-framework candidate hint。
- Phase 3闭合coverage、建立provisional GA identity、标记potential mapping ambiguity并承载evidence freeze commit marker，不规划framework。
- Phase 4按Phase 1 candidate bucket确定性重排冻结原文；不作semantic profile、owner、relation、projection、refit或Capability impact判断。
- Phase 5先复审initial framework并形成provisional framework，再为全部GA建立provisional mapping和裁决ambiguity；随后用mapping、repository baseline与Change order推导overlay/impact，最后一致性冻结refit、mapping和final plan。
- Phase 1 framework默认保留；Phase 5只做frozen evidence支持的最小refit，不以heading、技术层、矩阵形状或GA数量调整boundary。

## Ownership 与 Capability advancement

- Phase 2 candidate owner/projection/target只是extraction-time hint；Phase 4 bucket也不是final owner或advancement。
- 每个GA恰好一个final owner Change、relation、projection和Capability字段；direct与non-direct evidence都进入该Change公开的owner-scoped `change-source.md`，但GA与mapping元数据不进入公开文件。
- 只有direct `spec-requirement|spec-guard` mapping推进Capability；design、verification、non-direct和related-only mapping不推进。
- Advancement由final Change order、direct mapping和repository baseline统一推导：baseline已存在的target为`modified`；absent target首次推进为`new`，后续推进为`modified`。
- Mapping impact、refit overlay、baseline reconciliation和final plan overlay必须等于同一推导结果。

## Frozen evidence invariant

- Phase 2 preflight或Phase 3 closure finding只能在联合gate的剩余repair预算内修复；repair必须消费上一轮finding且不得扩大到无关source。
- `coverage-complete`后，candidate mapping与final mapping不一致由Phase 5 terminal mapping裁决，不回写Phase 2/3。
- Phase 5发现quote、range、missing occurrence或mixed independent occurrence等冻结evidence缺陷时记录`issues[]`并`blocked`；不得创建patch request、checkpoint或根`change-plan.md`。

## Handoff 与语言

- Phase 5 handoff从terminal mapping确定性生成完整`change-source.md`和direct spec/guard `capability-slices/*.md`。公开文件按内部source path、range与GA稳定排序，只将逐字`source-fact`作为原始Markdown直接排列，并以一个空行分隔；不得输出`Source Occurrence`标题、序号、source path/range字段、生成器附加围栏、GA、atom ID、evidence ref、relation、projection或mapping reason。重复occurrence仍逐条保留，不合并或去重。
- `capability-slices: []`是foundation的唯一公共判据；它最多出现一次、只能位于roadmap首位、无硬依赖且无overlay。其他Change至少一个slice。任何Phase都不得新增Change类型字段。
- GA、coverage、collections与terminal mapping继续作为上游内部审计链；下游不建立Requirement/Scenario到GA的映射，也无需保留多对一GA trace。
- Agent编写的解释、判断、理由、报告与handoff使用简体中文；固定field、enum、ID、path、代码符号和精确source quote可保留英文。
- `source-fact`保持source原文，不翻译、不转述、不改写。
