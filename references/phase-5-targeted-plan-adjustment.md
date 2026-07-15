# Phase 5：共享标准 refit、ambiguity 裁决与 checkpoint resume

Phase 5在Phase 3 `coverage-complete`且Phase 4 `assembled`后运行。它使用Phase 3逐GA mapping ambiguity、Phase 4原文集合和`references/change-capability-framework-principles.md`中与Phase 1完全相同的标准，复审initial framework、裁决全部ambiguity并只做source-backed最小调整。

writer必须完整读取`references/cross-phase-contract.md`、`references/change-capability-framework-principles.md`、本文件和`references/trace-sidecar-contract.md`。

Phase 5不执行semantic dedup；mapping与framework refit不得重新读取原始source，也不得创建replacement source window。若已从冻结row、coverage metadata或用户明确报告取得seed locator，可在生成request前对预先固定的同一source line window执行一次只读defect verification；不得全文扫描、搜索其他位置、迭代扩窗或在本Phase重提取evidence。只有核验确认合法defect、source digest仍与Phase 1/2冻结值一致且locator有界时，才可在checkpoint后生成唯一targeted evidence patch request；否则必须在Phase 5裁决或`blocked`。

## 输入

- Phase 1 `initial-change-plan.md`
- Phase 2/3 semantic JSON evidence、global atom index和mapping ambiguities
- Phase 4全部evidence collection Markdown及派生index
- 只读`openspec/specs/<capability>/spec.md` repository baseline
- checkpoint resume时的唯一`source-aligned-evidence-patch-request-v1`、`source-aligned-phase-5-checkpoint-v1`及Phase 2–4 incremental result
- 仅用于request前一次性核验的预先固定source line window；不得作为mapping/refit input或持久化为replacement evidence

## 输出与权威

所有状态都写入：

- semantic `phase-works/phase-5/framework-refit-trace.json`
- 由refit JSON渲染的`phase-works/phase-5/plan-refit-review.md`
- 非canonical `phase-works/phase-5/phase-5-agent-report.md`
- control `trace/phase-5.trace.json`

`needs-targeted-evidence-patch`还必须写入：

- control `phase-works/phase-5/evidence-patch-request.json`
- semantic `phase-works/phase-5/phase-5-checkpoint.json`

`accepted` / `adjusted`还必须写入：

- 内容权威`phase-works/phase-5/change-plan.md`
- 根`change-plan.md`，且与前者逐字节一致
- semantic `phase-works/phase-5/atom-plan-mapping.json`
- mapping Markdown mirror
- derived `capability-baseline-reconciliation.json|md`
- derived `final-packet-index.json`
- `change-capability-anchors/<change>/<change>.md`
- `change-capability-anchors/<change>/capability-anchors/<capability>.md`
- `change-capability-anchors/index.md`

agent report是非canonical流程证据，不进入manifest。Phase 5不创建reviewer/repair report，也不启动Phase reviewer/repair-writer。

禁止创建或保留：`phase5-refit.config.json`、`input-change-plan.md`、`source-window-refit-trace.md`、`change-plan-adjustments.md`、`capability-progression-review.md`、`change-complexity-review.md`、`plan-refit-decision-log.md`、`alignment-final-report.md`、`change-capability-human-plan.md`。

## 固定复审顺序

1. 对每个initial Capability逐项应用共享Capability gate。
2. 对每个initial Change逐项应用共享Change gate。
3. 审阅`unassigned-and-gap.md`中的每个GA。
4. 对全部GA执行一次只读evidence-integrity检查，并对`mapping-ambiguities[]`中的每个GA确定唯一final mapping tuple；mapping ambiguity不得触发evidence patch。只有确认冻结atom包含可独立引用的多个occurrence且locator有界时，才可定性为`mixed-independent-occurrences`并请求`split`。
5. 重建Change-Capability overlay。
6. 按hard dependency和outcome maturity复审roadmap顺序。
7. 在`framework-refit-trace.json`中冻结decision和final framework。
8. 直接编写final `change-plan.md`，与refit JSON交叉校验。
9. 只读核对final target Capability repository baseline。
10. 为每个GA写入final mapping；该terminal mapping row是同GA ambiguity的唯一resolution。
11. 运行mechanical helper生成全部mirror和派生物。

