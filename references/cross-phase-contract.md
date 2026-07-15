# 跨 Phase 语义契约

本文件定义 Phase 1–5、Phase 1 bounded review/repair、targeted evidence patch 和 final integration gate 共同遵守的不变量。Change/Capability boundary 只以 `references/change-capability-framework-principles.md` 为准；Phase 内 artifact 和任务由对应 Phase reference 定义；JSON schema、renderer 和 validator 由 trace contract 定义。

## 权威边界

- source document 是 production obligation 的原始语义来源。
- Phase 2/3 通过原始 source 验证并冻结 `source-fact`；Phase 4以及Phase 5的mapping/refit只通过evidence resolver消费frozen evidence。唯一例外是Phase 5在已从冻结row、coverage metadata或用户明确报告取得seed locator后，可对预先固定的同一source line window执行一次只读defect verification；不得全文扫描、搜索其他位置、迭代扩窗、提取replacement evidence或把该窗口用于framework判断。
- authority 按 Phase 划分：Phase 1 initial plan和Phase 5 final plan以Markdown为内容权威；Phase 2/3以JSON为语义权威；Phase 4 collection Markdown是确定性assembler的内容权威，JSON index只是派生机器索引；Phase 5 refit与GA mapping以JSON为语义权威，review mirror不是第二份权威。
- work queue、agent report、Phase 1 reviewer/repair report 和 final integration report 是非canonical流程证据，不进入 manifest。
- Phase 1 通过 bounded review gate 后冻结 initial hypothesis。Phase 2 initial extraction 通过 validator 后冻结；只有 Phase 5 发出的唯一 `source-aligned-evidence-patch-request-v1` 可以授权 Phase 2 修改明确列出的 occurrence。
- Phase 2–5 不存在独立 Phase reviewer 或 repair loop。contract 冲突时停止并报告 blocker，不得弱化规则。

## Evidence occurrence 与 GA identity

- 每个 Phase 2 source atom 和 Phase 3 gap atom 都是独立 evidence occurrence，并恰好获得一个 `GA-####`。
- GA 不是语义去重后的 requirement。语义相同、原文相同或 range 重叠的 occurrence 仍保留独立 GA。
- Phase 3 global index 只保存 `global-atom-id` 和 `evidence-ref`；Phase 4/5 通过 resolver 取得 frozen evidence。
- 本技能不识别、标记、合并、归组或消除 semantic duplicate。
- duplicate ID、重复 source-atom key、dangling ref 和 identity cardinality 错误由 validator 拒绝。
- targeted patch 后，未受影响 evidence ref 和 GA 必须保持原 ID 与 row digest；新增 occurrence 只追加新 GA，已替换 occurrence 的旧 ref 必须显式退出 global index，不得让旧 ref 静默指向新内容。

## Coverage 与 mapping ambiguity

- Phase 3 coverage closure 是 Phase 2 atom range 的机械补集及每个 uncovered range 的处置，不是语义唯一性证明。
- `coverage-complete` 只表示 source/artifact 有效、全部 uncovered range 已补提取或安全分类、没有 blocker。非空 mapping ambiguity 不阻止 coverage complete。
- Phase 3 `mapping-ambiguities[]` 以 GA 为唯一键，只记录 `owner-change`、`relation`、`artifact-projection` 或 `target-capability` 哪些维度无法由 extraction-time hint 唯一确定；不得写 final value。
- Phase 5 必须逐 GA 裁决全部 mapping ambiguity；同GA terminal atom mapping row是唯一resolution，不得另建第二份final mapping authority。candidate mapping 不一致、`unassigned`、gap 或 final mapping 选择不是 evidence defect，不得触发上游回补。
- Phase 3若观察到一个冻结atom可能承载多个独立responsibility，不得在本Phase定性evidence defect、发起patch或仅因此`blocked`。单一mapping tuple无法无损表达时按实际维度记录ambiguity；多个responsibility仍共享唯一tuple时不得为传递finding伪造ambiguity row。Phase 5对全部GA执行只读evidence-integrity检查并完成最终分类。
- Phase 5发现Phase 3未记录的mapping ambiguity时，不得回写Phase 3或请求evidence patch；应在该GA唯一terminal mapping row直接选择完整tuple，并在reason记录late-discovered ambiguity及裁决依据。无法唯一裁决且需要产品决定时`blocked`；该发现本身不改变`accepted|adjusted`。
- source authority 自身冲突、range/source-fact 无法可信验证或 source 缺失是 blocker；不得伪装成 mapping ambiguity。

## Framework 标准与 Phase 边界

- Phase 1 和 Phase 5 必须直接读取同一份 `change-capability-framework-principles.md`。
- Phase 1 使用共享标准初次生成 coarse hypothesis；不执行 atom extraction、coverage 或 final `New` / `Modified`。
- Phase 1 执行 initial review 和最多两轮 repair；machine-readable review gate 写入 `source-aligned-phase-1-trace-v3`。Phase 2–5 不执行独立 reviewer/repair。
- Phase 4 assembler 只按 Phase 2 candidate hint 和 Phase 3 provenance 直接生成 Markdown collection，再生成派生 index；不做 semantic profile、refit、owner、projection、relation 或 Capability impact 判断。
- Phase 5 使用共享标准复审 initial framework；默认保留，只在 frozen evidence 证明 gate 失败时做最小 refit。
- Phase 5 先在 `framework-refit-trace.json` 中冻结 refit decision 和 final framework，再直接编写 final plan并完成repository baseline reconciliation和逐GA mapping；review Markdown只能由refit JSON渲染。

## 唯一 targeted evidence patch

