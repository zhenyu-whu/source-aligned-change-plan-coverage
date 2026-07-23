# Trace Sidecar Contract v7

本技能采用Phase-specific authority、独立final-roadmap authority与workflow completion commit marker。JSON用于精确校验、检索和跨artifact映射；Markdown是否为authority由本文件明确规定。

## 全局版本

- Trace contract：`source-aligned-trace-v7`
- Render contract：`source-aligned-render-v11`
- JSON key使用kebab-case；ID不含Markdown反引号；多ID使用array。
- Canonical line evidence为`line-ranges: [{"start":1,"end":2}]`。
- 所有JSON path字段为workspace/repository root-relative lexical path，不得使用绝对路径、orchestrate-relative短路径或symlink。
- Row hash统一为compact sorted UTF-8 JSON SHA256。

旧generation规则：

- `source-aligned-trace-v6`及更早generation只读保留；
- v7 validator、renderer、helper和resume必须拒绝legacy generation；
- 不提供migration、relabel或in-place upgrade；
- 在非空legacy output root上不得自动删除、覆盖、归档或初始化v7。

## Authority 表

| Phase/Workflow | 内容权威 | Mirror/派生 |
| --- | --- | --- |
| Phase 1 | `initial-framework.json` | `initial-change-plan.md`、Phase 1 trace中的source、双artifact digest与review gate |
| Phase 2 | provisional source atom JSON v6 | atom Markdown、index |
| Phase 3 | global index JSON、coverage review JSON v3 | Markdown、freeze gate |
| Phase 4 | deterministic neutral collection Markdown | evidence collection index v3 |
| Phase 5 boundary | framework refit JSON v5 | plan-refit-review Markdown |
| Phase 5 roadmap | final-roadmap JSON v1 | final `change-plan.md` |
| Phase 5 mapping | terminal mapping JSON v5 | mapping Markdown、baseline、public handoff |
| Integration | final integration review JSON v1 | deterministic review Markdown |
| Workflow | one-shot attempt/result v1、workflow completion trace v1 | 无第二份completion authority |

Work queue、agent report、Phase 1/3/5 reviewer/repair report是noncanonical，不进入manifest。Final integration review JSON、one-shot attempt/result与workflow completion trace是canonical；合法completion发布后的final manifest登记这四项workflow authority。

## 必需布局

```text
<orchestrate-root>/
├── change-plan.md
├── final-integration-review.json|md
├── trace/
│   ├── manifest.json
│   ├── phase-1.trace.json ... phase-5.trace.json
│   ├── final-integration-review-attempt.trace.json
│   ├── final-integration-review-attempt-result.trace.json
│   └── workflow-completion.trace.json
├── change-capability-anchors/
│   ├── obligation-atom-index.json|md
│   ├── index.md
│   └── <change>/
│       ├── change-source.md
│       └── capability-slices/<capability>.md
└── phase-works/
    ├── phase-1/
    │   ├── initial-framework.json
    │   ├── initial-change-plan.md
    │   ├── source-doc-manifest.md
    │   └── phase-1-*.md
    ├── phase-2/...
    ├── phase-3/...
    ├── phase-4/
    │   └── source-evidence-collections/
    │       ├── evidence-collection-index.json
    │       ├── index.md
    │       ├── all-evidence.md
    │       ├── by-source/<source-key>.md
    │       └── delivery-directives.md
    └── phase-5/
        ├── framework-refit-trace.json
        ├── plan-refit-review.md
        ├── final-roadmap.json
        ├── change-plan.md
        ├── atom-plan-mapping.json|md
        ├── capability-baseline-reconciliation.json|md
        ├── final-packet-index.json
        ├── phase-5-agent-report.md
        ├── phase-5-reviewer-report.md
        └── phase-5-repair-report.md
```

V7 exact surface禁止Phase 4 initial Change/Capability bucket目录、unassigned-and-gap collection、patch request、checkpoint、incremental/targeted artifact和legacy integration Markdown-only authority。

