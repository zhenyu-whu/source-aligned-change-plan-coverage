#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""source-aligned trace sidecar 的共享 helper。

本技能需要在未安装额外 Python package 的 repository 中运行，
因此这些 helper 刻意只使用 stdlib。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


TRACE_CONTRACT_VERSION = "source-aligned-trace-v2"
MANIFEST_SCHEMA = "source-aligned-orchestrate-manifest-v1"
PHASE_TRACE_SCHEMAS = {
    "phase-1": "source-aligned-phase-1-trace-v2",
    "phase-2": "source-aligned-phase-2-trace-v2",
    "phase-3": "source-aligned-phase-3-trace-v1",
    "phase-4": "source-aligned-phase-4-trace-v1",
    "phase-5": "source-aligned-phase-5-trace-v1",
}
SOURCE_ATOMS_SCHEMA = "source-aligned-source-atoms-v3"
GLOBAL_ATOM_INDEX_SCHEMA = "source-aligned-global-atom-index-v2"
SOURCE_TO_GLOBAL_MAP_SCHEMA = "source-aligned-source-to-global-map-v3"
SOURCE_REMAINDER_REVIEW_SCHEMA = "source-aligned-source-remainder-review-v1"
SOURCE_WINDOW_INDEX_SCHEMA = "source-aligned-source-window-index-v1"
ATOM_PLAN_MAPPING_SCHEMA = "source-aligned-atom-plan-mapping-v2"
FINAL_PACKET_INDEX_SCHEMA = "source-aligned-final-packet-index-v2"
CAPABILITY_BASELINE_SCHEMA = "source-aligned-capability-baseline-v1"

GLOBAL_ATOM_ID_RE = re.compile(r"^GA-\d{4}$")
GLOBAL_ATOM_ID_FIND_RE = re.compile(r"GA-\d{4}")
TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
CANONICAL_RANGE_RE = re.compile(r"^L([1-9]\d*)-L([1-9]\d*)$")
LEGACY_RANGE_RE = re.compile(r"^L?(\d+)(?:\s*-\s*L?(\d+))?$", re.IGNORECASE)
KEBAB_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

DIRECT_PROJECTIONS = {
    "spec-requirement",
    "spec-guard",
    "design-obligation",
    "verification-obligation",
}


@dataclass
class Issue:
    severity: str
    rule_id: str
    file: str
    message: str


class IssueReporter:
    def __init__(self) -> None:
        self.issues: List[Issue] = []

    def error(self, rule_id: str, file: Path | str, message: str) -> None:
        self.issues.append(Issue("error", rule_id, str(file), message))

    def warning(self, rule_id: str, file: Path | str, message: str) -> None:
        self.issues.append(Issue("warning", rule_id, str(file), message))

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    def result(self) -> Dict[str, object]:
        return {
            "ok": self.error_count == 0,
            "error-count": self.error_count,
            "warning-count": self.warning_count,
            "issues": [asdict(issue) for issue in self.issues],
        }


def split_md_row(line: str) -> Optional[List[str]]:
    """拆分 Markdown table 行，同时保留 code span 中的竖线。"""
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


