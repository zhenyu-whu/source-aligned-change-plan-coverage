# trace sidecar contract 规范

本文件是 `source-aligned-change-plan-coverage` 的强制 trace sidecar 协议。进入该 workflow 前必须读取。JSON trace sidecar 是 validator 的唯一 canonical 输入；renderer-backed Markdown artifact 只是从 JSON 机械生成的中文 reviewer 可读镜像，不作为 validator 的权威数据源。

## 全局规则

- trace contract version 为 `source-aligned-trace-v2`。
- 所有 JSON key 必须使用 kebab-case。
- 所有 ID 字段不得包含 Markdown 反引号。
- 多 ID 字段必须使用数组，不得使用逗号字符串。
- `line-ranges: [{"start": 1, "end": 2}]` 是 canonical line evidence。Phase 2 source atom v3 与 Phase 3 source-to-global map v3 不得重复保存 `lines` 字符串；renderer 从 `line-ranges[]` 生成 Markdown `Lines`。其他仍采用既有 schema 的 artifact 按各自数据模型处理。
- 每个 trace JSON 必须包含 `trace-schema` 和 `trace-contract-version`。
- Renderer-backed Markdown mirror 可包含中文解释，但必须由 canonical JSON 重新渲染得到，不得手工修补 canonical 字段。
- render contract version 为 `source-aligned-render-v3`。
- 当前契约不兼容旧 Phase 1 plan trace、旧 Phase 2 extraction/trace shape 或旧 Capability owner 字段。canonical artifact 集合中若出现 `source-aligned-phase-1-trace-v1`、`source-aligned-phase-2-trace-v1`、`source-aligned-source-atoms-v1`、`source-aligned-source-atoms-v2`、`source-aligned-source-to-global-map-v1`、`source-aligned-source-to-global-map-v2`、`source-aligned-global-atom-index-v1`、`source-aligned-atom-plan-mapping-v1`、`source-aligned-final-packet-index-v1`、`source-aligned-render-v1` 或 `source-aligned-render-v2`，必须拒绝。

## 必需布局

```text
openspec/orchestrate/
├── change-plan.md                 # Phase 5 accepted/adjusted 后发布
├── trace/
│   ├── manifest.json
│   ├── phase-1.trace.json
│   ├── phase-2.trace.json
│   ├── phase-3.trace.json
│   ├── phase-4.trace.json
│   └── phase-5.trace.json
├── change-capability-anchors/
│   ├── obligation-atom-index.md
│   └── obligation-atom-index.json
└── phase-works/
    ├── phase-1/
    │   ├── initial-change-plan.md
    │   ├── source-doc-manifest.md
    │   └── phase-1-agent-report.md
    ├── phase-2/source-obligation-atoms/<source>.atoms.md
    ├── phase-2/source-obligation-atoms/<source>.atoms.json
    ├── phase-3/phase-3-trace/source-to-global-atom-map.md
    ├── phase-3/phase-3-trace/source-to-global-atom-map.json
    ├── phase-3/phase-3-trace/source-remainder-review.md
    ├── phase-3/phase-3-trace/source-remainder-review.json
    ├── phase-4/
    │   ├── input-change-plan.md
    │   └── source-window-dossiers/source-window-index.json
    └── phase-5/
        ├── input-change-plan.md       # accepted/adjusted only
        ├── change-plan.md             # accepted/adjusted only
        ├── source-window-refit-trace.md
        ├── atom-plan-mapping.md      # accepted/adjusted only
        ├── atom-plan-mapping.json    # accepted/adjusted only
        ├── capability-baseline-reconciliation.md # accepted/adjusted only
        ├── capability-baseline-reconciliation.json # accepted/adjusted only
        └── final-packet-index.json   # accepted/adjusted only
```

## manifest 规范

`trace/manifest.json` 的 schema 为 `source-aligned-orchestrate-manifest-v1`。

Manifest lifecycle 如下：

1. 初始化 orchestration 目录时，创建或刷新 `trace/manifest.json` 作为 skeleton manifest。尚无 trace sidecar 的 Phase 使用 `missing`。每个当前存在的 canonical JSON sidecar 必须恰好对应一个 artifact 行；不得遗漏、重复或列出不存在的 `trace-path`。
2. 每次运行 `validate_source_aligned_orchestrate.py --phase ...` 前刷新 `trace/manifest.json`，确保列出的每个 artifact 行都保存其 JSON `trace-path` 的当前 sha256。
3. validator 和 independent reviewer 通过后再次刷新 `trace/manifest.json`，让 `phase-statuses` 记录 trace sidecar 中 canonical Phase `status` 或 `decision`。不得把 reviewer-loop bookkeeping value 用作 Phase decision。

