# Phase 3：覆盖规范化与 gap 审计

Phase 3 消费 source-first Phase 2 atom file，并生成规范化 global obligation atom index。它负责闭合 source coverage、处理跨文档 duplicate 和稳定 atom identity，不负责创建/refit Change 或判定 new Capability；这些 final boundary decision 由 Phase 5 完成。

执行本 Phase 前，writer 必须直接完整读取 `references/cross-phase-contract.md`；prompt 摘要、转述或继承上下文不能替代直接读取。

Phase 3 不是新的 propose-writing pass，不得在没有 source evidence 时发明 production requirement。它回答：

1. 每项具有生产意义的 source obligation 是否都有 atom？
2. 每个 atom 是否足够小、具有 source 支撑且语义有效？
3. broad atom 是否压缩了多个 UI/flow/data/verification obligation？
4. 重复 atom 是真正 duplicate、refinement、preserve/dependency/context，还是 conflict？
5. 每项 production obligation 是否能分配给一个 candidate owner Change，每项 spec projection 是否能获得规范化 capability impact/target；还是必须等 Phase 4 source-window grounding 后，由 Phase 5 refit 决定？
6. 所有无 atom 的 source range 是否确实属于 non-production、reference-only、formatting、background 或其他可安全忽略内容？
7. 每个 atom 是否根据 source semantics 获得正确 artifact projection（`spec-requirement`、`spec-guard`、`design-obligation`、`verification-obligation` 或 `contextual-only`）？

Phase 2 atom 行范围和 section inventory 可用于导航与 mechanical check，但 semantic obligation coverage 才是 quality gate。

## 输入

- `openspec/orchestrate/phase-works/phase-1/initial-change-plan.md`
- `openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/work-queue.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/index.md`
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/<source>.atoms.json`，作为 canonical extraction evidence
- `openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/<source>.atoms.md`，作为 reviewer mirror
- 用户指定的 source document 根目录或精确 source path，用于 manifest verification 和 targeted semantic read。
- 必需 mechanical helper/input shape：`.codex/skills/source-aligned-change-plan-coverage/scripts/phase3_line_range_audit.py` 或等效 Phase 3 code 必须为每份 `read-full` source document 计算 Phase 2 atom line coverage，并将结果保存在 `source-remainder-review.json` 中。section inventory 的全文覆盖由 Phase 2 validator 单独校验。

## 输出

只写入当前副本：

- `openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md`
- 为 manifest 中列出的每份 source document 写入 `openspec/orchestrate/phase-works/phase-3/source-doc-coverage/<source-relative-path-without-extension>.coverage.md`
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`
- `openspec/orchestrate/change-capability-anchors/obligation-atom-index.json`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/source-to-global-atom-map.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/source-remainder-review.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/source-remainder-review.json`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/duplicate-ownership-review.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-trace/atom-normalization-decision-log.md`
- `openspec/orchestrate/phase-works/phase-3/coverage-review.md`
- `openspec/orchestrate/phase-works/phase-3/phase-3-agent-report.md`
- `openspec/orchestrate/trace/phase-3.trace.json`

per-source file 使用单层 filename。根据 manifest 中列出的 source document path 生成名称，移除 extension，将 path separator 替换为 `--`，再添加 `.coverage.md`。不得在 `phase-works/phase-3/source-doc-coverage/` 下创建 nested directory。

Phase 3 可以向 canonical `obligation-atom-index.json` 添加精确的 missing source-backed atom，再从该 JSON 渲染 `obligation-atom-index.md`。不得编辑 Phase 2 source atom file。如果 missing obligation 过于宽泛，或需要超出 targeted semantic review 范围重读大量 document，返回 `Decision: blocked`，并说明是否需要完整 Phase 2 rerun。

`phase-works/phase-3/phase-3-trace/` 记录当前 Phase 3 intermediate audit trail。JSON file 是 canonical；renderer-backed Markdown mirror 只是 review aid，不是 source of truth。每次 fresh Phase 3 run 都必须覆盖这些文件，并确保它们与 canonical `obligation-atom-index.json`、per-source coverage file 和 `phase-works/phase-3/coverage-review.md` 一致。

