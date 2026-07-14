#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 5 机械派生器。

语义权威是 final change-plan.md、framework-refit-trace.json 和
atom-plan-mapping.json；plan-refit-review.md 只是 JSON mirror。
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

from render_source_aligned_orchestrate import (
    render_atom_plan_mapping,
    render_capability_baseline,
    render_framework_refit_review,
)
from source_aligned_trace_lib import (
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_BASELINE_SCHEMA,
    EVIDENCE_COLLECTION_INDEX_SCHEMA,
    FINAL_PACKET_INDEX_SCHEMA,
    FRAMEWORK_REFIT_TRACE_SCHEMA,
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
NONTERMINAL_STATUSES = {"needs-coverage-recheck", "blocked"}
NONE_VALUES = {"", "none", "null", "None", "NULL"}
CAPABILITY_REVIEW_DECISIONS = {"keep", "split", "merge", "remove", "rename"}
CHANGE_REVIEW_DECISIONS = {"keep", "split", "merge", "scope-adjusted", "remove", "rename", "reorder"}


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


def _phase1_framework(orchestrate_dir: Path) -> tuple[List[str], List[str], set[Tuple[str, str]]]:
    path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    text = path.read_text(encoding="utf-8")
    changes = [
        normalize_code(match.group(1))
        for match in re.finditer(r"(?m)^- Change 名称[：:]\s*(.+?)\s*$", text)
    ]
    capabilities = [
        normalize_code(cell(row, "Candidate Capability"))
        for row in table_rows(path, ["Candidate Capability", "Purpose", "Owns", "Excludes"])
    ]
    overlay = {
        (normalize_code(cell(row, "Change")), normalize_code(cell(row, "Candidate Capability")))
        for row in table_rows(path, ["Change", "Candidate Capability", "Roadmap Role", "Direct Behavior Delta Hypothesis"])
    }
    return changes, capabilities, overlay


def _require_exact_fields(row: Dict[str, object], expected: set[str], where: str) -> None:
    actual = set(row)
    if actual != expected:
        raise ValueError(f"{where}字段必须精确为{sorted(expected)}；缺少={sorted(expected-actual)}，多余={sorted(actual-expected)}")


def _require_identifier_list(value: object, where: str, allow_empty: bool = False) -> List[str]:
    if not isinstance(value, list):
        raise ValueError(f"{where}必须是array")
    result = [normalize_code(item) for item in value]
    if any(not KEBAB_CASE_RE.match(item) for item in result) or len(result) != len(set(result)):
        raise ValueError(f"{where}必须是无重复kebab-case identifier array")
    if not allow_empty and not result:
        raise ValueError(f"{where}不得为空")
    return result


def _validate_gate_results(value: object, where: str) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{where}.gate-results必须是非空array")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{where}.gate-results[{index}]必须是object")
        _require_exact_fields(item, {"gate", "result", "note"}, f"{where}.gate-results[{index}]")
        if not normalize_code(item.get("gate")) or normalize_code(item.get("result")) not in {"passed", "failed"}:
            raise ValueError(f"{where}.gate-results[{index}] gate/result非法")
        if not squash(item.get("note")):
            raise ValueError(f"{where}.gate-results[{index}].note不得为空")


def load_framework_refit(path: Path) -> Dict[str, object]:
    return require_json(path, FRAMEWORK_REFIT_TRACE_SCHEMA)


