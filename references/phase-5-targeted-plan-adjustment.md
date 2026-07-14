# Phase 5：逐 GA 最终框架映射与 plan refit

Phase 5 在 Phase 3 `coverage-complete` 且 Phase 4 `grounded` 后运行。它消费完整 evidence occurrence registry和 source-window semantics，为每个 GA 独立建立 final mapping，再据此调整最终 Change/Capability framework。

Phase 5 不执行 semantic dedup。final packet是完整 evidence mapping，不是去重后的 requirement inventory。

writer 必须完整读取 `references/cross-phase-contract.md`、本文件和 `references/trace-sidecar-contract.md`。

## 输入

- Phase 1 `initial-change-plan.md`
- Phase 2 source atom JSON
- Phase 3 `obligation-atom-index.json` 与 `coverage-review.json`
- Phase 4 `source-window-index.json`、dossier、semantic profile和 grounding issues
- 只读 `openspec/specs/<capability>/spec.md` repository baseline

Phase 5 通过 evidence resolver取得每个 GA 的 source fact/range/type/normativity；不得假设 global index重复保存 extraction字段。

## 输出

所有 terminal status都写入：

- `phase-works/phase-5/source-window-refit-trace.md`
- `phase-works/phase-5/phase-5-agent-report.md`
- `trace/phase-5.trace.json`

`accepted` / `adjusted` 还必须写入：

- `phase-works/phase-5/input-change-plan.md`
- `phase-works/phase-5/change-plan.md`
- 根 `change-plan.md`
- `phase-works/phase-5/atom-plan-mapping.json`
- `phase-works/phase-5/atom-plan-mapping.md`
- `phase-works/phase-5/final-packet-index.json`
- `phase-works/phase-5/capability-progression-review.md`
- `phase-works/phase-5/capability-baseline-reconciliation.json|md`
- `phase-works/phase-5/change-complexity-review.md`
- `phase-works/phase-5/plan-refit-decision-log.md`
- `phase-works/phase-5/alignment-final-report.md`
- `change-capability-anchors/<change>/<change>.md`
- `change-capability-anchors/<change>/capability-anchors/<capability>.md`
- `phase-works/phase-5/change-capability-human-plan.md`
- `change-capability-anchors/index.md`

accepted/adjusted 时，Phase 5 input snapshot必须与 Phase 1 snapshot逐字节一致，两个 final `change-plan.md` 必须逐字节一致。

## 每个 GA 的独立映射

`atom-plan-mapping.json` 必须对 global index中的每个 GA恰好一行，并保留相同 `evidence-ref`。每行独立决定：

- final owner Change与 owner type；
- final artifact projection；
- final relation；
- Capability impact/target/related Capability；
- plan decision与中文 reason。

多个语义相同的 GA可以映射到完全相同的 Change、projection、relation和 Capability，不产生 warning、ownership conflict或 recheck。不得添加 equivalence key、canonical GA、duplicate status、earliest duplicate owner、delivery-unit group或其他语义归组字段。

technical duplicate GA ID、缺失 mapping、dangling evidence ref或一个 GA多行仍是错误。

## Final mapping 规则

- `direct` mapping 必须有一个 final Change owner以及 `spec-requirement`、`spec-guard`、`design-obligation` 或 `verification-obligation` projection。
- non-direct evidence仍必须 owner-scoped 地保留在 final packet，可使用 preserve/dependency/context/reference relation，不得静默丢失。
- `spec-requirement` / `spec-guard` 必须给出具体 target Capability和 `new|modified` impact。
- direct design/verification以及 non-direct evidence使用 `none` / `none`，除非 source语义明确要求 spec delta。
- `related-capabilities[]` 只保存 source-explicit、non-owning relation；不推进 Capability。
- final packet保留每个 GA evidence row，不在本技能内合并 requirement。

## Framework refit

先从 Phase 4 source-window profile推导 semantic planning graph，再调整 framework：

