# Phase 5：共享标准复审与JSON refit trace

Phase 5在Phase 3 `coverage-complete`且Phase 4 `assembled`后运行。它使用Phase 4原文集合和`references/change-capability-framework-principles.md`中与Phase 1完全相同的标准，复审initial framework并只做source-backed最小调整。

writer必须完整读取`references/cross-phase-contract.md`、`references/change-capability-framework-principles.md`、本文件和`references/trace-sidecar-contract.md`。

Phase 5不执行semantic dedup，不重新读取原始source，不创建replacement source window。冻结的`source-fact`过窄时返回targeted coverage/extraction recheck。

## 输入

- Phase 1 `initial-change-plan.md`
- Phase 2/3 semantic JSON evidence和global atom index
- Phase 4全部evidence collection Markdown及派生index
- 只读`openspec/specs/<capability>/spec.md` repository baseline

## 输出与权威

所有状态都写入：

- semantic `phase-works/phase-5/framework-refit-trace.json`
- 由refit JSON渲染的`phase-works/phase-5/plan-refit-review.md`
- 非canonical `phase-works/phase-5/phase-5-agent-report.md`
- control `trace/phase-5.trace.json`

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

agent/reviewer/repair report是非canonical流程证据，不进入manifest。

禁止创建或保留：`phase5-refit.config.json`、`input-change-plan.md`、`source-window-refit-trace.md`、`change-plan-adjustments.md`、`capability-progression-review.md`、`change-complexity-review.md`、`plan-refit-decision-log.md`、`alignment-final-report.md`、`change-capability-human-plan.md`。

## 固定复审顺序

1. 对每个initial Capability逐项应用共享Capability gate。
2. 对每个initial Change逐项应用共享Change gate。
3. 审阅`unassigned-and-gap.md`中的每个GA。
4. 重建Change-Capability overlay。
5. 按hard dependency和outcome maturity复审roadmap顺序。
6. 在`framework-refit-trace.json`中冻结decision和final framework。
7. 直接编写final `change-plan.md`，与refit JSON交叉校验。
8. 只读核对final target Capability repository baseline。
9. 为每个GA写入final mapping。
10. 运行mechanical helper生成全部mirror和派生物。

Phase 1 framework默认保留。只有evidence collection证明共享gate失败时才允许split、merge、add、remove、rename、reorder或scope adjustment；不得从零重新规划。

## 最小refit

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

## Framework refit trace v1

`framework-refit-trace.json`使用`source-aligned-framework-refit-trace-v1`，顶层必须且只能包含：

- `trace-schema`
- `trace-contract-version`
- `status`
- `initial-plan-ref`
- `capability-reviews[]`
- `change-reviews[]`
- `unassigned-and-gap-reviews[]`
- `final-framework`
- `issues[]`
- `language-self-check`

`initial-plan-ref`包含`artifact-path`和`sha256`。

`capability-reviews[]`每行包含`input-capability`、`evidence-collection-path`、`decision`、`final-capabilities[]`、`gate-results[]`、简体中文`reason`。每个initial Capability按Phase 1顺序恰好一行。

`change-reviews[]`每行包含`input-change`、`evidence-collection-path`、`decision`、`final-changes[]`、`gate-results[]`、简体中文`reason`。每个initial Change按Phase 1顺序恰好一行。

每个`gate-results[]` item只包含`gate`、`result: passed|failed`和非空`note`。

`unassigned-and-gap-reviews[]`每行包含：

- `global-atom-id`
- `evidence-ref`
- `disposition`
- `final-change`
- `final-capability`
- 简体中文`reason`

每个Phase 4 `unassigned-and-gap` GA恰好一行，evidence ref必须与派生index一致。

terminal `final-framework`只包含：

- `change-order[]`
- `capabilities[]`
- `overlay[]`

每个overlay row只包含`change`、`capability`、`capability-impact: new|modified`。

`accepted`要求所有initial unit为`keep`、所有gate通过、`issues[]`为空，final framework的集合、顺序、overlay和Change/Capability语义与Phase 1实质一致。

`adjusted`要求所有gate通过、`issues[]`为空，并至少存在一个可追溯的split/merge/add/remove/rename/reorder/scope adjustment。

`needs-coverage-recheck|blocked`要求`final-framework: null`和非空`issues[]`。

## plan-refit-review.md

review Markdown完全由refit JSON渲染，固定包含：

- `## Capability Review`
- `## Change Review`
- `## Unassigned and Gap Review`
- `## Final Decision`
- `## 语言自检`

不得直接编辑review或从review反向恢复语义；validator逐字重渲染比较。

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

每个GA恰好一行，且只能包含：

- `global-atom-id`
- `evidence-ref`
- `final-owner-change`
- `final-relation`
- `final-artifact-projection`
- `final-capability-impact`
- `final-target-capability`
- `related-capabilities[]`
- 简体中文`reason`

规则：

- `evidence-ref`与global index完全一致；source path/range/fact通过resolver取得，不在mapping复制。
- direct和non-direct都必须归属一个final Change。
- relation只允许`direct`、`context`、`dependency`、`preserve`、`reference`、`non-goal`。
- direct projection只允许`spec-requirement`、`spec-guard`、`design-obligation`、`verification-obligation`。
- direct spec/guard必须指定具体Capability和`new|modified`。
- direct design/verification以及所有non-direct使用`none` / `none`；non-direct projection使用`contextual-only`。
- `related-capabilities[]`只表达source-explicit、non-owning relation，不推进Capability。
- refit gap review的final Change/Capability必须与对应mapping owner/target一致。
- mapping推导的overlay advancement必须与refit JSON和final plan一致。

## Mechanical helper

`phase5_plan_refit.py`只执行确定性工作：

- 读取final `change-plan.md`、`framework-refit-trace.json`、mapping v4、Phase 2/3 resolver和repository specs；
- 拒绝缺少必需Change字段、refit cardinality错误或final framework不一致；
- 从refit JSON生成`plan-refit-review.md`，不得读取review取得语义；
- 生成mapping Markdown、baseline、final packet、Capability view、packet index、anchor index和根plan；
- packet中的原文直接来自Phase 2/3冻结的`source-fact`；
- 不接受config，不推断semantic decision，不补写acceptance/dependency/non-goal/archive文案。

validator重新生成并检查review、mapping/baseline Markdown、packet、Capability view、anchor index和packet index，拒绝drift或stale文件。

## Status与trace v3

- `accepted`：framework实质不变，全部GA完成final mapping和baseline reconciliation。
- `adjusted`：framework按共享标准发生source-backed最小调整，并完成全部terminal artifact。
- `needs-coverage-recheck`：冻结evidence缺失、broad或不足以安全判断。
- `blocked`：source evidence存在需要用户决定的产品冲突，或repository baseline不可访问。

terminal trace使用`source-aligned-phase-5-trace-v3`，记录final plan、framework refit JSON、review mirror、mapping、baseline和packet index各自的path/SHA。

非终态trace只记录refit JSON、review mirror及与refit JSON一致的非空`issues[]`。此时禁止final plan、mapping、baseline、packet index、根plan、final Change packet、Capability view和anchor index。

`accepted` / `adjusted`只有在Phase validator、independent reviewer、all-phase validator和final integration reviewer全部通过后才能handoff。
