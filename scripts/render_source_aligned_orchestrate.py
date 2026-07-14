#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 Phase-specific authority 渲染 source-aligned 人工阅读产物。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from source_aligned_trace_lib import (
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_BASELINE_SCHEMA,
    EVIDENCE_COLLECTION_INDEX_SCHEMA,
    FRAMEWORK_REFIT_TRACE_SCHEMA,
    GLOBAL_ATOM_INDEX_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
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


RENDER_CONTRACT_VERSION = "source-aligned-render-v6"
SUPPORTED_ARTIFACTS = {
    "phase2-source-atoms",
    "phase2-index",
    "phase3-global-index",
    "phase3-coverage-review",
    "phase4-evidence-collections",
    "phase5-atom-plan-mapping",
    "phase5-capability-baseline",
    "phase5-refit-review",
    "all-supported",
}


def squash(value: object) -> str:
    text = "" if value is None else str(value)
    return " ".join(text.replace("\n", " ").split())


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def repo_root_for(orchestrate_dir: Path) -> Path:
    if orchestrate_dir.name == "orchestrate" and orchestrate_dir.parent.name == "openspec":
        return orchestrate_dir.parent.parent
    return Path.cwd()


def md(value: object) -> str:
    text = squash(value)
    return text.replace("|", "\\|") if text else "None"


def code(value: object) -> str:
    text = squash(value)
    escaped = text.replace("|", "\\|")
    return f"`{escaped}`" if text else "`None`"


def list_text(value: object) -> str:
    if value is None or value == "":
        return "None"
    if isinstance(value, list):
        if not value:
            return "None"
        return "; ".join(md(item) for item in value)
    if isinstance(value, dict):
        return md(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return md(value)


def code_list(value: object) -> str:
    if isinstance(value, list):
        items = [squash(item) for item in value if squash(item)]
        escaped_items = [item.replace("|", "\\|") for item in items]
        return ", ".join(f"`{item}`" for item in escaped_items) if escaped_items else "`None`"
    return code(value)


def stable_code_list(value: object) -> str:
    """以确定性顺序渲染 identifier 数组，并移除重复项。"""
    if isinstance(value, list):
        items = sorted({squash(item) for item in value if squash(item)})
        escaped_items = [item.replace("|", "\\|") for item in items]
        return ", ".join(f"`{item}`" for item in escaped_items) if escaped_items else "`None`"
    return code(value)


def capability_target(value: object) -> str:
    """在面向 reviewer 的 mirror 中显式标注仅属于 Change 的 capability target。"""
    target = squash(value)
    if not target or target.lower() == "none":
        return code("None/change-only")
    return code(target)


def lines_from(row: Dict[str, object]) -> str:
    ranges = row.get("line-ranges")
    if isinstance(ranges, list):
        valid = [
            {"start": item.get("start"), "end": item.get("end")}
            for item in ranges
            if isinstance(item, dict) and isinstance(item.get("start"), int) and isinstance(item.get("end"), int)
        ]
        if valid:
            return line_ranges_label(valid)
    return "None"


def range_label(value: object) -> str:
    """渲染单个 canonical ``{start, end}`` range。"""
    if not isinstance(value, dict):
        return "None"
    start = value.get("start")
    end = value.get("end")
    if not isinstance(start, int) or not isinstance(end, int):
        return "None"
    return line_ranges_label([{"start": start, "end": end}])


def render_table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        output.append("| " + " | ".join(str(cell) if str(cell) else "None" for cell in row) + " |")
    return "\n".join(output) + "\n"


def trace_appendix(trace_path: Path, trace_schema: str, repo_root: Path) -> str:
    digest = sha256_file(trace_path) if trace_path.exists() else ""
    return (
        "\n## Trace Appendix\n\n"
        f"Trace file: `{rel(trace_path, repo_root)}`\n"
        f"Trace schema: `{trace_schema}`\n"
        f"Trace digest: `{digest}`\n"
        f"Render contract: `{RENDER_CONTRACT_VERSION}`\n"
    )


def read_json(path: Path) -> Dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} 必须包含 JSON object")
    return data


def require_trace_contract(data: Dict[str, object], path: Path, trace_schema: str) -> None:
    actual_schema = squash(data.get("trace-schema"))
    if actual_schema != trace_schema:
        raise ValueError(f"{path} 的 trace-schema 必须为 {trace_schema}，实际为 {actual_schema or 'missing'}")
    actual_contract = squash(data.get("trace-contract-version"))
    if actual_contract != TRACE_CONTRACT_VERSION:
        raise ValueError(
            f"{path} 的 trace-contract-version 必须为 {TRACE_CONTRACT_VERSION}，"
            f"实际为 {actual_contract or 'missing'}"
        )


def source_line_count(repo_root: Path, source_document: str) -> str:
    path = repo_root / source_document
    if not path.exists():
        return "None"
    return str(len(path.read_text(encoding="utf-8").splitlines()))


def manifest_source_role(orchestrate_dir: Path, source_document: str) -> str:
    manifest = orchestrate_dir / "phase-works/phase-1/source-doc-manifest.md"
    if not manifest.exists():
        return ""
    lines = manifest.read_text(encoding="utf-8").splitlines()
    for raw in lines:
        if source_document not in raw or not raw.strip().startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in raw.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] == source_document:
            return cells[2]
    return ""


