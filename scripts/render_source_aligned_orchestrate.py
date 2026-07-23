#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 Phase-specific authority 渲染 source-aligned 人工阅读产物。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from source_aligned_trace_lib import (
    ATOM_PLAN_MAPPING_SCHEMA,
    CAPABILITY_BASELINE_SCHEMA,
    EVIDENCE_COLLECTION_INDEX_SCHEMA,
    FINAL_INTEGRATION_REVIEW_SCHEMA,
    FRAMEWORK_REFIT_TRACE_SCHEMA,
    GLOBAL_ATOM_INDEX_SCHEMA,
    INITIAL_FRAMEWORK_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    PHASE3_COVERAGE_REVIEW_SCHEMA,
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    require_atom_plan_mapping_envelope,
    cell,
    line_ranges_label,
    normalize_code,
    repo_relative_path as rel,
    sha256_file,
    source_atom_file_name,
    table_rows,
    write_json,
)
from source_aligned_v7_contract import (
    load_final_integration_review,
    load_initial_framework,
    terminal_authority_sha256,
)


RENDER_CONTRACT_VERSION = "source-aligned-render-v11"
SUPPORTED_ARTIFACTS = {
    "phase1-initial-framework",
    "phase2-source-atoms",
    "phase2-index",
    "phase3-global-index",
    "phase3-coverage-review",
    "phase4-evidence-collections",
    "phase5-atom-plan-mapping",
    "phase5-capability-baseline",
    "phase5-refit-review",
    "workflow-final-integration-review",
    "all-supported",
}


def squash(value: object) -> str:
    text = "" if value is None else str(value)
    return " ".join(text.replace("\n", " ").split())


def repo_root_for(orchestrate_dir: Path) -> Path:
    if orchestrate_dir.parent.name == "openspec":
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


def trace_appendix(
    trace_path: Path,
    trace_schema: str,
    repo_root: Path,
    *,
    digest_override: Optional[str] = None,
) -> str:
    digest = (
        digest_override
        if digest_override is not None
        else sha256_file(trace_path) if trace_path.exists() else ""
    )
    return (
        "\n## Trace Appendix\n\n"
        f"Trace file: `{rel(trace_path, repo_root)}`\n"
        f"Trace schema: `{trace_schema}`\n"
        f"Trace digest: `{digest}`\n"
        f"Render contract: `{RENDER_CONTRACT_VERSION}`\n"
    )


def _markdown_list(values: object) -> List[str]:
    if not isinstance(values, list) or not values:
        return ["- `None`"]
    return [f"- {md(value)}" for value in values]


