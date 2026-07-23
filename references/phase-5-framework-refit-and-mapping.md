# Phase 5：Boundary Refit、Final Roadmap 与 Terminal Mapping

Phase 5基于冻结evidence和共享原则完成三份互不重叠的semantic authority：

1. `framework-refit-trace.json`只记录initial→final Capability、Change、outcome thread、dependency edge与guard link review；
2. `final-roadmap.json`是最终semantic landscape、Capability、outcome thread、Change、dependency edge、guard link、directive resolution、order、prefix、overlay与foundation的唯一权威；
3. `atom-plan-mapping.json`是逐GA owner/relation/projection/target与ambiguity resolution的唯一权威。

Handoff由final roadmap + terminal mapping + frozen evidence确定性派生。Phase 1顺序、Phase 2 candidate mapping和Phase 4 collection均不是final order authority。

Writer必须完整读取cross-phase、共享原则、本文件、review gate和trace contract。

## 输入

- Phase 1 initial framework；
- Phase 2/3 frozen evidence、directive与GA；
- Phase 3 potential mapping ambiguity；
- Phase 4 neutral collections仅可供人工辅助阅读；helper、validator、mapping与handoff派生不得读取其Markdown或membership；
- repository Capability baseline。

Phase 5不重新读取source，不修改frozen authority，不从Markdown mirror恢复语义。进入candidate计算前，helper必须运行完整Phase 1/2/3 canonical validator，并验证Phase 3 terminal review绑定当前source bytes、Phase 2 atom sidecar、global index、coverage review及其确定性Markdown mirror；摘要自洽但不满足canonical contract的冻结结果必须阻断。

## 输出

```text
phase-works/phase-5/
├── framework-refit-trace.json
├── plan-refit-review.md
├── final-roadmap.json
├── change-plan.md
├── atom-plan-mapping.json|md
├── capability-baseline-reconciliation.json|md
├── final-packet-index.json
├── phase-5-agent-report.md
├── phase-5-reviewer-report.md
└── phase-5-repair-report.md  # 仅发生repair时
```

根`change-plan.md`只在Phase 5 bounded gate通过后发布，并与Phase 5 plan逐字节一致。

## Semantic flow

1. 按稳定identifier逐项复审每个initial Capability与Change的boundary gate；不得保留或借用Phase 1顺序，neutral evidence只作全局support，不形成candidate bucket保留偏置。
2. 形成provisional final Capability/Change boundary；不保留Phase 1 order。
3. 为全部GA建立provisional terminal mapping；裁决Phase 3 ambiguity与late-discovered ambiguity。
4. 从全部非空`delivery-directives[]`建立完整terminal directive resolution。
5. 对每个final Change执行8项Change gate、guard allocation、Prefix Utility、Consumer Closure与foundation-like审查。
6. 在final Change形成后建立typed hard dependency edges；逐条执行四项dependency proof。
7. 从dependency DAG和显式directive选择final order，并对每个prefix执行viability review。
8. 原子写入final roadmap与terminal mapping；mapping envelope不内嵌roadmap ref，由Phase 5 trace、refit refs与validator共同绑定同一terminal candidate。
9. 使用final roadmap order、mapping与baseline推导overlay、impact、final plan与公开handoff。
10. Helper在staging校验全部authority并生成派生物；运行Phase 5 preflight与bounded review。
11. Review pass后发布terminal authority、根plan与Phase 5 terminal trace。

任何一步需要产品决定、无法形成唯一mapping/roadmap、baseline不可访问、dependency proof失败或共享原则冲突时返回`blocked`。

## Framework refit v5

`framework-refit-trace.json`使用`source-aligned-framework-refit-trace-v5`，只负责initial→final lineage review。

顶层只含：

- `trace-schema`
- `trace-contract-version`
- `status: accepted|adjusted|blocked`
- `initial-framework-ref`
- `final-roadmap-ref`
- `capability-reviews[]`
- `change-reviews[]`
- `outcome-thread-reviews[]`
- `dependency-edge-reviews[]`
- `guard-link-reviews[]`
- `issues[]`
- `language-self-check`

两个ref只含repository-relative`artifact-path`与`sha256`。`initial-framework-ref`固定绑定Phase 1 `initial-framework.json`，不得绑定Markdown mirror；terminal `final-roadmap-ref`绑定当前`final-roadmap.json`，blocked时为`null`。

Capability review row只含：

- `input-capability`
- `decision: keep|split|merge|remove|rename`
- `final-capabilities[]`
- 固定8项`initial-gate-results[]`
- `supporting-global-atom-ids[]`
- 中文`reason`

