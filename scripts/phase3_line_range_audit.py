#!/usr/bin/env python3
"""Mechanical Phase 3 line-range helper.

This script parses canonical per-change anchor tables, groups anchors by source
document, merges line ranges, and emits candidate uncovered ranges and overlap
clusters. It intentionally does not classify semantic meaning.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
CANONICAL_RANGE_SEGMENT_RE = re.compile(r"^L([1-9]\d*)-L([1-9]\d*)$")
LEGACY_RANGE_SEGMENT_RE = re.compile(r"^L?(\d+)(?:\s*-\s*L?(\d+))?$", re.IGNORECASE)


@dataclass
class AnchorRow:
    change: str
    file: str
    table_line: int
    source_document: str
    anchor: str
    lines: str
    raw_lines: str
    source_phrase: str
    coverage_status: str
    capabilities: str
    roles: str


@dataclass
class ParsedRange:
    start: int
    end: int
    row: AnchorRow


def split_md_row(line: str) -> Optional[List[str]]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def normalize_cell(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("`", "")).strip()


def normalize_spacing(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_anchor_rows(markdown_path: Path, change: str) -> List[AnchorRow]:
    lines = markdown_path.read_text(encoding="utf-8").splitlines()
    rows: List[AnchorRow] = []
    for i in range(len(lines) - 1):
        header = split_md_row(lines[i])
        separator = split_md_row(lines[i + 1])
        if not header or not separator:
            continue
        if not all(TABLE_SEPARATOR_RE.match(cell) for cell in separator):
            continue
        index = {normalize_cell(name).lower(): pos for pos, name in enumerate(header)}
        required = ["source document", "anchor", "lines"]
        if not all(name in index for name in required):
            continue
        for j in range(i + 2, len(lines)):
            cells = split_md_row(lines[j])
            if not cells:
                break
            if len(cells) < len(header):
                continue
            def cell(name: str) -> str:
                pos = index.get(name)
                return cells[pos] if pos is not None and pos < len(cells) else ""

            source_document = normalize_cell(cell("source document"))
            anchor = normalize_cell(cell("anchor"))
            raw_line_spec = normalize_spacing(cell("lines"))
            line_spec = normalize_cell(raw_line_spec)
            if not source_document or not anchor or not line_spec:
                continue
            rows.append(
                AnchorRow(
                    change=change,
                    file=str(markdown_path),
                    table_line=j + 1,
                    source_document=source_document,
                    anchor=anchor,
                    lines=line_spec,
                    raw_lines=raw_line_spec,
                    source_phrase=cell("source phrase"),
                    coverage_status=cell("coverage status"),
                    capabilities=cell("capabilities"),
                    roles=cell("roles"),
                )
            )
    return rows


def parse_line_ranges(row: AnchorRow) -> Tuple[List[Tuple[int, int]], List[str], List[str]]:
    ranges: List[Tuple[int, int]] = []
    errors: List[str] = []
    warnings: List[str] = []

    if "`" in row.raw_lines:
        warnings.append("line range should not be wrapped in markdown backticks")
    if "," in row.lines:
        warnings.append("multiple line ranges should be separated with '; ', not ','")

    parts = [part.strip() for part in re.split(r"[;,]", row.lines) if part.strip()]
    for part in parts:
        canonical_match = CANONICAL_RANGE_SEGMENT_RE.match(part)
        if canonical_match:
            start = int(canonical_match.group(1))
            end = int(canonical_match.group(2))
        else:
            warnings.append(f"non-canonical range segment: {part}; expected L<start>-L<end>")
            match = LEGACY_RANGE_SEGMENT_RE.match(part)
            if not match:
                errors.append(f"unsupported range segment: {part}")
                continue
            start = int(match.group(1))
            end = int(match.group(2) or match.group(1))
        if start > end:
            warnings.append(f"range start greater than end, normalized mechanically: {part}")
            start, end = end, start
        if start <= 0 or end <= 0:
            errors.append(f"line numbers must be positive: {part}")
            continue
        ranges.append((start, end))
    return ranges, errors, warnings


def intersect_ranges(left: ParsedRange, right: ParsedRange) -> Optional[Tuple[int, int]]:
    start = max(left.start, right.start)
    end = min(left.end, right.end)
    if start <= end:
        return start, end
    return None


def iter_canonical_change_files(orchestrate_dir: Path) -> Iterable[Tuple[str, Path]]:
    anchor_root = orchestrate_dir / "change-capability-anchors"
    if not anchor_root.exists():
        return
    for change_dir in sorted(path for path in anchor_root.iterdir() if path.is_dir()):
        change_file = change_dir / f"{change_dir.name}.md"
        if change_file.exists():
            yield change_dir.name, change_file


def merge_ranges(ranges: List[ParsedRange]) -> List[Tuple[int, int]]:
    merged: List[Tuple[int, int]] = []
    for parsed in sorted(ranges, key=lambda item: (item.start, item.end)):
        if not merged or parsed.start > merged[-1][1] + 1:
            merged.append((parsed.start, parsed.end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], parsed.end))
    return merged


def uncovered_ranges(merged: List[Tuple[int, int]], line_count: int) -> List[Tuple[int, int]]:
    uncovered: List[Tuple[int, int]] = []
    cursor = 1
    for start, end in merged:
        if cursor < start:
            uncovered.append((cursor, start - 1))
        cursor = max(cursor, end + 1)
    if cursor <= line_count:
        uncovered.append((cursor, line_count))
    return uncovered


def overlap_groups(ranges: List[ParsedRange]) -> List[Dict[str, object]]:
    groups: List[Dict[str, object]] = []
    sorted_ranges = sorted(ranges, key=lambda item: (item.start, item.end, item.row.change, item.row.anchor))
    for index, current in enumerate(sorted_ranges):
        for other in sorted_ranges[index + 1 :]:
            if other.start > current.end:
                break
            intersection = intersect_ranges(current, other)
            if not intersection or current.row.change == other.row.change:
                continue
            overlap_start, overlap_end = intersection
            participants = [current, other]
            groups.append(
                {
                    "overlap_lines": [overlap_start, overlap_end],
                    "participants": [
                        {
                            "change": item.row.change,
                            "anchor": item.row.anchor,
                            "lines": [item.start, item.end],
                            "capabilities": item.row.capabilities,
                        }
                        for item in participants
                    ],
                }
            )
    return groups


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase 3 line-range mechanics.")
    parser.add_argument("--orchestrate-dir", default="openspec/orchestrate")
    parser.add_argument("--source-root", default="docs")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    orchestrate_dir = Path(args.orchestrate_dir)
    source_root = Path(args.source_root)
    by_doc: Dict[str, List[ParsedRange]] = {}
    malformed: List[Dict[str, object]] = []
    range_format_warnings: List[Dict[str, object]] = []
    rows_read = 0

    for change, change_file in iter_canonical_change_files(orchestrate_dir):
        for row in parse_anchor_rows(change_file, change):
            rows_read += 1
            if ";" in row.source_document:
                malformed.append({"row": asdict(row), "errors": ["multiple source documents in one row"]})
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
        source_path = Path(source_document)
        if not source_path.is_absolute():
            source_path = source_root.parent / source_document
        source_exists = source_path.exists()
        line_count = len(source_path.read_text(encoding="utf-8").splitlines()) if source_exists else None
        merged = merge_ranges(parsed_ranges)
        documents[source_document] = {
            "source_exists": source_exists,
            "line_count": line_count,
            "anchor_ranges": [
                {
                    "lines": [item.start, item.end],
                    "change": item.row.change,
                    "anchor": item.row.anchor,
                    "capabilities": item.row.capabilities,
                    "coverage_status": item.row.coverage_status,
                }
                for item in sorted(parsed_ranges, key=lambda value: (value.start, value.end))
            ],
            "merged_covered_ranges": merged,
            "candidate_uncovered_ranges": uncovered_ranges(merged, line_count) if line_count is not None else [],
            "overlap_groups": overlap_groups(parsed_ranges),
        }

    result = {
        "summary": {
            "canonical_rows_read": rows_read,
            "source_documents_with_ranges": len(documents),
            "malformed_rows": len(malformed),
            "range_format_warnings": len(range_format_warnings),
            "note": "Mechanical candidates only; semantic review is required before any decision.",
        },
        "malformed_rows": malformed,
        "range_format_warnings": range_format_warnings,
        "documents": documents,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
