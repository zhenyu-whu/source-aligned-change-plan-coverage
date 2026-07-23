#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v8 finalizer one-shot gate 与 final review evidence 归属负例。"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TEST_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = TEST_DIR.parent
for candidate in (str(TEST_DIR), str(SCRIPT_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import finalize_source_aligned_orchestrate as finalizer  # noqa: E402
from source_aligned_trace_lib import (  # noqa: E402
    INITIAL_FRAMEWORK_SCHEMA,
    MANIFEST_SCHEMA,
    TRACE_CONTRACT_VERSION,
    IssueReporter,
    sha256_file,
    write_json,
)
import test_v8_phase5_handoff as handoff  # noqa: E402
from test_v8_phase5_handoff import V8HandoffFixture  # noqa: E402
from validate_source_aligned_orchestrate import (  # noqa: E402
    validate_change_outcome_evidence_alignment,
    validate_final_integration_review_candidate,
)


def _minimal_manifest(orchestrate: Path, workflow_status: str) -> None:
    write_json(
        orchestrate / "trace/manifest.json",
        {
            "trace-schema": MANIFEST_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "authority": "control",
            "orchestrate-dir": "openspec/orchestrate",
            "phase-statuses": {
                f"phase-{index}": "missing" for index in range(1, 6)
            },
            "workflow-status": workflow_status,
            "artifacts": [],
        },
    )


class FinalizerOneShotTests(unittest.TestCase):
    def _preflight_with_phase_checks_stubbed(
        self,
        orchestrate: Path,
        root: Path,
    ) -> None:
        patches = [
            mock.patch.object(finalizer, name)
            for name in (
                "validate_phase_1",
                "validate_phase_2",
                "validate_phase_3",
                "validate_phase_4",
                "validate_phase_5",
                "validate_final_integration_review_candidate",
            )
        ]
        started = [patch.start() for patch in patches]
        self.addCleanup(
            lambda: [patch.stop() for patch in reversed(patches)]
        )
        self.assertEqual(len(started), len(patches))
        finalizer._pre_completion_validation(orchestrate, root)

    def test_finalizer_rejects_absent_or_non_pending_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate = root / "openspec/orchestrate"
            orchestrate.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "manifest"):
                self._preflight_with_phase_checks_stubbed(
                    orchestrate,
                    root,
                )

        for workflow_status in ("blocked", "integration-passed"):
            with self.subTest(workflow_status=workflow_status):
                with tempfile.TemporaryDirectory() as raw:
                    root = Path(raw)
                    orchestrate = root / "openspec/orchestrate"
                    _minimal_manifest(orchestrate, workflow_status)
                    with self.assertRaisesRegex(
                        ValueError,
                        "workflow-status=pending",
                    ):
                        self._preflight_with_phase_checks_stubbed(
                            orchestrate,
                            root,
                        )

    def test_blocked_or_passed_completion_cannot_be_finalized_again(
        self,
    ) -> None:
        for status in ("blocked", "integration-passed"):
            with self.subTest(status=status):
                with tempfile.TemporaryDirectory() as raw:
                    root = Path(raw)
                    orchestrate = root / "openspec/orchestrate"
                    write_json(
                        orchestrate / "final-integration-review.json",
                        {"review": "already-consumed"},
                    )
                    write_json(
                        orchestrate
                        / "trace/workflow-completion.trace.json",
                        {"status": status},
                    )
                    with mock.patch.object(
                        finalizer,
                        "_pre_completion_validation",
                    ) as preflight:
                        with self.assertRaisesRegex(
                            ValueError,
                            "不得重复finalize",
                        ):
                            finalizer.finalize(orchestrate, root)
                    preflight.assert_not_called()

    def test_pending_manifest_inventory_digest_drift_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate = root / "openspec/orchestrate"
            framework = (
                orchestrate
                / "phase-works/phase-1/initial-framework.json"
            )
            write_json(
                framework,
                {
                    "trace-schema": INITIAL_FRAMEWORK_SCHEMA,
                    "trace-contract-version": TRACE_CONTRACT_VERSION,
                },
            )
            _minimal_manifest(orchestrate, "pending")
            manifest_path = orchestrate / "trace/manifest.json"
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            manifest["artifacts"] = [
                {
                    "json-path": (
                        "openspec/orchestrate/phase-works/phase-1/"
                        "initial-framework.json"
                    ),
                    "trace-schema": INITIAL_FRAMEWORK_SCHEMA,
                    "sha256": "0" * 64,
                    "phase": "phase-1",
                    "role": "initial-framework",
                    "authority": "semantic",
                }
            ]
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(ValueError, "sha256"):
                self._preflight_with_phase_checks_stubbed(
                    orchestrate,
                    root,
                )

    def test_existing_review_mirror_is_also_permanent_retry_marker(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate = root / "openspec/orchestrate"
            write_json(
                orchestrate / "final-integration-review.json",
                {"review": "already-consumed"},
            )
            mirror = orchestrate / "final-integration-review.md"
            mirror.write_text("blocked review mirror\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "不得重复finalize"):
                finalizer._assert_one_shot_finalize_state(orchestrate)

    def test_successful_blocked_finalization_is_one_shot(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fixture = V8HandoffFixture(root)
            fixture.publish()
            handoff.WorkflowCompletionTests()._publish_workflow(
                fixture,
                status="blocked",
            )
            (
                fixture.orchestrate / "final-integration-review.md"
            ).unlink()
            (
                fixture.orchestrate
                / "trace/workflow-completion.trace.json"
            ).unlink()
            for name in (
                "final-integration-review-attempt.trace.json",
                "final-integration-review-attempt-result.trace.json",
            ):
                (fixture.orchestrate / "trace" / name).unlink()
            statuses = {
                "phase-1": {"status": "initial-plan-written"},
                "phase-2": {"status": "source-atoms-written"},
                "phase-3": {"decision": "coverage-complete"},
                "phase-4": {"status": "assembled"},
            }
            for phase, payload in statuses.items():
                write_json(
                    fixture.orchestrate / f"trace/{phase}.trace.json",
                    payload,
                )
            with (
                mock.patch.object(
                    finalizer,
                    "_pre_completion_validation",
                ),
                mock.patch.object(
                    finalizer,
                    "validate",
                    return_value={
                        "ok": True,
                        "issues": [],
                        "error-count": 0,
                        "warning-count": 0,
                    },
                ),
            ):
                finalizer.finalize(fixture.orchestrate, fixture.root)

            completion = json.loads(
                (
                    fixture.orchestrate
                    / "trace/workflow-completion.trace.json"
                ).read_text(encoding="utf-8")
            )
            manifest = json.loads(
                (
                    fixture.orchestrate / "trace/manifest.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(completion["status"], "blocked")
            self.assertEqual(manifest["workflow-status"], "blocked")
            with mock.patch.object(
                finalizer,
                "_pre_completion_validation",
            ) as preflight:
                with self.assertRaisesRegex(
                    ValueError,
                    "不得重复finalize",
                ):
                    finalizer.finalize(
                        fixture.orchestrate,
                        fixture.root,
                    )
            preflight.assert_not_called()

    def test_publish_validation_failure_rolls_back_every_target(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            transaction = root / "transaction"
            transaction.mkdir()
            staged_review = transaction / "review.md"
            staged_completion = transaction / "completion.json"
            staged_manifest = transaction / "manifest.json"
            staged_review.write_text("new review\n", encoding="utf-8")
            staged_completion.write_text(
                '{"status":"blocked"}\n',
                encoding="utf-8",
            )
            staged_manifest.write_text("new manifest\n", encoding="utf-8")
            target_review = root / "orchestrate/review.md"
            target_completion = root / "orchestrate/completion.json"
            target_manifest = root / "orchestrate/manifest.json"
            target_manifest.parent.mkdir(parents=True)
            target_manifest.write_text("old manifest\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "post publish"):
                finalizer._publish_with_rollback(
                    (
                        (staged_review, target_review),
                        (staged_completion, target_completion),
                        (staged_manifest, target_manifest),
                    ),
                    transaction,
                    lambda: (_ for _ in ()).throw(
                        ValueError("post publish validation failed")
                    ),
                )
            self.assertFalse(target_review.exists())
            self.assertFalse(target_completion.exists())
            self.assertEqual(
                target_manifest.read_text(encoding="utf-8"),
                "old manifest\n",
            )
            self.assertFalse(transaction.exists())


class FinalReviewEvidenceScopeTests(unittest.TestCase):
    @staticmethod
    def _published_review(
        root: Path,
    ) -> tuple[V8HandoffFixture, Path, dict[str, object]]:
        fixture = V8HandoffFixture(root)
        initial_path = (
            fixture.orchestrate
            / "phase-works/phase-1/initial-framework.json"
        )
        initial = json.loads(initial_path.read_text(encoding="utf-8"))
        initial["overlay"] = [
            {
                "change": row["change"],
                "capability": row["capability"],
            }
            for row in initial["overlay"]
        ]
        write_json(initial_path, initial)
        refit_path = fixture.work / "framework-refit-trace.json"
        refit = json.loads(refit_path.read_text(encoding="utf-8"))
        refit["initial-framework-ref"]["sha256"] = sha256_file(initial_path)
        write_json(refit_path, refit)
        fixture.publish()
        handoff.WorkflowCompletionTests()._publish_workflow(
            fixture,
            status="passed",
        )
        review_path = (
            fixture.orchestrate / "final-integration-review.json"
        )
        review = json.loads(review_path.read_text(encoding="utf-8"))
        return fixture, review_path, review

    def _assert_review_scope_error(
        self,
        fixture: V8HandoffFixture,
    ) -> None:
        reporter = IssueReporter()
        validate_final_integration_review_candidate(
            fixture.orchestrate,
            fixture.root,
            reporter,
        )
        self.assertTrue(
            any(
                item.rule_id
                in {
                    "workflow-unit-review-evidence-unrelated",
                    "workflow-unit-review-evidence-scope",
                }
                for item in reporter.issues
            ),
            [item.message for item in reporter.issues],
        )

    def test_change_result_cannot_be_stamped_by_unrelated_known_ga(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture, review_path, review = self._published_review(Path(raw))
            ship = review["change-results"][0]
            ship["evidence-ga-ids"] = ["GA-0006"]
            write_json(review_path, review)
            self._assert_review_scope_error(fixture)

    def test_capability_gate_cannot_be_stamped_by_unrelated_known_ga(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture, review_path, review = self._published_review(Path(raw))
            capability = review["capability-results"][0]
            capability["gate-results"][0]["evidence-ga-ids"] = [
                "GA-0006"
            ]
            write_json(review_path, review)
            self._assert_review_scope_error(fixture)

    def test_change_outcome_evidence_must_match_realized_thread(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = V8HandoffFixture(Path(raw))
            roadmap = copy.deepcopy(fixture.roadmap)
            roadmap["changes"][0]["outcome-ga-ids"] = ["GA-0003"]
            reporter = IssueReporter()
            validate_change_outcome_evidence_alignment(
                roadmap,
                fixture.work / "final-roadmap.json",
                reporter,
            )
            self.assertTrue(
                any(
                    item.rule_id
                    in {
                        "phase5-change-outcome-thread-evidence",
                        "phase5-change-outcome-evidence-scope",
                    }
                    for item in reporter.issues
                ),
                [item.message for item in reporter.issues],
            )


if __name__ == "__main__":
    unittest.main()