每个`initial-gate-results[]` row只含`gate`、`result: passed|failed`、中文`note`与非空`evidence-ga-ids[]`，并按共享原则固定8项顺序完整覆盖。

Change review row只含：

- `input-change`
- `decision: keep|split|merge|remove|rename|scope-adjusted`
- `final-changes[]`
- 固定8项`initial-gate-results[]`
- `supporting-global-atom-ids[]`
- 中文`reason`

Outcome thread、dependency edge与guard link review分别按final roadmap对应array顺序完整覆盖。每行只含对应的`outcome-thread-id|dependency-id|guard-link-id`、`result: passed`、非空`evidence-ga-ids[]`与中文`reason`。

Refit不得内嵌final semantic landscape、Capability、outcome thread、Change、dependency edge、guard link、directive resolution、order、prefix、overlay、foundation或mapping。顺序变化不属于Change boundary decision，只能由final roadmap的order authority表达。

`accepted`只表示Capability/Change boundary保持且逐项decision为keep；它不表示Phase 1 order或overlay被接受。`adjusted`表示存在可追溯boundary调整。Final overlay始终由terminal mapping与repository baseline重新推导，不参与`accepted|adjusted`判定。Blocked时final-roadmap ref为`null`且issues非空。

## Final roadmap v1

`final-roadmap.json`使用`source-aligned-final-roadmap-v1`，是final framework、outcome与sequence唯一authority。

顶层只含：

- `trace-schema`
- `trace-contract-version`
- repository-relative `artifact-path`
- `semantic-landscape[]`
- `capabilities[]`
- `outcome-threads[]`
- `changes[]`
- `dependency-edges[]`
- `guard-links[]`
- `delivery-directive-resolutions[]`
- `change-order[]`
- `order-decisions[]`
- `prefix-reviews[]`
- `overlay[]`
- `foundation`
- `language-self-check`

`artifact-path`固定指向`phase-works/phase-5/change-plan.md` deterministic mirror；Phase 5 gate通过后，helper再把同一字节发布到根`change-plan.md`。Semantic landscape只保存final coarse synthesis，不建立另一个order authority。

Capability row只含：

- `capability`
- `purpose`
- `owns`
- `excludes`
- `boundary-rationale`
- 非空`evidence-ga-ids[]`

Outcome thread row只含：

- `outcome-thread-id`
- `beneficiary`
- `trigger`
- `observable-result`
- `acceptance-signal`
- `primary`
- 非空`outcome-ga-ids[]`
- 非空`acceptance-ga-ids[]`
- `first-realizing-change`

至少一个outcome thread必须为primary；`first-realizing-change`必须等于`change-order[]`中首个realize该thread的Change。

Change row只含：

- `change`
- `intent`
- `scope-in`
- `scope-out`
- `behavior-profile`
- `realizes-outcome-thread-ids[]`
- `usable-postcondition`
- `consumer-closure`
- `independent-archive`
- `split-merge-judgment`
- `outcome-ga-ids[]`
- `acceptance-ga-ids[]`

`behavior-profile`只含：

- `trigger-context`
- `normative-behavior`
- `observable-outcome-invariant`
- `important-exception-error-semantics`
- `acceptance-evidence`

`consumer-closure`只含`mode`与`ref`，mode只允许`existing-baseline|foundation-first-outcome|same-change-outcome`。除foundation外，每个Change必须realize outcome、拥有非空outcome/acceptance GA、使用当前consumer closure并推进至少一个Capability。

Dependency edge row只含：

- `dependency-id`
- `prerequisite-change`
- `dependent-change`
- `kind`
- `contract-id`
- `produced-contract`
- `consumed-contract`
- `counterfactual-failure`
- `co-delivery-rejection`
- 非空`evidence-ga-ids[]`

Kind只允许`behavior-availability|compatibility-contract|lifecycle-state|safety-invariant`。每条edge必须通过四项dependency gate，端点存在、无重复、无环且prerequisite位于dependent之前。

Guard link row只含：

- `guard-link-id`
- `guarding-change`
- `guarded-outcome-thread-id`
- `surface-state: existing|planned`
- 非空`evidence-ga-ids[]`

每个outcome最多一个guard link；planned guard必须由该outcome的`first-realizing-change`交付。

Delivery directive resolution row只含：

- `global-atom-id`
- `delivery-directive`
- `effect: defers|no-order-effect|orders|scopes`
- `affected-changes[]`
- `scope-label`
- `ordering-relations[]`
- 中文`reason`

