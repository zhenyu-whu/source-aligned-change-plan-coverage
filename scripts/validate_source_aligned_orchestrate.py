#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 source-aligned orchestrate JSON trace sidecar。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from source_aligned_trace_lib import (
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_BASELINE_SCHEMA,
    DIRECT_PROJECTIONS,
    FINAL_PACKET_INDEX_SCHEMA,
    GLOBAL_ATOM_ID_RE,
    GLOBAL_ATOM_INDEX_SCHEMA,
    KEBAB_CASE_RE,
    MANIFEST_SCHEMA,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    SOURCE_WINDOW_INDEX_SCHEMA,
    TRACE_CONTRACT_VERSION,
    IssueReporter,
    cell,
    extract_ga_ids,
    line_range_label,
    line_ranges_label,
    merge_line_ranges,
    parse_line_ranges,
    range_covered_by,
    read_json,
    sha256_file,
    sha256_text,
    source_atom_file_name,
    source_line_count,
    source_text_for_ranges,
    table_rows,
    uncovered_line_ranges,
    validate_kebab_keys,
    normalize_code,
    squash,
)
from render_source_aligned_orchestrate import (
    render_atom_plan_mapping,
    render_capability_baseline,
    render_global_index,
    render_phase2_source_atoms,
    render_coverage_review,
)

