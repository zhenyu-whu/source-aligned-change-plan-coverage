---
name: source-aligned-change-plan-coverage
description: 当用户要求从指定 source document 出发，在 openspec-propose 前建立具备 Change/Capability 分离、delivery directive、evidence occurrence 覆盖、typed dependency 完整性、final roadmap、terminal mapping 与 workflow completion 的 OpenSpec 全局计划时使用；v8 采用隔离的 writer/reviewer/repair 角色和 5-review/4-repair bounded gates。
---

# source-aligned-change-plan-coverage v8

本技能从 source 构建可审计的 OpenSpec Change/Capability 全局计划。v8 是硬切换协议：只在新的干净 generation output root 运行，既有 v7 generation 永远只读。

## 运行前

1. 确认用户提供的 source paths 与新的 generation output root。
2. 若 output root 非空或包含非 v8 generation，停止；不得迁移、覆盖、删除、补写或原地重试。
3. 记录 `openspec/orchestrate/` 当前状态；所有 forward test 只使用临时目录。
4. Main agent 读取：
   - `references/change-capability-framework-principles.md`
   - `references/cross-phase-contract.md`
   - `references/trace-sidecar-contract.md`
   - `references/review-gates.md`
   - `references/bounded-repair-contract.md`
   - 当前 Phase authoring contract

## 角色加载矩阵

| Role | 必须读取 | 禁止读取 |
| --- | --- | --- |
| Phase writer | source、共享 framework 原则、cross-phase 正向语义、对应 Phase authoring contract | review gate、repair contract、trace contract、manifest、预算、历史 review/repair |
| Fresh reviewer | 当前 authority、source/frozen evidence、共享原则、对应 Phase authoring contract、`review-gates.md` | 任何先前 review result、repair row/report、历史 finding |
| Repair writer | 当前 authority、紧邻上一轮完整 review result、共享原则、对应 Phase authoring contract、`bounded-repair-contract.md` | reviewer playbook、其他轮 result、trace、manifest、预算 |
| Main agent | 全部 control contract 与当前 canonical artifacts | 不得代替独立 worker 作语义判断 |
| Final integration reviewer | terminal authority、frozen evidence、共享原则、`review-gates.md` | bounded gate 历史、repair history |

每次派发 worker 时只提供该行允许的引用。不得通过摘要、prompt 拼接或 report 间接泄漏禁止内容。

## 五阶段

### Phase 1

Writer 按 `phase-1-initial-change-plan.md` 只产生 initial framework authority 与 mirrors/reports，不写 trace。

Main agent：

1. 确定性渲染；
2. 创建 Phase 1 v5 pending trace 与 manifest v4；
3. 运行 validator；
4. 执行独立 bounded gate。

通过条件同时包括 dependency edge soundness 与 dependency set completeness。

### Phase 2

按 `phase-2-source-anchor-coverage.md` 对每个 source occurrence 进行 canonical atom extraction，保持显式 delivery directive。Main agent写 Phase 2 trace并运行 validator。

### Phase 3

Writer 按 `phase-3-coverage-review-iteration.md` 产生 global GA index 与 coverage closure authority，不写 trace。

Main agent执行联合 Phase 2/3 bounded gate。通过后 Phase 1–3 evidence authority 冻结；此后不得回写 evidence、directive、reference 或 GA。

### Phase 4

按 `phase-4-frozen-evidence-collections.md` 从冻结 authority 确定性重建中性 evidence collections。不得加载候选 Change/Capability routing 作为读者展示结构。

### Phase 5

Writer 按 `phase-5-framework-refit-and-mapping.md` 只写 framework refit、final roadmap、terminal mapping candidate authority。

Main agent使用 helper：

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase5_plan_refit.py \
  --orchestrate-dir <new-output-root> \
  --prepare-review \
  --writer-id <writer-id>
```

该步骤生成 candidate mirrors、pending trace，并绑定七项 candidate digest。Phase 5 bounded gate通过后：

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase5_plan_refit.py \
  --orchestrate-dir <new-output-root> \
  --write
```

## Bounded review / repair

- Phase 1、联合 Phase 2/3、Phase 5 均最多 5 次 fresh review、4 次 fresh repair。
- Review result 使用每轮独立、不可覆盖 JSON；trace 只保存 path 与 SHA-256。
- Finding 只有 `rule`、`subject`、中文 `finding`；不生成或比较 fingerprint。
- Round 1–4 的 `repair-required` 才能 repair。
- Repair writer消费完整紧邻 result，并按每个 rule class 执行 sibling regression audit。
- Repair 后 authority digest 必须改变；随后完整重渲染、刷新派生 digest、运行 validator，才能 review。
- Round 5 只允许 passed 或 blocked。
- no-op、身份复用、authority/result digest 漂移立即 blocked。
- 三个 gate 的预算与 identity history 相互独立。

Phase 5 repair 后刷新：

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/phase5_plan_refit.py \
  --orchestrate-dir <new-output-root> \
  --refresh-review-candidate
```

## Final integration

Phase 5 passed 后先运行 pre-handoff validator，再由 fresh final integration reviewer一次性写 `source-aligned-final-integration-review-v2`。

Review 必须分别包含：

- `dependency-edge-results[]`：逐条验证已声明 edge；
- `dependency-set-result`：证明 consumer closure 未遗漏 edge。

Finalizer先 exclusive-create attempt，再写唯一 attempt result；失败不可覆盖或重试。只有合法 passed result 才能发布 Markdown mirror、workflow completion 与 integration-passed manifest。

```bash
python3 .codex/skills/source-aligned-change-plan-coverage/scripts/validate_source_aligned_orchestrate.py \
  --orchestrate-dir <new-output-root> \
  --pre-handoff

python3 .codex/skills/source-aligned-change-plan-coverage/scripts/finalize_source_aligned_orchestrate.py \
  --orchestrate-dir <new-output-root>

python3 .codex/skills/source-aligned-change-plan-coverage/scripts/validate_source_aligned_orchestrate.py \
  --orchestrate-dir <new-output-root> \
  --complete
```

## 阻断

任一 source、authority、schema、validator、身份、digest 或用户决策问题无法在预算内闭合时，当前 generation 合法终态为 `blocked`。不得进入后续 Phase、不得发布根 `change-plan.md`、不得声明 apply-ready，也不得在原 output root 原地修补或重试。

## 发布自检

修改本技能时必须：

1. 运行完整 `unittest discover`；
2. 运行 skill-creator `quick_validate.py`；
3. 运行 renderer、validator、helper、finalizer 集成测试；
4. 按 `evals/README.md` 对每个中性 case 进行 3 名 fresh evaluator 的独立判断并逐 case 达到 3/3；
5. 验证实施前记录的现有 `openspec/orchestrate/` 状态与字节 digest 未变化。
