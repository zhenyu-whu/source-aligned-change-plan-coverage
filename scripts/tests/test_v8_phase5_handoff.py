#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v8 Phase 5 public handoff、bounded review 与 workflow completion 测试。

本文件只在 tempfile 中构造 generation；绝不读取或修改工作区现存的
``openspec/orchestrate``。
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional
from unittest import mock


TEST_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = TEST_DIR.parent
for candidate in (str(TEST_DIR), str(SCRIPT_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import phase5_plan_refit as phase5  # noqa: E402
from render_source_aligned_orchestrate import (  # noqa: E402
    render_coverage_review,
    render_final_integration_review,
    render_global_index,
    render_initial_framework,
    render_orchestrate,
    render_phase2_index,
    render_phase2_source_atoms,
)
from source_aligned_trace_lib import (  # noqa: E402
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_GATE_NAMES,
    CHANGE_GATE_NAMES,
    FINAL_INTEGRATION_REVIEW_SCHEMA,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
    FRAMEWORK_REFIT_TRACE_SCHEMA,
    GLOBAL_ATOM_INDEX_SCHEMA,
    INITIAL_FRAMEWORK_SCHEMA,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    WORKFLOW_COMPLETION_SCHEMA,
    IssueReporter,
    evidence_authority_sha256,
    sha256_file,
    write_json,
)
from source_aligned_v8_contract import (  # noqa: E402
    terminal_authority_payload,
    terminal_authority_sha256,
)
from test_source_aligned_v8_contract import (  # noqa: E402
    _base_roadmap,
    _foundation_roadmap,
)
from validate_source_aligned_orchestrate import (  # noqa: E402
    validate_phase_5,
    validate_workflow_terminal,
)
from review_fixture_v8 import write_review_result  # noqa: E402


REPEATED_SOURCE = "重复的冻结要求原文"
CONTEXT_SOURCE = "只属于 Change 上下文的设计背景原文"
DEPENDENCY_SOURCE = "依赖关系的冻结背景原文"


def _repo_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _gate_rows(gates: object, ga: str) -> List[Dict[str, object]]:
    return [
        {
            "gate": gate,
            "result": "passed",
            "note": f"{gate}已由冻结证据验证通过",
            "evidence-ga-ids": [ga],
        }
        for gate in gates
    ]


def _source_ref(index: int) -> Dict[str, object]:
    return {
        "kind": "phase-2-source-atom",
        "source-document": "docs/source.md",
        "source-atom-id": f"SA-{index:04d}",
    }


class V8HandoffFixture:
    """最小但完整的 Phase 5 helper fixture。"""

    def __init__(
        self,
        root: Path,
        *,
        foundation: bool = False,
        include_audit_capability: bool = False,
        include_guard: bool = False,
        second_target: str = "report-delivery",
        dependency_owner: str = "notify-reader",
        generation_name: str = "orchestrate",
    ) -> None:
        self.root = root
        self.generation_name = generation_name
        self.generation_prefix = f"openspec/{generation_name}"
        self.orchestrate = root / "openspec" / generation_name
        self.work = self.orchestrate / "phase-works/phase-5"
        self.foundation = foundation
        self.include_audit_capability = include_audit_capability
        self.include_guard = include_guard
        self.second_target = second_target
        self.dependency_owner = dependency_owner
        self.roadmap = self._roadmap()
        self.mapping_rows = self._mapping_rows()
        self._write_evidence()
        self._write_phase1_framework()
        self._write_freeze_traces()
        self._write_phase5_authority()

    @property
    def ga_count(self) -> int:
        return 7 if self.foundation else 6

    def _roadmap(self) -> Dict[str, object]:
        roadmap = (
            copy.deepcopy(_foundation_roadmap())
            if self.foundation
            else copy.deepcopy(_base_roadmap())
        )
        roadmap["artifact-path"] = (
            f"{self.generation_prefix}/phase-works/phase-5/"
            "change-plan.md"
        )
        if self.foundation and isinstance(roadmap.get("foundation"), dict):
            roadmap["foundation"]["evidence-ga-ids"] = ["GA-0007"]
        if self.include_audit_capability:
            roadmap["capabilities"].append(
                {
                    "capability": "audit-delivery",
                    "purpose": "提供可审计的交付约束",
                    "owns": "审计要求及其可观察行为",
                    "excludes": "不拥有报告主体行为",
                    "boundary-rationale": "审计职责在实现替换后仍保持稳定",
                    "evidence-ga-ids": ["GA-0002"],
                }
            )
        if self.second_target == "audit-delivery":
            roadmap["overlay"].insert(
                1,
                {
                    "change": "ship-report",
                    "capability": "audit-delivery",
                    "capability-impact": "new",
                },
            )
        if self.include_guard:
            roadmap["guard-links"] = [
                {
                    "guard-link-id": "notice-access-guard",
                    "guarding-change": "notify-reader",
                    "guarded-outcome-thread-id": "reader-gets-notice",
                    "surface-state": "planned",
                    "evidence-ga-ids": ["GA-0004"],
                }
            ]
        return roadmap

    def _mapping_rows(self) -> List[Dict[str, object]]:
        rows = [
            self._mapping(
                1,
                "ship-report",
                "direct",
                "spec-requirement",
                "new",
                "report-delivery",
            ),
            self._mapping(
                2,
                "ship-report",
                "direct",
                "spec-guard",
                "new",
                self.second_target,
            ),
            self._mapping(
                3,
                "notify-reader",
                "direct",
                "spec-requirement",
                "modified",
                "report-delivery",
            ),
            self._mapping(
                4,
                "notify-reader",
                "direct",
                "spec-guard",
                "modified",
                "report-delivery",
            ),
            self._mapping(
                5,
                self.dependency_owner,
                "dependency",
                "contextual-only",
                "none",
                "none",
            ),
            self._mapping(
                6,
                "notify-reader",
                "reference",
                "contextual-only",
                "none",
                "none",
            ),
        ]
        if self.foundation:
            rows.append(
                self._mapping(
                    7,
                    "establish-base",
                    "direct",
                    "design-obligation",
                    "none",
                    "none",
                )
            )
        return rows

    @staticmethod
    def _mapping(
        index: int,
        owner: str,
        relation: str,
        projection: str,
        impact: str,
        target: str,
    ) -> Dict[str, object]:
        return {
            "global-atom-id": f"GA-{index:04d}",
            "evidence-ref": _source_ref(index),
            "final-owner-change": owner,
            "final-relation": relation,
            "final-artifact-projection": projection,
            "final-capability-impact": impact,
            "final-target-capability": target,
            "related-capabilities": [],
            "reason": "该终态分配由冻结原文及最终结果边界直接支持。",
        }

    def _write_evidence(self) -> None:
        atom_root = (
            self.orchestrate
            / "phase-works/phase-2/source-obligation-atoms"
        )
        facts = [
            REPEATED_SOURCE,
            REPEATED_SOURCE,
            "通知结果的直接规范原文",
            "通知结果的直接守卫原文",
            DEPENDENCY_SOURCE,
            CONTEXT_SOURCE,
            "foundation只需要的实现设计原文",
        ]
        source_path = self.root / "docs/source.md"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(
            "\n".join(facts[: self.ga_count]) + "\n",
            encoding="utf-8",
        )
        mapping_by_ga = {
            row["global-atom-id"]: row for row in self.mapping_rows
        }
        atoms = []
        for index in range(1, self.ga_count + 1):
            mapping = mapping_by_ga[f"GA-{index:04d}"]
            projection = str(mapping["final-artifact-projection"])
            if projection == "contextual-only":
                candidate_status = "contextual-candidate"
                candidate_owner = "contextual"
                candidate_target = "none"
            else:
                candidate_status = "direct-candidate"
                candidate_owner = str(mapping["final-owner-change"])
                candidate_target = (
                    str(mapping["final-target-capability"])
                    if projection in {"spec-requirement", "spec-guard"}
                    else "none"
                )
            atoms.append(
                {
                    "source-atom-id": f"SA-{index:04d}",
                    "line-ranges": [{"start": index, "end": index}],
                    "atom-type": "behavior" if index <= 4 else "context",
                    "source-fact": facts[index - 1],
                    "normativity": "must" if index <= 4 else "context",
                    "candidate-status": candidate_status,
                    "candidate-artifact-projection": projection,
                    "candidate-owner-change": candidate_owner,
                    "candidate-target-capability": candidate_target,
                    "delivery-directives": (
                        ["explicit-precedence"] if index == 6 else []
                    ),
                    "rationale": (
                        "该候选映射仅记录来源提取时的上下文，"
                        "最终边界由Phase 5重新裁决。"
                    ),
                }
            )
        atom_path = atom_root / "docs--source.atoms.json"
        write_json(
            atom_path,
            {
                "trace-schema": SOURCE_ATOMS_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "source-document": "docs/source.md",
                "source-sha256": sha256_file(source_path),
                "read-status": "read-full",
                "canonical-owner": "phase2-source-writer",
                "source-role": "primary",
                "phase-1-candidate-changes-capabilities-considered": [],
                "source-atoms": atoms,
                "blockers": [],
                "language-self-check": "所有解释字段均使用简体中文。",
            },
        )
        coverage_path = (
            self.orchestrate
            / "phase-works/phase-3/coverage-review.json"
        )
        write_json(
            coverage_path,
            {
                "trace-schema": PHASE3_COVERAGE_REVIEW_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "artifact-path": _repo_path(
                    self.root,
                    coverage_path.with_suffix(".md"),
                ),
                "documents": [
                    {
                        "source-document": "docs/source.md",
                        "source-sha256": sha256_file(source_path),
                        "line-count": self.ga_count,
                        "phase-2-atom-path": _repo_path(
                            self.root,
                            atom_path,
                        ),
                        "phase-2-atom-sha256": sha256_file(atom_path),
                        "covered-ranges": [
                            {"start": 1, "end": self.ga_count}
                        ],
                        "candidate-uncovered-ranges": [],
                    }
                ],
                "gap-atoms": [],
                "remainder-dispositions": [],
                "mapping-ambiguities": [],
                "summary": {
                    "source-documents": 1,
                    "phase-2-atoms": self.ga_count,
                    "gap-atoms": 0,
                    "global-atoms": self.ga_count,
                    "mapping-ambiguities": 0,
                    "candidate-uncovered-ranges": 0,
                    "remainder-dispositions": {
                        "blocked": 0,
                        "missing-obligation": 0,
                        "safe-non-obligation": 0,
                    },
                    "delivery-directive-atoms": 1,
                    "delivery-directives": {
                        "milestone-scope": 0,
                        "explicit-precedence": 1,
                        "explicit-deferred": 0,
                    },
                },
                "decision": "coverage-complete",
                "language-self-check": "所有解释字段均使用简体中文。",
            },
        )
        global_path = (
            self.orchestrate
            / "change-capability-anchors/obligation-atom-index.json"
        )
        write_json(
            global_path,
            {
                "trace-schema": GLOBAL_ATOM_INDEX_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "artifact-path": _repo_path(
                    self.root,
                    global_path.with_suffix(".md"),
                ),
                "global-atoms": [
                    {
                        "global-atom-id": f"GA-{index:04d}",
                        "evidence-ref": _source_ref(index),
                    }
                    for index in range(1, self.ga_count + 1)
                ],
            },
        )

    def _initial_framework_payload(self) -> Dict[str, object]:
        final = self.roadmap

        def initial_capability(row: Dict[str, object]) -> Dict[str, object]:
            return {
                field: copy.deepcopy(row[field])
                for field in (
                    "capability",
                    "purpose",
                    "owns",
                    "excludes",
                    "boundary-rationale",
                )
            } | {"source-hints": ["docs/source.md"]}

        def initial_outcome(row: Dict[str, object]) -> Dict[str, object]:
            return {
                field: copy.deepcopy(row[field])
                for field in (
                    "outcome-thread-id",
                    "beneficiary",
                    "trigger",
                    "observable-result",
                    "acceptance-signal",
                    "primary",
                )
            } | {"source-hints": ["docs/source.md"]}

        def initial_change(row: Dict[str, object]) -> Dict[str, object]:
            return {
                field: copy.deepcopy(row[field])
                for field in (
                    "change",
                    "intent",
                    "scope-in",
                    "scope-out",
                    "behavior-profile",
                    "realizes-outcome-thread-ids",
                    "usable-postcondition",
                    "consumer-closure",
                    "independent-archive",
                    "split-merge-judgment",
                )
            } | {"source-hints": ["docs/source.md"]}

        def initial_dependency(row: Dict[str, object]) -> Dict[str, object]:
            return {
                field: copy.deepcopy(row[field])
                for field in (
                    "dependency-id",
                    "prerequisite-change",
                    "dependent-change",
                    "kind",
                    "contract-id",
                    "produced-contract",
                    "consumed-contract",
                    "counterfactual-failure",
                    "co-delivery-rejection",
                )
            } | {"source-hints": ["docs/source.md"]}

        def initial_guard(row: Dict[str, object]) -> Dict[str, object]:
            return {
                field: copy.deepcopy(row[field])
                for field in (
                    "guard-link-id",
                    "guarding-change",
                    "guarded-outcome-thread-id",
                    "surface-state",
                )
            } | {"source-hints": ["docs/source.md"]}

        foundation = final["foundation"]
        if foundation is not None:
            foundation = {
                "change": foundation["change"],
                "first-consumer-change": foundation[
                    "first-consumer-change"
                ],
                "source-hints": ["docs/source.md"],
            }
        return {
            "trace-schema": INITIAL_FRAMEWORK_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "artifact-path": (
                f"{self.generation_prefix}/phase-works/phase-1/"
                "initial-change-plan.md"
            ),
            "delivery-semantics": [
                {
                    "source-backed-statement": "来源明确要求先报告后通知",
                    "delivery-directive": "explicit-precedence",
                    "affected-outcome-thread-ids": [
                        "reader-gets-report",
                        "reader-gets-notice",
                    ],
                    "planning-effect": "形成候选先后关系",
                    "source-hint": "docs/source.md",
                }
            ],
            "semantic-landscape": [],
            "capabilities": [
                initial_capability(row) for row in final["capabilities"]
            ],
            "outcome-threads": [
                initial_outcome(row) for row in final["outcome-threads"]
            ],
            "changes": [
                initial_change(row) for row in final["changes"]
            ],
            "dependency-edges": [
                initial_dependency(row)
                for row in final["dependency-edges"]
            ],
            "guard-links": [
                initial_guard(row) for row in final["guard-links"]
            ],
            "change-order": copy.deepcopy(final["change-order"]),
            "overlay": [
                {
                    "change": row["change"],
                    "capability": row["capability"],
                }
                for row in final["overlay"]
            ],
            "foundation": foundation,
            "assumptions": [],
            "conflicts": [],
            "non-goals": [],
            "deferred": [],
            "language-self-check": "所有解释字段均使用简体中文。",
        }

    def _write_phase1_framework(self) -> None:
        framework_path = (
            self.orchestrate
            / "phase-works/phase-1/initial-framework.json"
        )
        write_json(framework_path, self._initial_framework_payload())
        plan_path = framework_path.with_name("initial-change-plan.md")
        plan_path.write_text(
            render_initial_framework(self.orchestrate, framework_path),
            encoding="utf-8",
        )
        phase1_dir = framework_path.parent
        (phase1_dir / "source-doc-manifest.md").write_text(
            "\n".join(
                [
                    "# Source Document Manifest",
                    "",
                    (
                        "| Source Document | Read Status | Source Role | "
                        "Coarse Topics / Paths | Notes |"
                    ),
                    "| --- | --- | --- | --- | --- |",
                    (
                        "| `docs/source.md` | `read-full` | `primary` | "
                        "交付结果与边界 | 测试冻结来源 |"
                    ),
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (phase1_dir / "phase-1-agent-report.md").write_text(
            "# Phase 1 Agent Report\n\n初始框架及其review已完成。\n",
            encoding="utf-8",
        )

    def _write_freeze_traces(self) -> None:
        source_path = self.root / "docs/source.md"
        framework_path = (
            self.orchestrate
            / "phase-works/phase-1/initial-framework.json"
        )
        plan_path = framework_path.with_name("initial-change-plan.md")
        phase1_review = write_review_result(
            self.orchestrate,
            self.root,
            phase="phase-1",
            round_number=1,
            authority={
                "initial-framework-sha256": sha256_file(framework_path),
                "initial-change-plan-sha256": sha256_file(plan_path),
            },
        )
        write_json(
            self.orchestrate / "trace/phase-1.trace.json",
            {
                "trace-schema": PHASE_TRACE_SCHEMAS["phase-1"],
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": "initial-plan-written",
                "source-documents": [
                    {
                        "source-document": "docs/source.md",
                        "read-status": "read-full",
                        "source-role": "primary",
                        "coarse-topics-paths": "交付结果与边界",
                        "notes": "测试冻结来源",
                        "line-count": self.ga_count,
                        "source-sha256": sha256_file(source_path),
                    }
                ],
                "initial-framework": {
                    "artifact-path": _repo_path(
                        self.root,
                        framework_path,
                    ),
                    "sha256": sha256_file(framework_path),
                },
                "initial-change-plan": {
                    "artifact-path": _repo_path(self.root, plan_path),
                    "sha256": sha256_file(plan_path),
                },
                "review-gate": {
                    "status": "passed",
                    "terminal-reason": "none",
                    "writer-id": "phase1-writer",
                    "reviews": [phase1_review],
                    "repairs": [],
                },
            },
        )
        atom_root = (
            self.orchestrate
            / "phase-works/phase-2/source-obligation-atoms"
        )
        atom_path = atom_root / "docs--source.atoms.json"
        work_queue_path = atom_root / "work-queue.md"
        work_queue_path.write_text(
            "\n".join(
                [
                    "# Phase 2 Work Queue",
                    "",
                    "| Batch | Source Documents | Canonical Owner |",
                    "| --- | --- | --- |",
                    (
                        "| `batch-1` | `docs/source.md` | "
                        "`phase2-source-writer` |"
                    ),
                    "",
                ]
            ),
            encoding="utf-8",
        )
        phase2_report_path = (
            self.orchestrate
            / "phase-works/phase-2/phase-2-agent-report.md"
        )
        phase2_report_path.parent.mkdir(parents=True, exist_ok=True)
        phase2_report_path.write_text(
            "# Phase 2 Agent Report\n\n全部来源已完成原子提取。\n",
            encoding="utf-8",
        )
        phase2_trace_path = self.orchestrate / "trace/phase-2.trace.json"
        write_json(
            phase2_trace_path,
            {
                "trace-schema": PHASE_TRACE_SCHEMAS["phase-2"],
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": "source-atoms-written",
                "work-queue-path": _repo_path(
                    self.root,
                    work_queue_path,
                ),
                "sources": [
                    {
                        "source-document": "docs/source.md",
                        "atom-json-path": _repo_path(
                            self.root,
                            atom_path,
                        ),
                        "atom-json-sha256": sha256_file(atom_path),
                        "atom-markdown-path": _repo_path(
                            self.root,
                            atom_path.with_suffix(".md"),
                        ),
                        "canonical-owner": "phase2-source-writer",
                        "read-status": "read-full",
                        "atom-count": self.ga_count,
                        "delivery-directive-atom-count": 1,
                        "blockers": [],
                    }
                ],
                "phase-report-path": _repo_path(
                    self.root,
                    phase2_report_path,
                ),
            },
        )
        atom_path.with_suffix(".md").write_text(
            render_phase2_source_atoms(self.orchestrate, atom_path),
            encoding="utf-8",
        )
        (atom_root / "index.md").write_text(
            render_phase2_index(self.orchestrate),
            encoding="utf-8",
        )
        global_path = (
            self.orchestrate
            / "change-capability-anchors/obligation-atom-index.json"
        )
        coverage_path = (
            self.orchestrate
            / "phase-works/phase-3/coverage-review.json"
        )
        global_path.with_suffix(".md").write_text(
            render_global_index(self.orchestrate, global_path),
            encoding="utf-8",
        )
        coverage_path.with_suffix(".md").write_text(
            render_coverage_review(self.orchestrate, coverage_path),
            encoding="utf-8",
        )
        evidence_digest = evidence_authority_sha256(
            self.orchestrate,
            self.root,
        )
        phase3_review = write_review_result(
            self.orchestrate,
            self.root,
            phase="phase-3",
            round_number=1,
            authority={
                "evidence-authority-sha256": evidence_digest,
            },
        )
        write_json(
            self.orchestrate / "trace/phase-3.trace.json",
            {
                "trace-schema": PHASE_TRACE_SCHEMAS["phase-3"],
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "decision": "coverage-complete",
                "global-atom-index-path": _repo_path(
                    self.root,
                    global_path,
                ),
                "global-atom-index-sha256": sha256_file(global_path),
                "coverage-review-path": _repo_path(
                    self.root,
                    coverage_path,
                ),
                "coverage-review-sha256": sha256_file(coverage_path),
                "review-gate": {
                    "status": "passed",
                    "terminal-reason": "none",
                    "phase-2-canonical-owner-ids": [
                        "phase2-source-writer"
                    ],
                    "phase-2-aggregate-writer-id": (
                        "phase2-aggregate-writer"
                    ),
                    "phase-3-writer-id": "phase3-writer",
                    "reviews": [phase3_review],
                    "repairs": [],
                },
                "issues": [],
            },
        )

    def _framework_refit_payload(self) -> Dict[str, object]:
        initial_path = (
            self.orchestrate
            / "phase-works/phase-1/initial-framework.json"
        )
        final_path = self.work / "final-roadmap.json"
        capability_support = {
            "report-delivery": "GA-0001",
            "audit-delivery": "GA-0002",
        }
        change_support = {
            "establish-base": "GA-0007",
            "ship-report": "GA-0001",
            "notify-reader": "GA-0003",
        }
        return {
            "trace-schema": FRAMEWORK_REFIT_TRACE_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "accepted",
            "initial-framework-ref": {
                "artifact-path": _repo_path(self.root, initial_path),
                "sha256": sha256_file(initial_path),
            },
            "final-roadmap-ref": {
                "artifact-path": _repo_path(self.root, final_path),
                "sha256": sha256_file(final_path),
            },
            "capability-reviews": [
                {
                    "input-capability": capability,
                    "decision": "keep",
                    "final-capabilities": [capability],
                    "initial-gate-results": _gate_rows(
                        CAPABILITY_GATE_NAMES,
                        capability_support[capability],
                    ),
                    "supporting-global-atom-ids": [
                        capability_support[capability]
                    ],
                    "reason": "冻结证据支持保持该稳定Capability边界。",
                }
                for capability in sorted(capability_support)
                if any(
                    row["capability"] == capability
                    for row in self.roadmap["capabilities"]
                )
            ],
            "change-reviews": [
                {
                    "input-change": change,
                    "decision": "keep",
                    "final-changes": [change],
                    "initial-gate-results": _gate_rows(
                        CHANGE_GATE_NAMES,
                        change_support[change],
                    ),
                    "supporting-global-atom-ids": [
                        change_support[change]
                    ],
                    "reason": "冻结证据支持保持该可验收Change边界。",
                }
                for change in sorted(change_support)
                if change in self.roadmap["change-order"]
            ],
            "outcome-thread-reviews": [
                {
                    "outcome-thread-id": row["outcome-thread-id"],
                    "result": "passed",
                    "evidence-ga-ids": row["outcome-ga-ids"],
                    "reason": "结果线程具有受益者、触发和可观察验收。",
                }
                for row in self.roadmap["outcome-threads"]
            ],
            "dependency-edge-reviews": [
                {
                    "dependency-id": row["dependency-id"],
                    "result": "passed",
                    "evidence-ga-ids": row["evidence-ga-ids"],
                    "reason": "依赖具有独立产出、消费与反事实证明。",
                }
                for row in self.roadmap["dependency-edges"]
            ],
            "guard-link-reviews": [
                {
                    "guard-link-id": row["guard-link-id"],
                    "result": "passed",
                    "evidence-ga-ids": row["evidence-ga-ids"],
                    "reason": "守卫与受保护结果保持共同交付。",
                }
                for row in self.roadmap["guard-links"]
            ],
            "issues": [],
            "language-self-check": "所有判断和理由均使用简体中文。",
        }

    def _write_phase5_authority(self) -> None:
        write_json(self.work / "final-roadmap.json", self.roadmap)
        write_json(
            self.work / "atom-plan-mapping.json",
            {
                "trace-schema": ATOM_PLAN_MAPPING_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "artifact-path": (
                    f"{self.generation_prefix}/phase-works/phase-5/"
                    "atom-plan-mapping.md"
                ),
                "rows": self.mapping_rows,
            },
        )
        write_json(
            self.work / "framework-refit-trace.json",
            self._framework_refit_payload(),
        )
        report = self.work / "phase-5-agent-report.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("Phase 5 writer已完成候选authority。\n", encoding="utf-8")

    def prepare(self) -> None:
        phase5.prepare_review(self.orchestrate, "phase5-writer")

    def pass_review(self) -> None:
        plan_text = (self.work / "change-plan.md").read_text(
            encoding="utf-8"
        )
        digests = phase5.phase5_candidate_authority(
            self.orchestrate,
            plan_text,
        )
        trace_path = self.orchestrate / "trace/phase-5.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        review = write_review_result(
            self.orchestrate,
            self.root,
            phase="phase-5",
            round_number=1,
            reviewer_id="phase5-reviewer",
            authority=digests,
        )
        trace["review-gate"] = {
            "status": "passed",
            "terminal-reason": "none",
            "writer-id": "phase5-writer",
            "reviews": [review],
            "repairs": [],
        }
        write_json(trace_path, trace)

    def publish(self) -> None:
        self.prepare()
        self.pass_review()
        phase5.write_outputs(self.orchestrate)

    def path(self, relative: str) -> Path:
        return self.root / relative

    def anchor(self, change: str, *parts: str) -> Path:
        return (
            self.orchestrate
            / "change-capability-anchors"
            / change
            / Path(*parts)
        )

    def packet(self) -> Dict[str, object]:
        return json.loads(
            (self.work / "final-packet-index.json").read_text(
                encoding="utf-8"
            )
        )


class Phase5PublicHandoffTests(unittest.TestCase):
    def test_explicit_alternate_generation_root_uses_repository_root(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(
                Path(raw),
                generation_name="orchestrate-alt",
            )
            self.assertEqual(
                phase5.repo_root_for(fixture.orchestrate),
                fixture.root,
            )
            fixture.publish()
            packet = fixture.packet()
            self.assertTrue(
                all(
                    str(row["change-source-path"]).startswith(
                        "openspec/orchestrate-alt/"
                    )
                    for row in packet["packets"]
                )
            )
            phase5.validate_outputs(fixture.orchestrate)

    def test_changes_array_order_is_ignored_in_favor_of_change_order(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            roadmap_path = fixture.work / "final-roadmap.json"
            roadmap = json.loads(roadmap_path.read_text(encoding="utf-8"))
            roadmap["changes"] = list(reversed(roadmap["changes"]))
            roadmap["semantic-landscape"] = [
                {
                    "semantic-area": "报告交付",
                    "source-backed-understanding": "读者需要可读取报告",
                    "planning-relevance": "决定首个可观察结果",
                    "evidence-ga-ids": ["GA-0001"],
                }
            ]
            write_json(roadmap_path, roadmap)
            refit_path = fixture.work / "framework-refit-trace.json"
            refit = json.loads(refit_path.read_text(encoding="utf-8"))
            refit["final-roadmap-ref"]["sha256"] = sha256_file(
                roadmap_path
            )
            write_json(refit_path, refit)

            fixture.publish()

            packet = fixture.packet()
            self.assertEqual(
                [row["change"] for row in packet["packets"]],
                ["ship-report", "notify-reader"],
            )
            root_plan = (
                fixture.orchestrate / "change-plan.md"
            ).read_text(encoding="utf-8")
            self.assertLess(
                root_plan.index("### 1. `ship-report`"),
                root_plan.index("### 2. `notify-reader`"),
            )
            self.assertIn(
                "| 报告交付 | 读者需要可读取报告 | "
                "决定首个可观察结果 | GA-0001 |",
                root_plan,
            )
            self.assertNotIn(
                "| 报告交付 | 读者需要可读取报告 | "
                "决定首个可观察结果 | None |",
                root_plan,
            )

    def test_owner_scoped_sources_direct_slices_and_packet_v3(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.publish()

            ship_source_path = fixture.anchor(
                "ship-report", "change-source.md"
            )
            ship_slice_path = fixture.anchor(
                "ship-report",
                "capability-slices",
                "report-delivery.md",
            )
            notify_source_path = fixture.anchor(
                "notify-reader", "change-source.md"
            )
            notify_slice_path = fixture.anchor(
                "notify-reader",
                "capability-slices",
                "report-delivery.md",
            )
            ship_source = ship_source_path.read_text(encoding="utf-8")
            ship_slice = ship_slice_path.read_text(encoding="utf-8")
            notify_source = notify_source_path.read_text(encoding="utf-8")
            notify_slice = notify_slice_path.read_text(encoding="utf-8")
            packet = fixture.packet()

            self.assertEqual(ship_source.count(REPEATED_SOURCE), 2)
            self.assertEqual(ship_slice.count(REPEATED_SOURCE), 2)
            self.assertIn(CONTEXT_SOURCE, notify_source)
            self.assertNotIn(CONTEXT_SOURCE, notify_slice)
            self.assertIn(DEPENDENCY_SOURCE, notify_source)
            self.assertNotIn(DEPENDENCY_SOURCE, notify_slice)
            self.assertNotIn("GA-", ship_source)
            self.assertNotIn("evidence-ref", ship_slice)

            self.assertEqual(
                packet["trace-schema"],
                "source-aligned-final-packet-index-v3",
            )
            self.assertEqual(
                packet["trace-contract-version"],
                TRACE_CONTRACT_VERSION,
            )
            self.assertEqual(
                [row["change"] for row in packet["packets"]],
                ["ship-report", "notify-reader"],
            )
            self.assertEqual(packet["packets"][0]["depends-on"], [])
            self.assertEqual(
                packet["packets"][1]["depends-on"],
                ["ship-report"],
            )
            for row in packet["packets"]:
                source = fixture.root / row["change-source-path"]
                self.assertEqual(row["change-source-sha256"], sha256_file(source))
                for cap_slice in row["capability-slices"]:
                    slice_path = fixture.root / cap_slice["slice-path"]
                    self.assertEqual(
                        cap_slice["slice-sha256"],
                        sha256_file(slice_path),
                    )
            phase5.validate_outputs(fixture.orchestrate)

    def test_owner_change_moves_only_the_non_direct_occurrence(self) -> None:
        with tempfile.TemporaryDirectory() as left_raw, tempfile.TemporaryDirectory() as right_raw:
            before = V8HandoffFixture(Path(left_raw))
            after = V8HandoffFixture(
                Path(right_raw),
                dependency_owner="ship-report",
            )
            before.publish()
            after.publish()

            before_ship = before.anchor(
                "ship-report", "change-source.md"
            ).read_text(encoding="utf-8")
            after_ship = after.anchor(
                "ship-report", "change-source.md"
            ).read_text(encoding="utf-8")
            before_notify = before.anchor(
                "notify-reader", "change-source.md"
            ).read_text(encoding="utf-8")
            after_notify = after.anchor(
                "notify-reader", "change-source.md"
            ).read_text(encoding="utf-8")
            before_slice = before.anchor(
                "notify-reader",
                "capability-slices",
                "report-delivery.md",
            ).read_bytes()
            after_slice = after.anchor(
                "notify-reader",
                "capability-slices",
                "report-delivery.md",
            ).read_bytes()

            self.assertNotIn(DEPENDENCY_SOURCE, before_ship)
            self.assertIn(DEPENDENCY_SOURCE, after_ship)
            self.assertIn(DEPENDENCY_SOURCE, before_notify)
            self.assertNotIn(DEPENDENCY_SOURCE, after_notify)
            self.assertEqual(before_slice, after_slice)

    def test_target_capability_moves_only_the_direct_slice_occurrence(self) -> None:
        with tempfile.TemporaryDirectory() as left_raw, tempfile.TemporaryDirectory() as right_raw:
            before = V8HandoffFixture(
                Path(left_raw),
                include_audit_capability=True,
            )
            after = V8HandoffFixture(
                Path(right_raw),
                include_audit_capability=True,
                second_target="audit-delivery",
            )
            before.publish()
            after.publish()

            before_source = before.anchor(
                "ship-report", "change-source.md"
            ).read_bytes()
            after_source = after.anchor(
                "ship-report", "change-source.md"
            ).read_bytes()
            before_report = before.anchor(
                "ship-report",
                "capability-slices",
                "report-delivery.md",
            ).read_text(encoding="utf-8")
            after_report = after.anchor(
                "ship-report",
                "capability-slices",
                "report-delivery.md",
            ).read_text(encoding="utf-8")
            after_audit = after.anchor(
                "ship-report",
                "capability-slices",
                "audit-delivery.md",
            ).read_text(encoding="utf-8")
            before_notify = before.anchor(
                "notify-reader",
                "capability-slices",
                "report-delivery.md",
            ).read_bytes()
            after_notify = after.anchor(
                "notify-reader",
                "capability-slices",
                "report-delivery.md",
            ).read_bytes()

            self.assertEqual(before_source, after_source)
            self.assertEqual(before_report.count(REPEATED_SOURCE), 2)
            self.assertEqual(after_report.count(REPEATED_SOURCE), 1)
            self.assertEqual(after_audit.count(REPEATED_SOURCE), 1)
            self.assertEqual(before_notify, after_notify)

    def test_ordinary_empty_slice_is_rejected_and_foundation_empty_slice_passes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            ordinary = V8HandoffFixture(Path(raw))
            roadmap_path = ordinary.work / "final-roadmap.json"
            roadmap = json.loads(roadmap_path.read_text(encoding="utf-8"))
            roadmap["overlay"] = [
                row
                for row in roadmap["overlay"]
                if row["change"] != "notify-reader"
            ]
            write_json(roadmap_path, roadmap)
            refit_path = ordinary.work / "framework-refit-trace.json"
            refit = json.loads(refit_path.read_text(encoding="utf-8"))
            refit["final-roadmap-ref"]["sha256"] = sha256_file(roadmap_path)
            write_json(refit_path, refit)
            with self.assertRaisesRegex(
                ValueError,
                "推进至少一个Capability",
            ):
                ordinary.prepare()
            self.assertFalse((ordinary.orchestrate / "change-plan.md").exists())

        with tempfile.TemporaryDirectory() as raw:
            foundation = V8HandoffFixture(Path(raw), foundation=True)
            foundation.publish()
            packet = foundation.packet()
            first = packet["packets"][0]
            self.assertEqual(first["change"], "establish-base")
            self.assertEqual(first["depends-on"], [])
            self.assertEqual(first["capability-slices"], [])
            slice_dir = foundation.anchor(
                "establish-base",
                "capability-slices",
            )
            self.assertTrue(slice_dir.is_dir())
            self.assertEqual(list(slice_dir.iterdir()), [])
            phase5.validate_outputs(foundation.orchestrate)


class Phase5ReviewAndTamperTests(unittest.TestCase):
    def test_prepare_rejects_orphan_public_anchor_without_mutation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            orphan = (
                fixture.orchestrate
                / "change-capability-anchors/stale-change/owned.md"
            )
            orphan.parent.mkdir(parents=True)
            orphan.write_text("不得覆盖的旧公开文件\n", encoding="utf-8")
            before = orphan.read_bytes()

            with self.assertRaisesRegex(
                ValueError,
                "clean generation.*published surface",
            ):
                fixture.prepare()

            self.assertEqual(orphan.read_bytes(), before)
            self.assertFalse(
                (fixture.orchestrate / "trace/phase-5.trace.json").exists()
            )

    def test_write_rejects_orphan_public_anchor_without_mutation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.prepare()
            fixture.pass_review()
            orphan = (
                fixture.orchestrate
                / "change-capability-anchors/stale-change/owned.md"
            )
            orphan.parent.mkdir(parents=True)
            orphan.write_text("review后注入的旧公开文件\n", encoding="utf-8")
            before = orphan.read_bytes()
            trace_path = fixture.orchestrate / "trace/phase-5.trace.json"
            before_trace = trace_path.read_bytes()

            with self.assertRaisesRegex(
                ValueError,
                "拒绝覆盖或删除既有published surface",
            ):
                phase5.write_outputs(fixture.orchestrate)

            self.assertEqual(orphan.read_bytes(), before)
            self.assertEqual(trace_path.read_bytes(), before_trace)
            self.assertFalse(
                (fixture.orchestrate / "change-plan.md").exists()
            )

    def test_passed_review_is_invalidated_by_source_atom_or_freeze_drift(
        self,
    ) -> None:
        mutations = (
            (
                "source",
                lambda fixture: (
                    fixture.root / "docs/source.md"
                ).write_text("未经review的新来源。\n", encoding="utf-8"),
                "Phase 2 atom source/owner/rows非法",
            ),
            (
                "atom",
                lambda fixture: self._mutate_atom_source_fact(fixture),
                "Phase 2 trace未绑定当前atom authority",
            ),
            (
                "phase3",
                lambda fixture: self._mutate_phase3_trace(fixture),
                "terminal Phase 3 trace字段非法",
            ),
        )
        for label, mutate, message in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                fixture = V8HandoffFixture(Path(raw))
                fixture.prepare()
                fixture.pass_review()
                mutate(fixture)
                with self.assertRaisesRegex(ValueError, message):
                    phase5.write_outputs(fixture.orchestrate)
                self.assertFalse(
                    (fixture.orchestrate / "change-plan.md").exists()
                )
                self.assertFalse(
                    (fixture.work / "final-packet-index.json").exists()
                )

    @staticmethod
    def _mutate_atom_source_fact(fixture: V8HandoffFixture) -> None:
        atom_path = (
            fixture.orchestrate
            / "phase-works/phase-2/source-obligation-atoms/"
            "docs--source.atoms.json"
        )
        atom = json.loads(atom_path.read_text(encoding="utf-8"))
        atom["source-atoms"][0]["source-fact"] = "未经review的新atom原文"
        write_json(atom_path, atom)

    @staticmethod
    def _mutate_phase3_trace(fixture: V8HandoffFixture) -> None:
        trace_path = fixture.orchestrate / "trace/phase-3.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["unexpected"] = "drift"
        write_json(trace_path, trace)

    def test_prepare_requires_terminal_phase3_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            (
                fixture.orchestrate / "trace/phase-3.trace.json"
            ).unlink()
            with self.assertRaises(FileNotFoundError):
                fixture.prepare()
            self.assertFalse((fixture.work / "change-plan.md").exists())
            self.assertFalse(
                (fixture.work / "plan-refit-review.md").exists()
            )

    def test_pending_never_publishes_and_passed_gate_publishes_atomically(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.prepare()
            root_plan = fixture.orchestrate / "change-plan.md"
            packet = fixture.work / "final-packet-index.json"
            candidate_trace = (
                fixture.orchestrate / "trace/phase-5.trace.json"
            ).read_bytes()
            self.assertTrue(
                (fixture.work / "plan-refit-review.md").is_file()
            )
            self.assertFalse(root_plan.exists())
            self.assertFalse(packet.exists())
            with self.assertRaisesRegex(ValueError, "尚未passed"):
                phase5.write_outputs(fixture.orchestrate)
            self.assertFalse(root_plan.exists())
            self.assertFalse(packet.exists())

            fixture.pass_review()
            passed_candidate_trace = (
                fixture.orchestrate / "trace/phase-5.trace.json"
            ).read_bytes()
            with mock.patch.object(
                phase5,
                "validate_outputs",
                side_effect=ValueError("注入发布后自检失败"),
            ):
                with self.assertRaisesRegex(ValueError, "注入发布后自检失败"):
                    phase5.write_outputs(fixture.orchestrate)
            self.assertFalse(root_plan.exists())
            self.assertFalse(packet.exists())
            self.assertEqual(
                (
                    fixture.orchestrate / "trace/phase-5.trace.json"
                ).read_bytes(),
                passed_candidate_trace,
            )
            self.assertNotEqual(candidate_trace, passed_candidate_trace)

            phase5.write_outputs(fixture.orchestrate)
            self.assertTrue(root_plan.is_file())
            self.assertTrue(packet.is_file())
            phase5.validate_outputs(fixture.orchestrate)

    def _assert_tamper_rejected(self, kind: str) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.publish()
            packet_path = fixture.work / "final-packet-index.json"
            trace_path = fixture.orchestrate / "trace/phase-5.trace.json"

            if kind == "source":
                path = fixture.anchor("ship-report", "change-source.md")
                path.write_text(
                    path.read_text(encoding="utf-8") + "篡改\n",
                    encoding="utf-8",
                )
            elif kind == "slice":
                path = fixture.anchor(
                    "ship-report",
                    "capability-slices",
                    "report-delivery.md",
                )
                path.write_text(
                    path.read_text(encoding="utf-8") + "篡改\n",
                    encoding="utf-8",
                )
            elif kind == "root-plan":
                path = fixture.orchestrate / "change-plan.md"
                path.write_text(
                    path.read_text(encoding="utf-8") + "篡改\n",
                    encoding="utf-8",
                )
            else:
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                if kind == "packet":
                    packet["unexpected"] = True
                elif kind == "dependency":
                    packet["packets"][1]["depends-on"] = []
                elif kind == "path":
                    packet["packets"][0][
                        "change-source-path"
                    ] = "openspec/orchestrate/wrong.md"
                elif kind == "digest":
                    packet["packets"][0]["change-source-sha256"] = "0" * 64
                else:
                    raise AssertionError(kind)
                write_json(packet_path, packet)
                trace = json.loads(trace_path.read_text(encoding="utf-8"))
                trace["final-packet-index-sha256"] = sha256_file(packet_path)
                write_json(trace_path, trace)

            with self.assertRaises(ValueError, msg=kind):
                phase5.validate_outputs(fixture.orchestrate)

    def test_source_slice_packet_root_dependency_path_and_digest_tamper_fail(
        self,
    ) -> None:
        for kind in (
            "source",
            "slice",
            "packet",
            "root-plan",
            "dependency",
            "path",
            "digest",
        ):
            with self.subTest(kind=kind):
                self._assert_tamper_rejected(kind)

    def test_every_terminal_trace_reference_path_and_digest_is_checked(
        self,
    ) -> None:
        prefixes = (
            "final-roadmap",
            "final-change-plan",
            "framework-refit-trace",
            "plan-refit-review",
            "atom-plan-mapping",
            "capability-baseline-reconciliation",
            "final-packet-index",
        )
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.publish()
            trace_path = fixture.orchestrate / "trace/phase-5.trace.json"
            original = json.loads(trace_path.read_text(encoding="utf-8"))
            for prefix in prefixes:
                for suffix, value in (
                    ("path", "openspec/orchestrate/wrong.md"),
                    ("sha256", "0" * 64),
                ):
                    with self.subTest(prefix=prefix, suffix=suffix):
                        tampered = copy.deepcopy(original)
                        tampered[f"{prefix}-{suffix}"] = value
                        write_json(trace_path, tampered)
                        with self.assertRaisesRegex(
                            ValueError,
                            f"{prefix} .*drift",
                        ):
                            phase5.validate_outputs(fixture.orchestrate)
                        write_json(trace_path, original)


class Phase5RefitIntegrityTests(unittest.TestCase):
    @staticmethod
    def _load_refit(fixture: V8HandoffFixture) -> Dict[str, object]:
        return json.loads(
            (
                fixture.work / "framework-refit-trace.json"
            ).read_text(encoding="utf-8")
        )

    @staticmethod
    def _validate_refit(
        fixture: V8HandoffFixture,
        refit: Dict[str, object],
    ) -> None:
        write_json(fixture.work / "framework-refit-trace.json", refit)
        phase5.validate_framework_refit(fixture.orchestrate, refit)

    def test_final_change_lineage_must_be_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            refit = self._load_refit(fixture)
            refit["status"] = "adjusted"
            notify = next(
                row
                for row in refit["change-reviews"]
                if row["input-change"] == "notify-reader"
            )
            notify["decision"] = "rename"
            notify["final-changes"] = ["ship-report"]
            notify["initial-gate-results"] = _gate_rows(
                CHANGE_GATE_NAMES,
                "GA-0001",
            )
            notify["supporting-global-atom-ids"] = ["GA-0001"]
            with self.assertRaisesRegex(
                ValueError,
                "final Change缺少refit lineage：notify-reader",
            ):
                self._validate_refit(fixture, refit)

        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(
                Path(raw),
                include_audit_capability=True,
            )
            refit = self._load_refit(fixture)
            refit["status"] = "adjusted"
            audit = next(
                row
                for row in refit["capability-reviews"]
                if row["input-capability"] == "audit-delivery"
            )
            audit["decision"] = "rename"
            audit["final-capabilities"] = ["report-delivery"]
            audit["initial-gate-results"] = _gate_rows(
                CAPABILITY_GATE_NAMES,
                "GA-0001",
            )
            audit["supporting-global-atom-ids"] = ["GA-0001"]
            with self.assertRaisesRegex(
                ValueError,
                "final Capability缺少refit lineage：audit-delivery",
            ):
                self._validate_refit(fixture, refit)

    def test_merge_requires_two_initial_claimants(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            refit = self._load_refit(fixture)
            refit["status"] = "adjusted"
            ship = next(
                row
                for row in refit["change-reviews"]
                if row["input-change"] == "ship-report"
            )
            ship["decision"] = "merge"
            with self.assertRaisesRegex(
                ValueError,
                "merge必须至少由两个initial Change共同指向",
            ):
                self._validate_refit(fixture, refit)

        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            refit = self._load_refit(fixture)
            refit["status"] = "adjusted"
            capability = refit["capability-reviews"][0]
            capability["decision"] = "merge"
            with self.assertRaisesRegex(
                ValueError,
                "merge必须至少由两个initial Capability共同指向",
            ):
                self._validate_refit(fixture, refit)

    def test_incompatible_duplicate_final_claim_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            refit = self._load_refit(fixture)
            refit["status"] = "adjusted"
            ship = next(
                row
                for row in refit["change-reviews"]
                if row["input-change"] == "ship-report"
            )
            ship["decision"] = "split"
            ship["final-changes"] = [
                "ship-report",
                "notify-reader",
            ]
            with self.assertRaisesRegex(
                ValueError,
                "不兼容的重复认领",
            ):
                self._validate_refit(fixture, refit)

    def test_scope_adjusted_requires_real_boundary_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            refit = self._load_refit(fixture)
            refit["status"] = "adjusted"
            ship = next(
                row
                for row in refit["change-reviews"]
                if row["input-change"] == "ship-report"
            )
            ship["decision"] = "scope-adjusted"
            with self.assertRaisesRegex(
                ValueError,
                "scope-adjusted要求真实",
            ):
                self._validate_refit(fixture, refit)

    def test_keep_cannot_be_stamped_with_unrelated_ga(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            refit = self._load_refit(fixture)
            capability = refit["capability-reviews"][0]
            capability["initial-gate-results"] = _gate_rows(
                CAPABILITY_GATE_NAMES,
                "GA-0005",
            )
            capability["supporting-global-atom-ids"] = ["GA-0005"]
            with self.assertRaisesRegex(
                ValueError,
                "与被审单元无关",
            ):
                self._validate_refit(fixture, refit)

    def test_final_outcome_dependency_and_guard_reviews_are_unit_scoped(
        self,
    ) -> None:
        mutations = (
            ("outcome-thread-reviews", "GA-0005"),
            ("dependency-edge-reviews", "GA-0001"),
        )
        for field, unrelated_ga in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as raw:
                fixture = V8HandoffFixture(Path(raw))
                refit = self._load_refit(fixture)
                self.assertTrue(refit[field])
                refit[field][0]["evidence-ga-ids"] = [unrelated_ga]
                with self.assertRaisesRegex(
                    ValueError,
                    "自身的终态evidence",
                ):
                    self._validate_refit(fixture, refit)

        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw), include_guard=True)
            refit = self._load_refit(fixture)
            refit["guard-link-reviews"][0]["evidence-ga-ids"] = [
                "GA-0001"
            ]
            with self.assertRaisesRegex(
                ValueError,
                "自身的终态evidence",
            ):
                self._validate_refit(fixture, refit)

        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            refit = self._load_refit(fixture)
            capability = refit["capability-reviews"][0]
            capability["supporting-global-atom-ids"] = ["GA-0005"]
            with self.assertRaisesRegex(
                ValueError,
                "supporting-global-atom-ids包含与被审单元无关",
            ):
                self._validate_refit(fixture, refit)

        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            refit = self._load_refit(fixture)
            ship = next(
                row
                for row in refit["change-reviews"]
                if row["input-change"] == "ship-report"
            )
            ship["initial-gate-results"] = _gate_rows(
                CHANGE_GATE_NAMES,
                "GA-0006",
            )
            ship["supporting-global-atom-ids"] = ["GA-0006"]
            with self.assertRaisesRegex(
                ValueError,
                "与被审单元无关",
            ):
                self._validate_refit(fixture, refit)


class Phase5ReviewRefreshTests(unittest.TestCase):
    @staticmethod
    def _failed_review(
        fixture: V8HandoffFixture,
        digests: Dict[str, str],
        *,
        round_number: int = 1,
    ) -> Dict[str, object]:
        return write_review_result(
            fixture.orchestrate,
            fixture.root,
            phase="phase-5",
            round_number=round_number,
            decision="repair-required",
            authority=digests,
        )

    @staticmethod
    def _stage_semantic_repair(
        fixture: V8HandoffFixture,
    ) -> Dict[str, str]:
        plan_path = fixture.work / "change-plan.md"
        old_plan = plan_path.read_text(encoding="utf-8")
        old_digests = phase5.phase5_candidate_authority(
            fixture.orchestrate,
            old_plan,
        )
        trace_path = fixture.orchestrate / "trace/phase-5.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["review-gate"]["reviews"] = [
            Phase5ReviewRefreshTests._failed_review(
                fixture,
                old_digests,
            )
        ]

        roadmap_path = fixture.work / "final-roadmap.json"
        roadmap = json.loads(roadmap_path.read_text(encoding="utf-8"))
        roadmap["semantic-landscape"] = [
            {
                "semantic-area": "报告交付",
                "source-backed-understanding": "修复后的冻结事实摘要",
                "planning-relevance": "重新绑定最终候选计划",
                "evidence-ga-ids": ["GA-0001"],
            }
        ]
        write_json(roadmap_path, roadmap)
        refit_path = fixture.work / "framework-refit-trace.json"
        refit = json.loads(refit_path.read_text(encoding="utf-8"))
        refit["final-roadmap-ref"]["sha256"] = sha256_file(
            roadmap_path
        )
        write_json(refit_path, refit)
        evidence = phase5.load_evidence(fixture.orchestrate)
        final, changes, capabilities, overlay = (
            phase5.load_final_roadmap_defs(
                fixture.orchestrate,
                evidence,
            )
        )
        repaired_plan = phase5.render_final_plan_from_roadmap(
            final,
            changes,
            capabilities,
            overlay,
        )
        repaired_digests = phase5.phase5_candidate_authority(
            fixture.orchestrate,
            repaired_plan,
        )
        trace["review-gate"]["repairs"] = [
            {
                "round": 1,
                "repair-writer-id": "phase5-repair-writer",
                "source-review-result-sha256": (
                    trace["review-gate"]["reviews"][0][
                        "review-result-sha256"
                    ]
                ),
                "before-terminal-authority-sha256": (
                    phase5.phase5_candidate_authority_sha256(
                        old_digests
                    )
                ),
                "after-terminal-authority-sha256": (
                    phase5.phase5_candidate_authority_sha256(
                        repaired_digests
                    )
                ),
            }
        ]
        write_json(trace_path, trace)
        return repaired_digests

    def test_refresh_cli_preserves_history_and_rebinds_full_candidate(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.prepare()
            repaired_digests = self._stage_semantic_repair(fixture)

            result = phase5.main(
                [
                    "--orchestrate-dir",
                    str(fixture.orchestrate),
                    "--refresh-review-candidate",
                ]
            )
            self.assertEqual(result, 0)
            trace_path = fixture.orchestrate / "trace/phase-5.trace.json"
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            self.assertEqual(len(trace["review-gate"]["reviews"]), 1)
            self.assertEqual(len(trace["review-gate"]["repairs"]), 1)
            self.assertEqual(
                trace["candidate-final-change-plan-sha256"],
                repaired_digests["final-change-plan-sha256"],
            )
            self.assertIn(
                "修复后的冻结事实摘要",
                (fixture.work / "change-plan.md").read_text(
                    encoding="utf-8"
                ),
            )

            current_plan = (
                fixture.work / "change-plan.md"
            ).read_text(encoding="utf-8")
            current_digests = phase5.phase5_candidate_authority(
                fixture.orchestrate,
                current_plan,
            )
            trace["review-gate"]["status"] = "passed"
            trace["review-gate"]["reviews"].append(
                write_review_result(
                    fixture.orchestrate,
                    fixture.root,
                    phase="phase-5",
                    round_number=2,
                    authority=current_digests,
                )
            )
            write_json(trace_path, trace)
            phase5.write_outputs(fixture.orchestrate)
            phase5.validate_outputs(fixture.orchestrate)

    def test_refresh_rejects_missing_repair_and_rolls_back_on_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.prepare()
            plan = (fixture.work / "change-plan.md").read_text(
                encoding="utf-8"
            )
            digests = phase5.phase5_candidate_authority(
                fixture.orchestrate,
                plan,
            )
            trace_path = fixture.orchestrate / "trace/phase-5.trace.json"
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            trace["review-gate"]["reviews"] = [
                self._failed_review(fixture, digests)
            ]
            write_json(trace_path, trace)
            with self.assertRaisesRegex(ValueError, "完成repair后"):
                phase5.refresh_review_candidate(fixture.orchestrate)

        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.prepare()
            self._stage_semantic_repair(fixture)
            plan_path = fixture.work / "change-plan.md"
            trace_path = fixture.orchestrate / "trace/phase-5.trace.json"
            before_plan = plan_path.read_bytes()
            before_trace = trace_path.read_bytes()
            with mock.patch.object(
                phase5,
                "_load_phase5_review_gate",
                side_effect=ValueError("注入refresh发布后自检失败"),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "注入refresh发布后自检失败",
                ):
                    phase5.refresh_review_candidate(
                        fixture.orchestrate
                    )
            self.assertEqual(plan_path.read_bytes(), before_plan)
            self.assertEqual(trace_path.read_bytes(), before_trace)


class Phase5BlockedPublicationTests(unittest.TestCase):
    @staticmethod
    def _five_round_gate(
        fixture: V8HandoffFixture,
        *,
        status: str,
    ) -> Dict[str, object]:
        current_plan = (
            fixture.work / "change-plan.md"
        ).read_text(encoding="utf-8")
        current = phase5.phase5_candidate_authority(
            fixture.orchestrate,
            current_plan,
        )
        historical = [
            {
                field: digit * 64
                for field in phase5.PHASE5_CANDIDATE_DIGEST_FIELDS
            }
            for digit in ("1", "2", "3", "4")
        ]
        digests = [*historical, current]
        reviews = []
        for index, digest in enumerate(digests, start=1):
            reviews.append(
                write_review_result(
                    fixture.orchestrate,
                    fixture.root,
                    phase="phase-5",
                    round_number=index,
                    decision=(
                        "blocked"
                        if index == 5
                        else "repair-required"
                    ),
                    authority=digest,
                )
            )
        repairs = [
            {
                "round": index,
                "repair-writer-id": f"phase5-repair-writer-{index}",
                "source-review-result-sha256": reviews[index - 1][
                    "review-result-sha256"
                ],
                "before-terminal-authority-sha256": (
                    phase5.phase5_candidate_authority_sha256(
                        digests[index - 1]
                    )
                ),
                "after-terminal-authority-sha256": (
                    phase5.phase5_candidate_authority_sha256(
                        digests[index]
                    )
                ),
            }
            for index in (1, 2, 3, 4)
        ]
        return {
            "status": status,
            "terminal-reason": (
                "budget-exhausted"
                if status == "blocked"
                else "none"
            ),
            "writer-id": "phase5-writer",
            "reviews": reviews,
            "repairs": repairs,
        }

    @classmethod
    def _set_five_round_gate(
        cls,
        fixture: V8HandoffFixture,
        *,
        status: str,
    ) -> Dict[str, object]:
        trace_path = fixture.orchestrate / "trace/phase-5.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["review-gate"] = cls._five_round_gate(
            fixture,
            status=status,
        )
        write_json(trace_path, trace)
        return trace

    @staticmethod
    def _make_blocked_refit(fixture: V8HandoffFixture) -> None:
        refit_path = fixture.work / "framework-refit-trace.json"
        refit = json.loads(refit_path.read_text(encoding="utf-8"))
        refit["status"] = "blocked"
        refit["final-roadmap-ref"] = None
        refit["issues"] = ["冻结证据不足，Phase 5 无法形成终态框架。"]
        write_json(refit_path, refit)

    def test_authority_integrity_is_a_legal_immediate_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.prepare()
            fixture.pass_review()
            trace_path = fixture.orchestrate / "trace/phase-5.trace.json"
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            review_gate = trace["review-gate"]
            review_gate["status"] = "blocked"
            review_gate["terminal-reason"] = "authority-integrity"
            review_gate["reviews"][0]["review-result-sha256"] = "0" * 64
            current_plan = (fixture.work / "change-plan.md").read_text(
                encoding="utf-8"
            )
            current = phase5.phase5_candidate_authority(
                fixture.orchestrate,
                current_plan,
            )

            self.assertEqual(
                phase5.validate_phase5_review_gate(
                    review_gate,
                    orchestrate_dir=fixture.orchestrate,
                    repo_root=fixture.root,
                    current_digests=current,
                ),
                "blocked",
            )

    def test_identity_reuse_is_a_legal_immediate_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.prepare()
            fixture.pass_review()
            trace_path = fixture.orchestrate / "trace/phase-5.trace.json"
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            review_gate = trace["review-gate"]
            result_path = (
                fixture.work / "reviews/review-round-01.json"
            )
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["reviewer-id"] = "phase5-writer"
            write_json(result_path, result)
            review_gate["reviews"][0]["review-result-sha256"] = sha256_file(
                result_path
            )
            review_gate["status"] = "blocked"
            review_gate["terminal-reason"] = "identity-reuse"
            current_plan = (fixture.work / "change-plan.md").read_text(
                encoding="utf-8"
            )
            current = phase5.phase5_candidate_authority(
                fixture.orchestrate,
                current_plan,
            )

            self.assertEqual(
                phase5.validate_phase5_review_gate(
                    review_gate,
                    orchestrate_dir=fixture.orchestrate,
                    repo_root=fixture.root,
                    current_digests=current,
                ),
                "blocked",
            )

    def test_blocked_refuses_to_delete_published_terminal_results(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.publish()
            root_plan = fixture.orchestrate / "change-plan.md"
            packet = fixture.work / "final-packet-index.json"
            before_plan = root_plan.read_bytes()
            before_packet = packet.read_bytes()
            before_trace = (
                fixture.orchestrate / "trace/phase-5.trace.json"
            ).read_bytes()
            self._make_blocked_refit(fixture)

            with self.assertRaisesRegex(
                ValueError,
                "拒绝覆盖或删除既有published surface",
            ):
                phase5.write_outputs(fixture.orchestrate)

            self.assertEqual(root_plan.read_bytes(), before_plan)
            self.assertEqual(packet.read_bytes(), before_packet)
            self.assertEqual(
                (
                    fixture.orchestrate / "trace/phase-5.trace.json"
                ).read_bytes(),
                before_trace,
            )

    def test_blocked_review_and_trace_publish_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            self._make_blocked_refit(fixture)
            (fixture.work / "final-roadmap.json").unlink()
            (fixture.work / "atom-plan-mapping.json").unlink()
            review_path = fixture.work / "plan-refit-review.md"
            trace_path = fixture.orchestrate / "trace/phase-5.trace.json"

            with mock.patch.object(
                phase5,
                "validate_outputs",
                side_effect=ValueError("注入blocked发布后自检失败"),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "注入blocked发布后自检失败",
                ):
                    phase5.write_outputs(fixture.orchestrate)
            self.assertFalse(review_path.exists())
            self.assertFalse(trace_path.exists())

            phase5.write_outputs(fixture.orchestrate)
            self.assertTrue(review_path.is_file())
            self.assertTrue(trace_path.is_file())
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            self.assertEqual(trace["block-kind"], "framework-refit")
            phase5.validate_outputs(fixture.orchestrate)
            reporter = IssueReporter()
            validate_phase_5(
                fixture.orchestrate,
                fixture.root,
                reporter,
            )
            self.assertEqual(reporter.result()["issues"], [])

    def test_failed_fifth_review_cannot_remain_pending(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.prepare()
            review_gate = self._five_round_gate(
                fixture,
                status="pending",
            )
            plan = (fixture.work / "change-plan.md").read_text(
                encoding="utf-8"
            )
            current_digests = phase5.phase5_candidate_authority(
                fixture.orchestrate,
                plan,
            )
            with self.assertRaisesRegex(
                ValueError,
                "第五轮review后不得保持pending",
            ):
                phase5.validate_phase5_review_gate(
                    review_gate,
                    orchestrate_dir=fixture.orchestrate,
                    repo_root=fixture.root,
                    current_digests=current_digests,
                )

    def test_bounded_review_block_publishes_only_canonical_trace(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.prepare()
            self._set_five_round_gate(fixture, status="blocked")

            phase5.write_outputs(fixture.orchestrate)

            trace_path = fixture.orchestrate / "trace/phase-5.trace.json"
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            self.assertEqual(trace["status"], "blocked")
            self.assertEqual(trace["block-kind"], "bounded-review")
            self.assertEqual(trace["review-gate"]["status"], "blocked")
            self.assertTrue(trace["issues"])
            self.assertTrue((fixture.work / "final-roadmap.json").is_file())
            self.assertTrue(
                (fixture.work / "atom-plan-mapping.json").is_file()
            )
            self.assertTrue((fixture.work / "change-plan.md").is_file())
            self.assertFalse(
                (fixture.orchestrate / "change-plan.md").exists()
            )
            self.assertFalse(
                (fixture.work / "final-packet-index.json").exists()
            )
            self.assertFalse(
                (
                    fixture.orchestrate
                    / "change-capability-anchors/index.md"
                ).exists()
            )
            phase5.validate_outputs(fixture.orchestrate)
            reporter = IssueReporter()
            validate_phase_5(
                fixture.orchestrate,
                fixture.root,
                reporter,
            )
            self.assertEqual(reporter.result()["issues"], [])

    def test_bounded_block_rejects_public_surface_and_retry(
        self,
    ) -> None:
        for relative_path in (
            "change-plan.md",
            "trace/workflow-completion.trace.json",
        ):
            with self.subTest(relative_path=relative_path):
                with tempfile.TemporaryDirectory() as raw:
                    fixture = V8HandoffFixture(Path(raw))
                    fixture.prepare()
                    self._set_five_round_gate(
                        fixture,
                        status="blocked",
                    )
                    trace_path = (
                        fixture.orchestrate / "trace/phase-5.trace.json"
                    )
                    before_trace = trace_path.read_bytes()
                    published = fixture.orchestrate / relative_path
                    published.parent.mkdir(parents=True, exist_ok=True)
                    published.write_text(
                        "既有公开结果\n",
                        encoding="utf-8",
                    )

                    with self.assertRaisesRegex(
                        ValueError,
                        "拒绝覆盖或删除既有published surface",
                    ):
                        phase5.write_outputs(fixture.orchestrate)
                    self.assertEqual(
                        published.read_text(encoding="utf-8"),
                        "既有公开结果\n",
                    )
                    self.assertEqual(
                        trace_path.read_bytes(),
                        before_trace,
                    )

        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.prepare()
            self._set_five_round_gate(fixture, status="blocked")
            phase5.write_outputs(fixture.orchestrate)
            trace_path = fixture.orchestrate / "trace/phase-5.trace.json"
            before_trace = trace_path.read_bytes()
            with self.assertRaisesRegex(
                ValueError,
                "review-pending candidate trace",
            ):
                phase5.write_outputs(fixture.orchestrate)
            self.assertEqual(trace_path.read_bytes(), before_trace)

    def test_bounded_block_trace_tamper_and_atomic_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.prepare()
            self._set_five_round_gate(fixture, status="blocked")
            trace_path = fixture.orchestrate / "trace/phase-5.trace.json"
            pending_trace = trace_path.read_bytes()
            with mock.patch.object(
                phase5,
                "validate_outputs",
                side_effect=ValueError("注入bounded blocked自检失败"),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "注入bounded blocked自检失败",
                ):
                    phase5.write_outputs(fixture.orchestrate)
            self.assertEqual(trace_path.read_bytes(), pending_trace)
            self.assertFalse(
                (fixture.orchestrate / "change-plan.md").exists()
            )
            self.assertFalse(
                (fixture.work / "final-packet-index.json").exists()
            )

            phase5.write_outputs(fixture.orchestrate)
            original = json.loads(trace_path.read_text(encoding="utf-8"))
            for field, value in (
                ("final-roadmap-sha256", "0" * 64),
                ("issues", ["篡改后的问题"]),
            ):
                with self.subTest(field=field):
                    tampered = copy.deepcopy(original)
                    tampered[field] = value
                    write_json(trace_path, tampered)
                    with self.assertRaises(ValueError):
                        phase5.validate_outputs(fixture.orchestrate)
                    reporter = IssueReporter()
                    validate_phase_5(
                        fixture.orchestrate,
                        fixture.root,
                        reporter,
                    )
                    self.assertTrue(reporter.result()["issues"])
                    write_json(trace_path, original)


class WorkflowCompletionTests(unittest.TestCase):
    @staticmethod
    def _unit_result(
        id_field: str,
        unit_id: str,
        ga: str,
        *,
        gates: Optional[object] = None,
    ) -> Dict[str, object]:
        row: Dict[str, object] = {
            id_field: unit_id,
            "result": "passed",
            "evidence-ga-ids": [ga],
            "note": "该终态单元已经由冻结证据完整审查。",
        }
        if gates is not None:
            row["gate-results"] = _gate_rows(gates, ga)
        return row

    def _publish_workflow(
        self,
        fixture: V8HandoffFixture,
        *,
        status: str,
    ) -> None:
        digest = terminal_authority_sha256(
            fixture.orchestrate,
            fixture.root,
        )
        reviewed = terminal_authority_payload(
            fixture.orchestrate,
            fixture.root,
        )["artifacts"]
        review = {
            "trace-schema": FINAL_INTEGRATION_REVIEW_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": status,
            "reviewer-id": "fresh-final-integration-reviewer",
            "terminal-authority-sha256": digest,
            "reviewed-artifacts": reviewed,
            "capability-results": [
                self._unit_result(
                    "capability",
                    row["capability"],
                    row["evidence-ga-ids"][0],
                    gates=CAPABILITY_GATE_NAMES,
                )
                for row in fixture.roadmap["capabilities"]
            ],
            "change-results": [
                self._unit_result(
                    "change",
                    change,
                    (
                        "GA-0007"
                        if change == "establish-base"
                        else (
                            "GA-0001"
                            if change == "ship-report"
                            else "GA-0003"
                        )
                    ),
                    gates=CHANGE_GATE_NAMES,
                )
                for change in fixture.roadmap["change-order"]
            ],
            "outcome-thread-results": [
                self._unit_result(
                    "outcome-thread-id",
                    row["outcome-thread-id"],
                    row["outcome-ga-ids"][0],
                )
                for row in fixture.roadmap["outcome-threads"]
            ],
            "dependency-edge-results": [
                self._unit_result(
                    "dependency-id",
                    row["dependency-id"],
                    row["evidence-ga-ids"][0],
                )
                for row in fixture.roadmap["dependency-edges"]
            ],
            "dependency-set-result": {
                "result": "passed",
                "note": "逐Change消费者闭包未发现遗漏的hard dependency边。",
                "evidence-ga-ids": [
                    f"GA-{index:04d}"
                    for index in range(1, fixture.ga_count + 1)
                ],
            },
            "guard-link-results": [
                self._unit_result(
                    "guard-link-id",
                    row["guard-link-id"],
                    row["evidence-ga-ids"][0],
                )
                for row in fixture.roadmap["guard-links"]
            ],
            "occurrence-chain-result": {
                "result": "passed",
                "note": "全部冻结occurrence按global index顺序完成唯一分配。",
                "evidence-ga-ids": [
                    f"GA-{index:04d}"
                    for index in range(1, fixture.ga_count + 1)
                ],
            },
            "findings": (
                [] if status == "passed" else ["存在终态阻断问题"]
            ),
            "language-self-check": "所有审查说明均使用简体中文。",
        }
        review_path = fixture.orchestrate / "final-integration-review.json"
        write_json(review_path, review)
        attempt_path = (
            fixture.orchestrate
            / FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH
        )
        write_json(
            attempt_path,
            {
                "trace-schema": FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": "submitted",
                "final-integration-review-path": _repo_path(
                    fixture.root,
                    review_path,
                ),
                "final-integration-review-sha256": sha256_file(
                    review_path
                ),
            },
        )
        write_json(
            fixture.orchestrate
            / FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH,
            {
                "trace-schema": (
                    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA
                ),
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": (
                    "passed" if status == "passed" else "blocked"
                ),
                "final-integration-review-attempt-path": _repo_path(
                    fixture.root,
                    attempt_path,
                ),
                "final-integration-review-attempt-sha256": sha256_file(
                    attempt_path
                ),
                "terminal-authority-sha256": digest,
                "issues": (
                    [] if status == "passed" else ["存在终态阻断问题"]
                ),
            },
        )
        (
            fixture.orchestrate / "final-integration-review.md"
        ).write_text(
            render_final_integration_review(
                fixture.orchestrate,
                review_path,
            ),
            encoding="utf-8",
        )
        completion_status = (
            "integration-passed" if status == "passed" else "blocked"
        )
        write_json(
            fixture.orchestrate
            / "trace/workflow-completion.trace.json",
            {
                "trace-schema": WORKFLOW_COMPLETION_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": completion_status,
                "terminal-authority-sha256": digest,
                "final-integration-review-path": (
                    "openspec/orchestrate/final-integration-review.json"
                ),
                "final-integration-review-sha256": sha256_file(review_path),
                "issues": (
                    [] if status == "passed" else ["存在终态阻断问题"]
                ),
            },
        )

    def test_complete_requires_integration_and_accepts_bound_completion(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.publish()
            absent = IssueReporter()
            validate_workflow_terminal(
                fixture.orchestrate,
                fixture.root,
                absent,
                required=True,
            )
            self.assertGreater(absent.error_count, 0)

            self._publish_workflow(fixture, status="passed")
            passed = IssueReporter()
            validate_workflow_terminal(
                fixture.orchestrate,
                fixture.root,
                passed,
                required=True,
            )
            self.assertEqual(
                passed.error_count,
                0,
                [item.message for item in passed.issues],
            )

    def test_blocked_completion_is_valid_state_but_cannot_complete(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.publish()
            self._publish_workflow(fixture, status="blocked")

            allowed = IssueReporter()
            validate_workflow_terminal(
                fixture.orchestrate,
                fixture.root,
                allowed,
                required=False,
            )
            self.assertEqual(
                allowed.error_count,
                0,
                [item.message for item in allowed.issues],
            )
            complete = IssueReporter()
            validate_workflow_terminal(
                fixture.orchestrate,
                fixture.root,
                complete,
                required=True,
            )
            self.assertTrue(
                any(
                    item.rule_id == "workflow-complete-required"
                    for item in complete.issues
                )
            )


class HardCutPreservationTests(unittest.TestCase):
    def test_renderer_rejects_legacy_phase4_without_deleting_it(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            orchestrate = Path(raw) / "openspec/orchestrate"
            legacy = (
                orchestrate
                / "phase-works/phase-4/input-change-plan.md"
            )
            legacy.parent.mkdir(parents=True)
            legacy.write_text("legacy-v6-byte-content\n", encoding="utf-8")
            before = legacy.read_bytes()
            with self.assertRaisesRegex(ValueError, "legacy Phase 4"):
                render_orchestrate(
                    orchestrate,
                    "phase4-evidence-collections",
                    write=True,
                )
            self.assertEqual(legacy.read_bytes(), before)

    def test_helper_rejects_legacy_phase5_without_deleting_it(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            fixture.prepare()
            fixture.pass_review()
            legacy = fixture.work / "input-change-plan.md"
            legacy.write_text("legacy-v6-byte-content\n", encoding="utf-8")
            before = legacy.read_bytes()
            with self.assertRaisesRegex(ValueError, "legacy Phase 5"):
                phase5.write_outputs(fixture.orchestrate)
            self.assertEqual(legacy.read_bytes(), before)
            self.assertFalse((fixture.orchestrate / "change-plan.md").exists())
            self.assertFalse(
                (fixture.work / "final-packet-index.json").exists()
            )


if __name__ == "__main__":
    unittest.main()