1. 按 intent、trigger、normative behavior、observable outcome/invariant、exception、acceptance和 dependency判断 Change cohesion。
2. 按 Purpose/Owns/Excludes和 implementation-substitution判断 Capability boundary。
3. 依据 repository baseline决定 Capability-level `New` / `Modified`。
4. 只有 source-backed outcome可独立验收/归档且 dependency允许时拆分 Change；只有多个 slice实际构成同一不可分 outcome时合并。
5. 生成 final mapping、packet、Capability view、roadmap和 progression matrix并交叉校验。

GA count只作为 trace volume展示。不得用 direct atom `>80`、exception atom `>12`、总数 `>120` 或任何固定 evidence count阈值决定 split、merge、block或 complexity warning。重复 evidence增加 mapping row数量，但不能单独改变 roadmap、Capability Map、progression或 Change顺序。

complexity review检查的是语义复杂度：

- 是否混合多个独立 intent/outcome；
- acceptance是否可以独立成立；
- dependency、transaction、invariant、protocol、安全或兼容性是否要求整体交付；
- 是否具备独立 archive/deploy/risk/rollback/review boundary；
- Capability boundary是否稳定。

## Capability baseline 与 progression

- existing spec target的所有 planned delta为 Capability-level `Modified`。
- absent target的首次 source-backed roadmap advancement为 `New`，之后为 `Modified`。
- requirement-level `ADDED|MODIFIED|REMOVED|RENAMED` 不能反推 Capability existence。
- progression matrix、Capability Map、roadmap、anchor index和 packet必须一致。
- Capability advancement只由适用的 direct spec mapping产生；design/verification、contextual和 related-only evidence不推进 Capability。
- progression不得从 GA数量或重复 occurrence数量推断。

## Final Change packet

每个 final Change packet至少包含：

- Change identity、intent、outcome、acceptance和 independent archive条件；
- dependency/upstream realized baseline/downstream constraints/non-goals；
- direct evidence mapping表；
- owner-scoped non-direct evidence表；
- Capability delta与 baseline relation；
- design/verification obligations和 evidence burden；
- 所有相关 GA与 evidence ref。

packet 必须显式写明：

> 本 packet 是完整、未做语义去重的 evidence mapping，不是 requirement inventory。下游规格生成可以综合多个 GA，但必须保留多对一 GA trace。

语义相同的多个 GA仍各占一行，不合并、不选 canonical。

## Human plan 与 handoff

`change-capability-human-plan.md` 必须以 reviewer可读方式呈现 final Capability Map、Change roadmap、progression、每个 Change的 intent/outcome/acceptance/dependency和 ledger link，并声明：

- evidence occurrence数量仅为 trace volume；
- final framework没有按 evidence数量切分；
- packet未做 semantic dedup；
- semantic dedup由后续 specification generation负责，并保留多对一 GA trace。

## Recheck 与 blocker

- source-window暴露 uncovered missing obligation：返回 `needs-coverage-recheck`，先回 Phase 3补提取。
- evidence显示某 Phase 2 atom broad：返回 `needs-coverage-recheck`，targeted回 Phase 2重提取该 source/atom，再重跑 Phase 3/4/5。
- product boundary需要用户决定、source conflict无法解决或 repository baseline不可访问：返回 `blocked`。
- 不得因 semantic duplicate或 GA数量返回 recheck/blocker。

## Status

- `accepted`：Phase 1 framework无需语义调整，但已完成每个 GA mapping、baseline reconciliation和 final packet。
- `adjusted`：根据 source-window semantics调整了 Change/Capability boundary、sequence、ownership或 projection，并完成全部 terminal artifact。
- `needs-coverage-recheck`：extraction/coverage不闭合。
- `blocked`：需要用户决定或无法安全完成。

`accepted` / `adjusted` 只有在 validator、independent Phase 5 reviewer、all-phase validator和 final integration reviewer全部通过后才允许 handoff 给后续 OpenSpec流程。
