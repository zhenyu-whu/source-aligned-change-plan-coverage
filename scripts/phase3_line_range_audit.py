#!/usr/bin/env python3
"""Phase 3 line-range mechanical helper。

解析 Phase 2 source-first atom file，按 source document 对 atom 范围分组，
合并行范围，并输出 candidate uncovered range 和 overlap cluster。
本工具刻意不对语义进行分类。
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from source_aligned_trace_lib import (
    SOURCE_ATOMS_SCHEMA,
    TRACE_CONTRACT_VERSION,
    line_ranges_label,
    merge_line_ranges,
    uncovered_line_ranges,
)


TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
CANONICAL_RANGE_SEGMENT_RE = re.compile(r"^L([1-9]\d*)-L([1-9]\d*)$")
LEGACY_RANGE_SEGMENT_RE = re.compile(r"^L?(\d+)(?:\s*-\s*L?(\d+))?$", re.IGNORECASE)


@dataclass
class EvidenceRow:
    origin: str
    file: str
    table_line: int
    source_document: str
    row_id: str
    lines: str
    raw_lines: str
    source_fact: str
    status: str
    candidate_owner_change: str
    candidate_target_capability: str


@dataclass
class ParsedRange:
    start: int
    end: int
    row: EvidenceRow


def split_md_row(line: str) -> Optional[List[str]]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def normalize_cell(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("`", "")).strip()


def normalize_spacing(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def index_header(header: List[str]) -> Dict[str, int]:
    return {normalize_cell(name).lower(): pos for pos, name in enumerate(header)}


def get_cell(cells: List[str], index: Dict[str, int], *names: str) -> str:
    for name in names:
        pos = index.get(name)
        if pos is not None and pos < len(cells):
            return cells[pos]
    return ""


def parse_source_rows(markdown_path: Path) -> List[EvidenceRow]:
    lines = markdown_path.read_text(encoding="utf-8").splitlines()
    source_document = ""
    for raw in lines:
        if raw.startswith("- 来源路径："):
            source_document = normalize_cell(raw.split("：", 1)[1])
            break
    rows: List[EvidenceRow] = []
    for i in range(len(lines) - 1):
        header = split_md_row(lines[i])
        separator = split_md_row(lines[i + 1])
        if not header or not separator:
            continue
        if not all(TABLE_SEPARATOR_RE.match(cell) for cell in separator):
            continue
        index = index_header(header)
        if "lines" not in index:
            continue

        has_atom_id = "source atom id" in index
        if not has_atom_id:
            continue

        origin = "atom"
        for j in range(i + 2, len(lines)):
            cells = split_md_row(lines[j])
            if not cells:
                break
            if len(cells) < len(header):
                continue

            raw_line_spec = normalize_spacing(get_cell(cells, index, "lines"))
            line_spec = normalize_cell(raw_line_spec)
            if not source_document or not line_spec:
                continue

            row_id = normalize_cell(get_cell(cells, index, "source atom id"))
            source_fact = get_cell(cells, index, "source fact")
            status = get_cell(cells, index, "candidate status")
            owner_change = get_cell(cells, index, "candidate owner change")
            target_capability = get_cell(cells, index, "candidate target capability")

            if not row_id:
                continue

            rows.append(
                EvidenceRow(
                    origin=origin,
                    file=str(markdown_path),
                    table_line=j + 1,
                    source_document=source_document,
                    row_id=row_id,
                    lines=line_spec,
                    raw_lines=raw_line_spec,
                    source_fact=source_fact,
                    status=status,
                    candidate_owner_change=owner_change,
                    candidate_target_capability=target_capability,
                )
            )
    return rows


def source_document_from_markdown(markdown_path: Path) -> str:
    for raw in markdown_path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("- 来源路径："):
            return normalize_cell(raw.split("：", 1)[1])
    return ""


def source_document_from_trace(json_path: Path) -> str:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if data.get("trace-schema") != SOURCE_ATOMS_SCHEMA or data.get("trace-contract-version") != TRACE_CONTRACT_VERSION:
        raise ValueError(
            f"{json_path} 必须使用 {SOURCE_ATOMS_SCHEMA} / {TRACE_CONTRACT_VERSION}"
        )
    return normalize_cell(str(data.get("source-document", "")))


def parse_source_rows_from_trace(json_path: Path) -> List[EvidenceRow]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if data.get("trace-schema") != SOURCE_ATOMS_SCHEMA or data.get("trace-contract-version") != TRACE_CONTRACT_VERSION:
        raise ValueError(
            f"{json_path} 必须使用 {SOURCE_ATOMS_SCHEMA} / {TRACE_CONTRACT_VERSION}"
        )
    rows: List[EvidenceRow] = []
    source_document = normalize_cell(str(data.get("source-document", "")))
    for index, raw in enumerate(data.get("source-atoms", []), start=1):
        if not isinstance(raw, dict):
            continue
        raw_ranges = raw.get("line-ranges", [])
        valid_ranges = [
            {"start": item.get("start"), "end": item.get("end")}
            for item in raw_ranges
            if isinstance(item, dict)
            and isinstance(item.get("start"), int)
            and isinstance(item.get("end"), int)
        ] if isinstance(raw_ranges, list) else []
        line_spec = line_ranges_label(valid_ranges) if valid_ranges else ""
        row_id = normalize_cell(str(raw.get("source-atom-id", "")))
        if not source_document or not line_spec or not row_id:
            continue
        rows.append(
            EvidenceRow(
                origin="atom",
                file=str(json_path),
                table_line=index,
                source_document=source_document,
                row_id=row_id,
                lines=line_spec,
                raw_lines=line_spec,
                source_fact=str(raw.get("source-fact", "")),
                status=str(raw.get("candidate-status", "")),
                candidate_owner_change=str(raw.get("candidate-owner-change", "")),
                candidate_target_capability=str(raw.get("candidate-target-capability", "")),
            )
        )
    return rows


def parse_line_ranges(row: EvidenceRow) -> Tuple[List[Tuple[int, int]], List[str], List[str]]:
    ranges: List[Tuple[int, int]] = []
    errors: List[str] = []
    warnings: List[str] = []

    if "`" in row.raw_lines:
        warnings.append("行范围不应包含在 Markdown 反引号中")
    if "," in row.lines:
        warnings.append("多个行范围应使用 '; ' 分隔，不应使用 ','")

    parts = [part.strip() for part in re.split(r"[;,]", row.lines) if part.strip()]
    for part in parts:
        canonical_match = CANONICAL_RANGE_SEGMENT_RE.match(part)
        if canonical_match:
            start = int(canonical_match.group(1))
            end = int(canonical_match.group(2))
        else:
            warnings.append(f"非 canonical range segment：{part}；预期格式为 L<start>-L<end>")
            match = LEGACY_RANGE_SEGMENT_RE.match(part)
            if not match:
                errors.append(f"不支持的 range segment：{part}")
                continue
            start = int(match.group(1))
            end = int(match.group(2) or match.group(1))
        if start > end:
            warnings.append(f"range start 大于 end，已执行 mechanical normalization：{part}")
            start, end = end, start
        if start <= 0 or end <= 0:
            errors.append(f"行号必须为正数：{part}")
            continue
        ranges.append((start, end))
    return ranges, errors, warnings


def iter_source_atom_files(orchestrate_dir: Path) -> Iterable[Path]:
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    if not atom_root.exists():
        return
    for atom_file in sorted(atom_root.glob("*.atoms.md")):
        if atom_file.name != "index.md":
            yield atom_file


def iter_source_atom_trace_files(orchestrate_dir: Path) -> Iterable[Path]:
    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    if not atom_root.exists():
        return
    for atom_file in sorted(atom_root.glob("*.atoms.json")):
        yield atom_file


def merge_ranges(ranges: List[ParsedRange]) -> List[Tuple[int, int]]:
    merged = merge_line_ranges([{"start": item.start, "end": item.end} for item in ranges])
    return [(item["start"], item["end"]) for item in merged]


def uncovered_ranges(merged: List[Tuple[int, int]], line_count: int) -> List[Tuple[int, int]]:
    uncovered = uncovered_line_ranges([{"start": start, "end": end} for start, end in merged], line_count)
    return [(item["start"], item["end"]) for item in uncovered]


def intersect_ranges(left: ParsedRange, right: ParsedRange) -> Optional[Tuple[int, int]]:
    start = max(left.start, right.start)
    end = min(left.end, right.end)
    if start <= end:
        return start, end
    return None


def overlap_groups(ranges: List[ParsedRange]) -> List[Dict[str, object]]:
    groups: List[Dict[str, object]] = []
    sorted_ranges = sorted(
        ranges,
        key=lambda item: (item.start, item.end, item.row.origin, item.row.row_id),
    )
    for index, current in enumerate(sorted_ranges):
        for other in sorted_ranges[index + 1 :]:
            if other.start > current.end:
                break
            intersection = intersect_ranges(current, other)
            if not intersection:
                continue
            if current.row.file == other.row.file and current.row.row_id == other.row.row_id:
                continue
            overlap_start, overlap_end = intersection
            groups.append(
                {
                    "overlap_lines": [overlap_start, overlap_end],
                    "participants": [
                        {
                            "origin": item.row.origin,
                            "row_id": item.row.row_id,
                            "lines": [item.start, item.end],
                            "status": item.row.status,
                            "candidate_owner_change": item.row.candidate_owner_change,
                            "candidate_target_capability": item.row.candidate_target_capability,
                        }
                        for item in (current, other)
                    ],
                }
            )
    return groups


def resolve_source_path(workspace_root: Path, source_document: str) -> Path:
    source_path = Path(source_document)
    if source_path.is_absolute():
        return source_path
    return workspace_root / source_document


def main() -> int:
    parser = argparse.ArgumentParser(description="审计 Phase 3 source atom 的 line-range mechanics。")
    parser.add_argument("--orchestrate-dir", default="openspec/orchestrate", help="orchestrate 目录路径")
    parser.add_argument("--workspace-root", default=".", help="工作区根目录路径")
    parser.add_argument("--pretty", action="store_true", help="格式化 JSON 输出")
    parser.add_argument("--from-trace", dest="from_trace", action="store_true", default=True, help="读取 Phase 2 .atoms.json sidecar；这是默认行为。")
    parser.add_argument("--from-markdown", dest="from_trace", action="store_false", help="读取 rendered v4 Phase 2 .atoms.md file，而不是 JSON trace。")
    args = parser.parse_args()

    orchestrate_dir = Path(args.orchestrate_dir)
    workspace_root = Path(args.workspace_root)
    by_doc: Dict[str, List[ParsedRange]] = {}
    malformed: List[Dict[str, object]] = []
    range_format_warnings: List[Dict[str, object]] = []
    rows_read = 0
    files_read = 0

    atom_files = iter_source_atom_trace_files(orchestrate_dir) if args.from_trace else iter_source_atom_files(orchestrate_dir)
    for atom_file in atom_files:
        files_read += 1
        source_rows = parse_source_rows_from_trace(atom_file) if args.from_trace else parse_source_rows(atom_file)
        source_document = source_document_from_trace(atom_file) if args.from_trace else source_document_from_markdown(atom_file)
        if source_document:
            by_doc.setdefault(source_document, [])
        for row in source_rows:
            rows_read += 1
            if ";" in row.source_document:
                malformed.append({"row": asdict(row), "errors": ["同一行包含多个 source document"]})
                continue
            ranges, errors, warnings = parse_line_ranges(row)
            if warnings:
                range_format_warnings.append({"row": asdict(row), "warnings": warnings})
            if errors:
                malformed.append({"row": asdict(row), "errors": errors})
                continue
            by_doc.setdefault(row.source_document, [])
            for start, end in ranges:
                by_doc[row.source_document].append(ParsedRange(start=start, end=end, row=row))

    documents: Dict[str, object] = {}
    for source_document, parsed_ranges in sorted(by_doc.items()):
        source_path = resolve_source_path(workspace_root, source_document)
        source_exists = source_path.exists()
        line_count = len(source_path.read_text(encoding="utf-8").splitlines()) if source_exists else None
        merged = merge_ranges(parsed_ranges)
        documents[source_document] = {
            "source_exists": source_exists,
            "line_count": line_count,
            "evidence_ranges": [
                {
                    "lines": [item.start, item.end],
                    "origin": item.row.origin,
                    "row_id": item.row.row_id,
                    "status": item.row.status,
                    "candidate_owner_change": item.row.candidate_owner_change,
                    "candidate_target_capability": item.row.candidate_target_capability,
                }
                for item in sorted(parsed_ranges, key=lambda value: (value.start, value.end))
            ],
            "merged_covered_ranges": merged,
            "candidate_uncovered_ranges": uncovered_ranges(merged, line_count) if line_count is not None else [],
            "overlap_groups": overlap_groups(parsed_ranges),
        }

    result = {
        "summary": {
            "source_atom_files_read": files_read,
            "evidence_rows_read": rows_read,
            "source_documents_audited": len(documents),
            "malformed_rows": len(malformed),
            "range_format_warnings": len(range_format_warnings),
            "note": "这里只提供 mechanical candidate；作出任何 decision 前都必须执行 semantic review。",
        },
        "malformed_rows": malformed,
        "range_format_warnings": range_format_warnings,
        "documents": documents,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
