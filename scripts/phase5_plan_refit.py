#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 5 机械派生器与targeted evidence patch checkpoint 呈现器。

语义权威是 final change-plan.md、framework-refit-trace.json 和
atom-plan-mapping.json；plan-refit-review.md 只是 JSON mirror。
本脚本不接受 semantic config，不推断 framework，不补写 acceptance/dependency/archive 文案。
targeted patch / blocked 状态下只校验引用、渲染 review 并发布非终态 trace。
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
    EVIDENCE_PATCH_REQUEST_SCHEMA,
    EVIDENCE_COLLECTION_INDEX_SCHEMA,
    FINAL_PACKET_INDEX_SCHEMA,
    FRAMEWORK_REFIT_TRACE_SCHEMA,
    GLOBAL_ATOM_ID_RE,
    GLOBAL_ATOM_INDEX_SCHEMA,
    KEBAB_CASE_RE,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    PHASE5_CHECKPOINT_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    canonical_json_sha256,
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
TARGETED_PATCH_STATUS = "needs-targeted-evidence-patch"
NONTERMINAL_STATUSES = {TARGETED_PATCH_STATUS, "blocked"}
NONE_VALUES = {"", "none", "null", "None", "NULL"}
CAPABILITY_REVIEW_DECISIONS = {"keep", "split", "merge", "remove", "rename"}
CHANGE_REVIEW_DECISIONS = {"keep", "split", "merge", "scope-adjusted", "remove", "rename", "reorder"}
PATCH_HISTORY_FIELDS = {
    "request-id", "patch-request-ref", "checkpoint-ref", "finding-fingerprint", "status",
}
PATCH_HISTORY_STATUSES = {"requested", "closed", "blocked"}

# 与 references/change-capability-framework-principles.md 的顺序严格一致。
# 测试 fixture 与其他 validator 应直接复用这些 tuple，避免 gate 名称漂移。
CAPABILITY_INITIAL_GATE_NAMES = (
    "domain-basis",
    "purpose",
    "behavior-first",
    "cohesion",
    "owns-excludes",
    "implementation-substitution",
    "archive-durability",
    "delta-feasibility",
)
CHANGE_INITIAL_GATE_NAMES = (
    "one-intent",
    "scope-cohesion",
    "independent-decision-archive",
    "indivisibility",
    "acceptance",
    "implementation-readiness",
)


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


