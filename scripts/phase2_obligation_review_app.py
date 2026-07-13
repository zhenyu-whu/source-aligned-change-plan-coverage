#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the Phase 2 source obligation atom review app.

The generated HTML is a reviewer-facing aid. It renders source documents with
line numbers and shows Phase 2 atom rows as margin annotations. It does not
perform semantic coverage review, duplicate resolution, or ownership decisions.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from source_aligned_trace_lib import SOURCE_ATOMS_SCHEMA, TRACE_CONTRACT_VERSION


TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CANONICAL_RANGE_RE = re.compile(r"^L([1-9]\d*)-L([1-9]\d*)$")
LEGACY_RANGE_RE = re.compile(r"^L?(\d+)(?:\s*-\s*L?(\d+))?$", re.IGNORECASE)


@dataclass(frozen=True)
class ManifestSource:
    path: str
    read_status: str
    role: str
    topics: str
    notes: str


def split_md_row(line: str) -> Optional[List[str]]:
    """Split a markdown table row while preserving pipes inside code spans."""
    text = line.strip()
    if not text.startswith("|"):
        return None
    if text.endswith("|"):
        text = text[1:-1]
    else:
        text = text[1:]

    cells: List[str] = []
    buf: List[str] = []
    escaped = False
    in_code = False
    for char in text:
        if escaped:
            buf.append(char)
            escaped = False
            continue
        if char == "\\":
            buf.append(char)
            escaped = True
            continue
        if char == "`":
            in_code = not in_code
            buf.append(char)
            continue
        if char == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf = []
            continue
        buf.append(char)
    cells.append("".join(buf).strip())
    return cells


def normalize_code(value: str) -> str:
    text = value.strip()
    while text.startswith("`"):
        text = text[1:].strip()
    while text.endswith("`"):
        text = text[:-1].strip()
    return text.replace("\\|", "|").strip()


def normalize_header(value: str) -> str:
    return normalize_code(value).lower()


def squash(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def stable_identifier_list(value: object) -> str:
    """Return a deterministic, de-duplicated reviewer-facing ID list."""
    if isinstance(value, list):
        items = [normalize_code(str(item)) for item in value]
    else:
        text = str(value or "").replace("`", "")
        items = [item.strip() for item in re.split(r"[,;]", text)]
    normalized = sorted({item for item in items if item and item.lower() != "none"})
    return "; ".join(normalized)


def capability_target(value: object) -> str:
    target = normalize_code(str(value or ""))
    return "None/change-only" if not target or target.lower() == "none" else target


def iter_markdown_tables(lines: Sequence[str]) -> Iterable[Tuple[Dict[str, int], List[List[str]]]]:
    for i in range(len(lines) - 1):
        header = split_md_row(lines[i])
        separator = split_md_row(lines[i + 1])
        if not header or not separator:
            continue
        if not all(TABLE_SEPARATOR_RE.match(cell.strip()) for cell in separator):
            continue

        index = {normalize_header(name): pos for pos, name in enumerate(header)}
        rows: List[List[str]] = []
        for raw in lines[i + 2 :]:
            cells = split_md_row(raw)
            if not cells:
                break
            if len(cells) < len(header):
                continue
            rows.append(cells)
        yield index, rows


def get_cell(cells: Sequence[str], index: Dict[str, int], *names: str) -> str:
    for name in names:
        pos = index.get(name.lower())
        if pos is not None and pos < len(cells):
            return cells[pos].strip()
    return ""


def parse_manifest(manifest_path: Path) -> List[ManifestSource]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"source manifest not found: {manifest_path}")

    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    for index, rows in iter_markdown_tables(lines):
        required = {"source document", "read status", "source role"}
        if not required.issubset(index):
            continue

        sources: List[ManifestSource] = []
        for cells in rows:
            source_path = normalize_code(get_cell(cells, index, "source document"))
            read_status = normalize_code(get_cell(cells, index, "read status"))
            if not source_path:
                continue
            sources.append(
                ManifestSource(
                    path=source_path,
                    read_status=read_status,
                    role=squash(get_cell(cells, index, "source role")),
                    topics=squash(get_cell(cells, index, "coarse topics / paths")),
                    notes=squash(get_cell(cells, index, "notes")),
                )
            )
        return sources

    raise ValueError(f"source manifest table not found: {manifest_path}")


def source_atom_file_name(source_path: str) -> str:
    without_suffix = str(Path(source_path).with_suffix(""))
    return without_suffix.replace("/", "--") + ".atoms.md"