def validate_framework_refit(
    orchestrate_dir: Path,
    data: Dict[str, object],
    changes: Optional[Sequence[ChangeDef]] = None,
    capabilities: Optional[Sequence[CapabilityDef]] = None,
    overlay: Optional[Dict[Tuple[str, str], str]] = None,
) -> str:
    """校验 refit trace 的结构、基数及与 final plan 的 framework 一致性。"""
    _require_exact_fields(data, {
        "trace-schema", "trace-contract-version", "status", "initial-plan-ref",
        "capability-reviews", "change-reviews", "unassigned-and-gap-reviews",
        "final-framework", "issues", "language-self-check",
    }, "framework-refit-trace")
    status = normalize_code(data.get("status"))
    if status not in TERMINAL_STATUSES | NONTERMINAL_STATUSES:
        raise ValueError(f"framework refit status非法：{status}")
    repo_root = repo_root_for(orchestrate_dir)
    initial_path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    initial_ref = data.get("initial-plan-ref")
    if not isinstance(initial_ref, dict):
        raise ValueError("initial-plan-ref必须是object")
    _require_exact_fields(initial_ref, {"artifact-path", "sha256"}, "initial-plan-ref")
    if initial_ref.get("artifact-path") != rel(initial_path, repo_root) or initial_ref.get("sha256") != sha256_file(initial_path):
        raise ValueError("initial-plan-ref path或digest与Phase 1 initial plan不一致")
    initial_changes, initial_capabilities, initial_overlay = _phase1_framework(orchestrate_dir)

    capability_rows = data.get("capability-reviews")
    change_rows = data.get("change-reviews")
    gap_rows = data.get("unassigned-and-gap-reviews")
    if not isinstance(capability_rows, list) or not isinstance(change_rows, list) or not isinstance(gap_rows, list):
        raise ValueError("三个review集合必须是array")
    capability_decisions: Dict[str, str] = {}
    for index, row in enumerate(capability_rows):
        if not isinstance(row, dict):
            raise ValueError(f"capability-reviews[{index}]必须是object")
        _require_exact_fields(row, {
            "input-capability", "evidence-collection-path", "decision", "final-capabilities", "gate-results", "reason",
        }, f"capability-reviews[{index}]")
        source = normalize_code(row.get("input-capability"))
        decision = normalize_code(row.get("decision"))
        if source in capability_decisions or source not in initial_capabilities:
            raise ValueError(f"input Capability未知或重复：{source}")
        if decision not in CAPABILITY_REVIEW_DECISIONS:
            raise ValueError(f"{source} Capability decision非法：{decision}")
        finals = _require_identifier_list(row.get("final-capabilities"), f"{source}.final-capabilities", allow_empty=decision == "remove")
        if decision == "remove" and finals:
            raise ValueError(f"{source} remove要求final-capabilities为空")
        if decision == "keep" and finals != [source]:
            raise ValueError(f"{source} keep要求final-capabilities仅包含自身")
        if decision == "rename" and (len(finals) != 1 or finals[0] == source):
            raise ValueError(f"{source} rename要求一个不同的final Capability")
        if decision == "split" and len(finals) < 2:
            raise ValueError(f"{source} split要求至少两个final Capability")
        if decision == "merge" and len(finals) != 1:
            raise ValueError(f"{source} merge要求恰好一个final Capability")
        expected_collection = rel(
            orchestrate_dir / f"phase-works/phase-4/source-evidence-collections/by-input-capability/{source}.md",
            repo_root,
        )
        if row.get("evidence-collection-path") != expected_collection:
            raise ValueError(f"{source} evidence-collection-path应为{expected_collection}")
        _validate_gate_results(row.get("gate-results"), f"capability-reviews[{index}]")
        if not squash(row.get("reason")) or not re.search(r"[\u4e00-\u9fff]", str(row.get("reason"))):
            raise ValueError(f"{source} reason必须使用简体中文解释")
        capability_decisions[source] = decision
    if list(capability_decisions) != initial_capabilities:
        raise ValueError(f"每个initial Capability必须按原顺序恰好一行：期望={initial_capabilities}，实际={list(capability_decisions)}")
    capability_merge_targets: Dict[str, int] = {}
    for row in capability_rows:
        if normalize_code(row.get("decision")) == "merge":
            target = normalize_code(row.get("final-capabilities", [""])[0])
            capability_merge_targets[target] = capability_merge_targets.get(target, 0) + 1
    if any(count < 2 for count in capability_merge_targets.values()):
        raise ValueError("Capability merge要求至少两个initial Capability指向同一个final Capability")

    change_decisions: Dict[str, str] = {}
    for index, row in enumerate(change_rows):
        if not isinstance(row, dict):
            raise ValueError(f"change-reviews[{index}]必须是object")
        _require_exact_fields(row, {
            "input-change", "evidence-collection-path", "decision", "final-changes", "gate-results", "reason",
        }, f"change-reviews[{index}]")
        source = normalize_code(row.get("input-change"))
        decision = normalize_code(row.get("decision"))
        if source in change_decisions or source not in initial_changes:
            raise ValueError(f"input Change未知或重复：{source}")
        if decision not in CHANGE_REVIEW_DECISIONS:
            raise ValueError(f"{source} Change decision非法：{decision}")
        finals = _require_identifier_list(row.get("final-changes"), f"{source}.final-changes", allow_empty=decision == "remove")
        if decision == "remove" and finals:
            raise ValueError(f"{source} remove要求final-changes为空")
        if decision in {"keep", "reorder", "scope-adjusted"} and finals != [source]:
            raise ValueError(f"{source} {decision}要求final-changes仅包含自身")
        if decision == "rename" and (len(finals) != 1 or finals[0] == source):
            raise ValueError(f"{source} rename要求一个不同的final Change")
        if decision == "split" and len(finals) < 2:
            raise ValueError(f"{source} split要求至少两个final Change")
        if decision == "merge" and len(finals) != 1:
            raise ValueError(f"{source} merge要求恰好一个final Change")
        expected_collection = rel(
            orchestrate_dir / f"phase-works/phase-4/source-evidence-collections/by-input-change/{source}.md",
            repo_root,
        )
        if row.get("evidence-collection-path") != expected_collection:
            raise ValueError(f"{source} evidence-collection-path应为{expected_collection}")
        _validate_gate_results(row.get("gate-results"), f"change-reviews[{index}]")
        if not squash(row.get("reason")) or not re.search(r"[\u4e00-\u9fff]", str(row.get("reason"))):
            raise ValueError(f"{source} reason必须使用简体中文解释")
        change_decisions[source] = decision
    if list(change_decisions) != initial_changes:
        raise ValueError(f"每个initial Change必须按原顺序恰好一行：期望={initial_changes}，实际={list(change_decisions)}")
    change_merge_targets: Dict[str, int] = {}
    for row in change_rows:
        if normalize_code(row.get("decision")) == "merge":
            target = normalize_code(row.get("final-changes", [""])[0])
            change_merge_targets[target] = change_merge_targets.get(target, 0) + 1
    if any(count < 2 for count in change_merge_targets.values()):
        raise ValueError("Change merge要求至少两个initial Change指向同一个final Change")

    collection_path = orchestrate_dir / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
    collection = require_json(collection_path, EVIDENCE_COLLECTION_INDEX_SCHEMA)
    expected_gap = {
        normalize_code(row.get("global-atom-id")): row.get("evidence-ref")
        for row in collection.get("rows", [])
        if isinstance(row, dict) and normalize_code(row.get("change-bucket")) == "unassigned-and-gap"
    }
    seen_gap: set[str] = set()
    for index, row in enumerate(gap_rows):
        if not isinstance(row, dict):
            raise ValueError(f"unassigned-and-gap-reviews[{index}]必须是object")
        _require_exact_fields(row, {
            "global-atom-id", "evidence-ref", "disposition", "final-change", "final-capability", "reason",
        }, f"unassigned-and-gap-reviews[{index}]")
        ga = normalize_code(row.get("global-atom-id"))
        if ga in seen_gap or ga not in expected_gap:
            raise ValueError(f"unassigned/gap GA未知或重复：{ga}")
        seen_gap.add(ga)
        if row.get("evidence-ref") != expected_gap[ga]:
            raise ValueError(f"{ga} evidence-ref与Phase 4 index不一致")
        if not normalize_code(row.get("disposition")) or not normalize_code(row.get("final-change")):
            raise ValueError(f"{ga} disposition/final-change不得为空")
        if not normalize_code(row.get("final-capability")):
            raise ValueError(f"{ga} final-capability必须显式使用none或Capability ID")
        if not squash(row.get("reason")) or not re.search(r"[\u4e00-\u9fff]", str(row.get("reason"))):
            raise ValueError(f"{ga} reason必须使用简体中文解释")
    if seen_gap != set(expected_gap):
        raise ValueError(f"每个unassigned/gap GA必须恰好一行；缺少={sorted(set(expected_gap)-seen_gap)}")

    issues = data.get("issues")
    if not isinstance(issues, list):
        raise ValueError("issues必须是array")
    language = squash(data.get("language-self-check"))
    if not language or not re.search(r"[\u4e00-\u9fff]", language):
        raise ValueError("language-self-check必须使用简体中文解释")
    if status in NONTERMINAL_STATUSES:
        if data.get("final-framework") is not None or not issues:
            raise ValueError(f"{status}要求final-framework=null且issues非空")
        return status
    if issues:
        raise ValueError(f"{status}要求issues为空")
    failed_gates = [
        normalize_code(gate.get("gate"))
        for review in [*capability_rows, *change_rows]
        if isinstance(review, dict)
        for gate in review.get("gate-results", [])
        if isinstance(gate, dict) and normalize_code(gate.get("result")) != "passed"
    ]
    if failed_gates:
        raise ValueError(f"terminal refit要求所有gate通过；未通过={failed_gates}")

    framework = data.get("final-framework")
    if not isinstance(framework, dict):
        raise ValueError(f"{status}要求非空final-framework")
    _require_exact_fields(framework, {"change-order", "capabilities", "overlay"}, "final-framework")
    final_change_order = _require_identifier_list(framework.get("change-order"), "final-framework.change-order")
    final_capabilities = _require_identifier_list(
        framework.get("capabilities"), "final-framework.capabilities", allow_empty=True,
    )
    framework_overlay: Dict[Tuple[str, str], str] = {}
    overlay_rows = framework.get("overlay")
    if not isinstance(overlay_rows, list):
        raise ValueError("final-framework.overlay必须是array")
    for index, row in enumerate(overlay_rows):
        if not isinstance(row, dict):
            raise ValueError(f"final-framework.overlay[{index}]必须是object")
        _require_exact_fields(row, {"change", "capability", "capability-impact"}, f"final-framework.overlay[{index}]")
        pair = (normalize_code(row.get("change")), normalize_code(row.get("capability")))
        impact = normalize_code(row.get("capability-impact"))
        if pair in framework_overlay or pair[0] not in final_change_order or pair[1] not in final_capabilities or impact not in {"new", "modified"}:
            raise ValueError(f"final-framework overlay row非法或重复：{pair}/{impact}")
        framework_overlay[pair] = impact
    if changes is not None and final_change_order != [item.slug for item in changes]:
        raise ValueError("final-framework.change-order与final change-plan不一致")
    if capabilities is not None and final_capabilities != [item.slug for item in capabilities]:
        raise ValueError("final-framework.capabilities与final change-plan不一致")
    if overlay is not None and framework_overlay != overlay:
        raise ValueError("final-framework.overlay与final change-plan不一致")
    final_change_ids = set(final_change_order)
    final_capability_ids = set(final_capabilities)
    for row in capability_rows:
        if any(item not in final_capability_ids for item in row.get("final-capabilities", [])):
            raise ValueError(f"{row.get('input-capability')}引用未知final Capability")
    for row in change_rows:
        if any(item not in final_change_ids for item in row.get("final-changes", [])):
            raise ValueError(f"{row.get('input-change')}引用未知final Change")
    for row in gap_rows:
        if normalize_code(row.get("final-change")) not in final_change_ids:
            raise ValueError(f"{row.get('global-atom-id')}引用未知final Change")
        cap = normalize_code(row.get("final-capability"))
        if cap != "none" and cap not in final_capability_ids:
            raise ValueError(f"{row.get('global-atom-id')}引用未知final Capability")
    all_keep = all(value == "keep" for value in capability_decisions.values()) and all(value == "keep" for value in change_decisions.values())
    same_framework = (
        final_change_order == initial_changes
        and final_capabilities == initial_capabilities
        and set(framework_overlay) == initial_overlay
    )
    if "reorder" in change_decisions.values() and final_change_order == initial_changes:
        raise ValueError("reorder decision要求final Change顺序发生变化")
    if status == "accepted" and (not all_keep or not same_framework):
        raise ValueError("accepted要求所有initial unit为keep且final framework集合、顺序、overlay与Phase 1一致")
    if status == "adjusted" and all_keep and same_framework:
        raise ValueError("adjusted要求至少一个可追溯的framework调整")
    return status


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


