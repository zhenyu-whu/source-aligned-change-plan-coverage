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
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    SOURCE_REMAINDER_REVIEW_SCHEMA,
    SOURCE_TO_GLOBAL_MAP_SCHEMA,
    SOURCE_WINDOW_INDEX_SCHEMA,
    TRACE_CONTRACT_VERSION,
    IssueReporter,
    cell,
    coverage_file_name,
    extract_ga_ids,
    line_range_label,
    line_ranges_label,
    merge_line_ranges,
    parse_line_ranges,
    range_covered_by,
    read_json,
    sha256_file,
    source_atom_file_name,
    source_line_count,
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
    render_remainder_review,
    render_source_map,
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
PHASE2_DIRECT_CANDIDATE_STATUSES = {
    "direct-candidate",
    "candidate-new-change",
    "candidate-new-capability",
    "unassigned",
}
PHASE2_NON_DIRECT_STATUSES = {
    "contextual-candidate",
    "reference-only",
    "prototype-only-not-production",
    "superseded",
    "duplicate-candidate",
    "no-product-or-system-impact",
}
PHASE3_DIRECT_STATUSES = {"direct", "direct-candidate"}
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
    "phase-3": {"coverage-complete", "blocked"},
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


def validate_phase2_capability_status(
    row: Dict[str, object],
    path: Path,
    reporter: IssueReporter,
    context: str,
) -> None:
    status = normalize_code(row.get("candidate-status"))
    projection = normalize_code(row.get("candidate-artifact-projection"))
    impact = normalize_code(row.get("candidate-capability-impact"))
    target = normalize_code(row.get("candidate-target-capability"))
    if status in PHASE2_NON_DIRECT_STATUSES and (impact != "none" or target != "none"):
        reporter.error("phase2-non-direct-capability", path, f"{context} 的 non-direct/contextual row 必须使用 impact=none、target=none")
    if status in PHASE2_DIRECT_CANDIDATE_STATUSES and projection in SPEC_PROJECTIONS:
        if impact not in {*BUSINESS_CAPABILITY_IMPACTS, "unresolved"}:
            reporter.error("phase2-direct-spec-impact", path, f"{context} 的 direct spec candidate 必须使用 new、modified 或 unresolved")
    if status == "candidate-new-capability" and impact != "new":
        reporter.error("phase2-new-capability-impact", path, f"{context} 的 candidate-new-capability 必须使用 impact=new")
    if target == "candidate-new-capability":
        if impact != "new":
            reporter.error("phase2-new-capability-impact", path, f"{context} 的 candidate-new-capability target 必须使用 impact=new")
        if projection not in SPEC_PROJECTIONS:
            reporter.error("phase2-new-capability-projection", path, f"{context} 的 candidate-new-capability target 必须采用 spec projection")


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
            orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json",
            SOURCE_TO_GLOBAL_MAP_SCHEMA,
            "phase-3",
        ),
        (
            orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-remainder-review.json",
            SOURCE_REMAINDER_REVIEW_SCHEMA,
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
    phase5_status = phase_status_value(phase_statuses.get("phase-5"))
    if complete and phase5_status not in FINAL_PHASE5_STATUSES:
        reporter.error(
            "manifest-phase5-complete-status",
            path,
            f"--complete 要求 phase-statuses.phase-5 为 accepted/adjusted，实际为 {phase5_status or 'missing'}",
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


def load_phase2_atoms(orchestrate_dir: Path, reporter: IssueReporter) -> Dict[str, Dict[str, object]]:
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    all_atoms: Dict[str, Dict[str, object]] = {}
    for sidecar in sorted(atom_root.glob("*.atoms.json")):
        data = json_obj(sidecar, reporter, SOURCE_ATOMS_SCHEMA)
        for row in data.get("source-atoms", []) if isinstance(data.get("source-atoms"), list) else []:
            if not isinstance(row, dict):
                reporter.error("phase2-source-atom-row", sidecar, "source-atoms item 必须是 object")
                continue
            atom_id = str(row.get("source-atom-id", ""))
            source_document = str(row.get("source-document", ""))
            key = f"{source_document}::{atom_id}"
            if key in all_atoms:
                reporter.error("phase2-source-atom-duplicate", sidecar, f"Phase 2 source atom row 重复：{key}")
            all_atoms[key] = row
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
    if trace:
        validate_trace_status(trace, trace_path, reporter, "phase-2", "phase2-status")
    require_file(orchestrate_dir / "phase-works/phase-2/source-obligation-atoms/work-queue.md", reporter, "phase2-interface-artifact", "缺少 Phase 2 work queue")
    require_file(orchestrate_dir / "phase-works/phase-2/source-obligation-atoms/index.md", reporter, "phase2-interface-artifact", "缺少 Phase 2 atom index")
    require_file(orchestrate_dir / "phase-works/phase-2/phase-2-agent-report.md", reporter, "phase2-interface-artifact", "缺少 Phase 2 agent 报告")
    sources = phase1_sources(orchestrate_dir, repo_root)
    queue_counts = work_queue_counts(orchestrate_dir)
    for source in sources:
        if not isinstance(source, dict) or source.get("read-status") != "read-full":
            continue
        source_document = str(source.get("source-document", ""))
        count = queue_counts.get(source_document, 0)
        if count != 1:
            reporter.error("phase2-work-queue-coverage", trace_path, f"{source_document} 在 Phase 2 work queue 中出现了 {count} 次")
        sidecar = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms" / source_atom_file_name(source_document).replace(".md", ".json")
        data = json_obj(sidecar, reporter, SOURCE_ATOMS_SCHEMA)
        if not data:
            continue
        if data.get("source-document") != source_document:
            reporter.error("phase2-source-document", sidecar, "source-document 与 Phase 1 manifest 不一致")
        source_path = repo_root / source_document
        if source_path.exists() and data.get("source-sha256") != sha256_file(source_path):
            reporter.error("phase2-source-sha", sidecar, f"{source_document} 的 source-sha256 发生 drift")
        atoms = data.get("source-atoms")
        if not isinstance(atoms, list):
            reporter.error("phase2-source-atoms", sidecar, "source-atoms 必须是 array")
            continue
        for row in atoms:
            if not isinstance(row, dict):
                reporter.error("phase2-source-atom-row", sidecar, "source-atoms item 必须是 object")
                continue
            context = str(row.get("source-atom-id", ""))
            reject_legacy_capability_fields(row, sidecar, reporter, context or "source atom")
            if not context:
                reporter.error("phase2-source-atom-id", sidecar, "必须提供 source-atom-id")
            check_ranges(sidecar, reporter, row.get("line-ranges"), source_document, repo_root, context)
            projection = str(row.get("candidate-artifact-projection", ""))
            status = str(row.get("candidate-status", ""))
            if not projection:
                reporter.error("phase2-projection", sidecar, f"{context} 的 candidate-artifact-projection 为空")
            if status == "direct-candidate" and projection == "contextual-only":
                reporter.error("phase2-direct-contextual-only", sidecar, f"{context} 是 direct-candidate，却使用了 contextual-only")
            if status == "direct-candidate" and is_no_owner(row.get("candidate-owner-change")):
                reporter.error("phase2-direct-change-owner", sidecar, f"{context} 的 direct-candidate 必须指定 candidate owner Change 或 unassigned 标记")
            validate_capability_contract(
                row,
                impact_field="candidate-capability-impact",
                target_field="candidate-target-capability",
                related_field="candidate-related-capabilities",
                projection_field="candidate-artifact-projection",
                allowed_impacts=NON_TERMINAL_CAPABILITY_IMPACTS,
                path=sidecar,
                reporter=reporter,
                context=context,
                rationale_field="rationale",
            )
            validate_phase2_capability_status(row, sidecar, reporter, context)
            if status == "candidate-new-capability" and projection not in SPEC_PROJECTIONS:
                reporter.error(
                    "phase2-new-capability-projection",
                    sidecar,
                    f"{context} 的 candidate-new-capability 必须采用 spec projection",
                )
    validate_phase2_mirror(orchestrate_dir, reporter)


def load_global_atoms(orchestrate_dir: Path, reporter: IssueReporter) -> Dict[str, Dict[str, object]]:
    path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    data = json_obj(path, reporter, GLOBAL_ATOM_INDEX_SCHEMA)
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


def validate_source_map_mirror(orchestrate_dir: Path, reporter: IssueReporter) -> None:
    json_path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json"
    md_path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.md"
    if not json_path.exists():
        return
    validate_rendered_markdown(
        orchestrate_dir,
        json_path,
        md_path,
        render_source_map,
        reporter,
        "phase3-source-map",
    )


def validate_remainder_review_mirror(orchestrate_dir: Path, reporter: IssueReporter) -> None:
    json_path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-remainder-review.json"
    md_path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-remainder-review.md"
    if not json_path.exists():
        return
    validate_rendered_markdown(
        orchestrate_dir,
        json_path,
        md_path,
        render_remainder_review,
        reporter,
        "phase3-remainder-review",
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


def phase2_evidence_ranges(orchestrate_dir: Path, source_document: str) -> tuple[List[Dict[str, int]], List[str]]:
    sidecar = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms" / source_atom_file_name(source_document).replace(".md", ".json")
    if not sidecar.exists():
        return [], []
    try:
        data = read_json(sidecar)
    except Exception:  # noqa: BLE001
        return [], []

    ranges: List[Dict[str, int]] = []
    origins: List[str] = []
    for collection, id_key in (("source-atoms", "source-atom-id"), ("source-anchors", "anchor")):
        rows = data.get(collection)
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            row_ranges = valid_range_items(row.get("line-ranges"))
            if not row_ranges:
                continue
            ranges.extend(row_ranges)
            origin = normalize_code(row.get(id_key) or row.get("source-atom-ids") or f"{collection}[{index}]")
            if origin:
                origins.append(origin)
    return merge_line_ranges(ranges), origins


def validate_phase3_manifest_and_coverage(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    manifest_path = orchestrate_dir / "phase-works/phase-3/source-doc-manifest.md"
    rows = table_rows(manifest_path, ["Source Document", "Classification", "Review File"])
    seen: Set[str] = set()
    for raw in rows:
        source_document = normalize_code(cell(raw, "Source Document"))
        if not source_document:
            continue
        if source_document in seen:
            reporter.error("phase3-manifest-duplicate", manifest_path, f"Phase 3 来源文档重复：{source_document}")
        seen.add(source_document)
        review_file = normalize_code(cell(raw, "Review File"))
        if review_file:
            review_path = repo_root / review_file
        else:
            review_path = orchestrate_dir / "phase-works/phase-3/source-doc-coverage" / coverage_file_name(source_document)
        if not review_path.exists():
            reporter.error("phase3-coverage-file", manifest_path, f"{source_document} 缺少 coverage 文件：{review_path}")

    for source_document in read_full_sources(orchestrate_dir, repo_root):
        if source_document not in seen:
            reporter.error("phase3-manifest-coverage", manifest_path, f"Phase 3 manifest 缺少 read-full 来源：{source_document}")


def production_obligation_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = normalize_code(value).lower()
    return text in {
        "true",
        "yes",
        "y",
        "1",
        "production",
        "production-obligation",
        "obligation-bearing",
        "meaningful-production-obligation",
    }


def validate_remainder_audit_documents(
    remainder_path: Path,
    reporter: IssueReporter,
    audit_documents: object,
    expected_by_source: Dict[str, List[Dict[str, int]]],
    evidence_by_source: Dict[str, List[Dict[str, int]]],
    repo_root: Path,
) -> None:
    if not isinstance(audit_documents, list):
        reporter.error("phase3-remainder-audit-documents", remainder_path, "audit-documents 必须是 array")
        return
    by_source: Dict[str, Dict[str, object]] = {}
    for item in audit_documents:
        if not isinstance(item, dict):
            reporter.error("phase3-remainder-audit-documents", remainder_path, "audit-documents item 必须是 object")
            continue
        source_document = str(item.get("source-document", ""))
        if source_document:
            by_source[source_document] = item

    for source_document, expected_uncovered in expected_by_source.items():
        item = by_source.get(source_document)
        if not item:
            reporter.error("phase3-remainder-audit-document", remainder_path, f"缺少 {source_document} 的审计文档")
            continue
        line_count = source_line_count(repo_root, source_document)
        if line_count is not None and item.get("line-count") != line_count:
            reporter.error("phase3-remainder-audit-drift", remainder_path, f"{source_document} 的 line-count 发生 drift")
        source_path = repo_root / source_document
        if source_path.exists() and item.get("source-sha256") != sha256_file(source_path):
            reporter.error("phase3-remainder-audit-drift", remainder_path, f"{source_document} 的 source-sha256 发生 drift")

        actual_uncovered = merge_line_ranges(
            range_item
            for row in item.get("candidate-uncovered-ranges", [])
            if isinstance(row, dict)
            for range_item in valid_range_items(row.get("line-ranges"))
        )
        if actual_uncovered != merge_line_ranges(expected_uncovered):
            reporter.error(
                "phase3-remainder-audit-drift",
                remainder_path,
                f"{source_document} 的 candidate-uncovered-ranges 发生 drift；期望 {line_ranges_label(expected_uncovered)}",
            )

        actual_evidence = merge_line_ranges(
            range_item
            for row in item.get("evidence-ranges", [])
            if isinstance(row, dict)
            for range_item in valid_range_items(row.get("line-ranges"))
        )
        if actual_evidence and actual_evidence != merge_line_ranges(evidence_by_source.get(source_document, [])):
            reporter.error(
                "phase3-remainder-audit-drift",
                remainder_path,
                f"{source_document} 的 evidence-ranges 发生 drift；期望 {line_ranges_label(evidence_by_source.get(source_document, []))}",
            )


def validate_phase3_remainder_review(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
    global_atoms: Dict[str, Dict[str, object]],
    phase3_decision: str,
) -> None:
    remainder_path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-remainder-review.json"
    data = json_obj(remainder_path, reporter, SOURCE_REMAINDER_REVIEW_SCHEMA)
    if not data:
        return

    evidence_by_source: Dict[str, List[Dict[str, int]]] = {}
    uncovered_by_source: Dict[str, List[Dict[str, int]]] = {}
    for source_document in read_full_sources(orchestrate_dir, repo_root):
        sidecar = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms" / source_atom_file_name(source_document).replace(".md", ".json")
        if not sidecar.exists():
            reporter.error("phase3-phase2-source-atoms", remainder_path, f"{source_document} 缺少 Phase 2 source atom sidecar")
        evidence_ranges, _ = phase2_evidence_ranges(orchestrate_dir, source_document)
        line_count = source_line_count(repo_root, source_document)
        if line_count is None:
            reporter.error("phase3-source-exists", remainder_path, f"缺少来源文档：{source_document}")
            line_count = 0
        evidence_by_source[source_document] = evidence_ranges
        uncovered_by_source[source_document] = uncovered_line_ranges(evidence_ranges, line_count)

    validate_remainder_audit_documents(
        remainder_path,
        reporter,
        data.get("audit-documents"),
        uncovered_by_source,
        evidence_by_source,
        repo_root,
    )

    rows = data.get("rows")
    if not isinstance(rows, list):
        reporter.error("phase3-remainder-rows", remainder_path, "rows 必须是 array")
        rows = []

    review_ranges_by_source: Dict[str, List[Dict[str, int]]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            reporter.error("phase3-remainder-row", remainder_path, "rows item 必须是 object")
            continue
        source_document = str(row.get("source-document", ""))
        context = f"{source_document}::{row.get('lines', '') or index}"
        check_ranges(remainder_path, reporter, row.get("line-ranges"), source_document, repo_root, context)
        row_ranges = valid_range_items(row.get("line-ranges"))
        review_ranges_by_source.setdefault(source_document, []).extend(row_ranges)

        linked_ids = row.get("linked-global-atom-ids")
        if not isinstance(linked_ids, list):
            reporter.error("phase3-remainder-linked-ga", remainder_path, f"{context} 的 linked-global-atom-ids 必须是 array")
            linked_ids = []
        for atom_id in linked_ids:
            if atom_id not in global_atoms:
                reporter.error("phase3-remainder-unknown-ga", remainder_path, f"{context} 引用了未知的 {atom_id}")

        blocker = squash(row.get("blocker", ""))
        non_coverage = squash(row.get("non-coverage-status", ""))
        if production_obligation_value(row.get("production-obligation")) and not linked_ids and not blocker:
            reporter.error("phase3-remainder-outcome", remainder_path, f"{context} 的 production obligation 必须关联 GA 或提供 blocker")
        if not linked_ids and not non_coverage and not blocker:
            reporter.error("phase3-remainder-outcome", remainder_path, f"{context} 必须提供关联 GA、non-coverage status 或 blocker")
        if blocker and phase3_decision == "coverage-complete":
            reporter.error("phase3-remainder-blocker-complete", remainder_path, f"{context} 在 coverage-complete 状态下仍有 blocker")

    for source_document, uncovered_ranges in uncovered_by_source.items():
        review_ranges = review_ranges_by_source.get(source_document, [])
        for candidate in uncovered_ranges:
            if not range_covered_by(candidate, review_ranges):
                reporter.error(
                    "phase3-remainder-coverage",
                    remainder_path,
                    f"{source_document} 的未覆盖 range {line_range_label(candidate)} 未在 source-remainder-review.json 中审阅",
                )


def validate_phase_3(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    require_file(
        orchestrate_dir / "phase-works/phase-1/initial-change-plan.md",
        reporter,
        "phase3-interface-input",
        "缺少 Phase 3 输入：Phase 1 initial-change-plan.md",
    )
    phase3_trace = json_obj(orchestrate_dir / "trace/phase-3.trace.json", reporter, PHASE_TRACE_SCHEMAS["phase-3"])
    phase3_decision = ""
    if phase3_trace:
        phase3_decision = validate_trace_status(
            phase3_trace,
            orchestrate_dir / "trace/phase-3.trace.json",
            reporter,
            "phase-3",
            "phase3-status",
        )
    require_file(orchestrate_dir / "phase-works/phase-3/coverage-review.md", reporter, "phase3-interface-artifact", "缺少 Phase 3 coverage review")
    require_file(orchestrate_dir / "phase-works/phase-3/phase-3-agent-report.md", reporter, "phase3-interface-artifact", "缺少 Phase 3 agent 报告")
    require_file(orchestrate_dir / "phase-works/phase-3/phase-3-trace/duplicate-ownership-review.md", reporter, "phase3-interface-artifact", "缺少 Phase 3 duplicate ownership review")
    require_file(orchestrate_dir / "phase-works/phase-3/phase-3-trace/atom-normalization-decision-log.md", reporter, "phase3-interface-artifact", "缺少 Phase 3 normalization decision log")
    validate_phase3_manifest_and_coverage(orchestrate_dir, repo_root, reporter)
    global_atoms = load_global_atoms(orchestrate_dir, reporter)
    index_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    for atom_id, row in global_atoms.items():
        reject_legacy_capability_fields(row, index_path, reporter, atom_id)
        source_document = str(row.get("source-document", ""))
        check_ranges(index_path, reporter, row.get("line-ranges"), source_document, repo_root, atom_id)
        projection = str(row.get("artifact-projection", ""))
        status = str(row.get("coverage-status", ""))
        if not projection:
            reporter.error("phase3-projection", index_path, f"{atom_id} 的 artifact-projection 为空")
        if status in {"direct", "direct-candidate"} and projection == "contextual-only":
            reporter.error("phase3-direct-contextual-only", index_path, f"{atom_id} 是 direct，却使用了 contextual-only")
        if status in {"direct", "direct-candidate"} and is_no_owner(row.get("owner-change")):
            reporter.error("phase3-direct-change-owner", index_path, f"{atom_id} direct atom 必须提供 owner-change 或 phase-5-refit-required")
        validate_capability_contract(
            row,
            impact_field="capability-impact",
            target_field="target-capability",
            related_field="related-capabilities",
            projection_field="artifact-projection",
            allowed_impacts=NON_TERMINAL_CAPABILITY_IMPACTS,
            path=index_path,
            reporter=reporter,
            context=atom_id,
            rationale_field="review-judgment",
        )
        impact = normalize_code(row.get("capability-impact"))
        target = normalize_code(row.get("target-capability"))
        if target == "candidate-new-capability":
            reporter.error(
                "phase3-capability-target-placeholder",
                index_path,
                f"{atom_id} 的 Phase 3 target 必须将 candidate-new-capability 消解为具体 Capability 或 unresolved",
            )
        if status not in PHASE3_DIRECT_STATUSES and (impact != "none" or target != "none"):
            reporter.error(
                "phase3-non-direct-capability",
                index_path,
                f"{atom_id} 的 non-direct/contextual row 必须使用 impact=none、target=none",
            )
        if status in PHASE3_DIRECT_STATUSES and projection in SPEC_PROJECTIONS:
            if impact not in {*BUSINESS_CAPABILITY_IMPACTS, "unresolved"}:
                reporter.error(
                    "phase3-direct-spec-impact",
                    index_path,
                    f"{atom_id} direct spec atom 必须使用 new、modified 或 unresolved",
                )

    map_path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json"
    data = json_obj(map_path, reporter, SOURCE_TO_GLOBAL_MAP_SCHEMA)
    phase2_atoms = load_phase2_atoms(orchestrate_dir, reporter)
    mapped_keys: Set[str] = set()
    rows = data.get("rows")
    if not isinstance(rows, list):
        reporter.error("phase3-map-rows", map_path, "rows 必须是 array")
        rows = []
    for row in rows:
        if not isinstance(row, dict):
            reporter.error("phase3-map-row", map_path, "rows item 必须是 object")
            continue
        source_document = str(row.get("source-document", ""))
        atom_id = str(row.get("source-atom-id", ""))
        reject_legacy_capability_fields(row, map_path, reporter, f"{source_document}::{atom_id}")
        source_key = f"{source_document}::{atom_id}"
        mapped_keys.add(source_key)
        phase2_row = phase2_atoms.get(source_key)
        if phase2_row:
            for field in (
                "candidate-status",
                "candidate-artifact-projection",
                "candidate-owner-change",
                "candidate-capability-impact",
                "candidate-target-capability",
                "candidate-related-capabilities",
            ):
                if row.get(field) != phase2_row.get(field):
                    reporter.error(
                        "phase3-map-candidate-drift",
                        map_path,
                        f"{source_key} 的 {field} 与不可变的 Phase 2 evidence 不一致",
                    )
        populated = [
            key
            for key in ("global-atom-id", "global-relation", "non-coverage-status", "blocker")
            if row.get(key)
        ]
        if len(populated) != 1:
            reporter.error("phase3-map-exclusive", map_path, f"{source_document}::{atom_id} 必须且只能设置一个 mapping outcome")
        if row.get("global-atom-id") and row.get("global-atom-id") not in global_atoms:
            reporter.error("phase3-map-unknown-ga", map_path, f"{atom_id} 映射到了未知的 {row.get('global-atom-id')}")
        validate_capability_contract(
            row,
            impact_field="candidate-capability-impact",
            target_field="candidate-target-capability",
            related_field="candidate-related-capabilities",
            projection_field="candidate-artifact-projection",
            allowed_impacts=NON_TERMINAL_CAPABILITY_IMPACTS,
            path=map_path,
            reporter=reporter,
            context=f"{source_document}::{atom_id}",
            rationale_field="reason",
        )
        validate_phase2_capability_status(
            row,
            map_path,
            reporter,
            f"{source_document}::{atom_id}",
        )
        global_atom_id = str(row.get("global-atom-id", ""))
        if global_atom_id in global_atoms:
            global_row = global_atoms[global_atom_id]
            expected = {
                "global-capability-impact": global_row.get("capability-impact"),
                "global-target-capability": global_row.get("target-capability"),
                "global-related-capabilities": global_row.get("related-capabilities"),
            }
            for field, value in expected.items():
                if row.get(field) != value:
                    reporter.error(
                        "phase3-map-capability-drift",
                        map_path,
                        f"{source_document}::{atom_id} 的 {field} 与 {global_atom_id} 不一致",
                    )
        check_ranges(map_path, reporter, row.get("line-ranges"), source_document, repo_root, atom_id)

    for key in phase2_atoms:
        if key not in mapped_keys:
            reporter.error("phase3-map-coverage", map_path, f"source-to-global map 缺少 Phase 2 atom/context row：{key}")
    validate_global_index_mirror(orchestrate_dir, reporter)
    validate_source_map_mirror(orchestrate_dir, reporter)
    validate_phase3_remainder_review(orchestrate_dir, repo_root, reporter, global_atoms, phase3_decision)
    validate_remainder_review_mirror(orchestrate_dir, reporter)


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
    index_path = orchestrate_dir / "phase-works/phase-4/source-window-dossiers/source-window-index.json"
    data = json_obj(index_path, reporter, SOURCE_WINDOW_INDEX_SCHEMA)
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
    for row in windows:
        if not isinstance(row, dict):
            reporter.error("phase4-window-row", index_path, "windows item 必须是 object")
            continue
        window_id = str(row.get("window-id", ""))
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
        ids = row.get("linked-global-atom-ids")
        if not isinstance(ids, list) or not ids:
            reporter.error("phase4-linked-ga", index_path, f"{window_id} 的 linked-global-atom-ids 必须非空")
        else:
            for atom_id in ids:
                if atom_id not in global_atoms:
                    reporter.error("phase4-linked-ga", index_path, f"{window_id} 引用了未知的 {atom_id}")


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
        for atom_id in non_direct_ids:
            if atom_id not in text:
                reporter.error("phase5-final-non-direct-packet", packet_path, f"final packet 缺少 owner-scoped non-direct atom {atom_id}")

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
    mapping = load_mapping(orchestrate_dir, reporter)
    missing = sorted(set(global_atoms) - set(mapping))
    extra = sorted(set(mapping) - set(global_atoms))
    if missing:
        reporter.error("phase5-mapping-coverage", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"mapping 缺少 global atom：{', '.join(missing[:12])}")
    if extra:
        reporter.error("phase5-mapping-extra", orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", f"mapping 包含未知 global atom：{', '.join(extra[:12])}")
    for atom_id, row in mapping.items():
        reject_legacy_capability_fields(
            row,
            orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json",
            reporter,
            atom_id,
        )
        source_document = str(row.get("source-document", ""))
        check_ranges(orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json", reporter, row.get("line-ranges"), source_document, repo_root, atom_id)
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

    for raw in table_rows(orchestrate_dir / "phase-works/phase-5/change-complexity-review.md", ["Change", "Budget Status"]):
        budget = normalize_code(cell(raw, "Budget Status"))
        if budget in {"over-budget-reviewed", "hard-over-budget", "above-target-reviewed"}:
            reporter.warning("phase5-over-budget-review", orchestrate_dir / "phase-works/phase-5/change-complexity-review.md", f"{normalize_code(cell(raw, 'Change'))} 的 budget status 为 {budget}；必须提供 reviewer 判断")

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
