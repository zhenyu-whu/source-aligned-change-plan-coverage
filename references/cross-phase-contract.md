# 跨 Phase 语义契约

本文件定义 Phase 1–5 以及 reviewer/repair 共同遵守的语义不变量。Phase 内任务和 artifact 由对应 Phase reference 定义；JSON schema、renderer 和 validator 由 `references/trace-sidecar-contract.md` 定义。

## 强制加载与权威边界

- main agent、所有 writer、reviewer、repair-writer 和 final integration reviewer 必须直接完整读取本文件。
- source document 是 production obligation 的语义来源；canonical JSON 是 machine-readable authority，renderer-backed Markdown 只是 review mirror。
- Phase 2 source atom JSON 通过 reviewer 后冻结。Phase 3 只能补充 uncovered range 中遗漏的 evidence occurrence；broad atom 必须返回 targeted Phase 2 re-extraction，不得在 Phase 3 拆分或改写。
- contract 之间冲突时停止并报告 blocker，不得自行弱化规则。

## Evidence occurrence 与 GA identity

- 每个 Phase 2 source atom 和每个 Phase 3 gap atom都是一个独立的 extracted evidence occurrence，并恰好获得一个 `GA-####`。
- GA 不是语义去重后的唯一 requirement。多个语义相同的 occurrence 必须保留为多个 GA；本技能不识别、标记、合并、归组或消除 semantic duplicate。
- Phase 3 global index 只保存 `global-atom-id` 和 `evidence-ref`，不得复制 Phase 2 `source-fact`、行范围、atom type、normativity 或 extraction metadata。
- `evidence-ref` 指向 frozen Phase 2 atom或 Phase 3 gap atom。Phase 4/5 通过 evidence resolver 加载原始证据，不得把 global index 扩展为第二份 extraction ledger。
- technical duplicate ID、重复 source-atom key、dangling reference 和一对多/多对一 identity 错误仍由 validator 拒绝。

## Coverage 与重新提取

- Phase 3 coverage closure 是 Phase 2 atom ranges 的机械补集加上对每个 uncovered range 的处置，不是语义唯一性证明。
- `coverage-complete` 只表示：每份 `read-full` source 有有效 Phase 2 artifact；所有 uncovered range 已补提取或安全分类；不存在 broad extraction recheck 或 blocker。
- semantic duplicate 不影响 coverage decision。
- Phase 3、Phase 4 或 Phase 5 发现 broad/missing extraction 时，只能返回 targeted coverage/extraction recheck。Phase 3 gap atom只允许来自 uncovered range。

## Ownership、projection 与 Capability

- Phase 2 candidate owner/projection/target 仅是 extraction-time hint；Phase 3 不判断 Change owner、artifact projection、relation 或 Capability。
- Phase 5 必须为每个 GA 独立给出 final owner Change、artifact projection、relation、Capability impact/target 和 related Capability。语义相同的 GA 可以具有完全相同的 mapping。
- executable direct evidence 的 final mapping 恰好一个 Change owner。Capability metadata 不是 co-ownership surface。
- Capability advancement 只来自 final direct `spec-requirement` / `spec-guard` mapping；普通 design/verification 和 non-direct mapping 不推进 Capability。
- Capability/Change boundary 只能依据 intent、outcome、acceptance、dependency、Capability boundary 和独立 archive 条件；不得从 GA 数量、重复 evidence 数量或表格形状推断。
- Phase 5 返回 `accepted` 或 `adjusted` 前，必须解决每个 GA 的 final mapping 和 repository baseline reconciliation。

## Capability、Change 与 Phase 1 边界

- Capability 是可跨 Change 演进的稳定 behavior/spec boundary；Change 是一个 source-backed、可独立决策、验收和归档的 outcome slice。两者多对多，不能互相机械生成。
- Phase 1 先建立 candidate Capability topology，再按 outcome/cohesion/acceptance/dependency 建立 Change roadmap；不得执行 atom extraction、coverage 或 final `New`/`Modified` 判断。
- Phase 5 将 final target 与只读 `openspec/specs/<capability>/spec.md` baseline 对齐。existing target 为 Capability-level `Modified`；absent target 的首次 roadmap advancement 为 `New`，后续为 `Modified`。

## 下游 semantic dedup handoff

- Phase 5 final packet 是完整 evidence mapping，不是经过语义去重的 requirement inventory。
- 后续规格生成流程可以把多个 GA 综合成一个 requirement，但必须保留多对一 GA trace。该判断与实现不属于本技能。

## Artifact Language Gate

- agent 编写的解释、判断、理由、报告和 handoff 使用简体中文。
- 固定 heading、field、enum、ID、path、代码符号和精确 source quote 可以保留英文。
- `source-fact` 必须保持 source 原文，不翻译、不转述。
