# Phase 3：覆盖闭合、GA identity 与 mapping ambiguity

Phase 3 检查 Phase 2 extraction 对 source 行范围的覆盖情况，从 uncovered range 补提取遗漏 obligation，为每个 evidence occurrence 分配稳定 GA，并以 GA 为键记录 mapping ambiguity。它不规范化语义、不规划 Change/Capability、不裁决 mapping，也不处理 semantic duplicate。

writer 必须直接完整读取 `references/cross-phase-contract.md`、本文件和 `references/trace-sidecar-contract.md`。

## 输入

- `phase-works/phase-1/source-doc-manifest.md`
- `phase-works/phase-2/source-obligation-atoms/<source>.atoms.json`
- 用户指定的 source document
- `scripts/phase3_line_range_audit.py`（必须用于合并 covered range 和计算 complement）
- `update-mode: incremental-patch` 时还必须读取唯一 `source-aligned-evidence-patch-request-v1`、`source-aligned-phase-5-checkpoint-v1` 和 `source-aligned-phase-2-trace-v4` 的 targeted-patch evidence。

Phase 2 Markdown mirror 只用于 review；canonical extraction evidence 是 `.atoms.json`。

writer 必须执行随技能提供的 `scripts/phase3_line_range_audit.py`，不得手工计算 complement，不得用模型推理、临时脚本或其他等价实现替代。脚本 stdout 是 Phase 3 covered/complement range 的唯一 writer 输入；validator 仍须独立机械重算并检查 drift。

## 固定输出

Phase 3 只保留以下五个 artifact：

- `change-capability-anchors/obligation-atom-index.json`
- `change-capability-anchors/obligation-atom-index.md`
- `phase-works/phase-3/coverage-review.json`
- `phase-works/phase-3/coverage-review.md`
- `trace/phase-3.trace.json`

不得创建逐文档 coverage、Phase 3 manifest 副本、source-to-global map、remainder review、duplicate review、normalization log 或 agent report。现有旧 Phase 3 canonical artifact 必须删除；validator 会拒绝旧布局。

## 执行顺序

1. 从 Phase 1 manifest 取得全部 `read-full` source。
2. 验证每份 source 恰好有一个有效 Phase 2 atom JSON，且 source/artifact digest 当前有效。
3. 必须执行以下命令，由脚本对每份 source 合并 Phase 2 atom 的 `line-ranges[]` 并计算 `L1..line-count` 的 complement：

   ```bash
   python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase3_line_range_audit.py \
     --orchestrate-dir openspec/orchestrate \
     --workspace-root . \
     --pretty
   ```

   将 stdout `documents.<source>.merged_covered_ranges` 原样转换为 `documents[].covered-ranges[]`，将 `documents.<source>.candidate_uncovered_ranges` 原样转换为 `documents[].candidate-uncovered-ranges[]`；只允许进行 tuple/list 到 `{start, end}` 的结构转换，不得修改、补算或重新解释 range。若脚本失败、source 不存在、存在 malformed row，或脚本结果无法覆盖全部 `read-full` source，返回 `blocked`。
4. 按稳定顺序为每个 Phase 2 source atom 一对一分配 `GA-####`。
5. 只阅读 candidate uncovered range及理解该 range 所需的最小局部上下文。
6. 对 uncovered range 中遗漏的 production obligation 创建 `P3-GAP-####`，再为每个 gap atom分配一个独立 GA。
7. 将其余 uncovered range分类为 `safe-non-obligation` 或 `blocked`；遗漏 obligation 使用 `missing-obligation` 并链接 gap atom。
8. 为每个GA检查 extraction-time hint 是否存在 mapping ambiguity；只记录 ambiguity dimensions 和 reason，不填写 final mapping。若观察到一个冻结atom可能承载多个独立responsibility：单一tuple无法无损表达时只按实际维度记录ambiguity；仍共享唯一tuple时不得为传递finding伪造ambiguity row。两种情况都不得在本Phase定性evidence defect、发起patch或仅因此`blocked`，最终分类留给Phase 5的全GA检查。
9. `update-mode: incremental-patch` 时验证 request/checkpoint、Phase 2 before/after row及全部protected row，只更新request影响的document/gap/disposition/ambiguity/global index row；未受影响GA和ambiguity row必须保持identity与row digest。
10. 写入coverage decision和`language-self-check`，并用v7 renderer生成两个Markdown mirror。validator失败时返回`blocked`，不得自动重启writer或重复Phase 3。

## 明确禁止

Phase 3 不得：

- 比较两个 atom 的语义是否相同；
- 选择 canonical atom；
- 判断 duplicate/refinement/preserve/dependency relation；
- 拆分或修改 frozen Phase 2 atom；只有 Phase 2 targeted patch writer 可以执行 request 明确允许的操作；
- 把疑似mixed occurrence定性为patch defect、发起patch，或为传递该finding伪造mapping ambiguity；
- 判断 owner Change、artifact projection、Capability impact/target/related Capability；
- 把 Phase 2 `source-fact` 复制到任何 Phase 3 artifact；
- 因 GA 数量或重复 evidence 数量触发 complexity、split、merge 或回补。

## Global atom index v3

`source-aligned-global-atom-index-v3` 顶层字段：

- `trace-schema`
- `trace-contract-version`
- `artifact-path`
- `global-atoms[]`

每个 `global-atoms[]` row 必须且只能包含：

- `global-atom-id`
- `evidence-ref`

Phase 2 evidence ref：

