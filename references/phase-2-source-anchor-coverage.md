# Phase 2：source-first obligation atom 提取

Phase 2逐份完整阅读source document，按自然语义单位提取所有具有产品或系统语义的source atom candidate。Analysis unit是source document，不是planned Change；Phase 1 framework只提供现有Change/Capability的候选映射目标。

本 Phase 只负责 raw extraction 和 existing-framework candidate mapping。正常路径使用 `mode: initial`；唯一回补路径使用 `mode: targeted-patch`，且只能消费 Phase 5 生成的 `EPR-0001`。本 Phase 不执行跨文档去重、global coverage closure、new/refit Change 判断、new Capability 判断或 repository baseline reconciliation；无法映射到现有 framework 的 atom 统一标记为 `unassigned`。

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
- `mode: targeted-patch`时必须额外完整读取`references/targeted-evidence-patch-contract.md`，并验证request、checkpoint、refit history与Phase 5 trace commit marker构成闭合授权组；孤立artifact不得授权写入。

只写入以下 Phase 2 artifact：

- `phase-works/phase-2/source-obligation-atoms/work-queue.md`
- 每份 `Read Status: read-full` source 对应的 `<source>.atoms.json`
- 从每个 JSON 渲染的 `<source>.atoms.md`
- `phase-works/phase-2/source-obligation-atoms/index.md`
- `phase-works/phase-2/phase-2-agent-report.md`
- `trace/phase-2.trace.json`

路径均相对于 `openspec/orchestrate/`。source atom file 使用单层确定性名称：移除 source extension，将 path separator 替换为 `--`，再添加 `.atoms.json` 或 `.atoms.md`。

Canonical JSON、renderer和validator以`references/trace-sidecar-contract.md`为准；跨阶段语义以`references/cross-phase-contract.md`为准。每个extraction writer和index/report writer必须直接完整读取本文件、cross-phase contract和trace-sidecar contract；只有targeted patch writer加载patch contract。

validator 通过后冻结 `.atoms.json`；`.atoms.md` 只能由 renderer 刷新。validator 未通过时本 Phase `blocked`，不得自动重启 producer 或重复当前 Phase。唯一例外是已进入合法 `mode: targeted-patch` 的单次局部写入。

## 角色与执行顺序

| 角色 | 允许读取 | Phase 2 content 写入 | 禁止事项 |
| --- | --- | --- | --- |
| main agent | Phase 1 plan、manifest、source metadata；targeted mode下读取request/checkpoint metadata | `work-queue.md` | 提取或修改 atom、作 coverage 判断 |
| extraction writer | 分配的 source 正文、Phase 1 plan/manifest、work queue、必需 contract | 分配 source 的 canonical `.atoms.json` | 写其他 source、跨文档比较、聚合、判断 new Change/Capability、读取 Phase 3–5 output |
| targeted patch writer | request列出的source、atom/range及必要最小局部上下文、request/checkpoint | 只修改request targets所在canonical `.atoms.json` | 全量重提取、越过allowed window、删除/合并/重命名atom、改变protected row |
| renderer | work queue、canonical Phase 2 JSON、Phase trace | 匹配的`.atoms.md` mirror和聚合`index.md` | 解释或补充atom |
| index/report writer | Phase 1 plan/manifest、work queue、全部 `.atoms.json` | 非canonical`phase-2-agent-report.md`、`phase-2.trace.json` | 手写index、重读source创建evidence、编辑atom、去重、闭合coverage或作final decision |

表中的写入限制只约束 Phase 2 content artifact。main agent 仍按 trace contract 负责共享 `trace/manifest.json` 的初始化和 validator 前后刷新；这不构成 extraction content 写入。

执行顺序：

1. main agent 建立 work queue。
2. 每个 batch 启动一个 fresh extraction writer；每份 source 只分配一个 canonical owner。
3. extraction writer 对每份 source 依次完成：全文阅读 → atom extraction → existing-framework mapping → canonical JSON。
4. 所有extraction完成后，启动fresh index/report writer，只读聚合JSON，并写入非canonical report和status为`source-atoms-written`的Phase trace。该status只表示writer output已形成。
5. 在repository root运行Phase 2 scoped renderer，依次生成每份atom mirror和聚合index：

   ```bash
   python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
     --orchestrate-dir openspec/orchestrate \
     --artifact phase2-source-atoms \
     --write
   python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
     --orchestrate-dir openspec/orchestrate \
     --artifact phase2-index \
     --write
   ```
6. 聚合发现缺失或格式错误时只记录blocker，不得修复extraction。
7. main agent运行validator；通过后刷新manifest并冻结Phase 2，失败则记录issue并`blocked`。不得启动reviewer/repair或自动重复当前Phase。

## Targeted patch mode

本模式的eligibility、defect/operation、window、successor ID、protected row、发布组和失败规则全部以`references/targeted-evidence-patch-contract.md`为唯一权威，本文件不复制。

- Writer只修改request targets及必要最小局部上下文，并使用冻结canonical owner；不得执行全量重提取。
- Candidate mapping保持不变；split successor继承原candidate metadata，新增missing occurrence使用`unassigned`且不预填Capability target。
- 完成后仍使用`status: source-atoms-written`，只以`phase-2.trace.json.mode: targeted-patch`区分。
- 失败trace保留commit marker引用、base digest与affected sources，随后由main agent按patch contract执行abort；不得重跑本Phase。

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

一个 atom 的粒度只需保证该source occurrence可被独立引用，并能由单一mapping tuple无损表达。长度、behavior数量、实现或验证是否可独立执行，都不是单独的拆分指标。