Phase 1目录必须包含`initial-framework.json`、由其确定性生成的`initial-change-plan.md`、`source-doc-manifest.md`及流程报告。JSON authority与Phase 1 trace进入manifest；Markdown mirror和report不进入manifest。

## Schema 目录

Phase/control：

- `source-aligned-orchestrate-manifest-v3`
- `source-aligned-phase-1-trace-v4`
- `source-aligned-phase-2-trace-v6`
- `source-aligned-phase-3-trace-v5`
- `source-aligned-phase-4-trace-v6`
- `source-aligned-phase-5-trace-v6`
- `source-aligned-final-integration-review-v1`
- `source-aligned-workflow-completion-v1`

Artifact：

- `source-aligned-source-atoms-v6`
- `source-aligned-global-atom-index-v4`
- `source-aligned-phase-3-coverage-review-v3`
- `source-aligned-evidence-collection-index-v3`
- `source-aligned-framework-refit-trace-v5`
- `source-aligned-final-roadmap-v1`
- `source-aligned-atom-plan-mapping-v5`
- `source-aligned-capability-baseline-v2`
- `source-aligned-initial-framework-v1`
- `source-aligned-final-packet-index-v3`

每个新generation JSON的`trace-contract-version`必须精确为`source-aligned-trace-v7`。

## Manifest v3

`trace/manifest.json`使用`source-aligned-orchestrate-manifest-v3`，顶层必须且只能包含：

```text
trace-schema
trace-contract-version
authority: control
orchestrate-dir
phase-statuses
workflow-status
artifacts[]
```

`workflow-status`只允许：

- `pending`：generation尚未发布合法completion；
- `integration-passed`：completion trace与passed review均有效；
- `blocked`：任一terminal gate或integration失败。

每个artifact row只含：

```text
json-path
trace-schema
sha256
phase
role
authority
```

Authority只允许：

- `semantic`：Phase 1 initial framework、Phase 2 atoms、Phase 3 index/coverage、Phase 5 refit/final-roadmap/mapping、final integration review；
- `derived`：Phase 4 index、Phase 5 baseline/packet；
- `control`：Phase traces、one-shot final review attempt/result与workflow completion trace。

Markdown不进入manifest。Manifest不自列。合法completion发布后，Final integration review JSON、attempt、attempt result与workflow completion trace必须各自恰好一行。

`initial-framework.json`必须以`phase: phase-1`、`role: initial-framework`、`authority: semantic`登记；`final-roadmap.json`必须以`phase: phase-5`、`role: final-roadmap`、`authority: semantic`登记。对应Phase trace分别以`role: phase-trace`、`authority: control`登记；两个plan Markdown mirror均不登记。

Phase 1–5运行期间`workflow-status`保持`pending`。任何blocked terminal状态将其设为`blocked`。只有合法completion trace发布后才能设为`integration-passed`。

## Initial framework v1

`initial-framework.json`使用`source-aligned-initial-framework-v1`，顶层必须且只能包含：

```text
trace-schema
trace-contract-version
artifact-path
delivery-semantics[]
semantic-landscape[]
capabilities[]
outcome-threads[]
changes[]
dependency-edges[]
guard-links[]
change-order[]
overlay[]
foundation
assumptions[]
conflicts[]
non-goals[]
deferred[]
language-self-check
```

`artifact-path`指向`initial-change-plan.md` mirror。各row的exact shape、枚举与cross-field constraints见Phase 1 task contract，并由`source_aligned_v7_contract.py`校验。

## Phase 1 trace v4

`phase-1.trace.json`顶层必须且只能包含：

```text
trace-schema
trace-contract-version
status
source-documents[]
initial-framework
initial-change-plan
review-gate
```

`initial-framework`与`initial-change-plan`都只含repository-relative `artifact-path`与当前raw-bytes `sha256`；前者绑定JSON semantic authority，后者绑定其deterministic Markdown mirror。