NO_OWNER_VALUES = {"", "None", "none", "null", "NULL"}
FOUNDATION_CHANGE_KIND = "foundation"
BUSINESS_CHANGE_KIND = "business"
EXECUTABLE_OWNER_TYPE = "executable-change"
FOUNDATION_CAPABILITY = "runtime-substrate-foundation"
FOUNDATION_IMPACT = "foundation-substrate"
SPEC_PROJECTIONS = {"spec-requirement", "spec-guard"}
CHANGE_ONLY_PROJECTIONS = {"design-obligation", "verification-obligation"}
NON_TERMINAL_CAPABILITY_IMPACTS = {"new", "modified", "none", "unresolved"}
TERMINAL_CAPABILITY_IMPACTS = {"new", "modified", "none", FOUNDATION_IMPACT}
BUSINESS_CAPABILITY_IMPACTS = {"new", "modified"}
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
PHASE3_DISPOSITIONS = {"missing-obligation", "safe-non-obligation", "requires-reextract", "blocked"}
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
PHASE_NAMES = ("phase-1", "phase-2", "phase-3", "phase-4", "phase-5")
FINAL_PHASE5_STATUSES = {"accepted", "adjusted"}
NON_FINAL_PHASE4_STATUSES = {"needs-coverage-recheck", "blocked"}
NON_FINAL_PHASE5_STATUSES = {"needs-coverage-recheck", "blocked"}
PHASE_ALLOWED_TRACE_STATUSES = {
    "phase-1": {"initial-plan-written"},
    "phase-2": {"source-atoms-written"},
    "phase-3": {"coverage-complete", "needs-extraction-recheck", "blocked"},
    "phase-4": {"grounded", *NON_FINAL_PHASE4_STATUSES},
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


def is_executable_direct_row(row: Dict[str, object]) -> bool:
    return row.get("final-relation") == "direct"


def is_capability_view_row(row: Dict[str, object]) -> bool:
    return is_executable_direct_row(row) and row.get("final-capability-impact") in {
        *BUSINESS_CAPABILITY_IMPACTS,
        FOUNDATION_IMPACT,
    }


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


def markdown_capability_list(value: object) -> List[str]:
    text = str(value or "").strip()
    code_values = [normalize_code(item) for item in re.findall(r"`([^`]+)`", text)]
    raw_values = code_values or [normalize_code(item) for item in re.split(r"\s*[,;]\s*", text)]
    return [value for value in raw_values if value and value.lower() not in {"none", "none/change-only"}]


def markdown_target(value: object) -> str:
    target = normalize_code(value)
    return "none" if target.lower() in {"none", "none/change-only"} else target


def validate_related_capabilities(
    row: Dict[str, object],
    field: str,
    target: str,
    path: Path,
    reporter: IssueReporter,
    context: str,
) -> List[str]:
    raw = row.get(field)
    if not isinstance(raw, list):
        reporter.error("capability-related-array", path, f"{context} 的 {field} 必须是 array")
        return []
    values = [normalize_code(item) for item in raw]
    if len(values) != len(set(values)):
        reporter.error("capability-related-duplicate", path, f"{context} 的 {field} 包含重复项")
    for value in values:
        if not KEBAB_CASE_RE.match(value):
            reporter.error("capability-related-format", path, f"{context} 的 related capability 不是 kebab-case：{value}")
        elif value in RESERVED_CAPABILITY_MARKERS:
            reporter.error("capability-related-reserved", path, f"{context} 的 related capability 使用了保留标记：{value}")
        if value == target:
            reporter.error("capability-related-target", path, f"{context} 的 related capability 不得等于 target：{value}")
    return values


def validate_capability_contract(
    row: Dict[str, object],
    *,
    impact_field: str,
    target_field: str,
    related_field: str,
    projection_field: str,
    allowed_impacts: Set[str],
    path: Path,
    reporter: IssueReporter,
    context: str,
    rationale_field: str = "",
) -> None:
    impact = normalize_code(row.get(impact_field))
    target = normalize_code(row.get(target_field))
    projection = normalize_code(row.get(projection_field))
    related = validate_related_capabilities(row, related_field, target, path, reporter, context)
    if impact not in allowed_impacts:
        reporter.error("capability-impact", path, f"{context} 的 {impact_field} 非法：{impact}")
        return
    if impact in BUSINESS_CAPABILITY_IMPACTS:
        if projection not in SPEC_PROJECTIONS:
            reporter.error("capability-impact-projection", path, f"{context} 使用 new/modified 时必须采用 spec projection")
        if is_no_owner(target) or target == "unresolved" or not KEBAB_CASE_RE.match(target):
            reporter.error("capability-target", path, f"{context} 使用 new/modified 时必须指定具体 target capability")
    elif impact == "none":
        if target != "none":
            reporter.error("capability-target", path, f"{context} 使用 impact=none 时必须使用 target=none")
    elif impact == "unresolved":
        rationale = squash(row.get(rationale_field)) if rationale_field else ""
        if not rationale:
            reporter.error("capability-unresolved-rationale", path, f"{context} 的 unresolved impact 必须提供理由")
        if target != "unresolved" and (is_no_owner(target) or not KEBAB_CASE_RE.match(target)):
            reporter.error("capability-target", path, f"{context} 的 unresolved target 必须是已知 kebab-case Capability 或 unresolved")
    if projection in CHANGE_ONLY_PROJECTIONS and impact != "none":
        reporter.error("capability-change-only", path, f"{context} 的 {projection} 必须使用 impact=none")


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


def expected_manifest_artifacts(orchestrate_dir: Path, repo_root: Path) -> Dict[str, Tuple[str, str]]:
    specs: List[Tuple[Path, str, str]] = [
        (orchestrate_dir / "trace/phase-1.trace.json", PHASE_TRACE_SCHEMAS["phase-1"], "phase-1"),
        (orchestrate_dir / "trace/phase-2.trace.json", PHASE_TRACE_SCHEMAS["phase-2"], "phase-2"),
        (
            orchestrate_dir / "change-capability-anchors/obligation-atom-index.json",
            GLOBAL_ATOM_INDEX_SCHEMA,
            "phase-3",
        ),
        (
            orchestrate_dir / "phase-works/phase-3/coverage-review.json",
            PHASE3_COVERAGE_REVIEW_SCHEMA,
            "phase-3",
        ),
        (orchestrate_dir / "trace/phase-3.trace.json", PHASE_TRACE_SCHEMAS["phase-3"], "phase-3"),
        (
            orchestrate_dir / "phase-works/phase-4/source-window-dossiers/source-window-index.json",
            SOURCE_WINDOW_INDEX_SCHEMA,
            "phase-4",
        ),
        (orchestrate_dir / "trace/phase-4.trace.json", PHASE_TRACE_SCHEMAS["phase-4"], "phase-4"),
        (
            orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json",
            ATOM_PLAN_MAPPING_SCHEMA,
            "phase-5",
        ),
        (
            orchestrate_dir / "phase-works/phase-5/capability-baseline-reconciliation.json",
            CAPABILITY_BASELINE_SCHEMA,
            "phase-5",
        ),
        (
            orchestrate_dir / "phase-works/phase-5/final-packet-index.json",
            FINAL_PACKET_INDEX_SCHEMA,
            "phase-5",
        ),
        (orchestrate_dir / "trace/phase-5.trace.json", PHASE_TRACE_SCHEMAS["phase-5"], "phase-5"),
    ]
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    specs.extend((path, SOURCE_ATOMS_SCHEMA, "phase-2") for path in sorted(atom_root.glob("*.atoms.json")))
    return {
        rel(path, repo_root): (schema, phase)
        for path, schema, phase in specs
        if path.exists()
    }


def validate_manifest(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter, complete: bool = False) -> None:
    path = orchestrate_dir / "trace/manifest.json"
    data = json_obj(path, reporter, MANIFEST_SCHEMA)
    if not data:
        return
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
            "phase-4": {"grounded"},
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
        phase3_trace_path = orchestrate_dir / "trace/phase-3.trace.json"
        if phase3_trace_path.exists():
            phase3_trace = read_json(phase3_trace_path)
            reviewer_loop = phase3_trace.get("reviewer-loop")
            reviewer_status = normalize_code(reviewer_loop.get("status")) if isinstance(reviewer_loop, dict) else ""
            if reviewer_status != "passed":
                reporter.error(
                    "manifest-complete-phase3-reviewer",
                    path,
                    f"--complete 要求 Phase 3 reviewer-loop.status=passed，实际为 {reviewer_status or 'missing'}",
                )
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        reporter.error("manifest-artifacts", path, "artifacts 必须是 array")
        return
    expected_artifacts = expected_manifest_artifacts(orchestrate_dir, repo_root)
    seen_trace_paths: Set[str] = set()
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            reporter.error("manifest-artifact", path, f"artifacts[{index}] 必须是 object")
            continue
        trace_rel = item.get("trace-path")
        digest = item.get("sha256")
        if not isinstance(trace_rel, str) or not trace_rel:
            reporter.error("manifest-artifact-trace-path", path, f"artifacts[{index}] 缺少 trace-path")
            continue
        if trace_rel in seen_trace_paths:
            reporter.error("manifest-artifact-duplicate", path, f"trace-path 重复：{trace_rel}")
        seen_trace_paths.add(trace_rel)
        for field in ("artifact-path", "trace-schema", "phase", "role"):
            if not isinstance(item.get(field), str) or not str(item.get(field)).strip():
                reporter.error("manifest-artifact-field", path, f"{trace_rel} 缺少非空 {field}")
        trace_path = repo_root / trace_rel
        if not trace_path.exists():
            reporter.error("manifest-artifact-trace-path", path, f"{trace_rel} 不存在")
            continue
        current = sha256_file(trace_path)
        if digest != current:
            reporter.error("manifest-digest", path, f"{trace_rel} 的 sha256 不匹配")
        expected = expected_artifacts.get(trace_rel)
        if expected:
            expected_schema, expected_phase = expected
            if item.get("trace-schema") != expected_schema:
                reporter.error("manifest-artifact-schema", path, f"{trace_rel} 的 trace-schema 必须为 {expected_schema}")
            if item.get("phase") != expected_phase:
                reporter.error("manifest-artifact-phase", path, f"{trace_rel} 的 phase 必须为 {expected_phase}")
        try:
            trace_data = read_json(trace_path)
        except Exception:  # noqa: BLE001
            trace_data = {}
        if trace_data and item.get("trace-schema") != trace_data.get("trace-schema"):
            reporter.error("manifest-artifact-schema", path, f"{trace_rel} 的 trace-schema 与 canonical JSON 不一致")
    for trace_rel in sorted(set(expected_artifacts) - seen_trace_paths):
        reporter.error("manifest-artifact-missing", path, f"manifest artifacts 缺少 canonical JSON：{trace_rel}")


def validate_phase_1(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    path = orchestrate_dir / "trace/phase-1.trace.json"
    data = json_obj(path, reporter, PHASE_TRACE_SCHEMAS["phase-1"])
    if not data:
        return
    validate_trace_status(data, path, reporter, "phase-1", "phase1-status")
    initial_plan_path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    source_manifest_path = orchestrate_dir / "phase-works/phase-1/source-doc-manifest.md"
    require_file(initial_plan_path, reporter, "phase1-interface-artifact", "缺少 Phase 1 initial-change-plan.md")
    require_file(source_manifest_path, reporter, "phase1-interface-artifact", "缺少 Phase 1 source-doc-manifest.md")
    require_file(orchestrate_dir / "phase-works/phase-1/phase-1-agent-report.md", reporter, "phase1-interface-artifact", "缺少 Phase 1 agent 报告")
    validate_phase1_plan_structure(initial_plan_path, reporter)

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
    if trace:
        validate_trace_status(trace, trace_path, reporter, "phase-2", "phase2-status")
        for field in ("work-queue-path", "sources", "phase-report-path"):
            if field not in trace:
                reporter.error("phase2-trace-field", trace_path, f"Phase 2 trace 缺少字段：{field}")
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
                "reviewer-loop",
            },
            trace_path,
            reporter,
            "phase3-trace-fields",
            "Phase 3 trace",
        )
        if not isinstance(trace.get("reviewer-loop"), dict):
            reporter.error("phase3-reviewer-loop", trace_path, "reviewer-loop 必须是 object")
        else:
            reviewer_loop = trace["reviewer-loop"]
            exact_fields(
                reviewer_loop,
                {"status", "writer-id", "reviewer-id", "validator-status", "findings", "repairs"},
                trace_path,
                reporter,
                "phase3-reviewer-loop-fields",
                "reviewer-loop",
            )
            loop_status = normalize_code(reviewer_loop.get("status"))
            if loop_status not in {"pending", "passed", "blocked"}:
                reporter.error("phase3-reviewer-loop-status", trace_path, f"reviewer-loop status非法：{loop_status}")
            if not isinstance(reviewer_loop.get("findings"), list) or not isinstance(reviewer_loop.get("repairs"), list):
                reporter.error("phase3-reviewer-loop-evidence", trace_path, "findings与repairs必须是 array")
            if loop_status == "passed":
                writer_id = squash(reviewer_loop.get("writer-id"))
                reviewer_id = squash(reviewer_loop.get("reviewer-id"))
                if not writer_id or not reviewer_id:
                    reporter.error("phase3-reviewer-loop-identity", trace_path, "passed reviewer-loop必须记录 writer/reviewer identity")
                elif writer_id == reviewer_id:
                    reporter.error("phase3-reviewer-loop-independence", trace_path, "Phase 3 reviewer identity必须不同于 writer identity")
                if normalize_code(reviewer_loop.get("validator-status")) != "passed":
                    reporter.error("phase3-reviewer-loop-validator", trace_path, "passed reviewer-loop必须记录 validator-status=passed")
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
                "recheck-sources",
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

    rechecks = coverage.get("recheck-sources")
    if not isinstance(rechecks, list):
        reporter.error("phase3-recheck-sources", coverage_path, "recheck-sources 必须是 array")
        rechecks = []
    recheck_fields = {"source-document", "source-atom-ids", "line-ranges", "reason"}
    phase2_keys = set(phase2_atoms)
    for row in rechecks:
        if not isinstance(row, dict):
            reporter.error("phase3-recheck-row", coverage_path, "recheck-sources item 必须是 object")
            continue
        source_document = normalize_code(row.get("source-document"))
        exact_fields(row, recheck_fields, coverage_path, reporter, "phase3-recheck-fields", source_document or "recheck")
        ids = row.get("source-atom-ids")
        if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
            reporter.error("phase3-recheck-atom-ids", coverage_path, f"{source_document} recheck必须提供非空唯一 source-atom-ids")
            ids = []
        for atom_id in ids:
            if f"{source_document}::{atom_id}" not in phase2_keys:
                reporter.error("phase3-recheck-unknown-atom", coverage_path, f"recheck引用未知 Phase 2 atom：{source_document}::{atom_id}")
        check_ranges(coverage_path, reporter, row.get("line-ranges"), source_document, repo_root, f"recheck::{source_document}")
        if not squash(row.get("reason")):
            reporter.error("phase3-recheck-reason", coverage_path, f"{source_document} recheck缺少中文 reason")

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

    summary = coverage.get("summary") if isinstance(coverage.get("summary"), dict) else {}
    disposition_counts = {name: classifications.count(name) for name in sorted(PHASE3_DISPOSITIONS)}
    expected_summary = {
        "source-documents": len(read_full),
        "phase-2-atoms": len(phase2_atoms),
        "gap-atoms": len(gap_atoms),
        "global-atoms": len(global_atoms),
        "candidate-uncovered-ranges": sum(len(items) for items in uncovered_by_source.values()),
        "remainder-dispositions": disposition_counts,
    }
    if summary != expected_summary:
        reporter.error("phase3-summary-drift", coverage_path, f"summary 与机械重算不一致；期望 {expected_summary}")

    if decision == "coverage-complete" and (rechecks or "requires-reextract" in classifications or "blocked" in classifications):
        reporter.error("phase3-decision-consistency", coverage_path, "coverage-complete不得包含 recheck或 blocker")
    if decision == "needs-extraction-recheck" and not (rechecks or "requires-reextract" in classifications):
        reporter.error("phase3-decision-consistency", coverage_path, "needs-extraction-recheck要求 targeted recheck evidence")
    if decision == "needs-extraction-recheck" and "blocked" in classifications:
        reporter.error("phase3-decision-consistency", coverage_path, "存在 blocked disposition时 decision必须是 blocked")
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
    status = ""
    if phase4_trace:
        status = validate_trace_status(phase4_trace, phase4_trace_path, reporter, "phase-4", "phase4-status")
    phase1_plan_path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    phase4_input_plan_path = orchestrate_dir / "phase-works/phase-4/input-change-plan.md"
    require_file(phase1_plan_path, reporter, "phase4-interface-input", "缺少 Phase 4 输入：Phase 1 initial-change-plan.md")
    require_file(phase4_input_plan_path, reporter, "phase4-interface-artifact", "缺少 Phase 4 input change plan")
    require_same_file(
        phase1_plan_path,
        phase4_input_plan_path,
        reporter,
        "phase4-input-plan-drift",
        "Phase 4 input-change-plan.md 必须与 Phase 1 initial-change-plan.md 完全一致",
    )
    require_file(orchestrate_dir / "phase-works/phase-4/source-window-dossiers/index.md", reporter, "phase4-interface-artifact", "缺少 Phase 4 source-window dossier index")
    require_file(orchestrate_dir / "phase-works/phase-4/source-window-semantic-profile-review.md", reporter, "phase4-interface-artifact", "缺少 Phase 4 semantic profile review")
    require_file(orchestrate_dir / "phase-works/phase-4/source-window-grounding-issues.md", reporter, "phase4-interface-artifact", "缺少 Phase 4 grounding issues 报告")
    require_file(orchestrate_dir / "phase-works/phase-4/phase-4-agent-report.md", reporter, "phase4-interface-artifact", "缺少 Phase 4 agent 报告")
    global_atoms = load_global_atoms(orchestrate_dir, reporter)
    resolved_evidence = resolve_global_evidence(orchestrate_dir, global_atoms, reporter)
    index_path = orchestrate_dir / "phase-works/phase-4/source-window-dossiers/source-window-index.json"
    data = json_obj(index_path, reporter, SOURCE_WINDOW_INDEX_SCHEMA)
    if data:
        exact_fields(
            data,
            {"trace-schema", "trace-contract-version", "status", "windows", "semantic-profiles", "grounding-issues"},
            index_path,
            reporter,
            "phase4-index-fields",
            "source-window-index",
        )
        forbidden_tokens = ("duplicate", "equivalence", "canonical-ga", "canonical-atom", "delivery-unit")
        forbidden_keys = sorted({key for key in iter_nested_keys(data) if any(token in key.lower() for token in forbidden_tokens)})
        if forbidden_keys:
            reporter.error(
                "phase4-semantic-dedup-field",
                index_path,
                f"Phase 4 不得包含 semantic dedup metadata：{', '.join(forbidden_keys)}",
            )
    index_status = phase_status_value(data.get("status"))
    if status and index_status and status != index_status:
        reporter.error("phase4-status-drift", index_path, f"source-window-index status {index_status} 与 phase trace status {status} 不一致")
    windows = data.get("windows")
    if not isinstance(windows, list):
        reporter.error("phase4-windows", index_path, "windows 必须是 array")
        return
    if not windows:
        issues = data.get("grounding-issues")
        if status == "grounded" or not status:
            reporter.error("phase4-windows", index_path, "Phase 4 为 grounded 时，windows 必须是非空 array")
        if status in NON_FINAL_PHASE4_STATUSES and not (isinstance(issues, list) and issues):
            reporter.error("phase4-grounding-issues", index_path, f"{status} 要求提供非空 grounding-issues")
        return
    grounded_ids: Set[str] = set()
    window_fields = {
        "window-id",
        "input-unit",
        "unit-type",
        "source-document",
        "line-ranges",
        "context-line-ranges",
        "linked-global-atom-ids",
        "dossier-path",
        "source-sha256",
        "window-text-sha256",
    }
    for row in windows:
        if not isinstance(row, dict):
            reporter.error("phase4-window-row", index_path, "windows item 必须是 object")
            continue
        window_id = str(row.get("window-id", ""))
        exact_fields(row, window_fields, index_path, reporter, "phase4-window-fields", window_id or "window")
        source_document = str(row.get("source-document", ""))
        dossier_path = row.get("dossier-path")
        if not isinstance(dossier_path, str) or not (repo_root / dossier_path).exists():
            reporter.error("phase4-dossier-path", index_path, f"{window_id} 缺少 dossier 路径：{dossier_path}")
        source_path = repo_root / source_document
        if not source_path.exists():
            reporter.error("phase4-source-path", index_path, f"{window_id} 缺少来源：{source_document}")
        elif row.get("source-sha256") != sha256_file(source_path):
            reporter.error("phase4-source-sha", index_path, f"{window_id} 的来源 hash 相对 {source_document} 发生 drift")
        check_ranges(index_path, reporter, row.get("line-ranges"), source_document, repo_root, window_id)
        context_ranges = row.get("context-line-ranges")
        if not isinstance(context_ranges, list):
            reporter.error("phase4-context-line-ranges", index_path, f"{window_id} 的 context-line-ranges 必须是 array")
        elif context_ranges:
            check_ranges(index_path, reporter, context_ranges, source_document, repo_root, f"{window_id} context")
        window_ranges = valid_range_items(row.get("line-ranges"))
        expected_window_sha = sha256_text(source_text_for_ranges(repo_root, source_document, window_ranges))
        if row.get("window-text-sha256") != expected_window_sha:
            reporter.error("phase4-window-text-sha", index_path, f"{window_id} 的 window-text-sha256 与 source/range不一致")
        ids = row.get("linked-global-atom-ids")
        if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
            reporter.error("phase4-linked-ga", index_path, f"{window_id} 的 linked-global-atom-ids 必须非空")
        else:
            evidence_signatures: Set[Tuple[str, str]] = set()
            for atom_id in ids:
                if atom_id not in global_atoms:
                    reporter.error("phase4-linked-ga", index_path, f"{window_id} 引用了未知的 {atom_id}")
                    continue
                grounded_ids.add(str(atom_id))
                evidence = resolved_evidence.get(str(atom_id))
                if not evidence:
                    continue
                evidence_signatures.add(
                    (
                        str(evidence.get("source-document", "")),
                        json.dumps(evidence.get("line-ranges"), ensure_ascii=False, sort_keys=True),
                    )
                )
                if source_document != evidence.get("source-document"):
                    reporter.error("phase4-window-evidence-source", index_path, f"{window_id}/{atom_id} 与 resolved source不一致")
                evidence_ranges = valid_range_items(evidence.get("line-ranges"))
                if evidence_ranges and not range_covered_by(evidence_ranges[0], window_ranges):
                    reporter.error("phase4-window-evidence-range", index_path, f"{window_id} 未覆盖 {atom_id} 的 resolved evidence range")
            if len(ids) > 1 and len(evidence_signatures) > 1:
                reporter.error(
                    "phase4-window-reuse-nonidentical",
                    index_path,
                    f"{window_id} 只能机械复用 source/range完全相同的 GA evidence",
                )
    if status == "grounded" and grounded_ids != set(global_atoms):
        reporter.error(
            "phase4-ga-grounding-coverage",
            index_path,
            f"grounded要求每个 GA至少一个 window；缺少={sorted(set(global_atoms)-grounded_ids)}",
        )