Phase 1 framework默认保留。只有evidence collection证明共享gate失败时才允许split、merge、add、remove、rename、reorder或scope adjustment；不得从零重新规划。

## 最小 refit

Capability decision：

- 全部gate通过：`keep`，final IDs只能包含自身。
- 混合多个不相关稳定behavior boundary：`split`，至少两个final Capability。
- 多个Capability重叠且不能独立成立：`merge`，至少两个input指向同一个final Capability。
- unassigned/gap暴露新的稳定behavior boundary：新增。
- 只是implementation component、临时阶段或Change alias：`remove`、`merge`或`rename`。

Change decision：

- 全部gate通过：`keep`。
- 包含多个可独立acceptance/archive的outcome：`split`。
- 多个Change共同构成不可分outcome：`merge`。
- evidence属于另一Change或boundary变化：`scope-adjusted`。
- unassigned/gap形成独立outcome：新增。
- 只有辅助实现内容且无独立outcome：`remove`或并入consumer。
- roadmap违反hard dependency：`reorder`，final顺序必须实际变化。
- boundary正确但名称不准确：`rename`。

不得引入planning graph、atom clustering、complexity budget、固定evidence count threshold或基于矩阵形状的调整。

## Mapping ambiguity adjudication

Phase 3 `mapping-ambiguities[]`中的每个GA必须在terminal `atom-plan-mapping.json`中恰好有一个完整row，且evidence ref一致。validator按ambiguity `dimensions[]`读取同GA mapping row中的对应final字段并确认没有placeholder。不得在framework refit JSON、review mirror或其他artifact复制第二份final mapping。

candidate owner/target/projection不一致、`unassigned`、gap、relation选择或framework调整都必须在本Phase裁决，不得请求evidence patch。checkpoint期间已经完成的mapping只保存在`completed-rows.atom-plan-mappings[]`，terminal时仍以mapping v4为唯一权威。

若本Phase发现Phase 3未记录的mapping ambiguity，不得修改Phase 3 authority或请求evidence patch；必须在该GA唯一terminal mapping row中直接选择完整tuple，并在reason记录late-discovered ambiguity及裁决依据。无法唯一裁决且需要产品决定时`blocked`。该发现不单独改变`accepted|adjusted`；状态仍只由framework是否发生source-backed调整决定。

## Framework refit trace v2

`framework-refit-trace.json`使用`source-aligned-framework-refit-trace-v2`，顶层必须且只能包含：

- `trace-schema`
- `trace-contract-version`
- `status`
- `initial-plan-ref`
- `capability-reviews[]`
- `change-reviews[]`
- `unassigned-and-gap-reviews[]`
- `final-framework`
- `patch-history[]`
- `issues[]`
- `language-self-check`

`initial-plan-ref`包含`artifact-path`和`sha256`。

`capability-reviews[]`每行包含`input-capability`、`evidence-collection-path`、`decision`、`final-capabilities[]`、`gate-results[]`、简体中文`reason`。每个initial Capability按Phase 1顺序恰好一行。

`change-reviews[]`每行包含`input-change`、`evidence-collection-path`、`decision`、`final-changes[]`、`gate-results[]`、简体中文`reason`。每个initial Change按Phase 1顺序恰好一行。

每个`gate-results[]` item只包含`gate`、`result: passed|failed`和非空`note`。

`unassigned-and-gap-reviews[]`每行包含`global-atom-id`、`evidence-ref`、`disposition`、`final-change`、`final-capability`和简体中文`reason`。每个Phase 4 `unassigned-and-gap` GA恰好一行，evidence ref必须与派生index一致。

terminal `final-framework`只包含`change-order[]`、`capabilities[]`和`overlay[]`；每个overlay row只包含`change`、`capability`、`capability-impact: new|modified`。

`patch-history[]`普通路径必须为`[]`。每行必须且只能包含`request-id`、`patch-request-ref`、`checkpoint-ref`、`finding-fingerprint`和`status: requested|closed|blocked`。`needs-targeted-evidence-patch`时必须恰好一条`requested`；checkpoint resume后的terminal状态必须把同一行改为`closed`；失败终止时改为`blocked`。不得出现第二行。

`accepted`要求所有initial unit为`keep`、所有gate通过、每个mapping ambiguity GA都有完整terminal mapping、`issues[]`为空，final framework的集合、顺序、overlay和Change/Capability语义与Phase 1实质一致。