`review-gate`只含：

```text
status: pending|passed|blocked
writer-id
reviews[]
repairs[]
```

Phase 1 trace顶层`status`只允许`review-pending|initial-plan-written|blocked`，并分别与gate的`pending|passed|blocked`一一对应。Writer发布authority与mirror、但尚未取得首轮review时，使用`review-pending`、空reviews与空repairs；manifest在未完成generation中记录同一非terminal状态。Complete workflow仍只接受`initial-plan-written`。

Review row只含：

```text
round
reviewer-id
validator-status
initial-framework-sha256
initial-change-plan-sha256
semantic-checks[]
finding-fingerprints[]
```

`semantic-checks[]`每行只含`check`、`result: passed|failed`，并按Phase 1 contract固定九项完整排列。

Repair row只含：

```text
round
repair-writer-id
finding-fingerprints[]
before-initial-framework-sha256
after-initial-framework-sha256
```

Repair只修改JSON authority；每轮repair后必须从JSON完整重渲染Markdown，再运行validator与fresh review。Review row必须同时绑定当轮JSON与mirror digest；mirror drift、JSON no-op repair、repeated finding或身份复用均阻断。

Pending gate允许0..3条review和0..2条repair：`reviews == repairs`表示等待fresh review，`reviews == repairs + 1`表示等待repair或terminalization。前者非零时最后repair after digest绑定当前JSON，后者最后review双digest绑定当前JSON与mirror；任意两轮review间必须有对应repair。Terminal gate至少一轮review且通常要求`reviews == repairs + 1`；仅blocked terminal no-op repair允许两者等长。第三轮未通过、重复finding或no-op repair强制立即blocked，不得继续维持pending或追加轮次。只有gate passed、最后review validator passed、双digest当前、全部semantic checks passed且findings为空，status才可`initial-plan-written`。

## Phase 2 source atoms v6 与 trace v6

每份atom JSON顶层只含：

```text
trace-schema
trace-contract-version
source-document
source-sha256
read-status
canonical-owner
source-role
phase-1-candidate-changes-capabilities-considered[]
source-atoms[]
blockers[]
language-self-check
```

每个source atom row只含：

```text
source-atom-id
line-ranges[]
atom-type
source-fact
normativity
delivery-directives[]
candidate-status
candidate-artifact-projection
candidate-owner-change
candidate-target-capability
rationale
```

`delivery-directives[]`只允许`milestone-scope|explicit-precedence|explicit-deferred`，唯一并按该固定顺序排列。

成功Phase 2 trace只含既有control字段；每个sources row在v5字段基础上增加`delivery-directive-atom-count`。Blocked trace只含schema、contract、status与非空issues。

Phase 2 preflight检查source、quote/range、directive enum/依据和candidate mapping，不要求terminal trace/manifest/mirror。

## Phase 3 global index v4、coverage v3 与 trace v5

Global index v4 shape保持：

- 顶层`trace-schema`、`trace-contract-version`、`artifact-path`、`global-atoms[]`；
- GA row只含`global-atom-id`与`evidence-ref`。

Coverage review v3顶层只含：

```text
trace-schema
trace-contract-version
artifact-path
documents[]
gap-atoms[]
remainder-dispositions[]
mapping-ambiguities[]
summary
decision
language-self-check
```

Gap row只含：

```text
gap-atom-id
source-document
line-ranges[]
source-fact
atom-type
normativity
delivery-directives[]
review-judgment
```

Document、remainder disposition与mapping ambiguity shape沿用v2。Summary在v2机械计数外增加：

```text
delivery-directive-atoms
delivery-directives:
  milestone-scope
  explicit-precedence
  explicit-deferred
```

Phase 3 trace review row在v4字段基础上增加`delivery-directive-status: passed|failed`。Terminal passed要求最后stage为`phase-3-closure`、双validator passed、directive status passed、findings为空且authority digest当前有效。