def load_mapping(orchestrate_dir: Path, reporter: IssueReporter) -> Dict[str, Dict[str, object]]:
    path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
    data = json_obj(path, reporter, ATOM_PLAN_MAPPING_SCHEMA)
    mapping: Dict[str, Dict[str, object]] = {}
    rows = data.get("rows")
    if not isinstance(rows, list):
        reporter.error("phase5-mapping-rows", path, "rows 必须是 array")
        return mapping
    for row in rows:
        if not isinstance(row, dict):
            reporter.error("phase5-mapping-row", path, "rows item 必须是 object")
            continue
        atom_id = str(row.get("global-atom-id", ""))
        if not GLOBAL_ATOM_ID_RE.match(atom_id):
            reporter.error("phase5-ga-format", path, f"Global Atom ID 非法：{atom_id}")
            continue
        if atom_id in mapping:
            reporter.error("phase5-ga-duplicate", path, f"mapping row 重复：{atom_id}")
        mapping[atom_id] = row
    return mapping


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


def load_capability_baselines(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
) -> Dict[str, Dict[str, object]]:
    json_path = orchestrate_dir / "phase-works/phase-5/capability-baseline-reconciliation.json"
    md_path = json_path.with_suffix(".md")
    data = json_obj(json_path, reporter, CAPABILITY_BASELINE_SCHEMA)
    if data and normalize_code(data.get("repository-specs-root")) != "openspec/specs":
        reporter.error(
            "phase5-capability-baseline-root",
            json_path,
            "repository-specs-root 必须是 openspec/specs",
        )
    if json_path.exists():
        validate_rendered_markdown(
            orchestrate_dir,
            json_path,
            md_path,
            render_capability_baseline,
            reporter,
            "phase5-capability-baseline",
        )
    rows = data.get("capabilities")
    result: Dict[str, Dict[str, object]] = {}
    if not isinstance(rows, list):
        reporter.error("phase5-capability-baseline-rows", json_path, "capabilities 必须是 array")
        return result
    for row in rows:
        if not isinstance(row, dict):
            reporter.error("phase5-capability-baseline-row", json_path, "capabilities item 必须是 object")
            continue
        required_keys = {
            "capability",
            "baseline-status",
            "spec-path",
            "spec-sha256",
            "baseline-evidence",
            "first-planned-advancement",
            "required-first-relation",
            "later-relation-rule",
        }
        missing_keys = sorted(required_keys - set(row))
        if missing_keys:
            reporter.error(
                "phase5-capability-baseline-fields",
                json_path,
                f"baseline row 缺少字段：{', '.join(missing_keys)}",
            )
        capability = normalize_code(row.get("capability"))
        if not KEBAB_CASE_RE.match(capability):
            reporter.error("phase5-capability-baseline-id", json_path, f"Capability ID 非法：{capability}")
            continue
        if capability in result:
            reporter.error("phase5-capability-baseline-duplicate", json_path, f"Capability baseline 重复：{capability}")
            continue
        status = normalize_code(row.get("baseline-status"))
        if status not in {"existing", "absent"}:
            reporter.error("phase5-capability-baseline-status", json_path, f"{capability} baseline-status 非法：{status}")
        expected_rel = f"openspec/specs/{capability}/spec.md"
        spec_rel = normalize_code(row.get("spec-path"))
        if spec_rel != expected_rel:
            reporter.error("phase5-capability-baseline-path", json_path, f"{capability} spec-path 必须是 {expected_rel}")
        spec_path = repo_root / expected_rel
        actual_status = "existing" if spec_path.is_file() else "absent"
        if status != actual_status:
            reporter.error(
                "phase5-capability-baseline-filesystem",
                json_path,
                f"{capability} 声明 {status}，实际 repository baseline 为 {actual_status}",
            )
        expected_sha = sha256_file(spec_path) if spec_path.is_file() else None
        if row.get("spec-sha256") != expected_sha:
            reporter.error("phase5-capability-baseline-sha", json_path, f"{capability} spec-sha256 与 repository baseline 不一致")
        if not squash(row.get("baseline-evidence")):
            reporter.error("phase5-capability-baseline-evidence", json_path, f"{capability} 缺少 baseline-evidence")
        expected_first_relation = "modified" if status == "existing" else "new"
        if normalize_code(row.get("required-first-relation")) != expected_first_relation:
            reporter.error(
                "phase5-capability-baseline-relation",
                json_path,
                f"{capability} required-first-relation 应为 {expected_first_relation}",
            )
        if normalize_code(row.get("later-relation-rule")) != "modified":
            reporter.error("phase5-capability-baseline-relation", json_path, f"{capability} later-relation-rule 必须为 modified")
        result[capability] = row
    return result


