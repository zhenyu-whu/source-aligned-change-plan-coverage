# Phase 3：Coverage、Directive Freeze、GA Identity 与 Mapping Ambiguity

Phase 3检查Phase 2 provisional extraction对source行范围的覆盖，从uncovered range补提取遗漏obligation或显式delivery directive，为每个occurrence分配provisional GA，并记录potential mapping ambiguity。联合Phase 2/3 bounded review通过后，`coverage-complete`同时冻结source-fact、`delivery-directives[]`、evidence ref与GA。

Phase 3不规范化语义、不规划Change/Capability、不证明dependency、不选择roadmap order、不裁决mapping，也不处理semantic duplicate。

Writer、reviewer和repair writer必须完整读取cross-phase、本文件、review gate与trace contract。

## 输入

- Phase 1 source manifest；
- Phase 2 canonical atom JSON；
- 用户指定source；
- `scripts/phase3_line_range_audit.py`。

Writer必须使用随技能脚本计算covered range与complement；不得手工或用临时脚本替代。

## 固定输出

```text
change-capability-anchors/obligation-atom-index.json|md
phase-works/phase-3/coverage-review.json|md
trace/phase-3.trace.json
phase-works/phase-3/phase-3-reviewer-report.md
phase-works/phase-3/phase-3-repair-report.md  # 仅发生repair时
```

JSON是canonical authority，Markdown是mirror，trace是freeze commit marker；review/repair report是noncanonical。

## 执行顺序

1. 从Phase 1 manifest取得全部read-full source。
2. 验证每份source有唯一有效Phase 2 v6 atom JSON。
3. 执行range audit，机械取得covered与candidate uncovered ranges。
4. 为每个Phase 2 atom按稳定顺序一对一分配provisional GA。
5. 只阅读uncovered range及最小必要上下文。
6. 对遗漏production obligation或显式delivery directive创建`P3-GAP-####`，再分配独立GA。
7. 其余uncovered range分类为`safe-non-obligation|blocked`；遗漏内容使用`missing-obligation`并链接gap。
8. 核对每个Phase 2 atom和gap atom的`delivery-directives[]`是否由source明示。
9. 为每个GA检查potential mapping ambiguity；只记录实际不唯一的mapping dimension，不填写final value。
10. 写coverage authority、provisional global index与`review-pending` trace，使用v11 renderer生成mirror。
11. 运行Phase 2普通validator和Phase 3 preflight，再执行联合bounded review。
12. Repair后重新执行range audit、coverage closure、directive audit、GA稳定排序、renderer与两个validator。
13. Terminal review双validator passed、directive status passed且findings为空后，只把Phase 3 trace改为`coverage-complete`与gate passed，冻结完整authority。

## 明确禁止

Phase 3不得：

- 比较两个atom是否语义相同或选择canonical atom；
- 判断duplicate/refinement/preserve/dependency；
- 将steady-state architecture、guard、Capability或实现关系转成delivery directive；
- 判断directive影响哪个final Change或如何排序；
- 判断owner Change、Capability impact、target或related Capability；
- 把mixed independent responsibilities留到Phase 5；
- freeze后修改evidence、directive、range、ref或GA；
- 因GA数量、重复evidence或directive数量触发split/merge/framework调整。

## Global identity 与 gap atom

- 每个Phase 2 atom和Phase 3 gap atom恰好一个GA；语义或原文相同仍保持独立。
- Gap atom与Phase 2 atom一样只有一个连续range、逐字source-fact、type、normativity与`delivery-directives[]`。
- Gap directive只在uncovered range明示时填写；没有明示使用空数组。
- Freeze前split/add后确定性重算provisional GA；freeze后不可修改或重编号。

## Coverage semantic review

Coverage review document、gap、disposition、ambiguity与summary exact shape见trace contract。

- `missing-obligation`必须链接至少一个位于range内的gap atom；
- `safe-non-obligation`不得链接gap；
- 每个candidate uncovered range必须完整处置；
- 每个gap恰好由一个missing disposition链接；
- mapping ambiguity dimension仍只允许`owner-change|relation|artifact-projection|target-capability`；
- delivery directive不是mapping ambiguity；不唯一或冲突的source时序必须在freeze前修复或blocked。

## Evidence freeze review gate

Reviewer必须全文确认：

1. 每个source行由covered range或remainder disposition解释；
2. 每项production obligation进入Phase 2 atom或Phase 3 gap；
3. 每项source明示milestone/precedence/deferred语义进入唯一occurrence的`delivery-directives[]`；
4. 所有非空directive都有逐字source依据；
5. steady-state architecture/security/layer/reuse没有被误判为directive；
6. 每个source-fact、digest、range可信；
7. 每个occurrence能由单一terminal mapping tuple无损表达；
8. 不执行semantic dedup；
9. 真实mapping ambiguity逐GA记录但未提前裁决；
10. Source冲突、无法可信覆盖或需要产品决定时blocked。

Repair只能消费上一轮finding并修改明确命中的provisional Phase 2/3 authority。Repeated fingerprint、no-op repair、身份复用或第三次review仍失败立即blocked。

## Schema、trace 与 renderer

- Global index使用`source-aligned-global-atom-index-v4`。
- Coverage review使用`source-aligned-phase-3-coverage-review-v3`。
- Gap row在v2字段基础上增加`delivery-directives[]`。
- Summary增加`delivery-directive-atoms`及三种directive occurrence计数。
- Phase 3 trace使用`source-aligned-phase-3-trace-v5`。
- Review row在既有字段基础上增加`delivery-directive-status: passed|failed`。
- Renderer使用`source-aligned-render-v11`，mirror显示每个atom/gap的directive。

Trace decision：

- `review-pending`：只用于preflight；
- `coverage-complete`：coverage闭合、directive audit passed、review gate passed；
- `blocked`：source/evidence/directive/authority不可信或需要用户决定。

Evidence authority digest覆盖source digest、Phase 2 atom JSON、global index与coverage review；directive作为atom/gap JSON内容自然进入digest。Trace、manifest、mirror和report不进入该digest。

Writer最终只报告decision、gap atom数量、directive atom数量、mapping ambiguity数量、review/repair用量和blocker。