Evidence authority digest包含source digest、全部Phase 2 atom JSON、global index与coverage review。Directive作为atom/gap内容进入同一digest。

## Phase 4 neutral collection index v3

Phase 4 assembler生成all-evidence完整中性collection、按source中性视图与directive secondary collection。

Index顶层只含：

```text
trace-schema
trace-contract-version
generated-from[]
rows[]
rendered-artifacts[]
```

每个GA row只含：

```text
global-atom-id
evidence-ref
source-document
rendered-collection-paths[]
```

`rendered-collection-paths[]`固定先列`all-evidence.md`、再列唯一`by-source` path；directive非空时才追加固定`delivery-directives.md` path。空directive时恰好两个path，非空时恰好三个path。

Rendered artifact row只含`artifact-path`、`sha256`、`collection-kind`、`scope`；kind只允许`index|all-evidence|source|delivery-directives`。前三个非source全局surface的scope固定为`all`；source row的scope为对应repository-relative source path。

Phase 4 trace v6 shape保持；全部artifact使用v7 contract。

## Framework refit v5

顶层只含：

```text
trace-schema
trace-contract-version
status
initial-framework-ref
final-roadmap-ref
capability-reviews[]
change-reviews[]
outcome-thread-reviews[]
dependency-edge-reviews[]
guard-link-reviews[]
issues[]
language-self-check
```

`initial-framework-ref`只含Phase 1 `initial-framework.json` path/SHA，不得指向plan mirror。`final-roadmap-ref`在accepted/adjusted时只含final-roadmap path/SHA；blocked时为`null`。

Capability review row只含：

```text
input-capability
decision
final-capabilities[]
initial-gate-results[]
supporting-global-atom-ids[]
reason
```

Change review row只含：

```text
input-change
decision
final-changes[]
initial-gate-results[]
supporting-global-atom-ids[]
reason
```

Capability decision只允许`keep|split|merge|remove|rename`；Change decision只允许`keep|split|merge|remove|rename|scope-adjusted`。每个initial gate row只含`gate`、`result`、`note`、`evidence-ga-ids[]`，Capability/Change分别固定8项。

Outcome thread、dependency edge与guard link review row分别只含：

```text
outcome-thread-id | dependency-id | guard-link-id
result
evidence-ga-ids[]
reason
```

三个array必须按final roadmap中对应array顺序完整覆盖，terminal result必须为`passed`。

Refit不得内嵌final semantic landscape、Capability、outcome thread、Change、dependency edge、guard link、directive resolution、order、prefix、overlay、foundation或mapping。

## Final roadmap v1

顶层只含：

```text
trace-schema
trace-contract-version
artifact-path
semantic-landscape[]
capabilities[]
outcome-threads[]
changes[]
dependency-edges[]
guard-links[]
delivery-directive-resolutions[]
change-order[]
order-decisions[]
prefix-reviews[]
overlay[]
foundation
language-self-check
```

Capability row只含：

```text
capability
purpose
owns
excludes
boundary-rationale
evidence-ga-ids[]
```

Outcome thread row只含：

```text
outcome-thread-id
beneficiary
trigger
observable-result
acceptance-signal
primary
outcome-ga-ids[]
acceptance-ga-ids[]
first-realizing-change
```

Change row只含：

```text
change
intent
scope-in
scope-out
behavior-profile
realizes-outcome-thread-ids[]
usable-postcondition
consumer-closure
independent-archive
split-merge-judgment
outcome-ga-ids[]
acceptance-ga-ids[]
```

Behavior profile只含：

```text
trigger-context
normative-behavior
observable-outcome-invariant
important-exception-error-semantics
acceptance-evidence
```

Consumer closure只含`mode`与`ref`；mode只允许`existing-baseline|foundation-first-outcome|same-change-outcome`。

Dependency edge row只含：

```text
dependency-id
prerequisite-change
dependent-change
kind
contract-id
produced-contract
consumed-contract
counterfactual-failure
co-delivery-rejection
evidence-ga-ids[]
```

