# Trace sidecar contract

本技能采用 Phase-specific authority。JSON用于精确校验、检索、增量保护和跨产物映射，但并非每个Phase的内容权威；Markdown是否为权威由下表决定。

## 全局版本与权威边界

- trace contract：`source-aligned-trace-v3`
- render contract：`source-aligned-render-v7`
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

`source-aligned-evidence-patch-request-v1`是control authority，只授权并保护一次增量回补。`source-aligned-phase-5-checkpoint-v1`是nonterminal semantic authority，保存provisional framework和completed semantic row；两者都不是source或terminal final plan authority。

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
- `source-aligned-framework-refit-trace-v2`
- `source-aligned-atom-plan-mapping-v4`
- `source-aligned-capability-baseline-v1`
- `source-aligned-final-packet-index-v2`
- `source-aligned-evidence-patch-request-v1`
- `source-aligned-phase-5-checkpoint-v1`

## Manifest v2

`trace/manifest.json`继续使用`source-aligned-orchestrate-manifest-v2`，顶层必须且只能包含`trace-schema`、`trace-contract-version`、`authority: control`、`orchestrate-dir`、`phase-statuses`和`artifacts[]`。

每个artifact row必须且只能包含`json-path`、`trace-schema`、`sha256`、`phase`、`role`和`authority`。

`authority`枚举：

- `semantic`：Phase 2 atoms、Phase 3 global index/coverage review、Phase 5 refit trace/mapping，以及存在时的Phase 5 checkpoint。
- `derived`：Phase 4 index、Phase 5 baseline/packet index。
- `control`：各Phase trace及可选evidence patch request；manifest自身通过顶层`authority`声明，不自列。

Markdown不进入manifest。manifest只列当前存在且应登记的JSON，每份恰好一次；每次validator前刷新digest，validator pass后刷新Phase status。Phase 1/2读取trace`status`，Phase 3读取`decision`，Phase 4/5读取`status`。

Phase 2–5 validator只能pass或使Phase blocked；失败不得自动重启producer、就地修正后重验或重复当前Phase。唯一例外是Phase 5已合法发布request/checkpoint后按固定状态机执行一次targeted patch。

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

## Phase 2 trace v4 与 JSON 渲染

`phase-2.trace.json`保留既有字段，并新增`mode`、`patch-request-ref`、`checkpoint-ref`和`patch-summary`；成功terminal status始终为`source-atoms-written`，失败终止使用`blocked`。

- `mode`只允许`initial|targeted-patch`。
- initial mode的两个ref和summary均为null。
- targeted-patch mode的两个ref都只包含`artifact-path`、`sha256`；`patch-summary`必须且只能包含`base-phase-2-trace-sha256`、`affected-sources[]`、`changed-atoms[]`、`new-atoms[]`和`patch-writer-id`。
- `changed-atoms[]`每行只含`source-document`、`source-atom-id`、`before-row-sha256`、`after-row-sha256`；`new-atoms[]`每行只含`source-document`、`source-atom-id`、`row-sha256`。
- targeted mode只能消费`EPR-0001`，不得产生第二个成功terminal status。
- extraction、patch或validator无法在授权边界内完成时使用`status: blocked`。blocked trace必须且只能包含schema/version、status、mode、request/checkpoint refs、nullable `base-phase-2-trace-sha256`、`affected-sources[]`和非空`issues[]`：initial mode的refs/base为null且affected为空；targeted-patch mode必须绑定request/checkpoint，base digest等于request中的`base-artifacts.phase-2-trace-sha256`，affected sources按request target首次出现顺序精确覆盖。不得触发重跑。
- 每份`.atoms.md`完全由对应`.atoms.json`渲染；`index.md`由work queue、全部atoms JSON和Phase trace聚合渲染；validator逐字重渲染比较。

## Phase 3 coverage review v2 与 trace v3

coverage review顶层必须且只能包含`trace-schema`、`trace-contract-version`、`artifact-path`、`documents[]`、`gap-atoms[]`、`remainder-dispositions[]`、`mapping-ambiguities[]`、`summary`、`decision`和`language-self-check`。

`mapping-ambiguities[]`每行必须且只能包含`global-atom-id`、`evidence-ref`、`dimensions[]`和简体中文`reason`。`global-atom-id`是唯一键；dimensions只允许`owner-change`、`relation`、`artifact-projection`、`target-capability`，不得包含final value。