必需字段：

- `trace-schema`
- `trace-contract-version`
- `orchestrate-dir`
- `phase-statuses`
- `artifacts[]`

`phase-statuses` 记录 Phase trace sidecar 中的 canonical Phase decision，而不是 reviewer-loop workflow state。它必须包含 `phase-1` 至 `phase-5`；没有 trace sidecar 的 Phase 使用 `missing`。Phase 1 和 Phase 2 使用 `trace/phase-1.trace.json`、`trace/phase-2.trace.json` 的 `status`；Phase 3、Phase 4 和 Phase 5 使用相应 Phase trace 的 `decision` 或 `status`。Phase trace sidecar 一旦存在，就必须包含 canonical `status` 或 `decision`，且 `phase-statuses.phase-n` 必须与其完全一致。存在 `trace/phase-5.trace.json.status` 时，`phase-statuses.phase-5` 必须与其相同。proposal-ready handoff 要求两者都为 `accepted` 或 `adjusted`；不得把 `reviewer-passed`、`validator-passed`、`repair-not-needed`、`present` 或其他 workflow/status bookkeeping 写入任何 `phase-statuses` 值。

每个 artifact 行必须包含：

- `artifact-path`
- `trace-path`
- `trace-schema`
- `sha256`
- `phase`
- `role`

`sha256` 根据 `trace-path` 指向的 JSON trace file 计算。刷新 manifest 时，`artifacts[]` 只能列出 `trace-path` 已存在的行，并必须覆盖当前存在的 Phase trace、Phase 2 source atom JSON、Phase 3 global/map/remainder JSON、Phase 4 source-window index JSON 和 Phase 5 terminal mapping/index JSON。`trace-schema`、`phase` 和 canonical JSON 内的 schema 必须一致。

## renderer contract

renderer-backed mirror 使用 `source-aligned-render-v3`，通过以下命令生成：

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact all-supported \
  --write
