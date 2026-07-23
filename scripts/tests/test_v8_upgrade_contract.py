#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused v8 hard-cut, role-isolation and completeness contract tests."""

from __future__ import annotations

import copy
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

from review_fixture_v8 import write_review_result  # noqa: E402
from source_aligned_trace_lib import (  # noqa: E402
    FINAL_INTEGRATION_REVIEW_SCHEMA,
    MANIFEST_SCHEMA,
    MAX_BOUNDED_REPAIRS,
    MAX_BOUNDED_REVIEWS,
    PHASE1_REVIEW_CHECKS,
    PHASE1_REVIEW_RESULT_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    REPAIR_REFERENCE_ALLOWLISTS,
    REVIEWER_REFERENCE_ALLOWLISTS,
    TRACE_CONTRACT_VERSION,
    WRITER_REFERENCE_ALLOWLISTS,
    bounded_review_result_path,
    evidence_authority_sha256,
    require_phase3_frozen_evidence,
    sha256_file,
    write_bounded_review_result_exclusive,
    write_json,
)
from source_aligned_v8_contract import (  # noqa: E402
    load_final_integration_review,
)
from test_source_aligned_v8_contract import _review  # noqa: E402
from test_v8_frozen_evidence_authority import (  # noqa: E402
    FrozenEvidenceFixture,
)
from validate_source_aligned_orchestrate import (  # noqa: E402
    _validate_phase3_review_gate,
    expected_manifest_artifacts,
    IssueReporter,
)


