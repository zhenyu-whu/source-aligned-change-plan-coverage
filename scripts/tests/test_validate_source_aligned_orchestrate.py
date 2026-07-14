#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from phase5_plan_refit import budget_status, load_global_atoms_json, load_mapping  # noqa: E402
from render_source_aligned_orchestrate import RENDER_CONTRACT_VERSION, render_orchestrate  # noqa: E402
from source_aligned_trace_lib import (  # noqa: E402
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_BASELINE_SCHEMA,
    FINAL_PACKET_INDEX_SCHEMA,
    GLOBAL_ATOM_INDEX_SCHEMA,
    MANIFEST_SCHEMA,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    SOURCE_WINDOW_INDEX_SCHEMA,
    TRACE_CONTRACT_VERSION,
    sha256_file,
    sha256_text,
    write_json,
)
from validate_source_aligned_orchestrate import validate  # noqa: E402


class SourceAlignedValidatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.orchestrate = self.root / "openspec/orchestrate"
        self._build_valid_fixture()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _read_json(self, relative: str) -> dict:
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def _write_data(self, relative: str, data: dict) -> None:
        write_json(self.root / relative, data)

    def _phase1_plan(self) -> str:
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
| `cap-a` | feature area | 规定持久行为。 | 拥有结果行为。 | 不拥有实现细节。 | `docs/source.md` | 实现替换后仍成立。 |

## Change 切分原则

- 按 source-backed outcome 切分；Capability 先形成，但不决定 Change 边界。
- Phase 1 未执行 obligation extraction，所有 boundary 均为 hypothesis。

## Change Roadmap

- Change 名称：`change-a`
- 单一 intent：让用户获得可验证结果。
- source-backed outcome：交付可观察且可验证的行为。
- 来源 evidence hint：`docs/source.md`。
- 范围内：行为基线。
- 范围外：后续增强。
- behavior completeness profile：
  - trigger/context：API 请求。
  - normative behavior：系统处理请求。
  - observable outcome / invariant：返回可验证结果。
  - important exception / error semantics：未由 source 指定。
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

1. Source 完整性：通过。
2. Phase 边界：通过。
3. Capability 稳定性：通过。
4. Change 粒度：通过。
5. Behavior 完整性：通过。
6. Overlay 合法性：通过。
7. Roadmap 顺序：通过。
8. Foundation 合法性：通过。
9. Hide Capability Names：通过。
10. Hide Roadmap：通过。
11. Post-mapping audit：通过。

## Phase 1 语言自检

