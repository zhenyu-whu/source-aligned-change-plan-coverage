# Trace sidecar contract

本技能采用 Phase-specific authority。JSON用于精确校验、检索、增量保护和跨产物映射，但并非每个Phase的内容权威；Markdown是否为权威由下表决定。

## 目录

- [全局版本与权威边界](#全局版本与权威边界)
- [必需布局与 Schema](#必需布局)
- [Manifest v2](#manifest-v2)
- [Phase 1 trace](#phase-1-trace-v3-bounded-review-gate)
- [Evidence resolver](#evidence-resolver)
- [Phase 2 machine interface](#phase-2-source-atoms-v4trace-v4-与渲染)
- [Phase 3 machine interface](#phase-3-global-index-v3coverage-v2-与-trace-v3)
- [Phase 4 machine interface](#phase-4-assemblerindex-v2-与-trace-v4)
- [Patch request 与 checkpoint](#evidence-patch-request-v1)
- [Phase 5 machine interface](#phase-5-framework-refit-v3mapping-v4-与-trace-v4)
- [Renderer、validation 与 handoff](#renderer)

## 全局版本与权威边界

- trace contract：`source-aligned-trace-v4`
- render contract：`source-aligned-render-v8`
- JSON key使用kebab-case；ID不含Markdown反引号；多ID使用array。
- canonical line evidence为`line-ranges: [{"start": 1, "end": 2}]`。
- Phase 2 atom和Phase 3 gap atom各包含一个连续range及冻结的`source-fact`；后续索引和mapping只保存reference。
- row hash统一为compact sorted UTF-8 JSON SHA256。

| Phase | 内容权威 | 机器校验与派生产物 |
| --- | --- | --- |
| Phase 1 | `initial-change-plan.md` | Phase trace中的source manifest、digest与bounded review gate |
| Phase 2 | 每份`.atoms.json` | atoms Markdown mirror、聚合`index.md`、targeted patch verification |
| Phase 3 | global atom index JSON与coverage review JSON | 对应Markdown mirror、逐GA mapping ambiguity |
| Phase 4 | 由确定性assembler直接生成的evidence collection Markdown | 派生`evidence-collection-index.json` |
| Phase 5 | final `change-plan.md`、framework refit JSON、atom mapping JSON | review mirror、baseline、packet、Capability view、anchor index |

work queue、agent report、Phase 1 reviewer/repair report和final integration report是非canonical流程证据，直接写Markdown，不进入manifest。Phase 2–5不创建Phase reviewer/repair report。

`source-aligned-evidence-patch-request-v1`是control authority。`source-aligned-phase-5-checkpoint-v2`是nonterminal semantic authority。两者都不是source或terminal final plan authority，且必须与Phase 5 trace commit marker组成patch contract定义的闭合授权组。

旧trace/artifact schema一律拒绝；不提供迁移脚本。恢复不得把旧artifact伪装成checkpoint或targeted patch。

## 必需布局

```text
openspec/orchestrate/
├── change-plan.md
├── trace/
│   ├── manifest.json
│   └── phase-1.trace.json ... phase-5.trace.json
├── change-capability-anchors/
│   ├── obligation-atom-index.json|md
│   ├── index.md
│   └── <change>/...
└── phase-works/
    ├── phase-1/
    │   ├── initial-change-plan.md
    │   ├── source-doc-manifest.md
    │   ├── phase-1-agent-report.md
    │   ├── phase-1-reviewer-report.md
    │   └── phase-1-repair-report.md       # 仅发生repair时
    ├── phase-2/
    │   ├── source-obligation-atoms/work-queue.md
    │   ├── source-obligation-atoms/index.md
    │   ├── source-obligation-atoms/<source>.atoms.json|md
    │   └── phase-2-agent-report.md
    ├── phase-3/coverage-review.json|md
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
        ├── phase-5-agent-report.md
        ├── evidence-patch-request.json    # 仅唯一patch链
        └── phase-5-checkpoint.json        # 仅唯一patch链
```

## Schema

Phase trace：

- `source-aligned-phase-1-trace-v3`
- `source-aligned-phase-2-trace-v4`
- `source-aligned-phase-3-trace-v3`
- `source-aligned-phase-4-trace-v4`
- `source-aligned-phase-5-trace-v4`

Artifact：

- `source-aligned-source-atoms-v4`
- `source-aligned-global-atom-index-v3`
- `source-aligned-phase-3-coverage-review-v2`
- `source-aligned-evidence-collection-index-v2`
- `source-aligned-framework-refit-trace-v3`
- `source-aligned-atom-plan-mapping-v4`
- `source-aligned-capability-baseline-v1`
- `source-aligned-final-packet-index-v2`
- `source-aligned-evidence-patch-request-v1`
- `source-aligned-phase-5-checkpoint-v2`

## Manifest v2

`trace/manifest.json`继续使用`source-aligned-orchestrate-manifest-v2`，顶层必须且只能包含`trace-schema`、`trace-contract-version`、`authority: control`、`orchestrate-dir`、`phase-statuses`和`artifacts[]`。

每个artifact row必须且只能包含`json-path`、`trace-schema`、`sha256`、`phase`、`role`和`authority`。

`authority`枚举：

- `semantic`：Phase 2 atoms、Phase 3 global index/coverage review、Phase 5 refit trace/mapping，以及存在时的Phase 5 checkpoint。
- `derived`：Phase 4 index、Phase 5 baseline/packet index。
- `control`：各Phase trace及可选evidence patch request；manifest自身通过顶层`authority`声明，不自列。

Markdown不进入manifest。manifest只列当前存在且应登记的JSON，每份恰好一次；每次validator前刷新digest，validator pass后刷新Phase status。Phase 1/2读取trace`status`，Phase 3读取`decision`，Phase 4/5读取`status`。

Phase 2–5 validator只能pass或使Phase blocked；失败不得自动重启producer、就地修正后重验或重复当前Phase。唯一例外是patch contract定义的完整Phase 5授权组已提交后执行一次targeted patch。

## Phase 1 trace v3 bounded review gate

除source manifest、initial plan ref和status外，`phase-1.trace.json`必须包含`review-gate`，且只包含`status`、`writer-id`、`reviews[]`、`repairs[]`。

- `reviews[]`最多三行；每行只含`round`、`reviewer-id`、`validator-status`、`plan-sha256`、`finding-fingerprints[]`。
- `repairs[]`最多两行；每行只含`round`、`repair-writer-id`、`finding-fingerprints[]`、`before-plan-sha256`、`after-plan-sha256`。
- round必须从1连续递增；通常`len(reviews) = len(repairs) + 1`，仅blocked的terminal no-op repair允许两者等长且不得继续review。只有`review-gate.status: passed`、最后review findings为空且validator passed时才能使用`initial-plan-written`。
- 同一finding fingerprint在后续任一轮review再次出现时，即使整份plan digest已变化，也必须立即`blocked`；任一repair before/after digest相同、身份不独立或第三次review仍不pass同样必须`blocked`。

Phase 1 canonical `blocked` trace仍要求已有可校验initial plan及完整review gate。若在创建这些authority之前即无法完整读取source，只记录非canonical orchestration stop并停止，不得伪造缺少plan/review gate的Phase 1 blocked trace。

## Evidence resolver

- Phase 2 evidence ref按`source-document + source-atom-id`加载source path、唯一range、`source-fact`、type、normativity和candidate hint。
- Phase 3 evidence ref按`gap-atom-id`从coverage review加载同类字段和review judgment。
- ref不存在、重复或类型不匹配是blocker，不属于evidence patch defect。
- resolver不得读取source document，不比较不同evidence的语义。

## Phase 2 source atoms v4、trace v4 与渲染

每份`source-aligned-source-atoms-v4`顶层必须且只能包含：

- `trace-schema`、`trace-contract-version`
- `source-document`、`source-sha256`、`read-status: read-full`、`canonical-owner`、`source-role`
- `phase-1-candidate-changes-capabilities-considered[]`
- `source-atoms[]`、`blockers[]`、`language-self-check`

`phase-1-candidate-changes-capabilities-considered[]` row只含`change`、`capabilities[]`和简体中文`note`。每个`source-atoms[]` row必须且只能包含`source-atom-id`、`line-ranges[]`、`atom-type`、逐字`source-fact`、`normativity`、`candidate-status`、`candidate-artifact-projection`、`candidate-owner-change`、`candidate-target-capability`和简体中文`rationale`；`line-ranges[]`恰有一行，且该行只含整数`start`、`end`并表示一个连续范围。`blockers[]`是简体中文string array，`language-self-check`是非空简体中文string。Atom enum与组合语义见`references/phase-2-source-anchor-coverage.md`；不得出现Capability impact、related Capability或其他later-phase字段。

每份`.atoms.md`完全由对应JSON渲染，表列固定为`Source Atom ID`、`Lines`、`Atom Type`、`Source Fact`、`Normativity`、`Candidate Status`、`Candidate Artifact Projection`、`Candidate Owner Change`、`Candidate Target Capability`、`Rationale`。聚合`index.md`只由work queue、全部atoms JSON和Phase trace生成；两类Markdown都不是第二份authority。

`phase-2.trace.json`保留既有字段，并新增`mode`、`patch-request-ref`、`checkpoint-ref`和`patch-summary`；成功terminal status始终为`source-atoms-written`，失败终止使用`blocked`。

- `mode`只允许`initial|targeted-patch`。
- 成功trace顶层必须且只能包含`trace-schema`、`trace-contract-version`、`status`、`mode`、`work-queue-path`、`sources[]`、`phase-report-path`、`patch-request-ref`、`checkpoint-ref`和`patch-summary`。
- `sources[]`每份read-full source恰好一行，只含`source-document`、`atom-json-path`、`atom-json-sha256`、`atom-markdown-path`、`canonical-owner`、`read-status`、`atom-count`和`blockers[]`。
- initial mode的两个ref和summary均为null。
- targeted-patch mode的两个ref都只包含`artifact-path`、`sha256`；`patch-summary`必须且只能包含`base-phase-2-trace-sha256`、`affected-sources[]`、`changed-atoms[]`、`new-atoms[]`和`patch-writer-id`。
- `changed-atoms[]`每行只含`source-document`、`source-atom-id`、`before-row-sha256`、`after-row-sha256`；`new-atoms[]`每行只含`source-document`、`source-atom-id`、`row-sha256`。
- targeted mode只能消费`EPR-0001`，不得产生第二个成功terminal status。
- extraction、patch或validator无法在授权边界内完成时使用`status: blocked`。blocked trace必须且只能包含`trace-schema`、`trace-contract-version`、`status`、`mode`、`patch-request-ref`、`checkpoint-ref`、nullable `base-phase-2-trace-sha256`、`affected-sources[]`和非空`issues[]`：initial mode的refs/base为null且affected为空；targeted-patch mode必须绑定request/checkpoint，base digest等于request中的`base-artifacts.phase-2-trace-sha256`，affected sources按request target首次出现顺序精确覆盖。不得触发重跑。
- 每份`.atoms.md`完全由对应`.atoms.json`渲染；`index.md`由work queue、全部atoms JSON和Phase trace聚合渲染；validator逐字重渲染比较。

## Phase 3 global index v3、coverage v2 与 trace v3

`source-aligned-global-atom-index-v3`顶层必须且只能包含`trace-schema`、`trace-contract-version`、`artifact-path`和`global-atoms[]`。每个`global-atoms[]` row只含`global-atom-id`和`evidence-ref`；GA使用`GA-####`。`evidence-ref`按kind采用唯一shape：

- `phase-2-source-atom`：只含`kind`、`source-document`、`source-atom-id`。
- `phase-3-gap-atom`：只含`kind`、`gap-atom-id`。

`source-aligned-phase-3-coverage-review-v2`顶层必须且只能包含`trace-schema`、`trace-contract-version`、`artifact-path`、`documents[]`、`gap-atoms[]`、`remainder-dispositions[]`、`mapping-ambiguities[]`、`summary`、`decision`和`language-self-check`。其嵌套shape为：

- `documents[]`：只含`source-document`、`source-sha256`、`line-count`、`phase-2-atom-path`、`phase-2-atom-sha256`、`covered-ranges[]`和`candidate-uncovered-ranges[]`。
- `gap-atoms[]`：只含`gap-atom-id`、`source-document`、单元素`line-ranges[]`、`source-fact`、`atom-type`、`normativity`和简体中文`review-judgment`；ID使用`P3-GAP-####`。
- `remainder-dispositions[]`：只含`disposition-id`、`source-document`、`line-ranges[]`、`classification`、`linked-gap-atom-ids[]`和简体中文`reason`；ID使用`RD-####`，classification只允许`missing-obligation|safe-non-obligation|blocked`。
- `mapping-ambiguities[]`：只含`global-atom-id`、与global index逐字一致的`evidence-ref`、非空唯一`dimensions[]`和简体中文`reason`；dimensions只允许`owner-change|relation|artifact-projection|target-capability`，不得包含候选或final value。
- `summary`：必须且只能包含整数`source-documents`、`phase-2-atoms`、`gap-atoms`、`global-atoms`、`mapping-ambiguities`、`candidate-uncovered-ranges`和`remainder-dispositions`；后者必须且只能包含整数`blocked`、`missing-obligation`和`safe-non-obligation`。

所有range row只含整数`start`、`end`。mapping ambiguity非空不阻止`coverage-complete`；其语义判据、remainder覆盖和GA identity规则由`references/phase-3-coverage-review-iteration.md`定义。

成功的`phase-3.trace.json`必须且只能包含`trace-schema`、`trace-contract-version`、`decision`、`global-atom-index-path`、`global-atom-index-sha256`、`coverage-review-path`、`coverage-review-sha256`、`update-mode`、`patch-request-ref`、`checkpoint-ref`、`base-global-atom-index-sha256`、`base-coverage-review-sha256`、`affected-source-documents[]`和`new-global-atom-ids[]`。`decision: blocked`时必须且只能包含`trace-schema`、`trace-contract-version`、`decision`、`update-mode`、`patch-request-ref`、`checkpoint-ref`、`base-global-atom-index-sha256`、`base-coverage-review-sha256`、`affected-source-documents[]`、`new-global-atom-ids[]`和非空`issues[]`，不得保留成功态path或digest。

initial mode的ref、base digest为null且两个array为空；incremental-patch mode必须引用request/checkpoint及base digest。未受影响GA/ambiguity row保持identity与row digest，新GA只在当前最大ID后追加。global index与coverage review Markdown完全由对应JSON渲染；coverage mirror必须呈现mapping ambiguities，validator对两个mirror逐字重渲染比较。

## Phase 4 assembler、index v2 与 trace v4

Phase 4 assembler只读Phase 1 initial plan、Phase 2 atoms JSON、Phase 3 global index/coverage review，解析全部GA/evidence ref、机械计算bucket、生成所有collection Markdown，最后生成派生index。不得从index反向生成Markdown，不得读取source、裁决mapping ambiguity或引入framework判断。

`source-aligned-evidence-collection-index-v2`顶层必须且只能包含`trace-schema`、`trace-contract-version`、`generated-from[]`、`rows[]`和`rendered-artifacts[]`。嵌套shape为：

- `generated-from[]`每行只含`artifact-path`和`sha256`。
- `rows[]`每行只含`global-atom-id`、与global index逐字一致的`evidence-ref`、`change-bucket`、`capability-bucket`和`rendered-collection-paths[]`；每个GA恰好一行。
- `rendered-artifacts[]`每行只含`artifact-path`、`sha256`、`collection-kind`和`owner-id`。`collection-kind`只允许`index|unassigned-and-gap|input-change|input-capability`；对应owner依次为`all`、`unassigned-and-gap`、Phase 1 initial Change ID、Phase 1 initial Capability ID。

assembled的`phase-4.trace.json`必须且只能包含`trace-schema`、`trace-contract-version`、`status`、`update-mode`、`patch-request-ref`、`checkpoint-ref`、`base-evidence-collection-index-sha256`、`affected-closure`和`assembled`。`affected-closure`只含`global-atom-ids[]`、`change-buckets[]`、`capability-buckets[]`和`rendered-artifact-paths[]`；`assembled`只含`evidence-collection-index-path`、`evidence-collection-index-sha256`和`renderer-result-summary`。`status: blocked`时必须且只能包含`trace-schema`、`trace-contract-version`、`status`、`update-mode`、`patch-request-ref`、`checkpoint-ref`、`base-evidence-collection-index-sha256`、`affected-closure`和非空`issues[]`，不得保留成功态artifact digest。

initial mode的ref/base为null且closure各array为空；incremental-patch mode必须验证base与protected Phase 4 row，只有closure列出的collection允许语义变化。由于Phase 4只投影Phase 1 identity，change/capability buckets只能由checkpoint `initial-changes[]`/`initial-capabilities[]`授权，不能使用同名final scope。Phase 3/4 incremental `blocked` trace保留各自mode、request/checkpoint ref、base digest、已知affected source/new GA或affected closure以及非空issues；授权、abort和清理顺序只见patch contract。

validator从Phase 1–3重新计算全部Markdown和派生index并检查缺失、篡改、stale文件、GA基数、上游digest和`source-fact`逐字一致性。失败即`blocked`。

## Evidence patch request v1

顶层必须且只能包含`trace-schema`、`trace-contract-version`、`request-id`、`base-artifacts`、`targets`、`protected-rows`；`request-id`固定`EPR-0001`。

`base-artifacts`必须且只能包含：

- `phase-2-trace-sha256`
- `phase-3-trace-sha256`
- `global-atom-index-sha256`
- `coverage-review-sha256`
- `phase-4-index-sha256`

Target必须且只能包含`source-document`、nullable `source-atom-id`、nullable `global-atom-id`、nullable `evidence-ref`、`defect`、`allowed-operations[]`、`allowed-line-window`、`new-source-atom-ids[]`、nullable `base-row`、nullable `base-row-sha256`、`canonical-owner`、简体中文`reason`和`defect-witness`。`allowed-line-window`只包含`start`、`end`。

`defect-witness`必须且只能包含`locator-origin`、`source-sha256`和`window-sha256`；`locator-origin`只含非空`row-refs[]`。每个row ref只含`artifact-path`、`row-kind: phase-2-atom|phase-3-disposition`、`row-key`和`row-sha256`。

`defect`只允许`quote-mismatch|range-mismatch|mixed-independent-occurrences|missing-occurrence`；operation只允许`replace-quote|adjust-range|split|add`。Enum组合、locator核验与successor ID规则只见patch contract。

`protected-rows`必须且只能包含`phase-2-atoms`、`phase-3-documents`、`phase-3-gap-atoms`、`phase-3-dispositions`、`phase-3-mapping-ambiguities`、`global-atoms`、`phase-4-index-rows`和`phase-4-rendered-artifacts`；各row保存对应stable key字段和`sha256`。

## Phase 5 checkpoint v2

顶层必须且只能包含`trace-schema`、`trace-contract-version`、`checkpoint-id`、`stage`、`patch-request-ref`、`input-fingerprints`、`provisional-framework`、`completed-rows`、`pending-ids`、`allowed-update-scope`、`preserved-row-digests`和`patch-attempt`。

- `checkpoint-id`固定`P5CP-0001`，`stage`固定`mapping`；`patch-request-ref`只含`artifact-path`、`sha256`，每个`input-fingerprints[]` row同shape。
- `provisional-framework`必须且只能包含`change-order[]`、`capabilities[]`、`overlay[]`、`dependency-edges[]`、`change-lineage[]`、`capability-lineage[]`、`ga-lineage[]`、`change-semantic-digests[]`、`capability-semantic-digests[]`。
- `dependency-edges[]` row只含`change`、`depends-on`。Change lineage row只含`input-change`、`provisional-final-changes[]`；Capability lineage row只含`input-capability`、`provisional-final-capabilities[]`；GA lineage row只含`global-atom-id`、`provisional-final-change`、`provisional-final-capability`和`provisional-related-capabilities[]`。
- Change semantic digest row只含`final-change`、`sha256`；Capability semantic digest row只含`final-capability`、`sha256`。
- `completed-rows`与`pending-ids`都必须且只能包含`capability-reviews[]`、`change-reviews[]`、`unassigned-and-gap-reviews[]`、`atom-plan-mappings[]`。Completed arrays保存完整row，其中review row逐字段使用refit v3 shape、mapping row使用mapping v4 shape；pending arrays只保存对应input ID或GA。不得保留旧`gate-results`或gap owner/target字段。
- `allowed-update-scope`只含`global-atom-ids[]`、`initial-changes[]`、`initial-capabilities[]`、`final-changes[]`、`final-capabilities[]`和`allow-roadmap-reorder: false`。
- `preserved-row-digests[]` row只含`row-kind`、`row-key`、`sha256`；`patch-attempt`只含`attempt: 1`、`finding-fingerprint`、`authority-digest`。

Partition、scope closure、full-refit guard、fingerprint及resume/abort语义只见patch contract。

## Phase 5 framework refit v3、mapping v4 与 trace v4

Framework refit顶层必须且只能包含`trace-schema`、`trace-contract-version`、`status`、`initial-plan-ref`、`capability-reviews[]`、`change-reviews[]`、`unassigned-and-gap-reviews[]`、`final-framework`、`patch-history[]`、`issues[]`和`language-self-check`。`status`只允许`accepted|adjusted|needs-targeted-evidence-patch|blocked`；`initial-plan-ref`只含`artifact-path`、`sha256`。

Capability review row必须且只能包含`input-capability`、`evidence-collection-path`、`decision`、`final-capabilities[]`、`initial-gate-results[]`、`supporting-global-atom-ids[]`和简体中文`reason`。Decision只允许`keep|split|merge|remove|rename`。

Change review row必须且只能包含`input-change`、`evidence-collection-path`、`decision`、`final-changes[]`、`initial-gate-results[]`、`supporting-global-atom-ids[]`和简体中文`reason`。Decision只允许`keep|split|merge|remove|rename|reorder|scope-adjusted`。

每个`initial-gate-results[]` row只含`gate`、`result: passed|failed`和非空简体中文`note`。Capability gate固定按`domain-basis`、`purpose`、`behavior-first`、`cohesion`、`owns-excludes`、`implementation-substitution`、`archive-durability`、`delta-feasibility`完整覆盖；Change gate固定按`one-intent`、`scope-cohesion`、`independent-decision-archive`、`indivisibility`、`acceptance`、`implementation-readiness`完整覆盖。

Unassigned/gap review row必须且只能包含`global-atom-id`、`evidence-ref`、`framework-impact: none|supports-adjustment`和简体中文`reason`。不得包含`disposition`、`final-change`、`final-capability`或其他mapping字段。

Terminal `final-framework`只含`change-order[]`、`capabilities[]`和`overlay[]`；overlay row只含`change`、`capability`、`capability-impact: new|modified`。Nonterminal `needs-targeted-evidence-patch|blocked`按validator允许的surface使用`null`。

`patch-history[]`普通路径为`[]`。row只含`request-id`、`patch-request-ref`、`checkpoint-ref`、`finding-fingerprint`、`status: requested|closed|blocked`。needs patch时恰一条requested；resume terminal时同一条closed；失败时blocked。不得出现第二行。

Atom mapping v4顶层只含`trace-schema`、`trace-contract-version`、`artifact-path`、`rows[]`。每个GA恰好一行，且row只含`global-atom-id`、`evidence-ref`、`final-owner-change`、`final-relation`、`final-artifact-projection`、`final-capability-impact`、`final-target-capability`、`related-capabilities[]`和简体中文`reason`。

- Relation只允许`direct|context|dependency|preserve|reference|non-goal`。
- Direct projection只允许`spec-requirement|spec-guard|design-obligation|verification-obligation`；non-direct使用`contextual-only`。
- Direct spec/guard指定具体Capability和`new|modified`；其他row的impact/target按mapping contract使用`none`。
- Mapping row是final owner/relation/projection/target以及ambiguity resolution的唯一权威。Helper从refit JSON生成review mirror，并确定性生成mapping mirror、baseline、packet、Capability view、anchor index和packet index。

`phase-5.trace.json`使用`source-aligned-phase-5-trace-v4`。无patch的terminal状态必须使用`execution-mode: initial`、空patch history和null request/checkpoint字段；`needs-targeted-evidence-patch`必须使用`execution-mode: initial`、一条requested history并记录refit、review、request、checkpoint和issues，不得引用terminal artifact；checkpoint resume后的terminal状态必须使用`execution-mode: checkpoint-resume`、同一条closed history并绑定immutable request/checkpoint；patch lifecycle失败后的blocked状态必须使用`execution-mode: checkpoint-resume`、同一条blocked history并绑定immutable request/checkpoint。普通initial blocked不属于patch lifecycle，使用最小blocked trace且不伪造execution mode或patch引用。

## Renderer

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact all-supported \
  --write
```

支持Phase 2 atoms/index、Phase 3 global index/coverage review、Phase 4 assembler/index、Phase 5 refit review/mapping/baseline。所有mirror使用`source-aligned-render-v8`。

Phase 5 review mirror固定使用`Initial Gate Results`与`Supporting GAs`列；gap表只显示`Framework Impact`，不得显示final owner/target；输入ambiguity章节名固定为`Potential Mapping Ambiguities (Input)`并声明resolution只在mapping mirror。Renderer不得从Markdown恢复语义。

## Validation 与 handoff

- Validator检查schema、digest、ID、reference cardinality、frozen source quote、coverage complement、potential mapping ambiguity、protected/preserved row、checkpoint scope、render drift和跨artifact一致性。
- Phase 5 helper/validator由final Change order、direct spec/guard mapping与repository baseline执行唯一advancement推导，并拒绝mapping impact、refit/final plan overlay或baseline row的任一漂移。
- Phase 4 assembler/validator及Phase 5 helper不得读取source document；source quote验证只属于Phase 2/3及合法targeted patch。
- validator不检查semantic duplicate，也不因GA数量推断framework。
- Phase 2–5 validator失败即blocked，不得自动重启或重复当前Phase。
- final packet和plan必须声明它是完整evidence mapping，不是经过语义去重的requirement inventory。
