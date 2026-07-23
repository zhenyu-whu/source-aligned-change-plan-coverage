#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 1 bounded review 中间态的聚焦契约测试。"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from source_aligned_trace_lib import (  # noqa: E402
    MANIFEST_SCHEMA,
    PHASE1_REVIEW_CHECKS,
    PHASE_TRACE_SCHEMAS,
    TRACE_CONTRACT_VERSION,
    IssueReporter,
)
from render_source_aligned_orchestrate import render_initial_framework  # noqa: E402
from test_source_aligned_v7_contract import _base_initial_framework  # noqa: E402
from validate_source_aligned_orchestrate import (  # noqa: E402
    _validate_phase1_review_gate,
    validate_manifest,
    validate_phase_1,
    validate_trace_status,
)


FINDING_A = "a" * 64
FINDING_B = "b" * 64
FINDING_C = "c" * 64


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _checks(*, passed: bool = True) -> List[Dict[str, str]]:
    return [
        {
            "check": check,
            "result": "passed" if passed else "failed",
        }
        for check in PHASE1_REVIEW_CHECKS
    ]


def _review(
    round_number: int,
    framework_sha: str,
    plan_sha: str,
    *,
    findings: List[str] | None = None,
    passed: bool = False,
) -> Dict[str, object]:
    return {
        "round": round_number,
        "reviewer-id": f"phase1-reviewer-{round_number}",
        "validator-status": "passed" if passed else "failed",
        "initial-framework-sha256": framework_sha,
        "initial-change-plan-sha256": plan_sha,
        "semantic-checks": _checks(passed=passed),
        "finding-fingerprints": [] if findings is None else findings,
    }


def _repair(
    round_number: int,
    before_sha: str,
    after_sha: str,
    finding: str,
) -> Dict[str, object]:
    return {
        "round": round_number,
        "repair-writer-id": f"phase1-repair-writer-{round_number}",
        "finding-fingerprints": [finding],
        "before-initial-framework-sha256": before_sha,
        "after-initial-framework-sha256": after_sha,
    }


def _gate(
    status: str,
    reviews: List[Dict[str, object]],
    repairs: List[Dict[str, object]],
) -> Dict[str, object]:
    return {
        "status": status,
        "writer-id": "phase1-writer",
        "reviews": reviews,
        "repairs": repairs,
    }