writer 完成后返回 main agent，由 main agent 完整执行 `references/reviewer-repair-loop.md`。Phase 3 writer 不得自行 reviewer、repair 或推进 Phase 4。

## Artifact 语言门禁

继承 `references/cross-phase-contract.md` 的 Artifact Language Gate。Phase 3 的 `Source Fact`、`Review Judgment`、`Reason`、`Interpretation`、semantic classification、duplicate/ownership resolution、non-atom range reason、handoff、metric interpretation 和 report summary 必须使用简体中文。

## global atom 索引

`change-capability-anchors/obligation-atom-index.json` 是 canonical 规范化 global registry；`change-capability-anchors/obligation-atom-index.md` 是其 renderer-backed review mirror。该 registry 解决 global uniqueness、artifact projection、candidate Change ownership、capability impact/target、source-explicit related Capability、source traceability 和 non-direct relation。Capability 不是 co-owner。

必须包含：

| Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Coverage Status | Artifact Projection | Owner Change | Capability Impact | Target Capability | Related Capabilities | Source Atom Origins | Atom Relation | Propose Use | Evidence Need | Review Judgment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

规则：

- 为每项 production obligation 分配且只分配一个 `Global Atom ID`。
- 每个 `Global Atom ID` 必须使用 canonical `GA-####` 格式，例如 `GA-0001`。不得使用其他 global 前缀、范围或 Phase 2 source-local atom ID 作为规范化 global atom ID。
- 如果两个 source atom 行描述同一 source obligation，保留一个 global atom，并将其他行映射到同一 global atom 或 non-direct relation。
- 如果后续 obligation 确实增强或缩窄早期 obligation，只为额外的 source-backed delta 创建新 atom，并将 `Atom Relation` 设为 `refines:<global-atom-id>` 或 `modifies:<global-atom-id>`。
- 如果 source fact 只 preserve 或依赖另一 atom，使用 `preserves:<global-atom-id>` 或 `depends-on:<global-atom-id>` 等 `Atom Relation`，不得计入 duplicate direct coverage。
- 如果 source fact 只用于使当前 design 与后续 obligation 保持兼容，将其分类为 contextual future-compatibility；已知时链接到未来或 candidate global atom。
- coverage 完成但 final Change placement 依赖 source-window grounding、sequence 或 granularity decision 时，`Owner Change` 可以保持 `phase-5-refit-required`。Phase 5 必须在 final output 前解决。
- `Capability Impact` 为 `new`、`modified`、`none` 或 `unresolved`。`new` / `modified` 只适用于 direct `spec-requirement` / `spec-guard` 行，并要求具体、已声明的 `Target Capability` 与可信 repository baseline evidence；Phase 3 未读取或无法确认 baseline 时必须使用 `unresolved`。`none` 要求 target `none`。`unresolved` 可以使用已知 target 或 `unresolved`，要求非空 `Review Judgment` 或 rationale，并且必须在 Phase 5 baseline reconciliation 中解决。
- direct `design-obligation` / `verification-obligation` 行使用 impact `none` 和 target `none`，同时保持 direct 且由 Change candidate-own。non-direct/contextual 行也使用 `none` / `none`。
- `Related Capabilities` 是已声明 Capability ID 的唯一 array，其关联必须由引用 source window 明确表达。默认为 `[]`，排除 `Target Capability`，不得替代 target，也不产生 ownership、progression、Capability view 或 complexity count。
- `Artifact Projection` 必须独立于 `Coverage Status` 并遵循 source semantics：direct architecture/runtime/package/schema/provider/deployment atom 可以为 `design-obligation`；test strategy、fixture、visual、smoke 和 evidence atom 可以为 `verification-obligation`；preserve 和显式 non-goal atom 可以为 `spec-guard`。
- `contextual-only` 只用于 non-direct context、reference、future-compatibility 或 non-coverage 行。如果 atom 仍为 direct candidate 或 `phase-5-refit-required`，分配 `spec-requirement`、`spec-guard`、`design-obligation` 或 `verification-obligation`；如果不存在安全的 non-context projection，将该行标记为 `blocked`，不得让 direct atom 以 `contextual-only` 继续。
- 除非指出 duplicate 的 `Global Atom ID` 并解释 semantic equivalence，否则 `duplicate` 不是完整 rationale。

