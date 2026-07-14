#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 5 机械派生器。

语义权威只有 final change-plan.md、plan-refit-review.md 和 atom-plan-mapping.json。
本脚本不接受 semantic config，不推断 framework，不补写 acceptance/dependency/archive 文案。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from render_source_aligned_orchestrate import render_atom_plan_mapping, render_capability_baseline
from source_aligned_trace_lib import (
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_BASELINE_SCHEMA,
    FINAL_PACKET_INDEX_SCHEMA,
    GLOBAL_ATOM_INDEX_SCHEMA,
    KEBAB_CASE_RE,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    cell,
    line_ranges_label,
    normalize_code,
    sha256_file,
    source_atom_file_name,
    table_rows,
    write_json,
)


DIRECT_PROJECTIONS = {"spec-requirement", "spec-guard", "design-obligation", "verification-obligation"}
SPEC_PROJECTIONS = {"spec-requirement", "spec-guard"}
CHANGE_ONLY_PROJECTIONS = {"design-obligation", "verification-obligation"}
RELATIONS = {"direct", "context", "dependency", "preserve", "reference", "non-goal"}
CAPABILITY_IMPACTS = {"new", "modified", "none"}
TERMINAL_STATUSES = {"accepted", "adjusted"}
NONE_VALUES = {"", "none", "null", "None", "NULL"}


@dataclass(frozen=True)
class CapabilityDef:
    slug: str
    purpose: str
    owns: str
    excludes: str
    rationale: str


@dataclass(frozen=True)
class ChangeDef:
    slug: str
    intent: str
    outcome: str
    source_hint: str
    scope_in: str
    scope_out: str
    trigger: str
    normative_behavior: str
    observable_outcome: str
    exception_semantics: str
    acceptance: str
    dependencies_raw: str
    dependencies: Tuple[str, ...]
    ordering_reason: str
    archive_condition: str
    split_merge_judgment: str


@dataclass(frozen=True)
class Evidence:
    ga: str
    evidence_ref: Dict[str, object]
    source_document: str
    line_ranges: Tuple[Tuple[int, int], ...]
    source_fact: str
    atom_type: str
    normativity: str


@dataclass(frozen=True)
class Mapping:
    ga: str
    evidence_ref: Dict[str, object]
    owner_change: str
    relation: str
    projection: str
    capability_impact: str
    target_capability: str
    related_capabilities: Tuple[str, ...]
    reason: str


def squash(value: object) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value).replace("\n", " ")).strip()


def md(value: object) -> str:
    return squash(value).replace("|", "\\|") or "None"


def code(value: object) -> str:
    text = squash(value).replace("|", "\\|")
    return f"`{text}`" if text else "`None`"


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def repo_root_for(orchestrate_dir: Path) -> Path:
    if orchestrate_dir.name == "orchestrate" and orchestrate_dir.parent.name == "openspec":
        return orchestrate_dir.parent.parent
    return Path.cwd()


def require_json(path: Path, schema: str) -> Dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} 必须是JSON object")
    if data.get("trace-schema") != schema:
        raise ValueError(f"{path} trace-schema必须是{schema}")
    if data.get("trace-contract-version") != TRACE_CONTRACT_VERSION:
        raise ValueError(f"{path} trace-contract-version必须是{TRACE_CONTRACT_VERSION}")
    return data


def single_range(raw: object, where: str) -> Tuple[Tuple[int, int], ...]:
    if not isinstance(raw, list) or len(raw) != 1 or not isinstance(raw[0], dict):
        raise ValueError(f"{where} line-ranges必须包含一个连续range")
    start, end = raw[0].get("start"), raw[0].get("end")
    if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
        raise ValueError(f"{where} line-ranges非法")
    return ((start, end),)


