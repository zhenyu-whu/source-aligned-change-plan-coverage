# Phase 2：source occurrence atom extraction

这是 Phase 2 source writer 的 authoring contract，不包含 review gate、repair、预算或 trace 状态机。

## 输入与隔离

Writer 读取：

- 分配给自己的完整 source document；
- Phase 1 current framework，仅用于 candidate routing context；
- 共享 framework 原则、cross-phase 正向语义与本文件。

Writer 不读取 reviewer playbook、repair contract、trace contract、manifest 或历史 review/repair。

## 输出

每个 source document 恰有一份 canonical JSON：

```text
phase-works/phase-2/source-obligation-atoms/<source-key>.atoms.json
```

Markdown mirror 由 renderer 确定性生成。Writer 不创建 aggregate index、phase report、trace 或 manifest。

## Occurrence extraction

- 全量逐行阅读 source；每个义务 occurrence 独立建 atom。
- 相同文本在不同 line range 出现时保留多个 atom，不做语义去重。
- atom 的 `line-ranges` 必须精确支持 `source-fact`。
- 不把标题、说明性上下文或示例误判为 normative obligation。
- source 冲突保留为 blocker，不擅自选择业务策略。

每个 atom exact fields 保持 `source-aligned-source-atoms-v6`：

- `source-atom-id`
- `line-ranges`
- `atom-type`
- `source-fact`
- `normativity`
- `candidate-status`
- `candidate-artifact-projection`
- `candidate-owner-change`
- `candidate-target-capability`
- `delivery-directives`
- `rationale`

顶层声明 `source-aligned-trace-v8`。

## Atom semantics

`atom-type` 从当前 schema 枚举选择：

- `behavior`
- `data-contract`
- `architecture-runtime`
- `verification`
- `scope-guard`
- `context`

`normativity`：

- `must`
- `must-not`
- `should`
- `context`

Candidate routing 是 provisional hint，不是 final mapping。无法可信归属时使用 unassigned/unsure 状态，不伪造 owner。

## Delivery directives

仅从 source 明示内容提取：

- `milestone-scope`
- `explicit-precedence`
- `explicit-deferred`

同一 occurrence 可有多个不重复 directive，按 canonical 顺序排列。不得从架构惯例、实现便利或 reviewer 期望推断 directive。

Directive 与 dependency 分离：

- precedence 不自动等于 hard dependency；
- deferred 不自动等于 non-goal；
- milestone scope 不自动改变 Capability boundary。

## Writer 完成条件

- source path、SHA、line count 与 read status 准确；
- occurrence 无遗漏、无合并；
- line range 与 source fact 一致；
- atom type、normativity 与 projection 合法；
- directive 仅来自显式 source；
- blocker 与 rationale 使用简体中文。

Writer 完成后停止。Main agent负责聚合 index/report、写 Phase 2 trace、运行 validator，并决定是否进入 Phase 3。
