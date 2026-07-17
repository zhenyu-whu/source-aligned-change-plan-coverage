# Phase 3：覆盖闭合、GA identity 与 potential mapping ambiguity

Phase 3检查Phase 2 provisional extraction对source行范围的覆盖情况，从uncovered range补提取遗漏obligation，为每个evidence occurrence分配provisional GA，并以GA为键记录potential mapping ambiguity。随后执行Phase 2/3联合bounded semantic review；只有terminal review通过，才以`coverage-complete` commit marker同时冻结Phase 2/3 evidence与GA。它不规范化语义、不规划Change/Capability、不裁决mapping，也不处理semantic duplicate。

Writer、reviewer和repair writer必须直接完整读取`references/cross-phase-contract.md`、本文件、`references/review-gates.md`和`references/trace-sidecar-contract.md`。

## 输入

- `phase-works/phase-1/source-doc-manifest.md`
- `phase-works/phase-2/source-obligation-atoms/<source>.atoms.json`
- 用户指定的 source document
- `scripts/phase3_line_range_audit.py`（必须用于合并 covered range 和计算 complement）

Phase 2 Markdown mirror 只用于 review；canonical extraction evidence 是 `.atoms.json`。

writer 必须执行随技能提供的 `scripts/phase3_line_range_audit.py`，不得手工计算 complement，不得用模型推理、临时脚本或其他等价实现替代。脚本 stdout 是 Phase 3 covered/complement range 的唯一 writer 输入；validator 仍须独立机械重算并检查 drift。

## 固定输出

Phase 3只保留以下五个canonical/derived artifact，并可创建两份noncanonical流程报告：

- `change-capability-anchors/obligation-atom-index.json`
- `change-capability-anchors/obligation-atom-index.md`
- `phase-works/phase-3/coverage-review.json`
- `phase-works/phase-3/coverage-review.md`
- `trace/phase-3.trace.json`
- `phase-works/phase-3/phase-3-reviewer-report.md`
- `phase-works/phase-3/phase-3-repair-report.md`（仅发生repair时）

前五项中JSON是canonical authority，Markdown是mirror，trace是commit marker；review/repair report不进入manifest且不能覆盖JSON authority。不得创建逐文档coverage、Phase 3 manifest副本、source-to-global map、remainder review、duplicate review、normalization log或agent report。Validator拒绝旧布局和旧schema。

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
4. 按稳定顺序为每个Phase 2 source atom一对一分配provisional `GA-####`。
5. 只阅读 candidate uncovered range及理解该 range 所需的最小局部上下文。
6. 对 uncovered range 中遗漏的 production obligation 创建 `P3-GAP-####`，再为每个 gap atom分配一个独立 GA。
7. 将其余 uncovered range分类为 `safe-non-obligation` 或 `blocked`；遗漏 obligation 使用 `missing-obligation` 并链接 gap atom。
8. 为每个GA检查extraction-time hint是否存在potential mapping ambiguity；只记录实际不唯一的dimensions和reason，不填写final mapping。一个occurrence若包含无法由单一terminal tuple无损表达的多个独立responsibility，必须作为review finding在freeze前拆分；不得用ambiguity row替代拆分。
9. Coverage review在机械闭合且无blocked disposition时写`decision: coverage-complete`；Phase 3 trace写`decision: review-pending`、完整`review-gate`当前历史，并用v9 renderer生成两个Markdown mirror。Trace的pending状态不改变coverage authority或其digest。
10. 运行`--phase phase-2`普通validator和`--phase phase-3 --preflight`。Phase 3 preflight允许`review-pending`，校验当前Phase 2/3 authority、coverage、provisional GA、ambiguity和mirror，但不要求review gate已pass。
11. 启动fresh independent reviewer全文读取所有source并联合检查Phase 2/3。若有finding，启动fresh repair writer消费该轮finding；repair只能修改明确命中的provisional Phase 2/3 authority。随后重新执行range audit、coverage closure、GA稳定排序、两个renderer和两个validator，再启动fresh reviewer。
12. 最多三次review、两次repair。最后一个review必须为`stage: phase-3-closure`、两个validator status均为`passed`且findings为空；随后只把Phase 3 trace写为`decision: coverage-complete`与`review-gate.status: passed`，作为原子freeze commit marker，不改动已审global index或coverage review。Repeated finding、no-op repair、身份复用、预算耗尽或无法可信覆盖时写`blocked`。

## 明确禁止

Phase 3 不得：

- 比较两个 atom 的语义是否相同；
- 选择 canonical atom；
- 判断 duplicate/refinement/preserve/dependency relation；
- 由Phase 3 writer直接拆分或修改Phase 2 atom；只有联合gate的fresh repair writer可在finding范围内修改provisional authority；
- 把mixed independent responsibilities留到Phase 5、为传递finding伪造mapping ambiguity，或在freeze后修改evidence；
- 判断 owner Change、artifact projection、Capability impact/target/related Capability；
- 在`gap-atoms[]`合法extraction之外新增或发布独立的`source-fact` authority，或把解释文本当作独立evidence authority；解释字段可以使用必要的领域名称或引用性文字，但证据解析仍必须通过`evidence-ref`；
- 因 GA 数量或重复 evidence 数量触发 complexity、split、merge 或回补。

