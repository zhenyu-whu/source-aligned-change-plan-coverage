# Phase 5：共享标准复审与最小 plan refit

Phase 5 在 Phase 3 `coverage-complete` 且 Phase 4 `assembled` 后运行。它使用 Phase 4 原文集合和 `references/change-capability-framework-principles.md` 中与 Phase 1 完全相同的标准，复审 initial framework并只做 source-backed最小调整。

writer 必须完整读取 `references/cross-phase-contract.md`、`references/change-capability-framework-principles.md`、本文件和 `references/trace-sidecar-contract.md`。

Phase 5不执行 semantic dedup，不重新读取原始 source，不创建 replacement source window。frozen `source-fact` 过窄时返回 targeted coverage/extraction recheck。

## 输入

- Phase 1 `initial-change-plan.md`
- Phase 2/3 canonical evidence和global atom index
- Phase 4 `evidence-collection-index.json`及全部 rendered collection
- 只读 `openspec/specs/<capability>/spec.md` repository baseline

## 输出

所有状态都写入：

- `phase-works/phase-5/plan-refit-review.md`
- `phase-works/phase-5/phase-5-agent-report.md`
- `trace/phase-5.trace.json`

`accepted` / `adjusted` 还必须写入：

- `phase-works/phase-5/change-plan.md`
- 根 `change-plan.md`，且与前者逐字节一致
- `phase-works/phase-5/atom-plan-mapping.json|md`
- `phase-works/phase-5/capability-baseline-reconciliation.json|md`
- `phase-works/phase-5/final-packet-index.json`
- `change-capability-anchors/<change>/<change>.md`
- `change-capability-anchors/<change>/capability-anchors/<capability>.md`
- `change-capability-anchors/index.md`

禁止创建或保留：`phase5-refit.config.json`、`input-change-plan.md`、`source-window-refit-trace.md`、`change-plan-adjustments.md`、`capability-progression-review.md`、`change-complexity-review.md`、`plan-refit-decision-log.md`、`alignment-final-report.md`、`change-capability-human-plan.md`。

## 固定复审顺序

1. 对每个 initial Capability逐项应用共享 Capability gate。
2. 对每个 initial Change逐项应用共享 Change gate。
3. 审阅 `unassigned-and-gap.md` 中每个 GA。
4. 重建 Change-Capability overlay。
5. 按 hard dependency和outcome maturity复审 roadmap顺序。
6. 冻结 final Change/Capability framework。
7. 只读核对 final target Capability repository baseline。
8. 为每个 GA写入 final mapping。
9. 运行 mechanical helper生成 baseline、packet、Capability view和根 plan。

Phase 1 framework默认保留。只有 evidence collection证明共享 gate失败时才允许 split、merge、add、remove、rename、reorder或scope adjustment；不得从零重新规划。

## 最小 refit

Capability：

- 全部 gate通过：`keep`。
- 混合多个不相关稳定 behavior boundary：`split`。
- 多个 Capability重叠且不能独立成立：`merge`。
- unassigned/gap暴露新的稳定 behavior boundary：新增。
- 只是 implementation component、临时阶段或 Change alias：`remove`、`merge`或`rename`。

Change：

- 全部 gate通过：`keep`。
- 包含多个可独立 acceptance/archive的 outcome：`split`。
- 多个 Change共同构成不可分 outcome：`merge`。
- evidence属于另一 Change：`scope-adjusted`。
- unassigned/gap形成独立 outcome：新增。
- 只有辅助实现内容且无独立 outcome：`remove`或并入consumer。
- roadmap违反hard dependency：`reorder`。
- boundary正确但名称不准确：`rename`。

不得引入 planning graph、atom clustering、complexity budget、固定 evidence count threshold或基于矩阵形状的调整。

## plan-refit-review.md

固定包含以下 heading和表格。

### `## Capability Review`

| Input Capability | Evidence Collection | Decision | Final Capability(s) | Failed or Passed Gates | Reason |
| --- | --- | --- | --- | --- | --- |

每个 Phase 1 Capability恰好一行。

### `## Change Review`