artifact projection value：

- `spec-requirement`
- `spec-guard`
- `design-obligation`
- `verification-obligation`
- `contextual-only`
- `blocked`

coverage status：

- `direct`
- `contextual`
- `preserve-existing`
- `later-change`
- `explicit-non-goal`
- `reference-only`
- `prototype-only-not-production`
- `superseded`
- `no-product-or-system-impact`
- `phase-5-refit-required`
- `unresolved-conflict`
- `blocked`

## 来源发现与读取边界

读取 Phase 1 `phase-works/phase-1/source-doc-manifest.md`，确认它仍与用户指定的 source root 匹配，并将增强后的 Phase 3 review 副本写入 `phase-works/phase-3/source-doc-manifest.md`。如果 Phase 1 未列出每份 source document，或 Phase 2 未为每份 `read-full` source document 写入 source atom file，则返回 `Decision: blocked`；除非可以通过 targeted Phase 3 review 修正问题，且不会使 Phase 1 或 Phase 2 失效。

为每个 manifest 行在 `phase-works/phase-3/source-doc-coverage/` 下写入匹配的 per-source review file，即使 final classification 为 `reference-only`、`intentionally-not-read` 或 `non-source-artifact`。

将每份 document 分类为：

- `covered-by-atoms`
- `candidate-missing-atoms`
- `reference-only`
- `intentionally-not-read`
- `non-source-artifact`
- `blocked`

使用 Phase 2 source atom file、section inventory、Phase 1 source hint、file path/name、source-root scope 和 targeted source read 分类 document。出现以下任一情形时，阅读 source file content：

- source section 可能是 obligation-bearing，需要 atom completeness review
- candidate uncovered 行范围必须接受 semantic review
- document 没有 atom candidate，但可能包含有意义的 product/system obligation
- 缺少 local context 时无法判断 duplicate/ownership conflict
- broad atom 看起来覆盖 page/object/flow section，但没有分解 obligation
- path/name/Phase 2 trace 不足以证明 non-source 或 reference-only classification 合理

对 UI、object/component、flow、interaction、state、fixture、scenario、verification 和 design-system document，targeted semantic reading 必须覆盖 obligation-bearing section，而不只是 Phase 2 范围之外的行。

## 审计工作流

按以下顺序评估：