remainder classification只允许`missing-obligation`、`safe-non-obligation`和`blocked`。mapping ambiguity非空不阻止`coverage-complete`。

`phase-3.trace.json`保留原paths/digests，并新增`update-mode`、`patch-request-ref`、`checkpoint-ref`、`base-global-atom-index-sha256`、`base-coverage-review-sha256`、`affected-source-documents[]`和`new-global-atom-ids[]`，不包含reviewer字段。initial mode的ref、base digest为null且两个array为空；incremental-patch mode必须引用request/checkpoint及base digest。未受影响GA/ambiguity row保持identity与row digest，新GA只在当前最大ID后追加。

global index与coverage review Markdown完全由对应JSON渲染；coverage mirror必须呈现mapping ambiguities。validator对两个mirror逐字重渲染比较。

## Phase 4 assembler、index v2 与 trace v4

Phase 4 assembler只读Phase 1 initial plan、Phase 2 atoms JSON、Phase 3 global index/coverage review，解析全部GA/evidence ref、机械计算bucket、生成所有collection Markdown，最后生成派生index。不得从index反向生成Markdown，不得读取source、裁决mapping ambiguity或引入framework判断。

`evidence-collection-index.json`顶层只包含`trace-schema`、`trace-contract-version`、`generated-from[]`、`rows[]`和`rendered-artifacts[]`。每个GA恰好一行。

`phase-4.trace.json`使用`source-aligned-phase-4-trace-v4`。terminal字段为既有`status: assembled`与`assembled`，加`update-mode`、`patch-request-ref`、`checkpoint-ref`、`base-evidence-collection-index-sha256`和`affected-closure`。`affected-closure`必须且只能包含`global-atom-ids[]`、`change-buckets[]`、`capability-buckets[]`和`rendered-artifact-paths[]`。initial mode的ref/base为null且closure各array为空；incremental-patch mode必须验证base与protected Phase 4 row，只有closure列出的collection允许语义变化。由于Phase 4只投影Phase 1 identity，change/capability buckets只能由checkpoint `initial-changes[]`/`initial-capabilities[]`授权，不能使用同名final scope。

Phase 3/4 incremental `blocked` trace保留各自mode、request/checkpoint ref、base digest、已知affected source/new GA或affected closure以及非空issues，不引用成功态artifact digest。随后main agent只调用`phase5_plan_refit.py --abort-patch-chain --issue ...`执行机械control transform：request/checkpoint字节不变，只把refit `status`改为`blocked`、替换`issues[]`并把唯一history row的`status`从`requested`改为`blocked`；该transform不是semantic writer或完整refit。其static snapshot validation与blocked review渲染都不读取已失败、损坏或已清理的current Phase 3/4 surface，也不重新比较current Phase 1/principles fingerprint；fingerprint drift可直接作为blocked原因。blocked review的mapping ambiguity展示可以为空，request/checkpoint仍是static authority。

validator从Phase 1–3重新计算全部Markdown和派生index并检查缺失、篡改、stale文件、GA基数、上游digest和`source-fact`逐字一致性。失败即`blocked`。

## Evidence patch request v1

顶层必须且只能包含`trace-schema`、`trace-contract-version`、`request-id`、`base-artifacts`、`targets`、`protected-rows`；`request-id`固定`EPR-0001`。

`base-artifacts`必须且只能包含：

- `phase-2-trace-sha256`
- `phase-3-trace-sha256`
- `global-atom-index-sha256`
- `coverage-review-sha256`
- `phase-4-index-sha256`

target必须且只能包含`source-document`、nullable `source-atom-id`、nullable `global-atom-id`、nullable `evidence-ref`、`defect`、`allowed-operations[]`、`allowed-line-window`、`new-source-atom-ids[]`、nullable `base-row`、nullable `base-row-sha256`、`canonical-owner`、简体中文`reason`和`defect-witness`。`allowed-line-window`只包含`start`、`end`。existing target的`base-row`保存patch前完整source atom row，SHA必须匹配；missing occurrence两者均为null。patch后target row只有allowed operation对应的`source-fact`/`line-ranges`可变化。