- 每个 generation 最多生成一个 request，固定 `request-id: EPR-0001`。只有 Phase 5 可在已写入 `source-aligned-phase-5-checkpoint-v1` 后生成 `source-aligned-evidence-patch-request-v1`。
- request 只处理 `quote-mismatch`、`range-mismatch`、`mixed-independent-occurrences` 或 `missing-occurrence`；允许操作只为 `replace-quote`、`adjust-range`、`split` 或 `add`。
- request 的每个 target 必须提供具体 source document、canonical owner、有界 line window和`defect-witness`；除 missing occurrence 外还必须引用既有 source atom / GA / evidence ref。witness只可引用同source的immutable Phase 2 atom或Phase 3 disposition row，绑定origin row、完整source及window digest，且window必须落在origin ranges的连续闭包内。无法有界时必须 `blocked`。
- request前必须重验Phase 2–4 base gate仍有效，并确认当前source digest与Phase 1/2冻结值一致。existing target的base range必须位于预先固定window内且base quote仍为该range内原文substring；`quote-mismatch`只允许选错或截断substring，非原文base直接`blocked`，不得借request洗白。missing occurrence必须已有冻结coverage locator或用户提供的精确locator。核验需要扩大/再次读取窗口时立即`blocked`。
- Phase 2 targeted patch 只能修改 request target 及其必要局部上下文，并必须验证 `protected-rows` 全部保持 row hash；不得全量重提取或改变未授权 candidate mapping。
- Phase 3 随后只做 incremental reconcile，Phase 4 只做 deterministic refresh，Phase 5 只从 checkpoint resume。finding fingerprint只由request target的source/atom/GA/evidence-ref、defect和line window规范化计算，不受reason、operation或writer措辞影响。需要第二个 request、相同 finding fingerprint 在 authority digest 未变时重现或影响闭包扩张到全 framework 时，必须 `blocked`。
- 增量链任一Phase失败时，失败trace必须保留mode、request/checkpoint ref、base digest及已知affected closure。main agent随后只调用`phase5_plan_refit.py --abort-patch-chain --issue ...`执行唯一机械control transform：request/checkpoint与全部semantic row字节不变，只修改refit `status`、`issues[]`和同一history row的`status`，生成`execution-mode: checkpoint-resume`的blocked trace并清理terminal surface；该transform不是semantic writer。abort snapshot validator只重验immutable schema/ref/finding/authority/preserved-row内部自洽，不再要求已失败/已删除的Phase 3/4 surface或current Phase 1/principles仍与冻结fingerprint相同；不得以此启动第二次patch或完整Phase 5。

## Phase 5 checkpoint

- checkpoint 固定 `checkpoint-id: P5CP-0001`、`stage: mapping`、`patch-attempt.attempt: 1`，只在全局review/mapping完成后保存 input fingerprints、provisional framework、已完成 row、pending ID、允许更新范围和 preserved row digest。
- checkpoint 是 nonterminal semantic resume authority，不是 final plan authority；不得覆盖 source evidence 或 terminal Phase 5 canonical artifact。
- resume 前必须验证 request/checkpoint digest、base artifact digest 和全部 protected/preserved row digest。未受影响 fingerprint 有效的 completed row 必须复用。
- pending Capability、Change、mapping、unassigned/gap必须分别精确等于`allowed-update-scope`中的initial Capability、initial Change、GA，以及scope GA与Phase 4 unassigned/gap GA的交集；不得将scope外row标为pending。initial framework scope非空时必须由target的Phase 4 initial bucket发起，并恰好等于所选root经initial与provisional dependency/overlay拓扑形成的最小连通闭包；provisional final ID按冻结review/GA lineage反向投影到授权origin。final scope使用old/new语义：mutable old ID可消失，new ID必须由pending review/mapping实际产生。resume只允许更新该集合及其声明的final ID；既有final ID不能劫持scope外origin，跨scope overlay/dependency不得改变，`allow-roadmap-reorder`固定为`false`。
- Phase 5 trace mode固定：needs patch为`initial`；无patchterminal为`initial`；checkpoint resume后的terminal或patch lifecycle blocked为`checkpoint-resume`。
- final refit 的 `patch-history[]` 在普通路径为空；请求 patch 时恰好一条 `requested`，checkpoint resume terminal 时同一条更新为 `closed`。不得出现第二行。

## Ownership、projection 与 Capability

- Phase 2 candidate owner/projection/target 只是 extraction-time hint。
- Phase 3 不决定 planning metadata，只记录逐 GA mapping ambiguity。
- Phase 4 bucket 只是 initial framework 投影，不是 final owner 或 advancement。
- Phase 5 必须为每个 GA 给出一个 final owner Change、relation、projection 和 Capability 字段；每个ambiguity GA由该terminal mapping row唯一resolution。
- direct evidence 恰好一个 final Change owner；non-direct evidence 也必须 owner-scoped 地进入一个 final packet。
- Capability advancement 只来自 direct `spec-requirement` / `spec-guard` mapping；design/verification、non-direct和related-only mapping不推进Capability。
- existing target 为 Capability-level `modified`；absent target 首次 advancement 为 `new`，之后为 `modified`。

## 下游 handoff

- Phase 5 final packet 是完整、未语义去重的 evidence mapping，不是 requirement inventory。
- 下游规格生成可以综合多个 GA 为一个 requirement，但必须保留多对一 GA trace；该判断不属于本技能。

## Artifact Language Gate

- agent 编写的解释、判断、理由、报告和 handoff 使用简体中文。
- 固定 heading、field、enum、ID、path、代码符号和精确 source quote 可以保留英文。
- `source-fact` 保持 source 原文，不翻译、不转述、不改写。
