#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v8 one-shot workflow attempt loader and validator integration tests."""

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

from source_aligned_trace_lib import (  # noqa: E402
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
    MANIFEST_SCHEMA,
    TRACE_CONTRACT_VERSION,
    IssueReporter,
    sha256_file,
    write_json,
)
from source_aligned_v8_contract import (  # noqa: E402
    load_final_integration_review_attempt,
    load_final_integration_review_attempt_result,
)
import validate_source_aligned_orchestrate as validator  # noqa: E402


class WorkflowAttemptValidatorTests(unittest.TestCase):
    @staticmethod
    def _authorities(
        root: Path,
        *,
        result_status: str = "passed",
        terminal_digest: str | None = "a" * 64,
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
        review.write_text('{"review":"submitted"}\n', encoding="utf-8")
        write_json(
            attempt,
            {
                "trace-schema": (
                    FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA
                ),
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": "submitted",
                "final-integration-review-path": (
                    "openspec/orchestrate/"
                    "final-integration-review.json"
                ),
                "final-integration-review-sha256": sha256_file(review),
            },
        )
        write_json(
            result,
            {
                "trace-schema": (
                    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA
                ),
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": result_status,
                "final-integration-review-attempt-path": (
                    "openspec/orchestrate/trace/"
                    "final-integration-review-attempt.trace.json"
                ),
                "final-integration-review-attempt-sha256": sha256_file(
                    attempt
                ),
                "terminal-authority-sha256": terminal_digest,
                "issues": (
                    []
                    if result_status == "passed"
                    else ["终态审查提交未通过语义校验。"]
                ),
            },
        )
        return orchestrate, review, attempt, result

    def test_loaders_enforce_exact_raw_byte_binding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _orchestrate, review, attempt, result = self._authorities(
                root
            )
            loaded_attempt = load_final_integration_review_attempt(
                attempt,
                review_path=review,
                repo_root=root,
            )
            loaded_result = (
                load_final_integration_review_attempt_result(
                    result,
                    attempt_path=attempt,
                    repo_root=root,
                    expected_terminal_digest="a" * 64,
                )
            )
            self.assertEqual(loaded_attempt["status"], "submitted")
            self.assertEqual(loaded_result["status"], "passed")

            review.write_text(
                '{"review":"replacement"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "attempt digest drift"):
                load_final_integration_review_attempt(
                    attempt,
                    review_path=review,
                    repo_root=root,
                )

            # Result remains bound to the original attempt raw bytes.
            attempt_data = json.loads(
                attempt.read_text(encoding="utf-8")
            )
            attempt_data["status"] = "replaced"
            write_json(attempt, attempt_data)
            with self.assertRaisesRegex(
                ValueError,
                "attempt result digest drift",
            ):
                load_final_integration_review_attempt_result(
                    result,
                    attempt_path=attempt,
                    repo_root=root,
                    expected_terminal_digest="a" * 64,
                )

    def test_blocked_result_allows_null_terminal_digest_but_not_empty_issues(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _orchestrate, _review, attempt, result = self._authorities(
                root,
                result_status="blocked",
                terminal_digest=None,
            )
            loaded = load_final_integration_review_attempt_result(
                result,
                attempt_path=attempt,
                repo_root=root,
                expected_terminal_digest="a" * 64,
            )
            self.assertEqual(loaded["status"], "blocked")
            self.assertIsNone(loaded["terminal-authority-sha256"])

            data = json.loads(result.read_text(encoding="utf-8"))
            data["issues"] = []
            write_json(result, data)
            with self.assertRaisesRegex(ValueError, "必须包含issues"):
                load_final_integration_review_attempt_result(
                    result,
                    attempt_path=attempt,
                    repo_root=root,
                )

    def test_early_invalid_blocked_result_is_fail_closed_without_completion(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate, _review, _attempt, _result = self._authorities(
                root,
                result_status="blocked",
                terminal_digest=None,
            )
            reporter = IssueReporter()
            validator.validate_workflow_terminal(
                orchestrate,
                root,
                reporter,
                required=False,
            )
            self.assertTrue(
                any(
                    item.rule_id == "workflow-early-blocked-attempt"
                    for item in reporter.issues
                ),
                [item.message for item in reporter.issues],
            )
            self.assertFalse(
                (
                    orchestrate
                    / "trace/workflow-completion.trace.json"
                ).exists()
            )

    def test_completed_passed_workflow_requires_consistent_attempt_result(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate, _review, _attempt, result = self._authorities(
                root
            )
            completion = (
                orchestrate / "trace/workflow-completion.trace.json"
            )
            completion.write_text('{"completion":true}\n', encoding="utf-8")
            with (
                mock.patch.object(
                    validator,
                    "terminal_authority_sha256",
                    return_value="a" * 64,
                ),
                mock.patch.object(
                    validator,
                    "validate_final_integration_review_candidate",
                    return_value={"status": "passed", "findings": []},
                ),
                mock.patch.object(
                    validator,
                    "validate_rendered_markdown",
                ),
                mock.patch.object(
                    validator,
                    "load_workflow_completion",
                    return_value={
                        "status": "integration-passed",
                        "issues": [],
                    },
                ),
            ):
                reporter = IssueReporter()
                validator.validate_workflow_terminal(
                    orchestrate,
                    root,
                    reporter,
                    required=True,
                )
                self.assertEqual(
                    reporter.error_count,
                    0,
                    [item.message for item in reporter.issues],
                )

                result_data = json.loads(
                    result.read_text(encoding="utf-8")
                )
                result_data["terminal-authority-sha256"] = "b" * 64
                write_json(result, result_data)
                drift = IssueReporter()
                validator.validate_workflow_terminal(
                    orchestrate,
                    root,
                    drift,
                    required=True,
                )
                self.assertTrue(
                    any(
                        item.rule_id
                        == "workflow-final-review-attempt-result"
                        for item in drift.issues
                    ),
                    [item.message for item in drift.issues],
                )

    def test_manifest_inventory_includes_control_rows_only_when_terminal(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate, _review, attempt, result = self._authorities(
                root
            )
            with_workflow = validator.expected_manifest_artifacts(
                orchestrate,
                root,
                include_workflow_artifacts=True,
            )
            pending = validator.expected_manifest_artifacts(
                orchestrate,
                root,
                include_workflow_artifacts=False,
            )
            attempt_rel = attempt.relative_to(root).as_posix()
            result_rel = result.relative_to(root).as_posix()
            self.assertIn(attempt_rel, with_workflow)
            self.assertIn(result_rel, with_workflow)
            self.assertNotIn(attempt_rel, pending)
            self.assertNotIn(result_rel, pending)

            write_json(
                orchestrate / "trace/manifest.json",
                {
                    "trace-schema": MANIFEST_SCHEMA,
                    "trace-contract-version": TRACE_CONTRACT_VERSION,
                    "authority": "control",
                    "orchestrate-dir": "openspec/orchestrate",
                    "phase-statuses": {
                        f"phase-{index}": "missing"
                        for index in range(1, 6)
                    },
                    "workflow-status": "pending",
                    "artifacts": [],
                },
            )
            reporter = IssueReporter()
            validator.validate_manifest(
                orchestrate,
                root,
                reporter,
                include_workflow_artifacts=False,
                required_workflow_status="pending",
            )
            self.assertEqual(
                reporter.error_count,
                0,
                [item.message for item in reporter.issues],
            )


if __name__ == "__main__":
    unittest.main()
