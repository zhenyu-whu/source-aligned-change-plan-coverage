# Review Gates 规范

本文件只定义Phase 1 bounded review/repair、Phase 2/3 evidence-freeze bounded review/repair和workflow terminal integration gate。Phase 4–5不存在独立Phase reviewer或repair loop。

Phase 1 reviewer/repair-writer必须直接完整读取`references/cross-phase-contract.md`、`references/change-capability-framework-principles.md`和`references/phase-1-initial-change-plan.md`。Phase 2/3 reviewer/repair-writer必须直接完整读取cross-phase contract及Phase 2/3 reference。Final integration reviewer必须读取cross-phase contract、共享framework原则及Phase 3–5 reference。Prompt摘要不能替代原文件。

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

## Phase 2/3 evidence-freeze bounded review

默认顺序：

```text
Phase 2 provisional extraction -> Phase 2 preflight
-> Phase 2 aggregate/renderer/validator
-> Phase 3 provisional coverage/GA -> Phase 2 validator + Phase 3 preflight
-> fresh independent reviewer
-> 若有finding：fresh independent repair-writer #1
-> 重新计算Phase 3、重跑两个validator、fresh reviewer #2
-> 若仍有finding：fresh independent repair-writer #2
-> 重新计算Phase 3、重跑两个validator、fresh reviewer #3
-> evidence freeze，或blocked
```

Phase 2 preflight阶段若已有需要semantic repair的finding，可以在进入Phase 3前启动`stage: phase-2-preflight` review/repair；main agent必须先预留后续fresh Phase 2 aggregate writer与Phase 3 writer identity并写入gate，这两个identity之后不得替换或复用。其review/repair与后续closure共享最多三次review、两次repair的总预算。无repair正常路径可以只运行一次`stage: phase-3-closure` terminal review。

- Phase 2/3 authority在terminal pass前都是provisional。Repair可split/add occurrence；每次repair后必须机械重算Phase 3 complement、coverage、GA和ambiguity，再重跑Phase 2普通validator与Phase 3 preflight。
- Reviewer全文读取所有source并检查coverage completeness、safe disposition、逐字quote/range、单tuple无损表达、mixed responsibility拆分及ambiguity记录；不得执行semantic dedup或提前裁决final mapping。
- Reviewer对authority只读，只追加`phase-3-reviewer-report.md`。Repair writer只消费上一轮finding，只修改finding明确涉及的provisional Phase 2/3 authority，并追加`phase-3-repair-report.md`。
- 全部Phase 2 canonical owner、Phase 2 aggregate writer、Phase 3 writer、各reviewer与各repair writer身份必须相互独立；validator或producer自检不能替代reviewer。
- 同一finding fingerprint在后续review再次出现、repair before/after evidence authority digest相同、第三次review仍不pass、source不可信或需要产品决定时立即`blocked`。
- Terminal pass的最后review必须为`stage: phase-3-closure`，Phase 2/3 validator均为`passed`且findings为空。最后写入`coverage-complete` commit marker；此前的Phase 2 pass不构成freeze。

`phase-3-reviewer-report.md`每次run追加reviewer identity、全部producer identity、round/stage、两个validator状态、authority digest、findings/warnings与decision。`phase-3-repair-report.md`每次repair追加repair writer identity、消费的fingerprints、修改的source/artifact、before/after authority digest、保留不变量与blocker。二者均为noncanonical，不进入manifest。

同一证据还必须机械写入`source-aligned-phase-3-trace-v4.review-gate`。Gate严格只含`status`、`phase-2-canonical-owner-ids[]`、`phase-2-aggregate-writer-id`、`phase-3-writer-id`、`reviews[]`、`repairs[]`：

- Review row严格为`{round,stage,reviewer-id,phase-2-validator-status,phase-3-validator-status,evidence-authority-sha256,finding-fingerprints[]}`；stage只允许`phase-2-preflight|phase-3-closure`，validator status只允许`passed|failed|not-run`，其中Phase 3只有在`phase-2-preflight`可为`not-run`。
- Repair row严格为`{round,repair-writer-id,finding-fingerprints[],before-evidence-authority-sha256,after-evidence-authority-sha256}`。
- Review和repair round分别从1连续递增；reviews最多三行、repairs最多两行。通常`len(reviews) = len(repairs) + 1`；terminal no-op repair立即blocked时允许两者等长且不得再启动reviewer。

## Phase 4–5 validator gate

- Phase 4–5仅执行assembler/helper与Phase validator；不创建Phase reviewer/repair report，不启动reviewer/repair-writer。
- Validator检查结构、trace、digest、schema、ID、mirror drift和跨artifact一致性；失败使当前Phase `blocked`，不得回写冻结evidence、自动重启producer、重复当前Phase或创建patch/checkpoint。

## Workflow terminal integration gate

Phase 5 terminal 状态后固定执行：

```text
main agent 运行 all-phase complete validator
-> fresh independent final integration reviewer
-> pass 后 handoff；否则 blocked
```

- final integration reviewer 是 workflow-level 只读 gate，不是 Phase 5 reviewer，只运行一次，不得修改 artifact、执行 repair、重新启动 refit或回写冻结evidence。
- Reviewer必须核对Phase 3 global atom index与potential mapping ambiguities、Phase 4 collections/index、framework refit、作为唯一ambiguity resolution的terminal atom mapping、baseline、final packets、Capability views、anchor index和根`change-plan.md`。
- Reviewer必须直接使用共享framework原则确认每个final Capability通过全部8项标准、每个final Change通过全部6项标准，并确认roadmap dependency、minimality和overlay成立；不得要求refit JSON复制第二套final gate数组。
- Phase 3 `mapping-ambiguities[]`是冻结的pre-refit observation，不是terminal completeness authority；不得要求把Phase 5 late-discovered ambiguity回填Phase 3。完整性以每个GA恰好一个有效terminal mapping row、且已记录ambiguity均由同GA row裁决为准。
- 每个 evidence occurrence 从 frozen source fact 到 GA、collection、final mapping 和 packet 必须保持一对一 identity；语义相同 occurrence 不得丢失或合并。
- complete validator 或 final integration reviewer 未通过时不得 handoff；workflow 返回 `blocked` 并报告最小用户决定，不进入自动 repair loop。
