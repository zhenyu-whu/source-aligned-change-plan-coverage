# source-aligned trace v8 machine contract

本文件只提供给 main agent 与机械工具。Writer、reviewer、repair writer 不读取。

## Version registry

| Surface | Schema / contract |
| --- | --- |
| Trace contract | `source-aligned-trace-v8` |
| Renderer | `source-aligned-render-v12` |
| Manifest | `source-aligned-orchestrate-manifest-v4` |
| Phase 1 trace | `source-aligned-phase-1-trace-v5` |
| Phase 2 trace | `source-aligned-phase-2-trace-v6` |
| Phase 3 trace | `source-aligned-phase-3-trace-v6` |
| Phase 4 trace | `source-aligned-phase-4-trace-v6` |
| Phase 5 trace | `source-aligned-phase-5-trace-v7` |
| Phase 1 review result | `source-aligned-phase-1-review-result-v1` |
| Phase 3 review result | `source-aligned-phase-3-review-result-v1` |
| Phase 5 review result | `source-aligned-phase-5-review-result-v1` |
| Final integration review | `source-aligned-final-integration-review-v2` |

未改变 shape 的 evidence/framework artifact 保持原 schema 版本，但都必须声明 `source-aligned-trace-v8`。

## Hard cut

- v8 只接受新的干净 generation output root。
- 任一 canonical JSON 的 `trace-contract-version` 不是 v8 时 fail closed。
- v8 helper、renderer、validator 不迁移、不覆盖、不删除 v7 generation。
- 不存在 compatibility write 或 migration path。

## Manifest v4

`trace/manifest.json` 是 control authority，exact fields：

- `trace-schema`
- `trace-contract-version`
- `authority`
- `orchestrate-dir`
- `phase-statuses`
- `workflow-status`
- `artifacts`

每个 `artifacts[]` row exact fields：

- `json-path`
- `trace-schema`
- `sha256`
- `phase`
- `role`
- `authority`

所有 canonical bounded review result 必须登记为：

- `authority: control`
- `role: bounded-review-result`
- 对应 phase 与 review-result schema

Manifest digest 必须匹配当前普通文件；遗漏、重复、额外 JSON 或 digest 漂移均阻断。

## Bounded review result

Canonical path：

```text
phase-works/<phase>/reviews/review-round-01.json
...
phase-works/<phase>/reviews/review-round-05.json
```

路径必须与 phase/round 一致。文件一经 trace 引用不可覆盖。

共同 exact fields：

```text
trace-schema
trace-contract-version
phase
round
reviewer-id
semantic-checks
findings
warnings
finding-count
decision
language-self-check
```

Phase 1 additional fields：

```text
validator-status
initial-framework-sha256
initial-change-plan-sha256
```

Phase 3 additional fields：

```text
stage
phase-2-validator-status
phase-3-validator-status
delivery-directive-status
evidence-authority-sha256
```

Phase 5 additional fields：

```text
validator-status
framework-refit-sha256
final-roadmap-sha256
atom-plan-mapping-sha256
final-change-plan-sha256
frozen-evidence-authority-sha256
phase-3-freeze-trace-sha256
candidate-handoff-sha256
```

`semantic-checks[]` exact fields 为 `check`、`result`，顺序必须匹配 phase 固定检查列表。`result` 只允许 `passed|failed`。

`findings[]` exact fields：

- `rule`
- `subject`
- `finding`

`finding` 必须为中文。不存在 fingerprint、hash 或跨轮 finding ID。

`decision` 只允许：

- `passed`
- `repair-required`
- `blocked`

Passed 要求 validator/check 全部通过且 findings 为空。非 passed 必须有 finding。Round 5 禁止 `repair-required`。

## Review gate

共同字段：

```text
status
terminal-reason
reviews
repairs
```

Phase-specific producer identity fields按 runtime schema 保持：

- Phase 1：`writer-id`
- Phase 3：`phase-2-canonical-owner-ids`、`phase-2-aggregate-writer-id`、`phase-3-writer-id`
- Phase 5：`writer-id`

`status`：`pending|passed|blocked`。

`terminal-reason`：

```text
none
review-blocked
budget-exhausted
no-op-repair
identity-reuse
authority-integrity
```

Pending/passed 必须 `none`；blocked 必须非 `none`。

Review reference row exact shape：

```json
{
  "round": 1,
  "review-result-path": "openspec/orchestrate-v8/phase-works/phase-1/reviews/review-round-01.json",
  "review-result-sha256": "<sha256>"
}
```

Phase 1 repair row：

```text
round
repair-writer-id
source-review-result-sha256
before-initial-framework-sha256
after-initial-framework-sha256
```

Phase 3 repair row：

```text
round
repair-writer-id
source-review-result-sha256
before-evidence-authority-sha256
after-evidence-authority-sha256
```

Phase 5 repair row：

```text
round
repair-writer-id
source-review-result-sha256
before-terminal-authority-sha256
after-terminal-authority-sha256
```

## Cardinality 与终态

- 最大 reviews=5，repairs=4。
- Pending 只允许 `reviews == repairs` 或 `reviews == repairs + 1`。
- 相邻 review 之间恰好一条 repair。
- 只有 Round 1–4 的 `repair-required` 可对应 repair。
- `source-review-result-sha256` 必须等于紧邻 review reference digest。
- repair after 必须不同于 before；no-op 立即 blocked。
- Round 5 后不得 pending。
- Passed 与 review/budget blocked 一般要求 `reviews == repairs + 1`。
- `no-op-repair` blocked 允许 `reviews == repairs`。
- identity reuse、authority/result digest 漂移、路径错误立即 blocked。
- 不进行 finding 重复、相似度或 fingerprint 比较。

## Phase trace ownership

- Main agent 独占所有 phase trace、manifest、review budgets、identity 与状态转换。
- Phase 1/3 writer 不创建 `review-pending` trace。
- Trace 只引用 review result，不内嵌 reviewer semantic payload。
- 非 canonical Markdown reviewer/repair report 不进入 manifest，也不得被后续 worker 消费。

## Phase 5 candidate binding

Phase 5 每轮 review 同时绑定七项：

1. framework refit digest；
2. final roadmap digest；
3. atom plan mapping digest；
4. candidate final plan digest；
5. frozen evidence authority digest；
6. Phase 3 freeze trace digest；
7. candidate handoff digest。

Repair 后必须完整重渲染、刷新七项 digest、运行 preflight validator，再启动 fresh reviewer。

## Final integration v2

`final-integration-review.json` 在 v1 字段基础上新增必需：

```json
{
  "dependency-set-result": {
    "result": "passed",
    "note": "逐 Change consumer closure 未发现遗漏 edge。",
    "evidence-ga-ids": ["GA-0001"]
  }
}
```

`dependency-edge-results[]` 逐条验证已声明 edge；`dependency-set-result` 独立证明 edge set 完整。缺少或失败均不得 workflow completion。

Final integration attempt/result、terminal seven-artifact digest、exclusive one-shot create 与 public handoff 机制保持原有 contract。

## Paths 与 integrity

- canonical path 为 repository-relative POSIX path；
- 禁止 absolute path、`..`、symlink traversal 与 root escape；
- SHA-256 为 64 位小写十六进制；
- canonical JSON 使用 UTF-8、排序 key 与尾随换行；
- 所有生成式验证只在临时目录运行。