def render_phase2_source_atoms(orchestrate_dir: Path, json_path: Path) -> str:
    repo_root = repo_root_for(orchestrate_dir)
    data = read_json(json_path)
    require_trace_contract(data, json_path, SOURCE_ATOMS_SCHEMA)
    source_document = squash(data.get("source-document"))
    source_role = squash(data.get("source-role")) or manifest_source_role(orchestrate_dir, source_document) or "None"
    lines: List[str] = [
        f"# Phase 2 Source Obligation Atoms：{Path(source_document).with_suffix('').as_posix().replace('/', '--')}",
        "",
        "## 来源元数据",
        "",
        f"- 来源路径：{code(source_document)}",
        f"- 来源角色：{md(source_role)}",
        f"- 读取状态：{code(data.get('read-status'))}",
        f"- 行数：{code(source_line_count(repo_root, source_document))}",
        f"- 来源 SHA-256：{code(data.get('source-sha256'))}",
        f"- Canonical owner：{code(data.get('canonical-owner'))}",
        "",
        "## Phase 1 已考虑的候选 Change/Capability",
        "",
    ]
    considered = data.get("phase-1-candidate-changes-capabilities-considered")
    if isinstance(considered, list) and considered:
        for item in considered:
            if isinstance(item, dict):
                change = code(item.get("change"))
                caps = code_list(item.get("capabilities"))
                note = md(item.get("note"))
                lines.append(f"- {change}：Capability {caps}。{note}")
            else:
                lines.append(f"- {md(item)}")
    elif considered:
        lines.append(md(considered))
    else:
        lines.append("- `None`")
    lines.extend(["", "## obligation atom 候选台账", ""])
    lines.append(
        render_table(
            [
                "Source Atom ID",
                "Lines",
                "Atom Type",
                "Source Fact",
                "Normativity",
                "Candidate Status",
                "Candidate Artifact Projection",
                "Candidate Owner Change",
                "Candidate Target Capability",
                "Rationale",
            ],
            (
                [
                    code(row.get("source-atom-id")),
                    lines_from(row),
                    code(row.get("atom-type")),
                    md(row.get("source-fact")),
                    code(row.get("normativity")),
                    code(row.get("candidate-status")),
                    code(row.get("candidate-artifact-projection")),
                    code(row.get("candidate-owner-change")),
                    capability_target(row.get("candidate-target-capability")),
                    md(row.get("rationale")),
                ]
                for row in data.get("source-atoms", [])
                if isinstance(row, dict)
            ),
        ).rstrip()
    )
    lines.extend(["", "## 阻塞项", ""])
    blockers = data.get("blockers")
    if isinstance(blockers, list) and blockers:
        lines.extend(f"- {md(item)}" for item in blockers)
    elif blockers:
        lines.append(md(blockers))
    else:
        lines.append("- `None`")
    lines.extend(["", "## 语言自检", "", md(data.get("language-self-check") or "该 Markdown mirror 由 canonical JSON sidecar 机械渲染。")])
    return "\n".join(lines).rstrip() + "\n" + trace_appendix(json_path, SOURCE_ATOMS_SCHEMA, repo_root)


def _count_summary(values: Iterable[object]) -> str:
    counts: Dict[str, int] = {}
    for value in values:
        key = normalize_code(value) or "none"
        counts[key] = counts.get(key, 0) + 1
    return "; ".join(f"{key}={counts[key]}" for key in sorted(counts)) or "none"


def _phase2_batch_by_source(orchestrate_dir: Path) -> Dict[str, str]:
    queue = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms/work-queue.md"
    result: Dict[str, str] = {}
    for row in table_rows(queue, ["Batch", "Source Documents", "Canonical Owner"]):
        batch = normalize_code(cell(row, "Batch"))
        raw_sources = cell(row, "Source Documents").replace("<br/>", "<br>")
        for source in raw_sources.split("<br>"):
            source_id = normalize_code(source)
            if source_id:
                result[source_id] = batch
    return result


def render_phase2_index(orchestrate_dir: Path) -> str:
    """从 Phase 2 canonical JSON 与调度 metadata 机械生成聚合索引。"""
    repo_root = repo_root_for(orchestrate_dir)
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    trace_path = orchestrate_dir / "trace/phase-2.trace.json"
    trace = read_json(trace_path)
    require_trace_contract(trace, trace_path, PHASE_TRACE_SCHEMAS["phase-2"])
    batches = _phase2_batch_by_source(orchestrate_dir)
    rows: List[List[object]] = []
    for json_path in sorted(atom_root.glob("*.atoms.json")):
        data = read_json(json_path)
        require_trace_contract(data, json_path, SOURCE_ATOMS_SCHEMA)
        atoms = [row for row in data.get("source-atoms", []) if isinstance(row, dict)]
        mapped_changes = sorted({
            normalize_code(row.get("candidate-owner-change"))
            for row in atoms
            if normalize_code(row.get("candidate-owner-change")) not in {"", "none", "unassigned", "contextual"}
        })
        mapped_capabilities = sorted({
            normalize_code(row.get("candidate-target-capability"))
            for row in atoms
            if normalize_code(row.get("candidate-target-capability")) not in {"", "none", "unresolved"}
        })
        unassigned = sorted(
            normalize_code(row.get("source-atom-id"))
            for row in atoms
            if normalize_code(row.get("candidate-status")) == "unassigned"
        )
        blockers = data.get("blockers") if isinstance(data.get("blockers"), list) else []
        source_document = normalize_code(data.get("source-document"))
        rows.append([
            code(source_document),
            code(batches.get(source_document, "none")),
            code(data.get("canonical-owner")),
            code(rel(json_path.with_suffix(".md"), repo_root)),
            code(data.get("read-status")),
            code(len(atoms)),
            md(_count_summary(row.get("candidate-status") for row in atoms)),
            md(_count_summary(row.get("candidate-artifact-projection") for row in atoms)),
            code_list(mapped_changes),
            code_list(mapped_capabilities),
            code_list(unassigned),
            md("；".join(str(item) for item in blockers) if blockers else "无"),
        ])
    body = [
        "# Phase 2 Source Obligation Atom Index",
        "",
        f"- Phase status：{code(trace.get('status'))}",
        f"- Phase trace：{code(rel(trace_path, repo_root))}",
        f"- Phase trace digest：{code(sha256_file(trace_path))}",
        f"- Render contract：{code(RENDER_CONTRACT_VERSION)}",
        "",
        render_table(
            [
                "Source Document", "Work Queue Batch", "Canonical Owner", "Source Atom File",
                "Read Status", "Atom Candidates", "Candidate Status Summary", "Projection Summary",
                "Mapped Changes", "Mapped Capabilities", "Unassigned Atoms", "Blockers",
            ],
            rows,
        ).rstrip(),
        "",
        "> 本索引由 Phase 2 canonical atom JSON 机械生成，不是独立语义权威。",
    ]
    return "\n".join(body).rstrip() + "\n"