- 保留同一规则的 condition + trigger/action + expected effect，不机械拆分。
- 只有source内存在需要独立引用的多个occurrence，或一个tuple无法无损表达其责任时才拆分。Phase 2不因猜测final owner、relation、projection或target Capability而拆分。
- 内容较长但单一tuple可无损表达时不报错；内容较短但可导出多个合理tuple时，保留occurrence并交Phase 3记录mapping ambiguity，不在Phase 2主观过拆。
- 每个 atom 的 `line-ranges[]` 必须且只能包含一个连续 range。连续多行可使用一个 `{start, end}`；互不连续的 source 片段必须分别提取为独立 atom。即使这些 atom语义相同，后续也保留独立 evidence occurrence。

对 UI/flow source，至少检查 page role、route/entry/exit、具名 state、trigger、可见行为、允许/禁用 action、failure/recovery、persistence/navigation/access/privacy、影响任务完成的 responsive behavior、acceptance 和 scope guard。

### 3. 写入 source-local identity 与 evidence

- 使用稳定、可读、仅在当前 source 内唯一的 `source-atom-id`，例如 `intake-form.valid-submit`。
- canonical JSON 只写结构化 `line-ranges: [{"start": 1, "end": 2}]`，数组长度必须为 1，不得写冗余的 `lines` 字符串。
- renderer 从 `line-ranges[]` 机械生成 Markdown 的 `Lines` 列，例如 `L1-L2`。Markdown `Lines` 是 review surface，不是第二份 canonical evidence。
- `source-fact` 必须直接摘录唯一 range 内的原文连续片段，不得转述、翻译、概括或改写。解析后的 canonical JSON string 保留原始字符和换行；renderer 可为 Markdown table 执行展示层转义或折行处理，但不得回写、改造或替代 canonical value。

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

每个 atom 只保留后续 evidence resolution 与 final mapping 必需的候选辅助字段：

- `atom-type`：`behavior`、`data-contract`、`architecture-runtime`、`verification`、`scope-guard` 或 `context`。
- `normativity`：`must`、`must-not`、`should` 或 `context`。source 中“用户可/系统允许”若定义必须提供的可用能力，记录为 `must`。
- `rationale`：简短说明 status/projection/mapping；`unassigned`、`contextual-candidate`、`unresolved-conflict` 和 `unclassified` 必须非空。

Phase 2 不记录 `candidate-capability-impact`、`candidate-related-capabilities`、`roles`、`propose-use` 或 `evidence-need`；这些字段需要完整原文集合复审或 final plan context，提前填写只会制造噪声和伪精度。

## Canonical source atom file

每份`.atoms.json`使用`source-aligned-source-atoms-v4`，是本Phase extraction的内容权威；顶层、context row、atom row、range row、trace source row及Markdown mirror的exact machine/render shape只由`references/trace-sidecar-contract.md`定义。本文件只定义如何按自然语义单位提取及填写这些字段，不复制机器契约。

每个atom仍只对应一个连续evidence range，`source-fact`必须是该range对应source text的逐字连续substring。`.atoms.md`完全由canonical JSON按`source-aligned-render-v8`生成，只用于review，不得直接编辑或补充第二份语义。

## 索引与报告

`source-obligation-atoms/index.md`：

| Source Document | Work Queue Batch | Canonical Owner | Source Atom File | Read Status | Atom Candidates | Candidate Status Summary | Projection Summary | Mapped Changes | Mapped Capabilities | Unassigned Atoms | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

该index完全由work queue、全部`.atoms.json`和`phase-2.trace.json`聚合渲染；不得直接编辑。validator逐字重渲染比较。

`phase-2-agent-report.md` 先记录 index/report writer identity、只读 input、output 和 blocker，再包含：

| Batch | Source Documents | Source Atom Files | Docs Read Full | Atom Candidates | Status Summary | Projection Summary | Mapped Changes / Capabilities | Unassigned Atoms | Conflicts / Unclassified | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

aggregate 不发布 duplicate statistic、candidate new boundary、global coverage statistic、global atom 或 final plan map。

`phase-2.trace.json`继续使用`source-aligned-phase-2-trace-v4`。字段、exact shape、initial/targeted cardinality和blocked surface只由trace contract定义；targeted trace还必须满足patch contract的commit marker与affected closure规则，不得伪装成第二次initial extraction。

## 完成门禁

1. **Source gate**：每份 `read-full` source 在 work queue 中恰好一次，并有一个 canonical JSON 与 mirror。
2. **Semantic gate**：每项有产品/系统语义的 source fact 都有 atom；每个 atom 只有一个连续 evidence range，`source-fact` 是该 range 内的原文连续摘录，且该occurrence可被独立引用。全文 remainder disposition 留给 Phase 3。
3. **Atom gate**：每个atom可由一个mapping tuple无损表达；不以长度、behavior数量或主观“粗/细”判定质量。多义但可独立引用的occurrence交Phase 3 ambiguity audit；status仅使用五种允许值；guard/non-goal语义没有塞入status；不存在duplicate/new Change/new Capability的Phase 2判断。
4. **Mapping gate**：owner/target 只引用现有 framework 或使用 `unassigned` / `unresolved` / `none`；不存在 Capability impact 判断。
5. **Artifact gate**：canonical JSON 使用 v4 schema 且只含 `line-ranges[]`；mirror 与 renderer output 一致。
6. **Role gate**：extraction writer 只写分配 JSON；index/report writer 未编辑 extraction 或执行全局判断。
7. **Validation gate**：validator通过且manifest已刷新；失败即`blocked`，不得自动重启producer、重复当前Phase或启动reviewer/repair。
8. **Patch gate**：targeted mode只出现一次，完整Phase 5授权组、base/protected row与affected closure全部有效，修改严格落在patch contract授权范围内。

final reply 使用简短中文，报告 batch、已处理 source、atom count、mapped/unassigned atom、conflict/unclassified、language gate 和 blocker。
