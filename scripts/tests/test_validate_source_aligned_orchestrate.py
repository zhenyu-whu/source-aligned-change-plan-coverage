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
sys.path.insert(0, str(SCRIPT_DIR))

from source_aligned_trace_lib import (  # noqa: E402
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_BASELINE_SCHEMA,
    FINAL_PACKET_INDEX_SCHEMA,
    GLOBAL_ATOM_INDEX_SCHEMA,
    MANIFEST_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    SOURCE_TO_GLOBAL_MAP_SCHEMA,
    SOURCE_WINDOW_INDEX_SCHEMA,
    TRACE_CONTRACT_VERSION,
    sha256_file,
    sha256_text,
    write_json,
)
from render_source_aligned_orchestrate import render_orchestrate  # noqa: E402
from validate_source_aligned_orchestrate import validate  # noqa: E402


class SourceAlignedValidatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.orchestrate = self.root / "openspec/orchestrate"
        self.script = SCRIPT_DIR / "validate_source_aligned_orchestrate.py"
        self.refit_script = SCRIPT_DIR / "phase5_plan_refit.py"
        self._build_valid_fixture()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write(self, path: str, text: str) -> Path:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def _source_sha(self) -> str:
        return sha256_file(self.root / "docs/source.md")

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

    def _build_valid_fixture(self) -> None:
        source = "\n".join(f"line {i}" for i in range(1, 21)) + "\n"
        self._write("docs/source.md", source)
        self._write("openspec/orchestrate/phase-works/phase-1/initial-change-plan.md", self._phase1_plan())
        self._write(
            "openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md",
            "| Source Document | Read Status | Source Role | Coarse Topics / Paths | Notes |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| docs/source.md | read-full | main | topic | note |\n",
        )
        self._write("openspec/orchestrate/phase-works/phase-1/phase-1-agent-report.md", "ok\n")
        self._write(
            "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/work-queue.md",
            "| Batch | Source Documents | Canonical Owner |\n"
            "| --- | --- | --- |\n"
            "| B1 | docs/source.md | owner-a |\n",
        )
        self._write(
            "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.md",
            "phase-2 source atoms are rendered from JSON\n",
        )
        self._write("openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/index.md", "index\n")
        self._write("openspec/orchestrate/phase-works/phase-2/phase-2-agent-report.md", "ok\n")
        self._write(
            "openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md",
            "| Source Document | Classification | Phase 2 Atom File | Review File | Effective Atom Ranges | Missing Obligation Atom Ranges | Non-Atom Ranges | Read Scope | Reason |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| docs/source.md | covered-by-atoms | openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.md | openspec/orchestrate/phase-works/phase-3/source-doc-coverage/docs--source.coverage.md | L1-L8 | None | L9-L20 | full-source remainder audit | ok |\n",
        )
        self._write(
            "openspec/orchestrate/phase-works/phase-3/source-doc-coverage/docs--source.coverage.md",
            "| Global Atom ID | Source Atom Origins | Lines | Atom Type | Coverage Status | Artifact Projection | Candidate / Owner Change | Capability Impact | Target Capability | Related Capabilities | Source Fact |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| GA-0001 | atom.spec | L1-L2 | behavior | direct | spec-requirement | change-a | new | cap-a | None | spec fact |\n"
            "| GA-0002 | atom.design | L3-L4 | architecture | direct | design-obligation | change-a | none | none | cap-support | design fact |\n"
            "| GA-0003 | atom.verify | L5-L6 | verification | direct | verification-obligation | change-a | none | none | cap-support | verification fact |\n"
            "| GA-0004 | atom.non-goal | L7-L8 | explicit-non-goal | explicit-non-goal | spec-guard | change-a | none | none | None | non-goal fact |\n"
            "\n"
            "| Source Section or Range | Expected Atom Type | Global Atom IDs | Coverage Judgment | Reason |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| L1-L8 | mixed | GA-0001; GA-0002; GA-0003; GA-0004 | covered | ok |\n"
            "| L9-L20 | none | None | non-atom | safe remainder |\n"
            "\n"
            "| Candidate Range | Read Scope | Semantic Classification | Production Obligation? | Reason |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| L9-L20 | full-source remainder audit | formatting/background | false | no production obligation |\n",
        )
        self._write("openspec/orchestrate/phase-works/phase-3/coverage-review.md", "Decision: coverage-complete\n")
        self._write("openspec/orchestrate/phase-works/phase-3/phase-3-agent-report.md", "ok\n")
        self._write("openspec/orchestrate/phase-works/phase-3/phase-3-trace/duplicate-ownership-review.md", "ok\n")
        self._write("openspec/orchestrate/phase-works/phase-3/phase-3-trace/atom-normalization-decision-log.md", "ok\n")
        self._write("openspec/orchestrate/phase-works/phase-4/input-change-plan.md", self._phase1_plan())
        self._write("openspec/orchestrate/phase-works/phase-4/source-window-dossiers/index.md", "index\n")
        self._write("openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md", "profile\n")
        self._write("openspec/orchestrate/phase-works/phase-4/source-window-grounding-issues.md", "issues\n")
        self._write("openspec/orchestrate/phase-works/phase-4/phase-4-agent-report.md", "Phase 4 Status: grounded\n")
        self._write("openspec/orchestrate/phase-works/phase-5/input-change-plan.md", self._phase1_plan())
        self._write("openspec/orchestrate/phase-works/phase-5/source-window-refit-trace.md", "trace\n")
        self._write("openspec/orchestrate/phase-works/phase-5/change-plan.md", "# Final Plan\n")
        self._write("openspec/orchestrate/change-plan.md", "# Final Plan\n")
        self._write("openspec/orchestrate/phase-works/phase-5/capability-progression-review.md", "progression\n")
        self._write("openspec/orchestrate/phase-works/phase-5/plan-refit-decision-log.md", "decisions\n")
        self._write("openspec/orchestrate/phase-works/phase-5/alignment-final-report.md", "alignment\n")
        self._write("openspec/orchestrate/phase-works/phase-5/change-capability-human-plan.md", "human\n")
        self._write("openspec/orchestrate/phase-works/phase-5/phase-5-agent-report.md", "Phase 5 Status: adjusted\n")
        self._write("openspec/orchestrate/change-capability-anchors/index.md", "index\n")
        self._write(
            "openspec/orchestrate/change-capability-anchors/obligation-atom-index.md",
            "phase-3 global atom index is rendered from JSON\n",
        )
        self._write(
            "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.md",
            "phase-5 atom mapping is rendered from JSON\n",
        )
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/change-a.md",
            "# change-a\n\n## Final Direct Owner Atoms\n\n"
            "| Global Atom ID | Capability Impact | Target Capability | Related Capabilities | Relation |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| GA-0001 | new | cap-a | None | direct |\n"
            "| GA-0002 | none | None/change-only | cap-support | direct |\n"
            "| GA-0003 | none | None/change-only | cap-support | direct |\n\n"
            "## Contextual Atoms\n\n| Global Atom ID | Relation |\n| --- | --- |\n"
            "| GA-0004 | non-goal |\n",
        )
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/capability-anchors/cap-a.md",
            "# cap-a\n\n| Global Atom ID | Relation |\n| --- | --- |\n| GA-0001 | direct |\n",
        )
        self._write(
            "openspec/orchestrate/phase-works/phase-5/change-complexity-review.md",
            "| Change | Direct Atom Count | Budget Status |\n| --- | --- | --- |\n| change-a | 3 | within-target |\n",
        )

        self._write_json_sidecars()

    def _write_json_sidecars(self) -> None:
        source_sha = self._source_sha()
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
                        "source-role": "main",
                        "coarse-topics-paths": "topic",
                        "notes": "note",
                        "line-count": 20,
                        "source-sha256": source_sha,
                    }
                ],
                "initial-change-plan": {
                    "artifact-path": "openspec/orchestrate/phase-works/phase-1/initial-change-plan.md",
                    "sha256": sha256_file(self.orchestrate / "phase-works/phase-1/initial-change-plan.md"),
                },
            },
        )
        source_atoms = [
            {
                "source-atom-id": "atom.spec",
                "line-ranges": [{"start": 1, "end": 2}],
                "atom-type": "behavior",
                "source-fact": "spec fact",
                "normativity": "must",
                "candidate-status": "direct-candidate",
                "candidate-artifact-projection": "spec-requirement",
                "candidate-owner-change": "change-a",
                "candidate-target-capability": "cap-a",
                "rationale": "why",
            },
            {
                "source-atom-id": "atom.design",
                "line-ranges": [{"start": 3, "end": 4}],
                "atom-type": "architecture-runtime",
                "source-fact": "design fact",
                "normativity": "must",
                "candidate-status": "direct-candidate",
                "candidate-artifact-projection": "design-obligation",
                "candidate-owner-change": "change-a",
                "candidate-target-capability": "none",
                "rationale": "source-explicit support for cap-a",
            },
            {
                "source-atom-id": "atom.verify",
                "line-ranges": [{"start": 5, "end": 6}],
                "atom-type": "verification",
                "source-fact": "verification fact",
                "normativity": "must",
                "candidate-status": "direct-candidate",
                "candidate-artifact-projection": "verification-obligation",
                "candidate-owner-change": "change-a",
                "candidate-target-capability": "none",
                "rationale": "source-explicit verification for cap-a",
            },
            {
                "source-atom-id": "atom.non-goal",
                "line-ranges": [{"start": 7, "end": 8}],
                "atom-type": "scope-guard",
                "source-fact": "non-goal fact",
                "normativity": "must-not",
                "candidate-status": "direct-candidate",
                "candidate-artifact-projection": "spec-guard",
                "candidate-owner-change": "change-a",
                "candidate-target-capability": "cap-a",
                "rationale": "why",
            },
        ]
        write_json(
            self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json",
            {
                "trace-schema": SOURCE_ATOMS_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "source-document": "docs/source.md",
                "source-sha256": source_sha,
                "read-status": "read-full",
                "canonical-owner": "owner-a",
                "source-role": "main",
                "phase-1-candidate-changes-capabilities-considered": [
                    {"change": "change-a", "capabilities": ["cap-a"], "note": "现有 framework mapping。"}
                ],
                "source-atoms": source_atoms,
                "section-inventory": [
                    {
                        "source-section": "产品与系统事实",
                        "line-ranges": [{"start": 1, "end": 8}],
                        "production-meaning": "obligation-bearing",
                        "atom-ids": ["atom.spec", "atom.design", "atom.verify", "atom.non-goal"],
                        "non-atom-classification": "none",
                        "reason": "包含可执行、验证和范围约束。",
                    },
                    {
                        "source-section": "背景内容",
                        "line-ranges": [{"start": 9, "end": 20}],
                        "production-meaning": "background",
                        "atom-ids": [],
                        "non-atom-classification": "no-product-or-system-impact",
                        "reason": "不包含产品或系统语义。",
                    },
                ],
                "blockers": [],
                "language-self-check": "解释字段已使用简体中文。",
            },
        )
        write_json(
            self.orchestrate / "trace/phase-2.trace.json",
            {
                "trace-schema": PHASE_TRACE_SCHEMAS["phase-2"],
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": "source-atoms-written",
                "work-queue-path": "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/work-queue.md",
                "sources": [
                    {
                        "source-document": "docs/source.md",
                        "atom-json-path": "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json",
                        "atom-json-sha256": sha256_file(
                            self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
                        ),
                        "atom-markdown-path": "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.md",
                        "canonical-owner": "owner-a",
                        "read-status": "read-full",
                        "inventory-section-count": 2,
                        "atom-count": 4,
                        "blockers": [],
                    }
                ],
                "phase-report-path": "openspec/orchestrate/phase-works/phase-2/phase-2-agent-report.md",
            },
        )
        global_atoms = [
            {
                "global-atom-id": "GA-0001",
                "source-document": "docs/source.md",
                "lines": "L1-L2",
                "line-ranges": [{"start": 1, "end": 2}],
                "atom-type": "behavior",
                "source-fact": "spec fact",
                "normativity": "must",
                "coverage-status": "direct",
                "artifact-projection": "spec-requirement",
                "owner-change": "change-a",
                "capability-impact": "new",
                "target-capability": "cap-a",
                "related-capabilities": [],
                "source-atom-origins": "atom.spec",
                "origins": ["atom.spec"],
                "atom-relation": "direct",
                "propose-use": "use",
                "evidence-need": "unit",
                "review-judgment": "ok",
            },
            {
                "global-atom-id": "GA-0002",
                "source-document": "docs/source.md",
                "lines": "L3-L4",
                "line-ranges": [{"start": 3, "end": 4}],
                "atom-type": "architecture",
                "source-fact": "design fact",
                "normativity": "must",
                "coverage-status": "direct",
                "artifact-projection": "design-obligation",
                "owner-change": "change-a",
                "capability-impact": "none",
                "target-capability": "none",
                "related-capabilities": ["cap-support"],
                "source-atom-origins": "atom.design",
                "origins": ["atom.design"],
                "atom-relation": "direct",
                "propose-use": "use",
                "evidence-need": "architecture-review",
                "review-judgment": "ok",
            },
            {
                "global-atom-id": "GA-0003",
                "source-document": "docs/source.md",
                "lines": "L5-L6",
                "line-ranges": [{"start": 5, "end": 6}],
                "atom-type": "verification",
                "source-fact": "verification fact",
                "normativity": "must",
                "coverage-status": "direct",
                "artifact-projection": "verification-obligation",
                "owner-change": "change-a",
                "capability-impact": "none",
                "target-capability": "none",
                "related-capabilities": ["cap-support"],
                "source-atom-origins": "atom.verify",
                "origins": ["atom.verify"],
                "atom-relation": "direct",
                "propose-use": "use",
                "evidence-need": "integration",
                "review-judgment": "ok",
            },
            {
                "global-atom-id": "GA-0004",
                "source-document": "docs/source.md",
                "lines": "L7-L8",
                "line-ranges": [{"start": 7, "end": 8}],
                "atom-type": "explicit-non-goal",
                "source-fact": "non-goal fact",
                "normativity": "must-not",
                "coverage-status": "explicit-non-goal",
                "artifact-projection": "spec-guard",
                "owner-change": "change-a",
                "capability-impact": "none",
                "target-capability": "none",
                "related-capabilities": [],
                "source-atom-origins": "atom.non-goal",
                "origins": ["atom.non-goal"],
                "atom-relation": "non-goal",
                "propose-use": "use",
                "evidence-need": "none",
                "review-judgment": "ok",
            },
        ]
        write_json(
            self.orchestrate / "change-capability-anchors/obligation-atom-index.json",
            {
                "trace-schema": GLOBAL_ATOM_INDEX_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "artifact-path": "openspec/orchestrate/change-capability-anchors/obligation-atom-index.md",
                "global-atoms": global_atoms,
            },
        )
        write_json(
            self.orchestrate / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json",
            {
                "trace-schema": SOURCE_TO_GLOBAL_MAP_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "artifact-path": "openspec/orchestrate/phase-works/phase-3/phase-3-trace/source-to-global-atom-map.md",
                "rows": [
                    {
                        "source-document": "docs/source.md",
                        "source-atom-id": "atom.spec",
                        "line-ranges": [{"start": 1, "end": 2}],
                        "candidate-status": "direct-candidate",
                        "candidate-artifact-projection": "spec-requirement",
                        "candidate-owner-change": "change-a",
                        "candidate-target-capability": "cap-a",
                        "global-atom-id": "GA-0001",
                        "global-coverage-status": "direct",
                        "global-artifact-projection": "spec-requirement",
                        "global-capability-impact": "new",
                        "global-target-capability": "cap-a",
                        "global-related-capabilities": [],
                        "review-decision": "global-atom-created",
                        "reason": "ok",
                    },
                    {
                        "source-document": "docs/source.md",
                        "source-atom-id": "atom.design",
                        "line-ranges": [{"start": 3, "end": 4}],
                        "candidate-status": "direct-candidate",
                        "candidate-artifact-projection": "design-obligation",
                        "candidate-owner-change": "change-a",
                        "candidate-target-capability": "none",
                        "global-atom-id": "GA-0002",
                        "global-coverage-status": "direct",
                        "global-artifact-projection": "design-obligation",
                        "global-capability-impact": "none",
                        "global-target-capability": "none",
                        "global-related-capabilities": ["cap-support"],
                        "review-decision": "global-atom-created",
                        "reason": "ok",
                    },
                    {
                        "source-document": "docs/source.md",
                        "source-atom-id": "atom.verify",
                        "line-ranges": [{"start": 5, "end": 6}],
                        "candidate-status": "direct-candidate",
                        "candidate-artifact-projection": "verification-obligation",
                        "candidate-owner-change": "change-a",
                        "candidate-target-capability": "none",
                        "global-atom-id": "GA-0003",
                        "global-coverage-status": "direct",
                        "global-artifact-projection": "verification-obligation",
                        "global-capability-impact": "none",
                        "global-target-capability": "none",
                        "global-related-capabilities": ["cap-support"],
                        "review-decision": "global-atom-created",
                        "reason": "ok",
                    },
                    {
                        "source-document": "docs/source.md",
                        "source-atom-id": "atom.non-goal",
                        "line-ranges": [{"start": 7, "end": 8}],
                        "candidate-status": "direct-candidate",
                        "candidate-artifact-projection": "spec-guard",
                        "candidate-owner-change": "change-a",
                        "candidate-target-capability": "cap-a",
                        "global-atom-id": "GA-0004",
                        "global-coverage-status": "explicit-non-goal",
                        "global-artifact-projection": "spec-guard",
                        "global-capability-impact": "none",
                        "global-target-capability": "none",
                        "global-related-capabilities": [],
                        "review-decision": "non-direct-status",
                        "reason": "ok",
                    },
                ],
            },
        )
        write_json(
            self.orchestrate / "phase-works/phase-3/phase-3-trace/source-remainder-review.json",
            {
                "trace-schema": "source-aligned-source-remainder-review-v1",
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "artifact-path": "openspec/orchestrate/phase-works/phase-3/phase-3-trace/source-remainder-review.md",
                "audit-documents": [
                    {
                        "source-document": "docs/source.md",
                        "source-sha256": source_sha,
                        "line-count": 20,
                        "evidence-ranges": [
                            {
                                "lines": "L1-L8",
                                "line-ranges": [{"start": 1, "end": 8}],
                                "origins": ["atom.spec", "atom.design", "atom.verify", "atom.non-goal"],
                            }
                        ],
                        "candidate-uncovered-ranges": [
                            {
                                "lines": "L9-L20",
                                "line-ranges": [{"start": 9, "end": 20}],
                            }
                        ],
                    }
                ],
                "rows": [
                    {
                        "source-document": "docs/source.md",
                        "lines": "L9-L20",
                        "line-ranges": [{"start": 9, "end": 20}],
                        "how-found": "phase3-line-range-audit",
                        "read-scope": "full-source remainder audit",
                        "semantic-classification": "formatting/background",
                        "production-obligation": False,
                        "linked-global-atom-ids": [],
                        "non-coverage-status": "no-product-or-system-impact",
                        "blocker": "",
                        "reason": "no production obligation",
                    }
                ],
            },
        )
        write_json(
            self.orchestrate / "trace/phase-3.trace.json",
            {
                "trace-schema": PHASE_TRACE_SCHEMAS["phase-3"],
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "decision": "coverage-complete",
                "source-classifications": [],
            },
        )
        window_text = "\n".join(["line 1", "line 2"])
        write_json(
            self.orchestrate / "phase-works/phase-4/source-window-dossiers/source-window-index.json",
            {
                "trace-schema": SOURCE_WINDOW_INDEX_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": "grounded",
                "windows": [
                    {
                        "window-id": "SW-001",
                        "input-unit": "change-a",
                        "unit-type": "input-change",
                        "source-document": "docs/source.md",
                        "lines": "L1-L2",
                        "line-ranges": [{"start": 1, "end": 2}],
                        "context-line-ranges": [],
                        "linked-global-atom-ids": ["GA-0001"],
                        "dossier-path": "openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-change/change-a.md",
                        "source-sha256": source_sha,
                        "window-text-sha256": sha256_text(window_text),
                    }
                ],
                "semantic-profiles": [],
                "grounding-issues": [],
            },
        )
        self._write("openspec/orchestrate/phase-works/phase-4/source-window-dossiers/by-input-change/change-a.md", "dossier\n")
        write_json(
            self.orchestrate / "trace/phase-4.trace.json",
            {
                "trace-schema": PHASE_TRACE_SCHEMAS["phase-4"],
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": "grounded",
                "source-window-index-path": "openspec/orchestrate/phase-works/phase-4/source-window-dossiers/source-window-index.json",
            },
        )
        write_json(
            self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json",
            {
                "trace-schema": ATOM_PLAN_MAPPING_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "artifact-path": "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.md",
                "rows": [
                    {
                        "global-atom-id": "GA-0001",
                        "source-document": "docs/source.md",
                        "lines": "L1-L2",
                        "line-ranges": [{"start": 1, "end": 2}],
                        "phase-3-owner-status": "change-a / direct",
                        "phase-3-artifact-projection": "spec-requirement",
                        "final-owner-type": "executable-change",
                        "final-owner-change": "change-a",
                        "final-capability-impact": "new",
                        "final-target-capability": "cap-a",
                        "related-capabilities": [],
                        "final-artifact-projection": "spec-requirement",
                        "final-relation": "direct",
                        "plan-decision": "direct-owner",
                        "reason": "reason",
                    },
                    {
                        "global-atom-id": "GA-0002",
                        "source-document": "docs/source.md",
                        "lines": "L3-L4",
                        "line-ranges": [{"start": 3, "end": 4}],
                        "phase-3-owner-status": "change-a / direct",
                        "phase-3-artifact-projection": "design-obligation",
                        "final-owner-type": "executable-change",
                        "final-owner-change": "change-a",
                        "final-capability-impact": "none",
                        "final-target-capability": "none",
                        "related-capabilities": ["cap-support"],
                        "final-artifact-projection": "design-obligation",
                        "final-relation": "direct",
                        "plan-decision": "direct-owner",
                        "reason": "reason",
                    },
                    {
                        "global-atom-id": "GA-0003",
                        "source-document": "docs/source.md",
                        "lines": "L5-L6",
                        "line-ranges": [{"start": 5, "end": 6}],
                        "phase-3-owner-status": "change-a / direct",
                        "phase-3-artifact-projection": "verification-obligation",
                        "final-owner-type": "executable-change",
                        "final-owner-change": "change-a",
                        "final-capability-impact": "none",
                        "final-target-capability": "none",
                        "related-capabilities": ["cap-support"],
                        "final-artifact-projection": "verification-obligation",
                        "final-relation": "direct",
                        "plan-decision": "direct-owner",
                        "reason": "reason",
                    },
                    {
                        "global-atom-id": "GA-0004",
                        "source-document": "docs/source.md",
                        "lines": "L7-L8",
                        "line-ranges": [{"start": 7, "end": 8}],
                        "phase-3-owner-status": "change-a / explicit-non-goal",
                        "phase-3-artifact-projection": "spec-guard",
                        "final-owner-type": "executable-change",
                        "final-owner-change": "change-a",
                        "final-capability-impact": "none",
                        "final-target-capability": "none",
                        "related-capabilities": [],
                        "final-artifact-projection": "spec-guard",
                        "final-relation": "non-goal",
                        "plan-decision": "scoped-non-direct",
                        "reason": "reason",
                    },
                ],
            },
        )
        write_json(
            self.orchestrate / "phase-works/phase-5/final-packet-index.json",
            {
                "trace-schema": FINAL_PACKET_INDEX_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "packets": [
                    {
                        "change": "change-a",
                        "change-kind": "business",
                        "packet-path": "openspec/orchestrate/change-capability-anchors/change-a/change-a.md",
                        "packet-digest": sha256_file(self.orchestrate / "change-capability-anchors/change-a/change-a.md"),
                        "direct-atom-ids": ["GA-0001", "GA-0002", "GA-0003"],
                        "owner-scoped-non-direct-atom-ids": ["GA-0004"],
                        "capability-view-paths": [
                            "openspec/orchestrate/change-capability-anchors/change-a/capability-anchors/cap-a.md"
                        ],
                    }
                ],
            },
        )
        baseline_path = self.orchestrate / "phase-works/phase-5/capability-baseline-reconciliation.json"
        write_json(
            baseline_path,
            {
                "trace-schema": CAPABILITY_BASELINE_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "repository-specs-root": "openspec/specs",
                "capabilities": [
                    {
                        "capability": "cap-a",
                        "baseline-status": "absent",
                        "spec-path": "openspec/specs/cap-a/spec.md",
                        "spec-sha256": None,
                        "baseline-evidence": "已只读检查精确 spec 路径，当前不存在。",
                        "first-planned-advancement": "change-a",
                        "required-first-relation": "new",
                        "later-relation-rule": "modified",
                    }
                ],
            },
        )
        write_json(
            self.orchestrate / "trace/phase-5.trace.json",
            {
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
            },
        )
        self._write_manifest()
        render_orchestrate(self.orchestrate, "all-supported", write=True)

    def _write_manifest(self) -> None:
        specs = [
            ("openspec/orchestrate/trace/phase-1.trace.json", PHASE_TRACE_SCHEMAS["phase-1"], "phase-1"),
            ("openspec/orchestrate/trace/phase-2.trace.json", PHASE_TRACE_SCHEMAS["phase-2"], "phase-2"),
            (
                "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json",
                SOURCE_ATOMS_SCHEMA,
                "phase-2",
            ),
            ("openspec/orchestrate/change-capability-anchors/obligation-atom-index.json", GLOBAL_ATOM_INDEX_SCHEMA, "phase-3"),
            ("openspec/orchestrate/phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json", SOURCE_TO_GLOBAL_MAP_SCHEMA, "phase-3"),
            (
                "openspec/orchestrate/phase-works/phase-3/phase-3-trace/source-remainder-review.json",
                "source-aligned-source-remainder-review-v1",
                "phase-3",
            ),
            ("openspec/orchestrate/trace/phase-3.trace.json", PHASE_TRACE_SCHEMAS["phase-3"], "phase-3"),
            ("openspec/orchestrate/phase-works/phase-4/source-window-dossiers/source-window-index.json", SOURCE_WINDOW_INDEX_SCHEMA, "phase-4"),
            ("openspec/orchestrate/trace/phase-4.trace.json", PHASE_TRACE_SCHEMAS["phase-4"], "phase-4"),
            ("openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json", ATOM_PLAN_MAPPING_SCHEMA, "phase-5"),
            (
                "openspec/orchestrate/phase-works/phase-5/capability-baseline-reconciliation.json",
                CAPABILITY_BASELINE_SCHEMA,
                "phase-5",
            ),
            ("openspec/orchestrate/phase-works/phase-5/final-packet-index.json", FINAL_PACKET_INDEX_SCHEMA, "phase-5"),
            ("openspec/orchestrate/trace/phase-5.trace.json", PHASE_TRACE_SCHEMAS["phase-5"], "phase-5"),
        ]
        artifacts = []
        for trace_path, schema, phase in specs:
            if not (self.root / trace_path).exists():
                continue
            artifacts.append(
                {
                    "artifact-path": trace_path.replace(".json", ".md"),
                    "trace-path": trace_path,
                    "trace-schema": schema,
                    "sha256": sha256_file(self.root / trace_path),
                    "phase": phase,
                    "role": "trace",
                }
            )
        phase_statuses = {}
        for phase in ("phase-1", "phase-2", "phase-3", "phase-4", "phase-5"):
            trace_path = self.orchestrate / "trace" / f"{phase}.trace.json"
            if not trace_path.exists():
                phase_statuses[phase] = "missing"
                continue
            data = json.loads(trace_path.read_text(encoding="utf-8"))
            phase_statuses[phase] = data.get("status") or data.get("decision") or "missing"
        write_json(
            self.orchestrate / "trace/manifest.json",
            {
                "trace-schema": MANIFEST_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "orchestrate-dir": "openspec/orchestrate",
                "phase-statuses": phase_statuses,
                "artifacts": artifacts,
            },
        )

    def _sync_phase2_trace_source(self) -> None:
        atom_path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        atom_data = json.loads(atom_path.read_text(encoding="utf-8"))
        trace_path = self.orchestrate / "trace/phase-2.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        row = trace["sources"][0]
        row["atom-json-sha256"] = sha256_file(atom_path)
        row["inventory-section-count"] = len(atom_data["section-inventory"])
        row["atom-count"] = len(atom_data["source-atoms"])
        row["blockers"] = atom_data["blockers"]
        write_json(trace_path, trace)

    def _convert_ga0002_to_foundation_change(self, legacy_reference: bool = False, wrong_order: bool = False) -> None:
        global_index_path = self.orchestrate / "change-capability-anchors/obligation-atom-index.json"
        global_index = json.loads(global_index_path.read_text(encoding="utf-8"))
        row = global_index["global-atoms"][1]
        row["atom-type"] = "architecture"
        row["coverage-status"] = "direct"
        row["artifact-projection"] = "design-obligation"
        row["owner-change"] = "bootstrap-runtime-substrate"
        row["capability-impact"] = "none"
        row["target-capability"] = "none"
        row["related-capabilities"] = []
        row["atom-relation"] = "direct"
        write_json(global_index_path, global_index)
        render_orchestrate(self.orchestrate, "phase3-global-index", write=True)

        source_map_path = self.orchestrate / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json"
        source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
        source_map["rows"][1]["global-capability-impact"] = "none"
        source_map["rows"][1]["global-target-capability"] = "none"
        source_map["rows"][1]["global-related-capabilities"] = []
        write_json(source_map_path, source_map)
        render_orchestrate(self.orchestrate, "phase3-source-map", write=True)

        mapping_path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        mapping["rows"][0]["final-owner-type"] = "executable-change"
        foundation_row = mapping["rows"][1]
        foundation_row["phase-3-owner-status"] = "bootstrap-runtime-substrate / direct"
        foundation_row["phase-3-artifact-projection"] = "design-obligation"
        foundation_row["final-owner-type"] = "executable-change"
        foundation_row["final-owner-change"] = "bootstrap-runtime-substrate"
        foundation_row["final-capability-impact"] = "foundation-substrate"
        foundation_row["final-target-capability"] = "runtime-substrate-foundation"
        foundation_row["related-capabilities"] = []
        foundation_row["final-artifact-projection"] = "design-obligation"
        foundation_row["final-relation"] = "direct"
        foundation_row["plan-decision"] = "foundation-executable"
        if legacy_reference:
            foundation_row["foundation-reference-id"] = "foundation-runtime-substrate"
            foundation_row["final-owner-type"] = "foundation-reference"
        write_json(mapping_path, mapping)
        render_orchestrate(self.orchestrate, "phase5-atom-plan-mapping", write=True)

        self._write(
            "openspec/orchestrate/change-capability-anchors/bootstrap-runtime-substrate/bootstrap-runtime-substrate.md",
            "# bootstrap-runtime-substrate\n\n## Final Direct Owner Atoms\n\n"
            "| Global Atom ID | Capability Impact | Target Capability | Related Capabilities | Relation |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| GA-0002 | foundation-substrate | runtime-substrate-foundation | None | direct |\n",
        )
        self._write(
            "openspec/orchestrate/change-capability-anchors/bootstrap-runtime-substrate/capability-anchors/runtime-substrate-foundation.md",
            "# runtime-substrate-foundation\n\n| Global Atom ID | Relation |\n| --- | --- |\n| GA-0002 | direct |\n",
        )
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/change-a.md",
            "# change-a\n\n## Final Direct Owner Atoms\n\n"
            "| Global Atom ID | Capability Impact | Target Capability | Related Capabilities | Relation |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| GA-0001 | new | cap-a | None | direct |\n"
            "| GA-0003 | none | None/change-only | cap-support | direct |\n\n"
            "## Contextual Atoms\n\n| Global Atom ID | Relation |\n| --- | --- |\n"
            "| GA-0004 | non-goal |\n",
        )
        self._write("openspec/orchestrate/change-capability-anchors/index.md", "index\nGA-0001\nGA-0002\nGA-0003\nGA-0004\n")
        index_path = self.orchestrate / "phase-works/phase-5/final-packet-index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        foundation_packet = {
            "change": "bootstrap-runtime-substrate",
            "change-kind": "foundation",
            "packet-path": "openspec/orchestrate/change-capability-anchors/bootstrap-runtime-substrate/bootstrap-runtime-substrate.md",
            "packet-digest": sha256_file(self.orchestrate / "change-capability-anchors/bootstrap-runtime-substrate/bootstrap-runtime-substrate.md"),
            "direct-atom-ids": ["GA-0002"],
            "owner-scoped-non-direct-atom-ids": [],
            "capability-view-paths": [
                "openspec/orchestrate/change-capability-anchors/bootstrap-runtime-substrate/capability-anchors/runtime-substrate-foundation.md"
            ],
        }
        index["packets"][0]["change-kind"] = "business"
        index["packets"][0]["packet-digest"] = sha256_file(self.orchestrate / "change-capability-anchors/change-a/change-a.md")
        index["packets"][0]["direct-atom-ids"] = ["GA-0001", "GA-0003"]
        index["packets"][0]["owner-scoped-non-direct-atom-ids"] = ["GA-0004"]
        index["packets"] = [index["packets"][0], foundation_packet] if wrong_order else [foundation_packet, index["packets"][0]]
        write_json(index_path, index)
        self._write_manifest()

    def _validate(self, complete: bool = True) -> dict:
        return validate(self.orchestrate, self.root, "all", complete)

    def _validate_phase(self, phase: str, complete: bool = False) -> dict:
        return validate(self.orchestrate, self.root, phase, complete)

    def assert_error(self, rule_id: str) -> None:
        result = self._validate()
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == rule_id for issue in result["issues"]), result)

    def assert_issue_contains(self, needle: str, phase: str = "all") -> dict:
        result = self._validate() if phase == "all" else self._validate_phase(phase)
        self.assertFalse(result["ok"], result)
        matching = [
            issue
            for issue in result["issues"]
            if needle.lower() in f"{issue['rule_id']} {issue['message']}".lower()
        ]
        self.assertTrue(matching, result)
        return result

    def test_minimal_valid_orchestrate_passes(self) -> None:
        result = self._validate()
        self.assertTrue(result["ok"], result)

    def test_change_only_direct_atoms_stay_in_change_packet_not_capability_view(self) -> None:
        result = self._validate()
        self.assertTrue(result["ok"], result)
        packet = (
            self.orchestrate / "change-capability-anchors/change-a/change-a.md"
        ).read_text(encoding="utf-8")
        capability_view = (
            self.orchestrate / "change-capability-anchors/change-a/capability-anchors/cap-a.md"
        ).read_text(encoding="utf-8")
        for atom_id in ("GA-0002", "GA-0003"):
            self.assertIn(atom_id, packet)
            self.assertNotIn(atom_id, capability_view)

    def test_phase1_minimal_with_manifest_skeleton_passes(self) -> None:
        for trace in ("phase-2", "phase-3", "phase-4", "phase-5"):
            path = self.orchestrate / "trace" / f"{trace}.trace.json"
            if path.exists():
                path.unlink()
        (self.orchestrate / "change-plan.md").unlink()
        self._write_manifest()
        result = self._validate_phase("phase-1")
        self.assertTrue(result["ok"], result)

    def test_phase1_legacy_plan_filename_does_not_satisfy_contract(self) -> None:
        (self.orchestrate / "phase-works/phase-1/initial-change-plan.md").unlink()
        legacy_plan = "openspec/orchestrate/phase-works/phase-1" + "/change-plan.md"
        self._write(legacy_plan, self._phase1_plan())
        result = self._validate_phase("phase-1")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "phase1-interface-artifact" for issue in result["issues"]), result)

    def test_phase1_trace_plan_path_must_match_contract(self) -> None:
        path = self.orchestrate / "trace/phase-1.trace.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["initial-change-plan"]["artifact-path"] = (
            "openspec/orchestrate/phase-works/phase-1" + "/change-plan.md"
        )
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase1-initial-plan-path")

    def test_phase1_plan_digest_drift_fails(self) -> None:
        self._write(
            "openspec/orchestrate/phase-works/phase-1/initial-change-plan.md",
            self._phase1_plan() + "\n计划已发生变化。\n",
        )
        self.assert_error("phase1-initial-plan-sha")

    def test_phase1_manifest_trace_drift_fails(self) -> None:
        self._write(
            "openspec/orchestrate/phase-works/phase-1/source-doc-manifest.md",
            "| Source Document | Read Status | Source Role | Coarse Topics / Paths | Notes |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| docs/source.md | read-full | main | changed-topic | note |\n",
        )
        self.assert_error("phase1-source-manifest-drift")

    def test_phase1_required_heading_missing_fails(self) -> None:
        plan_path = self.orchestrate / "phase-works/phase-1/initial-change-plan.md"
        plan_path.write_text(self._phase1_plan().replace("## Change 切分原则", "## 其他原则"), encoding="utf-8")
        trace_path = self.orchestrate / "trace/phase-1.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["initial-change-plan"]["sha256"] = sha256_file(plan_path)
        write_json(trace_path, trace)
        self._write_manifest()
        self.assert_error("phase1-plan-heading")

    def test_phase1_overlay_rejects_openspec_relation_label(self) -> None:
        plan_path = self.orchestrate / "phase-works/phase-1/initial-change-plan.md"
        plan_path.write_text(
            self._phase1_plan().replace("`first-advancement`", "`New`"),
            encoding="utf-8",
        )
        trace_path = self.orchestrate / "trace/phase-1.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["initial-change-plan"]["sha256"] = sha256_file(plan_path)
        write_json(trace_path, trace)
        self._write_manifest()
        self.assert_error("phase1-plan-overlay-role")

    def test_phase1_roadmap_rejects_new_modified_fields(self) -> None:
        plan_path = self.orchestrate / "phase-works/phase-1/initial-change-plan.md"
        plan_path.write_text(
            self._phase1_plan().replace(
                "- 范围内：行为基线。",
                "- New：`cap-a`\n- 范围内：行为基线。",
            ),
            encoding="utf-8",
        )
        trace_path = self.orchestrate / "trace/phase-1.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["initial-change-plan"]["sha256"] = sha256_file(plan_path)
        write_json(trace_path, trace)
        self._write_manifest()
        self.assert_error("phase1-plan-baseline-relation")

    def test_phase4_input_plan_must_match_phase1_initial_plan(self) -> None:
        self._write("openspec/orchestrate/phase-works/phase-4/input-change-plan.md", "stale input\n")
        self.assert_error("phase4-input-plan-drift")

    def test_phase5_input_plan_must_match_phase4_input_plan(self) -> None:
        self._write("openspec/orchestrate/phase-works/phase-5/input-change-plan.md", "stale input\n")
        self.assert_error("phase5-input-plan-drift")

    def test_phase5_final_status_requires_root_plan(self) -> None:
        (self.orchestrate / "change-plan.md").unlink()
        result = self._validate_phase("phase-5")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "phase5-interface-artifact" for issue in result["issues"]), result)

    def test_phase5_root_plan_must_match_phase5_snapshot(self) -> None:
        self._write("openspec/orchestrate/change-plan.md", "stale final plan\n")
        self.assert_error("phase5-root-plan-drift")

    def test_manifest_digest_drift_fails(self) -> None:
        path = self.orchestrate / "trace/phase-1.trace.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "changed-after-manifest"
        write_json(path, data)
        result = self._validate_phase("phase-1")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "manifest-digest" for issue in result["issues"]), result)

    def test_manifest_cannot_omit_existing_canonical_artifacts(self) -> None:
        path = self.orchestrate / "trace/manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["artifacts"] = []
        write_json(path, data)
        self.assert_error("manifest-artifact-missing")

    def test_manifest_present_status_is_rejected(self) -> None:
        path = self.orchestrate / "trace/manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["phase-statuses"]["phase-1"] = "present"
        write_json(path, data)
        result = self._validate_phase("phase-1")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "manifest-phase-status-workflow-state" for issue in result["issues"]), result)

    def test_manifest_missing_phase_status_fails(self) -> None:
        path = self.orchestrate / "trace/manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        del data["phase-statuses"]["phase-2"]
        write_json(path, data)
        result = self._validate_phase("phase-1")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "manifest-phase-status-missing" for issue in result["issues"]), result)

    def test_manifest_trace_without_status_fails(self) -> None:
        trace_path = self.orchestrate / "trace/phase-2.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        del trace["status"]
        write_json(trace_path, trace)
        self._write_manifest()
        result = self._validate_phase("phase-2")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "manifest-phase-status-trace-missing" for issue in result["issues"]), result)
        self.assertTrue(any(issue["rule_id"] == "phase2-status" for issue in result["issues"]), result)

    def test_manifest_phase5_status_must_match_phase5_trace(self) -> None:
        path = self.orchestrate / "trace/manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["phase-statuses"]["phase-5"] = "accepted"
        write_json(path, data)
        self.assert_error("manifest-phase-status-drift")

    def test_manifest_phase5_complete_status_must_be_handoff_status(self) -> None:
        path = self.orchestrate / "trace/manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["phase-statuses"]["phase-5"] = "reviewer-passed"
        write_json(path, data)
        self.assert_error("manifest-phase5-complete-status")

    def test_phase1_status_must_be_initial_plan_written(self) -> None:
        path = self.orchestrate / "trace/phase-1.trace.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "source-atoms-written"
        write_json(path, data)
        self._write_manifest()
        result = self._validate_phase("phase-1")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "phase1-status" for issue in result["issues"]), result)

    def test_phase2_status_must_be_source_atoms_written(self) -> None:
        path = self.orchestrate / "trace/phase-2.trace.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "initial-plan-written"
        write_json(path, data)
        self._write_manifest()
        result = self._validate_phase("phase-2")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "phase2-status" for issue in result["issues"]), result)

    def test_phase2_work_queue_missing_source_fails(self) -> None:
        self._write(
            "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/work-queue.md",
            "| Batch | Source Documents | Canonical Owner |\n| --- | --- | --- |\n",
        )
        self.assert_error("phase2-work-queue-coverage")

    def test_phase2_missing_source_atom_json_fails(self) -> None:
        (self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json").unlink()
        self._write_manifest()
        self.assert_error("missing-json")

    def test_phase2_direct_candidate_contextual_only_fails(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source-atoms"][0]["candidate-artifact-projection"] = "contextual-only"
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase2-direct-contextual-only")

    def test_phase2_spec_delta_requires_target_capability(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source-atoms"][0]["candidate-target-capability"] = "none"
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        self._write_manifest()
        self.assert_error("phase2-target")

    def test_phase2_spec_target_may_remain_unresolved(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source-atoms"][0]["candidate-target-capability"] = "unresolved"
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        self._sync_phase2_trace_source()
        self._write_manifest()
        result = self._validate_phase("phase-2")
        self.assertTrue(result["ok"], result)

    def test_phase2_design_atom_cannot_target_capability(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        design = data["source-atoms"][1]
        design["candidate-target-capability"] = "cap-support"
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        self._write_manifest()
        self.assert_error("phase2-target")

    def test_phase2_contextual_candidate_requires_contextual_projection(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source-atoms"][0]["candidate-status"] = "contextual-candidate"
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase2-contextual-projection")

    def test_phase2_candidate_new_capability_status_is_rejected(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source-atoms"][0]["candidate-status"] = "candidate-new-capability"
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase2-candidate-status")

    def test_phase2_design_requires_explicit_none_target(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source-atoms"][1]["candidate-target-capability"] = ""
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase2-target")

    def test_phase2_legacy_auxiliary_field_is_rejected(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source-atoms"][1]["candidate-related-capabilities"] = ["cap-support"]
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        self._write_manifest()
        self.assert_error("phase2-atom-field")

    def test_phase2_redundant_lines_field_is_rejected(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source-atoms"][1]["lines"] = "L3-L4"
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        self._write_manifest()
        self.assert_error("phase2-atom-field")

    def test_phase2_inventory_gap_fails(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["section-inventory"][1]["line-ranges"] = [{"start": 10, "end": 20}]
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        self._write_manifest()
        self.assert_error("phase2-inventory-gap")

    def test_phase2_meaningful_inventory_requires_atom_or_blocker(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["section-inventory"][0]["atom-ids"] = []
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        self._write_manifest()
        self.assert_error("phase2-inventory-meaningful-without-atom")

    def test_phase2_v1_schema_is_rejected(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["trace-schema"] = "source-aligned-source-atoms-v1"
        data["trace-contract-version"] = "source-aligned-trace-v1"
        write_json(path, data)
        self._write_manifest()
        result = self.assert_issue_contains("trace-contract-version", phase="phase-2")
        self.assertTrue(any(issue["rule_id"] == "trace-schema" for issue in result["issues"]), result)

    def test_phase2_mixed_v1_capability_fields_are_rejected(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        spec = data["source-atoms"][0]
        spec.pop("candidate-target-capability")
        spec["candidate-owner-capability"] = "cap-a"
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        self._write_manifest()
        self.assert_issue_contains("candidate-owner-capability", phase="phase-2")

    def test_phase2_rendered_markdown_drift_fails(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("spec fact", "spec fact edited only in markdown", 1), encoding="utf-8")
        result = self._validate_phase("phase-2")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "rendered-markdown-drift" for issue in result["issues"]), result)

    def test_phase2_render_after_json_change_passes(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source-atoms"][0]["source-fact"] = "中文事实包含 | 管道符和\n换行。"
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase2-source-atoms", write=True)
        markdown = (self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.md").read_text(encoding="utf-8")
        self.assertIn("中文事实包含 \\| 管道符和 换行。", markdown)
        self.assertIn("Render contract: `source-aligned-render-v3`", markdown)
        self._sync_phase2_trace_source()
        self._write_manifest()
        result = self._validate_phase("phase-2")
        self.assertTrue(result["ok"], result)

    def test_phase2_missing_rendered_markdown_fails(self) -> None:
        (self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.md").unlink()
        result = self._validate_phase("phase-2")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "markdown-mirror-missing" for issue in result["issues"]), result)

    def test_phase3_duplicate_ga_fails(self) -> None:
        path = self.orchestrate / "change-capability-anchors/obligation-atom-index.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["global-atoms"].append(dict(data["global-atoms"][0]))
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase3-ga-duplicate")

    def test_phase3_non_direct_spec_atom_cannot_advance_capability(self) -> None:
        path = self.orchestrate / "change-capability-anchors/obligation-atom-index.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["global-atoms"][0]["coverage-status"] = "contextual"
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase3-non-direct-capability")

    def test_phase3_source_to_global_map_missing_atom_fails(self) -> None:
        path = self.orchestrate / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"] = data["rows"][:1]
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase3-map-coverage")

    def test_phase3_source_map_rendered_markdown_drift_fails(self) -> None:
        path = self.orchestrate / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("GA-0001", "GA-9999", 1), encoding="utf-8")
        result = self._validate_phase("phase-3")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "rendered-markdown-drift" for issue in result["issues"]), result)

    def test_phase3_remainder_missing_uncovered_range_fails(self) -> None:
        path = self.orchestrate / "phase-works/phase-3/phase-3-trace/source-remainder-review.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"] = []
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase3-remainder-coverage")

    def test_phase3_remainder_production_obligation_without_outcome_fails(self) -> None:
        path = self.orchestrate / "phase-works/phase-3/phase-3-trace/source-remainder-review.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"][0]["production-obligation"] = True
        data["rows"][0]["linked-global-atom-ids"] = []
        data["rows"][0]["blocker"] = ""
        data["rows"][0]["non-coverage-status"] = ""
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase3-remainder-outcome")

    def test_phase3_remainder_unknown_ga_fails(self) -> None:
        path = self.orchestrate / "phase-works/phase-3/phase-3-trace/source-remainder-review.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"][0]["production-obligation"] = True
        data["rows"][0]["linked-global-atom-ids"] = ["GA-9999"]
        data["rows"][0]["non-coverage-status"] = ""
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase3-remainder-unknown-ga")

    def test_phase3_remainder_blocker_prevents_coverage_complete(self) -> None:
        path = self.orchestrate / "phase-works/phase-3/phase-3-trace/source-remainder-review.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"][0]["blocker"] = "needs human decision"
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase3-remainder-blocker-complete")

    def test_phase3_manifest_missing_read_full_source_fails(self) -> None:
        self._write(
            "openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md",
            "| Source Document | Classification | Phase 2 Atom File | Review File | Effective Atom Ranges | Missing Obligation Atom Ranges | Non-Atom Ranges | Read Scope | Reason |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
        )
        self.assert_error("phase3-manifest-coverage")

    def test_phase3_coverage_file_missing_fails(self) -> None:
        (self.orchestrate / "phase-works/phase-3/source-doc-coverage/docs--source.coverage.md").unlink()
        self.assert_error("phase3-coverage-file")

    def test_phase4_source_hash_mismatch_fails(self) -> None:
        path = self.orchestrate / "phase-works/phase-4/source-window-dossiers/source-window-index.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["windows"][0]["source-sha256"] = "bad"
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase4-source-sha")

    def test_phase4_blocked_allows_empty_windows_with_grounding_issue(self) -> None:
        trace_path = self.orchestrate / "trace/phase-4.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["status"] = "blocked"
        write_json(trace_path, trace)
        index_path = self.orchestrate / "phase-works/phase-4/source-window-dossiers/source-window-index.json"
        data = json.loads(index_path.read_text(encoding="utf-8"))
        data["status"] = "blocked"
        data["windows"] = []
        data["grounding-issues"] = [{"issue": "source boundary requires decision"}]
        write_json(index_path, data)
        self._write("openspec/orchestrate/phase-works/phase-4/phase-4-agent-report.md", "Phase 4 Status: blocked\n")
        self._write_manifest()
        result = self._validate_phase("phase-4")
        self.assertTrue(result["ok"], result)

    def test_phase4_grounded_requires_non_empty_windows(self) -> None:
        index_path = self.orchestrate / "phase-works/phase-4/source-window-dossiers/source-window-index.json"
        data = json.loads(index_path.read_text(encoding="utf-8"))
        data["windows"] = []
        write_json(index_path, data)
        self._write_manifest()
        self.assert_error("phase4-windows")

    def test_phase5_mapping_missing_global_atom_fails(self) -> None:
        path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"] = data["rows"][:1]
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase5-mapping-coverage")

    def test_phase5_terminal_mapping_rejects_unresolved_impact(self) -> None:
        path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"][0]["final-capability-impact"] = "unresolved"
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase5-atom-plan-mapping", write=True)
        self._write_manifest()
        self.assert_error("phase5-capability-impact")

    def test_phase5_direct_spec_atom_requires_target(self) -> None:
        path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"][0]["final-target-capability"] = "none"
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase5-atom-plan-mapping", write=True)
        self._write_manifest()
        self.assert_error("phase5-capability-target")

    def test_phase5_business_impact_cannot_use_unresolved_target(self) -> None:
        path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"][0]["final-target-capability"] = "unresolved"
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase5-capability-target")

    def test_phase5_direct_atom_requires_executable_owner_type(self) -> None:
        path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"][0]["final-owner-type"] = "garbage-owner"
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase5-direct-owner-type")

    def test_phase5_direct_spec_atom_cannot_use_none_impact(self) -> None:
        path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"][0]["final-capability-impact"] = "none"
        data["rows"][0]["final-target-capability"] = "none"
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase5-atom-plan-mapping", write=True)
        self._write_manifest()
        self.assert_error("phase5-spec-impact")

    def test_phase5_design_atom_cannot_use_business_capability_impact(self) -> None:
        path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        design = data["rows"][1]
        design["final-capability-impact"] = "new"
        design["final-target-capability"] = "cap-a"
        design["related-capabilities"] = []
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase5-atom-plan-mapping", write=True)
        self._write_manifest()
        self.assert_error("phase5-change-only-impact")

    def test_phase5_verification_atom_cannot_use_business_capability_impact(self) -> None:
        path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        verification = data["rows"][2]
        verification["final-capability-impact"] = "modified"
        verification["final-target-capability"] = "cap-a"
        verification["related-capabilities"] = []
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase5-atom-plan-mapping", write=True)
        self._write_manifest()
        self.assert_error("phase5-change-only-impact")

    def test_phase5_same_change_capability_cannot_mix_new_and_modified(self) -> None:
        mapping_path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        second_spec = mapping["rows"][3]
        second_spec["final-relation"] = "direct"
        second_spec["final-capability-impact"] = "modified"
        second_spec["final-target-capability"] = "cap-a"
        second_spec["related-capabilities"] = []
        write_json(mapping_path, mapping)
        render_orchestrate(self.orchestrate, "phase5-atom-plan-mapping", write=True)

        packet_index_path = self.orchestrate / "phase-works/phase-5/final-packet-index.json"
        packet_index = json.loads(packet_index_path.read_text(encoding="utf-8"))
        packet = packet_index["packets"][0]
        packet["direct-atom-ids"].append("GA-0004")
        packet["owner-scoped-non-direct-atom-ids"] = []
        write_json(packet_index_path, packet_index)
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/capability-anchors/cap-a.md",
            "# cap-a\n\n| Global Atom ID | Relation |\n| --- | --- |\n"
            "| GA-0001 | direct |\n"
            "| GA-0004 | direct |\n",
        )
        self._write_manifest()
        self.assert_error("phase5-capability-impact-mixed")

    def test_phase5_existing_baseline_allows_modified_first_advancement(self) -> None:
        spec_path = self._write(
            "openspec/specs/cap-a/spec.md",
            "# cap-a\n\n## Purpose\n\n现有能力。\n",
        )
        mapping_path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        mapping["rows"][0]["final-capability-impact"] = "modified"
        write_json(mapping_path, mapping)
        render_orchestrate(self.orchestrate, "phase5-atom-plan-mapping", write=True)

        packet_path = self.orchestrate / "change-capability-anchors/change-a/change-a.md"
        packet_path.write_text(
            packet_path.read_text(encoding="utf-8").replace(
                "| GA-0001 | new |",
                "| GA-0001 | modified |",
            ),
            encoding="utf-8",
        )
        packet_index_path = self.orchestrate / "phase-works/phase-5/final-packet-index.json"
        packet_index = json.loads(packet_index_path.read_text(encoding="utf-8"))
        packet_index["packets"][0]["packet-digest"] = sha256_file(packet_path)
        write_json(packet_index_path, packet_index)

        baseline_path = self.orchestrate / "phase-works/phase-5/capability-baseline-reconciliation.json"
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        row = baseline["capabilities"][0]
        row["baseline-status"] = "existing"
        row["spec-sha256"] = sha256_file(spec_path)
        row["baseline-evidence"] = "已只读检查精确 spec 路径，当前存在。"
        row["required-first-relation"] = "modified"
        write_json(baseline_path, baseline)
        render_orchestrate(self.orchestrate, "phase5-capability-baseline", write=True)

        trace_path = self.orchestrate / "trace/phase-5.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["capability-baseline-reconciliation-sha256"] = sha256_file(baseline_path)
        write_json(trace_path, trace)
        self._write_manifest()
        result = self._validate()
        self.assertTrue(result["ok"], result)

    def test_phase5_existing_baseline_rejects_new(self) -> None:
        spec_path = self._write("openspec/specs/cap-a/spec.md", "# cap-a\n")
        baseline_path = self.orchestrate / "phase-works/phase-5/capability-baseline-reconciliation.json"
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        row = baseline["capabilities"][0]
        row["baseline-status"] = "existing"
        row["spec-sha256"] = sha256_file(spec_path)
        row["baseline-evidence"] = "已只读检查精确 spec 路径，当前存在。"
        row["required-first-relation"] = "modified"
        write_json(baseline_path, baseline)
        render_orchestrate(self.orchestrate, "phase5-capability-baseline", write=True)
        trace_path = self.orchestrate / "trace/phase-5.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["capability-baseline-reconciliation-sha256"] = sha256_file(baseline_path)
        write_json(trace_path, trace)
        self._write_manifest()
        self.assert_error("phase5-capability-impact-baseline")

    def test_phase5_active_capability_requires_baseline_row(self) -> None:
        baseline_path = self.orchestrate / "phase-works/phase-5/capability-baseline-reconciliation.json"
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        baseline["capabilities"] = []
        write_json(baseline_path, baseline)
        render_orchestrate(self.orchestrate, "phase5-capability-baseline", write=True)
        trace_path = self.orchestrate / "trace/phase-5.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["capability-baseline-reconciliation-sha256"] = sha256_file(baseline_path)
        write_json(trace_path, trace)
        self._write_manifest()
        self.assert_error("phase5-capability-baseline-missing")

    def test_phase5_absent_baseline_rejects_modified_first_advancement(self) -> None:
        mapping_path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        second_change_spec = mapping["rows"][3]
        second_change_spec["final-owner-change"] = "change-b"
        second_change_spec["final-relation"] = "direct"
        second_change_spec["final-capability-impact"] = "modified"
        second_change_spec["final-target-capability"] = "cap-a"
        second_change_spec["related-capabilities"] = []
        write_json(mapping_path, mapping)
        render_orchestrate(self.orchestrate, "phase5-atom-plan-mapping", write=True)

        change_b_packet = self._write(
            "openspec/orchestrate/change-capability-anchors/change-b/change-b.md",
            "# change-b\n\n| Global Atom ID | Relation |\n| --- | --- |\n| GA-0004 | direct |\n",
        )
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-b/capability-anchors/cap-a.md",
            "# cap-a\n\n| Global Atom ID | Relation |\n| --- | --- |\n| GA-0004 | direct |\n",
        )
        packet_index_path = self.orchestrate / "phase-works/phase-5/final-packet-index.json"
        packet_index = json.loads(packet_index_path.read_text(encoding="utf-8"))
        packet_index["packets"][0]["owner-scoped-non-direct-atom-ids"] = []
        packet_index["packets"].insert(
            0,
            {
                "change": "change-b",
                "change-kind": "business",
                "packet-path": "openspec/orchestrate/change-capability-anchors/change-b/change-b.md",
                "packet-digest": sha256_file(change_b_packet),
                "direct-atom-ids": ["GA-0004"],
                "owner-scoped-non-direct-atom-ids": [],
                "capability-view-paths": [
                    "openspec/orchestrate/change-capability-anchors/change-b/capability-anchors/cap-a.md"
                ],
            },
        )
        write_json(packet_index_path, packet_index)
        self._write_manifest()
        self.assert_error("phase5-capability-impact-baseline")

    def test_phase5_absent_baseline_allows_new_then_modified(self) -> None:
        mapping_path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        second = mapping["rows"][3]
        second["final-owner-change"] = "change-b"
        second["final-relation"] = "direct"
        second["final-capability-impact"] = "modified"
        second["final-target-capability"] = "cap-a"
        second["related-capabilities"] = []
        write_json(mapping_path, mapping)
        render_orchestrate(self.orchestrate, "phase5-atom-plan-mapping", write=True)

        first_packet_path = self.orchestrate / "change-capability-anchors/change-a/change-a.md"
        first_packet_path.write_text(
            first_packet_path.read_text(encoding="utf-8").replace(
                "| GA-0004 | non-goal |\n",
                "",
            ),
            encoding="utf-8",
        )
        second_packet = self._write(
            "openspec/orchestrate/change-capability-anchors/change-b/change-b.md",
            "# change-b\n\n## Final Direct Owner Atoms\n\n"
            "| Global Atom ID | Capability Impact | Target Capability | Related Capabilities | Relation |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| GA-0004 | modified | cap-a | None | direct |\n",
        )
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-b/capability-anchors/cap-a.md",
            "# cap-a\n\n| Global Atom ID | Relation |\n| --- | --- |\n| GA-0004 | direct |\n",
        )
        packet_index_path = self.orchestrate / "phase-works/phase-5/final-packet-index.json"
        packet_index = json.loads(packet_index_path.read_text(encoding="utf-8"))
        packet_index["packets"][0]["packet-digest"] = sha256_file(first_packet_path)
        packet_index["packets"][0]["owner-scoped-non-direct-atom-ids"] = []
        packet_index["packets"].append(
            {
                "change": "change-b",
                "change-kind": "business",
                "packet-path": "openspec/orchestrate/change-capability-anchors/change-b/change-b.md",
                "packet-digest": sha256_file(second_packet),
                "direct-atom-ids": ["GA-0004"],
                "owner-scoped-non-direct-atom-ids": [],
                "capability-view-paths": [
                    "openspec/orchestrate/change-capability-anchors/change-b/capability-anchors/cap-a.md"
                ],
            }
        )
        write_json(packet_index_path, packet_index)
        self._write_manifest()
        result = self._validate()
        self.assertTrue(result["ok"], result)

    def test_phase5_blocked_does_not_require_final_packets(self) -> None:
        trace_path = self.orchestrate / "trace/phase-5.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["status"] = "blocked"
        write_json(trace_path, trace)
        for rel_path in (
            "phase-works/phase-5/input-change-plan.md",
            "phase-works/phase-5/change-plan.md",
            "phase-works/phase-5/atom-plan-mapping.json",
            "phase-works/phase-5/atom-plan-mapping.md",
            "phase-works/phase-5/capability-baseline-reconciliation.json",
            "phase-works/phase-5/capability-baseline-reconciliation.md",
            "phase-works/phase-5/final-packet-index.json",
            "phase-works/phase-5/capability-progression-review.md",
            "phase-works/phase-5/change-complexity-review.md",
            "phase-works/phase-5/plan-refit-decision-log.md",
            "phase-works/phase-5/alignment-final-report.md",
            "phase-works/phase-5/change-capability-human-plan.md",
            "change-capability-anchors/index.md",
        ):
            path = self.orchestrate / rel_path
            if path.exists():
                path.unlink()
        anchors_dir = self.orchestrate / "change-capability-anchors"
        for child in anchors_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
        (self.orchestrate / "change-plan.md").unlink()
        self._write("openspec/orchestrate/phase-works/phase-5/change-plan-adjustments.md", "blocked\n")
        self._write("openspec/orchestrate/phase-works/phase-5/phase-5-agent-report.md", "Phase 5 Status: blocked\n")
        self._write_manifest()
        result = self._validate_phase("phase-5")
        self.assertTrue(result["ok"], result)

    def test_phase5_nonfinal_status_rejects_terminal_artifacts(self) -> None:
        trace_path = self.orchestrate / "trace/phase-5.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["status"] = "needs-coverage-recheck"
        write_json(trace_path, trace)
        (self.orchestrate / "change-plan.md").unlink()
        self._write("openspec/orchestrate/phase-works/phase-5/change-plan-adjustments.md", "recheck\n")
        self._write_manifest()
        self.assert_error("phase5-nonfinal-terminal-artifact")

    def test_phase5_nonfinal_status_rejects_root_plan(self) -> None:
        trace_path = self.orchestrate / "trace/phase-5.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["status"] = "blocked"
        write_json(trace_path, trace)
        self._write("openspec/orchestrate/phase-works/phase-5/change-plan-adjustments.md", "blocked\n")
        self._write_manifest()
        self.assert_error("phase5-nonfinal-root-plan")

    def test_phase5_accepted_requires_final_packet_index(self) -> None:
        (self.orchestrate / "phase-works/phase-5/final-packet-index.json").unlink()
        self._write_manifest()
        self.assert_error("missing-json")

    def test_phase5_direct_owner_requires_final_packet(self) -> None:
        path = self.orchestrate / "phase-works/phase-5/final-packet-index.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["packets"] = []
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase5-final-direct-owner")

    def test_phase5_foundation_change_requires_packet_and_passes_first(self) -> None:
        self._convert_ga0002_to_foundation_change()
        result = self._validate()
        self.assertTrue(result["ok"], result)

    def test_phase5_foundation_reference_mapping_fails(self) -> None:
        self._convert_ga0002_to_foundation_change(legacy_reference=True)
        self.assert_error("phase5-foundation-reference-deprecated")

    def test_phase5_foundation_change_not_first_fails(self) -> None:
        self._convert_ga0002_to_foundation_change(wrong_order=True)
        self.assert_error("phase5-foundation-order")

    def test_phase5_foundation_packet_cannot_be_empty(self) -> None:
        self._convert_ga0002_to_foundation_change()
        path = self.orchestrate / "phase-works/phase-5/final-packet-index.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["packets"][0]["direct-atom-ids"] = []
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase5-foundation-empty")

    def test_phase5_refit_helper_rejects_blocked_write(self) -> None:
        config_path = self.orchestrate / "phase-works/phase-5/phase5-refit.config.json"
        write_json(
            config_path,
            {
                "status": "blocked",
                "changes": [
                    {
                        "slug": "change-a",
                        "title": "change-a",
                        "outcome": "被阻塞的 Phase 5 不应渲染 final packets。",
                        "kind": "business",
                    }
                ],
                "capabilities": [
                    {
                        "slug": "cap-a",
                        "boundary": "cap-a",
                        "baseline_status": "absent",
                        "baseline_evidence": "已只读检查精确 spec 路径，当前不存在。",
                    },
                ],
            },
        )
        output_dir = self.root / "out/orchestrate"
        proc = subprocess.run(
            [
                sys.executable,
                str(self.refit_script),
                "--orchestrate-dir",
                str(self.orchestrate),
                "--mapping",
                str(self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"),
                "--config",
                str(config_path),
                "--output-orchestrate-dir",
                str(output_dir),
                "--write",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("只渲染 accepted/adjusted", proc.stderr)
        self.assertFalse((output_dir / "change-capability-anchors/index.md").exists())

    def test_phase5_refit_helper_accepts_terminal_write(self) -> None:
        config_path = self.orchestrate / "phase-works/phase-5/phase5-refit.config.json"
        write_json(
            config_path,
            {
                "status": "accepted",
                "changes": [
                    {
                        "slug": "change-a",
                        "title": "change-a",
                        "outcome": "终态 Phase 5 可以渲染 final packets。",
                        "kind": "business",
                    }
                ],
                "capabilities": [
                    {
                        "slug": "cap-a",
                        "boundary": "cap-a",
                        "baseline_status": "absent",
                        "baseline_evidence": "已只读检查精确 spec 路径，当前不存在。",
                    },
                    {"slug": "cap-support", "boundary": "仅作为 source-explicit related capability。"},
                ],
            },
        )
        output_dir = self.root / "out/orchestrate"
        self._write("out/orchestrate/phase-works/phase-5/input-change-plan.md", "stale input\n")
        proc = subprocess.run(
            [
                sys.executable,
                str(self.refit_script),
                "--orchestrate-dir",
                str(self.orchestrate),
                "--mapping",
                str(self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"),
                "--config",
                str(config_path),
                "--output-orchestrate-dir",
                str(output_dir),
                "--write",
                "--validate-rendered",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            (output_dir / "phase-works/phase-5/input-change-plan.md").read_bytes(),
            (self.orchestrate / "phase-works/phase-4/input-change-plan.md").read_bytes(),
        )
        self.assertEqual(
            (output_dir / "change-plan.md").read_bytes(),
            (output_dir / "phase-works/phase-5/change-plan.md").read_bytes(),
        )
        self.assertTrue((output_dir / "change-capability-anchors/index.md").exists())
        rendered_plan = (output_dir / "phase-works/phase-5/change-plan.md").read_text(encoding="utf-8")
        self.assertIn("- 单一 intent：", rendered_plan)
        self.assertIn("- behavior completeness profile：", rendered_plan)
        self.assertNotIn("- vertical slice：", rendered_plan)
        self.assertTrue(
            (output_dir / "phase-works/phase-5/capability-baseline-reconciliation.json").exists()
        )
        self.assertTrue(
            (output_dir / "phase-works/phase-5/capability-baseline-reconciliation.md").exists()
        )
        packet_path = output_dir / "change-capability-anchors/change-a/change-a.md"
        self.assertTrue(packet_path.exists())
        packet = packet_path.read_text(encoding="utf-8")
        for atom_id in ("GA-0001", "GA-0002", "GA-0003", "GA-0004"):
            self.assertIn(atom_id, packet)
        self.assertIn("Related Capabilities", packet)
        self.assertIn("cap-support", packet)

        capability_view = (
            output_dir / "change-capability-anchors/change-a/capability-anchors/cap-a.md"
        ).read_text(encoding="utf-8")
        self.assertIn("GA-0001", capability_view)
        self.assertNotIn("GA-0002", capability_view)
        self.assertNotIn("GA-0003", capability_view)
        self.assertFalse(
            (output_dir / "change-capability-anchors/change-a/capability-anchors/cap-support.md").exists()
        )

        for derived_path in (
            "phase-works/phase-5/change-plan.md",
            "phase-works/phase-5/capability-progression-review.md",
            "phase-works/phase-5/change-complexity-review.md",
            "change-capability-anchors/index.md",
        ):
            derived = (output_dir / derived_path).read_text(encoding="utf-8")
            self.assertNotIn("cap-support", derived, derived_path)

    def test_phase5_refit_rejects_undeclared_spec_target(self) -> None:
        config_path = self.orchestrate / "phase-works/phase-5/phase5-refit.config.json"
        write_json(
            config_path,
            {
                "status": "adjusted",
                "changes": [
                    {
                        "slug": "change-a",
                        "title": "change-a",
                        "outcome": "Spec target 必须在 config capabilities 中声明。",
                        "kind": "business",
                    }
                ],
                "capabilities": [],
            },
        )
        output_dir = self.root / "out/orchestrate"
        proc = subprocess.run(
            [
                sys.executable,
                str(self.refit_script),
                "--orchestrate-dir",
                str(self.orchestrate),
                "--mapping",
                str(self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"),
                "--config",
                str(config_path),
                "--output-orchestrate-dir",
                str(output_dir),
                "--write",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("target capability 未在 config capabilities 中声明", proc.stderr)

    def test_phase5_refit_allows_change_only_plan_with_empty_capabilities(self) -> None:
        mapping_path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        former_spec = mapping["rows"][0]
        former_spec["phase-3-artifact-projection"] = "design-obligation"
        former_spec["final-artifact-projection"] = "design-obligation"
        former_spec["final-capability-impact"] = "none"
        former_spec["final-target-capability"] = "none"
        former_spec["related-capabilities"] = []
        write_json(mapping_path, mapping)

        config_path = self.orchestrate / "phase-works/phase-5/phase5-refit.config.json"
        write_json(
            config_path,
            {
                "status": "adjusted",
                "changes": [
                    {
                        "slug": "change-a",
                        "title": "change-a",
                        "outcome": "仅交付 change-owned design 与 verification 义务。",
                        "kind": "business",
                    }
                ],
                "capabilities": [],
            },
        )
        output_dir = self.root / "out/orchestrate"
        proc = subprocess.run(
            [
                sys.executable,
                str(self.refit_script),
                "--orchestrate-dir",
                str(self.orchestrate),
                "--mapping",
                str(mapping_path),
                "--config",
                str(config_path),
                "--output-orchestrate-dir",
                str(output_dir),
                "--write",
                "--validate-rendered",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            (output_dir / "change-plan.md").read_bytes(),
            (output_dir / "phase-works/phase-5/change-plan.md").read_bytes(),
        )
        plan = (output_dir / "phase-works/phase-5/change-plan.md").read_text(encoding="utf-8")
        self.assertIn("## Capability Map", plan)
        self.assertIn("本计划没有业务 Capability delta", plan)
        self.assertIn("不生成空矩阵", plan)
        capability_views = list(
            (output_dir / "change-capability-anchors/change-a/capability-anchors").glob("*.md")
        )
        self.assertEqual(capability_views, [])
        packet = (
            output_dir / "change-capability-anchors/change-a/change-a.md"
        ).read_text(encoding="utf-8")
        for atom_id in ("GA-0001", "GA-0002", "GA-0003", "GA-0004"):
            self.assertIn(atom_id, packet)

    def test_phase5_refit_helper_writes_foundation_executable_packet(self) -> None:
        self._convert_ga0002_to_foundation_change()
        mapping_path = self.orchestrate / "phase-works/phase-5/atom-plan-mapping.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        foundation_row = mapping["rows"][1]
        foundation_row["final-owner-change"] = "bootstrap-runtime-substrate"
        write_json(mapping_path, mapping)

        config_path = self.orchestrate / "phase-works/phase-5/phase5-refit.config.json"
        write_json(
            config_path,
            {
                "status": "adjusted",
                "changes": [
                    {
                        "slug": "bootstrap-runtime-substrate",
                        "title": "foundation",
                        "outcome": "底座候选输出为 executable foundation change。",
                        "kind": "foundation",
                    },
                    {
                        "slug": "change-a",
                        "title": "change-a",
                        "outcome": "业务 change 跟随 foundation packet。",
                        "kind": "business",
                    },
                ],
                "capabilities": [
                    {"slug": "runtime-substrate-foundation", "boundary": "工程底座 substrate。"},
                    {
                        "slug": "cap-a",
                        "boundary": "cap-a",
                        "baseline_status": "absent",
                        "baseline_evidence": "已只读检查精确 spec 路径，当前不存在。",
                    },
                ],
            },
        )
        output_dir = self.root / "out/orchestrate"
        proc = subprocess.run(
            [
                sys.executable,
                str(self.refit_script),
                "--orchestrate-dir",
                str(self.orchestrate),
                "--mapping",
                str(mapping_path),
                "--config",
                str(config_path),
                "--output-orchestrate-dir",
                str(output_dir),
                "--write",
                "--validate-rendered",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse((output_dir / "foundation-reference").exists())
        self.assertTrue((output_dir / "change-capability-anchors/bootstrap-runtime-substrate/bootstrap-runtime-substrate.md").exists())
        packet_index = json.loads((output_dir / "phase-works/phase-5/final-packet-index.json").read_text(encoding="utf-8"))
        self.assertEqual([packet["change"] for packet in packet_index["packets"]], ["bootstrap-runtime-substrate", "change-a"])
        self.assertEqual(packet_index["packets"][0]["change-kind"], "foundation")
        rendered_mapping = json.loads((output_dir / "phase-works/phase-5/atom-plan-mapping.json").read_text(encoding="utf-8"))
        self.assertEqual(rendered_mapping["rows"][1]["final-owner-type"], "executable-change")
        self.assertEqual(rendered_mapping["rows"][1]["final-owner-change"], "bootstrap-runtime-substrate")
        self.assertEqual(rendered_mapping["rows"][1]["final-capability-impact"], "foundation-substrate")
        self.assertEqual(rendered_mapping["rows"][1]["final-target-capability"], "runtime-substrate-foundation")
        plan = (output_dir / "phase-works/phase-5/change-plan.md").read_text(encoding="utf-8")
        matrix = plan.split("## Capability Progression Matrix", 1)[1].split("## Change Roadmap", 1)[0]
        self.assertIn("cap-a", matrix)
        self.assertNotIn("runtime-substrate-foundation", matrix)
        progression_review = (
            output_dir / "phase-works/phase-5/capability-progression-review.md"
        ).read_text(encoding="utf-8")
        self.assertIn("| `cap-a` |", progression_review)
        self.assertNotIn("| `runtime-substrate-foundation` |", progression_review)

    def test_phase5_non_direct_atom_missing_from_packet_fails(self) -> None:
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/change-a.md",
            "# change-a\n\n| Global Atom ID | Relation |\n| --- | --- |\n"
            "| GA-0001 | direct |\n"
            "| GA-0002 | direct |\n"
            "| GA-0003 | direct |\n",
        )
        self._write_manifest()
        self.assert_error("phase5-final-non-direct-packet")

    def test_phase5_non_direct_atom_missing_from_packet_index_fails(self) -> None:
        packet_path = self.orchestrate / "change-capability-anchors/change-a/change-a.md"
        packet = packet_path.read_text(encoding="utf-8").replace("| GA-0004 | non-goal |\n", "")
        packet_path.write_text(packet, encoding="utf-8")
        index_path = self.orchestrate / "phase-works/phase-5/final-packet-index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["packets"][0]["owner-scoped-non-direct-atom-ids"] = []
        index["packets"][0]["packet-digest"] = sha256_file(packet_path)
        write_json(index_path, index)
        self._write_manifest()
        self.assert_error("phase5-final-non-direct-packet-index")

    def test_capability_view_contains_non_direct_atom_fails(self) -> None:
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/capability-anchors/cap-a.md",
            "# cap-a\n\n| Global Atom ID | Relation |\n| --- | --- |\n| GA-0001 | direct |\n| GA-0004 | non-goal |\n",
        )
        self.assert_error("phase5-capability-view-non-direct")

    def test_capability_view_contains_change_only_direct_atom_fails(self) -> None:
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/capability-anchors/cap-a.md",
            "# cap-a\n\n| Global Atom ID | Relation |\n| --- | --- |\n"
            "| GA-0001 | direct |\n"
            "| GA-0002 | direct |\n",
        )
        self.assert_error("phase5-capability-view-non-advancing")

    def test_unindexed_capability_view_is_scanned_and_rejected(self) -> None:
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/capability-anchors/cap-support.md",
            "# stale related view\n\n| Global Atom ID | Relation |\n| --- | --- |\n| GA-0002 | direct |\n",
        )
        self._write_manifest()
        self.assert_error("phase5-capability-view-unindexed")

    def test_final_direct_table_capability_fields_must_match_mapping(self) -> None:
        packet_path = self.orchestrate / "change-capability-anchors/change-a/change-a.md"
        packet = packet_path.read_text(encoding="utf-8").replace(
            "| GA-0001 | new | cap-a | None | direct |",
            "| GA-0001 | modified | cap-a | None | direct |",
        )
        packet_path.write_text(packet, encoding="utf-8")
        index_path = self.orchestrate / "phase-works/phase-5/final-packet-index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["packets"][0]["packet-digest"] = sha256_file(packet_path)
        write_json(index_path, index)
        self._write_manifest()
        self.assert_error("phase5-final-direct-table-drift")

    def test_phase2_line_ranges_participate_in_render_drift(self) -> None:
        path = self.orchestrate / "phase-works/phase-2/source-obligation-atoms/docs--source.atoms.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source-atoms"][1]["line-ranges"] = [{"start": 3, "end": 5}]
        write_json(path, data)
        self._write_manifest()
        self.assert_error("rendered-markdown-drift")

    def test_phase3_source_map_candidate_fields_must_match_phase2_evidence(self) -> None:
        path = self.orchestrate / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"][1]["candidate-target-capability"] = "other-cap"
        write_json(path, data)
        render_orchestrate(self.orchestrate, "phase3-source-map", write=True)
        self._write_manifest()
        self.assert_error("phase3-map-candidate-drift")

    def test_strict_warnings_returns_non_zero(self) -> None:
        self._write(
            "openspec/orchestrate/phase-works/phase-5/change-complexity-review.md",
            "| Change | Direct Atom Count | Budget Status |\n| --- | --- | --- |\n| change-a | 3 | hard-over-budget |\n",
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(self.script),
                "--orchestrate-dir",
                str(self.orchestrate),
                "--workspace-root",
                str(self.root),
                "--phase",
                "all",
                "--complete",
                "--json",
                "--strict-warnings",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["error-count"], 0, payload)
        self.assertGreater(payload["warning-count"], 0, payload)

    def test_cli_help_is_chinese_and_flags_remain_stable(self) -> None:
        scripts_and_markers = [
            (self.script, "校验 source-aligned orchestrate trace sidecar。", "--strict-warnings"),
            (self.refit_script, "根据已审阅的 mapping/config 校验并渲染", "--print-config-template"),
            (SCRIPT_DIR / "render_source_aligned_orchestrate.py", "根据 canonical JSON sidecar 渲染", "--source-document"),
            (SCRIPT_DIR / "phase3_line_range_audit.py", "审计 Phase 3 source atom", "--from-markdown"),
        ]
        for script, chinese_marker, stable_flag in scripts_and_markers:
            with self.subTest(script=script.name):
                proc = subprocess.run(
                    [sys.executable, str(script), "--help"],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn(chinese_marker, proc.stdout)
                self.assertIn(stable_flag, proc.stdout)

    def test_cli_diagnostic_is_chinese_and_json_contract_is_stable(self) -> None:
        missing = self.root / "missing-orchestrate"
        proc = subprocess.run(
            [
                sys.executable,
                str(self.script),
                "--orchestrate-dir",
                str(missing),
                "--workspace-root",
                str(self.root),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(set(payload), {"ok", "error-count", "warning-count", "issues"})
        self.assertEqual(payload["issues"][0]["rule_id"], "orchestrate-dir")
        self.assertEqual(payload["issues"][0]["severity"], "error")
        self.assertIn("目录不存在", payload["issues"][0]["message"])

    def test_rendered_markdown_localizes_prose_but_preserves_table_contract(self) -> None:
        result = render_orchestrate(self.orchestrate, "phase3-global-index", write=True)
        self.assertTrue(result["ok"], result)
        rendered = (
            self.orchestrate / "change-capability-anchors/obligation-atom-index.md"
        ).read_text(encoding="utf-8")
        self.assertIn("# obligation atom 索引", rendered)
        self.assertIn("| Global Atom ID | Source Document | Lines | Atom Type |", rendered)
        sidecar = json.loads(
            (self.orchestrate / "change-capability-anchors/obligation-atom-index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(sidecar["trace-schema"], GLOBAL_ATOM_INDEX_SCHEMA)
        self.assertEqual(sidecar["trace-contract-version"], TRACE_CONTRACT_VERSION)


if __name__ == "__main__":
    unittest.main()
