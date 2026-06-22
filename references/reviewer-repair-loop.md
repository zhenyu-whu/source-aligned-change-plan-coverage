# Reviewer Repair Loop

本文件定义每个 Phase 的 validator/reviewer/repair 闭环。进入 workflow 前必须读取。

## Required Order

每个 Phase 完成顺序固定为：

```text
phase writer/subagent
-> phase validator
-> phase reviewer
-> phase repair-writer/subagent
-> rerun validator
-> rerun reviewer
-> pass 后进入下一 Phase
```

## Authority Rules

- Validator 只检查结构、trace、digest、schema、ID、coverage、mirror drift 和跨 artifact 一致性；不替代语义判断。
- Reviewer 只读，不直接改 artifact。
- Reviewer 必须处理 validator warnings；warnings 可以接受，但必须有 reviewer 判断或修复计划。
- Repair-writer 只能修改本 Phase 允许的 artifact。
- Phase 2 完成后 raw `.atoms.md/.json` 冻结。后续发现的问题进入 Phase 3 missing/split/recheck，不回改 Phase 2。
- Phase 5 发现缺失或过宽 source obligation 时返回 `needs-coverage-recheck`，不得在 Phase 5 发明新 atom。

## Reviewer Scope

Phase 1 reviewer:

- 检查 vertical loop、foundation exception、capability shape、anti one-to-one roadmap。
- 检查 Phase 1 没有提前创建 atom、coverage status、line-range anchor 或 Phase 2 work queue。

Phase 2 reviewer:

- 检查漏抽、broad atom、projection/status、owner 候选是否仅作为候选。
- 检查每个 `read-full` source 是否正好一个 canonical owner 和一个 `.atoms.md/.json`。

Phase 3 reviewer:

- 检查 `GA-####` 归一、source-to-global 全覆盖、non-coverage 合理性、duplicate/broad split 处理。
- 检查 direct 或 `phase-5-refit-required` atom 没有使用 `contextual-only`。

Phase 4 reviewer:

- 检查 source-window dossier 是否真实支撑 semantic profile。
- 检查 grounding issue 是否应返回 `needs-coverage-recheck`。

Phase 5 reviewer:

- 检查 final ownership、non-direct 承载、capability progression、complexity gate。
- 检查 final packet 是否显式列出 owner-scoped non-direct atom。
- 检查 capability view 只包含 direct advancement rows。

Final integration reviewer:

- 对 Phase 3/4/5 做跨 artifact reconciliation。
- 检查 global atom index、source-window index、atom-plan mapping、final packets、capability views、root `change-plan.md` 和 human plan 是否一致。

## Repair Rules

- Repair 必须保留 `GA-####`、source path、line range、source fact 和 upstream evidence，除非本 Phase 明确允许修正。
- Repair 不得通过删除 warning 对应数据来让 validator 通过。
- Repair 后必须重新运行 validator 和 reviewer。
- 若 repair 需要修改冻结上游 evidence，返回 `needs-coverage-recheck` 或 `blocked`，由主 agent 重新启动允许的 Phase。
