# Phase 1：Capability-first 初始 Change 框架

Phase 1完整阅读用户指定的source document，先形成candidate Capability topology，再形成outcome-sliced Change roadmap。该产物是供Phase 2–5验证和refit的framework hypothesis，不是requirement inventory、coverage结论或final plan。

writer必须直接完整读取：

- `references/cross-phase-contract.md`
- `references/change-capability-framework-principles.md`
- 本文件
- `references/trace-sidecar-contract.md`

Change/Capability定义、gate、split/merge、foundation、排序和overlay规则只以共享原则文档为准；本文件不建立第二套标准。

## 目标与边界

Phase 1只负责：

- 枚举并完整阅读用户指定source set中的每份source document；
- 建立coarse semantic landscape：actor、长期domain object、lifecycle、responsibility、contract、constraint、architecture decision和major outcome；
- 按共享原则先推导candidate Capability topology；
- 再按source-backed outcome和hard dependency建立candidate Change roadmap；
- 建立coarse Change-Capability advancement hypothesis；
- 直接编写内容权威`initial-change-plan.md`，并写入source manifest、非canonical agent report和control trace。

Phase 1不得：

- 提取、枚举、规范化或计数obligation atom；
- 创建atom ID、line-level trace、coverage ledger或unique owner；
- 决定requirement-level operation或Capability-level `New` / `Modified`；
- 创建proposal、design、spec、task或verification artifact。

所有initial Change、Capability、advancement和排序必须标为hypothesis，Phase 2–5可以根据完整evidence调整。

## 输入权威

- 只使用用户指定的文档或目录作为production obligation的source authority。
- 必须枚举并完整阅读每份有意义的source document；不得抽样或只浏览文件名。
- 非source artifact可以标记为`non-source-artifact`，但有意义的source document不得跳过。
- 除非用户明确纳入input，不读取或依赖现有OpenSpec spec/Change/archive，因此不得输出`New` / `Modified`。
- 无法安全完成full-source read时返回blocker，不得写成功态plan或trace。

## 产出

```text
phase-works/phase-1/
├── initial-change-plan.md
├── source-doc-manifest.md
├── phase-1-agent-report.md
├── phase-1-reviewer-report.md
└── phase-1-repair-report.md  # 仅发生 repair 时

trace/phase-1.trace.json
```

Phase 1不得创建或更新根`change-plan.md`。

`initial-change-plan.md`是Phase 1内容权威。`source-doc-manifest.md`是人工阅读界面；其逐行数据、source digest、initial plan digest和machine-readable bounded review gate由`phase-1.trace.json`提供机器校验。agent/reviewer/repair report是非canonical流程证据，不进入manifest。

## 规划方法

严格按以下顺序：

1. 枚举source set，完整阅读正文并写source manifest。
2. 建立coarse semantic landscape，不转写为atom ledger。
3. 使用共享Capability gate推导candidate Capability topology，为每项写Purpose、Owns、Excludes、boundary rationale和coarse source hint。
4. 建立source-backed behavior maturity / hard-dependency graph。
5. 独立于Capability列表，使用共享Change gate生成candidate Change。
6. 使用共享overlay规则叠加Change与Capability；dependency、reuse、preserve、related-only和implementation-only内容不建立edge。
7. 先按hard dependency DAG排序，再按outcome maturity选择最薄可验收结果。
8. 写入assumption、conflict、non-goal、deferred content和风险检查，并声明当前framework是hypothesis。

coarse source hint只使用source path、heading、section、decision ID、route/page/object/API/command/entity/job/event等locator；不得包含line range、atom ID、coverage status或完整requirement枚举。

## 输出模板

### Source manifest

`source-doc-manifest.md` 使用：

| Source Document | Read Status | Source Role | Coarse Topics / Paths | Notes |
| --- | --- | --- | --- | --- |

- 每份用户指定source document恰好一行。
- 成功态中每份source document均为`read-full`。
- 只有确实不属于source authority的文件才可标记`non-source-artifact`。

### Initial change plan

`initial-change-plan.md` 必须按顺序包含以下二级heading。

#### `## 输入`

- 已指定并完整阅读的source document；
- 用户提供的non-source candidate plan，或`无`；
- assumption、conflict和blocker；成功态blocker为`无`。

#### `## Source Semantic Landscape`

| Semantic Area | Coarse Source-backed Understanding | Planning Relevance | Source Hint |
| --- | --- | --- | --- |

只记录coarse synthesis，不拆成obligation行，不声称exhaustive coverage。

#### `## Capability Map`

| Candidate Capability | Grouping Basis | Purpose | Owns | Excludes | Coarse Source Hint | Boundary Rationale |
| --- | --- | --- | --- | --- | --- | --- |

- ID使用英文kebab-case。
- Purpose、Owns、Excludes和Boundary Rationale必须直接回答共享Capability gate。
- 没有business Capability delta时写`无 candidate business Capability`，不得发明technical Capability。

