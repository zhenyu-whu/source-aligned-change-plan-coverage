#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from phase5_plan_refit import write_outputs  # noqa: E402
from render_source_aligned_orchestrate import render_evidence_collections, render_orchestrate  # noqa: E402
from source_aligned_trace_lib import (  # noqa: E402
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_BASELINE_SCHEMA,
    EVIDENCE_COLLECTION_INDEX_SCHEMA,
    FINAL_PACKET_INDEX_SCHEMA,
    GLOBAL_ATOM_INDEX_SCHEMA,
    MANIFEST_SCHEMA,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    sha256_file,
    write_json,
)
from validate_source_aligned_orchestrate import validate  # noqa: E402


class SourceAlignedPhase45Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.orchestrate = self.root / "openspec/orchestrate"
        self._build_fixture()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _data(self, relative: str) -> dict:
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def _write_data(self, relative: str, data: dict) -> None:
        write_json(self.root / relative, data)

    @staticmethod
    def _ref(atom_id: str) -> dict:
        return {
            "kind": "phase-2-source-atom",
            "source-document": "docs/source.md",
            "source-atom-id": atom_id,
        }

    @staticmethod
    def _phase1_plan() -> str:
        return """# Phase 1 初始计划

## 输入

- 已完整阅读 `docs/source.md`。

## Source Semantic Landscape

| Semantic Area | Coarse Source-backed Understanding | Planning Relevance | Source Hint |
| --- | --- | --- | --- |
| 核心行为 | 用户请求产生可验证结果。 | 支撑能力边界和 Change outcome。 | `docs/source.md` |

## Capability Map

| Candidate Capability | Grouping Basis | Purpose | Owns | Excludes | Coarse Source Hint | Boundary Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `cap-a` | 领域行为 | 规定持久的结果行为。 | 拥有结果行为。 | 不拥有实现细节。 | `docs/source.md` | 实现替换后仍成立。 |

## Change 切分原则

- 按 source-backed outcome 切分；Capability 先形成，但不决定 Change 边界。
- Phase 1 未执行 obligation extraction，所有 boundary 均为 hypothesis。

## Change Roadmap

- Change 名称：`change-a`
- 单一 intent：让用户获得可验证结果。
- source-backed outcome：交付可观察且可验证的行为。
- 来源 evidence hint：`docs/source.md`。
- 范围内：结果行为和必要约束。
- 范围外：后续增强。
- behavior completeness profile：
  - trigger/context：API 请求。
  - normative behavior：系统处理请求。
  - observable outcome / invariant：返回可验证结果。
  - important exception / error semantics：保留来源约束。
  - acceptance evidence：integration test。
- 硬依赖：无。
- 排序理由：无硬依赖，是最薄可验收 outcome。
- 独立完成与归档：可以独立批准、实现、验收和归档。
- 拆分/合并判断：再拆分会产生无意义半状态。

## Change-Capability Overlay

| Change | Candidate Capability | Roadmap Role | Direct Behavior Delta Hypothesis | Coarse Source Hint |
| --- | --- | --- | --- | --- |
| `change-a` | `cap-a` | `first-advancement` | 建立 source-backed 行为。 | `docs/source.md` |

## Phase 1 风险检查

1. source manifest完整且全部read-full：通过。
2. 未提前执行atom extraction：通过。
3. Capability gate：通过。
4. Change gate：通过。
5. behavior completeness：通过。
6. overlay：通过。
7. roadmap：通过。
8. foundation：不适用。
9. 隐藏Capability名称：通过。
10. 隐藏roadmap：通过。
11. 多对多检查：通过。

## Phase 1 语言自检

解释内容已使用简体中文。
"""

    @staticmethod
    def _final_plan() -> str:
        return """# Final Change Plan

## 输入

- 复用 Phase 1–4 的冻结证据并完成复审。

## Source Semantic Landscape

| Semantic Area | Final Source-backed Understanding | Planning Relevance | Evidence Collection |
| --- | --- | --- | --- |
| 核心行为 | 用户请求产生可验证结果。 | 支撑最终能力与Change边界。 | `source-evidence-collections/index.md` |

## Capability Map

| Capability | Purpose | Owns | Excludes | Boundary Rationale |
| --- | --- | --- | --- | --- |
| `cap-a` | 规定持久的结果行为。 | 拥有结果行为。 | 不拥有实现细节。 | 实现替换后仍成立。 |

## Change 切分原则

- 复用共享标准，以最小 refit 保留原框架。

## Change Roadmap

- Change 名称：`change-a`
- 单一 intent：让用户获得可验证结果。
- source-backed outcome：交付可观察且可验证的行为。
- 来源 evidence hint：Phase 4 原文集合。
- 范围内：结果行为和必要约束。
- 范围外：后续增强。
- behavior completeness profile：
  - trigger/context：API 请求。
  - normative behavior：系统处理请求。
  - observable outcome / invariant：返回可验证结果。
  - important exception / error semantics：保留来源约束。
  - acceptance evidence：integration test。
- 硬依赖：无。
- 排序理由：无硬依赖，是最薄可验收 outcome。
- 独立完成与归档：可以独立批准、实现、验收和归档。
- 拆分/合并判断：再拆分会产生无意义半状态。

## Change-Capability Overlay

| Change | Capability | Capability Impact | Direct Behavior Delta |
| --- | --- | --- | --- |
| `change-a` | `cap-a` | `new` | 建立 source-backed 行为。 |

## Phase 5 风险检查

1. final framework逐项通过共享gate。
2. mapping覆盖全部GA。

## Phase 5 语言自检

解释内容已使用简体中文。
"""

    @staticmethod
    def _atom(atom_id: str, start: int, end: int, fact: str, status: str, projection: str, owner: str, target: str) -> dict:
        return {
            "source-atom-id": atom_id,
            "line-ranges": [{"start": start, "end": end}],
            "atom-type": "context" if status == "contextual-candidate" else "behavior",
            "source-fact": fact,
            "normativity": "context" if status == "contextual-candidate" else "must",
            "candidate-status": status,
            "candidate-artifact-projection": projection,
            "candidate-owner-change": owner,
            "candidate-target-capability": target,
            "rationale": "保留该独立 evidence occurrence，供后续完整复审。",
        }

    def _review(self) -> str:
        gap_rows = []
        for ga, provenance in (
            ("GA-0002", "phase-2-unassigned"),
            ("GA-0003", "phase-2-contextual"),
            ("GA-0004", "phase-2-unresolved"),
            ("GA-0005", "phase-3-gap"),
        ):
            gap_rows.append(
                f"| `{ga}` | `{provenance}` | `{ga}` frozen source-fact | mapped | `change-a` | `none` | 归入同一结果范围且不推进Capability。 |"
            )
        return """# Plan Refit Review

## Capability Review

| Input Capability | Evidence Collection | Decision | Final Capability(s) | Failed or Passed Gates | Reason |
| --- | --- | --- | --- | --- | --- |
| `cap-a` | `by-input-capability/cap-a.md` | `keep` | `cap-a` | 全部Capability gate通过 | 原文集合支持稳定行为边界。 |

## Change Review

| Input Change | Evidence Collection | Decision | Final Change(s) | Failed or Passed Gates | Reason |
| --- | --- | --- | --- | --- | --- |
| `change-a` | `by-input-change/change-a.md` | `keep` | `change-a` | 全部Change gate通过 | 原文集合支持单一可验收结果。 |

## Unassigned and Gap Review

| GA | Provenance | Source Fact Reference | Disposition | Final Change | Final Capability | Reason |
| --- | --- | --- | --- | --- | --- | --- |
""" + "\n".join(gap_rows) + """

## Final Decision

- Status: accepted
- framework变化摘要：无
- recheck/blocker及最小下一步：无
"""

    def _build_fixture(self) -> None:
        source_text = "same | requirement\n```embedded```\nsame outcome\nunassigned fact\ncontextual fact\nunresolved fact\ngap must\nbackground\n"
        source_path = self._write("docs/source.md", source_text)
        source_sha = sha256_file(source_path)
        plan_path = self._write("openspec/orchestrate/phase-works/phase-1/initial-change-plan.md", self._phase1_plan())
        self._write(
            "openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md",
            "| Source Document | Read Status | Source Role | Coarse Topics / Paths | Notes |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| docs/source.md | read-full | main | result behavior | canonical source |\n",
        )
        self._write("openspec/orchestrate/phase-works/phase-1/phase-1-agent-report.md", "Phase 1通过。\n")
        write_json(self.orchestrate / "trace/phase-1.trace.json", {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-1"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "initial-plan-written",
            "source-documents": [{
                "source-document": "docs/source.md",
                "read-status": "read-full",
                "source-role": "main",
                "coarse-topics-paths": "result behavior",
                "notes": "canonical source",
                "line-count": 8,
                "source-sha256": source_sha,
            }],
            "initial-change-plan": {
                "artifact-path": "openspec/orchestrate/phase-works/phase-1/initial-change-plan.md",
                "sha256": sha256_file(plan_path),
            },
        })

        atom_root = self.orchestrate / "phase-works/phase-2/source-obligation-atoms"
        self._write(
            "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/work-queue.md",
            "| Batch | Source Documents | Canonical Owner |\n| --- | --- | --- |\n| B1 | docs/source.md | owner-a |\n",
        )
        self._write("openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/index.md", "索引。\n")
        self._write("openspec/orchestrate/phase-works/phase-2/phase-2-agent-report.md", "Phase 2通过。\n")
        atom_path = atom_root / "docs--source.atoms.json"
        atoms = [
            self._atom("SA-0001", 1, 3, "same | requirement\n```embedded```\nsame outcome", "direct-candidate", "spec-requirement", "change-a", "cap-a"),
            self._atom("SA-0002", 4, 4, "unassigned fact", "unassigned", "unsure", "unassigned", "none"),
            self._atom("SA-0003", 5, 5, "contextual fact", "contextual-candidate", "contextual-only", "contextual", "none"),
            self._atom("SA-0004", 6, 6, "unresolved fact", "unresolved-conflict", "unsure", "none", "none"),
        ]
        blockers = ["SA-0004需要Phase 5结合完整原文集合消解候选冲突。"]
        write_json(atom_path, {
            "trace-schema": SOURCE_ATOMS_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "source-document": "docs/source.md",
            "source-sha256": source_sha,
            "read-status": "read-full",
            "canonical-owner": "owner-a",
            "source-role": "main",
            "phase-1-candidate-changes-capabilities-considered": [{
                "change": "change-a", "capabilities": ["cap-a"], "note": "仅作为extraction hint。",
            }],
            "source-atoms": atoms,
            "blockers": blockers,
            "language-self-check": "解释字段已使用简体中文。",
        })
        write_json(self.orchestrate / "trace/phase-2.trace.json", {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-2"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "source-atoms-written",
            "work-queue-path": "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/work-queue.md",
            "sources": [{
                "source-document": "docs/source.md",
                "atom-json-path": "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json",
                "atom-json-sha256": sha256_file(atom_path),
                "atom-markdown-path": "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.md",
                "canonical-owner": "owner-a",
                "read-status": "read-full",
                "atom-count": 4,
                "blockers": blockers,
            }],
            "phase-report-path": "openspec/orchestrate/phase-works/phase-2/phase-2-agent-report.md",
        })

        global_path = self.orchestrate / "change-capability-anchors/obligation-atom-index.json"
        global_rows = [
            {"global-atom-id": f"GA-{index:04d}", "evidence-ref": self._ref(f"SA-{index:04d}")}
            for index in range(1, 5)
        ]
        global_rows.append({
            "global-atom-id": "GA-0005",
            "evidence-ref": {"kind": "phase-3-gap-atom", "gap-atom-id": "P3-GAP-0001"},
        })
        write_json(global_path, {
            "trace-schema": GLOBAL_ATOM_INDEX_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "artifact-path": "openspec/orchestrate/change-capability-anchors/obligation-atom-index.md",
            "global-atoms": global_rows,
        })
        coverage_path = self.orchestrate / "phase-works/phase-3/coverage-review.json"
        write_json(coverage_path, {
            "trace-schema": PHASE3_COVERAGE_REVIEW_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "artifact-path": "openspec/orchestrate/phase-works/phase-3/coverage-review.md",
            "documents": [{
                "source-document": "docs/source.md",
                "source-sha256": source_sha,
                "line-count": 8,
                "phase-2-atom-path": "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json",
                "phase-2-atom-sha256": sha256_file(atom_path),
                "covered-ranges": [{"start": 1, "end": 6}],
                "candidate-uncovered-ranges": [{"start": 7, "end": 8}],
            }],
            "gap-atoms": [{
                "gap-atom-id": "P3-GAP-0001",
                "source-document": "docs/source.md",
                "line-ranges": [{"start": 7, "end": 7}],
                "source-fact": "gap must",
                "atom-type": "behavior",
                "normativity": "must",
                "review-judgment": "该行包含未被Phase 2提取的生产义务。",
            }],
            "remainder-dispositions": [
                {
                    "disposition-id": "RD-0001",
                    "source-document": "docs/source.md",
                    "line-ranges": [{"start": 7, "end": 7}],
                    "classification": "missing-obligation",
                    "linked-gap-atom-ids": ["P3-GAP-0001"],
                    "reason": "补提取遗漏义务。",
                },
                {
                    "disposition-id": "RD-0002",
                    "source-document": "docs/source.md",
                    "line-ranges": [{"start": 8, "end": 8}],
                    "classification": "safe-non-obligation",
                    "linked-gap-atom-ids": [],
                    "reason": "仅为背景。",
                },
            ],
            "recheck-sources": [],
            "summary": {
                "source-documents": 1,
                "phase-2-atoms": 4,
                "gap-atoms": 1,
                "global-atoms": 5,
                "candidate-uncovered-ranges": 1,
                "remainder-dispositions": {
                    "blocked": 0,
                    "missing-obligation": 1,
                    "requires-reextract": 0,
                    "safe-non-obligation": 1,
                },
            },
            "decision": "coverage-complete",
            "language-self-check": "判断与理由已使用简体中文。",
        })
        write_json(self.orchestrate / "trace/phase-3.trace.json", {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-3"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "decision": "coverage-complete",
            "global-atom-index-path": "openspec/orchestrate/change-capability-anchors/obligation-atom-index.json",
            "global-atom-index-sha256": sha256_file(global_path),
            "coverage-review-path": "openspec/orchestrate/phase-works/phase-3/coverage-review.json",
            "coverage-review-sha256": sha256_file(coverage_path),
            "reviewer-loop": {
                "status": "passed",
                "writer-id": "writer-phase-3",
                "reviewer-id": "reviewer-phase-3",
                "validator-status": "passed",
                "findings": [],
                "repairs": [],
            },
        })
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        render_orchestrate(self.orchestrate, "phase3-global-index", write=True)
        render_orchestrate(self.orchestrate, "phase3-coverage-review", write=True)

        collection_path = self.orchestrate / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        collection_rows = []
        for index, global_row in enumerate(global_rows, start=1):
            collection_rows.append({
                "global-atom-id": f"GA-{index:04d}",
                "evidence-ref": global_row["evidence-ref"],
                "change-bucket": "change-a" if index == 1 else "unassigned-and-gap",
                "capability-bucket": "cap-a" if index == 1 else "none",
            })
        write_json(collection_path, {
            "trace-schema": EVIDENCE_COLLECTION_INDEX_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "assembled",
            "rows": collection_rows,
            "issues": [],
            "language-self-check": "机械汇总未执行语义调整。",
        })
        render_orchestrate(self.orchestrate, "phase4-evidence-collections", write=True)
        self._write("openspec/orchestrate/phase-works/phase-4/phase-4-agent-report.md", "Phase 4 Status: assembled\n")
        write_json(self.orchestrate / "trace/phase-4.trace.json", {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-4"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "assembled",
            "evidence-collection-index-path": "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/evidence-collection-index.json",
            "evidence-collection-index-sha256": sha256_file(collection_path),
            "renderer-result-summary": {
                "render-contract-version": "source-aligned-render-v5",
                "rendered-files": 4,
                "global-atoms": 5,
            },
        })

        self._write("openspec/orchestrate/phase-works/phase-5/change-plan.md", self._final_plan())
        self._write("openspec/orchestrate/phase-works/phase-5/plan-refit-review.md", self._review())
        self._write("openspec/orchestrate/phase-works/phase-5/phase-5-agent-report.md", "Phase 5 Status: accepted\n")
        mapping_rows = []
        for index, global_row in enumerate(global_rows, start=1):
            direct = index == 1
            mapping_rows.append({
                "global-atom-id": f"GA-{index:04d}",
                "evidence-ref": global_row["evidence-ref"],
                "final-owner-change": "change-a",
                "final-relation": "direct" if direct else ("context" if index in {2, 3} else "reference"),
                "final-artifact-projection": "spec-requirement" if direct else "contextual-only",
                "final-capability-impact": "new" if direct else "none",
                "final-target-capability": "cap-a" if direct else "none",
                "related-capabilities": [],
                "reason": "原文支持该最终归属，且不执行语义去重。",
            })
        write_json(self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json", {
            "trace-schema": ATOM_PLAN_MAPPING_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "artifact-path": "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.md",
            "rows": mapping_rows,
        })
        write_outputs(self.orchestrate)
        self._write_manifest()

    def _write_manifest(self) -> None:
        specs = [
            ("trace/phase-1.trace.json", PHASE_TRACE_SCHEMAS["phase-1"], "phase-1"),
            ("trace/phase-2.trace.json", PHASE_TRACE_SCHEMAS["phase-2"], "phase-2"),
            ("phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json", SOURCE_ATOMS_SCHEMA, "phase-2"),
            ("change-capability-anchors/obligation-atom-index.json", GLOBAL_ATOM_INDEX_SCHEMA, "phase-3"),
            ("phase-works/phase-3/coverage-review.json", PHASE3_COVERAGE_REVIEW_SCHEMA, "phase-3"),
            ("trace/phase-3.trace.json", PHASE_TRACE_SCHEMAS["phase-3"], "phase-3"),
            ("phase-works/phase-4/source-evidence-collections/evidence-collection-index.json", EVIDENCE_COLLECTION_INDEX_SCHEMA, "phase-4"),
            ("trace/phase-4.trace.json", PHASE_TRACE_SCHEMAS["phase-4"], "phase-4"),
            ("phase-works/phase-5/atom-plan-mapping.json", ATOM_PLAN_MAPPING_SCHEMA, "phase-5"),
            ("phase-works/phase-5/capability-baseline-reconciliation.json", CAPABILITY_BASELINE_SCHEMA, "phase-5"),
            ("phase-works/phase-5/final-packet-index.json", FINAL_PACKET_INDEX_SCHEMA, "phase-5"),
            ("trace/phase-5.trace.json", PHASE_TRACE_SCHEMAS["phase-5"], "phase-5"),
        ]
        artifacts = []
        for relative, schema, phase in specs:
            path = self.orchestrate / relative
            if not path.exists():
                continue
            artifacts.append({
                "artifact-path": f"openspec/orchestrate/{relative.replace('.json', '.md')}",
                "trace-path": f"openspec/orchestrate/{relative}",
                "trace-schema": schema,
                "sha256": sha256_file(path),
                "phase": phase,
                "role": "trace",
            })
        statuses = {}
        for phase in ("phase-1", "phase-2", "phase-3", "phase-4", "phase-5"):
            trace = self._data(f"openspec/orchestrate/trace/{phase}.trace.json")
            statuses[phase] = trace.get("status") or trace.get("decision")
        write_json(self.orchestrate / "trace/manifest.json", {
            "trace-schema": MANIFEST_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "orchestrate-dir": "openspec/orchestrate",
            "phase-statuses": statuses,
            "artifacts": artifacts,
        })

    def _result(self, phase: str = "all", complete: bool = False) -> dict:
        return validate(self.orchestrate, self.root, phase, complete)

    def _assert_rule(self, result: dict, rule: str) -> None:
        self.assertIn(rule, [issue["rule_id"] for issue in result["issues"]], result)

    def test_all_phase_complete(self) -> None:
        result = self._result("all", complete=True)
        self.assertTrue(result["ok"], result)

    def test_phase4_renders_without_original_source(self) -> None:
        (self.root / "docs/source.md").unlink()
        index = self.orchestrate / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        outputs = render_evidence_collections(self.orchestrate, index)
        self.assertIn("same | requirement\n```embedded```\nsame outcome", outputs[index.parent / "by-input-change/change-a.md"])
        self.assertTrue(self._result("phase-4")["ok"])

    def test_phase4_preserves_source_fact_with_adaptive_fence(self) -> None:
        dossier = (self.orchestrate / "phase-works/phase-4/source-evidence-collections/by-input-change/change-a.md").read_text(encoding="utf-8")
        self.assertIn("````text\nsame | requirement\n```embedded```\nsame outcome\n````", dossier)

    def test_phase4_renders_empty_initial_units(self) -> None:
        plan = self.orchestrate / "phase-works/phase-1/initial-change-plan.md"
        text = plan.read_text(encoding="utf-8")
        text = text.replace(
            "| `cap-a` | 领域行为 | 规定持久的结果行为。 | 拥有结果行为。 | 不拥有实现细节。 | `docs/source.md` | 实现替换后仍成立。 |",
            "| `cap-a` | 领域行为 | 规定持久的结果行为。 | 拥有结果行为。 | 不拥有实现细节。 | `docs/source.md` | 实现替换后仍成立。 |\n"
            "| `cap-empty` | 领域行为 | 规定另一个稳定行为。 | 拥有另一类行为。 | 不拥有cap-a行为。 | `docs/source.md` | 可独立维护。 |",
        )
        second_change = """
- Change 名称：`change-empty`
- 单一 intent：交付另一个结果。
- source-backed outcome：形成另一个可验收结果。
"""
        text = text.replace("\n## Change-Capability Overlay", second_change + "\n## Change-Capability Overlay")
        plan.write_text(text, encoding="utf-8")
        index = self.orchestrate / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        outputs = render_evidence_collections(self.orchestrate, index)
        self.assertIn("无关联 evidence occurrence", outputs[index.parent / "by-input-change/change-empty.md"])
        self.assertIn("无关联 evidence occurrence", outputs[index.parent / "by-input-capability/cap-empty.md"])

    def test_phase4_mechanical_buckets_and_sections(self) -> None:
        index = self._data("openspec/orchestrate/phase-works/phase-4/source-evidence-collections/evidence-collection-index.json")
        self.assertEqual(index["rows"][0]["change-bucket"], "change-a")
        self.assertTrue(all(row["change-bucket"] == "unassigned-and-gap" for row in index["rows"][1:]))
        text = (self.orchestrate / "phase-works/phase-4/source-evidence-collections/unassigned-and-gap.md").read_text(encoding="utf-8")
        for heading in ("Phase 2 Unassigned", "Phase 2 Unresolved / Contextual", "Phase 3 Gap Atoms"):
            self.assertIn(heading, text)

    def test_phase4_wrong_bucket_is_rejected(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        data = self._data(relative)
        data["rows"][1]["change-bucket"] = "change-a"
        self._write_data(relative, data)
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-change-bucket")

    def test_phase4_duplicate_ga_is_rejected(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        data = self._data(relative)
        data["rows"].append(dict(data["rows"][0]))
        self._write_data(relative, data)
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-ga-duplicate")

    def test_phase4_missing_ga_is_rejected(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        data = self._data(relative)
        data["rows"].pop()
        self._write_data(relative, data)
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-ga-coverage")

    def test_phase4_dangling_evidence_ref_is_rejected(self) -> None:
        global_relative = "openspec/orchestrate/change-capability-anchors/obligation-atom-index.json"
        global_index = self._data(global_relative)
        dangling = self._ref("SA-9999")
        global_index["global-atoms"][0]["evidence-ref"] = dangling
        self._write_data(global_relative, global_index)
        collection_relative = "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        collection = self._data(collection_relative)
        collection["rows"][0]["evidence-ref"] = dangling
        self._write_data(collection_relative, collection)
        self._write_manifest()
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "evidence-resolver-dangling")

    def test_phase5_review_must_cover_every_unassigned_ga(self) -> None:
        path = self.orchestrate / "phase-works/phase-5/plan-refit-review.md"
        text = path.read_text(encoding="utf-8")
        text = "\n".join(line for line in text.splitlines() if "`GA-0005`" not in line) + "\n"
        path.write_text(text, encoding="utf-8")
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-review-gap-coverage")

    def test_phase5_mapping_v4_rejects_repeated_source_fields(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json"
        data = self._data(relative)
        data["rows"][0]["source-document"] = "docs/source.md"
        self._write_data(relative, data)
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-mapping-contract")

    def test_phase5_packet_drift_is_rejected(self) -> None:
        packet = self.orchestrate / "change-capability-anchors/change-a/change-a.md"
        packet.write_text(packet.read_text(encoding="utf-8").replace("same outcome", "changed outcome"), encoding="utf-8")
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-packet-drift")

    def test_phase5_adjusted_new_capability_from_gap(self) -> None:
        plan = self.orchestrate / "phase-works/phase-5/change-plan.md"
        plan_text = plan.read_text(encoding="utf-8")
        plan_text = plan_text.replace(
            "| `cap-a` | 规定持久的结果行为。 | 拥有结果行为。 | 不拥有实现细节。 | 实现替换后仍成立。 |",
            "| `cap-a` | 规定持久的结果行为。 | 拥有结果行为。 | 不拥有实现细节。 | 实现替换后仍成立。 |\n"
            "| `cap-b` | 规定gap暴露的新稳定行为。 | 拥有补充行为。 | 不拥有cap-a结果行为。 | 独立于当前实现成立。 |",
        ).replace(
            "| `change-a` | `cap-a` | `new` | 建立 source-backed 行为。 |",
            "| `change-a` | `cap-a` | `new` | 建立 source-backed 行为。 |\n"
            "| `change-a` | `cap-b` | `new` | gap evidence建立新的稳定行为。 |",
        )
        plan.write_text(plan_text, encoding="utf-8")
        review = self.orchestrate / "phase-works/phase-5/plan-refit-review.md"
        review_text = review.read_text(encoding="utf-8")
        review_text = review_text.replace(
            "| `GA-0005` | `phase-3-gap` | `GA-0005` frozen source-fact | mapped | `change-a` | `none` | 归入同一结果范围且不推进Capability。 |",
            "| `GA-0005` | `phase-3-gap` | `GA-0005` frozen source-fact | direct advancement | `change-a` | `cap-b` | gap暴露新的稳定行为边界。 |",
        ).replace("- Status: accepted", "- Status: adjusted").replace("framework变化摘要：无", "framework变化摘要：新增cap-b Capability")
        review.write_text(review_text, encoding="utf-8")
        mapping_path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        gap_row = mapping["rows"][4]
        gap_row["final-relation"] = "direct"
        gap_row["final-artifact-projection"] = "spec-requirement"
        gap_row["final-capability-impact"] = "new"
        gap_row["final-target-capability"] = "cap-b"
        write_json(mapping_path, mapping)
        write_outputs(self.orchestrate)
        self._write_manifest()
        result = self._result("all", complete=True)
        self.assertTrue(result["ok"], result)

    def test_phase5_accepted_rejects_boundary_change(self) -> None:
        plan = self.orchestrate / "phase-works/phase-5/change-plan.md"
        plan.write_text(plan.read_text(encoding="utf-8").replace("结果行为和必要约束。", "不同的结果边界。"), encoding="utf-8")
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-review-status-consistency")

    def test_phase5_helper_uses_frozen_evidence_without_source(self) -> None:
        (self.root / "docs/source.md").unlink()
        write_outputs(self.orchestrate)
        packet = self.orchestrate / "change-capability-anchors/change-a/change-a.md"
        self.assertIn("same | requirement", packet.read_text(encoding="utf-8"))
        self.assertTrue(self._result("phase-5")["ok"])

    def test_phase5_needs_coverage_recheck_is_valid_nonterminal_state(self) -> None:
        work = self.orchestrate / "phase-works/phase-5"
        review = work / "plan-refit-review.md"
        review.write_text(review.read_text(encoding="utf-8").replace("- Status: accepted", "- Status: needs-coverage-recheck"), encoding="utf-8")
        for path in (
            work / "change-plan.md",
            work / "atom-plan-mapping.json",
            work / "atom-plan-mapping.md",
            work / "capability-baseline-reconciliation.json",
            work / "capability-baseline-reconciliation.md",
            work / "final-packet-index.json",
            self.orchestrate / "change-plan.md",
            self.orchestrate / "change-capability-anchors/index.md",
        ):
            if path.exists():
                path.unlink()
        shutil.rmtree(self.orchestrate / "change-capability-anchors/change-a")
        write_json(self.orchestrate / "trace/phase-5.trace.json", {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "needs-coverage-recheck",
            "plan-refit-review-path": "openspec/orchestrate/phase-works/phase-5/plan-refit-review.md",
            "plan-refit-review-sha256": sha256_file(review),
            "issues": ["GA-0004的frozen source-fact不足以支持安全判断，需要targeted recheck。"],
        })
        self._write_manifest()
        self.assertTrue(self._result("phase-5")["ok"])
        complete = self._result("all", complete=True)
        self.assertFalse(complete["ok"])
        self._assert_rule(complete, "manifest-complete-phase-status")

    def test_phase5_legacy_artifact_is_rejected(self) -> None:
        self._write("openspec/orchestrate/phase-works/phase-5/phase5-refit.config.json", "{}\n")
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-legacy-artifact")

    def test_phase4_renderer_cleans_legacy_artifacts(self) -> None:
        legacy_file = self._write("openspec/orchestrate/phase-works/phase-4/input-change-plan.md", "legacy\n")
        legacy_dir = self.orchestrate / "phase-works/phase-4/source-window-dossiers"
        legacy_dir.mkdir(parents=True)
        (legacy_dir / "index.md").write_text("legacy\n", encoding="utf-8")
        render_orchestrate(self.orchestrate, "phase4-evidence-collections", write=True)
        self.assertFalse(legacy_file.exists())
        self.assertFalse(legacy_dir.exists())

    def test_phase5_helper_has_no_config_interface(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "phase5_plan_refit.py"), "--config", "legacy.json"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(completed.returncode, 0)

    def test_phase1_and_phase5_share_one_principles_document(self) -> None:
        shared = "references/change-capability-framework-principles.md"
        for relative in ("references/phase-1-initial-change-plan.md", "references/phase-5-targeted-plan-adjustment.md"):
            text = (SKILL_DIR / relative).read_text(encoding="utf-8")
            self.assertIn(shared, text)
            self.assertNotIn("## Capability gate", text)
            self.assertNotIn("## Change gate", text)


if __name__ == "__main__":
    unittest.main()