1. 确认每份 `read-full` manifest source document 都恰好在 `phase-works/phase-2/source-obligation-atoms/work-queue.md` 中出现一次，并有一个 canonical extraction owner。
2. 确认每份 `read-full` manifest source document 都有一个 Phase 2 source atom file。
3. 只将 `work-queue.md` 视为 scheduling trace；不得把其 batching rationale、document name、path、role 或 line count 用作 coverage evidence。
4. 提取每个 Phase 2 atom candidate 的 source document、source-local atom ID、行范围、atom type、source fact、normativity、candidate status、candidate artifact projection、candidate owner Change、candidate target Capability、rationale 和 artifact origin。
5. 运行 `scripts/phase3_line_range_audit.py` 或等效 Phase 3 code，机械解析 Phase 2 source atom 范围、规范化并合并行范围、列出 candidate uncovered interval 和 overlap。该 output 不是 semantic decision；`line-ranges[]` 是唯一 canonical line evidence，不再校验冗余 `lines` 字符串格式。
6. 跨已提取 atom 建立 semantic duplicate review。同一 source document/range、等价 source fact 或等价 state/action/verification obligation 在完成 review 前都属于 duplicate candidate。duplicate 是 Phase 3 finding，不要求 Phase 2 预判。
7. 如果一个 Phase 2 行覆盖多个 mandatory UI/flow/data/verification obligation，拆分 broad atom。每个 split atom 必须保留 source evidence 和 source-local origin 或 Phase 3 missing-atom finding ID。
8. 建立 `change-capability-anchors/obligation-atom-index.json`：每项 production obligation 对应一个 global atom；每个 global atom 具有一个规范化 artifact projection、一个 candidate owner Change/status，以及规范化 capability impact/target/related field。
9. 从 canonical global atom trace sidecar 渲染 `change-capability-anchors/obligation-atom-index.md`。
10. 写入 `phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json`，将每个 Phase 2 atom 行恰好映射到一个 global atom ID、relation、non-direct status 或 blocker，再从 JSON 渲染 `source-to-global-atom-map.md`。
11. 写入 `phase-works/phase-3/phase-3-trace/duplicate-ownership-review.md`，保留所有纳入考虑的 duplicate、broad-atom、overlap 和 ownership candidate 及其 resolution。
12. 写入 final global review 前，为 manifest 中每份 source document 创建或更新匹配的 `phase-works/phase-3/source-doc-coverage/<source>.coverage.md` file。
13. 对每份 source document 检查 obligation-bearing section 并验证 atom completeness：
    - page/object：page role、route、entry、exit、具有 behavior impact 的 layout constraint、每个具名 state、state trigger、display、primary action、disabled action、recovery、interaction rule、object dependency、定义行为的 action label、acceptance criterion、responsive behavior 和 non-goal。
    - flow/state/system doc：lifecycle stage、allowed transition、overlay/blocking rule、fixture field、scenario ID、verification matrix row、interaction outcome 和 preserve boundary。
    - architecture/product doc：data fact、access/privacy rule、runtime/deployment requirement、background execution rule、external integration boundary、failure/recovery rule、observability/audit rule 和 verification requirement。
14. 识别位于所有 Phase 2 atom 范围之外的 source range，并利用 section inventory 定位 Phase 2 的 non-atom disposition。阅读这些 candidate range 及必要 local context 并分类：
    - 忽略 blank line、table separator、decorative separator、生成的 table-of-contents 行和纯 formatting
    - 忽略 background prose、重复 summary、discarded option 和纯 explanatory text；但如果定义了 production behavior、boundary、data fact、verification obligation、deployment requirement、auth/privacy rule、failure path 或 preserve constraint，则不得忽略
    - 将剩余每项有意义的 uncovered source obligation 记录为 missing atom；足够精确时加入 global index
15. 写入 canonical `phase-works/phase-3/phase-3-trace/source-remainder-review.json`，列出每个已 review 的 candidate remaining source range、发现方式、read scope、semantic classification、是否包含 production obligation 以及产生的 atom/status/finding，再从 JSON 渲染 `source-remainder-review.md`。JSON sidecar 必须包含 `audit-documents[]`，为每份 `read-full` source document 保存 mechanical recompute 得到的 evidence range 和 candidate uncovered range；还必须包含覆盖每个 candidate uncovered range 的 `rows[]`。较大的 semantic review 行可以覆盖较小 uncovered range，但任何 candidate uncovered range 都不得缺少 review 行。
16. 识别无法在缺少 source-window grounding 和 plan refit 时解决 candidate owner Change 或 spec target/impact 的 atom。将 Change placement 标为 `phase-5-refit-required` 和/或将 capability impact 标为具有 rationale 的 `unresolved`，不得强制放入 Phase 1 framework。
17. 写入 `phase-works/phase-3/phase-3-trace/atom-normalization-decision-log.md`，保留纳入考虑的每项 candidate finding、对应 decision，以及是否必须由 Phase 5 解决 final placement。
18. 建立紧凑 global statistic，覆盖 source document、global atom、有意义的 missing atom、duplicate finding、broad-atom split finding、non-coverage classification、Change-ownership ambiguity、capability-impact/target uncertainty、gap 和 conflict。
19. 按照 `references/trace-sidecar-contract.md` 写入 `trace/phase-3.trace.json`，其中包含 canonical source remainder review path。
20. 分别运行 `scripts/render_source_aligned_orchestrate.py --artifact phase3-global-index --write`、`--artifact phase3-source-map --write` 和 `--artifact phase3-remainder-review --write`，确保 Phase 3 JSON-backed Markdown mirror 为最新版本；不得用 `all-supported` 重渲染 frozen Phase 2 evidence 或 Phase 5 output。
21. 返回 main agent，由其按 trace contract 和 reviewer/repair loop 验证 Phase 3；`rendered-markdown-drift` 只能通过修复 JSON 或重新渲染解决。
22. 决定 coverage normalization 已完成还是 blocked。