Kind只允许`behavior-availability|compatibility-contract|lifecycle-state|safety-invariant`。

Guard link row只含：

```text
guard-link-id
guarding-change
guarded-outcome-thread-id
surface-state
evidence-ga-ids[]
```

Surface state只允许`existing|planned`。

Delivery directive resolution row只含：

```text
global-atom-id
delivery-directive
effect
affected-changes[]
scope-label
ordering-relations[]
reason
```

Effect只允许`defers|no-order-effect|orders|scopes`；每个ordering relation row只含`before-change`与`after-change`。

Order decision row只含：

```text
position
selected-change
eligible-changes[]
selection-basis
supporting-global-atom-ids[]
reason
```

Selection basis只允许`current-baseline-risk-retirement|explicit-source-directive|foundation-first|only-eligible|stable-tie-break|thin-observable-outcome`。

Prefix review row只含：

```text
change
delivered-prefix-outcome
current-prefix-consumption
guard-closure
foundation-like-assessment
result
reason
```

Foundation-like assessment只允许`not-foundation-like|valid-foundation-exception`；result只允许`passed|failed`。

Overlay row只含`change`、`capability`、`capability-impact`。Foundation为`null`或只含`change`、`first-consumer-change`、非空`evidence-ga-ids[]`。

Validator必须检查outcome realization、consumer closure、guard co-delivery、directive pair completeness、typed dependency DAG、eligible set/order decision、prefix cardinality、overlay与foundation一致性。`explicit-precedence/orders`与`explicit-deferred/defers`都必须携带非空ordering relation并进入同一个order graph；`no-order-effect`不得携带relation。

## Terminal mapping v5

顶层只含：

```text
trace-schema
trace-contract-version
artifact-path
rows[]
```

Mapping row沿用exact shape：`global-atom-id`、`evidence-ref`、`final-owner-change`、`final-relation`、`final-artifact-projection`、`final-capability-impact`、`final-target-capability`、`related-capabilities[]`、`reason`。所有owner和target必须存在于同一Phase 5 candidate的final roadmap；绑定由Phase 5 trace、refit refs与validator负责，不在mapping顶层重复roadmap ref。

Mapping不保存dependency、guard allocation、prefix outcome或order reason。

## Capability baseline v2

`capability-baseline-reconciliation.json`使用`source-aligned-capability-baseline-v2`，顶层只含：

```text
trace-schema
trace-contract-version
repository-specs-root
capabilities[]
```

每个Capability row只含`capability`、`baseline-status`、`spec-path`、`spec-sha256`、`baseline-evidence`、`first-planned-advancement`、`required-first-relation`与`later-relation-rule`。

## Phase 5 trace v6 与 bounded gate

Phase 5 review gate只含：

```text
status: pending|passed|blocked
writer-id
reviews[]
repairs[]
```

Review row只含：

```text
round
reviewer-id
validator-status
framework-refit-sha256
final-roadmap-sha256
atom-plan-mapping-sha256
final-change-plan-sha256
frozen-evidence-authority-sha256
phase-3-freeze-trace-sha256
candidate-handoff-sha256
semantic-checks[]
finding-fingerprints[]
```

Semantic checks按review gate固定九项。Repair row只含：

```text
round
repair-writer-id
finding-fingerprints[]
before-terminal-authority-sha256
after-terminal-authority-sha256
```

Phase 5 candidate authority digest对以下七项SHA的compact sorted object计算：

```text
framework-refit-sha256
final-roadmap-sha256
atom-plan-mapping-sha256
final-change-plan-sha256
frozen-evidence-authority-sha256
phase-3-freeze-trace-sha256
candidate-handoff-sha256
```

其中`candidate-handoff-sha256`由helper在私有staging生成完整非trace handoff后计算，输入包含所有预期最终path、文件字节与foundation显式空目录；它覆盖root plan、refit review、mapping mirror、baseline JSON/Markdown、packet、anchor index、全部change-source和全部Capability slice。它不包含terminal trace、manifest或review report，因而无自引用。

