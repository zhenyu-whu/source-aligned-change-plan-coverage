#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据 canonical JSON sidecar 渲染 source-aligned Markdown mirror。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from source_aligned_trace_lib import (
    ATOM_PLAN_MAPPING_SCHEMA,
    GLOBAL_ATOM_INDEX_SCHEMA,
    SOURCE_ATOMS_SCHEMA,
    SOURCE_REMAINDER_REVIEW_SCHEMA,
    SOURCE_TO_GLOBAL_MAP_SCHEMA,
    TRACE_CONTRACT_VERSION,
    line_ranges_label,
    sha256_file,
    source_atom_file_name,
)


RENDER_CONTRACT_VERSION = "source-aligned-render-v2"
SUPPORTED_ARTIFACTS = {
    "phase2-source-atoms",
    "phase3-global-index",
    "phase3-source-map",
    "phase3-remainder-review",
    "phase5-atom-plan-mapping",
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
    raw = squash(row.get("lines", ""))
    if raw:
        return raw
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
    lines.extend(["", "## 来源章节清单", ""])
    lines.append(
        render_table(
            ["Source Section or Range", "Read Status", "Production Meaning", "Atom IDs", "Non-Atom Classification", "Reason"],
            (
                [
                    md(row.get("source-section-or-range")),
                    code(row.get("read-status")),
                    code(row.get("production-meaning")),
                    code_list(row.get("atom-ids")),
                    code(row.get("non-atom-classification")),
                    md(row.get("reason")),
                ]
                for row in data.get("section-inventory", [])
                if isinstance(row, dict)
            ),
        ).rstrip()
    )
    lines.extend(["", "## obligation atom 候选台账", ""])
    lines.append(
        render_table(
            [
                "Source Atom ID",
                "Source Document",
                "Lines",
                "Atom Type",
                "Source Fact",
                "Normativity",
                "Candidate Status",
                "Candidate Artifact Projection",
                "Candidate Owner Change",
                "Candidate Capability Impact",
                "Candidate Target Capability",
                "Candidate Related Capabilities",
                "Roles",
                "Rationale",
                "Propose Use",
                "Evidence Need",
            ],
            (
                [
                    code(row.get("source-atom-id")),
                    code(row.get("source-document")),
                    lines_from(row),
                    code(row.get("atom-type")),
                    md(row.get("source-fact")),
                    code(row.get("normativity")),
                    code(row.get("candidate-status")),
                    code(row.get("candidate-artifact-projection")),
                    code(row.get("candidate-owner-change")),
                    code(row.get("candidate-capability-impact")),
                    capability_target(row.get("candidate-target-capability")),
                    stable_code_list(row.get("candidate-related-capabilities")),
                    code_list(row.get("roles")),
                    md(row.get("rationale")),
                    md(row.get("propose-use")),
                    code(row.get("evidence-need")),
                ]
                for row in data.get("source-atoms", [])
                if isinstance(row, dict)
            ),
        ).rstrip()
    )
    lines.extend(["", "## source anchor 表", ""])
    lines.append(
        render_table(
            [
                "Source Document",
                "Anchor",
                "Lines",
                "Source Phrase",
                "Candidate Status",
                "Source Atom IDs",
                "Candidate Owners",
                "Roles",
                "Rationale",
            ],
            (
                [
                    code(row.get("source-document")),
                    md(row.get("anchor")),
                    lines_from(row),
                    md(row.get("source-phrase")),
                    code(row.get("candidate-status")),
                    code_list(row.get("source-atom-ids")),
                    code_list(row.get("candidate-owners")),
                    code_list(row.get("roles")),
                    md(row.get("rationale")),
                ]
                for row in data.get("source-anchors", [])
                if isinstance(row, dict)
            ),
        ).rstrip()
    )
    notes = [
        ("来源剩余内容说明", data.get("source-remainder-notes")),
        ("所有权歧义说明", data.get("ownership-ambiguity-notes")),
        ("候选缺失 plan 边界", data.get("candidate-missing-plan-boundaries")),
        ("阻塞项", data.get("blockers")),
    ]
    for heading, value in notes:
        lines.extend(["", f"## {heading}", ""])
        if isinstance(value, list) and value:
            lines.extend(f"- {md(item)}" for item in value)
        elif value:
            lines.append(md(value))
        else:
            lines.append("- `None`")
    lines.extend(["", "## 语言自检", "", md(data.get("language-self-check") or "该 Markdown mirror 由 canonical JSON sidecar 机械渲染。")])
    return "\n".join(lines).rstrip() + "\n" + trace_appendix(json_path, SOURCE_ATOMS_SCHEMA, repo_root)


def render_global_index(orchestrate_dir: Path, json_path: Path) -> str:
    repo_root = repo_root_for(orchestrate_dir)
    data = read_json(json_path)
    require_trace_contract(data, json_path, GLOBAL_ATOM_INDEX_SCHEMA)
    body = [
        "# obligation atom 索引",
        "",
        render_table(
            [
                "Global Atom ID",
                "Source Document",
                "Lines",
                "Atom Type",
                "Source Fact",
                "Normativity",
                "Coverage Status",
                "Artifact Projection",
                "Owner Change",
                "Capability Impact",
                "Target Capability",
                "Related Capabilities",
                "Source Atom Origins",
                "Atom Relation",
                "Propose Use",
                "Evidence Need",
                "Review Judgment",
            ],
            (
                [
                    code(row.get("global-atom-id")),
                    code(row.get("source-document")),
                    lines_from(row),
                    code(row.get("atom-type")),
                    md(row.get("source-fact")),
                    code(row.get("normativity")),
                    code(row.get("coverage-status")),
                    code(row.get("artifact-projection")),
                    code(row.get("owner-change")),
                    code(row.get("capability-impact")),
                    capability_target(row.get("target-capability")),
                    stable_code_list(row.get("related-capabilities")),
                    code_list(row.get("source-atom-origins") or row.get("origins")),
                    code(row.get("atom-relation")),
                    md(row.get("propose-use")),
                    code(row.get("evidence-need")),
                    md(row.get("review-judgment")),
                ]
                for row in data.get("global-atoms", [])
                if isinstance(row, dict)
            ),
        ).rstrip(),
    ]
    return "\n".join(body).rstrip() + "\n" + trace_appendix(json_path, GLOBAL_ATOM_INDEX_SCHEMA, repo_root)


def render_source_map(orchestrate_dir: Path, json_path: Path) -> str:
    repo_root = repo_root_for(orchestrate_dir)
    data = read_json(json_path)
    require_trace_contract(data, json_path, SOURCE_TO_GLOBAL_MAP_SCHEMA)
    body = [
        "# source atom 到 global atom 的映射",
        "",
        render_table(
            [
                "Source Document",
                "Source Atom ID",
                "Lines",
                "Candidate Status",
                "Candidate Artifact Projection",
                "Candidate Owner Change",
                "Candidate Capability Impact",
                "Candidate Target Capability",
                "Candidate Related Capabilities",
                "Global Atom ID",
                "Global Relation",
                "Global Capability Impact",
                "Global Target Capability",
                "Global Related Capabilities",
                "Non-Coverage Status",
                "Blocker",
                "Review Decision",
                "Reason",
            ],
            (
                [
                    code(row.get("source-document")),
                    code(row.get("source-atom-id")),
                    lines_from(row),
                    code(row.get("candidate-status")),
                    code(row.get("candidate-artifact-projection")),
                    code(row.get("candidate-owner-change")),
                    code(row.get("candidate-capability-impact")),
                    capability_target(row.get("candidate-target-capability")),
                    stable_code_list(row.get("candidate-related-capabilities")),
                    code(row.get("global-atom-id")),
                    code(row.get("global-relation")),
                    code(row.get("global-capability-impact")),
                    capability_target(row.get("global-target-capability")),
                    stable_code_list(row.get("global-related-capabilities")),
                    code(row.get("non-coverage-status")),
                    md(row.get("blocker")),
                    code(row.get("review-decision")),
                    md(row.get("reason")),
                ]
                for row in data.get("rows", [])
                if isinstance(row, dict)
            ),
        ).rstrip(),
    ]
    return "\n".join(body).rstrip() + "\n" + trace_appendix(json_path, SOURCE_TO_GLOBAL_MAP_SCHEMA, repo_root)


def render_remainder_review(orchestrate_dir: Path, json_path: Path) -> str:
    repo_root = repo_root_for(orchestrate_dir)
    data = read_json(json_path)
    require_trace_contract(data, json_path, SOURCE_REMAINDER_REVIEW_SCHEMA)
    body = ["# 来源剩余内容审阅", "", "## 审计文档", ""]
    body.append(
        render_table(
            ["Source Document", "Line Count", "Evidence Ranges", "Candidate Uncovered Ranges"],
            (
                [
                    code(row.get("source-document")),
                    code(row.get("line-count")),
                    md("; ".join(lines_from(item) for item in row.get("evidence-ranges", []) if isinstance(item, dict))),
                    md("; ".join(lines_from(item) for item in row.get("candidate-uncovered-ranges", []) if isinstance(item, dict))),
                ]
                for row in data.get("audit-documents", [])
                if isinstance(row, dict)
            ),
        ).rstrip()
    )
    body.extend(["", "## 语义审阅记录", ""])
    body.append(
        render_table(
            [
                "Source Document",
                "Lines",
                "How Found",
                "Read Scope",
                "Semantic Classification",
                "Production Obligation",
                "Linked Global Atom IDs",
                "Non-Coverage Status",
                "Blocker",
                "Reason",
            ],
            (
                [
                    code(row.get("source-document")),
                    lines_from(row),
                    code(row.get("how-found")),
                    md(row.get("read-scope")),
                    code(row.get("semantic-classification")),
                    code(row.get("production-obligation")),
                    code_list(row.get("linked-global-atom-ids")),
                    code(row.get("non-coverage-status")),
                    md(row.get("blocker")),
                    md(row.get("reason")),
                ]
                for row in data.get("rows", [])
                if isinstance(row, dict)
            ),
        ).rstrip()
    )
    return "\n".join(body).rstrip() + "\n" + trace_appendix(json_path, SOURCE_REMAINDER_REVIEW_SCHEMA, repo_root)


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
                "Source Document",
                "Lines",
                "Phase 3 Owner / Status",
                "Phase 3 Artifact Projection",
                "Final Owner Type",
                "Final Owner Change",
                "Final Capability Impact",
                "Final Target Capability",
                "Related Capabilities",
                "Final Artifact Projection",
                "Final Relation",
                "Plan Decision",
                "Reason",
            ],
            (
                [
                    code(row.get("global-atom-id")),
                    code(row.get("source-document")),
                    lines_from(row),
                    md(row.get("phase-3-owner-status")),
                    code(row.get("phase-3-artifact-projection")),
                    code(row.get("final-owner-type")),
                    code(row.get("final-owner-change")),
                    code(row.get("final-capability-impact")),
                    capability_target(row.get("final-target-capability")),
                    stable_code_list(row.get("related-capabilities")),
                    code(row.get("final-artifact-projection")),
                    code(row.get("final-relation")),
                    code(row.get("plan-decision")),
                    md(row.get("reason")),
                ]
                for row in data.get("rows", [])
                if isinstance(row, dict)
            ),
        ).rstrip(),
    ]
    return "\n".join(body).rstrip() + "\n" + trace_appendix(json_path, ATOM_PLAN_MAPPING_SCHEMA, repo_root)


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
    if artifact in {"phase3-source-map", "all-supported"}:
        path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json"
        if path.exists():
            jobs.append({"json-path": path, "md-path": path.with_suffix(".md"), "renderer": render_source_map})
    if artifact in {"phase3-remainder-review", "all-supported"}:
        path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-remainder-review.json"
        if path.exists():
            jobs.append({"json-path": path, "md-path": path.with_suffix(".md"), "renderer": render_remainder_review})
    if artifact in {"phase5-atom-plan-mapping", "all-supported"}:
        path = orchestrate_dir / "phase-works/phase-5/atom-plan-mapping.json"
        if path.exists():
            jobs.append({"json-path": path, "md-path": path.with_suffix(".md"), "renderer": render_atom_plan_mapping})
    return jobs


def render_orchestrate(orchestrate_dir: Path, artifact: str, source_document: str = "", write: bool = False) -> Dict[str, object]:
    if artifact not in SUPPORTED_ARTIFACTS:
        raise ValueError(f"不支持的 artifact：{artifact}")
    results: List[Dict[str, object]] = []
    drift_count = 0
    warnings: List[str] = []
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
        for key in ("source-atoms", "global-atoms", "rows"):
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
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="根据 canonical JSON sidecar 渲染 source-aligned Markdown mirror。")
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