class V8UpgradeContractTests(unittest.TestCase):
    def test_version_registry_is_hard_switched(self) -> None:
        self.assertEqual(TRACE_CONTRACT_VERSION, "source-aligned-trace-v8")
        self.assertEqual(
            MANIFEST_SCHEMA,
            "source-aligned-orchestrate-manifest-v4",
        )
        self.assertEqual(
            PHASE_TRACE_SCHEMAS,
            {
                "phase-1": "source-aligned-phase-1-trace-v5",
                "phase-2": "source-aligned-phase-2-trace-v6",
                "phase-3": "source-aligned-phase-3-trace-v6",
                "phase-4": "source-aligned-phase-4-trace-v6",
                "phase-5": "source-aligned-phase-5-trace-v7",
            },
        )

    def test_all_bounded_gates_share_five_four_budget(self) -> None:
        self.assertEqual(MAX_BOUNDED_REVIEWS, 5)
        self.assertEqual(MAX_BOUNDED_REPAIRS, 4)

    def test_writer_allowlists_exclude_control_oracles(self) -> None:
        forbidden = {
            "references/review-gates.md",
            "references/bounded-repair-contract.md",
            "references/trace-sidecar-contract.md",
        }
        for phase, references in WRITER_REFERENCE_ALLOWLISTS.items():
            with self.subTest(phase=phase):
                self.assertTrue(forbidden.isdisjoint(references))

    def test_reviewer_and_repair_allowlists_are_isolated(self) -> None:
        for phase in ("phase-1", "phase-3", "phase-5"):
            with self.subTest(phase=phase):
                self.assertIn(
                    "references/review-gates.md",
                    REVIEWER_REFERENCE_ALLOWLISTS[phase],
                )
                self.assertNotIn(
                    "references/bounded-repair-contract.md",
                    REVIEWER_REFERENCE_ALLOWLISTS[phase],
                )
                self.assertIn(
                    "references/bounded-repair-contract.md",
                    REPAIR_REFERENCE_ALLOWLISTS[phase],
                )
                self.assertNotIn(
                    "references/review-gates.md",
                    REPAIR_REFERENCE_ALLOWLISTS[phase],
                )

    def test_all_allowlisted_reference_files_exist(self) -> None:
        skill_root = SCRIPT_DIR.parent
        groups = (
            WRITER_REFERENCE_ALLOWLISTS,
            REVIEWER_REFERENCE_ALLOWLISTS,
            REPAIR_REFERENCE_ALLOWLISTS,
        )
        for group in groups:
            for references in group.values():
                for relative in references:
                    self.assertTrue((skill_root / relative).is_file())

    def test_review_result_paths_are_unique_and_bounded(self) -> None:
        root = Path("/tmp/orchestrate")
        paths = {
            bounded_review_result_path(root, "phase-1", round_number)
            for round_number in range(1, 6)
        }
        self.assertEqual(len(paths), 5)
        with self.assertRaisesRegex(ValueError, "round非法"):
            bounded_review_result_path(root, "phase-1", 6)

    def test_review_result_exclusive_create_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate = repo / "openspec/orchestrate-v8"
            payload = {
                "trace-schema": PHASE1_REVIEW_RESULT_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "phase": "phase-1",
                "round": 1,
                "reviewer-id": "fresh-reviewer-1",
                "validator-status": "passed",
                "initial-framework-sha256": "1" * 64,
                "initial-change-plan-sha256": "2" * 64,
                "semantic-checks": [
                    {"check": check, "result": "passed"}
                    for check in PHASE1_REVIEW_CHECKS
                ],
                "findings": [],
                "warnings": [],
                "finding-count": 0,
                "decision": "passed",
                "language-self-check": "所有说明均使用简体中文。",
            }
            reference = write_bounded_review_result_exclusive(
                orchestrate,
                repo,
                "phase-1",
                1,
                payload,
            )
            path = bounded_review_result_path(
                orchestrate,
                "phase-1",
                1,
            )
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_bounded_review_result_exclusive(
                    orchestrate,
                    repo,
                    "phase-1",
                    1,
                    payload,
                )
            after = path.read_bytes()
            current_digest = sha256_file(path)
        self.assertEqual(after, before)
        self.assertEqual(
            reference["review-result-sha256"],
            current_digest,
        )

    def test_manifest_registers_review_results_as_control(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate = repo / "openspec/orchestrate-v8"
            path = bounded_review_result_path(
                orchestrate,
                "phase-1",
                1,
            )
            path.parent.mkdir(parents=True)
            path.write_text("{}\n", encoding="utf-8")
            specs = expected_manifest_artifacts(orchestrate, repo)
            relative = path.relative_to(repo).as_posix()
        self.assertEqual(
            specs[relative],
            (
                "source-aligned-phase-1-review-result-v1",
                "phase-1",
                "control",
                "bounded-review-result",
            ),
        )

    def test_v8_helper_rejects_v7_generation_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate = repo / "openspec/orchestrate-v7-copy"
            trace_path = orchestrate / "trace/phase-1.trace.json"
            write_json(
                trace_path,
                {
                    "trace-schema": "source-aligned-phase-1-trace-v4",
                    "trace-contract-version": "source-aligned-trace-v7",
                    "status": "initial-plan-written",
                    "source-documents": [],
                    "initial-framework": {},
                    "initial-change-plan": {},
                    "review-gate": {},
                },
            )
            before = trace_path.read_bytes()
            with self.assertRaisesRegex(
                ValueError,
                "当前trace contract",
            ):
                require_phase3_frozen_evidence(orchestrate, repo)
            after = trace_path.read_bytes()
        self.assertEqual(after, before)

    def test_failed_dependency_set_blocks_final_review(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "final-integration-review.json"
            payload = _review("a" * 64)
            payload["dependency-set-result"]["result"] = "failed"
            write_json(path, payload)
            with self.assertRaisesRegex(
                ValueError,
                "dependency set completeness",
            ):
                load_final_integration_review(
                    path,
                    expected_terminal_digest="a" * 64,
                )

    def test_missing_dependency_set_blocks_final_review(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "final-integration-review.json"
            payload = _review("a" * 64)
            payload.pop("dependency-set-result")
            write_json(path, payload)
            with self.assertRaisesRegex(
                ValueError,
                "dependency-set-result",
            ):
                load_final_integration_review(
                    path,
                    expected_terminal_digest="a" * 64,
                )

    def test_phase3_accepts_five_review_four_repair_pass_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = FrozenEvidenceFixture(Path(raw))
            current_digest = evidence_authority_sha256(
                fixture.orchestrate,
                fixture.root,
            )
            digests = ["1" * 64, "2" * 64, "3" * 64, "4" * 64, current_digest]
            reviews = []
            for index, digest in enumerate(digests, start=1):
                reviews.append(
                    write_review_result(
                        fixture.orchestrate,
                        fixture.root,
                        phase="phase-3",
                        round_number=index,
                        decision=(
                            "passed"
                            if index == 5
                            else "repair-required"
                        ),
                        authority={
                            "evidence-authority-sha256": digest,
                        },
                    )
                )
            repairs = [
                {
                    "round": index,
                    "repair-writer-id": f"phase3-repair-{index}",
                    "source-review-result-sha256": reviews[index - 1][
                        "review-result-sha256"
                    ],
                    "before-evidence-authority-sha256": digests[index - 1],
                    "after-evidence-authority-sha256": digests[index],
                }
                for index in range(1, 5)
            ]
            trace_path = fixture.orchestrate / "trace/phase-3.trace.json"
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            review_gate = copy.deepcopy(trace["review-gate"])
            review_gate.update(
                {
                    "status": "passed",
                    "terminal-reason": "none",
                    "reviews": reviews,
                    "repairs": repairs,
                }
            )
            reporter = IssueReporter()
            status = _validate_phase3_review_gate(
                review_gate,
                trace_path,
                fixture.orchestrate,
                fixture.root,
                reporter,
            )
            pending_gate = copy.deepcopy(review_gate)
            pending_gate["status"] = "pending"
            pending_reporter = IssueReporter()
            _validate_phase3_review_gate(
                pending_gate,
                trace_path,
                fixture.orchestrate,
                fixture.root,
                pending_reporter,
            )
        self.assertEqual(status, "passed")
        self.assertEqual(reporter.result()["issues"], [])
        self.assertIn(
            "phase3-review-budget",
            {issue.rule_id for issue in pending_reporter.issues},
        )

    def test_phase3_authority_drift_is_a_legal_immediate_block(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = FrozenEvidenceFixture(Path(raw))
            trace_path = fixture.orchestrate / "trace/phase-3.trace.json"
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            review_gate = copy.deepcopy(trace["review-gate"])
            review_gate["status"] = "blocked"
            review_gate["terminal-reason"] = "authority-integrity"
            review_gate["reviews"][0]["review-result-sha256"] = "0" * 64
            reporter = IssueReporter()
            status = _validate_phase3_review_gate(
                review_gate,
                trace_path,
                fixture.orchestrate,
                fixture.root,
                reporter,
            )
        self.assertEqual(status, "blocked")
        self.assertEqual(reporter.result()["issues"], [])


if __name__ == "__main__":
    unittest.main()