def normalize_code(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.strip()
    while len(text) >= 2 and text.startswith("`") and text.endswith("`"):
        text = text[1:-1].strip()
    return text.replace("\\|", "|").strip()


def squash(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def normalize_header(value: object) -> str:
    return normalize_code(value).lower()


def kebab_key(value: object) -> str:
    text = normalize_code(value).lower()
    text = text.replace("&", " and ")
    text = text.replace("/", " ")
    text = text.replace("?", "")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


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


def table_rows(path: Path, required_headers: Sequence[str]) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    required = {normalize_header(name) for name in required_headers}
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, rows in iter_markdown_tables(lines):
        if not required.issubset(index):
            continue
        output: List[Dict[str, str]] = []
        for cells in rows:
            row: Dict[str, str] = {}
            for name, pos in index.items():
                row[name] = cells[pos] if pos < len(cells) else ""
            output.append(row)
        return output
    return []


def all_table_rows(path: Path) -> List[Tuple[Dict[str, int], List[List[str]]]]:
    if not path.exists():
        return []
    return list(iter_markdown_tables(path.read_text(encoding="utf-8").splitlines()))


def cell(row: Dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(normalize_header(name))
        if value is not None:
            return value
    return ""


def row_to_kebab(row: Dict[str, str], code_fields: Sequence[str] = ()) -> Dict[str, object]:
    code_keys = {normalize_header(name) for name in code_fields}
    result: Dict[str, object] = {}
    for key, value in row.items():
        out_key = kebab_key(key)
        if key in code_keys:
            result[out_key] = normalize_code(value)
        else:
            result[out_key] = squash(normalize_code(value) if "`" in value and value.strip().startswith("`") else value)
    return result


def parse_line_ranges(value: object) -> Tuple[str, List[Dict[str, int]], List[str], List[str]]:
    raw = "" if value is None else str(value)
    normalized = normalize_code(raw).replace("`", "")
    warnings: List[str] = []
    errors: List[str] = []
    ranges: List[Dict[str, int]] = []

    if "`" in raw:
        warnings.append("行范围不应包含在 Markdown 反引号中")
    if "," in normalized:
        warnings.append("多个行范围应使用 '; ' 分隔，不应使用 ','")

    for part in [normalize_code(part.strip()) for part in re.split(r"[;,]", normalized) if part.strip()]:
        match = CANONICAL_RANGE_RE.match(part)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
        else:
            legacy = LEGACY_RANGE_RE.match(part)
            if not legacy:
                errors.append(f"不支持的 range segment：{part}")
                continue
            start = int(legacy.group(1))
            end = int(legacy.group(2) or legacy.group(1))
            warnings.append(f"非 canonical range segment：{part}；预期格式为 L<start>-L<end>")
        if start <= 0 or end <= 0:
            errors.append(f"行号必须为正数：{part}")
            continue
        if start > end:
            start, end = end, start
            warnings.append(f"range start 大于 end，已执行 mechanical normalization：{part}")
        ranges.append({"start": start, "end": end})

    canonical = "; ".join(f"L{item['start']}-L{item['end']}" for item in ranges)
    if not ranges and normalized:
        errors.append(f"未解析到有效行范围：{normalized}")
    return canonical, ranges, warnings, errors


def line_range_label(item: Dict[str, int]) -> str:
    return f"L{int(item['start'])}-L{int(item['end'])}"


def line_ranges_label(ranges: Sequence[Dict[str, int]]) -> str:
    return "; ".join(line_range_label(item) for item in ranges)


def merge_line_ranges(ranges: Sequence[Dict[str, int]]) -> List[Dict[str, int]]:
    merged: List[Dict[str, int]] = []
    sorted_ranges = sorted(
        (
            {"start": int(item["start"]), "end": int(item["end"])}
            for item in ranges
            if isinstance(item, dict)
            and isinstance(item.get("start"), int)
            and isinstance(item.get("end"), int)
            and int(item["start"]) > 0
            and int(item["end"]) >= int(item["start"])
        ),
        key=lambda item: (item["start"], item["end"]),
    )
    for item in sorted_ranges:
        if not merged or item["start"] > merged[-1]["end"] + 1:
            merged.append(dict(item))
        else:
            merged[-1]["end"] = max(merged[-1]["end"], item["end"])
    return merged


def uncovered_line_ranges(covered_ranges: Sequence[Dict[str, int]], line_count: int) -> List[Dict[str, int]]:
    uncovered: List[Dict[str, int]] = []
    if line_count <= 0:
        return uncovered
    cursor = 1
    for item in merge_line_ranges(covered_ranges):
        start = int(item["start"])
        end = int(item["end"])
        if cursor < start:
            uncovered.append({"start": cursor, "end": start - 1})
        cursor = max(cursor, end + 1)
    if cursor <= line_count:
        uncovered.append({"start": cursor, "end": line_count})
    return uncovered


def range_covered_by(candidate: Dict[str, int], covering_ranges: Sequence[Dict[str, int]]) -> bool:
    cursor = int(candidate["start"])
    end = int(candidate["end"])
    for item in merge_line_ranges(covering_ranges):
        start = int(item["start"])
        item_end = int(item["end"])
        if item_end < cursor:
            continue
        if start > cursor:
            return False
        cursor = max(cursor, item_end + 1)
        if cursor > end:
            return True
    return cursor > end


def extract_ga_ids(value: object) -> List[str]:
    seen: set[str] = set()
    ids: List[str] = []
    for atom_id in GLOBAL_ATOM_ID_FIND_RE.findall("" if value is None else str(value)):
        if atom_id not in seen:
            seen.add(atom_id)
            ids.append(atom_id)
    return ids


def split_id_list(value: object) -> List[str]:
    text = normalize_code(value)
    if not text or text == "None":
        return []
    parts = re.split(r"[,;\s]+", text.replace("<br>", " "))
    result: List[str] = []
    for part in parts:
        item = normalize_code(part.strip())
        if item and item != "None":
            result.append(item)
    return result


def source_atom_file_name(source_path: str) -> str:
    without_suffix = str(Path(source_path).with_suffix(""))
    return without_suffix.replace("/", "--") + ".atoms.md"


def coverage_file_name(source_path: str) -> str:
    without_suffix = str(Path(source_path).with_suffix(""))
    return without_suffix.replace("/", "--") + ".coverage.md"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} 必须包含 JSON object")
    return data


def write_json(path: Path, data: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_kebab_keys(value: object, reporter: IssueReporter, file: Path | str, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not KEBAB_CASE_RE.match(str(key)):
                reporter.error("json-kebab-case", file, f"{path}.{key} 不是 kebab-case")
            validate_kebab_keys(child, reporter, file, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_kebab_keys(child, reporter, file, f"{path}[{index}]")


def source_line_count(repo_root: Path, source_document: str) -> Optional[int]:
    path = repo_root / source_document
    if not path.exists():
        return None
    return len(path.read_text(encoding="utf-8").splitlines())


def source_text_for_ranges(repo_root: Path, source_document: str, ranges: Sequence[Dict[str, int]]) -> str:
    path = repo_root / source_document
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    chunks: List[str] = []
    for item in ranges:
        start = int(item["start"])
        end = int(item["end"])
        chunks.extend(lines[start - 1 : end])
    return "\n".join(chunks)