## 必需表格

`phase-works/phase-3/source-doc-manifest.md` 必须包含：

| Source Document | Classification | Phase 2 Atom File | Review File | Effective Atom Ranges | Missing Obligation Atom Ranges | Non-Atom Ranges | Read Scope | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

每个 `phase-works/phase-3/source-doc-coverage/<source>.coverage.md` file 必须包含：

### 来源文档

- 来源文档路径
- classification 分类
- total line（如已知）
- 该 file 是否在 Phase 2 完整阅读，以及 Phase 3 是否执行 targeted reread

### 有效 atom 覆盖

| Global Atom ID | Source Atom Origins | Lines | Atom Type | Coverage Status | Artifact Projection | Candidate / Owner Change | Capability Impact | Target Capability | Related Capabilities | Source Fact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 来源义务覆盖

| Source Section or Range | Expected Atom Type | Global Atom IDs | Coverage Judgment | Reason |
| --- | --- | --- | --- | --- |

### non-atom range 审阅

| Candidate Range | Read Scope | Semantic Classification | Production Obligation? | Reason |
| --- | --- | --- | --- | --- |

### 重复项与所有权审阅

| Source Ranges or Atoms | Candidate Duplicate/Conflict | Resolution | Global Atom ID or Relation | Review Judgment |
| --- | --- | --- | --- | --- |

### 文档判断

- missing obligation atom，或 `None`
- duplicate direct atom，或 `None`
- broad-atom split finding，或 `None`
- 使用的 non-coverage status
- Phase 5 placement finding，或 `None`
- Judgment：`covered`、`covered-by-classification`、`phase-5-refit-required` 或 `blocked`

canonical `phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json` 必须为每个 Phase 2 atom 行提供一行。其 rendered Markdown mirror 使用以下 table：

| Source Document | Source Atom ID | Lines | Candidate Status | Candidate Artifact Projection | Candidate Owner Change | Candidate Target Capability | Global Atom ID | Global Relation | Global Capability Impact | Global Target Capability | Global Related Capabilities | Non-Coverage Status | Blocker | Review Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

canonical `phase-works/phase-3/phase-3-trace/source-remainder-review.json` 必须以 machine-readable form 包含同一 semantic review。其 rendered Markdown mirror 包含 audit document 和 semantic review 行：

| Source Document | Lines | How Found | Read Scope | Semantic Classification | Production Obligation | Linked Global Atom IDs | Non-Coverage Status | Blocker | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

JSON sidecar field：

- `audit-documents[]`：每份 Phase 1 `read-full` source document 一行，包含 `source-document`、`source-sha256`、`line-count`、`evidence-ranges[]` 和 `candidate-uncovered-ranges[]`。
- `rows[]`：每个已 review remainder range 一行，包含 `source-document`、`lines`、`line-ranges[]`、`how-found`、`read-scope`、`semantic-classification`、`production-obligation`、`linked-global-atom-ids[]`、`non-coverage-status`、`blocker` 和 `reason`。

validator gate：

- 每个 mechanically candidate uncovered range 必须至少由一个 `rows[]` review range 覆盖。
- production-obligation 行必须关联至少一个已知 `GA-####`，或记录 blocker。
- non-production 行必须记录 non-coverage status 或 blocker。
- 任一 remainder 行存在 blocker 时，`Decision: coverage-complete` 无效。

`phase-works/phase-3/phase-3-trace/duplicate-ownership-review.md` 必须包含：

| Candidate ID | Source Ranges or Source Atoms | Candidate Type | Equivalent Obligation? | Resolution | Global Atom ID or Relation | Phase 5 Placement Needed? | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