## Global atom identity

Global index和两种evidence ref的exact machine shape只由`references/trace-sidecar-contract.md`定义。本文件只规定identity语义：每个Phase 2 atom和Phase 3 gap atom恰好分配一个独立GA；语义相同、原文相同或范围重叠都不触发合并。Freeze前split/add后按稳定排序确定性重算全部provisional GA；freeze后不可修改或重编号。Markdown只显示GA与evidence reference，不复制evidence内容。

## Coverage semantic review

Coverage review顶层及document、gap、disposition、ambiguity、summary row的exact machine shape只由`references/trace-sidecar-contract.md`定义。本Phase按以下语义填充该接口：

- document row只保存当前source/Phase 2 digest及审计脚本给出的机械covered/complement range，不复制Phase 2 extraction内容。
- gap atom只提取candidate uncovered range中遗漏的production obligation；每个gap保持单一连续range、逐字原文、type、normativity和中文review judgment。
- `missing-obligation`必须链接至少一个位于该range内的gap atom；`safe-non-obligation`不得链接gap；`blocked`表示source缺失、范围不可信或无法在授权边界内判断。每个candidate uncovered range必须被disposition完整覆盖，每个gap atom必须由且只由一个`missing-obligation` disposition链接。
- mapping ambiguity只是potential input observation。只有当一个evidence occurrence无法由唯一mapping tuple（owner-change、relation、artifact-projection、target-capability）无损表达，或至少一个维度存在多个合理取值时才记录；不得写入候选值、final value、Change/Capability建议或resolution。`unassigned`、gap、source-fact长度、GA数量或candidate hint缺失都不是自动判据；source语义本身冲突必须`blocked`。
- summary只记录validator可机械重算的数量；其exact keys和嵌套classification计数shape见trace contract，GA count仅表示trace volume。

## Evidence freeze review gate

Reviewer必须确认：

- 每个source行都由atom covered range或remainder disposition解释；这不要求每行都提取为atom。
- 每项production obligation都进入Phase 2 atom或Phase 3 gap atom，`safe-non-obligation`只用于真实无production语义内容。
- 每个`source-fact`是其唯一连续range内的逐字substring；source、digest和range可信。
- 每个occurrence能由单一terminal mapping tuple无损表达；mixed independent responsibilities在freeze前拆分。
- 不执行semantic dedup；原文或语义相同的occurrence保持独立。
- 真实mapping ambiguity可以保留，但必须逐GA记录实际不唯一的维度，不得提前填写final value。
- Source自身冲突、无法可信覆盖或必须依赖产品决定时直接`blocked`。

`review-gate`的exact shape见trace contract。全部Phase 2 canonical owner、Phase 2 aggregate writer和Phase 3 writer都是producer；所有reviewer和repair writer必须fresh、互不相同且与全部producer不同。Repair只能消费前一轮fingerprint，不能扩大到无关source；相同fingerprint再次出现或before/after authority digest相同立即`blocked`。

Evidence authority SHA256是compact sorted UTF-8 JSON SHA256。输入对象按稳定顺序包含全部source document及SHA、全部Phase 2 atom JSON path及SHA、Phase 3 global index path及SHA、coverage review path及SHA，不包含trace、manifest、Markdown mirror或report。`phase-2-preflight`阶段尚不存在的Phase 3 path/SHA显式为`null`；`phase-3-closure`必须全部非null。

## Trace decision

只允许：

- `review-pending`：只允许Phase 3 trace在preflight使用；当前provisional authority可校验，但review gate尚未terminal。普通Phase 3 validator拒绝该decision。
- `coverage-complete`：所有source/artifact/digest有效；每个uncovered range已补提取或安全分类；`review-gate.status: passed`且terminal review满足双validator pass、空finding。Mapping ambiguity可以非空。
- `blocked`：存在 `blocked` disposition、source/artifact 缺失、digest/range 无法验证，或需要用户决定。

Coverage review JSON自身只使用`coverage-complete|blocked`；semantic duplicate的存在与数量不影响任一decision。

## Trace 与 renderer

`source-aligned-phase-3-trace-v4`的review-pending、coverage-complete、blocked及`review-gate` exact shape只由`references/trace-sidecar-contract.md`定义。Review/repair report只保存详细过程，不进入manifest；canonical bounded evidence必须机械写入trace。

`blocked` trace保留完整review/repair历史及issues，不伪装成功commit marker。恢复时从未完成review round继续，已有预算和历史不得重置；freeze后不存在repair、incremental或checkpoint resume。

渲染命令：

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact phase3-global-index --write
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/render_source_aligned_orchestrate.py \
  --orchestrate-dir openspec/orchestrate \
  --artifact phase3-coverage-review --write
```

writer最终只向main agent简要报告decision、gap atom数量、mapping ambiguity数量、review/repair用量和blocker；reviewer/repair writer分别追加规定的noncanonical报告。

coverage mirror必须把`covered-ranges[]`和`candidate-uncovered-ranges[]`中的每个`{start,end}`机械显示为`Lx-Ly`，并呈现逐GA mapping ambiguity与`language-self-check`。validator对global index和coverage review两个mirror逐字重渲染比较。
