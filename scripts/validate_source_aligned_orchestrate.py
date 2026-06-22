#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate source-aligned orchestrate JSON trace sidecars."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

from source_aligned_trace_lib import (
    ATOM_PLAN_MAPPING_SCHEMA,
    DIRECT_PROJECTIONS,
    FINAL_PACKET_INDEX_SCHEMA,
    GLOBAL_ATOM_ID_RE,
    GLOBAL_ATOM_INDEX_SCHEMA,
    MANIFEST_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    SOURCE_TO_GLOBAL_MAP_SCHEMA,
    SOURCE_WINDOW_INDEX_SCHEMA,
    TRACE_CONTRACT_VERSION,
    IssueReporter,
    cell,
    extract_ga_ids,
    parse_line_ranges,
    read_json,
    sha256_file,
    source_atom_file_name,
    source_line_count,
    table_rows,
    validate_kebab_keys,
    normalize_code,
    squash,
)


def rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def json_obj(path: Path, reporter: IssueReporter, schema: str | None = None) -> Dict[str, object]:
    if not path.exists():
        reporter.error("missing-json", path, "required JSON trace file is missing")
        return {}
    try:
        data = read_json(path)
    except Exception as exc:  # noqa: BLE001
        reporter.error("invalid-json", path, f"failed to parse JSON object: {exc}")
        return {}
    validate_kebab_keys(data, reporter, path)
    if schema and data.get("trace-schema") != schema:
        reporter.error("trace-schema", path, f"trace-schema must be {schema}")
    if data.get("trace-contract-version") != TRACE_CONTRACT_VERSION:
        reporter.error("trace-contract-version", path, f"trace-contract-version must be {TRACE_CONTRACT_VERSION}")
    return data


def check_ranges(
    path: Path,
    reporter: IssueReporter,
    line_ranges: object,
    source_document: str = "",
    repo_root: Path | None = None,
    context: str = "",
) -> None:
    if not isinstance(line_ranges, list) or not line_ranges:
        reporter.error("line-range", path, f"{context} missing non-empty line-ranges")
        return
    line_count = source_line_count(repo_root, source_document) if repo_root and source_document else None
    for item in line_ranges:
        if not isinstance(item, dict):
            reporter.error("line-range", path, f"{context} line-ranges item must be object")
            continue
        start = item.get("start")
        end = item.get("end")
        if not isinstance(start, int) or not isinstance(end, int) or start <= 0 or end <= 0 or start > end:
            reporter.error("line-range", path, f"{context} invalid range: {item}")
            continue
        if line_count is not None and end > line_count:
            reporter.error(
                "line-range-bounds",
                path,
                f"{context} range L{start}-L{end} exceeds {source_document} line count {line_count}",
            )


def markdown_backtick_warning(path: Path, reporter: IssueReporter, required_headers: Sequence[str]) -> None:
    rows = table_rows(path, required_headers)
    for row in rows:
        lines = cell(row, "Lines", "Source Section or Range", "Candidate Range")
        if "`" in lines:
            reporter.warning("markdown-line-range-backticks", path, "Markdown mirror line range still uses backticks")
            return


def phase1_sources(orchestrate_dir: Path, repo_root: Path) -> List[Dict[str, object]]:
    data = read_json(orchestrate_dir / "trace/phase-1.trace.json")
    sources = data.get("source-documents")
    return sources if isinstance(sources, list) else []


