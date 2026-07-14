# Phase 2：source-first obligation atom 提取

Phase 2 逐份完整阅读 source document，提取所有具有产品或系统语义的 source atom candidate。analysis unit 是 source document，不是 planned Change；Phase 1 framework 只提供现有 Change/Capability 的候选映射目标。

本 Phase 只负责 raw extraction 和 existing-framework mapping。不执行跨文档去重、global coverage closure、new/refit Change 判断、new Capability 判断或 repository baseline reconciliation；无法映射到现有 framework 的 atom 统一标记为 `unassigned`。

## 目录

- [输入与产出](#输入与产出)
- [角色与执行顺序](#角色与执行顺序)
- [Work queue](#work-queue)
- [Atom 提取方法](#atom-提取方法)
- [Canonical source atom file](#canonical-source-atom-file)
- [索引与报告](#索引与报告)
- [完成门禁](#完成门禁)

## 输入与产出

输入：

- `openspec/orchestrate/phase-works/phase-1/initial-change-plan.md`
- `openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md`
- 用户指定的 source root 或精确 source path，用于读取正文和生成行引用。

只写入以下 Phase 2 artifact：

- `phase-works/phase-2/source-obligation-atoms/work-queue.md`
- 每份 `Read Status: read-full` source 对应的 `<source>.atoms.json`
- 从每个 JSON 渲染的 `<source>.atoms.md`
- `phase-works/phase-2/source-obligation-atoms/index.md`
- `phase-works/phase-2/phase-2-agent-report.md`
- `trace/phase-2.trace.json`

路径均相对于 `openspec/orchestrate/`。source atom file 使用单层确定性名称：移除 source extension，将 path separator 替换为 `--`，再添加 `.atoms.json` 或 `.atoms.md`。

canonical JSON、renderer 和 validator 以 `references/trace-sidecar-contract.md` 为准；跨阶段语义以 `references/cross-phase-contract.md` 为准。每个 extraction writer 和 index/report writer 必须直接完整读取本文件、cross-phase contract 和 trace-sidecar contract。

validator 与 independent reviewer 通过后冻结 `.atoms.json`；`.atoms.md` 只能由 renderer 刷新。

## 角色与执行顺序

| 角色 | 允许读取 | Phase 2 content 写入 | 禁止事项 |
| --- | --- | --- | --- |
| main agent | Phase 1 plan、manifest 和 source metadata | `work-queue.md` | 提取或修复 atom、作 coverage 判断 |
| extraction writer | 分配的 source 正文、Phase 1 plan/manifest、work queue、必需 contract | 分配 source 的 canonical `.atoms.json` | 写其他 source、跨文档比较、聚合、判断 new Change/Capability、读取 Phase 3–5 output |
| renderer | canonical Phase 2 JSON | 匹配的 `.atoms.md` mirror | 解释或补充 atom |
| index/report writer | Phase 1 plan/manifest、work queue、全部 `.atoms.json` | `index.md`、`phase-2-agent-report.md`、`phase-2.trace.json` | 重读 source 创建 evidence、编辑 atom、repair、去重、闭合 coverage 或作 final decision |

reviewer 与 repair-writer 的权限由 `references/reviewer-repair-loop.md` 定义。

表中的写入限制只约束 Phase 2 content artifact。main agent 仍按 trace contract 负责共享 `trace/manifest.json` 的初始化、validator 前刷新和 reviewer 通过后刷新；这不构成 extraction content 写入。

执行顺序：

1. main agent 建立 work queue。
2. 每个 batch 启动一个 fresh extraction writer；每份 source 只分配一个 canonical owner。
3. extraction writer 对每份 source 依次完成：全文阅读 → atom extraction → existing-framework mapping → canonical JSON。
4. 在 repository root 运行 Phase 2 scoped renderer：

   ```bash
   python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
     --orchestrate-dir openspec/orchestrate \
     --artifact phase2-source-atoms \
     --write
   ```
5. 所有 extraction 完成后，启动 fresh index/report writer，只读聚合 JSON，并写入 index、report 和 status 为 `source-atoms-written` 的 Phase trace。该 status 只表示 writer output 已形成。
6. 聚合发现缺失或格式错误时只记录 blocker，不得修复 extraction。
7. main agent 运行 validator、reviewer 和必要的 repair loop；通过后刷新 manifest 并冻结 Phase 2。

## Work queue

`work-queue.md` 只做 scheduling，不得包含 atom、coverage judgment 或“该文档无 obligation”的结论。

- 每份 `read-full` source 必须恰好出现在一个 batch，并有一个 canonical owner。
- 按 source family、document role、doc type、line count、semantic density 和 context pressure 形成少量 coherent batch。
- 同一 source 不得拆给多个 writer；超大文档仍只有一个 owner。
- 默认 batch 不超过五个；超过时记录无法安全合并的原因。
- `small`、`medium`、`large` 只是调度标签，不是内容价值判断。

必须包含：

| Batch | Source Documents | Line Counts | Source Roles / Doc Types | Assignment Rationale | Extraction Mode | Canonical Owner |
| --- | --- | --- | --- | --- | --- | --- |

`Extraction Mode` 使用 `single-doc`、`small-doc-batch`、`medium-doc-batch` 或 `large-doc-dedicated`。table 后添加 `Batch Merge Review`，记录 initial/final batch count、合并情况和例外理由。

## Atom 提取方法

### 1. 提取所有有产品/系统语义的事实

以下内容必须成为 atom candidate：

- 用户或系统的 condition、state、action、transition、display、failure、recovery 或 observable result。
- 数据、权限、隐私、API、schema、runtime、provider、deployment、integration 或 persistence boundary。
- preserve rule、must-not、explicit non-goal 或 scope guard。
- acceptance、fixture、proof 或 verification requirement。
- 会改变当前实现、验证或兼容性判断的 contextual fact。
- 无法安全解释的 source conflict 或 meaningful unclear content。

纯格式、目录导航、重复的 heading/TOC 等机械性内容、discarded explanation、无 production effect 的 prototype detail 或已明确 superseded content 不创建 atom。Phase 3 根据 atom 范围的 complement 统一审阅并分类这些 remainder range；Phase 2 不判断两个有语义的事实是否 duplicate。

### 2. 控制 atom 粒度

一个 atom 应能被独立接受、拒绝、实现、保护或验证。

- 保留同一规则的 condition + trigger/action + expected effect，不机械拆分。
- 多个 behavior、不同 normativity、不同 projection、不同 failure/recovery path 或不同 acceptance obligation 可以独立变化时才拆分。
- 不得用 “page detail”“flow behavior” 或宽泛 summary 覆盖整个页面、对象或流程。
- 多个 source 片段分别提供同一规则的互补组成部分时，用一个 atom 的多个 `line-ranges[]` 表示；两个各自完整的有语义事实是否等价，留给 Phase 3 判断。

对 UI/flow source，至少检查 page role、route/entry/exit、具名 state、trigger、可见行为、允许/禁用 action、failure/recovery、persistence/navigation/access/privacy、影响任务完成的 responsive behavior、acceptance 和 scope guard。

### 3. 写入 source-local identity 与 evidence

- 使用稳定、可读、仅在当前 source 内唯一的 `source-atom-id`，例如 `intake-form.valid-submit`。
- canonical JSON 只写结构化 `line-ranges: [{"start": 1, "end": 2}]`，不得写冗余的 `lines` 字符串。
- renderer 从 `line-ranges[]` 机械生成 Markdown 的 `Lines` 列，例如 `L1-L2`。Markdown `Lines` 是 review surface，不是第二份 canonical evidence。
- `source-fact` 使用简体中文准确转述 source 语义，不用长段 quote 代替事实陈述。

### 4. 选择 Candidate Status

Phase 2 只使用以下五种 status；status 只表达 extraction disposition，不承载 guard、non-goal 或 duplicate 语义：

| 情形 | Candidate Status |
| --- | --- |
| actionable obligation 可映射到现有 Phase 1 Change | `direct-candidate` |
| actionable obligation 无法映射到现有 Change | `unassigned` |
| meaningful fact 只约束解释、设计或未来兼容，不创建当前 implementation scope | `contextual-candidate` |
| source 自身冲突，无法安全解释 | `unresolved-conflict` |
| meaningful content 暂时无法分类 | `unclassified` |

规则：

- 不使用 `duplicate-candidate`；Phase 2 不做同文档或跨文档 duplicate judgment。
- 不使用 `candidate-new-change` 或 `candidate-new-capability`；潜在 missing/refit boundary 一律使用 `unassigned`，由后续全局阶段决定。
- preserve rule、must-not 和 scope exclusion 可映射现有 Change 时使用 `direct-candidate`，无法映射时使用 `unassigned`；其语义由 `scope-guard`、`must-not` 和 `spec-guard` 表达。
- `unresolved-conflict` 和 `unclassified` 必须记录 blocker，不得用来绕过提取。

### 5. 选择 Artifact Projection

| Source 语义 | Candidate Artifact Projection |
| --- | --- |
| 用户/系统可观察的 normative behavior | `spec-requirement` |
| 保护已承诺行为的 preserve boundary、must-not 或 scope exclusion | `spec-guard` |
| architecture、runtime、data/API/schema、module/provider/deployment shape | `design-obligation` |
| test、fixture、visual、smoke、acceptance proof 或 evidence strategy | `verification-obligation` |
| 不创建当前 implementation scope 的 contextual fact | `contextual-only` |
| conflict/unclear 导致无法判断 | `unsure` |

projection 按 source 语义选择，不由 atom type 或 status 自动推断。

failure/recovery 内容若定义新的可观察结果，使用 `spec-requirement`；只有保护既有承诺或禁止 drift 的部分才使用 `spec-guard`。

### 6. 映射到现有 Change/Capability framework

只填写现有 framework mapping，不推断 `new` / `modified`：

| Atom | Candidate Owner Change | Candidate Target Capability |
| --- | --- | --- |
| direct spec / guard，可映射 | 现有 Phase 1 Change | 现有 Phase 1 Capability；无法判断时为 `unresolved` |
| direct design / verification，可映射 | 现有 Phase 1 Change | `none` |
| actionable 但无法映射现有 Change | `unassigned` | 已知现有 Capability，或 `unresolved` / `none` |
| contextual | `contextual` | `none` |
| conflict / unclassified | `none` | `none` |

Capability 不是 co-owner，target 也不表示 Capability advancement。

### 7. 最小辅助字段

每个 atom 只保留后续 normalization 必需的辅助字段：

- `atom-type`：`behavior`、`data-contract`、`architecture-runtime`、`verification`、`scope-guard` 或 `context`。
- `normativity`：`must`、`must-not`、`should` 或 `context`。source 中“用户可/系统允许”若定义必须提供的可用能力，记录为 `must`。
- `rationale`：简短说明 status/projection/mapping；`unassigned`、`contextual-candidate`、`unresolved-conflict` 和 `unclassified` 必须非空。

Phase 2 不再记录 `candidate-capability-impact`、`candidate-related-capabilities`、`roles`、`propose-use` 或 `evidence-need`；这些字段需要全局 normalization、source-window grounding 或 final plan context，提前填写只会制造噪声和伪精度。

## Canonical source atom file

每份 `.atoms.json` 使用 `source-aligned-source-atoms-v4`，包含：

- `trace-schema`、`trace-contract-version`
- `source-document`、`source-sha256`、`read-status: read-full`、`canonical-owner`
- `source-role`、`phase-1-candidate-changes-capabilities-considered`
- `source-atoms[]`
- `blockers[]`
- `language-self-check`

`source-atoms[]` 的 Markdown mirror：

| Source Atom ID | Lines | Atom Type | Source Fact | Normativity | Candidate Status | Candidate Artifact Projection | Candidate Owner Change | Candidate Target Capability | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

`Lines` 列由 canonical `line-ranges[]` 生成。`.atoms.md` 还包含 source identity、Phase 1 context、blocker、language self-check 和 `Trace Appendix`；render contract 为 `source-aligned-render-v4`。

字段 shape：

- `phase-1-candidate-changes-capabilities-considered` 是 array；每项包含 `change`、`capabilities[]` 和简短中文 `note`。
- `blockers[]` 是简体中文 string array；没有 blocker 时为 `[]`。
- `language-self-check` 是非空简体中文 string。
`phase-2.trace.json.sources[]` 每份 source 一行，包含 `source-document`、`atom-json-path`、`atom-json-sha256`、`atom-markdown-path`、`canonical-owner`、`read-status`、`atom-count` 和 `blockers[]`。

## 索引与报告

`source-obligation-atoms/index.md`：

| Source Document | Work Queue Batch | Canonical Owner | Source Atom File | Read Status | Atom Candidates | Candidate Status Summary | Projection Summary | Mapped Changes | Mapped Capabilities | Unassigned Atoms | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

`phase-2-agent-report.md` 先记录 index/report writer identity、只读 input、output 和 blocker，再包含：

| Batch | Source Documents | Source Atom Files | Docs Read Full | Atom Candidates | Status Summary | Projection Summary | Mapped Changes / Capabilities | Unassigned Atoms | Conflicts / Unclassified | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

aggregate 不发布 duplicate statistic、candidate new boundary、global coverage statistic、global atom 或 final plan map。

若 repair 修改 canonical `.atoms.json`，repair-writer 必须重跑 Phase 2 scoped renderer，并同步刷新受影响的 index、report 和 Phase trace count/digest；不得借此补做新的 extraction 或全局判断。随后 main agent 再刷新 manifest、运行 validator，并启动 fresh reviewer。

## 完成门禁

1. **Source gate**：每份 `read-full` source 在 work queue 中恰好一次，并有一个 canonical JSON 与 mirror。
2. **Semantic gate**：每项有产品/系统语义的 source fact 都有 atom；atom evidence range 尽量紧凑，不使用整章或整页范围掩盖未提取语义。全文 remainder disposition 留给 Phase 3。
3. **Atom gate**：atom 不 broad、不机械过拆；status 仅使用五种允许值；guard/non-goal 语义没有塞入 status；不存在 duplicate/new Change/new Capability 的 Phase 2 判断。
4. **Mapping gate**：owner/target 只引用现有 framework 或使用 `unassigned` / `unresolved` / `none`；不存在 Capability impact 判断。
5. **Artifact gate**：canonical JSON 使用 v4 schema 且只含 `line-ranges[]`；mirror 与 renderer output 一致。
6. **Role gate**：extraction writer 只写分配 JSON；index/report writer 未编辑 extraction 或执行全局判断。
7. **Review gate**：validator 和 fresh reviewer 通过；repair 后已重新验证；manifest 已刷新并冻结 evidence。

final reply 使用简短中文，报告 batch、已处理 source、atom count、mapped/unassigned atom、conflict/unclassified、language gate 和 blocker。
