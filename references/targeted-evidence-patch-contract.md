# Targeted Evidence Patch 共享契约

本文件是唯一 evidence patch 协议。它定义 eligibility、有界 defect 核验、request/checkpoint 发布、Phase 2→5 增量链、resume/abort 与失败规则。其他文档只能引用本文件，不得复制或改写这些规则。

## 目录

- [加载与授权](#加载与授权)
- [Eligibility 与禁止用途](#eligibility-与禁止用途)
- [一次性有界核验](#一次性有界核验)
- [Request 与 protected rows](#request-与-protected-rows)
- [Checkpoint 与 allowed scope](#checkpoint-与-allowed-scope)
- [原子发布与 commit marker](#原子发布与-commit-marker)
- [增量执行链](#增量执行链)
- [Checkpoint resume](#checkpoint-resume)
- [Abort 与失败](#abort-与失败)
- [不变量与终止条件](#不变量与终止条件)

## 加载与授权

- Initial Phase 5 writer仅在frozen row、coverage metadata或用户精确报告暗示可能存在evidence integrity defect时加载本文件；普通refit/mapping不加载。
- Phase 2 targeted writer、Phase 3/4 incremental worker、Phase 5 checkpoint-resume writer、main agent执行abort，以及patch-active final integration reviewer必须完整加载本文件。
- `evidence-patch-request.json`或`phase-5-checkpoint.json`单独存在都不授权增量执行；只有本文件规定的完整发布组有效。

## Eligibility 与禁止用途

Phase 5只能在以下条件同时成立时发出patch：

- 当前是该generation首次Phase 5执行，尚未存在canonical Phase 5 trace；
- Phase 2、3、4分别是validator通过的initial success snapshot；
- 每个finding有具体source document、seed locator、有界line window及immutable digest witness；
- 全局review与全部GA provisional mapping已经完成，可以冻结`stage: mapping` checkpoint；
- 影响范围可以收敛为小于整个framework的最小连通闭包。

每个generation固定最多一个`request-id: EPR-0001`和一个`checkpoint-id: P5CP-0001`。`accepted`、`adjusted`、`blocked`、`closed`或任一incremental状态都不能回退为`requested`。

Patch只允许修复：

| Defect | Required operation | Optional companion operation |
| --- | --- | --- |
| `quote-mismatch` | `replace-quote` | `adjust-range` |
| `range-mismatch` | `adjust-range` | `replace-quote` |
| `mixed-independent-occurrences` | `split` | `adjust-range`、`replace-quote` |
| `missing-occurrence` | `add` | 无 |

`allowed-operations[]`是非空唯一array：必须包含该defect的required operation，只能再包含表中列出的optional companion；`missing-occurrence`必须且只能为`["add"]`。

禁止删除、合并或重命名occurrence。Candidate mapping、`unassigned`、gap、final owner/relation/projection/target、Capability impact、framework boundary及mapping ambiguity都不是patch defect，必须由Phase 5裁决。

## 一次性有界核验

- Seed locator只能来自冻结Phase 2 atom、Phase 3 disposition或用户提供的精确locator；不得通过全文扫描或搜索式发现取得。
- Writer在request前只可读取witness预先固定的同一source `allowed-line-window`一次。Window必须落在immutable locator ranges的连续闭包内。
- 禁止扩大window、搜索其他位置、二次读取、提取replacement evidence或把window用于framework判断。
- 当前source SHA必须同时匹配Phase 1/2冻结值；Phase 2–4 base validator必须仍通过。
- Existing target的base range必须位于window内，base quote必须仍是对应原文range内的substring。`quote-mismatch`只表示substring选择错误或截断；非原文base是非法上游authority，直接`blocked`。
- `missing-occurrence`必须有冻结coverage locator或用户精确locator；已由gap承接的`missing-obligation` disposition不能伪造遗漏。
- Locator不足、source/base drift、需要扩窗或需要第二次读取时立即`blocked`，不得生成request。

## Request 与 protected rows

`source-aligned-evidence-patch-request-v1`的字段shape只由trace contract定义。语义要求如下：

- `targets[]`按稳定顺序绑定source、nullable旧identity、defect、兼容的`allowed-operations[]`、window、successor ID、immutable base row、canonical owner、reason和defect witness。
- Existing target必须保存完整`base-row`及其SHA；patch后只允许operation对应的`source-fact`或`line-ranges`改变。
- `split`保留旧atom ID为第一项，新增ID从`<old>.part-02`连续分配；`add`从`patch-epr-0001-add-01`连续分配。
- `defect-witness`绑定同source immutable origin row、完整source SHA及window SHA；window SHA按1-based window、LF连接、无尾随LF的UTF-8字节计算。
- Finding fingerprint只由source/atom/GA/evidence-ref、defect、window和witness source/window digest规范化计算；不包含reason、operation、successor ID或writer identity。
- `protected-rows`完整保护target/new identity之外的Phase 2、3、4 row；row hash统一使用compact sorted UTF-8 JSON SHA256。不得以range重叠为由漏掉未受影响ambiguity或collection row。

## Checkpoint 与 allowed scope

`source-aligned-phase-5-checkpoint-v2`是nonterminal semantic resume authority，不是source或terminal plan authority。

- 只允许`stage: mapping`：全局Capability/Change/gap review和全部GA provisional mapping已经完成。
- `provisional-framework`冻结change order、Capability、overlay、hard dependency、review/GA lineage及完整Change/Capability semantic digest。
- `completed-rows`与`pending-ids`分别对Capability review、Change review、gap review和mapping形成完整、不相交partition。
- Pending Capability/Change/mapping/gap必须分别精确等于allowed scope中的initial Capability、initial Change、GA，以及scope GA与Phase 4 unassigned/gap GA的交集。
- `allowed-update-scope`只授权GA、initial/final Change、initial/final Capability；`allow-roadmap-reorder`固定为`false`。
- Initial scope非空时，从request target的Phase 4 initial bucket选root，并经initial/provisional hard dependency与overlay反向投影得到最小连通闭包；不得夹带或漏掉相连unit。
- Final old ID只能在其全部initial origin位于scope时修改或删除；无initial origin的ID必须由scope内GA lineage支持。全新ID只能由pending review或mapping实际产生。
- Scope不得完整覆盖initial/final Change、initial/final Capability任一非空universe，也不得通过old/new ID切换绕过full-refit guard。
- 跨scope overlay/dependency和scope外semantic digest必须保持不变；preserved row digest保护其余completed row。
- `patch-attempt.attempt`固定为`1`；authority digest绑定input fingerprints、request ref与provisional framework。

## 原子发布与 commit marker

Patch授权组必须按以下逻辑顺序一次发布：

```text
定稿并写入 immutable request bytes
-> 写入 checkpoint，绑定 request path/SHA
-> 在 refit v3 写入同一条 requested patch-history
-> helper 完整校验 request/checkpoint/refit，清理 terminal surface
-> 最后写入 phase-5.trace.json，作为 commit marker
```

Commit marker必须是`source-aligned-phase-5-trace-v4`、`status: needs-targeted-evidence-patch`、`execution-mode: initial`，并闭合引用request、checkpoint、refit和review的path/SHA。Phase 2–4进入incremental mode前必须重新验证整个发布组；request-only、request+checkpoint但无marker、digest不闭合或marker不是最后的完整状态都不得授权patch。

## 增量执行链

完整链固定为：

```text
Phase 2 targeted evidence patch
-> Phase 3 incremental reconcile
-> Phase 4 deterministic refresh
-> Phase 5 checkpoint resume
```

Phase 2：

- 只读写request target及必要最小局部上下文；使用冻结canonical owner。
- 验证base row和全部protected row；不得全量重提取、删除/合并/重命名atom或改变candidate mapping。
- Split successor继承candidate metadata；新增missing occurrence使用`unassigned`且不预填Capability target。

Phase 3：

- 只更新受影响document、gap/disposition、ambiguity和global index row；未受影响GA/ambiguity identity与digest保持不变。
- 新occurrence只在当前最大GA后连续追加；不得全量编号或把mapping finding改写成evidence defect。

Phase 4：

- 从当前Phase 1–3 authority执行同一确定性assembler，不读取checkpoint取得语义。
- 只有changed/new GA进入的collection及index digest可以变化；bucket仍只使用Phase 1 identity。

每个incremental trace必须绑定request/checkpoint marker、对应base digest与已知affected closure。任一Phase不得自行扩大scope或重跑全量工作。

## Checkpoint resume

- Resume前验证commit marker、request/checkpoint digest、input fingerprint、protected/preserved row与各增量trace闭包。
- 只重算pending ID及其allowed scope；scope外completed review/mapping row逐字复用。
- Final mapping仍由mapping v4持有；checkpoint lineage不成为第二份terminal mapping authority。
- Roadmap不得reorder，跨scopeedge不得变化，不得从Phase 1重新执行全量refit。
- Terminal refit把同一patch-history row由`requested`改为`closed`；request/checkpoint bytes保持不变。
- Helper校验terminal plan/refit/mapping与scope保护后，生成terminal surface和`execution-mode: checkpoint-resume` Phase 5 trace。

## Abort 与失败

增量链任一Phase失败时：

- 失败Phase trace保留execution/update mode、request/checkpoint ref、base digest和已知affected closure；不得重跑该Phase。
- Main agent只调用`phase5_plan_refit.py --abort-patch-chain --issue ...`执行机械control transform。
- Transform保持request/checkpoint bytes及全部semantic review/mapping/framework row不变；只把refit `status`改为`blocked`、替换`issues[]`、把唯一history row改为`blocked`，清理terminal surface并最后发布checkpoint-resume blocked trace。
- Abort validation只检查immutable snapshot的schema、ref、finding/authority digest和completed/preserved row内部自洽；不依赖已失败或已清理的Phase 3/4 surface，也不重新比较current Phase 1/principles与冻结fingerprint。
- Abort不是semantic writer，不得创建第二个request或恢复全量Phase 5。

## 不变量与终止条件

- Request、checkpoint在publish后immutable；resume与abort都必须逐字节保持。
- 相同finding fingerprint在authority digest未变化时重现、需要第二次patch、scope无法有界、影响闭包扩张到全framework、roadmap必须reorder或input fingerprint失效时，必须`blocked`。
- Patch成功只关闭同一history row；patch失败只阻断同一history row。任何路径都不得出现第二行history。
- Patch-active final integration reviewer核对单次generation、未受影响identity/digest、minimal closure、scope外语义和request/checkpoint字节稳定性。