def load_evidence(orchestrate_dir: Path) -> Dict[str, Evidence]:
    index_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    global_data = require_json(index_path, GLOBAL_ATOM_INDEX_SCHEMA)
    coverage_path = orchestrate_dir / "phase-works/phase-3/coverage-review.json"
    coverage = require_json(coverage_path, PHASE3_COVERAGE_REVIEW_SCHEMA)
    gaps = {
        normalize_code(row.get("gap-atom-id")): row
        for row in coverage.get("gap-atoms", [])
        if isinstance(row, dict)
    }
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    cache: Dict[str, Dict[str, Dict[str, object]]] = {}
    evidence: Dict[str, Evidence] = {}
    seen_refs: set[str] = set()
    for global_row in global_data.get("global-atoms", []):
        if not isinstance(global_row, dict) or set(global_row) != {"global-atom-id", "evidence-ref"}:
            raise ValueError("global atom row只能包含global-atom-id和evidence-ref")
        ga = normalize_code(global_row.get("global-atom-id"))
        ref = global_row.get("evidence-ref")
        if not ga or ga in evidence or not isinstance(ref, dict):
            raise ValueError(f"global atom非法或重复：{ga}")
        kind = normalize_code(ref.get("kind"))
        row: Optional[Dict[str, object]] = None
        ref_key = ""
        if kind == "phase-2-source-atom":
            source = normalize_code(ref.get("source-document"))
            atom_id = normalize_code(ref.get("source-atom-id"))
            if source not in cache:
                atom_path = atom_root / source_atom_file_name(source).replace(".md", ".json")
                atoms = require_json(atom_path, SOURCE_ATOMS_SCHEMA)
                cache[source] = {
                    normalize_code(item.get("source-atom-id")): {**item, "source-document": source}
                    for item in atoms.get("source-atoms", [])
                    if isinstance(item, dict)
                }
            row = cache[source].get(atom_id)
            ref_key = f"p2::{source}::{atom_id}"
        elif kind == "phase-3-gap-atom":
            gap_id = normalize_code(ref.get("gap-atom-id"))
            row = gaps.get(gap_id)
            ref_key = f"p3::{gap_id}"
        if row is None or ref_key in seen_refs:
            raise ValueError(f"{ga} evidence-ref无法唯一解析")
        seen_refs.add(ref_key)
        evidence[ga] = Evidence(
            ga=ga,
            evidence_ref=dict(ref),
            source_document=normalize_code(row.get("source-document")),
            line_ranges=single_range(row.get("line-ranges"), ga),
            source_fact=str(row.get("source-fact", "")),
            atom_type=normalize_code(row.get("atom-type")),
            normativity=normalize_code(row.get("normativity")),
        )
    if not evidence:
        raise ValueError("global atom index为空")
    return evidence


def parse_dependencies(raw: str) -> Tuple[str, ...]:
    normalized = normalize_code(raw).strip("。.;；")
    if normalized.lower() in {"无", "none", "`none`"}:
        return ()
    backticks = re.findall(r"`([^`]+)`", raw)
    values = backticks or re.split(r"[、,，]", raw)
    cleaned = [normalize_code(value).strip("。.;；") for value in values]
    return tuple(value for value in cleaned if value and value.lower() not in {"无", "none"})


