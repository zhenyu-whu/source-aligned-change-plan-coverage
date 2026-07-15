# Phase 2：source-first obligation atom 提取

Phase 2 逐份完整阅读 source document，提取所有具有产品或系统语义的 source atom candidate。analysis unit 是 source document，不是 planned Change；Phase 1 framework 只提供现有 Change/Capability 的候选映射目标。

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
- `mode: targeted-patch` 时还必须读取 `phase-works/phase-5/evidence-patch-request.json` 和 `phase-works/phase-5/phase-5-checkpoint.json`；缺少、digest不匹配或request-id不是`EPR-0001`时立即`blocked`。

只写入以下 Phase 2 artifact：

- `phase-works/phase-2/source-obligation-atoms/work-queue.md`
- 每份 `Read Status: read-full` source 对应的 `<source>.atoms.json`
- 从每个 JSON 渲染的 `<source>.atoms.md`
- `phase-works/phase-2/source-obligation-atoms/index.md`
- `phase-works/phase-2/phase-2-agent-report.md`
- `trace/phase-2.trace.json`

路径均相对于 `openspec/orchestrate/`。source atom file 使用单层确定性名称：移除 source extension，将 path separator 替换为 `--`，再添加 `.atoms.json` 或 `.atoms.md`。

canonical JSON、renderer 和 validator 以 `references/trace-sidecar-contract.md` 为准；跨阶段语义以 `references/cross-phase-contract.md` 为准。每个 extraction writer 和 index/report writer 必须直接完整读取本文件、cross-phase contract 和 trace-sidecar contract。

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

每个 generation 最多执行一次 targeted patch，且固定消费 `source-aligned-evidence-patch-request-v1` 的 `request-id: EPR-0001`。

- `targets[]` 只允许 defect `quote-mismatch`、`range-mismatch`、`mixed-independent-occurrences`、`missing-occurrence`；只允许 operation `replace-quote`、`adjust-range`、`split`、`add`。
- writer只能读取并写入target的`source-document`、`source-atom-id`和`allowed-line-window`；必须使用request中的`canonical-owner`。不得删除、合并或重命名任何atom。
- `missing-occurrence`只能使用`add`，其`source-atom-id`、`global-atom-id`、`evidence-ref`、`base-row`和`base-row-sha256`必须为null；新增ID从`patch-epr-0001-add-01`连续分配。
- `split`保留原atom ID作为第一项，新增ID从`<old-source-atom-id>.part-02`连续分配；不得复用其他ID。
- `replace-quote`、`adjust-range`和`split`必须先验证immutable `base-row`及其`base-row-sha256`；原row除allowed operation对应的`source-fact`/`line-ranges`外不得改变；所有target必须限制在`allowed-line-window`。
- 每个target必须携带已冻结的`defect-witness`：只允许`phase-2-atom|phase-3-disposition` locator origin，source/window digest与canonical source逐字匹配，且window完全位于origin ranges的连续闭包内。existing target必须以自身immutable base row作为origin；非原文base不得进入targeted mode。
- `protected-rows`中的每行必须按compact sorted UTF-8 JSON计算SHA256并保持不变。任一protected row变化、request越界或需要第二次patch时立即`blocked`。
- targeted patch不得改变candidate mapping。split successor继承原atom的candidate status/projection/owner/target；新增遗漏occurrence使用`unassigned` owner/status且不得预填现有Capability target。最终mapping仍由Phase 5裁决。
- patch完成后仍使用canonical status `source-atoms-written`，只通过`phase-2.trace.json.mode: targeted-patch`区分；不得新增另一terminal status。

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

`Lines`列由canonical `line-ranges[]`生成。`.atoms.md`还包含source identity、Phase 1 context、blocker、language self-check和`Trace Appendix`；render contract为`source-aligned-render-v7`。

字段 shape：