def parse_ranges(line_spec: str) -> Tuple[List[Dict[str, int]], List[str]]:
    ranges: List[Dict[str, int]] = []
    warnings: List[str] = []
    normalized = normalize_code(line_spec)
    parts = [part.strip() for part in re.split(r"[;,]", normalized) if part.strip()]
    for raw_part in parts:
        part = normalize_code(raw_part)
        canonical = CANONICAL_RANGE_RE.match(part)
        if canonical:
            start = int(canonical.group(1))
            end = int(canonical.group(2))
        else:
            legacy = LEGACY_RANGE_RE.match(part)
            if not legacy:
                warnings.append(f"unsupported range: {part}")
                continue
            start = int(legacy.group(1))
            end = int(legacy.group(2) or legacy.group(1))
            warnings.append(f"non-canonical range: {part}")
        if start > end:
            start, end = end, start
            warnings.append(f"range start greater than end: {part}")
        ranges.append({"start": start, "end": end})
    return ranges, warnings


def parse_atom_ledger(atom_file: Path) -> Tuple[List[Dict[str, object]], List[str]]:
    if not atom_file.exists():
        return [], [f"missing atom file: {atom_file}"]

    lines = atom_file.read_text(encoding="utf-8").splitlines()
    warnings: List[str] = []
    for index, rows in iter_markdown_tables(lines):
        required = {
            "source atom id",
            "source document",
            "lines",
            "atom type",
            "source fact",
            "candidate status",
            "candidate capability impact",
            "candidate target capability",
            "candidate related capabilities",
        }
        if not required.issubset(index):
            continue

        atoms: List[Dict[str, object]] = []
        for cells in rows:
            atom_id = normalize_code(get_cell(cells, index, "source atom id"))
            source_document = normalize_code(get_cell(cells, index, "source document"))
            line_spec = normalize_code(get_cell(cells, index, "lines"))
            ranges, range_warnings = parse_ranges(line_spec)
            for warning in range_warnings:
                warnings.append(f"{atom_file.name}:{atom_id}: {warning}")
            if not atom_id:
                continue

            atoms.append(
                {
                    "id": atom_id,
                    "sourceDocument": source_document,
                    "lines": line_spec,
                    "ranges": ranges,
                    "atomType": squash(get_cell(cells, index, "atom type")),
                    "sourceFact": squash(get_cell(cells, index, "source fact")),
                    "normativity": squash(get_cell(cells, index, "normativity")),
                    "candidateStatus": squash(get_cell(cells, index, "candidate status")),
                    "candidateArtifactProjection": squash(
                        get_cell(cells, index, "candidate artifact projection")
                    ),
                    "candidateOwnerChange": squash(get_cell(cells, index, "candidate owner change")),
                    "candidateCapabilityImpact": normalize_code(
                        get_cell(cells, index, "candidate capability impact")
                    ),
                    "candidateTargetCapability": capability_target(
                        get_cell(cells, index, "candidate target capability")
                    ),
                    "candidateRelatedCapabilities": stable_identifier_list(
                        get_cell(cells, index, "candidate related capabilities")
                    ),
                    "roles": squash(get_cell(cells, index, "roles")),
                    "rationale": squash(get_cell(cells, index, "rationale")),
                    "proposeUse": squash(get_cell(cells, index, "propose use")),
                    "evidenceNeed": squash(get_cell(cells, index, "evidence need")),
                    "atomFile": str(atom_file),
                }
            )
        return atoms, warnings

    return [], [f"atom ledger table not found: {atom_file}"]


def parse_atom_json(atom_json: Path) -> Tuple[List[Dict[str, object]], List[str]]:
    if not atom_json.exists():
        return [], [f"trace sidecar not found, fallback to Markdown: {atom_json}"]
    data = json.loads(atom_json.read_text(encoding="utf-8"))
    atoms: List[Dict[str, object]] = []
    warnings: List[str] = []
    if data.get("trace-schema") != SOURCE_ATOMS_SCHEMA or data.get("trace-contract-version") != TRACE_CONTRACT_VERSION:
        return [], [
            f"unsupported trace contract in {atom_json}: expected "
            f"{SOURCE_ATOMS_SCHEMA} / {TRACE_CONTRACT_VERSION}"
        ]
    for row in data.get("source-atoms", []):
        if not isinstance(row, dict):
            warnings.append(f"invalid source-atoms row in {atom_json}")
            continue
        atom_id = normalize_code(str(row.get("source-atom-id", "")))
        ranges = row.get("line-ranges", [])
        if not isinstance(ranges, list):
            ranges = []
        atoms.append(
            {
                "id": atom_id,
                "sourceDocument": normalize_code(str(row.get("source-document", ""))),
                "lines": normalize_code(str(row.get("lines", ""))),
                "ranges": ranges,
                "atomType": squash(row.get("atom-type", "")),
                "sourceFact": squash(row.get("source-fact", "")),
                "normativity": squash(row.get("normativity", "")),
                "candidateStatus": squash(row.get("candidate-status", "")),
                "candidateArtifactProjection": squash(row.get("candidate-artifact-projection", "")),
                "candidateOwnerChange": squash(row.get("candidate-owner-change", "")),
                "candidateCapabilityImpact": squash(row.get("candidate-capability-impact", "")),
                "candidateTargetCapability": capability_target(row.get("candidate-target-capability", "")),
                "candidateRelatedCapabilities": stable_identifier_list(
                    row.get("candidate-related-capabilities", [])
                ),
                "roles": squash(row.get("roles", "")),
                "rationale": squash(row.get("rationale", "")),
                "proposeUse": squash(row.get("propose-use", "")),
                "evidenceNeed": squash(row.get("evidence-need", "")),
                "atomFile": str(atom_json),
            }
        )
    return atoms, warnings


