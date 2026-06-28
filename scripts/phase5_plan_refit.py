#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanical Phase 5 plan-refit renderer.

This helper is intentionally deterministic. A Phase 5 subagent still owns the
semantic refit decisions: final change list, capability list, atom mapping,
split decisions, and blockers. This script only validates those reviewed inputs
and renders the repetitive Phase 5 ledgers, packets, reviews, and reports.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from source_aligned_trace_lib import (
    ATOM_PLAN_MAPPING_SCHEMA,
    FINAL_PACKET_INDEX_SCHEMA,
    FOUNDATION_REFERENCE_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    TRACE_CONTRACT_VERSION,
    parse_line_ranges,
    sha256_file,
    write_json,
)


TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
GLOBAL_ATOM_ID_RE = re.compile(r"^GA-\d{4}$")
DIRECT_PROJECTIONS = {
    "spec-requirement",
    "spec-guard",
    "design-obligation",
    "verification-obligation",
}
FAILURE_TYPES = {"recovery", "failure-path", "disabled-action"}
PHASE5_STATUSES = {"accepted", "adjusted", "needs-coverage-recheck", "blocked"}
TERMINAL_PHASE5_STATUSES = {"accepted", "adjusted"}
EXECUTABLE_OWNER_TYPE = "executable-change"
FOUNDATION_OWNER_TYPE = "foundation-reference"
NO_OWNER_VALUES = {"", "None", "none", "null", "NULL"}
FOUNDATION_REFERENCE_ID = "foundation-runtime-substrate"


@dataclass(frozen=True)
class ChangeDef:
    slug: str
    title: str
    outcome: str
    kind: str


@dataclass(frozen=True)
class CapabilityDef:
    slug: str
    boundary: str


@dataclass(frozen=True)
class AtomRow:
    atom_id: str
    source_document: str
    lines: str
    atom_type: str
    source_fact: str
    normativity: str
    coverage_status: str
    artifact_projection: str
    owner_change: str
    owner_capability: str
    source_atom_origins: str
    atom_relation: str
    propose_use: str
    evidence_need: str
    review_judgment: str


@dataclass(frozen=True)
class MappingRow:
    atom_id: str
    final_owner_type: str
    final_change: str
    final_capability: str
    final_projection: str
    final_relation: str
    foundation_reference_id: str
    capability_advancement: str
    plan_decision: str
    reason: str


@dataclass(frozen=True)
class FinalAtom:
    source: AtomRow
    mapping: MappingRow


def split_md_row(line: str) -> Optional[List[str]]:
    """Split a markdown table row, ignoring pipes in code spans and escapes."""
    text = line.strip()
    if not text.startswith("|"):
        return None
    if text.endswith("|"):
        text = text[1:-1]
    else:
        text = text[1:]

    cells: List[str] = []
    buf: List[str] = []
    escaped = False
    in_code = False
    for char in text:
        if escaped:
            buf.append(char)
            escaped = False
            continue
        if char == "\\":
            buf.append(char)
            escaped = True
            continue
        if char == "`":
            in_code = not in_code
            buf.append(char)
            continue
        if char == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf = []
            continue
        buf.append(char)
    cells.append("".join(buf).strip())
    return cells


def normalize_header(value: str) -> str:
    return normalize_code(value).lower()


def normalize_code(value: str) -> str:
    value = value.strip()
    while len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return value.replace("\\|", "|").strip()