def parse_final_plan(path: Path) -> tuple[List[ChangeDef], List[CapabilityDef], Dict[Tuple[str, str], str]]:
    text = path.read_text(encoding="utf-8")
    required_headings = [
        "## 输入",
        "## Source Semantic Landscape",
        "## Capability Map",
        "## Change 切分原则",
        "## Change Roadmap",
        "## Change-Capability Overlay",
        "## Phase 5 风险检查",
        "## Phase 5 语言自检",
    ]
    positions = []
    for heading in required_headings:
        if heading not in text:
            raise ValueError(f"final change plan缺少heading：{heading}")
        positions.append(text.index(heading))
    if positions != sorted(positions):
        raise ValueError("final change plan heading顺序非法")

    capabilities: List[CapabilityDef] = []
    seen_caps: set[str] = set()
    for row in table_rows(path, ["Capability", "Purpose", "Owns", "Excludes", "Boundary Rationale"]):
        slug = normalize_code(cell(row, "Capability"))
        if not KEBAB_CASE_RE.match(slug) or slug in seen_caps:
            raise ValueError(f"final Capability缺失或重复：{slug}")
        seen_caps.add(slug)
        values = [squash(cell(row, name)) for name in ("Purpose", "Owns", "Excludes", "Boundary Rationale")]
        if not all(values):
            raise ValueError(f"{slug} Capability字段不完整")
        capabilities.append(CapabilityDef(slug, *values))

    field_patterns = {
        "intent": r"^- 单一 intent[：:]\s*(.*)$",
        "outcome": r"^- source-backed outcome[：:]\s*(.*)$",
        "source_hint": r"^- 来源 evidence hint[：:]\s*(.*)$",
        "scope_in": r"^- 范围内[：:]\s*(.*)$",
        "scope_out": r"^- 范围外[：:]\s*(.*)$",
        "trigger": r"^\s+- trigger/context[：:]\s*(.*)$",
        "normative_behavior": r"^\s+- normative behavior[：:]\s*(.*)$",
        "observable_outcome": r"^\s+- observable outcome / invariant[：:]\s*(.*)$",
        "exception_semantics": r"^\s+- important exception / error semantics[：:]\s*(.*)$",
        "acceptance": r"^\s+- acceptance evidence[：:]\s*(.*)$",
        "dependencies_raw": r"^- 硬依赖[：:]\s*(.*)$",
        "ordering_reason": r"^- 排序理由[：:]\s*(.*)$",
        "archive_condition": r"^- 独立完成与归档[：:]\s*(.*)$",
        "split_merge_judgment": r"^- 拆分/合并判断[：:]\s*(.*)$",
    }
    changes_raw: List[Dict[str, str]] = []
    current: Optional[Dict[str, str]] = None
    for raw in text.splitlines():
        start = re.match(r"^- Change 名称[：:]\s*(.+?)\s*$", raw)
        if start:
            if current:
                changes_raw.append(current)
            current = {"slug": normalize_code(start.group(1))}
            continue
        if current is None:
            continue
        for key, pattern in field_patterns.items():
            match = re.match(pattern, raw)
            if match:
                current[key] = match.group(1).strip()
                break
    if current:
        changes_raw.append(current)
    changes: List[ChangeDef] = []
    seen_changes: set[str] = set()
    required_fields = list(field_patterns)
    for raw in changes_raw:
        slug = raw.get("slug", "")
        if not KEBAB_CASE_RE.match(slug) or slug in seen_changes:
            raise ValueError(f"final Change缺失或重复：{slug}")
        missing = [key for key in required_fields if not raw.get(key, "").strip()]
        if missing:
            raise ValueError(f"{slug} 缺少final Change字段：{', '.join(missing)}")
        seen_changes.add(slug)
        changes.append(ChangeDef(
            slug=slug,
            intent=raw["intent"],
            outcome=raw["outcome"],
            source_hint=raw["source_hint"],
            scope_in=raw["scope_in"],
            scope_out=raw["scope_out"],
            trigger=raw["trigger"],
            normative_behavior=raw["normative_behavior"],
            observable_outcome=raw["observable_outcome"],
            exception_semantics=raw["exception_semantics"],
            acceptance=raw["acceptance"],
            dependencies_raw=raw["dependencies_raw"],
            dependencies=parse_dependencies(raw["dependencies_raw"]),
            ordering_reason=raw["ordering_reason"],
            archive_condition=raw["archive_condition"],
            split_merge_judgment=raw["split_merge_judgment"],
        ))
    if not changes:
        raise ValueError("final change plan没有Change")
    change_order = {change.slug: index for index, change in enumerate(changes)}
    for change in changes:
        for dependency in change.dependencies:
            if dependency not in change_order:
                raise ValueError(f"{change.slug}引用未知硬依赖：{dependency}")
            if change_order[dependency] >= change_order[change.slug]:
                raise ValueError(f"{change.slug}硬依赖必须位于roadmap前方：{dependency}")

    overlay: Dict[Tuple[str, str], str] = {}
    for row in table_rows(path, ["Change", "Capability", "Capability Impact", "Direct Behavior Delta"]):
        change = normalize_code(cell(row, "Change"))
        capability = normalize_code(cell(row, "Capability"))
        impact = normalize_code(cell(row, "Capability Impact")).lower()
        if change not in seen_changes or capability not in seen_caps or impact not in {"new", "modified"}:
            raise ValueError(f"final overlay row非法：{change}/{capability}/{impact}")
        if (change, capability) in overlay:
            raise ValueError(f"final overlay重复：{change}/{capability}")
        overlay[(change, capability)] = impact
    return changes, capabilities, overlay


