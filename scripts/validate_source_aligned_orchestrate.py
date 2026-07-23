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
    ATOM_PLAN_MAPPING_TOP_LEVEL_FIELDS,
    CAPABILITY_BASELINE_SCHEMA,
    DELIVERY_DIRECTIVES,
    DIRECT_PROJECTIONS,
    EVIDENCE_COLLECTION_INDEX_SCHEMA,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
    FINAL_INTEGRATION_REVIEW_SCHEMA,
    FINAL_PACKET_INDEX_SCHEMA,
    FINAL_ROADMAP_SCHEMA,
    FRAMEWORK_REFIT_TRACE_SCHEMA,
    GLOBAL_ATOM_ID_RE,
    GLOBAL_ATOM_INDEX_SCHEMA,
    KEBAB_CASE_RE,
    INITIAL_FRAMEWORK_SCHEMA,
    MANIFEST_SCHEMA,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    PHASE1_REVIEW_CHECKS,
    PHASE5_REVIEW_CHECKS,
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    WORKFLOW_COMPLETION_SCHEMA,
    first_symlink_in_repo_path,
    lexical_repo_relative_path as lexical_rel,
    IssueReporter,
    atom_plan_mapping_markdown_path,
    cell,
    evidence_authority_sha256,
    line_range_label,
    merge_line_ranges,
    range_covered_by,
    read_json,
    require_phase3_frozen_evidence,
    sha256_file,
    source_atom_file_name,
    source_line_count,
    repo_relative_path,
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
    render_final_integration_review,
    render_initial_framework,
)
from phase5_plan_refit import (
    build_baseline as build_phase5_baseline,
    load_framework_refit,
    load_evidence as load_phase5_evidence,
    load_final_roadmap_defs,
    parse_mapping_rows as parse_phase5_mapping_rows,
    render_anchor_index,
    render_capability_slice,
    render_change_source,
    render_final_plan_from_roadmap,
    phase5_candidate_authority,
    phase5_bounded_review_issues,
    validate_phase5_review_gate,
    validate_framework_refit,
    validate_gap_framework_impacts,
    validate_mapping as validate_phase5_mapping,
)
from source_aligned_v7_contract import (
    load_final_integration_review_attempt,
    load_final_integration_review_attempt_result,
    load_final_integration_review,
    load_final_roadmap,
    load_initial_framework,
    load_workflow_completion,
    terminal_authority_payload,
    terminal_authority_sha256,
)

NO_OWNER_VALUES = {"", "None", "none", "null", "NULL"}
SPEC_PROJECTIONS = {"spec-requirement", "spec-guard"}
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
    "delivery-directives",
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
NON_FINAL_PHASE5_STATUSES = {"blocked"}
PHASE_ALLOWED_TRACE_STATUSES = {
    "phase-1": {"review-pending", "initial-plan-written", "blocked"},
    "phase-2": {"source-atoms-written", "blocked"},
    "phase-3": {"review-pending", "coverage-complete", "blocked"},
    "phase-4": {"assembled", *NON_FINAL_PHASE4_STATUSES},
    "phase-5": {
        *FINAL_PHASE5_STATUSES,
        *NON_FINAL_PHASE5_STATUSES,
        "review-pending",
    },
}
WORKFLOW_PHASE_STATUS_VALUES = {
    "present",
    "reviewer-passed",
    "validator-passed",
    "repair-not-needed",
}
DELIVERY_DIRECTIVE_ORDER = (
    "milestone-scope",
    "explicit-precedence",
    "explicit-deferred",
)


def _delivery_directives_are_canonical(value: object) -> bool:
    """Require the v7 source-facing enum and its declared semantic order."""
    if not isinstance(value, list):
        return False
    if any(not isinstance(item, str) or item not in DELIVERY_DIRECTIVES for item in value):
        return False
    if len(value) != len(set(value)):
        return False
    return value == [directive for directive in DELIVERY_DIRECTIVE_ORDER if directive in value]


def _delivery_directive_summary(
    rows: Iterable[Dict[str, object]],
) -> tuple[int, Dict[str, int]]:
    """Mechanically count directive-bearing occurrences and each directive."""
    directive_counts = {directive: 0 for directive in DELIVERY_DIRECTIVE_ORDER}
    directive_atom_count = 0
    for row in rows:
        directives = row.get("delivery-directives")
        if not isinstance(directives, list) or not directives:
            continue
        directive_atom_count += 1
        for directive in directives:
            if directive in directive_counts:
                directive_counts[directive] += 1
    return directive_atom_count, directive_counts


def rel(path: Path, repo_root: Path) -> str:
    """Backward-compatible local alias for the shared canonical path helper."""
    return repo_relative_path(path, repo_root)


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


