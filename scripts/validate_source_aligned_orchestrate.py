#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 source-aligned orchestrate JSON trace sidecar。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from source_aligned_trace_lib import (
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_BASELINE_SCHEMA,
    DIRECT_PROJECTIONS,
    EVIDENCE_COLLECTION_INDEX_SCHEMA,
    EVIDENCE_PATCH_REQUEST_SCHEMA,
    FINAL_PACKET_INDEX_SCHEMA,
    FRAMEWORK_REFIT_TRACE_SCHEMA,
    GLOBAL_ATOM_ID_RE,
    GLOBAL_ATOM_INDEX_SCHEMA,
    KEBAB_CASE_RE,
    MANIFEST_SCHEMA,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    PHASE5_CHECKPOINT_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    IssueReporter,
    canonical_json_sha256,
    cell,
    evidence_patch_finding_fingerprint,
    line_range_label,
    merge_line_ranges,
    range_covered_by,
    read_json,
    sha256_file,
    source_atom_file_name,
    source_line_count,
    source_window_sha256,
    table_rows,
    uncovered_line_ranges,
    validate_kebab_keys,
    normalize_code,
    squash,
)
from render_source_aligned_orchestrate import (
    RENDER_CONTRACT_VERSION,
    build_evidence_collection_index,
    render_atom_plan_mapping,
    render_framework_refit_review,
    render_capability_baseline,
    render_global_index,
    render_phase2_index,
    render_phase2_source_atoms,
    render_coverage_review,
    render_evidence_collections,
)
from phase5_plan_refit import (
    CAPABILITY_IMPACTS,
    CAPABILITY_INITIAL_GATE_NAMES,
    CAPABILITY_REVIEW_DECISIONS,
    CHANGE_INITIAL_GATE_NAMES,
    CHANGE_REVIEW_DECISIONS,
    RELATIONS,
    build_baseline as build_phase5_baseline,
    framework_dependency_edges,
    framework_ga_lineage,
    framework_review_lineage,
    framework_semantic_digest_rows,
    load_framework_refit,
    load_evidence as load_phase5_evidence,
    load_mapping as load_phase5_mapping,
    parse_dependencies,
    parse_final_plan,
    render_anchor_index,
    render_capability_view,
    render_packet,
    validate_framework_refit,
    validate_gap_framework_impacts,
    validate_mapping as validate_phase5_mapping,
)

NO_OWNER_VALUES = {"", "None", "none", "null", "NULL"}
SPEC_PROJECTIONS = {"spec-requirement", "spec-guard"}
CHANGE_ONLY_PROJECTIONS = {"design-obligation", "verification-obligation"}
PHASE2_CANDIDATE_STATUSES = {
    "direct-candidate",
    "unassigned",
    "contextual-candidate",
    "unresolved-conflict",
    "unclassified",
}
PHASE2_PROJECTIONS = {*DIRECT_PROJECTIONS, "contextual-only", "unsure"}
PHASE2_ATOM_TYPES = {
    "behavior",
    "data-contract",
    "architecture-runtime",
    "verification",
    "scope-guard",
    "context",
}
PHASE2_NORMATIVITY = {"must", "must-not", "should", "context"}
PHASE2_ATOM_FIELDS = {
    "source-atom-id",
    "line-ranges",
    "atom-type",
    "source-fact",
    "normativity",
    "candidate-status",
    "candidate-artifact-projection",
    "candidate-owner-change",
    "candidate-target-capability",
    "rationale",
}
PHASE2_TOP_LEVEL_FIELDS = {
    "trace-schema",
    "trace-contract-version",
    "source-document",
    "source-sha256",
    "read-status",
    "canonical-owner",
    "source-role",
    "phase-1-candidate-changes-capabilities-considered",
    "source-atoms",
    "blockers",
    "language-self-check",
}
PHASE3_GAP_ID_RE = re.compile(r"^P3-GAP-\d{4}$")
PHASE3_DISPOSITION_ID_RE = re.compile(r"^RD-\d{4}$")
PHASE3_DISPOSITIONS = {"missing-obligation", "safe-non-obligation", "blocked"}
MAPPING_AMBIGUITY_DIMENSIONS = {"owner-change", "relation", "artifact-projection", "target-capability"}
PATCH_DEFECTS = {"quote-mismatch", "range-mismatch", "mixed-independent-occurrences", "missing-occurrence"}
PATCH_OPERATIONS = {"replace-quote", "adjust-range", "split", "add"}
PATCH_REQUEST_ID = "EPR-0001"
CHECKPOINT_ID = "P5CP-0001"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
LEGACY_CAPABILITY_FIELDS = {
    "candidate-owner-capability",
    "owner-capability",
    "final-owner-capability",
    "capability-advancement",
}
PHASE_NAMES = ("phase-1", "phase-2", "phase-3", "phase-4", "phase-5")
FINAL_PHASE5_STATUSES = {"accepted", "adjusted"}
NON_FINAL_PHASE4_STATUSES = {"blocked"}
NON_FINAL_PHASE5_STATUSES = {"needs-targeted-evidence-patch", "blocked"}
PHASE_ALLOWED_TRACE_STATUSES = {
    "phase-1": {"initial-plan-written", "blocked"},
    "phase-2": {"source-atoms-written", "blocked"},
    "phase-3": {"coverage-complete", "blocked"},
    "phase-4": {"assembled", *NON_FINAL_PHASE4_STATUSES},
    "phase-5": {*FINAL_PHASE5_STATUSES, *NON_FINAL_PHASE5_STATUSES},
}
WORKFLOW_PHASE_STATUS_VALUES = {
    "present",
    "reviewer-passed",
    "validator-passed",
    "repair-not-needed",
}


def rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def phase_status_value(value: object) -> str:
    if isinstance(value, dict):
        return normalize_code(value.get("status") or value.get("decision") or "")
    return normalize_code(value)


def is_no_owner(value: object) -> bool:
    return normalize_code(value) in NO_OWNER_VALUES


def reject_legacy_capability_fields(
    row: Dict[str, object],
    path: Path,
    reporter: IssueReporter,
    context: str,
) -> None:
    present = sorted(LEGACY_CAPABILITY_FIELDS.intersection(row))
    if present:
        reporter.error(
            "legacy-capability-field",
            path,
            f"{context} 将 v1 capability field 混入了 v2 契约：{', '.join(present)}",
        )