def render_global_index(orchestrate_dir: Path, json_path: Path) -> str:
    repo_root = repo_root_for(orchestrate_dir)
    data = read_json(json_path)
    require_trace_contract(data, json_path, GLOBAL_ATOM_INDEX_SCHEMA)
    body = [
        "# obligation atom 索引",
        "",
        render_table(
            ["Global Atom ID", "Evidence Reference"],
            (
                [
                    code(row.get("global-atom-id")),
                    code(json.dumps(row.get("evidence-ref"), ensure_ascii=False, sort_keys=True)),
                ]
                for row in data.get("global-atoms", [])
                if isinstance(row, dict)
            ),
        ).rstrip(),
    ]
    return "\n".join(body).rstrip() + "\n" + trace_appendix(json_path, GLOBAL_ATOM_INDEX_SCHEMA, repo_root)


def render_coverage_review(orchestrate_dir: Path, json_path: Path) -> str:
    repo_root = repo_root_for(orchestrate_dir)
    data = read_json(json_path)
    require_trace_contract(data, json_path, PHASE3_COVERAGE_REVIEW_SCHEMA)
    body = ["# Phase 3 覆盖审计", "", f"Decision: `{squash(data.get('decision'))}`", "", "## 文档覆盖", ""]
    body.append(
        render_table(
            ["Source Document", "Line Count", "Source SHA256", "Phase 2 Artifact", "Phase 2 SHA256", "Covered Ranges", "Candidate Uncovered Ranges"],
            (
                [
                    code(row.get("source-document")),
                    code(row.get("line-count")),
                    code(row.get("source-sha256")),
                    code(row.get("phase-2-atom-path")),
                    code(row.get("phase-2-atom-sha256")),
                    md("; ".join(range_label(item) for item in row.get("covered-ranges", []) if isinstance(item, dict))),
                    md("; ".join(range_label(item) for item in row.get("candidate-uncovered-ranges", []) if isinstance(item, dict))),
                ]
                for row in data.get("documents", [])
                if isinstance(row, dict)
            ),
        ).rstrip()
    )
    body.extend(["", "## 遗漏补提取", ""])
    body.append(
        render_table(
            ["Gap Atom ID", "Source Document", "Lines", "Source Fact", "Atom Type", "Normativity", "Review Judgment"],
            (
                [
                    code(row.get("gap-atom-id")),
                    code(row.get("source-document")),
                    lines_from(row),
                    md(row.get("source-fact")),
                    code(row.get("atom-type")),
                    code(row.get("normativity")),
                    md(row.get("review-judgment")),
                ]
                for row in data.get("gap-atoms", [])
                if isinstance(row, dict)
            ),
        ).rstrip()
    )
    body.extend(["", "## 未覆盖范围处置", ""])
    body.append(
        render_table(
            ["Disposition ID", "Source Document", "Lines", "Classification", "Linked Gap Atom IDs", "Reason"],
            (
                [
                    code(row.get("disposition-id")),
                    code(row.get("source-document")),
                    lines_from(row),
                    code(row.get("classification")),
                    code_list(row.get("linked-gap-atom-ids")),
                    md(row.get("reason")),
                ]
                for row in data.get("remainder-dispositions", [])
                if isinstance(row, dict)
            ),
        ).rstrip()
    )
    body.extend(["", "## 重新提取来源", ""])
    body.append(
        render_table(
            ["Source Document", "Source Atom IDs", "Lines", "Reason"],
            (
                [
                    code(row.get("source-document")),
                    code_list(row.get("source-atom-ids")),
                    md("; ".join(range_label(item) for item in row.get("line-ranges", []) if isinstance(item, dict))),
                    md(row.get("reason")),
                ]
                for row in data.get("recheck-sources", [])
                if isinstance(row, dict)
            ),
        ).rstrip()
    )
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    body.extend(["", "## 统计摘要", ""])
    body.append(
        render_table(
            ["Metric", "Value"],
            ([code(key), code(value)] for key, value in sorted(summary.items())),
        ).rstrip()
    )
    body.extend(["", "## 语言自检", "", md(data.get("language-self-check"))])
    return "\n".join(body).rstrip() + "\n" + trace_appendix(json_path, PHASE3_COVERAGE_REVIEW_SCHEMA, repo_root)