```json
{
  "kind": "phase-2-source-atom",
  "source-document": "docs/source.md",
  "source-atom-id": "SA-0001"
}
```

Phase 3 gap evidence ref：

```json
{
  "kind": "phase-3-gap-atom",
  "gap-atom-id": "P3-GAP-0001"
}
```

每个 Phase 2 atom和 gap atom恰好被一个 GA 引用。语义相同、原文相同或范围重叠都不改变这一 identity rule。Markdown 只显示 GA 与 evidence reference。

## Coverage review v2

`source-aligned-phase-3-coverage-review-v2` 顶层字段：

- `trace-schema`
- `trace-contract-version`
- `artifact-path`
- `documents[]`
- `gap-atoms[]`
- `remainder-dispositions[]`
- `mapping-ambiguities[]`
- `summary`
- `decision`
- `language-self-check`

`documents[]` 每份 `read-full` source 一行，且只包含：

- `source-document`
- `source-sha256`
- `line-count`
- `phase-2-atom-path`
- `phase-2-atom-sha256`
- `covered-ranges[]`
- `candidate-uncovered-ranges[]`

这些字段保存 digest 和机械 range，不复制 Phase 2 extraction 内容。

`gap-atoms[]` 只保存 uncovered range 中新增的 extraction：

- `gap-atom-id`，格式 `P3-GAP-####`
- `source-document`
- 长度为 1 的 `line-ranges[]`
- 原文连续摘录 `source-fact`
- `atom-type`
- `normativity`
- 简体中文 `review-judgment`

`remainder-dispositions[]` 每行包含：

- `disposition-id`，格式 `RD-####`
- `source-document`
- `line-ranges[]`
- `classification`
- `linked-gap-atom-ids[]`
- 简体中文 `reason`

classification 只允许：

- `missing-obligation`：必须链接至少一个位于该 range 内的 gap atom；
- `safe-non-obligation`：不得链接 gap atom；
- `blocked`：缺少 source、范围不可信或无法在授权边界内判断。

每个 candidate uncovered range 必须被 disposition range 完整覆盖；每个 gap atom必须由且只由一个 `missing-obligation` disposition 链接。

`mapping-ambiguities[]` 以 `global-atom-id` 为唯一键，每行必须且只能包含：

- `global-atom-id`
- `evidence-ref`
- `dimensions[]`
- 简体中文 `reason`

`dimensions[]` 为非空唯一数组，只允许 `owner-change`、`relation`、`artifact-projection`、`target-capability`。row不得包含候选值、final value、Change/Capability建议或resolution。

只有当一个evidence occurrence无法由唯一mapping tuple（owner-change、relation、artifact-projection、target-capability）无损表达，或该tuple的至少一个维度存在多个合理取值时才记录。`unassigned`、gap、source-fact长度、GA数量或candidate hint缺失都不是自动判据。一个GA最多一行；`evidence-ref`必须与global index逐字一致。source语义本身冲突不是mapping ambiguity，必须`blocked`。

`summary` 必须包含 `source-documents`、`phase-2-atoms`、`gap-atoms`、`global-atoms`、`mapping-ambiguities`、`candidate-uncovered-ranges`，以及 `remainder-dispositions` object；后者必须给出三种 classification 的计数。所有计数由 validator重算，GA count仅是 trace volume。

## Decision

只允许：

- `coverage-complete`：所有 source/artifact/digest 有效；每个 uncovered range 已补提取或安全分类；没有 blocker。mapping ambiguity可以非空。
- `blocked`：存在 `blocked` disposition、source/artifact 缺失、digest/range 无法验证，或需要用户决定。

semantic duplicate 的存在与数量不影响 decision。

## Trace 与 renderer

`source-aligned-phase-3-trace-v3` 必须包含：

- `decision`
- `global-atom-index-path` / `global-atom-index-sha256`
- `coverage-review-path` / `coverage-review-sha256`
- `update-mode: initial|incremental-patch`
- `patch-request-ref` / `checkpoint-ref`：initial时为`null`；incremental-patch时各只包含artifact path与SHA。
- `base-global-atom-index-sha256` / `base-coverage-review-sha256`：initial时为`null`。
- `affected-source-documents[]`
- `new-global-atom-ids[]`

Phase 3不创建reviewer/repair report，不写reviewer identity。initial mode的两个array为空；`update-mode: incremental-patch`必须保留所有未列入request影响范围的GA与mapping ambiguity row，新occurrence按request target及其new-ID顺序在当前最大GA之后连续追加，禁止全量重编号。validator只能pass或使Phase 3 `blocked`。

`blocked` trace不伪装成功产物，必须且只能包含schema/version、`decision: blocked`、`update-mode`、request/checkpoint ref、两个base digest、`affected-source-documents[]`、`new-global-atom-ids[]`和非空`issues[]`。incremental blocked必须保留immutable引用与已知affected/new identity，然后由main agent调用`phase5_plan_refit.py --abort-patch-chain --issue ...`机械关闭Phase 5同一patch history；不得手写semantic refit或重跑Phase 3。

渲染命令：

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact phase3-global-index --write
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact phase3-coverage-review --write
```

writer 最终只向 main agent 简要报告 decision、gap atom数量、mapping ambiguity数量、incremental affected source和 blocker；不额外创建报告文件。

coverage mirror必须把`covered-ranges[]`和`candidate-uncovered-ranges[]`中的每个`{start,end}`机械显示为`Lx-Ly`，并呈现逐GA mapping ambiguity与`language-self-check`。validator对global index和coverage review两个mirror逐字重渲染比较。