def parse_headings(source_lines: Sequence[str]) -> List[Dict[str, object]]:
    headings: List[Dict[str, object]] = []
    for index, line in enumerate(source_lines, start=1):
        match = HEADING_RE.match(line)
        if not match:
            continue
        headings.append(
            {
                "level": len(match.group(1)),
                "line": index,
                "title": match.group(2).strip().rstrip("#").strip(),
            }
        )
    return headings


def build_data(repo_root: Path, orchestrate_dir: Path) -> Dict[str, object]:
    manifest_path = orchestrate_dir / "phase-works/phase-1/source-doc-manifest.md"
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    manifest_sources = parse_manifest(manifest_path)

    docs: List[Dict[str, object]] = []
    warnings: List[str] = []
    status_counts: Counter[str] = Counter()
    projection_counts: Counter[str] = Counter()

    for source in manifest_sources:
        if source.read_status != "read-full":
            continue

        source_path = repo_root / source.path
        if source_path.exists():
            source_lines = source_path.read_text(encoding="utf-8").splitlines()
        else:
            source_lines = []
            warnings.append(f"missing source document: {source.path}")

        atom_file = atom_root / source_atom_file_name(source.path)
        atom_json = atom_file.with_suffix(".json")
        atoms, atom_warnings = parse_atom_json(atom_json)
        if not atom_json.exists():
            atoms, markdown_warnings = parse_atom_ledger(atom_file)
            atom_warnings.extend(markdown_warnings)
        warnings.extend(atom_warnings)
        for atom in atoms:
            status_counts[str(atom.get("candidateStatus", ""))] += 1
            projection_counts[str(atom.get("candidateArtifactProjection", ""))] += 1

        docs.append(
            {
                "path": source.path,
                "role": source.role,
                "topics": source.topics,
                "notes": source.notes,
                "readStatus": source.read_status,
                "lineCount": len(source_lines),
                "headings": parse_headings(source_lines),
                "lines": source_lines,
                "atoms": atoms,
                "atomFile": str(atom_file),
            }
        )

    return {
        "meta": {
            "manifest": str(manifest_path),
            "sourceCount": len(docs),
            "atomCount": sum(len(doc["atoms"]) for doc in docs),
            "statusCounts": dict(sorted(status_counts.items())),
            "projectionCounts": dict(sorted(projection_counts.items())),
            "warnings": warnings,
        },
        "docs": docs,
    }


