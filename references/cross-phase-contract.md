# 跨 Phase 语义契约

本文件只定义 Phase 1–5、Phase 1 bounded review 和 final integration gate 共同遵守的不变量。Phase-specific 语义由对应 task contract 定义，机器字段由 `references/trace-sidecar-contract.md` 定义，patch lifecycle由 `references/targeted-evidence-patch-contract.md` 唯一定义，Change/Capability boundary只以共享 framework 原则为准。

## 权威边界

- Source document 是 production obligation 的原始语义来源。
- Phase 2/3 读取 source 并冻结 `source-fact`；Phase 4 assembler、Phase 5 refit/mapping及helper只通过 evidence resolver消费冻结 evidence，不重新读取source。
- 唯一 source 重读例外是 patch contract授权的一次预先固定 window 核验；该window不成为framework input或replacement evidence。
- Phase 1 initial plan和Phase 5 final plan以Markdown为内容权威；Phase 2/3以JSON为语义权威；Phase 4 collection Markdown是确定性内容权威；Phase 5 refit与mapping JSON是语义权威。
- Mirror、index和report不得成为第二份语义权威。Work queue、agent/reviewer/repair/final integration report均不进入manifest。
- Phase 2–5没有独立Phase reviewer或repair loop；contract冲突或validator失败时停止，不弱化规则。

## Evidence occurrence 与 GA identity

- Phase 2 source atom和Phase 3 gap atom各代表一个独立 evidence occurrence，并恰好获得一个 `GA-####`。
- GA不是去重后的requirement。语义相同、原文相同或range重叠的occurrence仍保留独立GA。
- Global index只保存GA和evidence ref；后续通过resolver取得frozen evidence。
- 本技能不识别、标记、合并、归组或消除semantic duplicate。
- Duplicate ID、dangling ref和identity cardinality错误由validator拒绝。
- Targeted patch后，未受影响evidence ref、GA及row digest保持不变；新增occurrence只追加GA，旧ref退出时必须显式可追溯。

## Coverage 与 potential mapping ambiguity

- Phase 3 coverage closure是covered range的机械补集与每个uncovered range的处置，不是语义唯一性证明。
- `coverage-complete`允许非空potential mapping ambiguity；source/artifact/range不可信则`blocked`。
- Phase 3 ambiguity以GA为键，只记录`owner-change`、`relation`、`artifact-projection`、`target-capability`中实际不唯一的维度，不填写final value。
- `unassigned`、gap、candidate hint缺失或GA数量不自动构成ambiguity。
- Phase 5检查全部GA。每个GA的terminal mapping row是唯一final owner/relation/projection/target authority，也是已记录或late-discovered ambiguity的唯一resolution。
- Late-discovered ambiguity不回写Phase 3，也不触发patch；在mapping reason中记录裁决。需要产品决定且无法唯一映射时`blocked`。
- Candidate mapping不一致、final mapping选择或framework boundary调整都不是evidence defect。

## Framework 与 Phase 职责

- Phase 1和Phase 5直接读取同一份`change-capability-framework-principles.md`，不得复制或创建第二套gate。
- Phase 1建立coarse initial hypothesis，不执行atom extraction、coverage、unique mapping或`new|modified`判断。
- Phase 2按自然语义单位提取occurrence，只给出existing-framework candidate hint。
- Phase 3闭合coverage、建立GA identity、标记potential mapping ambiguity，不规划framework。
- Phase 4按Phase 1 candidate bucket确定性重排冻结原文；不作semantic profile、owner、relation、projection、refit或Capability impact判断。
- Phase 5先复审initial framework并形成provisional framework，再为全部GA建立provisional mapping和裁决ambiguity；随后用mapping、repository baseline与Change order推导overlay/impact，最后一致性冻结refit、mapping和final plan。
- Phase 1 framework默认保留；Phase 5只做frozen evidence支持的最小refit，不以heading、技术层、矩阵形状或GA数量调整boundary。

## Ownership 与 Capability advancement

- Phase 2 candidate owner/projection/target只是extraction-time hint；Phase 4 bucket也不是final owner或advancement。
- 每个GA恰好一个final owner Change、relation、projection和Capability字段；direct与non-direct evidence都进入一个owner-scoped final packet。
- 只有direct `spec-requirement|spec-guard` mapping推进Capability；design、verification、non-direct和related-only mapping不推进。
- Advancement由final Change order、direct mapping和repository baseline统一推导：baseline已存在的target为`modified`；absent target首次推进为`new`，后续推进为`modified`。
- Mapping impact、refit overlay、baseline reconciliation和final plan overlay必须等于同一推导结果。

## Targeted patch invariant

- 每个generation至多一次patch，只能由Phase 5合法启动；Phase 2–4不能自行发起。
- Patch只修复evidence integrity，不处理mapping或framework判断。完整eligibility、request/checkpoint、增量链、resume/abort和失败规则只见`targeted-evidence-patch-contract.md`。
- Request/checkpoint本身不授权incremental worker；必须同时存在patch contract规定的Phase 5 trace commit marker和闭合引用。

## Handoff 与语言

- Phase 5 final packet是完整、未语义去重的evidence mapping，不是requirement inventory。下游可以综合多个GA，但必须保留多对一trace。
- Agent编写的解释、判断、理由、报告与handoff使用简体中文；固定field、enum、ID、path、代码符号和精确source quote可保留英文。
- `source-fact`保持source原文，不翻译、不转述、不改写。