def validate_final_packets(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter, mapping: Dict[str, Dict[str, object]]) -> None:
    index_path = orchestrate_dir / "phase-works/phase-5/final-packet-index.json"
    data = json_obj(index_path, reporter, FINAL_PACKET_INDEX_SCHEMA)
    packets = data.get("packets")
    if not isinstance(packets, list):
        reporter.error("phase5-final-packet-index", index_path, "packets 必须是 array")
        return

    direct_by_view: Dict[tuple[str, str], Set[str]] = {}
    direct_by_change: Dict[str, Set[str]] = {}
    non_direct_by_change: Dict[str, Set[str]] = {}
    for atom_id, row in mapping.items():
        if is_executable_direct_row(row):
            change = str(row.get("final-owner-change", ""))
            direct_by_change.setdefault(change, set()).add(atom_id)
            if is_capability_view_row(row):
                capability = str(row.get("final-target-capability", ""))
                direct_by_view.setdefault((change, capability), set()).add(atom_id)
        else:
            change = str(row.get("final-owner-change", ""))
            if not is_no_owner(change):
                non_direct_by_change.setdefault(change, set()).add(atom_id)

    packet_changes: Set[str] = set()
    packet_direct_by_change: Dict[str, Set[str]] = {}
    packet_non_direct_by_change: Dict[str, Set[str]] = {}
    capability_views_by_owner: Set[tuple[str, str]] = set()
    packet_change_kinds: Dict[str, str] = {}
    packet_order: List[str] = []
    foundation_packet_count = 0
    for packet_index, packet in enumerate(packets):
        if not isinstance(packet, dict):
            reporter.error("phase5-final-packet-row", index_path, "packets item 必须是 object")
            continue
        change = str(packet.get("change", ""))
        change_kind = str(packet.get("change-kind", ""))
        if change_kind not in {FOUNDATION_CHANGE_KIND, BUSINESS_CHANGE_KIND}:
            reporter.error(
                "phase5-final-packet-change-kind",
                index_path,
                f"{change} packet 缺少有效的 change-kind foundation/business",
            )
            change_kind = BUSINESS_CHANGE_KIND
        if change_kind == FOUNDATION_CHANGE_KIND:
            foundation_packet_count += 1
            if packet_index != 0:
                reporter.error("phase5-foundation-order", index_path, f"{change} foundation packet 必须是第一个 packet")
        packet_change_kinds[change] = change_kind
        packet_order.append(change)
        packet_changes.add(change)
        packet_rel = packet.get("packet-path")
        if not isinstance(packet_rel, str) or not packet_rel:
            reporter.error("phase5-final-packet-path", index_path, f"{change} 缺少 packet-path")
            continue
        packet_path = repo_root / packet_rel
        if not packet_path.exists():
            reporter.error("phase5-final-packet-path", index_path, f"{change} 缺少 packet：{packet_rel}")
            continue
        text = packet_path.read_text(encoding="utf-8")
        if "未做语义去重" not in text or "多对一" not in text:
            reporter.error(
                "phase5-packet-dedup-handoff",
                packet_path,
                "final packet 必须声明其为未语义去重的 evidence mapping，并要求下游保留多对一 GA trace",
            )
        if packet.get("packet-digest") != sha256_file(packet_path):
            reporter.error("phase5-final-packet-digest", index_path, f"{change} 的 packet-digest 发生 drift")
        direct_ids = set(packet.get("direct-atom-ids") if isinstance(packet.get("direct-atom-ids"), list) else [])
        if change_kind == FOUNDATION_CHANGE_KIND and not direct_ids:
            reporter.error(
                "phase5-foundation-empty",
                index_path,
                f"{change} foundation packet 必须至少包含一个 direct foundation atom",
            )
        for atom_id in direct_ids:
            row = mapping.get(str(atom_id))
            if not row:
                reporter.error("phase5-final-direct-packet-index", index_path, f"{change} packet 列出了未知 direct atom {atom_id}")
                continue
            if row.get("final-relation") != "direct" or row.get("final-owner-change") != change:
                reporter.error(
                    "phase5-final-direct-packet-owner",
                    index_path,
                    f"{change} packet 将 {atom_id} 列为 direct，但 mapping 未将其直接分配给该 Change",
                )
            cap = str(row.get("final-target-capability", ""))
            impact = str(row.get("final-capability-impact", ""))
            if change_kind == FOUNDATION_CHANGE_KIND:
                if cap != FOUNDATION_CAPABILITY:
                    reporter.error("phase5-foundation-capability", index_path, f"{change}/{atom_id} foundation direct atom 必须以 {FOUNDATION_CAPABILITY} 为 target")
                if impact != FOUNDATION_IMPACT:
                    reporter.error("phase5-foundation-impact", index_path, f"{change}/{atom_id} foundation direct atom 必须使用 {FOUNDATION_IMPACT}")
            elif cap == FOUNDATION_CAPABILITY:
                reporter.error("phase5-foundation-capability", index_path, f"{change}/{atom_id} business packet 不得以 {FOUNDATION_CAPABILITY} 为 target")
        packet_direct_by_change.setdefault(change, set()).update(str(atom_id) for atom_id in direct_ids)
        non_direct_ids = set(
            packet.get("owner-scoped-non-direct-atom-ids")
            if isinstance(packet.get("owner-scoped-non-direct-atom-ids"), list)
            else []
        )
        packet_non_direct_by_change.setdefault(change, set()).update(str(atom_id) for atom_id in non_direct_ids)
        for atom_id in non_direct_ids:
            row = mapping.get(str(atom_id))
            if not row:
                reporter.error("phase5-final-non-direct-packet", index_path, f"{change} packet 列出了未知 non-direct atom {atom_id}")
            elif row.get("final-relation") == "direct" or row.get("final-owner-change") != change:
                reporter.error(
                    "phase5-final-non-direct-packet-owner",
                    index_path,
                    f"{change} packet 将 {atom_id} 列为 non-direct，但 mapping 未将其 scope 归入该 Change",
                )
        direct_table_rows = table_rows(
            packet_path,
            ["Global Atom ID", "Capability Impact", "Target Capability", "Related Capabilities"],
        )
        direct_table = {
            normalize_code(cell(row, "Global Atom ID")): row
            for row in direct_table_rows
            if normalize_code(cell(row, "Global Atom ID"))
        }
        if direct_ids and not direct_table:
            reporter.error(
                "phase5-final-direct-table-contract",
                packet_path,
                "final direct table 必须公开 Capability Impact、Target Capability 和 Related Capabilities",
            )
        for atom_id in direct_ids:
            mapping_row = mapping.get(str(atom_id))
            table_row = direct_table.get(str(atom_id))
            if table_row is None:
                reporter.error("phase5-final-direct-table-row", packet_path, f"v2 direct table 缺少 direct atom {atom_id}")
                continue
            if not mapping_row:
                continue
            displayed_impact = normalize_code(cell(table_row, "Capability Impact"))
            displayed_target = markdown_target(cell(table_row, "Target Capability"))
            displayed_related = sorted(markdown_capability_list(cell(table_row, "Related Capabilities")))
            expected_related = sorted(str(value) for value in mapping_row.get("related-capabilities", []))
            if displayed_impact != normalize_code(mapping_row.get("final-capability-impact")):
                reporter.error("phase5-final-direct-table-drift", packet_path, f"{atom_id} 的 Capability Impact 与 mapping 不一致")
            if displayed_target != normalize_code(mapping_row.get("final-target-capability")):
                reporter.error("phase5-final-direct-table-drift", packet_path, f"{atom_id} 的 Target Capability 与 mapping 不一致")
            if displayed_related != expected_related:
                reporter.error("phase5-final-direct-table-drift", packet_path, f"{atom_id} 的 Related Capabilities 与 mapping 不一致")
        for atom_id in set(direct_table) - {str(value) for value in direct_ids}:
            reporter.error("phase5-final-direct-table-extra", packet_path, f"v2 direct table 包含未索引的 direct atom {atom_id}")
        for atom_id in direct_ids:
            if atom_id not in text:
                reporter.error("phase5-final-direct-packet", packet_path, f"final packet 缺少 direct atom {atom_id}")
            mapping_row = mapping.get(str(atom_id), {})
            evidence_ref = mapping_row.get("evidence-ref")
            if isinstance(evidence_ref, dict) and json.dumps(evidence_ref, ensure_ascii=False, sort_keys=True) not in text:
                reporter.error("phase5-final-evidence-ref", packet_path, f"final packet 缺少 {atom_id} 的 evidence reference")
        for atom_id in non_direct_ids:
            if atom_id not in text:
                reporter.error("phase5-final-non-direct-packet", packet_path, f"final packet 缺少 owner-scoped non-direct atom {atom_id}")
            mapping_row = mapping.get(str(atom_id), {})
            evidence_ref = mapping_row.get("evidence-ref")
            if isinstance(evidence_ref, dict) and json.dumps(evidence_ref, ensure_ascii=False, sort_keys=True) not in text:
                reporter.error("phase5-final-evidence-ref", packet_path, f"final packet 缺少 {atom_id} 的 evidence reference")

        capability_paths = packet.get("capability-view-paths")
        if not isinstance(capability_paths, list):
            reporter.error("phase5-capability-view-paths", index_path, f"{change} 的 capability-view-paths 必须是 array")
            continue
        declared_cap_paths = {
            (repo_root / cap_rel).resolve()
            for cap_rel in capability_paths
            if isinstance(cap_rel, str) and cap_rel
        }
        actual_cap_dir = packet_path.parent / "capability-anchors"
        actual_cap_paths = {
            path.resolve()
            for path in actual_cap_dir.glob("*.md")
        } if actual_cap_dir.exists() else set()
        for cap_path in sorted(actual_cap_paths - declared_cap_paths):
            reporter.error(
                "phase5-capability-view-unindexed",
                cap_path,
                f"{change} 存在未索引的 capability view",
            )
        for cap_path in sorted(declared_cap_paths - actual_cap_paths):
            if cap_path.exists():
                reporter.error(
                    "phase5-capability-view-location",
                    cap_path,
                    f"{change} 声明的 capability view 位于 canonical capability-anchors 目录之外",
                )
        for cap_path in sorted(declared_cap_paths | actual_cap_paths):
            if not cap_path.exists():
                reporter.error("phase5-capability-view-path", index_path, f"缺少 capability view：{cap_path}")
                continue
            cap_slug = cap_path.stem
            capability_views_by_owner.add((change, cap_slug))
            text_ids = set(extract_ga_ids(cap_path.read_text(encoding="utf-8")))
            if change_kind == FOUNDATION_CHANGE_KIND and cap_slug != FOUNDATION_CAPABILITY:
                reporter.error("phase5-foundation-capability", cap_path, f"foundation packet capability view 必须是 {FOUNDATION_CAPABILITY}")
            if change_kind == BUSINESS_CHANGE_KIND and cap_slug == FOUNDATION_CAPABILITY:
                reporter.error("phase5-foundation-capability", cap_path, f"business packet 不得渲染 {FOUNDATION_CAPABILITY} capability view")
            expected_ids = direct_by_view.get((change, cap_slug), set())
            if not expected_ids:
                reporter.error("phase5-capability-view-extra", cap_path, f"{change}/{cap_slug} 没有 spec capability delta")
            for atom_id in text_ids:
                row = mapping.get(atom_id)
                if not row or row.get("final-relation") != "direct":
                    reporter.error("phase5-capability-view-non-direct", cap_path, f"capability view 包含 non-direct 或未知 atom {atom_id}")
                elif not is_capability_view_row(row):
                    reporter.error("phase5-capability-view-non-advancing", cap_path, f"capability view 包含 non-advancing 或未知 atom {atom_id}")
                elif row.get("final-owner-change") != change or row.get("final-target-capability") != cap_slug:
                    reporter.error("phase5-capability-view-owner", cap_path, f"{atom_id} 不属于 {change}/{cap_slug}")
            missing = expected_ids - text_ids
            if missing:
                reporter.error("phase5-capability-view-missing-direct", cap_path, f"capability view 缺少 direct atom：{', '.join(sorted(missing)[:12])}")

    for change, atom_ids in direct_by_change.items():
        if change not in packet_changes:
            reporter.error("phase5-final-direct-owner", index_path, f"direct owner Change {change} 没有 final packet")
            continue
        missing_direct = atom_ids - packet_direct_by_change.get(change, set())
        if missing_direct:
            reporter.error("phase5-final-direct-packet-index", index_path, f"{change} 的 final packet index 缺少 direct atom：{', '.join(sorted(missing_direct)[:12])}")

    for change, atom_ids in non_direct_by_change.items():
        if change not in packet_changes:
            reporter.error("phase5-final-non-direct-owner", index_path, f"non-direct owner Change {change} 没有 final packet")
            continue
        missing_non_direct = atom_ids - packet_non_direct_by_change.get(change, set())
        if missing_non_direct:
            reporter.error(
                "phase5-final-non-direct-packet-index",
                index_path,
                f"{change} 的 final packet index 缺少 owner-scoped non-direct atom：{', '.join(sorted(missing_non_direct)[:12])}",
            )

    for change, cap_slug in direct_by_view:
        if change in packet_changes and (change, cap_slug) not in capability_views_by_owner:
            reporter.error("phase5-capability-view-missing-owner", index_path, f"{change}/{cap_slug} 有 capability delta atom，但没有 capability view")

    baselines = load_capability_baselines(orchestrate_dir, repo_root, reporter)
    active_capabilities = {
        normalize_code(row.get("final-target-capability"))
        for row in mapping.values()
        if normalize_code(row.get("final-capability-impact")) in BUSINESS_CAPABILITY_IMPACTS
    }
    missing_baselines = active_capabilities - set(baselines)
    extra_baselines = set(baselines) - active_capabilities
    if missing_baselines:
        reporter.error(
            "phase5-capability-baseline-missing",
            index_path,
            f"缺少 active Capability baseline：{', '.join(sorted(missing_baselines))}",
        )
    if extra_baselines:
        reporter.error(
            "phase5-capability-baseline-extra",
            index_path,
            f"baseline reconciliation 包含未被 final spec atom 推进的 Capability：{', '.join(sorted(extra_baselines))}",
        )

    advancement_index: Dict[str, int] = {}
    for change in packet_order:
        impacts_by_target: Dict[str, Set[str]] = {}
        for row in mapping.values():
            if row.get("final-owner-change") != change or row.get("final-capability-impact") not in BUSINESS_CAPABILITY_IMPACTS:
                continue
            target = str(row.get("final-target-capability", ""))
            impacts_by_target.setdefault(target, set()).add(str(row.get("final-capability-impact", "")))
        for target, impacts in impacts_by_target.items():
            if len(impacts) != 1:
                reporter.error("phase5-capability-impact-mixed", index_path, f"{change}/{target} 混用了 impact：{sorted(impacts)}")
                continue
            impact = next(iter(impacts))
            baseline = baselines.get(target, {})
            status = normalize_code(baseline.get("baseline-status"))
            position = advancement_index.get(target, 0)
            expected = "modified" if status == "existing" or position > 0 else "new"
            if impact != expected:
                reporter.error(
                    "phase5-capability-impact-baseline",
                    index_path,
                    f"{change}/{target} baseline={status}，期望 {expected}，实际为 {impact}",
                )
            if position == 0 and normalize_code(baseline.get("first-planned-advancement")) != change:
                reporter.error(
                    "phase5-capability-baseline-first-advancement",
                    index_path,
                    f"{target} first-planned-advancement 与 packet order 不一致",
                )
            advancement_index[target] = position + 1

    for atom_id, row in mapping.items():
        change = str(row.get("final-owner-change", ""))
        if row.get("final-relation") != "direct" and change and change != "None" and change not in packet_changes:
            reporter.error("phase5-final-non-direct-owner", index_path, f"{atom_id} 有 final owner Change，但没有 final packet：{change}")
    if foundation_packet_count > 1:
        reporter.error("phase5-foundation-count", index_path, "final-packet-index 最多只能包含一个 foundation packet")