def render_atom_plan_mapping(orchestrate_dir: Path, json_path: Path) -> str:
    repo_root = repo_root_for(orchestrate_dir)
    data = read_json(json_path)
    require_trace_contract(data, json_path, ATOM_PLAN_MAPPING_SCHEMA)
    body = [
        "# atom plan 映射",
        "",
        render_table(
            [
                "Global Atom ID",
                "Evidence Reference",
                "Final Owner Change",
                "Final Relation",
                "Final Artifact Projection",
                "Final Capability Impact",
                "Final Target Capability",
                "Related Capabilities",
                "Reason",
            ],
            (
                [
                    code(row.get("global-atom-id")),
                    code(json.dumps(row.get("evidence-ref"), ensure_ascii=False, sort_keys=True)),
                    code(row.get("final-owner-change")),
                    code(row.get("final-relation")),
                    code(row.get("final-artifact-projection")),
                    code(row.get("final-capability-impact")),
                    capability_target(row.get("final-target-capability")),
                    stable_code_list(row.get("related-capabilities")),
                    md(row.get("reason")),
                ]
                for row in data.get("rows", [])
                if isinstance(row, dict)
            ),
        ).rstrip(),
    ]
    return "\n".join(body).rstrip() + "\n" + trace_appendix(json_path, ATOM_PLAN_MAPPING_SCHEMA, repo_root)


def _gate_results_text(value: object) -> str:
    if not isinstance(value, list):
        return "None"
    parts: List[str] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        gate = normalize_code(row.get("gate"))
        result = normalize_code(row.get("result"))
        note = squash(row.get("note"))
        parts.append(f"{gate}={result}" + (f"（{note}）" if note else ""))
    return "；".join(parts) or "None"


def render_framework_refit_review(orchestrate_dir: Path, json_path: Path) -> str:
    """从 framework refit trace 渲染 Phase 5 人工复审文档。"""
    repo_root = repo_root_for(orchestrate_dir)
    data = read_json(json_path)
    require_trace_contract(data, json_path, FRAMEWORK_REFIT_TRACE_SCHEMA)
    capability_rows = (
        [
            code(row.get("input-capability")),
            code(row.get("evidence-collection-path")),
            code(row.get("decision")),
            code_list(row.get("final-capabilities")),
            md(_gate_results_text(row.get("gate-results"))),
            md(row.get("reason")),
        ]
        for row in data.get("capability-reviews", [])
        if isinstance(row, dict)
    )
    change_rows = (
        [
            code(row.get("input-change")),
            code(row.get("evidence-collection-path")),
            code(row.get("decision")),
            code_list(row.get("final-changes")),
            md(_gate_results_text(row.get("gate-results"))),
            md(row.get("reason")),
        ]
        for row in data.get("change-reviews", [])
        if isinstance(row, dict)
    )
    gap_rows = (
        [
            code(row.get("global-atom-id")),
            code(json.dumps(row.get("evidence-ref"), ensure_ascii=False, sort_keys=True)),
            code(row.get("disposition")),
            code(row.get("final-change")),
            capability_target(row.get("final-capability")),
            md(row.get("reason")),
        ]
        for row in data.get("unassigned-and-gap-reviews", [])
        if isinstance(row, dict)
    )
    final_framework = data.get("final-framework") if isinstance(data.get("final-framework"), dict) else None
    summary = "无（非终态）"
    if final_framework is not None:
        summary = (
            f"Change顺序={', '.join(str(item) for item in final_framework.get('change-order', [])) or '无'}；"
            f"Capability={', '.join(str(item) for item in final_framework.get('capabilities', [])) or '无'}；"
            f"Overlay={len(final_framework.get('overlay', [])) if isinstance(final_framework.get('overlay'), list) else 0}"
        )
    issues = data.get("issues") if isinstance(data.get("issues"), list) else []
    body = [
        "# Plan Refit Review",
        "",
        "## Capability Review",
        "",
        render_table(
            ["Input Capability", "Evidence Collection", "Decision", "Final Capability(s)", "Failed or Passed Gates", "Reason"],
            capability_rows,
        ).rstrip(),
        "",
        "## Change Review",
        "",
        render_table(
            ["Input Change", "Evidence Collection", "Decision", "Final Change(s)", "Failed or Passed Gates", "Reason"],
            change_rows,
        ).rstrip(),
        "",
        "## Unassigned and Gap Review",
        "",
        render_table(
            ["GA", "Evidence Reference", "Disposition", "Final Change", "Final Capability", "Reason"],
            gap_rows,
        ).rstrip(),
        "",
        "## Final Decision",
        "",
        f"- Status: `{normalize_code(data.get('status'))}`",
        f"- Final framework：{summary}",
        f"- Issues：{'；'.join(str(item) for item in issues) if issues else '无'}",
        "",
        "## 语言自检",
        "",
        md(data.get("language-self-check")),
    ]
    return "\n".join(body).rstrip() + "\n" + trace_appendix(json_path, FRAMEWORK_REFIT_TRACE_SCHEMA, repo_root)