class Phase1ReviewStateTests(unittest.TestCase):
    def _validate(
        self,
        root: Path,
        gate: Dict[str, object],
        *,
        framework: bytes = b"framework-current\n",
        plan: bytes = b"plan-current\n",
    ) -> IssueReporter:
        framework_path = root / "initial-framework.json"
        plan_path = root / "initial-change-plan.md"
        framework_path.write_bytes(framework)
        plan_path.write_bytes(plan)
        reporter = IssueReporter()
        _validate_phase1_review_gate(
            gate,
            root / "phase-1.trace.json",
            framework_path,
            plan_path,
            reporter,
        )
        return reporter

    def _write_phase1_generation(
        self,
        root: Path,
        *,
        trace_status: str,
        gate_status: str,
    ) -> Path:
        orchestrate = root / "openspec/orchestrate"
        phase1_dir = orchestrate / "phase-works/phase-1"
        trace_dir = orchestrate / "trace"
        source_path = root / "docs/source.md"
        source_path.parent.mkdir(parents=True)
        source_path.write_text("来源要求。\n", encoding="utf-8")
        phase1_dir.mkdir(parents=True)
        trace_dir.mkdir(parents=True)

        framework_path = phase1_dir / "initial-framework.json"
        framework_path.write_text(
            json.dumps(
                _base_initial_framework(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        plan_path = phase1_dir / "initial-change-plan.md"
        plan_path.write_text(
            render_initial_framework(orchestrate, framework_path),
            encoding="utf-8",
        )
        (phase1_dir / "phase-1-agent-report.md").write_text(
            "Phase 1 writer报告。\n",
            encoding="utf-8",
        )
        (phase1_dir / "source-doc-manifest.md").write_text(
            "\n".join(
                [
                    "| Source Document | Read Status | Source Role | Coarse Topics / Paths | Notes |",
                    "| --- | --- | --- | --- | --- |",
                    "| docs/source.md | read-full | primary | outcome | none |",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        framework_sha = _sha(framework_path.read_bytes())
        plan_sha = _sha(plan_path.read_bytes())
        reviews = (
            [_review(1, framework_sha, plan_sha, passed=True)]
            if gate_status == "passed"
            else []
        )
        trace = {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-1"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": trace_status,
            "source-documents": [
                {
                    "source-document": "docs/source.md",
                    "read-status": "read-full",
                    "source-role": "primary",
                    "coarse-topics-paths": "outcome",
                    "notes": "none",
                    "line-count": 1,
                    "source-sha256": _sha(source_path.read_bytes()),
                }
            ],
            "initial-framework": {
                "artifact-path": (
                    "openspec/orchestrate/phase-works/phase-1/"
                    "initial-framework.json"
                ),
                "sha256": framework_sha,
            },
            "initial-change-plan": {
                "artifact-path": (
                    "openspec/orchestrate/phase-works/phase-1/"
                    "initial-change-plan.md"
                ),
                "sha256": plan_sha,
            },
            "review-gate": _gate(gate_status, reviews, []),
        }
        (trace_dir / "phase-1.trace.json").write_text(
            json.dumps(
                trace,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return orchestrate

    def test_trace_accepts_review_pending_before_first_reviewer(self) -> None:
        reporter = IssueReporter()
        status = validate_trace_status(
            {"status": "review-pending"},
            Path("phase-1.trace.json"),
            reporter,
            "phase-1",
            "phase1-status",
        )

        self.assertEqual(status, "review-pending")
        self.assertEqual(reporter.error_count, 0)

    def test_pending_accepts_zero_reviews_and_repairs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            reporter = self._validate(
                Path(raw),
                _gate("pending", [], []),
            )

        self.assertEqual(reporter.result()["issues"], [])

    def test_phase1_generation_accepts_pending_trace_and_empty_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate = self._write_phase1_generation(
                root,
                trace_status="review-pending",
                gate_status="pending",
            )
            reporter = IssueReporter()
            validate_phase_1(orchestrate, root, reporter)

        self.assertEqual(reporter.result()["issues"], [])

    def test_terminal_trace_rejects_pending_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate = self._write_phase1_generation(
                root,
                trace_status="initial-plan-written",
                gate_status="pending",
            )
            reporter = IssueReporter()
            validate_phase_1(orchestrate, root, reporter)

        self.assertIn(
            "phase1-status-review-gate-drift",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_review_pending_trace_rejects_passed_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate = self._write_phase1_generation(
                root,
                trace_status="review-pending",
                gate_status="passed",
            )
            reporter = IssueReporter()
            validate_phase_1(orchestrate, root, reporter)

        self.assertIn(
            "phase1-status-review-gate-drift",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_terminal_trace_accepts_strict_passed_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate = self._write_phase1_generation(
                root,
                trace_status="initial-plan-written",
                gate_status="passed",
            )
            reporter = IssueReporter()
            validate_phase_1(orchestrate, root, reporter)

        self.assertEqual(reporter.result()["issues"], [])

    def test_pending_manifest_accepts_phase1_review_pending(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate = root / "openspec/orchestrate"
            trace_dir = orchestrate / "trace"
            trace_dir.mkdir(parents=True)
            (trace_dir / "phase-1.trace.json").write_text(
                json.dumps({"status": "review-pending"}) + "\n",
                encoding="utf-8",
            )
            manifest = {
                "trace-schema": MANIFEST_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "authority": "control",
                "orchestrate-dir": "openspec/orchestrate",
                "phase-statuses": {
                    "phase-1": "review-pending",
                    "phase-2": "missing",
                    "phase-3": "missing",
                    "phase-4": "missing",
                    "phase-5": "missing",
                },
                "workflow-status": "pending",
                "artifacts": [],
            }
            (trace_dir / "manifest.json").write_text(
                json.dumps(manifest) + "\n",
                encoding="utf-8",
            )
            reporter = IssueReporter()
            with mock.patch(
                "validate_source_aligned_orchestrate.expected_manifest_artifacts",
                return_value={},
            ):
                validate_manifest(
                    orchestrate,
                    root,
                    reporter,
                    complete=False,
                )

        self.assertEqual(reporter.result()["issues"], [])

    def test_complete_manifest_rejects_phase1_review_pending(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate = root / "openspec/orchestrate"
            trace_dir = orchestrate / "trace"
            trace_dir.mkdir(parents=True)
            phase_traces = {
                "phase-1.trace.json": {
                    "status": "review-pending",
                    "review-gate": {"status": "pending"},
                },
                "phase-2.trace.json": {"status": "source-atoms-written"},
                "phase-3.trace.json": {
                    "decision": "coverage-complete",
                    "review-gate": {"status": "passed"},
                },
                "phase-4.trace.json": {"status": "assembled"},
                "phase-5.trace.json": {"status": "accepted"},
            }
            for name, payload in phase_traces.items():
                (trace_dir / name).write_text(
                    json.dumps(payload) + "\n",
                    encoding="utf-8",
                )
            (orchestrate / "final-integration-review.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            (trace_dir / "workflow-completion.trace.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            manifest = {
                "trace-schema": MANIFEST_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "authority": "control",
                "orchestrate-dir": "openspec/orchestrate",
                "phase-statuses": {
                    "phase-1": "review-pending",
                    "phase-2": "source-atoms-written",
                    "phase-3": "coverage-complete",
                    "phase-4": "assembled",
                    "phase-5": "accepted",
                },
                "workflow-status": "integration-passed",
                "artifacts": [],
            }
            (trace_dir / "manifest.json").write_text(
                json.dumps(manifest) + "\n",
                encoding="utf-8",
            )
            reporter = IssueReporter()
            with mock.patch(
                "validate_source_aligned_orchestrate.expected_manifest_artifacts",
                return_value={},
            ):
                validate_manifest(
                    orchestrate,
                    root,
                    reporter,
                    complete=True,
                )

        phase1_issues = [
            issue
            for issue in reporter.issues
            if "Phase 1" in issue.message
            or "phase-statuses.phase-1" in issue.message
        ]
        self.assertTrue(phase1_issues)

    def test_pending_accepts_review_waiting_for_repair(self) -> None:
        framework = b"framework-v1\n"
        plan = b"plan-v1\n"
        review = _review(
            1,
            _sha(framework),
            _sha(plan),
            findings=[FINDING_A],
        )
        with tempfile.TemporaryDirectory() as raw:
            reporter = self._validate(
                Path(raw),
                _gate("pending", [review], []),
                framework=framework,
                plan=plan,
            )

        self.assertEqual(reporter.result()["issues"], [])

    def test_pending_accepts_successful_review_waiting_for_terminalization(
        self,
    ) -> None:
        framework = b"framework-v1\n"
        plan = b"plan-v1\n"
        review = _review(
            1,
            _sha(framework),
            _sha(plan),
            passed=True,
        )
        with tempfile.TemporaryDirectory() as raw:
            reporter = self._validate(
                Path(raw),
                _gate("pending", [review], []),
                framework=framework,
                plan=plan,
            )

        self.assertEqual(reporter.result()["issues"], [])

    def test_pending_accepts_repair_waiting_for_fresh_review(self) -> None:
        framework_before = b"framework-v1\n"
        framework_after = b"framework-v2\n"
        plan_before = b"plan-v1\n"
        plan_after = b"plan-v2\n"
        review = _review(
            1,
            _sha(framework_before),
            _sha(plan_before),
            findings=[FINDING_A],
        )
        repair = _repair(
            1,
            _sha(framework_before),
            _sha(framework_after),
            FINDING_A,
        )
        with tempfile.TemporaryDirectory() as raw:
            reporter = self._validate(
                Path(raw),
                _gate("pending", [review], [repair]),
                framework=framework_after,
                plan=plan_after,
            )

        self.assertEqual(reporter.result()["issues"], [])

    def test_pending_rejects_missing_intermediate_repair(self) -> None:
        framework = b"framework-v2\n"
        plan = b"plan-v2\n"
        reviews = [
            _review(
                1,
                _sha(b"framework-v1\n"),
                _sha(b"plan-v1\n"),
                findings=[FINDING_A],
            ),
            _review(
                2,
                _sha(framework),
                _sha(plan),
                findings=[FINDING_B],
            ),
        ]
        with tempfile.TemporaryDirectory() as raw:
            reporter = self._validate(
                Path(raw),
                _gate("pending", reviews, []),
                framework=framework,
                plan=plan,
            )

        rule_ids = {issue.rule_id for issue in reporter.issues}
        self.assertIn("phase1-review-gate-cardinality", rule_ids)
        self.assertIn("phase1-repair-missing", rule_ids)

    def test_pending_rejects_noop_repair_that_forces_block(self) -> None:
        framework = b"framework-v1\n"
        plan = b"plan-v1\n"
        digest = _sha(framework)
        review = _review(
            1,
            digest,
            _sha(plan),
            findings=[FINDING_A],
        )
        repair = _repair(1, digest, digest, FINDING_A)
        with tempfile.TemporaryDirectory() as raw:
            reporter = self._validate(
                Path(raw),
                _gate("pending", [review], [repair]),
                framework=framework,
                plan=plan,
            )

        self.assertIn(
            "phase1-review-no-progress",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_pending_rejects_failed_third_review_that_forces_block(self) -> None:
        framework_1 = b"framework-v1\n"
        framework_2 = b"framework-v2\n"
        framework_3 = b"framework-v3\n"
        plan_1 = b"plan-v1\n"
        plan_2 = b"plan-v2\n"
        plan_3 = b"plan-v3\n"
        reviews = [
            _review(
                1,
                _sha(framework_1),
                _sha(plan_1),
                findings=[FINDING_A],
            ),
            _review(
                2,
                _sha(framework_2),
                _sha(plan_2),
                findings=[FINDING_B],
            ),
            _review(
                3,
                _sha(framework_3),
                _sha(plan_3),
                findings=[FINDING_C],
            ),
        ]
        repairs = [
            _repair(
                1,
                _sha(framework_1),
                _sha(framework_2),
                FINDING_A,
            ),
            _repair(
                2,
                _sha(framework_2),
                _sha(framework_3),
                FINDING_B,
            ),
        ]
        with tempfile.TemporaryDirectory() as raw:
            reporter = self._validate(
                Path(raw),
                _gate("pending", reviews, repairs),
                framework=framework_3,
                plan=plan_3,
            )

        self.assertIn(
            "phase1-review-no-progress",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_continuing_after_repeated_finding_is_rejected(self) -> None:
        framework_1 = b"framework-v1\n"
        framework_2 = b"framework-v2\n"
        framework_3 = b"framework-v3\n"
        plan_1 = b"plan-v1\n"
        plan_2 = b"plan-v2\n"
        plan_3 = b"plan-v3\n"
        reviews = [
            _review(
                1,
                _sha(framework_1),
                _sha(plan_1),
                findings=[FINDING_A],
            ),
            _review(
                2,
                _sha(framework_2),
                _sha(plan_2),
                findings=[FINDING_A],
            ),
            _review(
                3,
                _sha(framework_3),
                _sha(plan_3),
                passed=True,
            ),
        ]
        repairs = [
            _repair(
                1,
                _sha(framework_1),
                _sha(framework_2),
                FINDING_A,
            ),
            _repair(
                2,
                _sha(framework_2),
                _sha(framework_3),
                FINDING_A,
            ),
        ]
        with tempfile.TemporaryDirectory() as raw:
            reporter = self._validate(
                Path(raw),
                _gate("blocked", reviews, repairs),
                framework=framework_3,
                plan=plan_3,
            )

        self.assertIn(
            "phase1-review-continued-after-block",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_terminal_passed_remains_strict(self) -> None:
        framework = b"framework-v1\n"
        plan = b"plan-v1\n"
        review = _review(
            1,
            _sha(framework),
            _sha(plan),
            passed=True,
        )
        with tempfile.TemporaryDirectory() as raw:
            reporter = self._validate(
                Path(raw),
                _gate("passed", [review], []),
                framework=framework,
                plan=plan,
            )

        self.assertEqual(reporter.result()["issues"], [])

    def test_terminal_blocked_remains_strict(self) -> None:
        framework = b"framework-v1\n"
        plan = b"plan-v1\n"
        review = _review(
            1,
            _sha(framework),
            _sha(plan),
            findings=[FINDING_A],
        )
        with tempfile.TemporaryDirectory() as raw:
            reporter = self._validate(
                Path(raw),
                _gate("blocked", [review], []),
                framework=framework,
                plan=plan,
            )

        self.assertEqual(reporter.result()["issues"], [])

    def test_review_and_repair_budgets_are_enforced(self) -> None:
        framework = b"framework-current\n"
        plan = b"plan-current\n"
        reviews = [
            _review(
                index,
                _sha(framework),
                _sha(plan),
                findings=[FINDING_A],
            )
            for index in range(1, 5)
        ]
        with tempfile.TemporaryDirectory() as raw:
            reporter = self._validate(
                Path(raw),
                _gate("pending", reviews, []),
                framework=framework,
                plan=plan,
            )

        self.assertIn(
            "phase1-review-gate-reviews",
            {issue.rule_id for issue in reporter.issues},
        )


if __name__ == "__main__":
    unittest.main()