def validate_phase_5(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter, complete: bool = False) -> None:
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    trace = json_obj(trace_path, reporter, PHASE_TRACE_SCHEMAS["phase-5"])
    status = ""
    if trace:
        status = validate_trace_status(trace, trace_path, reporter, "phase-5", "phase5-status")
    require_file(orchestrate_dir / "phase-works/phase-5/source-window-refit-trace.md", reporter, "phase5-interface-artifact", "缺少 Phase 5 source-window refit trace")
    require_file(orchestrate_dir / "phase-works/phase-5/phase-5-agent-report.md", reporter, "phase5-interface-artifact", "缺少 Phase 5 agent 报告")
    if status in NON_FINAL_PHASE5_STATUSES:
        require_file(orchestrate_dir / "phase-works/phase-5/change-plan-adjustments.md", reporter, "phase5-interface-artifact", f"Phase 5 状态为 {status} 时必须提供 change-plan-adjustments.md")
        terminal_paths = [
            orchestrate_dir / "phase-works/phase-5/input-change-plan.md",
            orchestrate_dir / "phase-works/phase-5/change-plan.md",
            orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.md",
            orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json",
            orchestrate_dir / "phase-works/phase-5/capability-baseline-reconciliation.md",
            orchestrate_dir / "phase-works/phase-5/capability-baseline-reconciliation.json",
            orchestrate_dir / "phase-works/phase-5/final-packet-index.json",
            orchestrate_dir / "phase-works/phase-5/capability-progression-review.md",
            orchestrate_dir / "phase-works/phase-5/change-complexity-review.md",
            orchestrate_dir / "phase-works/phase-5/plan-refit-decision-log.md",
            orchestrate_dir / "phase-works/phase-5/alignment-final-report.md",
            orchestrate_dir / "phase-works/phase-5/change-capability-human-plan.md",
            orchestrate_dir / "change-capability-anchors/index.md",
        ]
        for terminal_path in terminal_paths:
            if terminal_path.exists():
                reporter.error(
                    "phase5-nonfinal-terminal-artifact",
                    terminal_path,
                    f"Phase 5 状态为 {status} 时不得保留 terminal artifact",
                )
        anchors_dir = orchestrate_dir / "change-capability-anchors"
        if anchors_dir.exists():
            for child in anchors_dir.iterdir():
                if child.is_dir():
                    reporter.error(
                        "phase5-nonfinal-terminal-artifact",
                        child,
                        f"Phase 5 状态为 {status} 时不得保留 final Change packet 或 Capability view",
                    )
        root_plan_path = orchestrate_dir / "change-plan.md"
        if root_plan_path.exists():
            reporter.error(
                "phase5-nonfinal-root-plan",
                root_plan_path,
                f"Phase 5 状态为 {status} 时不得发布根 change-plan.md",
            )
        if complete:
            reporter.error("phase5-complete-status", trace_path, f"--complete 要求 accepted/adjusted status，实际为 {status}")
        return
    if status in FINAL_PHASE5_STATUSES:
        phase4_input_plan_path = orchestrate_dir / "phase-works/phase-4/input-change-plan.md"
        phase5_input_plan_path = orchestrate_dir / "phase-works/phase-5/input-change-plan.md"
        phase5_plan_path = orchestrate_dir / "phase-works/phase-5/change-plan.md"
        root_plan_path = orchestrate_dir / "change-plan.md"
        require_file(phase4_input_plan_path, reporter, "phase5-interface-input", "缺少 Phase 5 输入：Phase 4 input-change-plan.md")
        require_file(phase5_input_plan_path, reporter, "phase5-interface-artifact", "缺少 Phase 5 input change plan")
        require_file(phase5_plan_path, reporter, "phase5-interface-artifact", "缺少 Phase 5 change plan")
        require_file(root_plan_path, reporter, "phase5-interface-artifact", "缺少 Phase 5 发布的根 change-plan.md")
        require_same_file(
            phase4_input_plan_path,
            phase5_input_plan_path,
            reporter,
            "phase5-input-plan-drift",
            "Phase 5 input-change-plan.md 必须与 Phase 4 input-change-plan.md 完全一致",
        )
        require_same_file(
            phase5_plan_path,
            root_plan_path,
            reporter,
            "phase5-root-plan-drift",
            "根 change-plan.md 必须与 Phase 5 change-plan.md 完全一致",
        )
        require_file(orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.md", reporter, "phase5-interface-artifact", "缺少 Phase 5 atom-plan-mapping.md")
        require_file(orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", reporter, "phase5-interface-artifact", "缺少 Phase 5 atom-plan-mapping.json")
        baseline_json_path = orchestrate_dir / "phase-works/phase-5/capability-baseline-reconciliation.json"
        require_file(baseline_json_path, reporter, "phase5-interface-artifact", "缺少 Capability baseline reconciliation JSON")
        require_file(orchestrate_dir / "phase-works/phase-5/capability-baseline-reconciliation.md", reporter, "phase5-interface-artifact", "缺少 Capability baseline reconciliation Markdown")
        require_file(orchestrate_dir / "phase-works/phase-5/final-packet-index.json", reporter, "phase5-interface-artifact", "缺少 Phase 5 final-packet-index.json")
        require_file(orchestrate_dir / "phase-works/phase-5/capability-progression-review.md", reporter, "phase5-interface-artifact", "缺少 Phase 5 capability progression review")
        require_file(orchestrate_dir / "phase-works/phase-5/change-complexity-review.md", reporter, "phase5-interface-artifact", "缺少 Phase 5 change complexity review")
        require_file(orchestrate_dir / "phase-works/phase-5/plan-refit-decision-log.md", reporter, "phase5-interface-artifact", "缺少 Phase 5 plan refit decision log")
        require_file(orchestrate_dir / "phase-works/phase-5/alignment-final-report.md", reporter, "phase5-interface-artifact", "缺少 Phase 5 alignment final report")
        require_file(orchestrate_dir / "phase-works/phase-5/change-capability-human-plan.md", reporter, "phase5-interface-artifact", "缺少 Phase 5 human plan")
        require_file(orchestrate_dir / "change-capability-anchors/index.md", reporter, "phase5-interface-artifact", "缺少 final change-capability anchor index")
        trace_baseline_path = str(trace.get("capability-baseline-reconciliation-path", ""))
        expected_baseline_rel = rel(baseline_json_path, repo_root)
        if trace_baseline_path != expected_baseline_rel:
            reporter.error(
                "phase5-capability-baseline-trace-path",
                trace_path,
                f"baseline reconciliation path 应为 {expected_baseline_rel}",
            )
        if baseline_json_path.exists() and trace.get("capability-baseline-reconciliation-sha256") != sha256_file(baseline_json_path):
            reporter.error("phase5-capability-baseline-trace-sha", trace_path, "baseline reconciliation digest 与 trace 不一致")
    global_atoms = load_global_atoms(orchestrate_dir, reporter)
    resolved_evidence = resolve_global_evidence(orchestrate_dir, global_atoms, reporter)
    mapping = load_mapping(orchestrate_dir, reporter)
    missing = sorted(set(global_atoms) - set(mapping))
    extra = sorted(set(mapping) - set(global_atoms))
    if missing:
        reporter.error("phase5-mapping-coverage", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"mapping 缺少 global atom：{', '.join(missing[:12])}")
    if extra:
        reporter.error("phase5-mapping-extra", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"mapping 包含未知 global atom：{', '.join(extra[:12])}")
    mapping_fields = {
        "global-atom-id",
        "evidence-ref",
        "source-document",
        "line-ranges",
        "final-owner-type",
        "final-owner-change",
        "final-capability-impact",
        "final-target-capability",
        "related-capabilities",
        "final-artifact-projection",
        "final-relation",
        "plan-decision",
        "reason",
    }
    for atom_id, row in mapping.items():
        mapping_path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
        exact_fields(row, mapping_fields, mapping_path, reporter, "phase5-mapping-fields", atom_id)
        reject_legacy_capability_fields(
            row,
            mapping_path,
            reporter,
            atom_id,
        )
        source_document = str(row.get("source-document", ""))
        check_atom_range(mapping_path, reporter, row.get("line-ranges"), source_document, repo_root, atom_id)
        global_row = global_atoms.get(atom_id)
        evidence = resolved_evidence.get(atom_id)
        if global_row and row.get("evidence-ref") != global_row.get("evidence-ref"):
            reporter.error("phase5-mapping-evidence-ref-drift", mapping_path, f"{atom_id} 的 evidence-ref 与 global index不一致")
        if evidence:
            for field in ("source-document", "line-ranges"):
                if row.get(field) != evidence.get(field):
                    reporter.error(
                        "phase5-mapping-source-drift",
                        mapping_path,
                        f"{atom_id} 的 {field} 与 resolved evidence不一致",
                    )
            check_source_fact_quote(
                mapping_path,
                reporter,
                evidence.get("source-fact"),
                evidence.get("line-ranges"),
                str(evidence.get("source-document", "")),
                repo_root,
                atom_id,
            )
        relation = str(row.get("final-relation", ""))
        projection = str(row.get("final-artifact-projection", ""))
        impact = normalize_code(row.get("final-capability-impact"))
        target = normalize_code(row.get("final-target-capability"))
        related = validate_related_capabilities(
            row,
            "related-capabilities",
            target,
            orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json",
            reporter,
            atom_id,
        )
        if impact not in TERMINAL_CAPABILITY_IMPACTS:
            reporter.error(
                "phase5-capability-impact",
                orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json",
                f"{atom_id} 的 terminal capability impact 非法或尚未消解：{impact}",
            )
        if row.get("final-owner-type") == "foundation-reference" or relation == "foundation-reference":
            reporter.error("phase5-foundation-reference-deprecated", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} 不得使用 foundation-reference owner/relation")
        if row.get("foundation-reference-id") not in {None, "", "None"}:
            reporter.error("phase5-foundation-reference-deprecated", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} 不得设置 foundation-reference-id")
        if relation == "direct":
            if projection not in DIRECT_PROJECTIONS:
                reporter.error("phase5-direct-projection", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} direct 使用了非法 projection {projection}")
            if row.get("final-owner-type") != EXECUTABLE_OWNER_TYPE:
                reporter.error(
                    "phase5-direct-owner-type",
                    orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json",
                    f"{atom_id} direct 的 final-owner-type 必须是 {EXECUTABLE_OWNER_TYPE}",
                )
            if is_no_owner(row.get("final-owner-change")):
                reporter.error("phase5-direct-owner", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} direct 缺少 final owner Change")
            if impact in BUSINESS_CAPABILITY_IMPACTS:
                if projection not in SPEC_PROJECTIONS:
                    reporter.error("phase5-capability-projection", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} 使用 new/modified 时必须采用 spec projection")
                if is_no_owner(target) or target == "unresolved" or not KEBAB_CASE_RE.match(target):
                    reporter.error("phase5-capability-target", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} 使用 new/modified 时必须指定 target Capability")
                elif target == "candidate-new-capability":
                    reporter.error("phase5-capability-target", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} 必须在终态输出前消解 candidate-new-capability")
            elif impact == "none":
                if target != "none":
                    reporter.error("phase5-capability-target", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} 使用 impact=none 时必须使用 target=none")
                if projection in SPEC_PROJECTIONS:
                    reporter.error("phase5-spec-impact", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} direct spec atom 必须使用 new/modified")
            elif impact == FOUNDATION_IMPACT:
                if target != FOUNDATION_CAPABILITY:
                    reporter.error("phase5-foundation-impact", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} 使用 foundation-substrate 时必须指定 runtime target")
            if projection in CHANGE_ONLY_PROJECTIONS and impact not in {"none", FOUNDATION_IMPACT}:
                reporter.error("phase5-change-only-impact", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} 的 {projection} 必须是 change-only")
        else:
            if impact != "none" or target != "none":
                reporter.error("phase5-non-direct-capability", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"{atom_id} 的 non-direct row 必须使用 impact=none、target=none")
    validate_mapping_mirror(orchestrate_dir, reporter)
    validate_final_packets(orchestrate_dir, repo_root, reporter, mapping)
    if (orchestrate_dir / "foundation-reference").exists():
        reporter.error("phase5-foundation-reference-deprecated", orchestrate_dir / "foundation-reference", "foundation-reference 输出已废弃；Phase 5 必须改为输出 executable foundation packet")

    if complete:
        status = str(trace.get("status", ""))
        if status not in {"accepted", "adjusted"}:
            reporter.error("phase5-complete-status", orchestrate_dir / "trace/phase-5.trace.json", f"--complete 要求 accepted/adjusted status，实际为 {status}")
        anchors_index = orchestrate_dir / "change-capability-anchors/index.md"
        if not anchors_index.exists():
            reporter.error("phase5-complete-packets", anchors_index, "缺少 final change-capability anchor index")


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
