# Phase 4：确定性冻结原文集合组装

Phase 4在Phase 3 `coverage-complete`后运行。它通过evidence resolver读取Phase 2 atom和Phase 3 gap atom中已冻结的`source-fact`，按Phase 1 initial Change、initial Capability和`unassigned-and-gap`机械重排原文。本Phase不读取原始source document、不扩展source window、不执行framework判断。

writer必须完整读取`references/cross-phase-contract.md`、本文件和`references/trace-sidecar-contract.md`。Phase 4不加载Change/Capability共享原则，因为它不得执行refit。

## 输入

- Phase 1 `initial-change-plan.md`
- Phase 2 frozen source atom JSON
- Phase 3 `obligation-atom-index.json`
- Phase 3 `coverage-review.json`

不得读取原始source document，也不得依赖旧Phase 4 source-window artifact或旧index决定collection内容。

## 输出与权威

```text
phase-works/phase-4/
├── source-evidence-collections/
│   ├── evidence-collection-index.json
│   ├── index.md
│   ├── by-input-change/<change>.md
│   ├── by-input-capability/<capability>.md
│   └── unassigned-and-gap.md
└── phase-4-agent-report.md

trace/phase-4.trace.json
```

evidence collection Markdown是Phase 4内容权威，但必须由确定性assembler直接从Phase 1–3生成，不允许人工补写。`evidence-collection-index.json`在Markdown全部生成后创建，只是用于检索、digest和映射校验的派生机器索引。agent report是非canonical流程证据，不进入manifest。Phase 4不创建reviewer/repair report。

禁止创建或保留：`input-change-plan.md`、`source-window-dossiers/`、`source-window-semantic-profile-review.md`、`source-window-grounding-issues.md`。

## Evidence resolver

对global index中的每个GA：

- `phase-2-source-atom`：从对应Phase 2 JSON加载source document、唯一range、`source-fact`、atom type、normativity、candidate status/projection/owner/target。
- `phase-3-gap-atom`：从Phase 3 coverage review加载source document、唯一range、`source-fact`、atom type、normativity和review judgment。

Phase 4信任经过Phase 2/3 validator冻结的`source-fact`，不按range重新读取source。resolver ref不存在、重复或类型不匹配时不得猜测或重新提取；记录issue并`blocked`。

## Assembler固定顺序

assembler必须：

1. 读取并解析Phase 1 initial Change/Capability集合及顺序。
2. 解析Phase 3 global index中的全部GA/evidence ref，并通过resolver逐一验证。
3. 按以下机械规则计算Change、Capability和unassigned/gap bucket。
4. 生成`index.md`、全部initial Change/Capability collection和`unassigned-and-gap.md`。
5. 检查每个GA的collection path、原文fence及空集合。
6. 最后生成派生`evidence-collection-index.json`。

不得先写index再从index渲染Markdown。

## Bucket规则

`change-bucket`：

- Phase 2 `candidate-owner-change`精确引用Phase 1 Change：使用该Change slug。
- 其他Phase 2 atom：使用`unassigned-and-gap`。
- 所有Phase 3 gap atom：使用`unassigned-and-gap`。

`capability-bucket`：

- Phase 2 `candidate-target-capability`精确引用Phase 1 Capability：使用该Capability slug。
- 其他Phase 2 atom和所有Phase 3 gap atom：使用`none`。

Phase 4不得根据语义修正candidate hint。一个GA在Change维度只有一个primary bucket；它可以同时投影到一个Capability collection，但不产生final ownership或Capability advancement。

## Markdown collection要求

assembler必须：

- 从Phase 1 plan取得Change intent/outcome和Capability Purpose/Owns/Excludes；
- 从resolver取得冻结的`source-fact`；
- 按source document、range起点、GA ID稳定排序；
- 使用长度大于原文最大连续反引号长度的code fence，使fence内部文本逐字符不变；
- 显示GA、evidence ref、source path/range、type、normativity和Phase 2 candidate metadata或Phase 3 gap provenance；
- 为每个Phase 1 Change/Capability生成collection；没有GA时明确写`无关联 evidence occurrence`；
- 在`unassigned-and-gap.md`中区分Phase 2 unassigned、unresolved/contextual和Phase 3 gap atom；
- 保留每个evidence occurrence，绝不合并语义相同或原文相同的GA。