def _resolved_global_evidence(orchestrate_dir: Path) -> Dict[str, Dict[str, object]]:
    global_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    global_data = read_json(global_path)
    require_trace_contract(global_data, global_path, GLOBAL_ATOM_INDEX_SCHEMA)
    coverage_path = orchestrate_dir / "phase-works/phase-3/coverage-review.json"
    coverage = read_json(coverage_path)
    require_trace_contract(coverage, coverage_path, PHASE3_COVERAGE_REVIEW_SCHEMA)
    gaps = {
        normalize_code(row.get("gap-atom-id")): row
        for row in coverage.get("gap-atoms", [])
        if isinstance(row, dict)
    }
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    source_cache: Dict[str, Dict[str, Dict[str, object]]] = {}
    resolved: Dict[str, Dict[str, object]] = {}
    for global_row in global_data.get("global-atoms", []):
        if not isinstance(global_row, dict):
            continue
        ga = normalize_code(global_row.get("global-atom-id"))
        ref = global_row.get("evidence-ref")
        if not ga or not isinstance(ref, dict):
            continue
        kind = normalize_code(ref.get("kind"))
        evidence: Optional[Dict[str, object]] = None
        if kind == "phase-2-source-atom":
            source = normalize_code(ref.get("source-document"))
            if source not in source_cache:
                atom_path = atom_root / source_atom_file_name(source).replace(".md", ".json")
                atom_data = read_json(atom_path)
                require_trace_contract(atom_data, atom_path, SOURCE_ATOMS_SCHEMA)
                source_cache[source] = {
                    normalize_code(row.get("source-atom-id")): {**row, "source-document": source}
                    for row in atom_data.get("source-atoms", [])
                    if isinstance(row, dict)
                }
            evidence = source_cache[source].get(normalize_code(ref.get("source-atom-id")))
        elif kind == "phase-3-gap-atom":
            evidence = gaps.get(normalize_code(ref.get("gap-atom-id")))
        if not isinstance(evidence, dict):
            raise ValueError(f"{ga} 无法解析 evidence-ref: {ref}")
        resolved[ga] = {**evidence, "evidence-ref": dict(ref), "evidence-kind": kind}
    return resolved


def _initial_framework(plan_path: Path) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    capabilities: List[Dict[str, str]] = []
    for row in table_rows(plan_path, ["Candidate Capability", "Purpose", "Owns", "Excludes"]):
        slug = normalize_code(cell(row, "Candidate Capability"))
        if slug:
            capabilities.append({
                "slug": slug,
                "purpose": squash(cell(row, "Purpose")),
                "owns": squash(cell(row, "Owns")),
                "excludes": squash(cell(row, "Excludes")),
            })
    changes: List[Dict[str, str]] = []
    current: Optional[Dict[str, str]] = None
    for raw in plan_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^- Change 名称[：:]\s*(.+?)\s*$", raw)
        if match:
            if current:
                changes.append(current)
            current = {"slug": normalize_code(match.group(1)), "intent": "", "outcome": ""}
            continue
        if not current:
            continue
        intent = re.match(r"^- 单一 intent[：:]\s*(.*)$", raw)
        outcome = re.match(r"^- source-backed outcome[：:]\s*(.*)$", raw)
        if intent:
            current["intent"] = intent.group(1).strip()
        elif outcome:
            current["outcome"] = outcome.group(1).strip()
    if current:
        changes.append(current)
    return changes, capabilities


def _evidence_sort_key(item: Dict[str, object]) -> tuple[str, int, str]:
    ranges = item.get("line-ranges")
    start = 0
    if isinstance(ranges, list) and ranges and isinstance(ranges[0], dict):
        value = ranges[0].get("start")
        start = value if isinstance(value, int) else 0
    return normalize_code(item.get("source-document")), start, normalize_code(item.get("global-atom-id"))


def _source_fact_fence(source_fact: object) -> str:
    text = "" if source_fact is None else str(source_fact)
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}text\n{text}\n{fence}"


def _render_evidence_item(item: Dict[str, object]) -> str:
    ref = item.get("evidence-ref")
    metadata = [
        f"### {code(item.get('global-atom-id'))}",
        "",
        f"- Evidence reference：{code(json.dumps(ref, ensure_ascii=False, sort_keys=True))}",
        f"- Source：{code(item.get('source-document'))}",
        f"- Lines：{code(lines_from(item))}",
        f"- Atom type：{code(item.get('atom-type'))}",
        f"- Normativity：{code(item.get('normativity'))}",
    ]
    if item.get("evidence-kind") == "phase-2-source-atom":
        metadata.extend([
            f"- Candidate status：{code(item.get('candidate-status'))}",
            f"- Candidate projection：{code(item.get('candidate-artifact-projection'))}",
            f"- Candidate owner Change：{code(item.get('candidate-owner-change'))}",
            f"- Candidate target Capability：{code(item.get('candidate-target-capability'))}",
        ])
    else:
        metadata.append(f"- Provenance：`phase-3-gap-atom`；{md(item.get('review-judgment'))}")
    metadata.extend(["", _source_fact_fence(item.get("source-fact")), ""])
    return "\n".join(metadata)


def _phase4_index_path(orchestrate_dir: Path) -> Path:
    return orchestrate_dir / "phase-works/phase-4/source-evidence-collections/evidence-collection-index.json"


def _phase4_appendix(orchestrate_dir: Path) -> str:
    repo_root = repo_root_for(orchestrate_dir)
    index_path = _phase4_index_path(orchestrate_dir)
    return (
        "\n## Assembly Appendix\n\n"
        f"Derived machine index: `{rel(index_path, repo_root)}`\n"
        f"Index schema: `{EVIDENCE_COLLECTION_INDEX_SCHEMA}`\n"
        f"Render contract: `{RENDER_CONTRACT_VERSION}`\n"
    )


