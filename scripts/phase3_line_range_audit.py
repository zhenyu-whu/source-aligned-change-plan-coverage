#!/usr/bin/env python3
"""Mechanical Phase 3 line-range helper.

This script parses Phase 2 source-first atom files, groups atom/anchor ranges by
source document, merges line ranges, and emits candidate uncovered ranges and
overlap clusters. It intentionally does not classify semantic meaning.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


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
    candidate_owner_capability: str
    roles: str


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
    rows: List[EvidenceRow] = []
    for i in range(len(lines) - 1):
        header = split_md_row(lines[i])
        separator = split_md_row(lines[i + 1])
        if not header or not separator:
            continue
        if not all(TABLE_SEPARATOR_RE.match(cell) for cell in separator):
            continue
        index = index_header(header)
        if "source document" not in index or "lines" not in index:
            continue

        has_atom_id = "source atom id" in index
        has_anchor = "anchor" in index and "source atom ids" in index
        if not has_atom_id and not has_anchor:
            continue

        origin = "atom" if has_atom_id else "anchor"
        for j in range(i + 2, len(lines)):
            cells = split_md_row(lines[j])
            if not cells:
                break
            if len(cells) < len(header):
                continue

            source_document = normalize_cell(get_cell(cells, index, "source document"))
            raw_line_spec = normalize_spacing(get_cell(cells, index, "lines"))
            line_spec = normalize_cell(raw_line_spec)
            if not source_document or not line_spec:
                continue

            if has_atom_id:
                row_id = normalize_cell(get_cell(cells, index, "source atom id"))
                source_fact = get_cell(cells, index, "source fact")
                status = get_cell(cells, index, "candidate status", "coverage status")
                owner_change = get_cell(cells, index, "candidate owner change", "owner change")
                owner_capability = get_cell(cells, index, "candidate owner capability", "owner capability")
            else:
                row_id = normalize_cell(get_cell(cells, index, "source atom ids", "atom ids", "anchor"))
                source_fact = get_cell(cells, index, "source phrase")
                status = get_cell(cells, index, "candidate status", "coverage status")
                owner_change = get_cell(cells, index, "candidate owners", "owner change")
                owner_capability = ""

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
                    candidate_owner_capability=owner_capability,
                    roles=get_cell(cells, index, "roles"),
                )
            )
    return rows


def parse_source_rows_from_trace(json_path: Path) -> List[EvidenceRow]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    rows: List[EvidenceRow] = []
    for index, raw in enumerate(data.get("source-atoms", []), start=1):
        if not isinstance(raw, dict):
            continue
        source_document = normalize_cell(str(raw.get("source-document", "")))
        line_spec = normalize_cell(str(raw.get("lines", "")))
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
                candidate_owner_capability=str(raw.get("candidate-owner-capability", "")),
                roles=str(raw.get("roles", "")),
            )
        )
    for index, raw in enumerate(data.get("source-anchors", []), start=1):
        if not isinstance(raw, dict):
            continue
        source_document = normalize_cell(str(raw.get("source-document", "")))
        line_spec = normalize_cell(str(raw.get("lines", "")))
        row_id = normalize_cell(str(raw.get("source-atom-ids", raw.get("anchor", ""))))
        if not source_document or not line_spec or not row_id:
            continue
        rows.append(
            EvidenceRow(
                origin="anchor",
                file=str(json_path),
                table_line=index,
                source_document=source_document,
                row_id=row_id,
                lines=line_spec,
                raw_lines=line_spec,
                source_fact=str(raw.get("source-phrase", "")),
                status=str(raw.get("candidate-status", "")),
                candidate_owner_change=str(raw.get("candidate-owners", raw.get("owner-change", ""))),
                candidate_owner_capability="",
                roles=str(raw.get("roles", "")),
            )
        )
    return rows


def parse_line_ranges(row: EvidenceRow) -> Tuple[List[Tuple[int, int]], List[str], List[str]]:
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
                            "candidate_owner_capability": item.row.candidate_owner_capability,
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
    parser = argparse.ArgumentParser(description="Audit Phase 3 source atom line-range mechanics.")
    parser.add_argument("--orchestrate-dir", default="openspec/orchestrate")
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--from-trace", dest="from_trace", action="store_true", default=True, help="Read Phase 2 .atoms.json sidecars. This is the default.")
    parser.add_argument("--from-markdown", dest="from_trace", action="store_false", help="Read legacy Phase 2 .atoms.md files instead of JSON trace.")
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
        for row in source_rows:
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
                    "candidate_owner_capability": item.row.candidate_owner_capability,
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