运行：

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact phase4-evidence-collections \
  --write
```

## 派生index v2

`evidence-collection-index.json`使用`source-aligned-evidence-collection-index-v2`，顶层必须且只能包含：

- `trace-schema`
- `trace-contract-version`
- `generated-from[]`
- `rows[]`
- `rendered-artifacts[]`

`generated-from[]`每行包含`artifact-path`和`sha256`。

`rows[]`每行必须且只能包含：

- `global-atom-id`
- `evidence-ref`
- `change-bucket`
- `capability-bucket`
- `rendered-collection-paths[]`

`rendered-artifacts[]`每行必须且只能包含：

- `artifact-path`
- `sha256`
- `collection-kind`
- `owner-id`

每个GA恰好一行，`evidence-ref`与global index完全相同。index不得复制source fact、path、range、type、normativity或candidate metadata。

## Incremental deterministic refresh

`update-mode: incremental-patch`只在唯一targeted patch链中使用：

- 输入必须包含有效`EPR-0001`、`P5CP-0001`和Phase 3 incremental result；
- assembler仍从当前Phase 1–3 authority确定性生成内容，不读取checkpoint取得语义；
- 未受影响`phase-4-index-rows`与`phase-4-rendered-artifacts`必须通过request的protected row digest；
- 只有changed/new GA所进入的collection及其index digest允许变化；不得修改bucket规则或解读mapping ambiguity；
- Phase 4 bucket只使用Phase 1 identity；受影响Change/Capability bucket必须分别属于checkpoint的`initial-changes[]`、`initial-capabilities[]`，不得用同名final scope绕过initial review scope；
- 可为实现确定性一致性重写文件，但语义变化必须严格落在受影响collection集合。

## Status与trace v4

- `assembled`：resolver成功，全部Markdown和派生index已生成且无drift。
- `blocked`：Phase 2/3 artifact或digest冲突，无法建立可信resolver结果。

terminal trace使用`source-aligned-phase-4-trace-v4`，顶层包含schema/version、`status: assembled`、`update-mode: initial|incremental-patch`、`patch-request-ref`、`checkpoint-ref`、`base-evidence-collection-index-sha256`、`affected-closure`和`assembled` object；assembled记录index path/SHA及`renderer-result-summary`。`affected-closure`只包含`global-atom-ids[]`、`change-buckets[]`、`capability-buckets[]`、`rendered-artifact-paths[]`。initial mode的ref/base为null且closure各array为空；incremental-patch时必须记录有效base与受影响closure。

blocked trace包含schema/version、status、update-mode、request/checkpoint ref、base index digest、已知`affected-closure`和非空`issues[]`。initial blocked的ref/base为null且closure为空；incremental blocked必须保留immutable ref与已知影响范围、清理未完成的terminal index/collection，再由main agent调用`phase5_plan_refit.py --abort-patch-chain --issue ...`机械关闭Phase 5唯一history。该control transform不得改写semantic row；abort validation不得依赖已清理的Phase 4 surface，也不得自动重跑assembler或回到其他Phase。

Phase 4不得记录split、merge、rename、reorder、boundary、owner、projection、relation或Capability impact判断。

## 完成条件

- collection Markdown、派生index、trace和非canonical agent report存在；
- validator从Phase 1–3重算全部Markdown和index且无drift；
- validator拒绝缺失、篡改、stale文件、GA基数错误、上游digest drift及`source-fact`变化；
- empty initial unit collection存在，bucket机械正确且没有refit判断；
- validator通过；失败即`blocked`，不得启动reviewer/repair、自动重启assembler或重复Phase 4。