解释内容已使用简体中文。
"""

    @staticmethod
    def _source_atom(atom_id: str, start: int, end: int) -> dict:
        return {
            "source-atom-id": atom_id,
            "line-ranges": [{"start": start, "end": end}],
            "atom-type": "behavior",
            "source-fact": "same requirement\nsame outcome",
            "normativity": "must",
            "candidate-status": "direct-candidate",
            "candidate-artifact-projection": "spec-requirement",
            "candidate-owner-change": "change-a",
            "candidate-target-capability": "cap-a",
            "rationale": "来源明确要求同一可观察行为。",
        }

    @staticmethod
    def _evidence_ref(atom_id: str) -> dict:
        return {
            "kind": "phase-2-source-atom",
            "source-document": "docs/source.md",
            "source-atom-id": atom_id,
        }

    def _mapping_row(self, ga_id: str, atom_id: str, start: int, end: int) -> dict:
        return {
            "global-atom-id": ga_id,
            "evidence-ref": self._evidence_ref(atom_id),
            "source-document": "docs/source.md",
            "line-ranges": [{"start": start, "end": end}],
            "final-owner-type": "executable-change",
            "final-owner-change": "change-a",
            "final-capability-impact": "new",
            "final-target-capability": "cap-a",
            "related-capabilities": [],
            "final-artifact-projection": "spec-requirement",
            "final-relation": "direct",
            "plan-decision": "direct-owner",
            "reason": "依据 source-window 语义映射到同一可归档结果。",
        }

    def _packet_text(self, ga_rows: list[tuple[str, dict]]) -> str:
        lines = [
            "# change-a\n\n",
            "本 packet 是完整、未做语义去重的 evidence mapping，不是 requirement inventory；下游综合多个 GA 时必须保留多对一 trace。\n\n",
            "| Global Atom ID | Evidence Reference | Capability Impact | Target Capability | Related Capabilities | Relation |\n",
            "| --- | --- | --- | --- | --- | --- |\n",
        ]
        for ga_id, evidence_ref in ga_rows:
            ref = json.dumps(evidence_ref, ensure_ascii=False, sort_keys=True)
            lines.append(f"| `{ga_id}` | `{ref}` | `new` | `cap-a` | `None` | `direct` |\n")
        return "".join(lines)

    def _build_valid_fixture(self) -> None:
        source = "same requirement\nsame outcome\nsame requirement\nsame outcome\n" + "\n".join(
            f"background {i}" for i in range(5, 11)
        ) + "\n"
        self._write("docs/source.md", source)
        plan = self._phase1_plan()
        self._write("openspec/orchestrate/phase-works/phase-1/initial-change-plan.md", plan)
        self._write(
            "openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md",
            "| Source Document | Read Status | Source Role | Coarse Topics / Paths | Notes |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| docs/source.md | read-full | main | topic | note |\n",
        )
        self._write("openspec/orchestrate/phase-works/phase-1/phase-1-agent-report.md", "通过。\n")
        self._write(
            "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/work-queue.md",
            "| Batch | Source Documents | Canonical Owner |\n| --- | --- | --- |\n| B1 | docs/source.md | owner-a |\n",
        )
        self._write("openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/index.md", "索引。\n")
        self._write("openspec/orchestrate/phase-works/phase-2/phase-2-agent-report.md", "通过。\n")
        self._write("openspec/orchestrate/phase-works/phase-4/input-change-plan.md", plan)
        self._write("openspec/orchestrate/phase-works/phase-4/source-window-dossiers/index.md", "索引。\n")
        self._write("openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md", "语义画像通过。\n")
        self._write("openspec/orchestrate/phase-works/phase-4/source-window-grounding-issues.md", "无问题。\n")
        self._write("openspec/orchestrate/phase-works/phase-4/phase-4-agent-report.md", "Phase 4 Status: grounded\n")
        self._write("openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-change/change-a.md", "窗口证据。\n")
        self._write("openspec/orchestrate/phase-works/phase-5/input-change-plan.md", plan)
        self._write("openspec/orchestrate/phase-works/phase-5/source-window-refit-trace.md", "逐 GA refit trace。\n")
        self._write("openspec/orchestrate/phase-works/phase-5/change-plan.md", "# Final Plan\n\nroadmap: change-a\n")
        self._write("openspec/orchestrate/change-plan.md", "# Final Plan\n\nroadmap: change-a\n")
        for name, text in (
            ("capability-progression-review.md", "Capability progression unchanged.\n"),
            ("change-complexity-review.md", "按 intent/outcome/acceptance 审阅，occurrence count仅为trace。\n"),
            ("plan-refit-decision-log.md", "保持 change-a。\n"),
            ("alignment-final-report.md", "全部 evidence occurrence 已映射。\n"),
            ("change-capability-human-plan.md", "未做语义去重；下游保留多对一 GA trace。roadmap: change-a\n"),
            ("phase-5-agent-report.md", "Phase 5 Status: adjusted\n"),
        ):
            self._write(f"openspec/orchestrate/phase-works/phase-5/{name}", text)
        self._write("openspec/orchestrate/change-capability-anchors/index.md", "change-a\n")

        source_path = self.root / "docs/source.md"
        source_sha = sha256_file(source_path)
        phase1_trace = {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-1"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "initial-plan-written",
            "source-documents": [{
                "source-document": "docs/source.md",
                "read-status": "read-full",
                "source-role": "main",
                "coarse-topics-paths": "topic",
                "notes": "note",
                "line-count": 10,
                "source-sha256": source_sha,
            }],
            "initial-change-plan": {
                "artifact-path": "openspec/orchestrate/phase-works/phase-1/initial-change-plan.md",
                "sha256": sha256_file(self.orchestrate / "phase-works/phase-1/initial-change-plan.md"),
            },
        }
        write_json(self.orchestrate / "trace/phase-1.trace.json", phase1_trace)

        atom_path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        phase2 = {
            "trace-schema": SOURCE_ATOMS_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "source-document": "docs/source.md",
            "source-sha256": source_sha,
            "read-status": "read-full",
            "canonical-owner": "owner-a",
            "source-role": "main",
            "phase-1-candidate-changes-capabilities-considered": [
                {"change": "change-a", "capabilities": ["cap-a"], "note": "仅作为 extraction hint。"}
            ],
            "source-atoms": [self._source_atom("SA-0001", 1, 2), self._source_atom("SA-0002", 3, 4)],
            "blockers": [],
            "language-self-check": "解释字段已使用简体中文。",
        }
        write_json(atom_path, phase2)
        write_json(
            self.orchestrate / "trace/phase-2.trace.json",
            {
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
                    "atom-count": 2,
                    "blockers": [],
                }],
                "phase-report-path": "openspec/orchestrate/phase-works/phase-2/phase-2-agent-report.md",
            },
        )

        index_path = self.orchestrate / "change-capability-anchors/obligation-atom-index.json"
        write_json(index_path, {
            "trace-schema": GLOBAL_ATOM_INDEX_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "artifact-path": "openspec/orchestrate/change-capability-anchors/obligation-atom-index.md",
            "global-atoms": [
                {"global-atom-id": "GA-0001", "evidence-ref": self._evidence_ref("SA-0001")},
                {"global-atom-id": "GA-0002", "evidence-ref": self._evidence_ref("SA-0002")},
            ],
        })
        coverage_path = self.orchestrate / "phase-works/phase-3/coverage-review.json"
        write_json(coverage_path, {
            "trace-schema": PHASE3_COVERAGE_REVIEW_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "artifact-path": "openspec/orchestrate/phase-works/phase-3/coverage-review.md",
            "documents": [{
                "source-document": "docs/source.md",
                "source-sha256": source_sha,
                "line-count": 10,
                "phase-2-atom-path": "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json",
                "phase-2-atom-sha256": sha256_file(atom_path),
                "covered-ranges": [{"start": 1, "end": 4}],
                "candidate-uncovered-ranges": [{"start": 5, "end": 10}],
            }],
            "gap-atoms": [],
            "remainder-dispositions": [{
                "disposition-id": "RD-0001",
                "source-document": "docs/source.md",
                "line-ranges": [{"start": 5, "end": 10}],
                "classification": "safe-non-obligation",
                "linked-gap-atom-ids": [],
                "reason": "该范围仅为背景说明，不包含生产义务。",
            }],
            "recheck-sources": [],
            "summary": {
                "source-documents": 1,
                "phase-2-atoms": 2,
                "gap-atoms": 0,
                "global-atoms": 2,
                "candidate-uncovered-ranges": 1,
                "remainder-dispositions": {
                    "blocked": 0,
                    "missing-obligation": 0,
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
            "global-atom-index-sha256": sha256_file(index_path),
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

        window_path = self.orchestrate / "phase-works/phase-4/source-window-dossiers/source-window-index.json"
        windows = []
        for pos, (ga_id, start, end) in enumerate((("GA-0001", 1, 2), ("GA-0002", 3, 4)), start=1):
            text = "same requirement\nsame outcome"
            windows.append({
                "window-id": f"SW-{pos:03d}",
                "input-unit": "change-a",
                "unit-type": "input-change",
                "source-document": "docs/source.md",
                "line-ranges": [{"start": start, "end": end}],
                "context-line-ranges": [],
                "linked-global-atom-ids": [ga_id],
                "dossier-path": "openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-change/change-a.md",
                "source-sha256": source_sha,
                "window-text-sha256": sha256_text(text),
            })
        write_json(window_path, {
            "trace-schema": SOURCE_WINDOW_INDEX_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "grounded",
            "windows": windows,
            "semantic-profiles": [],
            "grounding-issues": [],
        })
        write_json(self.orchestrate / "trace/phase-4.trace.json", {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-4"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "grounded",
            "source-window-index-path": "openspec/orchestrate/phase-works/phase-4/source-window-dossiers/source-window-index.json",
        })

        mapping_path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        mapping_rows = [
            self._mapping_row("GA-0001", "SA-0001", 1, 2),
            self._mapping_row("GA-0002", "SA-0002", 3, 4),
        ]
        write_json(mapping_path, {
            "trace-schema": ATOM_PLAN_MAPPING_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "artifact-path": "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.md",
            "rows": mapping_rows,
        })
        packet_path = self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/change-a.md",
            self._packet_text([(row["global-atom-id"], row["evidence-ref"]) for row in mapping_rows]),
        )
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/capability-anchors/cap-a.md",
            "# cap-a\n\n| Global Atom ID | Relation |\n| --- | --- |\n| GA-0001 | direct |\n| GA-0002 | direct |\n",
        )
        packet_index_path = self.orchestrate / "phase-works/phase-5/final-packet-index.json"
        write_json(packet_index_path, {
            "trace-schema": FINAL_PACKET_INDEX_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "packets": [{
                "change": "change-a",
                "change-kind": "business",
                "packet-path": "openspec/orchestrate/change-capability-anchors/change-a/change-a.md",
                "packet-digest": sha256_file(packet_path),
                "direct-atom-ids": ["GA-0001", "GA-0002"],
                "owner-scoped-non-direct-atom-ids": [],
                "capability-view-paths": ["openspec/orchestrate/change-capability-anchors/change-a/capability-anchors/cap-a.md"],
            }],
        })
        baseline_path = self.orchestrate / "phase-works/phase-5/capability-baseline-reconciliation.json"
        write_json(baseline_path, {
            "trace-schema": CAPABILITY_BASELINE_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "repository-specs-root": "openspec/specs",
            "capabilities": [{
                "capability": "cap-a",
                "baseline-status": "absent",
                "spec-path": "openspec/specs/cap-a/spec.md",
                "spec-sha256": None,
                "baseline-evidence": "已只读检查精确 spec 路径，当前不存在。",
                "first-planned-advancement": "change-a",
                "required-first-relation": "new",
                "later-relation-rule": "modified",
            }],
        })
        write_json(self.orchestrate / "trace/phase-5.trace.json", {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "adjusted",
            "atom-plan-mapping-path": "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json",
            "final-packet-index-path": "openspec/orchestrate/phase-works/phase-5/final-packet-index.json",
            "capability-baseline-reconciliation-path": "openspec/orchestrate/phase-works/phase-5/capability-baseline-reconciliation.json",
            "capability-baseline-reconciliation-sha256": sha256_file(baseline_path),
            "complexity-summaries": [],
            "capability-progression-summaries": [],
            "validator-gate-outcomes": [],
            "reviewer-gate-outcomes": [],
        })
        render_orchestrate(self.orchestrate, "all-supported", write=True)
        self._write_manifest()

    def _write_manifest(self) -> None:
        specs = [
            ("trace/phase-1.trace.json", PHASE_TRACE_SCHEMAS["phase-1"], "phase-1"),
            ("trace/phase-2.trace.json", PHASE_TRACE_SCHEMAS["phase-2"], "phase-2"),
            ("phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json", SOURCE_ATOMS_SCHEMA, "phase-2"),
            ("change-capability-anchors/obligation-atom-index.json", GLOBAL_ATOM_INDEX_SCHEMA, "phase-3"),
            ("phase-works/phase-3/coverage-review.json", PHASE3_COVERAGE_REVIEW_SCHEMA, "phase-3"),
            ("trace/phase-3.trace.json", PHASE_TRACE_SCHEMAS["phase-3"], "phase-3"),
            ("phase-works/phase-4/source-window-dossiers/source-window-index.json", SOURCE_WINDOW_INDEX_SCHEMA, "phase-4"),
            ("trace/phase-4.trace.json", PHASE_TRACE_SCHEMAS["phase-4"], "phase-4"),
            ("phase-works/phase-5/atom-plan-mapping.json", ATOM_PLAN_MAPPING_SCHEMA, "phase-5"),
            ("phase-works/phase-5/capability-baseline-reconciliation.json", CAPABILITY_BASELINE_SCHEMA, "phase-5"),
            ("phase-works/phase-5/final-packet-index.json", FINAL_PACKET_INDEX_SCHEMA, "phase-5"),
            ("trace/phase-5.trace.json", PHASE_TRACE_SCHEMAS["phase-5"], "phase-5"),
        ]
        artifacts = []
        for relative, schema, phase in specs:
            path = self.orchestrate / relative
            if path.exists():
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
            trace = self._read_json(f"openspec/orchestrate/trace/{phase}.trace.json")
            statuses[phase] = trace.get("status") or trace.get("decision")
        write_json(self.orchestrate / "trace/manifest.json", {
            "trace-schema": MANIFEST_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "orchestrate-dir": "openspec/orchestrate",
            "phase-statuses": statuses,
            "artifacts": artifacts,
        })

    def _sync_phase2_phase3(self) -> None:
        atom_path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        phase2 = self._read_json("openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json")
        trace2 = self._read_json("openspec/orchestrate/trace/phase-2.trace.json")
        trace2["sources"][0]["atom-json-sha256"] = sha256_file(atom_path)
        trace2["sources"][0]["atom-count"] = len(phase2["source-atoms"])
        write_json(self.orchestrate / "trace/phase-2.trace.json", trace2)
        coverage_path = self.orchestrate / "phase-works/phase-3/coverage-review.json"
        index_path = self.orchestrate / "change-capability-anchors/obligation-atom-index.json"
        trace3 = self._read_json("openspec/orchestrate/trace/phase-3.trace.json")
        trace3["decision"] = self._read_json("openspec/orchestrate/phase-works/phase-3/coverage-review.json")["decision"]
        trace3["global-atom-index-sha256"] = sha256_file(index_path)
        trace3["coverage-review-sha256"] = sha256_file(coverage_path)
        write_json(self.orchestrate / "trace/phase-3.trace.json", trace3)
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        render_orchestrate(self.orchestrate, "phase3-global-index", write=True)
        render_orchestrate(self.orchestrate, "phase3-coverage-review", write=True)
        self._write_manifest()

    def _result(self, phase: str = "all", complete: bool = False) -> dict:
        return validate(self.orchestrate, self.root, phase, complete)

    def _assert_rule(self, result: dict, rule: str) -> None:
        self.assertIn(rule, [issue["rule_id"] for issue in result["issues"]], result)

    def test_valid_all_phase_fixture(self) -> None:
        result = self._result("all", complete=True)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["warning-count"], 0, result)

    def test_semantically_identical_phase2_atoms_keep_independent_ga(self) -> None:
        phase2 = self._read_json("openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json")
        self.assertEqual(phase2["source-atoms"][0]["source-fact"], phase2["source-atoms"][1]["source-fact"])
        index = self._read_json("openspec/orchestrate/change-capability-anchors/obligation-atom-index.json")
        self.assertEqual(len(index["global-atoms"]), 2)
        self.assertNotEqual(index["global-atoms"][0]["evidence-ref"], index["global-atoms"][1]["evidence-ref"])
        result = self._result("phase-3")
        self.assertTrue(result["ok"], result)
        self.assertFalse(any("duplicate" in issue["rule_id"] for issue in result["issues"]))

    def test_phase3_never_copies_phase2_source_fact(self) -> None:
        phase2_fact = "same requirement\nsame outcome"
        for relative in (
            "openspec/orchestrate/change-capability-anchors/obligation-atom-index.json",
            "openspec/orchestrate/change-capability-anchors/obligation-atom-index.md",
            "openspec/orchestrate/phase-works/phase-3/coverage-review.json",
            "openspec/orchestrate/phase-works/phase-3/coverage-review.md",
            "openspec/orchestrate/trace/phase-3.trace.json",
        ):
            self.assertNotIn(phase2_fact, (self.root / relative).read_text(encoding="utf-8"))

    def test_global_index_rejects_extraction_field_copy(self) -> None:
        relative = "openspec/orchestrate/change-capability-anchors/obligation-atom-index.json"
        data = self._read_json(relative)
        data["global-atoms"][0]["source-fact"] = "same requirement\nsame outcome"
        self._write_data(relative, data)
        render_orchestrate(self.orchestrate, "phase3-global-index", write=True)
        self._write_manifest()
        result = self._result("phase-3")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase3-global-atom-fields")

    def test_technical_duplicate_ga_id_is_rejected(self) -> None:
        relative = "openspec/orchestrate/change-capability-anchors/obligation-atom-index.json"
        data = self._read_json(relative)
        data["global-atoms"][1]["global-atom-id"] = "GA-0001"
        self._write_data(relative, data)
        render_orchestrate(self.orchestrate, "phase3-global-index", write=True)
        self._sync_phase2_phase3()
        result = self._result("phase-3")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase3-ga-duplicate")

    def test_uncovered_obligation_creates_gap_atom_and_ga(self) -> None:
        coverage_rel = "openspec/orchestrate/phase-works/phase-3/coverage-review.json"
        coverage = self._read_json(coverage_rel)
        coverage["gap-atoms"] = [{
            "gap-atom-id": "P3-GAP-0001",
            "source-document": "docs/source.md",
            "line-ranges": [{"start": 5, "end": 5}],
            "source-fact": "background 5",
            "atom-type": "behavior",
            "normativity": "must",
            "review-judgment": "该行实际包含遗漏的生产义务。",
        }]
        coverage["remainder-dispositions"] = [
            {
                "disposition-id": "RD-0001",
                "source-document": "docs/source.md",
                "line-ranges": [{"start": 5, "end": 5}],
                "classification": "missing-obligation",
                "linked-gap-atom-ids": ["P3-GAP-0001"],
                "reason": "已补提取遗漏义务。",
            },
            {
                "disposition-id": "RD-0002",
                "source-document": "docs/source.md",
                "line-ranges": [{"start": 6, "end": 10}],
                "classification": "safe-non-obligation",
                "linked-gap-atom-ids": [],
                "reason": "其余范围仅为背景。",
            },
        ]
        coverage["summary"]["gap-atoms"] = 1
        coverage["summary"]["global-atoms"] = 3
        coverage["summary"]["remainder-dispositions"]["missing-obligation"] = 1
        coverage["summary"]["remainder-dispositions"]["safe-non-obligation"] = 1
        self._write_data(coverage_rel, coverage)
        index_rel = "openspec/orchestrate/change-capability-anchors/obligation-atom-index.json"
        index = self._read_json(index_rel)
        index["global-atoms"].append({
            "global-atom-id": "GA-0003",
            "evidence-ref": {"kind": "phase-3-gap-atom", "gap-atom-id": "P3-GAP-0001"},
        })
        self._write_data(index_rel, index)
        self._sync_phase2_phase3()
        result = self._result("phase-3")
        self.assertTrue(result["ok"], result)
        resolved = load_global_atoms_json(self.orchestrate / "change-capability-anchors/obligation-atom-index.json")
        self.assertEqual(resolved["GA-0003"].source_fact, "background 5")
        self.assertEqual(resolved["GA-0003"].evidence_ref["kind"], "phase-3-gap-atom")

    def test_broad_atom_requires_targeted_extraction_recheck(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-3/coverage-review.json"
        coverage = self._read_json(relative)
        coverage["recheck-sources"] = [{
            "source-document": "docs/source.md",
            "source-atom-ids": ["SA-0001"],
            "line-ranges": [{"start": 1, "end": 2}],
            "reason": "该 Phase 2 atom压缩了多个 obligation，需要 targeted重新提取。",
        }]
        coverage["decision"] = "needs-extraction-recheck"
        self._write_data(relative, coverage)
        self._sync_phase2_phase3()
        result = self._result("phase-3")
        self.assertTrue(result["ok"], result)
        self.assertEqual(self._read_json(relative)["decision"], "needs-extraction-recheck")
        complete_result = self._result("all", complete=True)
        self.assertFalse(complete_result["ok"])
        self._assert_rule(complete_result, "manifest-complete-phase-status")

    def test_blocked_decision_requires_blocked_disposition(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-3/coverage-review.json"
        coverage = self._read_json(relative)
        coverage["decision"] = "blocked"
        self._write_data(relative, coverage)
        self._sync_phase2_phase3()
        result = self._result("phase-3")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase3-decision-consistency")

    def test_blocked_decision_with_positive_evidence_is_structurally_valid(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-3/coverage-review.json"
        coverage = self._read_json(relative)
        coverage["decision"] = "blocked"
        coverage["remainder-dispositions"][0]["classification"] = "blocked"
        coverage["remainder-dispositions"][0]["reason"] = "该范围缺少作出安全判断所需的用户决定。"
        coverage["summary"]["remainder-dispositions"]["blocked"] = 1
        coverage["summary"]["remainder-dispositions"]["safe-non-obligation"] = 0
        self._write_data(relative, coverage)
        self._sync_phase2_phase3()
        result = self._result("phase-3")
        self.assertTrue(result["ok"], result)

    def test_complete_requires_phase3_reviewer_loop_passed(self) -> None:
        relative = "openspec/orchestrate/trace/phase-3.trace.json"
        trace = self._read_json(relative)
        trace["reviewer-loop"]["status"] = "pending"
        trace["reviewer-loop"]["reviewer-id"] = ""
        trace["reviewer-loop"]["validator-status"] = "pending"
        self._write_data(relative, trace)
        self._write_manifest()
        result = self._result("all", complete=True)
        self.assertFalse(result["ok"])
        self._assert_rule(result, "manifest-complete-phase3-reviewer")

    def test_phase3_reviewer_must_be_independent_from_writer(self) -> None:
        relative = "openspec/orchestrate/trace/phase-3.trace.json"
        trace = self._read_json(relative)
        trace["reviewer-loop"]["reviewer-id"] = trace["reviewer-loop"]["writer-id"]
        self._write_data(relative, trace)
        self._write_manifest()
        result = self._result("all", complete=True)
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase3-reviewer-loop-independence")

    def test_phase3_trace_cannot_copy_phase2_source_fact(self) -> None:
        relative = "openspec/orchestrate/trace/phase-3.trace.json"
        trace = self._read_json(relative)
        trace["reviewer-loop"]["findings"] = ["same requirement\nsame outcome"]
        self._write_data(relative, trace)
        self._write_manifest()
        result = self._result("phase-3")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase3-phase2-source-fact-copy")

    def test_legacy_phase3_artifact_is_rejected(self) -> None:
        self._write("openspec/orchestrate/phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json", "{}\n")
        result = self._result("phase-3")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase3-legacy-artifact")

    def test_phase4_requires_every_ga_grounded(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-4/source-window-dossiers/source-window-index.json"
        data = self._read_json(relative)
        data["windows"] = data["windows"][:1]
        self._write_data(relative, data)
        self._write_manifest()
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-ga-grounding-coverage")

    def test_phase4_only_reuses_window_for_identical_evidence_range(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-4/source-window-dossiers/source-window-index.json"
        data = self._read_json(relative)
        shared = data["windows"][0]
        shared["line-ranges"] = [{"start": 1, "end": 4}]
        shared["linked-global-atom-ids"] = ["GA-0001", "GA-0002"]
        data["windows"] = [shared]
        self._write_data(relative, data)
        self._write_manifest()
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-window-reuse-nonidentical")

    def test_phase4_recomputes_window_text_digest(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-4/source-window-dossiers/source-window-index.json"
        data = self._read_json(relative)
        data["windows"][0]["window-text-sha256"] = "0" * 64
        self._write_data(relative, data)
        self._write_manifest()
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-window-text-sha")

    def test_phase4_rejects_semantic_dedup_metadata(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-4/source-window-dossiers/source-window-index.json"
        data = self._read_json(relative)
        data["windows"][0]["duplicate-status"] = "canonical"
        self._write_data(relative, data)
        self._write_manifest()
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-semantic-dedup-field")

    def test_two_ga_may_have_identical_phase5_mapping(self) -> None:
        rows = self._read_json("openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json")["rows"]
        final_fields = (
            "final-owner-type", "final-owner-change", "final-capability-impact",
            "final-target-capability", "related-capabilities", "final-artifact-projection",
            "final-relation", "plan-decision", "reason",
        )
        self.assertTrue(all(rows[0][field] == rows[1][field] for field in final_fields))
        result = self._result("phase-5")
        self.assertTrue(result["ok"], result)

    def test_phase5_mapping_rejects_phase3_planning_fields(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json"
        data = self._read_json(relative)
        data["rows"][0]["phase-3-owner-status"] = "change-a / direct"
        self._write_data(relative, data)
        render_orchestrate(self.orchestrate, "phase5-atom-plan-mapping", write=True)
        self._write_manifest()
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-mapping-fields")

    def test_final_packet_keeps_each_evidence_reference(self) -> None:
        packet = (self.orchestrate / "change-capability-anchors/change-a/change-a.md").read_text(encoding="utf-8")
        for atom_id in ("SA-0001", "SA-0002"):
            self.assertIn(json.dumps(self._evidence_ref(atom_id), ensure_ascii=False, sort_keys=True), packet)
        self.assertIn("未做语义去重", packet)
        self.assertIn("多对一", packet)

    def test_packet_missing_dedup_handoff_is_rejected(self) -> None:
        path = self.orchestrate / "change-capability-anchors/change-a/change-a.md"
        path.write_text(path.read_text(encoding="utf-8").replace("未做语义去重", "完整"), encoding="utf-8")
        index_rel = "openspec/orchestrate/phase-works/phase-5/final-packet-index.json"
        index = self._read_json(index_rel)
        index["packets"][0]["packet-digest"] = sha256_file(path)
        self._write_data(index_rel, index)
        self._write_manifest()
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-packet-dedup-handoff")

    def test_renderer_contract_and_drift(self) -> None:
        self.assertEqual(RENDER_CONTRACT_VERSION, "source-aligned-render-v5")
        path = self.orchestrate / "phase-works/phase-3/coverage-review.md"
        path.write_text(path.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
        result = self._result("phase-3")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "rendered-markdown-drift")

    def test_phase5_helper_resolves_v3_evidence(self) -> None:
        atoms = load_global_atoms_json(self.orchestrate / "change-capability-anchors/obligation-atom-index.json")
        mapping = load_mapping(self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json")
        self.assertEqual(atoms["GA-0001"].source_fact, atoms["GA-0002"].source_fact)
        self.assertEqual(mapping["GA-0001"].final_change, mapping["GA-0002"].final_change)

    def test_phase3_mechanical_helper_has_no_planning_or_overlap_output(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "phase3_line_range_audit.py"),
                "--orchestrate-dir",
                str(self.orchestrate),
                "--workspace-root",
                str(self.root),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(completed.stdout)
        document = data["documents"]["docs/source.md"]
        self.assertEqual(document["merged_covered_ranges"], [[1, 4]])
        self.assertEqual(document["candidate_uncovered_ranges"], [[5, 10]])
        self.assertNotIn("overlap_groups", document)
        serialized = json.dumps(data, ensure_ascii=False)
        self.assertNotIn("candidate_owner_change", serialized)
        self.assertNotIn("source_fact", serialized)

    def test_phase5_helper_end_to_end_output_validates(self) -> None:
        config_path = self.orchestrate / "phase-works/phase-5/phase5-refit.config.json"
        write_json(config_path, {
            "status": "adjusted",
            "source_documents_read": "Phase 3 coverage review 已验证来源。",
            "assumptions_and_conflicts": "未新增、合并或删除 evidence occurrence。",
            "changes": [{
                "slug": "change-a",
                "title": "change-a",
                "intent": "让用户获得可验证结果。",
                "outcome": "交付可观察且可验证的行为。",
                "kind": "business",
            }],
            "capabilities": [{
                "slug": "cap-a",
                "boundary": "稳定的结果行为边界。",
                "purpose": "规定可验证结果。",
                "owns": "拥有结果行为。",
                "excludes": "不拥有实现细节。",
                "baseline_status": "absent",
                "baseline_evidence": "已只读检查精确 spec 路径，当前不存在。",
            }],
            "decisions": [],
            "source_window_refit_trace": [],
            "split_analyses": [],
            "adjustments": [],
            "complexity_decisions": [],
        })
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "phase5_plan_refit.py"),
                "--orchestrate-dir",
                str(self.orchestrate),
                "--config",
                str(config_path),
                "--write",
                "--validate-rendered",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self._write_manifest()
        result = self._result("all", complete=True)
        self.assertTrue(result["ok"], result)

    def test_evidence_volume_never_changes_budget_status(self) -> None:
        self.assertEqual(budget_status([]), "semantic-boundary-reviewed")
        self.assertEqual(budget_status([object()] * 500), "semantic-boundary-reviewed")

    def test_adding_duplicate_occurrence_only_increases_trace_rows(self) -> None:
        plan_before = (self.orchestrate / "change-plan.md").read_text(encoding="utf-8")
        human_before = (self.orchestrate / "phase-works/phase-5/change-capability-human-plan.md").read_text(encoding="utf-8")
        source_path = self.root / "docs/source.md"
        source_lines = source_path.read_text(encoding="utf-8").splitlines()
        source_lines[4:6] = ["same requirement", "same outcome"]
        source_path.write_text("\n".join(source_lines) + "\n", encoding="utf-8")
        source_sha = sha256_file(source_path)
        phase1_trace_rel = "openspec/orchestrate/trace/phase-1.trace.json"
        phase1_trace = self._read_json(phase1_trace_rel)
        phase1_trace["source-documents"][0]["source-sha256"] = source_sha
        self._write_data(phase1_trace_rel, phase1_trace)
        atom_rel = "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        phase2 = self._read_json(atom_rel)
        phase2["source-sha256"] = source_sha
        phase2["source-atoms"].append(self._source_atom("SA-0003", 5, 6))
        self._write_data(atom_rel, phase2)
        coverage_rel = "openspec/orchestrate/phase-works/phase-3/coverage-review.json"
        coverage = self._read_json(coverage_rel)
        coverage["documents"][0]["source-sha256"] = source_sha
        atom_path = self.root / atom_rel
        coverage["documents"][0]["phase-2-atom-sha256"] = sha256_file(atom_path)
        coverage["documents"][0]["covered-ranges"] = [{"start": 1, "end": 6}]
        coverage["documents"][0]["candidate-uncovered-ranges"] = [{"start": 7, "end": 10}]
        coverage["remainder-dispositions"][0]["line-ranges"] = [{"start": 7, "end": 10}]
        coverage["summary"]["phase-2-atoms"] = 3
        coverage["summary"]["global-atoms"] = 3
        self._write_data(coverage_rel, coverage)
        index_rel = "openspec/orchestrate/change-capability-anchors/obligation-atom-index.json"
        index = self._read_json(index_rel)
        index["global-atoms"].append({"global-atom-id": "GA-0003", "evidence-ref": self._evidence_ref("SA-0003")})
        self._write_data(index_rel, index)
        self._sync_phase2_phase3()

        window_rel = "openspec/orchestrate/phase-works/phase-4/source-window-dossiers/source-window-index.json"
        window = self._read_json(window_rel)
        for row in window["windows"]:
            row["source-sha256"] = source_sha
        window["windows"].append({
            "window-id": "SW-003",
            "input-unit": "change-a",
            "unit-type": "input-change",
            "source-document": "docs/source.md",
            "line-ranges": [{"start": 5, "end": 6}],
            "context-line-ranges": [],
            "linked-global-atom-ids": ["GA-0003"],
            "dossier-path": "openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-change/change-a.md",
            "source-sha256": source_sha,
            "window-text-sha256": sha256_text("same requirement\nsame outcome"),
        })
        self._write_data(window_rel, window)
        mapping_rel = "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json"
        mapping = self._read_json(mapping_rel)
        mapping["rows"].append(self._mapping_row("GA-0003", "SA-0003", 5, 6))
        self._write_data(mapping_rel, mapping)
        render_orchestrate(self.orchestrate, "phase5-atom-plan-mapping", write=True)
        packet_path = self.orchestrate / "change-capability-anchors/change-a/change-a.md"
        packet_path.write_text(
            self._packet_text([(row["global-atom-id"], row["evidence-ref"]) for row in mapping["rows"]]),
            encoding="utf-8",
        )
        cap_path = self.orchestrate / "change-capability-anchors/change-a/capability-anchors/cap-a.md"
        cap_path.write_text(cap_path.read_text(encoding="utf-8") + "| GA-0003 | direct |\n", encoding="utf-8")
        packet_index_rel = "openspec/orchestrate/phase-works/phase-5/final-packet-index.json"
        packet_index = self._read_json(packet_index_rel)
        packet_index["packets"][0]["packet-digest"] = sha256_file(packet_path)
        packet_index["packets"][0]["direct-atom-ids"].append("GA-0003")
        self._write_data(packet_index_rel, packet_index)
        self._write_manifest()

        result = self._result("all", complete=True)
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(index["global-atoms"]), 3)
        self.assertEqual(len(mapping["rows"]), 3)
        self.assertEqual((self.orchestrate / "change-plan.md").read_text(encoding="utf-8"), plan_before)
        self.assertEqual((self.orchestrate / "phase-works/phase-5/change-capability-human-plan.md").read_text(encoding="utf-8"), human_before)


if __name__ == "__main__":
    unittest.main()