def render_initial_framework(orchestrate_dir: Path, json_path: Path) -> str:
    """Render the Phase 1 Markdown mirror from the v7 JSON authority."""
    repo_root = repo_root_for(orchestrate_dir)
    data, parsed = load_initial_framework(json_path)
    dependency_by_change: Dict[str, List[Dict[str, object]]] = {}
    for row in parsed["dependencies"]:
        if isinstance(row, dict):
            dependency_by_change.setdefault(
                normalize_code(row.get("dependent-change")),
                [],
            ).append(row)
    guards_by_change: Dict[str, List[Dict[str, object]]] = {}
    for row in parsed["guards"]:
        if isinstance(row, dict):
            guards_by_change.setdefault(
                normalize_code(row.get("guarding-change")),
                [],
            ).append(row)

    landscape_rows: List[List[object]] = []
    for item in data.get("semantic-landscape", []):
        if isinstance(item, dict):
            landscape_rows.append(
                [
                    code(item.get("semantic-area")),
                    md(item.get("source-backed-understanding")),
                    md(item.get("planning-relevance")),
                    list_text(item.get("source-hints")),
                ]
            )
        else:
            landscape_rows.append([code("context"), md(item), md("规划背景"), "`None`"])

    lines = [
        "# Initial Change Plan",
        "",
        "> 本文件由 `initial-framework.json` 确定性渲染；JSON 是 Phase 1 唯一语义权威。",
        "",
        "## 输入",
        "",
        "### Assumptions",
        "",
        *_markdown_list(data.get("assumptions")),
        "",
        "### Conflicts",
        "",
        *_markdown_list(data.get("conflicts")),
        "",
        "### Non-goals",
        "",
        *_markdown_list(data.get("non-goals")),
        "",
        "### Deferred",
        "",
        *_markdown_list(data.get("deferred")),
        "",
        "## Source Semantic Landscape",
        "",
        render_table(
            ["Semantic Area", "Source-backed Understanding", "Planning Relevance", "Source Hints"],
            landscape_rows,
        ).rstrip(),
        "",
        "## Source Delivery Semantics",
        "",
        render_table(
            [
                "Source-backed Statement",
                "Delivery Directive",
                "Affected Outcome Threads",
                "Planning Effect",
                "Source Hint",
            ],
            (
                [
                    md(row.get("source-backed-statement")),
                    code(row.get("delivery-directive")),
                    code_list(row.get("affected-outcome-thread-ids")),
                    md(row.get("planning-effect")),
                    md(row.get("source-hint")),
                ]
                for row in data.get("delivery-semantics", [])
                if isinstance(row, dict)
            ),
        ).rstrip(),
        "",
        "## Capability Map",
        "",
        render_table(
            ["Capability", "Purpose", "Owns", "Excludes", "Boundary Rationale", "Source Hints"],
            (
                [
                    code(row.get("capability")),
                    md(row.get("purpose")),
                    md(row.get("owns")),
                    md(row.get("excludes")),
                    md(row.get("boundary-rationale")),
                    list_text(row.get("source-hints")),
                ]
                for row in parsed["capabilities"]
                if isinstance(row, dict)
            ),
        ).rstrip(),
        "",
        "## Outcome Threads",
        "",
        render_table(
            [
                "Outcome Thread",
                "Beneficiary",
                "Trigger",
                "Observable Result",
                "Acceptance Signal",
                "Primary",
                "Source Hints",
            ],
            (
                [
                    code(row.get("outcome-thread-id")),
                    md(row.get("beneficiary")),
                    md(row.get("trigger")),
                    md(row.get("observable-result")),
                    md(row.get("acceptance-signal")),
                    code(str(bool(row.get("primary"))).lower()),
                    list_text(row.get("source-hints")),
                ]
                for row in parsed["outcomes"]
                if isinstance(row, dict)
            ),
        ).rstrip(),
        "",
        "## Change 切分与排序原则",
        "",
        "- Capability topology 只定义稳定职责与规范归属，不决定 Change boundary、dependency 或 order。",
        "- Change 由 beneficiary、trigger、observable result 与 acceptance signal 构成的 outcome thread 推导。",
        "- 最小 runtime、data、guard、compatibility 与 observability slice 随当前 outcome 同 Change 交付。",
        "- 当前顺序、dependency、foundation 与 overlay 均是待冻结 evidence 在 Phase 5 重新裁决的 hypothesis。",
        "",
        "## Change Roadmap",
        "",
    ]
    changes_by_id = {
        normalize_code(row.get("change")): row
        for row in parsed["changes"]
        if isinstance(row, dict)
    }
    for slug in parsed["change-order"]:
        row = changes_by_id[slug]
        profile = row.get("behavior-profile")
        profile = profile if isinstance(profile, dict) else {}
        closure = row.get("consumer-closure")
        closure = closure if isinstance(closure, dict) else {}
        dependencies = dependency_by_change.get(slug, [])
        guards = guards_by_change.get(slug, [])
        lines.extend(
            [
                f"### {slug}",
                "",
                f"- Change 名称：{code(slug)}",
                f"- 单一 intent：{md(row.get('intent'))}",
                f"- Realized outcome threads：{code_list(row.get('realizes-outcome-thread-ids'))}",
                f"- Usable postcondition：{md(row.get('usable-postcondition'))}",
                f"- Consumer closure：{code(closure.get('mode'))} / {md(closure.get('ref'))}",
                f"- 范围内：{md(row.get('scope-in'))}",
                f"- 范围外：{md(row.get('scope-out'))}",
                "- Behavior completeness profile：",
                f"  - Trigger/context：{md(profile.get('trigger-context'))}",
                f"  - Normative behavior：{md(profile.get('normative-behavior'))}",
                f"  - Observable outcome / invariant：{md(profile.get('observable-outcome-invariant'))}",
                f"  - Important exception / error semantics：{md(profile.get('important-exception-error-semantics'))}",
                f"  - Acceptance evidence：{md(profile.get('acceptance-evidence'))}",
                f"- Hard dependencies：{code_list([item.get('prerequisite-change') for item in dependencies])}",
                f"- Dependency proofs：{md('；'.join(str(item.get('contract-id')) for item in dependencies) or '无')}",
                f"- Guard allocation：{code_list([item.get('guard-link-id') for item in guards])}",
                f"- Independent archive：{md(row.get('independent-archive'))}",
                f"- Split/merge judgment：{md(row.get('split-merge-judgment'))}",
                f"- Source hints：{list_text(row.get('source-hints'))}",
                "",
            ]
        )
    foundation = data.get("foundation")
    lines.extend(
        [
            "## Foundation",
            "",
            (
                f"- Change：{code(foundation.get('change'))}\n"
                f"- First consumer：{code(foundation.get('first-consumer-change'))}\n"
                f"- Source hints：{list_text(foundation.get('source-hints'))}"
                if isinstance(foundation, dict)
                else "- `None`"
            ),
            "",
            "## Change-Capability Overlay",
            "",
            render_table(
                ["Change", "Candidate Capability"],
                (
                    [
                        code(row.get("change")),
                        code(row.get("capability")),
                    ]
                    for row in parsed["overlay"]
                    if isinstance(row, dict)
                ),
            ).rstrip(),
            "",
            "## Phase 1 风险检查",
            "",
            "1. Capability topology 与 Change sequencing 已分离。",
            "2. 每个普通 Change 均有 outcome、usable postcondition、当前 consumer closure 与 direct Capability advancement。",
            "3. Foundation 例外至多一个、仅位于首位，并由紧邻首个 primary outcome Change 消费。",
            "4. Planned guard 与首次受保护 outcome 同 Change。",
            "5. Hard dependency 以 typed edge 和稳定 contract 表达。",
            "6. 每个 roadmap prefix 具有可部署、可验证的 outcome。",
            "",
            "## Phase 1 语言自检",
            "",
            md(data.get("language-self-check")),
        ]
    )
    return "\n".join(lines).rstrip() + "\n" + trace_appendix(
        json_path,
        INITIAL_FRAMEWORK_SCHEMA,
        repo_root,
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
    body.extend(["", "## Mapping Ambiguities", ""])
    body.append(
        render_table(
            ["Global Atom ID", "Evidence Reference", "Ambiguous Dimensions", "Reason"],
            (
                [
                    code(row.get("global-atom-id")),
                    code(json.dumps(row.get("evidence-ref"), ensure_ascii=False, sort_keys=True)),
                    code_list(row.get("dimensions")),
                    md(row.get("reason")),
                ]
                for row in data.get("mapping-ambiguities", [])
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
    require_atom_plan_mapping_envelope(data, json_path, repo_root)
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


def _mapping_ambiguities(orchestrate_dir: Path) -> List[Dict[str, object]]:
    """加载 Phase 3 冻结的 mapping ambiguity，供 Phase 5 review mirror 只读展示。"""
    coverage_path = orchestrate_dir / "phase-works/phase-3/coverage-review.json"
    if not coverage_path.exists():
        return []
    coverage = read_json(coverage_path)
    require_trace_contract(coverage, coverage_path, PHASE3_COVERAGE_REVIEW_SCHEMA)
    rows = coverage.get("mapping-ambiguities")
    return [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def render_framework_refit_review(orchestrate_dir: Path, json_path: Path) -> str:
    """从 v7 framework refit authority 渲染边界复审 mirror。"""
    repo_root = repo_root_for(orchestrate_dir)
    data = read_json(json_path)
    require_trace_contract(data, json_path, FRAMEWORK_REFIT_TRACE_SCHEMA)
    capability_rows = (
        [
            code(row.get("input-capability")),
            code(row.get("decision")),
            code_list(row.get("final-capabilities")),
            md(_gate_results_text(row.get("initial-gate-results"))),
            code_list(row.get("supporting-global-atom-ids")),
            md(row.get("reason")),
        ]
        for row in data.get("capability-reviews", [])
        if isinstance(row, dict)
    )
    change_rows = (
        [
            code(row.get("input-change")),
            code(row.get("decision")),
            code_list(row.get("final-changes")),
            md(_gate_results_text(row.get("initial-gate-results"))),
            code_list(row.get("supporting-global-atom-ids")),
            md(row.get("reason")),
        ]
        for row in data.get("change-reviews", [])
        if isinstance(row, dict)
    )
    final_unit_sections = (
        ("Final Outcome Thread Review", "outcome-thread-reviews", "outcome-thread-id"),
        ("Final Dependency Edge Review", "dependency-edge-reviews", "dependency-id"),
        ("Final Guard Link Review", "guard-link-reviews", "guard-link-id"),
    )
    ambiguity_rows = (
        [
            code(row.get("global-atom-id")),
            code(json.dumps(row.get("evidence-ref"), ensure_ascii=False, sort_keys=True)),
            code_list(row.get("dimensions")),
            md(row.get("reason")),
        ]
        for row in _mapping_ambiguities(orchestrate_dir)
    )
    issues = data.get("issues") if isinstance(data.get("issues"), list) else []
    body = [
        "# Plan Refit Review",
        "",
        "> 本 mirror 只记录 Phase 1 → Phase 5 boundary refit。最终顺序、dependency、guard 与 overlay 仅以 `final-roadmap.json` 为准。",
        "",
        "## Capability Review",
        "",
        render_table(
            [
                "Input Capability", "Decision", "Final Capability(s)",
                "Initial Gate Results", "Supporting GAs", "Reason",
            ],
            capability_rows,
        ).rstrip(),
        "",
        "## Change Review",
        "",
        render_table(
            [
                "Input Change", "Decision", "Final Change(s)",
                "Initial Gate Results", "Supporting GAs", "Reason",
            ],
            change_rows,
        ).rstrip(),
        "",
    ]
    for heading, key, id_field in final_unit_sections:
        body.extend(
            [
                f"## {heading}",
                "",
                render_table(
                    ["Unit", "Result", "Evidence GAs", "Reason"],
                    (
                        [
                            code(row.get(id_field)),
                            code(row.get("result")),
                            code_list(row.get("evidence-ga-ids")),
                            md(row.get("reason")),
                        ]
                        for row in data.get(key, [])
                        if isinstance(row, dict)
                    ),
                ).rstrip(),
                "",
            ]
        )
    body.extend(
        [
            "## Potential Mapping Ambiguities (Input)",
            "",
            "本节只镜像 Phase 3 输入；最终 resolution 仅见 atom-plan-mapping mirror。",
            "",
            render_table(
                ["GA", "Evidence Reference", "Ambiguous Dimensions", "Reason"],
                ambiguity_rows,
            ).rstrip(),
            "",
            "## Authority References",
            "",
            f"- Initial framework：{code(json.dumps(data.get('initial-framework-ref'), ensure_ascii=False, sort_keys=True))}",
            f"- Final roadmap：{code(json.dumps(data.get('final-roadmap-ref'), ensure_ascii=False, sort_keys=True))}",
            "",
            "## Final Decision",
            "",
            f"- Status：{code(data.get('status'))}",
            f"- Issues：{md('；'.join(str(item) for item in issues) if issues else '无')}",
            "",
            "## 语言自检",
            "",
            md(data.get("language-self-check")),
        ]
    )
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
    """Render frozen evidence without carrying extraction-time routing hints."""
    ref = item.get("evidence-ref")
    metadata = [
        f"### {code(item.get('global-atom-id'))}",
        "",
        f"- Evidence reference：{code(json.dumps(ref, ensure_ascii=False, sort_keys=True))}",
        f"- Source：{code(item.get('source-document'))}",
        f"- Lines：{code(lines_from(item))}",
        f"- Atom type：{code(item.get('atom-type'))}",
        f"- Normativity：{code(item.get('normativity'))}",
        f"- Evidence kind：{code(item.get('evidence-kind'))}",
        f"- Delivery directives：{code_list(item.get('delivery-directives'))}",
    ]
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


def _phase4_items(orchestrate_dir: Path) -> List[Dict[str, object]]:
    """Resolve every frozen GA once and return the neutral stable evidence order."""
    resolved = _resolved_global_evidence(orchestrate_dir)
    items = [
        {**evidence, "global-atom-id": ga}
        for ga, evidence in resolved.items()
    ]
    items.sort(key=_evidence_sort_key)
    return items


def _phase4_by_source_path(root: Path, source_document: str) -> Path:
    filename = source_atom_file_name(source_document).replace(".atoms.md", ".md")
    return root / "by-source" / filename


def _phase4_source_groups(
    orchestrate_dir: Path,
    items: Sequence[Dict[str, object]],
) -> List[tuple[str, Path, List[Dict[str, object]]]]:
    root = _phase4_index_path(orchestrate_dir).parent
    grouped: Dict[str, List[Dict[str, object]]] = {}
    for item in items:
        source = normalize_code(item.get("source-document"))
        if not source:
            raise ValueError(f"{item.get('global-atom-id')} 缺少 source-document")
        grouped.setdefault(source, []).append(item)

    paths: Dict[Path, str] = {}
    result: List[tuple[str, Path, List[Dict[str, object]]]] = []
    for source in sorted(grouped):
        path = _phase4_by_source_path(root, source)
        previous = paths.setdefault(path, source)
        if previous != source:
            raise ValueError(f"不同 source document 产生相同 by-source 路径：{previous} / {source}")
        result.append((source, path, grouped[source]))
    return result


def render_evidence_collections(orchestrate_dir: Path, json_path: Optional[Path] = None) -> Dict[Path, str]:
    """直接从冻结 evidence authority 机械组装中立的 Phase 4 Markdown。"""
    del json_path  # v3 index 是输出，不是 renderer 输入。
    items = _phase4_items(orchestrate_dir)
    root = _phase4_index_path(orchestrate_dir).parent
    repo_root = repo_root_for(orchestrate_dir)
    source_groups = _phase4_source_groups(orchestrate_dir, items)
    outputs: Dict[Path, str] = {}
    appendix = _phase4_appendix(orchestrate_dir)

    all_evidence_path = root / "all-evidence.md"
    directives_path = root / "delivery-directives.md"
    index_lines = [
        "# Phase 4 中立冻结证据索引",
        "",
        "本索引只按 source document 提供确定性导航，不表达 Change、Capability 或 roadmap 决策。",
        "",
        f"- All evidence：{code(rel(all_evidence_path, repo_root))}",
        f"- Delivery directives：{code(rel(directives_path, repo_root))}",
        "",
        "## Source Collections",
        "",
        render_table(
            ["Source Document", "Evidence Count", "Collection"],
            (
                [
                    code(source),
                    str(len(source_items)),
                    code(rel(path, repo_root)),
                ]
                for source, path, source_items in source_groups
            ),
        ).rstrip(),
    ]
    outputs[root / "index.md"] = "\n".join(index_lines).rstrip() + "\n" + appendix

    all_lines = [
        "# 全量冻结证据",
        "",
        "以下 evidence occurrence 已通过 frozen evidence resolver 解析，并按 source document、range 起点与 GA 稳定排序。",
        "",
    ]
    if items:
        all_lines.extend(_render_evidence_item(item) for item in items)
    else:
        all_lines.append("无冻结 evidence occurrence。")
    outputs[all_evidence_path] = "\n".join(all_lines).rstrip() + "\n" + appendix

    directive_lines = [
        "# Source-backed 交付指令",
        "",
        "本文件只汇总 source 明示且已冻结的 delivery directive occurrence，不从架构关系、文件位置或常识推断交付顺序。",
        "",
        "- `all-evidence.md` 是完整冻结 occurrence 集合；`by-source/` 只提供同一集合的 source 视图。",
        "- 本阶段不按 Change、Capability、归属状态或 roadmap 位置预分组。",
        "- 下游必须检查全部 GA；本文件不是 owner、target、relation、dependency 或 impact 结论。",
        "",
    ]
    directive_items = [
        item
        for item in items
        if isinstance(item.get("delivery-directives"), list)
        and item.get("delivery-directives")
    ]
    if directive_items:
        directive_lines.extend(_render_evidence_item(item) for item in directive_items)
    else:
        directive_lines.append("无 source-backed delivery directive occurrence。")
    outputs[directives_path] = "\n".join(directive_lines).rstrip() + "\n" + appendix

    for source, path, source_items in source_groups:
        lines = [
            f"# 按来源查看冻结证据：{source}",
            "",
            f"- Source document：{code(source)}",
            f"- Evidence occurrences：{len(source_items)}",
            "",
        ]
        lines.extend(_render_evidence_item(item) for item in source_items)
        outputs[path] = "\n".join(lines).rstrip() + "\n" + appendix
    return outputs


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_evidence_collection_index(
    orchestrate_dir: Path,
    outputs: Optional[Dict[Path, str]] = None,
) -> Dict[str, object]:
    """生成不承载 framework 预分组语义的 Phase 4 v3 派生机器索引。"""
    repo_root = repo_root_for(orchestrate_dir)
    items = _phase4_items(orchestrate_dir)
    rendered = outputs if outputs is not None else render_evidence_collections(orchestrate_dir)
    root = _phase4_index_path(orchestrate_dir).parent
    all_evidence_path = root / "all-evidence.md"
    source_by_path = {
        path: source
        for source, path, _ in _phase4_source_groups(orchestrate_dir, items)
    }
    expected_rendered_paths = {
        root / "index.md",
        all_evidence_path,
        root / "delivery-directives.md",
        *source_by_path,
    }
    if set(rendered) != expected_rendered_paths:
        raise ValueError(
            "Phase 4 rendered Markdown surface不精确；"
            f"missing={sorted(str(path) for path in expected_rendered_paths - set(rendered))}；"
            f"extra={sorted(str(path) for path in set(rendered) - expected_rendered_paths)}"
        )
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    generated_paths = [
        orchestrate_dir / "change-capability-anchors/obligation-atom-index.json",
        orchestrate_dir / "phase-works/phase-3/coverage-review.json",
        *sorted(atom_root.glob("*.atoms.json")),
    ]
    rows = []
    for item in items:
        collection_paths = [
            rel(all_evidence_path, repo_root),
            rel(
                _phase4_by_source_path(root, normalize_code(item.get("source-document"))),
                repo_root,
            ),
        ]
        directives = item.get("delivery-directives")
        if isinstance(directives, list) and directives:
            collection_paths.append(rel(root / "delivery-directives.md", repo_root))
        rows.append({
            "global-atom-id": normalize_code(item.get("global-atom-id")),
            "evidence-ref": item.get("evidence-ref"),
            "source-document": normalize_code(item.get("source-document")),
            "rendered-collection-paths": collection_paths,
        })
    rendered_artifacts: List[Dict[str, object]] = []
    for path, text_value in rendered.items():
        if path.name == "index.md":
            kind, scope = "index", "all"
        elif path.name == "all-evidence.md":
            kind, scope = "all-evidence", "all"
        elif path.name == "delivery-directives.md":
            kind, scope = "delivery-directives", "all"
        elif path.parent.name == "by-source":
            scope = source_by_path.get(path, "")
            if not scope:
                raise ValueError(f"无法解析 by-source rendered artifact：{path}")
            kind = "source"
        else:
            raise ValueError(f"无法分类 Phase 4 rendered artifact：{path}")
        rendered_artifacts.append({
            "artifact-path": rel(path, repo_root),
            "sha256": _sha256_text(text_value),
            "collection-kind": kind,
            "scope": scope,
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
    return render_capability_baseline_payload(orchestrate_dir, json_path, data)


def render_capability_baseline_payload(
    orchestrate_dir: Path,
    json_path: Path,
    data: Dict[str, object],
    *,
    json_sha256: Optional[str] = None,
) -> str:
    """Render baseline data while binding the canonical final JSON path."""
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
    return "\n".join(body).rstrip() + "\n" + trace_appendix(
        json_path,
        CAPABILITY_BASELINE_SCHEMA,
        repo_root,
        digest_override=json_sha256,
    )


def render_final_integration_review(orchestrate_dir: Path, json_path: Path) -> str:
    """Render the workflow-level review without creating a second authority."""
    repo_root = repo_root_for(orchestrate_dir)
    digest = terminal_authority_sha256(orchestrate_dir, repo_root)
    data = load_final_integration_review(
        json_path,
        expected_terminal_digest=digest,
    )
    body = [
        "# Final Integration Review",
        "",
        f"- Status：{code(data.get('status'))}",
        f"- Reviewer：{code(data.get('reviewer-id'))}",
        f"- Terminal authority SHA256：{code(data.get('terminal-authority-sha256'))}",
        "",
    ]
    sections = (
        ("Reviewed Artifacts", "reviewed-artifacts"),
        ("Capability Results", "capability-results"),
        ("Change Results", "change-results"),
        ("Outcome Thread Results", "outcome-thread-results"),
        ("Dependency Edge Results", "dependency-edge-results"),
        ("Guard Link Results", "guard-link-results"),
    )
    for heading, key in sections:
        body.extend([f"## {heading}", ""])
        rows = data.get(key)
        if isinstance(rows, list) and rows:
            body.extend(
                f"- `{json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}`"
                for row in rows
            )
        else:
            body.append("- `None`")
        body.append("")
    body.extend(
        [
            "## Occurrence Chain",
            "",
            f"- `{json.dumps(data.get('occurrence-chain-result'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}`",
            "",
            "## Findings",
            "",
            *_markdown_list(data.get("findings")),
            "",
            "## 语言自检",
            "",
            md(data.get("language-self-check")),
        ]
    )
    return "\n".join(body).rstrip() + "\n" + trace_appendix(
        json_path,
        FINAL_INTEGRATION_REVIEW_SCHEMA,
        repo_root,
    )


def render_jobs(orchestrate_dir: Path, artifact: str, source_document: str = "") -> List[Dict[str, object]]:
    jobs: List[Dict[str, object]] = []
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    if artifact in {"phase1-initial-framework", "all-supported"}:
        path = orchestrate_dir / "phase-works/phase-1/initial-framework.json"
        if path.exists():
            jobs.append(
                {
                    "json-path": path,
                    "md-path": path.with_name("initial-change-plan.md"),
                    "renderer": render_initial_framework,
                }
            )
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
    if artifact in {"workflow-final-integration-review", "all-supported"}:
        path = orchestrate_dir / "final-integration-review.json"
        if path.exists():
            jobs.append(
                {
                    "json-path": path,
                    "md-path": path.with_suffix(".md"),
                    "renderer": render_final_integration_review,
                }
            )
    return jobs


def clean_phase4_legacy(orchestrate_dir: Path) -> None:
    """Reject legacy Phase 4 surfaces; v7 never migrates or deletes them."""
    work = orchestrate_dir / "phase-works/phase-4"
    existing = []
    for name in (
        "input-change-plan.md",
        "source-window-dossiers",
        "source-window-semantic-profile-review.md",
        "source-window-grounding-issues.md",
    ):
        path = work / name
        if path.exists() or path.is_symlink():
            existing.append(str(path))
    if existing:
        raise ValueError(
            "检测到legacy Phase 4 generation；v7禁止迁移、清理或原地覆盖："
            + ", ".join(existing)
        )


def _phase4_expected_surface(
    collection_root: Path,
    rendered_outputs: Dict[Path, str],
) -> tuple[set[Path], set[Path]]:
    files = {Path("evidence-collection-index.json")}
    directories = {Path("by-source")}
    for path in rendered_outputs:
        try:
            relative = path.relative_to(collection_root)
        except ValueError as exc:
            raise ValueError(f"Phase 4 rendered path越出collection root：{path}") from exc
        if relative == Path(".") or relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Phase 4 rendered path非法：{path}")
        files.add(relative)
        directories.update(
            parent
            for parent in relative.parents
            if parent != Path(".")
        )
    return files, directories


def _phase4_actual_surface(collection_root: Path) -> tuple[set[Path], set[Path], set[Path]]:
    if not collection_root.exists() or not collection_root.is_dir() or collection_root.is_symlink():
        return set(), set(), {Path(".")} if collection_root.is_symlink() else set()
    files: set[Path] = set()
    directories: set[Path] = set()
    symlinks: set[Path] = set()
    for path in collection_root.rglob("*"):
        relative = path.relative_to(collection_root)
        if path.is_symlink():
            symlinks.add(relative)
        elif path.is_dir():
            directories.add(relative)
        elif path.is_file():
            files.add(relative)
        else:
            symlinks.add(relative)
    return files, directories, symlinks


def _write_phase4_staging_surface(
    staging_root: Path,
    final_root: Path,
    rendered_outputs: Dict[Path, str],
    index: Dict[str, object],
) -> None:
    staging_root.mkdir(parents=True, exist_ok=False)
    (staging_root / "by-source").mkdir()
    for final_path, text_value in rendered_outputs.items():
        relative = final_path.relative_to(final_root)
        staging_path = staging_root / relative
        staging_path.parent.mkdir(parents=True, exist_ok=True)
        staging_path.write_text(text_value, encoding="utf-8")
    write_json(staging_root / "evidence-collection-index.json", index)

    expected_files, expected_directories = _phase4_expected_surface(
        final_root,
        rendered_outputs,
    )
    actual_files, actual_directories, symlinks = _phase4_actual_surface(staging_root)
    if (
        actual_files != expected_files
        or actual_directories != expected_directories
        or symlinks
    ):
        raise ValueError(
            "Phase 4 staging surface不精确；"
            f"missing-files={sorted(str(path) for path in expected_files - actual_files)}；"
            f"extra-files={sorted(str(path) for path in actual_files - expected_files)}；"
            f"missing-dirs={sorted(str(path) for path in expected_directories - actual_directories)}；"
            f"extra-dirs={sorted(str(path) for path in actual_directories - expected_directories)}；"
            f"symlinks={sorted(str(path) for path in symlinks)}"
        )


def _publish_phase4_surface(
    collection_root: Path,
    rendered_outputs: Dict[Path, str],
    index: Dict[str, object],
) -> None:
    """Stage the complete exact surface, then replace the directory as one transaction."""
    parent = collection_root.parent
    parent.mkdir(parents=True, exist_ok=True)
    if collection_root.is_symlink():
        raise ValueError(f"Phase 4 collection root不得为symlink：{collection_root}")
    transaction_root = Path(tempfile.mkdtemp(prefix=".phase4-neutral-", dir=parent))
    staging_root = transaction_root / "source-evidence-collections"
    backup_root = transaction_root / "previous"
    moved_previous = False
    try:
        _write_phase4_staging_surface(
            staging_root,
            collection_root,
            rendered_outputs,
            index,
        )
        if collection_root.exists():
            if not collection_root.is_dir():
                raise ValueError(f"Phase 4 collection root必须是directory：{collection_root}")
            os.replace(collection_root, backup_root)
            moved_previous = True
        try:
            os.replace(staging_root, collection_root)
        except Exception:
            if moved_previous and backup_root.exists() and not collection_root.exists():
                os.replace(backup_root, collection_root)
                moved_previous = False
            raise
        if backup_root.exists():
            shutil.rmtree(backup_root)
            moved_previous = False
    finally:
        if moved_previous and backup_root.exists() and not collection_root.exists():
            os.replace(backup_root, collection_root)
        shutil.rmtree(transaction_root, ignore_errors=True)


def _phase4_surface_matches(
    collection_root: Path,
    rendered_outputs: Dict[Path, str],
) -> bool:
    expected_files, expected_directories = _phase4_expected_surface(
        collection_root,
        rendered_outputs,
    )
    actual_files, actual_directories, symlinks = _phase4_actual_surface(collection_root)
    return (
        actual_files == expected_files
        and actual_directories == expected_directories
        and not symlinks
    )


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
        if global_path.exists() and coverage_path.exists():
            rendered_outputs = render_evidence_collections(orchestrate_dir)
            index_path = _phase4_index_path(orchestrate_dir)
            markdown_states: List[tuple[Path, bool]] = []
            for md_path, rendered in rendered_outputs.items():
                current = md_path.read_text(encoding="utf-8") if md_path.exists() else None
                drift = current != rendered
                markdown_states.append((md_path, drift))
                drift_count += int(drift)
            expected_index = build_evidence_collection_index(orchestrate_dir, rendered_outputs)
            try:
                current_index = read_json(index_path) if index_path.exists() else None
            except (OSError, ValueError, json.JSONDecodeError):
                current_index = None
            index_drift = current_index != expected_index
            drift_count += int(index_drift)
            surface_drift = not _phase4_surface_matches(index_path.parent, rendered_outputs)
            drift_count += int(surface_drift)
            phase4_changed = any(drift for _, drift in markdown_states) or index_drift or surface_drift
            if write and phase4_changed:
                _publish_phase4_surface(index_path.parent, rendered_outputs, expected_index)
            evidence_count = len(_resolved_global_evidence(orchestrate_dir))
            for md_path, drift in markdown_states:
                results.append({
                    "source-json": "phase2-3-frozen-evidence-set",
                    "target-markdown": md_path.as_posix(),
                    "row-count": evidence_count,
                    "drift": drift if not write else False,
                    "written": bool(write and phase4_changed),
                })
            derived_json_results.append({
                "target-json": index_path.as_posix(),
                "drift": index_drift if not write else False,
                "written": bool(write and phase4_changed),
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
