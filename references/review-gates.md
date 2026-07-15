# Review Gates 规范

本文件只定义 Phase 1 bounded review/repair 和 workflow terminal integration gate。Phase 2–5 不存在独立 Phase reviewer 或 repair loop。

Phase 1 reviewer/repair-writer 必须直接完整读取 `references/cross-phase-contract.md`、`references/change-capability-framework-principles.md` 和 `references/phase-1-initial-change-plan.md`。final integration reviewer 必须读取 cross-phase contract、共享 framework 原则及 Phase 3–5 reference。prompt 摘要不能替代原文件。

## Phase 1 bounded review

固定顺序：

```text
Phase 1 writer
-> main agent 运行 Phase 1 validator
-> fresh independent initial reviewer
-> 若有 blocking finding：fresh independent repair-writer #1
-> main agent 重跑 validator
-> fresh independent reviewer #2
-> 若仍有 blocking finding：fresh independent repair-writer #2
-> main agent 重跑 validator
-> fresh independent final reviewer #3
-> pass，或 blocked
```

- initial review 后最多两轮 repair；不得启动第三个 repair-writer或第四次 reviewer run。
- 任一 reviewer pass 时立即结束 bounded review，不启动剩余 repair。
- 若在可校验initial plan和首轮review authority建立前即无法完整读取source，只记录noncanonical orchestration stop，不进入本gate或伪造canonical `blocked` trace。已有这些authority后，final reviewer #3仍有blocking finding、validator未通过、source authority失效或共享gate冲突时，Phase 1返回`blocked`。
- reviewer 对被审 artifact 只读，只能写入或追加 `phase-1-reviewer-report.md`；repair-writer 只能修改 Phase 1 允许的 artifact，并写入或追加 `phase-1-repair-report.md`。
- initial writer、各 reviewer 和各 repair-writer 身份必须相互独立。writer 自检、agent report 或 validator 不能替代 reviewer。
- 每次 repair 后必须重跑 validator，并启动 fresh independent reviewer；不得复用同一 reviewer。
- reviewer/repair-writer 都是 leaf worker，不得启动任何 nested agent 或 agentic child process。

## Phase 1 review evidence

`phase-1-reviewer-report.md` 每次 run 必须追加：

- reviewer identity、writer identity、run number `1..3`；
- validator input status、只读检查范围；
- findings、accepted non-blocking warnings；
- 是否需要 repair，以及 `pass|blocked` decision。

`phase-1-repair-report.md` 仅在发生修改时创建或追加，每轮必须记录：

- repair-writer identity 和 repair number `1..2`；
- 被消费的 reviewer/validator finding；
- 修改文件、保留的不变量、未修复项和 blocker。

Phase 1 只有 validator 通过且 reviewer report 中最后一个 run 为 `pass` 时，才可记录 `initial-plan-written` 并进入 Phase 2。review/repair report 是非canonical流程证据，不进入 manifest，不能覆盖 Phase 1 内容权威。

同一证据还必须机械写入`source-aligned-phase-1-trace-v3.review-gate`：review row严格为`{round,reviewer-id,validator-status,plan-sha256,finding-fingerprints[]}`，repair row严格为`{round,repair-writer-id,finding-fingerprints[],before-plan-sha256,after-plan-sha256}`；reviews最多三行、repairs最多两行且round连续。通常`len(reviews) = len(repairs) + 1`；仅当terminal repair的before/after digest相同并立即`blocked`时，允许`len(reviews) = len(repairs)`，不得为no-op repair启动下一reviewer。finding fingerprint的identity必须包含稳定rule/subject与相关input digest，排除措辞和修复方案；因此同一fingerprint在后续任一轮review再次出现即表示相关输入未有效改变，即使整份plan digest变化也必须立即`blocked`。

## Phase 1 reviewer 范围

- 直接使用共享 framework 原则检查 Capability-first 顺序、Capability gate、Change gate、foundation 例外、排序和 Change-Capability overlay；不得创建第二套标准。
- 执行 Hide Capability Names、Hide Roadmap 和 post-mapping diagnostic；不得为改善矩阵形状扭曲真实 boundary。
- 检查 Phase 1 没有提前创建 obligation、atom、coverage status、line-range anchor、unique owner、OpenSpec `New` / `Modified` 或 Phase 2 work queue。
- 检查 source manifest 与 coarse semantic landscape 足以支持 hypothesis，但不得要求 Phase 1 达到 Phase 2/3 evidence completeness 或 Phase 5 final mapping 精度。

## Phase 2–5 validator gate

- Phase 2–5 仅执行 renderer/helper 与 Phase validator；不创建 `phase-<n>-reviewer-report.md` 或 `phase-<n>-repair-report.md`，不启动 reviewer/repair-writer。
- validator 只检查结构、trace、digest、schema、ID、coverage、mirror drift 和跨 artifact 一致性，不作独立语义 reviewer。
- validator 只能 pass 或使当前 Phase blocked；失败后不得自动重启 producer、就地修正后重验或重复当前 Phase。唯一例外是 Phase 5 已合法生成 request/checkpoint 后进入的一次 targeted patch 状态机。
- 唯一 evidence 回补只可在Phase 2–4均为initial success snapshot、canonical Phase 5 trace尚未发布的首次Phase 5执行中，通过有效checkpoint和`source-aligned-evidence-patch-request-v1`启动；不得由Phase 2–4自行发起，也不得把accepted、adjusted、blocked、closed或incremental状态重放为requested。

## Workflow terminal integration gate

Phase 5 terminal 状态后固定执行：

```text
main agent 运行 all-phase complete validator
-> fresh independent final integration reviewer
-> pass 后 handoff；否则 blocked
```

- final integration reviewer 是 workflow-level 只读 gate，不是 Phase 5 reviewer，只运行一次，不得修改 artifact、执行 repair、生成第二次 evidence patch 或重新启动 refit。
- reviewer 必须核对 Phase 3 global atom index 与 mapping ambiguities、Phase 4 collections/index、framework refit、作为唯一ambiguity resolution的terminal atom mapping、baseline、final packets、Capability views、anchor index和根 `change-plan.md`。
- Phase 3 `mapping-ambiguities[]`是冻结的pre-refit observation，不是terminal completeness authority；不得要求把Phase 5 late-discovered ambiguity回填Phase 3。完整性以每个GA恰好一个有效terminal mapping row、且已记录ambiguity均由同GA row裁决为准。
- 每个 evidence occurrence 从 frozen source fact 到 GA、collection、final mapping 和 packet 必须保持一对一 identity；语义相同 occurrence 不得丢失或合并。
- 若执行过 targeted patch，必须检查未受影响 GA/ambiguity identity 稳定、patch generation 仅一次、checkpoint resume 只重算 invalidated unit 及最小影响闭包。
- complete validator 或 final integration reviewer 未通过时不得 handoff；workflow 返回 `blocked` 并报告最小用户决定，不进入自动 repair loop。