每个`ordering-relations[]` row只含`before-change`与`after-change`。每个冻结非空directive的`(GA,directive)` pair恰好一行；空directive不得出现。Resolution不得修改冻结directive，所有ordering relation必须被`change-order[]`满足。

`explicit-precedence`必须使用`effect: orders`并提供非空ordering relation；`explicit-deferred`若使用`effect: defers`也必须提供非空ordering relation，使被延期Change不能被排到其前置结果之前。只有该deferred occurrence确实不影响当前roadmap时才可使用`no-order-effect`且关系为空。每条relation的两端都必须列入同row的`affected-changes[]`。

Order decision按position逐项覆盖`change-order[]`，每行只含：

- `position`
- `selected-change`
- `eligible-changes[]`
- `selection-basis`
- `supporting-global-atom-ids[]`
- 中文`reason`

Selection basis只允许`current-baseline-risk-retirement|explicit-source-directive|foundation-first|only-eligible|stable-tie-break|thin-observable-outcome`。`eligible-changes[]`必须等于当前dependency edge与directive ordering relation约束下的完整eligible set，selected Change必须是其中成员。

Prefix review row只含：

- `change`
- `delivered-prefix-outcome`
- `current-prefix-consumption`
- `guard-closure`
- `foundation-like-assessment: not-foundation-like|valid-foundation-exception`
- `result: passed|failed`
- 中文`reason`

每个final Change按`change-order[]`恰好一行。只有roadmap首项可用`valid-foundation-exception`，且最多一项。所有terminal roadmap row必须passed。

Overlay row只含`change`、`capability`、`capability-impact: new|modified`。`foundation`为`null`或只含`change`、`first-consumer-change`、非空`evidence-ga-ids[]`。Foundation必须位于首位、由紧邻primary-outcome consumer消费、不realize outcome、无overlay；没有foundation时首项必须realize primary outcome。

`change-order[]`必须恰好覆盖changes。除dependency edge与source directive外，不得从Capability topology、candidate mapping或GA数量推断order。

## Terminal mapping v5

`atom-plan-mapping.json`使用`source-aligned-atom-plan-mapping-v5`。

顶层只含：

- `trace-schema`
- `trace-contract-version`
- repository-relative `artifact-path`
- `rows[]`

`artifact-path`固定指向`atom-plan-mapping.md` mirror。Mapping row只含：

- `global-atom-id`
- `evidence-ref`
- `final-owner-change`
- `final-relation`
- `final-artifact-projection`
- `final-capability-impact`
- `final-target-capability`
- `related-capabilities[]`
- 中文`reason`

每个GA恰好一行。Owner与target必须存在于同一Phase 5 terminal candidate的final roadmap；该绑定由refit/Phase 5 trace path/digest与validator校验，不在mapping envelope重复保存。Direct spec/guard推进Capability；design、verification、non-direct不推进。

Mapping row只裁决owner/relation/projection/target和ambiguity，不保存dependency、guard allocation、prefix outcome或order理由。

## Advancement、baseline 与 plan

Helper使用唯一推导链：

```text
final-roadmap change-order
+ dependency edges
+ terminal direct spec/guard mapping
+ repository baseline
-> overlay/impact
-> final change-plan
-> baseline reconciliation
-> public source/slices/final packet
```

- Final plan是final-roadmap与mapping/baseline的确定性Markdown projection，不是第二份JSON authority。
- Final plan每个Change的硬依赖只从`dependency-edges[]`派生。
- Final packet `depends-on[]`与terminal dependency edges逐edge一致。
- Repository已存在Capability的每条edge为modified；absent Capability首次advancement为new，后续modified。
- Mapping impact、plan overlay、baseline与slice必须一致。

`capability-baseline-reconciliation.json`使用`source-aligned-capability-baseline-v2`，顶层只含`trace-schema`、`trace-contract-version`、`repository-specs-root`与`capabilities[]`。每个Capability row只含`capability`、`baseline-status`、`spec-path`、`spec-sha256`、`baseline-evidence`、`first-planned-advancement`、`required-first-relation`与`later-relation-rule`。

公开`change-source.md`由owner-scoped frozen evidence重算；Capability slice由对应direct spec/guard mapping重算。公开surface不得泄露GA、directive、mapping或roadmap review metadata。

## Foundation 与 guard terminal checks