def json_for_script(data: Dict[str, object]) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render_html(data: Dict[str, object]) -> str:
    payload = json_for_script(data)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Phase 2 Obligation Atom Review</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f6f1;
      --panel: #ffffff;
      --panel-soft: #fbfaf6;
      --ink: #1f2523;
      --muted: #68716d;
      --line: #ded9ce;
      --line-strong: #c7c0b3;
      --accent: #1f7a6d;
      --accent-soft: #dceee9;
      --amber: #a35c00;
      --amber-soft: #fff0d8;
      --blue: #28609a;
      --blue-soft: #e4eef8;
      --danger: #9b3131;
      --danger-soft: #f8e3e0;
      --shadow: 0 12px 28px rgba(31, 37, 35, 0.08);
      --mono: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
      --sans: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      min-width: 1120px;
      background: var(--bg);
      color: var(--ink);
      font-family: var(--sans);
      letter-spacing: 0;
    }}

    button,
    input {{
      font: inherit;
    }}

    .app-shell {{
      display: grid;
      grid-template-columns: 320px minmax(520px, 1fr) 390px;
      height: 100vh;
      min-height: 680px;
    }}

    .sidebar,
    .annotations {{
      min-height: 0;
      overflow: hidden;
      background: var(--panel);
      border-color: var(--line);
    }}

    .sidebar {{
      border-right: 1px solid var(--line);
      display: grid;
      grid-template-rows: auto auto 1fr auto;
    }}

    .annotations {{
      border-left: 1px solid var(--line);
      display: grid;
      grid-template-rows: auto auto 1fr;
    }}

    .brand {{
      padding: 18px 18px 12px;
      border-bottom: 1px solid var(--line);
    }}

    .brand h1 {{
      margin: 0;
      font-size: 18px;
      line-height: 1.25;
      font-weight: 750;
    }}

    .brand p {{
      margin: 7px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}

    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      padding: 12px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel-soft);
    }}

    .summary-item {{
      border: 1px solid var(--line);
      background: #fff;
      padding: 8px;
      min-width: 0;
    }}

    .summary-value {{
      display: block;
      font-family: var(--mono);
      font-size: 17px;
      font-weight: 700;
    }}

    .summary-label {{
      display: block;
      margin-top: 3px;
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
    }}

    .search-box {{
      padding: 12px 18px;
      border-bottom: 1px solid var(--line);
    }}

    .search-box input,
    .annotation-filter input {{
      width: 100%;
      height: 34px;
      border: 1px solid var(--line-strong);
      background: #fff;
      padding: 7px 10px;
      color: var(--ink);
      outline: none;
      border-radius: 4px;
    }}

    .search-box input:focus,
    .annotation-filter input:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-soft);
    }}

    .tree-scroll,
    .annotation-list,
    .document-scroll {{
      min-height: 0;
      overflow: auto;
    }}

    .doc-tree {{
      padding: 8px 10px 14px;
    }}

    .tree-row {{
      width: 100%;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: center;
      min-height: 34px;
      border: 0;
      border-left: 3px solid transparent;
      background: transparent;
      color: var(--ink);
      padding: 7px 8px;
      text-align: left;
      cursor: pointer;
    }}

    .folder-row {{
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      gap: 7px;
      align-items: center;
      min-height: 28px;
      color: var(--muted);
      padding: 6px 8px;
      font-size: 12px;
      font-weight: 700;
    }}

    .folder-badge {{
      border: 1px solid var(--line);
      background: var(--panel-soft);
      color: var(--accent);
      font-family: var(--mono);
      font-size: 10px;
      padding: 1px 4px;
    }}

    .folder-name {{
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .tree-row:hover {{
      background: var(--panel-soft);
    }}

    .tree-row.active {{
      border-left-color: var(--accent);
      background: var(--accent-soft);
    }}

    .tree-path {{
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-family: var(--mono);
      font-size: 12px;
    }}

    .tree-count {{
      min-width: 30px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--muted);
      font-family: var(--mono);
      font-size: 11px;
      padding: 2px 5px;
      text-align: center;
    }}

    .outline {{
      padding: 12px 18px;
      border-top: 1px solid var(--line);
      background: var(--panel-soft);
      max-height: 210px;
      overflow: auto;
    }}

    .outline-title,
    .section-label {{
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0;
      text-transform: uppercase;
    }}

    .outline button {{
      display: block;
      width: 100%;
      border: 0;
      background: transparent;
      color: var(--ink);
      padding: 4px 0;
      text-align: left;
      cursor: pointer;
      font-size: 12px;
      line-height: 1.35;
    }}

    .outline button:hover {{
      color: var(--accent);
    }}

    .workspace {{
      min-width: 0;
      min-height: 0;
      display: grid;
      grid-template-rows: auto 1fr;
    }}

    .doc-header {{
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      padding: 16px 20px 14px;
      box-shadow: var(--shadow);
      z-index: 2;
    }}

    .doc-title-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 10px;
      align-items: start;
    }}

    .doc-path {{
      margin: 0;
      font-family: var(--mono);
      font-size: 17px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }}

    .doc-meta {{
      margin-top: 7px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}

    .doc-stats {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-start;
    }}

    .pill {{
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      border: 1px solid var(--line);
      background: var(--panel-soft);
      color: var(--muted);
      padding: 4px 8px;
      font-size: 12px;
      white-space: nowrap;
    }}

    .pill strong {{
      color: var(--ink);
      font-family: var(--mono);
      margin-right: 5px;
    }}

    .document-scroll {{
      background:
        linear-gradient(90deg, rgba(31, 122, 109, 0.07) 0, rgba(31, 122, 109, 0.07) 72px, transparent 72px),
        var(--bg);
    }}

    .source-lines {{
      padding: 18px 18px 120px;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.55;
    }}

    .source-line {{
      display: grid;
      grid-template-columns: 54px minmax(0, 1fr) 150px;
      gap: 10px;
      min-height: 24px;
      border-left: 3px solid transparent;
      padding: 1px 6px 1px 0;
    }}

    .source-line.has-atom {{
      background: rgba(31, 122, 109, 0.055);
      border-left-color: rgba(31, 122, 109, 0.55);
    }}

    .source-line.active-line {{
      background: var(--amber-soft);
      border-left-color: var(--amber);
    }}

    .line-number {{
      color: var(--muted);
      text-align: right;
      user-select: none;
      padding-right: 5px;
    }}

    .line-text {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }}

    .line-tags {{
      display: flex;
      gap: 4px;
      flex-wrap: wrap;
      align-content: flex-start;
      min-width: 0;
    }}

    .line-tag {{
      border: 1px solid rgba(31, 122, 109, 0.32);
      background: #fff;
      color: var(--accent);
      padding: 1px 5px;
      max-width: 140px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 10px;
      cursor: pointer;
    }}

    .line-tag.active {{
      border-color: var(--amber);
      color: var(--amber);
      background: var(--amber-soft);
    }}

    .annotation-header {{
      padding: 16px 18px 12px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}

    .annotation-header h2 {{
      margin: 0;
      font-size: 16px;
      line-height: 1.3;
    }}

    .annotation-header p {{
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }}

    .annotation-filter {{
      padding: 12px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel-soft);
    }}

    .annotation-list {{
      padding: 12px 14px 120px;
      background: var(--bg);
    }}

    .atom-card {{
      position: relative;
      border: 1px solid var(--line);
      border-left: 4px solid var(--accent);
      background: var(--panel);
      padding: 12px;
      margin-bottom: 10px;
      cursor: pointer;
    }}

    .atom-card:hover {{
      border-color: var(--line-strong);
      box-shadow: 0 8px 18px rgba(31, 37, 35, 0.07);
    }}

    .atom-card.active {{
      border-left-color: var(--amber);
      box-shadow: 0 0 0 3px var(--amber-soft);
    }}

    .atom-topline {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
    }}

    .atom-id {{
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-family: var(--mono);
      font-size: 12px;
      font-weight: 700;
    }}

    .atom-lines {{
      flex: 0 0 auto;
      color: var(--amber);
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 700;
    }}

    .atom-summary {{
      margin: 0 0 10px;
      font-size: 13px;
      line-height: 1.5;
    }}

    .atom-fields {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
    }}

    .field {{
      min-width: 0;
      border: 1px solid var(--line);
      background: var(--panel-soft);
      padding: 6px;
    }}

    .field span {{
      display: block;
      color: var(--muted);
      font-size: 10px;
      margin-bottom: 2px;
    }}

    .field strong {{
      display: block;
      overflow-wrap: anywhere;
      font-size: 11px;
      line-height: 1.3;
      font-weight: 650;
    }}

    .empty-state {{
      border: 1px dashed var(--line-strong);
      color: var(--muted);
      background: var(--panel-soft);
      padding: 14px;
      font-size: 13px;
      line-height: 1.45;
    }}

    .warning-box {{
      margin: 0 18px 12px;
      border: 1px solid var(--danger);
      background: var(--danger-soft);
      color: var(--danger);
      padding: 9px 10px;
      font-size: 12px;
      line-height: 1.45;
    }}

    @media (max-width: 1180px) {{
      body {{
        min-width: 980px;
      }}

      .app-shell {{
        grid-template-columns: 270px minmax(430px, 1fr) 330px;
      }}

      .source-line {{
        grid-template-columns: 48px minmax(0, 1fr) 112px;
      }}
    }}
  </style>
