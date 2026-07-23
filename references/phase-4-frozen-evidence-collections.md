# Phase 4：frozen evidence collections

Phase 4 是确定性 assembler，不进行语义 review 或 repair。

## 输入

- 已通过 gate 的 Phase 1 authority；
- Phase 2 frozen source atom JSON；
- Phase 3 global GA index 与 coverage review；
- `cross-phase-contract.md`；
- 本文件。

Assembler 不读取 reviewer/repair history，不修改上游 authority。

## 输出

```text
phase-works/phase-4/source-evidence-collections/
  evidence-collection-index.json
  index.md
  all-evidence.md
  delivery-directives.md
  by-source/*.md
```

`evidence-collection-index.json` 保持 `source-aligned-evidence-collection-index-v3` shape，并声明 `source-aligned-trace-v8`。Markdown 使用 `source-aligned-render-v12`。

## 中性投影

- Collection 只按 source、GA、occurrence、atom type、normativity 与 directive 组织。
- 不按 candidate owner Change 或 candidate Capability 组织读者 surface。
- 不把 provisional routing hint 解释为 final planning decision。
- 同一 GA 在全量 collection 与 source slice 中保持相同 source fact、line range 与 directive。
- 所有 evidence 以 frozen authority 的稳定顺序呈现。

## 完整性

- global GA 集合与 collection index GA 集合完全相等；
- 每个 GA 恰有一个 source occurrence；
- 每个 directive-bearing GA 出现在 directive collection；
- 每个 source 的 GA slice 与 global index 一致；
- 无 dangling、duplicate 或 synthesized GA；
- Markdown 与 index JSON 可从冻结 authority 确定性重算。

## 发布

Assembler在私有 staging中完整生成并自校验，成功后原子发布。Main agent最后写 Phase 4 v6 trace与 manifest。

Blocked 时丢弃未提交 staging，不回写 Phase 1–3，不启动 reviewer/repair。
