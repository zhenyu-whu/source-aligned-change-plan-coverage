# Phase 3：覆盖闭合、GA identity 与 potential mapping ambiguity

Phase 3检查Phase 2 extraction对source行范围的覆盖情况，从uncovered range补提取遗漏obligation，为每个evidence occurrence分配稳定GA，并以GA为键记录potential mapping ambiguity。它不规范化语义、不规划Change/Capability、不裁决mapping，也不处理semantic duplicate。

Writer必须直接完整读取`references/cross-phase-contract.md`、本文件和`references/trace-sidecar-contract.md`；仅`update-mode: incremental-patch`额外完整读取`references/targeted-evidence-patch-contract.md`。

## 输入

- `phase-works/phase-1/source-doc-manifest.md`
- `phase-works/phase-2/source-obligation-atoms/<source>.atoms.json`
- 用户指定的 source document
- `scripts/phase3_line_range_audit.py`（必须用于合并 covered range 和计算 complement）
- `update-mode: incremental-patch`时还必须验证唯一request、`source-aligned-phase-5-checkpoint-v2`、Phase 5 trace commit marker和Phase 2 targeted trace组成闭合授权链；孤立request/checkpoint不得授权增量写入。

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
8. 为每个GA检查extraction-time hint是否存在potential mapping ambiguity；只记录ambiguity dimensions和reason，不填写final mapping。若观察到一个冻结atom可能承载多个独立responsibility：单一tuple无法无损表达时只按实际维度记录ambiguity；仍共享唯一tuple时不得为传递finding伪造ambiguity row。两种情况都不得在本Phase定性evidence defect、发起patch或仅因此`blocked`，最终分类留给Phase 5的全GA检查。
9. `update-mode: incremental-patch`时按patch contract验证发布组、Phase 2 before/after row与protected row，只更新affected closure；未受影响GA和ambiguity row保持identity与row digest，新GA只追加不重编号。
10. 写入coverage decision和`language-self-check`，并用v8 renderer生成两个Markdown mirror。validator失败时返回`blocked`，不得自动重启writer或重复Phase 3。

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

## Global atom identity

Global index和两种evidence ref的exact machine shape只由`references/trace-sidecar-contract.md`定义。本文件只规定identity语义：每个Phase 2 atom和Phase 3 gap atom恰好分配一个独立GA；语义相同、原文相同或范围重叠都不触发合并。Markdown只显示GA与evidence reference，不复制evidence内容。

## Coverage semantic review

Coverage review顶层及document、gap、disposition、ambiguity、summary row的exact machine shape只由`references/trace-sidecar-contract.md`定义。本Phase按以下语义填充该接口：

- document row只保存当前source/Phase 2 digest及审计脚本给出的机械covered/complement range，不复制Phase 2 extraction内容。
- gap atom只提取candidate uncovered range中遗漏的production obligation；每个gap保持单一连续range、逐字原文、type、normativity和中文review judgment。
- `missing-obligation`必须链接至少一个位于该range内的gap atom；`safe-non-obligation`不得链接gap；`blocked`表示source缺失、范围不可信或无法在授权边界内判断。每个candidate uncovered range必须被disposition完整覆盖，每个gap atom必须由且只由一个`missing-obligation` disposition链接。
- mapping ambiguity只是potential input observation。只有当一个evidence occurrence无法由唯一mapping tuple（owner-change、relation、artifact-projection、target-capability）无损表达，或至少一个维度存在多个合理取值时才记录；不得写入候选值、final value、Change/Capability建议或resolution。`unassigned`、gap、source-fact长度、GA数量或candidate hint缺失都不是自动判据；source语义本身冲突必须`blocked`。
- summary只记录validator可机械重算的数量；其exact keys和嵌套classification计数shape见trace contract，GA count仅表示trace volume。

## Decision

只允许：

- `coverage-complete`：所有 source/artifact/digest 有效；每个 uncovered range 已补提取或安全分类；没有 blocker。mapping ambiguity可以非空。
- `blocked`：存在 `blocked` disposition、source/artifact 缺失、digest/range 无法验证，或需要用户决定。

semantic duplicate 的存在与数量不影响 decision。

## Trace 与 renderer

`source-aligned-phase-3-trace-v3`的成功态、blocked态及其nested ref的exact shape只由`references/trace-sidecar-contract.md`定义。Phase 3不创建reviewer/repair report，不写reviewer identity。Initial mode不带patch引用、base digest或affected/new identity；`update-mode: incremental-patch`的授权、identity保护、affected closure和失败规则以patch contract为准。Validator只能pass或使Phase 3 `blocked`。

`blocked` trace不伪装成功产物；exact shape见trace contract。Incremental blocked必须保留commit marker引用与已知affected/new identity，再由main agent按patch contract执行唯一机械abort；不得手写semantic refit或重跑Phase 3。

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
