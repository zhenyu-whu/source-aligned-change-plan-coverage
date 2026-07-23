#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 5 对 Phase 2/3 frozen evidence authority 的绑定测试。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = TEST_DIR.parent
for candidate in (str(TEST_DIR), str(SCRIPT_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from source_aligned_trace_lib import (  # noqa: E402
    GLOBAL_ATOM_INDEX_SCHEMA,
    INITIAL_FRAMEWORK_SCHEMA,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    PHASE1_REVIEW_CHECKS,
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    evidence_authority_sha256,
    require_phase3_frozen_evidence,
    sha256_file,
    write_json,
)
from render_source_aligned_orchestrate import (  # noqa: E402
    render_coverage_review,
    render_global_index,
    render_initial_framework,
    render_phase2_index,
    render_phase2_source_atoms,
)
from test_source_aligned_v7_contract import (  # noqa: E402
    _base_initial_framework,
)


class FrozenEvidenceFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.orchestrate = root / "openspec/orchestrate-v7"
        self.source = root / "docs/source.md"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("读者必须得到可读取报告。\n", encoding="utf-8")

        phase1_dir = self.orchestrate / "phase-works/phase-1"
        framework_path = phase1_dir / "initial-framework.json"
        framework = _base_initial_framework()
        framework["trace-schema"] = INITIAL_FRAMEWORK_SCHEMA
        framework["artifact-path"] = (
            "openspec/orchestrate-v7/phase-works/phase-1/"
            "initial-change-plan.md"
        )
        write_json(framework_path, framework)
        plan_path = phase1_dir / "initial-change-plan.md"
        plan_path.write_text(
            render_initial_framework(self.orchestrate, framework_path),
            encoding="utf-8",
        )
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
                        "报告交付 | 冻结证据测试来源 |"
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
                        "coarse-topics-paths": "报告交付",
                        "notes": "冻结证据测试来源",
                        "line-count": 1,
                        "source-sha256": sha256_file(self.source),
                    }
                ],
                "initial-framework": {
                    "artifact-path": (
                        "openspec/orchestrate-v7/phase-works/phase-1/"
                        "initial-framework.json"
                    ),
                    "sha256": sha256_file(framework_path),
                },
                "initial-change-plan": {
                    "artifact-path": (
                        "openspec/orchestrate-v7/phase-works/phase-1/"
                        "initial-change-plan.md"
                    ),
                    "sha256": sha256_file(plan_path),
                },
                "review-gate": {
                    "status": "passed",
                    "writer-id": "phase1-writer",
                    "reviews": [
                        {
                            "round": 1,
                            "reviewer-id": "phase1-reviewer",
                            "validator-status": "passed",
                            "initial-framework-sha256": sha256_file(
                                framework_path
                            ),
                            "initial-change-plan-sha256": sha256_file(
                                plan_path
                            ),
                            "semantic-checks": [
                                {
                                    "check": check,
                                    "result": "passed",
                                }
                                for check in PHASE1_REVIEW_CHECKS
                            ],
                            "finding-fingerprints": [],
                        }
                    ],
                    "repairs": [],
                },
            },
        )

        atom_root = (
            self.orchestrate
            / "phase-works/phase-2/source-obligation-atoms"
        )
        atom_path = atom_root / "docs--source.atoms.json"
        write_json(
            atom_path,
            {
                "trace-schema": SOURCE_ATOMS_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "source-document": "docs/source.md",
                "source-sha256": sha256_file(self.source),
                "read-status": "read-full",
                "canonical-owner": "phase2-source-writer",
                "source-role": "primary",
                "phase-1-candidate-changes-capabilities-considered": [],
                "source-atoms": [
                    {
                        "source-atom-id": "SA-0001",
                        "line-ranges": [{"start": 1, "end": 1}],
                        "source-fact": "读者必须得到可读取报告。",
                        "atom-type": "behavior",
                        "normativity": "must",
                        "candidate-status": "direct-candidate",
                        "candidate-artifact-projection": (
                            "spec-requirement"
                        ),
                        "candidate-owner-change": "ship-report",
                        "candidate-target-capability": "report-delivery",
                        "delivery-directives": [],
                        "rationale": "来源直接要求交付可读取报告。",
                    }
                ],
                "blockers": [],
                "language-self-check": "所有解释字段均使用简体中文。",
            },
        )
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
            "# Phase 2 Agent Report\n\n来源原子提取完成。\n",
            encoding="utf-8",
        )
        write_json(
            self.orchestrate / "trace/phase-2.trace.json",
            {
                "trace-schema": PHASE_TRACE_SCHEMAS["phase-2"],
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": "source-atoms-written",
                "work-queue-path": (
                    "openspec/orchestrate-v7/phase-works/phase-2/"
                    "source-obligation-atoms/work-queue.md"
                ),
                "sources": [
                    {
                        "source-document": "docs/source.md",
                        "atom-json-path": (
                            "openspec/orchestrate-v7/phase-works/phase-2/"
                            "source-obligation-atoms/docs--source.atoms.json"
                        ),
                        "atom-json-sha256": sha256_file(atom_path),
                        "atom-markdown-path": (
                            "openspec/orchestrate-v7/phase-works/phase-2/"
                            "source-obligation-atoms/docs--source.atoms.md"
                        ),
                        "canonical-owner": "phase2-source-writer",
                        "read-status": "read-full",
                        "atom-count": 1,
                        "delivery-directive-atom-count": 0,
                        "blockers": [],
                    }
                ],
                "phase-report-path": (
                    "openspec/orchestrate-v7/phase-works/phase-2/"
                    "phase-2-agent-report.md"
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
        write_json(
            global_path,
            {
                "trace-schema": GLOBAL_ATOM_INDEX_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "artifact-path": (
                    "openspec/orchestrate-v7/change-capability-anchors/"
                    "obligation-atom-index.md"
                ),
                "global-atoms": [
                    {
                        "global-atom-id": "GA-0001",
                        "evidence-ref": {
                            "kind": "phase-2-source-atom",
                            "source-document": "docs/source.md",
                            "source-atom-id": "SA-0001",
                        },
                    }
                ],
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
                "artifact-path": (
                    "openspec/orchestrate-v7/phase-works/phase-3/"
                    "coverage-review.md"
                ),
                "documents": [
                    {
                        "source-document": "docs/source.md",
                        "source-sha256": sha256_file(self.source),
                        "line-count": 1,
                        "phase-2-atom-path": (
                            "openspec/orchestrate-v7/phase-works/phase-2/"
                            "source-obligation-atoms/docs--source.atoms.json"
                        ),
                        "phase-2-atom-sha256": sha256_file(atom_path),
                        "covered-ranges": [{"start": 1, "end": 1}],
                        "candidate-uncovered-ranges": [],
                    }
                ],
                "gap-atoms": [],
                "remainder-dispositions": [],
                "mapping-ambiguities": [],
                "summary": {
                    "source-documents": 1,
                    "phase-2-atoms": 1,
                    "gap-atoms": 0,
                    "global-atoms": 1,
                    "mapping-ambiguities": 0,
                    "candidate-uncovered-ranges": 0,
                    "remainder-dispositions": {
                        "blocked": 0,
                        "missing-obligation": 0,
                        "safe-non-obligation": 0,
                    },
                    "delivery-directive-atoms": 0,
                    "delivery-directives": {
                        "milestone-scope": 0,
                        "explicit-precedence": 0,
                        "explicit-deferred": 0,
                    },
                },
                "decision": "coverage-complete",
                "language-self-check": "所有解释字段均使用简体中文。",
            },
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
        write_json(
            self.orchestrate / "trace/phase-3.trace.json",
            {
                "trace-schema": PHASE_TRACE_SCHEMAS["phase-3"],
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "decision": "coverage-complete",
                "global-atom-index-path": (
                    "openspec/orchestrate-v7/change-capability-anchors/"
                    "obligation-atom-index.json"
                ),
                "global-atom-index-sha256": sha256_file(global_path),
                "coverage-review-path": (
                    "openspec/orchestrate-v7/phase-works/phase-3/"
                    "coverage-review.json"
                ),
                "coverage-review-sha256": sha256_file(coverage_path),
                "review-gate": {
                    "status": "passed",
                    "phase-2-canonical-owner-ids": [
                        "phase2-source-writer"
                    ],
                    "phase-2-aggregate-writer-id": (
                        "phase2-aggregate-writer"
                    ),
                    "phase-3-writer-id": "phase3-writer",
                    "reviews": [
                        {
                            "round": 1,
                            "stage": "phase-3-closure",
                            "reviewer-id": "phase3-reviewer",
                            "phase-2-validator-status": "passed",
                            "phase-3-validator-status": "passed",
                            "delivery-directive-status": "passed",
                            "evidence-authority-sha256": evidence_digest,
                            "finding-fingerprints": [],
                        }
                    ],
                    "repairs": [],
                },
                "issues": [],
            },
        )

    def refreeze_phase3(self) -> None:
        """Rebind the freeze marker after an intentional malformed edit."""
        global_path = (
            self.orchestrate
            / "change-capability-anchors/obligation-atom-index.json"
        )
        coverage_path = (
            self.orchestrate
            / "phase-works/phase-3/coverage-review.json"
        )
        trace_path = self.orchestrate / "trace/phase-3.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["global-atom-index-sha256"] = sha256_file(global_path)
        trace["coverage-review-sha256"] = sha256_file(coverage_path)
        trace["review-gate"]["reviews"][-1][
            "evidence-authority-sha256"
        ] = evidence_authority_sha256(self.orchestrate, self.root)
        write_json(trace_path, trace)


class FrozenEvidenceAuthorityTests(unittest.TestCase):
    def test_terminal_freeze_binds_actual_source_atoms_and_phase3_trace(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = FrozenEvidenceFixture(Path(raw))
            result = require_phase3_frozen_evidence(
                fixture.orchestrate,
                fixture.root,
            )
            self.assertRegex(
                result["frozen-evidence-authority-sha256"],
                r"^[0-9a-f]{64}$",
            )
            self.assertEqual(
                result["phase-3-freeze-trace-sha256"],
                sha256_file(
                    fixture.orchestrate / "trace/phase-3.trace.json"
                ),
            )

    def test_source_bytes_drift_is_rejected_even_when_trace_is_unchanged(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = FrozenEvidenceFixture(Path(raw))
            fixture.source.write_text("来源已经被替换。\n", encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,
                "Phase 2 atom source/owner/rows非法",
            ):
                require_phase3_frozen_evidence(
                    fixture.orchestrate,
                    fixture.root,
                )

    def test_atom_bytes_drift_invalidates_terminal_phase3_review(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = FrozenEvidenceFixture(Path(raw))
            atom_path = (
                fixture.orchestrate
                / "phase-works/phase-2/source-obligation-atoms/"
                "docs--source.atoms.json"
            )
            atom = json.loads(atom_path.read_text(encoding="utf-8"))
            atom["source-atoms"][0]["source-fact"] = "未经冻结的新原文"
            write_json(atom_path, atom)
            with self.assertRaisesRegex(
                ValueError,
                "Phase 2 trace未绑定当前atom authority",
            ):
                require_phase3_frozen_evidence(
                    fixture.orchestrate,
                    fixture.root,
                )

    def test_nonterminal_phase3_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = FrozenEvidenceFixture(Path(raw))
            trace_path = fixture.orchestrate / "trace/phase-3.trace.json"
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            trace["decision"] = "review-pending"
            trace["review-gate"]["status"] = "pending"
            write_json(trace_path, trace)
            with self.assertRaisesRegex(ValueError, "coverage-complete"):
                require_phase3_frozen_evidence(
                    fixture.orchestrate,
                    fixture.root,
                )

    def test_canonical_gate_and_review_identities_are_required(self) -> None:
        mutations = (
            (
                "gate-owner-identities",
                lambda trace: trace["review-gate"].pop(
                    "phase-2-canonical-owner-ids"
                ),
                "canonical Phase 3 passed review-gate",
            ),
            (
                "reviewer-identity",
                lambda trace: trace["review-gate"]["reviews"][-1].pop(
                    "reviewer-id"
                ),
                "review history字段或round非法",
            ),
        )
        for label, mutate, message in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                fixture = FrozenEvidenceFixture(Path(raw))
                trace_path = (
                    fixture.orchestrate / "trace/phase-3.trace.json"
                )
                trace = json.loads(trace_path.read_text(encoding="utf-8"))
                mutate(trace)
                write_json(trace_path, trace)
                with self.assertRaisesRegex(ValueError, message):
                    require_phase3_frozen_evidence(
                        fixture.orchestrate,
                        fixture.root,
                    )

    def test_canonical_coverage_and_global_index_fields_are_required(
        self,
    ) -> None:
        mutations = (
            (
                "coverage-documents",
                (
                    "phase-works/phase-3/coverage-review.json",
                    "documents",
                ),
                "coverage review必须是coverage-complete",
            ),
            (
                "global-artifact-path",
                (
                    "change-capability-anchors/"
                    "obligation-atom-index.json",
                    "artifact-path",
                ),
                "Phase 1/2/3 frozen evidence未通过canonical validator",
            ),
        )
        for label, (relative, field), message in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                fixture = FrozenEvidenceFixture(Path(raw))
                path = fixture.orchestrate / relative
                data = json.loads(path.read_text(encoding="utf-8"))
                data.pop(field)
                write_json(path, data)
                fixture.refreeze_phase3()
                with self.assertRaisesRegex(ValueError, message):
                    require_phase3_frozen_evidence(
                        fixture.orchestrate,
                        fixture.root,
                    )

    def test_canonical_markdown_mirrors_are_required(self) -> None:
        for relative in (
            "change-capability-anchors/obligation-atom-index.md",
            "phase-works/phase-3/coverage-review.md",
            (
                "phase-works/phase-2/source-obligation-atoms/"
                "docs--source.atoms.md"
            ),
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as raw:
                fixture = FrozenEvidenceFixture(Path(raw))
                (fixture.orchestrate / relative).unlink()
                with self.assertRaisesRegex(
                    ValueError,
                    "Phase 1/2/3 frozen evidence未通过canonical validator",
                ):
                    require_phase3_frozen_evidence(
                        fixture.orchestrate,
                        fixture.root,
                    )

    def test_phase2_atom_authority_root_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = FrozenEvidenceFixture(Path(raw))
            atom_root = (
                fixture.orchestrate
                / "phase-works/phase-2/source-obligation-atoms"
            )
            real_root = atom_root.with_name("source-obligation-atoms-real")
            atom_root.rename(real_root)
            atom_root.symlink_to(real_root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                require_phase3_frozen_evidence(
                    fixture.orchestrate,
                    fixture.root,
                )


if __name__ == "__main__":
    unittest.main()
