# 跨 Phase 语义契约

本文件定义 Phase 1–5 及其 reviewer/repair 共同遵守的语义不变量。它不定义 Phase 内部任务、artifact schema 或 reviewer 顺序。

## 强制加载

- main agent 在启动或恢复工作流前完整读取本文件。
- 每个 Phase writer、Phase 2 index/report writer、reviewer、repair-writer 和 final integration reviewer 在开始任务前直接完整读取本文件。
- main agent 的 prompt 摘要、转述、继承上下文或上游 report 不能替代直接读取。
- Phase writer 必须读取当前 Phase reference；reviewer 和 repair-writer 还必须读取当前 Phase reference 与 `references/reviewer-repair-loop.md`；final integration reviewer 必须读取 Phase 3、Phase 4、Phase 5 reference 与 reviewer/repair contract。

## 权威边界

- 本文件只拥有跨 Phase 语义；每个 Phase 的任务、允许读写范围、output 和 terminal status 由对应 Phase reference 唯一定义。
- JSON key、schema、field、enum、manifest、renderer 和 validator contract 由 `references/trace-sidecar-contract.md` 唯一定义。
- reviewer、repair 和 final integration 顺序及独立性由 `references/reviewer-repair-loop.md` 唯一定义。
- 发现上述 contract 相互冲突时停止当前 Phase 并报告 blocker，不得自行选择、合并或弱化规则。

## Evidence 与 identity

- 原始 source document 是 production obligation 的语义来源。Phase 2 atom 行范围提供直接 trace evidence；Phase 3 根据 atom 范围的 complement 完成 remainder disposition 与全文 coverage closure。行范围本身不是 coverage 目标。
- canonical JSON sidecar 是 machine-readable authority；renderer-backed Markdown 是 reviewer/proposal surface。修复 drift 时更新 JSON 或重新渲染，不得只手工修改 mirror。
- Phase 2 canonical source atom JSON 通过 reviewer loop 后冻结。后续 missing、split、duplicate、grounding 或 ownership finding 进入 Phase 3–5，不回写 frozen evidence。
- Phase 3 分配的 global atom ID 必须使用 `GA-####`。Phase 4、Phase 5 和后续 OpenSpec 工作必须原样保留，不得改写为其他 global 前缀或 source-local ID。

## Ownership、projection 与 Capability

- executable direct atom 恰好有一个 Change owner。Capability metadata 不是 co-ownership surface。
- artifact projection 与 Change ownership 正交。direct atom 使用 `spec-requirement`、`spec-guard`、`design-obligation` 或 `verification-obligation`；`contextual-only` 只用于 non-direct context。
- Capability advancement 只来自具有具体 target Capability 的 direct `spec-requirement` / `spec-guard` atom。普通 direct design/verification atom 和所有 non-direct atom 不得产生 business Capability progression。
- `related-capabilities[]` 只保留 source-explicit、已声明、去重且不同于 target 的 non-owning evidence；不得替代 target，也不得产生 ownership、progression、Capability view 或 complexity count。
- Phase 2 只记录 source-local status/projection 和对现有 Change/Capability 的候选映射；Phase 3 负责跨文档规范化与 duplicate/coverage closure；Phase 5 负责 new/refit Change、new Capability 和其他 final determination。不得把较早 Phase 的 candidate owner、projection 或 target 当作 final authority。
- Phase 5 返回 `accepted` 或 `adjusted` 前必须解决所有 direct atom 的 final owner、final projection 和 unresolved Capability impact/target。

## Capability、Change 与 Phase 1 边界

- Capability 是跨 Change 持续存在的 logical spec/domain boundary；Change 是围绕一个 source-backed intent、可独立决策与归档的 delivery/evolution slice。两者是多对多关系，任何 Phase 都不得从一方机械生成另一方。
- Phase 1 必须先建立 coarse candidate Capability topology，再独立按 outcome、cohesion、indivisibility、acceptance 和 hard dependency 形成 Change roadmap；Capability 列数、名称或矩阵外观不得决定 Change boundary。
- Phase 1 不执行 obligation extraction、atom ID、line-level coverage、unique obligation ownership、requirement operation 或 completeness claim。coarse semantic landscape、Purpose、Owns/Excludes、intent、outcome 和 source hint 不得被解释为 obligation ledger。
- Phase 1 的 Change–Capability edge 只使用 `first-advancement` / `later-advancement` 表达 roadmap progression hypothesis。OpenSpec Capability relation `New` / `Modified` 取决于 repository spec baseline，不得从 roadmap 首次出现位置推断。
- Phase 2 不记录 capability impact；Phase 3 的 capability impact 只是 normalized planning metadata。在没有 repository baseline evidence 时，direct spec atom 应保持 `unresolved`，由 Phase 5 reconciliation。较早 Phase 的 `new` / `modified` 不能替代 Phase 5 baseline check。
- Phase 5 必须将 source-backed final target 与只读 `openspec/specs/<capability>/spec.md` baseline 对齐：existing target 的所有 planned delta 为 `modified`；absent target 的首次 planned delta 为 `new`，其后按明确 roadmap/archive 顺序为 `modified`。现有 spec 只提供 identity/existence/comparison evidence，不成为 production obligation authority。
- Capability-level `New` / `Modified` 与 requirement-level `ADDED` / `MODIFIED` / `REMOVED` / `RENAMED` 是两层语义。向 existing Capability 新增 requirement 仍是 Capability-level `Modified` + requirement-level `ADDED`；任何 Phase 都不得把 requirement operation 反推为 Capability existence。

## Artifact Language Gate

- agent 编写的解释、判断、理由、风险、proof/evidence description、report 和 handoff 必须使用简体中文。
- 固定 heading、table header、field label、enum/status、ID、path、command、code/API/DB/package symbol、filename、Capability ID、Change slug 和精确 source quote 可以保留英文。
- 技术英文可以作为 identifier 或 noun phrase 保留，但周围解释性语句必须使用简体中文。`Source Phrase` 可以保留 source 原文。
- 每次写入或修改 artifact 后执行 language self-check；忽略上述固定结构后，剩余英文主导的自然语言句必须在当前 Phase 结束前改写。

## 交接检查

- writer report 必须确认已直接读取并遵守本文件，且没有把 candidate metadata 提升为越权的 final decision。
- reviewer 必须将本文件作为独立 review 输入，检查跨 Phase identity、authority、ownership、projection、Capability 和语言语义。
- repair-writer 必须保留上游 frozen evidence、`GA-####`、source path、line range 和允许范围之外的 canonical decision；需要越权修改时返回 recheck 或 blocker。