```

支持的 mirror 包括 Phase 2 `<source>.atoms.md`，Phase 3 `obligation-atom-index.md`、`source-to-global-atom-map.md`、`source-remainder-review.md`，以及 Phase 5 `atom-plan-mapping.md`。

单独执行 Phase 2 时必须使用 `--artifact phase2-source-atoms`；`all-supported` 仅用于明确需要刷新当前已存在的全部 mirror 时，不得在 Phase 2 恢复/repair 中越权重渲染 Phase 3–5 artifact。

每个 rendered mirror 末尾都包含 `Trace Appendix`，列出 trace file、trace schema、trace sha256 和 render contract version。validator 会比较实际 Markdown 与 renderer output。如果报告 `rendered-markdown-drift`，repair 必须更新 canonical JSON sidecar 或重新运行 renderer；不得只手工编辑 Markdown。

## Phase schema

Phase trace schema：

- `source-aligned-phase-1-trace-v2`
- `source-aligned-phase-2-trace-v2`
- `source-aligned-phase-3-trace-v1`
- `source-aligned-phase-4-trace-v1`
- `source-aligned-phase-5-trace-v1`

artifact schema：

- `source-aligned-source-atoms-v3`
- `source-aligned-global-atom-index-v2`
- `source-aligned-source-to-global-map-v3`
- `source-aligned-source-remainder-review-v1`
- `source-aligned-source-window-index-v1`
- `source-aligned-atom-plan-mapping-v2`
- `source-aligned-final-packet-index-v2`

Phase 2 source atom 与 Phase 3 source map 必须整体采用 v3；Phase 2 trace、global index、atom-plan mapping 与 final packet index 采用 v2。Phase 3–5 trace、`manifest`、source remainder review 和 source window index 继续使用各自现有的 `*-v1` schema 名称，但其 `trace-contract-version` 必须是 `source-aligned-trace-v2`。

## 必需数据模型

Phase 1 trace：

- `status`：必须为 `initial-plan-written`
- `source-documents[]`: `source-document`, `read-status`, `source-role`, `coarse-topics-paths`, `notes`, `line-count`, `source-sha256`
- `initial-change-plan`: `artifact-path`, `sha256`
- `initial-change-plan.artifact-path` 必须为 `openspec/orchestrate/phase-works/phase-1/initial-change-plan.md`。
- Phase 1 trace 不得包含 `change-plan`、`phase-plan-path`、`phase-plan-sha256`、`root-plan-path` 或 `root-plan-sha256` 等旧字段。

Phase 2 trace：

- `status`：必须为 `source-atoms-written`
- `work-queue-path`
- `sources[]`：每份 source 一行，包含 `source-document`、`atom-json-path`、`atom-json-sha256`、`atom-markdown-path`、`canonical-owner`、`read-status`、`inventory-section-count`、`atom-count` 和 string array `blockers[]`
- `phase-report-path`

Phase 2 source atom sidecar：

- 顶层字段：`source-document`、`source-sha256`、`read-status`、`canonical-owner`、`source-role`、`phase-1-candidate-changes-capabilities-considered`、`section-inventory[]`、`source-atoms[]`、`blockers[]`、`language-self-check`。
- `phase-1-candidate-changes-capabilities-considered` 是 object array；每项为 `change`、`capabilities[]` 和中文 `note`。`blockers[]` 是中文 string array；`language-self-check` 是非空中文 string。
- `section-inventory[]`：`source-section`、`line-ranges[]`、`production-meaning`、`atom-ids[]`、`non-atom-classification`、`reason`。`production-meaning` 只允许 `obligation-bearing | contextual | explicit-non-goal | conflict | unclear | reference-only | prototype-only | background | formatting | superseded`；其范围合集必须覆盖 source 的每一物理行，meaningful row 必须关联 atom 或 blocker。
- `source-atoms[]` 只包含：`source-atom-id`、`line-ranges[]`、`atom-type`、`source-fact`、`normativity`、`candidate-status`、`candidate-artifact-projection`、`candidate-owner-change`、`candidate-target-capability`、`rationale`。
- `candidate-status` 只允许 `direct-candidate | unassigned | contextual-candidate | unresolved-conflict | unclassified`。guard/non-goal 语义由 `atom-type: scope-guard`、`normativity: must-not` 和 `candidate-artifact-projection: spec-guard` 表达；Phase 2 禁止 `duplicate-candidate`、`candidate-new-change` 和 `candidate-new-capability`。
- `non-atom-classification` 只允许 `none | reference-only | prototype-only-not-production | background-only | formatting-only | superseded | mechanical-repeat | no-product-or-system-impact`；没有 atom 的 inventory row 不得使用 `none`。
- `candidate-target-capability` 只映射现有 Phase 1 Capability，或使用 `unresolved` / `none`；Phase 2 不记录 Capability impact、related Capability、role、propose use 或 evidence need。
- Phase 2 不使用 `source-anchors[]`。atom 的 `line-ranges[]` 提供直接 evidence，section inventory 提供全文 disposition evidence。

Phase 3：

- `obligation-atom-index.json`：`global-atoms[]` 包含精确 `GA-####`、source field、status、projection、owner Change、`capability-impact`、`target-capability`、`related-capabilities[]`、relation、`origins[]` 和 `line-ranges[]`；不得输出 `owner-capability`
- `source-to-global-atom-map.json`：每个 Phase 2 atom 行对应一行，保留 Phase 2 的 candidate status/projection/owner/target，并增加规范化 `global-capability-impact`、`global-target-capability`、`global-related-capabilities[]`；mapping outcome 必须且只能是 `global-atom-id`、`global-relation`、`non-coverage-status` 或 `blocker` 之一
- `source-remainder-review.json`：使用 `audit-documents[]` 和 `rows[]` 保存 mechanical Phase 2 atom line coverage，以及对每个 candidate uncovered source range 的 semantic review
  - 每个 `audit-documents[]` 行包含 `source-document`、`source-sha256`、`line-count`、`evidence-ranges[]` 和 `candidate-uncovered-ranges[]`
  - 每个 `rows[]` 行包含 `source-document`、`lines`、`line-ranges[]`、`how-found`、`read-scope`、`semantic-classification`、`production-obligation`、`linked-global-atom-ids[]`、`non-coverage-status`、`blocker` 和 `reason`
- `phase-3.trace.json`：包含 source classification、review path、normalization decision、remainder review path 和 decision value

Phase 3 在全局规范化时新增 `capability-impact`、`target-capability` 和 `related-capabilities[]`。direct spec 行只有在具备可信 repository baseline evidence 时使用 `new | modified`，否则使用具有 rationale 的 `unresolved`；普通 direct design/verification 行和 non-direct 行使用 `none` / `none`。`related-capabilities[]` 不具有 ownership，也不代表 progression。