`adjusted`要求所有gate通过、每个mapping ambiguity GA都有完整terminal mapping、`issues[]`为空，并至少存在一个可追溯的split/merge/add/remove/rename/reorder/scope adjustment。

`needs-targeted-evidence-patch`要求`final-framework: null`、非空`issues[]`、一条`requested` patch history，以及有效request/checkpoint。provisional framework只保存在checkpoint，不构成terminal authority。`blocked`要求非空`issues[]`；若已发request，patch history必须为`blocked`。

## Evidence patch request v1

`evidence-patch-request.json`使用`source-aligned-evidence-patch-request-v1`，顶层必须且只能包含`trace-schema`、`trace-contract-version`、`request-id`、`base-artifacts`、`targets`和`protected-rows`；`request-id`固定为`EPR-0001`。

`base-artifacts`必须且只能包含`phase-2-trace-sha256`、`phase-3-trace-sha256`、`global-atom-index-sha256`、`coverage-review-sha256`和`phase-4-index-sha256`。

每个`targets[]` row必须且只能包含：

- `source-document`
- nullable `source-atom-id`
- nullable `global-atom-id`
- nullable `evidence-ref`
- `defect`
- `allowed-operations[]`
- `allowed-line-window`，且只包含`start`、`end`
- `new-source-atom-ids[]`
- nullable `base-row`；existing target保存patch前完整source atom row，missing occurrence为null
- nullable `base-row-sha256`
- `canonical-owner`
- 简体中文`reason`
- `defect-witness`

`defect`只允许`quote-mismatch`、`range-mismatch`、`mixed-independent-occurrences`、`missing-occurrence`；operation只允许`replace-quote`、`adjust-range`、`split`、`add`。`missing-occurrence`只能`add`且旧identity、`base-row`和`base-row-sha256`必须为null；其新ID从`patch-epr-0001-add-01`开始。existing target的`base-row-sha256`必须绑定immutable `base-row`；patch后除allowed operation对应的`source-fact`/`line-ranges`外，原row其余字段必须逐字段不变。`split`的新ID从`<old-source-atom-id>.part-02`开始。禁止删除、合并或重命名atom。

`defect-witness`必须且只能包含`locator-origin`、`source-sha256`和`window-sha256`；`locator-origin`必须且只能包含非空`row-refs[]`。每个row ref必须且只能包含`artifact-path`、`row-kind`、`row-key`、`row-sha256`，`row-kind`只允许`phase-2-atom|phase-3-disposition`。Phase 2 key固定`<source-document>::<source-atom-id>`并指向canonical atoms JSON；Phase 3 key固定disposition ID并指向canonical coverage review JSON。origin必须是同一source的immutable canonical row且digest匹配；existing target必须包含自身`base-row`的Phase 2 atom origin；missing target不得用已由gap承接的`missing-obligation` disposition伪造遗漏。`allowed-line-window`必须完全位于全部origin line ranges合并后的连续闭包内；`source-sha256`绑定完整source，`window-sha256`绑定该1-based window按LF连接、无尾随LF的UTF-8字节。

发出request前必须重新运行Phase 2、Phase 3与Phase 4 base validator；非法base drift不得被request“补合法”。allowed line window由witness在只读核验前固定，existing target的base row range必须落在其中；当前source SHA必须同时匹配Phase 1与Phase 2冻结值。合法`quote-mismatch`只能是仍为原文substring但选择错误或截断的引文；非原文Phase 2 base表示上游gate非法，必须直接`blocked`，不能通过request洗白。缺少seed locator、核验需要扩窗或二次读取时直接`blocked`。

`protected-rows`必须且只能包含`phase-2-atoms`、`phase-3-documents`、`phase-3-gap-atoms`、`phase-3-dispositions`、`phase-3-mapping-ambiguities`、`global-atoms`、`phase-4-index-rows`和`phase-4-rendered-artifacts`。每行保存对应stable key字段与`sha256`；row hash统一使用compact sorted UTF-8 JSON SHA256。除target/new GA自身外，所有既有mapping ambiguity row都必须保护，即使其source range与patch window重叠也不得豁免。Phase 4 rendered protection必须恰好覆盖target old/new bucket之外的collection：split successor继承原candidate bucket，missing occurrence机械进入unassigned bucket；只有新增occurrence时index mirror才进入affected closure。

