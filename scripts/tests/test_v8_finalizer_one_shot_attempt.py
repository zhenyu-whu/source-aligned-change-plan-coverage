#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v8 final integration review one-shot attempt authority tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TEST_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = TEST_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import finalize_source_aligned_orchestrate as finalizer  # noqa: E402
from source_aligned_trace_lib import (  # noqa: E402
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
    TRACE_CONTRACT_VERSION,
    sha256_file,
)


class FinalReviewOneShotAttemptTests(unittest.TestCase):
    @staticmethod
    def _paths(
        root: Path,
    ) -> tuple[Path, Path, Path, Path]:
        orchestrate = root / "openspec/orchestrate"
        review = orchestrate / "final-integration-review.json"
        attempt = (
            orchestrate
            / FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH
        )
        result = (
            orchestrate
            / FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH
        )
        review.parent.mkdir(parents=True, exist_ok=True)
        review.write_text('{"malformed-review":true}\n', encoding="utf-8")
        return orchestrate, review, attempt, result

    def test_prevalidation_failure_is_recorded_before_validation_and_blocks_retry(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate, review, attempt, result = self._paths(root)

            def fail_after_submission(*_args: object) -> None:
                self.assertTrue(attempt.is_file())
                self.assertFalse(result.exists())
                self.assertFalse(
                    (
                        orchestrate
                        / "trace/workflow-completion.trace.json"
                    ).exists()
                )
                raise ValueError("语义预校验失败")

            with mock.patch.object(
                finalizer,
                "_pre_completion_validation",
                side_effect=fail_after_submission,
            ):
                with self.assertRaisesRegex(ValueError, "语义预校验失败"):
                    finalizer.finalize(orchestrate, root)

            attempt_data = json.loads(
                attempt.read_text(encoding="utf-8")
            )
            result_data = json.loads(
                result.read_text(encoding="utf-8")
            )
            self.assertEqual(
                attempt_data["trace-schema"],
                FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
            )
            self.assertEqual(
                attempt_data["trace-contract-version"],
                TRACE_CONTRACT_VERSION,
            )
            self.assertEqual(attempt_data["status"], "submitted")
            self.assertEqual(
                attempt_data["final-integration-review-sha256"],
                sha256_file(review),
            )
            self.assertEqual(
                result_data["trace-schema"],
                FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA,
            )
            self.assertEqual(result_data["status"], "blocked")
            self.assertIsNone(
                result_data["terminal-authority-sha256"]
            )
            self.assertIn(
                "语义预校验失败",
                result_data["issues"][0],
            )
            self.assertFalse(
                (
                    orchestrate
                    / "trace/workflow-completion.trace.json"
                ).exists()
            )
            self.assertFalse(
                (orchestrate / "final-integration-review.md").exists()
            )

            review.write_text(
                '{"replacement-review":true}\n',
                encoding="utf-8",
            )
            with mock.patch.object(
                finalizer,
                "_pre_completion_validation",
            ) as prevalidation:
                with self.assertRaisesRegex(
                    ValueError,
                    "不得重复finalize",
                ):
                    finalizer.finalize(orchestrate, root)
            prevalidation.assert_not_called()

    def test_pending_submission_can_resume_only_with_identical_review_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate, review, attempt_path, result_path = self._paths(
                root
            )
            first = finalizer._record_or_resume_attempt(
                orchestrate,
                root,
            )
            second = finalizer._record_or_resume_attempt(
                orchestrate,
                root,
            )
            self.assertEqual(first, second)
            self.assertTrue(attempt_path.is_file())
            self.assertFalse(result_path.exists())

            review.write_text(
                '{"replacement-review":true}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError,
                "替换或digest drift",
            ):
                finalizer._record_or_resume_attempt(
                    orchestrate,
                    root,
                )
            result = json.loads(
                result_path.read_text(encoding="utf-8")
            )
            self.assertEqual(result["status"], "blocked")
            self.assertFalse(
                (
                    orchestrate
                    / "trace/workflow-completion.trace.json"
                ).exists()
            )

    def test_symlinked_review_is_consumed_as_a_blocked_attempt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate, review, attempt, result = self._paths(root)
            target = root / "review-target.json"
            target.write_text('{"review":"target"}\n', encoding="utf-8")
            review.unlink()
            review.symlink_to(target)

            with mock.patch.object(
                finalizer,
                "_pre_completion_validation",
            ) as prevalidation:
                with self.assertRaisesRegex(
                    ValueError,
                    "缺失或不是普通文件",
                ):
                    finalizer.finalize(orchestrate, root)
            prevalidation.assert_not_called()
            self.assertTrue(attempt.is_file())
            result_data = json.loads(
                result.read_text(encoding="utf-8")
            )
            self.assertEqual(result_data["status"], "blocked")
            self.assertFalse(
                (
                    orchestrate
                    / "trace/workflow-completion.trace.json"
                ).exists()
            )

    def test_semantic_pass_is_terminalized_before_completion_publish(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate, _review, _attempt, result = self._paths(root)
            terminal_digest = "a" * 64
            observed: dict[str, bool] = {}

            def observe_publish(
                _entries: object,
                transaction_root: Path,
                _validate_published: object,
            ) -> None:
                observed["result-exists"] = result.is_file()
                observed["completion-exists"] = (
                    orchestrate
                    / "trace/workflow-completion.trace.json"
                ).exists()
                # The real publisher owns cleanup; emulate it for this
                # isolated ordering test.
                import shutil

                shutil.rmtree(transaction_root, ignore_errors=True)

            with (
                mock.patch.object(
                    finalizer,
                    "_pre_completion_validation",
                ),
                mock.patch.object(
                    finalizer,
                    "terminal_authority_sha256",
                    return_value=terminal_digest,
                ),
                mock.patch.object(
                    finalizer,
                    "load_final_integration_review",
                    return_value={"status": "passed", "findings": []},
                ),
                mock.patch.object(
                    finalizer,
                    "render_final_integration_review",
                    return_value="# 终态审查\n",
                ),
                mock.patch.object(
                    finalizer,
                    "_manifest_payload",
                    return_value={},
                ),
                mock.patch.object(
                    finalizer,
                    "_publish_with_rollback",
                    side_effect=observe_publish,
                ),
            ):
                finalizer.finalize(orchestrate, root)

            result_data = json.loads(
                result.read_text(encoding="utf-8")
            )
            self.assertEqual(result_data["status"], "passed")
            self.assertEqual(
                result_data["terminal-authority-sha256"],
                terminal_digest,
            )
            self.assertTrue(observed["result-exists"])
            self.assertFalse(observed["completion-exists"])

    def test_no_write_probe_does_not_run_semantic_prevalidation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate, _review, attempt, result = self._paths(root)
            with mock.patch.object(
                finalizer,
                "_pre_completion_validation",
            ) as prevalidation:
                exit_code = finalizer.main(
                    (
                        "--orchestrate-dir",
                        str(orchestrate),
                        "--workspace-root",
                        str(root),
                    )
                )
            self.assertEqual(exit_code, 0)
            prevalidation.assert_not_called()
            self.assertFalse(attempt.exists())
            self.assertFalse(result.exists())

    def test_final_manifest_payload_registers_attempt_and_result(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate, _review, attempt, result = self._paths(root)
            attempt.parent.mkdir(parents=True, exist_ok=True)
            attempt.write_text('{"attempt":true}\n', encoding="utf-8")
            result.write_text('{"result":true}\n', encoding="utf-8")
            completion = root / "staged-completion.json"
            completion.write_text(
                '{"completion":true}\n',
                encoding="utf-8",
            )
            with (
                mock.patch.object(
                    finalizer,
                    "expected_manifest_artifacts",
                    return_value={},
                ),
                mock.patch.object(
                    finalizer,
                    "_phase_status",
                    return_value="accepted",
                ),
            ):
                manifest = finalizer._manifest_payload(
                    orchestrate,
                    root,
                    workflow_status="integration-passed",
                    completion_staging_path=completion,
                )
            rows = {
                item["role"]: item
                for item in manifest["artifacts"]
            }
            self.assertEqual(
                rows["final-integration-review-attempt"][
                    "trace-schema"
                ],
                FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
            )
            self.assertEqual(
                rows["final-integration-review-attempt-result"][
                    "trace-schema"
                ],
                FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA,
            )
            self.assertEqual(
                rows["final-integration-review-attempt"]["authority"],
                "control",
            )
            self.assertEqual(
                rows["final-integration-review-attempt-result"][
                    "authority"
                ],
                "control",
            )


if __name__ == "__main__":
    unittest.main()
