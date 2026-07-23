# v8 reviewer-only bounded gates

本文件只提供给 fresh reviewer 与 main agent。Writer 和 repair writer 禁止读取。

## 共同规则

- Phase 1、联合 Phase 2/3、Phase 5 三个 gate 均最多 5 次 fresh review、4 次 fresh repair。
- Round 1–4 的合法 decision：`passed`、`repair-required`、`blocked`。
- Round 5 只允许 `passed` 或 `blocked`；任何 finding、failed check 或 validator failure 都必须 `blocked`，terminal reason 为 `budget-exhausted`。
- Reviewer 只读取当前 authority、source/frozen evidence、共享语义原则、本文件与对应 Phase authoring contract。
- Reviewer 禁止读取任何先前 review result、repair row、repair report 或历史 finding。
- Reviewer identity 每轮必须 fresh，且不得与 writer、repair writer 或其他 producer 重用。
- Reviewer 只写当轮 canonical review result JSON；不得修改 authority、trace 或 manifest。

## Canonical review result

路径固定且不可覆盖：

- `phase-works/phase-1/reviews/review-round-01.json` … `05.json`
- `phase-works/phase-3/reviews/review-round-01.json` … `05.json`
- `phase-works/phase-5/reviews/review-round-01.json` … `05.json`

schema：

- `source-aligned-phase-1-review-result-v1`
- `source-aligned-phase-3-review-result-v1`
- `source-aligned-phase-5-review-result-v1`

共同字段：

- `trace-schema`
- `trace-contract-version`
- `phase`
- `round`
- `reviewer-id`
- phase-specific authority digest/status
- 固定顺序 `semantic-checks[]`
- `findings[]`
- `warnings[]`
- `finding-count`
- `decision`
- `language-self-check`

Finding exact shape：

```json
{
  "rule": "dependency-set-completeness",
  "subject": "runtime-node-change",
  "finding": "该 Change 消费既有 Draft 执行结果，但缺少 typed hard-dependency edge。"
}
```

Finding 不含 hash、fingerprint、跨轮 ID 或重复标识。系统不比较相同、相似或重复 finding；bounded budget 是唯一轮次终止机制。

## Phase 1 fixed checks

1. `capability-change-independence`
2. `source-delivery-semantics`
3. `prefix-utility`
4. `consumer-closure`
5. `dependency-edge-soundness`
6. `dependency-set-completeness`
7. `guard-co-delivery`
8. `foundation-like-content`
9. `order-selection`
10. `overlay-directness`

## Phase 3 fixed checks

1. `source-range-coverage`
2. `production-obligation-completeness`
3. `delivery-directive-completeness`
4. `delivery-directive-source-basis`
5. `architecture-directive-separation`
6. `evidence-quote-range-integrity`
7. `terminal-mapping-tuple-losslessness`
8. `semantic-dedup-prohibition`
9. `mapping-ambiguity-discipline`
10. `source-conflict-closure`

## Phase 5 fixed checks

1. `final-capability-gates`
2. `final-change-gates`
3. `delivery-directive-resolution`
4. `dependency-edge-soundness`
5. `dependency-set-completeness`
6. `prefix-viability`
7. `guard-co-delivery`
8. `foundation-like-content`
9. `order-selection`
10. `mapping-overlay-consistency`

## Consumer × predecessor outcome closure audit

Phase 1 与 Phase 5 reviewer 对每个 Change 执行：

1. 从 behavior、acceptance、outcome thread 与 consumer description 枚举它实际读取或依赖的稳定 outcome。
2. 为每个 outcome 确认 producer 是 earlier Change、existing baseline 或 same Change。
3. 若 producer 是 earlier Change，验证 typed edge 存在且满足四项成立条件。
4. 若没有 edge，验证 existing baseline 或 same-change co-delivery 恰有一个成立。
5. 反向检查所有已声明 edge，排除只因共享 schema/runtime/infrastructure、相邻顺序或 Capability adjacency 建边。

`dependency-edge-soundness` 只评价已声明 edge；`dependency-set-completeness` 独立评价是否遗漏 edge。两项不得合并或互相替代。

## Main agent gate transition

Main agent 独占 trace、manifest、预算、身份与状态转换。Trace 中 review row 只保存：

- `round`
- `review-result-path`
- `review-result-sha256`

Repair row 绑定 `source-review-result-sha256` 与 phase-specific authority before/after digest。

`terminal-reason` 只允许：

- `none`
- `review-blocked`
- `budget-exhausted`
- `no-op-repair`
- `identity-reuse`
- `authority-integrity`

`pending`、`passed` 必须为 `none`；`blocked` 必须为其他值。

- 只有 Round 1–4 的 `repair-required` 可进入 repair。
- Repair 后 authority digest 必须改变；no-op 立即 blocked。
- Repair 后完整重渲染、刷新派生 digest、运行 validator，才能启动 fresh reviewer。
- identity reuse、authority/result digest 漂移、result path 非 canonical 或已引用 result 被覆盖，立即 blocked。
- Round 5 后不得保持 pending。

## Final integration review

Final integration review 是独立、一次性、one-shot workflow gate，不占 bounded gate 预算。v2 result 除逐条 `dependency-edge-results[]` 外，必须包含独立 `dependency-set-result`，证明 consumer closure 未遗漏 hard dependency。