def render_anchor_index(
    changes: Sequence[ChangeDef],
    mapping: Dict[str, Mapping],
    repo_root: Path,
    anchors: Path,
) -> str:
    lines = [
        "# Final Change Packet Index", "",
        "| Change | Packet | Direct GA | Non-direct GA | Capability Views |",
        "| --- | --- | --- | --- | --- |",
    ]
    for change in changes:
        packet_path = anchors / change.slug / f"{change.slug}.md"
        direct_ids = sorted(ga for ga, row in mapping.items() if row.owner_change == change.slug and row.relation == "direct")
        non_direct_ids = sorted(ga for ga, row in mapping.items() if row.owner_change == change.slug and row.relation != "direct")
        capabilities = sorted({
            row.target_capability
            for row in mapping.values()
            if row.owner_change == change.slug and row.relation == "direct" and row.projection in SPEC_PROJECTIONS
        })
        cap_paths = [
            rel(anchors / change.slug / "capability-anchors" / f"{capability}.md", repo_root)
            for capability in capabilities
        ]
        lines.append(
            f"| {code(change.slug)} | {code(rel(packet_path, repo_root))} | "
            f"{md(', '.join(direct_ids))} | {md(', '.join(non_direct_ids))} | {md(', '.join(cap_paths))} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def validate_refit_mapping_crosscheck(data: Dict[str, object], mapping: Dict[str, Mapping]) -> None:
    """校验 refit gap disposition 与最终 GA owner/target 映射。"""
    for row in data.get("unassigned-and-gap-reviews", []):
        if not isinstance(row, dict):
            continue
        ga = normalize_code(row.get("global-atom-id"))
        mapped = mapping.get(ga)
        if mapped is None:
            raise ValueError(f"refit trace中的{ga}缺少atom mapping")
        final_capability = normalize_code(row.get("final-capability"))
        if mapped.owner_change != normalize_code(row.get("final-change")):
            raise ValueError(f"{ga} refit final Change与atom mapping owner不一致")
        if mapped.target_capability != final_capability:
            raise ValueError(f"{ga} refit final Capability与atom mapping target不一致")


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
    refit_path = work / "framework-refit-trace.json"
    review_path = work / "plan-refit-review.md"
    mapping_path = work / "atom-plan-mapping.json"
    changes, capabilities, overlay = parse_final_plan(plan_path)
    refit = load_framework_refit(refit_path)
    status = validate_framework_refit(orchestrate_dir, refit, changes, capabilities, overlay)
    if status not in TERMINAL_STATUSES:
        raise ValueError("mechanical helper只处理accepted/adjusted framework refit trace")
    evidence = load_evidence(orchestrate_dir)
    mapping = load_mapping(mapping_path)
    validate_mapping(evidence, mapping, changes, capabilities, overlay)
    validate_refit_mapping_crosscheck(refit, mapping)
    clean_legacy(orchestrate_dir)

    review_path.write_text(render_framework_refit_review(orchestrate_dir, refit_path), encoding="utf-8")
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
    (anchors / "index.md").write_text(render_anchor_index(changes, mapping, repo_root, anchors), encoding="utf-8")
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
        "framework-refit-trace-path": rel(refit_path, repo_root),
        "framework-refit-trace-sha256": sha256_file(refit_path),
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
    changes, capabilities, overlay = parse_final_plan(plan)
    refit_path = work / "framework-refit-trace.json"
    refit = load_framework_refit(refit_path)
    validate_framework_refit(orchestrate_dir, refit, changes, capabilities, overlay)
    if plan.read_bytes() != (orchestrate_dir / "change-plan.md").read_bytes():
        raise ValueError("根change-plan.md与Phase 5 plan不一致")
    review_path = work / "plan-refit-review.md"
    if review_path.read_text(encoding="utf-8") != render_framework_refit_review(orchestrate_dir, refit_path):
        raise ValueError("plan refit review Markdown drift")
    mapping_path = work / "atom-plan-mapping.json"
    evidence = load_evidence(orchestrate_dir)
    mapping = load_mapping(mapping_path)
    validate_mapping(evidence, mapping, changes, capabilities, overlay)
    validate_refit_mapping_crosscheck(refit, mapping)
    expected_mapping_md = render_atom_plan_mapping(orchestrate_dir, mapping_path)
    if (work / "atom-plan-mapping.md").read_text(encoding="utf-8") != expected_mapping_md:
        raise ValueError("atom plan mapping Markdown drift")
    baseline_path = work / "capability-baseline-reconciliation.json"
    if require_json(baseline_path, CAPABILITY_BASELINE_SCHEMA) != build_baseline(repo_root, changes, capabilities, mapping):
        raise ValueError("Capability baseline JSON drift")
    if (work / "capability-baseline-reconciliation.md").read_text(encoding="utf-8") != render_capability_baseline(orchestrate_dir, baseline_path):
        raise ValueError("Capability baseline Markdown drift")
    packet_index = require_json(work / "final-packet-index.json", FINAL_PACKET_INDEX_SCHEMA)
    indexed_changes: set[str] = set()
    for packet in packet_index.get("packets", []):
        if not isinstance(packet, dict):
            raise ValueError("final packet index row非法")
        packet_path = repo_root / str(packet.get("packet-path", ""))
        if not packet_path.is_file() or sha256_file(packet_path) != packet.get("packet-digest"):
            raise ValueError(f"final packet缺失或digest drift：{packet_path}")
        slug = normalize_code(packet.get("change"))
        indexed_changes.add(slug)
        change = next((item for item in changes if item.slug == slug), None)
        if change is None or packet_path.read_text(encoding="utf-8") != render_packet(change, evidence, mapping):
            raise ValueError(f"final packet内容drift：{packet_path}")
        expected_caps = sorted({
            row.target_capability
            for row in mapping.values()
            if row.owner_change == slug and row.relation == "direct" and row.projection in SPEC_PROJECTIONS
        })
        expected_cap_paths = [
            rel(packet_path.parent / "capability-anchors" / f"{capability}.md", repo_root)
            for capability in expected_caps
        ]
        if packet.get("capability-view-paths") != expected_cap_paths:
            raise ValueError(f"Capability view index drift：{slug}")
        for capability, cap_rel in zip(expected_caps, expected_cap_paths):
            cap_path = repo_root / cap_rel
            if not cap_path.is_file() or cap_path.read_text(encoding="utf-8") != render_capability_view(slug, capability, evidence, mapping):
                raise ValueError(f"Capability view drift：{cap_path}")
    if indexed_changes != {item.slug for item in changes}:
        raise ValueError("final packet index Change集合与final plan不一致")
    anchors = orchestrate_dir / "change-capability-anchors"
    if (anchors / "index.md").read_text(encoding="utf-8") != render_anchor_index(changes, mapping, repo_root, anchors):
        raise ValueError("anchor index Markdown drift")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从final plan/refit JSON/mapping机械生成Phase 5派生产物。")
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
            refit_path = args.orchestrate_dir / "phase-works/phase-5/framework-refit-trace.json"
            mapping_path = args.orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
            changes, capabilities, overlay = parse_final_plan(plan)
            refit = load_framework_refit(refit_path)
            validate_framework_refit(args.orchestrate_dir, refit, changes, capabilities, overlay)
            evidence = load_evidence(args.orchestrate_dir)
            mapping = load_mapping(mapping_path)
            validate_mapping(evidence, mapping, changes, capabilities, overlay)
            validate_refit_mapping_crosscheck(refit, mapping)
        if args.validate_rendered:
            validate_outputs(args.orchestrate_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("Phase 5 mechanical derivation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
