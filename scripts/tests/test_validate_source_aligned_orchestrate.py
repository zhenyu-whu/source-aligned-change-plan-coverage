#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import copy
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from phase5_plan_refit import (  # noqa: E402
    CAPABILITY_INITIAL_GATE_NAMES,
    CHANGE_INITIAL_GATE_NAMES,
    Evidence,
    Mapping,
    derive_advancement,
    parse_final_plan,
    validate_framework_refit,
    validate_mapping,
    write_outputs,
)
from render_source_aligned_orchestrate import (  # noqa: E402
    RENDER_CONTRACT_VERSION,
    render_coverage_review,
    render_evidence_collections,
    render_orchestrate,
)
from source_aligned_trace_lib import (  # noqa: E402
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_BASELINE_SCHEMA,
    EVIDENCE_COLLECTION_INDEX_SCHEMA,
    FINAL_PACKET_INDEX_SCHEMA,
    FRAMEWORK_REFIT_TRACE_SCHEMA,
    GLOBAL_ATOM_INDEX_SCHEMA,
    MANIFEST_SCHEMA,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    canonical_json_sha256,
    evidence_authority_sha256,
    repo_relative_path,
    sha256_file,
    write_json,
)
from validate_source_aligned_orchestrate import (  # noqa: E402
    validate,
)


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
    def _capability_gate_results(*, failed: str | None = None) -> list[dict]:
        return [
            {
                "gate": gate,
                "result": "failed" if gate == failed else "passed",
                "note": f"初始Capability的{gate}检查{'未通过' if gate == failed else '通过'}。",
            }
            for gate in CAPABILITY_INITIAL_GATE_NAMES
        ]

    @staticmethod
    def _change_gate_results(*, failed: str | None = None) -> list[dict]:
        return [
            {
                "gate": gate,
                "result": "failed" if gate == failed else "passed",
                "note": f"初始Change的{gate}检查{'未通过' if gate == failed else '通过'}。",
            }
            for gate in CHANGE_INITIAL_GATE_NAMES
        ]

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

    def _refit_trace(self) -> dict:
        initial_plan = self.orchestrate / "phase-works/phase-1/initial-change-plan.md"
        gap_refs = {
            "GA-0002": self._ref("SA-0002"),
            "GA-0003": self._ref("SA-0003"),
            "GA-0004": self._ref("SA-0004"),
            "GA-0005": {"kind": "phase-3-gap-atom", "gap-atom-id": "P3-GAP-0001"},
        }
        return {
            "trace-schema": FRAMEWORK_REFIT_TRACE_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "accepted",
            "initial-plan-ref": {
                "artifact-path": "openspec/orchestrate/phase-works/phase-1/initial-change-plan.md",
                "sha256": sha256_file(initial_plan),
            },
            "capability-reviews": [{
                "input-capability": "cap-a",
                "evidence-collection-path": "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/by-input-capability/cap-a.md",
                "decision": "keep",
                "final-capabilities": ["cap-a"],
                "initial-gate-results": self._capability_gate_results(),
                "supporting-global-atom-ids": [],
                "reason": "原文集合支持稳定行为边界。",
            }],
            "change-reviews": [{
                "input-change": "change-a",
                "evidence-collection-path": "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/by-input-change/change-a.md",
                "decision": "keep",
                "final-changes": ["change-a"],
                "initial-gate-results": self._change_gate_results(),
                "supporting-global-atom-ids": [],
                "reason": "原文集合支持单一可验收结果。",
            }],
            "unassigned-and-gap-reviews": [
                {
                    "global-atom-id": ga,
                    "evidence-ref": ref,
                    "framework-impact": "none",
                    "reason": "归入同一结果范围且不推进Capability。",
                }
                for ga, ref in gap_refs.items()
            ],
            "final-framework": {
                "change-order": ["change-a"],
                "capabilities": ["cap-a"],
                "overlay": [{"change": "change-a", "capability": "cap-a", "capability-impact": "new"}],
            },
            "issues": [],
            "language-self-check": "判断与理由已使用简体中文。",
        }

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
            "review-gate": {
                "status": "passed",
                "writer-id": "phase-1-writer",
                "reviews": [{
                    "round": 1,
                    "reviewer-id": "phase-1-reviewer-1",
                    "validator-status": "passed",
                    "plan-sha256": sha256_file(plan_path),
                    "finding-fingerprints": [],
                }],
                "repairs": [],
            },
        })

        atom_root = self.orchestrate / "phase-works/phase-2/source-obligation-atoms"
        self._write(
            "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/work-queue.md",
            "| Batch | Source Documents | Canonical Owner |\n| --- | --- | --- |\n| B1 | docs/source.md | owner-a |\n",
        )
        self._write("openspec/orchestrate/phase-works/phase-2/phase-2-agent-report.md", "Phase 2通过。\n")
        atom_path = atom_root / "docs--source.atoms.json"
        atoms = [
            self._atom("SA-0001", 1, 3, "same | requirement\n```embedded```\nsame outcome", "direct-candidate", "spec-requirement", "change-a", "cap-a"),
            self._atom("SA-0002", 4, 4, "unassigned fact", "unassigned", "spec-guard", "unassigned", "unresolved"),
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
            "mapping-ambiguities": [],
            "summary": {
                "source-documents": 1,
                "phase-2-atoms": 4,
                "gap-atoms": 1,
                "global-atoms": 5,
                "mapping-ambiguities": 0,
                "candidate-uncovered-ranges": 1,
                "remainder-dispositions": {
                    "blocked": 0,
                    "missing-obligation": 1,
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
            "review-gate": {
                "status": "passed",
                "phase-2-canonical-owner-ids": ["owner-a"],
                "phase-2-aggregate-writer-id": "phase-2-aggregate-writer",
                "phase-3-writer-id": "phase-3-writer",
                "reviews": [{
                    "round": 1,
                    "stage": "phase-3-closure",
                    "reviewer-id": "phase-3-reviewer-1",
                    "phase-2-validator-status": "passed",
                    "phase-3-validator-status": "passed",
                    "evidence-authority-sha256": evidence_authority_sha256(
                        self.orchestrate, self.root
                    ),
                    "finding-fingerprints": [],
                }],
                "repairs": [],
            },
            "issues": [],
        })
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        render_orchestrate(self.orchestrate, "phase2-index", write=True)
        render_orchestrate(self.orchestrate, "phase3-global-index", write=True)
        render_orchestrate(self.orchestrate, "phase3-coverage-review", write=True)

        collection_path = self.orchestrate / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        render_orchestrate(self.orchestrate, "phase4-evidence-collections", write=True)
        self._write("openspec/orchestrate/phase-works/phase-4/phase-4-agent-report.md", "Phase 4 Status: assembled\n")
        write_json(self.orchestrate / "trace/phase-4.trace.json", {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-4"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "assembled",
            "assembled": {
                "evidence-collection-index-path": "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/evidence-collection-index.json",
                "evidence-collection-index-sha256": sha256_file(collection_path),
                "renderer-result-summary": {
                    "render-contract-version": RENDER_CONTRACT_VERSION,
                    "rendered-files": 4,
                    "global-atoms": 5,
                },
            },
        })

        self._write("openspec/orchestrate/phase-works/phase-5/change-plan.md", self._final_plan())
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
        write_json(self.orchestrate / "phase-works/phase-5/framework-refit-trace.json", self._refit_trace())
        write_outputs(self.orchestrate)
        self._write_manifest()

    def _write_manifest(self) -> None:
        specs = [
            ("trace/phase-1.trace.json", PHASE_TRACE_SCHEMAS["phase-1"], "phase-1", "control", "phase-trace"),
            ("trace/phase-2.trace.json", PHASE_TRACE_SCHEMAS["phase-2"], "phase-2", "control", "phase-trace"),
            ("phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json", SOURCE_ATOMS_SCHEMA, "phase-2", "semantic", "source-atoms"),
            ("change-capability-anchors/obligation-atom-index.json", GLOBAL_ATOM_INDEX_SCHEMA, "phase-3", "semantic", "global-atom-index"),
            ("phase-works/phase-3/coverage-review.json", PHASE3_COVERAGE_REVIEW_SCHEMA, "phase-3", "semantic", "coverage-review"),
            ("trace/phase-3.trace.json", PHASE_TRACE_SCHEMAS["phase-3"], "phase-3", "control", "phase-trace"),
            ("phase-works/phase-4/source-evidence-collections/evidence-collection-index.json", EVIDENCE_COLLECTION_INDEX_SCHEMA, "phase-4", "derived", "evidence-collection-index"),
            ("trace/phase-4.trace.json", PHASE_TRACE_SCHEMAS["phase-4"], "phase-4", "control", "phase-trace"),
            ("phase-works/phase-5/framework-refit-trace.json", FRAMEWORK_REFIT_TRACE_SCHEMA, "phase-5", "semantic", "framework-refit-trace"),
            ("phase-works/phase-5/atom-plan-mapping.json", ATOM_PLAN_MAPPING_SCHEMA, "phase-5", "semantic", "atom-plan-mapping"),
            ("phase-works/phase-5/capability-baseline-reconciliation.json", CAPABILITY_BASELINE_SCHEMA, "phase-5", "derived", "capability-baseline"),
            ("phase-works/phase-5/final-packet-index.json", FINAL_PACKET_INDEX_SCHEMA, "phase-5", "derived", "final-packet-index"),
            ("trace/phase-5.trace.json", PHASE_TRACE_SCHEMAS["phase-5"], "phase-5", "control", "phase-trace"),
        ]
        artifacts = []
        for relative, schema, phase, authority, role in specs:
            path = self.orchestrate / relative
            if not path.exists():
                continue
            artifacts.append({
                "json-path": f"openspec/orchestrate/{relative}",
                "trace-schema": schema,
                "sha256": sha256_file(path),
                "phase": phase,
                "role": role,
                "authority": authority,
            })
        statuses = {}
        for phase in ("phase-1", "phase-2", "phase-3", "phase-4", "phase-5"):
            trace = self._data(f"openspec/orchestrate/trace/{phase}.trace.json")
            statuses[phase] = trace.get("status") or trace.get("decision")
        write_json(self.orchestrate / "trace/manifest.json", {
            "trace-schema": MANIFEST_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "authority": "control",
            "orchestrate-dir": "openspec/orchestrate",
            "phase-statuses": statuses,
            "artifacts": artifacts,
        })

    def _result(
        self,
        phase: str = "all",
        complete: bool = False,
        preflight: bool = False,
    ) -> dict:
        return validate(self.orchestrate, self.root, phase, complete, preflight)

    def _refresh_phase3_authority(self) -> None:
        relative = "openspec/orchestrate/trace/phase-3.trace.json"
        trace = self._data(relative)
        trace["global-atom-index-sha256"] = sha256_file(
            self.orchestrate / "change-capability-anchors/obligation-atom-index.json"
        )
        trace["coverage-review-sha256"] = sha256_file(
            self.orchestrate / "phase-works/phase-3/coverage-review.json"
        )
        if trace.get("review-gate", {}).get("reviews"):
            trace["review-gate"]["reviews"][-1][
                "evidence-authority-sha256"
            ] = evidence_authority_sha256(self.orchestrate, self.root)
        self._write_data(relative, trace)
        self._write_manifest()

    def _assert_rule(self, result: dict, rule: str) -> None:
        self.assertIn(rule, [issue["rule_id"] for issue in result["issues"]], result)

    def _set_phase1_review_gate(self, gate: dict, *, status: str) -> None:
        relative = "openspec/orchestrate/trace/phase-1.trace.json"
        trace = self._data(relative)
        trace["status"] = status
        trace["review-gate"] = gate
        self._write_data(relative, trace)
        self._write_manifest()

    def _three_round_phase1_gate(self) -> dict:
        current = sha256_file(self.orchestrate / "phase-works/phase-1/initial-change-plan.md")
        finding_1 = canonical_json_sha256({"finding": "first"})
        finding_2 = canonical_json_sha256({"finding": "second"})
        plan_1 = canonical_json_sha256({"plan": 1})
        plan_2 = canonical_json_sha256({"plan": 2})
        return {
            "status": "passed",
            "writer-id": "phase-1-writer",
            "reviews": [
                {
                    "round": 1,
                    "reviewer-id": "phase-1-reviewer-1",
                    "validator-status": "failed",
                    "plan-sha256": plan_1,
                    "finding-fingerprints": [finding_1],
                },
                {
                    "round": 2,
                    "reviewer-id": "phase-1-reviewer-2",
                    "validator-status": "failed",
                    "plan-sha256": plan_2,
                    "finding-fingerprints": [finding_2],
                },
                {
                    "round": 3,
                    "reviewer-id": "phase-1-reviewer-3",
                    "validator-status": "passed",
                    "plan-sha256": current,
                    "finding-fingerprints": [],
                },
            ],
            "repairs": [
                {
                    "round": 1,
                    "repair-writer-id": "phase-1-repair-writer-1",
                    "finding-fingerprints": [finding_1],
                    "before-plan-sha256": plan_1,
                    "after-plan-sha256": plan_2,
                },
                {
                    "round": 2,
                    "repair-writer-id": "phase-1-repair-writer-2",
                    "finding-fingerprints": [finding_2],
                    "before-plan-sha256": plan_2,
                    "after-plan-sha256": current,
                },
            ],
        }

    def _three_round_phase3_gate(self) -> dict:
        first = canonical_json_sha256({"authority": 1})
        second = canonical_json_sha256({"authority": 2})
        current = evidence_authority_sha256(self.orchestrate, self.root)
        finding_1 = canonical_json_sha256({"finding": "phase2-quote"})
        finding_2 = canonical_json_sha256({"finding": "phase3-missing"})
        return {
            "status": "passed",
            "phase-2-canonical-owner-ids": ["owner-a"],
            "phase-2-aggregate-writer-id": "phase-2-aggregate-writer",
            "phase-3-writer-id": "phase-3-writer",
            "reviews": [
                {
                    "round": 1,
                    "stage": "phase-2-preflight",
                    "reviewer-id": "phase-3-reviewer-1",
                    "phase-2-validator-status": "failed",
                    "phase-3-validator-status": "not-run",
                    "evidence-authority-sha256": first,
                    "finding-fingerprints": [finding_1],
                },
                {
                    "round": 2,
                    "stage": "phase-3-closure",
                    "reviewer-id": "phase-3-reviewer-2",
                    "phase-2-validator-status": "passed",
                    "phase-3-validator-status": "failed",
                    "evidence-authority-sha256": second,
                    "finding-fingerprints": [finding_2],
                },
                {
                    "round": 3,
                    "stage": "phase-3-closure",
                    "reviewer-id": "phase-3-reviewer-3",
                    "phase-2-validator-status": "passed",
                    "phase-3-validator-status": "passed",
                    "evidence-authority-sha256": current,
                    "finding-fingerprints": [],
                },
            ],
            "repairs": [
                {
                    "round": 1,
                    "repair-writer-id": "phase-3-repair-writer-1",
                    "finding-fingerprints": [finding_1],
                    "before-evidence-authority-sha256": first,
                    "after-evidence-authority-sha256": second,
                },
                {
                    "round": 2,
                    "repair-writer-id": "phase-3-repair-writer-2",
                    "finding-fingerprints": [finding_2],
                    "before-evidence-authority-sha256": second,
                    "after-evidence-authority-sha256": current,
                },
            ],
        }

    def _set_phase3_gate(self, gate: dict, *, decision: str = "coverage-complete") -> None:
        relative = "openspec/orchestrate/trace/phase-3.trace.json"
        trace = self._data(relative)
        trace["decision"] = decision
        trace["review-gate"] = gate
        self._write_data(relative, trace)
        self._write_manifest()

    def test_all_phase_complete(self) -> None:
        result = self._result("all", complete=True)
        self.assertTrue(result["ok"], result)

    def test_phase1_review_gate_is_bounded_to_three_reviews_and_two_repairs(self) -> None:
        valid_gate = self._three_round_phase1_gate()
        self._set_phase1_review_gate(valid_gate, status="initial-plan-written")
        self.assertTrue(self._result("phase-1")["ok"])

        four_reviews = copy.deepcopy(valid_gate)
        four_reviews["reviews"].append({
            "round": 4,
            "reviewer-id": "phase-1-reviewer-4",
            "validator-status": "passed",
            "plan-sha256": valid_gate["reviews"][-1]["plan-sha256"],
            "finding-fingerprints": [],
        })
        self._set_phase1_review_gate(four_reviews, status="initial-plan-written")
        self._assert_rule(self._result("phase-1"), "phase1-review-gate-reviews")

        three_repairs = copy.deepcopy(valid_gate)
        three_repairs["repairs"].append(copy.deepcopy(three_repairs["repairs"][-1]))
        self._set_phase1_review_gate(three_repairs, status="initial-plan-written")
        self._assert_rule(self._result("phase-1"), "phase1-review-gate-repairs")

    def test_phase1_repeated_finding_with_noop_repair_must_block(self) -> None:
        current = sha256_file(self.orchestrate / "phase-works/phase-1/initial-change-plan.md")
        finding = canonical_json_sha256({"finding": "repeated"})
        gate = {
            "status": "passed",
            "writer-id": "phase-1-writer",
            "reviews": [
                {
                    "round": 1,
                    "reviewer-id": "phase-1-reviewer-1",
                    "validator-status": "failed",
                    "plan-sha256": current,
                    "finding-fingerprints": [finding],
                },
                {
                    "round": 2,
                    "reviewer-id": "phase-1-reviewer-2",
                    "validator-status": "failed",
                    "plan-sha256": current,
                    "finding-fingerprints": [finding],
                },
            ],
            "repairs": [{
                "round": 1,
                "repair-writer-id": "phase-1-repair-writer",
                "finding-fingerprints": [finding],
                "before-plan-sha256": current,
                "after-plan-sha256": current,
            }],
        }
        self._set_phase1_review_gate(gate, status="initial-plan-written")
        self._assert_rule(self._result("phase-1"), "phase1-review-no-progress")
        self._assert_rule(self._result("phase-1"), "phase1-review-continued-after-block")

        gate["reviews"] = gate["reviews"][:1]
        gate["status"] = "blocked"
        self._set_phase1_review_gate(gate, status="blocked")
        blocked = self._result("phase-1")
        self.assertTrue(blocked["ok"], blocked)

    def test_phase1_repeated_finding_blocks_even_when_plan_digest_changed(self) -> None:
        gate = self._three_round_phase1_gate()
        repeated = gate["reviews"][0]["finding-fingerprints"][0]
        gate["reviews"][1]["finding-fingerprints"] = [repeated]
        gate["repairs"][1]["finding-fingerprints"] = [repeated]
        self._set_phase1_review_gate(gate, status="initial-plan-written")
        result = self._result("phase-1")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase1-review-no-progress")
        self._assert_rule(result, "phase1-review-continued-after-block")

        current = sha256_file(self.orchestrate / "phase-works/phase-1/initial-change-plan.md")
        gate["reviews"] = gate["reviews"][:2]
        gate["repairs"] = gate["repairs"][:1]
        gate["reviews"][1]["plan-sha256"] = current
        gate["repairs"][0]["after-plan-sha256"] = current
        gate["status"] = "blocked"
        self._set_phase1_review_gate(gate, status="blocked")
        blocked = self._result("phase-1")
        self.assertTrue(blocked["ok"], blocked)

    def test_phase1_nonconsecutive_repeated_finding_also_blocks(self) -> None:
        gate = self._three_round_phase1_gate()
        gate["reviews"][2]["validator-status"] = "failed"
        gate["reviews"][2]["finding-fingerprints"] = [
            gate["reviews"][0]["finding-fingerprints"][0]
        ]
        self._set_phase1_review_gate(gate, status="initial-plan-written")
        result = self._result("phase-1")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase1-review-no-progress")

        gate["status"] = "blocked"
        self._set_phase1_review_gate(gate, status="blocked")
        blocked = self._result("phase-1")
        self.assertTrue(blocked["ok"], blocked)

    def test_manifest_v2_authority_is_enforced(self) -> None:
        relative = "openspec/orchestrate/trace/manifest.json"
        data = self._data(relative)
        atom = next(row for row in data["artifacts"] if row["role"] == "source-atoms")
        atom["authority"] = "derived"
        self._write_data(relative, data)
        result = self._result("phase-2")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "manifest-artifact-authority")

    def test_manifest_v1_is_rejected(self) -> None:
        relative = "openspec/orchestrate/trace/manifest.json"
        data = self._data(relative)
        data["trace-schema"] = "source-aligned-orchestrate-manifest-v1"
        self._write_data(relative, data)
        result = self._result("phase-1")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "trace-schema")

    def test_phase2_atoms_and_index_drift_then_rerender(self) -> None:
        atom_md = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.md"
        index_md = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/index.md"
        atom_md.write_text(atom_md.read_text(encoding="utf-8") + "手工修改\n", encoding="utf-8")
        index_md.write_text(index_md.read_text(encoding="utf-8") + "手工修改\n", encoding="utf-8")
        result = self._result("phase-2")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "rendered-markdown-drift")
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        render_orchestrate(self.orchestrate, "phase2-index", write=True)
        self.assertTrue(self._result("phase-2")["ok"])

    def test_phase2_blocked_trace_is_terminal_without_retry_payload(self) -> None:
        self._write_data("openspec/orchestrate/trace/phase-2.trace.json", {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-2"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "blocked",
            "issues": ["当前generation的extraction无法在授权边界内完成，不得自动重跑。"],
        })
        self._write_manifest()
        result = self._result("phase-2")
        self.assertTrue(result["ok"], result)

    def test_repository_relative_paths_are_canonical(self) -> None:
        atom_path = (
            self.orchestrate
            / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        )
        self.assertEqual(
            repo_relative_path(atom_path, self.root),
            "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json",
        )
        relative = "openspec/orchestrate/trace/phase-2.trace.json"
        trace = self._data(relative)
        trace["work-queue-path"] = "phase-works/phase-2/source-obligation-atoms/work-queue.md"
        self._write_data(relative, trace)
        result = self._result("phase-2")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase2-trace-path")

    def test_phase2_preflight_needs_only_queue_atoms_and_phase1_authority(self) -> None:
        (self.orchestrate / "trace/phase-2.trace.json").unlink()
        (self.orchestrate / "trace/manifest.json").unlink()
        (self.orchestrate / "phase-works/phase-2/source-obligation-atoms/index.md").unlink()
        (
            self.orchestrate
            / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.md"
        ).unlink()
        result = self._result("phase-2", preflight=True)
        self.assertTrue(result["ok"], result)

    def test_preflight_cli_accepts_phase2_and_rejects_other_modes(self) -> None:
        validator = SCRIPT_DIR / "validate_source_aligned_orchestrate.py"
        base = [
            sys.executable,
            str(validator),
            "--orchestrate-dir",
            str(self.orchestrate),
            "--workspace-root",
            str(self.root),
        ]
        accepted = subprocess.run(
            [*base, "--phase", "phase-2", "--preflight", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        self.assertTrue(json.loads(accepted.stdout)["ok"])

        rejected = subprocess.run(
            [*base, "--phase", "all", "--preflight"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(rejected.returncode, 0)

    def test_phase2_candidate_mapping_matrix_accepts_all_v5_combinations(self) -> None:
        relative = (
            "openspec/orchestrate/phase-works/phase-2/"
            "source-obligation-atoms/docs--source.atoms.json"
        )
        original = self._data(relative)
        cases = [
            ("direct-candidate", "spec-requirement", "change-a", "cap-a"),
            ("direct-candidate", "spec-guard", "change-a", "cap-a"),
            ("direct-candidate", "design-obligation", "change-a", "none"),
            ("unassigned", "spec-requirement", "unassigned", "cap-a"),
            ("unassigned", "spec-guard", "unassigned", "unresolved"),
            ("unassigned", "verification-obligation", "unassigned", "none"),
            ("contextual-candidate", "contextual-only", "contextual", "none"),
            ("contextual-candidate", "contextual-only", "none", "none"),
            ("unresolved-conflict", "unsure", "none", "none"),
            ("unclassified", "unsure", "none", "none"),
        ]
        for status, projection, owner, target in cases:
            with self.subTest(status=status, projection=projection):
                data = copy.deepcopy(original)
                row = data["source-atoms"][0]
                row.update({
                    "candidate-status": status,
                    "candidate-artifact-projection": projection,
                    "candidate-owner-change": owner,
                    "candidate-target-capability": target,
                    "rationale": "该映射符合v5候选矩阵并保留独立occurrence。",
                })
                if status in {"unresolved-conflict", "unclassified"}:
                    data["blockers"] = ["该候选存在待Phase 5裁决的阻塞项。"]
                self._write_data(relative, data)
                result = self._result("phase-2", preflight=True)
                self.assertTrue(result["ok"], result)

    def test_phase2_candidate_mapping_matrix_rejects_invalid_targets(self) -> None:
        relative = (
            "openspec/orchestrate/phase-works/phase-2/"
            "source-obligation-atoms/docs--source.atoms.json"
        )
        data = self._data(relative)
        data["source-atoms"][0]["candidate-target-capability"] = "none"
        self._write_data(relative, data)
        self._assert_rule(self._result("phase-2", preflight=True), "phase2-target")

    def test_phase2_candidate_mapping_matrix_rejects_invalid_status_combinations(self) -> None:
        relative = (
            "openspec/orchestrate/phase-works/phase-2/"
            "source-obligation-atoms/docs--source.atoms.json"
        )
        original = self._data(relative)
        invalid_cases = [
            ("direct-candidate", "unsure", "change-a", "none", ["phase2-actionable-projection"]),
            ("unassigned", "unsure", "unassigned", "none", ["phase2-actionable-projection"]),
            ("contextual-candidate", "contextual-only", "change-a", "none", ["phase2-contextual-owner"]),
            ("contextual-candidate", "contextual-only", "contextual", "cap-a", ["phase2-target"]),
        ]
        for status, projection, owner, target, rules in invalid_cases:
            with self.subTest(status=status, owner=owner, target=target):
                data = copy.deepcopy(original)
                data["source-atoms"][0].update({
                    "candidate-status": status,
                    "candidate-artifact-projection": projection,
                    "candidate-owner-change": owner,
                    "candidate-target-capability": target,
                })
                self._write_data(relative, data)
                result = self._result("phase-2", preflight=True)
                self.assertFalse(result["ok"], result)
                for rule in rules:
                    self._assert_rule(result, rule)

        data = copy.deepcopy(original)
        data["source-atoms"][0].update({
            "candidate-status": "unresolved-conflict",
            "candidate-artifact-projection": "unsure",
            "candidate-owner-change": "none",
            "candidate-target-capability": "none",
        })
        data["blockers"] = []
        self._write_data(relative, data)
        self._assert_rule(
            self._result("phase-2", preflight=True), "phase2-blocker-required"
        )

        data["source-atoms"][0].update({
            "candidate-artifact-projection": "design-obligation",
            "candidate-target-capability": "cap-a",
        })
        self._write_data(relative, data)
        self._assert_rule(self._result("phase-2", preflight=True), "phase2-target")

    def test_phase3_preflight_accepts_review_pending(self) -> None:
        trace_relative = "openspec/orchestrate/trace/phase-3.trace.json"
        trace = self._data(trace_relative)
        trace["decision"] = "review-pending"
        trace["review-gate"]["status"] = "pending"
        trace["review-gate"]["reviews"] = []
        trace["review-gate"]["repairs"] = []
        self._write_data(trace_relative, trace)
        self._write_manifest()
        result = self._result("phase-3", preflight=True)
        self.assertTrue(result["ok"], result)

        terminal_result = self._result("phase-3")
        self.assertFalse(terminal_result["ok"])
        self._assert_rule(terminal_result, "phase3-terminal-state")

    def test_phase3_review_gate_allows_three_reviews_and_two_repairs(self) -> None:
        self._set_phase3_gate(self._three_round_phase3_gate())
        result = self._result("phase-3")
        self.assertTrue(result["ok"], result)

        gate = self._three_round_phase3_gate()
        gate["reviews"].append(copy.deepcopy(gate["reviews"][-1]))
        gate["reviews"][-1]["round"] = 4
        gate["reviews"][-1]["reviewer-id"] = "phase-3-reviewer-4"
        self._set_phase3_gate(gate)
        self._assert_rule(self._result("phase-3"), "phase3-review-gate-reviews")

        gate = self._three_round_phase3_gate()
        gate["repairs"].append(copy.deepcopy(gate["repairs"][-1]))
        gate["repairs"][-1]["round"] = 3
        gate["repairs"][-1]["repair-writer-id"] = "phase-3-repair-writer-3"
        self._set_phase3_gate(gate)
        self._assert_rule(self._result("phase-3"), "phase3-review-gate-repairs")

    def test_phase3_review_gate_rejects_noop_repair(self) -> None:
        gate = self._three_round_phase3_gate()
        gate["repairs"][0]["after-evidence-authority-sha256"] = gate["repairs"][0][
            "before-evidence-authority-sha256"
        ]
        self._set_phase3_gate(gate)
        self._assert_rule(self._result("phase-3"), "phase3-review-terminal-block")

    def test_phase3_review_gate_rejects_repeated_finding(self) -> None:
        gate = self._three_round_phase3_gate()
        gate["reviews"][1]["finding-fingerprints"] = list(
            gate["reviews"][0]["finding-fingerprints"]
        )
        gate["repairs"][1]["finding-fingerprints"] = list(
            gate["reviews"][1]["finding-fingerprints"]
        )
        self._set_phase3_gate(gate)
        self._assert_rule(self._result("phase-3"), "phase3-review-terminal-block")

    def test_phase3_review_gate_requires_fresh_identities(self) -> None:
        gate = self._three_round_phase3_gate()
        gate["reviews"][0]["reviewer-id"] = "owner-a"
        gate["repairs"][0]["repair-writer-id"] = "phase-3-writer"
        self._set_phase3_gate(gate)
        result = self._result("phase-3")
        self._assert_rule(result, "phase3-reviewer-identity")
        self._assert_rule(result, "phase3-repair-writer-identity")

    def test_phase3_missing_obligation_range_cannot_freeze_unexplained(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-3/coverage-review.json"
        coverage = self._data(relative)
        coverage["remainder-dispositions"] = [coverage["remainder-dispositions"][1]]
        coverage["summary"]["remainder-dispositions"] = {
            "blocked": 0,
            "missing-obligation": 0,
            "safe-non-obligation": 1,
        }
        self._write_data(relative, coverage)
        render_orchestrate(self.orchestrate, "phase3-coverage-review", write=True)
        self._refresh_phase3_authority()
        self._assert_rule(self._result("phase-3"), "phase3-uncovered-disposition")

    def test_phase3_safe_non_obligation_cannot_link_a_gap_atom(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-3/coverage-review.json"
        coverage = self._data(relative)
        coverage["remainder-dispositions"][1]["linked-gap-atom-ids"] = ["P3-GAP-0001"]
        self._write_data(relative, coverage)
        render_orchestrate(self.orchestrate, "phase3-coverage-review", write=True)
        self._refresh_phase3_authority()
        self._assert_rule(self._result("phase-3"), "phase3-unexpected-gap-link")

    def test_phase3_mixed_responsibility_finding_requires_repair_before_freeze(self) -> None:
        gate = self._data("openspec/orchestrate/trace/phase-3.trace.json")["review-gate"]
        gate["reviews"][0]["phase-3-validator-status"] = "failed"
        gate["reviews"][0]["finding-fingerprints"] = [
            canonical_json_sha256({
                "source-document": "docs/source.md",
                "source-atom-id": "SA-0001",
                "finding": "mixed-independent-responsibilities",
            })
        ]
        final_review = copy.deepcopy(gate["reviews"][0])
        final_review.update({
            "round": 2,
            "reviewer-id": "phase-3-reviewer-2",
            "phase-3-validator-status": "passed",
            "finding-fingerprints": [],
        })
        gate["reviews"].append(final_review)
        self._set_phase3_gate(gate)
        result = self._result("phase-3")
        self._assert_rule(result, "phase3-review-repair-cardinality")

    def test_phase3_explicit_mapping_ambiguity_passes_and_renders(self) -> None:
        coverage_path = self.orchestrate / "phase-works/phase-3/coverage-review.json"
        coverage = self._data("openspec/orchestrate/phase-works/phase-3/coverage-review.json")
        coverage["mapping-ambiguities"] = [{
            "global-atom-id": "GA-0004",
            "evidence-ref": self._ref("SA-0004"),
            "dimensions": ["owner-change", "relation", "artifact-projection", "target-capability"],
            "reason": (
                "原文中的 unresolved fact 与 HTTP、Notify、Function、API Key 轮换等领域名称"
                "可以用于解释潜在歧义，最终归属与投影仍由Phase 5结合完整集合裁决。"
            ),
        }]
        coverage["summary"]["mapping-ambiguities"] = 1
        write_json(coverage_path, coverage)
        render_orchestrate(self.orchestrate, "phase3-coverage-review", write=True)

        trace_relative = "openspec/orchestrate/trace/phase-3.trace.json"
        trace = self._data(trace_relative)
        trace["coverage-review-sha256"] = sha256_file(coverage_path)
        self._write_data(trace_relative, trace)
        self._refresh_phase3_authority()

        result = self._result("phase-3")
        self.assertTrue(result["ok"], result)
        rendered = coverage_path.with_suffix(".md").read_text(encoding="utf-8")
        self.assertIn("GA-0004", rendered)
        self.assertIn("owner-change", rendered)

        refit_path = self.orchestrate / "phase-works/phase-5/framework-refit-trace.json"
        review = render_coverage_review(self.orchestrate, coverage_path)
        self.assertIn("## Mapping Ambiguities", review)
        render_orchestrate(self.orchestrate, "phase5-refit-review", write=True)
        phase5_review = (refit_path.parent / "plan-refit-review.md").read_text(encoding="utf-8")
        self.assertIn("## Potential Mapping Ambiguities (Input)", phase5_review)
        self.assertIn("GA-0004", phase5_review)

    def test_phase3_mapping_ambiguity_rejects_source_fact_field(self) -> None:
        coverage_path = self.orchestrate / "phase-works/phase-3/coverage-review.json"
        coverage = self._data("openspec/orchestrate/phase-works/phase-3/coverage-review.json")
        coverage["mapping-ambiguities"] = [{
            "global-atom-id": "GA-0004",
            "evidence-ref": self._ref("SA-0004"),
            "dimensions": ["owner-change"],
            "reason": "该证据存在多个合理归属，需要在Phase 5裁决。",
            "source-fact": "unresolved fact",
        }]
        coverage["summary"]["mapping-ambiguities"] = 1
        write_json(coverage_path, coverage)
        render_orchestrate(self.orchestrate, "phase3-coverage-review", write=True)

        trace_relative = "openspec/orchestrate/trace/phase-3.trace.json"
        trace = self._data(trace_relative)
        trace["coverage-review-sha256"] = sha256_file(coverage_path)
        self._write_data(trace_relative, trace)
        self._write_manifest()

        result = self._result("phase-3")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase3-mapping-ambiguity-fields")

    def test_phase3_mirror_drift_is_rejected(self) -> None:
        path = self.orchestrate / "phase-works/phase-3/coverage-review.md"
        path.write_text(path.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
        result = self._result("phase-3")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "rendered-markdown-drift")

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
        first = index["rows"][0]
        self.assertEqual(
            first["rendered-collection-paths"],
            [
                "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/by-input-change/change-a.md",
                "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/by-input-capability/cap-a.md",
            ],
        )
        for artifact in index["rendered-artifacts"]:
            self.assertEqual(artifact["sha256"], sha256_file(self.root / artifact["artifact-path"]))

    def test_phase4_markdown_drift_and_stale_file_are_rejected(self) -> None:
        collection = self.orchestrate / "phase-works/phase-4/source-evidence-collections/by-input-change/change-a.md"
        collection.write_text(collection.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
        stale = self._write(
            "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/by-input-change/stale.md",
            "stale\n",
        )
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-rendered-collection-drift")
        self._assert_rule(result, "phase4-rendered-collection-extra")
        self.assertTrue(stale.exists())

    def test_phase4_wrong_bucket_is_rejected(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        data = self._data(relative)
        data["rows"][1]["change-bucket"] = "change-a"
        self._write_data(relative, data)
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-derived-index-drift")

    def test_phase4_duplicate_ga_is_rejected(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        data = self._data(relative)
        data["rows"].append(dict(data["rows"][0]))
        self._write_data(relative, data)
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-derived-index-drift")

    def test_phase4_missing_ga_is_rejected(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        data = self._data(relative)
        data["rows"].pop()
        self._write_data(relative, data)
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-derived-index-drift")

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
        self._assert_rule(result, "phase4-assembly")

    def test_phase4_rejects_phase2_atom_mutation_after_evidence_freeze(self) -> None:
        relative = (
            "openspec/orchestrate/phase-works/phase-2/"
            "source-obligation-atoms/docs--source.atoms.json"
        )
        atoms = self._data(relative)
        atoms["source-atoms"][0]["rationale"] = "冻结后不得修改该occurrence。"
        self._write_data(relative, atoms)
        result = self._result("phase-4")
        self.assertFalse(result["ok"], result)
        self._assert_rule(result, "phase3-review-terminal-authority")

    def test_complete_rejects_ga_mutation_after_evidence_freeze(self) -> None:
        relative = "openspec/orchestrate/change-capability-anchors/obligation-atom-index.json"
        index = self._data(relative)
        index["global-atoms"][0], index["global-atoms"][1] = (
            index["global-atoms"][1],
            index["global-atoms"][0],
        )
        self._write_data(relative, index)
        result = self._result("all", complete=True)
        self.assertFalse(result["ok"], result)
        self._assert_rule(result, "phase3-review-terminal-authority")

    def test_phase5_review_drift_is_rejected(self) -> None:
        path = self.orchestrate / "phase-works/phase-5/plan-refit-review.md"
        text = path.read_text(encoding="utf-8")
        text = "\n".join(line for line in text.splitlines() if "`GA-0005`" not in line) + "\n"
        path.write_text(text, encoding="utf-8")
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "rendered-markdown-drift")

    def test_phase5_refit_must_cover_every_unassigned_ga(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-5/framework-refit-trace.json"
        data = self._data(relative)
        data["unassigned-and-gap-reviews"].pop()
        self._write_data(relative, data)
        render_orchestrate(self.orchestrate, "phase5-refit-review", write=True)
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-refit-contract")

    def test_phase5_mapping_v4_rejects_repeated_source_fields(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json"
        data = self._data(relative)
        data["rows"][0]["source-document"] = "docs/source.md"
        self._write_data(relative, data)
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-mapping-contract")

    def test_long_unique_mapping_has_no_length_based_failure(self) -> None:
        changes, capabilities, overlay = parse_final_plan(
            self.orchestrate / "phase-works/phase-5/change-plan.md"
        )
        evidence = {}
        mapping = {}
        for index in range(1, 129):
            ga = f"GA-{index:04d}"
            evidence_ref = {
                "kind": "phase-2-source-atom",
                "source-document": "docs/source.md",
                "source-atom-id": f"SA-{index:04d}",
            }
            evidence[ga] = Evidence(
                ga=ga,
                evidence_ref=evidence_ref,
                source_document="docs/source.md",
                line_ranges=((index, index),),
                source_fact=f"unique source occurrence {index}",
                atom_type="behavior",
                normativity="must",
            )
            direct = index == 1
            mapping[ga] = Mapping(
                ga=ga,
                evidence_ref=evidence_ref,
                owner_change="change-a",
                relation="direct" if direct else "context",
                projection="spec-requirement" if direct else "contextual-only",
                capability_impact="new" if direct else "none",
                target_capability="cap-a" if direct else "none",
                related_capabilities=(),
                reason=f"第{index}条证据保持独立映射，不按列表长度触发返工。",
            )

        validate_mapping(
            evidence,
            mapping,
            changes,
            capabilities,
            overlay,
            repo_root=self.root,
        )

    def test_advancement_derivation_distinguishes_absent_and_existing_capability(self) -> None:
        changes, capabilities, _ = parse_final_plan(
            self.orchestrate / "phase-works/phase-5/change-plan.md"
        )

        def direct_mapping(impact: str) -> dict[str, Mapping]:
            return {
                "GA-0001": Mapping(
                    ga="GA-0001",
                    evidence_ref=self._ref("SA-0001"),
                    owner_change="change-a",
                    relation="direct",
                    projection="spec-requirement",
                    capability_impact=impact,
                    target_capability="cap-a",
                    related_capabilities=(),
                    reason="用于核验repository baseline的确定性推进关系。",
                )
            }

        absent_overlay, absent_baseline = derive_advancement(
            self.root,
            changes,
            capabilities,
            direct_mapping("new"),
        )
        self.assertEqual(absent_overlay, {("change-a", "cap-a"): "new"})
        self.assertEqual(
            absent_baseline["capabilities"][0]["baseline-status"],
            "absent",
        )

        self._write("openspec/specs/cap-a/spec.md", "# Existing Capability\n")
        existing_overlay, existing_baseline = derive_advancement(
            self.root,
            changes,
            capabilities,
            direct_mapping("modified"),
        )
        self.assertEqual(existing_overlay, {("change-a", "cap-a"): "modified"})
        self.assertEqual(
            existing_baseline["capabilities"][0]["baseline-status"],
            "existing",
        )

    def test_absent_capability_is_new_only_for_first_advancing_change(self) -> None:
        changes, capabilities, _ = parse_final_plan(
            self.orchestrate / "phase-works/phase-5/change-plan.md"
        )
        change_b = replace(changes[0], slug="change-b")
        mapping = {
            "GA-0001": Mapping(
                ga="GA-0001",
                evidence_ref=self._ref("SA-0001"),
                owner_change="change-a",
                relation="direct",
                projection="spec-requirement",
                capability_impact="new",
                target_capability="cap-a",
                related_capabilities=(),
                reason="第一个Change首次推进缺失Capability。",
            ),
            "GA-0002": Mapping(
                ga="GA-0002",
                evidence_ref=self._ref("SA-0002"),
                owner_change="change-b",
                relation="direct",
                projection="spec-guard",
                capability_impact="modified",
                target_capability="cap-a",
                related_capabilities=(),
                reason="第二个Change只能继续修改已由roadmap建立的Capability。",
            ),
        }
        overlay, _ = derive_advancement(
            self.root,
            [changes[0], change_b],
            capabilities,
            mapping,
        )
        self.assertEqual(overlay, {
            ("change-a", "cap-a"): "new",
            ("change-b", "cap-a"): "modified",
        })

    def test_phase5_mapping_impact_drift_is_rejected(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json"
        mapping = self._data(relative)
        mapping["rows"][0]["final-capability-impact"] = "modified"
        self._write_data(relative, mapping)
        self._write_manifest()
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-mapping-contract")

    def test_phase5_refit_overlay_drift_is_rejected(self) -> None:
        relative = (
            "openspec/orchestrate/phase-works/phase-5/framework-refit-trace.json"
        )
        refit = self._data(relative)
        refit["final-framework"]["overlay"][0]["capability-impact"] = "modified"
        self._write_data(relative, refit)
        render_orchestrate(self.orchestrate, "phase5-refit-review", write=True)
        self._write_manifest()
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-refit-contract")

    def test_phase5_final_plan_overlay_drift_is_rejected(self) -> None:
        plan = self.orchestrate / "phase-works/phase-5/change-plan.md"
        plan.write_text(
            plan.read_text(encoding="utf-8").replace(
                "| `change-a` | `cap-a` | `new` |",
                "| `change-a` | `cap-a` | `modified` |",
            ),
            encoding="utf-8",
        )
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-refit-contract")
        self._assert_rule(result, "phase5-mapping-contract")

    def test_phase5_baseline_drift_is_rejected(self) -> None:
        relative = (
            "openspec/orchestrate/phase-works/phase-5/"
            "capability-baseline-reconciliation.json"
        )
        baseline = self._data(relative)
        baseline["capabilities"][0]["required-first-relation"] = "modified"
        self._write_data(relative, baseline)
        self._write_manifest()
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-baseline-drift")

    def test_phase2_contract_uses_citation_and_lossless_mapping_not_subjective_size(self) -> None:
        contract = (
            SKILL_DIR / "references/phase-2-source-anchor-coverage.md"
        ).read_text(encoding="utf-8")
        self.assertIn("source occurrence可被独立引用", contract)
        self.assertIn("单一mapping tuple无损表达", contract)
        self.assertIn("内容较长但单一tuple可无损表达时不报错", contract)
        self.assertNotIn("独立接受、拒绝、实现、保护或验证", contract)
        self.assertNotIn("尽量紧凑", contract)

    def test_phase5_mapping_and_baseline_mirror_drift_are_rejected(self) -> None:
        work = self.orchestrate / "phase-works/phase-5"
        for name in ("atom-plan-mapping.md", "capability-baseline-reconciliation.md"):
            path = work / name
            path.write_text(path.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "rendered-markdown-drift")

    def test_phase5_packet_drift_is_rejected(self) -> None:
        packet = self.orchestrate / "change-capability-anchors/change-a/change-a.md"
        packet.write_text(packet.read_text(encoding="utf-8").replace("same outcome", "changed outcome"), encoding="utf-8")
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-packet-drift")

    def test_phase5_anchor_and_capability_view_drift_are_rejected(self) -> None:
        anchor_index = self.orchestrate / "change-capability-anchors/index.md"
        capability_view = self.orchestrate / "change-capability-anchors/change-a/capability-anchors/cap-a.md"
        anchor_index.write_text(anchor_index.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
        capability_view.write_text(capability_view.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-anchor-index-drift")
        self._assert_rule(result, "phase5-capability-view-drift")

    def test_phase5_gap_review_rejects_mapping_authority_fields(self) -> None:
        relative = "openspec/orchestrate/phase-works/phase-5/framework-refit-trace.json"
        data = self._data(relative)
        data["unassigned-and-gap-reviews"][0]["final-capability"] = "cap-a"
        self._write_data(relative, data)
        render_orchestrate(self.orchestrate, "phase5-refit-review", write=True)
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-refit-contract")

    def test_phase5_accepted_rejects_failed_initial_gate(self) -> None:
        refit = self._refit_trace()
        refit["capability-reviews"][0]["initial-gate-results"] = (
            self._capability_gate_results(failed="cohesion")
        )
        with self.assertRaises(ValueError):
            validate_framework_refit(self.orchestrate, refit)

    def test_phase5_adjusted_allows_failed_initial_gate_after_split(self) -> None:
        refit = self._refit_trace()
        refit["status"] = "adjusted"
        refit["capability-reviews"][0].update({
            "decision": "split",
            "final-capabilities": ["cap-a-one", "cap-a-two"],
            "initial-gate-results": self._capability_gate_results(failed="cohesion"),
            "supporting-global-atom-ids": ["GA-0001"],
        })
        refit["final-framework"]["capabilities"] = ["cap-a-one", "cap-a-two"]
        refit["final-framework"]["overlay"] = [{
            "change": "change-a",
            "capability": "cap-a-one",
            "capability-impact": "new",
        }]
        self.assertEqual(
            validate_framework_refit(self.orchestrate, refit),
            "adjusted",
        )

    def test_phase5_adjusted_rejects_failed_initial_gate_with_keep(self) -> None:
        refit = self._refit_trace()
        refit["status"] = "adjusted"
        refit["change-reviews"][0]["initial-gate-results"] = (
            self._change_gate_results(failed="scope-cohesion")
        )
        with self.assertRaises(ValueError):
            validate_framework_refit(self.orchestrate, refit)

    def test_phase5_non_keep_review_requires_supporting_ga(self) -> None:
        refit = self._refit_trace()
        refit["status"] = "adjusted"
        refit["change-reviews"][0]["decision"] = "scope-adjusted"
        with self.assertRaises(ValueError):
            validate_framework_refit(self.orchestrate, refit)

    def test_phase5_supporting_ga_must_belong_to_review_collection(self) -> None:
        refit = self._refit_trace()
        refit["status"] = "adjusted"
        refit["change-reviews"][0].update({
            "decision": "scope-adjusted",
            "supporting-global-atom-ids": ["GA-0002"],
        })
        with self.assertRaises(ValueError):
            validate_framework_refit(self.orchestrate, refit)

    def test_phase5_supporting_ga_must_follow_global_index_order(self) -> None:
        index_relative = (
            "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/"
            "evidence-collection-index.json"
        )
        collection = self._data(index_relative)
        ga2 = next(
            row for row in collection["rows"]
            if row["global-atom-id"] == "GA-0002"
        )
        ga2["change-bucket"] = "change-a"
        self._write_data(index_relative, collection)

        refit = self._refit_trace()
        refit["status"] = "adjusted"
        refit["change-reviews"][0].update({
            "decision": "scope-adjusted",
            "supporting-global-atom-ids": ["GA-0002", "GA-0001"],
        })
        with self.assertRaises(ValueError):
            validate_framework_refit(self.orchestrate, refit)

    def test_phase5_gap_supports_adjustment_requires_mechanical_link(self) -> None:
        refit = self._refit_trace()
        refit["status"] = "adjusted"
        refit["change-reviews"][0].update({
            "decision": "scope-adjusted",
            "supporting-global-atom-ids": ["GA-0001"],
        })
        refit["unassigned-and-gap-reviews"][0]["framework-impact"] = (
            "supports-adjustment"
        )
        self._write_data(
            "openspec/orchestrate/phase-works/phase-5/framework-refit-trace.json",
            refit,
        )
        with self.assertRaises(ValueError):
            write_outputs(self.orchestrate)

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
        refit_path = self.orchestrate / "phase-works/phase-5/framework-refit-trace.json"
        refit = json.loads(refit_path.read_text(encoding="utf-8"))
        refit["status"] = "adjusted"
        refit["final-framework"]["capabilities"].append("cap-b")
        refit["final-framework"]["overlay"].append({
            "change": "change-a", "capability": "cap-b", "capability-impact": "new",
        })
        refit["unassigned-and-gap-reviews"][3].update({
            "framework-impact": "supports-adjustment",
            "reason": "gap暴露新的稳定行为边界。",
        })
        write_json(refit_path, refit)
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

    def test_phase5_refit_split_rename_scope_and_add_shapes(self) -> None:
        base = self._refit_trace()

        def split_capability(data: dict) -> None:
            data["capability-reviews"][0].update({
                "decision": "split", "final-capabilities": ["cap-a-one", "cap-a-two"],
                "supporting-global-atom-ids": ["GA-0001"],
            })
            data["final-framework"]["capabilities"] = ["cap-a-one", "cap-a-two"]
            data["final-framework"]["overlay"] = [{
                "change": "change-a", "capability": "cap-a-one", "capability-impact": "new",
            }]

        def rename_change(data: dict) -> None:
            data["change-reviews"][0].update({
                "decision": "rename",
                "final-changes": ["change-renamed"],
                "supporting-global-atom-ids": ["GA-0001"],
            })
            data["final-framework"]["change-order"] = ["change-renamed"]
            data["final-framework"]["overlay"][0]["change"] = "change-renamed"

        def scope_change(data: dict) -> None:
            data["change-reviews"][0]["decision"] = "scope-adjusted"
            data["change-reviews"][0]["supporting-global-atom-ids"] = ["GA-0001"]

        def add_change(data: dict) -> None:
            data["final-framework"]["change-order"].append("change-new")
            data["unassigned-and-gap-reviews"][0]["framework-impact"] = "supports-adjustment"

        for name, mutate in (
            ("split-capability", split_capability),
            ("rename-change", rename_change),
            ("scope-adjusted", scope_change),
            ("add-change", add_change),
        ):
            with self.subTest(name=name):
                data = copy.deepcopy(base)
                data["status"] = "adjusted"
                mutate(data)
                self.assertEqual(validate_framework_refit(self.orchestrate, data), "adjusted")

    def test_phase5_refit_merge_and_reorder_shapes(self) -> None:
        initial_plan = self.orchestrate / "phase-works/phase-1/initial-change-plan.md"
        text = initial_plan.read_text(encoding="utf-8")
        text = text.replace(
            "\n## Change-Capability Overlay",
            "\n- Change 名称：`change-b`\n- 单一 intent：交付第二个结果。\n"
            "- source-backed outcome：形成第二个可验收结果。\n\n## Change-Capability Overlay",
        )
        initial_plan.write_text(text, encoding="utf-8")
        base = self._refit_trace()
        base["status"] = "adjusted"
        base["change-reviews"].append({
            "input-change": "change-b",
            "evidence-collection-path": "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/by-input-change/change-b.md",
            "decision": "keep",
            "final-changes": ["change-b"],
            "initial-gate-results": self._change_gate_results(),
            "supporting-global-atom-ids": [],
            "reason": "原文支持第二个独立结果。",
        })

        reordered = copy.deepcopy(base)
        reordered["change-reviews"][0]["decision"] = "reorder"
        reordered["change-reviews"][0]["supporting-global-atom-ids"] = ["GA-0001"]
        reordered["final-framework"]["change-order"] = ["change-b", "change-a"]
        self.assertEqual(validate_framework_refit(self.orchestrate, reordered), "adjusted")

        merged = copy.deepcopy(base)
        merged["change-reviews"][0].update({
            "decision": "merge",
            "final-changes": ["change-merged"],
            "supporting-global-atom-ids": ["GA-0001"],
        })
        merged["change-reviews"][1].update({
            "decision": "merge",
            "final-changes": ["change-merged"],
            "initial-gate-results": self._change_gate_results(failed="scope-cohesion"),
        })
        merged["final-framework"]["change-order"] = ["change-merged"]
        merged["final-framework"]["overlay"][0]["change"] = "change-merged"
        self.assertEqual(validate_framework_refit(self.orchestrate, merged), "adjusted")

    def test_phase5_zero_ga_collection_allows_failed_remove_without_support(self) -> None:
        initial_plan = self.orchestrate / "phase-works/phase-1/initial-change-plan.md"
        text = initial_plan.read_text(encoding="utf-8").replace(
            "\n## Change-Capability Overlay",
            "\n- Change 名称：`change-empty`\n"
            "- 单一 intent：移除无证据支撑的初始结果。\n"
            "- source-backed outcome：等待Phase 5复审。\n\n"
            "## Change-Capability Overlay",
        )
        initial_plan.write_text(text, encoding="utf-8")
        render_orchestrate(self.orchestrate, "phase4-evidence-collections", write=True)

        refit = self._refit_trace()
        refit["status"] = "adjusted"
        refit["change-reviews"].append({
            "input-change": "change-empty",
            "evidence-collection-path": (
                "openspec/orchestrate/phase-works/phase-4/"
                "source-evidence-collections/by-input-change/change-empty.md"
            ),
            "decision": "remove",
            "final-changes": [],
            "initial-gate-results": self._change_gate_results(
                failed="implementation-readiness"
            ),
            "supporting-global-atom-ids": [],
            "reason": "初始Change没有关联GA且初始gate失败，因此移除。",
        })
        self.assertEqual(
            validate_framework_refit(self.orchestrate, refit),
            "adjusted",
        )

    def test_phase5_zero_ga_collections_allow_failed_merge_without_support(self) -> None:
        initial_plan = self.orchestrate / "phase-works/phase-1/initial-change-plan.md"
        text = initial_plan.read_text(encoding="utf-8").replace(
            "\n## Change-Capability Overlay",
            "\n- Change 名称：`change-empty-a`\n"
            "- 单一 intent：复审第一个空初始结果。\n"
            "- source-backed outcome：等待Phase 5复审。\n\n"
            "- Change 名称：`change-empty-b`\n"
            "- 单一 intent：复审第二个空初始结果。\n"
            "- source-backed outcome：等待Phase 5复审。\n\n"
            "## Change-Capability Overlay",
        )
        initial_plan.write_text(text, encoding="utf-8")
        render_orchestrate(self.orchestrate, "phase4-evidence-collections", write=True)

        refit = self._refit_trace()
        refit["status"] = "adjusted"
        for change in ("change-empty-a", "change-empty-b"):
            refit["change-reviews"].append({
                "input-change": change,
                "evidence-collection-path": (
                    "openspec/orchestrate/phase-works/phase-4/"
                    f"source-evidence-collections/by-input-change/{change}.md"
                ),
                "decision": "merge",
                "final-changes": ["change-merged"],
                "initial-gate-results": self._change_gate_results(
                    failed="scope-cohesion"
                ),
                "supporting-global-atom-ids": [],
                "reason": "空集合对应的初始gate失败，合并后由一次final review裁决。",
            })
        refit["final-framework"]["change-order"] = ["change-a", "change-merged"]
        self.assertEqual(
            validate_framework_refit(self.orchestrate, refit),
            "adjusted",
        )

    def test_phase5_accepted_rejects_boundary_change(self) -> None:
        plan = self.orchestrate / "phase-works/phase-5/change-plan.md"
        plan.write_text(plan.read_text(encoding="utf-8").replace("结果行为和必要约束。", "不同的结果边界。"), encoding="utf-8")
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-refit-status-consistency")

    def test_phase5_adjusted_requires_actual_framework_change(self) -> None:
        refit_path = self.orchestrate / "phase-works/phase-5/framework-refit-trace.json"
        refit = json.loads(refit_path.read_text(encoding="utf-8"))
        refit["status"] = "adjusted"
        refit["change-reviews"][0]["decision"] = "scope-adjusted"
        refit["change-reviews"][0]["supporting-global-atom-ids"] = ["GA-0001"]
        write_json(refit_path, refit)
        render_orchestrate(self.orchestrate, "phase5-refit-review", write=True)
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-refit-status-consistency")

    def test_phase5_helper_uses_frozen_evidence_without_source(self) -> None:
        (self.root / "docs/source.md").unlink()
        write_outputs(self.orchestrate)
        packet = self.orchestrate / "change-capability-anchors/change-a/change-a.md"
        self.assertIn("same | requirement", packet.read_text(encoding="utf-8"))
        self.assertTrue(self._result("phase-5")["ok"])

    def test_phase5_blocked_cleans_all_terminal_surface_and_root_plan(self) -> None:
        authority_before = evidence_authority_sha256(self.orchestrate, self.root)
        relative = "openspec/orchestrate/phase-works/phase-5/framework-refit-trace.json"
        refit = self._data(relative)
        refit["status"] = "blocked"
        refit["final-framework"] = None
        refit["issues"] = ["冻结 evidence 存在 quote/range integrity defect，必须启动新generation。"]
        self._write_data(relative, refit)

        write_outputs(self.orchestrate)
        self._write_manifest()

        trace = self._data("openspec/orchestrate/trace/phase-5.trace.json")
        self.assertEqual(trace["status"], "blocked")
        forbidden = [
            self.orchestrate / "change-plan.md",
            self.orchestrate / "phase-works/phase-5/change-plan.md",
            self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json",
            self.orchestrate / "phase-works/phase-5/capability-baseline-reconciliation.json",
            self.orchestrate / "phase-works/phase-5/final-packet-index.json",
        ]
        self.assertFalse(any(path.exists() for path in forbidden), forbidden)
        self.assertEqual(
            evidence_authority_sha256(self.orchestrate, self.root), authority_before
        )
        result = self._result("phase-5")
        self.assertTrue(result["ok"], result)

    def test_phase5_late_discovered_ambiguity_resolves_without_phase3_backfill(self) -> None:
        coverage_path = self.orchestrate / "phase-works/phase-3/coverage-review.json"
        coverage_before = coverage_path.read_bytes()
        authority_before = evidence_authority_sha256(self.orchestrate, self.root)
        mapping_relative = "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json"
        mapping = self._data(mapping_relative)
        mapping["rows"][0]["reason"] = (
            "Phase 5发现Phase 3未记录的mapping ambiguity；根据可观察结果边界裁决为唯一direct tuple。"
        )
        self._write_data(mapping_relative, mapping)
        write_outputs(self.orchestrate)
        self._write_manifest()

        self.assertEqual(coverage_path.read_bytes(), coverage_before)
        self.assertEqual(
            evidence_authority_sha256(self.orchestrate, self.root), authority_before
        )
        result = self._result("all", complete=True)
        self.assertTrue(result["ok"], result)

    def test_phase5_legacy_artifact_is_rejected(self) -> None:
        self._write("openspec/orchestrate/phase-works/phase-5/phase5-refit.config.json", "{}\n")
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-legacy-artifact")

    def test_trace_contract_v4_is_rejected(self) -> None:
        relative = "openspec/orchestrate/trace/phase-1.trace.json"
        trace = self._data(relative)
        trace["trace-contract-version"] = "source-aligned-trace-v4"
        self._write_data(relative, trace)
        self._write_manifest()
        result = self._result("phase-1")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "trace-contract-version")

    def test_framework_refit_v2_is_rejected(self) -> None:
        relative = (
            "openspec/orchestrate/phase-works/phase-5/framework-refit-trace.json"
        )
        refit = self._data(relative)
        refit["trace-schema"] = "source-aligned-framework-refit-trace-v2"
        self._write_data(relative, refit)
        self._write_manifest()
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase5-refit-contract")

    def test_v5_rejects_removed_patch_and_checkpoint_artifacts(self) -> None:
        self._write(
            "openspec/orchestrate/phase-works/phase-5/evidence-patch-request.json",
            "{}\n",
        )
        self._write(
            "openspec/orchestrate/phase-works/phase-5/phase-5-checkpoint.json",
            "{}\n",
        )
        result = self._result("phase-5")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "legacy-patch-artifact")
        self._assert_rule(result, "phase5-legacy-artifact")

    def test_render_contract_v7_is_rejected(self) -> None:
        relative = "openspec/orchestrate/trace/phase-4.trace.json"
        trace = self._data(relative)
        trace["assembled"]["renderer-result-summary"][
            "render-contract-version"
        ] = "source-aligned-render-v7"
        self._write_data(relative, trace)
        self._write_manifest()
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-renderer-summary")

    def test_old_phase4_and_phase5_trace_schemas_are_rejected(self) -> None:
        phase4 = self._data("openspec/orchestrate/trace/phase-4.trace.json")
        phase4["trace-schema"] = "source-aligned-phase-4-trace-v2"
        self._write_data("openspec/orchestrate/trace/phase-4.trace.json", phase4)
        result4 = self._result("phase-4")
        self.assertFalse(result4["ok"])
        self._assert_rule(result4, "trace-schema")

        phase5 = self._data("openspec/orchestrate/trace/phase-5.trace.json")
        phase5["trace-schema"] = "source-aligned-phase-5-trace-v2"
        self._write_data("openspec/orchestrate/trace/phase-5.trace.json", phase5)
        result5 = self._result("phase-5")
        self.assertFalse(result5["ok"])
        self._assert_rule(result5, "trace-schema")

    def test_old_phase4_index_and_missing_refit_json_are_rejected(self) -> None:
        index_relative = "openspec/orchestrate/phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        index = self._data(index_relative)
        index["trace-schema"] = "source-aligned-evidence-collection-index-v1"
        self._write_data(index_relative, index)
        result4 = self._result("phase-4")
        self.assertFalse(result4["ok"])
        self._assert_rule(result4, "trace-schema")

        refit = self.orchestrate / "phase-works/phase-5/framework-refit-trace.json"
        refit.unlink()
        result5 = self._result("phase-5")
        self.assertFalse(result5["ok"])
        self._assert_rule(result5, "missing-json")

    def test_phase4_nonterminal_forbids_terminal_collections(self) -> None:
        write_json(self.orchestrate / "trace/phase-4.trace.json", {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-4"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "blocked",
            "issues": ["上游coverage尚未收敛。"],
        })
        result = self._result("phase-4")
        self.assertFalse(result["ok"])
        self._assert_rule(result, "phase4-blocked-derived-artifact")

    def test_phase4_renderer_cleans_legacy_artifacts(self) -> None:
        legacy_file = self._write("openspec/orchestrate/phase-works/phase-4/input-change-plan.md", "legacy\n")
        legacy_dir = self.orchestrate / "phase-works/phase-4/source-window-dossiers"
        legacy_dir.mkdir(parents=True)
        (legacy_dir / "index.md").write_text("legacy\n", encoding="utf-8")
        render_orchestrate(self.orchestrate, "phase4-evidence-collections", write=True)
        self.assertFalse(legacy_file.exists())
        self.assertFalse(legacy_dir.exists())

    def test_phase4_renderer_rebuilds_malformed_derived_index(self) -> None:
        index = self.orchestrate / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        index.write_text("{malformed\n", encoding="utf-8")
        render_orchestrate(self.orchestrate, "phase4-evidence-collections", write=True)
        self.assertEqual(json.loads(index.read_text(encoding="utf-8"))["trace-schema"], EVIDENCE_COLLECTION_INDEX_SCHEMA)
        self.assertTrue(self._result("phase-4")["ok"])

    def test_phase5_helper_has_no_config_interface(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "phase5_plan_refit.py"), "--config", "legacy.json"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(completed.returncode, 0)

    def test_phase1_and_phase5_share_one_principles_document(self) -> None:
        shared = "references/change-capability-framework-principles.md"
        for relative in ("references/phase-1-initial-change-plan.md", "references/phase-5-framework-refit-and-mapping.md"):
            text = (SKILL_DIR / relative).read_text(encoding="utf-8")
            self.assertIn(shared, text)
            self.assertNotIn("## Capability gate", text)
            self.assertNotIn("## Change gate", text)

    def test_phase5_reference_is_compact_and_old_alias_is_removed(self) -> None:
        phase5 = SKILL_DIR / "references/phase-5-framework-refit-and-mapping.md"
        old_alias = SKILL_DIR / "references/phase-5-targeted-plan-adjustment.md"
        patch_contract = SKILL_DIR / "references/targeted-evidence-patch-contract.md"
        self.assertTrue(phase5.is_file())
        self.assertFalse(patch_contract.exists())
        self.assertFalse(old_alias.exists())
        self.assertLess(len(phase5.read_text(encoding="utf-8").splitlines()), 150)


if __name__ == "__main__":
    unittest.main()