def expected_manifest_artifacts(
    orchestrate_dir: Path,
    repo_root: Path,
    *,
    include_workflow_artifacts: bool = True,
) -> Dict[str, Tuple[str, str, str, str]]:
    specs: List[Tuple[Path, str, str, str, str]] = [
        (
            orchestrate_dir / "phase-works/phase-1/initial-framework.json",
            INITIAL_FRAMEWORK_SCHEMA,
            "phase-1",
            "semantic",
            "initial-framework",
        ),
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
            orchestrate_dir / "phase-works/phase-5/final-roadmap.json",
            FINAL_ROADMAP_SCHEMA,
            "phase-5",
            "semantic",
            "final-roadmap",
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
    if include_workflow_artifacts:
        specs.extend(
            (
                (
                    orchestrate_dir / "final-integration-review.json",
                    FINAL_INTEGRATION_REVIEW_SCHEMA,
                    "workflow",
                    "semantic",
                    "final-integration-review",
                ),
                (
                    orchestrate_dir
                    / FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH,
                    FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
                    "workflow",
                    "control",
                    "final-integration-review-attempt",
                ),
                (
                    orchestrate_dir
                    / FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH,
                    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA,
                    "workflow",
                    "control",
                    "final-integration-review-attempt-result",
                ),
                (
                    orchestrate_dir / "trace/workflow-completion.trace.json",
                    WORKFLOW_COMPLETION_SCHEMA,
                    "workflow",
                    "control",
                    "workflow-completion",
                ),
            )
        )
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    specs.extend((path, SOURCE_ATOMS_SCHEMA, "phase-2", "semantic", "source-atoms") for path in sorted(atom_root.glob("*.atoms.json")))
    return {
        rel(path, repo_root): (schema, phase, authority, role)
        for path, schema, phase, authority, role in specs
        if path.exists()
    }


def validate_manifest(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
    complete: bool = False,
    *,
    include_workflow_artifacts: bool = True,
    required_workflow_status: str = "",
) -> None:
    path = orchestrate_dir / "trace/manifest.json"
    data = json_obj(path, reporter, MANIFEST_SCHEMA)
    if not data:
        return
    exact_fields(
        data,
        {
            "trace-schema",
            "trace-contract-version",
            "authority",
            "orchestrate-dir",
            "phase-statuses",
            "workflow-status",
            "artifacts",
        },
        path,
        reporter,
        "manifest-fields",
        "manifest v3",
    )
    if data.get("authority") != "control":
        reporter.error("manifest-authority", path, "manifest v3 authority必须是control")
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
    workflow_status = normalize_code(data.get("workflow-status"))
    if workflow_status not in {"pending", "integration-passed", "blocked"}:
        reporter.error(
            "manifest-workflow-status",
            path,
            "workflow-status只允许pending|integration-passed|blocked",
        )
    if required_workflow_status and workflow_status != required_workflow_status:
        reporter.error(
            "manifest-required-workflow-status",
            path,
            (
                f"当前操作要求workflow-status={required_workflow_status}，"
                f"实际为{workflow_status or 'missing'}"
            ),
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
        if workflow_status != "integration-passed":
            reporter.error(
                "manifest-complete-workflow-status",
                path,
                "--complete要求workflow-status=integration-passed",
            )
        for required_path in (
            orchestrate_dir / "final-integration-review.json",
            orchestrate_dir
            / FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH,
            orchestrate_dir
            / FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH,
            orchestrate_dir / "trace/workflow-completion.trace.json",
        ):
            if not required_path.exists():
                reporter.error(
                    "manifest-complete-workflow-artifact",
                    path,
                    f"--complete缺少{rel(required_path, repo_root)}",
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
        phase3_trace_path = orchestrate_dir / "trace/phase-3.trace.json"
        if phase3_trace_path.exists():
            phase3_trace = read_json(phase3_trace_path)
            review_gate = phase3_trace.get("review-gate")
            gate_status = normalize_code(review_gate.get("status")) if isinstance(review_gate, dict) else ""
            if phase_status_value(phase3_trace.get("decision")) != "coverage-complete" or gate_status != "passed":
                reporter.error(
                    "manifest-complete-phase3-review-gate",
                    path,
                    "--complete要求Phase 3 decision=coverage-complete且review-gate.status=passed",
                )
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        reporter.error("manifest-artifacts", path, "artifacts 必须是 array")
        return
    expected_artifacts = expected_manifest_artifacts(
        orchestrate_dir,
        repo_root,
        include_workflow_artifacts=include_workflow_artifacts,
    )
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
        else:
            reporter.error(
                "manifest-artifact-unexpected",
                path,
                f"manifest包含非canonical或不存在于当前generation的JSON：{trace_rel}",
            )
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
    framework_path: Path,
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
    if status not in {"pending", "passed", "blocked"}:
        reporter.error(
            "phase1-review-gate-status",
            trace_path,
            "review-gate.status只允许pending|passed|blocked",
        )
    writer_id = squash(gate.get("writer-id"))
    if not writer_id:
        reporter.error("phase1-review-gate-writer", trace_path, "review-gate.writer-id不得为空")
    reviews = gate.get("reviews")
    if (
        not isinstance(reviews, list)
        or len(reviews) > 3
        or (status in {"passed", "blocked"} and len(reviews) < 1)
    ):
        reporter.error(
            "phase1-review-gate-reviews",
            trace_path,
            (
                "pending的reviews必须是0..3轮；"
                "passed|blocked的reviews必须是1..3轮"
            ),
        )
        reviews = []
    reviewer_ids: Set[str] = set()
    review_by_round: Dict[int, Dict[str, object]] = {}
    for index, review in enumerate(reviews, start=1):
        if not isinstance(review, dict):
            reporter.error("phase1-review-row", trace_path, f"reviews[{index}]必须是object")
            continue
        exact_fields(
            review,
            {
                "round",
                "reviewer-id",
                "validator-status",
                "initial-framework-sha256",
                "initial-change-plan-sha256",
                "semantic-checks",
                "finding-fingerprints",
            },
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
        for digest_field in (
            "initial-framework-sha256",
            "initial-change-plan-sha256",
        ):
            if not _is_sha256(review.get(digest_field)):
                reporter.error(
                    "phase1-review-authority-sha",
                    trace_path,
                    f"round {index} {digest_field}非法",
                )
        semantic_checks = review.get("semantic-checks")
        if not isinstance(semantic_checks, list):
            reporter.error(
                "phase1-review-semantic-checks",
                trace_path,
                f"round {index} semantic-checks必须是array",
            )
            semantic_checks = []
        actual_checks: List[str] = []
        for check_index, check in enumerate(semantic_checks):
            if not isinstance(check, dict):
                reporter.error(
                    "phase1-review-semantic-check",
                    trace_path,
                    f"round {index} semantic-checks[{check_index}]必须是object",
                )
                continue
            exact_fields(
                check,
                {"check", "result"},
                trace_path,
                reporter,
                "phase1-review-semantic-check-fields",
                f"round {index} semantic-checks[{check_index}]",
            )
            actual_checks.append(normalize_code(check.get("check")))
            if check.get("result") not in {"passed", "failed"}:
                reporter.error(
                    "phase1-review-semantic-check-result",
                    trace_path,
                    f"round {index} semantic check result非法",
                )
        if tuple(actual_checks) != PHASE1_REVIEW_CHECKS:
            reporter.error(
                "phase1-review-semantic-check-order",
                trace_path,
                f"round {index} semantic-checks必须按固定九项排列",
            )
        findings = review.get("finding-fingerprints")
        if (
            not isinstance(findings, list)
            or any(not _is_sha256(item) for item in findings)
            or len(findings) != len(set(findings))
        ):
            reporter.error("phase1-review-findings", trace_path, f"round {index} finding-fingerprints必须是唯一SHA-256 array")
        review_by_round[index] = review
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
            {
                "round",
                "repair-writer-id",
                "finding-fingerprints",
                "before-initial-framework-sha256",
                "after-initial-framework-sha256",
            },
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
        before_sha = repair.get("before-initial-framework-sha256")
        after_sha = repair.get("after-initial-framework-sha256")
        if not _is_sha256(before_sha) or not _is_sha256(after_sha):
            reporter.error("phase1-repair-plan-sha", trace_path, f"round {round_number} repair plan digest非法")
        if before_sha != review_by_round[round_number].get(
            "initial-framework-sha256"
        ):
            reporter.error("phase1-repair-before", trace_path, f"round {round_number} before digest与review不一致")
        next_review = review_by_round.get(round_number + 1)
        if next_review and after_sha != next_review.get(
            "initial-framework-sha256"
        ):
            reporter.error("phase1-repair-after", trace_path, f"round {round_number} after digest与下一轮review不一致")
        if before_sha == after_sha:
            forced_block_rounds.add(round_number)

    terminal_repair = repair_by_round.get(len(reviews))
    terminal_noop_repair = (
        status == "blocked"
        and isinstance(terminal_repair, dict)
        and terminal_repair.get("before-initial-framework-sha256")
        == terminal_repair.get("after-initial-framework-sha256")
    )
    reviews_after_latest_repair = len(reviews) == len(repairs)
    reviews_after_latest_review = len(reviews) == len(repairs) + 1
    if status == "pending":
        if not (reviews_after_latest_repair or reviews_after_latest_review):
            reporter.error(
                "phase1-review-gate-cardinality",
                trace_path,
                (
                    "pending只允许reviews==repairs（等待fresh review）或"
                    "reviews==repairs+1（等待repair或terminalization）"
                ),
            )
    elif not (
        reviews_after_latest_review
        or (reviews_after_latest_repair and terminal_noop_repair)
    ):
        reporter.error(
            "phase1-review-gate-cardinality",
            trace_path,
            "terminal gate通常要求reviews==repairs+1；仅blocked的terminal no-op repair允许两者等长",
        )

    for round_number in range(1, len(reviews)):
        repair = repair_by_round.get(round_number)
        if repair is None:
            reporter.error("phase1-repair-missing", trace_path, f"round {round_number}与下一轮review之间缺少repair")
    if (
        status == "pending"
        and reviews_after_latest_repair
        and reviews
        and terminal_repair is None
    ):
        reporter.error(
            "phase1-repair-missing",
            trace_path,
            "reviews==repairs的pending状态必须由最后一轮repair结束并等待fresh review",
        )

    current_framework_sha = (
        sha256_file(framework_path) if framework_path.exists() else ""
    )
    current_plan_sha = sha256_file(plan_path) if plan_path.exists() else ""
    if reviews_after_latest_review and reviews:
        last_review = reviews[-1]
        if (
            current_framework_sha
            and last_review.get("initial-framework-sha256")
            != current_framework_sha
        ):
            reporter.error(
                "phase1-review-current-framework",
                trace_path,
                "等待repair/terminalization时最后一轮review必须绑定当前initial framework digest",
            )
        if (
            current_plan_sha
            and last_review.get("initial-change-plan-sha256")
            != current_plan_sha
        ):
            reporter.error(
                "phase1-review-current-plan",
                trace_path,
                "等待repair/terminalization时最后一轮review必须绑定当前initial plan mirror digest",
            )
    elif reviews_after_latest_repair and reviews and isinstance(terminal_repair, dict):
        if (
            current_framework_sha
            and terminal_repair.get("after-initial-framework-sha256")
            != current_framework_sha
        ):
            reporter.error(
                "phase1-repair-current-framework",
                trace_path,
                "等待fresh review时最后一轮repair.after digest必须绑定当前initial framework",
            )
    seen_findings: Set[str] = set()
    for round_number in range(1, len(reviews) + 1):
        review = review_by_round.get(round_number, {})
        findings = review.get("finding-fingerprints") if isinstance(review, dict) else []
        if not isinstance(findings, list) or not all(_is_sha256(item) for item in findings):
            continue
        if seen_findings.intersection(findings):
            forced_block_rounds.add(round_number)
        seen_findings.update(findings)
    if len(reviews) == 3:
        terminal_review = reviews[-1] if isinstance(reviews[-1], dict) else {}
        terminal_checks = terminal_review.get("semantic-checks")
        terminal_checks_passed = isinstance(terminal_checks, list) and all(
            isinstance(check, dict) and check.get("result") == "passed"
            for check in terminal_checks
        )
        if (
            normalize_code(terminal_review.get("validator-status")) != "passed"
            or terminal_review.get("finding-fingerprints") != []
            or not terminal_checks_passed
        ):
            forced_block_rounds.add(3)
    if forced_block_rounds and status != "blocked":
        reporter.error(
            "phase1-review-no-progress",
            trace_path,
            "repair未改变plan、finding重复或第三次review未通过时review-gate只能blocked",
        )
    if forced_block_rounds and len(reviews) > min(forced_block_rounds):
        reporter.error(
            "phase1-review-continued-after-block",
            trace_path,
            "重复finding或no-op repair一经确认必须立即blocked，不得继续repair/review",
        )
    if status == "passed" and reviews:
        last = reviews[-1]
        checks = last.get("semantic-checks")
        checks_passed = isinstance(checks, list) and all(
            isinstance(check, dict) and check.get("result") == "passed"
            for check in checks
        )
        if (
            last.get("finding-fingerprints") != []
            or normalize_code(last.get("validator-status")) != "passed"
            or not checks_passed
        ):
            reporter.error(
                "phase1-review-pass",
                trace_path,
                "passed要求最后review无finding、validator通过且九项semantic check全部passed",
            )
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
        {
            "trace-schema",
            "trace-contract-version",
            "status",
            "source-documents",
            "initial-framework",
            "initial-change-plan",
            "review-gate",
        },
        path,
        reporter,
        "phase1-trace-fields",
        "Phase 1 trace",
    )
    phase1_status = validate_trace_status(data, path, reporter, "phase-1", "phase1-status")
    initial_framework_path = (
        orchestrate_dir / "phase-works/phase-1/initial-framework.json"
    )
    initial_plan_path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    source_manifest_path = orchestrate_dir / "phase-works/phase-1/source-doc-manifest.md"
    require_file(
        initial_framework_path,
        reporter,
        "phase1-interface-artifact",
        "缺少 Phase 1 initial-framework.json",
    )
    require_file(initial_plan_path, reporter, "phase1-interface-artifact", "缺少 Phase 1 initial-change-plan.md")
    require_file(source_manifest_path, reporter, "phase1-interface-artifact", "缺少 Phase 1 source-doc-manifest.md")
    require_file(orchestrate_dir / "phase-works/phase-1/phase-1-agent-report.md", reporter, "phase1-interface-artifact", "缺少 Phase 1 agent 报告")
    if initial_framework_path.exists():
        try:
            framework, _ = load_initial_framework(initial_framework_path)
            expected_mirror_path = rel(initial_plan_path, repo_root)
            if framework.get("artifact-path") != expected_mirror_path:
                reporter.error(
                    "phase1-framework-artifact-path",
                    initial_framework_path,
                    f"artifact-path必须为{expected_mirror_path}",
                )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            reporter.error(
                "phase1-initial-framework-contract",
                initial_framework_path,
                str(exc),
            )
        validate_rendered_markdown(
            orchestrate_dir,
            initial_framework_path,
            initial_plan_path,
            render_initial_framework,
            reporter,
            "phase1-initial-framework",
        )
    gate_status = _validate_phase1_review_gate(
        data.get("review-gate"),
        path,
        initial_framework_path,
        initial_plan_path,
        reporter,
    )
    expected_gate_status = {
        "review-pending": "pending",
        "initial-plan-written": "passed",
        "blocked": "blocked",
    }.get(phase1_status)
    if expected_gate_status and gate_status != expected_gate_status:
        reporter.error(
            "phase1-status-review-gate-drift",
            path,
            f"Phase 1 status={phase1_status} 要求 review-gate.status={expected_gate_status}，实际为 {gate_status or 'missing'}",
        )

    initial_framework = data.get("initial-framework")
    if not isinstance(initial_framework, dict):
        reporter.error(
            "phase1-initial-framework-trace",
            path,
            "initial-framework必须是object",
        )
    else:
        exact_fields(
            initial_framework,
            {"artifact-path", "sha256"},
            path,
            reporter,
            "phase1-initial-framework-ref-fields",
            "initial-framework",
        )
        expected_framework_path = rel(initial_framework_path, repo_root)
        if initial_framework.get("artifact-path") != expected_framework_path:
            reporter.error(
                "phase1-initial-framework-path",
                path,
                f"initial-framework.artifact-path必须为{expected_framework_path}",
            )
        if (
            initial_framework_path.exists()
            and initial_framework.get("sha256")
            != sha256_file(initial_framework_path)
        ):
            reporter.error(
                "phase1-initial-framework-sha",
                path,
                "initial-framework.sha256与当前JSON authority不一致",
            )
    initial_plan = data.get("initial-change-plan")
    if not isinstance(initial_plan, dict):
        reporter.error("phase1-initial-plan-trace", path, "initial-change-plan 必须是 object")
    else:
        exact_fields(
            initial_plan,
            {"artifact-path", "sha256"},
            path,
            reporter,
            "phase1-initial-plan-ref-fields",
            "initial-change-plan",
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
    path = orchestrate_dir / "phase-works/phase-1/initial-framework.json"
    _, parsed = load_initial_framework(path)
    return set(parsed["change-ids"]), set(parsed["capability-ids"])


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


def validate_phase_2(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
    *,
    preflight: bool = False,
) -> None:
    require_file(
        orchestrate_dir / "phase-works/phase-1/initial-change-plan.md",
        reporter,
        "phase2-interface-input",
        "缺少 Phase 2 输入：Phase 1 initial-change-plan.md",
    )
    trace_path = orchestrate_dir / "trace/phase-2.trace.json"
    trace = {} if preflight else json_obj(trace_path, reporter, PHASE_TRACE_SCHEMAS["phase-2"])
    trace_sources: Dict[str, Dict[str, object]] = {}
    if trace:
        trace_status = validate_trace_status(trace, trace_path, reporter, "phase-2", "phase2-status")
        if trace_status == "blocked":
            exact_fields(
                trace,
                {"trace-schema", "trace-contract-version", "status", "issues"},
                trace_path,
                reporter,
                "phase2-trace-fields",
                "blocked Phase 2 v6 trace",
            )
            if not isinstance(trace.get("issues"), list) or not trace.get("issues"):
                reporter.error("phase2-trace-issues", trace_path, "blocked要求非空issues[]")
            return
        exact_fields(
            trace,
            {
                "trace-schema", "trace-contract-version", "status", "work-queue-path",
                "sources", "phase-report-path",
            },
            trace_path,
            reporter,
            "phase2-trace-fields",
            "Phase 2 v6 trace",
        )
        work_queue_path = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms/work-queue.md"
        phase_report_path = orchestrate_dir / "phase-works/phase-2/phase-2-agent-report.md"
        if trace.get("work-queue-path") != rel(work_queue_path, repo_root):
            reporter.error("phase2-trace-path", trace_path, "work-queue-path与canonical path不一致")
        if trace.get("phase-report-path") != rel(phase_report_path, repo_root):
            reporter.error("phase2-trace-path", trace_path, "phase-report-path与canonical path不一致")
        raw_trace_sources = trace.get("sources")
        if not isinstance(raw_trace_sources, list):
            reporter.error("phase2-trace-sources", trace_path, "Phase 2 trace sources 必须是 array")
        else:
            required = {
                "source-document", "atom-json-path", "atom-json-sha256",
                "atom-markdown-path", "canonical-owner", "read-status",
                "atom-count", "delivery-directive-atom-count", "blockers",
            }
            for index, row in enumerate(raw_trace_sources, start=1):
                if not isinstance(row, dict):
                    reporter.error("phase2-trace-source-row", trace_path, f"sources[{index}] 必须是 object")
                    continue
                exact_fields(
                    row, required, trace_path, reporter,
                    "phase2-trace-source-field", f"sources[{index}]",
                )
                source_document = normalize_code(row.get("source-document"))
                if source_document in trace_sources:
                    reporter.error("phase2-trace-source-duplicate", trace_path, f"Phase 2 trace source 重复：{source_document}")
                trace_sources[source_document] = row
    require_file(orchestrate_dir / "phase-works/phase-2/source-obligation-atoms/work-queue.md", reporter, "phase2-interface-artifact", "缺少 Phase 2 work queue")
    if not preflight:
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
                f"Phase 2 v6 sidecar 包含不允许的顶层字段：{', '.join(unexpected_top_level)}",
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
                    f"{context or 'source atom'} 包含 Phase 2 v6 不允许的字段：{', '.join(unexpected_fields)}",
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
            directives = row.get("delivery-directives")
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
            if not _delivery_directives_are_canonical(directives):
                reporter.error(
                    "phase2-delivery-directives",
                    sidecar,
                    f"{context} delivery-directives必须是唯一、按milestone-scope|explicit-precedence|explicit-deferred固定顺序排列的允许枚举array",
                )
            if status in {"direct-candidate", "unassigned"} and projection not in DIRECT_PROJECTIONS:
                reporter.error(
                    "phase2-actionable-projection",
                    sidecar,
                    f"{context} 的 {status} 只允许 spec/guard/design/verification projection",
                )
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
        if not preflight and trace_row is None:
            reporter.error("phase2-trace-source-coverage", trace_path, f"Phase 2 trace sources 缺少：{source_document}")
        elif not preflight and trace_row is not None:
            expected = {
                "atom-json-path": rel(sidecar, repo_root),
                "atom-json-sha256": sha256_file(sidecar),
                "atom-markdown-path": rel(sidecar.with_suffix(".md"), repo_root),
                "canonical-owner": data.get("canonical-owner"),
                "read-status": data.get("read-status"),
                "atom-count": len(atoms),
                "delivery-directive-atom-count": sum(
                    1
                    for atom in atoms
                    if (
                        isinstance(atom, dict)
                        and isinstance(atom.get("delivery-directives"), list)
                        and atom.get("delivery-directives")
                    )
                ),
                "blockers": blockers,
            }
            for field, expected_value in expected.items():
                if trace_row.get(field) != expected_value:
                    reporter.error("phase2-trace-source-drift", trace_path, f"{source_document} 的 {field} 与 canonical source atom sidecar 不一致")
    if not preflight:
        for extra_source in sorted(set(trace_sources) - read_full_documents):
            reporter.error("phase2-trace-source-coverage", trace_path, f"Phase 2 trace sources 包含非 read-full 或未知 source：{extra_source}")
        validate_phase2_mirror(orchestrate_dir, reporter)


def load_global_atoms(
    orchestrate_dir: Path,
    reporter: IssueReporter,
    repo_root: Path | None = None,
) -> Dict[str, Dict[str, object]]:
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
        expected_artifact = rel(path.with_suffix(".md"), repo_root or repo_root_for_path(path))
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


def load_phase3_gap_atoms(
    orchestrate_dir: Path,
    reporter: IssueReporter,
    repo_root: Path | None = None,
) -> Dict[str, Dict[str, object]]:
    path = orchestrate_dir / "phase-works/phase-3/coverage-review.json"
    data = json_obj(path, reporter, PHASE3_COVERAGE_REVIEW_SCHEMA)
    result: Dict[str, Dict[str, object]] = {}
    rows = data.get("gap-atoms")
    if not isinstance(rows, list):
        reporter.error("phase3-gap-atoms", path, "gap-atoms 必须是 array")
        return result
    expected_fields = {
        "gap-atom-id",
        "source-document",
        "line-ranges",
        "source-fact",
        "atom-type",
        "normativity",
        "delivery-directives",
        "review-judgment",
    }
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
        source_root = repo_root or repo_root_for_path(path)
        check_atom_range(path, reporter, row.get("line-ranges"), source_document, source_root, gap_id)
        check_source_fact_quote(path, reporter, row.get("source-fact"), row.get("line-ranges"), source_document, source_root, gap_id)
        if normalize_code(row.get("atom-type")) not in PHASE2_ATOM_TYPES:
            reporter.error("phase3-gap-atom-type", path, f"{gap_id} atom-type 非法")
        if normalize_code(row.get("normativity")) not in PHASE2_NORMATIVITY:
            reporter.error("phase3-gap-normativity", path, f"{gap_id} normativity 非法")
        directives = row.get("delivery-directives")
        if not _delivery_directives_are_canonical(directives):
            reporter.error(
                "phase3-gap-delivery-directives",
                path,
                f"{gap_id} delivery-directives必须是唯一、按milestone-scope|explicit-precedence|explicit-deferred固定顺序排列的允许枚举array",
            )
        if not squash(row.get("review-judgment")):
            reporter.error("phase3-gap-judgment", path, f"{gap_id} 缺少中文 review-judgment")
        result[gap_id] = row
    return result


def repo_root_for_path(path: Path) -> Path:
    for parent in path.parents:
        if parent.name == "orchestrate" and parent.parent.name == "openspec":
            return parent.parent.parent
    return Path.cwd()


def _validate_phase3_review_gate(
    gate: object,
    trace_path: Path,
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
) -> str:
    if not isinstance(gate, dict):
        reporter.error("phase3-review-gate", trace_path, "review-gate必须是object")
        return ""
    exact_fields(
        gate,
        {
            "status", "phase-2-canonical-owner-ids", "phase-2-aggregate-writer-id",
            "phase-3-writer-id", "reviews", "repairs",
        },
        trace_path,
        reporter,
        "phase3-review-gate-fields",
        "review-gate",
    )
    status = normalize_code(gate.get("status"))
    if status not in {"pending", "passed", "blocked"}:
        reporter.error("phase3-review-gate-status", trace_path, "review-gate.status只允许pending|passed|blocked")

    owner_ids = gate.get("phase-2-canonical-owner-ids")
    if (
        not isinstance(owner_ids, list)
        or not owner_ids
        or any(not isinstance(item, str) or not squash(item) for item in owner_ids)
        or len(owner_ids) != len(set(owner_ids))
    ):
        reporter.error(
            "phase3-review-gate-owner-ids",
            trace_path,
            "phase-2-canonical-owner-ids必须是非空唯一string array",
        )
        owner_ids = []
    else:
        owner_ids = [squash(item) for item in owner_ids]
    expected_owner_ids: List[str] = []
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    for sidecar in sorted(atom_root.glob("*.atoms.json")):
        try:
            owner_id = squash(read_json(sidecar).get("canonical-owner"))
        except Exception:  # noqa: BLE001
            continue
        if owner_id and owner_id not in expected_owner_ids:
            expected_owner_ids.append(owner_id)
    if owner_ids != expected_owner_ids:
        reporter.error(
            "phase3-review-gate-owner-drift",
            trace_path,
            "phase-2-canonical-owner-ids必须按atom JSON path顺序覆盖当前canonical owners",
        )

    aggregate_writer = squash(gate.get("phase-2-aggregate-writer-id"))
    phase3_writer = squash(gate.get("phase-3-writer-id"))
    if not aggregate_writer or not phase3_writer:
        reporter.error("phase3-review-gate-writers", trace_path, "Phase 2 aggregate与Phase 3 writer ID不得为空")
    producer_ids = set(owner_ids) | {aggregate_writer, phase3_writer}
    if "" in producer_ids or len(producer_ids) != len(owner_ids) + 2:
        reporter.error("phase3-review-gate-producer-identity", trace_path, "全部producer identity必须互不相同")

    reviews = gate.get("reviews")
    repairs = gate.get("repairs")
    if not isinstance(reviews, list) or len(reviews) > 3:
        reporter.error("phase3-review-gate-reviews", trace_path, "reviews必须是最多3轮的array")
        reviews = []
    if not isinstance(repairs, list) or len(repairs) > 2:
        reporter.error("phase3-review-gate-repairs", trace_path, "repairs必须是最多2轮的array")
        repairs = []
    if status == "passed" and not reviews:
        reporter.error("phase3-review-gate-terminal-review", trace_path, "passed要求至少一轮review")

    reviewer_ids: Set[str] = set()
    review_rows: Dict[int, Dict[str, object]] = {}
    seen_fingerprints: Set[str] = set()
    repeated_fingerprint = False
    for index, row in enumerate(reviews, start=1):
        if not isinstance(row, dict):
            reporter.error("phase3-review-row", trace_path, f"reviews[{index}]必须是object")
            continue
        exact_fields(
            row,
            {
                "round", "stage", "reviewer-id", "phase-2-validator-status",
                "phase-3-validator-status", "delivery-directive-status",
                "evidence-authority-sha256", "finding-fingerprints",
            },
            trace_path,
            reporter,
            "phase3-review-row-fields",
            f"reviews[{index}]",
        )
        round_number = row.get("round")
        if round_number != index:
            reporter.error("phase3-review-round", trace_path, "review round必须从1开始连续且与array顺序一致")
        if isinstance(round_number, int):
            review_rows[round_number] = row
        stage = normalize_code(row.get("stage"))
        if stage not in {"phase-2-preflight", "phase-3-closure"}:
            reporter.error("phase3-review-stage", trace_path, f"reviews[{index}].stage非法：{stage}")
        phase2_status = normalize_code(row.get("phase-2-validator-status"))
        phase3_status = normalize_code(row.get("phase-3-validator-status"))
        if phase2_status not in {"passed", "failed"}:
            reporter.error("phase3-review-validator-status", trace_path, "Phase 2 validator status只允许passed|failed")
        if phase3_status not in {"passed", "failed", "not-run"}:
            reporter.error("phase3-review-validator-status", trace_path, "Phase 3 validator status只允许passed|failed|not-run")
        directive_status = normalize_code(row.get("delivery-directive-status"))
        if directive_status not in {"passed", "failed"}:
            reporter.error(
                "phase3-review-directive-status",
                trace_path,
                "delivery-directive-status只允许passed|failed",
            )
        if stage == "phase-2-preflight" and phase3_status != "not-run":
            reporter.error("phase3-review-validator-stage", trace_path, "phase-2-preflight要求Phase 3 validator status=not-run")
        if stage == "phase-3-closure" and phase3_status == "not-run":
            reporter.error("phase3-review-validator-stage", trace_path, "phase-3-closure不允许Phase 3 validator status=not-run")
        reviewer_id = squash(row.get("reviewer-id"))
        if not reviewer_id or reviewer_id in reviewer_ids or reviewer_id in producer_ids:
            reporter.error("phase3-reviewer-identity", trace_path, "fresh reviewer ID必须非空、唯一且不得与producer重用")
        reviewer_ids.add(reviewer_id)
        digest = normalize_code(row.get("evidence-authority-sha256"))
        if not _is_sha256(digest):
            reporter.error("phase3-review-authority-digest", trace_path, f"reviews[{index}] authority digest非法")
        findings = row.get("finding-fingerprints")
        if (
            not isinstance(findings, list)
            or any(not isinstance(item, str) or not _is_sha256(item) for item in findings)
            or len(findings) != len(set(findings))
        ):
            reporter.error("phase3-review-findings", trace_path, "finding-fingerprints必须是唯一SHA-256 array")
            findings = []
        normalized_findings = set(findings)
        if seen_fingerprints.intersection(normalized_findings):
            repeated_fingerprint = True
        seen_fingerprints.update(normalized_findings)

    repair_ids: Set[str] = set()
    no_op_repair = False
    for index, row in enumerate(repairs, start=1):
        if not isinstance(row, dict):
            reporter.error("phase3-repair-row", trace_path, f"repairs[{index}]必须是object")
            continue
        exact_fields(
            row,
            {
                "round", "repair-writer-id", "finding-fingerprints",
                "before-evidence-authority-sha256", "after-evidence-authority-sha256",
            },
            trace_path,
            reporter,
            "phase3-repair-row-fields",
            f"repairs[{index}]",
        )
        round_number = row.get("round")
        if round_number != index:
            reporter.error("phase3-repair-round", trace_path, "repair round必须从1开始连续且与array顺序一致")
        review = review_rows.get(round_number) if isinstance(round_number, int) else None
        findings = row.get("finding-fingerprints")
        if not isinstance(findings, list) or not findings or any(not _is_sha256(item) for item in findings):
            reporter.error("phase3-repair-findings", trace_path, "repair finding-fingerprints必须是非空SHA-256 array")
            findings = []
        if review is None or findings != review.get("finding-fingerprints"):
            reporter.error("phase3-repair-finding-coverage", trace_path, "repair必须恰好消费同轮review的全部findings")
        writer_id = squash(row.get("repair-writer-id"))
        if (
            not writer_id
            or writer_id in repair_ids
            or writer_id in producer_ids
            or writer_id in reviewer_ids
        ):
            reporter.error("phase3-repair-writer-identity", trace_path, "fresh repair writer ID必须与producer/reviewer/其他repair互不相同")
        repair_ids.add(writer_id)
        before = normalize_code(row.get("before-evidence-authority-sha256"))
        after = normalize_code(row.get("after-evidence-authority-sha256"))
        if not _is_sha256(before) or not _is_sha256(after):
            reporter.error("phase3-repair-authority-digest", trace_path, "repair before/after digest必须是SHA-256")
        if review is not None and before != normalize_code(review.get("evidence-authority-sha256")):
            reporter.error("phase3-repair-before-digest", trace_path, "repair before digest必须绑定同轮review authority")
        if before == after:
            no_op_repair = True

    if len(repairs) > max(0, len(reviews)):
        reporter.error("phase3-review-repair-cardinality", trace_path, "repair不得多于已完成review")
    if (repeated_fingerprint or no_op_repair) and status != "blocked":
        reporter.error("phase3-review-terminal-block", trace_path, "finding重复或no-op repair要求review-gate.status=blocked")

    current_full_digest = ""
    if status == "passed":
        try:
            current_full_digest = evidence_authority_sha256(orchestrate_dir, repo_root)
        except Exception as exc:  # noqa: BLE001
            reporter.error("phase3-review-authority", trace_path, f"无法计算evidence authority digest：{exc}")
    if status == "pending" and reviews:
        latest_review = reviews[-1] if isinstance(reviews[-1], dict) else {}
        latest_stage = normalize_code(latest_review.get("stage"))
        include_phase3 = latest_stage == "phase-3-closure"
        try:
            current_stage_digest = evidence_authority_sha256(
                orchestrate_dir,
                repo_root,
                include_phase3=include_phase3,
            )
        except Exception as exc:  # noqa: BLE001
            reporter.error("phase3-review-authority", trace_path, f"无法计算当前stage authority digest：{exc}")
            current_stage_digest = ""
        if len(repairs) == len(reviews):
            latest_repair = repairs[-1] if isinstance(repairs[-1], dict) else {}
            recorded = normalize_code(latest_repair.get("after-evidence-authority-sha256"))
        else:
            recorded = normalize_code(latest_review.get("evidence-authority-sha256"))
        if recorded != current_stage_digest:
            reporter.error("phase3-review-current-authority", trace_path, "pending gate的最新review/repair digest必须绑定当前stage authority")
    if status == "passed" and reviews:
        final_review = reviews[-1] if isinstance(reviews[-1], dict) else {}
        if (
            normalize_code(final_review.get("stage")) != "phase-3-closure"
            or normalize_code(final_review.get("phase-2-validator-status")) != "passed"
            or normalize_code(final_review.get("phase-3-validator-status")) != "passed"
            or normalize_code(final_review.get("delivery-directive-status")) != "passed"
            or final_review.get("finding-fingerprints") != []
        ):
            reporter.error(
                "phase3-review-terminal-review",
                trace_path,
                "terminal review必须是phase-3-closure、双validator passed、delivery directive audit passed且无finding",
            )
        if normalize_code(final_review.get("evidence-authority-sha256")) != current_full_digest:
            reporter.error("phase3-review-terminal-authority", trace_path, "terminal review digest必须绑定当前完整evidence authority")
        if len(repairs) != len(reviews) - 1:
            reporter.error("phase3-review-repair-cardinality", trace_path, "passed要求每轮非terminal review后恰好一次repair")
        if final_review.get("finding-fingerprints"):
            reporter.error(
                "phase3-review-repair-cardinality",
                trace_path,
                "存在terminal finding时不得冻结；必须repair后由fresh reviewer形成无finding terminal round",
            )
    return status


def validate_phase_3(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
    *,
    preflight: bool = False,
) -> None:
    trace_path = orchestrate_dir / "trace/phase-3.trace.json"
    coverage_path = orchestrate_dir / "phase-works/phase-3/coverage-review.json"
    index_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    trace = json_obj(trace_path, reporter, PHASE_TRACE_SCHEMAS["phase-3"])
    trace_decision = phase_status_value(trace.get("decision")) if trace else ""
    if not trace:
        return
    validate_trace_status(trace, trace_path, reporter, "phase-3", "phase3-status")
    if trace_decision == "blocked":
        exact_fields(
            trace,
            {"trace-schema", "trace-contract-version", "decision", "review-gate", "issues"},
            trace_path,
            reporter,
            "phase3-trace-fields",
            "blocked Phase 3 v5 trace",
        )
        gate_status = _validate_phase3_review_gate(
            trace.get("review-gate"), trace_path, orchestrate_dir, repo_root, reporter,
        )
        if gate_status != "blocked":
            reporter.error("phase3-review-gate-decision", trace_path, "blocked decision要求review-gate.status=blocked")
        if not isinstance(trace.get("issues"), list) or not trace.get("issues"):
            reporter.error("phase3-trace-issues", trace_path, "blocked要求非空issues[]")
        return
    exact_fields(
        trace,
        {
            "trace-schema", "trace-contract-version", "decision",
            "global-atom-index-path", "global-atom-index-sha256",
            "coverage-review-path", "coverage-review-sha256", "review-gate", "issues",
        },
        trace_path,
        reporter,
        "phase3-trace-fields",
        "Phase 3 v5 trace",
    )
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
    gate_status = _validate_phase3_review_gate(
        trace.get("review-gate"), trace_path, orchestrate_dir, repo_root, reporter,
    )
    issues = trace.get("issues")
    if not isinstance(issues, list):
        reporter.error("phase3-trace-issues", trace_path, "issues必须是array")
        issues = []
    if preflight:
        if trace_decision != "review-pending" or gate_status != "pending":
            reporter.error(
                "phase3-preflight-state", trace_path,
                "Phase 3 --preflight只接受decision=review-pending且review-gate.status=pending",
            )
    elif trace_decision != "coverage-complete" or gate_status != "passed":
        reporter.error(
            "phase3-terminal-state", trace_path,
            "普通Phase 3 validator只接受decision=coverage-complete且review-gate.status=passed",
        )
    if trace_decision == "coverage-complete" and issues:
        reporter.error("phase3-trace-issues", trace_path, "coverage-complete要求issues=[]")
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
        expected_artifact = rel(coverage_path.with_suffix(".md"), repo_root)
        if coverage.get("artifact-path") != expected_artifact:
            reporter.error("phase3-coverage-artifact-path", coverage_path, f"artifact-path 应为 {expected_artifact}")
        if not isinstance(coverage.get("summary"), dict):
            reporter.error("phase3-summary", coverage_path, "summary 必须是 object")
        if not squash(coverage.get("language-self-check")):
            reporter.error("phase3-language-self-check", coverage_path, "language-self-check 必须非空")
    decision = normalize_code(coverage.get("decision"))
    if decision not in PHASE_ALLOWED_TRACE_STATUSES["phase-3"]:
        reporter.error("phase3-decision", coverage_path, f"decision 非法：{decision}")
    if trace_decision and decision and trace_decision != decision and not (
        preflight and trace_decision == "review-pending" and decision == "coverage-complete"
    ):
        reporter.error("phase3-decision-drift", trace_path, "Phase 3 trace 与 coverage review decision 不一致")

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
    allowed_phase3_files = {
        coverage_path.resolve(),
        coverage_path.with_suffix(".md").resolve(),
        (phase3_dir / "phase-3-reviewer-report.md").resolve(),
        (phase3_dir / "phase-3-repair-report.md").resolve(),
    }
    if phase3_dir.exists():
        for path in phase3_dir.rglob("*"):
            if path.is_file() and path.resolve() not in allowed_phase3_files:
                reporter.error("phase3-unexpected-artifact", path, "Phase 3 固定五产物契约不允许此文件")

    phase2_atoms = load_phase2_atoms(orchestrate_dir, reporter)
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

    gap_atoms = load_phase3_gap_atoms(orchestrate_dir, reporter, repo_root)
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

    global_atoms = load_global_atoms(orchestrate_dir, reporter, repo_root)
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

    summary = coverage.get("summary") if isinstance(coverage.get("summary"), dict) else {}
    disposition_counts = {name: classifications.count(name) for name in sorted(PHASE3_DISPOSITIONS)}
    directive_atom_count, directive_counts = _delivery_directive_summary(
        [*phase2_atoms.values(), *gap_atoms.values()]
    )
    expected_summary = {
        "source-documents": len(read_full),
        "phase-2-atoms": len(phase2_atoms),
        "gap-atoms": len(gap_atoms),
        "global-atoms": len(global_atoms),
        "mapping-ambiguities": len(ambiguity_rows),
        "candidate-uncovered-ranges": sum(len(items) for items in uncovered_by_source.values()),
        "remainder-dispositions": disposition_counts,
        "delivery-directive-atoms": directive_atom_count,
        "delivery-directives": directive_counts,
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
            "delivery-directives": evidence.get("delivery-directives"),
            "candidate-status": evidence.get("candidate-status"),
            "candidate-artifact-projection": evidence.get("candidate-artifact-projection"),
            "candidate-owner-change": evidence.get("candidate-owner-change"),
            "candidate-target-capability": evidence.get("candidate-target-capability"),
        }
    return resolved


def _validate_phase3_freeze_marker(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
) -> None:
    """Protect frozen GA/evidence authority without rereading source documents."""
    trace_path = orchestrate_dir / "trace/phase-3.trace.json"
    trace = json_obj(trace_path, reporter, PHASE_TRACE_SCHEMAS["phase-3"])
    if not trace:
        return
    if phase_status_value(trace.get("decision")) != "coverage-complete":
        reporter.error("phase4-phase3-freeze", trace_path, "Phase 4要求Phase 3 decision=coverage-complete")
        return
    gate_status = _validate_phase3_review_gate(
        trace.get("review-gate"), trace_path, orchestrate_dir, repo_root, reporter,
    )
    if gate_status != "passed":
        reporter.error("phase4-phase3-freeze", trace_path, "Phase 4要求Phase 3 review-gate.status=passed")


def _validate_phase4_index_contract(
    data: Dict[str, object],
    index_path: Path,
    reporter: IssueReporter,
) -> None:
    """Validate the exact neutral collection index v3 envelope and row shapes."""
    exact_fields(
        data,
        {"trace-schema", "trace-contract-version", "generated-from", "rows", "rendered-artifacts"},
        index_path,
        reporter,
        "phase4-index-fields",
        "derived evidence collection index",
    )

    generated_from = data.get("generated-from")
    if not isinstance(generated_from, list):
        reporter.error("phase4-index-generated-from", index_path, "generated-from必须是array")
        generated_from = []
    generated_paths: Set[str] = set()
    for index, row in enumerate(generated_from, start=1):
        if not isinstance(row, dict):
            reporter.error("phase4-index-generated-row", index_path, f"generated-from[{index}]必须是object")
            continue
        exact_fields(
            row,
            {"artifact-path", "sha256"},
            index_path,
            reporter,
            "phase4-index-generated-row-fields",
            f"generated-from[{index}]",
        )
        artifact_path = row.get("artifact-path")
        if not isinstance(artifact_path, str) or not artifact_path:
            reporter.error("phase4-index-generated-path", index_path, f"generated-from[{index}].artifact-path必须是非空string")
        elif artifact_path in generated_paths:
            reporter.error("phase4-index-generated-path", index_path, f"generated-from artifact-path重复：{artifact_path}")
        else:
            generated_paths.add(artifact_path)
        if not _is_sha256(row.get("sha256")):
            reporter.error("phase4-index-generated-sha", index_path, f"generated-from[{index}].sha256非法")

    rows = data.get("rows")
    if not isinstance(rows, list):
        reporter.error("phase4-index-rows", index_path, "rows必须是array")
        rows = []
    global_atom_ids: Set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            reporter.error("phase4-index-row", index_path, f"rows[{index}]必须是object")
            continue
        exact_fields(
            row,
            {
                "global-atom-id",
                "evidence-ref",
                "source-document",
                "rendered-collection-paths",
            },
            index_path,
            reporter,
            "phase4-index-row-fields",
            f"rows[{index}]",
        )
        global_atom_id = normalize_code(row.get("global-atom-id"))
        if not GLOBAL_ATOM_ID_RE.fullmatch(global_atom_id):
            reporter.error("phase4-index-global-atom-id", index_path, f"rows[{index}] global-atom-id非法：{global_atom_id}")
        elif global_atom_id in global_atom_ids:
            reporter.error("phase4-index-global-atom-id", index_path, f"global-atom-id重复：{global_atom_id}")
        else:
            global_atom_ids.add(global_atom_id)
        if not isinstance(row.get("evidence-ref"), dict):
            reporter.error("phase4-index-evidence-ref", index_path, f"{global_atom_id or f'rows[{index}]'} evidence-ref必须是object")
        if not normalize_code(row.get("source-document")):
            reporter.error("phase4-index-source-document", index_path, f"{global_atom_id or f'rows[{index}]'} source-document不得为空")
        collection_paths = row.get("rendered-collection-paths")
        if (
            not isinstance(collection_paths, list)
            or len(collection_paths) not in {2, 3}
            or any(not isinstance(item, str) or not item for item in collection_paths)
            or (
                all(isinstance(item, str) for item in collection_paths)
                and len(collection_paths) != len(set(collection_paths))
            )
        ):
            reporter.error(
                "phase4-index-collection-paths",
                index_path,
                f"{global_atom_id or f'rows[{index}]'} rendered-collection-paths必须是恰含2或3个唯一非空path的array",
            )

    rendered_artifacts = data.get("rendered-artifacts")
    if not isinstance(rendered_artifacts, list):
        reporter.error("phase4-index-rendered-artifacts", index_path, "rendered-artifacts必须是array")
        rendered_artifacts = []
    rendered_paths: Set[str] = set()
    global_kind_counts = {
        "index": 0,
        "all-evidence": 0,
        "delivery-directives": 0,
    }
    for index, row in enumerate(rendered_artifacts, start=1):
        if not isinstance(row, dict):
            reporter.error("phase4-index-rendered-row", index_path, f"rendered-artifacts[{index}]必须是object")
            continue
        exact_fields(
            row,
            {"artifact-path", "sha256", "collection-kind", "scope"},
            index_path,
            reporter,
            "phase4-index-rendered-row-fields",
            f"rendered-artifacts[{index}]",
        )
        artifact_path = row.get("artifact-path")
        if not isinstance(artifact_path, str) or not artifact_path:
            reporter.error("phase4-index-rendered-path", index_path, f"rendered-artifacts[{index}].artifact-path必须是非空string")
        elif artifact_path in rendered_paths:
            reporter.error("phase4-index-rendered-path", index_path, f"rendered artifact-path重复：{artifact_path}")
        else:
            rendered_paths.add(artifact_path)
        if not _is_sha256(row.get("sha256")):
            reporter.error("phase4-index-rendered-sha", index_path, f"rendered-artifacts[{index}].sha256非法")
        kind = normalize_code(row.get("collection-kind"))
        scope = normalize_code(row.get("scope"))
        if kind not in {"index", "all-evidence", "delivery-directives", "source"}:
            reporter.error("phase4-index-collection-kind", index_path, f"rendered-artifacts[{index}] collection-kind非法：{kind}")
        elif kind == "source":
            if not scope:
                reporter.error("phase4-index-collection-scope", index_path, "source collection的scope必须是source document path")
        else:
            global_kind_counts[kind] += 1
            if scope != "all":
                reporter.error("phase4-index-collection-scope", index_path, f"{kind} collection的scope必须是all")
    for kind, count in global_kind_counts.items():
        if count != 1:
            reporter.error("phase4-index-collection-cardinality", index_path, f"{kind} rendered artifact必须恰好一项，实际{count}")


def _validate_phase4_exact_surface(
    collection_root: Path,
    expected_outputs: Dict[Path, str],
    reporter: IssueReporter,
) -> None:
    """Reject every missing, extra, symlinked, or non-regular Phase 4 entry."""
    expected_files = {Path("evidence-collection-index.json")}
    expected_directories = {Path("by-source")}
    for output_path in expected_outputs:
        try:
            relative = output_path.relative_to(collection_root)
        except ValueError:
            reporter.error("phase4-rendered-path", output_path, "机械生成的Markdown path越出source-evidence-collections")
            continue
        expected_files.add(relative)
        expected_directories.update(
            parent
            for parent in relative.parents
            if parent != Path(".")
        )

    actual_files: Set[Path] = set()
    actual_directories: Set[Path] = set()
    invalid_entries: Set[Path] = set()
    if collection_root.is_symlink():
        invalid_entries.add(Path("."))
    elif collection_root.exists() and collection_root.is_dir():
        for path in collection_root.rglob("*"):
            relative = path.relative_to(collection_root)
            if path.is_symlink():
                invalid_entries.add(relative)
            elif path.is_file():
                actual_files.add(relative)
            elif path.is_dir():
                actual_directories.add(relative)
            else:
                invalid_entries.add(relative)

    for relative in sorted(expected_files - actual_files):
        reporter.error("phase4-surface-missing-file", collection_root / relative, "Phase 4 exact surface缺少文件")
    for relative in sorted(actual_files - expected_files):
        reporter.error("phase4-surface-extra-file", collection_root / relative, "Phase 4 exact surface包含未声明文件")
    for relative in sorted(expected_directories - actual_directories):
        reporter.error("phase4-surface-missing-directory", collection_root / relative, "Phase 4 exact surface缺少目录")
    for relative in sorted(actual_directories - expected_directories):
        reporter.error("phase4-surface-extra-directory", collection_root / relative, "Phase 4 exact surface包含未声明目录")
    for relative in sorted(invalid_entries):
        reporter.error("phase4-surface-invalid-entry", collection_root / relative, "Phase 4 exact surface不得包含symlink或非普通文件系统项")


def validate_phase_4(orchestrate_dir: Path, repo_root: Path, reporter: IssueReporter) -> None:
    _validate_phase3_freeze_marker(orchestrate_dir, repo_root, reporter)
    trace_path = orchestrate_dir / "trace/phase-4.trace.json"
    trace = json_obj(trace_path, reporter, PHASE_TRACE_SCHEMAS["phase-4"])
    status = validate_trace_status(trace, trace_path, reporter, "phase-4", "phase4-status") if trace else ""
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
    if status == "blocked":
        exact_fields(
            trace,
            {"trace-schema", "trace-contract-version", "status", "issues"},
            trace_path, reporter, "phase4-trace-fields", "blocked Phase 4 v6 trace",
        )
        if not isinstance(trace.get("issues"), list) or not trace.get("issues"):
            reporter.error("phase4-trace-issues", trace_path, "blocked要求非空issues[]")
        if collection_root.exists():
            for artifact in collection_root.rglob("*"):
                if artifact.is_file():
                    reporter.error("phase4-blocked-derived-artifact", artifact, "blocked Phase 4不得保留未提交派生surface")
        return
    if status != "assembled":
        return
    exact_fields(
        trace,
        {"trace-schema", "trace-contract-version", "status", "assembled"},
        trace_path, reporter, "phase4-trace-fields", "assembled Phase 4 v6 trace",
    )
    assembled = trace.get("assembled")
    if not isinstance(assembled, dict):
        reporter.error("phase4-trace-assembled", trace_path, "assembled必须是object")
        assembled = {}
    else:
        exact_fields(
            assembled,
            {"evidence-collection-index-path", "evidence-collection-index-sha256", "renderer-result-summary"},
            trace_path, reporter, "phase4-trace-assembled-fields", "assembled",
        )
    data = json_obj(index_path, reporter, EVIDENCE_COLLECTION_INDEX_SCHEMA)
    if data:
        _validate_phase4_index_contract(data, index_path, reporter)
    try:
        expected_outputs = render_evidence_collections(orchestrate_dir)
        expected_index = build_evidence_collection_index(orchestrate_dir, expected_outputs)
    except Exception as exc:  # noqa: BLE001
        reporter.error("phase4-assembly", index_path, f"无法从冻结Phase 2/3 evidence authority重算全部Markdown surface与index：{exc}")
        return
    if data != expected_index:
        reporter.error("phase4-derived-index-drift", index_path, "派生index与冻结Phase 2/3 evidence authority及机械生成的全部Markdown surface不一致")
    expected_path = rel(index_path, repo_root)
    if assembled.get("evidence-collection-index-path") != expected_path:
        reporter.error("phase4-trace-index-path", trace_path, f"collection index path应为{expected_path}")
    if index_path.exists() and assembled.get("evidence-collection-index-sha256") != sha256_file(index_path):
        reporter.error("phase4-trace-index-sha", trace_path, "collection index digest不一致")
    expected_summary = {
        "render-contract-version": RENDER_CONTRACT_VERSION,
        "rendered-files": len(expected_outputs),
        "global-atoms": len(expected_index.get("rows", [])),
    }
    if assembled.get("renderer-result-summary") != expected_summary:
        reporter.error("phase4-renderer-summary", trace_path, f"renderer-result-summary应为{expected_summary}")
    for output_path, expected_text in expected_outputs.items():
        if not output_path.exists():
            reporter.error("phase4-rendered-collection", output_path, "缺少机械生成的evidence collection Markdown")
        elif output_path.read_text(encoding="utf-8") != expected_text:
            reporter.error("phase4-rendered-collection-drift", output_path, "evidence collection与冻结Phase 2/3 authority重渲染结果不一致")
    _validate_phase4_exact_surface(collection_root, expected_outputs, reporter)


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


def validate_change_outcome_evidence_alignment(
    roadmap: Dict[str, object],
    roadmap_path: Path,
    reporter: IssueReporter,
) -> None:
    """Bind each Change's own evidence to every outcome thread it realizes."""
    outcomes = {
        normalize_code(row.get("outcome-thread-id")): row
        for row in roadmap.get("outcome-threads", [])
        if isinstance(row, dict)
    }
    for row in roadmap.get("changes", []):
        if not isinstance(row, dict):
            continue
        change = normalize_code(row.get("change"))
        realized = [
            normalize_code(item)
            for item in row.get("realizes-outcome-thread-ids", [])
        ]
        change_outcome = {
            normalize_code(item) for item in row.get("outcome-ga-ids", [])
        }
        change_acceptance = {
            normalize_code(item)
            for item in row.get("acceptance-ga-ids", [])
        }
        if not realized:
            if change_outcome or change_acceptance:
                reporter.error(
                    "phase5-change-outcome-evidence-without-thread",
                    roadmap_path,
                    (
                        f"{change}未realize outcome thread，"
                        "不得声明outcome-ga-ids或acceptance-ga-ids"
                    ),
                )
            continue

        outcome_union: Set[str] = set()
        acceptance_union: Set[str] = set()
        for outcome_id in realized:
            outcome = outcomes.get(outcome_id)
            if not isinstance(outcome, dict):
                continue
            outcome_ids = {
                normalize_code(item)
                for item in outcome.get("outcome-ga-ids", [])
            }
            acceptance_ids = {
                normalize_code(item)
                for item in outcome.get("acceptance-ga-ids", [])
            }
            outcome_union.update(outcome_ids)
            acceptance_union.update(acceptance_ids)
            if not change_outcome.intersection(outcome_ids):
                reporter.error(
                    "phase5-change-outcome-thread-evidence",
                    roadmap_path,
                    (
                        f"{change}.outcome-ga-ids必须与其realize的"
                        f"{outcome_id}.outcome-ga-ids有非空交集"
                    ),
                )
            if not change_acceptance.intersection(acceptance_ids):
                reporter.error(
                    "phase5-change-acceptance-thread-evidence",
                    roadmap_path,
                    (
                        f"{change}.acceptance-ga-ids必须与其realize的"
                        f"{outcome_id}.acceptance-ga-ids有非空交集"
                    ),
                )
        unrelated_outcome = change_outcome - outcome_union
        if unrelated_outcome:
            reporter.error(
                "phase5-change-outcome-evidence-scope",
                roadmap_path,
                (
                    f"{change}.outcome-ga-ids包含不属于其realized outcome "
                    f"thread的GA：{sorted(unrelated_outcome)}"
                ),
            )
        unrelated_acceptance = change_acceptance - acceptance_union
        if unrelated_acceptance:
            reporter.error(
                "phase5-change-acceptance-evidence-scope",
                roadmap_path,
                (
                    f"{change}.acceptance-ga-ids包含不属于其realized outcome "
                    f"thread的GA：{sorted(unrelated_acceptance)}"
                ),
            )


def _validate_phase5_refit(
    orchestrate_dir: Path,
    reporter: IssueReporter,
    final_changes: List[object] | None,
    final_capabilities: List[object] | None,
    final_overlay: Dict[tuple[str, str], str] | None,
    *,
    require_review: bool,
) -> str:
    refit_path = orchestrate_dir / "phase-works/phase-5/framework-refit-trace.json"
    review_path = orchestrate_dir / "phase-works/phase-5/plan-refit-review.md"
    data = json_obj(refit_path, reporter, FRAMEWORK_REFIT_TRACE_SCHEMA)
    if not data:
        return ""
    exact_fields(
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
        refit_path,
        reporter,
        "phase5-refit-fields",
        "framework-refit-trace v5",
    )
    status = normalize_code(data.get("status"))
    try:
        validate_framework_refit(
            orchestrate_dir, data, final_changes, final_capabilities, final_overlay,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        reporter.error("phase5-refit-contract", refit_path, str(exc))
    if require_review:
        require_file(review_path, reporter, "phase5-review", "缺少由framework-refit-trace.json渲染的plan-refit-review.md")
    if review_path.exists() and require_review:
        try:
            expected_review = render_framework_refit_review(orchestrate_dir, refit_path)
        except Exception as exc:  # noqa: BLE001
            reporter.error("phase5-review-render", refit_path, f"无法渲染plan-refit-review.md：{exc}")
        else:
            if review_path.read_text(encoding="utf-8") != expected_review:
                reporter.error("rendered-markdown-drift", review_path, "plan-refit-review.md与framework-refit-trace.json重渲染结果不一致")
    issues = data.get("issues")
    if not isinstance(issues, list):
        reporter.error("phase5-refit-issues", refit_path, "issues必须是array")
    elif status == "blocked" and not issues:
        reporter.error("phase5-refit-issues", refit_path, "blocked要求非空issues[]")
    elif status in FINAL_PHASE5_STATUSES and issues:
        reporter.error("phase5-refit-issues", refit_path, "accepted/adjusted要求issues=[]")
    return status


def _phase5_public_path_is_safe(
    path: Path,
    repo_root: Path,
    reporter: IssueReporter,
    rule_id: str,
) -> bool:
    try:
        symlink = first_symlink_in_repo_path(path, repo_root)
    except ValueError as exc:
        reporter.error(rule_id, path, str(exc))
        return False
    if symlink is not None:
        reporter.error(rule_id, symlink, f"public source bundle路径链不得包含symlink：{symlink}")
        return False
    return True


def _validate_phase5_public_surface(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
    changes: List[object],
    capabilities: List[object],
    mapping: Dict[str, object],
) -> None:
    anchors = orchestrate_dir / "change-capability-anchors"
    if not _phase5_public_path_is_safe(
        anchors, repo_root, reporter, "phase5-public-surface-symlink"
    ):
        return
    if not anchors.is_dir():
        reporter.error("phase5-public-surface-root", anchors, "change-capability-anchors必须是普通目录")
        return
    root_files = {"obligation-atom-index.json", "obligation-atom-index.md", "index.md"}
    expected_changes = {getattr(change, "slug", "") for change in changes}
    for child in anchors.iterdir():
        if not _phase5_public_path_is_safe(
            child, repo_root, reporter, "phase5-public-surface-symlink"
        ):
            continue
        if child.name in root_files:
            if not child.is_file():
                reporter.error("phase5-public-surface-extra", child, "anchor root固定文件不是regular file")
        elif child.name in expected_changes:
            if not child.is_dir():
                reporter.error("phase5-public-surface-extra", child, "Change source bundle不是普通目录")
        else:
            reporter.error("phase5-public-surface-extra", child, "anchor root存在额外public surface")
    capability_order = [getattr(capability, "slug", "") for capability in capabilities]
    for change in changes:
        slug = getattr(change, "slug", "")
        change_dir = anchors / slug
        change_dir_safe = _phase5_public_path_is_safe(
            change_dir, repo_root, reporter, "phase5-public-surface-symlink"
        )
        if not change_dir_safe:
            continue
        if not change_dir.exists():
            reporter.error("phase5-public-surface-missing", change_dir, f"缺少{slug} source bundle目录")
            continue
        if not change_dir.is_dir():
            reporter.error("phase5-public-surface-extra", change_dir, f"{slug} source bundle必须是普通目录")
            continue
        children = {child.name: child for child in change_dir.iterdir()}
        for name, child in children.items():
            if name not in {"change-source.md", "capability-slices"}:
                reporter.error("phase5-public-surface-extra", child, f"{slug}存在旧版或额外公开surface")
        source_path = change_dir / "change-source.md"
        cap_dir = change_dir / "capability-slices"
        source_safe = _phase5_public_path_is_safe(
            source_path, repo_root, reporter, "phase5-public-surface-symlink"
        )
        cap_dir_safe = _phase5_public_path_is_safe(
            cap_dir, repo_root, reporter, "phase5-public-surface-symlink"
        )
        if source_safe and not source_path.exists():
            reporter.error("phase5-public-surface-missing", source_path, f"缺少{slug} change-source.md")
        elif source_safe and not source_path.is_file():
            reporter.error("phase5-public-surface-extra", source_path, "change-source.md必须是regular file")
        expected_caps = {
            capability
            for capability in capability_order
            if any(
                getattr(row, "owner_change", "") == slug
                and getattr(row, "relation", "") == "direct"
                and getattr(row, "projection", "") in SPEC_PROJECTIONS
                and getattr(row, "target_capability", "") == capability
                for row in mapping.values()
            )
        }
        if not cap_dir_safe:
            continue
        if not cap_dir.exists():
            reporter.error("phase5-public-surface-missing", cap_dir, f"缺少{slug} capability-slices目录")
            continue
        if not cap_dir.is_dir():
            reporter.error("phase5-public-surface-extra", cap_dir, "capability-slices必须是普通目录")
            continue
        for child in cap_dir.iterdir():
            if not _phase5_public_path_is_safe(
                child, repo_root, reporter, "phase5-public-surface-symlink"
            ):
                continue
            expected_name = child.name.endswith(".md") and child.stem in expected_caps
            if not expected_name or not child.is_file():
                reporter.error(
                    "phase5-capability-slice-extra",
                    child,
                    f"{slug}存在额外、嵌套或非常规Capability slice surface",
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
    anchors = orchestrate_dir / "change-capability-anchors"
    if not _phase5_public_path_is_safe(
        anchors, repo_root, reporter, "phase5-public-surface-symlink"
    ):
        return
    mapping_path = work / "atom-plan-mapping.json"
    mapping_data = json_obj(mapping_path, reporter, ATOM_PLAN_MAPPING_SCHEMA)
    exact_fields(
        mapping_data,
        ATOM_PLAN_MAPPING_TOP_LEVEL_FIELDS,
        mapping_path,
        reporter,
        "phase5-mapping-top-fields",
        "mapping",
    )
    expected_artifact_path = atom_plan_mapping_markdown_path(mapping_path, repo_root)
    if mapping_data.get("artifact-path") != expected_artifact_path:
        reporter.error("phase5-mapping-artifact-path", mapping_path, f"artifact-path应为{expected_artifact_path}")
    try:
        evidence = load_phase5_evidence(orchestrate_dir)
        mapping = parse_phase5_mapping_rows(mapping_data)
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

    _validate_phase5_public_surface(
        orchestrate_dir,
        repo_root,
        reporter,
        changes,
        capabilities,
        mapping,
    )

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
    change_ids = [getattr(change, "slug", "") for change in changes]
    if [normalize_code(row.get("change")) for row in packets if isinstance(row, dict)] != change_ids:
        reporter.error("phase5-packet-order", packet_index_path, "packet顺序必须与final roadmap一致且每个Change恰好一行")
    by_change = {normalize_code(row.get("change")): row for row in packets if isinstance(row, dict)}
    capability_defs = {getattr(capability, "slug", ""): capability for capability in capabilities}
    for position, change in enumerate(changes):
        slug = getattr(change, "slug", "")
        row = by_change.get(slug)
        if not isinstance(row, dict):
            reporter.error("phase5-packet-missing", packet_index_path, f"缺少final packet：{slug}")
            continue
        exact_fields(
            row,
            {"change", "depends-on", "change-source-path", "change-source-sha256", "capability-slices"},
            packet_index_path,
            reporter,
            "phase5-packet-fields",
            slug,
        )
        if row.get("depends-on") != list(getattr(change, "dependencies", ())):
            reporter.error("phase5-packet-dependencies", packet_index_path, f"{slug} depends-on与roadmap不一致")
        expected_source = orchestrate_dir / "change-capability-anchors" / slug / "change-source.md"
        if row.get("change-source-path") != lexical_rel(expected_source, repo_root):
            reporter.error("phase5-change-source-path", packet_index_path, f"{slug} change-source-path非法")
        source_safe = _phase5_public_path_is_safe(
            expected_source, repo_root, reporter, "phase5-change-source-symlink"
        )
        if source_safe and not expected_source.exists():
            reporter.error("phase5-change-source-missing", expected_source, f"缺少{slug} change source")
        elif source_safe:
            if expected_source.read_text(encoding="utf-8") != render_change_source(change, evidence, mapping):
                reporter.error("phase5-change-source-drift", expected_source, "change source与frozen source-fact或final plan不一致")
            if row.get("change-source-sha256") != sha256_file(expected_source):
                reporter.error("phase5-change-source-digest", packet_index_path, f"{slug} change source digest不一致")
        cap_impacts = {
            item.target_capability: item.capability_impact
            for item in mapping.values()
            if item.owner_change == slug and item.relation == "direct" and item.projection in SPEC_PROJECTIONS
        }
        expected_caps = [getattr(capability, "slug", "") for capability in capabilities if getattr(capability, "slug", "") in cap_impacts]
        slices = row.get("capability-slices")
        if not isinstance(slices, list):
            reporter.error("phase5-capability-slices", packet_index_path, f"{slug} capability-slices必须是array")
            slices = []
        if position > 0 and not slices:
            reporter.error("phase5-foundation-position", packet_index_path, f"只有roadmap首个Change可使用空capability-slices：{slug}")
        if not slices and getattr(change, "dependencies", ()):
            reporter.error("phase5-foundation-dependencies", packet_index_path, f"foundation Change不得有依赖：{slug}")
        actual_caps: List[str] = []
        for item in slices:
            if not isinstance(item, dict):
                reporter.error("phase5-capability-slice-row", packet_index_path, f"{slug} capability slice必须是object")
                continue
            exact_fields(
                item,
                {"capability", "capability-impact", "slice-path", "slice-sha256"},
                packet_index_path,
                reporter,
                "phase5-capability-slice-fields",
                f"{slug} capability slice",
            )
            cap = normalize_code(item.get("capability"))
            actual_caps.append(cap)
            if item.get("capability-impact") != cap_impacts.get(cap):
                reporter.error("phase5-capability-slice-impact", packet_index_path, f"{slug}/{cap} impact与terminal mapping不一致")
            cap_path = expected_source.parent / "capability-slices" / f"{cap}.md"
            if item.get("slice-path") != lexical_rel(cap_path, repo_root):
                reporter.error("phase5-capability-slice-path", packet_index_path, f"{slug}/{cap} slice-path非法")
            cap_safe = _phase5_public_path_is_safe(
                cap_path, repo_root, reporter, "phase5-capability-slice-symlink"
            )
            if cap_safe and not cap_path.exists():
                reporter.error("phase5-capability-slice-missing", cap_path, f"缺少{slug}/{cap} Capability slice")
            elif cap_safe and cap in capability_defs:
                expected_text = render_capability_slice(slug, capability_defs[cap], cap_impacts.get(cap, ""), evidence, mapping)
                if cap_path.read_text(encoding="utf-8") != expected_text:
                    reporter.error("phase5-capability-slice-drift", cap_path, "Capability slice与terminal mapping或frozen source-fact不一致")
                if item.get("slice-sha256") != sha256_file(cap_path):
                    reporter.error("phase5-capability-slice-digest", packet_index_path, f"{slug}/{cap} slice digest不一致")
        if actual_caps != expected_caps:
            reporter.error("phase5-capability-slice-order", packet_index_path, f"{slug} capability slice集合或顺序与terminal mapping不一致")
    anchors = orchestrate_dir / "change-capability-anchors"
    anchor_index = anchors / "index.md"
    anchor_index_safe = _phase5_public_path_is_safe(
        anchor_index, repo_root, reporter, "phase5-public-surface-symlink"
    )
    if anchor_index_safe and anchor_index.exists():
        expected_anchor_index = render_anchor_index(changes, capabilities, mapping, repo_root, anchors)
        if anchor_index.read_text(encoding="utf-8") != expected_anchor_index:
            reporter.error("phase5-anchor-index-drift", anchor_index, "anchor index与final plan及source bundle不一致")


def validate_phase_5(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
    complete: bool = False,
    preflight: bool = False,
) -> None:
    work = orchestrate_dir / "phase-works/phase-5"
    trace_path = orchestrate_dir / "trace/phase-5.trace.json"
    trace = json_obj(trace_path, reporter, PHASE_TRACE_SCHEMAS["phase-5"])
    trace_status = validate_trace_status(trace, trace_path, reporter, "phase-5", "phase5-status") if trace else ""
    if trace:
        try:
            require_phase3_frozen_evidence(
                orchestrate_dir,
                repo_root,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            reporter.error(
                "phase5-frozen-evidence-prerequisite",
                trace_path,
                str(exc),
            )
    require_file(work / "phase-5-agent-report.md", reporter, "phase5-interface-artifact", "缺少Phase 5 agent报告")
    legacy_names = [
        "phase5-refit.config.json", "input-change-plan.md", "source-window-refit-trace.md",
        "change-plan-adjustments.md", "capability-progression-review.md", "change-complexity-review.md",
        "plan-refit-decision-log.md", "alignment-final-report.md", "change-capability-human-plan.md",
        "evidence-patch-request.json", "phase-5-checkpoint.json",
    ]
    for name in legacy_names:
        path = work / name
        if path.exists():
            reporter.error("phase5-legacy-artifact", path, "旧Phase 5或patch/checkpoint artifact已废弃，v7 workflow必须拒绝且不得迁移")

    final_plan_path = work / "change-plan.md"
    final_changes: List[object] | None = None
    final_capabilities: List[object] | None = None
    final_overlay: Dict[tuple[str, str], str] | None = None
    if final_plan_path.exists():
        try:
            phase5_evidence = load_phase5_evidence(orchestrate_dir)
            (
                _final_roadmap,
                final_changes,
                final_capabilities,
                final_overlay,
            ) = load_final_roadmap_defs(orchestrate_dir, phase5_evidence)
            validate_change_outcome_evidence_alignment(
                _final_roadmap,
                work / "final-roadmap.json",
                reporter,
            )
        except (OSError, ValueError) as exc:
            reporter.error(
                "phase5-final-roadmap-contract",
                work / "final-roadmap.json",
                str(exc),
            )
    refit_path = work / "framework-refit-trace.json"
    review_path = work / "plan-refit-review.md"
    block_kind = normalize_code(trace.get("block-kind"))
    refit_status = _validate_phase5_refit(
        orchestrate_dir,
        reporter,
        final_changes,
        final_capabilities,
        final_overlay,
        require_review=(
            trace_status in FINAL_PHASE5_STATUSES
            or trace_status in {"review-pending", "blocked"}
        ),
    )
    if (
        trace_status
        and trace_status != "review-pending"
        and not (
            trace_status == "blocked"
            and block_kind == "bounded-review"
            and refit_status in FINAL_PHASE5_STATUSES
        )
        and refit_status
        and trace_status != refit_status
    ):
        reporter.error("phase5-status-drift", trace_path, f"phase trace status {trace_status}与framework refit status {refit_status}不一致")

    if trace_status == "review-pending":
        exact_fields(
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
            trace_path,
            reporter,
            "phase5-candidate-trace-fields",
            "review-pending Phase 5 v6 trace",
        )
        candidate_paths = (
            ("framework-refit-trace", refit_path),
            ("final-roadmap", work / "final-roadmap.json"),
            ("atom-plan-mapping", work / "atom-plan-mapping.json"),
            ("candidate-final-change-plan", final_plan_path),
        )
        for prefix, candidate_path in candidate_paths:
            require_file(
                candidate_path,
                reporter,
                "phase5-candidate-artifact",
                f"缺少Phase 5 candidate artifact：{candidate_path.name}",
            )
            if trace.get(f"{prefix}-path") != rel(candidate_path, repo_root):
                reporter.error(
                    "phase5-candidate-trace-path",
                    trace_path,
                    f"{prefix}-path与canonical path不一致",
                )
            if (
                candidate_path.exists()
                and trace.get(f"{prefix}-sha256")
                != sha256_file(candidate_path)
            ):
                reporter.error(
                    "phase5-candidate-trace-sha",
                    trace_path,
                    f"{prefix} digest与candidate不一致",
                )
        if (
            final_changes is not None
            and final_capabilities is not None
            and final_overlay is not None
            and final_plan_path.exists()
        ):
            try:
                evidence = load_phase5_evidence(orchestrate_dir)
                roadmap, _, _, _ = load_final_roadmap_defs(
                    orchestrate_dir,
                    evidence,
                )
                expected_plan = render_final_plan_from_roadmap(
                    roadmap,
                    final_changes,
                    final_capabilities,
                    final_overlay,
                )
                if final_plan_path.read_text(encoding="utf-8") != expected_plan:
                    reporter.error(
                        "phase5-candidate-plan-drift",
                        final_plan_path,
                        "candidate plan必须由final-roadmap确定性渲染",
                    )
                current_digests = phase5_candidate_authority(
                    orchestrate_dir,
                    expected_plan,
                )
                if (
                    trace.get("frozen-evidence-authority-sha256")
                    != current_digests[
                        "frozen-evidence-authority-sha256"
                    ]
                    or trace.get("phase-3-freeze-trace-path")
                    != rel(
                        orchestrate_dir / "trace/phase-3.trace.json",
                        repo_root,
                    )
                    or trace.get("phase-3-freeze-trace-sha256")
                    != current_digests[
                        "phase-3-freeze-trace-sha256"
                    ]
                    or trace.get("candidate-handoff-sha256")
                    != current_digests["candidate-handoff-sha256"]
                ):
                    reporter.error(
                        "phase5-candidate-frozen-authority",
                        trace_path,
                        "candidate trace未绑定当前frozen evidence、"
                        "Phase 3 freeze或完整handoff派生摘要",
                    )
                validate_phase5_review_gate(
                    trace.get("review-gate"),
                    current_digests=current_digests,
                )
                mapping_data = json_obj(
                    work / "atom-plan-mapping.json",
                    reporter,
                    ATOM_PLAN_MAPPING_SCHEMA,
                )
                mapping = parse_phase5_mapping_rows(mapping_data)
                validate_phase5_mapping(
                    evidence,
                    mapping,
                    final_changes,
                    final_capabilities,
                    final_overlay,
                    repo_root=repo_root,
                )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                reporter.error(
                    "phase5-candidate-contract",
                    trace_path,
                    str(exc),
                )
        forbidden_published = (
            orchestrate_dir / "change-plan.md",
            work / "final-packet-index.json",
            orchestrate_dir / "change-capability-anchors/index.md",
        )
        for published_path in forbidden_published:
            if published_path.exists():
                reporter.error(
                    "phase5-candidate-premature-publish",
                    published_path,
                    "review-pending不得发布terminal handoff",
                )
        anchors_dir = orchestrate_dir / "change-capability-anchors"
        if anchors_dir.exists():
            for child in anchors_dir.iterdir():
                if child.is_dir():
                    reporter.error(
                        "phase5-candidate-premature-publish",
                        child,
                        "review-pending不得发布Change source bundle",
                    )
        if complete:
            reporter.error(
                "phase5-complete-status",
                trace_path,
                "--complete要求accepted/adjusted，实际为review-pending",
            )
        return

    if trace_status == "blocked":
        if block_kind == "framework-refit":
            exact_fields(
                trace,
                {
                    "trace-schema",
                    "trace-contract-version",
                    "status",
                    "block-kind",
                    "framework-refit-trace-path",
                    "framework-refit-trace-sha256",
                    "plan-refit-review-path",
                    "plan-refit-review-sha256",
                    "issues",
                },
                trace_path,
                reporter,
                "phase5-trace-fields",
                "framework-refit blocked Phase 5 v6 trace",
            )
            if refit_status != "blocked":
                reporter.error(
                    "phase5-block-kind",
                    trace_path,
                    "framework-refit block要求framework refit status=blocked",
                )
            for prefix, path in (
                ("framework-refit-trace", refit_path),
                ("plan-refit-review", review_path),
            ):
                if trace.get(f"{prefix}-path") != rel(path, repo_root):
                    reporter.error(
                        "phase5-trace-path",
                        trace_path,
                        f"{prefix}-path与canonical path不一致",
                    )
                if (
                    path.exists()
                    and trace.get(f"{prefix}-sha256")
                    != sha256_file(path)
                ):
                    reporter.error(
                        "phase5-trace-sha",
                        trace_path,
                        f"{prefix} digest与trace不一致",
                    )
            issues = trace.get("issues")
            if not isinstance(issues, list) or not issues:
                reporter.error(
                    "phase5-trace-issues",
                    trace_path,
                    "framework-refit blocked要求非空issues[]",
                )
            elif refit_path.exists():
                try:
                    refit_issues = read_json(refit_path).get("issues")
                except Exception:  # noqa: BLE001
                    refit_issues = None
                if issues != refit_issues:
                    reporter.error(
                        "phase5-trace-issues",
                        trace_path,
                        "framework-refit blocked issues必须与refit逐字一致",
                    )
            forbidden_private = (
                work / "final-roadmap.json",
                final_plan_path,
                work / "atom-plan-mapping.json",
            )
            for path in forbidden_private:
                if path.exists() or path.is_symlink():
                    reporter.error(
                        "phase5-blocked-candidate-artifact",
                        path,
                        "framework-refit blocked不得保留未绑定candidate authority",
                    )
        elif block_kind == "bounded-review":
            exact_fields(
                trace,
                {
                    "trace-schema",
                    "trace-contract-version",
                    "status",
                    "block-kind",
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
                    "issues",
                },
                trace_path,
                reporter,
                "phase5-trace-fields",
                "bounded-review blocked Phase 5 v6 trace",
            )
            if refit_status not in FINAL_PHASE5_STATUSES:
                reporter.error(
                    "phase5-block-kind",
                    trace_path,
                    "bounded-review block要求accepted/adjusted refit",
                )
            candidate_paths = (
                ("framework-refit-trace", refit_path),
                ("final-roadmap", work / "final-roadmap.json"),
                ("atom-plan-mapping", work / "atom-plan-mapping.json"),
                ("candidate-final-change-plan", final_plan_path),
            )
            for prefix, candidate_path in candidate_paths:
                require_file(
                    candidate_path,
                    reporter,
                    "phase5-candidate-artifact",
                    f"缺少blocked candidate artifact：{candidate_path.name}",
                )
                if trace.get(f"{prefix}-path") != rel(
                    candidate_path,
                    repo_root,
                ):
                    reporter.error(
                        "phase5-candidate-trace-path",
                        trace_path,
                        f"{prefix}-path与canonical path不一致",
                    )
                if (
                    candidate_path.exists()
                    and trace.get(f"{prefix}-sha256")
                    != sha256_file(candidate_path)
                ):
                    reporter.error(
                        "phase5-candidate-trace-sha",
                        trace_path,
                        f"{prefix} digest与candidate不一致",
                    )
            if final_plan_path.exists():
                try:
                    current_digests = phase5_candidate_authority(
                        orchestrate_dir,
                        final_plan_path.read_text(encoding="utf-8"),
                    )
                    if (
                        trace.get("frozen-evidence-authority-sha256")
                        != current_digests[
                            "frozen-evidence-authority-sha256"
                        ]
                        or trace.get("phase-3-freeze-trace-path")
                        != rel(
                            orchestrate_dir / "trace/phase-3.trace.json",
                            repo_root,
                        )
                        or trace.get("phase-3-freeze-trace-sha256")
                        != current_digests[
                            "phase-3-freeze-trace-sha256"
                        ]
                        or trace.get("candidate-handoff-sha256")
                        != current_digests["candidate-handoff-sha256"]
                    ):
                        reporter.error(
                            "phase5-bounded-block-authority",
                            trace_path,
                            "bounded-review blocked trace的frozen evidence"
                            "或handoff digest漂移",
                        )
                    gate_status = validate_phase5_review_gate(
                        trace.get("review-gate"),
                        current_digests=current_digests,
                    )
                    if gate_status != "blocked":
                        reporter.error(
                            "phase5-review-gate-status",
                            trace_path,
                            "bounded-review blocked要求review-gate blocked",
                        )
                    gate = trace.get("review-gate")
                    if not isinstance(gate, dict):
                        raise ValueError(
                            "bounded-review blocked review-gate必须是object"
                        )
                    expected_issues = phase5_bounded_review_issues(gate)
                    if trace.get("issues") != expected_issues:
                        reporter.error(
                            "phase5-trace-issues",
                            trace_path,
                            "bounded-review blocked issues与review-gate不一致",
                        )
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    reporter.error(
                        "phase5-bounded-block-review",
                        trace_path,
                        str(exc),
                    )
            if (
                final_changes is not None
                and final_capabilities is not None
                and final_overlay is not None
                and final_plan_path.exists()
            ):
                try:
                    evidence = load_phase5_evidence(orchestrate_dir)
                    roadmap, _, _, _ = load_final_roadmap_defs(
                        orchestrate_dir,
                        evidence,
                    )
                    expected_plan = render_final_plan_from_roadmap(
                        roadmap,
                        final_changes,
                        final_capabilities,
                        final_overlay,
                    )
                    if (
                        final_plan_path.read_text(encoding="utf-8")
                        != expected_plan
                    ):
                        reporter.error(
                            "phase5-candidate-plan-drift",
                            final_plan_path,
                            "blocked candidate plan必须由final-roadmap确定性渲染",
                        )
                    mapping_data = json_obj(
                        work / "atom-plan-mapping.json",
                        reporter,
                        ATOM_PLAN_MAPPING_SCHEMA,
                    )
                    mapping = parse_phase5_mapping_rows(mapping_data)
                    validate_phase5_mapping(
                        evidence,
                        mapping,
                        final_changes,
                        final_capabilities,
                        final_overlay,
                        repo_root=repo_root,
                    )
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    reporter.error(
                        "phase5-bounded-block-contract",
                        trace_path,
                        str(exc),
                    )
        else:
            reporter.error(
                "phase5-block-kind",
                trace_path,
                "blocked Phase 5必须明确block-kind="
                "framework-refit|bounded-review",
            )

        terminal_paths = [
            work / "atom-plan-mapping.md",
            work / "capability-baseline-reconciliation.json",
            work / "capability-baseline-reconciliation.md",
            work / "final-packet-index.json",
            orchestrate_dir / "change-plan.md",
            orchestrate_dir / "final-integration-review.json",
            orchestrate_dir / "final-integration-review.md",
            orchestrate_dir / "trace/workflow-completion.trace.json",
            orchestrate_dir / "change-capability-anchors/index.md",
        ]
        for path in terminal_paths:
            if path.exists() or path.is_symlink():
                reporter.error(
                    "phase5-blocked-terminal-artifact",
                    path,
                    "blocked状态不得保留Phase 5 terminal/public artifact",
                )
        manifest_path = orchestrate_dir / "trace/manifest.json"
        if manifest_path.exists():
            try:
                workflow_status = normalize_code(
                    read_json(manifest_path).get("workflow-status")
                )
            except Exception:  # noqa: BLE001
                workflow_status = "invalid"
            if workflow_status not in {"", "pending"}:
                reporter.error(
                    "phase5-blocked-terminal-manifest",
                    manifest_path,
                    "blocked Phase 5不得覆盖或并存于terminal workflow manifest",
                )
        anchors_dir = orchestrate_dir / "change-capability-anchors"
        if anchors_dir.exists():
            for child in anchors_dir.iterdir():
                if child.is_dir():
                    reporter.error(
                        "phase5-blocked-terminal-artifact",
                        child,
                        "blocked状态不得保留change source或Capability slice",
                    )
        if complete:
            reporter.error("phase5-complete-status", trace_path, "--complete要求accepted/adjusted，实际为blocked")
        return

    if trace_status not in FINAL_PHASE5_STATUSES:
        if complete:
            reporter.error("phase5-complete-status", trace_path, f"--complete要求accepted/adjusted，实际为{trace_status or 'missing'}")
        return
    exact_fields(
        trace,
        {
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
        },
        trace_path, reporter, "phase5-trace-fields", "terminal Phase 5 v6 trace",
    )
    required = [
        work / "final-roadmap.json", final_plan_path, refit_path, review_path, work / "atom-plan-mapping.json",
        work / "atom-plan-mapping.md", work / "capability-baseline-reconciliation.json",
        work / "capability-baseline-reconciliation.md", work / "final-packet-index.json",
        orchestrate_dir / "change-plan.md", orchestrate_dir / "change-capability-anchors/index.md",
    ]
    for path in required:
        require_file(path, reporter, "phase5-interface-artifact", f"缺少Phase 5 terminal artifact：{path.name}")
    require_same_file(
        final_plan_path, orchestrate_dir / "change-plan.md", reporter,
        "phase5-root-plan-drift", "根change-plan.md必须与Phase 5 final plan逐字节一致",
    )
    if final_changes is not None and final_capabilities is not None and final_overlay is not None:
        _validate_phase5_derived_outputs(orchestrate_dir, repo_root, reporter, final_changes, final_capabilities, final_overlay)
        try:
            current_digests = phase5_candidate_authority(
                orchestrate_dir,
                final_plan_path.read_text(encoding="utf-8"),
            )
            if (
                trace.get("frozen-evidence-authority-sha256")
                != current_digests[
                    "frozen-evidence-authority-sha256"
                ]
                or trace.get("phase-3-freeze-trace-path")
                != rel(
                    orchestrate_dir / "trace/phase-3.trace.json",
                    repo_root,
                )
                or trace.get("phase-3-freeze-trace-sha256")
                != current_digests[
                    "phase-3-freeze-trace-sha256"
                ]
                or trace.get("candidate-handoff-sha256")
                != current_digests["candidate-handoff-sha256"]
            ):
                reporter.error(
                    "phase5-terminal-candidate-authority",
                    trace_path,
                    "terminal trace的frozen evidence或handoff digest漂移",
                )
            if (
                validate_phase5_review_gate(
                    trace.get("review-gate"),
                    current_digests=current_digests,
                )
                != "passed"
            ):
                reporter.error(
                    "phase5-review-gate-status",
                    trace_path,
                    "terminal Phase 5要求review-gate passed",
                )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            reporter.error("phase5-review-gate", trace_path, str(exc))
    trace_specs = [
        ("final-roadmap", work / "final-roadmap.json"),
        ("final-change-plan", final_plan_path), ("framework-refit-trace", refit_path),
        ("plan-refit-review", review_path), ("atom-plan-mapping", work / "atom-plan-mapping.json"),
        ("capability-baseline-reconciliation", work / "capability-baseline-reconciliation.json"),
        ("final-packet-index", work / "final-packet-index.json"),
    ]
    for prefix, path in trace_specs:
        if trace.get(f"{prefix}-path") != rel(path, repo_root):
            reporter.error("phase5-trace-path", trace_path, f"{prefix}-path应为{rel(path, repo_root)}")
        if path.exists() and trace.get(f"{prefix}-sha256") != sha256_file(path):
            reporter.error("phase5-trace-sha", trace_path, f"{prefix} digest与trace不一致")


def _workflow_gate_identities(orchestrate_dir: Path) -> Set[str]:
    identities: Set[str] = set()
    for phase in ("phase-1", "phase-3", "phase-5"):
        path = orchestrate_dir / f"trace/{phase}.trace.json"
        if not path.exists():
            continue
        try:
            trace = read_json(path)
        except Exception:  # noqa: BLE001
            continue
        gate = trace.get("review-gate")
        if not isinstance(gate, dict):
            continue
        for field in (
            "writer-id",
            "phase-2-aggregate-writer-id",
            "phase-3-writer-id",
        ):
            value = squash(gate.get(field))
            if value:
                identities.add(value)
        owners = gate.get("phase-2-canonical-owner-ids")
        if isinstance(owners, list):
            identities.update(squash(item) for item in owners if squash(item))
        for row in gate.get("reviews", []):
            if isinstance(row, dict) and squash(row.get("reviewer-id")):
                identities.add(squash(row.get("reviewer-id")))
        for row in gate.get("repairs", []):
            if isinstance(row, dict) and squash(row.get("repair-writer-id")):
                identities.add(squash(row.get("repair-writer-id")))
    return identities


def _review_allowed_evidence(
    roadmap: Dict[str, object],
    mapping: Dict[str, object],
) -> Tuple[
    Dict[str, Set[str]],
    Dict[str, Set[str]],
    Dict[str, Set[str]],
    Dict[str, Set[str]],
    Dict[str, Set[str]],
]:
    """Derive the only GA sets that may attest every final review unit."""
    capability_allowed: Dict[str, Set[str]] = {}
    for row in roadmap.get("capabilities", []):
        if not isinstance(row, dict):
            continue
        capability = normalize_code(row.get("capability"))
        capability_allowed[capability] = {
            normalize_code(item)
            for item in row.get("evidence-ga-ids", [])
        }
    for ga, item in mapping.items():
        if (
            getattr(item, "relation", "") == "direct"
            and getattr(item, "projection", "") in SPEC_PROJECTIONS
        ):
            target = getattr(item, "target_capability", "")
            capability_allowed.setdefault(target, set()).add(ga)

    outcomes = {
        normalize_code(row.get("outcome-thread-id")): row
        for row in roadmap.get("outcome-threads", [])
        if isinstance(row, dict)
    }
    changes = {
        normalize_code(row.get("change")): row
        for row in roadmap.get("changes", [])
        if isinstance(row, dict)
    }
    change_allowed: Dict[str, Set[str]] = {
        change: set() for change in changes
    }
    for ga, item in mapping.items():
        owner = getattr(item, "owner_change", "")
        if owner in change_allowed:
            change_allowed[owner].add(ga)
    for change, row in changes.items():
        allowed = change_allowed[change]
        allowed.update(
            normalize_code(item) for item in row.get("outcome-ga-ids", [])
        )
        allowed.update(
            normalize_code(item)
            for item in row.get("acceptance-ga-ids", [])
        )
        for outcome_id in row.get("realizes-outcome-thread-ids", []):
            outcome = outcomes.get(normalize_code(outcome_id))
            if not isinstance(outcome, dict):
                continue
            allowed.update(
                normalize_code(item)
                for item in outcome.get("outcome-ga-ids", [])
            )
            allowed.update(
                normalize_code(item)
                for item in outcome.get("acceptance-ga-ids", [])
            )

    for edge in roadmap.get("dependency-edges", []):
        if not isinstance(edge, dict):
            continue
        edge_evidence = {
            normalize_code(item)
            for item in edge.get("evidence-ga-ids", [])
        }
        for endpoint in ("prerequisite-change", "dependent-change"):
            change = normalize_code(edge.get(endpoint))
            if change in change_allowed:
                change_allowed[change].update(edge_evidence)

    realized_by_outcome: Dict[str, Set[str]] = {}
    for change, row in changes.items():
        for outcome_id in row.get("realizes-outcome-thread-ids", []):
            realized_by_outcome.setdefault(
                normalize_code(outcome_id),
                set(),
            ).add(change)
    for guard in roadmap.get("guard-links", []):
        if not isinstance(guard, dict):
            continue
        guard_evidence = {
            normalize_code(item)
            for item in guard.get("evidence-ga-ids", [])
        }
        related_changes = set(
            realized_by_outcome.get(
                normalize_code(guard.get("guarded-outcome-thread-id")),
                set(),
            )
        )
        related_changes.add(normalize_code(guard.get("guarding-change")))
        for change in related_changes:
            if change in change_allowed:
                change_allowed[change].update(guard_evidence)

    foundation = roadmap.get("foundation")
    if isinstance(foundation, dict):
        foundation_change = normalize_code(foundation.get("change"))
        if foundation_change in change_allowed:
            change_allowed[foundation_change].update(
                normalize_code(item)
                for item in foundation.get("evidence-ga-ids", [])
            )
    outcome_allowed = {
        normalize_code(row.get("outcome-thread-id")): {
            normalize_code(item)
            for field in ("outcome-ga-ids", "acceptance-ga-ids")
            for item in row.get(field, [])
        }
        for row in roadmap.get("outcome-threads", [])
        if isinstance(row, dict)
    }
    dependency_allowed = {
        normalize_code(row.get("dependency-id")): {
            normalize_code(item)
            for item in row.get("evidence-ga-ids", [])
        }
        for row in roadmap.get("dependency-edges", [])
        if isinstance(row, dict)
    }
    guard_allowed = {
        normalize_code(row.get("guard-link-id")): {
            normalize_code(item)
            for item in row.get("evidence-ga-ids", [])
        }
        for row in roadmap.get("guard-links", [])
        if isinstance(row, dict)
    }
    return (
        capability_allowed,
        change_allowed,
        outcome_allowed,
        dependency_allowed,
        guard_allowed,
    )


def _validate_scoped_review_evidence(
    *,
    field: str,
    unit_id: str,
    evidence_ids: object,
    allowed: Set[str],
    review_path: Path,
    reporter: IssueReporter,
    gate: str = "",
) -> None:
    actual = (
        {normalize_code(item) for item in evidence_ids}
        if isinstance(evidence_ids, list)
        else set()
    )
    label = f"{field}.{unit_id}"
    if gate:
        label += f".gate[{gate}]"
    if not actual.intersection(allowed):
        reporter.error(
            "workflow-unit-review-evidence-unrelated",
            review_path,
            f"{label} evidence必须与该终态unit的allowed GA有非空交集",
        )
    unrelated = actual - allowed
    if unrelated:
        reporter.error(
            "workflow-unit-review-evidence-scope",
            review_path,
            f"{label}包含不属于该终态unit的GA：{sorted(unrelated)}",
        )


def validate_final_integration_review_candidate(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
) -> Dict[str, object] | None:
    """Validate the one-shot review authority before completion is published."""
    review_path = orchestrate_dir / "final-integration-review.json"
    if not review_path.is_file():
        reporter.error(
            "workflow-final-review",
            review_path,
            "缺少final-integration-review.json",
        )
        return None
    try:
        terminal_digest = terminal_authority_sha256(
            orchestrate_dir,
            repo_root,
        )
        review = load_final_integration_review(
            review_path,
            expected_terminal_digest=terminal_digest,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        reporter.error("workflow-final-review", review_path, str(exc))
        return None
    expected_reviewed = terminal_authority_payload(
        orchestrate_dir,
        repo_root,
    )["artifacts"]
    if review.get("reviewed-artifacts") != expected_reviewed:
        reporter.error(
            "workflow-reviewed-artifacts",
            review_path,
            "reviewed-artifacts必须按固定七路径精确绑定terminal authority",
        )
    reviewer_id = squash(review.get("reviewer-id"))
    if reviewer_id in _workflow_gate_identities(orchestrate_dir):
        reporter.error(
            "workflow-reviewer-independence",
            review_path,
            "final integration reviewer必须与全部writer/reviewer/repair writer不同",
        )
    try:
        evidence = load_phase5_evidence(orchestrate_dir)
        roadmap, parsed = load_final_roadmap(
            orchestrate_dir / "phase-works/phase-5/final-roadmap.json",
            known_ga_ids=set(evidence),
            evidence_directives={
                ga: item.delivery_directives
                for ga, item in evidence.items()
                if item.delivery_directives
            },
        )
        validate_change_outcome_evidence_alignment(
            roadmap,
            orchestrate_dir / "phase-works/phase-5/final-roadmap.json",
            reporter,
        )
        mapping_data = read_json(
            orchestrate_dir
            / "phase-works/phase-5/atom-plan-mapping.json"
        )
        if not isinstance(mapping_data, dict):
            raise ValueError("atom-plan-mapping.json必须是object")
        mapping = parse_phase5_mapping_rows(mapping_data)
        (
            capability_allowed,
            change_allowed,
            outcome_allowed,
            dependency_allowed,
            guard_allowed,
        ) = _review_allowed_evidence(roadmap, mapping)
        allowed_by_field = {
            "capability-results": capability_allowed,
            "change-results": change_allowed,
            "outcome-thread-results": outcome_allowed,
            "dependency-edge-results": dependency_allowed,
            "guard-link-results": guard_allowed,
        }
        expected_units = {
            "capability-results": (
                "capability",
                [
                    normalize_code(row.get("capability"))
                    for row in parsed["capabilities"]
                ],
            ),
            "change-results": (
                "change",
                list(parsed["change-order"]),
            ),
            "outcome-thread-results": (
                "outcome-thread-id",
                [
                    normalize_code(row.get("outcome-thread-id"))
                    for row in parsed["outcomes"]
                ],
            ),
            "dependency-edge-results": (
                "dependency-id",
                [
                    normalize_code(row.get("dependency-id"))
                    for row in parsed["dependencies"]
                ],
            ),
            "guard-link-results": (
                "guard-link-id",
                [
                    normalize_code(row.get("guard-link-id"))
                    for row in parsed["guards"]
                ],
            ),
        }
        for field, (id_field, expected_ids) in expected_units.items():
            rows = [
                row
                for row in review.get(field, [])
                if isinstance(row, dict)
            ]
            actual_ids = [
                normalize_code(row.get(id_field)) for row in rows
            ]
            if actual_ids != expected_ids:
                reporter.error(
                    "workflow-unit-review-coverage",
                    review_path,
                    f"{field}必须按final-roadmap顺序恰好覆盖全部unit",
                )
            for row in rows:
                unit_id = normalize_code(row.get(id_field))
                evidence_ids = row.get("evidence-ga-ids")
                if not isinstance(evidence_ids, list) or any(
                    normalize_code(item) not in evidence
                    for item in evidence_ids
                ):
                    reporter.error(
                        "workflow-unit-review-evidence",
                        review_path,
                        f"{field}包含未知GA",
                    )
                allowed = allowed_by_field[field].get(unit_id, set())
                _validate_scoped_review_evidence(
                    field=field,
                    unit_id=unit_id,
                    evidence_ids=evidence_ids,
                    allowed=allowed,
                    review_path=review_path,
                    reporter=reporter,
                )
                gate_results = row.get("gate-results")
                if isinstance(gate_results, list):
                    for gate_row in gate_results:
                        gate_ids = (
                            gate_row.get("evidence-ga-ids")
                            if isinstance(gate_row, dict)
                            else None
                        )
                        if not isinstance(gate_ids, list) or any(
                            normalize_code(item) not in evidence
                            for item in gate_ids
                        ):
                            reporter.error(
                                "workflow-unit-review-gate-evidence",
                                review_path,
                                f"{field} gate包含未知GA",
                            )
                        _validate_scoped_review_evidence(
                            field=field,
                            unit_id=unit_id,
                            evidence_ids=gate_ids,
                            allowed=allowed,
                            review_path=review_path,
                            reporter=reporter,
                            gate=(
                                normalize_code(gate_row.get("gate"))
                                if isinstance(gate_row, dict)
                                else ""
                            ),
                        )
        occurrence = review.get("occurrence-chain-result")
        actual_ga_ids = (
            occurrence.get("evidence-ga-ids")
            if isinstance(occurrence, dict)
            else None
        )
        if actual_ga_ids != list(evidence):
            reporter.error(
                "workflow-occurrence-chain",
                review_path,
                "occurrence-chain必须按global index顺序恰好覆盖全部GA",
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        reporter.error("workflow-review-roadmap", review_path, str(exc))
    return review


def validate_workflow_terminal(
    orchestrate_dir: Path,
    repo_root: Path,
    reporter: IssueReporter,
    *,
    required: bool,
) -> None:
    review_path = orchestrate_dir / "final-integration-review.json"
    review_md_path = orchestrate_dir / "final-integration-review.md"
    attempt_path = (
        orchestrate_dir
        / FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH
    )
    attempt_result_path = (
        orchestrate_dir
        / FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH
    )
    completion_path = (
        orchestrate_dir / "trace/workflow-completion.trace.json"
    )
    workflow_paths = (
        review_path,
        attempt_path,
        attempt_result_path,
        completion_path,
    )
    if not required and not any(
        path.exists() or path.is_symlink() for path in workflow_paths
    ):
        return
    for path, rule_id, message in (
        (
            review_path,
            "workflow-final-review",
            "缺少final-integration-review.json",
        ),
        (
            attempt_path,
            "workflow-final-review-attempt",
            "缺少final-integration-review-attempt.trace.json",
        ),
        (
            attempt_result_path,
            "workflow-final-review-attempt-result",
            "缺少final-integration-review-attempt-result.trace.json",
        ),
    ):
        require_file(path, reporter, rule_id, message)

    attempt: Dict[str, object] | None = None
    if review_path.is_file() and attempt_path.is_file():
        try:
            attempt = load_final_integration_review_attempt(
                attempt_path,
                review_path=review_path,
                repo_root=repo_root,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            reporter.error(
                "workflow-final-review-attempt",
                attempt_path,
                str(exc),
            )

    terminal_digest: str | None = None
    try:
        terminal_digest = terminal_authority_sha256(
            orchestrate_dir,
            repo_root,
        )
    except (OSError, ValueError) as exc:
        reporter.error(
            "workflow-terminal-authority",
            orchestrate_dir,
            str(exc),
        )

    attempt_result: Dict[str, object] | None = None
    if attempt_path.is_file() and attempt_result_path.is_file():
        try:
            attempt_result = (
                load_final_integration_review_attempt_result(
                    attempt_result_path,
                    attempt_path=attempt_path,
                    repo_root=repo_root,
                    expected_terminal_digest=terminal_digest,
                )
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            reporter.error(
                "workflow-final-review-attempt-result",
                attempt_result_path,
                str(exc),
            )

    if not completion_path.exists() and not completion_path.is_symlink():
        if attempt_result is not None:
            if attempt_result.get("status") == "blocked":
                reporter.error(
                    "workflow-early-blocked-attempt",
                    attempt_result_path,
                    "one-shot attempt已blocked且没有合法completion；"
                    "当前generation fail-closed，不得替换review或重试",
                )
            else:
                reporter.error(
                    "workflow-incomplete-attempt",
                    attempt_result_path,
                    "one-shot attempt已passed但completion尚未发布；"
                    "当前generation不可消费或重新审查",
                )
        elif attempt is not None:
            reporter.error(
                "workflow-incomplete-attempt",
                attempt_path,
                "one-shot attempt仍为submitted且尚未终态化",
            )
        else:
            reporter.error(
                "workflow-completion",
                completion_path,
                "缺少workflow-completion.trace.json",
            )
        return
    require_file(
        completion_path,
        reporter,
        "workflow-completion",
        "缺少workflow-completion.trace.json",
    )
    if (
        terminal_digest is None
        or not review_path.is_file()
        or attempt is None
        or attempt_result is None
    ):
        return
    review = validate_final_integration_review_candidate(
        orchestrate_dir,
        repo_root,
        reporter,
    )
    if review is None:
        return
    validate_rendered_markdown(
        orchestrate_dir,
        review_path,
        review_md_path,
        render_final_integration_review,
        reporter,
        "workflow-final-integration-review",
    )
    try:
        completion = load_workflow_completion(
            completion_path,
            review_path=review_path,
            expected_terminal_digest=terminal_digest,
            repo_root=repo_root,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        reporter.error("workflow-completion", completion_path, str(exc))
        return
    expected_completion_status = (
        "integration-passed"
        if review.get("status") == "passed"
        else "blocked"
    )
    expected_attempt_status = (
        "passed" if review.get("status") == "passed" else "blocked"
    )
    if attempt_result.get("status") != expected_attempt_status:
        reporter.error(
            "workflow-attempt-result-status",
            attempt_result_path,
            "attempt result status必须与final integration review一致",
        )
    if (
        attempt_result.get("terminal-authority-sha256")
        != terminal_digest
    ):
        reporter.error(
            "workflow-attempt-result-terminal-authority",
            attempt_result_path,
            "存在completion时attempt result必须绑定当前terminal authority",
        )
    review_issues = (
        []
        if review.get("status") == "passed"
        else review.get("findings", [])
    )
    if attempt_result.get("issues") != review_issues:
        reporter.error(
            "workflow-attempt-result-issues",
            attempt_result_path,
            "attempt result issues必须与final integration review findings一致",
        )
    if completion.get("status") != expected_completion_status:
        reporter.error(
            "workflow-completion-status",
            completion_path,
            "completion status必须与final integration review一致",
        )
    if completion.get("issues") != attempt_result.get("issues"):
        reporter.error(
            "workflow-completion-attempt-result",
            completion_path,
            "completion issues必须与attempt result逐项一致",
        )
    if required and completion.get("status") != "integration-passed":
        reporter.error(
            "workflow-complete-required",
            completion_path,
            "--complete要求合法integration-passed completion",
        )


def validate(
    orchestrate_dir: Path,
    repo_root: Path,
    phase: str,
    complete: bool,
    preflight: bool = False,
    pre_handoff: bool = False,
) -> Dict[str, object]:
    reporter = IssueReporter()
    if not orchestrate_dir.exists():
        reporter.error("orchestrate-dir", orchestrate_dir, "orchestrate 目录不存在")
        return reporter.result()

    if preflight and (
        complete
        or pre_handoff
        or phase not in {"phase-2", "phase-3", "phase-5"}
    ):
        reporter.error(
            "preflight-usage",
            orchestrate_dir,
            "--preflight只允许单独配合--phase phase-2|phase-3|phase-5，且与终态模式互斥",
        )
        return reporter.result()
    if pre_handoff and (complete or phase != "all"):
        reporter.error(
            "pre-handoff-usage",
            orchestrate_dir,
            "--pre-handoff只允许配合--phase all，且与--complete互斥",
        )
        return reporter.result()

    for legacy in (
        orchestrate_dir / "phase-works/phase-5/evidence-patch-request.json",
        orchestrate_dir / "phase-works/phase-5/phase-5-checkpoint.json",
    ):
        if legacy.exists():
            reporter.error("legacy-patch-artifact", legacy, "trace-v7 contract显式拒绝patch request/checkpoint artifact")

    if not preflight:
        validate_manifest(orchestrate_dir, repo_root, reporter, complete=complete)
    phases = ["phase-1", "phase-2", "phase-3", "phase-4", "phase-5"] if phase == "all" else [phase]
    if "phase-1" in phases:
        validate_phase_1(orchestrate_dir, repo_root, reporter)
    if "phase-2" in phases:
        validate_phase_2(orchestrate_dir, repo_root, reporter, preflight=preflight)
    if "phase-3" in phases:
        if preflight:
            validate_phase_2(orchestrate_dir, repo_root, reporter, preflight=True)
        validate_phase_3(orchestrate_dir, repo_root, reporter, preflight=preflight)
    if "phase-4" in phases:
        validate_phase_4(orchestrate_dir, repo_root, reporter)
    if "phase-5" in phases:
        validate_phase_5(
            orchestrate_dir,
            repo_root,
            reporter,
            complete=complete or pre_handoff,
            preflight=preflight,
        )

    if pre_handoff:
        manifest_path = orchestrate_dir / "trace/manifest.json"
        if manifest_path.exists():
            manifest = read_json(manifest_path)
            if manifest.get("workflow-status") != "pending":
                reporter.error(
                    "pre-handoff-workflow-status",
                    manifest_path,
                    "--pre-handoff要求manifest workflow-status=pending",
                )
        for workflow_path in (
            orchestrate_dir / "final-integration-review.json",
            orchestrate_dir
            / FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH,
            orchestrate_dir
            / FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH,
            orchestrate_dir / "trace/workflow-completion.trace.json",
        ):
            if workflow_path.exists():
                reporter.error(
                    "pre-handoff-stale-workflow-artifact",
                    workflow_path,
                    "--pre-handoff前不得保留旧final review、attempt/result或completion",
                )
        try:
            terminal_authority_sha256(orchestrate_dir, repo_root)
        except (OSError, ValueError) as exc:
            reporter.error(
                "pre-handoff-terminal-authority",
                orchestrate_dir,
                str(exc),
            )
    elif not preflight and phase == "all":
        validate_workflow_terminal(
            orchestrate_dir,
            repo_root,
            reporter,
            required=complete,
        )

    return reporter.result()


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 source-aligned orchestrate trace sidecar。")
    parser.add_argument("--orchestrate-dir", default="openspec/orchestrate", type=Path, help="orchestrate 目录路径")
    parser.add_argument("--workspace-root", default=".", type=Path, help="工作区根目录路径")
    parser.add_argument("--phase", choices=["phase-1", "phase-2", "phase-3", "phase-4", "phase-5", "all"], default="all", help="要校验的 Phase")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--complete", action="store_true", help="启用完整终态校验")
    mode.add_argument("--pre-handoff", action="store_true", help="校验Phase 1–5 terminal authority并计算handoff前状态，不要求workflow completion")
    mode.add_argument("--preflight", action="store_true", help="校验Phase 2/3/5 provisional authority，不要求terminal commit marker")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    parser.add_argument("--strict-warnings", action="store_true", help="将 warning 视为失败")
    args = parser.parse_args()
    if args.preflight and args.phase not in {"phase-2", "phase-3", "phase-5"}:
        parser.error("--preflight只允许配合--phase phase-2、phase-3或phase-5")
    if args.pre_handoff and args.phase != "all":
        parser.error("--pre-handoff只允许配合--phase all")

    result = validate(
        args.orchestrate_dir,
        args.workspace_root,
        args.phase,
        args.complete,
        args.preflight,
        args.pre_handoff,
    )
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
