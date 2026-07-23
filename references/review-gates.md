# v7 Review Gates 规范

本文件定义Phase 1 framework hypothesis gate、Phase 2/3 evidence-freeze gate、Phase 5 final-framework/roadmap/mapping gate与workflow terminal integration gate。

所有reviewer/repair writer必须直接完整读取cross-phase、共享framework原则、对应Phase contract和本文件；prompt摘要不能替代原文。所有worker都是leaf，身份必须满足对应gate独立性。

## 通用 bounded gate 规则

- 每个bounded gate最多三次fresh review、两次fresh repair。
- Reviewer对被审authority只读；repair writer只消费上一轮finding。
- 每次repair后必须重跑对应validator并启动fresh reviewer。
- Finding fingerprint必须绑定稳定rule/subject和相关authority digest，排除措辞与修复方案。
- 相同fingerprint在后续任一review重现、repair前后authority digest相同、身份复用或第三次review仍不pass，立即`blocked`。
- Gate之间的review/repair预算与fingerprint历史互不复用。

## Phase 1 bounded review

固定顺序：

```text
Phase 1 writer -> 写initial-framework JSON -> 确定性渲染plan
-> 发布status=review-pending / gate.status=pending trace
-> validator -> reviewer #1
-> repair JSON #1（如有）-> 全量重渲染 -> validator -> reviewer #2
-> repair JSON #2（如有）-> 全量重渲染 -> validator -> reviewer #3
-> pass 或 blocked
```

Writer发布authority时尚未存在reviewer结果，因此首个合法状态必须是`review-pending`与空`pending` gate。`pending`允许0..3条review、0..2条repair，并只允许：

- `reviews == repairs`：等待首轮或repair后的fresh review；
- `reviews == repairs + 1`：等待当前review后的repair或terminalization。

中间review不得跳过repair直接进入下一轮；repair后的当前JSON必须绑定最后repair after digest，review后的当前JSON和mirror必须绑定最后review digest。超过三次review或两次repair、缺失中间repair、重复finding、no-op repair或第三次review未通过时必须立即`blocked`，不得继续保持`pending`或追加后续轮次。

Reviewer必须执行：

1. Capability 8 gate与Change 8 gate；
2. Capability/Change/sequence independence；
3. Source Delivery Semantics完整性与显式性；
4. **Hide Future Consumers**：隐藏未来Change后当前Change是否仍改善prefix；
5. **Minimal Consumer Inclusion**：最小enabler/guard并入consumer后是否仍focused；
6. **Guard Subject Exists**：被保护行为是否已存在或在同Change暴露；
7. **Hide Capability Names Before Ordering**：order能否独立由outcome解释；
8. **Prefix Deployability**：每个prefix是否连贯、可部署、guard完整且无dormant substrate；
9. 每条hard dependency的四项proof；
10. Overlay只表达direct advancement；
11. Phase 1未越界创建atom、GA、line trace、frozen directive或baseline relation。

Phase 1 trace review row的`semantic-checks[]`必须按Phase 1 contract固定九项完整记录，并同时绑定当前`initial-framework.json`与`initial-change-plan.md` digest。Detailed finding写入noncanonical reviewer report；repair report记录消费finding、JSON authority before/after digest和保留不变量。Repair不得直接修改Markdown，下一轮review前必须从JSON完整重渲染。

只有validator passed、全部semantic checks passed、最后findings为空时，才可把trace从`review-pending` terminalize为`initial-plan-written`并把gate改为`passed`。Canonical blocked trace必须同时使用顶层`blocked`与gate `blocked`；complete workflow不接受Phase 1 `review-pending`。

## Phase 2/3 evidence-freeze bounded review

默认顺序：

```text
Phase 2 provisional extraction -> Phase 2 preflight/aggregate/validator
-> Phase 3 coverage/directive/GA closure -> 两个validator
-> reviewer #1
-> repair #1（如有）-> 全量重算Phase 3 -> 两个validator -> reviewer #2
-> repair #2（如有）-> 全量重算Phase 3 -> 两个validator -> reviewer #3
-> evidence freeze 或 blocked
```