def trace_decision_status(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        data = read_json(path)
    except Exception:  # noqa: BLE001
        return ""
    return phase_status_value(data.get("status") or data.get("decision"))


def validate_trace_status(
    data: Dict[str, object],
    path: Path,
    reporter: IssueReporter,
    phase_name: str,
    rule_id: str,
) -> str:
    status = phase_status_value(data.get("status") or data.get("decision"))
    allowed = PHASE_ALLOWED_TRACE_STATUSES.get(phase_name, set())
    if not status:
        reporter.error(rule_id, path, f"{phase_name} trace 必须包含 canonical status/decision")
    elif allowed and status not in allowed:
        reporter.error(
            rule_id,
            path,
            f"{phase_name} trace status/decision 必须是 {', '.join(sorted(allowed))} 之一，实际为 {status}",
        )
    return status


def json_obj(path: Path, reporter: IssueReporter, schema: str | None = None) -> Dict[str, object]:
    if not path.exists():
        reporter.error("missing-json", path, "缺少必需的 JSON trace 文件")
        return {}
    try:
        data = read_json(path)
    except Exception as exc:  # noqa: BLE001
        reporter.error("invalid-json", path, f"解析 JSON object 失败：{exc}")
        return {}
    validate_kebab_keys(data, reporter, path)
    if schema and data.get("trace-schema") != schema:
        reporter.error("trace-schema", path, f"trace-schema 必须为 {schema}")
    if data.get("trace-contract-version") != TRACE_CONTRACT_VERSION:
        reporter.error("trace-contract-version", path, f"trace-contract-version 必须为 {TRACE_CONTRACT_VERSION}")
    return data


def require_file(path: Path, reporter: IssueReporter, rule_id: str, message: str) -> None:
    if not path.exists():
        reporter.error(rule_id, path, message)


def require_same_file(
    expected_path: Path,
    actual_path: Path,
    reporter: IssueReporter,
    rule_id: str,
    message: str,
) -> None:
    if not expected_path.exists() or not actual_path.exists():
        return
    if expected_path.read_bytes() != actual_path.read_bytes():
        reporter.error(rule_id, actual_path, message)


def validate_phase1_plan_structure(path: Path, reporter: IssueReporter) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    required_headings = [
        "## 输入",
        "## Source Semantic Landscape",
        "## Capability Map",
        "## Change 切分原则",
        "## Change Roadmap",
        "## Change-Capability Overlay",
        "## Phase 1 风险检查",
        "## Phase 1 语言自检",
    ]
    heading_positions: List[int] = []
    for heading in required_headings:
        try:
            heading_positions.append(lines.index(heading))
        except ValueError:
            reporter.error("phase1-plan-heading", path, f"缺少必需 heading：{heading}")
    if len(heading_positions) == len(required_headings) and heading_positions != sorted(heading_positions):
        reporter.error("phase1-plan-heading-order", path, "Phase 1 plan heading 顺序不符合固定输出模板")

    if "## Change Roadmap" not in lines or "## Phase 1 风险检查" not in lines:
        return
    roadmap_start = lines.index("## Change Roadmap") + 1
    risk_start = lines.index("## Phase 1 风险检查")
    roadmap = "\n".join(lines[roadmap_start:risk_start])
    required_roadmap_patterns = {
        "Change 名称": r"(?m)^- Change 名称[：:]",
        "单一 intent": r"(?m)^- 单一 intent[：:]",
        "source-backed outcome": r"(?m)^- source-backed outcome[：:]",
        "来源 evidence hint": r"(?m)^- 来源 evidence hint[：:]",
        "范围内": r"(?m)^- 范围内[：:]",
        "范围外": r"(?m)^- 范围外[：:]",
        "behavior completeness profile": r"(?m)^- behavior completeness profile[：:]",
        "trigger/context": r"(?m)^\s+- trigger/context[：:]",
        "normative behavior": r"(?m)^\s+- normative behavior[：:]",
        "observable outcome / invariant": r"(?m)^\s+- observable outcome / invariant[：:]",
        "important exception / error semantics": r"(?m)^\s+- important exception / error semantics[：:]",
        "acceptance evidence": r"(?m)^\s+- acceptance evidence[：:]",
        "硬依赖": r"(?m)^- 硬依赖[：:]",
        "排序理由": r"(?m)^- 排序理由[：:]",
        "独立完成与归档": r"(?m)^- 独立完成与归档[：:]",
        "拆分/合并判断": r"(?m)^- 拆分/合并判断[：:]",
    }
    for label, pattern in required_roadmap_patterns.items():
        if not re.search(pattern, roadmap):
            reporter.error("phase1-plan-roadmap", path, f"Change Roadmap 缺少字段：{label}")
    if re.search(r"(?m)^\s*-\s*(?:New|Modified)[：:]", roadmap):
        reporter.error(
            "phase1-plan-baseline-relation",
            path,
            "Phase 1 Change Roadmap 不得输出 OpenSpec New/Modified；使用 overlay 的 first-advancement/later-advancement",
        )

    overlay_rows = table_rows(path, ["Change", "Candidate Capability", "Roadmap Role"])
    allowed_roles = {"first-advancement", "later-advancement"}
    for row in overlay_rows:
        role = normalize_code(cell(row, "Roadmap Role"))
        if role not in allowed_roles:
            reporter.error(
                "phase1-plan-overlay-role",
                path,
                f"Change-Capability Overlay 的 Roadmap Role 非法：{role}",
            )

    risk_end = lines.index("## Phase 1 语言自检") if "## Phase 1 语言自检" in lines else len(lines)
    risk_lines = lines[risk_start + 1 : risk_end]
    risk_numbers = [
        int(match.group(1))
        for line in risk_lines
        if (match := re.match(r"^(1[01]|[1-9])[.)]\s+", line.strip()))
    ]
    if risk_numbers != list(range(1, 12)):
        reporter.error("phase1-plan-risk-checks", path, "Phase 1 风险检查必须按 1–11 顺序包含十一个编号门禁")


def check_ranges(
    path: Path,
    reporter: IssueReporter,
    line_ranges: object,
    source_document: str = "",
    repo_root: Path | None = None,
    context: str = "",
) -> None:
    if not isinstance(line_ranges, list) or not line_ranges:
        reporter.error("line-range", path, f"{context} 缺少非空 line-ranges")
        return
    line_count = source_line_count(repo_root, source_document) if repo_root and source_document else None
    for item in line_ranges:
        if not isinstance(item, dict):
            reporter.error("line-range", path, f"{context} 的 line-ranges item 必须是 object")
            continue
        start = item.get("start")
        end = item.get("end")
        if not isinstance(start, int) or not isinstance(end, int) or start <= 0 or end <= 0 or start > end:
            reporter.error("line-range", path, f"{context} 的 range 非法：{item}")
            continue
        if line_count is not None and end > line_count:
            reporter.error(
                "line-range-bounds",
                path,
                f"{context} 的 range L{start}-L{end} 超过 {source_document} 的行数 {line_count}",
            )


def check_atom_range(
    path: Path,
    reporter: IssueReporter,
    line_ranges: object,
    source_document: str,
    repo_root: Path,
    context: str,
) -> None:
    check_ranges(path, reporter, line_ranges, source_document, repo_root, context)
    if isinstance(line_ranges, list) and len(line_ranges) != 1:
        reporter.error(
            "atom-line-range-cardinality",
            path,
            f"{context} 的 line-ranges 必须且只能包含一个连续 range，实际为 {len(line_ranges)} 个",
        )


def check_source_fact_quote(
    path: Path,
    reporter: IssueReporter,
    source_fact: object,
    line_ranges: object,
    source_document: str,
    repo_root: Path,
    context: str,
) -> None:
    if not isinstance(source_fact, str) or not source_fact.strip():
        reporter.error("source-fact-quote", path, f"{context} 缺少非空 source-fact 原文摘录")
        return
    ranges = valid_range_items(line_ranges)
    if len(ranges) != 1:
        return
    source_path = repo_root / source_document
    if not source_path.exists():
        return
    source_lines = source_path.read_text(encoding="utf-8").splitlines()
    source_range = ranges[0]
    excerpt_window = "\n".join(source_lines[source_range["start"] - 1 : source_range["end"]])
    if source_fact not in excerpt_window:
        reporter.error(
            "source-fact-quote",
            path,
            f"{context} 的 source-fact 不是唯一 line range 内的原文连续摘录",
        )


def validate_rendered_markdown(
    orchestrate_dir: Path,
    json_path: Path,
    md_path: Path,
    renderer,
    reporter: IssueReporter,
    artifact: str,
) -> None:
    if not md_path.exists():
        reporter.error("markdown-mirror-missing", json_path, f"缺少已渲染的 Markdown mirror：{md_path}")
        return
    try:
        expected = renderer(orchestrate_dir, json_path)
    except Exception as exc:  # noqa: BLE001
        reporter.error("rendered-markdown-render-error", json_path, f"渲染 {artifact} Markdown mirror 失败：{exc}")
        return
    actual = md_path.read_text(encoding="utf-8")
    if actual != expected:
        reporter.error(
            "rendered-markdown-drift",
            md_path,
            (
                f"{artifact} Markdown mirror 与 canonical JSON 渲染结果不一致；"
                f"请重新运行 render_source_aligned_orchestrate.py --orchestrate-dir {orchestrate_dir.as_posix()} "
                f"--artifact {artifact} --write"
            ),
        )


def phase1_sources(orchestrate_dir: Path, repo_root: Path) -> List[Dict[str, object]]:
    data = read_json(orchestrate_dir / "trace/phase-1.trace.json")
    sources = data.get("source-documents")
    return sources if isinstance(sources, list) else []


def expected_manifest_artifacts(orchestrate_dir: Path, repo_root: Path) -> Dict[str, Tuple[str, str, str, str]]:
    specs: List[Tuple[Path, str, str, str, str]] = [
        (orchestrate_dir / "trace/phase-1.trace.json", PHASE_TRACE_SCHEMAS["phase-1"], "phase-1", "control", "phase-trace"),
        (orchestrate_dir / "trace/phase-2.trace.json", PHASE_TRACE_SCHEMAS["phase-2"], "phase-2", "control", "phase-trace"),
        (
            orchestrate_dir / "change-capability-anchors/obligation-atom-index.json",
            GLOBAL_ATOM_INDEX_SCHEMA,
            "phase-3",
            "semantic",
            "global-atom-index",
        ),
        (
            orchestrate_dir / "phase-works/phase-3/coverage-review.json",
            PHASE3_COVERAGE_REVIEW_SCHEMA,
            "phase-3",
            "semantic",
            "coverage-review",
        ),
        (orchestrate_dir / "trace/phase-3.trace.json", PHASE_TRACE_SCHEMAS["phase-3"], "phase-3", "control", "phase-trace"),
        (
            orchestrate_dir / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json",
            EVIDENCE_COLLECTION_INDEX_SCHEMA,
            "phase-4",
            "derived",
            "evidence-collection-index",
        ),
        (orchestrate_dir / "trace/phase-4.trace.json", PHASE_TRACE_SCHEMAS["phase-4"], "phase-4", "control", "phase-trace"),
        (
            orchestrate_dir / "phase-works/phase-5/framework-refit-trace.json",
            FRAMEWORK_REFIT_TRACE_SCHEMA,
            "phase-5",
            "semantic",
            "framework-refit-trace",
        ),
        (
            orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json",
            ATOM_PLAN_MAPPING_SCHEMA,
            "phase-5",
            "semantic",
            "atom-plan-mapping",
        ),
        (
            orchestrate_dir / "phase-works/phase-5/capability-baseline-reconciliation.json",
            CAPABILITY_BASELINE_SCHEMA,
            "phase-5",
            "derived",
            "capability-baseline",
        ),
        (
            orchestrate_dir / "phase-works/phase-5/final-packet-index.json",
            FINAL_PACKET_INDEX_SCHEMA,
            "phase-5",
            "derived",
            "final-packet-index",
        ),
        (orchestrate_dir / "trace/phase-5.trace.json", PHASE_TRACE_SCHEMAS["phase-5"], "phase-5", "control", "phase-trace"),
    ]
    patch_request_path = _patch_request_path(orchestrate_dir)
    checkpoint_path = _checkpoint_path(orchestrate_dir)
    if patch_request_path.exists():
        specs.append((patch_request_path, EVIDENCE_PATCH_REQUEST_SCHEMA, "phase-5", "control", "evidence-patch-request"))
    if checkpoint_path.exists():
        specs.append((checkpoint_path, PHASE5_CHECKPOINT_SCHEMA, "phase-5", "semantic", "phase-5-checkpoint"))
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    specs.extend((path, SOURCE_ATOMS_SCHEMA, "phase-2", "semantic", "source-atoms") for path in sorted(atom_root.glob("*.atoms.json")))
    return {
        rel(path, repo_root): (schema, phase, authority, role)
        for path, schema, phase, authority, role in specs
        if path.exists()
    }


def validate_manifest(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter, complete: bool = False) -> None:
    path = orchestrate_dir / "trace/manifest.json"
    data = json_obj(path, reporter, MANIFEST_SCHEMA)
    if not data:
        return
    exact_fields(
        data,
        {"trace-schema", "trace-contract-version", "authority", "orchestrate-dir", "phase-statuses", "artifacts"},
        path,
        reporter,
        "manifest-fields",
        "manifest v2",
    )
    if data.get("authority") != "control":
        reporter.error("manifest-authority", path, "manifest v2 authority必须是control")
    if data.get("orchestrate-dir") != rel(orchestrate_dir, repo_root):
        reporter.error("manifest-orchestrate-dir", path, "orchestrate-dir 与 CLI --orchestrate-dir 不一致")
    phase_statuses = data.get("phase-statuses")
    if not isinstance(phase_statuses, dict):
        reporter.error("manifest-phase-statuses", path, "phase-statuses 必须是 object")
        phase_statuses = {}
    for phase_name in PHASE_NAMES:
        if phase_name not in phase_statuses:
            reporter.error(
                "manifest-phase-status-missing",
                path,
                f"必须提供 phase-statuses.{phase_name}；缺少 trace sidecar 时请使用 missing",
            )
        phase_status = phase_status_value(phase_statuses.get(phase_name))
        if phase_status in WORKFLOW_PHASE_STATUS_VALUES:
            reporter.error(
                "manifest-phase-status-workflow-state",
                path,
                f"phase-statuses.{phase_name} 必须是 canonical phase decision/status，不能是 {phase_status}",
            )
        trace_path = orchestrate_dir / f"trace/{phase_name}.trace.json"
        trace_status = trace_decision_status(trace_path)
        if trace_path.exists() and not trace_status:
            reporter.error(
                "manifest-phase-status-trace-missing",
                path,
                f"manifest 记录 {phase_name} 前，{rel(trace_path, repo_root)} 必须包含 canonical status/decision",
            )
        if trace_path.exists() and trace_status and not phase_status:
            reporter.error(
                "manifest-phase-status-missing",
                path,
                f"phase-statuses.{phase_name} 必须与 {rel(trace_path, repo_root)} 的 status {trace_status} 一致",
            )
        if trace_status and phase_status and phase_status != trace_status:
            reporter.error(
                "manifest-phase-status-drift",
                path,
                f"phase-statuses.{phase_name} 必须与 {rel(trace_path, repo_root)} 的 status {trace_status} 一致，实际为 {phase_status}",
            )
        if not trace_path.exists() and phase_status != "missing":
            reporter.error(
                "manifest-phase-status-drift",
                path,
                f"缺少 {rel(trace_path, repo_root)} 时，phase-statuses.{phase_name} 必须为 missing，实际为 {phase_status}",
            )
    if complete:
        terminal_statuses = {
            "phase-1": {"initial-plan-written"},
            "phase-2": {"source-atoms-written"},
            "phase-3": {"coverage-complete"},
            "phase-4": {"assembled"},
            "phase-5": FINAL_PHASE5_STATUSES,
        }
        for phase_name, allowed in terminal_statuses.items():
            actual = phase_status_value(phase_statuses.get(phase_name))
            if actual not in allowed:
                reporter.error(
                    "manifest-complete-phase-status",
                    path,
                    f"--complete 要求 phase-statuses.{phase_name} 为 {sorted(allowed)}，实际为 {actual or 'missing'}",
                )
        phase1_trace_path = orchestrate_dir / "trace/phase-1.trace.json"
        if phase1_trace_path.exists():
            phase1_trace = read_json(phase1_trace_path)
            review_gate = phase1_trace.get("review-gate")
            gate_status = normalize_code(review_gate.get("status")) if isinstance(review_gate, dict) else ""
            if gate_status != "passed":
                reporter.error(
                    "manifest-complete-phase1-review-gate",
                    path,
                    f"--complete 要求 Phase 1 review-gate.status=passed，实际为 {gate_status or 'missing'}",
                )
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        reporter.error("manifest-artifacts", path, "artifacts 必须是 array")
        return
    expected_artifacts = expected_manifest_artifacts(orchestrate_dir, repo_root)
    seen_json_paths: Set[str] = set()
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            reporter.error("manifest-artifact", path, f"artifacts[{index}] 必须是 object")
            continue
        exact_fields(
            item,
            {"json-path", "trace-schema", "sha256", "phase", "role", "authority"},
            path,
            reporter,
            "manifest-artifact-fields",
            f"artifacts[{index}]",
        )
        trace_rel = item.get("json-path")
        digest = item.get("sha256")
        if not isinstance(trace_rel, str) or not trace_rel:
            reporter.error("manifest-artifact-json-path", path, f"artifacts[{index}] 缺少 json-path")
            continue
        if trace_rel in seen_json_paths:
            reporter.error("manifest-artifact-duplicate", path, f"json-path 重复：{trace_rel}")
        seen_json_paths.add(trace_rel)
        for field in ("trace-schema", "phase", "role", "authority"):
            if not isinstance(item.get(field), str) or not str(item.get(field)).strip():
                reporter.error("manifest-artifact-field", path, f"{trace_rel} 缺少非空 {field}")
        trace_path = repo_root / trace_rel
        if not trace_path.exists():
            reporter.error("manifest-artifact-json-path", path, f"{trace_rel} 不存在")
            continue
        current = sha256_file(trace_path)
        if digest != current:
            reporter.error("manifest-digest", path, f"{trace_rel} 的 sha256 不匹配")
        expected = expected_artifacts.get(trace_rel)
        if expected:
            expected_schema, expected_phase, expected_authority, expected_role = expected
            if item.get("trace-schema") != expected_schema:
                reporter.error("manifest-artifact-schema", path, f"{trace_rel} 的 trace-schema 必须为 {expected_schema}")
            if item.get("phase") != expected_phase:
                reporter.error("manifest-artifact-phase", path, f"{trace_rel} 的 phase 必须为 {expected_phase}")
            if item.get("authority") != expected_authority:
                reporter.error("manifest-artifact-authority", path, f"{trace_rel} 的 authority 必须为 {expected_authority}")
            if item.get("role") != expected_role:
                reporter.error("manifest-artifact-role", path, f"{trace_rel} 的 role 必须为 {expected_role}")
        try:
            trace_data = read_json(trace_path)
        except Exception:  # noqa: BLE001
            trace_data = {}
        if trace_data and item.get("trace-schema") != trace_data.get("trace-schema"):
            reporter.error("manifest-artifact-schema", path, f"{trace_rel} 的 trace-schema 与 canonical JSON 不一致")
    for trace_rel in sorted(set(expected_artifacts) - seen_json_paths):
        reporter.error("manifest-artifact-missing", path, f"manifest artifacts 缺少应登记JSON：{trace_rel}")


def _validate_phase1_review_gate(
    gate: object,
    trace_path: Path,
    plan_path: Path,
    reporter: IssueReporter,
) -> str:
    if not isinstance(gate, dict):
        reporter.error("phase1-review-gate", trace_path, "review-gate必须是object")
        return ""
    exact_fields(
        gate,
        {"status", "writer-id", "reviews", "repairs"},
        trace_path,
        reporter,
        "phase1-review-gate-fields",
        "review-gate",
    )
    status = normalize_code(gate.get("status"))
    if status not in {"passed", "blocked"}:
        reporter.error("phase1-review-gate-status", trace_path, "review-gate.status只允许passed|blocked")
    writer_id = squash(gate.get("writer-id"))
    if not writer_id:
        reporter.error("phase1-review-gate-writer", trace_path, "review-gate.writer-id不得为空")
    reviews = gate.get("reviews")
    if not isinstance(reviews, list) or not 1 <= len(reviews) <= 3:
        reporter.error("phase1-review-gate-reviews", trace_path, "reviews必须包含1..3轮")
        reviews = []
    reviewer_ids: Set[str] = set()
    review_by_round: Dict[int, Dict[str, object]] = {}
    for index, review in enumerate(reviews, start=1):
        if not isinstance(review, dict):
            reporter.error("phase1-review-row", trace_path, f"reviews[{index}]必须是object")
            continue
        exact_fields(
            review,
            {"round", "reviewer-id", "validator-status", "plan-sha256", "finding-fingerprints"},
            trace_path,
            reporter,
            "phase1-review-row-fields",
            f"reviews[{index}]",
        )
        round_number = review.get("round")
        if round_number != index:
            reporter.error("phase1-review-round", trace_path, "review round必须从1连续递增")
            continue
        reviewer_id = squash(review.get("reviewer-id"))
        if not reviewer_id or reviewer_id == writer_id or reviewer_id in reviewer_ids:
            reporter.error("phase1-reviewer-independence", trace_path, f"round {index} reviewer必须fresh且不同于writer")
        reviewer_ids.add(reviewer_id)
        if normalize_code(review.get("validator-status")) not in {"passed", "failed"}:
            reporter.error("phase1-review-validator-status", trace_path, f"round {index} validator-status非法")
        if not _is_sha256(review.get("plan-sha256")):
            reporter.error("phase1-review-plan-sha", trace_path, f"round {index} plan-sha256非法")
        findings = review.get("finding-fingerprints")
        if (
            not isinstance(findings, list)
            or any(not _is_sha256(item) for item in findings)
            or len(findings) != len(set(findings))
        ):
            reporter.error("phase1-review-findings", trace_path, f"round {index} finding-fingerprints必须是唯一SHA-256 array")
        review_by_round[index] = review
    if reviews and plan_path.exists() and reviews[-1].get("plan-sha256") != sha256_file(plan_path):
        reporter.error("phase1-review-current-plan", trace_path, "最后一轮review必须绑定当前initial plan digest")

    repairs = gate.get("repairs")
    if not isinstance(repairs, list) or len(repairs) > 2:
        reporter.error("phase1-review-gate-repairs", trace_path, "repairs必须是0..2条")
        repairs = []
    repair_by_round: Dict[int, Dict[str, object]] = {}
    repair_writer_ids: Set[str] = set()
    forced_block_rounds: Set[int] = set()
    for index, repair in enumerate(repairs, start=1):
        if not isinstance(repair, dict):
            reporter.error("phase1-repair-row", trace_path, f"repairs[{index}]必须是object")
            continue
        exact_fields(
            repair,
            {"round", "repair-writer-id", "finding-fingerprints", "before-plan-sha256", "after-plan-sha256"},
            trace_path,
            reporter,
            "phase1-repair-row-fields",
            f"repairs[{index}]",
        )
        round_number = repair.get("round")
        if not isinstance(round_number, int) or round_number not in review_by_round or round_number > len(reviews) or round_number in repair_by_round:
            reporter.error("phase1-repair-round", trace_path, f"repair round必须唯一对应已存在review：{round_number}")
            continue
        repair_by_round[round_number] = repair
        repair_writer = squash(repair.get("repair-writer-id"))
        if (
            not repair_writer
            or repair_writer == writer_id
            or repair_writer in reviewer_ids
            or repair_writer in repair_writer_ids
        ):
            reporter.error("phase1-repair-independence", trace_path, f"round {round_number} repair writer身份不独立")
        repair_writer_ids.add(repair_writer)
        findings = repair.get("finding-fingerprints")
        review_findings = review_by_round[round_number].get("finding-fingerprints")
        if (
            not isinstance(findings, list)
            or not findings
            or any(not _is_sha256(item) for item in findings)
            or len(findings) != len(set(findings))
        ):
            reporter.error("phase1-repair-findings", trace_path, f"round {round_number} repair findings必须是非空唯一SHA-256 array")
        elif isinstance(review_findings, list) and not set(findings).issubset(set(review_findings)):
            reporter.error("phase1-repair-findings", trace_path, f"round {round_number} repair不得消费review之外的finding")
        before_sha = repair.get("before-plan-sha256")
        after_sha = repair.get("after-plan-sha256")
        if not _is_sha256(before_sha) or not _is_sha256(after_sha):
            reporter.error("phase1-repair-plan-sha", trace_path, f"round {round_number} repair plan digest非法")
        if before_sha != review_by_round[round_number].get("plan-sha256"):
            reporter.error("phase1-repair-before", trace_path, f"round {round_number} before digest与review不一致")
        next_review = review_by_round.get(round_number + 1)
        if next_review and after_sha != next_review.get("plan-sha256"):
            reporter.error("phase1-repair-after", trace_path, f"round {round_number} after digest与下一轮review不一致")
        if before_sha == after_sha:
            forced_block_rounds.add(round_number)

    terminal_repair = repair_by_round.get(len(reviews))
    terminal_noop_repair = (
        status == "blocked"
        and isinstance(terminal_repair, dict)
        and terminal_repair.get("before-plan-sha256") == terminal_repair.get("after-plan-sha256")
    )
    if not (
        len(reviews) == len(repairs) + 1
        or (len(reviews) == len(repairs) and terminal_noop_repair)
    ):
        reporter.error(
            "phase1-review-gate-cardinality",
            trace_path,
            "reviews通常必须比repairs多1；仅blocked的terminal no-op repair允许两者等长",
        )

    for round_number in range(1, len(reviews)):
        repair = repair_by_round.get(round_number)
        if repair is None:
            reporter.error("phase1-repair-missing", trace_path, f"round {round_number}与下一轮review之间缺少repair")
    seen_findings: Set[str] = set()
    for round_number in range(1, len(reviews) + 1):
        review = review_by_round.get(round_number, {})
        findings = review.get("finding-fingerprints") if isinstance(review, dict) else []
        if not isinstance(findings, list) or not all(_is_sha256(item) for item in findings):
            continue
        if seen_findings.intersection(findings):
            forced_block_rounds.add(round_number)
        seen_findings.update(findings)
    if forced_block_rounds and status != "blocked":
        reporter.error(
            "phase1-review-no-progress",
            trace_path,
            "repair未改变plan，或同一finding在后续review再次出现时review-gate只能blocked",
        )
    if forced_block_rounds and len(reviews) > min(forced_block_rounds):
        reporter.error(
            "phase1-review-continued-after-block",
            trace_path,
            "重复finding或no-op repair一经确认必须立即blocked，不得继续repair/review",
        )
    if status == "passed" and reviews:
        last = reviews[-1]
        if last.get("finding-fingerprints") != [] or normalize_code(last.get("validator-status")) != "passed":
            reporter.error("phase1-review-pass", trace_path, "passed要求最后review无finding且validator-status=passed")
    if status == "blocked" and reviews and not forced_block_rounds:
        last = reviews[-1]
        if last.get("finding-fingerprints") == [] and normalize_code(last.get("validator-status")) == "passed":
            reporter.error(
                "phase1-review-block-reason",
                trace_path,
                "blocked必须由当前blocking finding、validator failure、重复finding或no-op repair支持",
            )
    return status


def validate_phase_1(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    path = orchestrate_dir / "trace/phase-1.trace.json"
    data = json_obj(path, reporter, PHASE_TRACE_SCHEMAS["phase-1"])
    if not data:
        return
    exact_fields(
        data,
        {"trace-schema", "trace-contract-version", "status", "source-documents", "initial-change-plan", "review-gate"},
        path,
        reporter,
        "phase1-trace-fields",
        "Phase 1 trace",
    )
    phase1_status = validate_trace_status(data, path, reporter, "phase-1", "phase1-status")
    initial_plan_path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    source_manifest_path = orchestrate_dir / "phase-works/phase-1/source-doc-manifest.md"
    require_file(initial_plan_path, reporter, "phase1-interface-artifact", "缺少 Phase 1 initial-change-plan.md")
    require_file(source_manifest_path, reporter, "phase1-interface-artifact", "缺少 Phase 1 source-doc-manifest.md")
    require_file(orchestrate_dir / "phase-works/phase-1/phase-1-agent-report.md", reporter, "phase1-interface-artifact", "缺少 Phase 1 agent 报告")
    validate_phase1_plan_structure(initial_plan_path, reporter)
    gate_status = _validate_phase1_review_gate(data.get("review-gate"), path, initial_plan_path, reporter)
    expected_gate_status = {
        "initial-plan-written": "passed",
        "blocked": "blocked",
    }.get(phase1_status)
    if expected_gate_status and gate_status != expected_gate_status:
        reporter.error(
            "phase1-status-review-gate-drift",
            path,
            f"Phase 1 status={phase1_status} 要求 review-gate.status={expected_gate_status}，实际为 {gate_status or 'missing'}",
        )

    if "change-plan" in data:
        reporter.error("phase1-legacy-plan-trace", path, "Phase 1 v2 trace 不得包含旧 change-plan object")
    initial_plan = data.get("initial-change-plan")
    if not isinstance(initial_plan, dict):
        reporter.error("phase1-initial-plan-trace", path, "initial-change-plan 必须是 object")
    else:
        legacy_fields = {
            "phase-plan-path",
            "phase-plan-sha256",
            "root-plan-path",
            "root-plan-sha256",
        }
        present_legacy_fields = sorted(legacy_fields.intersection(initial_plan))
        if present_legacy_fields:
            reporter.error(
                "phase1-legacy-plan-trace",
                path,
                f"initial-change-plan 包含旧字段：{', '.join(present_legacy_fields)}",
            )
        expected_plan_path = rel(initial_plan_path, repo_root)
        if initial_plan.get("artifact-path") != expected_plan_path:
            reporter.error(
                "phase1-initial-plan-path",
                path,
                f"initial-change-plan.artifact-path 必须为 {expected_plan_path}",
            )
        if initial_plan_path.exists() and initial_plan.get("sha256") != sha256_file(initial_plan_path):
            reporter.error("phase1-initial-plan-sha", path, "initial-change-plan.sha256 与当前文件不一致")

    sources = data.get("source-documents")
    if not isinstance(sources, list) or not sources:
        reporter.error("phase1-source-documents", path, "source-documents 必须是非空 array")
        return
    seen: Set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            reporter.error("phase1-source-document", path, "source-documents item 必须是 object")
            continue
        source_document = str(source.get("source-document", ""))
        if not source_document:
            reporter.error("phase1-source-document", path, "必须提供 source-document")
            continue
        if source_document in seen:
            reporter.error("phase1-source-duplicate", path, f"source-document 重复：{source_document}")
        seen.add(source_document)
        read_status = source.get("read-status")
        if read_status not in {"read-full", "non-source-artifact"}:
            reporter.error(
                "phase1-source-read-status",
                path,
                f"{source_document} 的 read-status 必须为 read-full 或 non-source-artifact",
            )
        for field in ("source-role", "coarse-topics-paths", "notes"):
            if not isinstance(source.get(field), str):
                reporter.error("phase1-source-field", path, f"{source_document} 的 {field} 必须是 string")
        source_path = repo_root / source_document
        if not source_path.exists():
            reporter.error("phase1-source-exists", path, f"来源文档不存在：{source_document}")
            continue
        if source.get("line-count") != len(source_path.read_text(encoding="utf-8").splitlines()):
            reporter.error("phase1-source-line-count", path, f"{source_document} 的 line-count 发生 drift")
        if source.get("source-sha256") != sha256_file(source_path):
            reporter.error("phase1-source-sha", path, f"{source_document} 的 source-sha256 发生 drift")

    manifest_rows = table_rows(
        source_manifest_path,
        ["Source Document", "Read Status", "Source Role", "Coarse Topics / Paths", "Notes"],
    )
    if len(manifest_rows) != len(sources):
        reporter.error(
            "phase1-source-manifest-count",
            source_manifest_path,
            f"source manifest 行数 {len(manifest_rows)} 与 trace source-documents 数量 {len(sources)} 不一致",
        )
    manifest_by_source: Dict[str, Dict[str, str]] = {}
    for row in manifest_rows:
        source_document = normalize_code(cell(row, "Source Document"))
        if not source_document:
            reporter.error("phase1-source-manifest-row", source_manifest_path, "source manifest 行缺少 Source Document")
            continue
        if source_document in manifest_by_source:
            reporter.error("phase1-source-manifest-duplicate", source_manifest_path, f"source manifest 重复：{source_document}")
        manifest_by_source[source_document] = row
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_document = str(source.get("source-document", ""))
        row = manifest_by_source.get(source_document)
        if row is None:
            reporter.error("phase1-source-manifest-missing", source_manifest_path, f"source manifest 缺少：{source_document}")
            continue
        expected_fields = {
            "Read Status": source.get("read-status", ""),
            "Source Role": source.get("source-role", ""),
            "Coarse Topics / Paths": source.get("coarse-topics-paths", ""),
            "Notes": source.get("notes", ""),
        }
        for header, expected in expected_fields.items():
            actual = squash(normalize_code(cell(row, header)))
            if actual != squash(expected):
                reporter.error(
                    "phase1-source-manifest-drift",
                    source_manifest_path,
                    f"{source_document} 的 {header} 与 trace 不一致",
                )


def work_queue_counts(orchestrate_dir: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    path = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms/work-queue.md"
    for row in table_rows(path, ["Source Documents", "Canonical Owner"]):
        for part in str(cell(row, "Source Documents")).split("<br>"):
            source = normalize_code(part)
            if source:
                counts[source] = counts.get(source, 0) + 1
    return counts


def phase1_framework_ids(orchestrate_dir: Path) -> tuple[Set[str], Set[str]]:
    path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    capabilities = {
        normalize_code(cell(row, "Candidate Capability"))
        for row in table_rows(path, ["Candidate Capability", "Purpose", "Owns", "Excludes"])
        if normalize_code(cell(row, "Candidate Capability"))
    }
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    changes = {
        normalize_code(match.group(1) or match.group(2))
        for match in re.finditer(
            r"(?m)^- Change 名称[：:]\s*(?:`([^`]+)`|([^\s。]+))",
            text,
        )
    }
    return changes, capabilities


def load_phase2_atoms(orchestrate_dir: Path, reporter: IssueReporter) -> Dict[str, Dict[str, object]]:
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    all_atoms: Dict[str, Dict[str, object]] = {}
    for sidecar in sorted(atom_root.glob("*.atoms.json")):
        data = json_obj(sidecar, reporter, SOURCE_ATOMS_SCHEMA)
        source_document = str(data.get("source-document", ""))
        for row in data.get("source-atoms", []) if isinstance(data.get("source-atoms"), list) else []:
            if not isinstance(row, dict):
                reporter.error("phase2-source-atom-row", sidecar, "source-atoms item 必须是 object")
                continue
            atom_id = str(row.get("source-atom-id", ""))
            key = f"{source_document}::{atom_id}"
            if key in all_atoms:
                reporter.error("phase2-source-atom-duplicate", sidecar, f"Phase 2 source atom row 重复：{key}")
            normalized = dict(row)
            normalized["source-document"] = source_document
            all_atoms[key] = normalized
    return all_atoms


def validate_phase2_mirror(orchestrate_dir: Path, reporter: IssueReporter) -> None:
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    for sidecar in sorted(atom_root.glob("*.atoms.json")):
        md_path = sidecar.with_suffix(".md")
        validate_rendered_markdown(
            orchestrate_dir,
            sidecar,
            md_path,
            render_phase2_source_atoms,
            reporter,
            "phase2-source-atoms",
        )
    index_path = atom_root / "index.md"
    if index_path.exists():
        try:
            expected = render_phase2_index(orchestrate_dir)
        except Exception as exc:  # noqa: BLE001
            reporter.error("phase2-index-render-error", index_path, f"无法重渲染Phase 2 index：{exc}")
        else:
            if index_path.read_text(encoding="utf-8") != expected:
                reporter.error("rendered-markdown-drift", index_path, "Phase 2 index与atoms JSON/work queue/trace重渲染结果不一致")


def validate_phase_2(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    require_file(
        orchestrate_dir / "phase-works/phase-1/initial-change-plan.md",
        reporter,
        "phase2-interface-input",
        "缺少 Phase 2 输入：Phase 1 initial-change-plan.md",
    )
    trace_path = orchestrate_dir / "trace/phase-2.trace.json"
    trace = json_obj(trace_path, reporter, PHASE_TRACE_SCHEMAS["phase-2"])
    trace_sources: Dict[str, Dict[str, object]] = {}
    mode = ""
    if trace:
        trace_status = validate_trace_status(trace, trace_path, reporter, "phase-2", "phase2-status")
        mode = normalize_code(trace.get("mode"))
        if trace_status == "blocked":
            exact_fields(
                trace,
                {
                    "trace-schema", "trace-contract-version", "status", "mode",
                    "patch-request-ref", "checkpoint-ref", "base-phase-2-trace-sha256",
                    "affected-sources", "issues",
                },
                trace_path,
                reporter,
                "phase2-trace-fields",
                "blocked Phase 2 trace",
            )
            if mode not in {"initial", "targeted-patch"}:
                reporter.error("phase2-trace-mode", trace_path, "blocked mode只允许initial|targeted-patch")
            if not isinstance(trace.get("issues"), list) or not trace.get("issues"):
                reporter.error("phase2-trace-issues", trace_path, "blocked要求非空issues[]")
            affected_sources = trace.get("affected-sources")
            if (
                not isinstance(affected_sources, list)
                or any(not isinstance(item, str) for item in affected_sources)
                or len(affected_sources) != len(set(affected_sources))
            ):
                reporter.error("phase2-blocked-affected-sources", trace_path, "blocked affected-sources必须是唯一string array")
                affected_sources = []
            if mode == "initial":
                if (
                    trace.get("patch-request-ref") is not None
                    or trace.get("checkpoint-ref") is not None
                    or trace.get("base-phase-2-trace-sha256") is not None
                    or affected_sources
                ):
                    reporter.error("phase2-blocked-patch-fields", trace_path, "initial blocked要求patch refs/base为null且affected-sources为空")
            elif mode == "targeted-patch":
                _validate_phase5_patch_commit_marker(orchestrate_dir, repo_root, reporter)
                _validate_artifact_ref(
                    trace.get("patch-request-ref"),
                    _patch_request_path(orchestrate_dir),
                    trace_path,
                    repo_root,
                    reporter,
                    "phase2-patch-request-ref",
                )
                _validate_artifact_ref(
                    trace.get("checkpoint-ref"),
                    _checkpoint_path(orchestrate_dir),
                    trace_path,
                    repo_root,
                    reporter,
                    "phase2-checkpoint-ref",
                )
                request = _validate_aborted_patch_request_snapshot(orchestrate_dir, reporter)
                base = request.get("base-artifacts") if isinstance(request.get("base-artifacts"), dict) else {}
                if trace.get("base-phase-2-trace-sha256") != base.get("phase-2-trace-sha256"):
                    reporter.error("phase2-blocked-base-trace", trace_path, "blocked base Phase 2 trace digest与request不一致")
                expected_sources: List[str] = []
                for target in request.get("targets", []) if isinstance(request.get("targets"), list) else []:
                    if isinstance(target, dict):
                        source = normalize_code(target.get("source-document"))
                        if source and source not in expected_sources:
                            expected_sources.append(source)
                if affected_sources != expected_sources:
                    reporter.error("phase2-blocked-affected-sources", trace_path, "targeted blocked affected-sources必须按request顺序恰好覆盖")
            return
        exact_fields(
            trace,
            {
                "trace-schema", "trace-contract-version", "status", "mode", "work-queue-path", "sources",
                "phase-report-path", "patch-request-ref", "checkpoint-ref", "patch-summary",
            },
            trace_path,
            reporter,
            "phase2-trace-fields",
            "Phase 2 trace",
        )
        if mode not in {"initial", "targeted-patch"}:
            reporter.error("phase2-trace-mode", trace_path, "mode只允许initial|targeted-patch")
        work_queue_path = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms/work-queue.md"
        phase_report_path = orchestrate_dir / "phase-works/phase-2/phase-2-agent-report.md"
        if trace.get("work-queue-path") != rel(work_queue_path, repo_root):
            reporter.error("phase2-trace-path", trace_path, "work-queue-path与canonical path不一致")
        if trace.get("phase-report-path") != rel(phase_report_path, repo_root):
            reporter.error("phase2-trace-path", trace_path, "phase-report-path与canonical path不一致")
        if mode == "initial":
            if trace.get("patch-request-ref") is not None or trace.get("checkpoint-ref") is not None or trace.get("patch-summary") is not None:
                reporter.error("phase2-initial-patch-fields", trace_path, "initial mode要求patch refs和patch-summary均为null")
        elif mode == "targeted-patch":
            _validate_phase5_patch_commit_marker(orchestrate_dir, repo_root, reporter)
            request_path = _patch_request_path(orchestrate_dir)
            checkpoint_path = _checkpoint_path(orchestrate_dir)
            _validate_artifact_ref(
                trace.get("patch-request-ref"), request_path, trace_path, repo_root, reporter, "phase2-patch-request-ref",
            )
            _validate_artifact_ref(
                trace.get("checkpoint-ref"), checkpoint_path, trace_path, repo_root, reporter, "phase2-checkpoint-ref",
            )
            request = _validate_patch_request(orchestrate_dir, repo_root, reporter)
            _validate_checkpoint(orchestrate_dir, repo_root, reporter)
            summary = trace.get("patch-summary")
            if not isinstance(summary, dict):
                reporter.error("phase2-patch-summary", trace_path, "targeted-patch要求patch-summary object")
                summary = {}
            else:
                exact_fields(
                    summary,
                    {
                        "base-phase-2-trace-sha256", "affected-sources", "changed-atoms", "new-atoms",
                        "patch-writer-id",
                    },
                    trace_path,
                    reporter,
                    "phase2-patch-summary-fields",
                    "patch-summary",
                )
            request_base = request.get("base-artifacts") if isinstance(request.get("base-artifacts"), dict) else {}
            if summary.get("base-phase-2-trace-sha256") != request_base.get("phase-2-trace-sha256"):
                reporter.error("phase2-patch-summary-base", trace_path, "patch-summary base Phase 2 trace与request不一致")
            request_targets = request.get("targets") if isinstance(request.get("targets"), list) else []
            expected_sources: List[str] = []
            expected_changed: List[Tuple[str, str, str]] = []
            expected_new: List[Tuple[str, str]] = []
            for target in request_targets:
                if not isinstance(target, dict):
                    continue
                source = normalize_code(target.get("source-document"))
                if source and source not in expected_sources:
                    expected_sources.append(source)
                atom_id = normalize_code(target.get("source-atom-id"))
                if atom_id:
                    expected_changed.append((source, atom_id, normalize_code(target.get("base-row-sha256"))))
                for new_id in target.get("new-source-atom-ids", []) if isinstance(target.get("new-source-atom-ids"), list) else []:
                    expected_new.append((source, normalize_code(new_id)))
            if summary.get("affected-sources") != expected_sources:
                reporter.error("phase2-patch-affected-sources", trace_path, "affected-sources必须按request target首次出现顺序恰好覆盖")
            current_atoms = _current_protected_rows(orchestrate_dir)["phase-2-atoms"]
            changed_rows = summary.get("changed-atoms")
            seen_changed: List[Tuple[str, str, str]] = []
            if not isinstance(changed_rows, list):
                reporter.error("phase2-patch-changed-atoms", trace_path, "changed-atoms必须是array")
                changed_rows = []
            for index, row in enumerate(changed_rows):
                if not isinstance(row, dict):
                    reporter.error("phase2-patch-changed-row", trace_path, f"changed-atoms[{index}]必须是object")
                    continue
                exact_fields(
                    row,
                    {"source-document", "source-atom-id", "before-row-sha256", "after-row-sha256"},
                    trace_path,
                    reporter,
                    "phase2-patch-changed-row-fields",
                    f"changed-atoms[{index}]",
                )
                source = normalize_code(row.get("source-document"))
                atom_id = normalize_code(row.get("source-atom-id"))
                before = normalize_code(row.get("before-row-sha256"))
                after = normalize_code(row.get("after-row-sha256"))
                seen_changed.append((source, atom_id, before))
                current_row = current_atoms.get(f"{source}::{atom_id}")
                if not _is_sha256(before) or not _is_sha256(after):
                    reporter.error("phase2-patch-changed-row-sha", trace_path, f"changed-atoms[{index}] digest非法")
                elif current_row is None or after != canonical_json_sha256(current_row) or before == after:
                    reporter.error("phase2-patch-changed-row-drift", trace_path, f"changed-atoms[{index}]未绑定真实before/after变化")
            if seen_changed != expected_changed:
                reporter.error("phase2-patch-changed-coverage", trace_path, "changed-atoms必须按request顺序恰好覆盖existing targets")
            new_rows = summary.get("new-atoms")
            seen_new: List[Tuple[str, str]] = []
            if not isinstance(new_rows, list):
                reporter.error("phase2-patch-new-atoms", trace_path, "new-atoms必须是array")
                new_rows = []
            for index, row in enumerate(new_rows):
                if not isinstance(row, dict):
                    reporter.error("phase2-patch-new-row", trace_path, f"new-atoms[{index}]必须是object")
                    continue
                exact_fields(
                    row,
                    {"source-document", "source-atom-id", "row-sha256"},
                    trace_path,
                    reporter,
                    "phase2-patch-new-row-fields",
                    f"new-atoms[{index}]",
                )
                source = normalize_code(row.get("source-document"))
                atom_id = normalize_code(row.get("source-atom-id"))
                digest = normalize_code(row.get("row-sha256"))
                seen_new.append((source, atom_id))
                current_row = current_atoms.get(f"{source}::{atom_id}")
                if not _is_sha256(digest) or current_row is None or digest != canonical_json_sha256(current_row):
                    reporter.error("phase2-patch-new-row-drift", trace_path, f"new-atoms[{index}]未绑定当前新增row")
            if seen_new != expected_new:
                reporter.error("phase2-patch-new-coverage", trace_path, "new-atoms必须按request顺序恰好覆盖声明的新source atom")
            if not squash(summary.get("patch-writer-id")):
                reporter.error("phase2-patch-writer", trace_path, "patch-writer-id不得为空")
        raw_trace_sources = trace.get("sources")
        if not isinstance(raw_trace_sources, list):
            reporter.error("phase2-trace-sources", trace_path, "Phase 2 trace sources 必须是 array")
        else:
            required = {
                "source-document",
                "atom-json-path",
                "atom-json-sha256",
                "atom-markdown-path",
                "canonical-owner",
                "read-status",
                "atom-count",
                "blockers",
            }
            for index, row in enumerate(raw_trace_sources, start=1):
                if not isinstance(row, dict):
                    reporter.error("phase2-trace-source-row", trace_path, f"sources[{index}] 必须是 object")
                    continue
                missing = sorted(required - set(row))
                if missing:
                    reporter.error("phase2-trace-source-field", trace_path, f"sources[{index}] 缺少字段：{', '.join(missing)}")
                unexpected = sorted(set(row) - required)
                if unexpected:
                    reporter.error("phase2-trace-source-field", trace_path, f"sources[{index}] 包含不允许的字段：{', '.join(unexpected)}")
                source_document = str(row.get("source-document", ""))
                if source_document in trace_sources:
                    reporter.error("phase2-trace-source-duplicate", trace_path, f"Phase 2 trace source 重复：{source_document}")
                trace_sources[source_document] = row
    require_file(orchestrate_dir / "phase-works/phase-2/source-obligation-atoms/work-queue.md", reporter, "phase2-interface-artifact", "缺少 Phase 2 work queue")
    require_file(orchestrate_dir / "phase-works/phase-2/source-obligation-atoms/index.md", reporter, "phase2-interface-artifact", "缺少 Phase 2 atom index")
    require_file(orchestrate_dir / "phase-works/phase-2/phase-2-agent-report.md", reporter, "phase2-interface-artifact", "缺少 Phase 2 agent 报告")
    sources = phase1_sources(orchestrate_dir, repo_root)
    phase1_changes, phase1_capabilities = phase1_framework_ids(orchestrate_dir)
    read_full_documents: Set[str] = set()
    queue_counts = work_queue_counts(orchestrate_dir)
    for source in sources:
        if not isinstance(source, dict) or source.get("read-status") != "read-full":
            continue
        source_document = str(source.get("source-document", ""))
        read_full_documents.add(source_document)
        count = queue_counts.get(source_document, 0)
        if count != 1:
            reporter.error("phase2-work-queue-coverage", trace_path, f"{source_document} 在 Phase 2 work queue 中出现了 {count} 次")
        sidecar = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms" / source_atom_file_name(source_document).replace(".md", ".json")
        data = json_obj(sidecar, reporter, SOURCE_ATOMS_SCHEMA)
        if not data:
            continue
        unexpected_top_level = sorted(set(data) - PHASE2_TOP_LEVEL_FIELDS)
        if unexpected_top_level:
            reporter.error(
                "phase2-top-level-field",
                sidecar,
                f"Phase 2 v4 sidecar 包含不允许的顶层字段：{', '.join(unexpected_top_level)}",
            )
        if data.get("source-document") != source_document:
            reporter.error("phase2-source-document", sidecar, "source-document 与 Phase 1 manifest 不一致")
        if data.get("read-status") != "read-full":
            reporter.error("phase2-read-status", sidecar, f"{source_document} 的 read-status 必须是 read-full")
        if not squash(data.get("canonical-owner")):
            reporter.error("phase2-canonical-owner", sidecar, f"{source_document} 缺少 canonical-owner")
        if data.get("source-role") != source.get("source-role"):
            reporter.error("phase2-source-role", sidecar, f"{source_document} 的 source-role 与 Phase 1 trace 不一致")
        source_path = repo_root / source_document
        if source_path.exists() and data.get("source-sha256") != sha256_file(source_path):
            reporter.error("phase2-source-sha", sidecar, f"{source_document} 的 source-sha256 发生 drift")
        atoms = data.get("source-atoms")
        if not isinstance(atoms, list):
            reporter.error("phase2-source-atoms", sidecar, "source-atoms 必须是 array")
            continue
        blockers = data.get("blockers")
        if not isinstance(blockers, list):
            reporter.error("phase2-blockers", sidecar, "blockers 必须是 array")
            blockers = []
        elif any(not isinstance(item, str) or not item.strip() for item in blockers):
            reporter.error("phase2-blockers", sidecar, "blockers[] 必须只包含非空 string")
        considered = data.get("phase-1-candidate-changes-capabilities-considered")
        if not isinstance(considered, list):
            reporter.error("phase2-considered-context", sidecar, "phase-1-candidate-changes-capabilities-considered 必须是 array")
        else:
            for index, item in enumerate(considered, start=1):
                if not isinstance(item, dict) or set(item) != {"change", "capabilities", "note"}:
                    reporter.error("phase2-considered-context", sidecar, f"considered[{index}] 必须只包含 change、capabilities[]、note")
                    continue
                if not isinstance(item.get("capabilities"), list):
                    reporter.error("phase2-considered-context", sidecar, f"considered[{index}].capabilities 必须是 array")
                change = normalize_code(item.get("change"))
                if change and change not in phase1_changes:
                    reporter.error("phase2-considered-change", sidecar, f"considered[{index}] 引用了 Phase 1 未声明的 Change：{change}")
                for capability in item.get("capabilities", []) if isinstance(item.get("capabilities"), list) else []:
                    capability_id = normalize_code(capability)
                    if capability_id not in phase1_capabilities:
                        reporter.error("phase2-considered-capability", sidecar, f"considered[{index}] 引用了 Phase 1 未声明的 Capability：{capability_id}")
        if not isinstance(data.get("language-self-check"), str) or not str(data.get("language-self-check", "")).strip():
            reporter.error("phase2-language-self-check", sidecar, "language-self-check 必须是非空 string")
        atom_ids: Set[str] = set()
        for row in atoms:
            if not isinstance(row, dict):
                reporter.error("phase2-source-atom-row", sidecar, "source-atoms item 必须是 object")
                continue
            context = str(row.get("source-atom-id", ""))
            reject_legacy_capability_fields(row, sidecar, reporter, context or "source atom")
            unexpected_fields = sorted(set(row) - PHASE2_ATOM_FIELDS)
            if unexpected_fields:
                reporter.error(
                    "phase2-atom-field",
                    sidecar,
                    f"{context or 'source atom'} 包含 Phase 2 v4 不允许的字段：{', '.join(unexpected_fields)}",
                )
            if not context:
                reporter.error("phase2-source-atom-id", sidecar, "必须提供 source-atom-id")
            elif context in atom_ids:
                reporter.error("phase2-source-atom-duplicate", sidecar, f"source-atom-id 重复：{context}")
            atom_ids.add(context)
            check_atom_range(sidecar, reporter, row.get("line-ranges"), source_document, repo_root, context)
            status = normalize_code(row.get("candidate-status"))
            projection = normalize_code(row.get("candidate-artifact-projection"))
            owner = normalize_code(row.get("candidate-owner-change"))
            target = normalize_code(row.get("candidate-target-capability"))
            atom_type = normalize_code(row.get("atom-type"))
            normativity = normalize_code(row.get("normativity"))
            rationale = squash(row.get("rationale"))
            check_source_fact_quote(
                sidecar,
                reporter,
                row.get("source-fact"),
                row.get("line-ranges"),
                source_document,
                repo_root,
                context,
            )
            if status not in PHASE2_CANDIDATE_STATUSES:
                reporter.error("phase2-candidate-status", sidecar, f"{context} 的 candidate-status 非法：{status}")
            if projection not in PHASE2_PROJECTIONS:
                reporter.error("phase2-projection", sidecar, f"{context} 的 candidate-artifact-projection 非法：{projection}")
            if atom_type not in PHASE2_ATOM_TYPES:
                reporter.error("phase2-atom-type", sidecar, f"{context} 的 atom-type 非法：{atom_type}")
            if normativity not in PHASE2_NORMATIVITY:
                reporter.error("phase2-normativity", sidecar, f"{context} 的 normativity 非法：{normativity}")
            if status in {"direct-candidate", "unassigned"} and projection == "contextual-only":
                reporter.error("phase2-direct-contextual-only", sidecar, f"{context} 是 actionable atom，却使用 contextual-only")
            if status == "direct-candidate" and (is_no_owner(owner) or owner in {"unassigned", "contextual"}):
                reporter.error("phase2-direct-change-owner", sidecar, f"{context} 的 direct-candidate 必须映射到现有 Change")
            elif status == "direct-candidate" and owner not in phase1_changes:
                reporter.error("phase2-direct-change-owner", sidecar, f"{context} 映射到了 Phase 1 未声明的 Change：{owner}")
            if status == "unassigned" and owner != "unassigned":
                reporter.error("phase2-unassigned-owner", sidecar, f"{context} 的 unassigned status 必须使用 owner=unassigned")
            if status == "contextual-candidate":
                if projection != "contextual-only":
                    reporter.error("phase2-contextual-projection", sidecar, f"{context} 的 contextual-candidate 必须使用 contextual-only")
                if owner not in {"contextual", "none"}:
                    reporter.error("phase2-contextual-owner", sidecar, f"{context} 的 contextual-candidate owner 必须是 contextual 或 none")
            if status in {"unresolved-conflict", "unclassified"}:
                if projection != "unsure" or owner != "none" or target != "none":
                    reporter.error("phase2-blocked-mapping", sidecar, f"{context} 的 conflict/unclassified 必须使用 unsure、owner=none、target=none")
                if not blockers:
                    reporter.error("phase2-blocker-required", sidecar, f"{context} 要求在 blockers[] 中记录阻塞项")
            if projection in {"design-obligation", "verification-obligation", "contextual-only", "unsure"} and target != "none":
                reporter.error("phase2-target", sidecar, f"{context} 的 {projection} 必须使用 target=none")
            if projection in SPEC_PROJECTIONS and target != "unresolved" and (is_no_owner(target) or not KEBAB_CASE_RE.match(target)):
                reporter.error("phase2-target", sidecar, f"{context} 的 spec/guard target 必须是现有 kebab-case Capability 或 unresolved")
            elif projection in SPEC_PROJECTIONS and target != "unresolved" and target not in phase1_capabilities:
                reporter.error("phase2-target", sidecar, f"{context} 映射到了 Phase 1 未声明的 Capability：{target}")
            if status in {"unassigned", "contextual-candidate", "unresolved-conflict", "unclassified"} and not rationale:
                reporter.error("phase2-rationale", sidecar, f"{context} 的 {status} 必须提供 rationale")

        trace_row = trace_sources.get(source_document)
        if trace_row is None:
            reporter.error("phase2-trace-source-coverage", trace_path, f"Phase 2 trace sources 缺少：{source_document}")
        else:
            expected = {
                "atom-json-path": rel(sidecar, repo_root),
                "atom-json-sha256": sha256_file(sidecar),
                "atom-markdown-path": rel(sidecar.with_suffix(".md"), repo_root),
                "canonical-owner": data.get("canonical-owner"),
                "read-status": data.get("read-status"),
                "atom-count": len(atoms),
                "blockers": blockers,
            }
            for field, expected_value in expected.items():
                if trace_row.get(field) != expected_value:
                    reporter.error("phase2-trace-source-drift", trace_path, f"{source_document} 的 {field} 与 canonical source atom sidecar 不一致")
    for extra_source in sorted(set(trace_sources) - read_full_documents):
        reporter.error("phase2-trace-source-coverage", trace_path, f"Phase 2 trace sources 包含非 read-full 或未知 source：{extra_source}")
    validate_phase2_mirror(orchestrate_dir, reporter)


def load_global_atoms(orchestrate_dir: Path, reporter: IssueReporter) -> Dict[str, Dict[str, object]]:
    path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    data = json_obj(path, reporter, GLOBAL_ATOM_INDEX_SCHEMA)
    if data:
        exact_fields(
            data,
            {"trace-schema", "trace-contract-version", "artifact-path", "global-atoms"},
            path,
            reporter,
            "phase3-global-index-fields",
            "global index",
        )
        expected_artifact = "openspec/orchestrate/change-capability-anchors/obligation-atom-index.md"
        if data.get("artifact-path") != expected_artifact:
            reporter.error("phase3-global-index-artifact-path", path, f"artifact-path 应为 {expected_artifact}")
    atoms: Dict[str, Dict[str, object]] = {}
    rows = data.get("global-atoms")
    if not isinstance(rows, list):
        reporter.error("phase3-global-atoms", path, "global-atoms 必须是 array")
        return atoms
    for row in rows:
        if not isinstance(row, dict):
            reporter.error("phase3-global-atom-row", path, "global-atoms item 必须是 object")
            continue
        atom_id = str(row.get("global-atom-id", ""))
        if not GLOBAL_ATOM_ID_RE.match(atom_id):
            reporter.error("phase3-ga-format", path, f"Global Atom ID 非法：{atom_id}")
            continue
        if atom_id in atoms:
            reporter.error("phase3-ga-duplicate", path, f"Global Atom ID 重复：{atom_id}")
        atoms[atom_id] = row
    return atoms


def validate_global_index_mirror(orchestrate_dir: Path, reporter: IssueReporter) -> None:
    json_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    md_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.md"
    if not json_path.exists():
        return
    validate_rendered_markdown(
        orchestrate_dir,
        json_path,
        md_path,
        render_global_index,
        reporter,
        "phase3-global-index",
    )


def validate_coverage_review_mirror(orchestrate_dir: Path, reporter: IssueReporter) -> None:
    json_path = orchestrate_dir / "phase-works/phase-3/coverage-review.json"
    if json_path.exists():
        validate_rendered_markdown(
            orchestrate_dir,
            json_path,
            json_path.with_suffix(".md"),
            render_coverage_review,
            reporter,
            "phase3-coverage-review",
        )


def read_full_sources(orchestrate_dir: Path, repo_root: Path) -> List[str]:
    return [
        str(source.get("source-document", ""))
        for source in phase1_sources(orchestrate_dir, repo_root)
        if isinstance(source, dict) and source.get("read-status") == "read-full" and source.get("source-document")
    ]


def valid_range_items(value: object) -> List[Dict[str, int]]:
    ranges: List[Dict[str, int]] = []
    if not isinstance(value, list):
        return ranges
    for item in value:
        if not isinstance(item, dict):
            continue
        start = item.get("start")
        end = item.get("end")
        if isinstance(start, int) and isinstance(end, int) and start > 0 and end >= start:
            ranges.append({"start": start, "end": end})
    return ranges


def phase2_evidence_ranges(orchestrate_dir: Path, source_document: str) -> List[Dict[str, int]]:
    sidecar = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms" / source_atom_file_name(source_document).replace(".md", ".json")
    if not sidecar.exists():
        return []
    data = read_json(sidecar)
    return merge_line_ranges(
        item
        for row in data.get("source-atoms", [])
        if isinstance(row, dict)
        for item in valid_range_items(row.get("line-ranges"))
    )


def exact_fields(row: Dict[str, object], expected: Set[str], path: Path, reporter: IssueReporter, rule: str, context: str) -> None:
    actual = set(row)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        reporter.error(rule, path, f"{context} 字段不符合 schema；缺少={missing or 'None'}，多余={extra or 'None'}")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def _patch_request_path(orchestrate_dir: Path) -> Path:
    return orchestrate_dir / "phase-works/phase-5/evidence-patch-request.json"


def _checkpoint_path(orchestrate_dir: Path) -> Path:
    return orchestrate_dir / "phase-works/phase-5/phase-5-checkpoint.json"


def _patch_base_artifact_paths(orchestrate_dir: Path) -> Dict[str, Path]:
    return {
        "phase-2-trace-sha256": orchestrate_dir / "trace/phase-2.trace.json",
        "phase-3-trace-sha256": orchestrate_dir / "trace/phase-3.trace.json",
        "global-atom-index-sha256": orchestrate_dir / "change-capability-anchors/obligation-atom-index.json",
        "coverage-review-sha256": orchestrate_dir / "phase-works/phase-3/coverage-review.json",
        "phase-4-index-sha256": (
            orchestrate_dir
            / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        ),
    }


def _phase2_trace_mode(orchestrate_dir: Path) -> str:
    path = orchestrate_dir / "trace/phase-2.trace.json"
    if not path.exists():
        return ""
    try:
        return normalize_code(read_json(path).get("mode"))
    except Exception:  # noqa: BLE001
        return ""


def _validate_artifact_ref(
    value: object,
    expected_path: Path,
    contract_path: Path,
    repo_root: Path,
    reporter: IssueReporter,
    rule: str,
) -> None:
    if not isinstance(value, dict):
        reporter.error(rule, contract_path, "artifact ref必须是object")
        return
    exact_fields(value, {"artifact-path", "sha256"}, contract_path, reporter, rule, "artifact ref")
    if value.get("artifact-path") != rel(expected_path, repo_root):
        reporter.error(rule, contract_path, f"artifact-path必须为{rel(expected_path, repo_root)}")
    if not _is_sha256(value.get("sha256")):
        reporter.error(rule, contract_path, "artifact ref sha256必须是64位小写十六进制")
    elif expected_path.exists() and value.get("sha256") != sha256_file(expected_path):
        reporter.error(rule, contract_path, "artifact ref sha256与当前文件不一致")


PROTECTED_ROW_KEY_FIELDS: Dict[str, str] = {
    "phase-2-atoms": "source-atom-key",
    "phase-3-documents": "source-document",
    "phase-3-gap-atoms": "gap-atom-id",
    "phase-3-dispositions": "disposition-id",
    "phase-3-mapping-ambiguities": "global-atom-id",
    "global-atoms": "global-atom-id",
    "phase-4-index-rows": "global-atom-id",
    "phase-4-rendered-artifacts": "artifact-path",
}

DEFECT_WITNESS_ROW_KINDS = {"phase-2-atom", "phase-3-disposition"}


def _validate_defect_witness_shape(
    value: object,
    path: Path,
    reporter: IssueReporter,
    context: str,
) -> List[Dict[str, object]]:
    if not isinstance(value, dict):
        reporter.error("evidence-patch-witness", path, f"{context} defect-witness必须是object")
        return []
    exact_fields(
        value,
        {"locator-origin", "source-sha256", "window-sha256"},
        path,
        reporter,
        "evidence-patch-witness-fields",
        context,
    )
    for field in ("source-sha256", "window-sha256"):
        if not _is_sha256(value.get(field)):
            reporter.error("evidence-patch-witness-sha", path, f"{context}.{field}必须是SHA-256")
    origin = value.get("locator-origin")
    if not isinstance(origin, dict):
        reporter.error("evidence-patch-witness-origin", path, f"{context}.locator-origin必须是object")
        return []
    exact_fields(
        origin,
        {"row-refs"},
        path,
        reporter,
        "evidence-patch-witness-origin-fields",
        context,
    )
    rows = origin.get("row-refs")
    if not isinstance(rows, list) or not rows:
        reporter.error("evidence-patch-witness-origin", path, f"{context}.row-refs必须是非空array")
        return []
    result: List[Dict[str, object]] = []
    seen: Set[Tuple[str, str]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            reporter.error("evidence-patch-witness-origin-row", path, f"{context}.row-refs[{index}]必须是object")
            continue
        exact_fields(
            row,
            {"artifact-path", "row-kind", "row-key", "row-sha256"},
            path,
            reporter,
            "evidence-patch-witness-origin-row-fields",
            f"{context}.row-refs[{index}]",
        )
        kind = normalize_code(row.get("row-kind"))
        key = normalize_code(row.get("row-key"))
        identity = (kind, key)
        if kind not in DEFECT_WITNESS_ROW_KINDS or not key or identity in seen:
            reporter.error("evidence-patch-witness-origin-row", path, f"{context} origin kind/key非法或重复：{identity}")
        seen.add(identity)
        if not normalize_code(row.get("artifact-path")) or not _is_sha256(row.get("row-sha256")):
            reporter.error("evidence-patch-witness-origin-row", path, f"{context} origin path/digest非法：{identity}")
        result.append(row)
    return result


def _current_protected_rows(orchestrate_dir: Path) -> Dict[str, Dict[str, Dict[str, object]]]:
    current: Dict[str, Dict[str, Dict[str, object]]] = {name: {} for name in PROTECTED_ROW_KEY_FIELDS}
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    for atom_path in sorted(atom_root.glob("*.atoms.json")):
        try:
            atom_data = read_json(atom_path)
        except Exception:  # noqa: BLE001
            continue
        source = normalize_code(atom_data.get("source-document"))
        for row in atom_data.get("source-atoms", []) if isinstance(atom_data.get("source-atoms"), list) else []:
            if isinstance(row, dict):
                atom_id = normalize_code(row.get("source-atom-id"))
                current["phase-2-atoms"][f"{source}::{atom_id}"] = row

    coverage_path = orchestrate_dir / "phase-works/phase-3/coverage-review.json"
    if coverage_path.exists():
        try:
            coverage = read_json(coverage_path)
        except Exception:  # noqa: BLE001
            coverage = {}
        coverage_specs = (
            ("phase-3-documents", "documents", "source-document"),
            ("phase-3-gap-atoms", "gap-atoms", "gap-atom-id"),
            ("phase-3-dispositions", "remainder-dispositions", "disposition-id"),
            ("phase-3-mapping-ambiguities", "mapping-ambiguities", "global-atom-id"),
        )
        for kind, field, key_field in coverage_specs:
            rows = coverage.get(field)
            for row in rows if isinstance(rows, list) else []:
                if isinstance(row, dict):
                    current[kind][normalize_code(row.get(key_field))] = row

    global_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    if global_path.exists():
        try:
            global_data = read_json(global_path)
        except Exception:  # noqa: BLE001
            global_data = {}
        rows = global_data.get("global-atoms")
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict):
                current["global-atoms"][normalize_code(row.get("global-atom-id"))] = row

    phase4_path = orchestrate_dir / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
    if phase4_path.exists():
        try:
            phase4 = read_json(phase4_path)
        except Exception:  # noqa: BLE001
            phase4 = {}
        for kind, field, key_field in (
            ("phase-4-index-rows", "rows", "global-atom-id"),
            ("phase-4-rendered-artifacts", "rendered-artifacts", "artifact-path"),
        ):
            rows = phase4.get(field)
            for row in rows if isinstance(rows, list) else []:
                if isinstance(row, dict):
                    current[kind][normalize_code(row.get(key_field))] = row
    return current


def _validate_protected_rows(
    value: object,
    orchestrate_dir: Path,
    path: Path,
    reporter: IssueReporter,
    rule_prefix: str,
    *,
    verify_current_surfaces: bool = True,
) -> Dict[str, Set[str]]:
    protected_keys: Dict[str, Set[str]] = {name: set() for name in PROTECTED_ROW_KEY_FIELDS}
    if not isinstance(value, dict):
        reporter.error(f"{rule_prefix}-shape", path, "protected rows必须是object")
        return protected_keys
    exact_fields(value, set(PROTECTED_ROW_KEY_FIELDS), path, reporter, f"{rule_prefix}-fields", "protected rows")
    current = _current_protected_rows(orchestrate_dir) if verify_current_surfaces else {}
    for kind, key_field in PROTECTED_ROW_KEY_FIELDS.items():
        rows = value.get(kind)
        if not isinstance(rows, list):
            reporter.error(f"{rule_prefix}-rows", path, f"{kind}必须是array")
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                reporter.error(f"{rule_prefix}-row", path, f"{kind}[{index}]必须是object")
                continue
            exact_fields(row, {key_field, "sha256"}, path, reporter, f"{rule_prefix}-row-fields", f"{kind}[{index}]")
            key = normalize_code(row.get(key_field))
            if not key or key in protected_keys[kind]:
                reporter.error(f"{rule_prefix}-row-key", path, f"{kind}稳定key为空或重复：{key}")
                continue
            protected_keys[kind].add(key)
            if not _is_sha256(row.get("sha256")):
                reporter.error(f"{rule_prefix}-row-sha", path, f"{kind}/{key} sha256非法")
                continue
            if verify_current_surfaces:
                current_row = current[kind].get(key)
                if current_row is None:
                    reporter.error(f"{rule_prefix}-row-missing", path, f"受保护row不存在：{kind}/{key}")
                elif row.get("sha256") != canonical_json_sha256(current_row):
                    reporter.error(f"{rule_prefix}-row-drift", path, f"受保护row发生变化：{kind}/{key}")
    return protected_keys


def _validate_patch_request(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
) -> Dict[str, object]:
    path = _patch_request_path(orchestrate_dir)
    data = json_obj(path, reporter, EVIDENCE_PATCH_REQUEST_SCHEMA)
    if not data:
        return {}
    exact_fields(
        data,
        {"trace-schema", "trace-contract-version", "request-id", "base-artifacts", "targets", "protected-rows"},
        path,
        reporter,
        "evidence-patch-fields",
        "evidence patch request",
    )
    if data.get("request-id") != PATCH_REQUEST_ID:
        reporter.error("evidence-patch-request-id", path, f"单次patch request-id必须为{PATCH_REQUEST_ID}")
    base = data.get("base-artifacts")
    base_fields = {
        "phase-2-trace-sha256", "phase-3-trace-sha256", "global-atom-index-sha256",
        "coverage-review-sha256", "phase-4-index-sha256",
    }
    patch_applied = _phase2_trace_mode(orchestrate_dir) == "targeted-patch"
    if not isinstance(base, dict):
        reporter.error("evidence-patch-base", path, "base-artifacts必须是object")
    else:
        exact_fields(base, base_fields, path, reporter, "evidence-patch-base-fields", "base-artifacts")
        for field in base_fields:
            if not _is_sha256(base.get(field)):
                reporter.error("evidence-patch-base-sha", path, f"base-artifacts.{field}必须是SHA-256")

        base_paths = _patch_base_artifact_paths(orchestrate_dir)
        if not patch_applied:
            for field, artifact_path in base_paths.items():
                if not artifact_path.exists():
                    reporter.error("evidence-patch-base-artifact", path, f"请求初态缺少base artifact：{artifact_path}")
                elif base.get(field) != sha256_file(artifact_path):
                    reporter.error(
                        "evidence-patch-base-current-drift",
                        path,
                        f"请求初态base-artifacts.{field}与当前artifact不一致",
                    )

    protected = _validate_protected_rows(data.get("protected-rows"), orchestrate_dir, path, reporter, "evidence-patch-protected")
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        reporter.error("evidence-patch-targets", path, "targets必须是非空array")
        targets = []
    target_fields = {
        "source-document", "source-atom-id", "global-atom-id", "evidence-ref", "defect",
        "allowed-operations", "allowed-line-window", "new-source-atom-ids", "base-row", "base-row-sha256",
        "canonical-owner", "reason", "defect-witness",
    }
    current_rows = _current_protected_rows(orchestrate_dir)
    global_rows = current_rows["global-atoms"]
    atom_rows = current_rows["phase-2-atoms"]
    source_owners: Dict[str, str] = {}
    phase2_source_digests: Dict[str, str] = {}
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    for atom_path in sorted(atom_root.glob("*.atoms.json")):
        try:
            atom_data = read_json(atom_path)
        except Exception:  # noqa: BLE001
            continue
        source_owners[normalize_code(atom_data.get("source-document"))] = squash(atom_data.get("canonical-owner"))
        phase2_source_digests[normalize_code(atom_data.get("source-document"))] = normalize_code(
            atom_data.get("source-sha256")
        )
    phase1_source_digests = {
        normalize_code(row.get("source-document")): normalize_code(row.get("source-sha256"))
        for row in phase1_sources(orchestrate_dir, repo_root)
        if isinstance(row, dict) and normalize_code(row.get("source-document"))
    }
    read_full = set(read_full_sources(orchestrate_dir, repo_root))
    seen_targets: Set[str] = set()
    seen_new_ids: Set[str] = set()
    new_atom_keys: Set[str] = set()
    add_ids: List[str] = []
    target_atom_keys: Set[str] = set()
    target_ga_ids: Set[str] = set()
    target_sources: Set[str] = set()
    target_windows: Dict[str, List[Dict[str, int]]] = {}
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            reporter.error("evidence-patch-target", path, f"targets[{index}]必须是object")
            continue
        exact_fields(target, target_fields, path, reporter, "evidence-patch-target-fields", f"targets[{index}]")
        source = normalize_code(target.get("source-document"))
        atom_id = normalize_code(target.get("source-atom-id"))
        ga_id = normalize_code(target.get("global-atom-id"))
        defect = normalize_code(target.get("defect"))
        target_key = f"{source}::{atom_id or '<missing>'}"
        if target_key in seen_targets:
            reporter.error("evidence-patch-target-duplicate", path, f"重复target：{target_key}")
        seen_targets.add(target_key)
        if source not in read_full:
            reporter.error("evidence-patch-target-source", path, f"target source不是read-full source：{source}")
        target_sources.add(source)
        source_path = repo_root / source
        if not source_path.exists():
            reporter.error("evidence-patch-source-missing", path, f"target source不存在：{source}")
        else:
            current_source_sha = sha256_file(source_path)
            if (
                phase1_source_digests.get(source) != current_source_sha
                or phase2_source_digests.get(source) != current_source_sha
            ):
                reporter.error(
                    "evidence-patch-source-drift",
                    path,
                    f"target source必须与Phase 1/2冻结digest保持一致：{source}",
                )
        if defect not in PATCH_DEFECTS:
            reporter.error("evidence-patch-defect", path, f"{target_key} defect非法：{defect}")
        operations = target.get("allowed-operations")
        if (
            not isinstance(operations, list)
            or not operations
            or any(not isinstance(item, str) for item in operations)
            or len(operations) != len(set(operations))
        ):
            reporter.error("evidence-patch-operations", path, f"{target_key} allowed-operations必须是非空唯一array")
            operations = []
        normalized_ops = [normalize_code(item) for item in operations]
        if any(item not in PATCH_OPERATIONS for item in normalized_ops):
            reporter.error("evidence-patch-operations", path, f"{target_key}包含非法operation")
        operation_compatibility = {
            "quote-mismatch": ({"replace-quote", "adjust-range"}, "replace-quote"),
            "range-mismatch": ({"adjust-range", "replace-quote"}, "adjust-range"),
            "mixed-independent-occurrences": ({"split", "adjust-range", "replace-quote"}, "split"),
            "missing-occurrence": ({"add"}, "add"),
        }
        if defect in operation_compatibility:
            allowed_set, required_operation = operation_compatibility[defect]
            if set(normalized_ops) - allowed_set or required_operation not in normalized_ops:
                reporter.error(
                    "evidence-patch-operation-compatibility",
                    path,
                    f"{target_key} 的operation与defect={defect}不兼容",
                )
        window = target.get("allowed-line-window")
        if not isinstance(window, dict):
            reporter.error("evidence-patch-window", path, f"{target_key} allowed-line-window必须是object")
        else:
            if "add" in normalized_ops and defect != "missing-occurrence":
                reporter.error("evidence-patch-existing-add", path, "existing target不得包含add operation")
            exact_fields(window, {"start", "end"}, path, reporter, "evidence-patch-window-fields", target_key)
            start, end = window.get("start"), window.get("end")
            line_count = source_line_count(repo_root, source) or 0
            if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start or end > line_count:
                reporter.error("evidence-patch-window", path, f"{target_key} allowed-line-window越界或非法")
            else:
                target_windows.setdefault(source, []).append({"start": start, "end": end})
        canonical_owner = squash(target.get("canonical-owner"))
        if not canonical_owner or not squash(target.get("reason")):
            reporter.error("evidence-patch-target-required", path, f"{target_key} canonical-owner/reason不得为空")
        if source_owners.get(source) and canonical_owner != source_owners[source]:
            reporter.error(
                "evidence-patch-canonical-owner",
                path,
                f"{target_key} canonical-owner与Phase 2 source owner不一致",
            )
        new_ids = target.get("new-source-atom-ids")
        if (
            not isinstance(new_ids, list)
            or any(not isinstance(item, str) or not normalize_code(item) for item in new_ids)
            or len(new_ids) != len(set(new_ids))
        ):
            reporter.error("evidence-patch-new-ids", path, f"{target_key} new-source-atom-ids必须是唯一array")
            new_ids = []
        for new_id in [normalize_code(item) for item in new_ids]:
            if not new_id or new_id in seen_new_ids:
                reporter.error("evidence-patch-new-id-duplicate", path, f"新source atom ID为空或重复：{new_id}")
            seen_new_ids.add(new_id)
            new_atom_keys.add(f"{source}::{new_id}")

        missing = defect == "missing-occurrence"
        if missing:
            if (
                atom_id
                or ga_id
                or target.get("evidence-ref") is not None
                or target.get("base-row") is not None
                or target.get("base-row-sha256") is not None
            ):
                reporter.error("evidence-patch-missing-identity", path, "missing-occurrence要求旧identity、base-row和base-row-sha256均为null")
            if set(normalized_ops) != {"add"} or not new_ids:
                reporter.error("evidence-patch-missing-operation", path, "missing-occurrence只允许add且必须提供新ID")
            add_ids.extend(normalize_code(item) for item in new_ids)
        else:
            if not atom_id or not GLOBAL_ATOM_ID_RE.match(ga_id) or not isinstance(target.get("evidence-ref"), dict):
                reporter.error("evidence-patch-existing-identity", path, f"{target_key}必须提供source atom、GA和evidence-ref")
            base_row = target.get("base-row")
            if not isinstance(base_row, dict):
                reporter.error("evidence-patch-base-row", path, f"{target_key} base-row必须是完整的原始source atom row")
                base_row = {}
            else:
                exact_fields(
                    base_row,
                    PHASE2_ATOM_FIELDS,
                    path,
                    reporter,
                    "evidence-patch-base-row-fields",
                    f"{target_key}.base-row",
                )
                if normalize_code(base_row.get("source-atom-id")) != atom_id:
                    reporter.error("evidence-patch-base-row-id", path, f"{target_key} base-row必须保留source-atom-id")
                check_source_fact_quote(
                    path,
                    reporter,
                    base_row.get("source-fact"),
                    base_row.get("line-ranges"),
                    source,
                    repo_root,
                    f"{target_key}.base-row",
                )
                if isinstance(window, dict):
                    allowed = {"start": window.get("start"), "end": window.get("end")}
                    base_ranges = valid_range_items(base_row.get("line-ranges"))
                    if not base_ranges or any(not range_covered_by(item, [allowed]) for item in base_ranges):
                        reporter.error(
                            "evidence-patch-base-window",
                            path,
                            f"{target_key} base row range必须落在预先固定的allowed-line-window内",
                        )
            if not _is_sha256(target.get("base-row-sha256")):
                reporter.error("evidence-patch-base-row-sha", path, f"{target_key} base-row-sha256非法")
            elif base_row and target.get("base-row-sha256") != canonical_json_sha256(base_row):
                reporter.error("evidence-patch-base-row-sha", path, f"{target_key} base-row-sha256与immutable base-row不一致")
            target_atom_keys.add(f"{source}::{atom_id}")
            target_ga_ids.add(ga_id)
            expected_ref = {"kind": "phase-2-source-atom", "source-document": source, "source-atom-id": atom_id}
            if target.get("evidence-ref") != expected_ref:
                reporter.error("evidence-patch-evidence-ref", path, f"{target_key} evidence-ref与identity不一致")
            global_row = global_rows.get(ga_id)
            if global_row is None or global_row.get("evidence-ref") != expected_ref:
                reporter.error("evidence-patch-ga-ref", path, f"{ga_id}未保持原evidence-ref")
            current_atom = atom_rows.get(f"{source}::{atom_id}")
            if current_atom is None:
                reporter.error("evidence-patch-target-atom", path, f"target atom不存在：{target_key}")
            else:
                current_sha = canonical_json_sha256(current_atom)
                if patch_applied and current_sha == target.get("base-row-sha256"):
                    reporter.error("evidence-patch-target-unchanged", path, f"target atom在targeted-patch后没有变化：{target_key}")
                if not patch_applied and current_sha != target.get("base-row-sha256"):
                    reporter.error("evidence-patch-base-row-drift", path, f"请求初态target atom与base-row-sha256不一致：{target_key}")
                if not patch_applied and base_row and current_atom != base_row:
                    reporter.error("evidence-patch-base-row-drift", path, f"请求初态target atom与immutable base-row不一致：{target_key}")
                if patch_applied and base_row:
                    mutable_fields: Set[str] = set()
                    if "replace-quote" in normalized_ops:
                        mutable_fields.add("source-fact")
                    if "adjust-range" in normalized_ops:
                        mutable_fields.add("line-ranges")
                    if "split" in normalized_ops:
                        mutable_fields.update({"line-ranges", "source-fact"})
                    changed_fields = {
                        field
                        for field in PHASE2_ATOM_FIELDS
                        if current_atom.get(field) != base_row.get(field)
                    }
                    unauthorized = sorted(changed_fields - mutable_fields)
                    if unauthorized:
                        reporter.error(
                            "evidence-patch-target-field-scope",
                            path,
                            f"{target_key}修改了allowed operations之外的字段：{unauthorized}",
                        )
                    if defect == "quote-mismatch" and "source-fact" not in changed_fields:
                        reporter.error("evidence-patch-operation-not-applied", path, f"{target_key}未执行replace-quote")
                    if defect == "range-mismatch" and "line-ranges" not in changed_fields:
                        reporter.error("evidence-patch-operation-not-applied", path, f"{target_key}未执行adjust-range")
                if patch_applied and isinstance(window, dict):
                    allowed = {"start": window.get("start"), "end": window.get("end")}
                    current_ranges = valid_range_items(current_atom.get("line-ranges"))
                    if not current_ranges or any(not range_covered_by(item, [allowed]) for item in current_ranges):
                        reporter.error(
                            "evidence-patch-target-window",
                            path,
                            f"targeted-patch后的target atom超出allowed-line-window：{target_key}",
                        )
            if defect == "mixed-independent-occurrences":
                if "split" not in normalized_ops or not new_ids:
                    reporter.error("evidence-patch-split", path, "mixed-independent-occurrences要求split及新ID")
                expected_split = [f"{atom_id}.part-{part:02d}" for part in range(2, 2 + len(new_ids))]
                if [normalize_code(item) for item in new_ids] != expected_split:
                    reporter.error("evidence-patch-split-id", path, f"split新ID必须从{atom_id}.part-02连续追加")
            elif "split" in normalized_ops:
                reporter.error("evidence-patch-split-defect", path, "只有mixed-independent-occurrences允许split")
            elif new_ids:
                reporter.error("evidence-patch-unexpected-new-id", path, f"{target_key}非split不得新增ID")

        witness = target.get("defect-witness")
        witness_rows = _validate_defect_witness_shape(witness, path, reporter, target_key)
        if isinstance(witness, dict):
            current_source_sha = sha256_file(source_path) if source_path.exists() else ""
            if witness.get("source-sha256") != current_source_sha:
                reporter.error("evidence-patch-witness-source-sha", path, f"{target_key} witness source digest与冻结source不一致")
            if isinstance(window, dict):
                start, end = window.get("start"), window.get("end")
                if isinstance(start, int) and isinstance(end, int) and source_path.exists():
                    try:
                        expected_window_sha = source_window_sha256(source_path, start, end)
                    except ValueError:
                        expected_window_sha = ""
                    if witness.get("window-sha256") != expected_window_sha:
                        reporter.error("evidence-patch-witness-window-sha", path, f"{target_key} witness window digest不一致")

        origin_ranges: List[Dict[str, int]] = []
        own_origin = False
        for origin in witness_rows:
            kind = normalize_code(origin.get("row-kind"))
            row_key = normalize_code(origin.get("row-key"))
            origin_row: Dict[str, object] | None = None
            origin_source = ""
            expected_origin_path = ""
            if kind == "phase-2-atom":
                origin_source, separator, origin_atom_id = row_key.partition("::")
                if not separator or not origin_source or not origin_atom_id:
                    reporter.error("evidence-patch-witness-origin-row", path, f"{target_key} Phase 2 origin row-key非法：{row_key}")
                    continue
                expected_origin_path = rel(
                    atom_root / source_atom_file_name(origin_source).replace(".md", ".json"),
                    repo_root,
                )
                if origin_source == source and origin_atom_id == atom_id and isinstance(target.get("base-row"), dict):
                    origin_row = target.get("base-row")
                    own_origin = True
                elif not patch_applied:
                    origin_row = atom_rows.get(row_key)
            elif kind == "phase-3-disposition":
                expected_origin_path = rel(
                    orchestrate_dir / "phase-works/phase-3/coverage-review.json",
                    repo_root,
                )
                if not patch_applied:
                    origin_row = current_rows["phase-3-dispositions"].get(row_key)
                if isinstance(origin_row, dict):
                    origin_source = normalize_code(origin_row.get("source-document"))
                    if missing and normalize_code(origin_row.get("classification")) == "missing-obligation":
                        reporter.error(
                            "evidence-patch-witness-existing-gap",
                            path,
                            f"{target_key} missing occurrence不得以已存在gap的disposition作为locator origin",
                        )
            if origin.get("artifact-path") != expected_origin_path:
                reporter.error("evidence-patch-witness-origin-path", path, f"{target_key} origin artifact-path非法：{row_key}")
            if isinstance(origin_row, dict):
                if origin.get("row-sha256") != canonical_json_sha256(origin_row):
                    reporter.error("evidence-patch-witness-origin-drift", path, f"{target_key} origin row digest失效：{row_key}")
                if origin_source != source:
                    reporter.error("evidence-patch-witness-origin-source", path, f"{target_key} origin必须属于同一source：{row_key}")
                origin_ranges.extend(valid_range_items(origin_row.get("line-ranges")))
            elif not patch_applied:
                reporter.error("evidence-patch-witness-origin-missing", path, f"{target_key} locator origin不存在：{row_key}")

        if not missing and not own_origin:
            reporter.error("evidence-patch-witness-own-origin", path, f"{target_key} existing target必须以自身immutable base row作为locator origin")
        if not patch_applied and isinstance(window, dict):
            allowed_window = {"start": window.get("start"), "end": window.get("end")}
            if not origin_ranges or not range_covered_by(allowed_window, merge_line_ranges(origin_ranges)):
                reporter.error(
                    "evidence-patch-witness-origin-window",
                    path,
                    f"{target_key} allowed-line-window必须落在locator origin ranges的连续闭包内",
                )

    expected_add_ids = [f"patch-epr-0001-add-{index:02d}" for index in range(1, len(add_ids) + 1)]
    if add_ids != expected_add_ids:
        reporter.error("evidence-patch-add-id", path, "add新ID必须从patch-epr-0001-add-01全局连续追加")

    for target in targets:
        if not isinstance(target, dict):
            continue
        source = normalize_code(target.get("source-document"))
        window = target.get("allowed-line-window")
        if not isinstance(window, dict):
            continue
        for new_id in target.get("new-source-atom-ids", []) if isinstance(target.get("new-source-atom-ids"), list) else []:
            key = f"{source}::{normalize_code(new_id)}"
            new_row = atom_rows.get(key)
            if patch_applied and new_row is None:
                reporter.error("evidence-patch-new-atom-missing", path, f"targeted-patch缺少声明的新atom：{key}")
                continue
            if not patch_applied and new_row is not None:
                reporter.error("evidence-patch-new-atom-premature", path, f"请求初态不应已存在新atom：{key}")
            if new_row is not None:
                ranges = valid_range_items(new_row.get("line-ranges"))
                allowed = {"start": window.get("start"), "end": window.get("end")}
                if len(ranges) != 1 or not range_covered_by(ranges[0], [allowed]):
                    reporter.error("evidence-patch-new-atom-window", path, f"新atom超出allowed-line-window：{key}")
                defect = normalize_code(target.get("defect"))
                if defect == "mixed-independent-occurrences":
                    base_row = target.get("base-row") if isinstance(target.get("base-row"), dict) else {}
                    mapping_fields = {
                        "candidate-status",
                        "candidate-artifact-projection",
                        "candidate-owner-change",
                        "candidate-target-capability",
                    }
                    changed_mapping_fields = sorted(
                        field for field in mapping_fields if new_row.get(field) != base_row.get(field)
                    )
                    if changed_mapping_fields:
                        reporter.error(
                            "evidence-patch-split-candidate-mapping",
                            path,
                            f"split successor不得借evidence patch改变candidate mapping：{key}/{changed_mapping_fields}",
                        )
                elif defect == "missing-occurrence":
                    target_capability = normalize_code(new_row.get("candidate-target-capability"))
                    if (
                        normalize_code(new_row.get("candidate-status")) != "unassigned"
                        or normalize_code(new_row.get("candidate-owner-change")) != "unassigned"
                        or target_capability in phase1_framework_ids(orchestrate_dir)[1]
                    ):
                        reporter.error(
                            "evidence-patch-add-candidate-mapping",
                            path,
                            f"新增occurrence必须使用不预判framework的unassigned candidate mapping：{key}",
                        )

    current_base_atom_keys = set(atom_rows) - new_atom_keys
    if protected["phase-2-atoms"].intersection(target_atom_keys):
        reporter.error("evidence-patch-protection-overlap", path, "target Phase 2 atom不得同时列为protected")
    if protected["phase-2-atoms"] | target_atom_keys != current_base_atom_keys:
        reporter.error("evidence-patch-protection-coverage", path, "protected Phase 2 atoms与targets未恰好覆盖base atom identity")

    phase3_trace_path = orchestrate_dir / "trace/phase-3.trace.json"
    try:
        phase3_trace = read_json(phase3_trace_path) if phase3_trace_path.exists() else {}
    except Exception:  # noqa: BLE001
        phase3_trace = {}
    new_global_atom_ids = {
        normalize_code(item)
        for item in phase3_trace.get("new-global-atom-ids", [])
        if isinstance(item, str)
    } if normalize_code(phase3_trace.get("update-mode")) == "incremental-patch" else set()
    expected_protected_global = set(global_rows) - target_ga_ids - new_global_atom_ids
    if protected["global-atoms"] != expected_protected_global:
        reporter.error(
            "evidence-patch-global-protection-coverage",
            path,
            "protected global-atoms必须恰好覆盖全部base GA减target GA",
        )
    expected_protected_phase4_rows = set(current_rows["phase-4-index-rows"]) - target_ga_ids - new_global_atom_ids
    if protected["phase-4-index-rows"] != expected_protected_phase4_rows:
        reporter.error(
            "evidence-patch-phase4-row-protection-coverage",
            path,
            "protected phase-4-index-rows必须恰好覆盖全部base row减target/new GA",
        )
    expected_protected_documents = set(current_rows["phase-3-documents"]) - target_sources
    if protected["phase-3-documents"] != expected_protected_documents:
        reporter.error(
            "evidence-patch-document-protection-coverage",
            path,
            "protected Phase 3 documents必须恰好覆盖非target sources",
        )

    def intersects_target_window(source: str, ranges: List[Dict[str, int]]) -> bool:
        return any(
            item["start"] <= window["end"] and window["start"] <= item["end"]
            for item in ranges
            for window in target_windows.get(source, [])
        )

    expected_gap_keys = {
        key
        for key, row in current_rows["phase-3-gap-atoms"].items()
        if not intersects_target_window(
            normalize_code(row.get("source-document")),
            valid_range_items(row.get("line-ranges")),
        )
    }
    if protected["phase-3-gap-atoms"] != expected_gap_keys:
        reporter.error(
            "evidence-patch-gap-protection-coverage",
            path,
            "protected gap atoms必须恰好覆盖target window之外的rows",
        )
    expected_disposition_keys = {
        key
        for key, row in current_rows["phase-3-dispositions"].items()
        if not intersects_target_window(
            normalize_code(row.get("source-document")),
            valid_range_items(row.get("line-ranges")),
        )
    }
    if protected["phase-3-dispositions"] != expected_disposition_keys:
        reporter.error(
            "evidence-patch-disposition-protection-coverage",
            path,
            "protected dispositions必须恰好覆盖target window之外的rows",
        )

    expected_ambiguity_keys = (
        set(current_rows["phase-3-mapping-ambiguities"])
        - target_ga_ids
        - new_global_atom_ids
    )
    if protected["phase-3-mapping-ambiguities"] != expected_ambiguity_keys:
        reporter.error(
            "evidence-patch-ambiguity-protection-coverage",
            path,
            "protected mapping ambiguities必须恰好覆盖全部非target/new GA，不得因range重叠放开无关row",
        )

    rendered_rows = current_rows["phase-4-rendered-artifacts"]
    rendered_index_paths = {
        key
        for key, row in rendered_rows.items()
        if normalize_code(row.get("collection-kind")) == "index"
    }
    unassigned_paths = {
        key
        for key, row in rendered_rows.items()
        if normalize_code(row.get("collection-kind")) == "unassigned-and-gap"
    }
    affected_rendered_paths: Set[str] = set()
    has_new_occurrence = False
    for target in targets:
        if not isinstance(target, dict):
            continue
        ga_id = normalize_code(target.get("global-atom-id"))
        phase4_row = current_rows["phase-4-index-rows"].get(ga_id)
        if isinstance(phase4_row, dict):
            affected_rendered_paths.update(
                normalize_code(item)
                for item in phase4_row.get("rendered-collection-paths", [])
                if isinstance(item, str) and normalize_code(item)
            )
        new_ids = target.get("new-source-atom-ids")
        if isinstance(new_ids, list) and new_ids:
            has_new_occurrence = True
            if normalize_code(target.get("defect")) == "missing-occurrence":
                affected_rendered_paths.update(unassigned_paths)
    if has_new_occurrence:
        affected_rendered_paths.update(rendered_index_paths)
    expected_protected_rendered = set(rendered_rows) - affected_rendered_paths
    if protected["phase-4-rendered-artifacts"] != expected_protected_rendered:
        reporter.error(
            "evidence-patch-rendered-protection-coverage",
            path,
            "protected Phase 4 rendered artifacts必须恰好覆盖target old/new bucket之外的collection",
        )
    return data


def _validate_aborted_patch_request_snapshot(
    orchestrate_dir: Path,
    reporter: IssueReporter,
) -> Dict[str, object]:
    """Validate an immutable request after the incremental surfaces were abandoned."""
    path = _patch_request_path(orchestrate_dir)
    data = json_obj(path, reporter, EVIDENCE_PATCH_REQUEST_SCHEMA)
    if not data:
        return {}
    exact_fields(
        data,
        {"trace-schema", "trace-contract-version", "request-id", "base-artifacts", "targets", "protected-rows"},
        path,
        reporter,
        "evidence-patch-abort-fields",
        "aborted evidence patch request",
    )
    if data.get("request-id") != PATCH_REQUEST_ID:
        reporter.error("evidence-patch-request-id", path, f"单次patch request-id必须为{PATCH_REQUEST_ID}")
    base = data.get("base-artifacts")
    base_fields = {
        "phase-2-trace-sha256", "phase-3-trace-sha256", "global-atom-index-sha256",
        "coverage-review-sha256", "phase-4-index-sha256",
    }
    if not isinstance(base, dict):
        reporter.error("evidence-patch-base", path, "base-artifacts必须是object")
    else:
        exact_fields(base, base_fields, path, reporter, "evidence-patch-base-fields", "base-artifacts")
        for field in base_fields:
            if not _is_sha256(base.get(field)):
                reporter.error("evidence-patch-base-sha", path, f"base-artifacts.{field}必须是SHA-256")

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        reporter.error("evidence-patch-targets", path, "targets必须是非空array")
        targets = []
    target_fields = {
        "source-document", "source-atom-id", "global-atom-id", "evidence-ref", "defect",
        "allowed-operations", "allowed-line-window", "new-source-atom-ids", "base-row",
        "base-row-sha256", "canonical-owner", "reason", "defect-witness",
    }
    seen: Set[Tuple[str, str]] = set()
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            reporter.error("evidence-patch-target", path, f"targets[{index}]必须是object")
            continue
        exact_fields(target, target_fields, path, reporter, "evidence-patch-target-fields", f"targets[{index}]")
        _validate_defect_witness_shape(
            target.get("defect-witness"),
            path,
            reporter,
            f"targets[{index}]",
        )
        source = normalize_code(target.get("source-document"))
        atom_id = normalize_code(target.get("source-atom-id"))
        key = (source, atom_id or "<missing>")
        if not source or key in seen:
            reporter.error("evidence-patch-target-duplicate", path, f"target source为空或重复：{key}")
        seen.add(key)
        defect = normalize_code(target.get("defect"))
        if defect not in PATCH_DEFECTS:
            reporter.error("evidence-patch-defect", path, f"targets[{index}] defect非法：{defect}")
        operations = target.get("allowed-operations")
        normalized_ops = [normalize_code(item) for item in operations] if isinstance(operations, list) else []
        if (
            not normalized_ops
            or len(normalized_ops) != len(set(normalized_ops))
            or any(item not in PATCH_OPERATIONS for item in normalized_ops)
        ):
            reporter.error("evidence-patch-operations", path, f"targets[{index}] allowed-operations非法")
        window = target.get("allowed-line-window")
        if not isinstance(window, dict):
            reporter.error("evidence-patch-window", path, f"targets[{index}] allowed-line-window必须是object")
        else:
            exact_fields(window, {"start", "end"}, path, reporter, "evidence-patch-window-fields", f"targets[{index}]")
            if (
                not isinstance(window.get("start"), int)
                or not isinstance(window.get("end"), int)
                or window["start"] < 1
                or window["end"] < window["start"]
            ):
                reporter.error("evidence-patch-window", path, f"targets[{index}] allowed-line-window非法")
        new_ids = target.get("new-source-atom-ids")
        if not isinstance(new_ids, list) or len(new_ids) != len(set(new_ids)):
            reporter.error("evidence-patch-new-ids", path, f"targets[{index}] new-source-atom-ids必须是唯一array")
        base_row = target.get("base-row")
        base_sha = target.get("base-row-sha256")
        if defect == "missing-occurrence":
            if atom_id or target.get("global-atom-id") is not None or base_row is not None or base_sha is not None:
                reporter.error("evidence-patch-missing-identity", path, "missing-occurrence要求旧identity与base row为null")
        elif not isinstance(base_row, dict) or not _is_sha256(base_sha) or canonical_json_sha256(base_row) != base_sha:
            reporter.error("evidence-patch-base-row-sha", path, f"targets[{index}] immutable base-row或digest非法")
        if not squash(target.get("canonical-owner")) or not squash(target.get("reason")):
            reporter.error("evidence-patch-target-required", path, f"targets[{index}] canonical-owner/reason不得为空")

    _validate_protected_rows(
        data.get("protected-rows"),
        orchestrate_dir,
        path,
        reporter,
        "evidence-patch-abort-protected",
        verify_current_surfaces=False,
    )
    return data


CHECKPOINT_COMPLETED_ROW_FIELDS: Dict[str, Set[str]] = {
    "capability-reviews": {
        "input-capability", "evidence-collection-path", "decision", "final-capabilities",
        "initial-gate-results", "supporting-global-atom-ids", "reason",
    },
    "change-reviews": {
        "input-change", "evidence-collection-path", "decision", "final-changes",
        "initial-gate-results", "supporting-global-atom-ids", "reason",
    },
    "unassigned-and-gap-reviews": {
        "global-atom-id", "evidence-ref", "framework-impact", "reason",
    },
    "atom-plan-mappings": {
        "global-atom-id", "evidence-ref", "final-owner-change", "final-relation",
        "final-artifact-projection", "final-capability-impact", "final-target-capability",
        "related-capabilities", "reason",
    },
}
CHECKPOINT_ROW_KEY_FIELDS = {
    "capability-reviews": "input-capability",
    "change-reviews": "input-change",
    "unassigned-and-gap-reviews": "global-atom-id",
    "atom-plan-mappings": "global-atom-id",
}
CHECKPOINT_PENDING_FIELDS = {
    "capability-reviews",
    "change-reviews",
    "unassigned-and-gap-reviews",
    "atom-plan-mappings",
}


def _validate_checkpoint_initial_gate_results(
    value: object,
    expected_gates: Tuple[str, ...],
    path: Path,
    reporter: IssueReporter,
    context: str,
) -> bool:
    """校验checkpoint中冻结的initial gate全集；返回是否存在failed gate。"""
    if not isinstance(value, list):
        reporter.error(
            "phase5-checkpoint-initial-gates",
            path,
            f"{context}.initial-gate-results必须是array",
        )
        return False
    actual_gates: List[str] = []
    has_failed = False
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            reporter.error(
                "phase5-checkpoint-initial-gates",
                path,
                f"{context}.initial-gate-results[{index}]必须是object",
            )
            continue
        exact_fields(
            row,
            {"gate", "result", "note"},
            path,
            reporter,
            "phase5-checkpoint-initial-gate-fields",
            f"{context}.initial-gate-results[{index}]",
        )
        gate = normalize_code(row.get("gate"))
        result = normalize_code(row.get("result"))
        actual_gates.append(gate)
        if result not in {"passed", "failed"}:
            reporter.error(
                "phase5-checkpoint-initial-gate-result",
                path,
                f"{context}/{gate or index} result只允许passed|failed",
            )
        has_failed = has_failed or result == "failed"
        note = squash(row.get("note"))
        if not note or not re.search(r"[\u4e00-\u9fff]", note):
            reporter.error(
                "phase5-checkpoint-initial-gate-note",
                path,
                f"{context}/{gate or index} note必须使用简体中文解释",
            )
    if actual_gates != list(expected_gates):
        reporter.error(
            "phase5-checkpoint-initial-gate-coverage",
            path,
            f"{context}.initial-gate-results必须按共享原则固定顺序完整覆盖；"
            f"expected={list(expected_gates)} actual={actual_gates}",
        )
    return has_failed


def _validate_checkpoint_completed_review_semantics(
    completed_by_kind: Dict[str, Dict[str, Dict[str, object]]],
    path: Path,
    reporter: IssueReporter,
) -> None:
    review_specs = (
        (
            "capability-reviews", CAPABILITY_INITIAL_GATE_NAMES,
            CAPABILITY_REVIEW_DECISIONS, "final-capabilities", "Capability",
        ),
        (
            "change-reviews", CHANGE_INITIAL_GATE_NAMES,
            CHANGE_REVIEW_DECISIONS, "final-changes", "Change",
        ),
    )
    for kind, expected_gates, allowed_decisions, final_field, unit_label in review_specs:
        for key, row in completed_by_kind[kind].items():
            context = f"completed-rows.{kind}/{key}"
            has_failed = _validate_checkpoint_initial_gate_results(
                row.get("initial-gate-results"),
                expected_gates,
                path,
                reporter,
                context,
            )
            supporting = row.get("supporting-global-atom-ids")
            if (
                not isinstance(supporting, list)
                or any(
                    not isinstance(item, str)
                    or not GLOBAL_ATOM_ID_RE.fullmatch(normalize_code(item))
                    for item in supporting
                )
                or len(supporting) != len(set(supporting))
            ):
                reporter.error(
                    "phase5-checkpoint-supporting-ga",
                    path,
                    f"{context}.supporting-global-atom-ids必须是唯一合法GA array",
                )
                supporting_ids: List[str] = []
            else:
                supporting_ids = [normalize_code(item) for item in supporting]
            decision = normalize_code(row.get("decision"))
            if decision not in allowed_decisions:
                reporter.error(
                    "phase5-checkpoint-review-decision",
                    path,
                    f"{context}.decision非法：{decision}",
                )
            finals_raw = row.get(final_field)
            if (
                not isinstance(finals_raw, list)
                or any(
                    not isinstance(item, str)
                    or not KEBAB_CASE_RE.fullmatch(normalize_code(item))
                    for item in finals_raw
                )
                or len(finals_raw) != len(set(finals_raw))
            ):
                reporter.error(
                    "phase5-checkpoint-review-final-ids",
                    path,
                    f"{context}.{final_field}必须是唯一合法ID array",
                )
                finals: List[str] = []
            else:
                finals = [normalize_code(item) for item in finals_raw]
            if decision == "remove" and finals:
                reporter.error(
                    "phase5-checkpoint-review-final-ids",
                    path,
                    f"{context} remove要求{final_field}为空",
                )
            if unit_label == "Capability":
                identity_decisions = {"keep"}
            else:
                identity_decisions = {"keep", "reorder", "scope-adjusted"}
            if decision in identity_decisions and finals != [key]:
                reporter.error(
                    "phase5-checkpoint-review-final-ids",
                    path,
                    f"{context} {decision}要求{final_field}仅包含自身",
                )
            if decision == "rename" and (len(finals) != 1 or finals[0] == key):
                reporter.error(
                    "phase5-checkpoint-review-final-ids",
                    path,
                    f"{context} rename要求一个不同的final {unit_label}",
                )
            if decision == "split" and len(finals) < 2:
                reporter.error(
                    "phase5-checkpoint-review-final-ids",
                    path,
                    f"{context} split要求至少两个final {unit_label}",
                )
            if decision == "merge" and len(finals) != 1:
                reporter.error(
                    "phase5-checkpoint-review-final-ids",
                    path,
                    f"{context} merge要求恰好一个final {unit_label}",
                )
            if decision == "keep":
                if has_failed:
                    reporter.error(
                        "phase5-checkpoint-keep-failed-gate",
                        path,
                        f"{context} keep要求全部initial gate通过",
                    )
                if supporting_ids:
                    reporter.error(
                        "phase5-checkpoint-keep-supporting-ga",
                        path,
                        f"{context} keep要求supporting-global-atom-ids为空",
                    )
            elif not supporting_ids and not (decision in {"remove", "merge"} and has_failed):
                reporter.error(
                    "phase5-checkpoint-adjustment-supporting-ga",
                    path,
                    f"{context} 非keep decision必须引用source-backed supporting GA；"
                    "仅零GA collection的remove|merge且存在failed initial gate可为空",
                )
            reason = squash(row.get("reason"))
            if not reason or not re.search(r"[\u4e00-\u9fff]", reason):
                reporter.error(
                    "phase5-checkpoint-review-reason",
                    path,
                    f"{context}.reason必须使用简体中文解释",
                )

    for ga_id, row in completed_by_kind["unassigned-and-gap-reviews"].items():
        impact = normalize_code(row.get("framework-impact"))
        if impact not in {"none", "supports-adjustment"}:
            reporter.error(
                "phase5-checkpoint-gap-framework-impact",
                path,
                f"completed-rows.unassigned-and-gap-reviews/{ga_id} framework-impact只允许none|supports-adjustment",
            )
        reason = squash(row.get("reason"))
        if not reason or not re.search(r"[\u4e00-\u9fff]", reason):
            reporter.error(
                "phase5-checkpoint-gap-reason",
                path,
                f"completed-rows.unassigned-and-gap-reviews/{ga_id}.reason必须使用简体中文解释",
            )


def _validate_checkpoint_completed_mapping_semantics(
    completed_by_kind: Dict[str, Dict[str, Dict[str, object]]],
    provisional_changes: List[str],
    provisional_capabilities: List[str],
    path: Path,
    reporter: IssueReporter,
) -> None:
    """对checkpoint冻结的mapping v4子集执行完整tuple语义校验。"""
    change_ids = set(provisional_changes)
    capability_ids = set(provisional_capabilities)
    for ga_id, row in completed_by_kind["atom-plan-mappings"].items():
        context = f"completed-rows.atom-plan-mappings/{ga_id}"
        if not GLOBAL_ATOM_ID_RE.fullmatch(ga_id):
            reporter.error("phase5-checkpoint-mapping-ga", path, f"{context} GA非法")
        if not isinstance(row.get("evidence-ref"), dict):
            reporter.error(
                "phase5-checkpoint-mapping-evidence-ref",
                path,
                f"{context}.evidence-ref必须是object",
            )
        owner = normalize_code(row.get("final-owner-change"))
        relation = normalize_code(row.get("final-relation"))
        projection = normalize_code(row.get("final-artifact-projection"))
        impact = normalize_code(row.get("final-capability-impact"))
        target = normalize_code(row.get("final-target-capability"))
        if owner not in change_ids:
            reporter.error(
                "phase5-checkpoint-mapping-owner",
                path,
                f"{context} final owner Change不存在：{owner}",
            )
        if relation not in RELATIONS:
            reporter.error(
                "phase5-checkpoint-mapping-relation",
                path,
                f"{context} final relation非法：{relation}",
            )
        if impact not in CAPABILITY_IMPACTS:
            reporter.error(
                "phase5-checkpoint-mapping-impact",
                path,
                f"{context} Capability impact非法：{impact}",
            )
        related_raw = row.get("related-capabilities")
        if (
            not isinstance(related_raw, list)
            or any(
                not isinstance(item, str)
                or normalize_code(item) not in capability_ids
                for item in related_raw
            )
            or len(related_raw) != len(set(related_raw))
        ):
            reporter.error(
                "phase5-checkpoint-mapping-related",
                path,
                f"{context}.related-capabilities必须是唯一且引用provisional Capability的array",
            )
            related: List[str] = []
        else:
            related = [normalize_code(item) for item in related_raw]
        if target in related:
            reporter.error(
                "phase5-checkpoint-mapping-related",
                path,
                f"{context} related Capability不得等于target",
            )
        if relation == "direct":
            if projection not in DIRECT_PROJECTIONS:
                reporter.error(
                    "phase5-checkpoint-mapping-projection",
                    path,
                    f"{context} direct projection非法：{projection}",
                )
            elif projection in SPEC_PROJECTIONS:
                if impact not in {"new", "modified"} or target not in capability_ids:
                    reporter.error(
                        "phase5-checkpoint-mapping-tuple",
                        path,
                        f"{context} direct spec mapping缺少有效Capability impact/target",
                    )
            elif impact != "none" or target != "none":
                reporter.error(
                    "phase5-checkpoint-mapping-tuple",
                    path,
                    f"{context} design/verification mapping必须使用none/none",
                )
        elif relation in RELATIONS and (
            projection != "contextual-only" or impact != "none" or target != "none"
        ):
            reporter.error(
                "phase5-checkpoint-mapping-tuple",
                path,
                f"{context} non-direct mapping必须使用contextual-only和none/none",
            )
        reason = squash(row.get("reason"))
        if not reason or not re.search(r"[\u4e00-\u9fff]", reason):
            reporter.error(
                "phase5-checkpoint-mapping-reason",
                path,
                f"{context}.reason必须使用简体中文解释",
            )


def _validate_checkpoint_completed_review_links(
    orchestrate_dir: Path,
    completed_by_kind: Dict[str, Dict[str, Dict[str, object]]],
    collection_by_ga: Dict[str, Dict[str, object]],
    provisional_changes: List[str],
    provisional_capabilities: List[str],
    provisional_overlay: Set[Tuple[str, str]],
    initial_changes: Set[str],
    initial_capabilities: Set[str],
    global_positions: Dict[str, int],
    path: Path,
    reporter: IssueReporter,
) -> None:
    """用仍可读取的Phase 4 initial collection校验checkpoint review provenance。"""
    review_specs = (
        ("capability-reviews", "capability-bucket"),
        ("change-reviews", "change-bucket"),
    )
    adjustment_supporting_ga: Set[str] = set()
    for kind, bucket_field in review_specs:
        for key, row in completed_by_kind[kind].items():
            collection_ga = {
                ga_id
                for ga_id, collection_row in collection_by_ga.items()
                if normalize_code(collection_row.get(bucket_field)) == key
            }
            supporting_ids = [
                normalize_code(item)
                for item in row.get("supporting-global-atom-ids", [])
                if isinstance(item, str)
            ]
            supporting = set(supporting_ids)
            if all(item in global_positions for item in supporting_ids):
                positions = [global_positions[item] for item in supporting_ids]
                if positions != sorted(positions):
                    reporter.error(
                        "phase5-checkpoint-supporting-ga-order",
                        path,
                        f"completed-rows.{kind}/{key} supporting GA必须按obligation-atom-index.json的实际顺序排列",
                    )
            outside = sorted(supporting - collection_ga)
            if outside:
                reporter.error(
                    "phase5-checkpoint-supporting-ga-collection",
                    path,
                    f"completed-rows.{kind}/{key} supporting GA不属于对应Phase 4 collection：{outside}",
                )
            decision = normalize_code(row.get("decision"))
            gates = row.get("initial-gate-results")
            has_failed = any(
                isinstance(gate, dict) and normalize_code(gate.get("result")) == "failed"
                for gate in (gates if isinstance(gates, list) else [])
            )
            if decision != "keep":
                adjustment_supporting_ga.update(supporting)
                if (
                    not supporting
                    and not (
                        decision in {"remove", "merge"}
                        and has_failed
                        and not collection_ga
                    )
                ):
                    reporter.error(
                        "phase5-checkpoint-adjustment-supporting-ga",
                        path,
                        f"completed-rows.{kind}/{key}缺少对应collection中的supporting GA；"
                        "空引用仅允许零GA collection的remove|merge且initial gate存在failed",
                    )

    completed_mapping = completed_by_kind["atom-plan-mappings"]
    for ga_id, mapping_row in completed_mapping.items():
        collection_row = collection_by_ga.get(ga_id)
        if collection_row is None or mapping_row.get("evidence-ref") != collection_row.get("evidence-ref"):
            reporter.error(
                "phase5-checkpoint-mapping-evidence-ref",
                path,
                f"completed atom mapping/{ga_id} evidence-ref必须与Phase 4 collection index一致",
            )
    new_change_ids = set(provisional_changes) - initial_changes
    new_capability_ids = set(provisional_capabilities) - initial_capabilities
    new_advancement_edges = provisional_overlay - _phase1_overlay(orchestrate_dir)
    for ga_id, row in completed_by_kind["unassigned-and-gap-reviews"].items():
        collection_row = collection_by_ga.get(ga_id)
        if collection_row is not None and row.get("evidence-ref") != collection_row.get("evidence-ref"):
            reporter.error(
                "phase5-checkpoint-gap-evidence-ref",
                path,
                f"completed unassigned/gap review/{ga_id} evidence-ref与Phase 4 index不一致",
            )
        if normalize_code(row.get("framework-impact")) != "supports-adjustment":
            continue
        mapping_row = completed_mapping.get(ga_id, {})
        owner = normalize_code(mapping_row.get("final-owner-change"))
        target = normalize_code(mapping_row.get("final-target-capability"))
        projection = normalize_code(mapping_row.get("final-artifact-projection"))
        relation = normalize_code(mapping_row.get("final-relation"))
        linked_to_new_id = owner in new_change_ids or target in new_capability_ids
        linked_to_new_edge = (
            relation == "direct"
            and projection in SPEC_PROJECTIONS
            and (owner, target) in new_advancement_edges
        )
        if ga_id not in adjustment_supporting_ga and not linked_to_new_id and not linked_to_new_edge:
            reporter.error(
                "phase5-checkpoint-gap-framework-impact-link",
                path,
                f"{ga_id} supports-adjustment必须关联非keep review supporting GA、"
                "新增final ID或Phase 1不存在的advancement edge",
            )


def _validate_identifier_array(
    value: object,
    path: Path,
    reporter: IssueReporter,
    rule: str,
    context: str,
    *,
    global_atoms: bool = False,
) -> List[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not normalize_code(item) for item in value)
        or len(value) != len(set(value))
    ):
        reporter.error(rule, path, f"{context}必须是元素非空且不重复的string array（array本身可为空）")
        return []
    result = [normalize_code(item) for item in value]
    pattern = GLOBAL_ATOM_ID_RE if global_atoms else KEBAB_CASE_RE
    for item in result:
        if not pattern.fullmatch(item):
            reporter.error(rule, path, f"{context}包含非法ID：{item}")
    return result


def _scope_covers_full_typed_framework(
    initial_ids: Set[str],
    provisional_ids: Set[str],
    scoped_initial_ids: Set[str],
    scoped_final_ids: Set[str],
) -> bool:
    """任一initial或current-final typed universe全覆盖都视为full refit。"""
    union_ids = initial_ids | provisional_ids
    mutable_union = scoped_initial_ids | scoped_final_ids
    return (
        (bool(initial_ids) and initial_ids.issubset(scoped_initial_ids))
        or (bool(provisional_ids) and provisional_ids.issubset(scoped_final_ids))
        or (bool(union_ids) and union_ids.issubset(mutable_union))
    )


def _validate_checkpoint(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
    *,
    verify_current_surfaces: bool = True,
) -> Dict[str, object]:
    path = _checkpoint_path(orchestrate_dir)
    data = json_obj(path, reporter, PHASE5_CHECKPOINT_SCHEMA)
    if not data:
        return {}
    exact_fields(
        data,
        {
            "trace-schema", "trace-contract-version", "checkpoint-id", "stage", "patch-request-ref",
            "input-fingerprints", "provisional-framework", "completed-rows", "pending-ids",
            "allowed-update-scope", "preserved-row-digests", "patch-attempt",
        },
        path,
        reporter,
        "phase5-checkpoint-fields",
        "Phase 5 checkpoint",
    )
    if data.get("checkpoint-id") != CHECKPOINT_ID:
        reporter.error("phase5-checkpoint-id", path, f"checkpoint-id必须为{CHECKPOINT_ID}")
    if normalize_code(data.get("stage")) != "mapping":
        reporter.error(
            "phase5-checkpoint-stage",
            path,
            "evidence patch checkpoint必须固定在mapping stage；全局refit审查完成后只可重开局部影响闭包",
        )

    request_path = _patch_request_path(orchestrate_dir)
    _validate_artifact_ref(
        data.get("patch-request-ref"),
        request_path,
        path,
        repo_root,
        reporter,
        "phase5-checkpoint-request-ref",
    )

    fingerprints = data.get("input-fingerprints")
    fingerprint_map: Dict[str, str] = {}
    forbidden_fingerprint_prefixes = (
        rel(orchestrate_dir / "phase-works/phase-2", repo_root) + "/",
        rel(orchestrate_dir / "phase-works/phase-3", repo_root) + "/",
        rel(orchestrate_dir / "phase-works/phase-4", repo_root) + "/",
    )
    forbidden_fingerprint_paths = {
        rel(orchestrate_dir / "trace/phase-2.trace.json", repo_root),
        rel(orchestrate_dir / "trace/phase-3.trace.json", repo_root),
        rel(orchestrate_dir / "trace/phase-4.trace.json", repo_root),
        rel(orchestrate_dir / "change-capability-anchors/obligation-atom-index.json", repo_root),
        rel(orchestrate_dir / "change-capability-anchors/obligation-atom-index.md", repo_root),
    }
    if not isinstance(fingerprints, list) or not fingerprints:
        reporter.error("phase5-checkpoint-input-fingerprints", path, "input-fingerprints必须是非空array")
        fingerprints = []
    for index, row in enumerate(fingerprints):
        if not isinstance(row, dict):
            reporter.error("phase5-checkpoint-input-fingerprint", path, f"input-fingerprints[{index}]必须是object")
            continue
        exact_fields(
            row,
            {"artifact-path", "sha256"},
            path,
            reporter,
            "phase5-checkpoint-input-fingerprint-fields",
            f"input-fingerprints[{index}]",
        )
        artifact_rel = normalize_code(row.get("artifact-path"))
        digest = normalize_code(row.get("sha256"))
        if not artifact_rel or artifact_rel in fingerprint_map:
            reporter.error("phase5-checkpoint-input-fingerprint-path", path, f"fingerprint path为空或重复：{artifact_rel}")
            continue
        fingerprint_map[artifact_rel] = digest
        if artifact_rel in forbidden_fingerprint_paths or artifact_rel.startswith(forbidden_fingerprint_prefixes):
            reporter.error(
                "phase5-checkpoint-patchable-fingerprint",
                path,
                f"input-fingerprints不得锁定targeted patch期间应变化的Phase 2–4 artifact：{artifact_rel}",
            )
        if not _is_sha256(digest):
            reporter.error("phase5-checkpoint-input-fingerprint-sha", path, f"{artifact_rel} sha256非法")
            continue
        if verify_current_surfaces:
            artifact_path = repo_root / artifact_rel
            if not artifact_path.exists():
                reporter.error("phase5-checkpoint-input-missing", path, f"checkpoint input不存在：{artifact_rel}")
            elif sha256_file(artifact_path) != digest:
                reporter.error("phase5-checkpoint-input-drift", path, f"checkpoint input fingerprint失效：{artifact_rel}")
    required_fingerprints = {
        rel(orchestrate_dir / "phase-works/phase-1/initial-change-plan.md", repo_root),
        ".codex/skills/source-aligned-change-plan-coverage/references/change-capability-framework-principles.md",
    }
    missing_required_fingerprints = sorted(required_fingerprints - set(fingerprint_map))
    if missing_required_fingerprints:
        reporter.error(
            "phase5-checkpoint-required-fingerprint-missing",
            path,
            f"input-fingerprints缺少稳定authority：{missing_required_fingerprints}",
        )

    framework = data.get("provisional-framework")
    if not isinstance(framework, dict):
        reporter.error("phase5-checkpoint-framework", path, "provisional-framework必须是object")
        framework = {}
    else:
        exact_fields(
            framework,
            {
                "change-order", "capabilities", "overlay",
                "change-semantic-digests", "capability-semantic-digests",
                "dependency-edges", "change-lineage", "capability-lineage", "ga-lineage",
            },
            path,
            reporter,
            "phase5-checkpoint-framework-fields",
            "provisional-framework",
        )
    provisional_changes = _validate_identifier_array(
        framework.get("change-order"), path, reporter, "phase5-checkpoint-framework-change-order", "change-order",
    )
    provisional_capabilities = _validate_identifier_array(
        framework.get("capabilities"), path, reporter, "phase5-checkpoint-framework-capabilities", "capabilities",
    )
    overlay = framework.get("overlay")
    overlay_pairs: Set[Tuple[str, str]] = set()
    if not isinstance(overlay, list):
        reporter.error("phase5-checkpoint-framework-overlay", path, "provisional-framework.overlay必须是array")
        overlay = []
    for index, row in enumerate(overlay):
        if not isinstance(row, dict):
            reporter.error("phase5-checkpoint-framework-overlay-row", path, f"overlay[{index}]必须是object")
            continue
        exact_fields(
            row,
            {"change", "capability", "capability-impact"},
            path,
            reporter,
            "phase5-checkpoint-framework-overlay-fields",
            f"overlay[{index}]",
        )
        pair = (normalize_code(row.get("change")), normalize_code(row.get("capability")))
        impact = normalize_code(row.get("capability-impact"))
        if (
            pair in overlay_pairs
            or pair[0] not in provisional_changes
            or pair[1] not in provisional_capabilities
            or impact not in {"new", "modified"}
        ):
            reporter.error("phase5-checkpoint-framework-overlay-row", path, f"overlay[{index}]引用或impact非法")
        overlay_pairs.add(pair)

    semantic_digest_specs = (
        (
            "change-semantic-digests",
            "final-change",
            provisional_changes,
            "phase5-checkpoint-change-semantic-digests",
        ),
        (
            "capability-semantic-digests",
            "final-capability",
            provisional_capabilities,
            "phase5-checkpoint-capability-semantic-digests",
        ),
    )
    for field, key_field, expected_ids, rule in semantic_digest_specs:
        rows = framework.get(field)
        if not isinstance(rows, list):
            reporter.error(rule, path, f"provisional-framework.{field}必须是array")
            continue
        actual_ids: List[str] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                reporter.error(rule, path, f"{field}[{index}]必须是object")
                continue
            exact_fields(
                row,
                {key_field, "sha256"},
                path,
                reporter,
                f"{rule}-fields",
                f"{field}[{index}]",
            )
            row_id = normalize_code(row.get(key_field))
            actual_ids.append(row_id)
            if not _is_sha256(row.get("sha256")):
                reporter.error(rule, path, f"{field}[{index}].sha256必须是SHA-256")
        if actual_ids != expected_ids or len(actual_ids) != len(set(actual_ids)):
            reporter.error(
                rule,
                path,
                f"{field}必须按provisional framework顺序恰好覆盖全部ID",
            )

    dependency_edges = framework.get("dependency-edges")
    if not isinstance(dependency_edges, list):
        reporter.error(
            "phase5-checkpoint-dependency-edges",
            path,
            "provisional-framework.dependency-edges必须是array",
        )
        dependency_edges = []
    change_positions = {change_id: index for index, change_id in enumerate(provisional_changes)}
    normalized_dependency_edges: List[Dict[str, str]] = []
    seen_dependency_edges: Set[Tuple[str, str]] = set()
    for index, row in enumerate(dependency_edges):
        if not isinstance(row, dict):
            reporter.error("phase5-checkpoint-dependency-edges", path, f"dependency-edges[{index}]必须是object")
            continue
        exact_fields(
            row,
            {"change", "depends-on"},
            path,
            reporter,
            "phase5-checkpoint-dependency-edge-fields",
            f"dependency-edges[{index}]",
        )
        change_id = normalize_code(row.get("change"))
        dependency_id = normalize_code(row.get("depends-on"))
        pair = (change_id, dependency_id)
        if (
            pair in seen_dependency_edges
            or change_id not in change_positions
            or dependency_id not in change_positions
            or change_positions[dependency_id] >= change_positions[change_id]
        ):
            reporter.error(
                "phase5-checkpoint-dependency-edges",
                path,
                f"dependency-edges[{index}]引用、顺序或唯一性非法：{pair}",
            )
        seen_dependency_edges.add(pair)
        normalized_dependency_edges.append({"change": change_id, "depends-on": dependency_id})
    expected_dependency_order = sorted(
        normalized_dependency_edges,
        key=lambda row: (
            change_positions.get(row["change"], len(change_positions)),
            change_positions.get(row["depends-on"], len(change_positions)),
        ),
    )
    if normalized_dependency_edges != expected_dependency_order:
        reporter.error(
            "phase5-checkpoint-dependency-edge-order",
            path,
            "dependency-edges必须按provisional Change顺序确定性排列",
        )

    initial_plan_path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    if verify_current_surfaces:
        expected_initial_change_order = _phase1_change_order(orchestrate_dir)
        expected_initial_capability_order = [
            normalize_code(cell(row, "Candidate Capability"))
            for row in table_rows(
                initial_plan_path,
                ["Candidate Capability", "Purpose", "Owns", "Excludes", "Boundary Rationale"],
            )
            if normalize_code(cell(row, "Candidate Capability"))
        ]
    else:
        expected_initial_change_order = [
            normalize_code(row.get("input-change"))
            for row in framework.get("change-lineage", [])
            if isinstance(row, dict)
        ]
        expected_initial_capability_order = [
            normalize_code(row.get("input-capability"))
            for row in framework.get("capability-lineage", [])
            if isinstance(row, dict)
        ]
    lineage_specs = (
        (
            "change-lineage", "input-change", "provisional-final-changes",
            expected_initial_change_order, set(provisional_changes),
            "phase5-checkpoint-change-lineage",
        ),
        (
            "capability-lineage", "input-capability", "provisional-final-capabilities",
            expected_initial_capability_order, set(provisional_capabilities),
            "phase5-checkpoint-capability-lineage",
        ),
    )
    lineage_by_field: Dict[str, Dict[str, Dict[str, object]]] = {}
    for field, input_field, output_field, expected_inputs, valid_outputs, rule in lineage_specs:
        rows = framework.get(field)
        indexed: Dict[str, Dict[str, object]] = {}
        actual_inputs: List[str] = []
        if not isinstance(rows, list):
            reporter.error(rule, path, f"provisional-framework.{field}必须是array")
            rows = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                reporter.error(rule, path, f"{field}[{index}]必须是object")
                continue
            exact_fields(
                row,
                {input_field, output_field},
                path,
                reporter,
                f"{rule}-fields",
                f"{field}[{index}]",
            )
            input_id = normalize_code(row.get(input_field))
            output_ids = row.get(output_field)
            actual_inputs.append(input_id)
            if (
                not isinstance(output_ids, list)
                or any(not isinstance(item, str) or normalize_code(item) not in valid_outputs for item in output_ids)
                or len(output_ids) != len(set(output_ids))
            ):
                reporter.error(rule, path, f"{field}[{index}].{output_field}必须是唯一且引用provisional ID的array")
            if input_id in indexed:
                reporter.error(rule, path, f"{field} input重复：{input_id}")
            indexed[input_id] = row
        if actual_inputs != expected_inputs:
            reporter.error(rule, path, f"{field}必须按Phase 1顺序恰好覆盖全部initial ID")
        lineage_by_field[field] = indexed

    ga_lineage_rows = framework.get("ga-lineage")
    ga_lineage_by_id: Dict[str, Dict[str, object]] = {}
    ga_lineage_order: List[str] = []
    if not isinstance(ga_lineage_rows, list):
        reporter.error("phase5-checkpoint-ga-lineage", path, "provisional-framework.ga-lineage必须是array")
        ga_lineage_rows = []
    for index, row in enumerate(ga_lineage_rows):
        if not isinstance(row, dict):
            reporter.error("phase5-checkpoint-ga-lineage", path, f"ga-lineage[{index}]必须是object")
            continue
        exact_fields(
            row,
            {
                "global-atom-id", "provisional-final-change",
                "provisional-final-capability", "provisional-related-capabilities",
            },
            path,
            reporter,
            "phase5-checkpoint-ga-lineage-fields",
            f"ga-lineage[{index}]",
        )
        ga_id = normalize_code(row.get("global-atom-id"))
        change_id = normalize_code(row.get("provisional-final-change"))
        capability_id = normalize_code(row.get("provisional-final-capability"))
        related = row.get("provisional-related-capabilities")
        ga_lineage_order.append(ga_id)
        if not GLOBAL_ATOM_ID_RE.fullmatch(ga_id) or ga_id in ga_lineage_by_id:
            reporter.error("phase5-checkpoint-ga-lineage", path, f"ga-lineage GA非法或重复：{ga_id}")
        if change_id not in set(provisional_changes):
            reporter.error("phase5-checkpoint-ga-lineage", path, f"{ga_id} provisional final Change非法：{change_id}")
        if capability_id not in {"none", *set(provisional_capabilities)}:
            reporter.error("phase5-checkpoint-ga-lineage", path, f"{ga_id} provisional final Capability非法：{capability_id}")
        if (
            not isinstance(related, list)
            or any(not isinstance(item, str) or normalize_code(item) not in set(provisional_capabilities) for item in related)
            or len(related) != len(set(related))
        ):
            reporter.error("phase5-checkpoint-ga-lineage", path, f"{ga_id} related Capability lineage非法")
        ga_lineage_by_id[ga_id] = row
    if ga_lineage_order != sorted(ga_lineage_order):
        reporter.error("phase5-checkpoint-ga-lineage-order", path, "ga-lineage必须按GA单调顺序排列")

    completed = data.get("completed-rows")
    completed_by_kind: Dict[str, Dict[str, Dict[str, object]]] = {
        kind: {} for kind in CHECKPOINT_COMPLETED_ROW_FIELDS
    }
    if not isinstance(completed, dict):
        reporter.error("phase5-checkpoint-completed", path, "completed-rows必须是object")
        completed = {}
    else:
        exact_fields(
            completed,
            set(CHECKPOINT_COMPLETED_ROW_FIELDS),
            path,
            reporter,
            "phase5-checkpoint-completed-fields",
            "completed-rows",
        )
    for kind, fields in CHECKPOINT_COMPLETED_ROW_FIELDS.items():
        rows = completed.get(kind)
        if not isinstance(rows, list):
            reporter.error("phase5-checkpoint-completed-rows", path, f"completed-rows.{kind}必须是array")
            continue
        key_field = CHECKPOINT_ROW_KEY_FIELDS[kind]
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                reporter.error("phase5-checkpoint-completed-row", path, f"{kind}[{index}]必须是object")
                continue
            exact_fields(
                row,
                fields,
                path,
                reporter,
                "phase5-checkpoint-completed-row-fields",
                f"{kind}[{index}]",
            )
            key = normalize_code(row.get(key_field))
            if not key or key in completed_by_kind[kind]:
                reporter.error("phase5-checkpoint-completed-row-key", path, f"{kind} row key为空或重复：{key}")
                continue
            completed_by_kind[kind][key] = row

    _validate_checkpoint_completed_review_semantics(completed_by_kind, path, reporter)
    _validate_checkpoint_completed_mapping_semantics(
        completed_by_kind,
        provisional_changes,
        provisional_capabilities,
        path,
        reporter,
    )

    completed_lineage_specs = (
        (
            "change-reviews", "change-lineage", "input-change",
            "final-changes", "provisional-final-changes",
            "phase5-checkpoint-change-lineage-drift",
        ),
        (
            "capability-reviews", "capability-lineage", "input-capability",
            "final-capabilities", "provisional-final-capabilities",
            "phase5-checkpoint-capability-lineage-drift",
        ),
    )
    for review_kind, lineage_field, input_field, review_final_field, lineage_final_field, rule in completed_lineage_specs:
        lineage_rows = lineage_by_field.get(lineage_field, {})
        for origin, review_row in completed_by_kind[review_kind].items():
            lineage_row = lineage_rows.get(origin)
            if (
                lineage_row is None
                or review_row.get(review_final_field) != lineage_row.get(lineage_final_field)
                or normalize_code(lineage_row.get(input_field)) != origin
            ):
                reporter.error(
                    rule,
                    path,
                    f"completed {review_kind}/{origin}与provisional lineage不一致",
                )
    for ga_id, mapping_row in completed_by_kind["atom-plan-mappings"].items():
        lineage_row = ga_lineage_by_id.get(ga_id)
        expected_lineage = {
            "global-atom-id": ga_id,
            "provisional-final-change": normalize_code(mapping_row.get("final-owner-change")),
            "provisional-final-capability": normalize_code(mapping_row.get("final-target-capability")),
            "provisional-related-capabilities": list(mapping_row.get("related-capabilities", [])),
        }
        if lineage_row != expected_lineage:
            reporter.error(
                "phase5-checkpoint-ga-lineage-drift",
                path,
                f"completed atom mapping/{ga_id}与provisional GA lineage不一致",
            )

    pending = data.get("pending-ids")
    if not isinstance(pending, dict):
        reporter.error("phase5-checkpoint-pending", path, "pending-ids必须是object")
        pending = {}
    else:
        exact_fields(
            pending,
            CHECKPOINT_PENDING_FIELDS,
            path,
            reporter,
            "phase5-checkpoint-pending-fields",
            "pending-ids",
        )
    pending_capabilities = _validate_identifier_array(
        pending.get("capability-reviews"), path, reporter, "phase5-checkpoint-pending-capabilities", "pending capability reviews",
    )
    pending_changes = _validate_identifier_array(
        pending.get("change-reviews"), path, reporter, "phase5-checkpoint-pending-changes", "pending change reviews",
    )
    pending_unassigned = _validate_identifier_array(
        pending.get("unassigned-and-gap-reviews"),
        path,
        reporter,
        "phase5-checkpoint-pending-unassigned",
        "pending unassigned/gap reviews",
        global_atoms=True,
    )
    pending_mappings = _validate_identifier_array(
        pending.get("atom-plan-mappings"), path, reporter, "phase5-checkpoint-pending-mappings", "pending atom mappings",
        global_atoms=True,
    )
    if set(pending_capabilities).intersection(completed_by_kind["capability-reviews"]):
        reporter.error("phase5-checkpoint-pending-completed-overlap", path, "pending capability不得已有completed review")
    if set(pending_changes).intersection(completed_by_kind["change-reviews"]):
        reporter.error("phase5-checkpoint-pending-completed-overlap", path, "pending change不得已有completed review")
    if set(pending_unassigned).intersection(completed_by_kind["unassigned-and-gap-reviews"]):
        reporter.error("phase5-checkpoint-pending-completed-overlap", path, "pending unassigned/gap review不得已有同类completed row")
    if set(pending_mappings).intersection(completed_by_kind["atom-plan-mappings"]):
        reporter.error("phase5-checkpoint-pending-completed-overlap", path, "pending atom mapping不得已有completed mapping row")

    if verify_current_surfaces:
        initial_changes, initial_capabilities = phase1_framework_ids(orchestrate_dir)
    else:
        initial_changes = set(expected_initial_change_order)
        initial_capabilities = set(expected_initial_capability_order)
    if set(completed_by_kind["capability-reviews"]) | set(pending_capabilities) != initial_capabilities:
        reporter.error("phase5-checkpoint-capability-partition", path, "completed与pending capability reviews必须恰好划分全部initial Capability")
    if set(completed_by_kind["change-reviews"]) | set(pending_changes) != initial_changes:
        reporter.error("phase5-checkpoint-change-partition", path, "completed与pending change reviews必须恰好划分全部initial Change")

    try:
        request = read_json(request_path) if request_path.exists() else {}
    except Exception:  # noqa: BLE001
        request = {}
    request_targets = request.get("targets") if isinstance(request.get("targets"), list) else []
    target_ga_ids = {
        normalize_code(target.get("global-atom-id"))
        for target in request_targets
        if isinstance(target, dict) and target.get("global-atom-id") is not None
    }
    protected_global = (
        request.get("protected-rows", {}).get("global-atoms", [])
        if isinstance(request.get("protected-rows"), dict)
        else []
    )
    base_ga_ids = {
        normalize_code(row.get("global-atom-id"))
        for row in protected_global
        if isinstance(row, dict) and normalize_code(row.get("global-atom-id"))
    } | target_ga_ids
    if set(ga_lineage_by_id) != base_ga_ids:
        reporter.error(
            "phase5-checkpoint-ga-lineage-coverage",
            path,
            "ga-lineage必须恰好覆盖patch前全部existing GA，不包含预分配new GA",
        )
    max_base_ga = max(
        (int(item.split("-")[1]) for item in base_ga_ids if GLOBAL_ATOM_ID_RE.fullmatch(item)),
        default=0,
    )
    anticipated_new_rows: List[Tuple[str, Dict[str, object]]] = []
    next_ga_number = max_base_ga + 1
    for target in request_targets:
        if not isinstance(target, dict):
            continue
        new_ids = target.get("new-source-atom-ids")
        for _new_id in new_ids if isinstance(new_ids, list) else []:
            anticipated_new_rows.append((f"GA-{next_ga_number:04d}", target))
            next_ga_number += 1
    anticipated_new_ga_ids = {ga_id for ga_id, _target in anticipated_new_rows}
    expected_unassigned_ga = (
        set(completed_by_kind["unassigned-and-gap-reviews"])
        | set(pending_unassigned)
    )

    collection_by_ga: Dict[str, Dict[str, object]] = {}
    if verify_current_surfaces:
        global_index_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
        try:
            global_index = read_json(global_index_path) if global_index_path.exists() else {}
        except Exception:  # noqa: BLE001
            global_index = {}
        global_rows = global_index.get("global-atoms") if isinstance(global_index.get("global-atoms"), list) else []
        global_order = [
            normalize_code(row.get("global-atom-id"))
            for row in global_rows
            if isinstance(row, dict)
        ]
        if (
            len(global_order) != len(global_rows)
            or len(global_order) != len(set(global_order))
            or any(not GLOBAL_ATOM_ID_RE.fullmatch(ga_id) for ga_id in global_order)
        ):
            reporter.error(
                "phase5-checkpoint-global-index-order",
                global_index_path,
                "无法从obligation-atom-index.json建立唯一实际GA顺序",
            )
        global_positions = {ga_id: index for index, ga_id in enumerate(global_order)}
        collection_path = orchestrate_dir / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
        try:
            collection = read_json(collection_path) if collection_path.exists() else {}
        except Exception:  # noqa: BLE001
            collection = {}
        collection_rows = collection.get("rows") if isinstance(collection.get("rows"), list) else []
        all_collection_ga = {
            normalize_code(row.get("global-atom-id"))
            for row in collection_rows
            if isinstance(row, dict) and normalize_code(row.get("global-atom-id"))
        }
        unassigned_ga = {
            normalize_code(row.get("global-atom-id"))
            for row in collection_rows
            if isinstance(row, dict) and normalize_code(row.get("change-bucket")) == "unassigned-and-gap"
        }
        collection_by_ga = {
            normalize_code(row.get("global-atom-id")): row
            for row in collection_rows
            if isinstance(row, dict) and normalize_code(row.get("global-atom-id"))
        }
        anticipated_unassigned_ga = {
            ga_id
            for ga_id, target in anticipated_new_rows
            if normalize_code(target.get("defect")) == "missing-occurrence"
            or normalize_code(
                collection_by_ga.get(normalize_code(target.get("global-atom-id")), {}).get("change-bucket")
            ) == "unassigned-and-gap"
        }
        expected_unassigned_ga = unassigned_ga | anticipated_unassigned_ga
        expected_mapping_ga = all_collection_ga | anticipated_new_ga_ids
        if set(completed_by_kind["unassigned-and-gap-reviews"]) | set(pending_unassigned) != expected_unassigned_ga:
            reporter.error("phase5-checkpoint-unassigned-partition", path, "completed与pending unassigned/gap reviews必须恰好划分Phase 4 unassigned GA")
        if set(completed_by_kind["atom-plan-mappings"]) | set(pending_mappings) != expected_mapping_ga:
            reporter.error("phase5-checkpoint-mapping-partition", path, "completed与pending atom mappings必须恰好划分全部GA")
        _validate_checkpoint_completed_review_links(
            orchestrate_dir,
            completed_by_kind,
            collection_by_ga,
            provisional_changes,
            provisional_capabilities,
            overlay_pairs,
            initial_changes,
            initial_capabilities,
            global_positions,
            path,
            reporter,
        )

    scope = data.get("allowed-update-scope")
    if not isinstance(scope, dict):
        reporter.error("phase5-checkpoint-scope", path, "allowed-update-scope必须是object")
        scope = {}
    else:
        exact_fields(
            scope,
            {
                "global-atom-ids", "initial-changes", "initial-capabilities", "final-changes",
                "final-capabilities", "allow-roadmap-reorder",
            },
            path,
            reporter,
            "phase5-checkpoint-scope-fields",
            "allowed-update-scope",
        )
    scope_ga = _validate_identifier_array(
        scope.get("global-atom-ids"), path, reporter, "phase5-checkpoint-scope-ga", "scope global-atom-ids",
        global_atoms=True,
    )
    scope_initial_changes = _validate_identifier_array(
        scope.get("initial-changes"), path, reporter, "phase5-checkpoint-scope-initial-changes", "scope initial-changes",
    )
    scope_initial_capabilities = _validate_identifier_array(
        scope.get("initial-capabilities"), path, reporter, "phase5-checkpoint-scope-initial-capabilities", "scope initial-capabilities",
    )
    scope_final_changes = _validate_identifier_array(
        scope.get("final-changes"), path, reporter, "phase5-checkpoint-scope-final-changes", "scope final-changes",
    )
    scope_final_capabilities = _validate_identifier_array(
        scope.get("final-capabilities"), path, reporter, "phase5-checkpoint-scope-final-capabilities", "scope final-capabilities",
    )
    if scope.get("allow-roadmap-reorder") is not False:
        reporter.error("phase5-checkpoint-scope-reorder", path, "allow-roadmap-reorder必须严格为false")
    invalid_initial_changes = set(scope_initial_changes) - initial_changes
    invalid_initial_capabilities = set(scope_initial_capabilities) - initial_capabilities
    if invalid_initial_changes or invalid_initial_capabilities:
        reporter.error(
            "phase5-checkpoint-scope-initial-id",
            path,
            f"scope initial IDs不属于Phase 1 framework：changes={sorted(invalid_initial_changes)} capabilities={sorted(invalid_initial_capabilities)}",
        )
    scope_lineage_specs = (
        (
            "change-lineage", "input-change", "provisional-final-changes",
            set(scope_initial_changes), set(scope_final_changes),
            set(provisional_changes), "phase5-checkpoint-final-change-lineage",
        ),
        (
            "capability-lineage", "input-capability", "provisional-final-capabilities",
            set(scope_initial_capabilities), set(scope_final_capabilities),
            set(provisional_capabilities), "phase5-checkpoint-final-capability-lineage",
        ),
    )
    provisional_origins: Dict[str, Dict[str, Set[str]]] = {
        "change": {},
        "capability": {},
    }
    provisional_ga_origins: Dict[str, Dict[str, Set[str]]] = {
        "change": {},
        "capability": {},
    }
    for ga_id, row in ga_lineage_by_id.items():
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
            provisional_ga_origins["change"].setdefault(change_id, set()).add(ga_id)
        for capability_id in capability_ids:
            provisional_ga_origins["capability"].setdefault(capability_id, set()).add(ga_id)
    scoped_ga_ids = set(scope_ga)
    for lineage_field, input_field, final_field, scoped_initials, scoped_finals, existing_finals, rule in scope_lineage_specs:
        kind = "change" if lineage_field == "change-lineage" else "capability"
        origins = provisional_origins[kind]
        for row in framework.get(lineage_field, []) if isinstance(framework.get(lineage_field), list) else []:
            if not isinstance(row, dict):
                continue
            origin = normalize_code(row.get(input_field))
            for final_id in row.get(final_field, []) if isinstance(row.get(final_field), list) else []:
                origins.setdefault(normalize_code(final_id), set()).add(origin)
        hijacked: List[str] = []
        for final_id in sorted(scoped_finals & existing_finals):
            initial_origins = origins.get(final_id, set())
            evidence_origins = provisional_ga_origins[kind].get(final_id, set())
            if initial_origins:
                authorized = initial_origins.issubset(scoped_initials)
            else:
                authorized = bool(evidence_origins) and evidence_origins.issubset(scoped_ga_ids)
            if not authorized:
                hijacked.append(final_id)
        if hijacked:
            reporter.error(
                rule,
                path,
                "scope final IDs不得包含scope外或无lineage provenance的provisional ID："
                f"{hijacked}",
            )

    if verify_current_surfaces:
        phase2_trace_path = orchestrate_dir / "trace/phase-2.trace.json"
        try:
            phase2_trace = read_json(phase2_trace_path) if phase2_trace_path.exists() else {}
        except Exception:  # noqa: BLE001
            phase2_trace = {}
        if normalize_code(phase2_trace.get("mode")) == "initial":
            candidate_roots: Set[Tuple[str, str]] = set()
            for ga_id in target_ga_ids:
                row = collection_by_ga.get(ga_id, {})
                change_bucket = normalize_code(row.get("change-bucket"))
                capability_bucket = normalize_code(row.get("capability-bucket"))
                if change_bucket in initial_changes:
                    candidate_roots.add(("change", change_bucket))
                if capability_bucket in initial_capabilities:
                    candidate_roots.add(("capability", capability_bucket))

            selected_nodes = {
                *(("change", item) for item in scope_initial_changes),
                *(("capability", item) for item in scope_initial_capabilities),
            }
            selected_roots = selected_nodes & candidate_roots
            expected_nodes: Set[Tuple[str, str]] = set()
            if selected_nodes and not selected_roots:
                reporter.error(
                    "phase5-checkpoint-framework-closure",
                    path,
                    "framework review scope必须由request target的Phase 4 initial bucket发起；不得加入无关review unit",
                )
            elif selected_roots:
                graph: Dict[Tuple[str, str], Set[Tuple[str, str]]] = {}

                def connect(left: Tuple[str, str], right: Tuple[str, str]) -> None:
                    graph.setdefault(left, set()).add(right)
                    graph.setdefault(right, set()).add(left)

                for change_id, capability_id in _phase1_overlay(orchestrate_dir):
                    if change_id in initial_changes and capability_id in initial_capabilities:
                        connect(("change", change_id), ("capability", capability_id))
                change_semantics = _phase1_change_semantics(orchestrate_dir)
                for change_id, semantics in change_semantics.items():
                    dependency_text = semantics[9] if len(semantics) > 9 else ""
                    for dependency_id in parse_dependencies(dependency_text):
                        if change_id in initial_changes and dependency_id in initial_changes:
                            connect(("change", change_id), ("change", dependency_id))

                for overlay_row in framework.get("overlay", []) if isinstance(framework.get("overlay"), list) else []:
                    if not isinstance(overlay_row, dict):
                        continue
                    change_origins = provisional_origins["change"].get(
                        normalize_code(overlay_row.get("change")),
                        set(),
                    )
                    capability_origins = provisional_origins["capability"].get(
                        normalize_code(overlay_row.get("capability")),
                        set(),
                    )
                    for change_origin in change_origins:
                        for capability_origin in capability_origins:
                            connect(("change", change_origin), ("capability", capability_origin))
                for dependency_row in framework.get("dependency-edges", []) if isinstance(framework.get("dependency-edges"), list) else []:
                    if not isinstance(dependency_row, dict):
                        continue
                    change_origins = provisional_origins["change"].get(
                        normalize_code(dependency_row.get("change")),
                        set(),
                    )
                    dependency_origins = provisional_origins["change"].get(
                        normalize_code(dependency_row.get("depends-on")),
                        set(),
                    )
                    for change_origin in change_origins:
                        for dependency_origin in dependency_origins:
                            connect(("change", change_origin), ("change", dependency_origin))

                pending_nodes = list(selected_roots)
                while pending_nodes:
                    node = pending_nodes.pop()
                    if node in expected_nodes:
                        continue
                    expected_nodes.add(node)
                    pending_nodes.extend(graph.get(node, set()) - expected_nodes)
                if selected_nodes != expected_nodes:
                    reporter.error(
                        "phase5-checkpoint-framework-closure",
                        path,
                        "framework review scope必须恰好等于所选target bucket的最小dependency/overlay连通闭包；"
                        f"expected={sorted(expected_nodes)} actual={sorted(selected_nodes)}",
                    )

    expected_scope_ga = target_ga_ids | anticipated_new_ga_ids
    if set(scope_ga) != expected_scope_ga:
        reporter.error(
            "phase5-checkpoint-scope-target-ga",
            path,
            "allowed update scope的GA必须恰好等于target GA与确定性预分配的新GA，不得夹带无关GA",
        )
    invalid_scope_ga = set(scope_ga) - (base_ga_ids | anticipated_new_ga_ids)
    if invalid_scope_ga:
        reporter.error(
            "phase5-checkpoint-scope-unknown-ga",
            path,
            f"allowed update scope包含未知GA：{sorted(invalid_scope_ga)}",
        )

    pending_scope_checks = (
        (
            set(pending_capabilities),
            set(scope_initial_capabilities),
            "phase5-checkpoint-pending-capability-scope",
            "pending capability reviews必须恰好等于scope.initial-capabilities",
        ),
        (
            set(pending_changes),
            set(scope_initial_changes),
            "phase5-checkpoint-pending-change-scope",
            "pending change reviews必须恰好等于scope.initial-changes",
        ),
        (
            set(pending_mappings),
            set(scope_ga),
            "phase5-checkpoint-pending-mapping-scope",
            "pending atom mappings必须恰好等于scope.global-atom-ids",
        ),
        (
            set(pending_unassigned),
            set(scope_ga) & expected_unassigned_ga,
            "phase5-checkpoint-pending-unassigned-scope",
            "pending unassigned/gap reviews必须恰好等于scope GA与unassigned/gap GA的交集",
        ),
    )
    for actual_pending, expected_pending, rule, message in pending_scope_checks:
        if actual_pending != expected_pending:
            reporter.error(
                rule,
                path,
                f"{message}；期望={sorted(expected_pending)}，实际={sorted(actual_pending)}",
            )

    if (
        _scope_covers_full_typed_framework(
            initial_changes,
            set(provisional_changes),
            set(scope_initial_changes),
            set(scope_final_changes),
        )
        or _scope_covers_full_typed_framework(
            initial_capabilities,
            set(provisional_capabilities),
            set(scope_initial_capabilities),
            set(scope_final_capabilities),
        )
    ):
        reporter.error(
            "phase5-checkpoint-global-framework-scope",
            path,
            "allowed update scope已覆盖全部initial或全部provisional Change/Capability typed universe，必须blocked而不是继续patch",
        )

    preserved = data.get("preserved-row-digests")
    digest_rows: Dict[Tuple[str, str], str] = {}
    if not isinstance(preserved, list):
        reporter.error("phase5-checkpoint-preserved", path, "preserved-row-digests必须是array")
        preserved = []
    for index, row in enumerate(preserved):
        if not isinstance(row, dict):
            reporter.error("phase5-checkpoint-preserved-row", path, f"preserved-row-digests[{index}]必须是object")
            continue
        exact_fields(
            row,
            {"row-kind", "row-key", "sha256"},
            path,
            reporter,
            "phase5-checkpoint-preserved-row-fields",
            f"preserved-row-digests[{index}]",
        )
        kind = normalize_code(row.get("row-kind"))
        key = normalize_code(row.get("row-key"))
        pair = (kind, key)
        if kind not in CHECKPOINT_COMPLETED_ROW_FIELDS or not key or pair in digest_rows:
            reporter.error("phase5-checkpoint-preserved-row-key", path, f"preserved row kind/key非法或重复：{kind}/{key}")
            continue
        digest = normalize_code(row.get("sha256"))
        digest_rows[pair] = digest
        completed_row = completed_by_kind[kind].get(key)
        if completed_row is None:
            reporter.error("phase5-checkpoint-preserved-row-missing", path, f"preserved row没有对应completed row：{kind}/{key}")
        elif not _is_sha256(digest) or digest != canonical_json_sha256(completed_row):
            reporter.error("phase5-checkpoint-preserved-row-drift", path, f"preserved row digest失效：{kind}/{key}")
    expected_digest_keys = {
        (kind, key)
        for kind, rows in completed_by_kind.items()
        for key in rows
    }
    if set(digest_rows) != expected_digest_keys:
        reporter.error(
            "phase5-checkpoint-preserved-coverage",
            path,
            "preserved-row-digests必须恰好覆盖全部completed rows",
        )

    patch_attempt = data.get("patch-attempt")
    if not isinstance(patch_attempt, dict):
        reporter.error("phase5-checkpoint-patch-attempt", path, "patch-attempt必须是object")
    else:
        exact_fields(
            patch_attempt,
            {"attempt", "finding-fingerprint", "authority-digest"},
            path,
            reporter,
            "phase5-checkpoint-patch-attempt-fields",
            "patch-attempt",
        )
        if patch_attempt.get("attempt") != 1:
            reporter.error("phase5-checkpoint-patch-attempt-number", path, "patch-attempt.attempt必须严格为1")
        for field in ("finding-fingerprint", "authority-digest"):
            if not _is_sha256(patch_attempt.get(field)):
                reporter.error("phase5-checkpoint-patch-attempt-digest", path, f"patch-attempt.{field}必须是SHA-256")
        expected_finding_fingerprint = evidence_patch_finding_fingerprint(request_targets)
        if patch_attempt.get("finding-fingerprint") != expected_finding_fingerprint:
            reporter.error(
                "phase5-checkpoint-finding-fingerprint",
                path,
                "patch-attempt.finding-fingerprint必须由request targets的规范化defect locator机械计算",
            )
        expected_authority_digest = canonical_json_sha256({
            "input-fingerprints": data.get("input-fingerprints"),
            "patch-request-ref": data.get("patch-request-ref"),
            "provisional-framework": data.get("provisional-framework"),
        })
        if patch_attempt.get("authority-digest") != expected_authority_digest:
            reporter.error(
                "phase5-checkpoint-authority-digest",
                path,
                "patch-attempt.authority-digest必须绑定immutable input fingerprints、request ref与provisional framework",
            )
    return data


def _validate_patch_issuance_base_modes(
    orchestrate_dir: Path,
    reporter: IssueReporter,
) -> None:
    """requested patch只能从首次initial Phase 2–4快照发起。"""
    specs = (
        ("phase-2", "mode", "initial", "status", "source-atoms-written"),
        ("phase-3", "update-mode", "initial", "decision", "coverage-complete"),
        ("phase-4", "update-mode", "initial", "status", "assembled"),
    )
    for phase, mode_field, expected_mode, status_field, expected_status in specs:
        path = orchestrate_dir / f"trace/{phase}.trace.json"
        try:
            trace = read_json(path) if path.exists() else {}
        except Exception:  # noqa: BLE001
            trace = {}
        if (
            normalize_code(trace.get(mode_field)) != expected_mode
            or normalize_code(trace.get(status_field)) != expected_status
        ):
            reporter.error(
                "phase5-patch-budget-replay",
                path,
                "needs-targeted-evidence-patch只能从未执行patch的initial success Phase 2–4快照发起；"
                f"{phase}.{mode_field}={trace.get(mode_field)!r}, "
                f"{status_field}={trace.get(status_field)!r}",
            )


def validate_patch_authorization_group(
    orchestrate_dir: Path,
    repo_root: Path,
) -> Dict[str, object]:
    """在Phase 5 commit marker发布前完整校验request/checkpoint授权组。"""
    reporter = IssueReporter()
    _validate_patch_issuance_base_modes(orchestrate_dir, reporter)
    _validate_patch_request(orchestrate_dir, repo_root, reporter)
    _validate_checkpoint(orchestrate_dir, repo_root, reporter)
    return reporter.result()


def _validate_phase5_patch_scope_out_rows(
    refit: Dict[str, object],
    checkpoint: Dict[str, object],
    refit_path: Path,
    checkpoint_path: Path,
    reporter: IssueReporter,
) -> None:
    """闭合非终态refit snapshot与checkpoint completed/pending精确分区。"""
    completed = checkpoint.get("completed-rows")
    pending = checkpoint.get("pending-ids")
    provisional = checkpoint.get("provisional-framework")
    if not isinstance(completed, dict) or not isinstance(pending, dict) or not isinstance(provisional, dict):
        reporter.error(
            "phase5-patch-commit-refit-partition",
            checkpoint_path,
            "checkpoint必须提供completed-rows、pending-ids与provisional-framework以闭合nonterminal refit",
        )
        return
    base_ga_ids = {
        normalize_code(row.get("global-atom-id"))
        for row in provisional.get("ga-lineage", [])
        if isinstance(row, dict) and normalize_code(row.get("global-atom-id"))
    }
    specs = (
        ("capability-reviews", "input-capability", False),
        ("change-reviews", "input-change", False),
        ("unassigned-and-gap-reviews", "global-atom-id", True),
    )
    for kind, key_field, base_ga_only in specs:
        refit_rows = refit.get(kind)
        completed_rows = completed.get(kind)
        pending_raw = pending.get(kind)
        if not isinstance(refit_rows, list) or not isinstance(completed_rows, list) or not isinstance(pending_raw, list):
            reporter.error(
                "phase5-patch-commit-refit-partition",
                refit_path,
                f"{kind}必须在refit、checkpoint completed与pending中形成array分区",
            )
            continue
        pending_ids = {
            normalize_code(item)
            for item in pending_raw
            if isinstance(item, str) and normalize_code(item)
        }
        refit_keys: List[str] = []
        malformed_refit_row = False
        for row in refit_rows:
            if not isinstance(row, dict):
                malformed_refit_row = True
                continue
            refit_keys.append(normalize_code(row.get(key_field)))
        completed_keys: List[str] = []
        malformed_completed_row = False
        for row in completed_rows:
            if not isinstance(row, dict):
                malformed_completed_row = True
                continue
            completed_keys.append(normalize_code(row.get(key_field)))
        if (
            malformed_refit_row
            or malformed_completed_row
            or any(not key for key in refit_keys)
            or any(not key for key in completed_keys)
            or len(refit_keys) != len(set(refit_keys))
            or len(completed_keys) != len(set(completed_keys))
        ):
            reporter.error(
                "phase5-patch-commit-refit-partition",
                refit_path,
                f"{kind} row key必须非空且唯一",
            )
            continue
        existing_pending = pending_ids & base_ga_ids if base_ga_only else pending_ids
        expected_refit_keys = set(completed_keys) | existing_pending
        if set(refit_keys) != expected_refit_keys:
            reporter.error(
                "phase5-patch-commit-refit-partition",
                refit_path,
                f"nonterminal refit {kind}必须由completed keys与既有pending keys精确划分；"
                f"expected={sorted(expected_refit_keys)} actual={sorted(set(refit_keys))}",
            )
        scope_out_rows = [
            row
            for row in refit_rows
            if isinstance(row, dict) and normalize_code(row.get(key_field)) not in pending_ids
        ]
        if scope_out_rows != completed_rows:
            reporter.error(
                "phase5-patch-commit-scope-out-rows",
                refit_path,
                f"nonterminal refit {kind}的scope-out rows必须逐字复用checkpoint completed rows",
            )


def _validate_phase5_patch_commit_marker(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
) -> None:
    """验证Phase 5 trace对request/checkpoint/refit发布组的闭合提交。

    初次进入增量链时唯一合法marker是needs-targeted/requested；链完成或机械
    abort后，closed/blocked history是同一marker的不可回退后继状态，便于all-phase
    验证已推进的generation。
    """
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    refit_path = orchestrate_dir / "phase-works/phase-5/framework-refit-trace.json"
    request_path = _patch_request_path(orchestrate_dir)
    checkpoint_path = _checkpoint_path(orchestrate_dir)
    review_path = orchestrate_dir / "phase-works/phase-5/plan-refit-review.md"

    trace = json_obj(trace_path, reporter, PHASE_TRACE_SCHEMAS["phase-5"])
    refit = json_obj(refit_path, reporter, FRAMEWORK_REFIT_TRACE_SCHEMA)
    request = json_obj(request_path, reporter, EVIDENCE_PATCH_REQUEST_SCHEMA)
    checkpoint = json_obj(checkpoint_path, reporter, PHASE5_CHECKPOINT_SCHEMA)
    if not trace or not refit or not request or not checkpoint:
        reporter.error(
            "phase5-patch-commit-marker",
            trace_path,
            "targeted/incremental mode要求Phase 5 trace最后提交且request、checkpoint、refit四者齐全",
        )
        return

    trace_status = normalize_code(trace.get("status"))
    refit_status = normalize_code(refit.get("status"))
    execution_mode = normalize_code(trace.get("execution-mode"))
    history = refit.get("patch-history")
    trace_history = trace.get("patch-history")
    history_statuses = [
        normalize_code(row.get("status"))
        for row in history if isinstance(history, list) and isinstance(row, dict)
    ] if isinstance(history, list) else []
    lifecycle = ""
    if (
        trace_status == "needs-targeted-evidence-patch"
        and refit_status == trace_status
        and execution_mode == "initial"
        and history_statuses == ["requested"]
    ):
        lifecycle = "requested"
    elif (
        trace_status in FINAL_PHASE5_STATUSES
        and refit_status == trace_status
        and execution_mode == "checkpoint-resume"
        and history_statuses == ["closed"]
    ):
        lifecycle = "closed"
    elif (
        trace_status == "blocked"
        and refit_status == trace_status
        and execution_mode == "checkpoint-resume"
        and history_statuses == ["blocked"]
    ):
        lifecycle = "blocked"
    if not lifecycle:
        reporter.error(
            "phase5-patch-commit-marker",
            trace_path,
            "targeted/incremental mode缺少合法Phase 5 commit marker；"
            f"trace-status={trace_status or 'missing'} refit-status={refit_status or 'missing'} "
            f"execution-mode={execution_mode or 'missing'} history={history_statuses}",
        )
    if lifecycle in {"requested", "blocked"}:
        _validate_phase5_patch_scope_out_rows(
            refit,
            checkpoint,
            refit_path,
            checkpoint_path,
            reporter,
        )

    if trace_history != history:
        reporter.error(
            "phase5-patch-commit-history",
            trace_path,
            "Phase 5 trace patch-history必须与framework refit逐字一致",
        )
    history_row = history[0] if isinstance(history, list) and len(history) == 1 and isinstance(history[0], dict) else {}
    if not history_row:
        reporter.error("phase5-patch-commit-history", refit_path, "patch lifecycle要求恰好一条history row")
    else:
        exact_fields(
            history_row,
            {"request-id", "patch-request-ref", "checkpoint-ref", "finding-fingerprint", "status"},
            refit_path,
            reporter,
            "phase5-patch-commit-history-fields",
            "patch-history[0]",
        )
        if history_row.get("request-id") != PATCH_REQUEST_ID:
            reporter.error("phase5-patch-commit-history", refit_path, f"request-id必须为{PATCH_REQUEST_ID}")
        _validate_artifact_ref(
            history_row.get("patch-request-ref"),
            request_path,
            refit_path,
            repo_root,
            reporter,
            "phase5-patch-commit-request-ref",
        )
        _validate_artifact_ref(
            history_row.get("checkpoint-ref"),
            checkpoint_path,
            refit_path,
            repo_root,
            reporter,
            "phase5-patch-commit-checkpoint-ref",
        )
        patch_attempt = checkpoint.get("patch-attempt") if isinstance(checkpoint.get("patch-attempt"), dict) else {}
        if history_row.get("finding-fingerprint") != patch_attempt.get("finding-fingerprint"):
            reporter.error(
                "phase5-patch-commit-fingerprint",
                refit_path,
                "patch-history finding-fingerprint必须与checkpoint patch-attempt一致",
            )

    _validate_artifact_ref(
        checkpoint.get("patch-request-ref"),
        request_path,
        checkpoint_path,
        repo_root,
        reporter,
        "phase5-patch-commit-checkpoint-request-ref",
    )
    trace_artifacts = (
        ("framework-refit-trace", refit_path),
        ("plan-refit-review", review_path),
        ("evidence-patch-request", request_path),
        ("phase-5-checkpoint", checkpoint_path),
    )
    for prefix, artifact_path in trace_artifacts:
        if trace.get(f"{prefix}-path") != rel(artifact_path, repo_root):
            reporter.error(
                "phase5-patch-commit-path",
                trace_path,
                f"{prefix}-path未绑定canonical artifact",
            )
        if not artifact_path.exists() or trace.get(f"{prefix}-sha256") != sha256_file(artifact_path):
            reporter.error(
                "phase5-patch-commit-sha",
                trace_path,
                f"{prefix}-sha256未绑定当前artifact bytes",
            )

    if lifecycle in {"requested", "blocked"}:
        terminal_paths = (
            orchestrate_dir / "phase-works/phase-5/change-plan.md",
            orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json",
            orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.md",
            orchestrate_dir / "phase-works/phase-5/capability-baseline-reconciliation.json",
            orchestrate_dir / "phase-works/phase-5/capability-baseline-reconciliation.md",
            orchestrate_dir / "phase-works/phase-5/final-packet-index.json",
            orchestrate_dir / "change-plan.md",
            orchestrate_dir / "change-capability-anchors/index.md",
        )
        for terminal_path in terminal_paths:
            if terminal_path.exists():
                reporter.error(
                    "phase5-patch-commit-terminal-surface",
                    terminal_path,
                    "requested/blocked marker发布前必须清理Phase 5 terminal surface",
                )
        anchors_dir = orchestrate_dir / "change-capability-anchors"
        if anchors_dir.exists() and any(child.is_dir() for child in anchors_dir.iterdir()):
            reporter.error(
                "phase5-patch-commit-terminal-surface",
                anchors_dir,
                "requested/blocked marker不得保留final Change packet或Capability view目录",
            )


def iter_nested_keys(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from iter_nested_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_nested_keys(child)


def contains_source_fact(value: object, candidates: Set[str]) -> bool:
    if isinstance(value, str):
        return any(candidate in value for candidate in candidates)
    if isinstance(value, dict):
        return any(contains_source_fact(child, candidates) for child in value.values())
    if isinstance(value, list):
        return any(contains_source_fact(child, candidates) for child in value)
    return False


def load_phase3_gap_atoms(orchestrate_dir: Path, reporter: IssueReporter) -> Dict[str, Dict[str, object]]:
    path = orchestrate_dir / "phase-works/phase-3/coverage-review.json"
    data = json_obj(path, reporter, PHASE3_COVERAGE_REVIEW_SCHEMA)
    result: Dict[str, Dict[str, object]] = {}
    rows = data.get("gap-atoms")
    if not isinstance(rows, list):
        reporter.error("phase3-gap-atoms", path, "gap-atoms 必须是 array")
        return result
    expected_fields = {"gap-atom-id", "source-document", "line-ranges", "source-fact", "atom-type", "normativity", "review-judgment"}
    for row in rows:
        if not isinstance(row, dict):
            reporter.error("phase3-gap-atom-row", path, "gap-atoms item 必须是 object")
            continue
        gap_id = normalize_code(row.get("gap-atom-id"))
        exact_fields(row, expected_fields, path, reporter, "phase3-gap-atom-fields", gap_id or "gap atom")
        if not PHASE3_GAP_ID_RE.match(gap_id):
            reporter.error("phase3-gap-id", path, f"gap atom ID 非法：{gap_id}")
        if gap_id in result:
            reporter.error("phase3-gap-id-duplicate", path, f"gap atom ID 重复：{gap_id}")
        source_document = normalize_code(row.get("source-document"))
        check_atom_range(path, reporter, row.get("line-ranges"), source_document, repo_root_for_path(path), gap_id)
        check_source_fact_quote(path, reporter, row.get("source-fact"), row.get("line-ranges"), source_document, repo_root_for_path(path), gap_id)
        if normalize_code(row.get("atom-type")) not in PHASE2_ATOM_TYPES:
            reporter.error("phase3-gap-atom-type", path, f"{gap_id} atom-type 非法")
        if normalize_code(row.get("normativity")) not in PHASE2_NORMATIVITY:
            reporter.error("phase3-gap-normativity", path, f"{gap_id} normativity 非法")
        if not squash(row.get("review-judgment")):
            reporter.error("phase3-gap-judgment", path, f"{gap_id} 缺少中文 review-judgment")
        result[gap_id] = row
    return result


def repo_root_for_path(path: Path) -> Path:
    for parent in path.parents:
        if parent.name == "orchestrate" and parent.parent.name == "openspec":
            return parent.parent.parent
    return Path.cwd()


def validate_phase_3(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    trace_path = orchestrate_dir / "trace/phase-3.trace.json"
    coverage_path = orchestrate_dir / "phase-works/phase-3/coverage-review.json"
    index_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    trace = json_obj(trace_path, reporter, PHASE_TRACE_SCHEMAS["phase-3"])
    update_mode = ""
    patch_request: Dict[str, object] = {}
    checkpoint: Dict[str, object] = {}
    trace_new_ga_ids: List[str] = []
    trace_decision = validate_trace_status(trace, trace_path, reporter, "phase-3", "phase3-status") if trace else ""
    if trace_decision == "blocked":
        exact_fields(
            trace,
            {
                "trace-schema", "trace-contract-version", "decision", "update-mode",
                "patch-request-ref", "checkpoint-ref", "base-global-atom-index-sha256",
                "base-coverage-review-sha256", "affected-source-documents", "new-global-atom-ids", "issues",
            },
            trace_path,
            reporter,
            "phase3-trace-fields",
            "blocked Phase 3 trace",
        )
        update_mode = normalize_code(trace.get("update-mode"))
        affected_sources = trace.get("affected-source-documents")
        new_ga_ids = trace.get("new-global-atom-ids")
        if update_mode not in {"initial", "incremental-patch"}:
            reporter.error("phase3-update-mode", trace_path, "blocked update-mode只允许initial|incremental-patch")
        if (
            not isinstance(affected_sources, list)
            or any(not isinstance(item, str) for item in affected_sources)
            or len(affected_sources) != len(set(affected_sources))
        ):
            reporter.error("phase3-affected-sources", trace_path, "affected-source-documents必须是唯一string array")
            affected_sources = []
        if (
            not isinstance(new_ga_ids, list)
            or any(not isinstance(item, str) or not GLOBAL_ATOM_ID_RE.fullmatch(normalize_code(item)) for item in new_ga_ids)
            or len(new_ga_ids) != len(set(new_ga_ids))
        ):
            reporter.error("phase3-new-global-atoms", trace_path, "new-global-atom-ids必须是唯一合法GA array")
            new_ga_ids = []
        if not isinstance(trace.get("issues"), list) or not trace.get("issues"):
            reporter.error("phase3-trace-issues", trace_path, "blocked要求非空issues[]")
        if update_mode == "initial":
            if (
                trace.get("patch-request-ref") is not None
                or trace.get("checkpoint-ref") is not None
                or trace.get("base-global-atom-index-sha256") is not None
                or trace.get("base-coverage-review-sha256") is not None
                or affected_sources
                or new_ga_ids
            ):
                reporter.error("phase3-blocked-initial-fields", trace_path, "initial blocked要求patch/base为null且affected/new arrays为空")
        elif update_mode == "incremental-patch":
            _validate_phase5_patch_commit_marker(orchestrate_dir, repo_root, reporter)
            request_path = _patch_request_path(orchestrate_dir)
            checkpoint_path = _checkpoint_path(orchestrate_dir)
            _validate_artifact_ref(
                trace.get("patch-request-ref"), request_path, trace_path, repo_root, reporter, "phase3-patch-request-ref",
            )
            _validate_artifact_ref(
                trace.get("checkpoint-ref"), checkpoint_path, trace_path, repo_root, reporter, "phase3-checkpoint-ref",
            )
            patch_request = _validate_aborted_patch_request_snapshot(orchestrate_dir, reporter)
            _validate_checkpoint(orchestrate_dir, repo_root, reporter, verify_current_surfaces=False)
            base = patch_request.get("base-artifacts") if isinstance(patch_request.get("base-artifacts"), dict) else {}
            if trace.get("base-global-atom-index-sha256") != base.get("global-atom-index-sha256"):
                reporter.error("phase3-base-global-index", trace_path, "blocked base global index digest与request不一致")
            if trace.get("base-coverage-review-sha256") != base.get("coverage-review-sha256"):
                reporter.error("phase3-base-coverage", trace_path, "blocked base coverage digest与request不一致")
            expected_sources: List[str] = []
            for target in patch_request.get("targets", []) if isinstance(patch_request.get("targets"), list) else []:
                if isinstance(target, dict):
                    source = normalize_code(target.get("source-document"))
                    if source and source not in expected_sources:
                        expected_sources.append(source)
            if affected_sources != expected_sources:
                reporter.error("phase3-affected-sources", trace_path, "blocked affected-source-documents必须按request顺序恰好覆盖")
        return
    if trace:
        exact_fields(
            trace,
            {
                "trace-schema",
                "trace-contract-version",
                "decision",
                "global-atom-index-path",
                "global-atom-index-sha256",
                "coverage-review-path",
                "coverage-review-sha256",
                "update-mode",
                "patch-request-ref",
                "checkpoint-ref",
                "base-global-atom-index-sha256",
                "base-coverage-review-sha256",
                "affected-source-documents",
                "new-global-atom-ids",
            },
            trace_path,
            reporter,
            "phase3-trace-fields",
            "Phase 3 trace",
        )
        update_mode = normalize_code(trace.get("update-mode"))
        if update_mode not in {"initial", "incremental-patch"}:
            reporter.error("phase3-update-mode", trace_path, "update-mode只允许initial|incremental-patch")
        affected_sources = trace.get("affected-source-documents")
        new_ga_ids = trace.get("new-global-atom-ids")
        affected_valid = isinstance(affected_sources, list) and all(isinstance(item, str) for item in affected_sources)
        new_valid = isinstance(new_ga_ids, list) and all(isinstance(item, str) for item in new_ga_ids)
        if not affected_valid or len(affected_sources) != len(set(affected_sources)):
            reporter.error("phase3-affected-sources", trace_path, "affected-source-documents必须是唯一string array")
            affected_sources = []
        if (
            not new_valid
            or len(new_ga_ids) != len(set(new_ga_ids))
            or any(not GLOBAL_ATOM_ID_RE.fullmatch(normalize_code(item)) for item in new_ga_ids)
        ):
            reporter.error("phase3-new-global-atoms", trace_path, "new-global-atom-ids必须是唯一合法GA array")
            new_ga_ids = []
        trace_new_ga_ids = [normalize_code(item) for item in new_ga_ids]
        if update_mode == "initial":
            if (
                trace.get("patch-request-ref") is not None
                or trace.get("checkpoint-ref") is not None
                or trace.get("base-global-atom-index-sha256") is not None
                or trace.get("base-coverage-review-sha256") is not None
                or affected_sources != []
                or new_ga_ids != []
            ):
                reporter.error("phase3-initial-incremental-fields", trace_path, "initial mode要求patch/base为null且affected/new arrays为空")
        elif update_mode == "incremental-patch":
            _validate_phase5_patch_commit_marker(orchestrate_dir, repo_root, reporter)
            request_path = _patch_request_path(orchestrate_dir)
            checkpoint_path = _checkpoint_path(orchestrate_dir)
            _validate_artifact_ref(
                trace.get("patch-request-ref"), request_path, trace_path, repo_root, reporter, "phase3-patch-request-ref",
            )
            _validate_artifact_ref(
                trace.get("checkpoint-ref"), checkpoint_path, trace_path, repo_root, reporter, "phase3-checkpoint-ref",
            )
            patch_request = _validate_patch_request(orchestrate_dir, repo_root, reporter)
            checkpoint = _validate_checkpoint(orchestrate_dir, repo_root, reporter)
            request_base = patch_request.get("base-artifacts") if isinstance(patch_request.get("base-artifacts"), dict) else {}
            if trace.get("base-global-atom-index-sha256") != request_base.get("global-atom-index-sha256"):
                reporter.error("phase3-base-global-index", trace_path, "base global index digest与request不一致")
            if trace.get("base-coverage-review-sha256") != request_base.get("coverage-review-sha256"):
                reporter.error("phase3-base-coverage", trace_path, "base coverage digest与request不一致")
            expected_sources: List[str] = []
            for target in patch_request.get("targets", []) if isinstance(patch_request.get("targets"), list) else []:
                if isinstance(target, dict):
                    source = normalize_code(target.get("source-document"))
                    if source and source not in expected_sources:
                        expected_sources.append(source)
            if affected_sources != expected_sources:
                reporter.error("phase3-affected-sources", trace_path, "affected-source-documents必须按request顺序恰好覆盖")
    trace_decision = validate_trace_status(trace, trace_path, reporter, "phase-3", "phase3-status") if trace else ""
    coverage = json_obj(coverage_path, reporter, PHASE3_COVERAGE_REVIEW_SCHEMA)
    if coverage:
        exact_fields(
            coverage,
            {
                "trace-schema",
                "trace-contract-version",
                "artifact-path",
                "documents",
                "gap-atoms",
                "remainder-dispositions",
                "mapping-ambiguities",
                "summary",
                "decision",
                "language-self-check",
            },
            coverage_path,
            reporter,
            "phase3-coverage-review-fields",
            "coverage review",
        )
        expected_artifact = "openspec/orchestrate/phase-works/phase-3/coverage-review.md"
        if coverage.get("artifact-path") != expected_artifact:
            reporter.error("phase3-coverage-artifact-path", coverage_path, f"artifact-path 应为 {expected_artifact}")
        if not isinstance(coverage.get("summary"), dict):
            reporter.error("phase3-summary", coverage_path, "summary 必须是 object")
        if not squash(coverage.get("language-self-check")):
            reporter.error("phase3-language-self-check", coverage_path, "language-self-check 必须非空")
    decision = normalize_code(coverage.get("decision"))
    if decision not in PHASE_ALLOWED_TRACE_STATUSES["phase-3"]:
        reporter.error("phase3-decision", coverage_path, f"decision 非法：{decision}")
    if trace_decision and decision and trace_decision != decision:
        reporter.error("phase3-decision-drift", trace_path, "Phase 3 trace 与 coverage review decision 不一致")

    expected_trace = {
        "global-atom-index-path": rel(index_path, repo_root),
        "coverage-review-path": rel(coverage_path, repo_root),
    }
    for field, expected in expected_trace.items():
        if trace.get(field) != expected:
            reporter.error("phase3-trace-path", trace_path, f"{field} 应为 {expected}")
    for field, artifact in (("global-atom-index-sha256", index_path), ("coverage-review-sha256", coverage_path)):
        if artifact.exists() and trace.get(field) != sha256_file(artifact):
            reporter.error("phase3-trace-sha", trace_path, f"{field} 与 canonical artifact digest 不一致")

    removed_paths = [
        "phase-works/phase-3/source-doc-manifest.md",
        "phase-works/phase-3/source-doc-coverage",
        "phase-works/phase-3/phase-3-agent-report.md",
        "phase-works/phase-3/phase-3-trace",
    ]
    for relative in removed_paths:
        path = orchestrate_dir / relative
        if path.exists():
            reporter.error("phase3-legacy-artifact", path, "Phase 3 v1 已移除此 artifact")
    phase3_dir = orchestrate_dir / "phase-works/phase-3"
    allowed_phase3_files = {coverage_path.resolve(), coverage_path.with_suffix(".md").resolve()}
    if phase3_dir.exists():
        for path in phase3_dir.rglob("*"):
            if path.is_file() and path.resolve() not in allowed_phase3_files:
                reporter.error("phase3-unexpected-artifact", path, "Phase 3 固定五产物契约不允许此文件")

    phase2_atoms = load_phase2_atoms(orchestrate_dir, reporter)
    phase2_source_facts = {
        str(row.get("source-fact"))
        for row in phase2_atoms.values()
        if isinstance(row.get("source-fact"), str) and str(row.get("source-fact"))
    }
    coverage_without_gaps = dict(coverage)
    coverage_without_gaps["gap-atoms"] = []
    if contains_source_fact(trace, phase2_source_facts) or contains_source_fact(coverage_without_gaps, phase2_source_facts):
        reporter.error(
            "phase3-phase2-source-fact-copy",
            trace_path,
            "Phase 3 gap-atoms之外的 artifact不得复制 Phase 2 source-fact原文",
        )
    read_full = read_full_sources(orchestrate_dir, repo_root)
    documents = coverage.get("documents")
    document_rows: Dict[str, Dict[str, object]] = {}
    if not isinstance(documents, list):
        reporter.error("phase3-documents", coverage_path, "documents 必须是 array")
        documents = []
    document_fields = {"source-document", "source-sha256", "line-count", "phase-2-atom-path", "phase-2-atom-sha256", "covered-ranges", "candidate-uncovered-ranges"}
    uncovered_by_source: Dict[str, List[Dict[str, int]]] = {}
    for row in documents:
        if not isinstance(row, dict):
            reporter.error("phase3-document-row", coverage_path, "documents item 必须是 object")
            continue
        source_document = normalize_code(row.get("source-document"))
        exact_fields(row, document_fields, coverage_path, reporter, "phase3-document-fields", source_document or "document")
        if source_document in document_rows:
            reporter.error("phase3-document-duplicate", coverage_path, f"source document 重复：{source_document}")
        document_rows[source_document] = row
        source_path = repo_root / source_document
        sidecar = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms" / source_atom_file_name(source_document).replace(".md", ".json")
        if not source_path.exists():
            reporter.error("phase3-source-missing", coverage_path, f"来源文档不存在：{source_document}")
            continue
        if not sidecar.exists():
            reporter.error("phase3-phase2-artifact-missing", coverage_path, f"{source_document} 缺少 Phase 2 atom artifact")
        else:
            phase2_data = json_obj(sidecar, reporter, SOURCE_ATOMS_SCHEMA)
            if normalize_code(phase2_data.get("source-document")) != source_document:
                reporter.error("phase3-phase2-artifact-source", sidecar, f"Phase 2 artifact source-document 应为 {source_document}")
            if phase2_data.get("source-sha256") != sha256_file(source_path):
                reporter.error("phase3-phase2-artifact-source-sha", sidecar, f"{source_document} 的 Phase 2 source digest已失效")
        line_count = source_line_count(repo_root, source_document) or 0
        expected_covered = phase2_evidence_ranges(orchestrate_dir, source_document) if sidecar.exists() else []
        expected_uncovered = uncovered_line_ranges(expected_covered, line_count)
        uncovered_by_source[source_document] = expected_uncovered
        expected_values = {
            "source-sha256": sha256_file(source_path),
            "line-count": line_count,
            "phase-2-atom-path": rel(sidecar, repo_root),
            "phase-2-atom-sha256": sha256_file(sidecar) if sidecar.exists() else "",
            "covered-ranges": expected_covered,
            "candidate-uncovered-ranges": expected_uncovered,
        }
        for field, expected in expected_values.items():
            if row.get(field) != expected:
                reporter.error("phase3-document-drift", coverage_path, f"{source_document} 的 {field} 与机械重算不一致")
    if set(document_rows) != set(read_full):
        reporter.error("phase3-document-coverage", coverage_path, f"documents 必须恰好覆盖 read-full source；缺少={sorted(set(read_full)-set(document_rows))}，多余={sorted(set(document_rows)-set(read_full))}")

    gap_atoms = load_phase3_gap_atoms(orchestrate_dir, reporter)
    for gap_id, row in gap_atoms.items():
        source_document = normalize_code(row.get("source-document"))
        ranges = valid_range_items(row.get("line-ranges"))
        if ranges and not range_covered_by(ranges[0], uncovered_by_source.get(source_document, [])):
            reporter.error("phase3-gap-not-uncovered", coverage_path, f"{gap_id} 不在 Phase 2 uncovered range内")

    dispositions = coverage.get("remainder-dispositions")
    if not isinstance(dispositions, list):
        reporter.error("phase3-dispositions", coverage_path, "remainder-dispositions 必须是 array")
        dispositions = []
    disposition_fields = {"disposition-id", "source-document", "line-ranges", "classification", "linked-gap-atom-ids", "reason"}
    seen_disposition_ids: Set[str] = set()
    disposition_ranges: Dict[str, List[Dict[str, int]]] = {}
    gap_link_counts = {gap_id: 0 for gap_id in gap_atoms}
    classifications: List[str] = []
    for row in dispositions:
        if not isinstance(row, dict):
            reporter.error("phase3-disposition-row", coverage_path, "remainder-dispositions item 必须是 object")
            continue
        disposition_id = normalize_code(row.get("disposition-id"))
        source_document = normalize_code(row.get("source-document"))
        classification = normalize_code(row.get("classification"))
        classifications.append(classification)
        exact_fields(row, disposition_fields, coverage_path, reporter, "phase3-disposition-fields", disposition_id or "disposition")
        if not PHASE3_DISPOSITION_ID_RE.match(disposition_id) or disposition_id in seen_disposition_ids:
            reporter.error("phase3-disposition-id", coverage_path, f"disposition ID非法或重复：{disposition_id}")
        seen_disposition_ids.add(disposition_id)
        if classification not in PHASE3_DISPOSITIONS:
            reporter.error("phase3-disposition-classification", coverage_path, f"{disposition_id} classification非法：{classification}")
        check_ranges(coverage_path, reporter, row.get("line-ranges"), source_document, repo_root, disposition_id)
        ranges = valid_range_items(row.get("line-ranges"))
        disposition_ranges.setdefault(source_document, []).extend(ranges)
        for item in ranges:
            if not range_covered_by(item, uncovered_by_source.get(source_document, [])):
                reporter.error("phase3-disposition-not-uncovered", coverage_path, f"{disposition_id} 包含 Phase 2 covered range")
        linked = row.get("linked-gap-atom-ids")
        if not isinstance(linked, list) or len(linked) != len(set(linked)):
            reporter.error("phase3-disposition-gap-links", coverage_path, f"{disposition_id} 的 linked-gap-atom-ids 必须是唯一 array")
            linked = []
        if classification == "missing-obligation" and not linked:
            reporter.error("phase3-missing-gap-link", coverage_path, f"{disposition_id} 必须链接 gap atom")
        if classification != "missing-obligation" and linked:
            reporter.error("phase3-unexpected-gap-link", coverage_path, f"{disposition_id} 的 {classification} 不得链接 gap atom")
        for gap_id in linked:
            gap = gap_atoms.get(str(gap_id))
            if not gap:
                reporter.error("phase3-unknown-gap", coverage_path, f"{disposition_id} 引用了未知 gap atom：{gap_id}")
                continue
            gap_link_counts[str(gap_id)] += 1
            gap_ranges = valid_range_items(gap.get("line-ranges"))
            if normalize_code(gap.get("source-document")) != source_document or not gap_ranges or not range_covered_by(gap_ranges[0], ranges):
                reporter.error("phase3-gap-disposition-range", coverage_path, f"{gap_id} 不在 {disposition_id} 的 source/range内")
        if not squash(row.get("reason")):
            reporter.error("phase3-disposition-reason", coverage_path, f"{disposition_id} 缺少中文 reason")
    for source_document, candidates in uncovered_by_source.items():
        for candidate in candidates:
            if not range_covered_by(candidate, disposition_ranges.get(source_document, [])):
                reporter.error("phase3-uncovered-disposition", coverage_path, f"{source_document} 的 {line_range_label(candidate)} 尚未处置")
    for gap_id, count in gap_link_counts.items():
        if count != 1:
            reporter.error("phase3-gap-link-cardinality", coverage_path, f"{gap_id} 必须恰好由一个 missing-obligation disposition链接，实际 {count}")

    global_atoms = load_global_atoms(orchestrate_dir, reporter)
    seen_refs: Set[str] = set()
    referenced_phase2: Set[str] = set()
    referenced_gaps: Set[str] = set()
    for ga_id, row in global_atoms.items():
        exact_fields(row, {"global-atom-id", "evidence-ref"}, index_path, reporter, "phase3-global-atom-fields", ga_id)
        evidence_ref = row.get("evidence-ref")
        if not isinstance(evidence_ref, dict):
            reporter.error("phase3-evidence-ref", index_path, f"{ga_id} evidence-ref必须是 object")
            continue
        kind = normalize_code(evidence_ref.get("kind"))
        if kind == "phase-2-source-atom":
            exact_fields(evidence_ref, {"kind", "source-document", "source-atom-id"}, index_path, reporter, "phase3-evidence-ref-fields", ga_id)
            key = f"{normalize_code(evidence_ref.get('source-document'))}::{normalize_code(evidence_ref.get('source-atom-id'))}"
            if key not in phase2_atoms:
                reporter.error("phase3-evidence-ref-dangling", index_path, f"{ga_id} 引用未知 Phase 2 atom：{key}")
            referenced_phase2.add(key)
            ref_key = f"p2::{key}"
        elif kind == "phase-3-gap-atom":
            exact_fields(evidence_ref, {"kind", "gap-atom-id"}, index_path, reporter, "phase3-evidence-ref-fields", ga_id)
            gap_id = normalize_code(evidence_ref.get("gap-atom-id"))
            if gap_id not in gap_atoms:
                reporter.error("phase3-evidence-ref-dangling", index_path, f"{ga_id} 引用未知 gap atom：{gap_id}")
            referenced_gaps.add(gap_id)
            ref_key = f"p3::{gap_id}"
        else:
            reporter.error("phase3-evidence-ref-kind", index_path, f"{ga_id} evidence-ref kind非法：{kind}")
            continue
        if ref_key in seen_refs:
            reporter.error("phase3-evidence-ref-duplicate", index_path, f"evidence occurrence被多个 GA引用：{ref_key}")
        seen_refs.add(ref_key)
    if referenced_phase2 != set(phase2_atoms):
        reporter.error("phase3-phase2-ga-cardinality", index_path, f"Phase 2 occurrence必须一对一分配 GA；缺少={sorted(set(phase2_atoms)-referenced_phase2)}，多余={sorted(referenced_phase2-set(phase2_atoms))}")
    if referenced_gaps != set(gap_atoms):
        reporter.error("phase3-gap-ga-cardinality", index_path, f"gap occurrence必须一对一分配 GA；缺少={sorted(set(gap_atoms)-referenced_gaps)}，多余={sorted(referenced_gaps-set(gap_atoms))}")

    ambiguities = coverage.get("mapping-ambiguities")
    ambiguity_rows: Dict[str, Dict[str, object]] = {}
    if not isinstance(ambiguities, list):
        reporter.error("phase3-mapping-ambiguities", coverage_path, "mapping-ambiguities必须是array")
        ambiguities = []
    for index, row in enumerate(ambiguities):
        if not isinstance(row, dict):
            reporter.error("phase3-mapping-ambiguity-row", coverage_path, f"mapping-ambiguities[{index}]必须是object")
            continue
        exact_fields(
            row,
            {"global-atom-id", "evidence-ref", "dimensions", "reason"},
            coverage_path,
            reporter,
            "phase3-mapping-ambiguity-fields",
            f"mapping-ambiguities[{index}]",
        )
        ga_id = normalize_code(row.get("global-atom-id"))
        if not GLOBAL_ATOM_ID_RE.fullmatch(ga_id) or ga_id in ambiguity_rows or ga_id not in global_atoms:
            reporter.error("phase3-mapping-ambiguity-ga", coverage_path, f"mapping ambiguity GA非法、重复或未知：{ga_id}")
        else:
            ambiguity_rows[ga_id] = row
        if ga_id in global_atoms and row.get("evidence-ref") != global_atoms[ga_id].get("evidence-ref"):
            reporter.error("phase3-mapping-ambiguity-ref", coverage_path, f"{ga_id} evidence-ref与global index不一致")
        dimensions = row.get("dimensions")
        if (
            not isinstance(dimensions, list)
            or not dimensions
            or any(not isinstance(item, str) for item in dimensions)
            or len(dimensions) != len(set(dimensions))
            or any(normalize_code(item) not in MAPPING_AMBIGUITY_DIMENSIONS for item in dimensions)
        ):
            reporter.error(
                "phase3-mapping-ambiguity-dimensions",
                coverage_path,
                f"{ga_id} dimensions必须是非空唯一允许值array",
            )
        reason = str(row.get("reason", ""))
        if not squash(reason) or not re.search(r"[\u4e00-\u9fff]", reason):
            reporter.error("phase3-mapping-ambiguity-reason", coverage_path, f"{ga_id} reason必须使用简体中文")

    if update_mode == "incremental-patch" and patch_request:
        protected_rows = patch_request.get("protected-rows")
        protected_global_rows = protected_rows.get("global-atoms") if isinstance(protected_rows, dict) else []
        base_ga_ids = {
            normalize_code(row.get("global-atom-id"))
            for row in protected_global_rows if isinstance(row, dict)
        }
        request_targets = patch_request.get("targets") if isinstance(patch_request.get("targets"), list) else []
        target_ga_ids = {
            normalize_code(target.get("global-atom-id"))
            for target in request_targets
            if isinstance(target, dict) and target.get("global-atom-id") is not None
        }
        base_ga_ids.update(target_ga_ids)
        actual_new_ga_ids = sorted(
            set(global_atoms) - base_ga_ids,
            key=lambda item: int(item.split("-")[1]) if GLOBAL_ATOM_ID_RE.fullmatch(item) else 0,
        )
        if trace_new_ga_ids != actual_new_ga_ids:
            reporter.error("phase3-incremental-new-ga-coverage", trace_path, "new-global-atom-ids必须恰好覆盖增量追加GA")
        if set(global_atoms) != base_ga_ids | set(actual_new_ga_ids):
            reporter.error("phase3-incremental-ga-identity", index_path, "incremental global index丢失或重编号base GA")
        max_base_number = max(
            (int(item.split("-")[1]) for item in base_ga_ids if GLOBAL_ATOM_ID_RE.fullmatch(item)),
            default=0,
        )
        expected_new_ga_ids = [
            f"GA-{number:04d}"
            for number in range(max_base_number + 1, max_base_number + len(actual_new_ga_ids) + 1)
        ]
        if actual_new_ga_ids != expected_new_ga_ids:
            reporter.error("phase3-incremental-ga-append", index_path, "新GA必须从base最大ID之后单调连续追加")
        expected_new_refs = [
            (
                normalize_code(target.get("source-document")),
                normalize_code(new_id),
            )
            for target in request_targets
            if isinstance(target, dict)
            for new_id in (
                target.get("new-source-atom-ids", [])
                if isinstance(target.get("new-source-atom-ids"), list)
                else []
            )
        ]
        actual_new_refs = [
            (
                normalize_code(global_atoms[ga_id].get("evidence-ref", {}).get("source-document")),
                normalize_code(global_atoms[ga_id].get("evidence-ref", {}).get("source-atom-id")),
            )
            for ga_id in actual_new_ga_ids
            if isinstance(global_atoms[ga_id].get("evidence-ref"), dict)
            and normalize_code(global_atoms[ga_id].get("evidence-ref", {}).get("kind")) == "phase-2-source-atom"
        ]
        if actual_new_refs != expected_new_refs:
            reporter.error("phase3-incremental-new-ga-ref", index_path, "新增GA必须按request target/new-ID顺序恰好引用patch新增source atoms")

    summary = coverage.get("summary") if isinstance(coverage.get("summary"), dict) else {}
    disposition_counts = {name: classifications.count(name) for name in sorted(PHASE3_DISPOSITIONS)}
    expected_summary = {
        "source-documents": len(read_full),
        "phase-2-atoms": len(phase2_atoms),
        "gap-atoms": len(gap_atoms),
        "global-atoms": len(global_atoms),
        "mapping-ambiguities": len(ambiguity_rows),
        "candidate-uncovered-ranges": sum(len(items) for items in uncovered_by_source.values()),
        "remainder-dispositions": disposition_counts,
    }
    if summary != expected_summary:
        reporter.error("phase3-summary-drift", coverage_path, f"summary 与机械重算不一致；期望 {expected_summary}")

    if decision == "coverage-complete" and "blocked" in classifications:
        reporter.error("phase3-decision-consistency", coverage_path, "coverage-complete不得包含blocked disposition")
    if decision == "blocked" and "blocked" not in classifications:
        reporter.error("phase3-decision-consistency", coverage_path, "blocked decision要求至少一个 blocked disposition作为正向证据")
    validate_global_index_mirror(orchestrate_dir, reporter)
    validate_coverage_review_mirror(orchestrate_dir, reporter)


def resolve_global_evidence(
    orchestrate_dir: Path,
    global_atoms: Dict[str, Dict[str, object]],
    reporter: IssueReporter,
) -> Dict[str, Dict[str, object]]:
    index_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    phase2_atoms = load_phase2_atoms(orchestrate_dir, reporter)
    gap_atoms = load_phase3_gap_atoms(orchestrate_dir, reporter)
    resolved: Dict[str, Dict[str, object]] = {}
    seen_refs: Set[str] = set()
    for ga_id, global_row in global_atoms.items():
        evidence_ref = global_row.get("evidence-ref")
        if not isinstance(evidence_ref, dict):
            reporter.error("evidence-resolver-ref", index_path, f"{ga_id} 缺少有效 evidence-ref")
            continue
        kind = normalize_code(evidence_ref.get("kind"))
        evidence: Dict[str, object] | None = None
        if kind == "phase-2-source-atom":
            exact_fields(evidence_ref, {"kind", "source-document", "source-atom-id"}, index_path, reporter, "evidence-resolver-ref-fields", ga_id)
            key = f"{normalize_code(evidence_ref.get('source-document'))}::{normalize_code(evidence_ref.get('source-atom-id'))}"
            evidence = phase2_atoms.get(key)
            ref_key = f"p2::{key}"
        elif kind == "phase-3-gap-atom":
            exact_fields(evidence_ref, {"kind", "gap-atom-id"}, index_path, reporter, "evidence-resolver-ref-fields", ga_id)
            gap_id = normalize_code(evidence_ref.get("gap-atom-id"))
            evidence = gap_atoms.get(gap_id)
            ref_key = f"p3::{gap_id}"
        else:
            reporter.error("evidence-resolver-kind", index_path, f"{ga_id} evidence-ref kind非法：{kind}")
            continue
        if ref_key in seen_refs:
            reporter.error("evidence-resolver-duplicate", index_path, f"evidence occurrence被多个 GA引用：{ref_key}")
        seen_refs.add(ref_key)
        if evidence is None:
            reporter.error("evidence-resolver-dangling", index_path, f"{ga_id} 无法解析 evidence-ref")
            continue
        resolved[ga_id] = {
            "evidence-ref": evidence_ref,
            "source-document": evidence.get("source-document"),
            "line-ranges": evidence.get("line-ranges"),
            "source-fact": evidence.get("source-fact"),
            "atom-type": evidence.get("atom-type"),
            "normativity": evidence.get("normativity"),
            "candidate-status": evidence.get("candidate-status"),
            "candidate-artifact-projection": evidence.get("candidate-artifact-projection"),
            "candidate-owner-change": evidence.get("candidate-owner-change"),
            "candidate-target-capability": evidence.get("candidate-target-capability"),
        }
    return resolved


def validate_phase_4(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    phase4_trace_path = orchestrate_dir / "trace/phase-4.trace.json"
    phase4_trace = json_obj(phase4_trace_path, reporter, PHASE_TRACE_SCHEMAS["phase-4"])
    status = validate_trace_status(phase4_trace, phase4_trace_path, reporter, "phase-4", "phase4-status") if phase4_trace else ""
    update_mode = normalize_code(phase4_trace.get("update-mode")) if phase4_trace else ""
    if phase4_trace and update_mode not in {"initial", "incremental-patch"}:
        reporter.error("phase4-update-mode", phase4_trace_path, "update-mode只允许initial|incremental-patch")
    phase1_plan_path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    require_file(phase1_plan_path, reporter, "phase4-interface-input", "缺少 Phase 4 输入：Phase 1 initial-change-plan.md")
    require_file(orchestrate_dir / "phase-works/phase-4/phase-4-agent-report.md", reporter, "phase4-interface-artifact", "缺少 Phase 4 agent 报告")
    legacy_paths = [
        orchestrate_dir / "phase-works/phase-4/input-change-plan.md",
        orchestrate_dir / "phase-works/phase-4/source-window-dossiers",
        orchestrate_dir / "phase-works/phase-4/source-window-semantic-profile-review.md",
        orchestrate_dir / "phase-works/phase-4/source-window-grounding-issues.md",
    ]
    for legacy in legacy_paths:
        if legacy.exists():
            reporter.error("phase4-legacy-artifact", legacy, "旧 Phase 4 source-window artifact 已废弃，必须清理并重跑 Phase 4")
    index_path = orchestrate_dir / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"
    collection_root = index_path.parent
    if status in NON_FINAL_PHASE4_STATUSES:
        exact_fields(
            phase4_trace,
            {
                "trace-schema", "trace-contract-version", "status", "update-mode",
                "patch-request-ref", "checkpoint-ref", "base-evidence-collection-index-sha256",
                "affected-closure", "issues",
            },
            phase4_trace_path,
            reporter,
            "phase4-trace-fields",
            "nonterminal phase-4 trace",
        )
        if not isinstance(phase4_trace.get("issues"), list) or not phase4_trace.get("issues"):
            reporter.error("phase4-trace-issues", phase4_trace_path, f"{status}状态要求非空issues[]")
        blocked_closure = phase4_trace.get("affected-closure")
        if not isinstance(blocked_closure, dict):
            reporter.error("phase4-affected-closure", phase4_trace_path, "blocked affected-closure必须是object")
            blocked_closure = {}
        else:
            exact_fields(
                blocked_closure,
                {"global-atom-ids", "change-buckets", "capability-buckets", "rendered-artifact-paths"},
                phase4_trace_path,
                reporter,
                "phase4-affected-closure-fields",
                "blocked affected-closure",
            )
        blocked_closure_values: Dict[str, List[str]] = {}
        for field in ("global-atom-ids", "change-buckets", "capability-buckets", "rendered-artifact-paths"):
            value = blocked_closure.get(field)
            if (
                not isinstance(value, list)
                or any(not isinstance(item, str) or not normalize_code(item) for item in value)
                or len(value) != len(set(value))
            ):
                reporter.error("phase4-affected-closure-value", phase4_trace_path, f"blocked affected-closure.{field}必须是唯一string array")
                blocked_closure_values[field] = []
            else:
                blocked_closure_values[field] = [normalize_code(item) for item in value]
        if update_mode == "initial":
            if (
                phase4_trace.get("patch-request-ref") is not None
                or phase4_trace.get("checkpoint-ref") is not None
                or phase4_trace.get("base-evidence-collection-index-sha256") is not None
                or any(blocked_closure_values.values())
            ):
                reporter.error("phase4-blocked-initial-fields", phase4_trace_path, "initial blocked要求patch/base为null且affected closure为空")
        elif update_mode == "incremental-patch":
            _validate_phase5_patch_commit_marker(orchestrate_dir, repo_root, reporter)
            request_path = _patch_request_path(orchestrate_dir)
            checkpoint_path = _checkpoint_path(orchestrate_dir)
            _validate_artifact_ref(
                phase4_trace.get("patch-request-ref"), request_path, phase4_trace_path, repo_root, reporter, "phase4-patch-request-ref",
            )
            _validate_artifact_ref(
                phase4_trace.get("checkpoint-ref"), checkpoint_path, phase4_trace_path, repo_root, reporter, "phase4-checkpoint-ref",
            )
            request = _validate_aborted_patch_request_snapshot(orchestrate_dir, reporter)
            _validate_checkpoint(orchestrate_dir, repo_root, reporter, verify_current_surfaces=False)
            base = request.get("base-artifacts") if isinstance(request.get("base-artifacts"), dict) else {}
            if phase4_trace.get("base-evidence-collection-index-sha256") != base.get("phase-4-index-sha256"):
                reporter.error("phase4-base-index", phase4_trace_path, "blocked base evidence collection index digest与request不一致")
            target_ga_ids = {
                normalize_code(target.get("global-atom-id"))
                for target in request.get("targets", []) if isinstance(request.get("targets"), list)
                if isinstance(target, dict) and target.get("global-atom-id") is not None
            }
            if not target_ga_ids.issubset(set(blocked_closure_values["global-atom-ids"])):
                reporter.error("phase4-blocked-affected-ga", phase4_trace_path, "blocked affected closure必须至少包含全部target GA")
        if index_path.exists():
            reporter.error("phase4-nonfinal-terminal-artifact", index_path, f"{status}状态不得保留terminal index")
        if collection_root.exists():
            for path in collection_root.rglob("*.md"):
                reporter.error("phase4-nonfinal-terminal-artifact", path, f"{status}状态不得保留terminal collection")
        return
    if status != "assembled":
        return
    exact_fields(
        phase4_trace,
        {
            "trace-schema", "trace-contract-version", "status", "update-mode", "patch-request-ref",
            "checkpoint-ref", "base-evidence-collection-index-sha256", "affected-closure", "assembled",
        },
        phase4_trace_path,
        reporter,
        "phase4-trace-fields",
        "assembled phase-4 trace",
    )
    affected_closure = phase4_trace.get("affected-closure")
    if not isinstance(affected_closure, dict):
        reporter.error("phase4-affected-closure", phase4_trace_path, "affected-closure必须是object")
        affected_closure = {}
    else:
        exact_fields(
            affected_closure,
            {"global-atom-ids", "change-buckets", "capability-buckets", "rendered-artifact-paths"},
            phase4_trace_path,
            reporter,
            "phase4-affected-closure-fields",
            "affected-closure",
        )
    closure_values: Dict[str, List[str]] = {}
    for field in ("global-atom-ids", "change-buckets", "capability-buckets", "rendered-artifact-paths"):
        value = affected_closure.get(field)
        if (
            not isinstance(value, list)
            or any(not isinstance(item, str) or not normalize_code(item) for item in value)
            or len(value) != len(set(value))
        ):
            reporter.error("phase4-affected-closure-value", phase4_trace_path, f"affected-closure.{field}必须是唯一string array")
            closure_values[field] = []
        else:
            closure_values[field] = [normalize_code(item) for item in value]
    patch_request: Dict[str, object] = {}
    checkpoint: Dict[str, object] = {}
    if update_mode == "initial":
        if (
            phase4_trace.get("patch-request-ref") is not None
            or phase4_trace.get("checkpoint-ref") is not None
            or phase4_trace.get("base-evidence-collection-index-sha256") is not None
            or any(closure_values.values())
        ):
            reporter.error("phase4-initial-incremental-fields", phase4_trace_path, "initial mode要求patch/base为null且affected closure为空")
    elif update_mode == "incremental-patch":
        _validate_phase5_patch_commit_marker(orchestrate_dir, repo_root, reporter)
        request_path = _patch_request_path(orchestrate_dir)
        checkpoint_path = _checkpoint_path(orchestrate_dir)
        _validate_artifact_ref(
            phase4_trace.get("patch-request-ref"), request_path, phase4_trace_path, repo_root, reporter, "phase4-patch-request-ref",
        )
        _validate_artifact_ref(
            phase4_trace.get("checkpoint-ref"), checkpoint_path, phase4_trace_path, repo_root, reporter, "phase4-checkpoint-ref",
        )
        patch_request = _validate_patch_request(orchestrate_dir, repo_root, reporter)
        checkpoint = _validate_checkpoint(orchestrate_dir, repo_root, reporter)
        request_base = patch_request.get("base-artifacts") if isinstance(patch_request.get("base-artifacts"), dict) else {}
        if phase4_trace.get("base-evidence-collection-index-sha256") != request_base.get("phase-4-index-sha256"):
            reporter.error("phase4-base-index", phase4_trace_path, "base evidence collection index digest与request不一致")
    assembled = phase4_trace.get("assembled")
    if not isinstance(assembled, dict):
        reporter.error("phase4-trace-assembled", phase4_trace_path, "assembled必须是object")
        assembled = {}
    else:
        exact_fields(
            assembled,
            {"evidence-collection-index-path", "evidence-collection-index-sha256", "renderer-result-summary"},
            phase4_trace_path,
            reporter,
            "phase4-trace-assembled-fields",
            "assembled",
        )
    data = json_obj(index_path, reporter, EVIDENCE_COLLECTION_INDEX_SCHEMA)
    if data:
        exact_fields(
            data,
            {"trace-schema", "trace-contract-version", "generated-from", "rows", "rendered-artifacts"},
            index_path,
            reporter,
            "phase4-index-fields",
            "derived evidence collection index",
        )
    if update_mode == "incremental-patch" and patch_request and data:
        request_targets = patch_request.get("targets") if isinstance(patch_request.get("targets"), list) else []
        target_ga_ids = {
            normalize_code(target.get("global-atom-id"))
            for target in request_targets
            if isinstance(target, dict) and target.get("global-atom-id") is not None
        }
        phase3_trace_path = orchestrate_dir / "trace/phase-3.trace.json"
        try:
            phase3_trace = read_json(phase3_trace_path) if phase3_trace_path.exists() else {}
        except Exception:  # noqa: BLE001
            phase3_trace = {}
        new_ga_ids = {
            normalize_code(item)
            for item in phase3_trace.get("new-global-atom-ids", [])
            if isinstance(item, str)
        }
        expected_affected_ga = target_ga_ids | new_ga_ids
        if set(closure_values["global-atom-ids"]) != expected_affected_ga:
            reporter.error("phase4-affected-ga-closure", phase4_trace_path, "affected closure GA必须恰好覆盖target与新增GA")

        rendered_rows = data.get("rendered-artifacts") if isinstance(data.get("rendered-artifacts"), list) else []
        rendered_by_path = {
            normalize_code(row.get("artifact-path")): row
            for row in rendered_rows
            if isinstance(row, dict) and normalize_code(row.get("artifact-path"))
        }
        protected_rows = patch_request.get("protected-rows")
        protected_rendered = protected_rows.get("phase-4-rendered-artifacts") if isinstance(protected_rows, dict) else []
        protected_rendered_paths = {
            normalize_code(row.get("artifact-path"))
            for row in protected_rendered
            if isinstance(row, dict)
        }
        expected_affected_paths = set(rendered_by_path) - protected_rendered_paths
        if set(closure_values["rendered-artifact-paths"]) != expected_affected_paths:
            reporter.error(
                "phase4-affected-rendered-closure",
                phase4_trace_path,
                "affected rendered paths必须恰好是全部rendered artifacts减request protected rows",
            )
        expected_change_buckets = {
            normalize_code(rendered_by_path[item].get("owner-id"))
            for item in expected_affected_paths
            if normalize_code(rendered_by_path[item].get("collection-kind")) == "input-change"
        }
        expected_capability_buckets = {
            normalize_code(rendered_by_path[item].get("owner-id"))
            for item in expected_affected_paths
            if normalize_code(rendered_by_path[item].get("collection-kind")) == "input-capability"
        }
        if set(closure_values["change-buckets"]) != expected_change_buckets:
            reporter.error("phase4-affected-change-closure", phase4_trace_path, "change-buckets与affected rendered artifacts不一致")
        if set(closure_values["capability-buckets"]) != expected_capability_buckets:
            reporter.error("phase4-affected-capability-closure", phase4_trace_path, "capability-buckets与affected rendered artifacts不一致")
        scope = checkpoint.get("allowed-update-scope") if isinstance(checkpoint.get("allowed-update-scope"), dict) else {}
        scope_ga = {
            normalize_code(item)
            for item in scope.get("global-atom-ids", [])
            if isinstance(item, str)
        }
        if not expected_affected_ga.issubset(scope_ga):
            reporter.error("phase4-checkpoint-scope-ga", phase4_trace_path, "affected GA closure超出checkpoint allowed scope")
        scope_changes = {
            normalize_code(item)
            for item in (
                scope.get("initial-changes", [])
                if isinstance(scope.get("initial-changes"), list)
                else []
            )
            if isinstance(item, str)
        }
        scope_capabilities = {
            normalize_code(item)
            for item in (
                scope.get("initial-capabilities", [])
                if isinstance(scope.get("initial-capabilities"), list)
                else []
            )
            if isinstance(item, str)
        }
        if not expected_change_buckets.issubset(scope_changes):
            reporter.error("phase4-checkpoint-scope-change", phase4_trace_path, "affected Change bucket超出checkpoint allowed scope")
        if not expected_capability_buckets.issubset(scope_capabilities):
            reporter.error("phase4-checkpoint-scope-capability", phase4_trace_path, "affected Capability bucket超出checkpoint allowed scope")
    try:
        expected_outputs = render_evidence_collections(orchestrate_dir)
        expected_index = build_evidence_collection_index(orchestrate_dir, expected_outputs)
    except Exception as exc:  # noqa: BLE001
        reporter.error("phase4-assembly", index_path, f"无法从Phase 1–3重算evidence collections/index：{exc}")
        return
    if data != expected_index:
        reporter.error("phase4-derived-index-drift", index_path, "派生index与Phase 1–3 authority及机械生成的Markdown不一致")
    expected_path = rel(index_path, repo_root)
    if assembled.get("evidence-collection-index-path") != expected_path:
        reporter.error("phase4-trace-index-path", phase4_trace_path, f"collection index path应为{expected_path}")
    if index_path.exists() and assembled.get("evidence-collection-index-sha256") != sha256_file(index_path):
        reporter.error("phase4-trace-index-sha", phase4_trace_path, "collection index digest不一致")
    expected_summary = {
        "render-contract-version": RENDER_CONTRACT_VERSION,
        "rendered-files": len(expected_outputs),
        "global-atoms": len(expected_index.get("rows", [])),
    }
    if assembled.get("renderer-result-summary") != expected_summary:
        reporter.error("phase4-renderer-summary", phase4_trace_path, f"renderer-result-summary应为{expected_summary}")
    for output_path, expected_text in expected_outputs.items():
        if not output_path.exists():
            reporter.error("phase4-rendered-collection", output_path, "缺少机械生成的evidence collection Markdown")
        elif output_path.read_text(encoding="utf-8") != expected_text:
            reporter.error("phase4-rendered-collection-drift", output_path, "evidence collection与Phase 1–3 authority重渲染结果不一致")
    expected_paths = {path.resolve() for path in expected_outputs}
    actual_paths = {
        path.resolve()
        for pattern in ("index.md", "unassigned-and-gap.md", "by-input-change/*.md", "by-input-capability/*.md")
        for path in collection_root.glob(pattern)
    }
    for extra in sorted(actual_paths - expected_paths):
        reporter.error("phase4-rendered-collection-extra", extra, "存在不属于当前initial framework的stale evidence collection")


def validate_mapping_mirror(orchestrate_dir: Path, reporter: IssueReporter) -> None:
    json_path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
    md_path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.md"
    if not json_path.exists():
        return
    validate_rendered_markdown(
        orchestrate_dir,
        json_path,
        md_path,
        render_atom_plan_mapping,
        reporter,
        "phase5-atom-plan-mapping",
    )


def _phase1_change_order(orchestrate_dir: Path) -> List[str]:
    path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return [
        normalize_code(match.group(1))
        for match in re.finditer(r"(?m)^- Change 名称[：:]\s*(.+?)\s*$", text)
    ]


def _phase1_overlay(orchestrate_dir: Path) -> Set[tuple[str, str]]:
    path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    return {
        (normalize_code(cell(row, "Change")), normalize_code(cell(row, "Candidate Capability")))
        for row in table_rows(path, ["Change", "Candidate Capability", "Roadmap Role", "Direct Behavior Delta Hypothesis"])
        if normalize_code(cell(row, "Change")) and normalize_code(cell(row, "Candidate Capability"))
    }


def _semantic_text(value: object) -> str:
    return squash(normalize_code(value)).strip("。.;；")


def _phase1_capability_semantics(orchestrate_dir: Path) -> Dict[str, tuple[str, str, str, str]]:
    path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    return {
        normalize_code(cell(row, "Candidate Capability")): tuple(
            _semantic_text(cell(row, field)) for field in ("Purpose", "Owns", "Excludes", "Boundary Rationale")
        )
        for row in table_rows(path, ["Candidate Capability", "Purpose", "Owns", "Excludes", "Boundary Rationale"])
        if normalize_code(cell(row, "Candidate Capability"))
    }


def _phase1_change_semantics(orchestrate_dir: Path) -> Dict[str, tuple[str, ...]]:
    path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    patterns = (
        r"^- 单一 intent[：:]\s*(.*)$",
        r"^- source-backed outcome[：:]\s*(.*)$",
        r"^- 范围内[：:]\s*(.*)$",
        r"^- 范围外[：:]\s*(.*)$",
        r"^\s+- trigger/context[：:]\s*(.*)$",
        r"^\s+- normative behavior[：:]\s*(.*)$",
        r"^\s+- observable outcome / invariant[：:]\s*(.*)$",
        r"^\s+- important exception / error semantics[：:]\s*(.*)$",
        r"^\s+- acceptance evidence[：:]\s*(.*)$",
        r"^- 硬依赖[：:]\s*(.*)$",
        r"^- 独立完成与归档[：:]\s*(.*)$",
        r"^- 拆分/合并判断[：:]\s*(.*)$",
    )
    result: Dict[str, tuple[str, ...]] = {}
    current = ""
    values: Dict[int, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines() if path.exists() else []:
        start = re.match(r"^- Change 名称[：:]\s*(.+?)\s*$", raw)
        if start:
            if current:
                result[current] = tuple(values.get(index, "") for index in range(len(patterns)))
            current = normalize_code(start.group(1))
            values = {}
            continue
        if not current:
            continue
        for index, pattern in enumerate(patterns):
            match = re.match(pattern, raw)
            if match:
                values[index] = _semantic_text(match.group(1))
                break
    if current:
        result[current] = tuple(values.get(index, "") for index in range(len(patterns)))
    return result


def _final_framework_semantics(
    final_changes: List[object],
    final_capabilities: List[object],
) -> tuple[Dict[str, tuple[str, ...]], Dict[str, tuple[str, str, str, str]]]:
    changes = {
        getattr(change, "slug", ""): tuple(
            _semantic_text(getattr(change, field, ""))
            for field in (
                "intent", "outcome", "scope_in", "scope_out", "trigger", "normative_behavior",
                "observable_outcome", "exception_semantics", "acceptance", "dependencies_raw",
                "archive_condition", "split_merge_judgment",
            )
        )
        for change in final_changes
    }
    capabilities = {
        getattr(capability, "slug", ""): tuple(
            _semantic_text(getattr(capability, field, "")) for field in ("purpose", "owns", "excludes", "rationale")
        )
        for capability in final_capabilities
    }
    return changes, capabilities


def _validate_phase5_refit(
    orchestrate_dir: Path,
    reporter: IssueReporter,
    final_changes: List[object] | None,
    final_capabilities: List[object] | None,
    final_overlay: Dict[tuple[str, str], str] | None,
) -> str:
    refit_path = orchestrate_dir / "phase-works/phase-5/framework-refit-trace.json"
    review_path = orchestrate_dir / "phase-works/phase-5/plan-refit-review.md"
    data = json_obj(refit_path, reporter, FRAMEWORK_REFIT_TRACE_SCHEMA)
    if not data:
        return ""
    status = normalize_code(data.get("status"))
    patch_history = data.get("patch-history")
    patch_lifecycle_blocked = (
        status == "blocked"
        and isinstance(patch_history, list)
        and len(patch_history) == 1
        and isinstance(patch_history[0], dict)
        and normalize_code(patch_history[0].get("status")) == "blocked"
    )
    try:
        validate_framework_refit(
            orchestrate_dir,
            data,
            final_changes,
            final_capabilities,
            final_overlay,
            verify_current_inputs=not patch_lifecycle_blocked,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        reporter.error("phase5-refit-contract", refit_path, str(exc))
    if isinstance(patch_history, list):
        checkpoint_path = _checkpoint_path(orchestrate_dir)
        try:
            checkpoint = read_json(checkpoint_path) if checkpoint_path.exists() else {}
        except Exception:  # noqa: BLE001
            checkpoint = {}
        patch_attempt = checkpoint.get("patch-attempt") if isinstance(checkpoint.get("patch-attempt"), dict) else {}
        for index, row in enumerate(patch_history):
            if not isinstance(row, dict):
                continue
            if row.get("request-id") != PATCH_REQUEST_ID:
                reporter.error("phase5-patch-history-request-id", refit_path, f"patch-history[{index}] request-id必须为{PATCH_REQUEST_ID}")
            fingerprint = row.get("finding-fingerprint")
            if not _is_sha256(fingerprint):
                reporter.error("phase5-patch-history-fingerprint", refit_path, f"patch-history[{index}] finding-fingerprint非法")
            elif fingerprint != patch_attempt.get("finding-fingerprint"):
                reporter.error("phase5-patch-history-fingerprint", refit_path, f"patch-history[{index}] fingerprint与checkpoint不一致")
    require_file(review_path, reporter, "phase5-review", "缺少由framework-refit-trace.json渲染的plan-refit-review.md")
    if review_path.exists():
        try:
            expected_review = render_framework_refit_review(orchestrate_dir, refit_path)
        except Exception as exc:  # noqa: BLE001
            reporter.error("phase5-review-render", refit_path, f"无法渲染plan-refit-review.md：{exc}")
        else:
            if review_path.read_text(encoding="utf-8") != expected_review:
                reporter.error("rendered-markdown-drift", review_path, "plan-refit-review.md与framework-refit-trace.json重渲染结果不一致")
    if final_changes is not None and final_capabilities is not None and final_overlay is not None:
        initial_changes, initial_capabilities = phase1_framework_ids(orchestrate_dir)
        capability_decisions = {
            normalize_code(row.get("input-capability")): normalize_code(row.get("decision"))
            for row in data.get("capability-reviews", []) if isinstance(row, dict)
        }
        change_decisions = {
            normalize_code(row.get("input-change")): normalize_code(row.get("decision"))
            for row in data.get("change-reviews", []) if isinstance(row, dict)
        }
        final_cap_ids = {getattr(item, "slug", "") for item in final_capabilities}
        initial_change_order = _phase1_change_order(orchestrate_dir)
        final_change_semantics, final_capability_semantics = _final_framework_semantics(final_changes, final_capabilities)
        same_framework = (
            initial_change_order == [getattr(item, "slug", "") for item in final_changes]
            and initial_capabilities == final_cap_ids
            and _phase1_overlay(orchestrate_dir) == set(final_overlay)
            and _phase1_change_semantics(orchestrate_dir) == final_change_semantics
            and _phase1_capability_semantics(orchestrate_dir) == final_capability_semantics
        )
        all_keep = all(value == "keep" for value in capability_decisions.values()) and all(value == "keep" for value in change_decisions.values())
        if status == "accepted" and (not same_framework or not all_keep):
            reporter.error("phase5-refit-status-consistency", refit_path, "accepted要求initial framework语义、集合、顺序、overlay不变且逐项decision为keep")
        if status == "adjusted" and same_framework:
            reporter.error("phase5-refit-status-consistency", refit_path, "adjusted要求至少一项source-backed framework调整")
    return status


def _validate_checkpoint_pending_existing_output_scope(
    orchestrate_dir: Path,
    checkpoint: Dict[str, object],
    refit: Dict[str, object],
    reporter: IssueReporter,
) -> None:
    """pending review不得静默改指向scope外既有provisional final ID。"""
    path = _checkpoint_path(orchestrate_dir)
    pending = checkpoint.get("pending-ids")
    scope = checkpoint.get("allowed-update-scope")
    provisional = checkpoint.get("provisional-framework")
    if not isinstance(pending, dict) or not isinstance(scope, dict) or not isinstance(provisional, dict):
        return
    specs = (
        (
            "change-reviews", "input-change", "final-changes",
            "change-lineage", "provisional-final-changes",
            "final-changes", "change-order",
            "phase5-checkpoint-existing-change-output-scope",
        ),
        (
            "capability-reviews", "input-capability", "final-capabilities",
            "capability-lineage", "provisional-final-capabilities",
            "final-capabilities", "capabilities",
            "phase5-checkpoint-existing-capability-output-scope",
        ),
    )
    for review_field, input_field, terminal_final_field, lineage_field, lineage_final_field, scope_field, provisional_ids_field, rule in specs:
        pending_inputs = {
            normalize_code(item) for item in pending.get(review_field, []) if isinstance(item, str)
        }
        scoped_finals = {
            normalize_code(item) for item in scope.get(scope_field, []) if isinstance(item, str)
        }
        provisional_ids = {
            normalize_code(item)
            for item in provisional.get(provisional_ids_field, [])
            if isinstance(item, str)
        }
        frozen_by_input = {
            normalize_code(row.get(input_field)): {
                normalize_code(item)
                for item in row.get(lineage_final_field, [])
                if isinstance(item, str)
            }
            for row in provisional.get(lineage_field, [])
            if isinstance(row, dict) and isinstance(row.get(lineage_final_field), list)
        }
        for row in refit.get(review_field, []):
            if not isinstance(row, dict):
                continue
            input_id = normalize_code(row.get(input_field))
            if input_id not in pending_inputs:
                continue
            terminal_existing = {
                normalize_code(item)
                for item in row.get(terminal_final_field, [])
                if isinstance(item, str) and normalize_code(item) in provisional_ids
            }
            added_existing = terminal_existing - frozen_by_input.get(input_id, set())
            unauthorized = sorted(added_existing - scoped_finals)
            if unauthorized:
                reporter.error(
                    rule,
                    path,
                    f"pending {review_field}/{input_id}新增scope外既有provisional final ID：{unauthorized}",
                )


def _validate_checkpoint_resume_preservation(
    orchestrate_dir: Path,
    checkpoint: Dict[str, object],
    refit: Dict[str, object],
    parsed_changes: List[object],
    parsed_capabilities: List[object],
    reporter: IssueReporter,
) -> None:
    path = _checkpoint_path(orchestrate_dir)
    completed = checkpoint.get("completed-rows")
    scope = checkpoint.get("allowed-update-scope")
    if not isinstance(completed, dict) or not isinstance(scope, dict):
        return
    mapping_path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
    try:
        mapping = read_json(mapping_path) if mapping_path.exists() else {}
    except Exception:  # noqa: BLE001
        mapping = {}
    final_rows_by_kind = {
        "capability-reviews": refit.get("capability-reviews"),
        "change-reviews": refit.get("change-reviews"),
        "unassigned-and-gap-reviews": refit.get("unassigned-and-gap-reviews"),
        "atom-plan-mappings": mapping.get("rows"),
    }
    allowed_keys = {
        "capability-reviews": {
            normalize_code(item) for item in scope.get("initial-capabilities", []) if isinstance(item, str)
        },
        "change-reviews": {
            normalize_code(item) for item in scope.get("initial-changes", []) if isinstance(item, str)
        },
        "unassigned-and-gap-reviews": {
            normalize_code(item) for item in scope.get("global-atom-ids", []) if isinstance(item, str)
        },
        "atom-plan-mappings": {
            normalize_code(item) for item in scope.get("global-atom-ids", []) if isinstance(item, str)
        },
    }
    for kind, key_field in CHECKPOINT_ROW_KEY_FIELDS.items():
        final_rows = final_rows_by_kind.get(kind)
        checkpoint_rows = completed.get(kind)
        if not isinstance(final_rows, list) or not isinstance(checkpoint_rows, list):
            continue
        final_by_key = {
            normalize_code(row.get(key_field)): row
            for row in final_rows
            if isinstance(row, dict) and normalize_code(row.get(key_field))
        }
        for row in checkpoint_rows:
            if not isinstance(row, dict):
                continue
            key = normalize_code(row.get(key_field))
            if key in allowed_keys[kind]:
                continue
            final_row = final_by_key.get(key)
            if final_row is None or canonical_json_sha256(final_row) != canonical_json_sha256(row):
                reporter.error(
                    "phase5-checkpoint-resume-row-drift",
                    path,
                    f"scope外completed row未逐项复用：{kind}/{key}",
                )

    provisional = checkpoint.get("provisional-framework")
    final_framework = refit.get("final-framework")
    if not isinstance(provisional, dict) or not isinstance(final_framework, dict):
        return
    scope_initial_changes = {
        normalize_code(item) for item in scope.get("initial-changes", []) if isinstance(item, str)
    }
    scope_final_changes = {
        normalize_code(item) for item in scope.get("final-changes", []) if isinstance(item, str)
    }
    scope_initial_capabilities = {
        normalize_code(item) for item in scope.get("initial-capabilities", []) if isinstance(item, str)
    }
    scope_final_capabilities = {
        normalize_code(item) for item in scope.get("final-capabilities", []) if isinstance(item, str)
    }
    provisional_structure = {
        "change-order": provisional.get("change-order"),
        "capabilities": provisional.get("capabilities"),
        "overlay": provisional.get("overlay"),
    }
    if not scope_final_changes and not scope_final_capabilities:
        if final_framework != provisional_structure:
            reporter.error("phase5-checkpoint-framework-drift", path, "scope未授权final framework变化")
    # initial scope只授权重新生成对应review row；final framework mutation必须显式列入final scope。
    mutable_changes = scope_final_changes
    mutable_capabilities = scope_final_capabilities
    provisional_changes = [normalize_code(item) for item in provisional.get("change-order", []) if isinstance(item, str)]
    final_change_ids = [normalize_code(item) for item in final_framework.get("change-order", []) if isinstance(item, str)]
    shared_changes = set(provisional_changes).intersection(final_change_ids)
    if [item for item in provisional_changes if item in shared_changes] != [
        item for item in final_change_ids if item in shared_changes
    ]:
        reporter.error("phase5-checkpoint-roadmap-reorder", path, "checkpoint resume禁止重排既有Change的相对顺序")
    if any(
        normalize_code(row.get("decision")) == "reorder"
        for row in refit.get("change-reviews", [])
        if isinstance(row, dict)
    ):
        reporter.error("phase5-checkpoint-roadmap-reorder", path, "checkpoint resume不允许reorder decision")
    if [item for item in provisional_changes if item not in mutable_changes] != [
        item for item in final_change_ids if item not in mutable_changes
    ]:
        reporter.error("phase5-checkpoint-framework-order-drift", path, "scope外Change identity或相对顺序发生变化")
    provisional_capabilities = [normalize_code(item) for item in provisional.get("capabilities", []) if isinstance(item, str)]
    final_capability_ids = [normalize_code(item) for item in final_framework.get("capabilities", []) if isinstance(item, str)]
    if [item for item in provisional_capabilities if item not in mutable_capabilities] != [
        item for item in final_capability_ids if item not in mutable_capabilities
    ]:
        reporter.error("phase5-checkpoint-framework-capability-drift", path, "scope外Capability集合发生变化")

    def preserved_overlay(framework: Dict[str, object]) -> List[Dict[str, object]]:
        rows = framework.get("overlay")
        return [
            row
            for row in rows if isinstance(rows, list) and isinstance(row, dict)
            if normalize_code(row.get("change")) not in mutable_changes
            or normalize_code(row.get("capability")) not in mutable_capabilities
        ] if isinstance(rows, list) else []

    if preserved_overlay(provisional) != preserved_overlay(final_framework):
        reporter.error(
            "phase5-checkpoint-framework-overlay-drift",
            path,
            "只有Change与Capability两个endpoint都在mutable closure内的overlay row才允许变化",
        )

    def preserved_dependency_edges(rows: object) -> List[Dict[str, str]]:
        return [
            row
            for row in rows if isinstance(rows, list) and isinstance(row, dict)
            if normalize_code(row.get("change")) not in mutable_changes
            or normalize_code(row.get("depends-on")) not in mutable_changes
        ] if isinstance(rows, list) else []

    final_dependency_edges = framework_dependency_edges(parsed_changes)
    if preserved_dependency_edges(provisional.get("dependency-edges")) != preserved_dependency_edges(final_dependency_edges):
        reporter.error(
            "phase5-checkpoint-framework-dependency-drift",
            path,
            "只有两个endpoint都在mutable Change closure内的dependency edge才允许变化",
        )

    actual_change_rows, actual_capability_rows = framework_semantic_digest_rows(
        parsed_changes,
        parsed_capabilities,
    )
    semantic_specs = (
        (
            provisional.get("change-semantic-digests"),
            actual_change_rows,
            "final-change",
            mutable_changes,
            "phase5-checkpoint-framework-change-semantic-drift",
            "Change",
        ),
        (
            provisional.get("capability-semantic-digests"),
            actual_capability_rows,
            "final-capability",
            mutable_capabilities,
            "phase5-checkpoint-framework-capability-semantic-drift",
            "Capability",
        ),
    )
    for frozen_rows, actual_rows, key_field, mutable_ids, rule, label in semantic_specs:
        frozen_map = {
            normalize_code(row.get(key_field)): normalize_code(row.get("sha256"))
            for row in (frozen_rows if isinstance(frozen_rows, list) else [])
            if isinstance(row, dict)
        }
        actual_map = {
            normalize_code(row.get(key_field)): normalize_code(row.get("sha256"))
            for row in actual_rows
            if isinstance(row, dict)
        }
        for row_id, digest in frozen_map.items():
            if row_id in mutable_ids:
                continue
            if actual_map.get(row_id) != digest:
                reporter.error(
                    rule,
                    path,
                    f"scope外{label}语义row未原样复用：{row_id}",
                )


def _validate_phase5_derived_outputs(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
    changes: List[object],
    capabilities: List[object],
    overlay: Dict[tuple[str, str], str],
) -> None:
    work = orchestrate_dir / "phase-works/phase-5"
    mapping_path = work / "atom-plan-mapping.json"
    mapping_data = json_obj(mapping_path, reporter, ATOM_PLAN_MAPPING_SCHEMA)
    exact_fields(
        mapping_data,
        {"trace-schema", "trace-contract-version", "artifact-path", "rows"},
        mapping_path,
        reporter,
        "phase5-mapping-top-fields",
        "mapping",
    )
    expected_artifact_path = rel(mapping_path.with_suffix(".md"), repo_root)
    if mapping_data.get("artifact-path") != expected_artifact_path:
        reporter.error("phase5-mapping-artifact-path", mapping_path, f"artifact-path应为{expected_artifact_path}")
    try:
        evidence = load_phase5_evidence(orchestrate_dir)
        mapping = load_phase5_mapping(mapping_path)
        validate_phase5_mapping(
            evidence,
            mapping,
            changes,
            capabilities,
            overlay,
            repo_root=repo_root,
        )
        refit = load_framework_refit(work / "framework-refit-trace.json")
        validate_gap_framework_impacts(orchestrate_dir, refit, mapping)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        reporter.error("phase5-mapping-contract", mapping_path, str(exc))
        return

    validate_mapping_mirror(orchestrate_dir, reporter)
    baseline_path = work / "capability-baseline-reconciliation.json"
    baseline = json_obj(baseline_path, reporter, CAPABILITY_BASELINE_SCHEMA)
    expected_baseline = build_phase5_baseline(repo_root, changes, capabilities, mapping)
    if baseline != expected_baseline:
        reporter.error("phase5-baseline-drift", baseline_path, "baseline与final plan、mapping或repository specs不一致")
    if baseline_path.exists():
        validate_rendered_markdown(
            orchestrate_dir,
            baseline_path,
            baseline_path.with_suffix(".md"),
            render_capability_baseline,
            reporter,
            "phase5-capability-baseline",
        )

    packet_index_path = work / "final-packet-index.json"
    packet_index = json_obj(packet_index_path, reporter, FINAL_PACKET_INDEX_SCHEMA)
    exact_fields(
        packet_index,
        {"trace-schema", "trace-contract-version", "packets"},
        packet_index_path,
        reporter,
        "phase5-packet-index-fields",
        "final packet index",
    )
    packets = packet_index.get("packets")
    if not isinstance(packets, list):
        reporter.error("phase5-packet-index", packet_index_path, "packets必须是array")
        return
    by_change = {normalize_code(row.get("change")): row for row in packets if isinstance(row, dict)}
    change_ids = [getattr(change, "slug", "") for change in changes]
    if [normalize_code(row.get("change")) for row in packets if isinstance(row, dict)] != change_ids:
        reporter.error("phase5-packet-order", packet_index_path, "packet顺序必须与final roadmap一致且每个Change恰好一行")
    for change in changes:
        slug = getattr(change, "slug", "")
        row = by_change.get(slug)
        if not isinstance(row, dict):
            reporter.error("phase5-packet-missing", packet_index_path, f"缺少final packet：{slug}")
            continue
        exact_fields(
            row,
            {"change", "change-kind", "packet-path", "packet-digest", "direct-atom-ids", "owner-scoped-non-direct-atom-ids", "capability-view-paths"},
            packet_index_path,
            reporter,
            "phase5-packet-fields",
            slug,
        )
        if row.get("change-kind") != "business":
            reporter.error("phase5-packet-kind", packet_index_path, f"{slug} change-kind必须是business")
        expected_direct = sorted(ga for ga, item in mapping.items() if item.owner_change == slug and item.relation == "direct")
        expected_non_direct = sorted(ga for ga, item in mapping.items() if item.owner_change == slug and item.relation != "direct")
        if row.get("direct-atom-ids") != expected_direct or row.get("owner-scoped-non-direct-atom-ids") != expected_non_direct:
            reporter.error("phase5-packet-ga-drift", packet_index_path, f"{slug} packet GA集合与mapping不一致")
        expected_packet = orchestrate_dir / "change-capability-anchors" / slug / f"{slug}.md"
        if row.get("packet-path") != rel(expected_packet, repo_root):
            reporter.error("phase5-packet-path", packet_index_path, f"{slug} packet-path非法")
        if not expected_packet.exists():
            reporter.error("phase5-packet-missing", expected_packet, f"缺少{slug} packet")
        else:
            if expected_packet.read_text(encoding="utf-8") != render_packet(change, evidence, mapping):
                reporter.error("phase5-packet-drift", expected_packet, "packet与frozen source-fact、final plan或mapping不一致")
            if row.get("packet-digest") != sha256_file(expected_packet):
                reporter.error("phase5-packet-digest", packet_index_path, f"{slug} packet digest不一致")
        expected_caps = sorted({item.target_capability for item in mapping.values() if item.owner_change == slug and item.relation == "direct" and item.projection in SPEC_PROJECTIONS})
        expected_paths = [rel(expected_packet.parent / "capability-anchors" / f"{cap}.md", repo_root) for cap in expected_caps]
        if row.get("capability-view-paths") != expected_paths:
            reporter.error("phase5-capability-view-index", packet_index_path, f"{slug} Capability view index与mapping不一致")
        for cap, cap_rel in zip(expected_caps, expected_paths):
            cap_path = repo_root / cap_rel
            if not cap_path.exists():
                reporter.error("phase5-capability-view-missing", cap_path, f"缺少{slug}/{cap} Capability view")
            elif cap_path.read_text(encoding="utf-8") != render_capability_view(slug, cap, evidence, mapping):
                reporter.error("phase5-capability-view-drift", cap_path, "Capability view与frozen source-fact或mapping不一致")
        cap_dir = expected_packet.parent / "capability-anchors"
        actual_cap_paths = {path.resolve() for path in cap_dir.glob("*.md")} if cap_dir.exists() else set()
        expected_cap_paths = {(repo_root / path).resolve() for path in expected_paths}
        for stale in sorted(actual_cap_paths - expected_cap_paths):
            reporter.error("phase5-capability-view-extra", stale, f"{slug}存在stale Capability view")
    anchors = orchestrate_dir / "change-capability-anchors"
    anchor_index = anchors / "index.md"
    if anchor_index.exists():
        expected_anchor_index = render_anchor_index(changes, mapping, repo_root, anchors)
        if anchor_index.read_text(encoding="utf-8") != expected_anchor_index:
            reporter.error("phase5-anchor-index-drift", anchor_index, "anchor index与final plan、mapping及Capability views不一致")
    expected_change_dirs = {getattr(change, "slug", "") for change in changes}
    if anchors.exists():
        for child in anchors.iterdir():
            if child.is_dir() and child.name not in expected_change_dirs:
                reporter.error("phase5-stale-change-anchor", child, "存在不属于final roadmap的stale Change anchor")


def validate_phase_5(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter, complete: bool = False) -> None:
    work = orchestrate_dir / "phase-works/phase-5"
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    trace = json_obj(trace_path, reporter, PHASE_TRACE_SCHEMAS["phase-5"])
    trace_status = validate_trace_status(trace, trace_path, reporter, "phase-5", "phase5-status") if trace else ""
    require_file(work / "phase-5-agent-report.md", reporter, "phase5-interface-artifact", "缺少Phase 5 agent报告")
    legacy_names = [
        "phase5-refit.config.json", "input-change-plan.md", "source-window-refit-trace.md",
        "change-plan-adjustments.md", "capability-progression-review.md", "change-complexity-review.md",
        "plan-refit-decision-log.md", "alignment-final-report.md", "change-capability-human-plan.md",
    ]
    for name in legacy_names:
        path = work / name
        if path.exists():
            reporter.error("phase5-legacy-artifact", path, "旧Phase 5 artifact已废弃，必须清理")

    final_plan_path = work / "change-plan.md"
    final_changes: List[object] | None = None
    final_capabilities: List[object] | None = None
    final_overlay: Dict[tuple[str, str], str] | None = None
    if final_plan_path.exists():
        try:
            final_changes, final_capabilities, final_overlay = parse_final_plan(final_plan_path)
        except (OSError, ValueError) as exc:
            reporter.error("phase5-final-plan-contract", final_plan_path, str(exc))
    refit_status = _validate_phase5_refit(orchestrate_dir, reporter, final_changes, final_capabilities, final_overlay)
    if trace_status and refit_status and trace_status != refit_status:
        reporter.error("phase5-status-drift", trace_path, f"phase trace status {trace_status}与framework refit status {refit_status}不一致")

    if trace_status in NON_FINAL_PHASE5_STATUSES:
        refit_path = work / "framework-refit-trace.json"
        try:
            refit_data = read_json(refit_path) if refit_path.exists() else {}
        except Exception:  # noqa: BLE001
            refit_data = {}
        refit_history = refit_data.get("patch-history") if isinstance(refit_data.get("patch-history"), list) else []
        patch_lifecycle = trace_status == "needs-targeted-evidence-patch" or bool(refit_history)
        if patch_lifecycle:
            exact_fields(
                trace,
                {
                    "trace-schema", "trace-contract-version", "status", "execution-mode",
                    "framework-refit-trace-path", "framework-refit-trace-sha256",
                    "plan-refit-review-path", "plan-refit-review-sha256",
                    "evidence-patch-request-path", "evidence-patch-request-sha256",
                    "phase-5-checkpoint-path", "phase-5-checkpoint-sha256", "patch-history", "issues",
                },
                trace_path,
                reporter,
                "phase5-trace-fields",
                "patch lifecycle phase-5 trace",
            )
            _validate_phase5_patch_commit_marker(orchestrate_dir, repo_root, reporter)
            expected_execution_mode = "initial" if trace_status == "needs-targeted-evidence-patch" else "checkpoint-resume"
            if normalize_code(trace.get("execution-mode")) != expected_execution_mode:
                reporter.error("phase5-execution-mode", trace_path, f"{trace_status}要求execution-mode={expected_execution_mode}")
            if trace.get("patch-history") != refit_history:
                reporter.error("phase5-trace-patch-history", trace_path, "trace patch-history必须与framework refit逐字一致")
            expected_history_status = "requested" if trace_status == "needs-targeted-evidence-patch" else "blocked"
            history_statuses = [normalize_code(row.get("status")) for row in refit_history if isinstance(row, dict)]
            if history_statuses != [expected_history_status]:
                reporter.error("phase5-trace-patch-history-status", trace_path, f"patch-history必须恰好一条{expected_history_status}")
            request_path = _patch_request_path(orchestrate_dir)
            checkpoint_path = _checkpoint_path(orchestrate_dir)
            trace_patch_specs = (
                ("evidence-patch-request", request_path),
                ("phase-5-checkpoint", checkpoint_path),
            )
            for prefix, artifact_path in trace_patch_specs:
                if trace.get(f"{prefix}-path") != rel(artifact_path, repo_root):
                    reporter.error("phase5-trace-patch-path", trace_path, f"{prefix}-path与canonical path不一致")
                if artifact_path.exists() and trace.get(f"{prefix}-sha256") != sha256_file(artifact_path):
                    reporter.error("phase5-trace-patch-sha", trace_path, f"{prefix} digest与当前artifact不一致")
            if trace_status == "blocked":
                _validate_aborted_patch_request_snapshot(orchestrate_dir, reporter)
                _validate_checkpoint(
                    orchestrate_dir,
                    repo_root,
                    reporter,
                    verify_current_surfaces=False,
                )
            else:
                _validate_patch_issuance_base_modes(orchestrate_dir, reporter)
                _validate_patch_request(orchestrate_dir, repo_root, reporter)
                _validate_checkpoint(orchestrate_dir, repo_root, reporter)
        else:
            exact_fields(
                trace,
                {
                    "trace-schema", "trace-contract-version", "status",
                    "framework-refit-trace-path", "framework-refit-trace-sha256",
                    "plan-refit-review-path", "plan-refit-review-sha256", "issues",
                },
                trace_path,
                reporter,
                "phase5-trace-fields",
                "initial blocked phase-5 trace",
            )
        review_path = work / "plan-refit-review.md"
        expected_refit_path = rel(refit_path, repo_root)
        if trace.get("framework-refit-trace-path") != expected_refit_path:
            reporter.error("phase5-trace-path", trace_path, f"framework-refit-trace-path应为{expected_refit_path}")
        if refit_path.exists() and trace.get("framework-refit-trace-sha256") != sha256_file(refit_path):
            reporter.error("phase5-trace-sha", trace_path, "framework-refit-trace digest与trace不一致")
        expected_review_path = rel(review_path, repo_root)
        if trace.get("plan-refit-review-path") != expected_review_path:
            reporter.error("phase5-trace-path", trace_path, f"plan-refit-review-path应为{expected_review_path}")
        if review_path.exists() and trace.get("plan-refit-review-sha256") != sha256_file(review_path):
            reporter.error("phase5-trace-sha", trace_path, "plan-refit-review digest与trace不一致")
        if not isinstance(trace.get("issues"), list) or not trace.get("issues"):
            reporter.error("phase5-trace-issues", trace_path, f"{trace_status}状态要求非空issues[]")
        if refit_path.exists():
            if trace.get("issues") != refit_data.get("issues"):
                reporter.error("phase5-trace-issues", trace_path, "nonterminal trace issues必须与framework refit issues一致")
        terminal_paths = [
            final_plan_path,
            work / "atom-plan-mapping.json",
            work / "atom-plan-mapping.md",
            work / "capability-baseline-reconciliation.json",
            work / "capability-baseline-reconciliation.md",
            work / "final-packet-index.json",
            orchestrate_dir / "change-plan.md",
            orchestrate_dir / "change-capability-anchors/index.md",
        ]
        for path in terminal_paths:
            if path.exists():
                reporter.error("phase5-nonfinal-terminal-artifact", path, f"{trace_status}状态不得保留terminal artifact")
        anchors_dir = orchestrate_dir / "change-capability-anchors"
        if anchors_dir.exists():
            for child in anchors_dir.iterdir():
                if child.is_dir():
                    reporter.error("phase5-nonfinal-terminal-artifact", child, f"{trace_status}状态不得保留final Change packet或Capability view")
        if complete:
            reporter.error("phase5-complete-status", trace_path, f"--complete要求accepted/adjusted，实际为{trace_status}")
        return
    if trace_status not in FINAL_PHASE5_STATUSES:
        if complete:
            reporter.error("phase5-complete-status", trace_path, f"--complete要求accepted/adjusted，实际为{trace_status or 'missing'}")
        return

    exact_fields(
        trace,
        {
            "trace-schema", "trace-contract-version", "status", "execution-mode", "patch-history",
            "evidence-patch-request-path", "evidence-patch-request-sha256",
            "phase-5-checkpoint-path", "phase-5-checkpoint-sha256",
            "final-change-plan-path", "final-change-plan-sha256",
            "framework-refit-trace-path", "framework-refit-trace-sha256",
            "plan-refit-review-path", "plan-refit-review-sha256",
            "atom-plan-mapping-path", "atom-plan-mapping-sha256",
            "capability-baseline-reconciliation-path", "capability-baseline-reconciliation-sha256",
            "final-packet-index-path", "final-packet-index-sha256",
        },
        trace_path,
        reporter,
        "phase5-trace-fields",
        "phase-5 trace",
    )
    try:
        terminal_refit = read_json(work / "framework-refit-trace.json")
    except Exception:  # noqa: BLE001
        terminal_refit = {}
    refit_history = terminal_refit.get("patch-history") if isinstance(terminal_refit.get("patch-history"), list) else []
    if trace.get("patch-history") != refit_history:
        reporter.error("phase5-trace-patch-history", trace_path, "terminal trace patch-history必须与framework refit逐字一致")
    execution_mode = normalize_code(trace.get("execution-mode"))
    if refit_history:
        history_statuses = [normalize_code(row.get("status")) for row in refit_history if isinstance(row, dict)]
        if execution_mode != "checkpoint-resume" or history_statuses != ["closed"]:
            reporter.error("phase5-terminal-patch-history", trace_path, "patch terminal要求checkpoint-resume及恰一closed history")
        checkpoint = _validate_checkpoint(orchestrate_dir, repo_root, reporter)
        _validate_patch_request(orchestrate_dir, repo_root, reporter)
        request_path = _patch_request_path(orchestrate_dir)
        checkpoint_path = _checkpoint_path(orchestrate_dir)
        terminal_patch_specs = (
            ("evidence-patch-request", request_path),
            ("phase-5-checkpoint", checkpoint_path),
        )
        for prefix, artifact_path in terminal_patch_specs:
            if trace.get(f"{prefix}-path") != rel(artifact_path, repo_root):
                reporter.error("phase5-terminal-patch-path", trace_path, f"{prefix}-path与canonical path不一致")
            if artifact_path.exists() and trace.get(f"{prefix}-sha256") != sha256_file(artifact_path):
                reporter.error("phase5-terminal-patch-sha", trace_path, f"{prefix} digest与immutable artifact不一致")
        pending = checkpoint.get("pending-ids") if isinstance(checkpoint.get("pending-ids"), dict) else {}
        try:
            terminal_mapping = read_json(work / "atom-plan-mapping.json")
        except Exception:  # noqa: BLE001
            terminal_mapping = {}
        mapped_ga_ids = {
            normalize_code(row.get("global-atom-id"))
            for row in terminal_mapping.get("rows", [])
            if isinstance(row, dict)
        }
        pending_ga_ids = {
            normalize_code(item)
            for item in pending.get("atom-plan-mappings", [])
            if isinstance(item, str)
        }
        if not pending_ga_ids.issubset(mapped_ga_ids):
            reporter.error("phase5-checkpoint-pending-ga", _checkpoint_path(orchestrate_dir), "checkpoint pending GA未全部进入terminal mapping")
        reviewed_unassigned = {
            normalize_code(row.get("global-atom-id"))
            for row in terminal_refit.get("unassigned-and-gap-reviews", [])
            if isinstance(row, dict)
        }
        pending_unassigned = {
            normalize_code(item)
            for item in pending.get("unassigned-and-gap-reviews", [])
            if isinstance(item, str)
        }
        if not pending_unassigned.issubset(reviewed_unassigned):
            reporter.error(
                "phase5-checkpoint-pending-unassigned",
                _checkpoint_path(orchestrate_dir),
                "checkpoint pending unassigned/gap GA未全部进入terminal review",
            )
        final_framework = terminal_refit.get("final-framework") if isinstance(terminal_refit.get("final-framework"), dict) else {}
        final_change_ids = {
            normalize_code(item) for item in final_framework.get("change-order", []) if isinstance(item, str)
        }
        reviewed_changes = {
            normalize_code(row.get("input-change"))
            for row in terminal_refit.get("change-reviews", [])
            if isinstance(row, dict)
        }
        pending_changes = {
            normalize_code(item) for item in pending.get("change-reviews", []) if isinstance(item, str)
        }
        if not pending_changes.issubset(final_change_ids | reviewed_changes):
            reporter.error("phase5-checkpoint-pending-change", _checkpoint_path(orchestrate_dir), "checkpoint pending Change未在terminal framework/review中裁决")
        final_capability_ids = {
            normalize_code(item) for item in final_framework.get("capabilities", []) if isinstance(item, str)
        }
        reviewed_capabilities = {
            normalize_code(row.get("input-capability"))
            for row in terminal_refit.get("capability-reviews", [])
            if isinstance(row, dict)
        }
        pending_capabilities = {
            normalize_code(item) for item in pending.get("capability-reviews", []) if isinstance(item, str)
        }
        if not pending_capabilities.issubset(final_capability_ids | reviewed_capabilities):
            reporter.error("phase5-checkpoint-pending-capability", _checkpoint_path(orchestrate_dir), "checkpoint pending Capability未在terminal framework/review中裁决")
        scope = checkpoint.get("allowed-update-scope") if isinstance(checkpoint.get("allowed-update-scope"), dict) else {}
        scoped_terminal_changes = {
            normalize_code(item)
            for row in terminal_refit.get("change-reviews", [])
            if isinstance(row, dict) and normalize_code(row.get("input-change")) in pending_changes
            for item in row.get("final-changes", [])
            if isinstance(item, str)
        }
        scoped_terminal_capabilities = {
            normalize_code(item)
            for row in terminal_refit.get("capability-reviews", [])
            if isinstance(row, dict) and normalize_code(row.get("input-capability")) in pending_capabilities
            for item in row.get("final-capabilities", [])
            if isinstance(item, str)
        }
        scoped_mapping_changes = {
            normalize_code(row.get("final-owner-change"))
            for row in terminal_mapping.get("rows", [])
            if isinstance(row, dict)
            and normalize_code(row.get("global-atom-id")) in pending_ga_ids
            and normalize_code(row.get("final-owner-change")) not in {"", "none", "null"}
        }
        scoped_mapping_capabilities = {
            normalize_code(row.get("final-target-capability"))
            for row in terminal_mapping.get("rows", [])
            if isinstance(row, dict)
            and normalize_code(row.get("global-atom-id")) in pending_ga_ids
            and normalize_code(row.get("final-target-capability")) not in {"", "none", "null"}
        }
        expected_scoped_changes = {
            normalize_code(item) for item in scope.get("final-changes", []) if isinstance(item, str)
        }
        expected_scoped_capabilities = {
            normalize_code(item) for item in scope.get("final-capabilities", []) if isinstance(item, str)
        }
        provisional_framework = (
            checkpoint.get("provisional-framework")
            if isinstance(checkpoint.get("provisional-framework"), dict)
            else {}
        )
        provisional_change_ids = {
            normalize_code(item)
            for item in provisional_framework.get("change-order", [])
            if isinstance(item, str)
        }
        provisional_capability_ids = {
            normalize_code(item)
            for item in provisional_framework.get("capabilities", [])
            if isinstance(item, str)
        }
        actual_new_changes = (scoped_terminal_changes | scoped_mapping_changes) - provisional_change_ids
        actual_new_capabilities = (
            scoped_terminal_capabilities | scoped_mapping_capabilities
        ) - provisional_capability_ids
        expected_new_changes = expected_scoped_changes - provisional_change_ids
        expected_new_capabilities = expected_scoped_capabilities - provisional_capability_ids
        if actual_new_changes != expected_new_changes:
            reporter.error(
                "phase5-checkpoint-final-change-scope",
                _checkpoint_path(orchestrate_dir),
                "scope中新Change必须且只能由pending Change review或mapping row实际产生或引用；"
                f"expected-new={sorted(expected_new_changes)} actual-new={sorted(actual_new_changes)}",
            )
        if actual_new_capabilities != expected_new_capabilities:
            reporter.error(
                "phase5-checkpoint-final-capability-scope",
                _checkpoint_path(orchestrate_dir),
                "scope中新Capability必须且只能由pending Capability review或mapping row实际产生或引用；"
                f"expected-new={sorted(expected_new_capabilities)} actual-new={sorted(actual_new_capabilities)}",
            )
        _validate_checkpoint_pending_existing_output_scope(
            orchestrate_dir,
            checkpoint,
            terminal_refit,
            reporter,
        )
        _validate_checkpoint_resume_preservation(
            orchestrate_dir,
            checkpoint,
            terminal_refit,
            final_changes or [],
            final_capabilities or [],
            reporter,
        )
    else:
        if execution_mode != "initial":
            reporter.error("phase5-terminal-execution-mode", trace_path, "normal terminal要求execution-mode=initial且patch-history为空")
        for field in (
            "evidence-patch-request-path", "evidence-patch-request-sha256",
            "phase-5-checkpoint-path", "phase-5-checkpoint-sha256",
        ):
            if trace.get(field) is not None:
                reporter.error("phase5-terminal-stale-patch-ref", trace_path, f"normal terminal要求{field}=null")

    required = [
        final_plan_path,
        work / "framework-refit-trace.json",
        work / "plan-refit-review.md",
        work / "atom-plan-mapping.json",
        work / "atom-plan-mapping.md",
        work / "capability-baseline-reconciliation.json",
        work / "capability-baseline-reconciliation.md",
        work / "final-packet-index.json",
        orchestrate_dir / "change-plan.md",
        orchestrate_dir / "change-capability-anchors/index.md",
    ]
    for path in required:
        require_file(path, reporter, "phase5-interface-artifact", f"缺少Phase 5 terminal artifact：{path.name}")
    require_same_file(final_plan_path, orchestrate_dir / "change-plan.md", reporter, "phase5-root-plan-drift", "根change-plan.md必须与Phase 5 final plan逐字节一致")
    if final_changes is not None and final_capabilities is not None and final_overlay is not None:
        _validate_phase5_derived_outputs(orchestrate_dir, repo_root, reporter, final_changes, final_capabilities, final_overlay)

    trace_specs = [
        ("final-change-plan", final_plan_path),
        ("framework-refit-trace", work / "framework-refit-trace.json"),
        ("plan-refit-review", work / "plan-refit-review.md"),
        ("atom-plan-mapping", work / "atom-plan-mapping.json"),
        ("capability-baseline-reconciliation", work / "capability-baseline-reconciliation.json"),
        ("final-packet-index", work / "final-packet-index.json"),
    ]
    for prefix, path in trace_specs:
        expected_path = rel(path, repo_root)
        if trace.get(f"{prefix}-path") != expected_path:
            reporter.error("phase5-trace-path", trace_path, f"{prefix}-path应为{expected_path}")
        if path.exists() and trace.get(f"{prefix}-sha256") != sha256_file(path):
            reporter.error("phase5-trace-sha", trace_path, f"{prefix} digest与trace不一致")


def validate(orchestrate_dir: Path, repo_root: Path, phase: str, complete: bool) -> Dict[str, object]:
    reporter = IssueReporter()
    if not orchestrate_dir.exists():
        reporter.error("orchestrate-dir", orchestrate_dir, "orchestrate 目录不存在")
        return reporter.result()

    validate_manifest(orchestrate_dir, repo_root, reporter, complete=complete)
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

    return reporter.result()


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 source-aligned orchestrate trace sidecar。")
    parser.add_argument("--orchestrate-dir", default="openspec/orchestrate", type=Path, help="orchestrate 目录路径")
    parser.add_argument("--workspace-root", default=".", type=Path, help="工作区根目录路径")
    parser.add_argument("--phase", choices=["phase-1", "phase-2", "phase-3", "phase-4", "phase-5", "all"], default="all", help="要校验的 Phase")
    parser.add_argument("--complete", action="store_true", help="启用完整终态校验")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    parser.add_argument("--strict-warnings", action="store_true", help="将 warning 视为失败")
    args = parser.parse_args()

    result = validate(args.orchestrate_dir, args.workspace_root, args.phase, args.complete)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} 错误数={result['error-count']} 警告数={result['warning-count']}")
        for issue in result["issues"]:  # type: ignore[index]
            print(f"{issue['severity']}: {issue['rule_id']}: {issue['file']}: {issue['message']}")

    has_errors = int(result["error-count"]) > 0
    has_warnings = int(result["warning-count"]) > 0
    return 1 if has_errors or (args.strict_warnings and has_warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
