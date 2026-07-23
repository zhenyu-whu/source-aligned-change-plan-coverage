# Phase 2：source-first occurrence 与显式 delivery directive 提取

Phase 2逐份完整阅读source document，按自然语义单位提取所有具有产品或系统语义的source atom candidate，并只在source明示时记录`delivery-directives[]`。Analysis unit是source document，不是planned Change；Phase 1 framework只提供existing-framework candidate mapping目标。

本Phase只负责provisional raw extraction、explicit directive extraction和candidate mapping。它不执行跨文档去重、coverage closure、new/refit Change判断、hard dependency、Change order、guard allocation、foundation-like判断或baseline reconciliation。

## 输入与产出

输入：

- `phase-works/phase-1/initial-framework.json`语义权威
- `phase-works/phase-1/initial-change-plan.md`确定性mirror，仅用于人工导航
- `phase-works/phase-1/source-doc-manifest.md`
- 用户指定的source root或精确source path。

只写入：

- `phase-works/phase-2/source-obligation-atoms/work-queue.md`
- 每份read-full source的`<source>.atoms.json|md`
- `phase-works/phase-2/source-obligation-atoms/index.md`
- `phase-works/phase-2/phase-2-agent-report.md`
- `trace/phase-2.trace.json`

Canonical JSON、renderer和validator以`trace-sidecar-contract.md`为准；跨阶段语义以`cross-phase-contract.md`为准。`.atoms.json`在Phase 3 evidence-freeze gate通过前都是provisional。

## 角色与执行顺序

| 角色 | 允许读取 | 写入 | 禁止事项 |
| --- | --- | --- | --- |
| main agent | Phase 1 JSON authority、manifest、source metadata | `work-queue.md` | 提取atom、directive或coverage判断 |
| extraction writer | 分配source、Phase 1 JSON authority/manifest、contract | 分配source的canonical JSON | 写其他source、跨文档比较、判断dependency/order |
| renderer | work queue、canonical JSON、trace | Markdown mirror与index | 解释或补充atom/directive |
| index/report writer | Phase 1、queue、全部JSON | report与Phase 2 trace | 重读source创建evidence、编辑atom或规划framework |
| evidence repair writer | 上一轮finding及最小相关authority | finding命中的provisional JSON | 扩大scope、裁决final mapping/order |

执行顺序：

1. Main agent建立work queue。
2. 每个batch启动fresh extraction writer；每份source只有一个canonical owner。
3. Writer全文阅读，依次完成occurrence extraction、explicit directive extraction、candidate mapping与canonical JSON。
4. 运行Phase 2 preflight，检查source digest、quote/range、directive enum与candidate mapping矩阵。
5. Fresh index/report writer聚合JSON并写trace/report。
6. Renderer生成atom mirror和index。
7. Main agent运行普通Phase 2 validator；通过后进入Phase 3，但不得声明evidence或directive已冻结。

## Work queue

`work-queue.md`只做scheduling，不得包含atom、directive、coverage judgment或“无obligation”结论。

- 每份read-full source恰好出现在一个batch，并有一个canonical owner。
- 按source family、role、doc type、line count、semantic density和context pressure形成少量coherent batch。
- 同一source不得拆给多个writer。

## Atom 提取方法

### 1. 提取所有有产品/系统语义的事实

必须成为atom candidate：

- 用户或系统condition、state、action、transition、display、failure、recovery或observable result；
- 数据、权限、隐私、API、schema、runtime、provider、deployment、integration或persistence boundary；
- preserve rule、must-not、explicit non-goal或scope guard；
- acceptance、fixture、proof或verification requirement；
- 明示的milestone、precedence、deferred scope；
- 会改变当前实现、验证或兼容性判断的contextual fact；
- source conflict或meaningful unclear content。

纯格式、TOC、无production effect的prototype detail或明确superseded content不创建atom。Phase 2不判断semantic duplicate。

### 2. 控制 atom 粒度

一个atom必须可被独立引用，并能由单一mapping tuple无损表达。

- 保留同一规则的condition + trigger/action + expected effect，不机械拆分。
- 互不连续source片段分别提取；每个atom只有一个连续range。
- 不因猜测final owner、Capability或Change order拆分。
- `delivery-directives[]`可与behavior/architecture occurrence共存；只有存在多个独立责任、单一tuple无法表达时才拆分。