def validate_manifest(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    path = orchestrate_dir / "trace/manifest.json"
    data = json_obj(path, reporter, MANIFEST_SCHEMA)
    if not data:
        return
    if data.get("orchestrate-dir") != rel(orchestrate_dir, repo_root):
        reporter.error("manifest-orchestrate-dir", path, "orchestrate-dir does not match CLI --orchestrate-dir")
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        reporter.error("manifest-artifacts", path, "artifacts must be an array")
        return
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            reporter.error("manifest-artifact", path, f"artifacts[{index}] must be object")
            continue
        trace_rel = item.get("trace-path")
        digest = item.get("sha256")
        if not isinstance(trace_rel, str) or not trace_rel:
            reporter.error("manifest-artifact-trace-path", path, f"artifacts[{index}] missing trace-path")
            continue
        trace_path = repo_root / trace_rel
        if not trace_path.exists():
            reporter.error("manifest-artifact-trace-path", path, f"{trace_rel} does not exist")
            continue
        current = sha256_file(trace_path)
        if digest != current:
            reporter.error("manifest-digest", path, f"{trace_rel} sha256 mismatch")


def validate_phase_1(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    path = orchestrate_dir / "trace/phase-1.trace.json"
    data = json_obj(path, reporter, PHASE_TRACE_SCHEMAS["phase-1"])
    if not data:
        return
    sources = data.get("source-documents")
    if not isinstance(sources, list) or not sources:
        reporter.error("phase1-source-documents", path, "source-documents must be a non-empty array")
        return
    seen: Set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            reporter.error("phase1-source-document", path, "source-documents item must be object")
            continue
        source_document = str(source.get("source-document", ""))
        if not source_document:
            reporter.error("phase1-source-document", path, "source-document is required")
            continue
        if source_document in seen:
            reporter.error("phase1-source-duplicate", path, f"duplicate source-document: {source_document}")
        seen.add(source_document)
        source_path = repo_root / source_document
        if not source_path.exists():
            reporter.error("phase1-source-exists", path, f"source document does not exist: {source_document}")
            continue
        if source.get("line-count") != len(source_path.read_text(encoding="utf-8").splitlines()):
            reporter.error("phase1-source-line-count", path, f"line-count drift for {source_document}")
        if source.get("source-sha256") != sha256_file(source_path):
            reporter.error("phase1-source-sha", path, f"source-sha256 drift for {source_document}")


def work_queue_counts(orchestrate_dir: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    path = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms/work-queue.md"
    for row in table_rows(path, ["Source Documents", "Canonical Owner"]):
        for part in str(cell(row, "Source Documents")).split("<br>"):
            source = normalize_code(part)
            if source:
                counts[source] = counts.get(source, 0) + 1
    return counts


def load_phase2_atoms(orchestrate_dir: Path, reporter: IssueReporter) -> Dict[str, Dict[str, object]]:
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    all_atoms: Dict[str, Dict[str, object]] = {}
    for sidecar in sorted(atom_root.glob("*.atoms.json")):
        data = json_obj(sidecar, reporter, SOURCE_ATOMS_SCHEMA)
        for row in data.get("source-atoms", []) if isinstance(data.get("source-atoms"), list) else []:
            if not isinstance(row, dict):
                reporter.error("phase2-source-atom-row", sidecar, "source-atoms item must be object")
                continue
            atom_id = str(row.get("source-atom-id", ""))
            source_document = str(row.get("source-document", ""))
            key = f"{source_document}::{atom_id}"
            if key in all_atoms:
                reporter.error("phase2-source-atom-duplicate", sidecar, f"duplicate Phase 2 source atom row: {key}")
            all_atoms[key] = row
    return all_atoms


def validate_phase2_mirror(orchestrate_dir: Path, reporter: IssueReporter) -> None:
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    for sidecar in sorted(atom_root.glob("*.atoms.json")):
        md_path = sidecar.with_suffix(".md")
        if not md_path.exists():
            reporter.error("markdown-mirror-missing", sidecar, f"Markdown mirror missing: {md_path}")
            continue
        data = read_json(sidecar)
        by_id = {
            str(row.get("source-atom-id")): row
            for row in data.get("source-atoms", [])
            if isinstance(row, dict) and row.get("source-atom-id")
        }
        markdown_backtick_warning(md_path, reporter, ["Source Atom ID", "Source Document", "Lines"])
        for raw in table_rows(md_path, ["Source Atom ID", "Source Document", "Lines", "Source Fact"]):
            atom_id = normalize_code(cell(raw, "Source Atom ID"))
            row = by_id.get(atom_id)
            if not row:
                reporter.error("markdown-json-drift", md_path, f"Markdown atom {atom_id} missing from JSON sidecar")
                continue
            if squash(cell(raw, "Source Fact")) != squash(row.get("source-fact")):
                reporter.error("markdown-json-drift", md_path, f"{atom_id} Source Fact differs between Markdown and JSON")
            if normalize_code(cell(raw, "Candidate Artifact Projection")) != str(row.get("candidate-artifact-projection", "")):
                reporter.error("markdown-json-drift", md_path, f"{atom_id} candidate projection differs between Markdown and JSON")


def validate_phase_2(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    trace_path = orchestrate_dir / "trace/phase-2.trace.json"
    json_obj(trace_path, reporter, PHASE_TRACE_SCHEMAS["phase-2"])
    sources = phase1_sources(orchestrate_dir, repo_root)
    queue_counts = work_queue_counts(orchestrate_dir)
    for source in sources:
        if not isinstance(source, dict) or source.get("read-status") != "read-full":
            continue
        source_document = str(source.get("source-document", ""))
        count = queue_counts.get(source_document, 0)
        if count != 1:
            reporter.error("phase2-work-queue-coverage", trace_path, f"{source_document} appears in Phase 2 work queue {count} times")
        sidecar = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms" / source_atom_file_name(source_document).replace(".md", ".json")
        data = json_obj(sidecar, reporter, SOURCE_ATOMS_SCHEMA)
        if not data:
            continue
        if data.get("source-document") != source_document:
            reporter.error("phase2-source-document", sidecar, "source-document does not match Phase 1 manifest")
        source_path = repo_root / source_document
        if source_path.exists() and data.get("source-sha256") != sha256_file(source_path):
            reporter.error("phase2-source-sha", sidecar, f"source-sha256 drift for {source_document}")
        atoms = data.get("source-atoms")
        if not isinstance(atoms, list):
            reporter.error("phase2-source-atoms", sidecar, "source-atoms must be an array")
            continue
        for row in atoms:
            if not isinstance(row, dict):
                reporter.error("phase2-source-atom-row", sidecar, "source-atoms item must be object")
                continue
            context = str(row.get("source-atom-id", ""))
            if not context:
                reporter.error("phase2-source-atom-id", sidecar, "source-atom-id is required")
            check_ranges(sidecar, reporter, row.get("line-ranges"), source_document, repo_root, context)
            projection = str(row.get("candidate-artifact-projection", ""))
            status = str(row.get("candidate-status", ""))
            if not projection:
                reporter.error("phase2-projection", sidecar, f"{context} has empty candidate-artifact-projection")
            if status == "direct-candidate" and projection == "contextual-only":
                reporter.error("phase2-direct-contextual-only", sidecar, f"{context} is direct-candidate but uses contextual-only")
    validate_phase2_mirror(orchestrate_dir, reporter)


def load_global_atoms(orchestrate_dir: Path, reporter: IssueReporter) -> Dict[str, Dict[str, object]]:
    path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    data = json_obj(path, reporter, GLOBAL_ATOM_INDEX_SCHEMA)
    atoms: Dict[str, Dict[str, object]] = {}
    rows = data.get("global-atoms")
    if not isinstance(rows, list):
        reporter.error("phase3-global-atoms", path, "global-atoms must be an array")
        return atoms
    for row in rows:
        if not isinstance(row, dict):
            reporter.error("phase3-global-atom-row", path, "global-atoms item must be object")
            continue
        atom_id = str(row.get("global-atom-id", ""))
        if not GLOBAL_ATOM_ID_RE.match(atom_id):
            reporter.error("phase3-ga-format", path, f"invalid Global Atom ID: {atom_id}")
            continue
        if atom_id in atoms:
            reporter.error("phase3-ga-duplicate", path, f"duplicate Global Atom ID: {atom_id}")
        atoms[atom_id] = row
    return atoms


def validate_global_index_mirror(orchestrate_dir: Path, reporter: IssueReporter) -> None:
    json_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    md_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.md"
    if not json_path.exists() or not md_path.exists():
        return
    data = read_json(json_path)
    by_id = {
        str(row.get("global-atom-id")): row
        for row in data.get("global-atoms", [])
        if isinstance(row, dict) and row.get("global-atom-id")
    }
    markdown_backtick_warning(md_path, reporter, ["Global Atom ID", "Source Document", "Lines"])
    for raw in table_rows(md_path, ["Global Atom ID", "Source Document", "Lines", "Source Fact", "Artifact Projection"]):
        atom_id = normalize_code(cell(raw, "Global Atom ID"))
        row = by_id.get(atom_id)
        if not row:
            reporter.error("markdown-json-drift", md_path, f"Markdown global atom {atom_id} missing from JSON")
            continue
        if squash(cell(raw, "Source Fact")) != squash(row.get("source-fact")):
            reporter.error("markdown-json-drift", md_path, f"{atom_id} Source Fact differs between Markdown and JSON")
        if normalize_code(cell(raw, "Artifact Projection")) != str(row.get("artifact-projection", "")):
            reporter.error("markdown-json-drift", md_path, f"{atom_id} artifact projection differs between Markdown and JSON")


def validate_phase_3(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    json_obj(orchestrate_dir / "trace/phase-3.trace.json", reporter, PHASE_TRACE_SCHEMAS["phase-3"])
    global_atoms = load_global_atoms(orchestrate_dir, reporter)
    index_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    for atom_id, row in global_atoms.items():
        source_document = str(row.get("source-document", ""))
        check_ranges(index_path, reporter, row.get("line-ranges"), source_document, repo_root, atom_id)
        projection = str(row.get("artifact-projection", ""))
        status = str(row.get("coverage-status", ""))
        if not projection:
            reporter.error("phase3-projection", index_path, f"{atom_id} has empty artifact-projection")
        if status in {"direct", "direct-candidate"} and projection == "contextual-only":
            reporter.error("phase3-direct-contextual-only", index_path, f"{atom_id} is direct but uses contextual-only")

    map_path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json"
    data = json_obj(map_path, reporter, SOURCE_TO_GLOBAL_MAP_SCHEMA)
    mapped_keys: Set[str] = set()
    rows = data.get("rows")
    if not isinstance(rows, list):
        reporter.error("phase3-map-rows", map_path, "rows must be an array")
        rows = []
    for row in rows:
        if not isinstance(row, dict):
            reporter.error("phase3-map-row", map_path, "rows item must be object")
            continue
        source_document = str(row.get("source-document", ""))
        atom_id = str(row.get("source-atom-id", ""))
        mapped_keys.add(f"{source_document}::{atom_id}")
        populated = [
            key
            for key in ("global-atom-id", "global-relation", "non-coverage-status", "blocker")
            if row.get(key)
        ]
        if len(populated) != 1:
            reporter.error("phase3-map-exclusive", map_path, f"{source_document}::{atom_id} must set exactly one mapping outcome")
        if row.get("global-atom-id") and row.get("global-atom-id") not in global_atoms:
            reporter.error("phase3-map-unknown-ga", map_path, f"{atom_id} maps to unknown {row.get('global-atom-id')}")
        check_ranges(map_path, reporter, row.get("line-ranges"), source_document, repo_root, atom_id)

    for key in load_phase2_atoms(orchestrate_dir, reporter):
        if key not in mapped_keys:
            reporter.error("phase3-map-coverage", map_path, f"source-to-global map missing Phase 2 atom/context row: {key}")
    validate_global_index_mirror(orchestrate_dir, reporter)


def validate_phase_4(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    json_obj(orchestrate_dir / "trace/phase-4.trace.json", reporter, PHASE_TRACE_SCHEMAS["phase-4"])
    global_atoms = load_global_atoms(orchestrate_dir, reporter)
    index_path = orchestrate_dir / "phase-works/phase-4/source-window-dossiers/source-window-index.json"
    data = json_obj(index_path, reporter, SOURCE_WINDOW_INDEX_SCHEMA)
    windows = data.get("windows")
    if not isinstance(windows, list) or not windows:
        reporter.error("phase4-windows", index_path, "windows must be a non-empty array")
        return
    for row in windows:
        if not isinstance(row, dict):
            reporter.error("phase4-window-row", index_path, "windows item must be object")
            continue
        window_id = str(row.get("window-id", ""))
        source_document = str(row.get("source-document", ""))
        dossier_path = row.get("dossier-path")
        if not isinstance(dossier_path, str) or not (repo_root / dossier_path).exists():
            reporter.error("phase4-dossier-path", index_path, f"{window_id} dossier path missing: {dossier_path}")
        source_path = repo_root / source_document
        if not source_path.exists():
            reporter.error("phase4-source-path", index_path, f"{window_id} source missing: {source_document}")
        elif row.get("source-sha256") != sha256_file(source_path):
            reporter.error("phase4-source-sha", index_path, f"{window_id} source hash drift for {source_document}")
        check_ranges(index_path, reporter, row.get("line-ranges"), source_document, repo_root, window_id)
        ids = row.get("linked-global-atom-ids")
        if not isinstance(ids, list) or not ids:
            reporter.error("phase4-linked-ga", index_path, f"{window_id} linked-global-atom-ids must be non-empty")
        else:
            for atom_id in ids:
                if atom_id not in global_atoms:
                    reporter.error("phase4-linked-ga", index_path, f"{window_id} references unknown {atom_id}")


def load_mapping(orchestrate_dir: Path, reporter: IssueReporter) -> Dict[str, Dict[str, object]]:
    path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
    data = json_obj(path, reporter, ATOM_PLAN_MAPPING_SCHEMA)
    mapping: Dict[str, Dict[str, object]] = {}
    rows = data.get("rows")
    if not isinstance(rows, list):
        reporter.error("phase5-mapping-rows", path, "rows must be an array")
        return mapping
    for row in rows:
        if not isinstance(row, dict):
            reporter.error("phase5-mapping-row", path, "rows item must be object")
            continue
        atom_id = str(row.get("global-atom-id", ""))
        if not GLOBAL_ATOM_ID_RE.match(atom_id):
            reporter.error("phase5-ga-format", path, f"invalid Global Atom ID: {atom_id}")
            continue
        if atom_id in mapping:
            reporter.error("phase5-ga-duplicate", path, f"duplicate mapping row: {atom_id}")
        mapping[atom_id] = row
    return mapping


def validate_mapping_mirror(orchestrate_dir: Path, reporter: IssueReporter) -> None:
    json_path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
    md_path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.md"
    if not json_path.exists() or not md_path.exists():
        return
    data = read_json(json_path)
    by_id = {
        str(row.get("global-atom-id")): row
        for row in data.get("rows", [])
        if isinstance(row, dict) and row.get("global-atom-id")
    }
    markdown_backtick_warning(md_path, reporter, ["Global Atom ID", "Source Document", "Lines"])
    for raw in table_rows(md_path, ["Global Atom ID", "Final Owner Change", "Final Relation"]):
        atom_id = normalize_code(cell(raw, "Global Atom ID"))
        row = by_id.get(atom_id)
        if not row:
            reporter.error("markdown-json-drift", md_path, f"Markdown mapping {atom_id} missing from JSON")
            continue
        if normalize_code(cell(raw, "Final Owner Change")) != str(row.get("final-owner-change", "")):
            reporter.error("markdown-json-drift", md_path, f"{atom_id} final owner change differs between Markdown and JSON")
        if normalize_code(cell(raw, "Final Artifact Projection")) != str(row.get("final-artifact-projection", "")):
            reporter.error("markdown-json-drift", md_path, f"{atom_id} final projection differs between Markdown and JSON")


def validate_final_packets(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter, mapping: Dict[str, Dict[str, object]]) -> None:
    index_path = orchestrate_dir / "phase-works/phase-5/final-packet-index.json"
    data = json_obj(index_path, reporter, FINAL_PACKET_INDEX_SCHEMA)
    packets = data.get("packets")
    if not isinstance(packets, list):
        reporter.error("phase5-final-packet-index", index_path, "packets must be an array")
        return

    direct_by_owner: Dict[tuple[str, str], Set[str]] = {}
    for atom_id, row in mapping.items():
        if row.get("final-relation") == "direct":
            key = (str(row.get("final-owner-change", "")), str(row.get("final-owner-capability", "")))
            direct_by_owner.setdefault(key, set()).add(atom_id)

    packet_changes: Set[str] = set()
    for packet in packets:
        if not isinstance(packet, dict):
            reporter.error("phase5-final-packet-row", index_path, "packets item must be object")
            continue
        change = str(packet.get("change", ""))
        packet_changes.add(change)
        packet_rel = packet.get("packet-path")
        if not isinstance(packet_rel, str) or not packet_rel:
            reporter.error("phase5-final-packet-path", index_path, f"{change} missing packet-path")
            continue
        packet_path = repo_root / packet_rel
        if not packet_path.exists():
            reporter.error("phase5-final-packet-path", index_path, f"{change} packet missing: {packet_rel}")
            continue
        text = packet_path.read_text(encoding="utf-8")
        direct_ids = set(packet.get("direct-atom-ids") if isinstance(packet.get("direct-atom-ids"), list) else [])
        non_direct_ids = set(
            packet.get("owner-scoped-non-direct-atom-ids")
            if isinstance(packet.get("owner-scoped-non-direct-atom-ids"), list)
            else []
        )
        for atom_id in direct_ids:
            if atom_id not in text:
                reporter.error("phase5-final-direct-packet", packet_path, f"direct atom {atom_id} missing from final packet")
        for atom_id in non_direct_ids:
            if atom_id not in text:
                reporter.error("phase5-final-non-direct-packet", packet_path, f"owner-scoped non-direct atom {atom_id} missing from final packet")

        capability_paths = packet.get("capability-view-paths")
        if not isinstance(capability_paths, list):
            reporter.error("phase5-capability-view-paths", index_path, f"{change} capability-view-paths must be array")
            continue
        for cap_rel in capability_paths:
            if not isinstance(cap_rel, str):
                continue
            cap_path = repo_root / cap_rel
            if not cap_path.exists():
                reporter.error("phase5-capability-view-path", index_path, f"capability view missing: {cap_rel}")
                continue
            cap_slug = cap_path.stem
            text_ids = set(extract_ga_ids(cap_path.read_text(encoding="utf-8")))
            expected_ids = direct_by_owner.get((change, cap_slug), set())
            for atom_id in text_ids:
                row = mapping.get(atom_id)
                if not row or row.get("final-relation") != "direct":
                    reporter.error("phase5-capability-view-non-direct", cap_path, f"capability view contains non-direct or unknown atom {atom_id}")
                elif row.get("final-owner-change") != change or row.get("final-owner-capability") != cap_slug:
                    reporter.error("phase5-capability-view-owner", cap_path, f"{atom_id} does not belong to {change}/{cap_slug}")
            missing = expected_ids - text_ids
            if missing:
                reporter.error("phase5-capability-view-missing-direct", cap_path, f"capability view missing direct atoms: {', '.join(sorted(missing)[:12])}")

    for atom_id, row in mapping.items():
        change = str(row.get("final-owner-change", ""))
        if row.get("final-relation") != "direct" and change and change != "None" and change not in packet_changes:
            reporter.error("phase5-final-non-direct-owner", index_path, f"{atom_id} has final owner change without final packet: {change}")


def validate_phase_5(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter, complete: bool = False) -> None:
    trace = json_obj(orchestrate_dir / "trace/phase-5.trace.json", reporter, PHASE_TRACE_SCHEMAS["phase-5"])
    global_atoms = load_global_atoms(orchestrate_dir, reporter)
    mapping = load_mapping(orchestrate_dir, reporter)
    missing = sorted(set(global_atoms) - set(mapping))
    extra = sorted(set(mapping) - set(global_atoms))
    if missing:
        reporter.error("phase5-mapping-coverage", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"mapping missing global atoms: {', '.join(missing[:12])}")
    if extra:
        reporter.error("phase5-mapping-extra", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"mapping contains unknown global atoms: {', '.join(extra[:12])}")
    for atom_id, row in mapping.items():
        source_document = str(row.get("source-document", ""))
        check_ranges(orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", reporter, row.get("line-ranges"), source_document, repo_root, atom_id)
        relation = str(row.get("final-relation", ""))
        projection = str(row.get("final-artifact-projection", ""))
        if relation == "direct":
            if projection not in DIRECT_PROJECTIONS:
                reporter.error("phase5-direct-projection", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} direct uses invalid projection {projection}")
            if not row.get("final-owner-change") or row.get("final-owner-change") == "None":
                reporter.error("phase5-direct-owner", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} direct missing final owner change")
            if not row.get("final-owner-capability") or row.get("final-owner-capability") == "None":
                reporter.error("phase5-direct-owner", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} direct missing final owner capability")
    validate_mapping_mirror(orchestrate_dir, reporter)
    validate_final_packets(orchestrate_dir, repo_root, reporter, mapping)

    for raw in table_rows(orchestrate_dir / "phase-works/phase-5/change-complexity-review.md", ["Change", "Budget Status"]):
        budget = normalize_code(cell(raw, "Budget Status"))
        if budget in {"over-budget-reviewed", "hard-over-budget", "above-target-reviewed"}:
            reporter.warning("phase5-over-budget-review", orchestrate_dir / "phase-works/phase-5/change-complexity-review.md", f"{normalize_code(cell(raw, 'Change'))} has budget status {budget}; reviewer judgment required")

    if complete:
        status = str(trace.get("status", ""))
        if status not in {"accepted", "adjusted"}:
            reporter.error("phase5-complete-status", orchestrate_dir / "trace/phase-5.trace.json", f"--complete requires accepted/adjusted status, got {status}")
        anchors_index = orchestrate_dir / "change-capability-anchors/index.md"
        if not anchors_index.exists():
            reporter.error("phase5-complete-packets", anchors_index, "final change-capability anchor index is missing")


def validate(orchestrate_dir: Path, repo_root: Path, phase: str, complete: bool, legacy_tolerant: bool) -> Dict[str, object]:
    reporter = IssueReporter()
    if not orchestrate_dir.exists():
        reporter.error("orchestrate-dir", orchestrate_dir, "orchestrate directory does not exist")
        return reporter.result()

    validate_manifest(orchestrate_dir, repo_root, reporter)
    phases = ["phase-1", "phase-2", "phase-3", "phase-4", "phase-5"] if phase == "all" else [phase]
    if "phase-1" in phases:
        validate_phase_1(orchestrate_dir, repo_root, reporter)
    if "phase-2" in phases:
        validate_phase_2(orchestrate_dir, repo_root, reporter)
    if "phase-3" in phases:
        validate_phase_3(orchestrate_dir, repo_root, reporter)
    if "phase-4" in phases:
        validate_phase_4(orchestrate_dir, repo_root, reporter)
    if "phase-5" in phases:
        validate_phase_5(orchestrate_dir, repo_root, reporter, complete=complete)

    result = reporter.result()
    if legacy_tolerant:
        result["legacy-tolerant"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate source-aligned orchestrate trace sidecars.")
    parser.add_argument("--orchestrate-dir", default="openspec/orchestrate", type=Path)
    parser.add_argument("--workspace-root", default=".", type=Path)
    parser.add_argument("--phase", choices=["phase-1", "phase-2", "phase-3", "phase-4", "phase-5", "all"], default="all")
    parser.add_argument("--complete", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict-warnings", action="store_true")
    parser.add_argument("--legacy-tolerant", action="store_true")
    args = parser.parse_args()

    result = validate(args.orchestrate_dir, args.workspace_root, args.phase, args.complete, args.legacy_tolerant)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} errors={result['error-count']} warnings={result['warning-count']}")
        for issue in result["issues"]:  # type: ignore[index]
            print(f"{issue['severity']}: {issue['rule_id']}: {issue['file']}: {issue['message']}")

    has_errors = int(result["error-count"]) > 0
    has_warnings = int(result["warning-count"]) > 0
    return 1 if has_errors or (args.strict_warnings and has_warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
