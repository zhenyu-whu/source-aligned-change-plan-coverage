#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backfill JSON trace sidecars from existing source-aligned Markdown artifacts."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from source_aligned_trace_lib import (
    ATOM_PLAN_MAPPING_SCHEMA,
    FINAL_PACKET_INDEX_SCHEMA,
    GLOBAL_ATOM_INDEX_SCHEMA,
    MANIFEST_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    SOURCE_TO_GLOBAL_MAP_SCHEMA,
    SOURCE_WINDOW_INDEX_SCHEMA,
    TRACE_CONTRACT_VERSION,
    cell,
    coverage_file_name,
    extract_ga_ids,
    parse_line_ranges,
    read_json,
    row_to_kebab,
    sha256_file,
    sha256_text,
    source_atom_file_name,
    source_text_for_ranges,
    split_id_list,
    table_rows,
    write_json,
    normalize_code,
    squash,
)


def rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def source_sha(repo_root: Path, source_document: str) -> str:
    path = repo_root / source_document
    return sha256_file(path) if path.exists() else ""


def file_line_count(repo_root: Path, source_document: str) -> int:
    path = repo_root / source_document
    return len(path.read_text(encoding="utf-8").splitlines()) if path.exists() else 0


def trace_phase_status(orchestrate_dir: Path, phase: str) -> str:
    path = orchestrate_dir / f"trace/{phase}.trace.json"
    if not path.exists():
        return ""
    try:
        data = read_json(path)
    except Exception:  # noqa: BLE001
        return ""
    return normalize_code(data.get("status") or data.get("decision") or "")


def phase_status(orchestrate_dir: Path, phase: str) -> str:
    trace_status = trace_phase_status(orchestrate_dir, phase)
    if trace_status:
        return trace_status
    candidates = {
        "phase-3": orchestrate_dir / "phase-works/phase-3/coverage-review.md",
        "phase-4": orchestrate_dir / "phase-works/phase-4/phase-4-agent-report.md",
        "phase-5": orchestrate_dir / "phase-works/phase-5/phase-5-agent-report.md",
    }
    path = candidates.get(phase)
    if not path or not path.exists():
        return "present" if (orchestrate_dir / f"phase-works/{phase}").exists() else "missing"
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("Decision:"):
            return stripped.split(":", 1)[1].strip()
        if stripped.startswith("Phase 4 Status:"):
            return stripped.split(":", 1)[1].strip()
        if stripped.startswith("Phase 5 Status:"):
            return stripped.split(":", 1)[1].strip()
    return "present"


def manifest_sources(orchestrate_dir: Path, repo_root: Path) -> List[Dict[str, object]]:
    manifest_path = orchestrate_dir / "phase-works/phase-1/source-doc-manifest.md"
    rows = table_rows(manifest_path, ["Source Document", "Read Status", "Source Role"])
    sources: List[Dict[str, object]] = []
    for raw in rows:
        source_document = normalize_code(cell(raw, "Source Document"))
        item = row_to_kebab(
            raw,
            code_fields=["Source Document", "Read Status"],
        )
        item["source-document"] = source_document
        item["read-status"] = normalize_code(cell(raw, "Read Status"))
        item["source-role"] = squash(cell(raw, "Source Role"))
        item["coarse-topics-paths"] = squash(cell(raw, "Coarse Topics / Paths"))
        item["notes"] = squash(cell(raw, "Notes"))
        item["line-count"] = file_line_count(repo_root, source_document)
        item["source-sha256"] = source_sha(repo_root, source_document)
        sources.append(item)
    return sources


def backfill_phase_1(orchestrate_dir: Path, repo_root: Path, write: bool) -> Optional[Path]:
    trace_path = orchestrate_dir / "trace/phase-1.trace.json"
    phase_plan = orchestrate_dir / "phase-works/phase-1/change-plan.md"
    root_plan = orchestrate_dir / "change-plan.md"
    data = {
        "trace-schema": PHASE_TRACE_SCHEMAS["phase-1"],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "source-documents": manifest_sources(orchestrate_dir, repo_root),
        "change-plan": {
            "phase-plan-path": rel(phase_plan, repo_root),
            "root-plan-path": rel(root_plan, repo_root),
            "phase-plan-sha256": sha256_file(phase_plan) if phase_plan.exists() else "",
            "root-plan-sha256": sha256_file(root_plan) if root_plan.exists() else "",
        },
    }
    if write:
        write_json(trace_path, data)
    return trace_path


