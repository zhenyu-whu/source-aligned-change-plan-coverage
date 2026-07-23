#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 5 refit/mapping 机械派生器。

v7语义权威是final-roadmap.json、framework-refit-trace.json和
atom-plan-mapping.json；change-plan.md与plan-refit-review.md都是确定性mirror。
本脚本不接受 semantic config，不推断 framework，不补写 acceptance/dependency/archive 文案。
blocked 状态只在clean generation中原子发布review与最小trace，绝不清理结果。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from render_source_aligned_orchestrate import (
    render_atom_plan_mapping,
    render_capability_baseline,
    render_capability_baseline_payload,
    render_framework_refit_review,
)
from source_aligned_trace_lib import (
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_GATE_NAMES,
    CAPABILITY_BASELINE_SCHEMA,
    CHANGE_GATE_NAMES,
    FINAL_PACKET_INDEX_SCHEMA,
    FINAL_ROADMAP_SCHEMA,
    FRAMEWORK_REFIT_TRACE_SCHEMA,
    GLOBAL_ATOM_ID_RE,
    GLOBAL_ATOM_INDEX_SCHEMA,
    KEBAB_CASE_RE,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    PHASE5_REVIEW_CHECKS,
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    canonical_json_sha256,
    require_atom_plan_mapping_envelope,
    require_phase3_frozen_evidence,
    lexical_repo_relative_path as lexical_rel,
    require_no_symlink_in_repo_path,
    line_ranges_label,
    normalize_code,
    repo_relative_path as rel,
    sha256_file,
    source_atom_file_name,
    write_json,
)
from source_aligned_v7_contract import load_final_roadmap, load_initial_framework


DIRECT_PROJECTIONS = {"spec-requirement", "spec-guard", "design-obligation", "verification-obligation"}
SPEC_PROJECTIONS = {"spec-requirement", "spec-guard"}
CHANGE_ONLY_PROJECTIONS = {"design-obligation", "verification-obligation"}
RELATIONS = {"direct", "context", "dependency", "preserve", "reference", "non-goal"}
CAPABILITY_IMPACTS = {"new", "modified", "none"}
TERMINAL_STATUSES = {"accepted", "adjusted"}
NONTERMINAL_STATUSES = {"blocked"}
NONE_VALUES = {"", "none", "null", "None", "NULL"}
CAPABILITY_REVIEW_DECISIONS = {"keep", "split", "merge", "remove", "rename"}
CHANGE_REVIEW_DECISIONS = {
    "keep",
    "split",
    "merge",
    "scope-adjusted",
    "remove",
    "rename",
}

# 与 references/change-capability-framework-principles.md 的顺序严格一致。
# 测试 fixture 与其他 validator 应直接复用这些 tuple，避免 gate 名称漂移。
CAPABILITY_INITIAL_GATE_NAMES = CAPABILITY_GATE_NAMES
CHANGE_INITIAL_GATE_NAMES = CHANGE_GATE_NAMES


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
    delivery_directives: Tuple[str, ...]


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


def repo_root_for(orchestrate_dir: Path) -> Path:
    if orchestrate_dir.parent.name == "openspec":
        root = orchestrate_dir.parent.parent
        return root if root.is_absolute() else Path.cwd() / root
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
            delivery_directives=tuple(
                normalize_code(item)
                for item in row.get("delivery-directives", [])
                if normalize_code(item)
            ),
        )
    if not evidence:
        raise ValueError("global atom index为空")
    return evidence


def load_final_roadmap_defs(
    orchestrate_dir: Path,
    evidence: Dict[str, Evidence],
) -> tuple[
    Dict[str, object],
    List[ChangeDef],
    List[CapabilityDef],
    Dict[Tuple[str, str], str],
]:
    """Load v7 final-roadmap authority and project it to existing render types."""
    roadmap_path = orchestrate_dir / "phase-works/phase-5/final-roadmap.json"
    evidence_directives = {
        ga: list(item.delivery_directives)
        for ga, item in evidence.items()
        if item.delivery_directives
    }
    roadmap, parsed = load_final_roadmap(
        roadmap_path,
        known_ga_ids=set(evidence),
        evidence_directives=evidence_directives,
    )
    expected_artifact_path = rel(
        orchestrate_dir / "phase-works/phase-5/change-plan.md",
        repo_root_for(orchestrate_dir),
    )
    if roadmap.get("artifact-path") != expected_artifact_path:
        raise ValueError(
            "final-roadmap artifact-path必须绑定Phase 5 change-plan mirror："
            + expected_artifact_path
        )
    capabilities = [
        CapabilityDef(
            slug=normalize_code(row.get("capability")),
            purpose=squash(row.get("purpose")),
            owns=squash(row.get("owns")),
            excludes=squash(row.get("excludes")),
            rationale=squash(row.get("boundary-rationale")),
        )
        for row in parsed["capabilities"]
    ]
    outcomes = {
        normalize_code(row.get("outcome-thread-id")): row
        for row in parsed["outcomes"]
    }
    dependency_rows = list(parsed["dependencies"])
    order_decisions = {
        normalize_code(row.get("selected-change")): row
        for row in roadmap.get("order-decisions", [])
        if isinstance(row, dict)
    }
    change_rows = {
        normalize_code(row.get("change")): row
        for row in parsed["changes"]
    }
    change_order = list(parsed["change-order"])
    change_positions = {
        change: position for position, change in enumerate(change_order)
    }
    changes: List[ChangeDef] = []
    for slug in change_order:
        row = change_rows[slug]
        slug = normalize_code(row.get("change"))
        profile = row.get("behavior-profile")
        if not isinstance(profile, dict):
            raise ValueError(f"{slug} behavior-profile非法")
        realized = [
            outcomes[outcome_id]
            for outcome_id in row.get("realizes-outcome-thread-ids", [])
            if outcome_id in outcomes
        ]
        dependencies = tuple(
            sorted(
                (
                    normalize_code(edge.get("prerequisite-change"))
                    for edge in dependency_rows
                    if normalize_code(edge.get("dependent-change")) == slug
                ),
                key=change_positions.__getitem__,
            )
        )
        raw_dependencies = (
            "无。"
            if not dependencies
            else "、".join(f"`{dependency}`" for dependency in dependencies) + "。"
        )
        changes.append(
            ChangeDef(
                slug=slug,
                intent=squash(row.get("intent")),
                outcome="；".join(
                    squash(outcome.get("observable-result")) for outcome in realized
                )
                or squash(row.get("usable-postcondition")),
                source_hint="Phase 2/3 frozen evidence + terminal mapping",
                scope_in=squash(row.get("scope-in")),
                scope_out=squash(row.get("scope-out")),
                trigger=squash(profile.get("trigger-context")),
                normative_behavior=squash(profile.get("normative-behavior")),
                observable_outcome=squash(profile.get("observable-outcome-invariant")),
                exception_semantics=squash(
                    profile.get("important-exception-error-semantics")
                ),
                acceptance=squash(profile.get("acceptance-evidence")),
                dependencies_raw=raw_dependencies,
                dependencies=dependencies,
                ordering_reason=squash(
                    order_decisions.get(slug, {}).get("reason")
                ),
                archive_condition=squash(row.get("independent-archive")),
                split_merge_judgment=squash(row.get("split-merge-judgment")),
            )
        )
    overlay = {
        (
            normalize_code(row.get("change")),
            normalize_code(row.get("capability")),
        ): normalize_code(row.get("capability-impact"))
        for row in parsed["overlay"]
    }
    return roadmap, changes, capabilities, overlay


