# Trace sidecar contract

本技能采用Phase-specific authority。JSON用于精确校验、检索和跨产物映射，但并非每个Phase的内容权威；Markdown是否为权威由下表决定。

## 目录

- [全局版本与权威边界](#全局版本与权威边界)
- [必需布局与 Schema](#必需布局)
- [Manifest v2](#manifest-v2)
- [Phase 1 trace](#phase-1-trace-v3-bounded-review-gate)
- [Evidence resolver](#evidence-resolver)
- [Phase 2 machine interface](#phase-2-source-atoms-v5trace-v5-与渲染)
- [Phase 3 machine interface](#phase-3-global-index-v3coverage-v2-与-trace-v4)
- [Phase 4 machine interface](#phase-4-assemblerindex-v2-与-trace-v5)
- [Phase 5 machine interface](#phase-5-framework-refit-v4mapping-v4-与-trace-v5)
- [Renderer、validation 与 handoff](#renderer)

## 全局版本与权威边界

- trace contract：`source-aligned-trace-v6`
- render contract：`source-aligned-render-v10`
- JSON key使用kebab-case；ID不含Markdown反引号；多ID使用array。
- canonical line evidence为`line-ranges: [{"start": 1, "end": 2}]`。
- Phase 2 atom和Phase 3 gap atom各包含一个连续range及逐字`source-fact`；后续索引和mapping只保存reference。
- row hash统一为compact sorted UTF-8 JSON SHA256。
- 所有JSON `*-path`字段必须是workspace/repository root-relative path，统一使用共享canonical path helper生成；不得写绝对路径或相对于`openspec/orchestrate/`的短路径。文档目录树中的短路径仅用于展示，不是序列化规则。

| Phase | 内容权威 | 机器校验与派生产物 |
| --- | --- | --- |
| Phase 1 | `initial-change-plan.md` | Phase trace中的source manifest、digest与bounded review gate |
| Phase 2 | 每份provisional `.atoms.json` | atoms Markdown mirror、聚合`index.md`；直到Phase 3 freeze才冻结 |
| Phase 3 | global atom index JSON与coverage review JSON | 对应Markdown mirror、逐GA mapping ambiguity及evidence-freeze gate |
| Phase 4 | 由确定性assembler直接生成的evidence collection Markdown | 派生`evidence-collection-index.json` |
| Phase 5 | final `change-plan.md`、framework refit JSON、atom mapping JSON | review mirror、baseline、公开change source、Capability slices、bundle index |

Work queue、agent report、Phase 1和Phase 3 reviewer/repair report、final integration report是noncanonical流程证据，直接写Markdown，不进入manifest。Phase 4–5不创建Phase reviewer/repair report。

旧trace contract一律拒绝；不提供迁移脚本。`source-aligned-trace-v5`及更早generation保持原状态，不得迁移、伪装或原地升级；新generation必须从Phase 1使用v6开始。

## 必需布局

```text
openspec/orchestrate/
├── change-plan.md                              # 仅Phase 5 terminal
├── trace/
│   ├── manifest.json
│   └── phase-1.trace.json ... phase-5.trace.json
├── change-capability-anchors/
│   ├── obligation-atom-index.json|md
│   ├── index.md
│   └── <change>/
│       ├── change-source.md
│       └── capability-slices/<capability>.md
└── phase-works/
    ├── phase-1/
    │   ├── initial-change-plan.md
    │   ├── source-doc-manifest.md
    │   ├── phase-1-agent-report.md
    │   ├── phase-1-reviewer-report.md
    │   └── phase-1-repair-report.md             # 仅发生repair时
    ├── phase-2/
    │   ├── source-obligation-atoms/work-queue.md
    │   ├── source-obligation-atoms/index.md
    │   ├── source-obligation-atoms/<source>.atoms.json|md
    │   └── phase-2-agent-report.md
    ├── phase-3/
    │   ├── coverage-review.json|md
    │   ├── phase-3-reviewer-report.md
    │   └── phase-3-repair-report.md             # 仅发生repair时
    ├── phase-4/
    │   ├── phase-4-agent-report.md
    │   └── source-evidence-collections/...
    └── phase-5/
        ├── change-plan.md
        ├── framework-refit-trace.json
        ├── plan-refit-review.md
        ├── atom-plan-mapping.json|md
        ├── capability-baseline-reconciliation.json|md
        ├── final-packet-index.json
        └── phase-5-agent-report.md
```

Patch request、Phase 5 checkpoint及任何incremental/targeted artifact均不属于v6布局；validator必须拒绝其存在。

## Schema

Phase trace：

- `source-aligned-phase-1-trace-v3`
- `source-aligned-phase-2-trace-v5`
- `source-aligned-phase-3-trace-v4`
- `source-aligned-phase-4-trace-v5`
- `source-aligned-phase-5-trace-v5`

Artifact：

- `source-aligned-source-atoms-v5`
- `source-aligned-global-atom-index-v3`
- `source-aligned-phase-3-coverage-review-v2`
- `source-aligned-evidence-collection-index-v2`
- `source-aligned-framework-refit-trace-v4`
- `source-aligned-atom-plan-mapping-v4`
- `source-aligned-capability-baseline-v1`
- `source-aligned-final-packet-index-v3`

除final packet index升级为v3外，内部artifact沿用原schema shape；所有新generation artifact的`trace-contract-version`必须为`source-aligned-trace-v6`。

## Manifest v2

`trace/manifest.json`继续使用`source-aligned-orchestrate-manifest-v2`，顶层必须且只能包含`trace-schema`、`trace-contract-version`、`authority: control`、`orchestrate-dir`、`phase-statuses`和`artifacts[]`。

每个artifact row必须且只能包含`json-path`、`trace-schema`、`sha256`、`phase`、`role`和`authority`；`json-path`为repository-relative。

`authority`枚举：

- `semantic`：Phase 2 atoms、Phase 3 global index/coverage review、Phase 5 refit trace/mapping。
- `derived`：Phase 4 index、Phase 5 baseline/packet index。
- `control`：各Phase trace；manifest自身通过顶层`authority`声明，不自列。

Markdown不进入manifest。Manifest只列当前存在且应登记的JSON，每份恰好一次；每次validator前刷新digest，validator pass后刷新Phase status。Phase 1/2读取trace `status`，Phase 3读取`decision`，Phase 4/5读取`status`。

Phase 2 pass只表示provisional interface有效。只有Phase 3 `coverage-complete`且review gate passed才冻结Phase 2/3；Phase 4/5 validator失败直接blocked，不得修改冻结authority。

## Phase 1 trace v3 bounded review gate

除source manifest、initial plan ref和status外，`phase-1.trace.json`必须包含`review-gate`，且只包含`status`、`writer-id`、`reviews[]`、`repairs[]`。

- `reviews[]`最多三行；每行只含`round`、`reviewer-id`、`validator-status`、`plan-sha256`、`finding-fingerprints[]`。
- `repairs[]`最多两行；每行只含`round`、`repair-writer-id`、`finding-fingerprints[]`、`before-plan-sha256`、`after-plan-sha256`。
- Round从1连续递增；通常`len(reviews) = len(repairs) + 1`，仅terminal no-op repair blocked允许两者等长且不得继续review。
- 只有gate passed、最后review findings为空且validator passed时才能使用`initial-plan-written`。Repeated fingerprint、no-op repair、身份不独立或第三次review仍不pass必须blocked。

Phase 1 canonical blocked trace仍要求已有可校验initial plan及完整review gate；更早的orchestration stop只写noncanonical报告。

## Evidence resolver

- Phase 2 evidence ref按`source-document + source-atom-id`加载source path、唯一range、`source-fact`、type、normativity和candidate hint。
- Phase 3 evidence ref按`gap-atom-id`从coverage review加载同类字段和review judgment。
- Ref不存在、重复或类型不匹配是blocker。
- Resolver不得读取source document，不比较不同evidence的语义。

## Phase 2 source atoms v5、trace v5 与渲染

每份`source-aligned-source-atoms-v5`顶层必须且只能包含：

- `trace-schema`、`trace-contract-version`
- `source-document`、`source-sha256`、`read-status: read-full`、`canonical-owner`、`source-role`
- `phase-1-candidate-changes-capabilities-considered[]`
- `source-atoms[]`、`blockers[]`、`language-self-check`

`phase-1-candidate-changes-capabilities-considered[]` row只含`change`、`capabilities[]`和简体中文`note`。每个`source-atoms[]` row必须且只能包含`source-atom-id`、`line-ranges[]`、`atom-type`、逐字`source-fact`、`normativity`、`candidate-status`、`candidate-artifact-projection`、`candidate-owner-change`、`candidate-target-capability`和简体中文`rationale`；`line-ranges[]`恰有一行，只含整数`start`、`end`并表示连续范围。`blockers[]`是简体中文string array，`language-self-check`是非空简体中文string。

Status/projection/owner/target组合严格服从Phase 2 candidate mapping矩阵。尤其spec/guard target不得为`none`，design/verification target必须为`none`，conflict/unclassified必须projection `unsure`且有blocker。

`.atoms.md`完全由对应JSON渲染；聚合`index.md`只由work queue、全部atoms JSON和Phase trace生成。两类Markdown都不是第二份authority。

Phase 2 `--preflight`只要求work queue与全部atom JSON，检查source digest、quote/range、字段组合和candidate mapping；不要求Phase 2 trace、manifest登记或mirror。普通Phase 2 validator要求完整terminal surface。

成功的`phase-2.trace.json`必须且只能包含`trace-schema`、`trace-contract-version`、`status: source-atoms-written`、`work-queue-path`、`sources[]`和`phase-report-path`。`sources[]`每份read-full source恰好一行，只含`source-document`、`atom-json-path`、`atom-json-sha256`、`atom-markdown-path`、`canonical-owner`、`read-status`、`atom-count`和`blockers[]`。

`status: blocked` trace必须且只能包含`trace-schema`、`trace-contract-version`、`status`和非空`issues[]`。V5 trace显式拒绝`mode`、patch/checkpoint ref、patch summary、base digest及affected closure字段。Phase 2成功仍是provisional，不是freeze marker。

## Phase 3 global index v3、coverage v2 与 trace v4

`source-aligned-global-atom-index-v3`顶层必须且只能包含`trace-schema`、`trace-contract-version`、repository-relative `artifact-path`和`global-atoms[]`。每个row只含`global-atom-id`和`evidence-ref`；GA使用`GA-####`。Evidence ref shape：

- `phase-2-source-atom`：只含`kind`、`source-document`、`source-atom-id`。
- `phase-3-gap-atom`：只含`kind`、`gap-atom-id`。

`source-aligned-phase-3-coverage-review-v2`顶层必须且只能包含`trace-schema`、`trace-contract-version`、repository-relative `artifact-path`、`documents[]`、`gap-atoms[]`、`remainder-dispositions[]`、`mapping-ambiguities[]`、`summary`、`decision`和`language-self-check`。Nested shape：

- `documents[]`：只含`source-document`、`source-sha256`、`line-count`、repository-relative `phase-2-atom-path`、`phase-2-atom-sha256`、`covered-ranges[]`和`candidate-uncovered-ranges[]`。
- `gap-atoms[]`：只含`gap-atom-id`、`source-document`、单元素`line-ranges[]`、`source-fact`、`atom-type`、`normativity`和简体中文`review-judgment`；ID使用`P3-GAP-####`。
- `remainder-dispositions[]`：只含`disposition-id`、`source-document`、`line-ranges[]`、`classification`、`linked-gap-atom-ids[]`和简体中文`reason`；ID使用`RD-####`，classification只允许`missing-obligation|safe-non-obligation|blocked`。
- `mapping-ambiguities[]`：只含`global-atom-id`、与global index逐字一致的`evidence-ref`、非空唯一`dimensions[]`和简体中文`reason`；dimension只允许`owner-change|relation|artifact-projection|target-capability`，不得包含candidate/final value或resolution。
- `summary`：只含整数`source-documents`、`phase-2-atoms`、`gap-atoms`、`global-atoms`、`mapping-ambiguities`、`candidate-uncovered-ranges`和`remainder-dispositions`；最后一项只含整数`blocked`、`missing-obligation`、`safe-non-obligation`。

Coverage review的`decision`只允许`coverage-complete|blocked`，表示coverage artifact自身的闭合结果；它不是freeze marker。Trace在review期间使用`review-pending`，因此terminal commit只改trace，不改已审coverage authority或其digest。

非blocked的`phase-3.trace.json`必须且只能包含`trace-schema`、`trace-contract-version`、`decision`、`global-atom-index-path`、`global-atom-index-sha256`、`coverage-review-path`、`coverage-review-sha256`、`review-gate`和`issues[]`。`issues[]`必须为空。

- `--preflight`只接受`decision: review-pending`与`review-gate.status: pending`。
- 普通Phase 3 validator只接受`decision: coverage-complete`与`review-gate.status: passed`。
- 两种状态都要求四个artifact path/SHA绑定当前完整authority；Markdown mirror必须逐字重渲染一致。

Blocked trace必须且只能包含`trace-schema`、`trace-contract-version`、`decision: blocked`、`review-gate`和非空`issues[]`；`review-gate.status`必须为`blocked`。V4 trace拒绝全部update-mode、patch/checkpoint、base/affected/new identity字段。

`review-gate`必须且只能包含：

- `status: pending|passed|blocked`
- `phase-2-canonical-owner-ids[]`
- `phase-2-aggregate-writer-id`
- `phase-3-writer-id`
- `reviews[]`
- `repairs[]`

Review row必须且只能包含`round`、`stage`、`reviewer-id`、`phase-2-validator-status`、`phase-3-validator-status`、`evidence-authority-sha256`、`finding-fingerprints[]`。Stage只允许`phase-2-preflight|phase-3-closure`；Phase 2 status只允许`passed|failed`，Phase 3 status只允许`passed|failed|not-run`，且`not-run`只用于Phase 2 stage。

Repair row必须且只能包含`round`、`repair-writer-id`、`finding-fingerprints[]`、`before-evidence-authority-sha256`、`after-evidence-authority-sha256`。Reviews最多三行、repairs最多两行，分别从1连续编号。Repair必须恰好消费同轮review全部finding。全部producer、reviewer和repair writer ID互不相同；repeated fingerprint和no-op repair立即blocked。

Evidence authority digest对以下compact sorted JSON对象计算SHA256：按source path排序的source digests、按atom JSON path排序的Phase 2 artifact digests、global index path/SHA、coverage review path/SHA。Phase 2 stage的两个Phase 3 ref显式为null；Phase 3 closure必须全部非null。对象不包含trace、manifest、mirror或report。

Terminal passed要求最后review为`phase-3-closure`、双validator `passed`、findings为空、digest等于当前完整authority，且每个前序finding review恰有一轮repair。此时`coverage-complete` trace是Phase 2/3与GA的唯一freeze commit marker。

## Phase 4 assembler、index v2 与 trace v5

Phase 4 assembler只读冻结Phase 1–3 authority，解析全部GA/evidence ref，机械计算bucket，在staging生成全部collection Markdown，最后生成派生index。不得读取source、从index反向生成Markdown、裁决ambiguity或引入framework判断。

`source-aligned-evidence-collection-index-v2`顶层必须且只能包含`trace-schema`、`trace-contract-version`、`generated-from[]`、`rows[]`和`rendered-artifacts[]`：

- `generated-from[]`每行只含repository-relative `artifact-path`和`sha256`。
- `rows[]`每行只含`global-atom-id`、与global index一致的`evidence-ref`、`change-bucket`、`capability-bucket`和repository-relative `rendered-collection-paths[]`；每个GA恰好一行。
- `rendered-artifacts[]`每行只含repository-relative `artifact-path`、`sha256`、`collection-kind`和`owner-id`。Kind只允许`index|unassigned-and-gap|input-change|input-capability`。

Assembler自校验staging surface后原子发布collection/index，最后写Phase 4 trace。`assembled` trace必须且只能包含`trace-schema`、`trace-contract-version`、`status`和`assembled`；`assembled`只含repository-relative `evidence-collection-index-path`、`evidence-collection-index-sha256`和`renderer-result-summary`。

`blocked` trace必须且只能包含`trace-schema`、`trace-contract-version`、`status`和非空`issues[]`；不得保留未提交terminal index/collection。V5 trace拒绝update mode、patch/checkpoint ref、base digest与affected closure。

## Phase 5 framework refit v4、mapping v4 与 trace v5

Framework refit顶层必须且只能包含`trace-schema`、`trace-contract-version`、`status`、repository-relative `initial-plan-ref`、`capability-reviews[]`、`change-reviews[]`、`unassigned-and-gap-reviews[]`、`final-framework`、`issues[]`和`language-self-check`。Status只允许`accepted|adjusted|blocked`；`initial-plan-ref`只含`artifact-path`、`sha256`。

Capability review row只含`input-capability`、repository-relative `evidence-collection-path`、`decision`、`final-capabilities[]`、`initial-gate-results[]`、`supporting-global-atom-ids[]`和简体中文`reason`。Decision只允许`keep|split|merge|remove|rename`。

Change review row只含`input-change`、repository-relative `evidence-collection-path`、`decision`、`final-changes[]`、`initial-gate-results[]`、`supporting-global-atom-ids[]`和简体中文`reason`。Decision只允许`keep|split|merge|remove|rename|reorder|scope-adjusted`。

每个`initial-gate-results[]` row只含`gate`、`result: passed|failed`和非空简体中文`note`。Capability gate按共享原则的8项固定顺序完整覆盖；Change gate按6项固定顺序完整覆盖。

Unassigned/gap review row只含`global-atom-id`、`evidence-ref`、`framework-impact: none|supports-adjustment`和简体中文`reason`。不得包含final mapping字段。

Terminal `final-framework`只含`change-order[]`、`capabilities[]`和`overlay[]`；overlay row只含`change`、`capability`、`capability-impact: new|modified`。Blocked时`final-framework`为null、`issues[]`非空，并清理terminal mapping、plan与全部派生surface。Refit v4不含`patch-history`，validator拒绝旧patch status/field。

Atom mapping v4顶层只含`trace-schema`、`trace-contract-version`、repository-relative `artifact-path`和`rows[]`。`artifact-path`固定指向`openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.md`，不得指向JSON自身；JSON authority的位置由固定布局与manifest `json-path`标识。每个GA恰好一行，只含`global-atom-id`、`evidence-ref`、`final-owner-change`、`final-relation`、`final-artifact-projection`、`final-capability-impact`、`final-target-capability`、`related-capabilities[]`和简体中文`reason`。

- Relation只允许`direct|context|dependency|preserve|reference|non-goal`。
- Direct projection只允许`spec-requirement|spec-guard|design-obligation|verification-obligation`；non-direct使用`contextual-only`。
- Direct spec/guard指定具体Capability和`new|modified`；其他row的impact/target为`none`。
- Mapping row是final owner/relation/projection/target、related Capability及ambiguity resolution的唯一权威。Candidate hint与terminal mapping可以不同，不回写Phase 2/3。

Terminal `phase-5.trace.json`必须且只能包含`trace-schema`、`trace-contract-version`、`status: accepted|adjusted`、`final-change-plan-path`/SHA、`framework-refit-trace-path`/SHA、`plan-refit-review-path`/SHA、`atom-plan-mapping-path`/SHA、`capability-baseline-reconciliation-path`/SHA和`final-packet-index-path`/SHA。全部path为repository-relative。

Blocked trace必须且只能包含`trace-schema`、`trace-contract-version`、`status: blocked`、`framework-refit-trace-path`/SHA、`plan-refit-review-path`/SHA和非空`issues[]`。不得保留Phase 5或根terminal plan、mapping、baseline、change source、Capability slice或anchor index。V6 trace拒绝execution mode、patch history、request/checkpoint ref及resume/abort字段。

`source-aligned-final-packet-index-v3`顶层必须且只能包含`trace-schema`、`trace-contract-version`和roadmap顺序的`packets[]`。每个packet row必须且只能包含`change`、`depends-on[]`、`change-source-path`、`change-source-sha256`和显式`capability-slices[]`。每个slice row必须且只能包含`capability`、`capability-impact: new|modified`、`slice-path`和`slice-sha256`。

- `change-source.md`由该Change全部owner-scoped frozen evidence重算，按source path/range/GA稳定排序；除Change boundary外，只将逐字`source-fact`作为原始Markdown直接排列，并以一个空行分隔。
- `capability-slices/<capability>.md`只由该Change/Capability direct `spec-requirement|spec-guard` mapping重算；除Capability Purpose/Owns/Excludes与impact外，只按同一稳定顺序直接排列逐字`source-fact`。
- 两类公开文件都不得输出`Source Occurrence`标题、序号、source path/range字段或生成器附加围栏；重复occurrence保持独立且不得去重。
- 公开index与Markdown不包含任何Change类型字段，也禁止GA、atom ID、evidence ref、relation、projection、mapping reason等内部trace元数据。
- 非空slices表示普通Change；空slices表示可选foundation。foundation最多一个、必须是roadmap首项、`depends-on`为空且无overlay；其余Change必须非空。
- 所有公开path按固定repository-relative lexical path序列化，不跟随symlink。`change-capability-anchors/`、Change目录、`capability-slices/`及其文件的任一路径段为symlink时必须阻断；三个目录层级均执行exact-surface校验，空foundation也必须保留空的`capability-slices/`目录。

## Renderer

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact all-supported \
  --write
```

支持Phase 2 atoms/index、Phase 3 global index/coverage review、Phase 4 assembler/index、Phase 5 refit review/mapping/baseline。所有mirror使用`source-aligned-render-v10`。Renderer不得从Markdown恢复语义。

Phase 5 review mirror固定使用`Initial Gate Results`与`Supporting GAs`列；gap表只显示`Framework Impact`，不得显示final owner/target；输入ambiguity章节名固定为`Potential Mapping Ambiguities (Input)`并声明resolution只在mapping mirror。

## Validation 与 handoff

- Validator检查schema、repository-relative path、digest、ID、reference cardinality、source quote、coverage complement、potential ambiguity、review budget/identity/digest、render drift和跨artifact一致性。
- `--preflight`只允许配合`--phase phase-2|phase-3`，且与`--complete`互斥。Phase 2 preflight不要求terminal surface；Phase 3 preflight只接受review-pending。普通Phase 3 validator只接受coverage-complete+passed或合法blocked。
- Complete validator要求Phase 1 review passed、Phase 3 evidence freeze passed、Phase 4 assembled、Phase 5 terminal，且Phase 5 plan与根plan逐字节一致。
- Phase 5 helper在生成任何派生物前校验refit/mapping envelope与canonical mirror path；helper/validator由final Change order、direct spec/guard mapping与repository baseline执行唯一advancement推导，并拒绝mapping impact、refit/final plan overlay或baseline row漂移。Helper只拒绝非法输入，不自动修正authority。
- Phase 4 assembler/validator及Phase 5 helper不得读取source document；source quote验证只属于Phase 2/3 freeze前校验。
- Validator拒绝v5及更早trace contract、旧packet surface、旧patch/checkpoint schema、旧status、旧field和遗留patch artifact；不检查semantic duplicate，也不因GA数量推断framework。
- Validator从terminal mapping和final plan重算每个公开文件，核对source/slice集合、roadmap与Capability顺序、依赖、impact、固定path、digest及foundation cardinality；公开handoff不要求下游保留GA trace。
