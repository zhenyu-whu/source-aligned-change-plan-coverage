#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v8 Phase 1 bounded review state-machine contract tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Tuple


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from review_fixture_v8 import (  # noqa: E402
    gate,
    sha256_bytes,
    write_review_result,
)
from source_aligned_trace_lib import IssueReporter  # noqa: E402
from validate_source_aligned_orchestrate import (  # noqa: E402
    _validate_phase1_review_gate,
)


def _repair(
    round_number: int,
    review_ref: Dict[str, object],
    before_sha: str,
    after_sha: str,
    *,
    writer_id: str = "",
) -> Dict[str, object]:
    return {
        "round": round_number,
        "repair-writer-id": writer_id or f"phase-1-repair-{round_number}",
        "source-review-result-sha256": review_ref[
            "review-result-sha256"
        ],
        "before-initial-framework-sha256": before_sha,
        "after-initial-framework-sha256": after_sha,
    }


class Phase1ReviewStateTests(unittest.TestCase):
    def _tree(
        self,
        raw: str,
        *,
        framework: bytes = b"framework-current\n",
        plan: bytes = b"plan-current\n",
    ) -> Tuple[Path, Path, Path, Path]:
        repo_root = Path(raw)
        orchestrate = repo_root / "openspec/orchestrate"
        phase1 = orchestrate / "phase-works/phase-1"
        trace_path = orchestrate / "trace/phase-1.trace.json"
        framework_path = phase1 / "initial-framework.json"
        plan_path = phase1 / "initial-change-plan.md"
        trace_path.parent.mkdir(parents=True)
        phase1.mkdir(parents=True)
        framework_path.write_bytes(framework)
        plan_path.write_bytes(plan)
        return orchestrate, trace_path, framework_path, plan_path

    def _validate(
        self,
        trace_path: Path,
        framework_path: Path,
        plan_path: Path,
        review_gate: Dict[str, object],
    ) -> IssueReporter:
        reporter = IssueReporter()
        _validate_phase1_review_gate(
            review_gate,
            trace_path,
            framework_path,
            plan_path,
            reporter,
        )
        return reporter

    def _history(
        self,
        orchestrate: Path,
        repo_root: Path,
        framework_payloads: List[bytes],
        plan_payloads: List[bytes],
        *,
        last_decision: str,
    ) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
        reviews: List[Dict[str, object]] = []
        repairs: List[Dict[str, object]] = []
        for index, (framework, plan) in enumerate(
            zip(framework_payloads, plan_payloads),
            start=1,
        ):
            decision = (
                last_decision
                if index == len(framework_payloads)
                else "repair-required"
            )
            review = write_review_result(
                orchestrate,
                repo_root,
                phase="phase-1",
                round_number=index,
                decision=decision,
                authority={
                    "initial-framework-sha256": sha256_bytes(framework),
                    "initial-change-plan-sha256": sha256_bytes(plan),
                },
            )
            reviews.append(review)
            if index < len(framework_payloads):
                repairs.append(
                    _repair(
                        index,
                        review,
                        sha256_bytes(framework),
                        sha256_bytes(framework_payloads[index]),
                    )
                )
        return reviews, repairs

    def test_pending_accepts_empty_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            _, trace, framework, plan = self._tree(raw)
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "pending",
                    [],
                    [],
                    writer_id="phase-1-writer",
                ),
            )
        self.assertEqual(reporter.result()["issues"], [])

    def test_terminal_passed_accepts_fresh_review_result(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(raw)
            reviews, repairs = self._history(
                orchestrate,
                repo,
                [framework.read_bytes()],
                [plan.read_bytes()],
                last_decision="passed",
            )
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "passed",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                ),
            )
        self.assertEqual(reporter.result()["issues"], [])

    def test_round_four_may_remain_pending_for_repair(self) -> None:
        frameworks = [f"framework-{i}\n".encode() for i in range(1, 5)]
        plans = [f"plan-{i}\n".encode() for i in range(1, 5)]
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(
                raw,
                framework=frameworks[-1],
                plan=plans[-1],
            )
            reviews, repairs = self._history(
                orchestrate,
                repo,
                frameworks,
                plans,
                last_decision="repair-required",
            )
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "pending",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                ),
            )
        self.assertEqual(reporter.result()["issues"], [])

    def test_five_review_four_repair_path_can_pass(self) -> None:
        frameworks = [f"framework-{i}\n".encode() for i in range(1, 6)]
        plans = [f"plan-{i}\n".encode() for i in range(1, 6)]
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(
                raw,
                framework=frameworks[-1],
                plan=plans[-1],
            )
            reviews, repairs = self._history(
                orchestrate,
                repo,
                frameworks,
                plans,
                last_decision="passed",
            )
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "passed",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                ),
            )
        self.assertEqual(reporter.result()["issues"], [])

    def test_round_five_failure_must_budget_block(self) -> None:
        frameworks = [f"framework-{i}\n".encode() for i in range(1, 6)]
        plans = [f"plan-{i}\n".encode() for i in range(1, 6)]
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(
                raw,
                framework=frameworks[-1],
                plan=plans[-1],
            )
            reviews, repairs = self._history(
                orchestrate,
                repo,
                frameworks,
                plans,
                last_decision="blocked",
            )
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "blocked",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                    terminal_reason="budget-exhausted",
                ),
            )
            wrong_reason_reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "blocked",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                    terminal_reason="review-blocked",
                ),
            )
        self.assertEqual(reporter.result()["issues"], [])
        self.assertIn(
            "phase1-review-budget",
            {issue.rule_id for issue in wrong_reason_reporter.issues},
        )

    def test_round_five_cannot_remain_pending(self) -> None:
        frameworks = [f"framework-{i}\n".encode() for i in range(1, 6)]
        plans = [f"plan-{i}\n".encode() for i in range(1, 6)]
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(
                raw,
                framework=frameworks[-1],
                plan=plans[-1],
            )
            reviews, repairs = self._history(
                orchestrate,
                repo,
                frameworks,
                plans,
                last_decision="blocked",
            )
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "pending",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                ),
            )
        self.assertIn(
            "phase1-review-budget",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_sixth_review_is_rejected(self) -> None:
        review_refs = [{"round": index} for index in range(1, 7)]
        with tempfile.TemporaryDirectory() as raw:
            _, trace, framework, plan = self._tree(raw)
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "pending",
                    review_refs,
                    [],
                    writer_id="phase-1-writer",
                ),
            )
        self.assertIn(
            "phase1-review-gate-reviews",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_fifth_repair_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            _, trace, framework, plan = self._tree(raw)
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "pending",
                    [],
                    [{"round": index} for index in range(1, 6)],
                    writer_id="phase-1-writer",
                ),
            )
        self.assertIn(
            "phase1-review-gate-repairs",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_no_op_repair_requires_immediate_block(self) -> None:
        framework_payload = b"framework-1\n"
        plan_payload = b"plan-1\n"
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(
                raw,
                framework=framework_payload,
                plan=plan_payload,
            )
            review = write_review_result(
                orchestrate,
                repo,
                phase="phase-1",
                round_number=1,
                decision="repair-required",
                authority={
                    "initial-framework-sha256": sha256_bytes(
                        framework_payload
                    ),
                    "initial-change-plan-sha256": sha256_bytes(plan_payload),
                },
            )
            repair = _repair(
                1,
                review,
                sha256_bytes(framework_payload),
                sha256_bytes(framework_payload),
            )
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "pending",
                    [review],
                    [repair],
                    writer_id="phase-1-writer",
                ),
            )
        self.assertIn(
            "phase1-review-no-progress",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_no_op_repair_block_is_legal_terminal(self) -> None:
        framework_payload = b"framework-1\n"
        plan_payload = b"plan-1\n"
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(
                raw,
                framework=framework_payload,
                plan=plan_payload,
            )
            review = write_review_result(
                orchestrate,
                repo,
                phase="phase-1",
                round_number=1,
                decision="repair-required",
                authority={
                    "initial-framework-sha256": sha256_bytes(
                        framework_payload
                    ),
                    "initial-change-plan-sha256": sha256_bytes(plan_payload),
                },
            )
            repair = _repair(
                1,
                review,
                sha256_bytes(framework_payload),
                sha256_bytes(framework_payload),
            )
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "blocked",
                    [review],
                    [repair],
                    writer_id="phase-1-writer",
                    terminal_reason="no-op-repair",
                ),
            )
        self.assertEqual(reporter.result()["issues"], [])

    def test_reviewer_identity_reuse_is_rejected(self) -> None:
        frameworks = [b"framework-1\n", b"framework-2\n"]
        plans = [b"plan-1\n", b"plan-2\n"]
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(
                raw,
                framework=frameworks[-1],
                plan=plans[-1],
            )
            reviews, repairs = self._history(
                orchestrate,
                repo,
                frameworks,
                plans,
                last_decision="passed",
            )
            result_path = (
                orchestrate
                / "phase-works/phase-1/reviews/review-round-02.json"
            )
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["reviewer-id"] = "phase-1-reviewer-1"
            result_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
            reviews[1]["review-result-sha256"] = sha256_bytes(
                result_path.read_bytes()
            )
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "passed",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                ),
            )
        self.assertIn(
            "phase1-reviewer-independence",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_identity_reuse_is_a_legal_immediate_block(self) -> None:
        frameworks = [b"framework-1\n", b"framework-2\n"]
        plans = [b"plan-1\n", b"plan-2\n"]
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(
                raw,
                framework=frameworks[-1],
                plan=plans[-1],
            )
            reviews, repairs = self._history(
                orchestrate,
                repo,
                frameworks,
                plans,
                last_decision="passed",
            )
            result_path = (
                orchestrate
                / "phase-works/phase-1/reviews/review-round-02.json"
            )
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["reviewer-id"] = "phase-1-reviewer-1"
            result_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
            reviews[1]["review-result-sha256"] = sha256_bytes(
                result_path.read_bytes()
            )
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "blocked",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                    terminal_reason="identity-reuse",
                ),
            )
        self.assertEqual(reporter.result()["issues"], [])

    def test_review_result_digest_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(raw)
            reviews, repairs = self._history(
                orchestrate,
                repo,
                [framework.read_bytes()],
                [plan.read_bytes()],
                last_decision="passed",
            )
            reviews[0]["review-result-sha256"] = "0" * 64
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "passed",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                ),
            )
        self.assertIn(
            "phase1-review-result-digest",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_review_result_digest_drift_is_a_legal_integrity_block(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(raw)
            reviews, repairs = self._history(
                orchestrate,
                repo,
                [framework.read_bytes()],
                [plan.read_bytes()],
                last_decision="passed",
            )
            reviews[0]["review-result-sha256"] = "0" * 64
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "blocked",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                    terminal_reason="authority-integrity",
                ),
            )
        self.assertEqual(reporter.result()["issues"], [])

    def test_authority_digest_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(raw)
            reviews, repairs = self._history(
                orchestrate,
                repo,
                [framework.read_bytes()],
                [plan.read_bytes()],
                last_decision="passed",
            )
            framework.write_bytes(b"drifted-authority\n")
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "passed",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                ),
            )
        self.assertIn(
            "phase1-review-current-framework",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_repair_must_bind_full_source_review_result(self) -> None:
        frameworks = [b"framework-1\n", b"framework-2\n"]
        plans = [b"plan-1\n", b"plan-2\n"]
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(
                raw,
                framework=frameworks[-1],
                plan=plans[-1],
            )
            reviews, repairs = self._history(
                orchestrate,
                repo,
                frameworks,
                plans,
                last_decision="passed",
            )
            repairs[0]["source-review-result-sha256"] = "0" * 64
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "passed",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                ),
            )
        self.assertIn(
            "phase1-repair-source-review",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_review_result_rejects_fingerprint_field(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            orchestrate, trace, framework, plan = self._tree(raw)
            reviews, repairs = self._history(
                orchestrate,
                repo,
                [framework.read_bytes()],
                [plan.read_bytes()],
                last_decision="passed",
            )
            result_path = (
                orchestrate
                / "phase-works/phase-1/reviews/review-round-01.json"
            )
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["finding-fingerprints"] = []
            result_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
            reviews[0]["review-result-sha256"] = sha256_bytes(
                result_path.read_bytes()
            )
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "passed",
                    reviews,
                    repairs,
                    writer_id="phase-1-writer",
                ),
            )
        self.assertIn(
            "phase1-review-result",
            {issue.rule_id for issue in reporter.issues},
        )

    def test_blocked_requires_non_none_terminal_reason(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            _, trace, framework, plan = self._tree(raw)
            reporter = self._validate(
                trace,
                framework,
                plan,
                gate(
                    "blocked",
                    [],
                    [],
                    writer_id="phase-1-writer",
                    terminal_reason="none",
                ),
            )
        self.assertIn(
            "phase1-review-gate-terminal-reason",
            {issue.rule_id for issue in reporter.issues},
        )


if __name__ == "__main__":
    unittest.main()