- 空Capability slice仍是公开foundation marker；它必须与唯一`valid-foundation-exception` row一致。
- Foundation最多一个、roadmap首项、不参与hard dependency edge、无overlay。
- 其他Change必须有非空slice并通过Prefix Utility与Consumer Closure。
- `guard-closure`必须说明guard与当前受保护行为同Change，或说明它保护当前baseline的既有表面及独立可测结果。
- 完整identity/authorization/security Capability不得仅因未来行为需要而提前建设。

## Phase 5 bounded review

Phase 5 writer发布候选refit、final roadmap、mapping与plan后：

1. Helper运行`--prepare-review --writer-id <writer-id>`，完整校验candidate authority，确定性生成Phase 5 plan mirror与pending trace；
2. Validator运行`--phase phase-5 --preflight`；
3. 按review gate执行最多三次fresh review、两次repair；
4. Repair只能修改Phase 5 semantic authority；追加repair row后必须运行`--refresh-review-candidate`，从完整authority原子刷新plan/refit-review mirror与七项candidate digest（四份artifact、frozen evidence、Phase 3 freeze、完整staged handoff），再重跑preflight；
5. Gate通过后helper运行`--write`，在私有staging中全量生成并自检public source/slices、packet、baseline、mirror、根plan与terminal trace，然后原子发布；gate blocked时同一入口只原子终结canonical blocked trace；
6. Validator运行`--pre-handoff`；
7. Final integration reviewer写canonical review；
8. Finalizer `finalize_source_aligned_orchestrate.py --write`先原子记录one-shot review attempt及其terminal result，再发布review mirror与workflow completion；
9. Validator运行`--complete`。

Phase 5 trace使用`source-aligned-phase-5-trace-v6`，包含canonical review-gate。Pending时根plan不得存在；terminal accepted/adjusted要求gate passed。

第三轮review只要validator、九项check或finding任一未清零，就必须把gate从pending改为blocked。`--write`随后验证当前四份candidate path/SHA、三项绑定digest与完整blocked gate，并原子发布`block-kind: bounded-review` trace；它保留candidate authority用于私有诊断，但不得生成或改变根plan、packet、public source bundle、integration review、workflow completion或terminal manifest。既有public surface与blocked重试都必须无损拒绝。Refit自身在bounded review前失败则使用独立的`block-kind: framework-refit`最小trace，二者字段不得混用。

Phase 5 authority digest对七项SHA的compact sorted JSON计算：framework-refit、final-roadmap、terminal mapping、Phase 5 plan、frozen evidence authority、Phase 3 freeze trace和完整candidate handoff。Candidate handoff digest覆盖私有staging中全部预期非trace handoff path、文件字节与显式空目录，不包含terminal trace、manifest或review report。

`--prepare-review`和`--refresh-review-candidate`都不得发布根plan、packet或public source bundle，但必须在私有staging中全量生成并自检这些候选文件。Review针对七项candidate authority digest及其确定性派生关系；实际公开文件只由passed gate后的`--write`从相同authority重新生成、核对完整handoff digest后发布，再由`--pre-handoff`逐字节反向重算。

## Frozen evidence defect

若发现quote/range不可信、missing occurrence、mixed independent occurrence或directive extraction错误：

- 在refit issues与`block-kind: framework-refit` blocked trace记录稳定issue；
- `blocked`且不发布candidate roadmap/mapping/plan或terminal handoff；
- 不回写Phase 2/3、不创建patch request/checkpoint；
- 需要修正evidence时只能启动新的v7 generation。

## Terminal 与 workflow handoff

Phase 5 terminal表示其bounded gate通过，但不等于workflow complete。

随后必须：

1. 运行all-phase `--pre-handoff` validator，确认Phase 1–5 terminal authority完整且workflow仍为pending；
2. Final integration reviewer生成canonical根`final-integration-review.json`；passed review逐Capability、Change、outcome thread、dependency edge、guard link与occurrence chain记录结果，并绑定固定七份terminal artifact计算的`terminal-authority-sha256`；
3. Finalizer必须在语义预校验前以exclusive atomic create锁定review path/raw-bytes SHA；校验后以exclusive atomic create写唯一passed或blocked attempt result。无效review留下blocked result且不发布completion，也不得替换或重试；
4. 合法review终态化attempt result后，Finalizer才确定性生成review mirror与`trace/workflow-completion.trace.json`，绑定review path/digest与相同terminal digest；
5. Finalizer最后更新manifest，使`workflow-status`成为`integration-passed`；
6. 运行all-phase `--complete` validator。

只有合法workflow completion authority存在时，selector或下游才能消费final packet。