def render_final_plan_from_roadmap(
    roadmap: Dict[str, object],
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    overlay: Dict[Tuple[str, str], str],
) -> str:
    """Render the public/internal final Markdown plan from final-roadmap JSON."""
    lines = [
        "# Final Change Plan",
        "",
        "## 输入",
        "",
        "- 使用 Phase 2/3 冻结 evidence、terminal mapping 与 final roadmap 生成。",
        "",
        "## Source Semantic Landscape",
        "",
        "| Semantic Area | Final Source-backed Understanding | Planning Relevance | Evidence Authority |",
        "| --- | --- | --- | --- |",
    ]
    landscape = roadmap.get("semantic-landscape")
    if isinstance(landscape, list) and landscape:
        for item in landscape:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                + " | ".join(
                    (
                        md(item.get(field))
                        if field != "evidence-ga-ids"
                        else md(
                            ", ".join(
                                normalize_code(ga)
                                for ga in item.get(field, [])
                            )
                        )
                    )
                    for field in (
                        "semantic-area",
                        "source-backed-understanding",
                        "planning-relevance",
                        "evidence-ga-ids",
                    )
                )
                + " |"
            )
    else:
        lines.append("| 全局 | 见冻结 evidence。 | 支撑最终框架。 | Phase 2/3 frozen evidence |")
    lines.extend(
        [
            "",
            "## Capability Map",
            "",
            "| Capability | Purpose | Owns | Excludes | Boundary Rationale |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for capability in capabilities:
        lines.append(
            f"| {code(capability.slug)} | {md(capability.purpose)} | "
            f"{md(capability.owns)} | {md(capability.excludes)} | "
            f"{md(capability.rationale)} |"
        )
    lines.extend(
        [
            "",
            "## Change 切分原则",
            "",
            "- Change 以 outcome、prefix utility 与 consumer closure 为边界；Capability topology 不决定交付顺序。",
            "- hard dependency 只来自 final-roadmap typed dependency edge。",
            "",
            "## Change Roadmap",
            "",
        ]
    )
    for position, change in enumerate(changes, start=1):
        lines.extend(
            [
                f"### {position}. {code(change.slug)}",
                "",
                f"- Change 名称：{code(change.slug)}",
                f"- 单一 intent：{md(change.intent)}",
                f"- source-backed outcome：{md(change.outcome)}",
                f"- 来源 evidence hint：{md(change.source_hint)}",
                f"- 范围内：{md(change.scope_in)}",
                f"- 范围外：{md(change.scope_out)}",
                "- behavior completeness profile：",
                f"  - trigger/context：{md(change.trigger)}",
                f"  - normative behavior：{md(change.normative_behavior)}",
                f"  - observable outcome / invariant：{md(change.observable_outcome)}",
                f"  - important exception / error semantics：{md(change.exception_semantics)}",
                f"  - acceptance evidence：{md(change.acceptance)}",
                f"- 硬依赖：{md(change.dependencies_raw)}",
                f"- 排序理由：{md(change.ordering_reason)}",
                f"- 独立完成与归档：{md(change.archive_condition)}",
                f"- 拆分/合并判断：{md(change.split_merge_judgment)}",
                "",
            ]
        )
    lines.extend(
        [
            "## Change-Capability Overlay",
            "",
            "| Change | Capability | Capability Impact | Direct Behavior Delta |",
            "| --- | --- | --- | --- |",
        ]
    )
    for change in changes:
        for capability in capabilities:
            impact = overlay.get((change.slug, capability.slug))
            if impact:
                lines.append(
                    f"| {code(change.slug)} | {code(capability.slug)} | "
                    f"{code(impact)} | 见对应 direct spec/guard Capability slice。 |"
                )
    lines.extend(
        [
            "",
            "## Phase 5 风险检查",
            "",
            "1. final Change/Capability、dependency、guard、directive 与 prefix review 已由 v7 authority 约束。",
            "2. 公开 handoff 仅由 frozen evidence 与 terminal mapping 派生。",
            "",
            "## Phase 5 语言自检",
            "",
            md(roadmap.get("language-self-check")),
            "",
        ]
    )
    return "\n".join(lines)


def _phase1_framework(orchestrate_dir: Path) -> tuple[List[str], List[str]]:
    path = orchestrate_dir / "phase-works/phase-1/initial-framework.json"
    framework, parsed = load_initial_framework(path)
    expected_artifact_path = rel(
        path.with_name("initial-change-plan.md"),
        repo_root_for(orchestrate_dir),
    )
    if framework.get("artifact-path") != expected_artifact_path:
        raise ValueError(
            "initial-framework artifact-path必须绑定initial-change-plan mirror"
        )
    changes = sorted(parsed["change-ids"])
    capabilities = sorted(
        normalize_code(row.get("capability"))
        for row in parsed["capabilities"]
    )
    return changes, capabilities


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
    *,
    known_ga_ids: Optional[set[str]] = None,
    allowed_ga_ids: Optional[set[str]] = None,
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
            {"gate", "result", "note", "evidence-ga-ids"},
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
        evidence_ids = item.get("evidence-ga-ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            raise ValueError(
                f"{where}.initial-gate-results[{index}].evidence-ga-ids不得为空"
            )
        normalized_ids = [normalize_code(value) for value in evidence_ids]
        if (
            len(normalized_ids) != len(set(normalized_ids))
            or any(not GLOBAL_ATOM_ID_RE.fullmatch(value) for value in normalized_ids)
            or (
                known_ga_ids is not None
                and any(value not in known_ga_ids for value in normalized_ids)
            )
        ):
            raise ValueError(
                f"{where}.initial-gate-results[{index}].evidence-ga-ids非法"
            )
        if allowed_ga_ids is not None and any(
            value not in allowed_ga_ids for value in normalized_ids
        ):
            raise ValueError(
                f"{where}.initial-gate-results[{index}]包含与被审单元无关的GA"
            )
        has_failed = has_failed or result == "failed"
    if tuple(actual_gates) != tuple(expected_gates):
        raise ValueError(
            f"{where}.initial-gate-results必须完整按固定顺序覆盖共享gate；"
            f"期望={list(expected_gates)}，实际={actual_gates}"
        )
    return has_failed


def load_framework_refit(path: Path) -> Dict[str, object]:
    return require_json(path, FRAMEWORK_REFIT_TRACE_SCHEMA)


def validate_framework_refit(
    orchestrate_dir: Path,
    data: Dict[str, object],
    changes: Optional[Sequence[ChangeDef]] = None,
    capabilities: Optional[Sequence[CapabilityDef]] = None,
    overlay: Optional[Dict[Tuple[str, str], str]] = None,
) -> str:
    """校验 v7 refit lineage；Change order只由final-roadmap负责，不受keep保护。"""
    _require_exact_fields(
        data,
        {
            "trace-schema",
            "trace-contract-version",
            "status",
            "initial-framework-ref",
            "final-roadmap-ref",
            "capability-reviews",
            "change-reviews",
            "outcome-thread-reviews",
            "dependency-edge-reviews",
            "guard-link-reviews",
            "issues",
            "language-self-check",
        },
        "framework-refit-trace",
    )
    status = normalize_code(data.get("status"))
    if status not in TERMINAL_STATUSES | NONTERMINAL_STATUSES:
        raise ValueError(f"framework refit status非法：{status}")
    repo_root = repo_root_for(orchestrate_dir)
    initial_path = orchestrate_dir / "phase-works/phase-1/initial-framework.json"
    final_path = orchestrate_dir / "phase-works/phase-5/final-roadmap.json"
    initial_ref = data.get("initial-framework-ref")
    final_ref = data.get("final-roadmap-ref")
    if not isinstance(initial_ref, dict):
        raise ValueError("initial-framework-ref必须是object")
    _require_exact_fields(initial_ref, {"artifact-path", "sha256"}, "initial-framework-ref")
    if initial_ref.get("artifact-path") != rel(initial_path, repo_root):
        raise ValueError("initial-framework-ref path不一致")
    if initial_ref.get("sha256") != sha256_file(initial_path):
        raise ValueError("initial-framework-ref digest drift")
    issues = data.get("issues")
    if not isinstance(issues, list):
        raise ValueError("issues必须是array")
    language = squash(data.get("language-self-check"))
    if not language or not re.search(r"[\u4e00-\u9fff]", language):
        raise ValueError("language-self-check必须使用简体中文解释")
    if status == "blocked":
        if final_ref is not None or not issues:
            raise ValueError("blocked要求final-roadmap-ref=null且issues非空")
        return status
    if issues:
        raise ValueError(f"{status}要求issues为空")
    if not isinstance(final_ref, dict):
        raise ValueError("terminal refit要求final-roadmap-ref")
    _require_exact_fields(final_ref, {"artifact-path", "sha256"}, "final-roadmap-ref")
    if final_ref.get("artifact-path") != rel(final_path, repo_root):
        raise ValueError("final-roadmap-ref path不一致")
    if final_ref.get("sha256") != sha256_file(final_path):
        raise ValueError("final-roadmap-ref digest drift")

    evidence = load_evidence(orchestrate_dir)
    global_order = list(evidence)
    global_positions = {ga: index for index, ga in enumerate(global_order)}
    known_ga_ids = set(global_order)
    final_roadmap, final_changes, final_capabilities, final_overlay = load_final_roadmap_defs(
        orchestrate_dir,
        evidence,
    )
    if changes is not None and [item.slug for item in changes] != [
        item.slug for item in final_changes
    ]:
        raise ValueError("调用方Change与final-roadmap不一致")
    if capabilities is not None and [item.slug for item in capabilities] != [
        item.slug for item in final_capabilities
    ]:
        raise ValueError("调用方Capability与final-roadmap不一致")
    if overlay is not None and overlay != final_overlay:
        raise ValueError("调用方overlay与final-roadmap不一致")
    initial_changes, initial_capabilities = _phase1_framework(orchestrate_dir)
    _, initial_parsed = load_initial_framework(initial_path)
    initial_capability_rows = {
        normalize_code(row.get("capability")): row
        for row in initial_parsed["capabilities"]
    }
    initial_change_rows = {
        normalize_code(row.get("change")): row
        for row in initial_parsed["changes"]
    }
    final_capability_rows = {
        normalize_code(row.get("capability")): row
        for row in final_roadmap.get("capabilities", [])
        if isinstance(row, dict)
    }
    final_change_rows = {
        normalize_code(row.get("change")): row
        for row in final_roadmap.get("changes", [])
        if isinstance(row, dict)
    }
    final_change_ids = {item.slug for item in final_changes}
    final_capability_ids = {item.slug for item in final_capabilities}
    mapping = load_mapping(
        orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json",
        repo_root=repo_root,
    )
    final_outcome_rows = {
        normalize_code(row.get("outcome-thread-id")): row
        for row in final_roadmap.get("outcome-threads", [])
        if isinstance(row, dict)
    }
    final_dependency_rows = [
        row
        for row in final_roadmap.get("dependency-edges", [])
        if isinstance(row, dict)
    ]
    final_guard_rows = [
        row
        for row in final_roadmap.get("guard-links", [])
        if isinstance(row, dict)
    ]

    def row_ga_ids(row: object, *fields: str) -> set[str]:
        if not isinstance(row, dict):
            return set()
        return {
            normalize_code(ga)
            for field in fields
            for ga in row.get(field, [])
            if normalize_code(ga) in known_ga_ids
        }

    def initial_source_hint_ga_ids(row: object) -> set[str]:
        """仅为被remove的initial unit保留可机械验证的source lineage。"""
        if not isinstance(row, dict):
            return set()
        source_hints = {
            normalize_code(path) for path in row.get("source-hints", [])
        }
        return {
            ga
            for ga, item in evidence.items()
            if item.source_document in source_hints
        }

    def capability_review_ga_ids(
        finals: Sequence[str],
        *,
        initial_row: object,
    ) -> set[str]:
        """Capability lineage只接受边界evidence或其direct spec/guard投影。"""
        final_set = set(finals)
        allowed = set().union(
            *(
                row_ga_ids(final_capability_rows.get(final), "evidence-ga-ids")
                for final in finals
            ),
            set(),
        )
        allowed.update(
            ga
            for ga, item in mapping.items()
            if item.relation == "direct"
            and item.projection in SPEC_PROJECTIONS
            and item.target_capability in final_set
        )
        if not finals:
            allowed.update(initial_source_hint_ga_ids(initial_row))
        return allowed

    def change_review_ga_ids(
        finals: Sequence[str],
        *,
        initial_row: object,
    ) -> set[str]:
        """Change lineage只接受owner/outcome/acceptance/dependency/guard关联。"""
        final_set = set(finals)
        allowed = {
            ga
            for ga, item in mapping.items()
            if item.owner_change in final_set
        }
        realized_outcomes: set[str] = set()
        for final in finals:
            row = final_change_rows.get(final)
            allowed.update(
                row_ga_ids(row, "outcome-ga-ids", "acceptance-ga-ids")
            )
            if isinstance(row, dict):
                realized_outcomes.update(
                    normalize_code(outcome_id)
                    for outcome_id in row.get(
                        "realizes-outcome-thread-ids",
                        [],
                    )
                )
        for outcome_id in realized_outcomes:
            allowed.update(
                row_ga_ids(
                    final_outcome_rows.get(outcome_id),
                    "outcome-ga-ids",
                    "acceptance-ga-ids",
                )
            )
        for row in final_dependency_rows:
            if (
                normalize_code(row.get("prerequisite-change")) in final_set
                or normalize_code(row.get("dependent-change")) in final_set
            ):
                allowed.update(row_ga_ids(row, "evidence-ga-ids"))
        for row in final_guard_rows:
            guarded_outcome = normalize_code(
                row.get("guarded-outcome-thread-id")
            )
            guarded_row = final_outcome_rows.get(guarded_outcome)
            if (
                normalize_code(row.get("guarding-change")) in final_set
                or guarded_outcome in realized_outcomes
                or (
                    isinstance(guarded_row, dict)
                    and normalize_code(
                        guarded_row.get("first-realizing-change")
                    )
                    in final_set
                )
            ):
                allowed.update(row_ga_ids(row, "evidence-ga-ids"))
        if not finals:
            allowed.update(initial_source_hint_ga_ids(initial_row))
        return allowed

    def validate_supporting(
        value: object,
        where: str,
        *,
        allowed_ga_ids: set[str],
    ) -> List[str]:
        if not isinstance(value, list) or not value:
            raise ValueError(f"{where}.supporting-global-atom-ids不得为空")
        result = [normalize_code(item) for item in value]
        if (
            len(result) != len(set(result))
            or any(item not in known_ga_ids for item in result)
            or result != sorted(result, key=global_positions.__getitem__)
        ):
            raise ValueError(f"{where}.supporting-global-atom-ids非法")
        if any(item not in allowed_ga_ids for item in result):
            raise ValueError(
                f"{where}.supporting-global-atom-ids包含与被审单元无关的GA"
            )
        return result

    capability_rows = data.get("capability-reviews")
    if not isinstance(capability_rows, list):
        raise ValueError("capability-reviews必须是array")
    capability_decisions: Dict[str, str] = {}
    capability_claims: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for index, row in enumerate(capability_rows):
        if not isinstance(row, dict):
            raise ValueError(f"capability-reviews[{index}]必须是object")
        _require_exact_fields(
            row,
            {
                "input-capability",
                "decision",
                "final-capabilities",
                "initial-gate-results",
                "supporting-global-atom-ids",
                "reason",
            },
            f"capability-reviews[{index}]",
        )
        source = normalize_code(row.get("input-capability"))
        decision = normalize_code(row.get("decision"))
        if source in capability_decisions or source not in initial_capabilities:
            raise ValueError(f"input Capability未知或重复：{source}")
        if decision not in CAPABILITY_REVIEW_DECISIONS:
            raise ValueError(f"{source} Capability decision非法：{decision}")
        finals = _require_identifier_list(
            row.get("final-capabilities"),
            f"{source}.final-capabilities",
            allow_empty=decision == "remove",
        )
        if any(item not in final_capability_ids for item in finals):
            raise ValueError(f"{source}引用未知final Capability")
        if decision == "keep" and finals != [source]:
            raise ValueError(f"{source} keep要求final-capabilities仅包含自身")
        if decision == "keep":
            initial_boundary = initial_capability_rows[source]
            final_boundary = final_capability_rows.get(source)
            boundary_fields = (
                "purpose",
                "owns",
                "excludes",
                "boundary-rationale",
            )
            if not isinstance(final_boundary, dict) or any(
                final_boundary.get(field) != initial_boundary.get(field)
                for field in boundary_fields
            ):
                raise ValueError(
                    f"{source} keep不得改变Capability boundary semantics"
                )
        if decision == "remove" and finals:
            raise ValueError(f"{source} remove要求空final-capabilities")
        if decision == "rename" and (len(finals) != 1 or finals[0] == source):
            raise ValueError(f"{source} rename要求一个不同final Capability")
        if decision == "split" and len(finals) < 2:
            raise ValueError(f"{source} split要求至少两个final Capability")
        if decision == "merge" and len(finals) != 1:
            raise ValueError(f"{source} merge要求一个final Capability")
        allowed_ga_ids = capability_review_ga_ids(
            finals,
            initial_row=initial_capability_rows[source],
        )
        if not allowed_ga_ids:
            raise ValueError(
                f"{source} Capability review无法建立可验证的final evidence lineage"
            )
        failed = _validate_initial_gate_results(
            row.get("initial-gate-results"),
            CAPABILITY_INITIAL_GATE_NAMES,
            f"capability-reviews[{index}]",
            known_ga_ids=known_ga_ids,
            allowed_ga_ids=allowed_ga_ids,
        )
        validate_supporting(
            row.get("supporting-global-atom-ids"),
            f"capability-reviews[{index}]",
            allowed_ga_ids=allowed_ga_ids,
        )
        if decision == "keep" and failed:
            raise ValueError(f"{source} keep要求全部gate passed")
        if not squash(row.get("reason")) or not re.search(r"[\u4e00-\u9fff]", str(row.get("reason"))):
            raise ValueError(f"{source} reason必须使用简体中文")
        capability_decisions[source] = decision
        for final in finals:
            capability_claims[final].append((source, decision))
    if list(capability_decisions) != initial_capabilities:
        raise ValueError("每个initial Capability必须按原顺序恰好一行")
    for final in sorted(final_capability_ids):
        claims = capability_claims.get(final, [])
        if not claims:
            raise ValueError(f"final Capability缺少refit lineage：{final}")
        if len(claims) > 1 and any(
            decision != "merge" for _, decision in claims
        ):
            raise ValueError(
                f"final Capability存在不兼容的重复认领：{final}"
            )
        if any(decision == "merge" for _, decision in claims) and (
            len(claims) < 2
            or any(decision != "merge" for _, decision in claims)
        ):
            raise ValueError(
                f"Capability merge必须至少由两个initial Capability共同指向：{final}"
            )

    change_rows = data.get("change-reviews")
    if not isinstance(change_rows, list):
        raise ValueError("change-reviews必须是array")
    change_decisions: Dict[str, str] = {}
    change_claims: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for index, row in enumerate(change_rows):
        if not isinstance(row, dict):
            raise ValueError(f"change-reviews[{index}]必须是object")
        _require_exact_fields(
            row,
            {
                "input-change",
                "decision",
                "final-changes",
                "initial-gate-results",
                "supporting-global-atom-ids",
                "reason",
            },
            f"change-reviews[{index}]",
        )
        source = normalize_code(row.get("input-change"))
        decision = normalize_code(row.get("decision"))
        if source in change_decisions or source not in initial_changes:
            raise ValueError(f"input Change未知或重复：{source}")
        if decision not in CHANGE_REVIEW_DECISIONS:
            raise ValueError(f"{source} Change decision非法：{decision}")
        finals = _require_identifier_list(
            row.get("final-changes"),
            f"{source}.final-changes",
            allow_empty=decision == "remove",
        )
        if any(item not in final_change_ids for item in finals):
            raise ValueError(f"{source}引用未知final Change")
        if decision in {"keep", "scope-adjusted"} and finals != [source]:
            raise ValueError(f"{source} {decision}要求final-changes仅包含自身")
        boundary_fields = (
            "intent",
            "scope-in",
            "scope-out",
            "behavior-profile",
            "realizes-outcome-thread-ids",
            "usable-postcondition",
            "consumer-closure",
            "independent-archive",
            "split-merge-judgment",
        )
        if decision == "keep":
            initial_boundary = initial_change_rows[source]
            final_boundary = final_change_rows.get(source)
            if not isinstance(final_boundary, dict) or any(
                final_boundary.get(field) != initial_boundary.get(field)
                for field in boundary_fields
            ):
                raise ValueError(
                    f"{source} keep不得改变Change boundary semantics"
                )
        if decision == "scope-adjusted":
            initial_boundary = initial_change_rows[source]
            final_boundary = final_change_rows.get(source)
            if not isinstance(final_boundary, dict) or all(
                final_boundary.get(field) == initial_boundary.get(field)
                for field in boundary_fields
            ):
                raise ValueError(
                    f"{source} scope-adjusted要求真实的Change boundary变化"
                )
        if decision == "remove" and finals:
            raise ValueError(f"{source} remove要求空final-changes")
        if decision == "rename" and (len(finals) != 1 or finals[0] == source):
            raise ValueError(f"{source} rename要求一个不同final Change")
        if decision == "split" and len(finals) < 2:
            raise ValueError(f"{source} split要求至少两个final Change")
        if decision == "merge" and len(finals) != 1:
            raise ValueError(f"{source} merge要求一个final Change")
        allowed_ga_ids = change_review_ga_ids(
            finals,
            initial_row=initial_change_rows[source],
        )
        if not allowed_ga_ids:
            raise ValueError(
                f"{source} Change review无法建立可验证的final evidence lineage"
            )
        failed = _validate_initial_gate_results(
            row.get("initial-gate-results"),
            CHANGE_INITIAL_GATE_NAMES,
            f"change-reviews[{index}]",
            known_ga_ids=known_ga_ids,
            allowed_ga_ids=allowed_ga_ids,
        )
        validate_supporting(
            row.get("supporting-global-atom-ids"),
            f"change-reviews[{index}]",
            allowed_ga_ids=allowed_ga_ids,
        )
        if decision == "keep" and failed:
            raise ValueError(f"{source} keep要求全部gate passed")
        if not squash(row.get("reason")) or not re.search(r"[\u4e00-\u9fff]", str(row.get("reason"))):
            raise ValueError(f"{source} reason必须使用简体中文")
        change_decisions[source] = decision
        for final in finals:
            change_claims[final].append((source, decision))
    if list(change_decisions) != initial_changes:
        raise ValueError("每个initial Change必须按原顺序恰好一行")
    for final in sorted(final_change_ids):
        claims = change_claims.get(final, [])
        if not claims:
            raise ValueError(f"final Change缺少refit lineage：{final}")
        if len(claims) > 1 and any(
            decision != "merge" for _, decision in claims
        ):
            raise ValueError(f"final Change存在不兼容的重复认领：{final}")
        if any(decision == "merge" for _, decision in claims) and (
            len(claims) < 2
            or any(decision != "merge" for _, decision in claims)
        ):
            raise ValueError(
                f"Change merge必须至少由两个initial Change共同指向：{final}"
            )

    def validate_final_unit_reviews(
        raw: object,
        expected_ids: Sequence[str],
        id_field: str,
        where: str,
        allowed_ga_ids_by_unit: Dict[str, set[str]],
    ) -> None:
        if not isinstance(raw, list):
            raise ValueError(f"{where}必须是array")
        seen: List[str] = []
        for index, row in enumerate(raw):
            if not isinstance(row, dict):
                raise ValueError(f"{where}[{index}]必须是object")
            _require_exact_fields(
                row,
                {id_field, "result", "evidence-ga-ids", "reason"},
                f"{where}[{index}]",
            )
            unit_id = normalize_code(row.get(id_field))
            seen.append(unit_id)
            if row.get("result") != "passed":
                raise ValueError(f"{where}[{index}]必须passed")
            ga_ids = row.get("evidence-ga-ids")
            if not isinstance(ga_ids, list) or not ga_ids or any(
                normalize_code(item) not in known_ga_ids for item in ga_ids
            ):
                raise ValueError(f"{where}[{index}].evidence-ga-ids非法")
            actual_ga_ids = {
                normalize_code(item) for item in ga_ids
            }
            allowed_ga_ids = allowed_ga_ids_by_unit.get(unit_id, set())
            if (
                not actual_ga_ids.intersection(allowed_ga_ids)
                or actual_ga_ids - allowed_ga_ids
            ):
                raise ValueError(
                    f"{where}[{index}].evidence-ga-ids必须只引用"
                    f"{unit_id}自身的终态evidence"
                )
            if not squash(row.get("reason")) or not re.search(r"[\u4e00-\u9fff]", str(row.get("reason"))):
                raise ValueError(f"{where}[{index}].reason必须使用简体中文")
        if seen != list(expected_ids):
            raise ValueError(f"{where}必须按final-roadmap顺序完整覆盖")

    roadmap, parsed = load_final_roadmap(
        final_path,
        known_ga_ids=known_ga_ids,
        evidence_directives={
            ga: item.delivery_directives
            for ga, item in evidence.items()
            if item.delivery_directives
        },
    )
    outcome_review_evidence = {
        normalize_code(row.get("outcome-thread-id")): {
            normalize_code(item)
            for field in ("outcome-ga-ids", "acceptance-ga-ids")
            for item in row.get(field, [])
        }
        for row in parsed["outcomes"]
    }
    dependency_review_evidence = {
        normalize_code(row.get("dependency-id")): {
            normalize_code(item)
            for item in row.get("evidence-ga-ids", [])
        }
        for row in parsed["dependencies"]
    }
    guard_review_evidence = {
        normalize_code(row.get("guard-link-id")): {
            normalize_code(item)
            for item in row.get("evidence-ga-ids", [])
        }
        for row in parsed["guards"]
    }
    validate_final_unit_reviews(
        data.get("outcome-thread-reviews"),
        [normalize_code(row.get("outcome-thread-id")) for row in parsed["outcomes"]],
        "outcome-thread-id",
        "outcome-thread-reviews",
        outcome_review_evidence,
    )
    validate_final_unit_reviews(
        data.get("dependency-edge-reviews"),
        [normalize_code(row.get("dependency-id")) for row in parsed["dependencies"]],
        "dependency-id",
        "dependency-edge-reviews",
        dependency_review_evidence,
    )
    validate_final_unit_reviews(
        data.get("guard-link-reviews"),
        [normalize_code(row.get("guard-link-id")) for row in parsed["guards"]],
        "guard-link-id",
        "guard-link-reviews",
        guard_review_evidence,
    )

    all_keep = all(value == "keep" for value in capability_decisions.values()) and all(
        value == "keep" for value in change_decisions.values()
    )
    same_boundaries = (
        {item.slug for item in final_changes} == set(initial_changes)
        and {item.slug for item in final_capabilities} == set(initial_capabilities)
    )
    if status == "accepted" and (not all_keep or not same_boundaries):
        raise ValueError("accepted只允许Capability/Change边界不变；顺序与overlay仍独立重算")
    if status == "adjusted" and all_keep and same_boundaries:
        raise ValueError("adjusted要求至少一个可追溯的Capability或Change boundary调整")
    return status


def parse_mapping_rows(data: Dict[str, object]) -> Dict[str, Mapping]:
    """Parse mapping rows after the caller has handled the document envelope."""
    expected = {
        "global-atom-id", "evidence-ref", "final-owner-change", "final-relation",
        "final-artifact-projection", "final-capability-impact", "final-target-capability",
        "related-capabilities", "reason",
    }
    mapping: Dict[str, Mapping] = {}
    for row in data.get("rows", []):
        if not isinstance(row, dict) or set(row) != expected:
            raise ValueError("atom-plan-mapping v5 row字段非法")
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


def load_mapping(path: Path, *, repo_root: Path) -> Dict[str, Mapping]:
    data = require_json(path, ATOM_PLAN_MAPPING_SCHEMA)
    require_atom_plan_mapping_envelope(data, path, repo_root)
    return parse_mapping_rows(data)


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
    spec_targets_by_change = {
        change.slug: {
            row.target_capability
            for row in mapping.values()
            if row.owner_change == change.slug
            and row.relation == "direct"
            and row.projection in SPEC_PROJECTIONS
        }
        for change in changes
    }
    empty_changes = [change for change in changes if not spec_targets_by_change[change.slug]]
    if empty_changes:
        foundation = empty_changes[0]
        if len(empty_changes) != 1 or foundation.slug != changes[0].slug:
            raise ValueError("空Capability切片只允许唯一的roadmap首个foundation Change")
        if foundation.dependencies:
            raise ValueError("foundation Change不得声明硬依赖")
        if any(owner == foundation.slug for owner, _ in overlay):
            raise ValueError("foundation Change不得拥有Capability overlay")
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


def public_source_markdown(items: Sequence[Evidence]) -> str:
    """Arrange verbatim frozen source as raw Markdown without occurrence metadata."""
    return "\n\n".join(item.source_fact for item in items)


def _public_source_sort_key(item: Evidence) -> Tuple[object, ...]:
    return (item.source_document, item.line_ranges, item.ga)


def render_change_source(change: ChangeDef, evidence: Dict[str, Evidence], mapping: Dict[str, Mapping]) -> str:
    items = sorted(
        (evidence[ga] for ga, row in mapping.items() if row.owner_change == change.slug),
        key=_public_source_sort_key,
    )
    lines = [
        f"# Change Source：{change.slug}", "",
        "> 本文件是该 Change 的完整 owner-scoped 冻结原文包；不包含上游内部 trace 或 mapping 元数据。", "",
        "## Change Boundary", "",
        f"- Intent：{md(change.intent)}",
        f"- Outcome：{md(change.outcome)}",
        f"- Scope in：{md(change.scope_in)}",
        f"- Scope out：{md(change.scope_out)}",
        f"- Acceptance：{md(change.acceptance)}",
        f"- Hard dependencies：{md(change.dependencies_raw)}",
        f"- Independent archive：{md(change.archive_condition)}", "",
        "## Owner-scoped Frozen Source", "",
    ]
    lines.append(public_source_markdown(items))
    return "\n".join(lines).rstrip() + "\n"


def render_capability_slice(
    change: str,
    capability: CapabilityDef,
    impact: str,
    evidence: Dict[str, Evidence],
    mapping: Dict[str, Mapping],
) -> str:
    items = sorted(
        (
            evidence[ga]
            for ga, row in mapping.items()
            if row.owner_change == change
            and row.relation == "direct"
            and row.target_capability == capability.slug
            and row.projection in SPEC_PROJECTIONS
        ),
        key=_public_source_sort_key,
    )
    lines = [
        f"# Capability Slice：{change} / {capability.slug}", "",
        f"- Capability：{code(capability.slug)}",
        f"- Capability Impact：{code(impact)}",
        f"- Purpose：{md(capability.purpose)}",
        f"- Owns：{md(capability.owns)}",
        f"- Excludes：{md(capability.excludes)}", "",
        "## Direct Spec/Guard Frozen Source", "",
    ]
    lines.append(public_source_markdown(items))
    return "\n".join(lines).rstrip() + "\n"


def render_anchor_index(
    changes: Sequence[ChangeDef],
    capability_defs: Sequence[CapabilityDef],
    mapping: Dict[str, Mapping],
    repo_root: Path,
    anchors: Path,
) -> str:
    lines = [
        "# Change Source Bundle Index", "",
        "| Change | Depends On | Change Source | Capability Slices |",
        "| --- | --- | --- | --- |",
    ]
    for change in changes:
        change_source_path = anchors / change.slug / "change-source.md"
        mapped_capabilities = {
            row.target_capability
            for row in mapping.values()
            if row.owner_change == change.slug and row.relation == "direct" and row.projection in SPEC_PROJECTIONS
        }
        capabilities = [capability.slug for capability in capability_defs if capability.slug in mapped_capabilities]
        cap_paths = [
            lexical_rel(anchors / change.slug / "capability-slices" / f"{capability}.md", repo_root)
            for capability in capabilities
        ]
        lines.append(
            f"| {code(change.slug)} | {md(', '.join(change.dependencies))} | "
            f"{code(lexical_rel(change_source_path, repo_root))} | {md(', '.join(cap_paths))} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def validate_gap_framework_impacts(
    orchestrate_dir: Path,
    data: Dict[str, object],
    mapping: Dict[str, Mapping],
) -> None:
    """v7不再使用Phase 4 bucket/gap impact作为framework authority。

    所有新增或重分配单元由refit review的GA lineage与terminal mapping直接校验。
    """
    evidence = load_evidence(orchestrate_dir)
    if set(mapping) != set(evidence):
        raise ValueError("terminal mapping必须逐GA完整覆盖frozen evidence")


def clean_legacy(orchestrate_dir: Path) -> None:
    """Hard-cut guard: never mutate a legacy generation in place."""
    work = orchestrate_dir / "phase-works/phase-5"
    legacy = [
        "phase5-refit.config.json", "input-change-plan.md", "source-window-refit-trace.md",
        "change-plan-adjustments.md", "capability-progression-review.md", "change-complexity-review.md",
        "plan-refit-decision-log.md", "alignment-final-report.md", "change-capability-human-plan.md",
    ]
    existing: List[str] = []
    for name in legacy:
        path = work / name
        if path.exists() or path.is_symlink():
            existing.append(str(path))
    if existing:
        raise ValueError(
            "检测到legacy Phase 5 generation；v7禁止迁移、清理或原地覆盖："
            + ", ".join(existing)
        )


ANCHOR_ROOT_FILES = {
    "obligation-atom-index.json",
    "obligation-atom-index.md",
    "index.md",
}


def _prepare_anchor_root_for_write(anchors: Path, repo_root: Path) -> None:
    """Reject symlinks, preserve internal indexes, and clear the generated public surface."""
    require_no_symlink_in_repo_path(anchors, repo_root, "change-capability-anchors")
    anchors.mkdir(parents=True, exist_ok=True)
    for candidate in anchors.rglob("*"):
        if candidate.is_symlink():
            raise ValueError(f"public source bundle不得包含symlink：{candidate}")
    preserved = {"obligation-atom-index.json", "obligation-atom-index.md"}
    for child in anchors.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        elif child.is_file():
            if child.name not in preserved:
                child.unlink()
        else:
            raise ValueError(f"change-capability-anchors包含非常规文件：{child}")


def _validate_public_anchor_surface(
    anchors: Path,
    repo_root: Path,
    changes: Sequence[ChangeDef],
    expected_caps_by_change: Dict[str, Sequence[str]],
) -> None:
    """Validate the exact v3 public tree without following symlinks."""
    require_no_symlink_in_repo_path(anchors, repo_root, "change-capability-anchors")
    if not anchors.is_dir():
        raise ValueError("change-capability-anchors必须是普通目录")
    expected_change_names = {change.slug for change in changes}
    for child in anchors.iterdir():
        require_no_symlink_in_repo_path(child, repo_root, "public source bundle")
        if child.name in ANCHOR_ROOT_FILES:
            if not child.is_file():
                raise ValueError(f"anchor root固定文件不是regular file：{child}")
        elif child.name in expected_change_names:
            if not child.is_dir():
                raise ValueError(f"Change source bundle不是普通目录：{child}")
        else:
            raise ValueError(f"anchor root存在额外public surface：{child}")
    for change in changes:
        change_dir = anchors / change.slug
        require_no_symlink_in_repo_path(change_dir, repo_root, f"{change.slug} source bundle")
        if not change_dir.is_dir():
            raise ValueError(f"缺少{change.slug} source bundle目录")
        children = {child.name: child for child in change_dir.iterdir()}
        if set(children) != {"change-source.md", "capability-slices"}:
            raise ValueError(f"{change.slug} public surface字段不精确：{sorted(children)}")
        source_path = children["change-source.md"]
        cap_dir = children["capability-slices"]
        require_no_symlink_in_repo_path(source_path, repo_root, f"{change.slug} change source")
        require_no_symlink_in_repo_path(cap_dir, repo_root, f"{change.slug} capability slices")
        if not source_path.is_file() or not cap_dir.is_dir():
            raise ValueError(f"{change.slug} public source bundle类型非法")
        expected_names = {f"{capability}.md" for capability in expected_caps_by_change.get(change.slug, ())}
        actual_names: set[str] = set()
        for child in cap_dir.iterdir():
            require_no_symlink_in_repo_path(child, repo_root, f"{change.slug} capability slice")
            actual_names.add(child.name)
            if child.name not in expected_names or not child.is_file():
                raise ValueError(f"{change.slug} capability-slices存在额外或非常规文件：{child}")
        if actual_names != expected_names:
            raise ValueError(
                f"{change.slug} capability-slices集合不一致；"
                f"expected={sorted(expected_names)} actual={sorted(actual_names)}"
            )


def _phase5_terminal_public_surfaces(orchestrate_dir: Path) -> List[Path]:
    """列出 bounded-review blocked 不得覆盖或删除的公开/terminal surface。

    final-roadmap、terminal mapping与Phase 5 plan是review candidate authority，
    因而不属于这个集合；bounded-review blocked会保留它们作为私有诊断证据。
    """
    work = orchestrate_dir / "phase-works/phase-5"
    candidates = [
        work / name
        for name in (
            "atom-plan-mapping.md",
            "capability-baseline-reconciliation.json",
            "capability-baseline-reconciliation.md",
            "final-packet-index.json",
        )
    ]
    candidates.extend(
        (
            orchestrate_dir / "change-plan.md",
            orchestrate_dir / "final-integration-review.json",
            orchestrate_dir / "final-integration-review.md",
            orchestrate_dir / "trace/workflow-completion.trace.json",
        )
    )
    anchors = orchestrate_dir / "change-capability-anchors"
    if anchors.exists() or anchors.is_symlink():
        require_no_symlink_in_repo_path(
            anchors,
            repo_root_for(orchestrate_dir),
            "change-capability-anchors",
        )
        for child in anchors.iterdir():
            if child.name not in {
                "obligation-atom-index.json",
                "obligation-atom-index.md",
            }:
                candidates.append(child)
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    if trace_path.is_file():
        try:
            trace_status = normalize_code(
                json.loads(trace_path.read_text(encoding="utf-8")).get(
                    "status"
                )
            )
        except (OSError, ValueError, json.JSONDecodeError, AttributeError):
            trace_status = "invalid"
        if (
            trace_status in TERMINAL_STATUSES
            or trace_status == "blocked"
            or trace_status == "invalid"
        ):
            candidates.append(trace_path)
    manifest_path = orchestrate_dir / "trace/manifest.json"
    if manifest_path.is_file():
        try:
            workflow_status = normalize_code(
                json.loads(
                    manifest_path.read_text(encoding="utf-8")
                ).get("workflow-status")
            )
        except (OSError, ValueError, json.JSONDecodeError, AttributeError):
            workflow_status = "invalid"
        if workflow_status not in {"", "pending"}:
            candidates.append(manifest_path)
    return [path for path in candidates if path.exists() or path.is_symlink()]


def _phase5_framework_block_forbidden_surfaces(
    orchestrate_dir: Path,
) -> List[Path]:
    """Framework-refit early block不得留下未绑定的candidate或公开surface。"""
    work = orchestrate_dir / "phase-works/phase-5"
    candidates = [
        work / "final-roadmap.json",
        work / "change-plan.md",
        work / "atom-plan-mapping.json",
        *_phase5_terminal_public_surfaces(orchestrate_dir),
    ]
    return [
        path
        for index, path in enumerate(candidates)
        if (path.exists() or path.is_symlink())
        and path not in candidates[:index]
    ]


PHASE5_CANDIDATE_DIGEST_FIELDS = (
    "framework-refit-sha256",
    "final-roadmap-sha256",
    "atom-plan-mapping-sha256",
    "final-change-plan-sha256",
    "frozen-evidence-authority-sha256",
    "phase-3-freeze-trace-sha256",
    "candidate-handoff-sha256",
)


def _raw_text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stage_handoff_digest(
    files: Sequence[Tuple[Path, Path]],
    directories: Sequence[Path],
    repo_root: Path,
) -> str:
    """Digest the exact non-trace handoff surface using its final paths."""
    rows: List[Dict[str, str]] = []
    seen_paths: set[str] = set()
    for staged, target in files:
        artifact_path = lexical_rel(target, repo_root)
        if artifact_path in seen_paths:
            raise ValueError(f"candidate handoff path重复：{artifact_path}")
        if not staged.is_file() or staged.is_symlink():
            raise ValueError(f"candidate handoff staged file非法：{staged}")
        seen_paths.add(artifact_path)
        rows.append(
            {
                "artifact-path": artifact_path,
                "sha256": sha256_file(staged),
            }
        )
    directory_paths = sorted(
        {lexical_rel(path, repo_root) for path in directories}
    )
    return canonical_json_sha256(
        {
            "files": sorted(rows, key=lambda row: row["artifact-path"]),
            "directories": directory_paths,
        }
    )


def _stage_phase5_handoff(
    orchestrate_dir: Path,
    stage: Path,
    *,
    plan_text: str,
    refit_path: Path,
    mapping_path: Path,
    evidence: Dict[str, Evidence],
    changes: Sequence[ChangeDef],
    capabilities: Sequence[CapabilityDef],
    mapping: Dict[str, Mapping],
) -> Tuple[str, Dict[str, Path]]:
    """Generate and mechanically self-check the complete non-trace handoff."""
    repo_root = repo_root_for(orchestrate_dir)
    work = orchestrate_dir / "phase-works/phase-5"
    anchors = orchestrate_dir / "change-capability-anchors"
    stage_work = stage / "phase-5"
    stage_anchors = stage / "change-capability-anchors"
    stage_root_plan = stage / "change-plan.md"
    stage_work.mkdir(parents=True)
    stage_anchors.mkdir(parents=True)

    staged_files: List[Tuple[Path, Path]] = []
    staged_directories: List[Path] = []
    for preserved_name in (
        "obligation-atom-index.json",
        "obligation-atom-index.md",
    ):
        source = anchors / preserved_name
        if source.exists():
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"anchor authority非法：{source}")
            staged = stage_anchors / preserved_name
            shutil.copyfile(source, staged)
            staged_files.append((staged, source))

    stage_root_plan.write_text(plan_text, encoding="utf-8")
    staged_files.append((stage_root_plan, orchestrate_dir / "change-plan.md"))

    stage_review = stage_work / "plan-refit-review.md"
    stage_review.write_text(
        render_framework_refit_review(orchestrate_dir, refit_path),
        encoding="utf-8",
    )
    staged_files.append(
        (stage_review, work / "plan-refit-review.md")
    )

    stage_mapping_md = stage_work / "atom-plan-mapping.md"
    stage_mapping_md.write_text(
        render_atom_plan_mapping(orchestrate_dir, mapping_path),
        encoding="utf-8",
    )
    staged_files.append(
        (stage_mapping_md, work / "atom-plan-mapping.md")
    )

    _, baseline = derive_advancement(
        repo_root,
        changes,
        capabilities,
        mapping,
    )
    baseline_path = work / "capability-baseline-reconciliation.json"
    stage_baseline = stage_work / "capability-baseline-reconciliation.json"
    write_json(stage_baseline, baseline)
    staged_files.append((stage_baseline, baseline_path))
    stage_baseline_md = (
        stage_work / "capability-baseline-reconciliation.md"
    )
    stage_baseline_md.write_text(
        render_capability_baseline_payload(
            orchestrate_dir,
            baseline_path,
            baseline,
            json_sha256=sha256_file(stage_baseline),
        ),
        encoding="utf-8",
    )
    staged_files.append(
        (
            stage_baseline_md,
            work / "capability-baseline-reconciliation.md",
        )
    )

    packets: List[Dict[str, object]] = []
    capability_defs = {
        capability.slug: capability for capability in capabilities
    }
    expected_caps_by_change: Dict[str, List[str]] = {}
    for change in changes:
        stage_change_dir = stage_anchors / change.slug
        stage_cap_dir = stage_change_dir / "capability-slices"
        stage_cap_dir.mkdir(parents=True)
        final_change_dir = anchors / change.slug
        final_cap_dir = final_change_dir / "capability-slices"
        staged_directories.extend((final_change_dir, final_cap_dir))

        stage_change_source = stage_change_dir / "change-source.md"
        stage_change_source.write_text(
            render_change_source(change, evidence, mapping),
            encoding="utf-8",
        )
        final_change_source = final_change_dir / "change-source.md"
        staged_files.append((stage_change_source, final_change_source))

        cap_impacts = {
            row.target_capability: row.capability_impact
            for row in mapping.values()
            if row.owner_change == change.slug
            and row.relation == "direct"
            and row.projection in SPEC_PROJECTIONS
        }
        caps = [
            capability.slug
            for capability in capabilities
            if capability.slug in cap_impacts
        ]
        expected_caps_by_change[change.slug] = caps
        slices: List[Dict[str, object]] = []
        for capability in caps:
            stage_cap_path = stage_cap_dir / f"{capability}.md"
            stage_cap_path.write_text(
                render_capability_slice(
                    change.slug,
                    capability_defs[capability],
                    cap_impacts[capability],
                    evidence,
                    mapping,
                ),
                encoding="utf-8",
            )
            final_cap_path = final_cap_dir / f"{capability}.md"
            staged_files.append((stage_cap_path, final_cap_path))
            slices.append(
                {
                    "capability": capability,
                    "capability-impact": cap_impacts[capability],
                    "slice-path": lexical_rel(final_cap_path, repo_root),
                    "slice-sha256": sha256_file(stage_cap_path),
                }
            )
        packets.append(
            {
                "change": change.slug,
                "depends-on": list(change.dependencies),
                "change-source-path": lexical_rel(
                    final_change_source,
                    repo_root,
                ),
                "change-source-sha256": sha256_file(stage_change_source),
                "capability-slices": slices,
            }
        )

    stage_anchor_index = stage_anchors / "index.md"
    stage_anchor_index.write_text(
        render_anchor_index(
            changes,
            capabilities,
            mapping,
            repo_root,
            anchors,
        ),
        encoding="utf-8",
    )
    staged_files.append((stage_anchor_index, anchors / "index.md"))

    packet_index_path = work / "final-packet-index.json"
    stage_packet = stage_work / "final-packet-index.json"
    write_json(
        stage_packet,
        {
            "trace-schema": FINAL_PACKET_INDEX_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "packets": packets,
        },
    )
    staged_files.append((stage_packet, packet_index_path))

    _validate_public_anchor_surface(
        stage_anchors,
        repo_root,
        changes,
        expected_caps_by_change,
    )
    if stage_root_plan.read_text(encoding="utf-8") != plan_text:
        raise ValueError("Phase 5 staging root plan自检失败")
    packet_check = require_json(stage_packet, FINAL_PACKET_INDEX_SCHEMA)
    if packet_check.get("packets") != packets:
        raise ValueError("Phase 5 staging packet逐字节自检失败")
    staged_tree_files = {
        path
        for root in (stage_work, stage_anchors)
        for path in root.rglob("*")
        if path.is_file()
    } | {stage_root_plan}
    if staged_tree_files != {path for path, _ in staged_files}:
        raise ValueError("Phase 5 staging存在未纳入handoff digest的文件")

    return (
        _stage_handoff_digest(
            staged_files,
            staged_directories,
            repo_root,
        ),
        {
            "root-plan": stage_root_plan,
            "review": stage_review,
            "mapping-md": stage_mapping_md,
            "baseline": stage_baseline,
            "baseline-md": stage_baseline_md,
            "packet": stage_packet,
            "anchors": stage_anchors,
        },
    )


def _candidate_handoff_sha256(
    orchestrate_dir: Path,
    plan_text: str,
) -> str:
    """Rebuild the full handoff in private staging and return its digest."""
    repo_root = repo_root_for(orchestrate_dir)
    work = orchestrate_dir / "phase-works/phase-5"
    refit_path = work / "framework-refit-trace.json"
    mapping_path = work / "atom-plan-mapping.json"
    evidence = load_evidence(orchestrate_dir)
    roadmap, changes, capabilities, overlay = load_final_roadmap_defs(
        orchestrate_dir,
        evidence,
    )
    refit = load_framework_refit(refit_path)
    status = validate_framework_refit(
        orchestrate_dir,
        refit,
        changes,
        capabilities,
        overlay,
    )
    if status not in TERMINAL_STATUSES:
        raise ValueError("candidate handoff只接受accepted/adjusted refit")
    mapping = load_mapping(mapping_path, repo_root=repo_root)
    validate_mapping(
        evidence,
        mapping,
        changes,
        capabilities,
        overlay,
        repo_root=repo_root,
    )
    validate_gap_framework_impacts(orchestrate_dir, refit, mapping)
    expected_plan = render_final_plan_from_roadmap(
        roadmap,
        changes,
        capabilities,
        overlay,
    )
    if plan_text != expected_plan:
        raise ValueError("candidate handoff plan未由当前final roadmap确定性派生")
    transaction_root = Path(
        tempfile.mkdtemp(prefix=".phase5-candidate-check-", dir=orchestrate_dir)
    )
    try:
        stage = transaction_root / "stage"
        stage.mkdir()
        digest, _ = _stage_phase5_handoff(
            orchestrate_dir,
            stage,
            plan_text=plan_text,
            refit_path=refit_path,
            mapping_path=mapping_path,
            evidence=evidence,
            changes=changes,
            capabilities=capabilities,
            mapping=mapping,
        )
        return digest
    finally:
        shutil.rmtree(transaction_root, ignore_errors=True)


def phase5_candidate_authority(
    orchestrate_dir: Path,
    plan_text: str,
) -> Dict[str, str]:
    repo_root = repo_root_for(orchestrate_dir)
    work = orchestrate_dir / "phase-works/phase-5"
    frozen = require_phase3_frozen_evidence(
        orchestrate_dir,
        repo_root,
    )
    return {
        "framework-refit-sha256": sha256_file(work / "framework-refit-trace.json"),
        "final-roadmap-sha256": sha256_file(work / "final-roadmap.json"),
        "atom-plan-mapping-sha256": sha256_file(work / "atom-plan-mapping.json"),
        "final-change-plan-sha256": _raw_text_sha256(plan_text),
        **frozen,
        "candidate-handoff-sha256": _candidate_handoff_sha256(
            orchestrate_dir,
            plan_text,
        ),
    }


def phase5_candidate_authority_sha256(digests: Dict[str, str]) -> str:
    return canonical_json_sha256(
        {
            "artifacts": [
                {"name": field, "sha256": digests[field]}
                for field in PHASE5_CANDIDATE_DIGEST_FIELDS
            ]
        }
    )


def validate_phase5_review_gate(
    gate: object,
    *,
    current_digests: Dict[str, str],
) -> str:
    """Validate the independent 3-review/2-repair Phase 5 bounded gate."""
    if not isinstance(gate, dict):
        raise ValueError("Phase 5 review-gate必须是object")
    _require_exact_fields(
        gate,
        {"status", "writer-id", "reviews", "repairs"},
        "Phase 5 review-gate",
    )
    status = normalize_code(gate.get("status"))
    if status not in {"pending", "passed", "blocked"}:
        raise ValueError("Phase 5 review-gate.status非法")
    writer_id = squash(gate.get("writer-id"))
    if not writer_id:
        raise ValueError("Phase 5 review-gate.writer-id不得为空")
    reviews = gate.get("reviews")
    repairs = gate.get("repairs")
    if not isinstance(reviews, list) or len(reviews) > 3:
        raise ValueError("Phase 5 reviews必须是0..3条")
    if not isinstance(repairs, list) or len(repairs) > 2:
        raise ValueError("Phase 5 repairs必须是0..2条")
    if status in {"passed", "blocked"} and not reviews:
        raise ValueError(f"Phase 5 {status} review-gate必须至少有一轮review")

    review_by_round: Dict[int, Dict[str, object]] = {}
    reviewer_ids: set[str] = set()
    forced_block_rounds: set[int] = set()
    seen_fingerprints: set[str] = set()
    for index, raw in enumerate(reviews, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Phase 5 reviews[{index}]必须是object")
        _require_exact_fields(
            raw,
            {
                "round",
                "reviewer-id",
                "validator-status",
                *PHASE5_CANDIDATE_DIGEST_FIELDS,
                "semantic-checks",
                "finding-fingerprints",
            },
            f"Phase 5 reviews[{index}]",
        )
        if raw.get("round") != index:
            raise ValueError("Phase 5 review round必须从1连续递增")
        reviewer_id = squash(raw.get("reviewer-id"))
        if (
            not reviewer_id
            or reviewer_id == writer_id
            or reviewer_id in reviewer_ids
        ):
            raise ValueError("Phase 5 reviewer必须fresh且不同于writer")
        reviewer_ids.add(reviewer_id)
        if raw.get("validator-status") not in {"passed", "failed"}:
            raise ValueError(f"Phase 5 review {index} validator-status非法")
        for field in PHASE5_CANDIDATE_DIGEST_FIELDS:
            if not re.fullmatch(r"[0-9a-f]{64}", str(raw.get(field, ""))):
                raise ValueError(f"Phase 5 review {index} {field}非法")
        checks = raw.get("semantic-checks")
        if not isinstance(checks, list) or len(checks) != len(PHASE5_REVIEW_CHECKS):
            raise ValueError("Phase 5 semantic-checks必须完整覆盖固定九项")
        actual_checks: List[str] = []
        for check_index, check in enumerate(checks):
            if not isinstance(check, dict):
                raise ValueError("Phase 5 semantic check必须是object")
            _require_exact_fields(
                check,
                {"check", "result"},
                f"Phase 5 reviews[{index}].semantic-checks[{check_index}]",
            )
            actual_checks.append(normalize_code(check.get("check")))
            if check.get("result") not in {"passed", "failed"}:
                raise ValueError("Phase 5 semantic check result非法")
        if tuple(actual_checks) != PHASE5_REVIEW_CHECKS:
            raise ValueError("Phase 5 semantic-checks顺序非法")
        findings = raw.get("finding-fingerprints")
        if (
            not isinstance(findings, list)
            or any(
                not re.fullmatch(r"[0-9a-f]{64}", str(item))
                for item in findings
            )
            or len(findings) != len(set(findings))
        ):
            raise ValueError("Phase 5 finding-fingerprints非法")
        if seen_fingerprints.intersection(findings):
            forced_block_rounds.add(index)
        seen_fingerprints.update(findings)
        review_by_round[index] = raw

    repair_writer_ids: set[str] = set()
    repair_by_round: Dict[int, Dict[str, object]] = {}
    for index, raw in enumerate(repairs, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Phase 5 repairs[{index}]必须是object")
        _require_exact_fields(
            raw,
            {
                "round",
                "repair-writer-id",
                "finding-fingerprints",
                "before-terminal-authority-sha256",
                "after-terminal-authority-sha256",
            },
            f"Phase 5 repairs[{index}]",
        )
        round_number = raw.get("round")
        if (
            not isinstance(round_number, int)
            or round_number not in review_by_round
            or round_number in repair_by_round
        ):
            raise ValueError("Phase 5 repair round必须唯一对应已存在review")
        repair_writer = squash(raw.get("repair-writer-id"))
        if (
            not repair_writer
            or repair_writer == writer_id
            or repair_writer in reviewer_ids
            or repair_writer in repair_writer_ids
        ):
            raise ValueError("Phase 5 repair writer身份不独立")
        repair_writer_ids.add(repair_writer)
        findings = raw.get("finding-fingerprints")
        review_findings = review_by_round[round_number].get(
            "finding-fingerprints"
        )
        if (
            not isinstance(findings, list)
            or not findings
            or not isinstance(review_findings, list)
            or not set(findings).issubset(set(review_findings))
        ):
            raise ValueError("Phase 5 repair findings必须来自对应review且非空")
        before = str(raw.get("before-terminal-authority-sha256", ""))
        after = str(raw.get("after-terminal-authority-sha256", ""))
        if not re.fullmatch(r"[0-9a-f]{64}", before) or not re.fullmatch(
            r"[0-9a-f]{64}",
            after,
        ):
            raise ValueError("Phase 5 repair candidate digest非法")
        review_digest = phase5_candidate_authority_sha256(
            {
                field: str(review_by_round[round_number].get(field, ""))
                for field in PHASE5_CANDIDATE_DIGEST_FIELDS
            }
        )
        if before != review_digest:
            raise ValueError("Phase 5 repair before digest与review不一致")
        next_review = review_by_round.get(round_number + 1)
        if next_review is not None:
            next_digest = phase5_candidate_authority_sha256(
                {
                    field: str(next_review.get(field, ""))
                    for field in PHASE5_CANDIDATE_DIGEST_FIELDS
                }
            )
            if after != next_digest:
                raise ValueError("Phase 5 repair after digest与下一轮review不一致")
        if before == after:
            forced_block_rounds.add(round_number)
        repair_by_round[round_number] = raw

    current_authority_sha256 = phase5_candidate_authority_sha256(
        current_digests
    )
    terminal_noop = (
        status == "blocked"
        and reviews
        and isinstance(repair_by_round.get(len(reviews)), dict)
        and repair_by_round[len(reviews)].get(
            "before-terminal-authority-sha256"
        )
        == repair_by_round[len(reviews)].get(
            "after-terminal-authority-sha256"
        )
    )
    awaiting_review = (
        status == "pending"
        and bool(reviews)
        and len(reviews) == len(repairs)
    )
    current_bound_by_review = len(reviews) == len(repairs) + 1
    if reviews and not (
        current_bound_by_review or awaiting_review or terminal_noop
    ):
        raise ValueError("Phase 5 reviews/repairs cardinality非法")
    if current_bound_by_review:
        last = reviews[-1]
        for field in PHASE5_CANDIDATE_DIGEST_FIELDS:
            if last.get(field) != current_digests[field]:
                raise ValueError(
                    "最后Phase 5 review未绑定当前candidate authority"
                )
    elif reviews:
        latest_repair = repair_by_round.get(len(reviews))
        if (
            not isinstance(latest_repair, dict)
            or latest_repair.get("after-terminal-authority-sha256")
            != current_authority_sha256
        ):
            raise ValueError(
                "最新Phase 5 repair未绑定当前candidate authority"
            )
    for round_number in range(1, len(reviews)):
        if round_number not in repair_by_round:
            raise ValueError("Phase 5相邻review之间缺少repair")
    if len(reviews) == 3:
        terminal_review = reviews[-1]
        terminal_checks = terminal_review.get("semantic-checks")
        terminal_checks_passed = isinstance(
            terminal_checks,
            list,
        ) and all(
            isinstance(check, dict) and check.get("result") == "passed"
            for check in terminal_checks
        )
        if (
            terminal_review.get("validator-status") != "passed"
            or terminal_review.get("finding-fingerprints") != []
            or not terminal_checks_passed
        ):
            forced_block_rounds.add(3)
    if forced_block_rounds and status != "blocked":
        raise ValueError(
            "Phase 5重复finding、no-op repair或第三轮未通过时必须blocked"
        )
    if forced_block_rounds and len(reviews) > min(forced_block_rounds):
        raise ValueError("Phase 5确认无进展后不得继续review")
    if status == "passed":
        last = reviews[-1]
        if (
            last.get("validator-status") != "passed"
            or last.get("finding-fingerprints") != []
            or any(
                isinstance(check, dict) and check.get("result") != "passed"
                for check in last.get("semantic-checks", [])
            )
        ):
            raise ValueError("Phase 5 passed要求最终validator和九项check通过且无finding")
    if status == "pending" and forced_block_rounds:
        raise ValueError("Phase 5 pending不得保留已确认的blocking no-progress")
    if status == "blocked" and reviews and not forced_block_rounds:
        last = reviews[-1]
        checks = last.get("semantic-checks")
        checks_passed = isinstance(checks, list) and all(
            isinstance(check, dict) and check.get("result") == "passed"
            for check in checks
        )
        if (
            last.get("validator-status") == "passed"
            and last.get("finding-fingerprints") == []
            and checks_passed
        ):
            raise ValueError(
                "Phase 5 blocked必须由当前validator/check/finding failure、"
                "重复finding或no-op repair支持"
            )
    return status


def phase5_bounded_review_issues(
    gate: Dict[str, object],
) -> List[str]:
    """从canonical blocked review gate确定性派生非空问题摘要。"""
    reviews = gate.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        raise ValueError("bounded-review blocked要求至少一轮review")
    last = reviews[-1]
    if not isinstance(last, dict):
        raise ValueError("bounded-review blocked最后review非法")
    issues: List[str] = []
    round_number = last.get("round")
    if last.get("validator-status") != "passed":
        issues.append(
            f"Phase 5 bounded review第{round_number}轮validator未通过。"
        )
    checks = last.get("semantic-checks")
    failed_checks = [
        normalize_code(check.get("check"))
        for check in checks
        if isinstance(check, dict) and check.get("result") != "passed"
    ] if isinstance(checks, list) else []
    if failed_checks:
        issues.append(
            "Phase 5 bounded review仍有未通过检查："
            + "、".join(failed_checks)
            + "。"
        )
    findings = last.get("finding-fingerprints")
    if isinstance(findings, list) and findings:
        issues.append(
            "Phase 5 bounded review仍有blocking finding："
            + "、".join(str(item) for item in findings)
            + "。"
        )
    if not issues:
        raise ValueError(
            "bounded-review blocked必须由当前validator/check/finding failure支持"
        )
    return issues


def _framework_blocked_trace_payload(
    orchestrate_dir: Path,
    refit: Dict[str, object],
    refit_path: Path,
    review_path: Path,
    *,
    review_sha256: Optional[str] = None,
) -> Dict[str, object]:
    """构造 blocked 的最小 Phase 5 trace。"""
    repo_root = repo_root_for(orchestrate_dir)
    return {
        "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "status": "blocked",
        "block-kind": "framework-refit",
        "framework-refit-trace-path": rel(refit_path, repo_root),
        "framework-refit-trace-sha256": sha256_file(refit_path),
        "plan-refit-review-path": rel(review_path, repo_root),
        "plan-refit-review-sha256": (
            review_sha256
            if review_sha256 is not None
            else sha256_file(review_path)
        ),
        "issues": list(refit.get("issues", [])),
    }


def _bounded_review_blocked_trace_payload(
    orchestrate_dir: Path,
    plan_text: str,
    gate: Dict[str, object],
) -> Dict[str, object]:
    """构造绑定完整candidate与frozen evidence的bounded-review blocked trace。"""
    repo_root = repo_root_for(orchestrate_dir)
    work = orchestrate_dir / "phase-works/phase-5"
    digests = phase5_candidate_authority(orchestrate_dir, plan_text)
    return {
        "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "status": "blocked",
        "block-kind": "bounded-review",
        "framework-refit-trace-path": rel(
            work / "framework-refit-trace.json",
            repo_root,
        ),
        "framework-refit-trace-sha256": digests[
            "framework-refit-sha256"
        ],
        "final-roadmap-path": rel(
            work / "final-roadmap.json",
            repo_root,
        ),
        "final-roadmap-sha256": digests["final-roadmap-sha256"],
        "atom-plan-mapping-path": rel(
            work / "atom-plan-mapping.json",
            repo_root,
        ),
        "atom-plan-mapping-sha256": digests[
            "atom-plan-mapping-sha256"
        ],
        "candidate-final-change-plan-path": rel(
            work / "change-plan.md",
            repo_root,
        ),
        "candidate-final-change-plan-sha256": digests[
            "final-change-plan-sha256"
        ],
        "frozen-evidence-authority-sha256": digests[
            "frozen-evidence-authority-sha256"
        ],
        "phase-3-freeze-trace-path": rel(
            orchestrate_dir / "trace/phase-3.trace.json",
            repo_root,
        ),
        "phase-3-freeze-trace-sha256": digests[
            "phase-3-freeze-trace-sha256"
        ],
        "candidate-handoff-sha256": digests[
            "candidate-handoff-sha256"
        ],
        "review-gate": gate,
        "issues": phase5_bounded_review_issues(gate),
    }


def _write_framework_blocked_outputs(
    orchestrate_dir: Path,
    refit: Dict[str, object],
    refit_path: Path,
    review_path: Path,
) -> None:
    """在clean generation中原子发布blocked review/trace，绝不清理结果。"""
    if normalize_code(refit.get("status")) != "blocked":
        raise ValueError("blocked output只接受status=blocked")
    clean_legacy(orchestrate_dir)
    existing = _phase5_framework_block_forbidden_surfaces(
        orchestrate_dir
    )
    if existing:
        raise ValueError(
            "blocked路径拒绝覆盖或删除既有published surface："
            + ", ".join(str(path) for path in existing)
        )
    transaction_root = Path(
        tempfile.mkdtemp(prefix=".phase5-blocked-", dir=orchestrate_dir)
    )
    stage = transaction_root / "stage"
    stage.mkdir()
    stage_review = stage / "plan-refit-review.md"
    stage_review.write_text(
        render_framework_refit_review(orchestrate_dir, refit_path),
        encoding="utf-8",
    )
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    stage_trace = stage / "phase-5.trace.json"
    write_json(
        stage_trace,
        _framework_blocked_trace_payload(
            orchestrate_dir,
            refit,
            refit_path,
            review_path,
            review_sha256=sha256_file(stage_review),
        ),
    )
    _atomic_publish_phase5(
        (
            (stage_review, review_path),
            (stage_trace, trace_path),
        ),
        transaction_root,
        lambda: validate_outputs(orchestrate_dir),
    )


def _write_bounded_review_blocked_outputs(
    orchestrate_dir: Path,
    plan_text: str,
    gate: Dict[str, object],
) -> None:
    """把review-pending原子终结为bounded-review blocked，保留私有candidate。"""
    if normalize_code(gate.get("status")) != "blocked":
        raise ValueError("bounded blocked output只接受status=blocked gate")
    clean_legacy(orchestrate_dir)
    existing = _phase5_terminal_public_surfaces(orchestrate_dir)
    if existing:
        raise ValueError(
            "bounded-review blocked拒绝覆盖或删除既有published surface："
            + ", ".join(str(path) for path in existing)
        )
    transaction_root = Path(
        tempfile.mkdtemp(
            prefix=".phase5-review-blocked-",
            dir=orchestrate_dir,
        )
    )
    stage = transaction_root / "stage"
    stage.mkdir()
    stage_trace = stage / "phase-5.trace.json"
    write_json(
        stage_trace,
        _bounded_review_blocked_trace_payload(
            orchestrate_dir,
            plan_text,
            gate,
        ),
    )
    _atomic_publish_phase5(
        (
            (
                stage_trace,
                orchestrate_dir / "trace/phase-5.trace.json",
            ),
        ),
        transaction_root,
        lambda: validate_outputs(orchestrate_dir),
    )


def prepare_review(orchestrate_dir: Path, writer_id: str) -> None:
    """Create the bounded-review candidate plan and pending control trace.

    This step deliberately does not publish the root plan, public source bundle,
    packet, or workflow completion authority.
    """
    writer = squash(writer_id)
    if not writer:
        raise ValueError("--writer-id在--prepare-review时不得为空")
    repo_root = repo_root_for(orchestrate_dir)
    work = orchestrate_dir / "phase-works/phase-5"
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    if trace_path.exists():
        raise ValueError(
            "Phase 5 trace已存在；不得用--prepare-review覆盖review历史"
        )
    plan_path = work / "change-plan.md"
    review_path = work / "plan-refit-review.md"
    forbidden_published = [
        *_phase5_terminal_public_surfaces(orchestrate_dir),
        plan_path,
        review_path,
    ]
    existing = [
        path
        for path in dict.fromkeys(forbidden_published)
        if path.exists() or path.is_symlink()
    ]
    if existing:
        raise ValueError(
            "v7 prepare-review只允许clean generation；已存在published surface："
            + ", ".join(str(path) for path in existing)
        )
    refit_path = work / "framework-refit-trace.json"
    mapping_path = work / "atom-plan-mapping.json"
    refit = load_framework_refit(refit_path)
    status = validate_framework_refit(orchestrate_dir, refit)
    if status not in TERMINAL_STATUSES:
        raise ValueError("只有accepted/adjusted refit可进入Phase 5 bounded review")
    evidence = load_evidence(orchestrate_dir)
    roadmap, changes, capabilities, overlay = load_final_roadmap_defs(
        orchestrate_dir,
        evidence,
    )
    mapping = load_mapping(mapping_path, repo_root=repo_root)
    validate_mapping(
        evidence,
        mapping,
        changes,
        capabilities,
        overlay,
        repo_root=repo_root,
    )
    plan_text = render_final_plan_from_roadmap(
        roadmap,
        changes,
        capabilities,
        overlay,
    )
    digests = phase5_candidate_authority(orchestrate_dir, plan_text)
    trace_payload = {
        "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "status": "review-pending",
        "framework-refit-trace-path": rel(refit_path, repo_root),
        "framework-refit-trace-sha256": digests[
            "framework-refit-sha256"
        ],
        "final-roadmap-path": rel(work / "final-roadmap.json", repo_root),
        "final-roadmap-sha256": digests["final-roadmap-sha256"],
        "atom-plan-mapping-path": rel(mapping_path, repo_root),
        "atom-plan-mapping-sha256": digests[
            "atom-plan-mapping-sha256"
        ],
        "candidate-final-change-plan-path": rel(plan_path, repo_root),
        "candidate-final-change-plan-sha256": digests[
            "final-change-plan-sha256"
        ],
        "frozen-evidence-authority-sha256": digests[
            "frozen-evidence-authority-sha256"
        ],
        "phase-3-freeze-trace-path": rel(
            orchestrate_dir / "trace/phase-3.trace.json",
            repo_root,
        ),
        "phase-3-freeze-trace-sha256": digests[
            "phase-3-freeze-trace-sha256"
        ],
        "candidate-handoff-sha256": digests[
            "candidate-handoff-sha256"
        ],
        "review-gate": {
            "status": "pending",
            "writer-id": writer,
            "reviews": [],
            "repairs": [],
        },
    }
    transaction_root = Path(
        tempfile.mkdtemp(prefix=".phase5-prepare-", dir=orchestrate_dir)
    )
    stage = transaction_root / "stage"
    stage.mkdir()
    stage_plan = stage / "change-plan.md"
    stage_plan.write_text(plan_text, encoding="utf-8")
    stage_review = stage / "plan-refit-review.md"
    stage_review.write_text(
        render_framework_refit_review(orchestrate_dir, refit_path),
        encoding="utf-8",
    )
    stage_trace = stage / "phase-5.trace.json"
    write_json(
        stage_trace,
        trace_payload,
    )
    _atomic_publish_phase5(
        (
            (stage_plan, plan_path),
            (stage_review, review_path),
            (stage_trace, trace_path),
        ),
        transaction_root,
        lambda: _load_phase5_review_gate(
            orchestrate_dir,
            plan_text,
            allowed_statuses={"pending"},
        ),
    )


def _load_phase5_review_gate(
    orchestrate_dir: Path,
    plan_text: str,
    *,
    allowed_statuses: set[str],
) -> Dict[str, object]:
    repo_root = repo_root_for(orchestrate_dir)
    work = orchestrate_dir / "phase-works/phase-5"
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    trace = require_json(trace_path, PHASE_TRACE_SCHEMAS["phase-5"])
    if trace.get("status") != "review-pending":
        raise ValueError("Phase 5 publish要求review-pending candidate trace")
    _require_exact_fields(
        trace,
        {
            "trace-schema",
            "trace-contract-version",
            "status",
            "framework-refit-trace-path",
            "framework-refit-trace-sha256",
            "final-roadmap-path",
            "final-roadmap-sha256",
            "atom-plan-mapping-path",
            "atom-plan-mapping-sha256",
            "candidate-final-change-plan-path",
            "candidate-final-change-plan-sha256",
            "frozen-evidence-authority-sha256",
            "phase-3-freeze-trace-path",
            "phase-3-freeze-trace-sha256",
            "candidate-handoff-sha256",
            "review-gate",
        },
        "Phase 5 review-pending trace",
    )
    plan_path = work / "change-plan.md"
    digests = phase5_candidate_authority(orchestrate_dir, plan_text)
    refs = (
        (
            "framework-refit-trace",
            work / "framework-refit-trace.json",
            "framework-refit-sha256",
        ),
        ("final-roadmap", work / "final-roadmap.json", "final-roadmap-sha256"),
        (
            "atom-plan-mapping",
            work / "atom-plan-mapping.json",
            "atom-plan-mapping-sha256",
        ),
        (
            "candidate-final-change-plan",
            plan_path,
            "final-change-plan-sha256",
        ),
    )
    for prefix, path, digest_field in refs:
        if trace.get(f"{prefix}-path") != rel(path, repo_root):
            raise ValueError(f"Phase 5 candidate {prefix} path drift")
        if trace.get(f"{prefix}-sha256") != digests[digest_field]:
            raise ValueError(f"Phase 5 candidate {prefix} digest drift")
    if not plan_path.is_file() or plan_path.read_text(encoding="utf-8") != plan_text:
        raise ValueError("Phase 5 candidate change-plan mirror drift")
    review_path = work / "plan-refit-review.md"
    refit_path = work / "framework-refit-trace.json"
    if (
        not review_path.is_file()
        or review_path.read_text(encoding="utf-8")
        != render_framework_refit_review(orchestrate_dir, refit_path)
    ):
        raise ValueError("Phase 5 candidate plan-refit-review mirror drift")
    if (
        trace.get("frozen-evidence-authority-sha256")
        != digests["frozen-evidence-authority-sha256"]
    ):
        raise ValueError("Phase 5 candidate frozen evidence authority drift")
    phase3_trace_path = orchestrate_dir / "trace/phase-3.trace.json"
    if (
        trace.get("phase-3-freeze-trace-path")
        != rel(phase3_trace_path, repo_root)
        or trace.get("phase-3-freeze-trace-sha256")
        != digests["phase-3-freeze-trace-sha256"]
    ):
        raise ValueError("Phase 5 candidate Phase 3 freeze trace drift")
    if (
        trace.get("candidate-handoff-sha256")
        != digests["candidate-handoff-sha256"]
    ):
        raise ValueError("Phase 5 candidate handoff derivation drift")
    gate = trace.get("review-gate")
    gate_status = validate_phase5_review_gate(
        gate,
        current_digests=digests,
    )
    if gate_status not in allowed_statuses:
        raise ValueError(
            "Phase 5 bounded review状态不允许当前操作："
            + gate_status
        )
    return dict(gate)


def load_passed_phase5_review_gate(
    orchestrate_dir: Path,
    plan_text: str,
) -> Dict[str, object]:
    gate = _load_phase5_review_gate(
        orchestrate_dir,
        plan_text,
        allowed_statuses={"pending", "passed", "blocked"},
    )
    if normalize_code(gate.get("status")) != "passed":
        raise ValueError("Phase 5 bounded review尚未passed")
    return gate


def _atomic_publish_phase5(
    entries: Sequence[Tuple[Path, Path]],
    transaction_root: Path,
    validate_published,
) -> None:
    """Publish multiple files/directories with rollback and a trace-last commit."""
    backup_root = transaction_root / "backup"
    failed_root = transaction_root / "failed"
    backup_root.mkdir()
    failed_root.mkdir()
    applied: List[Tuple[Path, Optional[Path]]] = []
    try:
        for index, (staged, target) in enumerate(entries):
            if not staged.exists() or staged.is_symlink():
                raise ValueError(f"Phase 5 staging entry非法：{staged}")
            if target.is_symlink():
                raise ValueError(f"Phase 5 publish target不得为symlink：{target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            backup: Optional[Path] = None
            if target.exists():
                backup = backup_root / f"{index:02d}"
                os.replace(target, backup)
            try:
                os.replace(staged, target)
            except Exception:
                if backup is not None and backup.exists() and not target.exists():
                    os.replace(backup, target)
                raise
            applied.append((target, backup))
        validate_published()
    except Exception:
        for index, (target, backup) in reversed(list(enumerate(applied))):
            if target.exists() or target.is_symlink():
                os.replace(target, failed_root / f"{index:02d}")
            if backup is not None and backup.exists():
                os.replace(backup, target)
        raise
    finally:
        shutil.rmtree(transaction_root, ignore_errors=True)


def refresh_review_candidate(orchestrate_dir: Path) -> None:
    """Repair后重算完整candidate，并原子刷新plan与pending trace。

    Review/repair历史由调用方先追加到review-gate；本入口只接受最后一轮
    review已经有对应repair、且repair.after绑定当前authority的合法状态。
    """
    repo_root = repo_root_for(orchestrate_dir)
    work = orchestrate_dir / "phase-works/phase-5"
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    trace = require_json(trace_path, PHASE_TRACE_SCHEMAS["phase-5"])
    expected_fields = {
        "trace-schema",
        "trace-contract-version",
        "status",
        "framework-refit-trace-path",
        "framework-refit-trace-sha256",
        "final-roadmap-path",
        "final-roadmap-sha256",
        "atom-plan-mapping-path",
        "atom-plan-mapping-sha256",
        "candidate-final-change-plan-path",
        "candidate-final-change-plan-sha256",
        "frozen-evidence-authority-sha256",
        "phase-3-freeze-trace-path",
        "phase-3-freeze-trace-sha256",
        "candidate-handoff-sha256",
        "review-gate",
    }
    _require_exact_fields(
        trace,
        expected_fields,
        "Phase 5 review-pending trace",
    )
    if trace.get("status") != "review-pending":
        raise ValueError(
            "--refresh-review-candidate只接受review-pending trace"
        )
    gate = trace.get("review-gate")
    if not isinstance(gate, dict) or gate.get("status") != "pending":
        raise ValueError(
            "--refresh-review-candidate要求pending review-gate"
        )
    reviews = gate.get("reviews")
    repairs = gate.get("repairs")
    if (
        not isinstance(reviews, list)
        or not isinstance(repairs, list)
        or not reviews
        or len(reviews) != len(repairs)
    ):
        raise ValueError(
            "--refresh-review-candidate只允许在最新review完成repair后执行"
        )
    last_review = reviews[-1]
    if not isinstance(last_review, dict):
        raise ValueError("最新Phase 5 review非法")
    plan_path = work / "change-plan.md"
    old_refs = (
        (
            "framework-refit-trace",
            work / "framework-refit-trace.json",
            "framework-refit-sha256",
        ),
        (
            "final-roadmap",
            work / "final-roadmap.json",
            "final-roadmap-sha256",
        ),
        (
            "atom-plan-mapping",
            work / "atom-plan-mapping.json",
            "atom-plan-mapping-sha256",
        ),
        (
            "candidate-final-change-plan",
            plan_path,
            "final-change-plan-sha256",
        ),
    )
    for prefix, path, review_field in old_refs:
        if trace.get(f"{prefix}-path") != rel(path, repo_root):
            raise ValueError(
                f"Phase 5 candidate {prefix} path drift"
            )
        if trace.get(f"{prefix}-sha256") != last_review.get(
            review_field
        ):
            raise ValueError(
                f"Phase 5 candidate {prefix}历史digest未绑定最新review"
            )
    if (
        not plan_path.is_file()
        or sha256_file(plan_path)
        != trace.get("candidate-final-change-plan-sha256")
    ):
        raise ValueError("待刷新的旧candidate change-plan已漂移")
    for field in (
        "frozen-evidence-authority-sha256",
        "phase-3-freeze-trace-sha256",
        "candidate-handoff-sha256",
    ):
        if trace.get(field) != last_review.get(field):
            raise ValueError(
                f"Phase 5 candidate {field}历史digest未绑定最新review"
            )
    phase3_trace_path = orchestrate_dir / "trace/phase-3.trace.json"
    if trace.get("phase-3-freeze-trace-path") != rel(
        phase3_trace_path,
        repo_root,
    ):
        raise ValueError("Phase 5 candidate Phase 3 freeze path drift")
    forbidden = [
        orchestrate_dir / "change-plan.md",
        orchestrate_dir / "final-integration-review.json",
        orchestrate_dir / "final-integration-review.md",
        orchestrate_dir / "trace/workflow-completion.trace.json",
        work / "atom-plan-mapping.md",
        work / "capability-baseline-reconciliation.json",
        work / "capability-baseline-reconciliation.md",
        work / "final-packet-index.json",
    ]
    anchors = orchestrate_dir / "change-capability-anchors"
    if anchors.is_dir():
        forbidden.extend(
            child
            for child in anchors.iterdir()
            if child.name
            not in {
                "obligation-atom-index.json",
                "obligation-atom-index.md",
            }
        )
    published = [
        path for path in forbidden if path.exists() or path.is_symlink()
    ]
    if published:
        raise ValueError(
            "--refresh-review-candidate拒绝既有published surface："
            + ", ".join(str(path) for path in published)
        )

    refit_path = work / "framework-refit-trace.json"
    mapping_path = work / "atom-plan-mapping.json"
    refit = load_framework_refit(refit_path)
    status = validate_framework_refit(orchestrate_dir, refit)
    if status not in TERMINAL_STATUSES:
        raise ValueError("repair后的refit必须是accepted或adjusted")
    evidence = load_evidence(orchestrate_dir)
    roadmap, changes, capabilities, overlay = load_final_roadmap_defs(
        orchestrate_dir,
        evidence,
    )
    validate_framework_refit(
        orchestrate_dir,
        refit,
        changes,
        capabilities,
        overlay,
    )
    mapping = load_mapping(mapping_path, repo_root=repo_root)
    validate_mapping(
        evidence,
        mapping,
        changes,
        capabilities,
        overlay,
        repo_root=repo_root,
    )
    validate_gap_framework_impacts(orchestrate_dir, refit, mapping)
    plan_text = render_final_plan_from_roadmap(
        roadmap,
        changes,
        capabilities,
        overlay,
    )
    digests = phase5_candidate_authority(orchestrate_dir, plan_text)
    if (
        validate_phase5_review_gate(
            gate,
            current_digests=digests,
        )
        != "pending"
    ):
        raise ValueError("repair后review-gate必须保持pending")

    refreshed_trace = dict(trace)
    refreshed_trace.update(
        {
            "framework-refit-trace-sha256": digests[
                "framework-refit-sha256"
            ],
            "final-roadmap-sha256": digests[
                "final-roadmap-sha256"
            ],
            "atom-plan-mapping-sha256": digests[
                "atom-plan-mapping-sha256"
            ],
            "candidate-final-change-plan-sha256": digests[
                "final-change-plan-sha256"
            ],
            "frozen-evidence-authority-sha256": digests[
                "frozen-evidence-authority-sha256"
            ],
            "phase-3-freeze-trace-sha256": digests[
                "phase-3-freeze-trace-sha256"
            ],
            "candidate-handoff-sha256": digests[
                "candidate-handoff-sha256"
            ],
        }
    )
    transaction_root = Path(
        tempfile.mkdtemp(prefix=".phase5-refresh-", dir=orchestrate_dir)
    )
    stage = transaction_root / "stage"
    stage.mkdir()
    stage_plan = stage / "change-plan.md"
    stage_plan.write_text(plan_text, encoding="utf-8")
    stage_review = stage / "plan-refit-review.md"
    stage_review.write_text(
        render_framework_refit_review(orchestrate_dir, refit_path),
        encoding="utf-8",
    )
    stage_trace = stage / "phase-5.trace.json"
    write_json(stage_trace, refreshed_trace)
    _atomic_publish_phase5(
        (
            (stage_plan, plan_path),
            (stage_review, work / "plan-refit-review.md"),
            (stage_trace, trace_path),
        ),
        transaction_root,
        lambda: _load_phase5_review_gate(
            orchestrate_dir,
            plan_text,
            allowed_statuses={"pending"},
        ),
    )


def write_outputs(orchestrate_dir: Path) -> None:
    repo_root = repo_root_for(orchestrate_dir)
    anchors = orchestrate_dir / "change-capability-anchors"
    require_no_symlink_in_repo_path(anchors, repo_root, "change-capability-anchors")
    work = orchestrate_dir / "phase-works/phase-5"
    plan_path = work / "change-plan.md"
    refit_path = work / "framework-refit-trace.json"
    review_path = work / "plan-refit-review.md"
    mapping_path = work / "atom-plan-mapping.json"
    refit = load_framework_refit(refit_path)
    status = validate_framework_refit(orchestrate_dir, refit)
    if status == "blocked":
        _write_framework_blocked_outputs(
            orchestrate_dir,
            refit,
            refit_path,
            review_path,
        )
        return
    if status not in TERMINAL_STATUSES:
        raise ValueError("mechanical helper只处理accepted/adjusted framework refit trace")
    evidence = load_evidence(orchestrate_dir)
    roadmap, changes, capabilities, overlay = load_final_roadmap_defs(
        orchestrate_dir,
        evidence,
    )
    validate_framework_refit(orchestrate_dir, refit, changes, capabilities, overlay)
    mapping = load_mapping(mapping_path, repo_root=repo_root)
    validate_mapping(
        evidence,
        mapping,
        changes,
        capabilities,
        overlay,
        repo_root=repo_root,
    )
    validate_gap_framework_impacts(orchestrate_dir, refit, mapping)
    plan_text = render_final_plan_from_roadmap(
        roadmap,
        changes,
        capabilities,
        overlay,
    )
    review_gate = _load_phase5_review_gate(
        orchestrate_dir,
        plan_text,
        allowed_statuses={"pending", "passed", "blocked"},
    )
    review_gate_status = normalize_code(review_gate.get("status"))
    if review_gate_status == "blocked":
        _write_bounded_review_blocked_outputs(
            orchestrate_dir,
            plan_text,
            review_gate,
        )
        return
    if review_gate_status != "passed":
        raise ValueError("Phase 5 bounded review尚未passed")
    existing_public = _phase5_terminal_public_surfaces(orchestrate_dir)
    if existing_public:
        raise ValueError(
            "Phase 5 handoff拒绝覆盖或删除既有published surface："
            + ", ".join(str(path) for path in existing_public)
        )
    clean_legacy(orchestrate_dir)
    transaction_root = Path(
        tempfile.mkdtemp(prefix=".phase5-handoff-", dir=orchestrate_dir)
    )
    stage = transaction_root / "stage"
    stage_trace = stage / "phase-5.trace.json"
    stage.mkdir()
    try:
        handoff_digest, staged = _stage_phase5_handoff(
            orchestrate_dir,
            stage,
            plan_text=plan_text,
            refit_path=refit_path,
            mapping_path=mapping_path,
            evidence=evidence,
            changes=changes,
            capabilities=capabilities,
            mapping=mapping,
        )
        candidate_digests = phase5_candidate_authority(
            orchestrate_dir,
            plan_text,
        )
        if handoff_digest != candidate_digests[
            "candidate-handoff-sha256"
        ]:
            raise ValueError(
                "Phase 5 publish staging与reviewed candidate handoff不一致"
            )
        baseline_path = work / "capability-baseline-reconciliation.json"
        packet_index_path = work / "final-packet-index.json"
        trace_path = orchestrate_dir / "trace/phase-5.trace.json"
        write_json(
            stage_trace,
            {
                "trace-schema": PHASE_TRACE_SCHEMAS["phase-5"],
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": status,
                "final-roadmap-path": rel(
                    work / "final-roadmap.json",
                    repo_root,
                ),
                "final-roadmap-sha256": sha256_file(
                    work / "final-roadmap.json"
                ),
                "final-change-plan-path": rel(plan_path, repo_root),
                "final-change-plan-sha256": _raw_text_sha256(plan_text),
                "framework-refit-trace-path": rel(refit_path, repo_root),
                "framework-refit-trace-sha256": sha256_file(refit_path),
                "plan-refit-review-path": rel(review_path, repo_root),
                "plan-refit-review-sha256": sha256_file(
                    staged["review"]
                ),
                "atom-plan-mapping-path": rel(mapping_path, repo_root),
                "atom-plan-mapping-sha256": sha256_file(mapping_path),
                "capability-baseline-reconciliation-path": rel(
                    baseline_path,
                    repo_root,
                ),
                "capability-baseline-reconciliation-sha256": sha256_file(
                    staged["baseline"]
                ),
                "final-packet-index-path": rel(
                    packet_index_path,
                    repo_root,
                ),
                "final-packet-index-sha256": sha256_file(
                    staged["packet"]
                ),
                "frozen-evidence-authority-sha256": candidate_digests[
                    "frozen-evidence-authority-sha256"
                ],
                "phase-3-freeze-trace-path": rel(
                    orchestrate_dir / "trace/phase-3.trace.json",
                    repo_root,
                ),
                "phase-3-freeze-trace-sha256": candidate_digests[
                    "phase-3-freeze-trace-sha256"
                ],
                "candidate-handoff-sha256": handoff_digest,
                "review-gate": review_gate,
            },
        )
        entries = (
            (staged["review"], review_path),
            (staged["mapping-md"], work / "atom-plan-mapping.md"),
            (staged["baseline"], baseline_path),
            (
                staged["baseline-md"],
                work / "capability-baseline-reconciliation.md",
            ),
            (staged["packet"], packet_index_path),
            (staged["anchors"], anchors),
            (staged["root-plan"], orchestrate_dir / "change-plan.md"),
            (stage_trace, trace_path),
        )
        _atomic_publish_phase5(
            entries,
            transaction_root,
            lambda: validate_outputs(orchestrate_dir),
        )
    except Exception:
        shutil.rmtree(transaction_root, ignore_errors=True)
        raise


def validate_outputs(orchestrate_dir: Path) -> None:
    repo_root = repo_root_for(orchestrate_dir)
    anchors = orchestrate_dir / "change-capability-anchors"
    require_no_symlink_in_repo_path(anchors, repo_root, "change-capability-anchors")
    work = orchestrate_dir / "phase-works/phase-5"
    refit_path = work / "framework-refit-trace.json"
    refit = load_framework_refit(refit_path)
    status = validate_framework_refit(orchestrate_dir, refit)
    review_path = work / "plan-refit-review.md"
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    trace = require_json(trace_path, PHASE_TRACE_SCHEMAS["phase-5"])
    trace_status = normalize_code(trace.get("status"))
    block_kind = normalize_code(trace.get("block-kind"))
    if trace_status == "blocked" and block_kind == "framework-refit":
        if status != "blocked":
            raise ValueError(
                "framework-refit blocked trace要求refit status=blocked"
            )
        if not review_path.is_file() or review_path.read_text(encoding="utf-8") != render_framework_refit_review(orchestrate_dir, refit_path):
            raise ValueError("blocked plan refit review Markdown drift")
        expected_trace = _framework_blocked_trace_payload(
            orchestrate_dir,
            refit,
            refit_path,
            review_path,
        )
        if trace != expected_trace:
            raise ValueError("framework-refit blocked Phase 5 trace drift")
        existing = [
            rel(path, repo_root)
            for path in _phase5_framework_block_forbidden_surfaces(
                orchestrate_dir
            )
            if path not in {review_path, trace_path}
        ]
        if existing:
            raise ValueError(
                f"framework-refit blocked禁止candidate/terminal artifact："
                f"{existing}"
            )
        return
    if trace_status == "blocked" and block_kind == "bounded-review":
        if status not in TERMINAL_STATUSES:
            raise ValueError(
                "bounded-review blocked trace要求accepted/adjusted refit"
            )
        evidence = load_evidence(orchestrate_dir)
        roadmap, changes, capabilities, overlay = load_final_roadmap_defs(
            orchestrate_dir,
            evidence,
        )
        validate_framework_refit(
            orchestrate_dir,
            refit,
            changes,
            capabilities,
            overlay,
        )
        mapping = load_mapping(
            work / "atom-plan-mapping.json",
            repo_root=repo_root,
        )
        validate_mapping(
            evidence,
            mapping,
            changes,
            capabilities,
            overlay,
            repo_root=repo_root,
        )
        plan_text = render_final_plan_from_roadmap(
            roadmap,
            changes,
            capabilities,
            overlay,
        )
        plan_path = work / "change-plan.md"
        if (
            not plan_path.is_file()
            or plan_path.read_text(encoding="utf-8") != plan_text
        ):
            raise ValueError("bounded-review blocked candidate plan drift")
        if (
            not review_path.is_file()
            or review_path.read_text(encoding="utf-8")
            != render_framework_refit_review(
                orchestrate_dir,
                refit_path,
            )
        ):
            raise ValueError(
                "bounded-review blocked plan-refit-review drift"
            )
        gate = trace.get("review-gate")
        digests = phase5_candidate_authority(
            orchestrate_dir,
            plan_text,
        )
        if (
            validate_phase5_review_gate(
                gate,
                current_digests=digests,
            )
            != "blocked"
        ):
            raise ValueError(
                "bounded-review blocked trace要求完整blocked review-gate"
            )
        if not isinstance(gate, dict):
            raise ValueError("bounded-review blocked review-gate非法")
        expected_trace = _bounded_review_blocked_trace_payload(
            orchestrate_dir,
            plan_text,
            gate,
        )
        if trace != expected_trace:
            raise ValueError("bounded-review blocked Phase 5 trace drift")
        existing = [
            rel(path, repo_root)
            for path in _phase5_terminal_public_surfaces(orchestrate_dir)
            if path != trace_path
        ]
        if existing:
            raise ValueError(
                f"bounded-review blocked禁止terminal/public artifact："
                f"{existing}"
            )
        return
    if trace_status == "blocked":
        raise ValueError("blocked Phase 5 trace block-kind非法")
    if status == "blocked":
        raise ValueError(
            "framework-refit blocked必须使用canonical block-kind trace"
        )
    if status not in TERMINAL_STATUSES:
        raise ValueError("rendered output validation只处理terminal或blocked状态")
    plan = work / "change-plan.md"
    evidence = load_evidence(orchestrate_dir)
    roadmap, changes, capabilities, overlay = load_final_roadmap_defs(
        orchestrate_dir,
        evidence,
    )
    validate_framework_refit(orchestrate_dir, refit, changes, capabilities, overlay)
    expected_trace_fields = {
        "trace-schema", "trace-contract-version", "status",
        "final-roadmap-path", "final-roadmap-sha256",
        "final-change-plan-path", "final-change-plan-sha256",
        "framework-refit-trace-path", "framework-refit-trace-sha256",
        "plan-refit-review-path", "plan-refit-review-sha256",
        "atom-plan-mapping-path", "atom-plan-mapping-sha256",
        "capability-baseline-reconciliation-path", "capability-baseline-reconciliation-sha256",
        "final-packet-index-path", "final-packet-index-sha256",
        "frozen-evidence-authority-sha256",
        "phase-3-freeze-trace-path", "phase-3-freeze-trace-sha256",
        "candidate-handoff-sha256",
        "review-gate",
    }
    _require_exact_fields(trace, expected_trace_fields, "terminal Phase 5 trace")
    roadmap_path = work / "final-roadmap.json"
    terminal_refs = (
        ("final-roadmap", roadmap_path),
        ("final-change-plan", plan),
        ("framework-refit-trace", refit_path),
        ("plan-refit-review", review_path),
        ("atom-plan-mapping", work / "atom-plan-mapping.json"),
        (
            "capability-baseline-reconciliation",
            work / "capability-baseline-reconciliation.json",
        ),
        ("final-packet-index", work / "final-packet-index.json"),
    )
    if trace.get("status") != status:
        raise ValueError("Phase 5 trace status与refit authority不一致")
    for prefix, path in terminal_refs:
        if trace.get(f"{prefix}-path") != rel(path, repo_root):
            raise ValueError(f"Phase 5 trace {prefix} path drift")
        if (
            not path.is_file()
            or trace.get(f"{prefix}-sha256") != sha256_file(path)
        ):
            raise ValueError(f"Phase 5 trace {prefix} digest drift")
    current_candidate_digests = phase5_candidate_authority(
        orchestrate_dir,
        plan.read_text(encoding="utf-8"),
    )
    if (
        trace.get("frozen-evidence-authority-sha256")
        != current_candidate_digests[
            "frozen-evidence-authority-sha256"
        ]
        or trace.get("phase-3-freeze-trace-path")
        != rel(
            orchestrate_dir / "trace/phase-3.trace.json",
            repo_root,
        )
        or trace.get("phase-3-freeze-trace-sha256")
        != current_candidate_digests[
            "phase-3-freeze-trace-sha256"
        ]
        or trace.get("candidate-handoff-sha256")
        != current_candidate_digests["candidate-handoff-sha256"]
    ):
        raise ValueError(
            "terminal Phase 5 trace的frozen evidence或handoff digest drift"
        )
    if (
        validate_phase5_review_gate(
            trace.get("review-gate"),
            current_digests=current_candidate_digests,
        )
        != "passed"
    ):
        raise ValueError("terminal Phase 5 trace要求passed review-gate")
    if plan.read_text(encoding="utf-8") != render_final_plan_from_roadmap(
        roadmap,
        changes,
        capabilities,
        overlay,
    ):
        raise ValueError("Phase 5 change-plan mirror drift")
    if plan.read_bytes() != (orchestrate_dir / "change-plan.md").read_bytes():
        raise ValueError("根change-plan.md与Phase 5 plan不一致")
    if review_path.read_text(encoding="utf-8") != render_framework_refit_review(orchestrate_dir, refit_path):
        raise ValueError("plan refit review Markdown drift")
    mapping_path = work / "atom-plan-mapping.json"
    mapping = load_mapping(mapping_path, repo_root=repo_root)
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
    if set(packet_index) != {"trace-schema", "trace-contract-version", "packets"}:
        raise ValueError("final packet index顶层字段非法")
    if not isinstance(packet_index.get("packets"), list):
        raise ValueError("final packet index packets必须是array")
    indexed_changes: set[str] = set()
    capability_defs = {capability.slug: capability for capability in capabilities}
    expected_caps_by_change = {
        change.slug: [
            capability.slug
            for capability in capabilities
            if any(
                row.owner_change == change.slug
                and row.relation == "direct"
                and row.projection in SPEC_PROJECTIONS
                and row.target_capability == capability.slug
                for row in mapping.values()
            )
        ]
        for change in changes
    }
    _validate_public_anchor_surface(anchors, repo_root, changes, expected_caps_by_change)
    for position, packet in enumerate(packet_index.get("packets", [])):
        if not isinstance(packet, dict) or set(packet) != {
            "change", "depends-on", "change-source-path", "change-source-sha256", "capability-slices",
        }:
            raise ValueError("final packet index row非法")
        slug = normalize_code(packet.get("change"))
        indexed_changes.add(slug)
        change = next((item for item in changes if item.slug == slug), None)
        if change is None or packet.get("depends-on") != list(change.dependencies):
            raise ValueError(f"final packet Change或依赖drift：{slug}")
        change_source_path = orchestrate_dir / "change-capability-anchors" / slug / "change-source.md"
        require_no_symlink_in_repo_path(change_source_path, repo_root, f"{slug} change source")
        if packet.get("change-source-path") != lexical_rel(change_source_path, repo_root):
            raise ValueError(f"change source path drift：{slug}")
        if not change_source_path.is_file() or sha256_file(change_source_path) != packet.get("change-source-sha256"):
            raise ValueError(f"change source缺失或digest drift：{change_source_path}")
        if change_source_path.read_text(encoding="utf-8") != render_change_source(change, evidence, mapping):
            raise ValueError(f"change source内容drift：{change_source_path}")
        cap_impacts = {
            row.target_capability: row.capability_impact
            for row in mapping.values()
            if row.owner_change == slug and row.relation == "direct" and row.projection in SPEC_PROJECTIONS
        }
        expected_caps = expected_caps_by_change[slug]
        slices = packet.get("capability-slices")
        if not isinstance(slices, list):
            raise ValueError(f"{slug} capability-slices必须是array")
        if position > 0 and not slices:
            raise ValueError(f"只有roadmap首个Change可使用空capability-slices：{slug}")
        if not slices and change.dependencies:
            raise ValueError(f"foundation Change不得声明依赖：{slug}")
        actual_caps: List[str] = []
        for item in slices:
            if not isinstance(item, dict) or set(item) != {
                "capability", "capability-impact", "slice-path", "slice-sha256",
            }:
                raise ValueError(f"{slug} capability slice row非法")
            capability = normalize_code(item.get("capability"))
            actual_caps.append(capability)
            if item.get("capability-impact") != cap_impacts.get(capability):
                raise ValueError(f"{slug}/{capability} Capability impact drift")
            cap_path = change_source_path.parent / "capability-slices" / f"{capability}.md"
            require_no_symlink_in_repo_path(cap_path, repo_root, f"{slug}/{capability} capability slice")
            if item.get("slice-path") != lexical_rel(cap_path, repo_root):
                raise ValueError(f"{slug}/{capability} slice path drift")
            if not cap_path.is_file() or sha256_file(cap_path) != item.get("slice-sha256"):
                raise ValueError(f"{slug}/{capability} slice缺失或digest drift")
            if cap_path.read_text(encoding="utf-8") != render_capability_slice(
                slug, capability_defs[capability], cap_impacts[capability], evidence, mapping
            ):
                raise ValueError(f"{slug}/{capability} slice内容drift")
        if actual_caps != expected_caps:
            raise ValueError(f"{slug} capability slice顺序或集合drift")
    if indexed_changes != {item.slug for item in changes}:
        raise ValueError("final packet index Change集合与final plan不一致")
    if [normalize_code(row.get("change")) for row in packet_index["packets"]] != [item.slug for item in changes]:
        raise ValueError("final packet index顺序与roadmap不一致")
    if (anchors / "index.md").read_text(encoding="utf-8") != render_anchor_index(changes, capabilities, mapping, repo_root, anchors):
        raise ValueError("anchor index Markdown drift")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从Phase 5 refit/mapping状态机械生成允许的派生产物。")
    parser.add_argument("--orchestrate-dir", type=Path, default=Path("openspec/orchestrate"))
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--prepare-review",
        action="store_true",
        help="生成Phase 5 candidate plan与pending bounded-review trace，不发布handoff",
    )
    action.add_argument(
        "--write",
        action="store_true",
        help="bounded review passed后原子发布baseline、packets、trace和根plan",
    )
    action.add_argument(
        "--refresh-review-candidate",
        action="store_true",
        help="repair后保留review历史并原子重算完整candidate plan/digests",
    )
    parser.add_argument(
        "--writer-id",
        default="",
        help="--prepare-review所需的独立writer identity",
    )
    parser.add_argument("--validate-rendered", action="store_true", help="验证已生成派生产物")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.prepare_review:
            prepare_review(args.orchestrate_dir, args.writer_id)
        elif args.refresh_review_candidate:
            refresh_review_candidate(args.orchestrate_dir)
        elif args.write:
            write_outputs(args.orchestrate_dir)
        else:
            refit_path = args.orchestrate_dir / "phase-works/phase-5/framework-refit-trace.json"
            refit = load_framework_refit(refit_path)
            status = validate_framework_refit(args.orchestrate_dir, refit)
            if status in TERMINAL_STATUSES:
                mapping_path = args.orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
                evidence = load_evidence(args.orchestrate_dir)
                _, changes, capabilities, overlay = load_final_roadmap_defs(
                    args.orchestrate_dir,
                    evidence,
                )
                validate_framework_refit(args.orchestrate_dir, refit, changes, capabilities, overlay)
                repo_root = repo_root_for(args.orchestrate_dir)
                mapping = load_mapping(mapping_path, repo_root=repo_root)
                validate_mapping(
                    evidence,
                    mapping,
                    changes,
                    capabilities,
                    overlay,
                    repo_root=repo_root,
                )
                validate_gap_framework_impacts(args.orchestrate_dir, refit, mapping)
            elif status != "blocked":
                raise ValueError("mechanical helper只处理terminal或blocked状态")
        if args.validate_rendered:
            validate_outputs(args.orchestrate_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("Phase 5 mechanical derivation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
