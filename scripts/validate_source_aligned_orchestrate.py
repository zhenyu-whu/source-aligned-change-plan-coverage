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
    FINAL_PACKET_INDEX_SCHEMA,
    FRAMEWORK_REFIT_TRACE_SCHEMA,
    GLOBAL_ATOM_ID_RE,
    GLOBAL_ATOM_INDEX_SCHEMA,
    KEBAB_CASE_RE,
    MANIFEST_SCHEMA,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    IssueReporter,
    cell,
    line_range_label,
    merge_line_ranges,
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
    build_baseline as build_phase5_baseline,
    load_framework_refit,
    load_evidence as load_phase5_evidence,
    load_mapping as load_phase5_mapping,
    parse_final_plan,
    render_anchor_index,
    render_capability_view,
    render_packet,
    validate_framework_refit,
    validate_refit_mapping_crosscheck,
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
PHASE3_DISPOSITIONS = {"missing-obligation", "safe-non-obligation", "requires-reextract", "blocked"}
LEGACY_CAPABILITY_FIELDS = {
    "candidate-owner-capability",
    "owner-capability",
    "final-owner-capability",
    "capability-advancement",
}
PHASE_NAMES = ("phase-1", "phase-2", "phase-3", "phase-4", "phase-5")
FINAL_PHASE5_STATUSES = {"accepted", "adjusted"}
NON_FINAL_PHASE4_STATUSES = {"needs-coverage-recheck", "blocked"}
NON_FINAL_PHASE5_STATUSES = {"needs-coverage-recheck", "blocked"}
PHASE_ALLOWED_TRACE_STATUSES = {
    "phase-1": {"initial-plan-written"},
    "phase-2": {"source-atoms-written"},
    "phase-3": {"coverage-complete", "needs-extraction-recheck", "blocked"},
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
    status = validate_trace_status(phase4_trace, phase4_trace_path, reporter, "phase-4", "phase4-status") if phase4_trace else ""
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
            {"trace-schema", "trace-contract-version", "status", "issues"},
            phase4_trace_path,
            reporter,
            "phase4-trace-fields",
            "nonterminal phase-4 trace",
        )
        if not isinstance(phase4_trace.get("issues"), list) or not phase4_trace.get("issues"):
            reporter.error("phase4-trace-issues", phase4_trace_path, f"{status}状态要求非空issues[]")
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
        {"trace-schema", "trace-contract-version", "status", "assembled"},
        phase4_trace_path,
        reporter,
        "phase4-trace-fields",
        "assembled phase-4 trace",
    )
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
    try:
        validate_framework_refit(orchestrate_dir, data, final_changes, final_capabilities, final_overlay)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        reporter.error("phase5-refit-contract", refit_path, str(exc))
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
        validate_phase5_mapping(evidence, mapping, changes, capabilities, overlay)
        refit = load_framework_refit(work / "framework-refit-trace.json")
        validate_refit_mapping_crosscheck(refit, mapping)
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
            "nonterminal phase-5 trace",
        )
        review_path = work / "plan-refit-review.md"
        refit_path = work / "framework-refit-trace.json"
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
            refit_data = read_json(refit_path)
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
            "trace-schema", "trace-contract-version", "status",
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
