# v7 跨 Phase 语义契约

本文件只定义Phase 1–5、三个bounded review gate和final integration gate共同遵守的不变量。Phase-specific语义由对应task contract定义，机器字段由`references/trace-sidecar-contract.md`定义，Change/Capability boundary与delivery sequence只以共享framework原则为准。

## 权威边界

- Source document是production obligation与显式delivery directive的原始语义来源。
- Phase 2/3读取source并建立provisional evidence；只有Phase 3 `coverage-complete` commit marker与`review-gate.status: passed`同时成立时，`source-fact`、`delivery-directives[]`、evidence ref和GA才作为一个authority set冻结。
- Phase 4 assembler、Phase 5 refit/mapping及helper只通过evidence resolver消费冻结evidence，不重新读取source。
- Phase 1以`initial-framework.json`为唯一语义权威，`initial-change-plan.md`是确定性mirror；Phase 2/3以JSON为语义权威；Phase 4 collection Markdown是确定性内容权威；Phase 5 refit JSON只负责initial→final review，独立final-roadmap JSON负责最终semantic landscape、Capability、outcome thread、Change、dependency edge、guard link、directive resolution、order、prefix、overlay与foundation，mapping JSON负责逐GA terminal mapping。Final plan是确定性projection。
- Mirror、派生index和report不得成为第二份语义权威。Work queue、agent/reviewer/repair report均不进入manifest。
- Final integration review JSON是workflow-level canonical review authority；其Markdown是确定性mirror。Workflow completion trace是整个generation唯一完成commit marker。
- Phase 2/3 freeze后发现evidence integrity defect、contract冲突或validator失败时停止，不弱化规则。

## Capability topology 与 delivery sequence

- Capability topology规定长期normative ownership；delivery sequence规定从当前baseline到目标状态的Change transition path。两者必须独立推导。
- Capability名称、基础性、复用范围、首次advancement或Capability之间的概念关系不得形成Change dependency或order。
- 一个Capability可以由多个Change增量推进；首次consumer只需建立当前outcome安全成立所需的最小slice。
- Change必须在隐藏未来roadmap时仍通过Prefix Utility；除唯一foundation外，新substrate/guard必须在同一Change或当前prefix被消费。
- 显式delivery directive优先于architecture、reuse或readiness推断。任何source冲突无法安全裁决时必须`blocked`。

## Evidence occurrence、directive 与 GA identity

- Phase 2 source atom和Phase 3 gap atom各代表一个独立evidence occurrence，并恰好获得一个`GA-####`。
- 每个occurrence都显式保存`delivery-directives[]`；只有source明示时使用`milestone-scope|explicit-precedence|explicit-deferred`，否则为空数组。
- GA不是去重后的requirement。语义相同、原文相同或range重叠的occurrence仍保留独立GA。
- Global index只保存GA和evidence ref；后续通过resolver取得frozen evidence与directive。
- 本技能不识别、标记、合并、归组或消除semantic duplicate。
- Evidence freeze前repair可以split/add occurrence或修正directive，并按稳定排序重新分配provisional GA；freeze后任何evidence、directive、ref或GA都不可修改或重编号。

## Coverage 与 potential mapping ambiguity

- Phase 3 coverage closure是covered range的机械补集与每个uncovered range的处置，并由联合reviewer全文核对production obligation与显式directive completeness；它不是mapping或roadmap证明。
- `coverage-complete`允许非空potential mapping ambiguity；source/artifact/range不可信则`blocked`。
- Phase 3 ambiguity以GA为键，只记录`owner-change`、`relation`、`artifact-projection`、`target-capability`中实际不唯一的维度，不填写final value。
- Delivery directive不是mapping ambiguity dimension；Phase 3只判断source是否明示，不裁决它影响哪个final Change。
- Phase 5检查全部GA。每个GA的terminal mapping row是唯一final owner/relation/projection/target authority；每个非空directive GA还必须有唯一terminal directive resolution。
- Candidate mapping不一致、final mapping选择或framework boundary调整都不是evidence defect。

## Phase 职责

- **Phase 1**：完整读取source，先建立Capability topology，再建立coarse delivery semantics、outcome-sliced Change、typed dependency edge hypothesis与prefix review；写`initial-framework.json`并确定性渲染plan，不提取atom。
- **Phase 2**：按自然语义单位提取provisional occurrence，只记录source明示的directive，并给出existing-framework candidate hint；不规划dependency/order。
- **Phase 3**：闭合coverage、补提取gap、核对directive completeness、建立provisional GA、记录potential mapping ambiguity并冻结evidence；不规划framework。
- **Phase 4**：确定性生成all-evidence完整中性collection、按source中性视图与delivery-directive collection；不按Phase 1 Change/Capability或candidate mapping分桶，不渲染candidate routing metadata，不作semantic profile、owner、dependency、order、refit或Capability impact判断。
- **Phase 5**：先形成provisional final boundary与terminal mapping，再全量裁决directive、证明hard dependency、审核每个prefix、选择final order，最后推导overlay/baseline并执行bounded review。
- Phase 1 boundary默认是hypothesis；Phase 5可以做最小boundary refit，但必须从冻结evidence完整重算order。Phase 1顺序没有保留偏置。