def _phase4_rows(
    orchestrate_dir: Path,
    changes: Sequence[Dict[str, str]],
    capabilities: Sequence[Dict[str, str]],
) -> tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    resolved = _resolved_global_evidence(orchestrate_dir)
    change_ids = {row["slug"] for row in changes}
    capability_ids = {row["slug"] for row in capabilities}
    root = _phase4_index_path(orchestrate_dir).parent
    rows: List[Dict[str, object]] = []
    enriched: List[Dict[str, object]] = []
    for ga, evidence in resolved.items():
        kind = normalize_code(evidence.get("evidence-kind"))
        owner_hint = normalize_code(evidence.get("candidate-owner-change"))
        target_hint = normalize_code(evidence.get("candidate-target-capability"))
        change_bucket = owner_hint if kind == "phase-2-source-atom" and owner_hint in change_ids else "unassigned-and-gap"
        capability_bucket = target_hint if kind == "phase-2-source-atom" and target_hint in capability_ids else "none"
        collection_paths = [
            (root / "by-input-change" / f"{change_bucket}.md")
            if change_bucket != "unassigned-and-gap"
            else (root / "unassigned-and-gap.md")
        ]
        if capability_bucket != "none":
            collection_paths.append(root / "by-input-capability" / f"{capability_bucket}.md")
        row = {
            "global-atom-id": ga,
            "evidence-ref": evidence.get("evidence-ref"),
            "change-bucket": change_bucket,
            "capability-bucket": capability_bucket,
            "rendered-collection-paths": [rel(path, repo_root_for(orchestrate_dir)) for path in collection_paths],
        }
        rows.append(row)
        enriched.append({**evidence, **row})
    enriched.sort(key=_evidence_sort_key)
    return rows, enriched


def render_evidence_collections(orchestrate_dir: Path, json_path: Optional[Path] = None) -> Dict[Path, str]:
    """直接从 Phase 1–3 authority 机械组装 Phase 4 Markdown。"""
    del json_path  # v2 index 是输出，不再是 renderer 输入。
    plan_path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    changes, capabilities = _initial_framework(plan_path)
    _, enriched = _phase4_rows(orchestrate_dir, changes, capabilities)
    root = _phase4_index_path(orchestrate_dir).parent
    outputs: Dict[Path, str] = {}
    appendix = _phase4_appendix(orchestrate_dir)

    index_lines = ["# Phase 4 冻结原文集合索引", ""]
    index_lines.append(render_table(
        ["Global Atom ID", "Evidence Reference", "Change Bucket", "Capability Bucket"],
        (
            [
                code(row.get("global-atom-id")),
                code(json.dumps(row.get("evidence-ref"), ensure_ascii=False, sort_keys=True)),
                code(row.get("change-bucket")),
                code(row.get("capability-bucket")),
            ]
            for row in enriched
        ),
    ).rstrip())
    outputs[root / "index.md"] = "\n".join(index_lines).rstrip() + "\n" + appendix

    for change in changes:
        items = [item for item in enriched if item.get("change-bucket") == change["slug"]]
        lines = [
            f"# Initial Change 原文集合：{change['slug']}", "",
            f"- Initial intent：{md(change['intent'])}",
            f"- Initial outcome：{md(change['outcome'])}", "",
        ]
        if items:
            lines.extend(_render_evidence_item(item) for item in items)
        else:
            lines.append("无关联 evidence occurrence。")
        outputs[root / "by-input-change" / f"{change['slug']}.md"] = "\n".join(lines).rstrip() + "\n" + appendix

    for capability in capabilities:
        items = [item for item in enriched if item.get("capability-bucket") == capability["slug"]]
        lines = [
            f"# Initial Capability 原文集合：{capability['slug']}", "",
            f"- Purpose：{md(capability['purpose'])}",
            f"- Owns：{md(capability['owns'])}",
            f"- Excludes：{md(capability['excludes'])}", "",
        ]
        if items:
            lines.extend(_render_evidence_item(item) for item in items)
        else:
            lines.append("无关联 evidence occurrence。")
        outputs[root / "by-input-capability" / f"{capability['slug']}.md"] = "\n".join(lines).rstrip() + "\n" + appendix

    unassigned = [item for item in enriched if item.get("change-bucket") == "unassigned-and-gap"]
    lines = ["# Unassigned 与 Gap 原文集合", ""]
    groups = [
        ("Phase 2 Unassigned", lambda item: item.get("evidence-kind") == "phase-2-source-atom" and item.get("candidate-status") == "unassigned"),
        ("Phase 2 Unresolved / Contextual", lambda item: item.get("evidence-kind") == "phase-2-source-atom" and item.get("candidate-status") != "unassigned"),
        ("Phase 3 Gap Atoms", lambda item: item.get("evidence-kind") == "phase-3-gap-atom"),
    ]
    for heading, predicate in groups:
        lines.extend([f"## {heading}", ""])
        group_items = [item for item in unassigned if predicate(item)]
        if group_items:
            lines.extend(_render_evidence_item(item) for item in group_items)
        else:
            lines.append("无关联 evidence occurrence。")
    outputs[root / "unassigned-and-gap.md"] = "\n".join(lines).rstrip() + "\n" + appendix
    return outputs


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_evidence_collection_index(
    orchestrate_dir: Path,
    outputs: Optional[Dict[Path, str]] = None,
) -> Dict[str, object]:
    """生成不承载新语义的 Phase 4 v2 派生机器索引。"""
    repo_root = repo_root_for(orchestrate_dir)
    plan_path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
    changes, capabilities = _initial_framework(plan_path)
    rows, _ = _phase4_rows(orchestrate_dir, changes, capabilities)
    rendered = outputs if outputs is not None else render_evidence_collections(orchestrate_dir)
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    generated_paths = [
        plan_path,
        orchestrate_dir / "change-capability-anchors/obligation-atom-index.json",
        orchestrate_dir / "phase-works/phase-3/coverage-review.json",
        *sorted(atom_root.glob("*.atoms.json")),
    ]
    change_ids = {row["slug"] for row in changes}
    capability_ids = {row["slug"] for row in capabilities}
    rendered_artifacts: List[Dict[str, object]] = []
    for path, text_value in rendered.items():
        if path.name == "index.md":
            kind, owner = "index", "all"
        elif path.name == "unassigned-and-gap.md":
            kind, owner = "unassigned-and-gap", "unassigned-and-gap"
        elif path.parent.name == "by-input-change" and path.stem in change_ids:
            kind, owner = "input-change", path.stem
        elif path.parent.name == "by-input-capability" and path.stem in capability_ids:
            kind, owner = "input-capability", path.stem
        else:
            raise ValueError(f"无法分类 Phase 4 rendered artifact：{path}")
        rendered_artifacts.append({
            "artifact-path": rel(path, repo_root),
            "sha256": _sha256_text(text_value),
            "collection-kind": kind,
            "owner-id": owner,
        })
    return {
        "trace-schema": EVIDENCE_COLLECTION_INDEX_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "generated-from": [
            {"artifact-path": rel(path, repo_root), "sha256": sha256_file(path)}
            for path in generated_paths
        ],
        "rows": rows,
        "rendered-artifacts": rendered_artifacts,
    }


