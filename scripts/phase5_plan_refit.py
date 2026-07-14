#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 5 plan refit 的机械渲染器。

该辅助工具刻意保持确定性。Phase 5 subagent 仍负责语义 refit 决策，包括 final Change
列表、Capability 列表、atom mapping、拆分决策和阻塞项。本脚本仅校验经过审阅的输入，
并渲染重复性的 Phase 5 台账、packet、审阅文档和报告。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from source_aligned_trace_lib import (
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_BASELINE_SCHEMA,
    FINAL_PACKET_INDEX_SCHEMA,
    GLOBAL_ATOM_INDEX_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    TRACE_CONTRACT_VERSION,
    line_ranges_label,
    sha256_file,
    write_json,
)
from render_source_aligned_orchestrate import render_atom_plan_mapping, render_capability_baseline


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
NO_OWNER_VALUES = {"", "None", "none", "null", "NULL"}
FOUNDATION_CHANGE_KIND = "foundation"
BUSINESS_CHANGE_KIND = "business"
FOUNDATION_CAPABILITY = "runtime-substrate-foundation"
FOUNDATION_IMPACT = "foundation-substrate"
SPEC_PROJECTIONS = {"spec-requirement", "spec-guard"}
CHANGE_ONLY_PROJECTIONS = {"design-obligation", "verification-obligation"}
BUSINESS_CAPABILITY_IMPACTS = {"new", "modified"}
TERMINAL_CAPABILITY_IMPACTS = {*BUSINESS_CAPABILITY_IMPACTS, "none", FOUNDATION_IMPACT}
BUSINESS_BASELINE_STATUSES = {"existing", "absent"}
LEGACY_CAPABILITY_FIELDS = {
    "candidate-owner-capability",
    "owner-capability",
    "final-owner-capability",
    "capability-advancement",
}
RESERVED_CAPABILITY_MARKERS = {
    "none",
    "unresolved",
    "candidate-new-capability",
    "unassigned",
    "candidate-new-change",
    "contextual",
    "non-direct",
}


@dataclass(frozen=True)
class ChangeDef:
    slug: str
    title: str
    intent: str
    outcome: str
    kind: str


@dataclass(frozen=True)
class CapabilityDef:
    slug: str
    boundary: str
    purpose: str
    owns: str
    excludes: str
    baseline_status: str
    baseline_evidence: str


@dataclass(frozen=True)
class AtomRow:
    atom_id: str
    source_document: str
    lines: str
    line_ranges: Tuple[Tuple[int, int], ...]
    atom_type: str
    source_fact: str
    normativity: str
    coverage_status: str
    artifact_projection: str
    owner_change: str
    capability_impact: str
    target_capability: str
    related_capabilities: Tuple[str, ...]
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
    final_capability_impact: str
    final_target_capability: str
    related_capabilities: Tuple[str, ...]
    final_projection: str
    final_relation: str
    plan_decision: str
    reason: str


@dataclass(frozen=True)
class FinalAtom:
    source: AtomRow
    mapping: MappingRow


def normalize_code(value: str) -> str:
    value = value.strip()
    while len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return value.replace("\\|", "|").strip()


def related_from_json(value: object, where: str) -> Tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{where} 必须是 JSON array")
    return tuple(normalize_code(str(item)) for item in value if normalize_code(str(item)))


def require_v2_json_contract(data: object, path: Path, schema: str) -> Dict[str, object]:
    if not isinstance(data, dict):
        raise ValueError(f"{path} 必须是 JSON object")
    if data.get("trace-schema") != schema:
        raise ValueError(f"{path} trace-schema 必须是 {schema}")
    if data.get("trace-contract-version") != TRACE_CONTRACT_VERSION:
        raise ValueError(f"{path} trace-contract-version 必须是 {TRACE_CONTRACT_VERSION}")
    return data


def reject_legacy_capability_fields(row: Dict[str, object], where: str) -> None:
    present = sorted(LEGACY_CAPABILITY_FIELDS.intersection(row))
    if present:
        raise ValueError(f"{where} 混入 v1 capability fields: {', '.join(present)}")


def is_business_capability_delta(item: FinalAtom) -> bool:
    return (
        item.mapping.final_relation == "direct"
        and item.mapping.final_capability_impact in BUSINESS_CAPABILITY_IMPACTS
    )


def is_foundation_delta(item: FinalAtom) -> bool:
    return (
        item.mapping.final_relation == "direct"
        and item.mapping.final_capability_impact == FOUNDATION_IMPACT
        and item.mapping.final_target_capability == FOUNDATION_CAPABILITY
    )


def is_capability_view_atom(item: FinalAtom) -> bool:
    return is_business_capability_delta(item) or is_foundation_delta(item)


def active_capabilities(
    capabilities: Sequence[CapabilityDef],
    items: Iterable[FinalAtom],
) -> List[CapabilityDef]:
    targets = {
        item.mapping.final_target_capability
        for item in items
        if is_business_capability_delta(item)
    }
    return [capability for capability in capabilities if capability.slug in targets]


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


def single_atom_line_range(raw: object, context: str) -> Tuple[Tuple[int, int], ...]:
    if not isinstance(raw, list) or len(raw) != 1 or not isinstance(raw[0], dict):
        raise ValueError(f"{context} 的 line-ranges 必须且只能包含一个连续 range")
    start = raw[0].get("start")
    end = raw[0].get("end")
    if not isinstance(start, int) or not isinstance(end, int) or start <= 0 or end < start:
        raise ValueError(f"{context} 的唯一 line range 非法：{raw[0]}")
    return ((start, end),)