`defect-witness`必须且只能包含`locator-origin`、`source-sha256`和`window-sha256`；`locator-origin`必须且只能包含非空`row-refs[]`。每个row ref必须且只能包含`artifact-path`、`row-kind`、`row-key`、`row-sha256`，`row-kind`只允许`phase-2-atom|phase-3-disposition`。Phase 2 key固定`<source-document>::<source-atom-id>`并指向canonical atoms JSON；Phase 3 key固定disposition ID并指向canonical coverage review JSON。row ref必须指向同一source的immutable canonical row且digest匹配；existing target必须包含自身`base-row`的`phase-2-atom` origin；missing target不得用已由gap承接的`missing-obligation` disposition伪造遗漏。`allowed-line-window`必须完全位于全部origin line ranges合并后的连续闭包内，不得借witness扩窗。`source-sha256`绑定完整冻结source；`window-sha256`绑定该1-based window按LF连接且无尾随LF的UTF-8字节。

request前的defect verification只允许读取由`defect-witness`预先固定的`allowed-line-window`一次；request digest随后冻结该locator。validator要求当前source SHA与Phase 1/2冻结值一致、existing base range位于window内，且base quote仍为该range内的原文substring。`quote-mismatch`只表示该substring选择错误或截断；非原文Phase 2 base直接`blocked`，不得借request洗白。核验窗口不构成新authority，实际patch extraction仍只由Phase 2 targeted writer完成。

defect只允许`quote-mismatch`、`range-mismatch`、`mixed-independent-occurrences`、`missing-occurrence`；operation只允许`replace-quote`、`adjust-range`、`split`、`add`。missing只能add且旧identity字段为null；split新ID从`<old>.part-02`起，add新ID从`patch-epr-0001-add-01`起。禁止删除、合并或重命名。

`protected-rows`必须且只能包含`phase-2-atoms`、`phase-3-documents`、`phase-3-gap-atoms`、`phase-3-dispositions`、`phase-3-mapping-ambiguities`、`global-atoms`、`phase-4-index-rows`和`phase-4-rendered-artifacts`。每行保存对应稳定key字段与SHA256；除target/new GA外的既有mapping ambiguity row必须全部保护，不能因source range与patch window重叠而漏列。Phase 4 rendered rows必须恰好保护target old/new bucket之外的collection，不得通过漏列扩大closure。

## Phase 5 checkpoint v1

顶层必须且只能包含`trace-schema`、`trace-contract-version`、`checkpoint-id`、`stage`、`patch-request-ref`、`input-fingerprints`、`provisional-framework`、`completed-rows`、`pending-ids`、`allowed-update-scope`、`preserved-row-digests`和`patch-attempt`。

- `checkpoint-id`固定`P5CP-0001`；evidence patch checkpoint的`stage`必须严格为`mapping`，表示全局Capability、Change、unassigned/gap review和mapping已完成，只允许恢复局部影响闭包。
- patch request ref只含`artifact-path`、`sha256`；input fingerprint每行只含`artifact-path`、`sha256`。input fingerprints只锁定patch期间不得变化的authority，至少为Phase 1 initial plan与共享framework principles，可含repository baseline；不得把patch后应变化的Phase 2/3/4整文件digest作为相等条件。
- provisional framework包含terminal framework的`change-order`、`capabilities`、`overlay`，以及`dependency-edges[]`、`change-lineage[]`、`capability-lineage[]`、`ga-lineage[]`和按相同顺序完整覆盖每个final ID的`change-semantic-digests[]`、`capability-semantic-digests[]`。dependency edges冻结provisional hard dependency；review lineage按Phase 1顺序绑定每个initial review unit与其provisional final IDs；GA lineage按GA顺序绑定existing GA与provisional final Change/Capability/related Capability，恰好覆盖patch前GA且与completed mapping一致；digest绑定完整Change/Capability语义，不能只保护ID和overlay。
- completed rows与pending IDs都只含`capability-reviews[]`、`change-reviews[]`、`unassigned-and-gap-reviews[]`、`atom-plan-mappings[]`；每一类分别完整且不相交地划分对应review/mapping全集。pending capability、change、mapping、unassigned/gap必须分别精确等于`allowed-update-scope.initial-capabilities[]`、`allowed-update-scope.initial-changes[]`、`allowed-update-scope.global-atom-ids[]`、以及scope GA与Phase 4 unassigned/gap GA（含确定性预分配后仍属该bucket的新GA）的交集；不得把scope外row标为pending。
- allowed update scope只含`global-atom-ids[]`、`initial-changes[]`、`initial-capabilities[]`、`final-changes[]`、`final-capabilities[]`、`allow-roadmap-reorder: false`。initial review scope非空时必须由target的Phase 4 initial bucket发起，并恰好等于所选root经initial与provisional overlay/hard-dependency边形成的最小连通闭包；provisional边通过lineage反向投影到initial review unit。final scope采用old/new集合语义：既有provisional ID可保留或删除，其initial origins必须全在initial scope；若无initial origin，则必须有非空GA lineage且全部origin GA在GA scope。全新ID可在initial scope为空时预声明，但terminal必须且只能由pending initial review、unassigned review或mapping实际产生/引用。只有两个endpoint都在mutable closure内的overlay或dependency edge才允许变化。
- scope GA必须恰好为target/new GA；full-refit guard分别检查initial Change、provisional final Change、initial Capability、provisional final Capability四个typed universe，并额外检查initial/provisional并集。scope完整覆盖任一非空universe即blocked；既不能漏掉remove/rename前的initial ID，也不能借已remove initial unit放行对全部current finals的重写。
- preserved row digest每行只含`row-kind`、`row-key`、`sha256`。
- patch attempt只含`attempt: 1`、`finding-fingerprint`、`authority-digest`；authority digest机械绑定`input-fingerprints`、`patch-request-ref`和`provisional-framework`组成的compact sorted JSON。finding fingerprint从request target的source/atom/GA/evidence-ref、defect、line window以及witness的source/window digest规范化计算，不包含reason、operation、successor ID或writer identity。