def framework_semantic_digest_rows(
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """为checkpoint生成可按final ID保护的framework语义row digest。"""
    change_rows: List[Dict[str, str]] = []
    for change in changes:
        payload = {
            "final-change": change.slug,
            "intent": change.intent,
            "outcome": change.outcome,
            "source-hint": change.source_hint,
            "scope-in": change.scope_in,
            "scope-out": change.scope_out,
            "trigger": change.trigger,
            "normative-behavior": change.normative_behavior,
            "observable-outcome": change.observable_outcome,
            "exception-semantics": change.exception_semantics,
            "acceptance": change.acceptance,
            "dependencies": change.dependencies_raw,
            "ordering-reason": change.ordering_reason,
            "archive-condition": change.archive_condition,
            "split-merge-judgment": change.split_merge_judgment,
        }
        change_rows.append({
            "final-change": change.slug,
            "sha256": canonical_json_sha256(payload),
        })
    capability_rows: List[Dict[str, str]] = []
    for capability in capabilities:
        payload = {
            "final-capability": capability.slug,
            "purpose": capability.purpose,
            "owns": capability.owns,
            "excludes": capability.excludes,
            "boundary-rationale": capability.rationale,
        }
        capability_rows.append({
            "final-capability": capability.slug,
            "sha256": canonical_json_sha256(payload),
        })
    return change_rows, capability_rows


def framework_dependency_edges(changes: Sequence[ChangeDef]) -> List[Dict[str, str]]:
    """按provisional roadmap顺序冻结final Change hard-dependency拓扑。"""
    positions = {change.slug: index for index, change in enumerate(changes)}
    return [
        {"change": change.slug, "depends-on": dependency}
        for change in changes
        for dependency in sorted(change.dependencies, key=lambda item: positions[item])
    ]


def framework_review_lineage(
    refit: Dict[str, object],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    """冻结每个initial review unit在patch前产生的provisional final IDs。"""
    change_lineage = [
        {
            "input-change": normalize_code(row.get("input-change")),
            "provisional-final-changes": list(row.get("final-changes", [])),
        }
        for row in refit.get("change-reviews", [])
        if isinstance(row, dict) and isinstance(row.get("final-changes"), list)
    ]
    capability_lineage = [
        {
            "input-capability": normalize_code(row.get("input-capability")),
            "provisional-final-capabilities": list(row.get("final-capabilities", [])),
        }
        for row in refit.get("capability-reviews", [])
        if isinstance(row, dict) and isinstance(row.get("final-capabilities"), list)
    ]
    return change_lineage, capability_lineage


def framework_ga_lineage(mapping_rows: object) -> List[Dict[str, object]]:
    """冻结existing GA对provisional final framework的最小provenance。"""
    return [
        {
            "global-atom-id": normalize_code(row.get("global-atom-id")),
            "provisional-final-change": normalize_code(row.get("final-owner-change")),
            "provisional-final-capability": normalize_code(row.get("final-target-capability")),
            "provisional-related-capabilities": list(row.get("related-capabilities", [])),
        }
        for row in mapping_rows if isinstance(mapping_rows, list) and isinstance(row, dict)
    ] if isinstance(mapping_rows, list) else []


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


def _validate_initial_gate_results(
    value: object,
    expected_gates: Sequence[str],
    where: str,
) -> bool:
    """校验完整、固定顺序的initial gate快照，并返回是否存在failed gate。"""
    if not isinstance(value, list):
        raise ValueError(f"{where}.initial-gate-results必须是array")
    actual_gates: List[str] = []
    has_failed = False
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{where}.initial-gate-results[{index}]必须是object")
        _require_exact_fields(
            item,
            {"gate", "result", "note"},
            f"{where}.initial-gate-results[{index}]",
        )
        gate = normalize_code(item.get("gate"))
        result = normalize_code(item.get("result"))
        actual_gates.append(gate)
        if result not in {"passed", "failed"}:
            raise ValueError(f"{where}.initial-gate-results[{index}].result非法")
        note = squash(item.get("note"))
        if not note or not re.search(r"[\u4e00-\u9fff]", note):
            raise ValueError(
                f"{where}.initial-gate-results[{index}].note必须使用简体中文解释"
            )
        has_failed = has_failed or result == "failed"
    if tuple(actual_gates) != tuple(expected_gates):
        raise ValueError(
            f"{where}.initial-gate-results必须完整按固定顺序覆盖共享gate；"
            f"期望={list(expected_gates)}，实际={actual_gates}"
        )
    return has_failed


def _validate_supporting_global_atom_ids(
    value: object,
    *,
    where: str,
    decision: str,
    collection_ga_ids: Sequence[str],
    global_positions: Dict[str, int],
    has_failed_gate: bool,
) -> List[str]:
    """校验review的source-backed supporting GA及唯一空集合例外。"""
    if not isinstance(value, list):
        raise ValueError(f"{where}.supporting-global-atom-ids必须是array")
    result = [normalize_code(item) for item in value]
    if any(not GLOBAL_ATOM_ID_RE.fullmatch(item) for item in result):
        raise ValueError(f"{where}.supporting-global-atom-ids必须只包含GA ID")
    if len(result) != len(set(result)):
        raise ValueError(f"{where}.supporting-global-atom-ids不得重复")
    if any(item not in global_positions for item in result):
        raise ValueError(f"{where}.supporting-global-atom-ids包含未知GA")
    if result != sorted(result, key=global_positions.__getitem__):
        raise ValueError(f"{where}.supporting-global-atom-ids必须按global index顺序排列")
    allowed = set(collection_ga_ids)
    outside = [item for item in result if item not in allowed]
    if outside:
        raise ValueError(f"{where}.supporting-global-atom-ids跨出对应Phase 4 collection：{outside}")
    if decision == "keep":
        if has_failed_gate:
            raise ValueError(f"{where} keep要求全部initial gate通过")
        if result:
            raise ValueError(f"{where} keep要求supporting-global-atom-ids为空")
    elif not result:
        empty_collection_exception = (
            decision in {"remove", "merge"}
            and not collection_ga_ids
            and has_failed_gate
        )
        if not empty_collection_exception:
            raise ValueError(
                f"{where} 非keep决定必须引用对应collection中的supporting GA；"
                "只有零GA collection的remove/merge且initial gate失败时允许为空"
            )
    return result


def load_framework_refit(path: Path) -> Dict[str, object]:
    return require_json(path, FRAMEWORK_REFIT_TRACE_SCHEMA)


def _validate_artifact_ref(
    orchestrate_dir: Path,
    value: object,
    where: str,
    expected_path: Path,
    expected_schema: str,
) -> Dict[str, object]:
    """校验 patch lifecycle 引用，但不重做 request/checkpoint 内的语义。"""
    if not isinstance(value, dict):
        raise ValueError(f"{where}必须是object")
    _require_exact_fields(value, {"artifact-path", "sha256"}, where)
    repo_root = repo_root_for(orchestrate_dir)
    expected_relative = rel(expected_path, repo_root)
    if value.get("artifact-path") != expected_relative:
        raise ValueError(f"{where}.artifact-path应为{expected_relative}")
    if not expected_path.is_file():
        raise ValueError(f"{where}引用的artifact不存在：{expected_relative}")
    require_json(expected_path, expected_schema)
    actual_digest = sha256_file(expected_path)
    if value.get("sha256") != actual_digest:
        raise ValueError(f"{where}.sha256与当前artifact不一致")
    return dict(value)


def _validate_patch_history(
    orchestrate_dir: Path,
    value: object,
    status: str,
) -> List[Dict[str, object]]:
    if not isinstance(value, list):
        raise ValueError("patch-history必须是array")
    work = orchestrate_dir / "phase-works/phase-5"
    request_path = work / "evidence-patch-request.json"
    checkpoint_path = work / "phase-5-checkpoint.json"
    rows: List[Dict[str, object]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"patch-history[{index}]必须是object")
        _require_exact_fields(item, PATCH_HISTORY_FIELDS, f"patch-history[{index}]")
        request_id = normalize_code(item.get("request-id"))
        fingerprint = normalize_code(item.get("finding-fingerprint"))
        row_status = normalize_code(item.get("status"))
        if not request_id or not fingerprint or row_status not in PATCH_HISTORY_STATUSES:
            raise ValueError(f"patch-history[{index}] request-id/finding-fingerprint/status非法")
        _validate_artifact_ref(
            orchestrate_dir,
            item.get("patch-request-ref"),
            f"patch-history[{index}].patch-request-ref",
            request_path,
            EVIDENCE_PATCH_REQUEST_SCHEMA,
        )
        _validate_artifact_ref(
            orchestrate_dir,
            item.get("checkpoint-ref"),
            f"patch-history[{index}].checkpoint-ref",
            checkpoint_path,
            PHASE5_CHECKPOINT_SCHEMA,
        )
        rows.append(dict(item))

    row_statuses = [normalize_code(row.get("status")) for row in rows]
    if status == TARGETED_PATCH_STATUS and (len(rows) != 1 or row_statuses != ["requested"]):
        raise ValueError(f"{TARGETED_PATCH_STATUS}要求patch-history恰好一条requested")
    if status in TERMINAL_STATUSES and row_statuses not in ([], ["closed"]):
        raise ValueError("terminal refit的patch-history必须为空，或恰好一条closed")
    if status == "blocked" and row_statuses not in ([], ["blocked"]):
        raise ValueError("blocked refit的patch-history只允许为空，或恰好一条blocked")
    return rows


def validate_framework_refit(
    orchestrate_dir: Path,
    data: Dict[str, object],
    changes: Optional[Sequence[ChangeDef]] = None,
    capabilities: Optional[Sequence[CapabilityDef]] = None,
    overlay: Optional[Dict[Tuple[str, str], str]] = None,
    *,
    verify_current_inputs: bool = True,
) -> str:
    """校验 refit trace 的结构、基数及与 final plan 的 framework 一致性。"""
    _require_exact_fields(data, {
        "trace-schema", "trace-contract-version", "status", "initial-plan-ref",
        "capability-reviews", "change-reviews", "unassigned-and-gap-reviews",
        "final-framework", "issues", "patch-history", "language-self-check",
    }, "framework-refit-trace")
    if data.get("trace-schema") != FRAMEWORK_REFIT_TRACE_SCHEMA:
        raise ValueError(f"framework-refit-trace trace-schema必须是{FRAMEWORK_REFIT_TRACE_SCHEMA}")
    if data.get("trace-contract-version") != TRACE_CONTRACT_VERSION:
        raise ValueError(f"framework-refit-trace trace-contract-version必须是{TRACE_CONTRACT_VERSION}")
    status = normalize_code(data.get("status"))
    if status not in TERMINAL_STATUSES | NONTERMINAL_STATUSES:
        raise ValueError(f"framework refit status非法：{status}")
    repo_root = repo_root_for(orchestrate_dir)
    initial_path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    initial_ref = data.get("initial-plan-ref")
    if not isinstance(initial_ref, dict):
        raise ValueError("initial-plan-ref必须是object")
    _require_exact_fields(initial_ref, {"artifact-path", "sha256"}, "initial-plan-ref")
    if initial_ref.get("artifact-path") != rel(initial_path, repo_root):
        raise ValueError("initial-plan-ref path与Phase 1 canonical path不一致")
    initial_digest = normalize_code(initial_ref.get("sha256"))
    if not re.fullmatch(r"[0-9a-f]{64}", initial_digest):
        raise ValueError("initial-plan-ref sha256非法")
    if verify_current_inputs and initial_digest != sha256_file(initial_path):
        raise ValueError("initial-plan-ref digest与Phase 1 initial plan不一致")
    if verify_current_inputs or status in TERMINAL_STATUSES:
        initial_changes, initial_capabilities, initial_overlay = _phase1_framework(orchestrate_dir)
    else:
        # patch lifecycle abort只验证冻结refit内部结构；current authority drift正是blocked原因。
        initial_changes, initial_capabilities, initial_overlay = [], [], {}

    capability_rows = data.get("capability-reviews")
    change_rows = data.get("change-reviews")
    gap_rows = data.get("unassigned-and-gap-reviews")
    if not isinstance(capability_rows, list) or not isinstance(change_rows, list) or not isinstance(gap_rows, list):
        raise ValueError("三个review集合必须是array")
    issues = data.get("issues")
    if not isinstance(issues, list):
        raise ValueError("issues必须是array")
    language = squash(data.get("language-self-check"))
    if not language or not re.search(r"[\u4e00-\u9fff]", language):
        raise ValueError("language-self-check必须使用简体中文解释")
    _validate_patch_history(orchestrate_dir, data.get("patch-history"), status)
    if status in NONTERMINAL_STATUSES:
        if data.get("final-framework") is not None or not issues:
            raise ValueError(f"{status}要求final-framework=null且issues非空")
        return status

    collection_path = (
        orchestrate_dir
        / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
    )
    collection = require_json(collection_path, EVIDENCE_COLLECTION_INDEX_SCHEMA)
    collection_rows = collection.get("rows")
    if not isinstance(collection_rows, list):
        raise ValueError("Phase 4 evidence collection index rows必须是array")
    global_index_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    global_index = require_json(global_index_path, GLOBAL_ATOM_INDEX_SCHEMA)
    global_rows = global_index.get("global-atoms")
    if not isinstance(global_rows, list):
        raise ValueError("global atom index global-atoms必须是array")
    global_order = [
        normalize_code(row.get("global-atom-id"))
        for row in global_rows
        if isinstance(row, dict)
    ]
    if any(not GLOBAL_ATOM_ID_RE.fullmatch(ga) for ga in global_order) or len(global_order) != len(set(global_order)):
        raise ValueError("global atom index GA顺序非法")
    global_positions = {ga: index for index, ga in enumerate(global_order)}
    change_collection_ga_ids: Dict[str, List[str]] = defaultdict(list)
    capability_collection_ga_ids: Dict[str, List[str]] = defaultdict(list)
    for row in collection_rows:
        if not isinstance(row, dict):
            raise ValueError("Phase 4 evidence collection index row必须是object")
        ga = normalize_code(row.get("global-atom-id"))
        if ga not in global_positions:
            raise ValueError(f"Phase 4 evidence collection index引用未知GA：{ga}")
        change_collection_ga_ids[normalize_code(row.get("change-bucket"))].append(ga)
        capability = normalize_code(row.get("capability-bucket"))
        if capability != "none":
            capability_collection_ga_ids[capability].append(ga)

    capability_decisions: Dict[str, str] = {}
    for index, row in enumerate(capability_rows):
        if not isinstance(row, dict):
            raise ValueError(f"capability-reviews[{index}]必须是object")
        _require_exact_fields(row, {
            "input-capability", "evidence-collection-path", "decision", "final-capabilities",
            "initial-gate-results", "supporting-global-atom-ids", "reason",
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
        where = f"capability-reviews[{index}]"
        has_failed_gate = _validate_initial_gate_results(
            row.get("initial-gate-results"),
            CAPABILITY_INITIAL_GATE_NAMES,
            where,
        )
        _validate_supporting_global_atom_ids(
            row.get("supporting-global-atom-ids"),
            where=where,
            decision=decision,
            collection_ga_ids=capability_collection_ga_ids[source],
            global_positions=global_positions,
            has_failed_gate=has_failed_gate,
        )
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
            "input-change", "evidence-collection-path", "decision", "final-changes",
            "initial-gate-results", "supporting-global-atom-ids", "reason",
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
        where = f"change-reviews[{index}]"
        has_failed_gate = _validate_initial_gate_results(
            row.get("initial-gate-results"),
            CHANGE_INITIAL_GATE_NAMES,
            where,
        )
        _validate_supporting_global_atom_ids(
            row.get("supporting-global-atom-ids"),
            where=where,
            decision=decision,
            collection_ga_ids=change_collection_ga_ids[source],
            global_positions=global_positions,
            has_failed_gate=has_failed_gate,
        )
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

    expected_gap = {
        normalize_code(row.get("global-atom-id")): row.get("evidence-ref")
        for row in collection_rows
        if isinstance(row, dict) and normalize_code(row.get("change-bucket")) == "unassigned-and-gap"
    }
    seen_gap: set[str] = set()
    for index, row in enumerate(gap_rows):
        if not isinstance(row, dict):
            raise ValueError(f"unassigned-and-gap-reviews[{index}]必须是object")
        _require_exact_fields(row, {
            "global-atom-id", "evidence-ref", "framework-impact", "reason",
        }, f"unassigned-and-gap-reviews[{index}]")
        ga = normalize_code(row.get("global-atom-id"))
        if ga in seen_gap or ga not in expected_gap:
            raise ValueError(f"unassigned/gap GA未知或重复：{ga}")
        seen_gap.add(ga)
        if row.get("evidence-ref") != expected_gap[ga]:
            raise ValueError(f"{ga} evidence-ref与Phase 4 index不一致")
        if normalize_code(row.get("framework-impact")) not in {"none", "supports-adjustment"}:
            raise ValueError(f"{ga} framework-impact必须为none或supports-adjustment")
        if not squash(row.get("reason")) or not re.search(r"[\u4e00-\u9fff]", str(row.get("reason"))):
            raise ValueError(f"{ga} reason必须使用简体中文解释")
    if seen_gap != set(expected_gap):
        raise ValueError(f"每个unassigned/gap GA必须恰好一行；缺少={sorted(set(expected_gap)-seen_gap)}")

    if issues:
        raise ValueError(f"{status}要求issues为空")
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
    all_keep = all(value == "keep" for value in capability_decisions.values()) and all(value == "keep" for value in change_decisions.values())
    same_framework = (
        final_change_order == initial_changes
        and final_capabilities == initial_capabilities
        and set(framework_overlay) == initial_overlay
    )
    if "reorder" in change_decisions.values() and final_change_order == initial_changes:
        raise ValueError("reorder decision要求final Change顺序发生变化")
    if status == "accepted" and (
        not all_keep
        or not same_framework
        or any(normalize_code(row.get("framework-impact")) != "none" for row in gap_rows)
    ):
        raise ValueError(
            "accepted要求所有initial unit为通过全部gate的keep、所有gap impact为none，"
            "且final framework集合、顺序、overlay与Phase 1一致"
        )
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
    *,
    repo_root: Path,
) -> None:
    if set(mapping) != set(evidence):
        raise ValueError(f"mapping GA集合不一致；缺少={sorted(set(evidence)-set(mapping))}，多余={sorted(set(mapping)-set(evidence))}")
    change_ids = {change.slug for change in changes}
    capability_ids = {capability.slug for capability in capabilities}
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
    expected_overlay, _ = derive_advancement(
        repo_root,
        changes,
        capabilities,
        mapping,
    )
    if expected_overlay != overlay:
        raise ValueError(
            f"final plan overlay与确定性advancement derivation不一致；"
            f"plan={overlay} derived={expected_overlay}"
        )


def derive_advancement(
    repo_root: Path,
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    mapping: Dict[str, Mapping],
) -> Tuple[Dict[Tuple[str, str], str], Dict[str, object]]:
    """从final顺序、direct spec mapping与repository baseline派生唯一edge和baseline。"""
    cap_defs = {capability.slug: capability for capability in capabilities}
    by_change_target: Dict[Tuple[str, str], set[str]] = defaultdict(set)
    for row in mapping.values():
        if row.relation == "direct" and row.projection in SPEC_PROJECTIONS:
            by_change_target[(row.owner_change, row.target_capability)].add(row.capability_impact)
    derived_overlay: Dict[Tuple[str, str], str] = {}
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
            derived_overlay[(change.slug, target)] = expected
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
    baseline = {
        "trace-schema": CAPABILITY_BASELINE_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "repository-specs-root": "openspec/specs",
        "capabilities": rows,
    }
    return derived_overlay, baseline


def build_baseline(
    repo_root: Path,
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    mapping: Dict[str, Mapping],
) -> Dict[str, object]:
    """兼容调用入口；baseline与overlay均由derive_advancement一次性产生。"""
    _, baseline = derive_advancement(repo_root, changes, capabilities, mapping)
    return baseline


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


def validate_gap_framework_impacts(
    orchestrate_dir: Path,
    data: Dict[str, object],
    mapping: Dict[str, Mapping],
) -> None:
    """校验gap impact的机械依据，不在refit中复制mapping owner/target。"""
    initial_changes, initial_capabilities, initial_overlay = _phase1_framework(orchestrate_dir)
    final_framework = data.get("final-framework")
    if not isinstance(final_framework, dict):
        return
    new_change_ids = {
        normalize_code(item)
        for item in final_framework.get("change-order", [])
        if normalize_code(item) not in set(initial_changes)
    }
    new_capability_ids = {
        normalize_code(item)
        for item in final_framework.get("capabilities", [])
        if normalize_code(item) not in set(initial_capabilities)
    }
    supporting_ga_ids = {
        normalize_code(ga)
        for review in [
            *data.get("capability-reviews", []),
            *data.get("change-reviews", []),
        ]
        if isinstance(review, dict) and normalize_code(review.get("decision")) != "keep"
        for ga in review.get("supporting-global-atom-ids", [])
    }
    reviewed_final_changes = {
        normalize_code(item)
        for review in data.get("change-reviews", [])
        if isinstance(review, dict)
        for item in review.get("final-changes", [])
    }
    reviewed_final_capabilities = {
        normalize_code(item)
        for review in data.get("capability-reviews", [])
        if isinstance(review, dict)
        for item in review.get("final-capabilities", [])
    }
    gap_mapped_new_changes: set[str] = set()
    gap_mapped_new_capabilities: set[str] = set()
    for row in data.get("unassigned-and-gap-reviews", []):
        if not isinstance(row, dict):
            continue
        ga = normalize_code(row.get("global-atom-id"))
        mapped = mapping.get(ga)
        if mapped is None:
            raise ValueError(f"refit trace中的{ga}缺少atom mapping")
        if normalize_code(row.get("framework-impact")) != "supports-adjustment":
            continue
        if mapped.owner_change in new_change_ids:
            gap_mapped_new_changes.add(mapped.owner_change)
        if mapped.target_capability in new_capability_ids:
            gap_mapped_new_capabilities.add(mapped.target_capability)
        maps_to_new_final_id = (
            mapped.owner_change in new_change_ids
            or mapped.target_capability in new_capability_ids
        )
        creates_new_advancement_edge = (
            mapped.relation == "direct"
            and mapped.projection in SPEC_PROJECTIONS
            and (mapped.owner_change, mapped.target_capability) not in initial_overlay
        )
        if (
            ga not in supporting_ga_ids
            and not maps_to_new_final_id
            and not creates_new_advancement_edge
        ):
            raise ValueError(
                f"{ga} supports-adjustment必须关联非keep review、映射到新增final ID，"
                "或产生Phase 1不存在的advancement edge"
            )
    untraced_changes = new_change_ids - reviewed_final_changes - gap_mapped_new_changes
    untraced_capabilities = (
        new_capability_ids - reviewed_final_capabilities - gap_mapped_new_capabilities
    )
    if untraced_changes or untraced_capabilities:
        raise ValueError(
            "新增final unit缺少initial review lineage或supports-adjustment gap mapping；"
            f"Changes={sorted(untraced_changes)}，Capabilities={sorted(untraced_capabilities)}"
        )


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


def _remove_terminal_outputs_for_patch(orchestrate_dir: Path) -> None:
    """进入 targeted patch checkpoint 时移除旧 terminal surface，保留 request/checkpoint/refit。"""
    work = orchestrate_dir / "phase-works/phase-5"
    for name in (
        "change-plan.md",
        "atom-plan-mapping.json",
        "atom-plan-mapping.md",
        "capability-baseline-reconciliation.json",
        "capability-baseline-reconciliation.md",
        "final-packet-index.json",
    ):
        path = work / name
        if path.exists():
            path.unlink()
    root_plan = orchestrate_dir / "change-plan.md"
    if root_plan.exists():
        root_plan.unlink()
    anchors = orchestrate_dir / "change-capability-anchors"
    if anchors.exists():
        for child in anchors.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
        final_index = anchors / "index.md"
        if final_index.exists():
            final_index.unlink()


def _patch_trace_payload(
    orchestrate_dir: Path,
    refit: Dict[str, object],
    refit_path: Path,
    review_path: Path,
) -> Dict[str, object]:
    repo_root = repo_root_for(orchestrate_dir)
    history = refit.get("patch-history")
    if not isinstance(history, list) or len(history) != 1 or not isinstance(history[0], dict):
        raise ValueError("targeted patch trace要求恰好一条patch-history")
    patch_ref = history[0].get("patch-request-ref")
    checkpoint_ref = history[0].get("checkpoint-ref")
    if not isinstance(patch_ref, dict) or not isinstance(checkpoint_ref, dict):
        raise ValueError("targeted patch trace缺少request/checkpoint ref")
    return {
        "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "status": TARGETED_PATCH_STATUS,
        "execution-mode": "initial",
        "framework-refit-trace-path": rel(refit_path, repo_root),
        "framework-refit-trace-sha256": sha256_file(refit_path),
        "plan-refit-review-path": rel(review_path, repo_root),
        "plan-refit-review-sha256": sha256_file(review_path),
        "evidence-patch-request-path": patch_ref.get("artifact-path"),
        "evidence-patch-request-sha256": patch_ref.get("sha256"),
        "phase-5-checkpoint-path": checkpoint_ref.get("artifact-path"),
        "phase-5-checkpoint-sha256": checkpoint_ref.get("sha256"),
        "patch-history": [dict(history[0])],
        "issues": list(refit.get("issues", [])),
    }


def _blocked_trace_payload(
    orchestrate_dir: Path,
    refit: Dict[str, object],
    refit_path: Path,
    review_path: Path,
) -> Dict[str, object]:
    """构造普通 blocked 或 checkpoint-resume blocked 的最小 trace。"""
    repo_root = repo_root_for(orchestrate_dir)
    history = refit.get("patch-history")
    if not isinstance(history, list):
        raise ValueError("blocked trace要求patch-history array")
    payload: Dict[str, object] = {
        "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "status": "blocked",
        "framework-refit-trace-path": rel(refit_path, repo_root),
        "framework-refit-trace-sha256": sha256_file(refit_path),
        "plan-refit-review-path": rel(review_path, repo_root),
        "plan-refit-review-sha256": sha256_file(review_path),
        "issues": list(refit.get("issues", [])),
    }
    if not history:
        return payload
    if len(history) != 1 or not isinstance(history[0], dict) or normalize_code(history[0].get("status")) != "blocked":
        raise ValueError("patch lifecycle blocked要求patch-history恰好一条blocked")
    patch_ref = history[0].get("patch-request-ref")
    checkpoint_ref = history[0].get("checkpoint-ref")
    if not isinstance(patch_ref, dict) or not isinstance(checkpoint_ref, dict):
        raise ValueError("patch lifecycle blocked缺少request/checkpoint ref")
    payload.update({
        "execution-mode": "checkpoint-resume",
        "evidence-patch-request-path": patch_ref.get("artifact-path"),
        "evidence-patch-request-sha256": patch_ref.get("sha256"),
        "phase-5-checkpoint-path": checkpoint_ref.get("artifact-path"),
        "phase-5-checkpoint-sha256": checkpoint_ref.get("sha256"),
        "patch-history": [dict(history[0])],
    })
    return payload


def _write_nonterminal_outputs(
    orchestrate_dir: Path,
    refit: Dict[str, object],
    refit_path: Path,
    review_path: Path,
) -> None:
    """发布非终态 review/trace，并清理所有 terminal surface。"""
    clean_legacy(orchestrate_dir)
    _remove_terminal_outputs_for_patch(orchestrate_dir)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(render_framework_refit_review(orchestrate_dir, refit_path), encoding="utf-8")
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    status = normalize_code(refit.get("status"))
    if status == TARGETED_PATCH_STATUS:
        trace_payload = _patch_trace_payload(orchestrate_dir, refit, refit_path, review_path)
    elif status == "blocked":
        trace_payload = _blocked_trace_payload(orchestrate_dir, refit, refit_path, review_path)
    else:
        raise ValueError(f"非终态输出不支持status={status}")
    write_json(trace_path, trace_payload)


def _validate_patch_authorization_before_marker(orchestrate_dir: Path) -> None:
    """复用validator机器权威，在任何清理或commit marker写入前校验完整授权组。"""
    # 延迟导入避免validator在模块加载时反向导入本helper形成循环。
    from validate_source_aligned_orchestrate import validate_patch_authorization_group

    result = validate_patch_authorization_group(
        orchestrate_dir,
        repo_root_for(orchestrate_dir),
    )
    if result.get("ok"):
        return
    messages = [
        f"{issue.get('rule_id')}: {issue.get('message')}"
        for issue in result.get("issues", [])
        if isinstance(issue, dict) and issue.get("severity") == "error"
    ]
    raise ValueError("Phase 5 patch授权组未通过完整机器校验：" + " | ".join(messages))


def _write_targeted_patch_outputs(
    orchestrate_dir: Path,
    refit: Dict[str, object],
    refit_path: Path,
    review_path: Path,
) -> None:
    existing_phase5_trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    if existing_phase5_trace_path.exists():
        existing_phase5_trace = require_json(existing_phase5_trace_path, PHASE_TRACE_SCHEMAS["phase-5"])
        raise ValueError(
            "targeted evidence patch只能在首次Phase 5尚未发布canonical trace时发起；"
            f"现有Phase 5状态{existing_phase5_trace.get('status')!r}不得回退为requested"
        )

    _validate_patch_authorization_before_marker(orchestrate_dir)

    plan_path = orchestrate_dir / "phase-works/phase-5/change-plan.md"
    checkpoint_path = orchestrate_dir / "phase-works/phase-5/phase-5-checkpoint.json"
    if not plan_path.is_file():
        raise ValueError("targeted patch checkpoint发布前必须保留provisional change-plan供机械冻结")
    checkpoint = require_json(checkpoint_path, PHASE5_CHECKPOINT_SCHEMA)
    provisional = checkpoint.get("provisional-framework")
    if not isinstance(provisional, dict):
        raise ValueError("checkpoint provisional-framework必须是object")
    _require_exact_fields(
        provisional,
        {
            "change-order", "capabilities", "overlay",
            "change-semantic-digests", "capability-semantic-digests",
            "dependency-edges", "change-lineage", "capability-lineage", "ga-lineage",
        },
        "checkpoint.provisional-framework",
    )
    changes, capabilities, overlay = parse_final_plan(plan_path)
    expected_change_digests, expected_capability_digests = framework_semantic_digest_rows(
        changes,
        capabilities,
    )
    expected_change_lineage, expected_capability_lineage = framework_review_lineage(refit)
    mapping_path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
    mapping_data = require_json(mapping_path, ATOM_PLAN_MAPPING_SCHEMA)
    expected_overlay = [
        {"change": change, "capability": capability, "capability-impact": impact}
        for (change, capability), impact in overlay.items()
    ]
    expected = {
        "change-order": [change.slug for change in changes],
        "capabilities": [capability.slug for capability in capabilities],
        "overlay": expected_overlay,
        "change-semantic-digests": expected_change_digests,
        "capability-semantic-digests": expected_capability_digests,
        "dependency-edges": framework_dependency_edges(changes),
        "change-lineage": expected_change_lineage,
        "capability-lineage": expected_capability_lineage,
        "ga-lineage": framework_ga_lineage(mapping_data.get("rows")),
    }
    if provisional != expected:
        raise ValueError("checkpoint provisional-framework未逐row绑定发布前provisional change-plan")

    provisional_refit = dict(refit)
    provisional_refit["final-framework"] = {
        "change-order": list(provisional.get("change-order", [])),
        "capabilities": list(provisional.get("capabilities", [])),
        "overlay": list(provisional.get("overlay", [])),
    }
    provisional_refit["issues"] = []
    provisional_refit["patch-history"] = []
    refit_valid = False
    refit_errors: List[str] = []
    for candidate_status in ("accepted", "adjusted"):
        candidate = dict(provisional_refit)
        candidate["status"] = candidate_status
        try:
            validate_framework_refit(
                orchestrate_dir,
                candidate,
                changes,
                capabilities,
                overlay,
            )
        except ValueError as exc:
            refit_errors.append(str(exc))
        else:
            provisional_refit = candidate
            refit_valid = True
            break
    if not refit_valid:
        raise ValueError(
            "checkpoint发布前provisional refit rows无法组成合法terminal snapshot："
            + " | ".join(refit_errors)
        )

    evidence = load_evidence(orchestrate_dir)
    mapping = load_mapping(mapping_path)
    validate_mapping(
        evidence,
        mapping,
        changes,
        capabilities,
        overlay,
        repo_root=repo_root_for(orchestrate_dir),
    )
    validate_gap_framework_impacts(orchestrate_dir, provisional_refit, mapping)

    completed = checkpoint.get("completed-rows")
    pending = checkpoint.get("pending-ids")
    if not isinstance(completed, dict) or not isinstance(pending, dict):
        raise ValueError("checkpoint completed-rows/pending-ids必须是object")
    checkpoint_row_specs = (
        ("capability-reviews", "input-capability", provisional_refit.get("capability-reviews")),
        ("change-reviews", "input-change", provisional_refit.get("change-reviews")),
        ("unassigned-and-gap-reviews", "global-atom-id", provisional_refit.get("unassigned-and-gap-reviews")),
        ("atom-plan-mappings", "global-atom-id", mapping_data.get("rows")),
    )
    for kind, key_field, source_rows in checkpoint_row_specs:
        pending_ids = {
            normalize_code(item)
            for item in pending.get(kind, [])
            if isinstance(item, str)
        }
        expected_completed = [
            row
            for row in source_rows if isinstance(source_rows, list) and isinstance(row, dict)
            if normalize_code(row.get(key_field)) not in pending_ids
        ] if isinstance(source_rows, list) else []
        if completed.get(kind) != expected_completed:
            raise ValueError(
                f"checkpoint completed-rows.{kind}必须逐字复用发布前provisional terminal rows"
            )

    scope = checkpoint.get("allowed-update-scope")
    if not isinstance(scope, dict):
        raise ValueError("checkpoint allowed-update-scope必须是object")
    ga_origins: Dict[str, Dict[str, set[str]]] = {
        "change": defaultdict(set),
        "capability": defaultdict(set),
    }
    for row in provisional.get("ga-lineage", []):
        if not isinstance(row, dict):
            continue
        ga_id = normalize_code(row.get("global-atom-id"))
        change_id = normalize_code(row.get("provisional-final-change"))
        capability_ids = {
            normalize_code(row.get("provisional-final-capability")),
            *(
                normalize_code(item)
                for item in row.get("provisional-related-capabilities", [])
                if isinstance(item, str)
            ),
        } - {"", "none", "null"}
        if change_id not in {"", "none", "null"}:
            ga_origins["change"][change_id].add(ga_id)
        for capability_id in capability_ids:
            ga_origins["capability"][capability_id].add(ga_id)

    lineage_specs = (
        (
            "change-lineage", "input-change", "provisional-final-changes",
            "initial-changes", "final-changes", set(provisional.get("change-order", [])), "change",
        ),
        (
            "capability-lineage", "input-capability", "provisional-final-capabilities",
            "initial-capabilities", "final-capabilities", set(provisional.get("capabilities", [])), "capability",
        ),
    )
    scoped_ga = {
        normalize_code(item) for item in scope.get("global-atom-ids", []) if isinstance(item, str)
    }
    for lineage_field, input_field, output_field, scope_initial_field, scope_final_field, existing_ids, kind in lineage_specs:
        origins: Dict[str, set[str]] = defaultdict(set)
        for row in provisional.get(lineage_field, []):
            if not isinstance(row, dict):
                continue
            origin = normalize_code(row.get(input_field))
            for final_id in row.get(output_field, []) if isinstance(row.get(output_field), list) else []:
                origins[normalize_code(final_id)].add(origin)
        scoped_initial = {
            normalize_code(item) for item in scope.get(scope_initial_field, []) if isinstance(item, str)
        }
        for final_id in scope.get(scope_final_field, []) if isinstance(scope.get(scope_final_field), list) else []:
            normalized_final = normalize_code(final_id)
            if normalized_final not in existing_ids:
                continue
            initial_origins = origins.get(normalized_final, set())
            evidence_origins = ga_origins[kind].get(normalized_final, set())
            if initial_origins:
                authorized = initial_origins.issubset(scoped_initial)
            else:
                authorized = bool(evidence_origins) and evidence_origins.issubset(scoped_ga)
            if not authorized:
                raise ValueError(
                    f"checkpoint {scope_final_field}不得劫持scope外或无provenance的provisional final ID：{normalized_final}"
                )
    _write_nonterminal_outputs(
        orchestrate_dir,
        refit,
        refit_path,
        review_path,
    )


def _write_blocked_outputs(
    orchestrate_dir: Path,
    refit: Dict[str, object],
    refit_path: Path,
    review_path: Path,
) -> None:
    _write_nonterminal_outputs(
        orchestrate_dir,
        refit,
        refit_path,
        review_path,
    )


def abort_patch_lifecycle(orchestrate_dir: Path, issue: str) -> None:
    """将唯一requested patch链机械终止为blocked。

    该control transform只修改refit status、issues和唯一history row的status；
    不重算review/mapping/framework语义row。
    """
    normalized_issue = issue.strip()
    if not normalized_issue:
        raise ValueError("abort patch chain要求非空issue")
    refit_path = orchestrate_dir / "phase-works/phase-5/framework-refit-trace.json"
    refit = load_framework_refit(refit_path)
    if validate_framework_refit(
        orchestrate_dir,
        refit,
        verify_current_inputs=False,
    ) != TARGETED_PATCH_STATUS:
        raise ValueError("abort patch chain只允许从needs-targeted-evidence-patch转移")
    history = refit.get("patch-history")
    if (
        not isinstance(history, list)
        or len(history) != 1
        or not isinstance(history[0], dict)
        or normalize_code(history[0].get("status")) != "requested"
    ):
        raise ValueError("abort patch chain要求恰好一条requested patch-history")

    blocked = dict(refit)
    blocked_history = dict(history[0])
    blocked_history["status"] = "blocked"
    blocked["status"] = "blocked"
    blocked["issues"] = [normalized_issue]
    blocked["patch-history"] = [blocked_history]
    validate_framework_refit(orchestrate_dir, blocked, verify_current_inputs=False)
    write_json(refit_path, blocked)
    write_outputs(orchestrate_dir)


def write_outputs(orchestrate_dir: Path) -> None:
    repo_root = repo_root_for(orchestrate_dir)
    work = orchestrate_dir / "phase-works/phase-5"
    plan_path = work / "change-plan.md"
    refit_path = work / "framework-refit-trace.json"
    review_path = work / "plan-refit-review.md"
    mapping_path = work / "atom-plan-mapping.json"
    refit = load_framework_refit(refit_path)
    raw_status = normalize_code(refit.get("status"))
    raw_history = refit.get("patch-history")
    patch_lifecycle_blocked = (
        raw_status == "blocked"
        and isinstance(raw_history, list)
        and len(raw_history) == 1
        and isinstance(raw_history[0], dict)
        and normalize_code(raw_history[0].get("status")) == "blocked"
    )
    status = validate_framework_refit(
        orchestrate_dir,
        refit,
        verify_current_inputs=not patch_lifecycle_blocked,
    )
    if status == TARGETED_PATCH_STATUS:
        _write_targeted_patch_outputs(orchestrate_dir, refit, refit_path, review_path)
        return
    if status == "blocked":
        _write_blocked_outputs(orchestrate_dir, refit, refit_path, review_path)
        return
    if status not in TERMINAL_STATUSES:
        raise ValueError("mechanical helper只处理accepted/adjusted framework refit trace")
    changes, capabilities, overlay = parse_final_plan(plan_path)
    validate_framework_refit(orchestrate_dir, refit, changes, capabilities, overlay)
    evidence = load_evidence(orchestrate_dir)
    mapping = load_mapping(mapping_path)
    validate_mapping(
        evidence,
        mapping,
        changes,
        capabilities,
        overlay,
        repo_root=repo_root,
    )
    validate_gap_framework_impacts(orchestrate_dir, refit, mapping)
    clean_legacy(orchestrate_dir)
    patch_history = [dict(row) for row in refit.get("patch-history", []) if isinstance(row, dict)]
    if not patch_history:
        for stale_patch_artifact in (work / "evidence-patch-request.json", work / "phase-5-checkpoint.json"):
            if stale_patch_artifact.exists():
                stale_patch_artifact.unlink()

    review_path.write_text(render_framework_refit_review(orchestrate_dir, refit_path), encoding="utf-8")
    mapping_md = work / "atom-plan-mapping.md"
    mapping_md.write_text(render_atom_plan_mapping(orchestrate_dir, mapping_path), encoding="utf-8")
    baseline_path = work / "capability-baseline-reconciliation.json"
    _, baseline = derive_advancement(repo_root, changes, capabilities, mapping)
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
    execution_mode = "checkpoint-resume" if patch_history else "initial"
    terminal_patch_ref = patch_history[0].get("patch-request-ref") if patch_history else None
    terminal_checkpoint_ref = patch_history[0].get("checkpoint-ref") if patch_history else None
    write_json(trace_path, {
        "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "status": status,
        "execution-mode": execution_mode,
        "patch-history": patch_history,
        "evidence-patch-request-path": terminal_patch_ref.get("artifact-path") if isinstance(terminal_patch_ref, dict) else None,
        "evidence-patch-request-sha256": terminal_patch_ref.get("sha256") if isinstance(terminal_patch_ref, dict) else None,
        "phase-5-checkpoint-path": terminal_checkpoint_ref.get("artifact-path") if isinstance(terminal_checkpoint_ref, dict) else None,
        "phase-5-checkpoint-sha256": terminal_checkpoint_ref.get("sha256") if isinstance(terminal_checkpoint_ref, dict) else None,
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
    refit_path = work / "framework-refit-trace.json"
    refit = load_framework_refit(refit_path)
    raw_status = normalize_code(refit.get("status"))
    raw_history = refit.get("patch-history")
    patch_lifecycle_blocked = (
        raw_status == "blocked"
        and isinstance(raw_history, list)
        and len(raw_history) == 1
        and isinstance(raw_history[0], dict)
        and normalize_code(raw_history[0].get("status")) == "blocked"
    )
    status = validate_framework_refit(
        orchestrate_dir,
        refit,
        verify_current_inputs=not patch_lifecycle_blocked,
    )
    review_path = work / "plan-refit-review.md"
    if status == TARGETED_PATCH_STATUS:
        if not review_path.is_file() or review_path.read_text(encoding="utf-8") != render_framework_refit_review(orchestrate_dir, refit_path):
            raise ValueError("targeted patch plan refit review Markdown drift")
        trace_path = orchestrate_dir / "trace/phase-5.trace.json"
        trace = require_json(trace_path, PHASE_TRACE_SCHEMAS["phase-5"])
        expected_trace = _patch_trace_payload(orchestrate_dir, refit, refit_path, review_path)
        if trace != expected_trace:
            raise ValueError("targeted patch Phase 5 trace drift")
        forbidden = [
            work / "change-plan.md",
            work / "atom-plan-mapping.json",
            work / "atom-plan-mapping.md",
            work / "capability-baseline-reconciliation.json",
            work / "capability-baseline-reconciliation.md",
            work / "final-packet-index.json",
            orchestrate_dir / "change-plan.md",
            orchestrate_dir / "change-capability-anchors/index.md",
        ]
        anchors = orchestrate_dir / "change-capability-anchors"
        if anchors.exists():
            forbidden.extend(child for child in anchors.iterdir() if child.is_dir())
        existing = [rel(path, repo_root) for path in forbidden if path.exists()]
        if existing:
            raise ValueError(f"targeted patch禁止terminal artifact：{existing}")
        return
    if status == "blocked":
        if not review_path.is_file() or review_path.read_text(encoding="utf-8") != render_framework_refit_review(orchestrate_dir, refit_path):
            raise ValueError("blocked plan refit review Markdown drift")
        trace_path = orchestrate_dir / "trace/phase-5.trace.json"
        trace = require_json(trace_path, PHASE_TRACE_SCHEMAS["phase-5"])
        expected_trace = _blocked_trace_payload(orchestrate_dir, refit, refit_path, review_path)
        if trace != expected_trace:
            raise ValueError("blocked Phase 5 trace drift")
        forbidden = [
            work / "change-plan.md",
            work / "atom-plan-mapping.json",
            work / "atom-plan-mapping.md",
            work / "capability-baseline-reconciliation.json",
            work / "capability-baseline-reconciliation.md",
            work / "final-packet-index.json",
            orchestrate_dir / "change-plan.md",
            orchestrate_dir / "change-capability-anchors/index.md",
        ]
        anchors = orchestrate_dir / "change-capability-anchors"
        if anchors.exists():
            forbidden.extend(child for child in anchors.iterdir() if child.is_dir())
        existing = [rel(path, repo_root) for path in forbidden if path.exists()]
        if existing:
            raise ValueError(f"blocked禁止terminal artifact：{existing}")
        return
    if status not in TERMINAL_STATUSES:
        raise ValueError("rendered output validation只处理terminal、targeted patch或blocked状态")
    plan = work / "change-plan.md"
    changes, capabilities, overlay = parse_final_plan(plan)
    validate_framework_refit(orchestrate_dir, refit, changes, capabilities, overlay)
    trace = require_json(orchestrate_dir / "trace/phase-5.trace.json", PHASE_TRACE_SCHEMAS["phase-5"])
    patch_history = [dict(row) for row in refit.get("patch-history", []) if isinstance(row, dict)]
    expected_mode = "checkpoint-resume" if patch_history else "initial"
    if trace.get("execution-mode") != expected_mode or trace.get("patch-history") != patch_history:
        raise ValueError("terminal Phase 5 trace execution-mode/patch-history drift")
    expected_patch_ref = patch_history[0].get("patch-request-ref") if patch_history else None
    expected_checkpoint_ref = patch_history[0].get("checkpoint-ref") if patch_history else None
    expected_patch_fields = {
        "evidence-patch-request-path": expected_patch_ref.get("artifact-path") if isinstance(expected_patch_ref, dict) else None,
        "evidence-patch-request-sha256": expected_patch_ref.get("sha256") if isinstance(expected_patch_ref, dict) else None,
        "phase-5-checkpoint-path": expected_checkpoint_ref.get("artifact-path") if isinstance(expected_checkpoint_ref, dict) else None,
        "phase-5-checkpoint-sha256": expected_checkpoint_ref.get("sha256") if isinstance(expected_checkpoint_ref, dict) else None,
    }
    if any(trace.get(field) != value for field, value in expected_patch_fields.items()):
        raise ValueError("terminal Phase 5 trace request/checkpoint refs drift")
    if plan.read_bytes() != (orchestrate_dir / "change-plan.md").read_bytes():
        raise ValueError("根change-plan.md与Phase 5 plan不一致")
    if review_path.read_text(encoding="utf-8") != render_framework_refit_review(orchestrate_dir, refit_path):
        raise ValueError("plan refit review Markdown drift")
    mapping_path = work / "atom-plan-mapping.json"
    evidence = load_evidence(orchestrate_dir)
    mapping = load_mapping(mapping_path)
    validate_mapping(
        evidence,
        mapping,
        changes,
        capabilities,
        overlay,
        repo_root=repo_root,
    )
    validate_gap_framework_impacts(orchestrate_dir, refit, mapping)
    expected_mapping_md = render_atom_plan_mapping(orchestrate_dir, mapping_path)
    if (work / "atom-plan-mapping.md").read_text(encoding="utf-8") != expected_mapping_md:
        raise ValueError("atom plan mapping Markdown drift")
    baseline_path = work / "capability-baseline-reconciliation.json"
    _, expected_baseline = derive_advancement(repo_root, changes, capabilities, mapping)
    if require_json(baseline_path, CAPABILITY_BASELINE_SCHEMA) != expected_baseline:
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
    parser = argparse.ArgumentParser(description="从Phase 5 refit/checkpoint状态机械生成允许的派生产物。")
    parser.add_argument("--orchestrate-dir", type=Path, default=Path("openspec/orchestrate"))
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true", help="写入baseline、packets、trace和根plan")
    action.add_argument(
        "--abort-patch-chain",
        action="store_true",
        help="机械将唯一requested patch链终止为blocked，不改写语义row",
    )
    parser.add_argument("--issue", help="--abort-patch-chain所需的单一终止原因")
    parser.add_argument("--validate-rendered", action="store_true", help="验证已生成派生产物")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.abort_patch_chain:
            if not args.issue:
                raise ValueError("--abort-patch-chain必须同时提供--issue")
            abort_patch_lifecycle(args.orchestrate_dir, args.issue)
        elif args.issue:
            raise ValueError("--issue只能与--abort-patch-chain一起使用")
        elif args.write:
            write_outputs(args.orchestrate_dir)
        else:
            refit_path = args.orchestrate_dir / "phase-works/phase-5/framework-refit-trace.json"
            refit = load_framework_refit(refit_path)
            raw_history = refit.get("patch-history")
            patch_lifecycle_blocked = (
                normalize_code(refit.get("status")) == "blocked"
                and isinstance(raw_history, list)
                and len(raw_history) == 1
                and isinstance(raw_history[0], dict)
                and normalize_code(raw_history[0].get("status")) == "blocked"
            )
            status = validate_framework_refit(
                args.orchestrate_dir,
                refit,
                verify_current_inputs=not patch_lifecycle_blocked,
            )
            if status in TERMINAL_STATUSES:
                plan = args.orchestrate_dir / "phase-works/phase-5/change-plan.md"
                mapping_path = args.orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
                changes, capabilities, overlay = parse_final_plan(plan)
                validate_framework_refit(args.orchestrate_dir, refit, changes, capabilities, overlay)
                evidence = load_evidence(args.orchestrate_dir)
                mapping = load_mapping(mapping_path)
                validate_mapping(
                    evidence,
                    mapping,
                    changes,
                    capabilities,
                    overlay,
                    repo_root=repo_root_for(args.orchestrate_dir),
                )
                validate_gap_framework_impacts(args.orchestrate_dir, refit, mapping)
            elif status not in {TARGETED_PATCH_STATUS, "blocked"}:
                raise ValueError("mechanical helper只处理terminal、targeted patch或blocked状态")
        if args.validate_rendered:
            validate_outputs(args.orchestrate_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("Phase 5 mechanical derivation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
