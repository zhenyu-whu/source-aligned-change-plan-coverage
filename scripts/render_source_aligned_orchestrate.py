#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render source-aligned Markdown mirrors from canonical JSON sidecars."""

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


RENDER_CONTRACT_VERSION = "source-aligned-render-v1"
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
        raise ValueError(f"{path} must contain a JSON object")
    return data


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
    source_document = squash(data.get("source-document"))
    source_role = squash(data.get("source-role")) or manifest_source_role(orchestrate_dir, source_document) or "None"
    lines: List[str] = [
        f"# Phase 2 Source Obligation Atoms: {Path(source_document).with_suffix('').as_posix().replace('/', '--')}",
        "",
        "## Source Metadata",
        "",
        f"- Source Path: {code(source_document)}",
        f"- Source Role: {md(source_role)}",
        f"- Read Status: {code(data.get('read-status'))}",
        f"- Line Count: {code(source_line_count(repo_root, source_document))}",
        f"- Source SHA-256: {code(data.get('source-sha256'))}",
        f"- Canonical Owner: {code(data.get('canonical-owner'))}",
        "",
        "## Phase 1 Candidate Changes/Capabilities Considered",
        "",
    ]
    considered = data.get("phase-1-candidate-changes-capabilities-considered")
    if isinstance(considered, list) and considered:
        for item in considered:
            if isinstance(item, dict):
                change = code(item.get("change"))
                caps = code_list(item.get("capabilities"))
                note = md(item.get("note"))
                lines.append(f"- {change}: capabilities {caps}。{note}")
            else:
                lines.append(f"- {md(item)}")
    elif considered:
        lines.append(md(considered))
    else:
        lines.append("- `None`")
    lines.extend(["", "## Source Section Inventory", ""])
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
    lines.extend(["", "## Obligation Atom Candidate Ledger", ""])
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
                "Candidate Owner Capability",
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
                    code(row.get("candidate-owner-capability")),
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
    lines.extend(["", "## Source Anchor Table", ""])
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
        ("Source Remainder Notes", data.get("source-remainder-notes")),
        ("Ownership Ambiguity Notes", data.get("ownership-ambiguity-notes")),
        ("Candidate Missing Plan Boundaries", data.get("candidate-missing-plan-boundaries")),
        ("Blockers", data.get("blockers")),
    ]
    for heading, value in notes:
        lines.extend(["", f"## {heading}", ""])
        if isinstance(value, list) and value:
            lines.extend(f"- {md(item)}" for item in value)
        elif value:
            lines.append(md(value))
        else:
            lines.append("- `None`")
    lines.extend(["", "## Language Self-Check", "", md(data.get("language-self-check") or "该 Markdown mirror 由 canonical JSON sidecar 机械渲染。")])
    return "\n".join(lines).rstrip() + "\n" + trace_appendix(json_path, SOURCE_ATOMS_SCHEMA, repo_root)


def render_global_index(orchestrate_dir: Path, json_path: Path) -> str:
    repo_root = repo_root_for(orchestrate_dir)
    data = read_json(json_path)
    body = [
        "# Obligation Atom Index",
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
                "Owner Capability",
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
                    code(row.get("owner-capability")),
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
    body = [
        "# Source To Global Atom Map",
        "",
        render_table(
            [
                "Source Document",
                "Source Atom ID",
                "Lines",
                "Candidate Status",
                "Candidate Artifact Projection",
                "Candidate Owner Change",
                "Candidate Owner Capability",
                "Global Atom ID",
                "Global Relation",
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
                    code(row.get("candidate-owner-capability")),
                    code(row.get("global-atom-id")),
                    code(row.get("global-relation")),
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
    body = ["# Source Remainder Review", "", "## Audit Documents", ""]
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
    body.extend(["", "## Semantic Review Rows", ""])
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
    body = [
        "# Atom Plan Mapping",
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
                "Final Owner Capability",
                "Final Artifact Projection",
                "Final Relation",
                "Capability Advancement",
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
                    code(row.get("final-owner-capability")),
                    code(row.get("final-artifact-projection")),
                    code(row.get("final-relation")),
                    code(row.get("capability-advancement")),
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
        raise ValueError(f"unsupported artifact: {artifact}")
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
    parser = argparse.ArgumentParser(description="Render source-aligned Markdown mirrors from canonical JSON sidecars.")
    parser.add_argument("--orchestrate-dir", default="openspec/orchestrate")
    parser.add_argument("--artifact", choices=sorted(SUPPORTED_ARTIFACTS), default="all-supported")
    parser.add_argument("--source-document", default="")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = render_orchestrate(Path(args.orchestrate_dir), args.artifact, args.source_document, args.write)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        action = "wrote" if args.write else "checked"
        print(f"{action} {result['rendered-files']} files; drift-count={result['drift-count']}")
        for warning in result["warnings"]:
            print(f"warning: {warning}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