def parse_review_status(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    for heading in ("## Capability Review", "## Change Review", "## Unassigned and Gap Review", "## Final Decision"):
        if heading not in text:
            raise ValueError(f"plan-refit-review缺少heading：{heading}")
    match = re.search(r"(?mi)^-?\s*Status[：:]\s*`?([a-z-]+)`?", text)
    if not match or match.group(1) not in TERMINAL_STATUSES:
        raise ValueError("mechanical helper只处理accepted/adjusted review")
    return match.group(1)


def load_mapping(path: Path) -> Dict[str, Mapping]:
    data = require_json(path, ATOM_PLAN_MAPPING_SCHEMA)
    expected = {
        "global-atom-id", "evidence-ref", "final-owner-change", "final-relation",
        "final-artifact-projection", "final-capability-impact", "final-target-capability",
        "related-capabilities", "reason",
    }
    mapping: Dict[str, Mapping] = {}
    for row in data.get("rows", []):
        if not isinstance(row, dict) or set(row) != expected:
            raise ValueError("atom-plan-mapping v4 row字段非法")
        ga = normalize_code(row.get("global-atom-id"))
        if not ga or ga in mapping or not isinstance(row.get("evidence-ref"), dict):
            raise ValueError(f"mapping GA非法或重复：{ga}")
        related = row.get("related-capabilities")
        if not isinstance(related, list):
            raise ValueError(f"{ga} related-capabilities必须是array")
        mapping[ga] = Mapping(
            ga=ga,
            evidence_ref=dict(row["evidence-ref"]),
            owner_change=normalize_code(row.get("final-owner-change")),
            relation=normalize_code(row.get("final-relation")),
            projection=normalize_code(row.get("final-artifact-projection")),
            capability_impact=normalize_code(row.get("final-capability-impact")),
            target_capability=normalize_code(row.get("final-target-capability")),
            related_capabilities=tuple(normalize_code(item) for item in related),
            reason=str(row.get("reason", "")),
        )
    return mapping


def validate_mapping(
    evidence: Dict[str, Evidence],
    mapping: Dict[str, Mapping],
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    overlay: Dict[Tuple[str, str], str],
) -> None:
    if set(mapping) != set(evidence):
        raise ValueError(f"mapping GA集合不一致；缺少={sorted(set(evidence)-set(mapping))}，多余={sorted(set(mapping)-set(evidence))}")
    change_ids = {change.slug for change in changes}
    capability_ids = {capability.slug for capability in capabilities}
    mapping_overlay: Dict[Tuple[str, str], set[str]] = defaultdict(set)
    direct_by_change: Dict[str, int] = defaultdict(int)
    for ga, row in mapping.items():
        source = evidence[ga]
        if row.evidence_ref != source.evidence_ref:
            raise ValueError(f"{ga} evidence-ref与global index不一致")
        if row.owner_change not in change_ids:
            raise ValueError(f"{ga} final owner Change不存在：{row.owner_change}")
        if row.relation not in RELATIONS:
            raise ValueError(f"{ga} final relation非法：{row.relation}")
        if row.capability_impact not in CAPABILITY_IMPACTS:
            raise ValueError(f"{ga} capability impact非法：{row.capability_impact}")
        if len(row.related_capabilities) != len(set(row.related_capabilities)):
            raise ValueError(f"{ga} related-capabilities重复")
        if any(cap not in capability_ids for cap in row.related_capabilities):
            raise ValueError(f"{ga} related Capability不存在")
        if row.target_capability in row.related_capabilities:
            raise ValueError(f"{ga} related Capability不得等于target")
        if row.relation == "direct":
            direct_by_change[row.owner_change] += 1
            if row.projection not in DIRECT_PROJECTIONS:
                raise ValueError(f"{ga} direct projection非法：{row.projection}")
            if row.projection in SPEC_PROJECTIONS:
                if row.capability_impact not in {"new", "modified"} or row.target_capability not in capability_ids:
                    raise ValueError(f"{ga} direct spec mapping缺少有效Capability impact/target")
                mapping_overlay[(row.owner_change, row.target_capability)].add(row.capability_impact)
            elif row.capability_impact != "none" or row.target_capability != "none":
                raise ValueError(f"{ga} design/verification mapping必须使用none/none")
        else:
            if row.projection != "contextual-only" or row.capability_impact != "none" or row.target_capability != "none":
                raise ValueError(f"{ga} non-direct mapping必须使用contextual-only和none/none")
        if not row.reason.strip():
            raise ValueError(f"{ga} mapping reason为空")
        if not re.search(r"[\u4e00-\u9fff]", row.reason):
            raise ValueError(f"{ga} mapping reason必须使用简体中文解释")
    missing_direct = sorted(change_id for change_id in change_ids if direct_by_change.get(change_id, 0) == 0)
    if missing_direct:
        raise ValueError(f"final Change缺少direct evidence：{', '.join(missing_direct)}")
    normalized_overlay = {pair: next(iter(impacts)) for pair, impacts in mapping_overlay.items() if len(impacts) == 1}
    if any(len(impacts) != 1 for impacts in mapping_overlay.values()) or normalized_overlay != overlay:
        raise ValueError(f"final plan overlay与mapping不一致；plan={overlay} mapping={normalized_overlay}")


def build_baseline(
    repo_root: Path,
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    mapping: Dict[str, Mapping],
) -> Dict[str, object]:
    cap_defs = {capability.slug: capability for capability in capabilities}
    by_change_target: Dict[Tuple[str, str], set[str]] = defaultdict(set)
    for row in mapping.values():
        if row.relation == "direct" and row.projection in SPEC_PROJECTIONS:
            by_change_target[(row.owner_change, row.target_capability)].add(row.capability_impact)
    rows: List[Dict[str, object]] = []
    progress: Dict[str, int] = defaultdict(int)
    first_change: Dict[str, str] = {}
    for change in changes:
        targets = sorted(target for owner, target in by_change_target if owner == change.slug)
        for target in targets:
            impacts = by_change_target[(change.slug, target)]
            if len(impacts) != 1 or target not in cap_defs:
                raise ValueError(f"{change.slug}/{target} Capability mapping不一致")
            spec_path = repo_root / "openspec/specs" / target / "spec.md"
            baseline = "existing" if spec_path.is_file() else "absent"
            expected = "modified" if baseline == "existing" or progress[target] > 0 else "new"
            actual = next(iter(impacts))
            if actual != expected:
                raise ValueError(f"{change.slug}/{target} baseline期望{expected}，mapping为{actual}")
            if target not in first_change:
                first_change[target] = change.slug
            progress[target] += 1
    for target in sorted(progress):
        spec_path = repo_root / "openspec/specs" / target / "spec.md"
        existing = spec_path.is_file()
        rows.append({
            "capability": target,
            "baseline-status": "existing" if existing else "absent",
            "spec-path": rel(spec_path, repo_root),
            "spec-sha256": sha256_file(spec_path) if existing else None,
            "baseline-evidence": "精确spec路径存在并已只读核对。" if existing else "精确spec路径不存在。",
            "first-planned-advancement": first_change[target],
            "required-first-relation": "modified" if existing else "new",
            "later-relation-rule": "modified",
        })
    return {
        "trace-schema": CAPABILITY_BASELINE_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "repository-specs-root": "openspec/specs",
        "capabilities": rows,
    }


def fence(text: str) -> str:
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", text)), default=0)
    marker = "`" * max(3, longest + 1)
    return f"{marker}text\n{text}\n{marker}"


def evidence_section(item: Evidence, row: Mapping) -> str:
    ranges = line_ranges_label([{"start": start, "end": end} for start, end in item.line_ranges])
    return "\n".join([
        f"### {code(item.ga)}", "",
        f"- Evidence reference：{code(json.dumps(item.evidence_ref, ensure_ascii=False, sort_keys=True))}",
        f"- Source：{code(item.source_document)} / {code(ranges)}",
        f"- Type / normativity：{code(item.atom_type)} / {code(item.normativity)}",
        f"- Relation / projection：{code(row.relation)} / {code(row.projection)}",
        f"- Capability：{code(row.capability_impact)} / {code(row.target_capability)}",
        f"- Reason：{md(row.reason)}", "", fence(item.source_fact), "",
    ])


def render_packet(change: ChangeDef, evidence: Dict[str, Evidence], mapping: Dict[str, Mapping]) -> str:
    direct = sorted(
        ((evidence[ga], row) for ga, row in mapping.items() if row.owner_change == change.slug and row.relation == "direct"),
        key=lambda pair: pair[0].ga,
    )
    non_direct = sorted(
        ((evidence[ga], row) for ga, row in mapping.items() if row.owner_change == change.slug and row.relation != "direct"),
        key=lambda pair: pair[0].ga,
    )
    lines = [
        f"# Final Change Packet：{change.slug}", "",
        "> 本 packet 是完整、未做语义去重的 evidence mapping，不是 requirement inventory；下游综合多个 GA 时必须保留多对一 GA trace。", "",
        "## Change boundary", "",
        f"- Intent：{md(change.intent)}",
        f"- Outcome：{md(change.outcome)}",
        f"- Scope in：{md(change.scope_in)}",
        f"- Scope out：{md(change.scope_out)}",
        f"- Acceptance：{md(change.acceptance)}",
        f"- Hard dependencies：{md(change.dependencies_raw)}",
        f"- Independent archive：{md(change.archive_condition)}", "",
        "## Direct evidence mapping", "",
    ]
    if direct:
        lines.extend(evidence_section(item, row) for item, row in direct)
    else:
        lines.append("无 direct evidence occurrence。")
    lines.extend(["", "## Owner-scoped non-direct evidence", ""])
    if non_direct:
        lines.extend(evidence_section(item, row) for item, row in non_direct)
    else:
        lines.append("无 owner-scoped non-direct evidence occurrence。")
    return "\n".join(lines).rstrip() + "\n"


def render_capability_view(change: str, capability: str, evidence: Dict[str, Evidence], mapping: Dict[str, Mapping]) -> str:
    items = sorted(
        (
            (evidence[ga], row)
            for ga, row in mapping.items()
            if row.owner_change == change
            and row.relation == "direct"
            and row.target_capability == capability
            and row.projection in SPEC_PROJECTIONS
        ),
        key=lambda pair: pair[0].ga,
    )
    lines = [f"# Capability View：{change} / {capability}", "", "> 只包含该Change对Capability的direct spec advancement，未做semantic dedup。", ""]
    lines.extend(evidence_section(item, row) for item, row in items)
    return "\n".join(lines).rstrip() + "\n"


def clean_legacy(orchestrate_dir: Path) -> None:
    work = orchestrate_dir / "phase-works/phase-5"
    legacy = [
        "phase5-refit.config.json", "input-change-plan.md", "source-window-refit-trace.md",
        "change-plan-adjustments.md", "capability-progression-review.md", "change-complexity-review.md",
        "plan-refit-decision-log.md", "alignment-final-report.md", "change-capability-human-plan.md",
    ]
    for name in legacy:
        path = work / name
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def write_outputs(orchestrate_dir: Path) -> None:
    repo_root = repo_root_for(orchestrate_dir)
    work = orchestrate_dir / "phase-works/phase-5"
    plan_path = work / "change-plan.md"
    review_path = work / "plan-refit-review.md"
    mapping_path = work / "atom-plan-mapping.json"
    status = parse_review_status(review_path)
    changes, capabilities, overlay = parse_final_plan(plan_path)
    evidence = load_evidence(orchestrate_dir)
    mapping = load_mapping(mapping_path)
    validate_mapping(evidence, mapping, changes, capabilities, overlay)
    clean_legacy(orchestrate_dir)

    mapping_md = work / "atom-plan-mapping.md"
    mapping_md.write_text(render_atom_plan_mapping(orchestrate_dir, mapping_path), encoding="utf-8")
    baseline_path = work / "capability-baseline-reconciliation.json"
    baseline = build_baseline(repo_root, changes, capabilities, mapping)
    write_json(baseline_path, baseline)
    (work / "capability-baseline-reconciliation.md").write_text(render_capability_baseline(orchestrate_dir, baseline_path), encoding="utf-8")

    root_plan = orchestrate_dir / "change-plan.md"
    shutil.copyfile(plan_path, root_plan)
    anchors = orchestrate_dir / "change-capability-anchors"
    anchors.mkdir(parents=True, exist_ok=True)
    for child in anchors.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
    packets: List[Dict[str, object]] = []
    index_lines = ["# Final Change Packet Index", "", "| Change | Packet | Direct GA | Non-direct GA | Capability Views |", "| --- | --- | --- | --- | --- |"]
    for change in changes:
        change_dir = anchors / change.slug
        cap_dir = change_dir / "capability-anchors"
        cap_dir.mkdir(parents=True, exist_ok=True)
        packet_path = change_dir / f"{change.slug}.md"
        packet_path.write_text(render_packet(change, evidence, mapping), encoding="utf-8")
        direct_ids = sorted(ga for ga, row in mapping.items() if row.owner_change == change.slug and row.relation == "direct")
        non_direct_ids = sorted(ga for ga, row in mapping.items() if row.owner_change == change.slug and row.relation != "direct")
        caps = sorted({row.target_capability for row in mapping.values() if row.owner_change == change.slug and row.relation == "direct" and row.projection in SPEC_PROJECTIONS})
        cap_paths: List[str] = []
        for capability in caps:
            cap_path = cap_dir / f"{capability}.md"
            cap_path.write_text(render_capability_view(change.slug, capability, evidence, mapping), encoding="utf-8")
            cap_paths.append(rel(cap_path, repo_root))
        packets.append({
            "change": change.slug,
            "change-kind": "business",
            "packet-path": rel(packet_path, repo_root),
            "packet-digest": sha256_file(packet_path),
            "direct-atom-ids": direct_ids,
            "owner-scoped-non-direct-atom-ids": non_direct_ids,
            "capability-view-paths": cap_paths,
        })
        index_lines.append(f"| {code(change.slug)} | {code(rel(packet_path, repo_root))} | {md(', '.join(direct_ids))} | {md(', '.join(non_direct_ids))} | {md(', '.join(cap_paths))} |")
    (anchors / "index.md").write_text("\n".join(index_lines).rstrip() + "\n", encoding="utf-8")
    packet_index_path = work / "final-packet-index.json"
    write_json(packet_index_path, {
        "trace-schema": FINAL_PACKET_INDEX_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "packets": packets,
    })
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    write_json(trace_path, {
        "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "status": status,
        "final-change-plan-path": rel(plan_path, repo_root),
        "final-change-plan-sha256": sha256_file(plan_path),
        "plan-refit-review-path": rel(review_path, repo_root),
        "plan-refit-review-sha256": sha256_file(review_path),
        "atom-plan-mapping-path": rel(mapping_path, repo_root),
        "atom-plan-mapping-sha256": sha256_file(mapping_path),
        "capability-baseline-reconciliation-path": rel(baseline_path, repo_root),
        "capability-baseline-reconciliation-sha256": sha256_file(baseline_path),
        "final-packet-index-path": rel(packet_index_path, repo_root),
        "final-packet-index-sha256": sha256_file(packet_index_path),
    })


def validate_outputs(orchestrate_dir: Path) -> None:
    repo_root = repo_root_for(orchestrate_dir)
    work = orchestrate_dir / "phase-works/phase-5"
    plan = work / "change-plan.md"
    if plan.read_bytes() != (orchestrate_dir / "change-plan.md").read_bytes():
        raise ValueError("根change-plan.md与Phase 5 plan不一致")
    mapping_path = work / "atom-plan-mapping.json"
    expected_mapping_md = render_atom_plan_mapping(orchestrate_dir, mapping_path)
    if (work / "atom-plan-mapping.md").read_text(encoding="utf-8") != expected_mapping_md:
        raise ValueError("atom plan mapping Markdown drift")
    baseline_path = work / "capability-baseline-reconciliation.json"
    if (work / "capability-baseline-reconciliation.md").read_text(encoding="utf-8") != render_capability_baseline(orchestrate_dir, baseline_path):
        raise ValueError("Capability baseline Markdown drift")
    packet_index = require_json(work / "final-packet-index.json", FINAL_PACKET_INDEX_SCHEMA)
    for packet in packet_index.get("packets", []):
        if not isinstance(packet, dict):
            raise ValueError("final packet index row非法")
        packet_path = repo_root / str(packet.get("packet-path", ""))
        if not packet_path.is_file() or sha256_file(packet_path) != packet.get("packet-digest"):
            raise ValueError(f"final packet缺失或digest drift：{packet_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从final plan/review/mapping机械生成Phase 5派生产物。")
    parser.add_argument("--orchestrate-dir", type=Path, default=Path("openspec/orchestrate"))
    parser.add_argument("--write", action="store_true", help="写入baseline、packets、trace和根plan")
    parser.add_argument("--validate-rendered", action="store_true", help="验证已生成派生产物")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.write:
            write_outputs(args.orchestrate_dir)
        else:
            plan = args.orchestrate_dir / "phase-works/phase-5/change-plan.md"
            review = args.orchestrate_dir / "phase-works/phase-5/plan-refit-review.md"
            mapping_path = args.orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
            changes, capabilities, overlay = parse_final_plan(plan)
            parse_review_status(review)
            evidence = load_evidence(args.orchestrate_dir)
            mapping = load_mapping(mapping_path)
            validate_mapping(evidence, mapping, changes, capabilities, overlay)
        if args.validate_rendered:
            validate_outputs(args.orchestrate_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("Phase 5 mechanical derivation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