def owner_by_source(orchestrate_dir: Path) -> Dict[str, str]:
    path = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms/work-queue.md"
    owners: Dict[str, str] = {}
    for row in table_rows(path, ["Source Documents", "Canonical Owner"]):
        owner = normalize_code(cell(row, "Canonical Owner"))
        docs_cell = cell(row, "Source Documents")
        for source_document in re.split(r"<br\s*/?>|\n", docs_cell):
            source = normalize_code(source_document)
            if source:
                owners[source] = owner
    return owners


def parse_section_ranges(value: str) -> tuple[str, List[Dict[str, int]]]:
    first = normalize_code(value).split(" ", 1)[0]
    canonical, ranges, _, _ = parse_line_ranges(first)
    return canonical, ranges


def parse_source_atoms(atom_file: Path) -> tuple[List[Dict[str, object]], List[Dict[str, object]], List[Dict[str, object]]]:
    section_rows = table_rows(atom_file, ["Source Section or Range", "Read Status", "Production Meaning"])
    atom_rows = table_rows(atom_file, ["Source Atom ID", "Source Document", "Lines", "Candidate Status"])
    anchor_rows = table_rows(atom_file, ["Anchor", "Source Document", "Lines"])

    sections: List[Dict[str, object]] = []
    for raw in section_rows:
        item = row_to_kebab(raw, code_fields=["Read Status", "Non-Atom Classification"])
        canonical, ranges = parse_section_ranges(cell(raw, "Source Section or Range"))
        item["line-ranges"] = ranges
        if canonical:
            item["lines"] = canonical
        item["atom-ids"] = split_id_list(cell(raw, "Atom IDs"))
        sections.append(item)

    atoms: List[Dict[str, object]] = []
    for raw in atom_rows:
        source_document = normalize_code(cell(raw, "Source Document"))
        canonical, ranges, _, _ = parse_line_ranges(cell(raw, "Lines"))
        item = row_to_kebab(
            raw,
            code_fields=[
                "Source Atom ID",
                "Source Document",
                "Normativity",
                "Candidate Status",
                "Candidate Artifact Projection",
                "Candidate Owner Change",
                "Candidate Owner Capability",
                "Roles",
                "Evidence Need",
            ],
        )
        item["source-atom-id"] = normalize_code(cell(raw, "Source Atom ID"))
        item["source-document"] = source_document
        item["lines"] = canonical or normalize_code(cell(raw, "Lines"))
        item["line-ranges"] = ranges
        atoms.append(item)

    anchors: List[Dict[str, object]] = []
    for raw in anchor_rows:
        canonical, ranges, _, _ = parse_line_ranges(cell(raw, "Lines"))
        item = row_to_kebab(raw, code_fields=["Anchor", "Source Document", "Source Atom IDs"])
        item["source-document"] = normalize_code(cell(raw, "Source Document"))
        item["lines"] = canonical or normalize_code(cell(raw, "Lines"))
        item["line-ranges"] = ranges
        item["source-atom-ids"] = split_id_list(cell(raw, "Source Atom IDs", "Atom IDs"))
        anchors.append(item)
    return sections, atoms, anchors


def backfill_phase_2(orchestrate_dir: Path, repo_root: Path, write: bool) -> Optional[Path]:
    owner_map = owner_by_source(orchestrate_dir)
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    source_docs = manifest_sources(orchestrate_dir, repo_root)
    source_summaries: List[Dict[str, object]] = []

    for source in source_docs:
        if source.get("read-status") != "read-full":
            continue
        source_document = str(source["source-document"])
        atom_file = atom_root / source_atom_file_name(source_document)
        if not atom_file.exists():
            continue
        sections, atoms, anchors = parse_source_atoms(atom_file)
        data = {
            "trace-schema": SOURCE_ATOMS_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "source-document": source_document,
            "source-sha256": source_sha(repo_root, source_document),
            "read-status": "read-full",
            "canonical-owner": owner_map.get(source_document, ""),
            "section-inventory": sections,
            "source-atoms": atoms,
            "source-anchors": anchors,
            "blockers": [],
        }
        sidecar = atom_file.with_suffix(".json")
        if write:
            write_json(sidecar, data)
        source_summaries.append(
            {
                "source-document": source_document,
                "atom-artifact-path": rel(atom_file, repo_root),
                "trace-path": rel(sidecar, repo_root),
                "canonical-owner": owner_map.get(source_document, ""),
                "source-atom-count": len(atoms),
                "source-anchor-count": len(anchors),
                "section-count": len(sections),
            }
        )

    trace_path = orchestrate_dir / "trace/phase-2.trace.json"
    data = {
        "trace-schema": PHASE_TRACE_SCHEMAS["phase-2"],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "work-queue-path": rel(atom_root / "work-queue.md", repo_root),
        "sources": source_summaries,
        "phase-report-path": rel(orchestrate_dir / "phase-works/phase-2/phase-2-agent-report.md", repo_root),
    }
    if write:
        write_json(trace_path, data)
    return trace_path


