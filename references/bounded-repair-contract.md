# v8 repair-writer-only contract

本文件只提供给 repair writer 与 main agent。Reviewer 和原始 writer 禁止读取。

## 输入隔离

Repair writer 只读取：

- 当前 phase authority；
- 紧邻上一轮 canonical review result JSON；
- `change-capability-framework-principles.md`；
- `cross-phase-contract.md`；
- 本文件；
- 对应 Phase authoring contract。

禁止读取 `review-gates.md`、其他轮 review result、历史 repair row/report、trace 状态机、manifest 或预算。

## 完整消费

- 必须读取紧邻 review result 的完整 `findings[]`，不得只处理摘要或挑选部分 finding。
- 对每个 finding 记录对应 rule、subject、authority edit 与验证证据。
- Finding 没有 fingerprint 或跨轮 identity；不得生成、比较或推断此类字段。
- Repair 只修正当前 authority，不改 review result。

## Sibling regression audit

处理每个 finding 时，按其 `rule` 对同类 sibling 做完整回查：

- dependency finding：检查全部 Change 的 consumer × predecessor outcome closure；
- capability boundary finding：检查全部 Capability 的 owns/excludes 与 overlay；
- occurrence finding：检查同 source 和同 atom type 的所有 occurrence；
- directive finding：检查全部 directive-bearing occurrence；
- mapping finding：检查全部相同 relation/projection 的 GA row；
- guard finding：检查全部首次受保护 outcome；
- acceptance/archive finding：检查全部 Change。

Sibling audit 只用于防止局部修复引入同类回归，不允许扩大到无关产品决策。

## Authority 边界

- Phase 1 repair 只修改 `initial-framework.json`，随后完整重渲染 initial plan mirror。
- Phase 2/3 repair 只修改 freeze 前的 provisional evidence authority；freeze 后禁止 repair。
- Phase 5 repair 只修改 framework refit、final roadmap、terminal mapping 与其完整派生 candidate；不得回写冻结 evidence。
- Repair 后 authority digest 必须不同于 before digest；相同即 no-op，交回 main agent blocked。

## Handoff

Repair writer 输出修改后的 authority 和中文 repair report，然后停止。Main agent负责：

- 验证 repair 绑定紧邻 review result digest；
- 写 repair trace row；
- 完整渲染与刷新所有派生 digest；
- 运行 validator；
- 决定是否启动下一位 fresh reviewer。
