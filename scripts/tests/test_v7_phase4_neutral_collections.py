#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import render_source_aligned_orchestrate as renderer  # noqa: E402
import validate_source_aligned_orchestrate as validator  # noqa: E402
from source_aligned_trace_lib import (  # noqa: E402
    EVIDENCE_COLLECTION_INDEX_SCHEMA,
    GLOBAL_ATOM_INDEX_SCHEMA,
    IssueReporter,
    PHASE_TRACE_SCHEMAS,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    repo_relative_path,
    sha256_file,
    source_atom_file_name,
    write_json,
)


class Phase4NeutralCollectionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.orchestrate = self.repo / "openspec/orchestrate"
        self.collection_root = (
            self.orchestrate
            / "phase-works/phase-4/source-evidence-collections"
        )
        self._build_frozen_evidence_fixture()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _atom_path(self, source: str) -> Path:
        filename = source_atom_file_name(source).replace(".md", ".json")
        return (
            self.orchestrate
            / "phase-works/phase-2/source-obligation-atoms"
            / filename
        )

    @staticmethod
    def _phase2_atom(
        atom_id: str,
        start: int,
        source_fact: str,
        directives: list[str],
        *,
        owner: str,
        capability: str,
    ) -> dict:
        return {
            "source-atom-id": atom_id,
            "line-ranges": [{"start": start, "end": start + 1}],
            "atom-type": "requirement",
            "source-fact": source_fact,
            "normativity": "normative",
            "delivery-directives": directives,
            "candidate-status": "mapped",
            "candidate-artifact-projection": "spec-requirement",
            "candidate-owner-change": owner,
            "candidate-target-capability": capability,
            "rationale": "仅用于证明中立 renderer 不泄漏 extraction-time routing hint。",
        }

    def _write_atom_file(self, source: str, atoms: list[dict]) -> None:
        write_json(
            self._atom_path(source),
            {
                "trace-schema": SOURCE_ATOMS_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "source-document": source,
                "canonical-owner": f"writer-{Path(source).stem}",
                "source-atoms": atoms,
            },
        )

    def _build_frozen_evidence_fixture(self) -> None:
        repeated_fact = "same | requirement\n```embedded```\nsame outcome"
        self._write_atom_file(
            "docs/zeta.md",
            [
                self._phase2_atom(
                    "P2-ZETA-001",
                    20,
                    repeated_fact,
                    [],
                    owner="candidate-owner-zeta",
                    capability="candidate-capability-zeta",
                )
            ],
        )
        self._write_atom_file(
            "docs/alpha.md",
            [
                self._phase2_atom(
                    "P2-ALPHA-001",
                    10,
                    repeated_fact,
                    ["milestone-scope"],
                    owner="candidate-owner-alpha",
                    capability="candidate-capability-alpha",
                )
            ],
        )

        coverage_path = (
            self.orchestrate / "phase-works/phase-3/coverage-review.json"
        )
        write_json(
            coverage_path,
            {
                "trace-schema": PHASE3_COVERAGE_REVIEW_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "gap-atoms": [
                    {
                        "gap-atom-id": "P3-GAP-0001",
                        "source-document": "docs/alpha.md",
                        "line-ranges": [{"start": 5, "end": 5}],
                        "source-fact": "Alpha 必须在 Zeta 之前交付。",
                        "atom-type": "constraint",
                        "normativity": "normative",
                        "delivery-directives": ["explicit-precedence"],
                        "review-judgment": "原文明确表达交付先后。",
                    }
                ],
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
                "global-atoms": [
                    {
                        "global-atom-id": "GA-0001",
                        "evidence-ref": {
                            "kind": "phase-2-source-atom",
                            "source-document": "docs/zeta.md",
                            "source-atom-id": "P2-ZETA-001",
                        },
                    },
                    {
                        "global-atom-id": "GA-0002",
                        "evidence-ref": {
                            "kind": "phase-2-source-atom",
                            "source-document": "docs/alpha.md",
                            "source-atom-id": "P2-ALPHA-001",
                        },
                    },
                    {
                        "global-atom-id": "GA-0003",
                        "evidence-ref": {
                            "kind": "phase-3-gap-atom",
                            "gap-atom-id": "P3-GAP-0001",
                        },
                    },
                ],
            },
        )

    def _relative_output_paths(
        self,
        outputs: dict[Path, str],
    ) -> set[str]:
        return {
            path.relative_to(self.collection_root).as_posix()
            for path in outputs
        }

    def _actual_surface(self) -> tuple[set[str], set[str]]:
        files = {
            path.relative_to(self.collection_root).as_posix()
            for path in self.collection_root.rglob("*")
            if path.is_file()
        }
        directories = {
            path.relative_to(self.collection_root).as_posix()
            for path in self.collection_root.rglob("*")
            if path.is_dir()
        }
        return files, directories

    def _write_phase4_validation_contract(self) -> None:
        renderer.render_orchestrate(
            self.orchestrate,
            "phase4-evidence-collections",
            write=True,
        )
        report_path = (
            self.orchestrate
            / "phase-works/phase-4/phase-4-agent-report.md"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("# Phase 4 agent report\n", encoding="utf-8")

        index_path = (
            self.collection_root / "evidence-collection-index.json"
        )
        index = json.loads(index_path.read_text(encoding="utf-8"))
        trace_path = self.orchestrate / "trace/phase-4.trace.json"
        write_json(
            trace_path,
            {
                "trace-schema": PHASE_TRACE_SCHEMAS["phase-4"],
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": "assembled",
                "assembled": {
                    "evidence-collection-index-path": repo_relative_path(
                        index_path,
                        self.repo,
                    ),
                    "evidence-collection-index-sha256": sha256_file(
                        index_path,
                    ),
                    "renderer-result-summary": {
                        "render-contract-version": (
                            renderer.RENDER_CONTRACT_VERSION
                        ),
                        "rendered-files": len(
                            renderer.render_evidence_collections(
                                self.orchestrate
                            )
                        ),
                        "global-atoms": len(index["rows"]),
                    },
                },
            },
        )

    def _update_phase4_trace_index_digest(self) -> None:
        index_path = (
            self.collection_root / "evidence-collection-index.json"
        )
        trace_path = self.orchestrate / "trace/phase-4.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["assembled"]["evidence-collection-index-sha256"] = (
            sha256_file(index_path)
        )
        write_json(trace_path, trace)

    def _validate_phase4(self) -> IssueReporter:
        reporter = IssueReporter()
        with mock.patch.object(
            validator,
            "_validate_phase3_freeze_marker",
        ):
            validator.validate_phase_4(
                self.orchestrate,
                self.repo,
                reporter,
            )
        return reporter

    def test_delivery_directive_order_and_summary_match_v7_contract(self) -> None:
        self.assertTrue(
            validator._delivery_directives_are_canonical(
                [
                    "milestone-scope",
                    "explicit-precedence",
                    "explicit-deferred",
                ]
            )
        )
        self.assertFalse(
            validator._delivery_directives_are_canonical(
                [
                    "explicit-deferred",
                    "explicit-precedence",
                    "milestone-scope",
                ]
            )
        )
        atom_count, directive_counts = (
            validator._delivery_directive_summary(
                [
                    {"delivery-directives": []},
                    {"delivery-directives": ["milestone-scope"]},
                    {
                        "delivery-directives": [
                            "milestone-scope",
                            "explicit-precedence",
                        ]
                    },
                    {"delivery-directives": ["explicit-deferred"]},
                ]
            )
        )
        self.assertEqual(atom_count, 3)
        self.assertEqual(
            directive_counts,
            {
                "milestone-scope": 2,
                "explicit-precedence": 1,
                "explicit-deferred": 1,
            },
        )

    def test_phase3_terminal_review_requires_directive_audit_status(
        self,
    ) -> None:
        gate = {
            "status": "passed",
            "phase-2-canonical-owner-ids": [
                "writer-alpha",
                "writer-zeta",
            ],
            "phase-2-aggregate-writer-id": "writer-phase2-aggregate",
            "phase-3-writer-id": "writer-phase3",
            "reviews": [
                {
                    "round": 1,
                    "stage": "phase-3-closure",
                    "reviewer-id": "reviewer-terminal",
                    "phase-2-validator-status": "passed",
                    "phase-3-validator-status": "passed",
                    "delivery-directive-status": "passed",
                    "evidence-authority-sha256": "a" * 64,
                    "finding-fingerprints": [],
                }
            ],
            "repairs": [],
        }
        trace_path = self.orchestrate / "trace/phase-3.trace.json"
        reporter = IssueReporter()
        with mock.patch.object(
            validator,
            "evidence_authority_sha256",
            return_value="a" * 64,
        ):
            status = validator._validate_phase3_review_gate(
                gate,
                trace_path,
                self.orchestrate,
                self.repo,
                reporter,
            )
        self.assertEqual(status, "passed")
        self.assertEqual(reporter.error_count, 0)

        del gate["reviews"][0]["delivery-directive-status"]
        missing_reporter = IssueReporter()
        with mock.patch.object(
            validator,
            "evidence_authority_sha256",
            return_value="a" * 64,
        ):
            validator._validate_phase3_review_gate(
                gate,
                trace_path,
                self.orchestrate,
                self.repo,
                missing_reporter,
            )
        rule_ids = {
            issue.rule_id
            for issue in missing_reporter.issues
        }
        self.assertIn("phase3-review-row-fields", rule_ids)
        self.assertIn("phase3-review-directive-status", rule_ids)
        self.assertIn("phase3-review-terminal-review", rule_ids)

    def test_neutral_surface_is_source_scoped_and_hides_candidate_routing(self) -> None:
        outputs = renderer.render_evidence_collections(self.orchestrate)
        self.assertEqual(
            self._relative_output_paths(outputs),
            {
                "index.md",
                "all-evidence.md",
                "delivery-directives.md",
                "by-source/docs--alpha.md",
                "by-source/docs--zeta.md",
            },
        )

        combined = "\n".join(outputs.values())
        for forbidden in (
            "candidate-owner-alpha",
            "candidate-owner-zeta",
            "candidate-capability-alpha",
            "candidate-capability-zeta",
            "Candidate owner Change",
            "Candidate target Capability",
            "by-input-change",
            "by-input-capability",
            "unassigned-and-gap",
        ):
            self.assertNotIn(forbidden, combined)

        all_evidence = outputs[self.collection_root / "all-evidence.md"]
        self.assertLess(
            all_evidence.index("GA-0003"),
            all_evidence.index("GA-0002"),
        )
        self.assertLess(
            all_evidence.index("GA-0002"),
            all_evidence.index("GA-0001"),
        )
        self.assertEqual(all_evidence.count("same | requirement"), 2)
        self.assertIn("````text\nsame | requirement\n```embedded```", all_evidence)

        directives = outputs[
            self.collection_root / "delivery-directives.md"
        ]
        self.assertIn("GA-0002", directives)
        self.assertIn("GA-0003", directives)
        self.assertNotIn("GA-0001", directives)
        self.assertIn("milestone-scope", directives)
        self.assertIn("explicit-precedence", directives)

        index = renderer.build_evidence_collection_index(
            self.orchestrate,
            outputs,
        )
        self.assertEqual(
            index["trace-schema"],
            EVIDENCE_COLLECTION_INDEX_SCHEMA,
        )
        self.assertEqual(
            index["trace-contract-version"],
            TRACE_CONTRACT_VERSION,
        )
        self.assertFalse(
            any(
                row["artifact-path"].endswith("initial-change-plan.md")
                for row in index["generated-from"]
            )
        )
        self.assertEqual(
            [row["global-atom-id"] for row in index["rows"]],
            ["GA-0003", "GA-0002", "GA-0001"],
        )
        rows = {
            row["global-atom-id"]: row
            for row in index["rows"]
        }
        self.assertEqual(len(rows["GA-0001"]["rendered-collection-paths"]), 2)
        self.assertEqual(len(rows["GA-0002"]["rendered-collection-paths"]), 3)
        self.assertTrue(
            rows["GA-0002"]["rendered-collection-paths"][-1].endswith(
                "/delivery-directives.md"
            )
        )
        self.assertEqual(
            {row["collection-kind"] for row in index["rendered-artifacts"]},
            {"index", "all-evidence", "delivery-directives", "source"},
        )
        self.assertTrue(
            all(
                set(row)
                == {
                    "artifact-path",
                    "sha256",
                    "collection-kind",
                    "scope",
                }
                for row in index["rendered-artifacts"]
            )
        )

    def test_write_replaces_stale_surface_and_enforces_exact_surface(self) -> None:
        stale = self.collection_root / "by-input-change/stale.md"
        stale.parent.mkdir(parents=True)
        stale.write_text("stale", encoding="utf-8")
        (self.collection_root / "unassigned-and-gap.md").write_text(
            "stale",
            encoding="utf-8",
        )

        result = renderer.render_orchestrate(
            self.orchestrate,
            "phase4-evidence-collections",
            write=True,
        )
        self.assertTrue(result["ok"])
        files, directories = self._actual_surface()
        self.assertEqual(
            files,
            {
                "evidence-collection-index.json",
                "index.md",
                "all-evidence.md",
                "delivery-directives.md",
                "by-source/docs--alpha.md",
                "by-source/docs--zeta.md",
            },
        )
        self.assertEqual(directories, {"by-source"})

        check = renderer.render_orchestrate(
            self.orchestrate,
            "phase4-evidence-collections",
            write=False,
        )
        self.assertTrue(check["ok"])
        self.assertEqual(check["drift-count"], 0)

        (self.collection_root / "stale.md").write_text(
            "stale",
            encoding="utf-8",
        )
        drift = renderer.render_orchestrate(
            self.orchestrate,
            "phase4-evidence-collections",
            write=False,
        )
        self.assertFalse(drift["ok"])
        self.assertGreater(drift["drift-count"], 0)

        renderer.render_orchestrate(
            self.orchestrate,
            "phase4-evidence-collections",
            write=True,
        )
        files, directories = self._actual_surface()
        self.assertNotIn("stale.md", files)
        self.assertEqual(directories, {"by-source"})

    def test_staging_failure_preserves_the_previous_surface(self) -> None:
        self.collection_root.mkdir(parents=True)
        sentinel = self.collection_root / "sentinel.md"
        sentinel.write_text("previous complete surface", encoding="utf-8")

        with mock.patch.object(
            renderer,
            "_write_phase4_staging_surface",
            side_effect=RuntimeError("synthetic staging failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "synthetic staging failure",
            ):
                renderer.render_orchestrate(
                    self.orchestrate,
                    "phase4-evidence-collections",
                    write=True,
                )

        self.assertEqual(
            sentinel.read_text(encoding="utf-8"),
            "previous complete surface",
        )
        self.assertFalse(
            any(
                path.name.startswith(".phase4-neutral-")
                for path in self.collection_root.parent.iterdir()
            )
        )

    def test_written_index_is_the_deterministic_renderer_result(self) -> None:
        renderer.render_orchestrate(
            self.orchestrate,
            "phase4-evidence-collections",
            write=True,
        )
        index_path = self.collection_root / "evidence-collection-index.json"
        actual = json.loads(index_path.read_text(encoding="utf-8"))
        outputs = renderer.render_evidence_collections(self.orchestrate)
        expected = renderer.build_evidence_collection_index(
            self.orchestrate,
            outputs,
        )
        self.assertEqual(actual, expected)

    def test_phase4_validator_accepts_exact_neutral_surface_without_phase1_plan(
        self,
    ) -> None:
        self._write_phase4_validation_contract()
        self.assertFalse(
            (
                self.orchestrate
                / "phase-works/phase-1/initial-change-plan.md"
            ).exists()
        )
        reporter = self._validate_phase4()
        self.assertEqual(reporter.result(), {
            "ok": True,
            "error-count": 0,
            "warning-count": 0,
            "issues": [],
        })

    def test_phase4_validator_rejects_any_extra_file_and_directory(
        self,
    ) -> None:
        self._write_phase4_validation_contract()
        stale = self.collection_root / "stale-view/stale.md"
        stale.parent.mkdir()
        stale.write_text("stale\n", encoding="utf-8")

        reporter = self._validate_phase4()
        rule_ids = {issue.rule_id for issue in reporter.issues}
        self.assertIn("phase4-surface-extra-file", rule_ids)
        self.assertIn("phase4-surface-extra-directory", rule_ids)

    def test_phase4_validator_rejects_symlinked_surface_entry(self) -> None:
        self._write_phase4_validation_contract()
        (
            self.collection_root / "linked-index.md"
        ).symlink_to(self.collection_root / "index.md")

        reporter = self._validate_phase4()
        rule_ids = {issue.rule_id for issue in reporter.issues}
        self.assertIn("phase4-surface-invalid-entry", rule_ids)

    def test_phase4_validator_rejects_non_v3_index_row_shape(self) -> None:
        self._write_phase4_validation_contract()
        index_path = (
            self.collection_root / "evidence-collection-index.json"
        )
        index = json.loads(index_path.read_text(encoding="utf-8"))
        first_row = index["rows"][0]
        first_row["source-collection-path"] = first_row.pop(
            "rendered-collection-paths"
        )[1]
        write_json(index_path, index)
        self._update_phase4_trace_index_digest()

        reporter = self._validate_phase4()
        rule_ids = {issue.rule_id for issue in reporter.issues}
        self.assertIn("phase4-index-row-fields", rule_ids)
        self.assertIn("phase4-index-collection-paths", rule_ids)
        self.assertIn("phase4-derived-index-drift", rule_ids)


if __name__ == "__main__":
    unittest.main()