- `phase-1-candidate-changes-capabilities-considered` 是 array；每项包含 `change`、`capabilities[]` 和简短中文 `note`。
- `blockers[]` 是简体中文 string array；没有 blocker 时为 `[]`。
- `language-self-check` 是非空简体中文 string。
- `source-atoms[].line-ranges[]` 必须恰好包含一个 range；`source-fact` 必须是该 range 对应 source text 的原文连续 substring。

`phase-2.trace.json.sources[]` 每份 source 一行，包含 `source-document`、`atom-json-path`、`atom-json-sha256`、`atom-markdown-path`、`canonical-owner`、`read-status`、`atom-count` 和 `blockers[]`。

## 索引与报告

`source-obligation-atoms/index.md`：

| Source Document | Work Queue Batch | Canonical Owner | Source Atom File | Read Status | Atom Candidates | Candidate Status Summary | Projection Summary | Mapped Changes | Mapped Capabilities | Unassigned Atoms | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

该index完全由work queue、全部`.atoms.json`和`phase-2.trace.json`聚合渲染；不得直接编辑。validator逐字重渲染比较。

`phase-2-agent-report.md` 先记录 index/report writer identity、只读 input、output 和 blocker，再包含：

| Batch | Source Documents | Source Atom Files | Docs Read Full | Atom Candidates | Status Summary | Projection Summary | Mapped Changes / Capabilities | Unassigned Atoms | Conflicts / Unclassified | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

aggregate 不发布 duplicate statistic、candidate new boundary、global coverage statistic、global atom 或 final plan map。

`phase-2.trace.json` 使用 `source-aligned-phase-2-trace-v4`，在既有字段外增加`mode`、`patch-request-ref`、`checkpoint-ref`和`patch-summary`。initial mode的两个ref和summary均为null。targeted mode的`patch-summary`必须且只能包含`base-phase-2-trace-sha256`、`affected-sources[]`、`changed-atoms[]`、`new-atoms[]`和`patch-writer-id`；changed row只含source document/atom ID与before/after row SHA，new row只含source document/atom ID与row SHA。不得把patch写成第二次initial extraction。`blocked` trace必须且只能包含schema/version、status、mode、两个patch ref、nullable `base-phase-2-trace-sha256`、`affected-sources[]`和非空`issues[]`；initial blocked的refs/base为null且affected为空，targeted blocked必须绑定唯一request/checkpoint、request中的base Phase 2 digest，并按request target首次出现顺序精确列出affected sources。

## 完成门禁

1. **Source gate**：每份 `read-full` source 在 work queue 中恰好一次，并有一个 canonical JSON 与 mirror。
2. **Semantic gate**：每项有产品/系统语义的 source fact 都有 atom；每个 atom 只有一个连续 evidence range，`source-fact` 是该 range 内的原文连续摘录，且该occurrence可被独立引用。全文 remainder disposition 留给 Phase 3。
3. **Atom gate**：每个atom可由一个mapping tuple无损表达；不以长度、behavior数量或主观“粗/细”判定质量。多义但可独立引用的occurrence交Phase 3 ambiguity audit；status仅使用五种允许值；guard/non-goal语义没有塞入status；不存在duplicate/new Change/new Capability的Phase 2判断。
4. **Mapping gate**：owner/target 只引用现有 framework 或使用 `unassigned` / `unresolved` / `none`；不存在 Capability impact 判断。
5. **Artifact gate**：canonical JSON 使用 v4 schema 且只含 `line-ranges[]`；mirror 与 renderer output 一致。
6. **Role gate**：extraction writer 只写分配 JSON；index/report writer 未编辑 extraction 或执行全局判断。
7. **Validation gate**：validator通过且manifest已刷新；失败即`blocked`，不得自动重启producer、重复当前Phase或启动reviewer/repair。
8. **Patch gate**：targeted mode只出现一次，request/checkpoint/base/protected row全部有效，修改严格落在targets与allowed operations内。

final reply 使用简短中文，报告 batch、已处理 source、atom count、mapped/unassigned atom、conflict/unclassified、language gate 和 blocker。