def render_capability_baseline(orchestrate_dir: Path, json_path: Path) -> str:
    data = read_json(json_path)
    repo_root = repo_root_for(orchestrate_dir)
    if data.get("trace-schema") != CAPABILITY_BASELINE_SCHEMA:
        raise ValueError(f"{json_path} trace-schema 必须是 {CAPABILITY_BASELINE_SCHEMA}")
    rows = data.get("capabilities")
    if not isinstance(rows, list):
        raise ValueError(f"{json_path} capabilities 必须是 array")
    body = [
        "# Capability repository baseline reconciliation",
        "",
        "该表只提供 repository spec identity/existence evidence；production obligation authority 仍是用户指定的 source document。",
        "",
        render_table(
            [
                "Capability",
                "Repository Baseline",
                "Spec Path",
                "Spec SHA256",
                "Baseline Evidence",
                "First Planned Advancement",
                "Required First Relation",
                "Later Relation Rule",
            ],
            (
                [
                    code(row.get("capability")),
                    code(row.get("baseline-status")),
                    code(row.get("spec-path")),
                    code(row.get("spec-sha256")),
                    md(row.get("baseline-evidence")),
                    code(row.get("first-planned-advancement")),
                    code(row.get("required-first-relation")),
                    code(row.get("later-relation-rule")),
                ]
                for row in rows
                if isinstance(row, dict)
            ),
        ).rstrip(),
    ]
    return "\n".join(body).rstrip() + "\n" + trace_appendix(json_path, CAPABILITY_BASELINE_SCHEMA, repo_root)


def render_jobs(orchestrate_dir: Path, artifact: str, source_document: str = "") -> List[Dict[str, object]]:
    jobs: List[Dict[str, object]] = []
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    if artifact in {"phase2-source-atoms", "all-supported"}:
        paths = sorted(atom_root.glob("*.atoms.json"))
        if source_document:
            expected = atom_root / source_atom_file_name(source_document).replace(".md", ".json")
            paths = [expected] if expected.exists() else []
        for json_path in paths:
            jobs.append({"json-path": json_path, "md-path": json_path.with_suffix(".md"), "renderer": render_phase2_source_atoms})
    if artifact in {"phase3-global-index", "all-supported"}:
        path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
        if path.exists():
            jobs.append({"json-path": path, "md-path": path.with_suffix(".md"), "renderer": render_global_index})
    if artifact in {"phase3-coverage-review", "all-supported"}:
        path = orchestrate_dir / "phase-works/phase-3/coverage-review.json"
        if path.exists():
            jobs.append({"json-path": path, "md-path": path.with_suffix(".md"), "renderer": render_coverage_review})
    if artifact in {"phase5-atom-plan-mapping", "all-supported"}:
        path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
        if path.exists():
            jobs.append({"json-path": path, "md-path": path.with_suffix(".md"), "renderer": render_atom_plan_mapping})
    if artifact in {"phase5-capability-baseline", "all-supported"}:
        path = orchestrate_dir / "phase-works/phase-5/capability-baseline-reconciliation.json"
        if path.exists():
            jobs.append({"json-path": path, "md-path": path.with_suffix(".md"), "renderer": render_capability_baseline})
    if artifact in {"phase5-refit-review", "all-supported"}:
        path = orchestrate_dir / "phase-works/phase-5/framework-refit-trace.json"
        if path.exists():
            jobs.append({
                "json-path": path,
                "md-path": orchestrate_dir / "phase-works/phase-5/plan-refit-review.md",
                "renderer": render_framework_refit_review,
            })
    return jobs