## Phase 5 checkpoint v1

`phase-5-checkpoint.json`使用`source-aligned-phase-5-checkpoint-v1`，顶层必须且只能包含：

- `trace-schema`、`trace-contract-version`
- `checkpoint-id: P5CP-0001`
- `stage: mapping`
- `patch-request-ref`，且只包含`artifact-path`、`sha256`
- `input-fingerprints[]`，每行只包含`artifact-path`、`sha256`
- `provisional-framework`，包含terminal framework的`change-order`、`capabilities`、`overlay`，以及`dependency-edges[]`、`change-lineage[]`、`capability-lineage[]`、`ga-lineage[]`、`change-semantic-digests[]`、`capability-semantic-digests[]`
- `completed-rows`
- `pending-ids`
- `allowed-update-scope`
- `preserved-row-digests[]`
- `patch-attempt`

evidence patch checkpoint只允许在全局review与mapping完成后的`mapping` stage冻结；不得在capability/change/unassigned中间阶段发request。`completed-rows`与`pending-ids`都必须且只能包含`capability-reviews[]`、`change-reviews[]`、`unassigned-and-gap-reviews[]`、`atom-plan-mappings[]`。每一类分别形成完整且不相交的partition：全部initial Capability、全部initial Change、Phase 4 unassigned/gap GA及全部GA都不得遗漏。pending capability reviews必须恰好等于`allowed-update-scope.initial-capabilities[]`；pending change reviews必须恰好等于`allowed-update-scope.initial-changes[]`；pending atom mappings必须恰好等于`allowed-update-scope.global-atom-ids[]`；pending unassigned/gap reviews必须恰好等于scope GA与Phase 4 unassigned/gap GA（含确定性预分配后仍属该bucket的新GA）的交集。scope内row不得同时保留在completed集合中。

`dependency-edges[]`每行只含`change`和`depends-on`，按provisional roadmap顺序冻结hard dependency。`change-lineage[]`和`capability-lineage[]`按Phase 1顺序记录每个initial review unit在patch前产生的provisional final IDs；completed row必须与其lineage一致。`ga-lineage[]`按GA顺序记录`global-atom-id`、`provisional-final-change`、`provisional-final-capability`和`provisional-related-capabilities[]`，恰好覆盖patch前existing GA，并与completed mapping一致；它只用于证明origin，不替代terminal mapping authority。`change-semantic-digests[]`每行只含`final-change`、`sha256`，`capability-semantic-digests[]`每行只含`final-capability`、`sha256`；两者必须按provisional plan顺序恰好覆盖所有final ID。digest绑定final Change的全部intent/outcome/scope/behavior/acceptance/dependency/order/archive语义字段，或final Capability的Purpose/Owns/Excludes/Boundary语义字段。发布needs-patch前，mechanical helper必须在清理terminal surface之前将dependency、lineage和digest与provisional refit/mapping/`change-plan.md`逐row比对；不匹配则不得进入patch链。

`allowed-update-scope`必须且只能包含`global-atom-ids[]`、`initial-changes[]`、`initial-capabilities[]`、`final-changes[]`、`final-capabilities[]`和`allow-roadmap-reorder: false`。initial framework scope可以为空；非空时必须至少选择一个request target的Phase 4 initial Change/Capability bucket作为root，并恰好等于所选root经initial与provisional dependency/overlay边（由lineage反向投影到initial unit）得到的最小连通闭包，禁止夹带或漏掉相连review unit。final scope采用old/new集合语义：既有provisional ID是可保留或删除的mutable old ID，其全部initial origin必须在initial scope内；没有initial origin时，必须有非空GA lineage且全部origin GA位于GA scope。全新ID可在initial scope为空时由pending GA/unassigned review预声明，terminal时必须且只能由pending initial review、unassigned review或mapping实际产生或引用。只有两个endpoint都在mutable closure内的overlay或dependency edge才允许改变，任何跨scope边必须逐字保留。`preserved-row-digests[]`每行只包含`row-kind`、`row-key`、`sha256`。`patch-attempt`只包含`attempt: 1`、`finding-fingerprint`和`authority-digest`；后者是`input-fingerprints`、`patch-request-ref`和`provisional-framework`组成的compact sorted JSON SHA256，不得任意填写。