`phase-works/phase-3/phase-3-trace/atom-normalization-decision-log.md` 必须包含：

| Review Item | Finding Class | Input Evidence | Decision | Output Artifact | Phase 5 Needed? | Reason |
| --- | --- | --- | --- | --- | --- | --- |

`phase-works/phase-3/coverage-review.md` 必须包含：

| Source Document | Review File | Atom Coverage Summary | Missing Obligation Atoms | Duplicate/Ownership Findings | Non-Atom Ranges | Read Scope | Review Judgment |
| --- | --- | --- | --- | --- | --- | --- | --- |

还必须包含：

| Metric | Value | Evidence | Interpretation |
| --- | --- | --- | --- |

以及 Phase 5 refit handoff table：

| Handoff Item | Source Ranges or Atoms | Current Candidate Owners | Current Artifact Projection | Why Phase 5 Must Decide | Required Plan Refit Consideration |
| --- | --- | --- | --- | --- | --- |

## Decision 值

`phase-works/phase-3/coverage-review.md` 末尾必须且只能包含一个 decision：

- `Decision: coverage-complete`
- `Decision: blocked`

只有满足以下条件时才使用 `coverage-complete`：指定根目录下每份 source document 都已完成 manifest classification；每项具有生产意义的 source obligation 都恰好有一个 global atom 或合理的 non-coverage status；每个没有 atom 的 source range 都在 `source-remainder-review.json` 中分类为 production-safe non-atom content；不存在 unclassified atom、unresolved duplicate obligation、未拆分或未合理说明的 broad atom compression finding、blocking conflict；每个 Phase 5 placement question 都显式 handoff。每个 global 行还必须满足 v2 Capability field structure：direct spec 行在具备可信 baseline evidence 时可使用 `new` / `modified`，否则使用具有 rationale 的 `unresolved`；direct design/verification 行使用 `none` / `none`，related Capability array 唯一、source-explicit、已声明且 non-owning。Capability impact unresolved 不阻碍 source coverage closure，但必须显式 handoff 给 Phase 5。

此外，只有 `phase-works/phase-3/source-doc-manifest.md` 中列出的每份 source document 都有匹配的 `phase-works/phase-3/source-doc-coverage/<source>.coverage.md` file，且包括 `source-remainder-review.json` 在内的所有 Phase 3 trace file 均存在并与 final review 一致时，才能使用 `coverage-complete`。

`coverage-review.md` 和 `phase-3-agent-report.md` 是必需 interface artifact。JSON sidecar 仍是 canonical validator input；Markdown file 是面向 reviewer 的 mirror，不得替代 canonical JSON。

当 source document 冲突、source root 不完整、source atom file 缺失、atom evidence 过宽而无法规范化，或 coverage 闭合前必须由用户决定 boundary 时，使用 `blocked`。

## 最终报告

`phase-works/phase-3/phase-3-agent-report.md` 必须概括：

- 已分类的 source document
- 已写入的 per-source-document review file
- 已写入的 Phase 3 trace file
- 已建立 index 的 global obligation atom
- 由 atom 覆盖的 source document
- 已添加的 missing obligation atom，或确认没有剩余项
- 分类为 non-atom content 的 source range
- duplicate 和 Change-ownership finding
- 已拆分或已合理说明的 broad atom
- non-coverage 分类
- artifact projection distribution、capability-impact distribution、target/related-Capability review，以及任何 unresolved spec-target uncertainty
- Phase 5 placement 交接
- 已解决或剩余 conflict
- 确认指定根目录下每项具有生产意义的 obligation 都由唯一 global atom 覆盖或得到合理说明
- 确认未使用 raw helper output 作为 gate
- 确认任何 line-range helper output（如使用）仅作为 mechanical candidate input
- 确认每项 Phase 3 artifact 都通过 Artifact Language Gate

final agent reply 应简短并使用中文，包含 decision、changed file、missing atom、duplicate/ownership finding、language-gate result、remaining blocker，以及是否可以继续 Phase 4 source-window grounding。