patch前Phase 2–4 digest只由request base-artifacts保存，未受影响内容由protected/preserved row digest证明。request只可从Phase 2–4 initial success snapshot且canonical Phase 5 trace尚不存在的首次执行发出；任何terminal、blocked、closed或incremental状态不得重放为requested。resume必须复用fingerprint有效且不在allowed scope内的completed row；不得全量refit、reorder roadmap或生成第二个request。

## Phase 5 framework refit v2、mapping 与 trace v4

framework refit顶层在既有review/final-framework字段外只增加`patch-history[]`，不得复制final mapping。每个Phase 3 ambiguity GA必须在terminal atom mapping v4中恰好一行且evidence ref一致；validator按`dimensions[]`检查对应final字段，该mapping row是唯一resolution。

`patch-history[]`普通路径为`[]`。row只含`request-id`、`patch-request-ref`、`checkpoint-ref`、`finding-fingerprint`、`status: requested|closed|blocked`。needs patch时恰一条requested；resume terminal时同一条closed；失败时blocked。不得出现第二行。

atom mapping v4仍是final mapping语义权威，每个GA恰好一行。helper从refit JSON生成review mirror，并确定性生成mapping mirror、baseline、packet、Capability view、anchor index和packet index；不得从review Markdown取得语义。

`phase-5.trace.json`使用`source-aligned-phase-5-trace-v4`。无patch的terminal状态必须使用`execution-mode: initial`、空patch history和null request/checkpoint字段；`needs-targeted-evidence-patch`必须使用`execution-mode: initial`、一条requested history并记录refit、review、request、checkpoint和issues，不得引用terminal artifact；checkpoint resume后的terminal状态必须使用`execution-mode: checkpoint-resume`、同一条closed history并绑定immutable request/checkpoint；patch lifecycle失败后的blocked状态必须使用`execution-mode: checkpoint-resume`、同一条blocked history并绑定immutable request/checkpoint。普通initial blocked不属于patch lifecycle，使用最小blocked trace且不伪造execution mode或patch引用。

## Renderer

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact all-supported \
  --write
```

支持Phase 2 atoms/index、Phase 3 global index/coverage review、Phase 4 assembler/index、Phase 5 refit review/mapping/baseline。

## Validation 与 handoff

- validator检查schema、digest、ID、reference cardinality、frozen source quote、coverage complement、mapping ambiguity、protected/preserved row、checkpoint scope、render drift和跨artifact一致性。
- Phase 4 assembler/validator及Phase 5 helper不得读取source document；source quote验证只属于Phase 2/3及合法targeted patch。
- validator不检查semantic duplicate，也不因GA数量推断framework。
- Phase 2–5 validator失败即blocked，不得自动重启或重复当前Phase。
- final packet和plan必须声明它是完整evidence mapping，不是经过语义去重的requirement inventory。