`review-pending` trace只含schema、contract、status、四份candidate artifact path/SHA、frozen evidence digest、Phase 3 freeze path/SHA、candidate handoff digest与review-gate，不含`issues`。此时根plan、packet与public source bundle不得存在。Repair后必须通过`--refresh-review-candidate`从相同authority重建完整私有staging，并原子刷新Phase 5 plan/refit-review mirror和全部七项digest；review历史与预算保持不变。

第三轮review只要validator、任一固定semantic check或finding未全部清零，gate就必须立即写成`blocked`；此时`pending`非法。重复finding与no-op repair同样立即强制`blocked`。

Terminal accepted/adjusted trace只含：

```text
trace-schema
trace-contract-version
status
final-change-plan-path / sha256
framework-refit-trace-path / sha256
plan-refit-review-path / sha256
final-roadmap-path / sha256
atom-plan-mapping-path / sha256
capability-baseline-reconciliation-path / sha256
final-packet-index-path / sha256
frozen-evidence-authority-sha256
phase-3-freeze-trace-path / sha256
candidate-handoff-sha256
review-gate
```

Blocked trace有且只有两种互斥shape：

- `block-kind: framework-refit`：用于refit在进入bounded review前失败。它只含schema、contract、status/block-kind、framework-refit ref、plan-refit-review ref与和refit逐字一致的非空`issues`，不含review-gate或candidate refs。
- `block-kind: bounded-review`：用于accepted/adjusted refit进入bounded review后失败。它只含schema、contract、status/block-kind、四份candidate artifact path/SHA、frozen evidence digest、Phase 3 freeze path/SHA、candidate handoff digest、完整`status: blocked` review-gate与由最后一轮validator/check/finding确定性派生的非空`issues`，不含plan-refit-review或任何terminal handoff ref。

两种blocked都只能由`--write`在不存在terminal/public surface时原子终结；失败必须回滚。Framework-refit block不得留下final roadmap、mapping或candidate plan。Bounded-review block保留四份candidate artifact与三项绑定digest作为私有诊断证据，但绝不发布、删除或覆盖根plan、packet、public source bundle、integration review、workflow completion或terminal manifest；已经blocked的generation不可重试覆盖。

## Final packet v3

Packet shape保持：

```text
trace-schema
trace-contract-version
packets[]
```

每个packet只含`change`、`depends-on[]`、`change-source-path`、`change-source-sha256`、`capability-slices[]`。Depends-on必须从final-roadmap `dependency-edges[]`确定性派生。

空slice marker必须与唯一`valid-foundation-exception` prefix row一致；其余Change非空。

## Terminal authority digest

Final integration review绑定的`terminal-authority-sha256`只覆盖以下七份terminal artifact。路径与顺序固定为：

```text
1. openspec/orchestrate/phase-works/phase-5/final-roadmap.json
2. openspec/orchestrate/phase-works/phase-5/framework-refit-trace.json
3. openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json
4. openspec/orchestrate/phase-works/phase-5/capability-baseline-reconciliation.json
5. openspec/orchestrate/phase-works/phase-5/final-packet-index.json
6. openspec/orchestrate/trace/phase-5.trace.json
7. openspec/orchestrate/change-plan.md
```

计算规则：

1. 按上述固定顺序读取每个文件的raw bytes，并分别计算lowercase hexadecimal SHA256；
2. 构造且只构造以下payload，`artifacts[]`保持上述固定顺序：

```json
{"artifacts":[{"artifact-path":"<repository-relative-path>","sha256":"<raw-bytes-sha256>"}]}
```

3. 对完整payload递归按key排序，使用`separators=(',', ':')`、`ensure_ascii=False`序列化为UTF-8 compact JSON，末尾不得写换行；
4. 对序列化bytes计算SHA256，得到`terminal-authority-sha256`。