def backfill_global_atom_index(orchestrate_dir: Path, repo_root: Path, write: bool) -> Path:
    source_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.md"
    trace_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    atoms: List[Dict[str, object]] = []
    for raw in table_rows(source_path, ["Global Atom ID", "Source Document", "Lines", "Coverage Status"]):
        source_document = normalize_code(cell(raw, "Source Document"))
        canonical, ranges, _, _ = parse_line_ranges(cell(raw, "Lines"))
        item = row_to_kebab(
            raw,
            code_fields=[
                "Global Atom ID",
                "Source Document",
                "Normativity",
                "Coverage Status",
                "Artifact Projection",
                "Owner Change",
                "Owner Capability",
                "Source Atom Origins",
                "Atom Relation",
                "Evidence Need",
            ],
        )
        item["global-atom-id"] = normalize_code(cell(raw, "Global Atom ID"))
        item["source-document"] = source_document
        item["lines"] = canonical or normalize_code(cell(raw, "Lines"))
        item["line-ranges"] = ranges
        item["origins"] = split_id_list(cell(raw, "Source Atom Origins"))
        atoms.append(item)
    data = {
        "trace-schema": GLOBAL_ATOM_INDEX_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "artifact-path": rel(source_path, repo_root),
        "global-atoms": atoms,
    }
    if write:
        write_json(trace_path, data)
    return trace_path


def backfill_source_to_global_map(orchestrate_dir: Path, repo_root: Path, write: bool) -> Path:
    source_path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.md"
    trace_path = source_path.with_suffix(".json")
    rows: List[Dict[str, object]] = []
    for raw in table_rows(source_path, ["Source Document", "Source Atom ID", "Lines", "Global Atom ID or Relation"]):
        canonical, ranges, _, _ = parse_line_ranges(cell(raw, "Lines"))
        relation = normalize_code(cell(raw, "Global Atom ID or Relation"))
        item = row_to_kebab(
            raw,
            code_fields=[
                "Source Document",
                "Source Atom ID",
                "Candidate Status",
                "Candidate Artifact Projection",
                "Candidate Owner Change",
                "Candidate Owner Capability",
                "Global Coverage Status",
                "Global Artifact Projection",
                "Review Decision",
            ],
        )
        item["source-document"] = normalize_code(cell(raw, "Source Document"))
        item["source-atom-id"] = normalize_code(cell(raw, "Source Atom ID"))
        item["lines"] = canonical or normalize_code(cell(raw, "Lines"))
        item["line-ranges"] = ranges
        ids = extract_ga_ids(relation)
        if len(ids) == 1 and relation == ids[0]:
            item["global-atom-id"] = ids[0]
        elif relation:
            item["global-relation"] = relation
        else:
            item["blocker"] = "missing-global-mapping"
        if normalize_code(cell(raw, "Global Coverage Status")).startswith("non-coverage"):
            item["non-coverage-status"] = normalize_code(cell(raw, "Global Coverage Status"))
        rows.append(item)
    data = {
        "trace-schema": SOURCE_TO_GLOBAL_MAP_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "artifact-path": rel(source_path, repo_root),
        "rows": rows,
    }
    if write:
        write_json(trace_path, data)
    return trace_path