Phase 4：

- `source-window-index.json`: `windows[]`, `semantic-profiles[]`, `grounding-issues[]`, `status`
- 每个 window 行必须包含 `window-id`、`input-unit`、`unit-type`、`source-document`、`line-ranges[]`、`context-line-ranges[]`、`linked-global-atom-ids[]`、`dossier-path`、`source-sha256` 和 `window-text-sha256`

Phase 5：

- `atom-plan-mapping.json`：`accepted` 或 `adjusted` 时必需；每个 global atom 一行，包含 final owner type/Change/projection/relation、`final-capability-impact`、`final-target-capability`、`related-capabilities[]`、decision 和 reason。executable direct 行使用 `final-owner-type: executable-change` 和恰好一个 `final-owner-change`；不得输出 `final-owner-capability` 或 `capability-advancement`。
- `final-packet-index.json`：`accepted` 或 `adjusted` 时必需；每个 executable planned Change 包含 direct atom ID、owner-scoped non-direct atom ID、从显式 mapping impact/target pair 派生的 Capability view path、packet path、packet digest 和 `change-kind`。`change-kind` 必须为 `foundation` 或 `business`；最多允许一个 foundation packet，且必须是第一个 packet。zero-business-Capability plan 不生成 business Capability view path；Phase 5 refit config 可以使用 `capabilities: []`。
- `capability-baseline-reconciliation.json`：schema 为 `source-aligned-capability-baseline-v1`，是 baseline reconciliation 的 canonical authority；包含 `repository-specs-root` 和 `capabilities[]`。每个被 final business spec atom 直接推进的 Capability 恰好一行，记录 `capability`、`baseline-status: existing | absent`、`spec-path`、`spec-sha256`、`baseline-evidence`、`first-planned-advancement`、`required-first-relation` 和 `later-relation-rule`。匹配 Markdown 必须由 JSON 渲染；该 sidecar 只拥有 repository identity/existence evidence，不是 production obligation authority。
- `phase-5.trace.json`：包含 final status、atom-plan mapping path、final packet index path、`capability-baseline-reconciliation-path`、`capability-baseline-reconciliation-sha256`、complexity summary、Capability progression summary 和 reviewer/validator gate outcome
- `accepted` 或 `adjusted` 时，`phase-works/phase-5/change-plan.md` 与根 `change-plan.md` 必须逐字节一致；`phase-works/phase-5/input-change-plan.md` 必须与 Phase 4 input snapshot 逐字节一致。
- `needs-coverage-recheck` 或 `blocked` 时不得发布根 `change-plan.md`。

Phase 5 Capability field 规则：

- `final-capability-impact`: `new | modified | none | foundation-substrate`；`accepted | adjusted` 中禁止 `unresolved`。
- `new | modified` 仅允许 direct `spec-requirement | spec-guard`，并要求具体 `final-target-capability`；`none` 要求 target `none`，普通 direct `design-obligation | verification-obligation` 必须使用 `none` / `none`。
- Foundation 是唯一例外：direct foundation row 使用 `final-capability-impact: foundation-substrate`、`final-target-capability: runtime-substrate-foundation`，生成专用 view 但不计入 business progression；其 related 数组仍遵循通用非 owning 规则。
- 同一 `(final-owner-change, final-target-capability)` 的 spec rows impact 必须一致。`existing` baseline 的 relation sequence 必须为 `modified+`；`absent` baseline 必须为 `new, modified*`，且后续 `modified` 依赖前序 Change 先 sync/archive。同一 target 最多一个 `new`，若存在必须是首次 advancement。Renderer 只验证并呈现，不得从顺序猜测。
- `related-capabilities[]` 必须是唯一的合法 kebab-case capability id、指向已声明的 Capability、source-explicit、与 target 不相同；不得产生 ownership、progression、capability view 或 advanced-capability complexity count。Validator 只检查数组结构、唯一性、ID 格式和不等于 target；独立 reviewer 审核 Capability 是否已声明以及 source-explicit 语义。

## validator 命令

每个 Phase 结束后运行：

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/validate_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --phase phase-<n> \
  --json
```

handoff 给 `openspec-propose` 前运行：

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/validate_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --phase all \
  --complete \
  --json
```

如果 reviewer 希望将零 warning 输出设为 hard gate，使用 `--strict-warnings`。