def clean_phase4_legacy(orchestrate_dir: Path) -> None:
    work = orchestrate_dir / "phase-works/phase-4"
    for name in (
        "input-change-plan.md",
        "source-window-dossiers",
        "source-window-semantic-profile-review.md",
        "source-window-grounding-issues.md",
    ):
        path = work / name
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def render_orchestrate(orchestrate_dir: Path, artifact: str, source_document: str = "", write: bool = False) -> Dict[str, object]:
    if artifact not in SUPPORTED_ARTIFACTS:
        raise ValueError(f"不支持的 artifact：{artifact}")
    if write and artifact in {"phase4-evidence-collections", "all-supported"}:
        clean_phase4_legacy(orchestrate_dir)
    results: List[Dict[str, object]] = []
    derived_json_results: List[Dict[str, object]] = []
    drift_count = 0
    warnings: List[str] = []

    if artifact in {"phase2-index", "all-supported"}:
        atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
        if any(atom_root.glob("*.atoms.json")):
            md_path = atom_root / "index.md"
            rendered = render_phase2_index(orchestrate_dir)
            current = md_path.read_text(encoding="utf-8") if md_path.exists() else None
            drift = current != rendered
            drift_count += int(drift)
            if write and drift:
                md_path.parent.mkdir(parents=True, exist_ok=True)
                md_path.write_text(rendered, encoding="utf-8")
            results.append({
                "source-json": "phase2-atom-json-set",
                "target-markdown": md_path.as_posix(),
                "row-count": len(list(atom_root.glob("*.atoms.json"))),
                "drift": drift if not write else False,
                "written": bool(write and drift),
            })

    if artifact in {"phase4-evidence-collections", "all-supported"}:
        global_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
        coverage_path = orchestrate_dir / "phase-works/phase-3/coverage-review.json"
        plan_path = orchestrate_dir / "phase-works/phase-1/initial-change-plan.md"
        if global_path.exists() and coverage_path.exists() and plan_path.exists():
            rendered_outputs = render_evidence_collections(orchestrate_dir)
            index_path = _phase4_index_path(orchestrate_dir)
            if write:
                expected_paths = {path.resolve() for path in rendered_outputs}
                for directory in (index_path.parent / "by-input-change", index_path.parent / "by-input-capability"):
                    for stale in directory.glob("*.md") if directory.exists() else []:
                        if stale.resolve() not in expected_paths:
                            stale.unlink()
            for md_path, rendered in rendered_outputs.items():
                current = md_path.read_text(encoding="utf-8") if md_path.exists() else None
                drift = current != rendered
                drift_count += int(drift)
                if write and drift:
                    md_path.parent.mkdir(parents=True, exist_ok=True)
                    md_path.write_text(rendered, encoding="utf-8")
                results.append({
                    "source-json": "phase1-3-authority-set",
                    "target-markdown": md_path.as_posix(),
                    "row-count": len(_resolved_global_evidence(orchestrate_dir)),
                    "drift": drift if not write else False,
                    "written": bool(write and drift),
                })
            expected_index = build_evidence_collection_index(orchestrate_dir, rendered_outputs)
            try:
                current_index = read_json(index_path) if index_path.exists() else None
            except (OSError, ValueError, json.JSONDecodeError):
                current_index = None
            index_drift = current_index != expected_index
            drift_count += int(index_drift)
            if write and index_drift:
                write_json(index_path, expected_index)
            derived_json_results.append({
                "target-json": index_path.as_posix(),
                "drift": index_drift if not write else False,
                "written": bool(write and index_drift),
            })

    for job in render_jobs(orchestrate_dir, artifact, source_document):
        json_path = job["json-path"]
        md_path = job["md-path"]
        renderer = job["renderer"]
        rendered = renderer(orchestrate_dir, json_path)
        current = md_path.read_text(encoding="utf-8") if md_path.exists() else None
        drift = current != rendered
        if drift:
            drift_count += 1
        if write and drift:
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(rendered, encoding="utf-8")
            drift = False
        row_count = 0
        data = read_json(json_path)
        for key in ("source-atoms", "global-atoms", "rows", "capabilities"):
            if isinstance(data.get(key), list):
                row_count = len(data[key])
                break
        results.append(
            {
                "source-json": json_path.as_posix(),
                "target-markdown": md_path.as_posix(),
                "row-count": row_count,
                "drift": drift if not write else False,
                "written": bool(write and current != rendered),
            }
        )
    if artifact != "all-supported" and not results:
        warnings.append(f"未找到可渲染 artifact: {artifact}")
    return {
        "ok": drift_count == 0 or write,
        "render-contract-version": RENDER_CONTRACT_VERSION,
        "artifact": artifact,
        "rendered-files": len(results),
        "drift-count": 0 if write else drift_count,
        "results": results,
        "derived-json-results": derived_json_results,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="按 Phase-specific authority 渲染 source-aligned 人工阅读产物。")
    parser.add_argument("--orchestrate-dir", default="openspec/orchestrate", help="orchestrate 目录路径")
    parser.add_argument("--artifact", choices=sorted(SUPPORTED_ARTIFACTS), default="all-supported", help="要渲染的 artifact")
    parser.add_argument("--source-document", default="", help="可选的来源文档路径筛选条件")
    parser.add_argument("--write", action="store_true", help="将渲染结果写入 Markdown 文件")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args()

    result = render_orchestrate(Path(args.orchestrate_dir), args.artifact, args.source_document, args.write)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        action = "已写入" if args.write else "已检查"
        print(f"{action} {result['rendered-files']} 个文件；drift-count={result['drift-count']}")
        for warning in result["warnings"]:
            print(f"warning: {warning}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