def backfill_phase_3(orchestrate_dir: Path, repo_root: Path, write: bool) -> Optional[Path]:
    global_index_path = backfill_global_atom_index(orchestrate_dir, repo_root, write)
    map_path = backfill_source_to_global_map(orchestrate_dir, repo_root, write)
    manifest_path = orchestrate_dir / "phase-works/phase-3/source-doc-manifest.md"
    classifications = [
        row_to_kebab(raw, code_fields=["Source Document", "Classification", "Phase 2 Atom File", "Review File"])
        for raw in table_rows(manifest_path, ["Source Document", "Classification", "Phase 2 Atom File", "Review File"])
    ]
    trace_path = orchestrate_dir / "trace/phase-3.trace.json"
    data = {
        "trace-schema": PHASE_TRACE_SCHEMAS["phase-3"],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "decision": phase_status(orchestrate_dir, "phase-3"),
        "source-classifications": classifications,
        "source-to-global-atom-map-path": rel(map_path, repo_root),
        "obligation-atom-index-path": rel(global_index_path, repo_root),
        "remainder-review-path": rel(orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-remainder-review.md", repo_root),
        "duplicate-review-path": rel(orchestrate_dir / "phase-works/phase-3/phase-3-trace/duplicate-ownership-review.md", repo_root),
        "normalization-decision-log-path": rel(orchestrate_dir / "phase-works/phase-3/phase-3-trace/atom-normalization-decision-log.md", repo_root),
    }
    if write:
        write_json(trace_path, data)
    return trace_path


def iter_dossiers(orchestrate_dir: Path) -> Iterable[tuple[str, str, Path]]:
    root = orchestrate_dir / "phase-works/phase-4/source-window-dossiers"
    for unit_type, folder in (("input-change", "by-input-change"), ("input-capability", "by-input-capability")):
        folder_path = root / folder
        if not folder_path.exists():
            continue
        for path in sorted(folder_path.glob("*.md")):
            yield unit_type, path.stem, path


def backfill_phase_4(orchestrate_dir: Path, repo_root: Path, write: bool) -> Optional[Path]:
    windows: List[Dict[str, object]] = []
    profiles: List[Dict[str, object]] = []
    for unit_type, input_unit, dossier in iter_dossiers(orchestrate_dir):
        for raw in table_rows(dossier, ["Window", "Source Document", "Lines", "Atoms"]):
            source_document = normalize_code(cell(raw, "Source Document"))
            canonical, ranges, _, _ = parse_line_ranges(cell(raw, "Lines"))
            window_text = source_text_for_ranges(repo_root, source_document, ranges)
            windows.append(
                {
                    "window-id": normalize_code(cell(raw, "Window")),
                    "input-unit": input_unit,
                    "unit-type": unit_type,
                    "source-document": source_document,
                    "lines": canonical or normalize_code(cell(raw, "Lines")),
                    "line-ranges": ranges,
                    "context-line-ranges": [],
                    "linked-global-atom-ids": extract_ga_ids(cell(raw, "Atoms")),
                    "dossier-path": rel(dossier, repo_root),
                    "source-sha256": source_sha(repo_root, source_document),
                    "window-text-sha256": sha256_text(window_text),
                }
            )
        profile_rows = table_rows(dossier, ["Profile Field", "Phase 4 Reading"])
        if profile_rows:
            profiles.append(
                {
                    "input-unit": input_unit,
                    "unit-type": unit_type,
                    "dossier-path": rel(dossier, repo_root),
                    "profile": [
                        {
                            "profile-field": squash(cell(row, "Profile Field")),
                            "phase-4-reading": squash(cell(row, "Phase 4 Reading")),
                        }
                        for row in profile_rows
                    ],
                }
            )
    issue_path = orchestrate_dir / "phase-works/phase-4/source-window-grounding-issues.md"
    grounding_issues = [
        row_to_kebab(raw)
        for raw in table_rows(issue_path, ["Issue", "Source Windows", "Severity", "Decision"])
    ]
    index_path = orchestrate_dir / "phase-works/phase-4/source-window-dossiers/source-window-index.json"
    data = {
        "trace-schema": SOURCE_WINDOW_INDEX_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "status": phase_status(orchestrate_dir, "phase-4"),
        "windows": windows,
        "semantic-profiles": profiles,
        "grounding-issues": grounding_issues,
    }
    if write:
        write_json(index_path, data)
    trace_path = orchestrate_dir / "trace/phase-4.trace.json"
    trace = {
        "trace-schema": PHASE_TRACE_SCHEMAS["phase-4"],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "source-window-index-path": rel(index_path, repo_root),
        "status": phase_status(orchestrate_dir, "phase-4"),
        "window-count": len(windows),
        "semantic-profile-count": len(profiles),
    }
    if write:
        write_json(trace_path, trace)
    return trace_path


def backfill_atom_plan_mapping(orchestrate_dir: Path, repo_root: Path, write: bool) -> Path:
    source_path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.md"
    trace_path = source_path.with_suffix(".json")
    rows: List[Dict[str, object]] = []
    for raw in table_rows(source_path, ["Global Atom ID", "Final Owner Change", "Final Relation"]):
        canonical, ranges, _, _ = parse_line_ranges(cell(raw, "Lines"))
        item = row_to_kebab(
            raw,
            code_fields=[
                "Global Atom ID",
                "Source Document",
                "Phase 3 Owner / Status",
                "Phase 3 Artifact Projection",
                "Final Owner Change",
                "Final Owner Capability",
                "Final Artifact Projection",
                "Final Relation",
                "Plan Decision",
            ],
        )
        item["global-atom-id"] = normalize_code(cell(raw, "Global Atom ID"))
        item["source-document"] = normalize_code(cell(raw, "Source Document"))
        item["lines"] = canonical or normalize_code(cell(raw, "Lines"))
        item["line-ranges"] = ranges
        rows.append(item)
    data = {
        "trace-schema": ATOM_PLAN_MAPPING_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "artifact-path": rel(source_path, repo_root),
        "rows": rows,
    }
    if write:
        write_json(trace_path, data)
    return trace_path


def final_packet_index(orchestrate_dir: Path, repo_root: Path, mapping_rows: Sequence[Dict[str, object]]) -> Dict[str, object]:
    anchors = orchestrate_dir / "change-capability-anchors"
    by_change_direct: Dict[str, List[str]] = {}
    by_change_non_direct: Dict[str, List[str]] = {}
    for row in mapping_rows:
        change = str(row.get("final-owner-change", ""))
        if not change or change == "None":
            continue
        atom_id = str(row.get("global-atom-id", ""))
        if row.get("final-relation") == "direct":
            by_change_direct.setdefault(change, []).append(atom_id)
        else:
            by_change_non_direct.setdefault(change, []).append(atom_id)

    packets: List[Dict[str, object]] = []
    for change_dir in sorted(child for child in anchors.iterdir() if child.is_dir()):
        packet_path = change_dir / f"{change_dir.name}.md"
        cap_dir = change_dir / "capability-anchors"
        capability_paths = sorted(cap_dir.glob("*.md")) if cap_dir.exists() else []
        packets.append(
            {
                "change": change_dir.name,
                "packet-path": rel(packet_path, repo_root),
                "packet-digest": sha256_file(packet_path) if packet_path.exists() else "",
                "direct-atom-ids": sorted(by_change_direct.get(change_dir.name, [])),
                "owner-scoped-non-direct-atom-ids": sorted(by_change_non_direct.get(change_dir.name, [])),
                "capability-view-paths": [rel(path, repo_root) for path in capability_paths],
            }
        )
    return {
        "trace-schema": FINAL_PACKET_INDEX_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "packets": packets,
    }


def backfill_phase_5(orchestrate_dir: Path, repo_root: Path, write: bool) -> Optional[Path]:
    mapping_path = backfill_atom_plan_mapping(orchestrate_dir, repo_root, write)
    mapping_data = read_json(mapping_path) if mapping_path.exists() else {"rows": []}
    packets = final_packet_index(orchestrate_dir, repo_root, mapping_data.get("rows", []))  # type: ignore[arg-type]
    packet_index_path = orchestrate_dir / "phase-works/phase-5/final-packet-index.json"
    if write:
        write_json(packet_index_path, packets)
    complexity = [
        row_to_kebab(raw, code_fields=["Change", "Budget Status", "Foundation/Business Gate Status"])
        for raw in table_rows(
            orchestrate_dir / "phase-works/phase-5/change-complexity-review.md",
            ["Change", "Direct Atom Count", "Budget Status"],
        )
    ]
    capability = [
        row_to_kebab(raw, code_fields=["Capability"])
        for raw in table_rows(
            orchestrate_dir / "phase-works/phase-5/capability-progression-review.md",
            ["Capability", "Current Change Sequence"],
        )
    ]
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    data = {
        "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "status": phase_status(orchestrate_dir, "phase-5"),
        "atom-plan-mapping-path": rel(mapping_path, repo_root),
        "final-packet-index-path": rel(packet_index_path, repo_root),
        "complexity-summaries": complexity,
        "capability-progression-summaries": capability,
        "validator-gate-outcomes": [],
        "reviewer-gate-outcomes": [],
    }
    if write:
        write_json(trace_path, data)
    return trace_path


def build_manifest(orchestrate_dir: Path, repo_root: Path, write: bool) -> Path:
    manifest_path = orchestrate_dir / "trace/manifest.json"
    artifact_specs = [
        ("phase-1", "trace", orchestrate_dir / "phase-works/phase-1/source-doc-manifest.md", orchestrate_dir / "trace/phase-1.trace.json", PHASE_TRACE_SCHEMAS["phase-1"]),
        ("phase-2", "trace", orchestrate_dir / "phase-works/phase-2/source-obligation-atoms/work-queue.md", orchestrate_dir / "trace/phase-2.trace.json", PHASE_TRACE_SCHEMAS["phase-2"]),
        ("phase-3", "trace", orchestrate_dir / "change-capability-anchors/obligation-atom-index.md", orchestrate_dir / "change-capability-anchors/obligation-atom-index.json", GLOBAL_ATOM_INDEX_SCHEMA),
        ("phase-3", "trace", orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.md", orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json", SOURCE_TO_GLOBAL_MAP_SCHEMA),
        ("phase-3", "trace", orchestrate_dir / "phase-works/phase-3/coverage-review.md", orchestrate_dir / "trace/phase-3.trace.json", PHASE_TRACE_SCHEMAS["phase-3"]),
        ("phase-4", "trace", orchestrate_dir / "phase-works/phase-4/source-window-dossiers/index.md", orchestrate_dir / "phase-works/phase-4/source-window-dossiers/source-window-index.json", SOURCE_WINDOW_INDEX_SCHEMA),
        ("phase-4", "trace", orchestrate_dir / "phase-works/phase-4/phase-4-agent-report.md", orchestrate_dir / "trace/phase-4.trace.json", PHASE_TRACE_SCHEMAS["phase-4"]),
        ("phase-5", "trace", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.md", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", ATOM_PLAN_MAPPING_SCHEMA),
        ("phase-5", "trace", orchestrate_dir / "phase-works/phase-5/phase-5-agent-report.md", orchestrate_dir / "trace/phase-5.trace.json", PHASE_TRACE_SCHEMAS["phase-5"]),
        ("phase-5", "trace", orchestrate_dir / "change-capability-anchors/index.md", orchestrate_dir / "phase-works/phase-5/final-packet-index.json", FINAL_PACKET_INDEX_SCHEMA),
    ]
    artifacts: List[Dict[str, object]] = []
    for phase, role, artifact_path, trace_path, schema in artifact_specs:
        if not trace_path.exists():
            continue
        artifacts.append(
            {
                "artifact-path": rel(artifact_path, repo_root),
                "trace-path": rel(trace_path, repo_root),
                "trace-schema": schema,
                "sha256": sha256_file(trace_path),
                "phase": phase,
                "role": role,
            }
        )
    data = {
        "trace-schema": MANIFEST_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "orchestrate-dir": rel(orchestrate_dir, repo_root),
        "phase-statuses": {
            "phase-1": "present" if (orchestrate_dir / "trace/phase-1.trace.json").exists() else "missing",
            "phase-2": "present" if (orchestrate_dir / "trace/phase-2.trace.json").exists() else "missing",
            "phase-3": phase_status(orchestrate_dir, "phase-3"),
            "phase-4": phase_status(orchestrate_dir, "phase-4"),
            "phase-5": phase_status(orchestrate_dir, "phase-5"),
        },
        "artifacts": artifacts,
    }
    if write:
        write_json(manifest_path, data)
    return manifest_path


def run_backfill(orchestrate_dir: Path, repo_root: Path, write: bool) -> List[Path]:
    paths = [
        backfill_phase_1(orchestrate_dir, repo_root, write),
        backfill_phase_2(orchestrate_dir, repo_root, write),
        backfill_phase_3(orchestrate_dir, repo_root, write),
        backfill_phase_4(orchestrate_dir, repo_root, write),
        backfill_phase_5(orchestrate_dir, repo_root, write),
    ]
    paths.append(build_manifest(orchestrate_dir, repo_root, write))
    return [path for path in paths if path is not None]


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill source-aligned JSON trace sidecars from Markdown artifacts.")
    parser.add_argument("--orchestrate-dir", default="openspec/orchestrate", type=Path)
    parser.add_argument("--workspace-root", default=".", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    paths = run_backfill(args.orchestrate_dir, args.workspace_root, args.write)
    action = "wrote" if args.write else "planned"
    print(f"{action} {len(paths)} top-level trace artifacts")
    for path in paths:
        print(path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
