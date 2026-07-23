# Neutral Sequencing Evaluation

本目录用于技能发布前的中性盲测，不是运行时输入，也不得被 Phase writer、reviewer、helper 或 selector读取。

执行协议：

1. 每个 evaluator 只读取 `cases.json`、`references/change-capability-framework-principles.md` 与 `references/phase-1-initial-change-plan.md`，不得读取 `oracle.json`、历史 finding、repair 结果或预期修复。
2. 每个 case 由三名 fresh、互不共享输出的 evaluator 各判断一次。
3. Evaluator只返回推荐的 Change boundary、完整 typed dependency set、order、foundation/guard判断及理由，不得按 case ID 猜测测试意图。
4. Coordinator最后读取 `oracle.json`，逐条核对 required invariants 与 forbidden outcomes。
5. 每个 case 必须 3/3 通过；任一失败都阻断技能发布，并按相同 case 语义修正规则或实现后重新运行全部三次。

`cases.json`只保存给 evaluator 的中性输入；`oracle.json`只保存 coordinator 的分类与判定标准。禁止把 oracle 合并进 case prompt。

Coordinator 可在全部独立输出完成后，把逐 case pass count 写入 `results/`；该目录同样禁止 evaluator 和 generation worker 读取。