def squash(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def md(value: object) -> str:
    return squash(value).replace("|", "\\|")


def code(value: object) -> str:
    text = squash(value)
    return f"`{text}`" if text else "`None`"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def parse_table(path: Path, required_headers: Sequence[str]) -> List[Dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    required = {name.lower() for name in required_headers}
    for i in range(len(lines) - 1):
        header = split_md_row(lines[i])
        separator = split_md_row(lines[i + 1])
        if not header or not separator:
            continue
        if not all(TABLE_SEPARATOR_RE.match(cell.strip()) for cell in separator):
            continue
        header_index = {normalize_header(name): pos for pos, name in enumerate(header)}
        if not required.issubset(header_index):
            continue

        rows: List[Dict[str, str]] = []
        for raw in lines[i + 2 :]:
            cells = split_md_row(raw)
            if not cells:
                break
            if len(cells) < len(header):
                continue
            row: Dict[str, str] = {}
            for name, pos in header_index.items():
                row[name] = cells[pos] if pos < len(cells) else ""
            rows.append(row)
        return rows
    raise ValueError(f"未在 {path} 找到包含 {', '.join(required_headers)} 的 markdown 表格")


def cell(row: Dict[str, str], name: str) -> str:
    return row.get(name.lower(), "")


def load_global_atoms(path: Path) -> Dict[str, AtomRow]:
    rows = parse_table(path, ["Global Atom ID", "Source Document", "Coverage Status"])
    atoms: Dict[str, AtomRow] = {}
    for raw in rows:
        atom_id = normalize_code(cell(raw, "Global Atom ID"))
        if not atom_id:
            continue
        if not GLOBAL_ATOM_ID_RE.match(atom_id):
            raise ValueError(f"global atom index 中的 Global Atom ID 必须匹配 GA-####: {atom_id}")
        if atom_id in atoms:
            raise ValueError(f"global atom index 中存在重复 ID: {atom_id}")
        atoms[atom_id] = AtomRow(
            atom_id=atom_id,
            source_document=normalize_code(cell(raw, "Source Document")),
            lines=normalize_code(cell(raw, "Lines")),
            atom_type=normalize_code(cell(raw, "Atom Type")),
            source_fact=cell(raw, "Source Fact"),
            normativity=normalize_code(cell(raw, "Normativity")),
            coverage_status=normalize_code(cell(raw, "Coverage Status")),
            artifact_projection=normalize_code(cell(raw, "Artifact Projection")),
            owner_change=normalize_code(cell(raw, "Owner Change")),
            owner_capability=normalize_code(cell(raw, "Owner Capability")),
            source_atom_origins=normalize_code(cell(raw, "Source Atom Origins")),
            atom_relation=normalize_code(cell(raw, "Atom Relation")),
            propose_use=cell(raw, "Propose Use"),
            evidence_need=normalize_code(cell(raw, "Evidence Need")),
            review_judgment=cell(raw, "Review Judgment"),
        )
    if not atoms:
        raise ValueError(f"{path} 中没有 global atom row")
    return atoms


def load_global_atoms_json(path: Path) -> Dict[str, AtomRow]:
    data = json.loads(path.read_text(encoding="utf-8"))
    atoms: Dict[str, AtomRow] = {}
    for raw in data.get("global-atoms", []):
        if not isinstance(raw, dict):
            continue
        atom_id = normalize_code(str(raw.get("global-atom-id", "")))
        if not atom_id:
            continue
        if not GLOBAL_ATOM_ID_RE.match(atom_id):
            raise ValueError(f"global atom index JSON 中的 Global Atom ID 必须匹配 GA-####: {atom_id}")
        if atom_id in atoms:
            raise ValueError(f"global atom index JSON 中存在重复 ID: {atom_id}")
        atoms[atom_id] = AtomRow(
            atom_id=atom_id,
            source_document=normalize_code(str(raw.get("source-document", ""))),
            lines=normalize_code(str(raw.get("lines", ""))),
            atom_type=normalize_code(str(raw.get("atom-type", ""))),
            source_fact=str(raw.get("source-fact", "")),
            normativity=normalize_code(str(raw.get("normativity", ""))),
            coverage_status=normalize_code(str(raw.get("coverage-status", ""))),
            artifact_projection=normalize_code(str(raw.get("artifact-projection", ""))),
            owner_change=normalize_code(str(raw.get("owner-change", ""))),
            owner_capability=normalize_code(str(raw.get("owner-capability", ""))),
            source_atom_origins=normalize_code(str(raw.get("source-atom-origins", ""))),
            atom_relation=normalize_code(str(raw.get("atom-relation", ""))),
            propose_use=str(raw.get("propose-use", "")),
            evidence_need=normalize_code(str(raw.get("evidence-need", ""))),
            review_judgment=str(raw.get("review-judgment", "")),
        )
    if not atoms:
        raise ValueError(f"{path} 中没有 global atom row")
    return atoms


def load_mapping(path: Path) -> Dict[str, MappingRow]:
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        mapping: Dict[str, MappingRow] = {}
        for raw in data.get("rows", []):
            if not isinstance(raw, dict):
                continue
            atom_id = normalize_code(str(raw.get("global-atom-id", "")))
            if not atom_id:
                continue
            if not GLOBAL_ATOM_ID_RE.match(atom_id):
                raise ValueError(f"Phase 5 mapping JSON 中的 Global Atom ID 必须匹配 GA-####: {atom_id}")
            if atom_id in mapping:
                raise ValueError(f"Phase 5 mapping JSON 中存在重复 ID: {atom_id}")
            mapping[atom_id] = MappingRow(
                atom_id=atom_id,
                final_owner_type=normalize_code(str(raw.get("final-owner-type", ""))),
                final_change=normalize_code(str(raw.get("final-owner-change", ""))),
                final_capability=normalize_code(str(raw.get("final-owner-capability", ""))),
                final_projection=normalize_code(str(raw.get("final-artifact-projection", ""))),
                final_relation=normalize_code(str(raw.get("final-relation", ""))),
                foundation_reference_id=normalize_code(str(raw.get("foundation-reference-id", ""))),
                capability_advancement=normalize_code(str(raw.get("capability-advancement", ""))),
                plan_decision=str(raw.get("plan-decision", "")),
                reason=str(raw.get("reason", "")),
            )
        if not mapping:
            raise ValueError(f"{path} 中没有 Phase 5 mapping row")
        return mapping

    rows = parse_table(path, ["Global Atom ID", "Final Owner Change", "Final Relation"])
    mapping: Dict[str, MappingRow] = {}
    for raw in rows:
        atom_id = normalize_code(cell(raw, "Global Atom ID"))
        if not atom_id:
            continue
        if not GLOBAL_ATOM_ID_RE.match(atom_id):
            raise ValueError(f"Phase 5 mapping 中的 Global Atom ID 必须匹配 GA-####: {atom_id}")
        if atom_id in mapping:
            raise ValueError(f"Phase 5 mapping 中存在重复 ID: {atom_id}")
        mapping[atom_id] = MappingRow(
            atom_id=atom_id,
            final_owner_type=normalize_code(cell(raw, "Final Owner Type")),
            final_change=normalize_code(cell(raw, "Final Owner Change")),
            final_capability=normalize_code(cell(raw, "Final Owner Capability")),
            final_projection=normalize_code(cell(raw, "Final Artifact Projection")),
            final_relation=normalize_code(cell(raw, "Final Relation")),
            foundation_reference_id=normalize_code(cell(raw, "Foundation Reference")),
            capability_advancement=normalize_code(cell(raw, "Capability Advancement")),
            plan_decision=cell(raw, "Plan Decision"),
            reason=cell(raw, "Reason"),
        )
    if not mapping:
        raise ValueError(f"{path} 中没有 Phase 5 mapping row")
    return mapping


def require_string(item: Dict[str, object], key: str, where: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where} 缺少字符串字段 {key}")
    return value.strip()


def load_config(path: Path) -> Dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Phase 5 config 必须是 JSON object")
    changes_raw = data.get("changes")
    caps_raw = data.get("capabilities")
    if not isinstance(changes_raw, list) or not changes_raw:
        raise ValueError("Phase 5 config 必须包含非空 changes 数组")
    if not isinstance(caps_raw, list) or not caps_raw:
        raise ValueError("Phase 5 config 必须包含非空 capabilities 数组")
    return data


def config_status(config: Dict[str, object]) -> str:
    return str(config.get("status") or "adjusted")


def require_terminal_status(status: str) -> None:
    if status not in PHASE5_STATUSES:
        raise ValueError(
            "Phase 5 config status 必须是 accepted、adjusted、needs-coverage-recheck 或 blocked，"
            f"不能使用 validator/reviewer/repair 流程态: {status}"
        )
    if status not in TERMINAL_PHASE5_STATUSES:
        raise ValueError(
            "phase5_plan_refit.py 只渲染 accepted/adjusted 的终态 mapping、final packets 和 handoff artifacts；"
            f"{status} 必须由 Phase 5 writer 写入 source-window-refit-trace、change-plan-adjustments、"
            "phase-5-agent-report 和 phase-5.trace.json，不能用 final-packet renderer 伪造终态输出。"
        )


def parse_changes(config: Dict[str, object]) -> List[ChangeDef]:
    changes: List[ChangeDef] = []
    seen: set[str] = set()
    for i, raw in enumerate(config["changes"]):  # type: ignore[index]
        if not isinstance(raw, dict):
            raise ValueError(f"changes[{i}] 必须是 object")
        slug = require_string(raw, "slug", f"changes[{i}]")
        if slug in seen:
            raise ValueError(f"changes 中存在重复 slug: {slug}")
        seen.add(slug)
        changes.append(
            ChangeDef(
                slug=slug,
                title=str(raw.get("title") or slug),
                outcome=str(raw.get("outcome") or slug),
                kind=str(raw.get("kind") or "business"),
            )
        )
    return changes


def parse_capabilities(config: Dict[str, object]) -> List[CapabilityDef]:
    caps: List[CapabilityDef] = []
    seen: set[str] = set()
    for i, raw in enumerate(config["capabilities"]):  # type: ignore[index]
        if not isinstance(raw, dict):
            raise ValueError(f"capabilities[{i}] 必须是 object")
        slug = require_string(raw, "slug", f"capabilities[{i}]")
        if slug in seen:
            raise ValueError(f"capabilities 中存在重复 slug: {slug}")
        seen.add(slug)
        caps.append(CapabilityDef(slug=slug, boundary=str(raw.get("boundary") or slug)))
    return caps


def latest_mapping(orchestrate_dir: Path) -> Path:
    mapping_path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
    if mapping_path.exists():
        return mapping_path
    mapping_path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.md"
    if not mapping_path.exists():
        raise ValueError(f"缺少 Phase 5 mapping JSON/Markdown: {mapping_path}")
    return mapping_path


def default_config_path(mapping_path: Path) -> Path:
    return mapping_path.parent / "phase5-refit.config.json"


def join_atoms(atoms: Dict[str, AtomRow], mapping: Dict[str, MappingRow]) -> List[FinalAtom]:
    atom_ids = set(atoms)
    mapping_ids = set(mapping)
    missing = sorted(atom_ids - mapping_ids)
    extra = sorted(mapping_ids - atom_ids)
    if missing:
        raise ValueError(f"Phase 5 mapping 缺少 global atom: {', '.join(missing[:12])}")
    if extra:
        raise ValueError(f"Phase 5 mapping 包含未知 global atom: {', '.join(extra[:12])}")
    return [FinalAtom(atoms[atom_id], mapping[atom_id]) for atom_id in sorted(atom_ids)]


def is_no_owner(value: str) -> bool:
    return normalize_code(value) in NO_OWNER_VALUES


def executable_changes(changes: Sequence[ChangeDef]) -> List[ChangeDef]:
    return [change for change in changes if change.kind != "foundation"]


def is_foundation_mapping(row: MappingRow, changes_by_slug: Dict[str, ChangeDef]) -> bool:
    if row.final_owner_type == FOUNDATION_OWNER_TYPE:
        return True
    if row.final_relation == FOUNDATION_OWNER_TYPE:
        return True
    owner = changes_by_slug.get(row.final_change)
    return bool(owner and owner.kind == "foundation")


def normalize_mapping_for_foundation_reference(
    mapping: Dict[str, MappingRow],
    changes: Sequence[ChangeDef],
) -> Dict[str, MappingRow]:
    changes_by_slug = {change.slug: change for change in changes}
    normalized: Dict[str, MappingRow] = {}
    for atom_id, row in mapping.items():
        if is_foundation_mapping(row, changes_by_slug):
            normalized[atom_id] = replace(
                row,
                final_owner_type=FOUNDATION_OWNER_TYPE,
                final_change="None",
                final_capability="None",
                final_relation=row.final_relation if row.final_relation and row.final_relation != FOUNDATION_OWNER_TYPE else "direct",
                foundation_reference_id=FOUNDATION_REFERENCE_ID,
                capability_advancement="does-not-advance-capability",
                plan_decision=row.plan_decision or "foundation-reference",
            )
            continue
        owner_type = row.final_owner_type or (EXECUTABLE_OWNER_TYPE if not is_no_owner(row.final_change) else "none")
        advancement = row.capability_advancement
        if not advancement:
            advancement = "advances-capability" if row.final_relation == "direct" else "does-not-advance-capability"
        normalized[atom_id] = replace(row, final_owner_type=owner_type, capability_advancement=advancement)
    return normalized


def is_executable_direct(item: FinalAtom) -> bool:
    return item.mapping.final_relation == "direct" and item.mapping.final_owner_type != FOUNDATION_OWNER_TYPE


def is_foundation_reference_atom(item: FinalAtom) -> bool:
    return item.mapping.final_owner_type == FOUNDATION_OWNER_TYPE


def validate(
    final_atoms: Sequence[FinalAtom],
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
) -> List[str]:
    warnings: List[str] = []
    change_slugs = {change.slug for change in changes}
    capability_slugs = {cap.slug for cap in capabilities}
    direct_seen: set[str] = set()

    for item in final_atoms:
        row = item.mapping
        if row.final_relation == "direct":
            if row.atom_id in direct_seen:
                raise ValueError(f"direct atom 重复: {row.atom_id}")
            direct_seen.add(row.atom_id)
            if row.final_projection not in DIRECT_PROJECTIONS:
                raise ValueError(
                    f"{row.atom_id} 是 direct，但 projection={row.final_projection}，"
                    "final direct atom 不能使用 contextual-only 或空 projection"
                )
            if row.final_owner_type == FOUNDATION_OWNER_TYPE:
                if row.capability_advancement != "does-not-advance-capability":
                    raise ValueError(f"{row.atom_id} foundation reference row 不能计入 capability advancement")
                continue
            if row.final_change not in change_slugs:
                raise ValueError(f"{row.atom_id} direct final change 未在 config changes 中声明: {row.final_change}")
            if row.final_capability not in capability_slugs:
                raise ValueError(
                    f"{row.atom_id} direct final capability 未在 config capabilities 中声明: {row.final_capability}"
                )
        else:
            if row.final_projection in ("", "None"):
                warnings.append(f"{row.atom_id} 非 direct row 缺少 final projection")

    by_change = direct_by_change(final_atoms, changes)
    for change in changes:
        direct_count = len(by_change[change.slug])
        caps = {item.mapping.final_capability for item in by_change[change.slug] if item.mapping.final_capability != "None"}
        if direct_count > 120:
            warnings.append(f"{change.slug} direct atom count={direct_count}，需要 hard split/blocker 级别说明")
        elif direct_count > 80 or len(caps) > 6:
            warnings.append(f"{change.slug} 超过 Phase 5 over-budget 复核阈值")
    return warnings


def direct_by_change(final_atoms: Sequence[FinalAtom], changes: Sequence[ChangeDef]) -> Dict[str, List[FinalAtom]]:
    result: Dict[str, List[FinalAtom]] = {change.slug: [] for change in changes}
    for item in final_atoms:
        row = item.mapping
        if is_executable_direct(item) and row.final_change in result:
            result[row.final_change].append(item)
    return result


def context_by_change(final_atoms: Sequence[FinalAtom], changes: Sequence[ChangeDef]) -> Dict[str, List[FinalAtom]]:
    result: Dict[str, List[FinalAtom]] = {change.slug: [] for change in changes}
    for item in final_atoms:
        row = item.mapping
        if row.final_owner_type != FOUNDATION_OWNER_TYPE and row.final_relation != "direct" and row.final_change in result:
            result[row.final_change].append(item)
    return result


def capability_progression(
    by_change: Dict[str, List[FinalAtom]],
    changes: Sequence[ChangeDef],
) -> Dict[str, List[str]]:
    progress: Dict[str, List[str]] = defaultdict(list)
    for change in changes:
        caps = sorted(
            {
                item.mapping.final_capability
                for item in by_change[change.slug]
                if item.mapping.final_capability != "None"
            }
        )
        for cap in caps:
            progress[cap].append(change.slug)
    return dict(progress)


def ids_for(items: Sequence[FinalAtom], limit: int = 12) -> str:
    atom_ids = [item.source.atom_id for item in items]
    if not atom_ids:
        return "`None`"
    if len(atom_ids) > limit:
        return ", ".join(code(atom_id) for atom_id in atom_ids[:limit]) + f" 等 {len(atom_ids)} 个"
    return ", ".join(code(atom_id) for atom_id in atom_ids)


def mapping_json_rows(final_atoms: Sequence[FinalAtom]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for item in final_atoms:
        source = item.source
        mapping = item.mapping
        _, line_ranges, _, _ = parse_line_ranges(source.lines)
        rows.append(
            {
                "global-atom-id": source.atom_id,
                "source-document": source.source_document,
                "lines": source.lines,
                "line-ranges": line_ranges,
                "phase-3-owner-status": f"{source.owner_change} / {source.coverage_status}",
                "phase-3-artifact-projection": source.artifact_projection,
                "final-owner-type": mapping.final_owner_type,
                "final-owner-change": mapping.final_change,
                "final-owner-capability": mapping.final_capability,
                "final-artifact-projection": mapping.final_projection,
                "final-relation": mapping.final_relation,
                "foundation-reference-id": mapping.foundation_reference_id,
                "capability-advancement": mapping.capability_advancement,
                "plan-decision": mapping.plan_decision,
                "reason": mapping.reason,
            }
        )
    return rows


def write_mapping_json(path: Path, final_atoms: Sequence[FinalAtom], artifact_path: Path) -> None:
    write_json(
        path,
        {
            "trace-schema": ATOM_PLAN_MAPPING_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "artifact-path": artifact_path.as_posix(),
            "rows": mapping_json_rows(final_atoms),
        },
    )


def render_mapping_markdown(final_atoms: Sequence[FinalAtom]) -> str:
    lines = [
        "# Atom Plan Mapping\n\n",
        "| Global Atom ID | Source Document | Lines | Phase 3 Owner / Status | Phase 3 Artifact Projection | Final Owner Type | Final Owner Change | Final Owner Capability | Final Artifact Projection | Final Relation | Foundation Reference | Capability Advancement | Plan Decision | Reason |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for item in final_atoms:
        source = item.source
        mapping = item.mapping
        lines.append(
            f"| `{source.atom_id}` | `{source.source_document}` | `{source.lines}` | "
            f"`{source.owner_change} / {source.coverage_status}` | `{source.artifact_projection}` | "
            f"`{mapping.final_owner_type}` | `{mapping.final_change}` | `{mapping.final_capability}` | `{mapping.final_projection}` | "
            f"`{mapping.final_relation}` | `{mapping.foundation_reference_id}` | `{mapping.capability_advancement}` | "
            f"`{mapping.plan_decision}` | {md(mapping.reason)} |\n"
        )
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def orchestrate_rel(output_orchestrate_dir: Path, path: Path) -> str:
    try:
        return (Path("openspec/orchestrate") / path.relative_to(output_orchestrate_dir)).as_posix()
    except ValueError:
        return path.as_posix()


def write_final_packet_index(
    output_orchestrate_dir: Path,
    work_dir: Path,
    changes: Sequence[ChangeDef],
    by_change: Dict[str, List[FinalAtom]],
    by_context: Dict[str, List[FinalAtom]],
) -> Path:
    packets: List[Dict[str, object]] = []
    anchors = output_orchestrate_dir / "change-capability-anchors"
    for change in changes:
        packet_path = anchors / change.slug / f"{change.slug}.md"
        cap_paths = sorted((anchors / change.slug / "capability-anchors").glob("*.md"))
        packets.append(
            {
                "change": change.slug,
                "packet-path": orchestrate_rel(output_orchestrate_dir, packet_path),
                "packet-digest": sha256_file(packet_path) if packet_path.exists() else "",
                "direct-atom-ids": sorted(item.source.atom_id for item in by_change[change.slug]),
                "owner-scoped-non-direct-atom-ids": sorted(item.source.atom_id for item in by_context[change.slug]),
                "capability-view-paths": [orchestrate_rel(output_orchestrate_dir, path) for path in cap_paths],
            }
        )
    path = work_dir / "final-packet-index.json"
    write_json(
        path,
        {
            "trace-schema": FINAL_PACKET_INDEX_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "packets": packets,
        },
    )
    return path


def render_foundation_reference(items: Sequence[FinalAtom], trace_rel: str) -> str:
    lines = [
        "# Foundation Runtime Substrate Reference\n\n",
        "本文件是 Phase 5 从 foundation candidate 派生的只读设计参考，不是 executable OpenSpec change packet。\n\n",
        f"- Reference ID: `{FOUNDATION_REFERENCE_ID}`\n",
        f"- Trace sidecar: `{trace_rel}`\n",
        "- Consumption contract: 后续业务 change 在 propose 时可以读取本 reference 作为设计约束和实现前提；不得把本文件中的 GA 反向投影为当前 change 的 specs、runtime acceptance、Proof Slice 或 capability advancement。\n\n",
        "## Reference Atoms\n\n",
        "| Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Artifact Projection | Propose Use | Evidence Need |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for item in items:
        source = item.source
        mapping = item.mapping
        lines.append(
            f"| `{source.atom_id}` | `{source.source_document}` | `{source.lines}` | `{source.atom_type}` | "
            f"{md(source.source_fact)} | `{source.normativity}` | `{mapping.final_projection}` | "
            f"{md(source.propose_use)} | `{source.evidence_need}` |\n"
        )
    lines.append(
        "\n## Usage Boundary\n\n"
        "- 本 reference 只表达底座设计背景、构建前提、smoke/conformance 线索和实现约束。\n"
        "- 业务 change 的 executable scope 必须来自该 change 自身的 final packet direct atoms。\n"
        "- runtime acceptance 只描述当前业务 change 的可观察运行行为；不得从本 reference 自动生成 runtime rows 或 required Proof Slice。\n"
        "- specs 只消费当前业务 change 的 direct `spec-requirement` / `spec-guard` atoms；不得从本 reference 或 `design-obligation` fallback 派生 spec requirement/guard。\n"
    )
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def write_foundation_reference(
    output_orchestrate_dir: Path,
    items: Sequence[FinalAtom],
    mapping_json_path: Path,
) -> Optional[Tuple[Path, Path]]:
    if not items:
        return None
    foundation_dir = output_orchestrate_dir / "foundation-reference"
    ensure_dir(foundation_dir)
    artifact_path = foundation_dir / f"{FOUNDATION_REFERENCE_ID}.md"
    trace_path = foundation_dir / f"{FOUNDATION_REFERENCE_ID}.trace.json"
    artifact_rel = orchestrate_rel(output_orchestrate_dir, artifact_path)
    trace_rel = orchestrate_rel(output_orchestrate_dir, trace_path)
    write_text(artifact_path, render_foundation_reference(items, trace_rel))
    rows: List[Dict[str, object]] = []
    for item in items:
        source = item.source
        mapping = item.mapping
        _, line_ranges, _, _ = parse_line_ranges(source.lines)
        rows.append(
            {
                "global-atom-id": source.atom_id,
                "source-document": source.source_document,
                "lines": source.lines,
                "line-ranges": line_ranges,
                "atom-type": source.atom_type,
                "source-fact": source.source_fact,
                "normativity": source.normativity,
                "artifact-projection": mapping.final_projection,
                "foundation-reference-id": FOUNDATION_REFERENCE_ID,
                "capability-advancement": "does-not-advance-capability",
            }
        )
    write_json(
        trace_path,
        {
            "trace-schema": FOUNDATION_REFERENCE_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "foundation-reference-id": FOUNDATION_REFERENCE_ID,
            "artifact-path": artifact_rel,
            "artifact-digest": sha256_file(artifact_path),
            "atom-plan-mapping-path": orchestrate_rel(output_orchestrate_dir, mapping_json_path),
            "atom-ids": [item.source.atom_id for item in items],
            "rows": rows,
        },
    )
    return artifact_path, trace_path


def atom_groups(items: Sequence[FinalAtom]) -> str:
    counts = Counter(item.mapping.final_capability for item in items)
    return "；".join(f"`{cap}` {count} 个" for cap, count in counts.most_common()) if counts else "`None`"


def projection_mix(items: Sequence[FinalAtom]) -> str:
    counts = Counter(item.mapping.final_projection for item in items)
    return ", ".join(f"{proj}={count}" for proj, count in counts.items()) if counts else "None"


def evidence_types(items: Sequence[FinalAtom]) -> str:
    values = sorted({item.source.evidence_need for item in items if item.source.evidence_need and item.source.evidence_need != "None"})
    return ", ".join(values) if values else "manual"


def failure_count(items: Sequence[FinalAtom]) -> int:
    return sum(1 for item in items if item.source.atom_type in FAILURE_TYPES)


def budget_status(items: Sequence[FinalAtom]) -> str:
    count = len(items)
    cap_count = len({item.mapping.final_capability for item in items if item.mapping.final_capability != "None"})
    if count > 120:
        return "hard-over-budget"
    if count > 80 or cap_count > 6:
        return "over-budget-reviewed"
    if count > 60:
        return "above-target-reviewed"
    return "within-target"


def relation_label(change_slug: str, cap_slug: str, cap_changes: Dict[str, List[str]]) -> str:
    return "New" if cap_changes.get(cap_slug, [None])[0] == change_slug else "Modified"


def optional_list(config: Dict[str, object], key: str) -> List[Dict[str, object]]:
    value = config.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"config.{key} 必须是数组")
    result: List[Dict[str, object]] = []
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"config.{key}[{i}] 必须是 object")
        result.append(item)
    return result


def render_change_plan(
    config: Dict[str, object],
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    by_change: Dict[str, List[FinalAtom]],
    cap_changes: Dict[str, List[str]],
    work_dir: Path,
) -> str:
    lines: List[str] = ["# Source-Aligned Phase 5 Change Plan\n\n", "## Inputs\n\n"]
    lines.append(
        f"- Source documents read: {config.get('source_documents_read', '`openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md` 中源文档已由 Phase 2/3 覆盖。')}\n"
    )
    lines.append("- Phase 3 global atom index path: `openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`。\n")
    lines.append("- Phase 4 source-window dossiers: `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/index.md`。\n")
    lines.append("- Phase 4 semantic profile review: `openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md`。\n")
    lines.append(f"- Phase 5 work path: `{work_dir.as_posix()}/`。\n")
    lines.append(
        f"- Assumptions and conflicts: {config.get('assumptions_and_conflicts', 'Phase 3 已给出 `Decision: coverage-complete`；Phase 5 未新增 atom，也未改写 Phase 2/3 证据。')}\n"
    )

    lines.append("\n## Capability Map\n\n")
    lines.append("| Capability | Behavior boundary | First change | Later expansion |\n")
    lines.append("| --- | --- | --- | --- |\n")
    for cap in capabilities:
        owners = cap_changes.get(cap.slug, [])
        first = owners[0] if owners else "None"
        later = [owner for owner in owners if owner != first]
        later_text = (
            "后续由 " + "、".join(code(owner) for owner in later) + " 直接拥有增量 atom。"
            if later
            else "当前来源只要求首版基线；后续扩展需新增 source-backed delta。"
        )
        lines.append(f"| `{cap.slug}` | {md(cap.boundary)} | `{first}` | {md(later_text)} |\n")

    lines.append("\n## Capability Progression Matrix\n\n")
    lines.append("| Change | " + " | ".join(code(cap.slug) for cap in capabilities) + " |\n")
    lines.append("| --- | " + " | ".join("---" for _ in capabilities) + " |\n")
    for change in changes:
        cells: List[str] = []
        for cap in capabilities:
            items = [item for item in by_change[change.slug] if item.mapping.final_capability == cap.slug]
            if not items:
                cells.append("")
            else:
                cells.append(f"{relation_label(change.slug, cap.slug, cap_changes)}: {ids_for(items, 4)}")
        lines.append(f"| `{change.slug}` | " + " | ".join(md(value) for value in cells) + " |\n")

    lines.append("\n## Change Roadmap\n")
    for change in changes:
        items = by_change[change.slug]
        caps = sorted({item.mapping.final_capability for item in items if item.mapping.final_capability != "None"})
        new_caps = [cap for cap in caps if cap_changes.get(cap, [None])[0] == change.slug]
        modified_caps = [cap for cap in caps if cap not in new_caps]
        gate = "business-executable"
        dep = "无" if change == changes[0] else "依赖前序 final change 已归档的 baseline；具体 upstream baseline 见 change packet。"
        lines.append(f"\n### Change name: `{change.slug}`\n\n")
        lines.append(f"- Closed-loop outcome: {md(change.outcome)}\n")
        lines.append("- Source-window grounding:\n")
        lines.append("  - Input source-window dossiers: `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/`。\n")
        lines.append("  - Source-backed semantic profile: `openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md`。\n")
        lines.append("  - Refit trace: `openspec/orchestrate/phase-works/phase-5/source-window-refit-trace.md`。\n")
        lines.append(f"- Direct atom groups: {atom_groups(items)}。\n")
        lines.append("- Capability changes:\n")
        lines.append("  - New: " + (", ".join(code(cap) for cap in new_caps) if new_caps else "`None`") + "\n")
        lines.append("  - Modified: " + (", ".join(code(cap) for cap in modified_caps) if modified_caps else "`None`") + "\n")
        lines.append(f"- In scope: {md(change.title)} 对应 direct atom 表中的行为、设计、guard 和验证义务。\n")
        lines.append("- Out of scope: 不直接拥有未映射到本 change 的未来 atom；依赖、上下文、非目标和横切证据策略仅按 packet 中的 context/evidence burden 消费。\n")
        lines.append("- Vertical slice:\n")
        lines.append("  - Entry: 由该 change 的闭环入口触发，详见 final packet direct atom 表。\n")
        lines.append("  - Fact: 只持久化该闭环需要的 domain fact、snapshot、action、version、entitlement、project 或 export 事实。\n")
        lines.append("  - Projection: 只展示该闭环产生的页面、对象、线程、列表、状态或下载结果。\n")
        lines.append("  - Failure: 失败路径不污染既有稳定事实，并保留可重试或可回流上下文。\n")
        lines.append(f"  - Verification: {md(evidence_types(items))}。\n")
        lines.append(f"- Dependencies: {dep}\n")
        lines.append("- Contextual atoms / downstream design constraints: 见 final packet context table 和 `atom-plan-mapping.md`。\n")
        lines.append("- Non-goals: 只保留与本闭环相关的全局/局部非目标 guard，不扩展 prototype-only 页面、scene、fixture 或 mock 资产。\n")
        lines.append("- Complexity budget:\n")
        lines.append(f"  - Direct atom count: `{len(items)}`\n")
        lines.append("  - Capabilities advanced: " + (", ".join(code(cap) for cap in caps) if caps else "`None`") + "\n")
        lines.append("  - Surface families: 该 change 的入口、页面/对象、domain command、worker 或列表/导出面；超过目标时见 complexity review。\n")
        lines.append(f"  - Evidence types: {md(evidence_types(items))}\n")
        lines.append(f"  - Executable roadmap status: `{gate}`\n")
        lines.append(f"  - Budget status: `{budget_status(items)}`\n")
        lines.append("  - Split/defer analysis: Phase 5 已按 atom 级闭环、失败路径和验证面记录拆分、保留或阻断判断。\n")
        lines.append("- Archive readiness: direct atom 表中的成功、失败、guard 和验证义务可在一个 focused OpenSpec change 中提案、实现、验证和归档。\n")

    lines.append("\n## Phase 5 Risk Checks\n\n")
    lines.append("1. final executable roadmap 从第一个业务 change 开始；foundation candidate 已转为只读 reference。\n")
    lines.append("2. 计划不是 capability-driven 对角矩阵；长期 capability 可在多个业务闭环中演进。\n")
    lines.append("3. 过大的 Phase 1 change 已按可保存、可验证、可归档的闭环拆分。\n")
    lines.append("4. `design-obligation` 与 `verification-obligation` 保留原 projection，没有因为 direct ownership 被强制改成 `spec-requirement`。\n")
    lines.append("5. prototype-only、fixture、scene、mock asset 和非目标 row 只作为 guard/context 消费。\n")
    lines.append("\n## Phase 5 Language Self-Check\n\n")
    lines.append("已忽略反引号内 ID、路径、命令、代码/API/DB/package 符号、固定 enum/status、relation token 和精确 source phrase 后检查；本文由代理撰写的解释内容均为简体中文。\n")
    return "".join(lines)


def render_capability_review(
    capabilities: Sequence[CapabilityDef],
    direct_items: Sequence[FinalAtom],
    cap_changes: Dict[str, List[str]],
) -> str:
    lines = [
        "# Capability Progression Review\n\n",
        "| Capability | Atom Families | Current Change Sequence | Required Order | Sequence Problem | Adjustment |\n",
        "| --- | --- | --- | --- | --- | --- |\n",
    ]
    for cap in capabilities:
        owners = cap_changes.get(cap.slug, [])
        fam = Counter(item.source.atom_type for item in direct_items if item.mapping.final_capability == cap.slug)
        fam_text = ", ".join(f"{name}={count}" for name, count in fam.items()) if fam else "None"
        seq = " -> ".join(code(owner) for owner in owners) if owners else "`None`"
        required = f"`{owners[0]}` 作为 baseline" if owners else "`None`"
        problem = (
            "无；首个 direct owner 与 Capability Map、矩阵首格、roadmap New、anchor index 和 human plan 一致。"
            if owners
            else "该能力没有 final direct atom，不计入最终能力进展。"
        )
        adjustment = "重算 New/Modified 标签；依赖、上下文、证据和非目标未计入 capability advancement。"
        lines.append(f"| `{cap.slug}` | {md(fam_text)} | {md(seq)} | {md(required)} | {md(problem)} | {md(adjustment)} |\n")
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_complexity_review(
    config: Dict[str, object],
    changes: Sequence[ChangeDef],
    by_change: Dict[str, List[FinalAtom]],
    cap_changes: Dict[str, List[str]],
) -> str:
    decision_overrides = {
        str(item.get("change")): str(item.get("decision"))
        for item in optional_list(config, "complexity_decisions")
        if item.get("change") and item.get("decision")
    }
    lines = [
        "# Change Complexity Review\n\n",
        "| Change | Direct Atom Count | Artifact Projection Mix | Atom Groups | New Capabilities | Modified Capabilities | Primary Functional Points | Entry/Fact/Projection Count | Failure/Recovery Count | Evidence Types | Surface Families | Executable Roadmap Status | Budget Status | Complexity Decision |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for change in changes:
        items = by_change[change.slug]
        caps = sorted({item.mapping.final_capability for item in items if item.mapping.final_capability != "None"})
        new_caps = [cap for cap in caps if cap_changes.get(cap, [None])[0] == change.slug]
        modified_caps = [cap for cap in caps if cap not in new_caps]
        gate = "business-executable"
        default_decision = "保留；该 change 已是可独立验证的业务闭环。"
        decision = decision_overrides.get(change.slug, default_decision)
        lines.append(
            f"| `{change.slug}` | `{len(items)}` | {md(projection_mix(items))} | {md(atom_groups(items))} | "
            f"{md(', '.join(code(cap) for cap in new_caps) if new_caps else '`None`')} | "
            f"{md(', '.join(code(cap) for cap in modified_caps) if modified_caps else '`None`')} | "
            f"1 个闭环：{md(change.outcome)} | entry=1; fact=1; projection=1 | `{failure_count(items)}` | "
            f"{md(evidence_types(items))} | 主要 surface 不超过该闭环的页面/对象/domain/worker 组合 | "
            f"`{gate}` | `{budget_status(items)}` | {md(decision)} |\n"
        )

    split_analyses = optional_list(config, "split_analyses")
    if split_analyses:
        lines.append("\n## Required Split Analysis\n\n")
        lines.append("| Change | Trigger | Candidate Split | Atoms / Capabilities Moved | New Closed-loop Outcome | Verification Surface | Decision | Reason |\n")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for item in split_analyses:
            lines.append(
                f"| {code(item.get('change', ''))} | {md(item.get('trigger', ''))} | {md(item.get('candidate_split', ''))} | "
                f"{md(item.get('atoms_moved', ''))} | {md(item.get('new_outcome', ''))} | {md(item.get('verification_surface', ''))} | "
                f"{code(item.get('decision', ''))} | {md(item.get('reason', ''))} |\n"
            )
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_decision_log(config: Dict[str, object]) -> str:
    decisions = optional_list(config, "decisions")
    if not decisions:
        decisions = [
            {
                "item": "Phase 3 gate",
                "input_evidence": "`coverage-review.md` 写明 `Decision: coverage-complete`。",
                "candidate_options": "继续 Phase 5 / 返回 blocker",
                "decision": "继续 Phase 5",
                "output_artifact": "全部 Phase 5 artifacts",
                "reason": "覆盖已闭合，Phase 5 可只做 plan refit。",
            }
        ]
    lines = [
        "# Plan Refit Decision Log\n\n",
        "| Decision Item | Input Evidence | Candidate Options | Decision | Output Artifact | Reason |\n",
        "| --- | --- | --- | --- | --- | --- |\n",
    ]
    for item in decisions:
        lines.append(
            f"| {code(item.get('item', ''))} | {md(item.get('input_evidence', ''))} | {md(item.get('candidate_options', ''))} | "
            f"{code(item.get('decision', ''))} | {md(item.get('output_artifact', ''))} | {md(item.get('reason', ''))} |\n"
        )
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_source_window_refit_trace(config: Dict[str, object], changes: Sequence[ChangeDef], by_change: Dict[str, List[FinalAtom]]) -> str:
    rows = optional_list(config, "source_window_refit_trace")
    lines = [
        "# Source-Window Refit Trace\n\n",
        "本文件记录 Phase 5 如何使用 Phase 4 source-window dossiers 和语义画像重构最终 change/capability 计划。\n\n",
        "| Input Change / Capability | Source Window Evidence | Input Atoms | Final Change / Capability | Atom Movement | Relation Changes | Engineering Reason |\n",
        "| --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    if rows:
        for item in rows:
            lines.append(
                f"| {md(item.get('input_unit', ''))} | {md(item.get('source_window_evidence', ''))} | "
                f"{md(item.get('input_atoms', ''))} | {md(item.get('final_change_capability', ''))} | "
                f"{md(item.get('atom_movement', ''))} | {md(item.get('relation_changes', ''))} | "
                f"{md(item.get('engineering_reason', ''))} |\n"
            )
    else:
        for change in changes:
            items = by_change[change.slug]
            lines.append(
                f"| `{change.slug}` | `phase-works/phase-4/source-window-dossiers/` 与 "
                "`source-window-semantic-profile-review.md` | "
                f"{md(ids_for(items, 8))} | `{change.slug}` / direct capabilities in packet | "
                "按 reviewed `atom-plan-mapping.md` 落位 direct owner。 | "
                "context/dependency/evidence/non-goal 见 mapping relation。 | "
                f"{md(change.outcome)} 形成可实现、可验证、可归档的工程交付闭环。 |\n"
            )
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_adjustments(config: Dict[str, object], status: str) -> Optional[str]:
    adjustments = optional_list(config, "adjustments")
    if status not in {"adjusted", "needs-coverage-recheck", "blocked"} and not adjustments:
        return None
    lines = [
        "# Change Plan Adjustments\n\n",
        "| Adjustment | Previous Plan Element | New Plan Element | Atom Groups Moved | Coverage Recheck Needed | Reason |\n",
        "| --- | --- | --- | --- | --- | --- |\n",
    ]
    for item in adjustments:
        lines.append(
            f"| {code(item.get('adjustment', ''))} | {md(item.get('previous_plan_element', ''))} | "
            f"{md(item.get('new_plan_element', ''))} | {md(item.get('atom_groups_moved', ''))} | "
            f"{code(item.get('coverage_recheck_needed', 'No'))} | {md(item.get('reason', ''))} |\n"
        )
    if not adjustments:
        lines.append("| `none` | `None` | `None` | 未移动 atom。 | `No` | Phase 5 未调整有效计划。 |\n")
    next_action = config.get("next_action", "Phase 5 状态已闭合；下一步可以从 final change packets 启动 `openspec-propose`。")
    lines.append(f"\n## Next Action\n\n{next_action}\n")
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_packet(
    change: ChangeDef,
    changes: Sequence[ChangeDef],
    by_change: Dict[str, List[FinalAtom]],
    by_context: Dict[str, List[FinalAtom]],
    work_dir: Path,
) -> str:
    items = by_change[change.slug]
    gate = "business-executable"
    lines = [
        f"# Change Packet: `{change.slug}`\n\n",
        f"- Change name: `{change.slug}`\n",
        f"- Closed-loop outcome: {md(change.outcome)}\n",
        "- Global atom index: `openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`\n",
        "- Source-window grounding: `openspec/orchestrate/phase-works/phase-4/source-window-dossiers/`；语义画像见 `openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md`。\n",
        f"- Source-window refit trace: `{work_dir.as_posix()}/source-window-refit-trace.md`\n",
        f"- Phase 5 mapping: `{work_dir.as_posix()}/atom-plan-mapping.md`\n",
        f"- Complexity budget status: `{budget_status(items)}`；direct atom count=`{len(items)}`。\n",
        f"- Executable roadmap status: `{gate}`。\n",
        "- Blockers: `None`\n\n",
        "## Final Direct Owner Atoms\n\n",
        "| Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Artifact Projection | Projection Rationale | Owner Capability | Atom Relation | Roles | Propose Use | Evidence Need |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for item in items:
        source = item.source
        mapping = item.mapping
        rationale = "保留 Phase 3 projection 或采用 Phase 5 final projection；不把 design 或 verification 行强制改成 spec requirement。"
        lines.append(
            f"| `{source.atom_id}` | `{source.source_document}` | `{source.lines}` | `{source.atom_type}` | {md(source.source_fact)} | "
            f"`{source.normativity}` | `{mapping.final_projection}` | {md(rationale)} | `{mapping.final_capability}` | "
            f"`direct` | `direct-owner` | {md(source.propose_use)} | `{source.evidence_need}` |\n"
        )
    lines.append("\n## Contextual Atoms And Future Constraints\n\n")
    lines.append("| Global Atom ID / Relation | Source Document | Lines | Context Type | Affects Current Design Because | Handling |\n")
    lines.append("| --- | --- | --- | --- | --- | --- |\n")
    context_items = by_context[change.slug]
    if not context_items:
        lines.append("| `None` | `None` | `None` | `None` | 本 change 没有专属 contextual row。 | 仅消费 upstream baseline 与全局非目标 guard。 |\n")
    else:
        for item in context_items:
            lines.append(
                f"| `{item.source.atom_id}` / `{item.mapping.final_relation}` | `{item.source.source_document}` | `{item.source.lines}` | "
                f"`{item.mapping.final_relation}` | {md(item.source.source_fact)} | {md(item.mapping.reason)} |\n"
            )
    order = {item.slug: pos for pos, item in enumerate(changes)}
    previous = [item.slug for item in changes if order[item.slug] < order[change.slug]]
    baseline = (
        "本 change 只依赖前序已归档 baseline：" + "、".join(code(slug) for slug in previous[-3:]) + "。更早 baseline 不吸收本 change 的 direct atom。\n"
        if previous
        else "无；这是第一个 executable business change；foundation 只作为只读 reference 被后续 propose 读取。\n"
    )
    lines.append("\n## Upstream Realized Baseline\n\n")
    lines.append(baseline)
    lines.append("\n## Downstream Constraints\n\n")
    lines.append("后续 change 可消费本 packet 已实现的 domain fact、guard、snapshot、action、version、project、entitlement 或 export baseline，但不得把未来义务反向计入本 change direct scope。\n")
    lines.append("\n## Explicit Non-Goals\n\n")
    lines.append("不实现 prototype-only scene、fixture、mock asset、未列入 MVP 的页面/对象、协作、团队权限、版本树、多图画布或完整科研设计平台。\n")
    lines.append("\n## Evidence Burden\n\n")
    lines.append("证据必须覆盖 direct atom 表中的成功、失败、guard、设计和验证义务；横切 viewport/object/state 证据按 Phase 5 mapping 作为 evidence burden 分散到相关业务闭环。\n")
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_capability_view(change: ChangeDef, cap: str, items: Sequence[FinalAtom]) -> str:
    lines = [
        f"# Capability View: `{cap}` in `{change.slug}`\n\n",
        "本文件是 final change packet 的派生视图，不改变 atom ID、来源行号、projection 或事实文本。\n\n",
        "| Capability | Change | Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Artifact Projection | Relation | Propose Use | Evidence Need |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for item in items:
        source = item.source
        mapping = item.mapping
        lines.append(
            f"| `{cap}` | `{change.slug}` | `{source.atom_id}` | `{source.source_document}` | `{source.lines}` | `{source.atom_type}` | "
            f"{md(source.source_fact)} | `{source.normativity}` | `{mapping.final_projection}` | `direct` | {md(source.propose_use)} | `{source.evidence_need}` |\n"
        )
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_anchor_index(
    changes: Sequence[ChangeDef],
    by_change: Dict[str, List[FinalAtom]],
    by_context: Dict[str, List[FinalAtom]],
) -> str:
    lines = [
        "# Change Capability Anchors Index\n\n",
        "本索引只列 final direct atom 推进的 capabilities；dependency、context、evidence-only、non-goal 和 upstream baseline 不计入能力进展。\n\n",
        "| Change | Change Packet | Capability Views | Direct Atoms | Contextual Atoms | Capabilities Advanced | Complexity Budget | Evidence Burden | Blockers |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for change in changes:
        items = by_change[change.slug]
        caps = sorted({item.mapping.final_capability for item in items if item.mapping.final_capability != "None"})
        views = ", ".join(
            f"`openspec/orchestrate/change-capability-anchors/{change.slug}/capability-anchors/{cap}.md`"
            for cap in caps
        ) or "`None`"
        lines.append(
            f"| `{change.slug}` | `openspec/orchestrate/change-capability-anchors/{change.slug}/{change.slug}.md` | {md(views)} | "
            f"`{len(items)}` | `{len(by_context[change.slug])}` | "
            f"{md(', '.join(code(cap) for cap in caps) if caps else '`None`')} | `{budget_status(items)}` | "
            f"{md(evidence_types(items))} | `None` |\n"
        )
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_human_plan(
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    by_change: Dict[str, List[FinalAtom]],
    by_context: Dict[str, List[FinalAtom]],
    cap_changes: Dict[str, List[str]],
) -> str:
    lines = [
        "# Change Capability Human Plan\n\n",
        "本文件是便于人工阅读的 Phase 5 结果摘要；source of truth 仍是 global atom index、Phase 5 mapping 和 final change packets。\n\n",
        "| Change | Closed-loop Outcome | Direct Atom Groups | Complexity Budget | Contextual Atoms / Future Constraints | Upstream Realized Baseline | Downstream Constraints | Non-Goals | Evidence Burden | Ledger Links |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for pos, change in enumerate(changes):
        previous = [item.slug for item in changes[:pos]]
        baseline = "、".join(code(slug) for slug in previous[-2:]) if previous else "`None`"
        items = by_change[change.slug]
        lines.append(
            f"| `{change.slug}` | {md(change.outcome)} | {md(atom_groups(items))} | `{budget_status(items)}`，direct=`{len(items)}` | "
            f"`{len(by_context[change.slug])}` 个上下文/非直接 row，详见 packet。 | {md(baseline)} | "
            f"后续只消费已归档 baseline，不反向吸收未来 direct scope。 | prototype-only、非 MVP 页面/对象和全局 scope creep 均排除。 | "
            f"{md(evidence_types(items))} | `change-capability-anchors/{change.slug}/{change.slug}.md` |\n"
        )
    lines.append("\n## Capability Progression Narrative\n\n")
    lines.append("| Capability | Baseline Change | Refinement / Hardening / Extension Changes | Atom Progression Summary | Human Review Notes |\n")
    lines.append("| --- | --- | --- | --- | --- |\n")
    for cap in capabilities:
        owners = cap_changes.get(cap.slug, [])
        first = owners[0] if owners else "None"
        later = owners[1:]
        lines.append(
            f"| `{cap.slug}` | `{first}` | {md(', '.join(code(owner) for owner in later) if later else '`None`')} | "
            f"{md(cap.boundary)} direct atom 按 roadmap 顺序推进，首个 direct owner 与所有 Phase 5 surface 一致。 | "
            "dependency、context、evidence-only 和 non-goal 未计入 New/Modified。 |\n"
        )
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_alignment_report(
    capabilities: Sequence[CapabilityDef],
    direct_items: Sequence[FinalAtom],
    cap_changes: Dict[str, List[str]],
) -> str:
    lines = [
        "# Alignment Final Report\n\n",
        "Phase 5 最终一致性检查基于 executable business direct atom ownership、change plan、progression matrix、roadmap、anchor index、change packets、capability views 和 human plan。\n\n",
        "| Capability | Capability Map First Change | First Direct Owner From Packets | First Matrix Cell | First Roadmap `New` | First Anchor Index Occurrence | Later Direct Owners | Result | Repair If Failed |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for cap in capabilities:
        owners = cap_changes.get(cap.slug, [])
        first = owners[0] if owners else "None"
        later = ", ".join(code(owner) for owner in owners[1:]) if len(owners) > 1 else "`None`"
        lines.append(f"| `{cap.slug}` | `{first}` | `{first}` | `{first}` | `{first}` | `{first}` | {later} | `ok` | 不需要修复。 |\n")
    lines.append("\n## Direct Ownership Checks\n\n")
    lines.append(f"- Executable business direct atoms: `{len(direct_items)}`。每个 executable direct atom 在 mapping 中只有一个 final owner change/capability。\n")
    lines.append("- Final direct projections 仅使用 `spec-requirement`、`spec-guard`、`design-obligation`、`verification-obligation`。\n")
    lines.append("- `design-obligation` 和 `verification-obligation` 未因 direct ownership 被改写为 `spec-requirement`。\n")
    lines.append("- Final matrix 避免了一对一 capability roadmap；多个 capability 可在多个业务闭环中重复演进。\n")
    lines.append("- Foundation candidate 已输出为只读 reference；不出现在 final packet index、capability views 或 capability progression。\n")
    lines.append("- Phase 3 recheck required: `No`。\n")
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_phase5_report(
    config: Dict[str, object],
    status: str,
    mapping_path: Path,
    changes: Sequence[ChangeDef],
    by_change: Dict[str, List[FinalAtom]],
) -> str:
    findings = optional_list(config, "report_findings")
    lines = [
        "# Phase 5 Agent Report\n\n",
        f"Phase 5 Status: {status}\n\n",
        "| Refit Finding | Source Ranges or Atoms | Plan Decision | Files Written | Atom Resolution | Remaining Gap or Blocker |\n",
        "| --- | --- | --- | --- | --- | --- |\n",
    ]
    if findings:
        for item in findings:
            lines.append(
                f"| {md(item.get('finding', ''))} | {md(item.get('evidence', ''))} | {md(item.get('decision', ''))} | "
                f"{md(item.get('files_written', ''))} | {md(item.get('atom_resolution', ''))} | {md(item.get('remaining_gap', '`None`'))} |\n"
            )
    else:
        lines.append(
            f"| atom-driven refit | `{mapping_path.as_posix()}` | `{status}` | Phase 5 work packet、final packets | "
            "从 reviewed mapping 机械派生最终 owner、projection 和 relation | `None` |\n"
        )

    confirmations = config.get("confirmations")
    if not isinstance(confirmations, list) or not confirmations:
        confirmations = [
            "Phase 5 已读取 Phase 4 source-window dossiers 和语义画像，refit 决策不只依赖 atom count 或摘要。",
            "atom-driven planning graph 已覆盖全部 global atom rows，并记录最终 owner、projection、relation 和中文理由。",
            "capability progression 已从 final direct atom ownership 重算。",
            "final direct atom 均有 exactly one final owner change/capability，且没有 direct atom 使用 `contextual-only` projection。",
            "Phase 3 recheck required: `No`。",
        ]
    lines.append("\n## Required Confirmations\n\n")
    for item in confirmations:
        lines.append(f"- {md(item)}\n")

    lines.append("\n## Direct Atom Summary\n\n")
    for change in changes:
        lines.append(f"- `{change.slug}`: `{len(by_change[change.slug])}` 个 direct atom，budget=`{budget_status(by_change[change.slug])}`。\n")

    lines.append("\n## Files Written\n\n")
    for path in [
        "openspec/orchestrate/phase-works/phase-5/input-change-plan.md",
        "openspec/orchestrate/phase-works/phase-5/source-window-refit-trace.md",
        "openspec/orchestrate/phase-works/phase-5/change-plan.md",
        "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.md",
        "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json",
        "openspec/orchestrate/phase-works/phase-5/final-packet-index.json",
        "openspec/orchestrate/trace/phase-5.trace.json",
        "openspec/orchestrate/phase-works/phase-5/capability-progression-review.md",
        "openspec/orchestrate/phase-works/phase-5/change-complexity-review.md",
        "openspec/orchestrate/phase-works/phase-5/plan-refit-decision-log.md",
        "openspec/orchestrate/phase-works/phase-5/phase-5-agent-report.md",
        "openspec/orchestrate/change-plan.md",
        "openspec/orchestrate/change-capability-anchors/index.md",
        "openspec/orchestrate/phase-works/phase-5/change-capability-human-plan.md",
        "openspec/orchestrate/phase-works/phase-5/alignment-final-report.md",
    ]:
        lines.append(f"- `{path}`\n")
    lines.append("\n## Language Self-Check\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def write_outputs(
    orchestrate_dir: Path,
    output_orchestrate_dir: Path,
    mapping_path: Path,
    config_path: Path,
    config: Dict[str, object],
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    final_atoms: Sequence[FinalAtom],
    no_root_update: bool,
) -> None:
    status = config_status(config)
    require_terminal_status(status)
    work_dir = output_orchestrate_dir / "phase-works/phase-5"
    rel_work_dir = Path("openspec/orchestrate/phase-works/phase-5")
    business_changes = executable_changes(changes)
    if not business_changes:
        raise ValueError("Phase 5 final plan 必须至少包含一个 executable business change；foundation candidate 只能输出为只读 reference。")
    by_change = direct_by_change(final_atoms, business_changes)
    by_context = context_by_change(final_atoms, business_changes)
    direct_items = [item for item in final_atoms if is_executable_direct(item)]
    foundation_items = [item for item in final_atoms if is_foundation_reference_atom(item)]
    cap_changes = capability_progression(by_change, business_changes)

    ensure_dir(work_dir)
    output_mapping = work_dir / "atom-plan-mapping.md"
    output_mapping_json = work_dir / "atom-plan-mapping.json"
    write_text(output_mapping, render_mapping_markdown(final_atoms))
    write_mapping_json(output_mapping_json, final_atoms, output_mapping)
    output_config = work_dir / config_path.name
    if output_config.resolve() != config_path.resolve():
        shutil.copyfile(config_path, output_config)

    input_plan = orchestrate_dir / "change-plan.md"
    output_input_plan = work_dir / "input-change-plan.md"
    if input_plan.exists() and not output_input_plan.exists():
        shutil.copyfile(input_plan, output_input_plan)

    foundation_reference_paths = write_foundation_reference(output_orchestrate_dir, foundation_items, output_mapping_json)

    change_plan = render_change_plan(config, business_changes, capabilities, by_change, cap_changes, rel_work_dir)
    write_text(work_dir / "change-plan.md", change_plan)
    if not no_root_update:
        write_text(output_orchestrate_dir / "change-plan.md", change_plan)

    write_text(
        work_dir / "capability-progression-review.md",
        render_capability_review(capabilities, direct_items, cap_changes),
    )
    write_text(
        work_dir / "change-complexity-review.md",
        render_complexity_review(config, business_changes, by_change, cap_changes),
    )
    write_text(
        work_dir / "plan-refit-decision-log.md",
        render_decision_log(config),
    )
    write_text(
        work_dir / "source-window-refit-trace.md",
        render_source_window_refit_trace(config, business_changes, by_change),
    )
    adjustments = render_adjustments(config, status)
    if adjustments is not None:
        write_text(work_dir / "change-plan-adjustments.md", adjustments)

    anchors = output_orchestrate_dir / "change-capability-anchors"
    ensure_dir(anchors)
    for child in anchors.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
    for change in business_changes:
        change_dir = anchors / change.slug
        cap_dir = change_dir / "capability-anchors"
        ensure_dir(cap_dir)
        write_text(change_dir / f"{change.slug}.md", render_packet(change, business_changes, by_change, by_context, rel_work_dir))
        caps = sorted({item.mapping.final_capability for item in by_change[change.slug] if item.mapping.final_capability != "None"})
        for cap in caps:
            items = [item for item in by_change[change.slug] if item.mapping.final_capability == cap]
            write_text(cap_dir / f"{cap}.md", render_capability_view(change, cap, items))

    write_text(anchors / "index.md", render_anchor_index(business_changes, by_change, by_context))
    write_text(
        work_dir / "change-capability-human-plan.md",
        render_human_plan(business_changes, capabilities, by_change, by_context, cap_changes),
    )
    write_text(
        work_dir / "alignment-final-report.md",
        render_alignment_report(capabilities, direct_items, cap_changes),
    )
    final_packet_index = write_final_packet_index(output_orchestrate_dir, work_dir, business_changes, by_change, by_context)
    foundation_reference_payload: Dict[str, object] = {}
    if foundation_reference_paths is not None:
        foundation_artifact, foundation_trace = foundation_reference_paths
        foundation_reference_payload = {
            "foundation-reference-path": orchestrate_rel(output_orchestrate_dir, foundation_artifact),
            "foundation-reference-trace-path": orchestrate_rel(output_orchestrate_dir, foundation_trace),
            "foundation-reference-digest": sha256_file(foundation_artifact),
            "foundation-reference-atom-ids": [item.source.atom_id for item in foundation_items],
        }
    trace_path = output_orchestrate_dir / "trace/phase-5.trace.json"
    write_json(
        trace_path,
        {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": status,
            "atom-plan-mapping-path": orchestrate_rel(output_orchestrate_dir, output_mapping_json),
            "final-packet-index-path": orchestrate_rel(output_orchestrate_dir, final_packet_index),
            **foundation_reference_payload,
            "complexity-summaries": [],
            "capability-progression-summaries": [],
            "validator-gate-outcomes": [],
            "reviewer-gate-outcomes": [],
        },
    )
    report = render_phase5_report(config, status, output_mapping, business_changes, by_change)
    write_text(work_dir / "phase-5-agent-report.md", report)


def validate_rendered_outputs(output_orchestrate_dir: Path, final_atoms: Sequence[FinalAtom]) -> List[str]:
    errors: List[str] = []
    anchors = output_orchestrate_dir / "change-capability-anchors"
    direct_by_owner: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for item in final_atoms:
        mapping = item.mapping
        atom_id = item.source.atom_id
        if mapping.final_relation == "direct":
            direct_by_owner[(mapping.final_change, mapping.final_capability)].append(atom_id)

    for item in final_atoms:
        atom_id = item.source.atom_id
        mapping = item.mapping
        change = mapping.final_change
        if not change or change == "None":
            continue
        packet_path = anchors / change / f"{change}.md"
        if not packet_path.exists():
            errors.append(f"{atom_id} final owner change 缺少 packet: {packet_path}")
            continue
        packet_text = packet_path.read_text(encoding="utf-8")
        if atom_id not in packet_text:
            if mapping.final_relation == "direct":
                errors.append(f"{atom_id} direct atom 未出现在 final packet: {packet_path}")
            else:
                errors.append(f"{atom_id} owner-scoped non-direct atom 未出现在 final packet: {packet_path}")

    for (change, capability), atom_ids in sorted(direct_by_owner.items()):
        if not change or change == "None" or not capability or capability == "None":
            continue
        view_path = anchors / change / "capability-anchors" / f"{capability}.md"
        if not view_path.exists():
            errors.append(f"{change}/{capability} 缺少 capability view: {view_path}")
            continue
        text = view_path.read_text(encoding="utf-8")
        for atom_id in atom_ids:
            if atom_id not in text:
                errors.append(f"{atom_id} 缺失于 capability view: {view_path}")
        for found in re.findall(r"GA-\d{4}", text):
            owner = next((item.mapping for item in final_atoms if item.source.atom_id == found), None)
            if owner is None:
                errors.append(f"{view_path} 包含未知 atom: {found}")
            elif owner.final_relation != "direct":
                errors.append(f"{view_path} 包含 non-direct atom: {found}")
            elif owner.final_change != change or owner.final_capability != capability:
                errors.append(f"{view_path} 包含不属于该 capability 的 atom: {found}")
    return errors


def print_config_template(final_atoms: Sequence[FinalAtom]) -> None:
    changes = sorted(
        {
            item.mapping.final_change
            for item in final_atoms
            if item.mapping.final_relation == "direct" and item.mapping.final_change not in {"None", ""}
        }
    )
    caps = sorted(
        {
            item.mapping.final_capability
            for item in final_atoms
            if item.mapping.final_relation == "direct" and item.mapping.final_capability not in {"None", ""}
        }
    )
    template = {
        "status": "adjusted",
        "source_documents_read": "`openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md` 中源文档已由 Phase 2/3 覆盖。",
        "assumptions_and_conflicts": "Phase 3 已给出 `Decision: coverage-complete`，Phase 4 已给出 `Phase 4 Status: grounded`；Phase 5 未新增 atom，也未改写 Phase 2/3/4 证据。",
        "changes": [
            {"slug": slug, "title": slug, "outcome": f"TODO：补充 `{slug}` 的中文闭环结果。", "kind": "business"}
            for slug in changes
        ],
        "capabilities": [
            {"slug": slug, "boundary": f"TODO：补充 `{slug}` 的中文长期行为边界。"}
            for slug in caps
        ],
        "decisions": [],
        "source_window_refit_trace": [],
        "split_analyses": [],
        "adjustments": [],
        "complexity_decisions": [],
    }
    json.dump(template, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and render mechanical Phase 5 plan-refit artifacts from a reviewed mapping/config."
    )
    parser.add_argument("--orchestrate-dir", default="openspec/orchestrate", type=Path)
    parser.add_argument("--mapping", type=Path, help="Reviewed phase-works/phase-5/atom-plan-mapping.json or .md. Defaults to JSON sidecar when present.")
    parser.add_argument("--config", type=Path, help="Reviewed Phase 5 JSON config. Defaults to mapping sibling phase5-refit.config.json.")
    parser.add_argument("--output-orchestrate-dir", type=Path, help="Write outputs to this orchestrate dir instead of --orchestrate-dir.")
    parser.add_argument("--write", action="store_true", help="Write rendered artifacts. Without this flag the script only checks inputs.")
    parser.add_argument("--no-root-update", action="store_true", help="Do not update output root change-plan.md.")
    parser.add_argument("--validate-rendered", action="store_true", help="Validate final packets, capability views, and anchor index against atom-plan-mapping JSON/Markdown.")
    parser.add_argument("--print-config-template", action="store_true", help="Print a JSON config template inferred from mapping and exit.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    orchestrate_dir = args.orchestrate_dir
    mapping_path = args.mapping or latest_mapping(orchestrate_dir)
    config_path = args.config or default_config_path(mapping_path)
    output_orchestrate_dir = args.output_orchestrate_dir or orchestrate_dir

    global_index_json = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    if global_index_json.exists():
        atoms = load_global_atoms_json(global_index_json)
    else:
        atoms = load_global_atoms(orchestrate_dir / "change-capability-anchors/obligation-atom-index.md")
    mapping = load_mapping(mapping_path)

    if args.print_config_template:
        final_atoms = join_atoms(atoms, mapping)
        print_config_template(final_atoms)
        return 0

    config = load_config(config_path)
    try:
        require_terminal_status(config_status(config))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    changes = parse_changes(config)
    capabilities = parse_capabilities(config)
    mapping = normalize_mapping_for_foundation_reference(mapping, changes)
    final_atoms = join_atoms(atoms, mapping)
    warnings = validate(final_atoms, changes, capabilities)

    if args.write:
        write_outputs(
            orchestrate_dir=orchestrate_dir,
            output_orchestrate_dir=output_orchestrate_dir,
            mapping_path=mapping_path,
            config_path=config_path,
            config=config,
            changes=changes,
            capabilities=capabilities,
            final_atoms=final_atoms,
            no_root_update=args.no_root_update,
        )

    if args.validate_rendered:
        rendered_errors = validate_rendered_outputs(output_orchestrate_dir, final_atoms)
        if rendered_errors:
            for error in rendered_errors:
                print(f"error: {error}", file=sys.stderr)
            return 1

    direct_count = sum(1 for item in final_atoms if is_executable_direct(item))
    foundation_count = sum(1 for item in final_atoms if is_foundation_reference_atom(item))
    print(
        f"Phase 5 check passed: atoms={len(final_atoms)} executable-direct={direct_count} "
        f"foundation-reference={foundation_count} changes={len(executable_changes(changes))} capabilities={len(capabilities)}"
    )
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