`global-atom-ids[]`必须恰好等于request既有target GA与确定性预分配的新GA，不得夹带其他base GA。全framework guard分别计算四个typed universe：initial Change、provisional final Change、initial Capability、provisional final Capability；scope完整覆盖其中任一个非空universe时即必须`blocked`。此外保留initial与provisional并集的组合覆盖检查，因此既不能借remove/rename漏掉initial unit，也不能因已remove的initial unit尚未入scope而放行对全部current final framework的重写。

`finding-fingerprint`必须由request `targets[]`机械计算：为每个target只保留`source-document`、nullable `source-atom-id`、nullable `global-atom-id`、nullable `evidence-ref`、`defect`、`allowed-line-window`以及witness的`source-sha256`、`window-sha256`，按compact sorted JSON对row排序，再计算`{"evidence-integrity-defects": rows}`的compact sorted UTF-8 JSON SHA256。不得纳入reason、canonical owner、allowed operations、successor ID、locator origin row或writer identity；因此同一defect locator不能通过改写措辞或修复方案伪装成新finding。

`input-fingerprints[]`只锁定patch期间不得变化的authority，至少包含Phase 1 initial plan和共享framework principles，可包含本次refit依赖的repository baseline；不得要求patch后的Phase 2/3/4整文件digest等于checkpoint。patch前P2–P4 digest由request `base-artifacts`保存，未受影响内容由protected/preserved row digest证明。

request只能从Phase 2–4均为initial success snapshot且尚未发布canonical Phase 5 trace的首次Phase 5执行中发出。accepted、adjusted、blocked、closed或任一incremental-patch状态都不可改回requested。resume前必须验证全部input fingerprint和preserved row digest。只能重算pending ID及已冻结allowed scope；其他completed row必须复用。若scope需要扩张为全部Change或全部Capability、roadmap必须reorder、fingerprint失效或finding在authority digest不变时重现，必须`blocked`，不得全量refit或生成第二个request。

若Phase 2–4增量链失败，main agent不得恢复完整refit，只调用`phase5_plan_refit.py --abort-patch-chain --issue ...`执行机械control transform。该transform保持request/checkpoint字节以及全部semantic review、mapping、framework row不变，只把refit `status`设为`blocked`、将`issues[]`替换为单一终止原因、把同一patch history row的`status`从`requested`改为`blocked`，再确定性生成`execution-mode: checkpoint-resume`的blocked trace与review；它不属于semantic writer。abort校验只验证immutable request/checkpoint的schema、ref、finding/authority digest和completed/preserved row内部自洽；不得要求已失败或已清理的增量surface仍存在，也不得把current Phase 1/principles与冻结fingerprint重新比对，因为fingerprint drift本身就是合法blocked原因。blocked review渲染同样不得读取失败或损坏的current Phase 3 surface；此时`Mapping Ambiguities`可以为空，request/checkpoint仍是static authority。

## plan-refit-review.md

review Markdown完全由refit JSON与只读Phase 3 ambiguity rows渲染，固定包含`## Capability Review`、`## Change Review`、`## Unassigned and Gap Review`、`## Mapping Ambiguities`、`## Patch History`、`## Final Decision`和`## 语言自检`。`Mapping Ambiguities`只镜像Phase 3的GA、evidence ref、dimensions和reason，既不写候选值，也不写final value或resolution；terminal mapping仍是唯一resolution authority。不得直接编辑review或从review反向恢复语义；validator逐字重渲染比较。

## Final change plan

`change-plan.md`继续使用Phase 1固定heading和Change字段，包括`Source Semantic Landscape`，但把candidate/hypothesis改为final结论。final `Capability Map`表头固定为：

| Capability | Purpose | Owns | Excludes | Boundary Rationale |
| --- | --- | --- | --- | --- |

final `Change-Capability Overlay`表头固定为：

| Change | Capability | Capability Impact | Direct Behavior Delta |
| --- | --- | --- | --- |

`Capability Impact`只允许`new|modified`。

每个final Change必须保留共享标准要求的intent、outcome、范围、behavior completeness profile、acceptance evidence、hard dependency、排序理由、独立完成与归档、拆分/合并判断。mechanical helper不得补写缺失内容。

validator必须校验final plan的Change/Capability集合、顺序和overlay与refit `final-framework`一致。

## Atom plan mapping v4

