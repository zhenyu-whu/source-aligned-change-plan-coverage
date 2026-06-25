#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from source_aligned_trace_lib import (  # noqa: E402
    ATOM_PLAN_MAPPING_SCHEMA,
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
from validate_source_aligned_orchestrate import validate  # noqa: E402


class SourceAlignedValidatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.orchestrate = self.root / "openspec/orchestrate"
        self.script = SCRIPT_DIR / "validate_source_aligned_orchestrate.py"
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

    def _build_valid_fixture(self) -> None:
        source = "\n".join(f"line {i}" for i in range(1, 21)) + "\n"
        self._write("docs/source.md", source)
        self._write("openspec/orchestrate/change-plan.md", "# Plan\n")
        self._write("openspec/orchestrate/phase-works/phase-1/change-plan.md", "# Phase 1 Plan\n")
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
            "| Source Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Candidate Status | Candidate Artifact Projection | Candidate Owner Change | Candidate Owner Capability | Roles | Rationale | Propose Use | Evidence Need |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| atom.one | docs/source.md | L1-L2 | behavior | fact one | must | direct-candidate | spec-requirement | change-a | cap-a | primary | why | use | unit |\n"
            "| atom.two | docs/source.md | L1-L2 | explicit-non-goal | fact two | must-not | explicit-non-goal | spec-guard | change-a | cap-a | non-goal | why | use | none |\n",
        )
        self._write("openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/index.md", "index\n")
        self._write("openspec/orchestrate/phase-works/phase-2/source-obligation-review/index.html", "<!doctype html>\n")
        self._write("openspec/orchestrate/phase-works/phase-2/phase-2-agent-report.md", "ok\n")
        self._write(
            "openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md",
            "| Source Document | Classification | Phase 2 Atom File | Review File | Effective Atom Ranges | Missing Obligation Atom Ranges | Non-Atom Ranges | Read Scope | Reason |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| docs/source.md | covered-by-atoms | openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.md | openspec/orchestrate/phase-works/phase-3/source-doc-coverage/docs--source.coverage.md | L1-L2 | None | L3-L20 | full-source remainder audit | ok |\n",
        )
        self._write(
            "openspec/orchestrate/phase-works/phase-3/source-doc-coverage/docs--source.coverage.md",
            "| Global Atom ID | Source Atom Origins | Lines | Atom Type | Coverage Status | Artifact Projection | Candidate / Owner Change | Candidate / Owner Capability | Source Fact |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| GA-0001 | atom.one | L1-L2 | behavior | direct | spec-requirement | change-a | cap-a | fact one |\n"
            "| GA-0002 | atom.two | L1-L2 | explicit-non-goal | explicit-non-goal | spec-guard | change-a | cap-a | fact two |\n"
            "\n"
            "| Source Section or Range | Expected Atom Type | Global Atom IDs | Coverage Judgment | Reason |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| L1-L2 | behavior | GA-0001; GA-0002 | covered | ok |\n"
            "| L3-L20 | none | None | non-atom | safe remainder |\n"
            "\n"
            "| Candidate Range | Read Scope | Semantic Classification | Production Obligation? | Reason |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| L3-L20 | full-source remainder audit | formatting/background | false | no production obligation |\n",
        )
        self._write("openspec/orchestrate/phase-works/phase-3/coverage-review.md", "Decision: coverage-complete\n")
        self._write("openspec/orchestrate/phase-works/phase-3/coverage-review-app/index.html", "<!doctype html>\n")
        self._write("openspec/orchestrate/phase-works/phase-3/phase-3-agent-report.md", "ok\n")
        self._write("openspec/orchestrate/phase-works/phase-3/phase-3-trace/duplicate-ownership-review.md", "ok\n")
        self._write("openspec/orchestrate/phase-works/phase-3/phase-3-trace/atom-normalization-decision-log.md", "ok\n")
        self._write("openspec/orchestrate/phase-works/phase-4/input-change-plan.md", "input\n")
        self._write("openspec/orchestrate/phase-works/phase-4/source-window-dossiers/index.md", "index\n")
        self._write("openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md", "profile\n")
        self._write("openspec/orchestrate/phase-works/phase-4/source-window-grounding-issues.md", "issues\n")
        self._write("openspec/orchestrate/phase-works/phase-4/phase-4-agent-report.md", "Phase 4 Status: grounded\n")
        self._write("openspec/orchestrate/phase-works/phase-5/input-change-plan.md", "input\n")
        self._write("openspec/orchestrate/phase-works/phase-5/source-window-refit-trace.md", "trace\n")
        self._write("openspec/orchestrate/phase-works/phase-5/change-plan.md", "plan\n")
        self._write("openspec/orchestrate/phase-works/phase-5/capability-progression-review.md", "progression\n")
        self._write("openspec/orchestrate/phase-works/phase-5/plan-refit-decision-log.md", "decisions\n")
        self._write("openspec/orchestrate/phase-works/phase-5/alignment-final-report.md", "alignment\n")
        self._write("openspec/orchestrate/phase-works/phase-5/change-capability-human-plan.md", "human\n")
        self._write("openspec/orchestrate/phase-works/phase-5/phase-5-agent-report.md", "Phase 5 Status: adjusted\n")
        self._write("openspec/orchestrate/change-capability-anchors/index.md", "index\n")
        self._write(
            "openspec/orchestrate/change-capability-anchors/obligation-atom-index.md",
            "| Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Coverage Status | Artifact Projection | Owner Change | Owner Capability | Source Atom Origins | Atom Relation | Propose Use | Evidence Need | Review Judgment |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| GA-0001 | docs/source.md | L1-L2 | behavior | fact one | must | direct | spec-requirement | change-a | cap-a | atom.one | direct | use | unit | ok |\n"
            "| GA-0002 | docs/source.md | L1-L2 | explicit-non-goal | fact two | must-not | explicit-non-goal | spec-guard | change-a | cap-a | atom.two | non-goal | use | none | ok |\n",
        )
        self._write(
            "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.md",
            "| Global Atom ID | Source Document | Lines | Phase 3 Owner / Status | Phase 3 Artifact Projection | Final Owner Change | Final Owner Capability | Final Artifact Projection | Final Relation | Plan Decision | Reason |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| GA-0001 | docs/source.md | L1-L2 | change-a / direct | spec-requirement | change-a | cap-a | spec-requirement | direct | direct-owner | reason |\n"
            "| GA-0002 | docs/source.md | L1-L2 | change-a / explicit-non-goal | spec-guard | change-a | cap-a | spec-guard | non-goal | scoped-non-direct | reason |\n",
        )
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/change-a.md",
            "# change-a\n\n| Global Atom ID | Relation |\n| --- | --- |\n| GA-0001 | direct |\n| GA-0002 | non-goal |\n",
        )
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/capability-anchors/cap-a.md",
            "# cap-a\n\n| Global Atom ID | Relation |\n| --- | --- |\n| GA-0001 | direct |\n",
        )
        self._write(
            "openspec/orchestrate/phase-works/phase-5/change-complexity-review.md",
            "| Change | Direct Atom Count | Budget Status |\n| --- | --- | --- |\n| change-a | 1 | within-target |\n",
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
                "change-plan": {
                    "phase-plan-path": "openspec/orchestrate/phase-works/phase-1/change-plan.md",
                    "root-plan-path": "openspec/orchestrate/change-plan.md",
                    "phase-plan-sha256": sha256_file(self.orchestrate / "phase-works/phase-1/change-plan.md"),
                    "root-plan-sha256": sha256_file(self.orchestrate / "change-plan.md"),
                },
            },
        )
        source_atoms = [
            {
                "source-atom-id": "atom.one",
                "source-document": "docs/source.md",
                "lines": "L1-L2",
                "line-ranges": [{"start": 1, "end": 2}],
                "atom-type": "behavior",
                "source-fact": "fact one",
                "normativity": "must",
                "candidate-status": "direct-candidate",
                "candidate-artifact-projection": "spec-requirement",
                "candidate-owner-change": "change-a",
                "candidate-owner-capability": "cap-a",
                "roles": "primary",
                "rationale": "why",
                "propose-use": "use",
                "evidence-need": "unit",
            },
            {
                "source-atom-id": "atom.two",
                "source-document": "docs/source.md",
                "lines": "L1-L2",
                "line-ranges": [{"start": 1, "end": 2}],
                "atom-type": "explicit-non-goal",
                "source-fact": "fact two",
                "normativity": "must-not",
                "candidate-status": "explicit-non-goal",
                "candidate-artifact-projection": "spec-guard",
                "candidate-owner-change": "change-a",
                "candidate-owner-capability": "cap-a",
                "roles": "non-goal",
                "rationale": "why",
                "propose-use": "use",
                "evidence-need": "none",
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
                "source-atoms": source_atoms,
                "source-anchors": [],
                "section-inventory": [],
                "blockers": [],
            },
        )
        write_json(
            self.orchestrate / "trace/phase-2.trace.json",
            {
                "trace-schema": PHASE_TRACE_SCHEMAS["phase-2"],
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": "source-atoms-written",
                "work-queue-path": "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/work-queue.md",
                "sources": [],
            },
        )
        global_atoms = [
            {
                "global-atom-id": "GA-0001",
                "source-document": "docs/source.md",
                "lines": "L1-L2",
                "line-ranges": [{"start": 1, "end": 2}],
                "atom-type": "behavior",
                "source-fact": "fact one",
                "normativity": "must",
                "coverage-status": "direct",
                "artifact-projection": "spec-requirement",
                "owner-change": "change-a",
                "owner-capability": "cap-a",
                "source-atom-origins": "atom.one",
                "origins": ["atom.one"],
                "atom-relation": "direct",
                "propose-use": "use",
                "evidence-need": "unit",
                "review-judgment": "ok",
            },
            {
                "global-atom-id": "GA-0002",
                "source-document": "docs/source.md",
                "lines": "L1-L2",
                "line-ranges": [{"start": 1, "end": 2}],
                "atom-type": "explicit-non-goal",
                "source-fact": "fact two",
                "normativity": "must-not",
                "coverage-status": "explicit-non-goal",
                "artifact-projection": "spec-guard",
                "owner-change": "change-a",
                "owner-capability": "cap-a",
                "source-atom-origins": "atom.two",
                "origins": ["atom.two"],
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
                        "source-atom-id": "atom.one",
                        "lines": "L1-L2",
                        "line-ranges": [{"start": 1, "end": 2}],
                        "candidate-status": "direct-candidate",
                        "candidate-artifact-projection": "spec-requirement",
                        "candidate-owner-change": "change-a",
                        "candidate-owner-capability": "cap-a",
                        "global-atom-id": "GA-0001",
                        "global-coverage-status": "direct",
                        "global-artifact-projection": "spec-requirement",
                        "review-decision": "global-atom-created",
                        "reason": "ok",
                    },
                    {
                        "source-document": "docs/source.md",
                        "source-atom-id": "atom.two",
                        "lines": "L1-L2",
                        "line-ranges": [{"start": 1, "end": 2}],
                        "candidate-status": "explicit-non-goal",
                        "candidate-artifact-projection": "spec-guard",
                        "candidate-owner-change": "change-a",
                        "candidate-owner-capability": "cap-a",
                        "global-atom-id": "GA-0002",
                        "global-coverage-status": "explicit-non-goal",
                        "global-artifact-projection": "spec-guard",
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
                                "lines": "L1-L2",
                                "line-ranges": [{"start": 1, "end": 2}],
                                "origins": ["atom.one", "atom.two"],
                            }
                        ],
                        "candidate-uncovered-ranges": [
                            {
                                "lines": "L3-L20",
                                "line-ranges": [{"start": 3, "end": 20}],
                            }
                        ],
                    }
                ],
                "rows": [
                    {
                        "source-document": "docs/source.md",
                        "lines": "L3-L20",
                        "line-ranges": [{"start": 3, "end": 20}],
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
                        "final-owner-change": "change-a",
                        "final-owner-capability": "cap-a",
                        "final-artifact-projection": "spec-requirement",
                        "final-relation": "direct",
                        "plan-decision": "direct-owner",
                        "reason": "reason",
                    },
                    {
                        "global-atom-id": "GA-0002",
                        "source-document": "docs/source.md",
                        "lines": "L1-L2",
                        "line-ranges": [{"start": 1, "end": 2}],
                        "phase-3-owner-status": "change-a / explicit-non-goal",
                        "phase-3-artifact-projection": "spec-guard",
                        "final-owner-change": "change-a",
                        "final-owner-capability": "cap-a",
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
                        "packet-path": "openspec/orchestrate/change-capability-anchors/change-a/change-a.md",
                        "packet-digest": sha256_file(self.orchestrate / "change-capability-anchors/change-a/change-a.md"),
                        "direct-atom-ids": ["GA-0001"],
                        "owner-scoped-non-direct-atom-ids": ["GA-0002"],
                        "capability-view-paths": [
                            "openspec/orchestrate/change-capability-anchors/change-a/capability-anchors/cap-a.md"
                        ],
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
                "complexity-summaries": [],
                "capability-progression-summaries": [],
                "validator-gate-outcomes": [],
                "reviewer-gate-outcomes": [],
            },
        )
        self._write_manifest()

    def _write_manifest(self) -> None:
        specs = [
            ("openspec/orchestrate/trace/phase-1.trace.json", PHASE_TRACE_SCHEMAS["phase-1"], "phase-1"),
            ("openspec/orchestrate/trace/phase-2.trace.json", PHASE_TRACE_SCHEMAS["phase-2"], "phase-2"),
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

    def _validate(self, complete: bool = True) -> dict:
        return validate(self.orchestrate, self.root, "all", complete, False)

    def _validate_phase(self, phase: str, complete: bool = False) -> dict:
        return validate(self.orchestrate, self.root, phase, complete, False)

    def assert_error(self, rule_id: str) -> None:
        result = self._validate()
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == rule_id for issue in result["issues"]), result)

    def test_minimal_valid_orchestrate_passes(self) -> None:
        result = self._validate()
        self.assertTrue(result["ok"], result)

    def test_phase1_minimal_with_manifest_skeleton_passes(self) -> None:
        for trace in ("phase-2", "phase-3", "phase-4", "phase-5"):
            path = self.orchestrate / "trace" / f"{trace}.trace.json"
            if path.exists():
                path.unlink()
        self._write_manifest()
        result = self._validate_phase("phase-1")
        self.assertTrue(result["ok"], result)

    def test_manifest_digest_drift_fails(self) -> None:
        path = self.orchestrate / "trace/phase-1.trace.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "changed-after-manifest"
        write_json(path, data)
        result = self._validate_phase("phase-1")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "manifest-digest" for issue in result["issues"]), result)

    def test_manifest_present_status_is_rejected(self) -> None:
        path = self.orchestrate / "trace/manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["phase-statuses"]["phase-1"] = "present"
        write_json(path, data)
        result = self._validate_phase("phase-1")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(issue["rule_id"] == "manifest-phase-status-workflow-state" for issue in result["issues"]), result)

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

    def test_phase3_duplicate_ga_fails(self) -> None:
        path = self.orchestrate / "change-capability-anchors/obligation-atom-index.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["global-atoms"].append(dict(data["global-atoms"][0]))
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase3-ga-duplicate")

    def test_phase3_source_to_global_map_missing_atom_fails(self) -> None:
        path = self.orchestrate / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"] = data["rows"][:1]
        write_json(path, data)
        self._write_manifest()
        self.assert_error("phase3-map-coverage")

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

    def test_phase5_blocked_does_not_require_final_packets(self) -> None:
        trace_path = self.orchestrate / "trace/phase-5.trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["status"] = "blocked"
        write_json(trace_path, trace)
        for rel_path in (
            "phase-works/phase-5/atom-plan-mapping.json",
            "phase-works/phase-5/atom-plan-mapping.md",
            "phase-works/phase-5/final-packet-index.json",
        ):
            path = self.orchestrate / rel_path
            if path.exists():
                path.unlink()
        self._write("openspec/orchestrate/phase-works/phase-5/change-plan-adjustments.md", "blocked\n")
        self._write("openspec/orchestrate/phase-works/phase-5/phase-5-agent-report.md", "Phase 5 Status: blocked\n")
        self._write_manifest()
        result = self._validate_phase("phase-5")
        self.assertTrue(result["ok"], result)

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

    def test_phase5_non_direct_atom_missing_from_packet_fails(self) -> None:
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/change-a.md",
            "# change-a\n\n| Global Atom ID | Relation |\n| --- | --- |\n| GA-0001 | direct |\n",
        )
        self._write_manifest()
        self.assert_error("phase5-final-non-direct-packet")

    def test_capability_view_contains_non_direct_atom_fails(self) -> None:
        self._write(
            "openspec/orchestrate/change-capability-anchors/change-a/capability-anchors/cap-a.md",
            "# cap-a\n\n| Global Atom ID | Relation |\n| --- | --- |\n| GA-0001 | direct |\n| GA-0002 | non-goal |\n",
        )
        self.assert_error("phase5-capability-view-non-direct")

    def test_markdown_json_drift_fails(self) -> None:
        self._write(
            "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.md",
            "| Source Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Candidate Status | Candidate Artifact Projection | Candidate Owner Change | Candidate Owner Capability | Roles | Rationale | Propose Use | Evidence Need |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| atom.one | docs/source.md | L1-L2 | behavior | drifted fact | must | direct-candidate | spec-requirement | change-a | cap-a | primary | why | use | unit |\n"
            "| atom.two | docs/source.md | L3-L4 | explicit-non-goal | fact two | must-not | explicit-non-goal | spec-guard | change-a | cap-a | non-goal | why | use | none |\n",
        )
        self.assert_error("markdown-json-drift")

    def test_strict_warnings_returns_non_zero(self) -> None:
        self._write(
            "openspec/orchestrate/phase-works/phase-2/source-obligation-atoms/docs--source.atoms.md",
            "| Source Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Candidate Status | Candidate Artifact Projection | Candidate Owner Change | Candidate Owner Capability | Roles | Rationale | Propose Use | Evidence Need |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| atom.one | docs/source.md | `L1-L2` | behavior | fact one | must | direct-candidate | spec-requirement | change-a | cap-a | primary | why | use | unit |\n"
            "| atom.two | docs/source.md | L3-L4 | explicit-non-goal | fact two | must-not | explicit-non-goal | spec-guard | change-a | cap-a | non-goal | why | use | none |\n",
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


if __name__ == "__main__":
    unittest.main()