### 3. Source-local identity 与 evidence

- 使用稳定、source-local唯一的`source-atom-id`。
- `line-ranges[]`恰好一个`{start,end}`。
- `source-fact`是range内逐字连续原文，不得转述、翻译或概括。

### 4. Delivery directives

每个atom必须显式包含`delivery-directives[]`，只允许：

- `milestone-scope`
- `explicit-precedence`
- `explicit-deferred`

填写规则：

- 只有source明示阶段/版本范围、前后关系或延期/非阻塞语义时填写；
- 数组唯一并按上述固定顺序排列；没有明示时为空数组；
- steady-state architecture、security invariant、component layering、调用方向、数据流、复用或实现常识不得产生directive；
- Phase 1 coarse ordering不得反向影响本字段；
- directive不改变candidate status、projection、owner或target；
- source同时表达多个directive时可以多值；无法安全判断时使用现有conflict/unclassified机制并记录blocker，不猜测。

### 5. Candidate status

只允许：

| 情形 | Candidate Status |
| --- | --- |
| actionable obligation可映射到Phase 1 Change | `direct-candidate` |
| actionable obligation无法映射 | `unassigned` |
| meaningful fact只约束解释、设计或未来兼容 | `contextual-candidate` |
| source冲突 | `unresolved-conflict` |
| meaningful content暂时无法分类 | `unclassified` |

不使用duplicate/new Change/new Capability status。潜在missing/refit boundary统一`unassigned`。

### 6. Artifact projection

| Source语义 | Candidate Projection |
| --- | --- |
| 用户/系统可观察normative behavior | `spec-requirement` |
| preserve/must-not/scope exclusion | `spec-guard` |
| architecture/runtime/data/API/schema/provider/deployment shape | `design-obligation` |
| test/fixture/smoke/acceptance proof | `verification-obligation` |
| 不创建当前scope的context | `contextual-only` |
| conflict/unclear | `unsure` |

Directive与projection正交。Architecture occurrence即使带显式milestone也仍可为design obligation；没有明示directive时不得因为是architecture而推断先后。

### 7. Existing-framework candidate mapping

只填写现有framework mapping，不推断`new|modified`：

| Status / Projection | Owner | Target |
| --- | --- | --- |
| direct + spec/guard | Phase 1 Change | Phase 1 Capability或`unresolved` |
| unassigned + spec/guard | `unassigned` | Phase 1 Capability或`unresolved` |
| direct/unassigned + design/verification | 与status一致的Change或`unassigned` | `none` |
| contextual + contextual-only | `contextual|none` | `none` |
| conflict/unclassified + unsure | `none` | `none` |

Capability不是co-owner，candidate target不表示advancement。Candidate mapping不得被用于证明Phase 1 boundary、dependency或order。

## Canonical source atom v6

每份`.atoms.json`使用`source-aligned-source-atoms-v6`。顶层exact shape见trace contract。每个`source-atoms[]` row只包含：

- `source-atom-id`
- `line-ranges[]`
- `atom-type`
- `source-fact`
- `normativity`
- `delivery-directives[]`
- `candidate-status`
- `candidate-artifact-projection`
- `candidate-owner-change`
- `candidate-target-capability`
- `rationale`

Markdown完全由JSON按`source-aligned-render-v11`生成。

## 索引、trace 与完成门禁

Index增加`Delivery Directive Atoms`与directive summary。Phase 2 report记录每个batch的atom count、directive atom count、mapped/unassigned和blocker。

`phase-2.trace.json`使用`source-aligned-phase-2-trace-v6`。成功source row在既有字段外增加`delivery-directive-atom-count`。成功状态`source-atoms-written`仍是provisional，不是freeze marker。

完成门禁：

1. 全部read-full source有唯一canonical JSON与mirror；
2. 每项production语义与显式delivery directive都有occurrence；
3. 每个source-fact、range可信；
4. 每个directive均由source明示，数组enum/顺序合法；
5. 不存在从architecture、Capability、guard或实现常识推断的directive；
6. Candidate mapping矩阵合法；
7. Writer未规划hard dependency、Change order或foundation-like；
8. Preflight与普通validator通过；
9. 只有Phase 3 terminal gate能冻结evidence与directive。

Final reply使用简短中文，报告batch、source、atom count、directive atom count、mapped/unassigned、conflict/unclassified和blocker。