`atom-plan-mapping.json`使用`source-aligned-atom-plan-mapping-v4`。顶层包含`trace-schema`、`trace-contract-version`、`artifact-path`、`rows[]`。

每个GA恰好一行，且只能包含`global-atom-id`、`evidence-ref`、`final-owner-change`、`final-relation`、`final-artifact-projection`、`final-capability-impact`、`final-target-capability`、`related-capabilities[]`和简体中文`reason`。

- `evidence-ref`与global index完全一致；source path/range/fact通过resolver取得，不在mapping复制。
- direct和non-direct都必须归属一个final Change。
- relation只允许`direct`、`context`、`dependency`、`preserve`、`reference`、`non-goal`。
- direct projection只允许`spec-requirement`、`spec-guard`、`design-obligation`、`verification-obligation`。
- direct spec/guard必须指定具体Capability和`new|modified`。
- direct design/verification以及所有non-direct使用`none` / `none`；non-direct projection使用`contextual-only`。
- `related-capabilities[]`只表达source-explicit、non-owning relation，不推进Capability。
- refit gap review必须与对应mapping一致；每个mapping ambiguity GA必须存在一个完整mapping row，该row是唯一resolution。
- mapping推导的overlay advancement必须与refit JSON和final plan一致。

## Mechanical helper

`phase5_plan_refit.py`只执行确定性工作：

- 读取final plan、framework refit v2、mapping v4、Phase 2/3 resolver、mapping ambiguities、可选checkpoint及repository specs；
- 拒绝缺少必需Change字段、refit/ambiguity cardinality错误、patch history错误或final framework不一致；
- 从refit JSON生成review mirror，不得从review取得语义；
- `needs-targeted-evidence-patch`与`blocked`只生成review/trace并清理terminal surface；patch lifecycle blocked保留immutable request/checkpoint引用；
- 生成mapping Markdown、baseline、final packet、Capability view、packet index、anchor index和根plan；
- packet中的原文直接来自Phase 2/3冻结的`source-fact`；
- checkpoint resume时验证terminal input已逐字复用scope外completed row，且只有allowed scope内row被重算；helper不代写或重新合并语义row；
- `--abort-patch-chain --issue ...`只执行固定control transform：修改refit `status`、`issues[]`与唯一history row的`status`，并刷新blocked review/trace；不得改动任何semantic row或request/checkpoint，也不得依赖失败或损坏的current Phase 3 ambiguity surface；
- 不接受config，不推断semantic decision，不补写acceptance/dependency/non-goal/archive文案。

validator重新生成并检查review、mapping/baseline Markdown、packet、Capability view、anchor index和packet index，拒绝drift或stale文件。

## Status 与 trace v4

- `accepted`：framework实质不变，全部GA完成final mapping和baseline reconciliation，全部ambiguity由同GA terminal mapping唯一裁决。
- `adjusted`：framework按共享标准发生source-backed最小调整，并完成全部terminal artifact。
- `needs-targeted-evidence-patch`：存在合法且有界的evidence defect，已生成唯一request与checkpoint。
- `blocked`：需要第二次patch、patch/scope无法有界、source evidence存在需要用户决定的产品冲突、checkpoint失效、validator失败或repository baseline不可访问。

terminal trace使用`source-aligned-phase-5-trace-v4`，记录final plan、framework refit JSON、review mirror、mapping、baseline和packet index各自的path/SHA。无patch terminal使用`execution-mode: initial`、空patch history且request/checkpoint path/SHA为null；checkpoint resume terminal使用`execution-mode: checkpoint-resume`，绑定immutable request/checkpoint并记录同一条closed history。

`needs-targeted-evidence-patch` trace使用`execution-mode: initial`，记录refit JSON、review mirror、request、checkpoint、同一条requested history及与refit JSON一致的非空`issues[]`；此时禁止final plan、mapping、baseline、packet index、根plan、final Change packet、Capability view和anchor index。patch lifecycle blocked使用`execution-mode: checkpoint-resume`并记录同一条blocked history；普通initial blocked不伪造patch execution mode。`blocked`不得自动重启Phase 5或重复当前Phase。

Phase 5 validator通过后才可记录`accepted` / `adjusted`；失败即`blocked`，不得启动Phase reviewer/repair或自动重复Phase 5。随后必须由main agent运行all-phase complete validator和一次workflow-level final integration reviewer；两者都通过后才能handoff。