Manifest、integration review JSON/Markdown、one-shot attempt/result与completion trace都不进入该digest。不得用manifest inventory、phase status、workflow status或文件mtime替代固定七文件payload。Phase 5 plan虽不进入digest，仍必须与根plan逐字节一致。

## Final integration review v1

根`final-integration-review.json`使用`source-aligned-final-integration-review-v1`，顶层只含：

```text
trace-schema
trace-contract-version
status: passed|blocked
reviewer-id
terminal-authority-sha256
reviewed-artifacts[]
capability-results[]
change-results[]
outcome-thread-results[]
dependency-edge-results[]
guard-link-results[]
occurrence-chain-result
findings[]
language-self-check
```

`reviewed-artifacts[]`必须与terminal digest payload中的七个artifact row逐项一致，顺序不变，每行只含`artifact-path`与`sha256`。

Capability result按final roadmap中的Capability顺序每项恰好一行，只含：

```text
capability
gate-results[]
result: passed|failed
note
evidence-ga-ids[]
```

Change result按`change-order[]`每项恰好一行，shape相同但首字段为`change`。`gate-results[]`每行只含`gate`、`result: passed|failed`、非空中文`note`与非空`evidence-ga-ids[]`，并分别完整覆盖共享原则的固定8项Capability gate或Change gate。

Outcome-thread result按final roadmap `outcome-threads[]`每项恰好一行，只含：

```text
outcome-thread-id
result: passed|failed
note
evidence-ga-ids[]
```

它复核该Change从trigger/context、normative behavior、observable outcome或invariant、exception semantics到acceptance evidence形成可独立交付的完整线程。

Dependency-edge result按final roadmap中每条dependency edge恰好一行，只含：

```text
dependency-id
result: passed|failed
note
evidence-ga-ids[]
```

它必须重新检查四项hard dependency gate；没有dependency edge时为空数组。

Guard-link result对final roadmap中的每个`guard-links[]` row恰好一行，只含：

```text
guard-link-id
result: passed|failed
note
evidence-ga-ids[]
```

它必须确认planned guard与guarded outcome的first-realizing Change共交付，或确认existing guard独立保护当前baseline中的既有运行表面；没有guard link时为空数组。

`occurrence-chain-result`只含：

```text
result
note
evidence-ga-ids[]
```

其中`result`、`note`必须为非空string，`evidence-ga-ids[]`必须是非空GA array。Passed时`result`必须为`passed`，并证明每个GA沿`frozen evidence → GA resolver → terminal mapping → public handoff`进入最终交付，且每个非空directive拥有唯一resolution。Phase 4 neutral collection另行接受一致性审计，但不属于mapping或handoff分配链。

`findings[]`只保存非空简体中文finding string；`language-self-check`是非空且含中文的string。Passed要求：

- `reviewed-artifacts[]`精确绑定当前固定七文件payload与digest；
- 每个Capability、Change、outcome thread、dependency edge与guard link result使用对应kebab-case ID，且`evidence-ga-ids[]`非空；
- 全部Capability、Change、outcome thread、dependency edge、guard link result均为`passed`；
- 全部gate result为`passed`；
- occurrence chain result为`passed`；
- 每个final Change的Prefix Utility、Consumer Closure、foundation-like、directive与order选择已在上述结果中复核；
- `findings[]`为空。

Blocked要求至少一个失败结果或非空finding。根`final-integration-review.md`由JSON与terminal authority确定性渲染；JSON不保存mirror path，不得手写第二份结论。

Review JSON以`phase: workflow`、`role: final-integration-review`、`authority: semantic`进入manifest。

## Final integration one-shot attempt envelope v1

Finalizer不得先运行review semantic prevalidation、失败后再依赖review mirror或completion充当one-shot标记。首次提交现有`final-integration-review.json`时，必须先以exclusive atomic create写入：

```text
trace/final-integration-review-attempt.trace.json
```