## Dependency、guard 与 foundation-like 不变量

- Hard dependency必须通过共享原则的四项gate；layering、internal reuse、shared infrastructure、readiness、Capability关系和“后续都需要”不得形成edge。
- 当前行为不可缺少的authorization/privacy/security/compatibility/consistency/data-integrity guard必须与首次暴露该行为的同一个Change交付。
- 只有保护既有运行表面且独立产生可测风险降低的guard，才能作为更早Change。
- Foundation公开marker仍为首项空`capability-slices[]`，但语义review必须独立识别foundation-like内容。非空technical/security overlay不能形成豁免。
- 除唯一foundation外，每个final Change必须拥有direct spec/guard slice，并通过Prefix Utility与Consumer Closure。

## Ownership 与 Capability advancement

- Phase 2 candidate owner/projection/target只是extraction-time hint；Phase 4不得把它们变成collection bucket、final owner、dependency、order或advancement。
- 每个GA恰好一个final owner Change、relation、projection和Capability字段。
- 只有direct `spec-requirement|spec-guard` mapping推进Capability；design、verification、non-direct和related-only mapping不推进。
- Advancement由final Change order、direct mapping和repository baseline统一推导；mapping impact、refit overlay、baseline reconciliation和final plan overlay必须等于同一结果。
- Final packet的`depends-on[]`必须由Phase 5 terminal `dependency-edges[]`确定性派生，不得仅从Markdown自由文本恢复。

## Frozen evidence 与 repair

- Phase 2/3 finding只能在联合gate剩余repair预算内修复；repair必须消费上一轮finding且不得扩大到无关source。
- Phase 5 bounded repair只能修改Phase 5 framework/refit、roadmap、mapping和final plan authority；不得回写Phase 2/3。
- 每次Phase 5 repair后必须完整重算helper派生surface、重跑preflight validator并由fresh reviewer检查；不得运行targeted、incremental或checkpoint repair。
- Phase 5发现quote、range、missing occurrence或mixed independent occurrence等冻结evidence缺陷时记录issue并`blocked`。

## Workflow completion authority

- `trace/manifest.json`使用manifest v3，并显式记录`workflow-status: pending|integration-passed|blocked`。
- Phase 5 terminal只表示final candidate authority通过Phase 5 bounded gate，不表示workflow完成。
- All-phase `--pre-handoff` validator通过后，fresh final integration reviewer只写根`final-integration-review.json`；finalizer必须先以exclusive atomic create锁定该review的path/raw-bytes SHA，再执行语义校验并一次性写passed或blocked attempt result。只有合法review终态化后才确定性生成Markdown mirror、completion trace与manifest commit marker，随后再运行`--complete` validator。
- Review语义无效也会消耗唯一attempt：finalizer写blocked attempt result但不得发布completion；替换review或第二次review attempt均被拒绝。进程只留下submitted attempt时，只允许对同一raw bytes继续crash recovery。
- Passed review必须绑定当前`terminal-authority-sha256`；该digest只覆盖trace contract固定顺序的七份terminal artifact及其raw-bytes SHA，不包含manifest、review自身、attempt/result或completion trace。
- `trace/workflow-completion.trace.json`是唯一workflow完成commit marker。只有`status: integration-passed`、review path/digest有效且terminal digest与passed review逐字一致时，selector与下游handoff才能消费generation。
- Final review为blocked时manifest `workflow-status: blocked`且completion trace使用blocked状态；pre-handoff或complete validator失败时不得伪装为完成或自动启动新repair。

## Handoff、语言与版本

- Phase 5 handoff从terminal mapping和dependency edges确定性生成完整`change-source.md`、Capability slices与final packet。
- 公开文件不得输出GA、atom ID、evidence ref、directive、relation、projection、mapping reason、Change类型或internal review metadata。
- `source-fact`保持source原文，不翻译、不转述、不改写；agent解释、判断、理由与报告使用简体中文。
- `source-aligned-trace-v6`及更早generation保持原状态，不迁移、不原地升级、不重渲染。新generation必须从Phase 1使用v7。
- v7 validator/renderer/helper不得消费或修改legacy generation；在非空legacy output root上必须阻断，等待用户明确选择干净root或授权替换。