| Input Change | Evidence Collection | Decision | Final Change(s) | Failed or Passed Gates | Reason |
| --- | --- | --- | --- | --- | --- |

每个 Phase 1 Change恰好一行。

### `## Unassigned and Gap Review`

| GA | Provenance | Source Fact Reference | Disposition | Final Change | Final Capability | Reason |
| --- | --- | --- | --- | --- | --- | --- |

每个 `unassigned-and-gap` GA恰好一行。

### `## Final Decision`

- `Status: accepted|adjusted|needs-coverage-recheck|blocked`
- framework变化摘要或 `无`
- recheck/blocker及最小下一步或 `无`

`accepted` 表示 final Capability/Change集合、boundary、overlay和roadmap顺序与 Phase 1实质一致；candidate atom hint的最终消解不构成 framework调整。发生 split、merge、add、remove、rename、reorder或实质boundary/overlay变化时必须使用 `adjusted`。

## Final change plan

`change-plan.md` 继续使用 Phase 1固定heading和Change字段，包括 `Source Semantic Landscape`，但把 candidate/hypothesis改为 final结论。为消除机械解析歧义，final `Capability Map` 的表头固定为：

| Capability | Purpose | Owns | Excludes | Boundary Rationale |
| --- | --- | --- | --- | --- |

final `Change-Capability Overlay` 的表头固定为：

| Change | Capability | Capability Impact | Direct Behavior Delta |
| --- | --- | --- | --- |

`Capability Impact` 只允许 `new|modified`。

每个 final Change必须保留共享标准要求的 intent、outcome、范围、behavior completeness profile、acceptance evidence、hard dependency、排序理由、独立完成与归档、拆分/合并判断。mechanical helper不得补写缺失内容。

## Atom plan mapping v4

`atom-plan-mapping.json` 使用 `source-aligned-atom-plan-mapping-v4`。顶层包含 `trace-schema`、`trace-contract-version`、`artifact-path`、`rows[]`。

每个 GA恰好一行，且只能包含：

- `global-atom-id`
- `evidence-ref`
- `final-owner-change`
- `final-relation`
- `final-artifact-projection`
- `final-capability-impact`
- `final-target-capability`
- `related-capabilities[]`
- 简体中文 `reason`

规则：

- `evidence-ref` 与global index完全一致；source path/range/fact通过resolver取得，不在mapping复制。
- direct和non-direct都必须归属一个final Change。
- relation只允许 `direct`、`context`、`dependency`、`preserve`、`reference`、`non-goal`。
- direct projection只允许 `spec-requirement`、`spec-guard`、`design-obligation`、`verification-obligation`。
- direct spec/guard必须指定具体Capability和`new|modified`。
- direct design/verification以及所有non-direct使用`none` / `none`；non-direct projection使用`contextual-only`。
- `related-capabilities[]` 只表达source-explicit、non-owning relation，不推进Capability。

## Mechanical helper

`phase5_plan_refit.py` 只执行确定性工作：

- 读取 final `change-plan.md`、`plan-refit-review.md`、mapping v4、Phase 2/3 resolver和repository specs；
- 拒绝缺少必需Change字段的final plan；
- 生成mapping Markdown、baseline、final packet、Capability view、packet index和根plan；
- packet中的原文直接来自Phase 2/3 frozen `source-fact`；
- 不接受config，不推断semantic decision，不补写acceptance/dependency/non-goal/archive文案。

## Status

- `accepted`：framework实质不变，全部GA完成final mapping和baseline reconciliation。
- `adjusted`：framework按共享标准发生source-backed最小调整，并完成全部terminal artifact。
- `needs-coverage-recheck`：frozen evidence缺失、broad或不足以安全判断。
- `blocked`：source evidence存在需要用户决定的产品冲突，或repository baseline不可访问。

`accepted` / `adjusted` 只有在Phase validator、independent reviewer、all-phase validator和final integration reviewer全部通过后才能handoff。

terminal trace使用`source-aligned-phase-5-trace-v2`，只保存final plan、review、mapping JSON、baseline JSON和packet index JSON的path及SHA。非终态trace只保存review path/SHA和非空`issues[]`。