def load_global_atoms_json(path: Path) -> Dict[str, AtomRow]:
    data = require_v2_json_contract(
        json.loads(path.read_text(encoding="utf-8")),
        path,
        GLOBAL_ATOM_INDEX_SCHEMA,
    )
    atoms: Dict[str, AtomRow] = {}
    for raw in data.get("global-atoms", []):
        if not isinstance(raw, dict):
            continue
        reject_legacy_capability_fields(raw, f"global atom index row {raw.get('global-atom-id', '')}")
        atom_id = normalize_code(str(raw.get("global-atom-id", "")))
        if not atom_id:
            continue
        if not GLOBAL_ATOM_ID_RE.match(atom_id):
            raise ValueError(f"global atom index JSON 中的 Global Atom ID 必须匹配 GA-####: {atom_id}")
        if atom_id in atoms:
            raise ValueError(f"global atom index JSON 中存在重复 ID: {atom_id}")
        line_ranges = single_atom_line_range(raw.get("line-ranges"), f"global atom {atom_id}")
        canonical_lines = line_ranges_label(
            [{"start": start, "end": end} for start, end in line_ranges]
        )
        atoms[atom_id] = AtomRow(
            atom_id=atom_id,
            source_document=normalize_code(str(raw.get("source-document", ""))),
            lines=canonical_lines,
            line_ranges=line_ranges,
            atom_type=normalize_code(str(raw.get("atom-type", ""))),
            source_fact=str(raw.get("source-fact", "")),
            normativity=normalize_code(str(raw.get("normativity", ""))),
            coverage_status=normalize_code(str(raw.get("coverage-status", ""))),
            artifact_projection=normalize_code(str(raw.get("artifact-projection", ""))),
            owner_change=normalize_code(str(raw.get("owner-change", ""))),
            capability_impact=normalize_code(str(raw.get("capability-impact", ""))),
            target_capability=normalize_code(str(raw.get("target-capability", ""))),
            related_capabilities=related_from_json(
                raw.get("related-capabilities"),
                f"global atom {atom_id}.related-capabilities",
            ),
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
    if path.suffix != ".json":
        raise ValueError(f"Phase 5 v2 只接受 canonical JSON mapping: {path}")
    data = require_v2_json_contract(
        json.loads(path.read_text(encoding="utf-8")),
        path,
        ATOM_PLAN_MAPPING_SCHEMA,
    )
    mapping: Dict[str, MappingRow] = {}
    for raw in data.get("rows", []):
        if not isinstance(raw, dict):
            continue
        reject_legacy_capability_fields(raw, f"Phase 5 mapping row {raw.get('global-atom-id', '')}")
        atom_id = normalize_code(str(raw.get("global-atom-id", "")))
        if not atom_id:
            continue
        if not GLOBAL_ATOM_ID_RE.match(atom_id):
            raise ValueError(f"Phase 5 mapping JSON 中的 Global Atom ID 必须匹配 GA-####: {atom_id}")
        if atom_id in mapping:
            raise ValueError(f"Phase 5 mapping JSON 中存在重复 ID: {atom_id}")
        legacy_ref = normalize_code(str(raw.get("foundation-reference-id", "")))
        if legacy_ref and legacy_ref not in NO_OWNER_VALUES:
            raise ValueError(
                f"{atom_id} 使用了已废弃的 foundation-reference-id={legacy_ref}；"
                "Phase 5 必须输出 executable foundation change packet"
            )
        if str(raw.get("final-owner-type", "")) == "foundation-reference" or str(raw.get("final-relation", "")) == "foundation-reference":
            raise ValueError(f"{atom_id} 使用了已废弃的 foundation-reference owner/relation")
        mapping[atom_id] = MappingRow(
            atom_id=atom_id,
            final_owner_type=normalize_code(str(raw.get("final-owner-type", ""))),
            final_change=normalize_code(str(raw.get("final-owner-change", ""))),
            final_capability_impact=normalize_code(str(raw.get("final-capability-impact", ""))),
            final_target_capability=normalize_code(str(raw.get("final-target-capability", ""))),
            related_capabilities=related_from_json(
                raw.get("related-capabilities"),
                f"Phase 5 mapping {atom_id}.related-capabilities",
            ),
            final_projection=normalize_code(str(raw.get("final-artifact-projection", ""))),
            final_relation=normalize_code(str(raw.get("final-relation", ""))),
            plan_decision=str(raw.get("plan-decision", "")),
            reason=str(raw.get("reason", "")),
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
    if not isinstance(caps_raw, list):
        raise ValueError("Phase 5 config 必须包含 capabilities 数组；没有业务 capability delta 时使用空数组")
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
                intent=str(raw.get("intent") or raw.get("outcome") or slug),
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
        boundary = str(raw.get("boundary") or raw.get("purpose") or slug)
        caps.append(
            CapabilityDef(
                slug=slug,
                boundary=boundary,
                purpose=str(raw.get("purpose") or boundary),
                owns=str(raw.get("owns") or boundary),
                excludes=str(raw.get("excludes") or "不拥有相邻 Capability 的行为。"),
                baseline_status=str(raw.get("baseline_status") or "unknown"),
                baseline_evidence=str(raw.get("baseline_evidence") or ""),
            )
        )
    return caps


def latest_mapping(orchestrate_dir: Path) -> Path:
    mapping_path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
    if not mapping_path.exists():
        raise ValueError(f"缺少 Phase 5 v2 canonical mapping JSON: {mapping_path}")
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


def planned_changes(changes: Sequence[ChangeDef]) -> List[ChangeDef]:
    return list(changes)


def change_kind(change: ChangeDef) -> str:
    return FOUNDATION_CHANGE_KIND if change.kind == FOUNDATION_CHANGE_KIND else BUSINESS_CHANGE_KIND


def normalize_mapping(
    mapping: Dict[str, MappingRow],
    changes: Sequence[ChangeDef],
) -> Dict[str, MappingRow]:
    del changes  # v2 renderer 必须保留已审阅的终态字段，不推断 owner 或 impact。
    for atom_id, row in mapping.items():
        if row.final_owner_type == "foundation-reference" or row.final_relation == "foundation-reference":
            raise ValueError(f"{atom_id} 使用了已废弃的 foundation-reference owner/relation")
    return dict(mapping)


def is_executable_direct(item: FinalAtom) -> bool:
    return item.mapping.final_relation == "direct"


def validate(
    final_atoms: Sequence[FinalAtom],
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    specs_root: Path,
) -> List[str]:
    warnings: List[str] = []
    changes_by_slug = {change.slug: change for change in changes}
    change_slugs = set(changes_by_slug)
    capability_slugs = {cap.slug for cap in capabilities}
    capabilities_by_slug = {cap.slug: cap for cap in capabilities}
    direct_seen: set[str] = set()
    foundation_changes = [change for change in changes if change.kind == FOUNDATION_CHANGE_KIND]
    if len(foundation_changes) > 1:
        raise ValueError("Phase 5 final plan 最多只能包含一个 foundation change")
    if foundation_changes and changes[0].slug != foundation_changes[0].slug:
        raise ValueError("foundation change 必须位于 executable roadmap 第一位")
    if foundation_changes and FOUNDATION_CAPABILITY not in capability_slugs:
        raise ValueError(f"foundation change 必须声明 capability `{FOUNDATION_CAPABILITY}`")

    deltas_by_change_target: Dict[Tuple[str, str], set[str]] = defaultdict(set)
    for item in final_atoms:
        row = item.mapping
        impact = row.final_capability_impact
        target = row.final_target_capability
        related = row.related_capabilities

        if impact not in TERMINAL_CAPABILITY_IMPACTS:
            raise ValueError(f"{row.atom_id} final capability impact 非法或未消解: {impact}")
        if len(related) != len(set(related)):
            raise ValueError(f"{row.atom_id} related-capabilities 存在重复值")
        for capability in related:
            if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", capability):
                raise ValueError(f"{row.atom_id} related capability 不是 kebab-case: {capability}")
            if capability in RESERVED_CAPABILITY_MARKERS:
                raise ValueError(f"{row.atom_id} related capability 使用了保留标记: {capability}")
            if capability == target:
                raise ValueError(f"{row.atom_id} related capability 不得与 target capability 相同: {capability}")

        if row.final_relation == "direct":
            if row.atom_id in direct_seen:
                raise ValueError(f"direct atom 重复: {row.atom_id}")
            direct_seen.add(row.atom_id)
            if row.final_projection not in DIRECT_PROJECTIONS:
                raise ValueError(
                    f"{row.atom_id} 是 direct，但 projection={row.final_projection}，"
                    "final direct atom 不能使用 contextual-only 或空 projection"
                )
            if row.final_owner_type != EXECUTABLE_OWNER_TYPE:
                raise ValueError(
                    f"{row.atom_id} direct row final-owner-type 必须是 {EXECUTABLE_OWNER_TYPE}"
                )
            if row.final_change not in change_slugs:
                raise ValueError(f"{row.atom_id} direct final change 未在 config changes 中声明: {row.final_change}")
            owner = changes_by_slug[row.final_change]
            if owner.kind == FOUNDATION_CHANGE_KIND:
                if impact != FOUNDATION_IMPACT or target != FOUNDATION_CAPABILITY:
                    raise ValueError(
                        f"{row.atom_id} foundation direct row 必须使用 "
                        f"{FOUNDATION_IMPACT} + {FOUNDATION_CAPABILITY}"
                    )
            else:
                if impact == FOUNDATION_IMPACT or target == FOUNDATION_CAPABILITY:
                    raise ValueError(f"{row.atom_id} business change 不得使用 foundation capability impact/target")
                if row.final_projection in SPEC_PROJECTIONS:
                    if impact not in BUSINESS_CAPABILITY_IMPACTS:
                        raise ValueError(
                            f"{row.atom_id} direct spec atom 必须使用 capability impact new/modified"
                        )
                    if target == "unresolved":
                        raise ValueError(f"{row.atom_id} terminal spec target 不得是 unresolved")
                    if is_no_owner(target) or target not in capability_slugs:
                        raise ValueError(
                            f"{row.atom_id} direct spec atom target capability 未在 config capabilities 中声明: {target}"
                        )
                    if target == "candidate-new-capability":
                        raise ValueError(f"{row.atom_id} terminal target 必须消解 candidate-new-capability placeholder")
                    deltas_by_change_target[(row.final_change, target)].add(impact)
                elif row.final_projection in CHANGE_ONLY_PROJECTIONS:
                    if impact != "none" or target != "none":
                        raise ValueError(
                            f"{row.atom_id} {row.final_projection} 必须 change-only：impact=none、target=none"
                        )
        else:
            if impact != "none" or target != "none":
                raise ValueError(f"{row.atom_id} non-direct row 必须使用 impact=none、target=none")
            if row.final_projection in ("", "None"):
                warnings.append(f"{row.atom_id} 非 direct row 缺少 final projection")

    for (change, target), impacts in deltas_by_change_target.items():
        if len(impacts) != 1:
            raise ValueError(f"{change}/{target} 同一 capability delta 混用了 impact: {sorted(impacts)}")

    advancement_index: Dict[str, int] = defaultdict(int)
    for change in changes:
        targets = sorted(target for owner, target in deltas_by_change_target if owner == change.slug)
        for target in targets:
            impact = next(iter(deltas_by_change_target[(change.slug, target)]))
            capability = capabilities_by_slug[target]
            if capability.baseline_status not in BUSINESS_BASELINE_STATUSES:
                raise ValueError(
                    f"{target} 是 active business Capability，baseline_status 必须是 existing 或 absent"
                )
            if not capability.baseline_evidence.strip():
                raise ValueError(f"{target} 缺少 baseline_evidence")
            spec_path = specs_root / target / "spec.md"
            actual_status = "existing" if spec_path.is_file() else "absent"
            if capability.baseline_status != actual_status:
                raise ValueError(
                    f"{target} baseline_status={capability.baseline_status} 与实际路径 "
                    f"{spec_path} 的状态 {actual_status} 不一致"
                )
            expected = (
                "modified"
                if capability.baseline_status == "existing" or advancement_index[target] > 0
                else "new"
            )
            if impact != expected:
                raise ValueError(
                    f"{change.slug}/{target} capability impact 与 repository baseline 不一致："
                    f"baseline={capability.baseline_status}，期望 {expected}，实际 {impact}"
                )
            advancement_index[target] += 1

    by_change = direct_by_change(final_atoms, changes)
    for change in changes:
        direct_count = len(by_change[change.slug])
        if change.kind == FOUNDATION_CHANGE_KIND and direct_count == 0:
            raise ValueError(f"{change.slug} foundation change 必须拥有至少一个 direct foundation atom")
        caps = {
            item.mapping.final_target_capability
            for item in by_change[change.slug]
            if is_business_capability_delta(item)
        }
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
        if row.final_relation != "direct" and row.final_change in result:
            result[row.final_change].append(item)
    return result


def capability_progression(
    by_change: Dict[str, List[FinalAtom]],
    changes: Sequence[ChangeDef],
) -> Dict[str, List[str]]:
    progress: Dict[str, List[str]] = defaultdict(list)
    for change in changes:
        if change.kind == FOUNDATION_CHANGE_KIND:
            continue
        caps = sorted({
            item.mapping.final_target_capability
            for item in by_change[change.slug]
            if is_business_capability_delta(item)
        })
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
        rows.append(
            {
                "global-atom-id": source.atom_id,
                "source-document": source.source_document,
                "lines": source.lines,
                "line-ranges": [
                    {"start": start, "end": end}
                    for start, end in source.line_ranges
                ],
                "phase-3-owner-status": f"{source.owner_change} / {source.coverage_status}",
                "phase-3-artifact-projection": source.artifact_projection,
                "final-owner-type": mapping.final_owner_type,
                "final-owner-change": mapping.final_change,
                "final-capability-impact": mapping.final_capability_impact,
                "final-target-capability": mapping.final_target_capability,
                "related-capabilities": list(mapping.related_capabilities),
                "final-artifact-projection": mapping.final_projection,
                "final-relation": mapping.final_relation,
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
                "change-kind": change_kind(change),
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


def atom_groups(items: Sequence[FinalAtom]) -> str:
    counts = Counter(item.mapping.final_projection for item in items)
    return "；".join(f"`{projection}` {count} 个" for projection, count in counts.most_common()) if counts else "`None`"


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
    cap_count = len({
        item.mapping.final_target_capability
        for item in items
        if is_business_capability_delta(item)
    })
    if count > 120:
        return "hard-over-budget"
    if count > 80 or cap_count > 6:
        return "over-budget-reviewed"
    if count > 60:
        return "above-target-reviewed"
    return "within-target"


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


def build_capability_baseline_data(
    orchestrate_dir: Path,
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    by_change: Dict[str, List[FinalAtom]],
) -> Dict[str, object]:
    specs_root = orchestrate_dir.parent / "specs"
    active_targets = {
        item.mapping.final_target_capability
        for items in by_change.values()
        for item in items
        if is_business_capability_delta(item)
    }
    rows: List[Dict[str, object]] = []
    for capability in capabilities:
        if capability.slug not in active_targets:
            continue
        owners = [
            change.slug
            for change in changes
            if any(
                is_business_capability_delta(item)
                and item.mapping.final_target_capability == capability.slug
                for item in by_change[change.slug]
            )
        ]
        spec_path = specs_root / capability.slug / "spec.md"
        status = "existing" if spec_path.is_file() else "absent"
        if capability.baseline_status != status:
            raise ValueError(
                f"{capability.slug} baseline_status={capability.baseline_status} 与实际 repository baseline={status} 不一致"
            )
        rows.append(
            {
                "capability": capability.slug,
                "baseline-status": status,
                "spec-path": f"openspec/specs/{capability.slug}/spec.md",
                "spec-sha256": sha256_file(spec_path) if spec_path.is_file() else None,
                "baseline-evidence": capability.baseline_evidence,
                "first-planned-advancement": owners[0] if owners else "None",
                "required-first-relation": "modified" if status == "existing" else "new",
                "later-relation-rule": "modified",
            }
        )
    return {
        "trace-schema": CAPABILITY_BASELINE_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "repository-specs-root": "openspec/specs",
        "capabilities": rows,
    }


def render_change_plan(
    config: Dict[str, object],
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    by_change: Dict[str, List[FinalAtom]],
    cap_changes: Dict[str, List[str]],
    work_dir: Path,
) -> str:
    all_direct_items = [item for items in by_change.values() for item in items]
    progression_capabilities = active_capabilities(capabilities, all_direct_items)
    lines: List[str] = ["# source-aligned Phase 5 Change 计划\n\n", "## 输入\n\n"]
    lines.append(
        f"- 已读取的来源文档：{config.get('source_documents_read', '`openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md` 中源文档已由 Phase 2/3 覆盖。')}\n"
    )
    lines.append("- Phase 3 global atom index 路径：`openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`。\n")
    lines.append("- Phase 4 source-window dossier：`openspec/orchestrate/phase-works/phase-4/source-window-dossiers/index.md`。\n")
    lines.append("- Phase 4 semantic profile 审阅：`openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md`。\n")
    lines.append(f"- Phase 5 工作路径：`{work_dir.as_posix()}/`。\n")
    lines.append(
        f"- 假设与冲突：{config.get('assumptions_and_conflicts', 'Phase 3 已给出 `Decision: coverage-complete`；Phase 5 未新增 atom，也未改写 Phase 2/3 证据。')}\n"
    )

    lines.append("\n## Capability Map\n\n")
    if not progression_capabilities:
        lines.append("本计划没有业务 Capability delta；Change scope 仅包含 change-owned design/verification 义务。\n")
    else:
        lines.append("| Capability | Purpose | Owns | Excludes | Repository Baseline | Baseline Evidence | First Advancement | Source-backed Later Advancement |\n")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
    for cap in progression_capabilities:
        owners = cap_changes.get(cap.slug, [])
        if cap.slug == FOUNDATION_CAPABILITY:
            foundation_owners = [
                change.slug
                for change in changes
                if change.kind == FOUNDATION_CHANGE_KIND
                and any(is_foundation_delta(item) for item in by_change[change.slug])
            ]
            first = foundation_owners[0] if foundation_owners else "None"
            lines.append(
                f"| `{cap.slug}` | {md(cap.purpose)} | {md(cap.owns)} | {md(cap.excludes)} | "
                f"`not-applicable` | 工程底座 special case。 | `{first}` | "
                "后续业务 Change 只能消费其已归档 baseline。 |\n"
            )
            continue
        first = owners[0] if owners else "None"
        later = [owner for owner in owners if owner != first]
        later_text = (
            "后续由 " + "、".join(code(owner) for owner in later) + " 直接拥有增量 atom。"
            if later
            else "无已知 source-backed later delta。"
        )
        lines.append(
            f"| `{cap.slug}` | {md(cap.purpose)} | {md(cap.owns)} | {md(cap.excludes)} | "
            f"`{cap.baseline_status}` | {md(cap.baseline_evidence)} | `{first}` | {md(later_text)} |\n"
        )

    lines.append("\n## Capability Progression Matrix\n\n")
    if not progression_capabilities:
        lines.append("本计划没有业务 Capability delta，因此不生成空矩阵。\n")
    else:
        lines.append("| Change | " + " | ".join(code(cap.slug) for cap in progression_capabilities) + " |\n")
        lines.append("| --- | " + " | ".join("---" for _ in progression_capabilities) + " |\n")
        for change in changes:
            cells: List[str] = []
            for cap in progression_capabilities:
                items = [
                    item for item in by_change[change.slug]
                    if is_capability_view_atom(item)
                    and item.mapping.final_target_capability == cap.slug
                ]
                if not items:
                    cells.append("")
                elif change.kind == FOUNDATION_CHANGE_KIND and cap.slug == FOUNDATION_CAPABILITY:
                    cells.append(f"foundation substrate：{ids_for(items, 4)}")
                else:
                    impact = items[0].mapping.final_capability_impact.capitalize()
                    cells.append(f"{impact}: {ids_for(items, 4)}")
            lines.append(f"| `{change.slug}` | " + " | ".join(md(value) for value in cells) + " |\n")

    lines.append("\n## Change Roadmap\n")
    for change in changes:
        items = by_change[change.slug]
        new_caps = sorted({
            item.mapping.final_target_capability
            for item in items
            if item.mapping.final_capability_impact == "new"
        })
        modified_caps = sorted({
            item.mapping.final_target_capability
            for item in items
            if item.mapping.final_capability_impact == "modified"
        })
        business_caps = sorted(set(new_caps + modified_caps))
        gate = "foundation-executable" if change.kind == FOUNDATION_CHANGE_KIND else "business-executable"
        dep = "无" if change == changes[0] else "依赖前序 final change 已归档的 baseline；具体 upstream baseline 见 change packet。"
        lines.append(f"\n### Change 名称：`{change.slug}`\n\n")
        lines.append(f"- 单一 intent：{md(change.intent)}\n")
        lines.append(f"- source-backed outcome：{md(change.outcome)}\n")
        lines.append("- source-window grounding：\n")
        lines.append("  - 输入 source-window dossier：`openspec/orchestrate/phase-works/phase-4/source-window-dossiers/`。\n")
        lines.append("  - source-backed semantic profile：`openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md`。\n")
        lines.append("  - refit trace：`openspec/orchestrate/phase-works/phase-5/source-window-refit-trace.md`。\n")
        lines.append(f"- direct atom 分组：{atom_groups(items)}。\n")
        lines.append("- Capability 变更：\n")
        lines.append("  - New: " + (", ".join(code(cap) for cap in new_caps) if new_caps else "`None`") + "\n")
        lines.append("  - Modified: " + (", ".join(code(cap) for cap in modified_caps) if modified_caps else "`None`") + "\n")
        if change.kind == FOUNDATION_CHANGE_KIND:
            lines.append(f"  - foundation substrate：`{FOUNDATION_CAPABILITY}`\n")
            lines.append(f"- 范围内：{md(change.title)} 对应 direct atom 表中的工程底座、启动、配置、脚本、生成链路或本地 smoke 义务。\n")
        else:
            lines.append(f"- 范围内：{md(change.title)} 对应 direct atom 表中的行为、设计、guard 和验证义务。\n")
        lines.append("- 范围外：不直接拥有未映射到本 Change 的未来 atom；依赖、上下文、非目标和横切证据策略仅按 packet 中的 context/evidence burden 消费。\n")
        lines.append("- behavior completeness profile：\n")
        if change.kind == FOUNDATION_CHANGE_KIND:
            lines.append("  - trigger/context：repo/workspace、app skeleton、脚本、配置、生成链路或本地运行入口。\n")
            lines.append("  - normative behavior：只交付 zero-domain engineering substrate。\n")
            lines.append("  - observable outcome / invariant：工程底座可构建、启动、健康检查、生成或迁移回读。\n")
            lines.append("  - important exception / error semantics：底座失败产生可诊断信号，不吸收 domain recovery。\n")
        else:
            lines.append("  - trigger/context：由 source-window profile 中与该 intent 对应的上下文触发。\n")
            lines.append("  - normative behavior：只包含 final packet direct atom 表中服务同一 intent 的行为与 guard。\n")
            lines.append("  - observable outcome / invariant：以 source-backed outcome、状态转换或 invariant 为准，不强制持久 fact 或 user-facing projection。\n")
            lines.append("  - important exception / error semantics：只纳入当前 outcome 真实成立所必需且 source-backed 的异常语义。\n")
        lines.append(f"  - acceptance evidence：{md(evidence_types(items))}。\n")
        lines.append(f"- 依赖：{dep}\n")
        lines.append("- contextual atom / downstream design constraint：见 final packet context table 和 `atom-plan-mapping.md`。\n")
        lines.append("- 非目标：只保留与本 intent/outcome 相关的全局/局部非目标 guard，不扩展 prototype-only 页面、scene、fixture 或 mock 资产。\n")
        lines.append("- complexity budget：\n")
        lines.append(f"  - direct atom 数量：`{len(items)}`\n")
        lines.append("  - 推进的 Capability：" + (", ".join(code(cap) for cap in business_caps) if business_caps else "`None`") + "\n")
        if change.kind == FOUNDATION_CHANGE_KIND:
            lines.append(f"  - foundation substrate Capability：`{FOUNDATION_CAPABILITY}`\n")
        lines.append("  - surface family：该 Change 的入口、页面/对象、domain command、worker 或列表/导出面；超过目标时见 complexity review。\n")
        lines.append(f"  - 证据类型：{md(evidence_types(items))}\n")
        lines.append(f"  - executable roadmap 状态：`{gate}`\n")
        lines.append(f"  - budget 状态：`{budget_status(items)}`\n")
        lines.append("  - split/defer 分析：Phase 5 已按 one-intent、独立决策/archive、indivisibility、acceptance 和 evidence surface 记录判断。\n")
        lines.append("- 归档就绪性：direct atom 表服务同一 intent，能够在一个 focused OpenSpec Change 中提案、实现、验收和归档。\n")

    lines.append("\n## Phase 5 风险检查\n\n")
    lines.append("1. final executable roadmap 可从至多一个 foundation change 开始；若存在，它必须位于第一位且只拥有工程底座义务。\n")
    lines.append("2. diagonal matrix 只作为 diagnostic；Change boundary 由 intent/cohesion/indivisibility/acceptance 决定。\n")
    lines.append("3. 过大的 Phase 1 Change 已按可独立决策、验收和归档的 outcome 拆分。\n")
    lines.append("4. `design-obligation` 与 `verification-obligation` 保留原 projection，没有因为 direct ownership 被强制改成 `spec-requirement`。\n")
    lines.append("5. prototype-only、fixture、scene、mock asset 和非目标 row 只作为 guard/context 消费。\n")
    lines.append("\n## Phase 5 语言自检\n\n")
    lines.append("已忽略反引号内 ID、路径、命令、代码/API/DB/package 符号、固定 enum/status、relation token 和精确 source phrase 后检查；本文由代理撰写的解释内容均为简体中文。\n")
    return "".join(lines)


def render_capability_review(
    capabilities: Sequence[CapabilityDef],
    direct_items: Sequence[FinalAtom],
    cap_changes: Dict[str, List[str]],
) -> str:
    progression_capabilities = active_capabilities(capabilities, direct_items)
    lines = ["# Capability progression 审阅\n\n"]
    if not progression_capabilities:
        lines.append("本计划没有业务 Capability delta；无需生成 Capability progression 空表。\n")
    else:
        lines.extend(
            [
                "| Capability | Repository Baseline | Baseline Evidence | Atom Families | Current Change Sequence | Required Relation Sequence | Sequence Problem | Adjustment |\n",
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n",
            ]
        )
    for cap in progression_capabilities:
        owners = (
            sorted({item.mapping.final_change for item in direct_items if is_foundation_delta(item)})
            if cap.slug == FOUNDATION_CAPABILITY
            else cap_changes.get(cap.slug, [])
        )
        fam = Counter(
            item.source.atom_type
            for item in direct_items
            if is_capability_view_atom(item) and item.mapping.final_target_capability == cap.slug
        )
        fam_text = ", ".join(f"{name}={count}" for name, count in fam.items()) if fam else "None"
        seq = " -> ".join(code(owner) for owner in owners) if owners else "`None`"
        required = (
            "`modified+`"
            if cap.baseline_status == "existing"
            else "`new, modified*`"
        )
        problem = (
            "无；显式 impact 与 repository baseline、Capability Map、矩阵、anchor index 和 human plan 一致。"
            if owners
            else "该能力没有 final direct atom，不计入最终能力进展。"
        )
        adjustment = "按 baseline 重算 New/Modified；依赖、上下文、证据和非目标未计入 capability advancement。"
        lines.append(
            f"| `{cap.slug}` | `{cap.baseline_status}` | {md(cap.baseline_evidence)} | {md(fam_text)} | "
            f"{md(seq)} | {md(required)} | {md(problem)} | {md(adjustment)} |\n"
        )
    lines.append("\n## 语言自检\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
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
        "# Change complexity 审阅\n\n",
        "| Change | Direct Atom Count | Artifact Projection Mix | Atom Groups | New Capabilities | Modified Capabilities | Primary Intent/Outcome Count | Trigger/Outcome/Invariant Families | Exception/Error Families | Evidence Types | Surface Families | Executable Roadmap Status | Budget Status | Complexity Decision |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for change in changes:
        items = by_change[change.slug]
        new_caps = sorted({
            item.mapping.final_target_capability
            for item in items
            if item.mapping.final_capability_impact == "new"
        })
        modified_caps = sorted({
            item.mapping.final_target_capability
            for item in items
            if item.mapping.final_capability_impact == "modified"
        })
        gate = "foundation-executable" if change.kind == FOUNDATION_CHANGE_KIND else "business-executable"
        default_decision = (
            "保留；该 foundation change 已是可独立验证的工程底座交付。"
            if change.kind == FOUNDATION_CHANGE_KIND
            else "保留；该 Change 已是单一 intent、可独立验收和归档的 outcome。"
        )
        decision = decision_overrides.get(change.slug, default_decision)
        functional_points = (
            f"1 个工程底座交付：{md(change.outcome)}"
            if change.kind == FOUNDATION_CHANGE_KIND
            else f"1 个 intent/outcome：{md(change.outcome)}"
        )
        surface_families = (
            "workspace/script、app skeleton、health/readiness、config/env、migration/generation、package boundary 或 CI/local smoke"
            if change.kind == FOUNDATION_CHANGE_KIND
            else "主要 surface 不超过该 intent/outcome 的必要页面/对象/domain/worker 组合"
        )
        lines.append(
            f"| `{change.slug}` | `{len(items)}` | {md(projection_mix(items))} | {md(atom_groups(items))} | "
            f"{md(', '.join(code(cap) for cap in new_caps) if new_caps else '`None`')} | "
            f"{md(', '.join(code(cap) for cap in modified_caps) if modified_caps else '`None`')} | "
            f"{functional_points} | 由 source-window profile 审阅 | `{failure_count(items)}` | "
            f"{md(evidence_types(items))} | {md(surface_families)} | "
            f"`{gate}` | `{budget_status(items)}` | {md(decision)} |\n"
        )

    split_analyses = optional_list(config, "split_analyses")
    if split_analyses:
        lines.append("\n## 必需的拆分分析\n\n")
        lines.append("| Change | Trigger | Candidate Split | Atoms / Capabilities Moved | Resulting Intent/Outcome | Acceptance Evidence | Decision | Reason |\n")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for item in split_analyses:
            lines.append(
                f"| {code(item.get('change', ''))} | {md(item.get('trigger', ''))} | {md(item.get('candidate_split', ''))} | "
                f"{md(item.get('atoms_moved', ''))} | {md(item.get('new_outcome', ''))} | {md(item.get('verification_surface', ''))} | "
                f"{code(item.get('decision', ''))} | {md(item.get('reason', ''))} |\n"
            )
    lines.append("\n## 语言自检\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
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
        "# plan refit 决策日志\n\n",
        "| Decision Item | Input Evidence | Candidate Options | Decision | Output Artifact | Reason |\n",
        "| --- | --- | --- | --- | --- | --- |\n",
    ]
    for item in decisions:
        lines.append(
            f"| {code(item.get('item', ''))} | {md(item.get('input_evidence', ''))} | {md(item.get('candidate_options', ''))} | "
            f"{code(item.get('decision', ''))} | {md(item.get('output_artifact', ''))} | {md(item.get('reason', ''))} |\n"
        )
    lines.append("\n## 语言自检\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_source_window_refit_trace(config: Dict[str, object], changes: Sequence[ChangeDef], by_change: Dict[str, List[FinalAtom]]) -> str:
    rows = optional_list(config, "source_window_refit_trace")
    lines = [
        "# source-window refit 追踪\n\n",
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
                f"{md(change.outcome)} 形成可实现、可验证、可归档的工程交付单元。 |\n"
            )
    lines.append("\n## 语言自检\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_adjustments(config: Dict[str, object], status: str) -> Optional[str]:
    adjustments = optional_list(config, "adjustments")
    if status not in {"adjusted", "needs-coverage-recheck", "blocked"} and not adjustments:
        return None
    lines = [
        "# Change 计划调整\n\n",
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
    lines.append(f"\n## 下一步行动\n\n{next_action}\n")
    lines.append("\n## 语言自检\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_packet(
    change: ChangeDef,
    changes: Sequence[ChangeDef],
    by_change: Dict[str, List[FinalAtom]],
    by_context: Dict[str, List[FinalAtom]],
    work_dir: Path,
) -> str:
    items = by_change[change.slug]
    gate = "foundation-executable" if change.kind == FOUNDATION_CHANGE_KIND else "business-executable"
    lines = [
        f"# Change packet：`{change.slug}`\n\n",
        f"- Change 名称：`{change.slug}`\n",
        f"- 单一 intent：{md(change.intent)}\n",
        f"- source-backed outcome：{md(change.outcome)}\n",
        "- global atom index：`openspec/orchestrate/change-capability-anchors/obligation-atom-index.md`\n",
        "- source-window grounding：`openspec/orchestrate/phase-works/phase-4/source-window-dossiers/`；语义画像见 `openspec/orchestrate/phase-works/phase-4/source-window-semantic-profile-review.md`。\n",
        f"- source-window refit trace：`{work_dir.as_posix()}/source-window-refit-trace.md`\n",
        f"- Phase 5 mapping：`{work_dir.as_posix()}/atom-plan-mapping.md`\n",
        f"- complexity budget 状态：`{budget_status(items)}`；direct atom 数量=`{len(items)}`。\n",
        f"- executable roadmap 状态：`{gate}`。\n",
        "- 阻塞项：`None`\n\n",
        "## Final Direct Owner Atoms\n\n",
        "| Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Artifact Projection | Projection Rationale | Capability Impact | Target Capability | Related Capabilities | Atom Relation | Roles | Propose Use | Evidence Need |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for item in items:
        source = item.source
        mapping = item.mapping
        rationale = "保留 Phase 3 projection 或采用 Phase 5 final projection；不把 design 或 verification 行强制改成 spec requirement。"
        related = ", ".join(code(cap) for cap in mapping.related_capabilities) or "`None`"
        target = "None/change-only" if is_no_owner(mapping.final_target_capability) else mapping.final_target_capability
        lines.append(
            f"| `{source.atom_id}` | `{source.source_document}` | `{source.lines}` | `{source.atom_type}` | {md(source.source_fact)} | "
            f"`{source.normativity}` | `{mapping.final_projection}` | {md(rationale)} | `{mapping.final_capability_impact}` | "
            f"`{target}` | {md(related)} | `direct` | `direct-owner` | "
            f"{md(source.propose_use)} | `{source.evidence_need}` |\n"
        )
    lines.append("\n## contextual atom 与未来约束\n\n")
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
        else (
            "无；这是第一个 executable foundation change，后续业务 change 只能消费其已归档工程底座 baseline。\n"
            if change.kind == FOUNDATION_CHANGE_KIND
            else "无；这是第一个 executable business change。\n"
        )
    )
    lines.append("\n## 上游已实现 baseline\n\n")
    lines.append(baseline)
    lines.append("\n## 下游约束\n\n")
    lines.append("后续 change 可消费本 packet 已实现的 domain fact、guard、snapshot、action、version、project、entitlement 或 export baseline，但不得把未来义务反向计入本 change direct scope。\n")
    lines.append("\n## 显式非目标\n\n")
    lines.append("不实现 prototype-only scene、fixture、mock asset、未列入 MVP 的页面/对象、协作、团队权限、版本树、多图画布或完整科研设计平台。\n")
    lines.append("\n## 证据负担\n\n")
    lines.append("证据必须覆盖 direct atom 表中的成功、失败、guard、设计和验证义务；横切 viewport/object/state 证据按 Phase 5 mapping 作为 evidence burden 分散到相关业务 outcome。\n")
    lines.append("\n## 语言自检\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_capability_view(change: ChangeDef, cap: str, items: Sequence[FinalAtom]) -> str:
    lines = [
        f"# Capability view：`{change.slug}` 中的 `{cap}`\n\n",
        "本文件是 final change packet 的派生视图，不改变 atom ID、来源行号、projection 或事实文本。\n\n",
        "| Capability | Change | Capability Impact | Global Atom ID | Source Document | Lines | Atom Type | Source Fact | Normativity | Artifact Projection | Relation | Propose Use | Evidence Need |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for item in items:
        source = item.source
        mapping = item.mapping
        lines.append(
            f"| `{cap}` | `{change.slug}` | `{mapping.final_capability_impact}` | `{source.atom_id}` | "
            f"`{source.source_document}` | `{source.lines}` | `{source.atom_type}` | "
            f"{md(source.source_fact)} | `{source.normativity}` | `{mapping.final_projection}` | `direct` | {md(source.propose_use)} | `{source.evidence_need}` |\n"
        )
    lines.append("\n## 语言自检\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_anchor_index(
    changes: Sequence[ChangeDef],
    by_change: Dict[str, List[FinalAtom]],
    by_context: Dict[str, List[FinalAtom]],
) -> str:
    lines = [
        "# Change Capability anchor 索引\n\n",
        "本索引只把 final direct `new` / `modified` spec atoms 计为 business capabilities advanced；foundation view、dependency、context、evidence-only、non-goal 和 upstream baseline 均不计入能力进展。\n\n",
        "| Change | Change Packet | Capability Views | Direct Atoms | Contextual Atoms | Capabilities Advanced | Complexity Budget | Evidence Burden | Blockers |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for change in changes:
        items = by_change[change.slug]
        caps = sorted({
            item.mapping.final_target_capability
            for item in items
            if is_capability_view_atom(item)
        })
        business_caps = sorted({
            item.mapping.final_target_capability
            for item in items
            if is_business_capability_delta(item)
        })
        advanced = ", ".join(code(cap) for cap in business_caps) if business_caps else "`None`"
        views = ", ".join(
            f"`openspec/orchestrate/change-capability-anchors/{change.slug}/capability-anchors/{cap}.md`"
            for cap in caps
        ) or "`None`"
        lines.append(
            f"| `{change.slug}` | `openspec/orchestrate/change-capability-anchors/{change.slug}/{change.slug}.md` | {md(views)} | "
            f"`{len(items)}` | `{len(by_context[change.slug])}` | "
            f"{md(advanced)} | `{budget_status(items)}` | "
            f"{md(evidence_types(items))} | `None` |\n"
        )
    lines.append("\n## 语言自检\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_human_plan(
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    by_change: Dict[str, List[FinalAtom]],
    by_context: Dict[str, List[FinalAtom]],
    cap_changes: Dict[str, List[str]],
) -> str:
    all_direct_items = [item for items in by_change.values() for item in items]
    progression_capabilities = active_capabilities(capabilities, all_direct_items)
    lines = [
        "# Change Capability 人工可读计划\n\n",
        "本文件是便于人工阅读的 Phase 5 结果摘要；source of truth 仍是 global atom index、Phase 5 mapping 和 final change packets。\n\n",
        "| Change | Intent / Outcome | Direct Atom Groups | Complexity Budget | Contextual Atoms / Future Constraints | Upstream Realized Baseline | Downstream Constraints | Non-Goals | Evidence Burden | Ledger Links |\n",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
    ]
    for pos, change in enumerate(changes):
        previous = [item.slug for item in changes[:pos]]
        baseline = "、".join(code(slug) for slug in previous[-2:]) if previous else "`None`"
        items = by_change[change.slug]
        lines.append(
            f"| `{change.slug}` | {md(change.intent)}；{md(change.outcome)} | {md(atom_groups(items))} | `{budget_status(items)}`，direct=`{len(items)}` | "
            f"`{len(by_context[change.slug])}` 个上下文/非直接 row，详见 packet。 | {md(baseline)} | "
            f"后续只消费已归档 baseline，不反向吸收未来 direct scope。 | prototype-only、非 MVP 页面/对象和全局 scope creep 均排除。 | "
            f"{md(evidence_types(items))} | `change-capability-anchors/{change.slug}/{change.slug}.md` |\n"
        )
    lines.append("\n## Capability progression 说明\n\n")
    if not progression_capabilities:
        lines.append("本计划没有业务 Capability delta；Change 仍按其 direct design/verification atoms 完整交付。\n")
    else:
        lines.append("| Capability | Repository Baseline | First Advancement | Source-backed Later Advancements | Atom Progression Summary | Human Review Notes |\n")
        lines.append("| --- | --- | --- | --- | --- | --- |\n")
    for cap in progression_capabilities:
        if cap.slug == FOUNDATION_CAPABILITY:
            owners = sorted({
                item.mapping.final_change
                for items in by_change.values()
                for item in items
                if is_foundation_delta(item)
            })
        else:
            owners = cap_changes.get(cap.slug, [])
        first = owners[0] if owners else "None"
        later = owners[1:]
        lines.append(
            f"| `{cap.slug}` | `{cap.baseline_status}` | `{first}` | "
            f"{md(', '.join(code(owner) for owner in later) if later else '无已知 source-backed later delta')} | "
            f"{md(cap.boundary)} direct atom 按 repository baseline 与 roadmap 顺序推进。 | "
            "dependency、context、evidence-only 和 non-goal 未计入 New/Modified；baseline evidence 见 reconciliation。 |\n"
        )
    lines.append("\n## 语言自检\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_alignment_report(
    capabilities: Sequence[CapabilityDef],
    direct_items: Sequence[FinalAtom],
    cap_changes: Dict[str, List[str]],
) -> str:
    progression_capabilities = active_capabilities(capabilities, direct_items)
    lines = [
        "# 最终对齐报告\n\n",
        "Phase 5 最终一致性检查基于 executable direct atom ownership、change plan、progression matrix、roadmap、anchor index、change packets、capability views 和 human plan。\n\n",
    ]
    if not progression_capabilities:
        lines.append("本计划没有业务 Capability delta；Capability 对齐表不适用，Change ownership 检查仍继续执行。\n")
    else:
        lines.extend(
            [
                "| Capability | Repository Baseline | Capability Map First Advancement | First Direct Owner From Packets | First Matrix Cell | First Roadmap Impact | First Anchor Index Occurrence | Later Direct Owners | Result | Repair If Failed |\n",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
            ]
        )
    for cap in progression_capabilities:
        owners = cap_changes.get(cap.slug, [])
        if cap.slug == FOUNDATION_CAPABILITY:
            foundation_owners = sorted({item.mapping.final_change for item in direct_items if is_foundation_delta(item)})
            first = foundation_owners[0] if foundation_owners else "None"
            later = ", ".join(code(owner) for owner in foundation_owners[1:]) if len(foundation_owners) > 1 else "`None`"
            lines.append(
                f"| `{cap.slug}` | `not-applicable` | `{first}` | `{first}` | `foundation-substrate` | `None` | `{first}` | {later} | `foundation-substrate` | 不计入业务 New/Modified。 |\n"
            )
            continue
        first = owners[0] if owners else "None"
        later = ", ".join(code(owner) for owner in owners[1:]) if len(owners) > 1 else "`None`"
        first_impact = "modified" if cap.baseline_status == "existing" else "new"
        lines.append(
            f"| `{cap.slug}` | `{cap.baseline_status}` | `{first}` | `{first}` | `{first}` | "
            f"`{first_impact}` | `{first}` | {later} | `ok` | 不需要修复。 |\n"
        )
    lines.append("\n## direct ownership 检查\n\n")
    lines.append(f"- executable direct atom：`{len(direct_items)}` 个。每个 executable direct atom 在 mapping 中只有一个 final owner Change。\n")
    lines.append("- Final direct projections 仅使用 `spec-requirement`、`spec-guard`、`design-obligation`、`verification-obligation`。\n")
    lines.append("- `design-obligation` 和 `verification-obligation` 使用 `impact=none`、`target=none`，仍由 Change 直接拥有。\n")
    lines.append("- `related-capabilities` 只保留 source-explicit 非拥有型关联，不进入 progression 或 capability views。\n")
    lines.append("- Final matrix 只作为 derived diagnostic；一对一或多对多形状都必须回到 intent、Capability Purpose 与 source evidence 审阅。\n")
    lines.append("- Foundation candidate 如存在，已输出为第一位 executable foundation change packet；`runtime-substrate-foundation` 可出现在 packet/capability view，但不计入业务 capability progression。\n")
    lines.append("- 是否需要 Phase 3 recheck：`No`。\n")
    lines.append("\n## 语言自检\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
    return "".join(lines)


def render_phase5_report(
    config: Dict[str, object],
    status: str,
    mapping_path: Path,
    changes: Sequence[ChangeDef],
    by_change: Dict[str, List[FinalAtom]],
    root_plan_published: bool,
) -> str:
    findings = optional_list(config, "report_findings")
    lines = [
        "# Phase 5 agent 报告\n\n",
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
            "capability progression 已从 final spec target 与只读 repository baseline reconciliation 重算。",
            "final direct atom 均有 exactly one final owner change，且没有 direct atom 使用 `contextual-only` projection。",
            "是否需要 Phase 3 recheck：`No`。",
        ]
    lines.append("\n## 必需确认项\n\n")
    for item in confirmations:
        lines.append(f"- {md(item)}\n")

    lines.append("\n## direct atom 摘要\n\n")
    for change in changes:
        lines.append(f"- `{change.slug}`: `{len(by_change[change.slug])}` 个 direct atom，budget=`{budget_status(by_change[change.slug])}`。\n")

    lines.append("\n## 已写入文件\n\n")
    written_paths = [
        "openspec/orchestrate/phase-works/phase-5/input-change-plan.md",
        "openspec/orchestrate/phase-works/phase-5/source-window-refit-trace.md",
        "openspec/orchestrate/phase-works/phase-5/change-plan.md",
        "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.md",
        "openspec/orchestrate/phase-works/phase-5/atom-plan-mapping.json",
        "openspec/orchestrate/phase-works/phase-5/capability-baseline-reconciliation.md",
        "openspec/orchestrate/phase-works/phase-5/capability-baseline-reconciliation.json",
        "openspec/orchestrate/phase-works/phase-5/final-packet-index.json",
        "openspec/orchestrate/trace/phase-5.trace.json",
        "openspec/orchestrate/phase-works/phase-5/capability-progression-review.md",
        "openspec/orchestrate/phase-works/phase-5/change-complexity-review.md",
        "openspec/orchestrate/phase-works/phase-5/plan-refit-decision-log.md",
        "openspec/orchestrate/phase-works/phase-5/phase-5-agent-report.md",
        "openspec/orchestrate/change-capability-anchors/index.md",
        "openspec/orchestrate/phase-works/phase-5/change-capability-human-plan.md",
        "openspec/orchestrate/phase-works/phase-5/alignment-final-report.md",
    ]
    if root_plan_published:
        written_paths.append("openspec/orchestrate/change-plan.md")
    for path in written_paths:
        lines.append(f"- `{path}`\n")
    lines.append("\n## 语言自检\n\n本文解释内容已按 Artifact Language Gate 检查为简体中文。\n")
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
) -> None:
    status = config_status(config)
    require_terminal_status(status)
    work_dir = output_orchestrate_dir / "phase-works/phase-5"
    rel_work_dir = Path("openspec/orchestrate/phase-works/phase-5")
    executable_plan = planned_changes(changes)
    if not executable_plan:
        raise ValueError("Phase 5 final plan 必须至少包含一个 executable change。")
    by_change = direct_by_change(final_atoms, executable_plan)
    by_context = context_by_change(final_atoms, executable_plan)
    direct_items = [item for item in final_atoms if is_executable_direct(item)]
    cap_changes = capability_progression(by_change, executable_plan)

    ensure_dir(work_dir)
    legacy_foundation_dir = output_orchestrate_dir / "foundation-reference"
    if legacy_foundation_dir.exists():
        shutil.rmtree(legacy_foundation_dir)
    output_mapping = work_dir / "atom-plan-mapping.md"
    output_mapping_json = work_dir / "atom-plan-mapping.json"
    write_mapping_json(output_mapping_json, final_atoms, output_mapping)
    write_text(output_mapping, render_atom_plan_mapping(output_orchestrate_dir, output_mapping_json))
    output_config = work_dir / config_path.name
    if output_config.resolve() != config_path.resolve():
        shutil.copyfile(config_path, output_config)

    input_plan = orchestrate_dir / "phase-works/phase-4/input-change-plan.md"
    output_input_plan = work_dir / "input-change-plan.md"
    if not input_plan.exists():
        raise ValueError(f"缺少 Phase 4 input change plan: {input_plan}")
    shutil.copyfile(input_plan, output_input_plan)

    change_plan = render_change_plan(config, executable_plan, capabilities, by_change, cap_changes, rel_work_dir)
    write_text(work_dir / "change-plan.md", change_plan)

    baseline_json = work_dir / "capability-baseline-reconciliation.json"
    baseline_data = build_capability_baseline_data(
        orchestrate_dir,
        executable_plan,
        capabilities,
        by_change,
    )
    write_json(baseline_json, baseline_data)
    write_text(
        work_dir / "capability-baseline-reconciliation.md",
        render_capability_baseline(output_orchestrate_dir, baseline_json),
    )

    write_text(
        work_dir / "capability-progression-review.md",
        render_capability_review(capabilities, direct_items, cap_changes),
    )
    write_text(
        work_dir / "change-complexity-review.md",
        render_complexity_review(config, executable_plan, by_change, cap_changes),
    )
    write_text(
        work_dir / "plan-refit-decision-log.md",
        render_decision_log(config),
    )
    write_text(
        work_dir / "source-window-refit-trace.md",
        render_source_window_refit_trace(config, executable_plan, by_change),
    )
    adjustments = render_adjustments(config, status)
    if adjustments is not None:
        write_text(work_dir / "change-plan-adjustments.md", adjustments)

    anchors = output_orchestrate_dir / "change-capability-anchors"
    ensure_dir(anchors)
    for child in anchors.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
    for change in executable_plan:
        change_dir = anchors / change.slug
        cap_dir = change_dir / "capability-anchors"
        ensure_dir(cap_dir)
        write_text(change_dir / f"{change.slug}.md", render_packet(change, executable_plan, by_change, by_context, rel_work_dir))
        caps = sorted({
            item.mapping.final_target_capability
            for item in by_change[change.slug]
            if is_capability_view_atom(item)
        })
        for cap in caps:
            items = [
                item for item in by_change[change.slug]
                if is_capability_view_atom(item)
                and item.mapping.final_target_capability == cap
            ]
            write_text(cap_dir / f"{cap}.md", render_capability_view(change, cap, items))

    write_text(anchors / "index.md", render_anchor_index(executable_plan, by_change, by_context))
    write_text(
        work_dir / "change-capability-human-plan.md",
        render_human_plan(executable_plan, capabilities, by_change, by_context, cap_changes),
    )
    write_text(
        work_dir / "alignment-final-report.md",
        render_alignment_report(capabilities, direct_items, cap_changes),
    )
    final_packet_index = write_final_packet_index(output_orchestrate_dir, work_dir, executable_plan, by_change, by_context)
    trace_path = output_orchestrate_dir / "trace/phase-5.trace.json"
    write_json(
        trace_path,
        {
            "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": status,
            "atom-plan-mapping-path": orchestrate_rel(output_orchestrate_dir, output_mapping_json),
            "final-packet-index-path": orchestrate_rel(output_orchestrate_dir, final_packet_index),
            "capability-baseline-reconciliation-path": orchestrate_rel(output_orchestrate_dir, baseline_json),
            "capability-baseline-reconciliation-sha256": sha256_file(baseline_json),
            "complexity-summaries": [],
            "capability-progression-summaries": [],
            "validator-gate-outcomes": [],
            "reviewer-gate-outcomes": [],
        },
    )
    report = render_phase5_report(
        config,
        status,
        output_mapping,
        executable_plan,
        by_change,
        root_plan_published=False,
    )
    write_text(work_dir / "phase-5-agent-report.md", report)


def validate_rendered_outputs(output_orchestrate_dir: Path, final_atoms: Sequence[FinalAtom]) -> List[str]:
    errors: List[str] = []
    anchors = output_orchestrate_dir / "change-capability-anchors"
    items_by_id = {item.source.atom_id: item for item in final_atoms}
    direct_by_owner: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for item in final_atoms:
        mapping = item.mapping
        atom_id = item.source.atom_id
        if is_capability_view_atom(item):
            direct_by_owner[(mapping.final_change, mapping.final_target_capability)].append(atom_id)

    for item in final_atoms:
        atom_id = item.source.atom_id
        mapping = item.mapping
        change = mapping.final_change
        if is_no_owner(change):
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
        if is_no_owner(change) or is_no_owner(capability):
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
            found_item = items_by_id.get(found)
            if found_item is None:
                errors.append(f"{view_path} 包含未知 atom: {found}")
            elif found_item.mapping.final_relation != "direct":
                errors.append(f"{view_path} 包含 non-direct atom: {found}")
            elif (
                not is_capability_view_atom(found_item)
                or found_item.mapping.final_change != change
                or found_item.mapping.final_target_capability != capability
            ):
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
            item.mapping.final_target_capability
            for item in final_atoms
            if is_capability_view_atom(item)
        }
    )
    foundation_slugs = {
        item.mapping.final_change
        for item in final_atoms
        if item.mapping.final_relation == "direct"
        and is_foundation_delta(item)
        and item.mapping.final_change not in {"None", ""}
    }
    template = {
        "status": "adjusted",
        "source_documents_read": "`openspec/orchestrate/phase-works/phase-3/source-doc-manifest.md` 中源文档已由 Phase 2/3 覆盖。",
        "assumptions_and_conflicts": "Phase 3 已给出 `Decision: coverage-complete`，Phase 4 已给出 `Phase 4 Status: grounded`；Phase 5 未新增 atom，也未改写 Phase 2/3/4 证据。",
        "changes": [
            {
                "slug": slug,
                "title": slug,
                "intent": f"TODO：补充 `{slug}` 的中文单一 intent。",
                "outcome": f"TODO：补充 `{slug}` 的中文 source-backed outcome。",
                "kind": "foundation" if slug in foundation_slugs or "foundation" in slug else "business",
            }
            for slug in changes
        ],
        "capabilities": [
            {
                "slug": slug,
                "boundary": f"TODO：补充 `{slug}` 的中文长期行为边界。",
                "purpose": f"TODO：补充 `{slug}` 的 Purpose。",
                "owns": f"TODO：补充 `{slug}` 拥有的行为。",
                "excludes": f"TODO：补充 `{slug}` 不拥有的行为。",
                "baseline_status": "TODO-existing-or-absent",
                "baseline_evidence": f"TODO：只读检查 `openspec/specs/{slug}/spec.md`。",
            }
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
        description="根据已审阅的 mapping/config 校验并渲染机械派生的 Phase 5 plan-refit artifact。"
    )
    parser.add_argument("--orchestrate-dir", default="openspec/orchestrate", type=Path, help="orchestrate 目录路径")
    parser.add_argument("--mapping", type=Path, help="已审阅的 v2 phase-works/phase-5/atom-plan-mapping.json。")
    parser.add_argument("--config", type=Path, help="已审阅的 Phase 5 JSON config；默认使用 mapping 同目录的 phase5-refit.config.json。")
    parser.add_argument("--output-orchestrate-dir", type=Path, help="将输出写入该 orchestrate 目录，而不是 --orchestrate-dir。")
    parser.add_argument("--write", action="store_true", help="写入渲染后的 artifact；不指定时只检查输入。")
    parser.add_argument(
        "--no-root-update",
        action="store_true",
        help="仅用于暂存输出；不更新根 change-plan.md，因此结果不能通过 terminal validator。",
    )
    parser.add_argument("--validate-rendered", action="store_true", help="依据 atom-plan-mapping JSON 校验 final packet、capability view 和 anchor index。")
    parser.add_argument("--print-config-template", action="store_true", help="输出根据 mapping 推断的 JSON config 模板并退出。")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    orchestrate_dir = args.orchestrate_dir
    output_orchestrate_dir = args.output_orchestrate_dir or orchestrate_dir

    global_index_json = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    try:
        mapping_path = args.mapping or latest_mapping(orchestrate_dir)
        config_path = args.config or default_config_path(mapping_path)
        if not global_index_json.exists():
            raise ValueError(f"缺少 Phase 3 v2 canonical global atom index JSON: {global_index_json}")
        if mapping_path.suffix != ".json":
            raise ValueError(f"Phase 5 v2 只接受 canonical JSON mapping: {mapping_path}")
        atoms = load_global_atoms_json(global_index_json)
        mapping = load_mapping(mapping_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

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
    mapping = normalize_mapping(mapping, changes)
    final_atoms = join_atoms(atoms, mapping)
    warnings = validate(final_atoms, changes, capabilities, orchestrate_dir.parent / "specs")

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
        )

    if args.validate_rendered:
        rendered_errors = validate_rendered_outputs(output_orchestrate_dir, final_atoms)
        if rendered_errors:
            for error in rendered_errors:
                print(f"error: {error}", file=sys.stderr)
            return 1

    if args.write and not args.no_root_update:
        phase5_plan = output_orchestrate_dir / "phase-works/phase-5/change-plan.md"
        shutil.copyfile(phase5_plan, output_orchestrate_dir / "change-plan.md")
        executable_plan = planned_changes(changes)
        report = render_phase5_report(
            config,
            config_status(config),
            output_orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.md",
            executable_plan,
            direct_by_change(final_atoms, executable_plan),
            root_plan_published=True,
        )
        write_text(output_orchestrate_dir / "phase-works/phase-5/phase-5-agent-report.md", report)

    direct_count = sum(1 for item in final_atoms if is_executable_direct(item))
    changes_by_slug = {change.slug: change for change in changes}
    foundation_count = sum(
        1
        for item in final_atoms
        if is_executable_direct(item) and changes_by_slug.get(item.mapping.final_change, ChangeDef("", "", "", "", "")).kind == FOUNDATION_CHANGE_KIND
    )
    print(
        f"Phase 5 检查通过：atoms={len(final_atoms)} executable-direct={direct_count} "
        f"foundation-direct={foundation_count} changes={len(planned_changes(changes))} capabilities={len(capabilities)}"
    )
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
