# 跨 Phase 语义契约

本文件定义 Phase 1–5 以及 reviewer/repair共同遵守的不变量。Change/Capability boundary只以`references/change-capability-framework-principles.md`为准；Phase内artifact和任务由对应Phase reference定义；JSON schema、renderer和validator由trace contract定义。

## 权威边界

- source document是production obligation的原始语义来源。
- Phase 2/3通过原始source验证并冻结`source-fact`；Phase 4/5只通过evidence resolver消费frozen evidence，不重新读取source或扩展source window。
- authority按Phase划分：Phase 1 initial plan和Phase 5 final plan以Markdown为内容权威；Phase 2/3以JSON为语义权威；Phase 4 collection Markdown是确定性assembler的内容权威，JSON index只是派生机器索引；Phase 5 refit与GA mapping以JSON为语义权威，review和其他派生Markdown不是第二份权威。
- work queue、agent report、reviewer report和repair report是非canonical流程证据，不进入manifest。
- Phase 2 source atom通过reviewer后冻结。Phase 3只在uncovered range补充gap atom；broad Phase 2 atom必须targeted回Phase 2重提取。
- contract冲突时停止并报告blocker，不得弱化规则。

## Evidence occurrence与GA identity

- 每个Phase 2 source atom和Phase 3 gap atom都是独立evidence occurrence，并恰好获得一个`GA-####`。
- GA不是语义去重后的requirement。语义相同、原文相同或range重叠的occurrence仍保留独立GA。
- Phase 3 global index只保存`global-atom-id`和`evidence-ref`；Phase 4/5通过resolver取得frozen evidence。
- 本技能不识别、标记、合并、归组或消除semantic duplicate。
- duplicate ID、重复source-atom key、dangling ref和identity cardinality错误由validator拒绝。

## Coverage与重新提取

- Phase 3 coverage closure是Phase 2 atom range的机械补集及每个uncovered range的处置，不是语义唯一性证明。
- `coverage-complete`只表示source/artifact有效、全部uncovered range已补提取或安全分类、没有recheck/blocker。
- Phase 3/4/5发现missing/broad extraction时只能返回targeted recheck；Phase 4/5不得自行读取source补充原文。

## Framework标准与Phase边界

- Phase 1和Phase 5必须直接读取同一份`change-capability-framework-principles.md`。
- Phase 1使用共享标准初次生成coarse hypothesis；不执行atom extraction、coverage或final`New` / `Modified`。
- Phase 4 assembler只按Phase 2 candidate hint和Phase 3 provenance直接生成Markdown collection，再生成派生index；不做semantic profile、refit、owner、projection、relation或Capability impact判断。
- Phase 5使用共享标准复审initial framework；默认保留，只在Phase 4 evidence collection证明gate失败时做最小refit。
- Phase 5先在`framework-refit-trace.json`中冻结refit decision和final framework，再直接编写final plan并完成repository baseline reconciliation和逐GA mapping；review Markdown只能由refit JSON渲染。

## Ownership、projection与Capability

- Phase 2 candidate owner/projection/target只是extraction-time hint。
- Phase 3不判断planning metadata。
- Phase 4 bucket只是initial framework投影，不是final owner或advancement。
- Phase 5必须为每个GA给出一个final owner Change、relation、projection和Capability字段。
- direct evidence恰好一个final Change owner；non-direct evidence也必须owner-scoped地进入一个final packet。
- Capability advancement只来自direct `spec-requirement` / `spec-guard` mapping；design/verification、non-direct和related-only mapping不推进Capability。
- existing target为Capability-level`modified`；absent target首次advancement为`new`，之后为`modified`。

## 下游handoff

- Phase 5 final packet是完整、未语义去重的evidence mapping，不是requirement inventory。
- 下游规格生成可以综合多个GA为一个requirement，但必须保留多对一GA trace；该判断不属于本技能。

## Artifact Language Gate

- agent编写的解释、判断、理由、报告和handoff使用简体中文。
- 固定heading、field、enum、ID、path、代码符号和精确source quote可以保留英文。
- `source-fact`保持source原文，不翻译、不转述、不改写。