其schema为`source-aligned-final-integration-review-attempt-v1`，顶层只含：

```text
trace-schema
trace-contract-version
status: submitted
final-integration-review-path
final-integration-review-sha256
```

该authority固定首次提交review的repository-relative path与raw-bytes SHA，发布后永不覆盖。Finalizer随后才允许执行all-phase、terminal authority与review semantic validation。若进程只留下`submitted` authority，恢复仅允许继续校验同一path、同一raw bytes；review缺失、symlink、替换或digest drift必须终态blocked。

每次已记录attempt必须且只能以exclusive atomic create写入一次：

```text
trace/final-integration-review-attempt-result.trace.json
```

其schema为`source-aligned-final-integration-review-attempt-result-v1`，顶层只含：

```text
trace-schema
trace-contract-version
status: passed|blocked
final-integration-review-attempt-path
final-integration-review-attempt-sha256
terminal-authority-sha256
issues[]
```

Result必须绑定attempt authority的repository-relative path与raw-bytes SHA。`passed`要求有效的64位lowercase terminal digest且`issues[]`为空；`blocked`要求非空`issues[]`，在失败发生于terminal authority可计算之前时`terminal-authority-sha256`为`null`，否则为当前64位lowercase digest。

Review schema、evidence scope、identity、terminal digest或任何pre-completion validation失败，都必须先发布blocked result再返回失败；不得生成review mirror、completion或integration-passed manifest，也不得通过替换review重试。已有result的generation永久拒绝第二次final integration attempt。合法blocked review同样产生blocked result，之后可按Workflow completion契约发布blocked completion；合法passed review先产生passed result，之后才可发布integration-passed completion。

Attempt与result是one-shot workflow control authority，不进入`terminal-authority-sha256`。合法completion发布后的final manifest必须登记两者；invalid review导致的early blocked result本身就是fail-closed terminal blocker，即使没有completion也不得恢复为可消费generation。

## Workflow completion v1

`trace/workflow-completion.trace.json`使用`source-aligned-workflow-completion-v1`，顶层只含：

```text
trace-schema
trace-contract-version
status: integration-passed|blocked
terminal-authority-sha256
final-integration-review-path
final-integration-review-sha256
issues[]
```

`integration-passed`要求：

- Review JSON status passed；
- review path固定为`openspec/orchestrate/final-integration-review.json`，SHA与当前raw bytes一致；
- completion terminal digest与review逐字一致；
- 按固定七文件payload重算得到同一terminal digest；
- issues为空。

Blocked要求非空issues。Completion以`phase: workflow`、`role: workflow-completion`、`authority: control`进入manifest。

Completion trace原子发布后，manifest最后更新`workflow-status: integration-passed|blocked`。Selector、handoff与任何“完成”声明只接受`integration-passed`。

## Renderer、validation 与 handoff

- Renderer v11支持Phase 2 atoms/index、Phase 3 index/coverage、Phase 4 neutral collections、Phase 5 refit/final-roadmap plan/mapping/baseline、integration review mirror。
- Renderer不得从Markdown恢复JSON语义。
- `--preflight`支持Phase 2、Phase 3与Phase 5；Phase 5 preflight只接受review-pending且根plan不存在。
- Phase 5 normal validator接受accepted/adjusted + gate passed的terminal handoff，或上述两种精确canonical blocked shape；`--complete`仍只接受前者及后续integration completion。
- Complete validator要求Phase 1/3/5 gate passed、Phase 4 assembled、Phase 5 terminal、root plan一致、integration review/completion尚未伪造。
- Workflow selector validator只接受manifest workflow-status integration-passed、passed review与合法completion。
- Validator拒绝legacy contract、Phase 4 candidate bucket、roadmap/refit双重authority、mapping与同一Phase 5 candidate roadmap不一致、packet dependency drift、public metadata leak和symlink surface。
- Validator不检查semantic duplicate，也不因GA数量推断framework。