Phase 2 preflight若已有semantic finding，可提前使用`stage: phase-2-preflight`，但与后续closure共享同一3/2预算。

Reviewer全文读取所有source并检查：

- production obligation completeness；
- 逐字quote/range与单tuple无损表达；
- mixed responsibility拆分；
- 每个source明示milestone/precedence/deferred语义进入`delivery-directives[]`；
- 所有非空directive都有直接source依据；
- steady-state architecture/security/layer/reuse未被误判为directive；
- mapping ambiguity只记录实际不唯一dimension；
- 未执行semantic dedup、dependency/order或final mapping裁决。

Terminal review必须为`phase-3-closure`，Phase 2/3 validator均passed，`delivery-directive-status: passed`且findings为空。最后发布`coverage-complete` marker；此前任何Phase 2 pass都不构成freeze。

Repair可以split/add occurrence或修正directive，但只限finding命中source。每次repair后必须重算range complement、gap、GA、ambiguity、directive summary和两个mirror。

## Phase 5 bounded final-framework/roadmap/mapping review

Phase 5新增独立bounded gate：

```text
Phase 5 writer生成候选refit、final roadmap、terminal mapping与plan
-> helper校验完整candidate并生成plan mirror/pending trace
-> Phase 5 preflight validator
-> reviewer #1
-> repair #1（如有）
-> refresh完整candidate/preflight -> reviewer #2
-> repair #2（如有）
-> refresh完整candidate/preflight -> reviewer #3
-> passed后staging全量生成、自检并terminal publish，或由同一--write原子终结blocked
```

Reviewer必须确认：

1. Final Capability全部通过8项Capability gate；
2. Final Change全部通过8项Change gate；
3. 每个冻结非空directive GA恰好一个terminal resolution；
4. 每条typed hard dependency edge通过四项proof，且final plan/packet依赖完全由`dependency-edges[]`派生；
5. 每个final Change恰好一个prefix review与position-matched order decision；
6. 每个非foundation Change通过Prefix Utility与Consumer Closure；
7. guard与首次受保护行为co-deliver，或独立guard确实保护既有运行表面；
8. Foundation-like内容没有借technical/security overlay逃逸；
9. 显式milestone/precedence/deferred约束优先于heuristic；
10. Capability topology、Phase 2 candidate mapping、GA数量和旧Phase 1 order未决定final order；
11. 每个GA恰好一个terminal mapping；ambiguity由同GA row裁决；
12. Overlay、baseline、public source/slices、final packet与terminal authority一致。

Canonical Phase 5 review checks固定为：

```text
final-capability-gates
final-change-gates
delivery-directive-resolution
dependency-strength
prefix-viability
guard-co-delivery
foundation-like-content
order-selection
mapping-overlay-consistency
```

Phase 5 repair只允许修改Phase 5候选authority：

- framework boundary/refit；
- final roadmap、dependency edges、delivery directive resolutions、prefix/order decision rows；
- terminal mapping与final plan。

Repair不得修改Phase 1–4、source-fact、directive、evidence ref或GA。Repair后必须运行`--refresh-review-candidate`，从完整Phase 5 authority重算plan/refit-review mirror、四份candidate artifact digest、frozen evidence digest、Phase 3 freeze digest与完整candidate handoff digest，并原子刷新pending trace，再重跑preflight；不得targeted render、checkpoint或局部patch。Gate通过后的`--write`才在私有staging全量重算overlay、baseline、public source/slices、packet和terminal digest，并验证完整handoff仍与review绑定值一致。

Gate通过前：

- 根`change-plan.md`不得发布；
- Phase 5 trace只能`review-pending`；
- Candidate plan只位于Phase 5 working surface；public derived surface尚未发布，其内容必须可从candidate authority确定性重算。

Gate通过后，helper才在私有staging生成并逐字节自检全部派生物，然后原子发布Phase 5 terminal authority、public handoff、根plan和terminal trace；任何生成或发布后校验失败都回滚。

