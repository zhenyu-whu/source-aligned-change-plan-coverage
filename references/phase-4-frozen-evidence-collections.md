# Phase 4：冻结 Evidence 的 Neutral Collections

Phase 4在Phase 3 evidence freeze后运行。它通过resolver读取全部冻结occurrence，生成全量中性collection、按source的中性视图与显式delivery-directive视图。本Phase不读取原始source、不按Phase 1 Change/Capability分桶、不作mapping、refit、dependency或order判断。

Assembler必须完整读取cross-phase、本文件和trace contract。Phase 4不加载framework原则。

## 输入

- Phase 1 source manifest；
- Phase 2 frozen source atom JSON；
- Phase 3 global atom index与coverage review。

Phase 1 `initial-framework.json`只用于验证source set identity，不得用于collection grouping；其Markdown mirror不作为机器输入。不得读取原始source或旧Phase 4 artifact决定collection内容。

## 输出与权威

```text
phase-works/phase-4/
├── source-evidence-collections/
│   ├── evidence-collection-index.json
│   ├── index.md
│   ├── all-evidence.md
│   ├── by-source/<source-key>.md
│   └── delivery-directives.md
└── phase-4-agent-report.md

trace/phase-4.trace.json
```

- `all-evidence.md`恰好覆盖全部GA，是不带framework路由的完整中性collection。
- 每个包含冻结occurrence的source恰好一个`by-source`中性视图。
- `delivery-directives.md`包含全部且仅包含`delivery-directives[]`非空的GA；允许为空但文件仍必须存在。
- Collection Markdown是确定性内容权威；index JSON是派生机器索引。
- Agent report是noncanonical，不进入manifest。

V7禁止创建或保留：

- `by-input-change/`
- `by-input-capability/`
- `unassigned-and-gap.md`
- input candidate bucket字段；
- source-window dossier、semantic profile、normalization log、mapping或refit artifact。

## Evidence resolver

对global index中的每个GA：

- Phase 2 ref加载source path、唯一range、source-fact、type、normativity、delivery-directives与candidate hint；
- Phase 3 gap ref加载相同evidence字段与review judgment。

Phase 4只使用source path、range、source-fact、type、normativity、directive与provenance。不得把candidate owner/target/status/projection渲染到collection或index，也不得让它们参与membership、顺序、kind或grouping。

Resolver不得重新读取source、猜测缺失字段或比较evidence语义。

## Assembler固定顺序

1. 读取Phase 1 manifest并取得read-full source顺序。
2. 解析Phase 3 global index，逐GA通过resolver验证。
3. 建立完整`all-evidence` membership，并按source path建立唯一source视图；每个GA必须同时出现在all-evidence与恰好一个by-source collection。
4. 机械筛选非空`delivery-directives[]`形成secondary directive collection。
5. 在staging生成all-evidence、全部by-source collection、directive collection与index Markdown。
6. 检查每个GA的all-evidence/source cardinality、directive subset与稳定排序。
7. 最后生成`evidence-collection-index.json`。
8. 自校验staging；成功后原子发布并最后写`status: assembled` trace。

不得先写index再从index反向恢复Markdown。

## Neutral collection规则

`all-evidence.md`：

- 恰好包含全部GA；
- 按source path、range起点、range终点、GA稳定排序；
- 是完整冻结occurrence集合，不表达owner、target、dependency、Capability或order；
- 不按candidate metadata、normativity或directive分组。

`by-source/<source-key>.md`：

- `source-key`由repository-relative source path确定性编码；
- 包含该source的全部Phase 2 atom与Phase 3 gap；
- 按range起点、range终点、GA稳定排序；
- 不按candidate owner、Capability、projection、normativity或directive分组；

`delivery-directives.md`：

- 包含全部且仅包含directive非空的GA；
- 按source path、range、GA稳定排序；
- 显示冻结directive enum与逐字source-fact；
- 不解释directive影响哪个Change，不生成dependency或order；
- 不得包含由steady-state architecture、guard或实现常识推导的synthetic row。

## Markdown要求

Assembler必须显示：

- GA与evidence ref；
- source path/range；
- type、normativity、delivery-directives；
- Phase 2/3 evidence kind，但不显示任何candidate routing metadata；
- 逐字`source-fact`，使用安全code fence。

Collection heading、summary或index不得出现candidate owner/target/status/projection，或把任何集合称为Change/Capability bucket、final mapping或framework support。

重复occurrence保持独立，绝不去重。

## Derived index v3

`evidence-collection-index.json`使用`source-aligned-evidence-collection-index-v3`。

顶层只含：

- `trace-schema`
- `trace-contract-version`
- `generated-from[]`
- `rows[]`
- `rendered-artifacts[]`

每个GA row只含：

- `global-atom-id`
- `evidence-ref`
- `source-document`
- `rendered-collection-paths[]`

`rendered-collection-paths[]`顺序固定：

1. `all-evidence.md`；
2. 该GA唯一的`by-source` path；
3. 仅当该GA的`delivery-directives[]`非空时，追加`delivery-directives.md`。

因此空directive GA恰好两个path，非空directive GA恰好三个path。Row不得包含change bucket、capability bucket、owner、relation、projection或framework impact。

Rendered artifact kind只允许：

- `index`
- `all-evidence`
- `source`
- `delivery-directives`

每个rendered artifact row只含`artifact-path`、`sha256`、`collection-kind`与`scope`。`index|all-evidence|delivery-directives`的scope固定为`all`；`source`的scope为对应repository-relative source path。

## Status、trace 与完成条件

- `assembled`：resolver成功，全部neutral collection和index已原子发布且无drift。
- `blocked`：冻结authority冲突或无法建立可信resolver结果。

Phase 4 trace使用`source-aligned-phase-4-trace-v6`，所有artifact必须声明`source-aligned-trace-v7`。Blocked时清理未提交staging surface，不启动review/repair或回写上游。

成功必须满足：

- 每个GA恰好进入all-evidence与一个by-source collection；
- directive collection与冻结非空directive GA集合完全一致；
- 无Phase 1 Change/Capability bucket surface；
- validator从Phase 1–3重算全部collection/index且无drift；
- renderer使用`source-aligned-render-v11`；
- candidate metadata未出现在neutral surface，也未影响collection membership或roadmap判断。