</head>
<body>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <h1>Phase 2 Atom 审阅</h1>
        <p>按源文档路径查看原文、行号范围和 obligation atom 批注。</p>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span class="summary-value" id="sourceCount">0</span><span class="summary-label">source docs</span></div>
        <div class="summary-item"><span class="summary-value" id="atomCount">0</span><span class="summary-label">atoms</span></div>
        <div class="summary-item"><span class="summary-value" id="warningCount">0</span><span class="summary-label">warnings</span></div>
      </div>
      <div class="search-box">
        <input id="docSearch" type="search" placeholder="过滤 source doc 路径" />
      </div>
      <div class="tree-scroll">
        <div class="doc-tree" id="docTree"></div>
      </div>
      <div class="outline" id="outline"></div>
    </aside>

    <main class="workspace">
      <header class="doc-header">
        <div class="doc-title-row">
          <div>
            <h2 class="doc-path" id="docPath"></h2>
            <div class="doc-meta" id="docMeta"></div>
          </div>
          <div class="doc-stats" id="docStats"></div>
        </div>
      </header>
      <div class="document-scroll" id="documentScroll">
        <div class="source-lines" id="sourceLines"></div>
      </div>
    </main>

    <aside class="annotations">
      <div class="annotation-header">
        <h2>Atom 批注</h2>
        <p>点击批注或行内标签可在原文中定位 Line Range。</p>
      </div>
      <div class="annotation-filter">
        <input id="atomSearch" type="search" placeholder="过滤 atom id / 摘要 / owner" />
      </div>
      <div class="annotation-list" id="annotationList"></div>
    </aside>
  </div>

  <script id="review-data" type="application/json">{payload}</script>
  <script>
    const data = JSON.parse(document.getElementById('review-data').textContent);
    const state = {{
      docIndex: 0,
      selectedAtomId: null,
      docFilter: '',
      atomFilter: '',
    }};

    const el = {{
      sourceCount: document.getElementById('sourceCount'),
      atomCount: document.getElementById('atomCount'),
      warningCount: document.getElementById('warningCount'),
      docSearch: document.getElementById('docSearch'),
      docTree: document.getElementById('docTree'),
      outline: document.getElementById('outline'),
      docPath: document.getElementById('docPath'),
      docMeta: document.getElementById('docMeta'),
      docStats: document.getElementById('docStats'),
      documentScroll: document.getElementById('documentScroll'),
      sourceLines: document.getElementById('sourceLines'),
      atomSearch: document.getElementById('atomSearch'),
      annotationList: document.getElementById('annotationList'),
    }};

    function escapeHtml(value) {{
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
    }}

    function currentDoc() {{
      return data.docs[state.docIndex] || data.docs[0];
    }}

    function atomStart(atom) {{
      if (!atom.ranges || atom.ranges.length === 0) return 999999;
      return Math.min(...atom.ranges.map((range) => range.start));
    }}

    function atomCoversLine(atom, lineNumber) {{
      return (atom.ranges || []).some((range) => lineNumber >= range.start && lineNumber <= range.end);
    }}

    function filteredDocs() {{
      const filter = state.docFilter.trim().toLowerCase();
      if (!filter) return data.docs;
      return data.docs.filter((doc) => doc.path.toLowerCase().includes(filter));
    }}

    function buildPathTree(docs) {{
      const root = {{ children: [] }};
      const ensureDir = (children, name, path) => {{
        let node = children.find((candidate) => candidate.type === 'dir' && candidate.name === name);
        if (!node) {{
          node = {{ type: 'dir', name, path, children: [] }};
          children.push(node);
        }}
        return node;
      }};

      docs.forEach((doc) => {{
        const parts = doc.path.split('/');
        let children = root.children;
        let currentPath = '';
        parts.slice(0, -1).forEach((part) => {{
          currentPath = currentPath ? `${{currentPath}}/${{part}}` : part;
          const dir = ensureDir(children, part, currentPath);
          children = dir.children;
        }});
        children.push({{
          type: 'doc',
          name: parts[parts.length - 1],
          path: doc.path,
          doc,
          index: data.docs.indexOf(doc),
        }});
      }});

      return root.children;
    }}

    function renderTreeNodes(nodes, depth = 0) {{
      return nodes.map((node) => {{
        if (node.type === 'dir') {{
          return `
            <div class="folder-row" style="padding-left:${{8 + depth * 14}}px" title="${{escapeHtml(node.path)}}">
              <span class="folder-badge">dir</span>
              <span class="folder-name">${{escapeHtml(node.name)}}</span>
            </div>
            ${{renderTreeNodes(node.children, depth + 1)}}
          `;
        }}

        const active = node.index === state.docIndex ? ' active' : '';
        return `
          <button class="tree-row${{active}}" data-doc-index="${{node.index}}" style="padding-left:${{8 + depth * 14}}px">
            <span class="tree-path" title="${{escapeHtml(node.path)}}">${{escapeHtml(node.name)}}</span>
            <span class="tree-count">${{node.doc.atoms.length}}</span>
          </button>
        `;
      }}).join('');
    }}

    function filteredAtoms(doc) {{
      const filter = state.atomFilter.trim().toLowerCase();
      const atoms = [...doc.atoms].sort((a, b) => atomStart(a) - atomStart(b) || a.id.localeCompare(b.id));
      if (!filter) return atoms;
      return atoms.filter((atom) => [
        atom.id,
        atom.lines,
        atom.atomType,
        atom.sourceFact,
        atom.candidateStatus,
        atom.candidateArtifactProjection,
        atom.candidateOwnerChange,
        atom.candidateCapabilityImpact,
        atom.candidateTargetCapability,
        atom.candidateRelatedCapabilities,
        atom.roles,
      ].join(' ').toLowerCase().includes(filter));
    }}

    function renderSummary() {{
      el.sourceCount.textContent = data.meta.sourceCount;
      el.atomCount.textContent = data.meta.atomCount;
      el.warningCount.textContent = data.meta.warnings.length;
    }}

    function renderDocTree() {{
      const docs = filteredDocs();
      if (docs.length === 0) {{
        el.docTree.innerHTML = '<div class="empty-state">没有匹配的 source doc。</div>';
        return;
      }}

      el.docTree.innerHTML = renderTreeNodes(buildPathTree(docs));

      el.docTree.querySelectorAll('[data-doc-index]').forEach((button) => {{
        button.addEventListener('click', () => {{
          state.docIndex = Number(button.dataset.docIndex);
          state.selectedAtomId = null;
          renderAll(false);
        }});
      }});
    }}

    function renderOutline(doc) {{
      if (!doc.headings.length) {{
        el.outline.innerHTML = '<p class="outline-title">目录</p><div class="empty-state">该文档没有 Markdown heading。</div>';
        return;
      }}

      el.outline.innerHTML = `
        <p class="outline-title">目录</p>
        ${{doc.headings.map((heading) => `
          <button data-line="${{heading.line}}" style="padding-left:${{(heading.level - 1) * 12}}px">
            L${{heading.line}} · ${{escapeHtml(heading.title)}}
          </button>
        `).join('')}}
      `;

      el.outline.querySelectorAll('[data-line]').forEach((button) => {{
        button.addEventListener('click', () => scrollToLine(Number(button.dataset.line)));
      }});
    }}

    function renderDocHeader(doc) {{
      el.docPath.textContent = doc.path;
      el.docMeta.textContent = `${{doc.role || '未标注 role'}} · ${{doc.topics || '无 coarse topics'}}`;
      const directCount = doc.atoms.filter((atom) => atom.candidateStatus === 'direct-candidate').length;
      const contextualCount = doc.atoms.filter((atom) => atom.candidateStatus === 'contextual-candidate').length;
      const unassignedCount = doc.atoms.filter((atom) => atom.candidateStatus === 'unassigned').length;
      el.docStats.innerHTML = `
        <span class="pill"><strong>${{doc.lineCount}}</strong>lines</span>
        <span class="pill"><strong>${{doc.atoms.length}}</strong>atoms</span>
        <span class="pill"><strong>${{directCount}}</strong>direct</span>
        <span class="pill"><strong>${{contextualCount}}</strong>context</span>
        <span class="pill"><strong>${{unassignedCount}}</strong>unassigned</span>
      `;
    }}

    function renderSourceLines(doc) {{
      if (!doc.lines.length) {{
        el.sourceLines.innerHTML = '<div class="empty-state">无法读取该 source doc 原文。</div>';
        return;
      }}

      el.sourceLines.innerHTML = doc.lines.map((line, index) => {{
        const lineNumber = index + 1;
        const atoms = doc.atoms.filter((atom) => atomCoversLine(atom, lineNumber));
        const selected = state.selectedAtomId && atoms.some((atom) => atom.id === state.selectedAtomId);
        const className = [
          'source-line',
          atoms.length ? 'has-atom' : '',
          selected ? 'active-line' : '',
        ].filter(Boolean).join(' ');
        const tags = atoms.slice(0, 4).map((atom) => {{
          const active = atom.id === state.selectedAtomId ? ' active' : '';
          return `<button class="line-tag${{active}}" data-atom-id="${{escapeHtml(atom.id)}}" title="${{escapeHtml(atom.sourceFact)}}">${{escapeHtml(atom.id)}}</button>`;
        }}).join('');
        const more = atoms.length > 4 ? `<span class="line-tag">+${{atoms.length - 4}}</span>` : '';
        return `
          <div class="${{className}}" data-line="${{lineNumber}}">
            <span class="line-number">${{lineNumber}}</span>
            <span class="line-text">${{escapeHtml(line || ' ')}}</span>
            <span class="line-tags">${{tags}}${{more}}</span>
          </div>
        `;
      }}).join('');

      el.sourceLines.querySelectorAll('[data-atom-id]').forEach((button) => {{
        button.addEventListener('click', () => selectAtom(button.dataset.atomId, true));
      }});
    }}

    function renderAnnotations(doc) {{
      const warnings = data.meta.warnings.length
        ? `<div class="warning-box">存在 ${{data.meta.warnings.length}} 条机械解析警告。请检查生成脚本输出或 HTML 数据中的 warnings。</div>`
        : '';
      const atoms = filteredAtoms(doc);
      if (!atoms.length) {{
        el.annotationList.innerHTML = `${{warnings}}<div class="empty-state">该过滤条件下没有 atom 批注。</div>`;
        return;
      }}

      el.annotationList.innerHTML = warnings + atoms.map((atom) => {{
        const active = atom.id === state.selectedAtomId ? ' active' : '';
        return `
          <article class="atom-card${{active}}" data-atom-id="${{escapeHtml(atom.id)}}">
            <div class="atom-topline">
              <div class="atom-id" title="${{escapeHtml(atom.id)}}">${{escapeHtml(atom.id)}}</div>
              <div class="atom-lines">${{escapeHtml(atom.lines)}}</div>
            </div>
            <p class="atom-summary">${{escapeHtml(atom.sourceFact || '未提供 Source Fact')}}</p>
            <div class="atom-fields">
              <div class="field"><span>Atom Type</span><strong>${{escapeHtml(atom.atomType)}}</strong></div>
              <div class="field"><span>Status</span><strong>${{escapeHtml(atom.candidateStatus)}}</strong></div>
              <div class="field"><span>Projection</span><strong>${{escapeHtml(atom.candidateArtifactProjection)}}</strong></div>
              <div class="field"><span>Owner Change</span><strong>${{escapeHtml(atom.candidateOwnerChange || 'none')}}</strong></div>
              <div class="field"><span>Capability Impact</span><strong>${{escapeHtml(atom.candidateCapabilityImpact || 'none')}}</strong></div>
              <div class="field"><span>Target Capability</span><strong>${{escapeHtml(atom.candidateTargetCapability || 'None/change-only')}}</strong></div>
              <div class="field"><span>Related Capabilities</span><strong>${{escapeHtml(atom.candidateRelatedCapabilities || 'none')}}</strong></div>
              <div class="field"><span>Evidence</span><strong>${{escapeHtml(atom.evidenceNeed || 'none')}}</strong></div>
            </div>
          </article>
        `;
      }}).join('');

      el.annotationList.querySelectorAll('[data-atom-id]').forEach((card) => {{
        card.addEventListener('click', () => selectAtom(card.dataset.atomId, true));
      }});
    }}

    function scrollToLine(lineNumber) {{
      const row = el.sourceLines.querySelector(`[data-line="${{lineNumber}}"]`);
      if (!row) return;
      row.scrollIntoView({{ block: 'center', behavior: 'smooth' }});
    }}

    function selectAtom(atomId, shouldScroll) {{
      state.selectedAtomId = atomId;
      const doc = currentDoc();
      const atom = doc.atoms.find((candidate) => candidate.id === atomId);
      renderSourceLines(doc);
      renderAnnotations(doc);
      if (shouldScroll && atom) {{
        scrollToLine(atomStart(atom));
      }}
    }}

    function renderAll(resetScroll = true) {{
      const doc = currentDoc();
      renderSummary();
      renderDocTree();
      renderOutline(doc);
      renderDocHeader(doc);
      renderSourceLines(doc);
      renderAnnotations(doc);
      if (resetScroll) {{
        el.documentScroll.scrollTop = 0;
      }}
    }}

    el.docSearch.addEventListener('input', (event) => {{
      state.docFilter = event.target.value;
      renderDocTree();
    }});

    el.atomSearch.addEventListener('input', (event) => {{
      state.atomFilter = event.target.value;
      renderAnnotations(currentDoc());
    }});

    renderAll();
  </script>
</body>
</html>
"""


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root that contains source documents.",
    )
    parser.add_argument(
        "--orchestrate-dir",
        type=Path,
        default=Path("openspec/orchestrate"),
        help="OpenSpec orchestrate directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output HTML path. Defaults to phase-works/phase-2/source-obligation-review/index.html.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    orchestrate_dir = args.orchestrate_dir
    if not orchestrate_dir.is_absolute():
        orchestrate_dir = repo_root / orchestrate_dir
    orchestrate_dir = orchestrate_dir.resolve()

    output = args.output
    if output is None:
        output = orchestrate_dir / "phase-works/phase-2/source-obligation-review/index.html"
    elif not output.is_absolute():
        output = repo_root / output
    output = output.resolve()

    data = build_data(repo_root, orchestrate_dir)
    write_text(output, render_html(data))

    meta = data["meta"]
    warning_count = len(meta["warnings"])  # type: ignore[index]
    print(
        "generated Phase 2 review app: "
        f"{output} ({meta['sourceCount']} source docs, {meta['atomCount']} atoms, {warning_count} warnings)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
