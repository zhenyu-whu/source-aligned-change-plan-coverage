# Phase 3：纯覆盖审计与遗漏补提取

Phase 3 只检查 Phase 2 extraction 对 source 行范围的覆盖情况，并从 uncovered range 补提取遗漏 obligation。它不规范化语义、不规划 Change/Capability，也不处理 semantic duplicate。

writer 必须直接完整读取 `references/cross-phase-contract.md`、本文件和 `references/trace-sidecar-contract.md`。

## 输入

- `phase-works/phase-1/source-doc-manifest.md`
- `phase-works/phase-2/source-obligation-atoms/<source>.atoms.json`
- 用户指定的 source document
- `scripts/phase3_line_range_audit.py` 或等价机械补集计算

Phase 2 Markdown mirror 只用于 review；canonical extraction evidence 是 `.atoms.json`。

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
3. 对每份 source 合并 Phase 2 atom 的 `line-ranges[]`，机械计算 `L1..line-count` 的 complement。
4. 按稳定顺序为每个 Phase 2 source atom 一对一分配 `GA-####`。
5. 只阅读 candidate uncovered range及理解该 range 所需的最小局部上下文。
6. 对 uncovered range 中遗漏的 production obligation 创建 `P3-GAP-####`，再为每个 gap atom分配一个独立 GA。
7. 将其余 uncovered range分类为 `safe-non-obligation`、`requires-reextract` 或 `blocked`；遗漏 obligation 使用 `missing-obligation` 并链接 gap atom。
8. 如果上游 reviewer、validator 或当前机械证据指出 Phase 2 atom broad，记录 targeted recheck source/atom/range，返回 `needs-extraction-recheck`。Phase 3 不读取该 covered range做拆分。
9. 写入 coverage decision，并用 renderer 生成两个 Markdown mirror。

## 明确禁止

Phase 3 不得：

- 比较两个 atom 的语义是否相同；
- 选择 canonical atom；
- 判断 duplicate/refinement/preserve/dependency relation；
- 拆分 broad Phase 2 atom或修改 frozen Phase 2 artifact；
- 判断 owner Change、artifact projection、Capability impact/target/related Capability；
- 把 Phase 2 `source-fact` 复制到任何 Phase 3 artifact；
- 因 GA 数量或重复 evidence 数量触发 complexity、split、merge 或 recheck。

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

## Coverage review v1

`source-aligned-phase-3-coverage-review-v1` 顶层字段：

- `trace-schema`
- `trace-contract-version`
- `artifact-path`
- `documents[]`
- `gap-atoms[]`
- `remainder-dispositions[]`
- `recheck-sources[]`
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
- `requires-reextract`：当前 uncovered range表明 Phase 2 extraction 需要重做；
- `blocked`：缺少 source、范围不可信或无法在授权边界内判断。

每个 candidate uncovered range 必须被 disposition range 完整覆盖；每个 gap atom必须由且只由一个 `missing-obligation` disposition 链接。

`recheck-sources[]` 用于 targeted broad/re-extraction finding，每行包含：

- `source-document`
- `source-atom-ids[]`
- `line-ranges[]`
- 简体中文 `reason`

`summary` 必须包含 `source-documents`、`phase-2-atoms`、`gap-atoms`、`global-atoms`、`candidate-uncovered-ranges`，以及 `remainder-dispositions` object；后者必须给出四种 classification 的计数。所有计数由 validator重算，GA count仅是 trace volume。

## Decision

只允许：

- `coverage-complete`：所有 source/artifact/digest 有效；每个 uncovered range 已补提取或安全分类；没有 recheck 或 blocker。
- `needs-extraction-recheck`：存在 `requires-reextract` 或 `recheck-sources[]`，且没有 blocker。main agent 必须 targeted 重跑对应 Phase 2 extraction，然后重新执行 Phase 3。
- `blocked`：存在 `blocked` disposition、source/artifact 缺失、digest/range 无法验证，或需要用户决定。

semantic duplicate 的存在与数量不影响 decision。

## Trace 与 renderer

`source-aligned-phase-3-trace-v2` 必须包含：

- `decision`
- `global-atom-index-path` / `global-atom-index-sha256`
- `coverage-review-path` / `coverage-review-sha256`
- `reviewer-loop`：保存 reviewer identity、validator status、finding、repair和 pass/block摘要；Phase 3 不另建 reviewer/repair report文件。

`reviewer-loop` 必须且只能包含 `status`、`writer-id`、`reviewer-id`、`validator-status`、`findings[]` 和 `repairs[]`。writer初次发布时使用 `status: pending`；reviewer保持只读并通过最终回复返回 evidence，由 main agent机械转录。只有 identity完整、validator通过且 independent reviewer通过时才改为 `passed`。

渲染命令：

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact phase3-global-index --write
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact phase3-coverage-review --write
```

writer 最终只向 main agent 简要报告 decision、gap atom数量、recheck source和 blocker；不额外创建报告文件。