#### `## Change 切分原则`

- 写明实际采用的source-backed outcome slicing principle；
- 写明被拒绝的机械切分及原因；
- 声明Capability topology先形成，但Change boundary独立使用共享Change gate决定；
- 声明当前boundary、advancement和order均为hypothesis，尚未执行obligation extraction。

#### `## Change Roadmap`

每个Change使用：

- Change 名称：英文kebab-case slug。
- 单一 intent：
- source-backed outcome：
- 来源 evidence hint：
- 范围内：
- 范围外：
- behavior completeness profile：
  - trigger/context：
  - normative behavior：
  - observable outcome / invariant：
  - important exception / error semantics：
  - acceptance evidence：
- 硬依赖：
- 排序理由：
- 独立完成与归档：
- 拆分/合并判断：

这些字段必须直接回答共享Change gate，不得用模板文本替代source-backed判断。

#### `## Change-Capability Overlay`

| Change | Candidate Capability | Roadmap Role | Direct Behavior Delta Hypothesis | Coarse Source Hint |
| --- | --- | --- | --- | --- |

- `Roadmap Role`只允许`first-advancement`或`later-advancement`，不等于`New` / `Modified`。
- 只有direct normative behavior delta建立edge。
- 没有advancement时写`无 candidate Capability advancement`。

#### `## Phase 1 风险检查`

逐项确认：

1. source manifest完整且全部`read-full`；
2. 未提前执行atom extraction、line coverage、unique owner或baseline relation；
3. 每个Capability通过共享Capability gate；
4. 每个Change通过共享Change gate；
5. behavior completeness只包含source-backed语义；
6. overlay只表达direct advancement；
7. roadmap满足hard dependency和outcome maturity；
8. foundation若存在则符合共享例外；
9. 隐藏Capability名称后Change仍可由intent/outcome解释；
10. 隐藏roadmap后Capability仍具有稳定Purpose和archive durability；
11. overlay自然表达多对多关系，没有机械对角化。

#### `## Phase 1 语言自检`

确认固定heading、field、enum、ID、path、代码符号和精确source quote之外的agent解释均为简体中文。

## Bounded review gate

writer发布可校验plan/trace后，main agent先运行Phase 1 validator，再按`references/review-gates.md`把validator结果与plan一起交给initial review；有finding时最多执行两轮定向repair，并在每轮repair后重跑validator。只有最后一次validator与review均通过才算Phase 1成功。`phase-1.trace.json`使用`source-aligned-phase-1-trace-v3`，其中`review-gate`必须且只能包含：

- `status: passed|blocked`
- `writer-id`
- `reviews[]`
- `repairs[]`

`reviews[]` 最多三行，每行只包含 `round`、`reviewer-id`、`validator-status`、`plan-sha256` 和 `finding-fingerprints[]`。`repairs[]` 最多两行，每行只包含 `round`、`repair-writer-id`、`finding-fingerprints[]`、`before-plan-sha256` 和 `after-plan-sha256`。finding fingerprint必须绑定稳定rule/subject及相关input digest，不受finding措辞或repair方案影响；相同fingerprint在后续任一轮review重现时，即使整份plan digest不同也立即`blocked`。

- review与repair round分别从1连续递增；通常`len(reviews) = len(repairs) + 1`。若repair未产生有效差异，必须在该repair后立即`blocked`，此时允许terminal trace使用`len(reviews) = len(repairs)`，不得再启动reviewer。
- terminal success要求`review-gate.status: passed`、最后一个review的findings为空且validator为`passed`，并且reviewer/writer/repair-writer身份相互独立。
- 同一 finding fingerprint 在后续任一轮 review 再次出现时，即使整份 plan digest 已变化，也必须立即 `blocked`。
- 任一 repair 的 before/after plan digest 相同，必须 `blocked`。
- 第二轮 repair 后的 final review 仍不通过，必须 `blocked`；不得启动第三轮 repair。

## Phase报告与完成条件

`phase-1-agent-report.md` 简要列出已读source、artifact path、assumption/conflict、candidate Capability/Change/edge数量、Phase边界确认、语言门禁和blocker。

成功态必须：

- source set完整读取；
- initial plan符合固定模板和共享原则；
- trace使用`source-aligned-phase-1-trace-v3`且source manifest数据、plan/source digest与bounded review gate有效；
- agent report blocker为`无`；
- validator通过，bounded review gate为`passed`。

若在initial plan与review gate可建立之前即无法完整读取source，只记录非canonical orchestration stop并停止，不得伪造缺少plan/review gate的canonical `blocked` trace。已有可校验initial plan后，共享gate无法满足或bounded review耗尽时才使用canonical `blocked`并停止；两种情况都不得发布成功态plan/trace或进入Phase 2。