第三轮review若validator、固定九项check或finding任一未清零，gate必须写成`blocked`，不得保持`pending`。此时运行同一`--write`，helper验证完整blocked gate与当前七项candidate digest后，只把`review-pending` trace原子替换为`block-kind: bounded-review`的canonical blocked trace。四份candidate artifact与三项绑定digest保留为私有诊断证据；根plan、packet、public source bundle、completion和terminal manifest均不得发布、删除或覆盖。已有任何public/terminal surface或已经blocked的trace时必须拒绝重试并保持原字节。

## Phase 5 review evidence

`phase-5-reviewer-report.md`每次run追加reviewer identity、writer/repair identity、run、preflight status、全部七项candidate authority digest、semantic checks、findings/warnings与decision。

`phase-5-repair-report.md`每轮记录repair identity、消费fingerprints、修改authority、before/after terminal-authority candidate digest、完整重算结果与blocker。

Canonical gate写入Phase 5 trace：

- `status: pending|passed|blocked`
- `writer-id`
- `reviews[]`
- `repairs[]`

Review row只含`round`、`reviewer-id`、`validator-status`、七项candidate digest（`framework-refit-sha256`、`final-roadmap-sha256`、`atom-plan-mapping-sha256`、`final-change-plan-sha256`、`frozen-evidence-authority-sha256`、`phase-3-freeze-trace-sha256`、`candidate-handoff-sha256`）、固定`semantic-checks[]`和`finding-fingerprints[]`。

Repair row只含`round`、`repair-writer-id`、`finding-fingerprints[]`、`before-terminal-authority-sha256`、`after-terminal-authority-sha256`。

Terminal authority candidate digest的精确输入见trace contract。

## Workflow terminal integration gate

Phase 5 terminal后固定执行：

```text
main agent运行all-phase pre-handoff validator
-> fresh independent final integration reviewer
-> 写canonical final-integration-review.json
-> finalizer以exclusive atomic create锁定review path/raw-bytes SHA
-> finalizer执行语义校验并一次性写passed|blocked attempt result
-> finalizer写review mirror、workflow-completion.trace.json与manifest commit marker
-> all-phase complete validator
-> integration-passed后handoff；否则blocked
```

- Final integration reviewer是workflow-level一次性只读gate，不是Phase 5 reviewer，不得repair、重新refit或回写evidence。
- Reviewer身份必须与全部writer/reviewer/repair writer不同。
- Reviewer必须核对Phase 3 freeze、Phase 4 neutral collections、Phase 5 refit/final-roadmap/mapping、baseline、公开source/slices、packet和根plan。
- Reviewer必须重新执行Phase 5九项semantic checks，而不能只确认DAG无环或digest一致；canonical JSON必须逐Capability、逐Change、逐outcome thread、逐dependency edge、逐guard link记录结果，并记录一次完整occurrence chain结果。
- `reviewed-artifacts[]`必须精确绑定trace contract固定顺序的七份terminal artifact；review顶层与各result row不得退化为单一`semantic-checks[]`摘要。
- Passed review JSON必须绑定当前`terminal-authority-sha256`。
- Finalizer必须在任何review semantic prevalidation之前发布不可替换的attempt authority；prevalidation失败也必须发布blocked attempt result，且不得替换review或发起第二次final integration attempt。
- 仅留下submitted attempt时，只允许对同一review raw bytes执行crash recovery；digest drift直接终态blocked。
- Completion trace `status: integration-passed`必须绑定review JSON path/digest与相同terminal digest。
- Review无效时不得发布completion；合法passed或blocked review也必须先终态化attempt result，随后才可发布对应completion。
- Manifest `workflow-status`只有在completion trace合法发布后才能变为`integration-passed`。
- Complete validator或review失败时写blocked review/completion authority与manifest workflow-status；不得自动进入新repair loop。
- Selector和下游只接受合法`integration-passed` completion；Phase 5 terminal本身不等于workflow complete。
