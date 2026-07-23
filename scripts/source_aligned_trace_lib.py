#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""source-aligned trace sidecar 的共享 helper。

本技能需要在未安装额外 Python package 的 repository 中运行，
因此这些 helper 刻意只使用 stdlib。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


TRACE_CONTRACT_VERSION = "source-aligned-trace-v8"
MANIFEST_SCHEMA = "source-aligned-orchestrate-manifest-v4"
PHASE_TRACE_SCHEMAS = {
    "phase-1": "source-aligned-phase-1-trace-v5",
    "phase-2": "source-aligned-phase-2-trace-v6",
    "phase-3": "source-aligned-phase-3-trace-v6",
    "phase-4": "source-aligned-phase-4-trace-v6",
    "phase-5": "source-aligned-phase-5-trace-v7",
}
PHASE1_REVIEW_RESULT_SCHEMA = "source-aligned-phase-1-review-result-v1"
PHASE3_REVIEW_RESULT_SCHEMA = "source-aligned-phase-3-review-result-v1"
PHASE5_REVIEW_RESULT_SCHEMA = "source-aligned-phase-5-review-result-v1"
SOURCE_ATOMS_SCHEMA = "source-aligned-source-atoms-v6"
GLOBAL_ATOM_INDEX_SCHEMA = "source-aligned-global-atom-index-v4"
PHASE3_COVERAGE_REVIEW_SCHEMA = "source-aligned-phase-3-coverage-review-v3"
EVIDENCE_COLLECTION_INDEX_SCHEMA = "source-aligned-evidence-collection-index-v3"
INITIAL_FRAMEWORK_SCHEMA = "source-aligned-initial-framework-v1"
FRAMEWORK_REFIT_TRACE_SCHEMA = "source-aligned-framework-refit-trace-v5"
FINAL_ROADMAP_SCHEMA = "source-aligned-final-roadmap-v1"
ATOM_PLAN_MAPPING_SCHEMA = "source-aligned-atom-plan-mapping-v5"
ATOM_PLAN_MAPPING_TOP_LEVEL_FIELDS = {
    "trace-schema",
    "trace-contract-version",
    "artifact-path",
    "rows",
}
FINAL_PACKET_INDEX_SCHEMA = "source-aligned-final-packet-index-v3"
CAPABILITY_BASELINE_SCHEMA = "source-aligned-capability-baseline-v2"
FINAL_INTEGRATION_REVIEW_SCHEMA = "source-aligned-final-integration-review-v2"
FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA = (
    "source-aligned-final-integration-review-attempt-v1"
)
FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA = (
    "source-aligned-final-integration-review-attempt-result-v1"
)
FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH = (
    "trace/final-integration-review-attempt.trace.json"
)
FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH = (
    "trace/final-integration-review-attempt-result.trace.json"
)
WORKFLOW_COMPLETION_SCHEMA = "source-aligned-workflow-completion-v1"

SHARED_SEMANTIC_REFERENCES = (
    "references/change-capability-framework-principles.md",
    "references/cross-phase-contract.md",
)
WRITER_REFERENCE_ALLOWLISTS = {
    "phase-1": (
        *SHARED_SEMANTIC_REFERENCES,
        "references/phase-1-initial-change-plan.md",
    ),
    "phase-2": (
        *SHARED_SEMANTIC_REFERENCES,
        "references/phase-2-source-anchor-coverage.md",
    ),
    "phase-3": (
        *SHARED_SEMANTIC_REFERENCES,
        "references/phase-3-coverage-review-iteration.md",
    ),
    "phase-4": (
        "references/cross-phase-contract.md",
        "references/phase-4-frozen-evidence-collections.md",
    ),
    "phase-5": (
        *SHARED_SEMANTIC_REFERENCES,
        "references/phase-5-framework-refit-and-mapping.md",
    ),
}
REVIEWER_REFERENCE_ALLOWLISTS = {
    "phase-1": (
        *WRITER_REFERENCE_ALLOWLISTS["phase-1"],
        "references/review-gates.md",
    ),
    "phase-3": (
        *SHARED_SEMANTIC_REFERENCES,
        "references/phase-2-source-anchor-coverage.md",
        "references/phase-3-coverage-review-iteration.md",
        "references/review-gates.md",
    ),
    "phase-5": (
        *WRITER_REFERENCE_ALLOWLISTS["phase-5"],
        "references/review-gates.md",
    ),
}
REPAIR_REFERENCE_ALLOWLISTS = {
    "phase-1": (
        *WRITER_REFERENCE_ALLOWLISTS["phase-1"],
        "references/bounded-repair-contract.md",
    ),
    "phase-3": (
        *SHARED_SEMANTIC_REFERENCES,
        "references/phase-2-source-anchor-coverage.md",
        "references/phase-3-coverage-review-iteration.md",
        "references/bounded-repair-contract.md",
    ),
    "phase-5": (
        *WRITER_REFERENCE_ALLOWLISTS["phase-5"],
        "references/bounded-repair-contract.md",
    ),
}

DELIVERY_DIRECTIVES = (
    "explicit-deferred",
    "explicit-precedence",
    "milestone-scope",
)
CAPABILITY_GATE_NAMES = (
    "domain-basis",
    "purpose",
    "behavior-first",
    "cohesion",
    "owns-excludes",
    "implementation-substitution",
    "archive-durability",
    "delta-feasibility",
)
CHANGE_GATE_NAMES = (
    "one-intent",
    "scope-cohesion",
    "independent-decision-archive",
    "indivisibility",
    "acceptance",
    "implementation-readiness",
    "prefix-utility",
    "consumer-closure",
)
ROADMAP_GATE_NAMES = (
    "delivery-directive-resolution",
    "dependency-edge-soundness",
    "dependency-set-completeness",
    "prefix-viability",
    "guard-co-delivery",
    "foundation-like-content",
    "order-selection",
)
PHASE1_REVIEW_CHECKS = (
    "capability-change-independence",
    "source-delivery-semantics",
    "prefix-utility",
    "consumer-closure",
    "dependency-edge-soundness",
    "dependency-set-completeness",
    "guard-co-delivery",
    "foundation-like-content",
    "order-selection",
    "overlay-directness",
)
PHASE5_REVIEW_CHECKS = (
    "final-capability-gates",
    "final-change-gates",
    "delivery-directive-resolution",
    "dependency-edge-soundness",
    "dependency-set-completeness",
    "prefix-viability",
    "guard-co-delivery",
    "foundation-like-content",
    "order-selection",
    "mapping-overlay-consistency",
)
PHASE3_REVIEW_CHECKS = (
    "source-range-coverage",
    "production-obligation-completeness",
    "delivery-directive-completeness",
    "delivery-directive-source-basis",
    "architecture-directive-separation",
    "evidence-quote-range-integrity",
    "terminal-mapping-tuple-losslessness",
    "semantic-dedup-prohibition",
    "mapping-ambiguity-discipline",
    "source-conflict-closure",
)
PHASE5_CANDIDATE_DIGEST_FIELDS = (
    "framework-refit-sha256",
    "final-roadmap-sha256",
    "atom-plan-mapping-sha256",
    "final-change-plan-sha256",
    "frozen-evidence-authority-sha256",
    "phase-3-freeze-trace-sha256",
    "candidate-handoff-sha256",
)
MAX_BOUNDED_REVIEWS = 5
MAX_BOUNDED_REPAIRS = 4
REVIEW_DECISIONS = ("passed", "repair-required", "blocked")
REVIEW_GATE_TERMINAL_REASONS = (
    "none",
    "review-blocked",
    "budget-exhausted",
    "no-op-repair",
    "identity-reuse",
    "authority-integrity",
)
DEPENDENCY_KINDS = (
    "behavior-availability",
    "compatibility-contract",
    "lifecycle-state",
    "safety-invariant",
)
CONSUMER_MODES = (
    "existing-baseline",
    "foundation-first-outcome",
    "same-change-outcome",
)

GLOBAL_ATOM_ID_RE = re.compile(r"^GA-\d{4}$")
GLOBAL_ATOM_ID_FIND_RE = re.compile(r"GA-\d{4}")
TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
CANONICAL_RANGE_RE = re.compile(r"^L([1-9]\d*)-L([1-9]\d*)$")
LEGACY_RANGE_RE = re.compile(r"^L?(\d+)(?:\s*-\s*L?(\d+))?$", re.IGNORECASE)
KEBAB_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
FORBIDDEN_CHANGE_CLASSIFICATION_KEYS = {
    "changekind",
    "changetype",
    "change类型",
    "specmode",
}

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


def canonical_json_sha256(value: object) -> str:
    """Return the workflow's deterministic digest for a JSON-compatible value."""
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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


def normalize_markdown_field_label(value: object) -> str:
    """Normalize a Markdown field/header label for reserved-field checks."""
    text = normalize_code(value).lower()
    return re.sub(r"[\s_\-*`]+", "", text)


def forbidden_change_classification_fields(text: str) -> List[str]:
    """Return forbidden Change classification labels used as fields or table headers."""
    findings: List[str] = []
    lines = text.splitlines()
    for line in lines:
        match = re.match(r"^\s*-\s*(.+?)[：:]", line)
        if match:
            label = normalize_markdown_field_label(match.group(1))
            if label in FORBIDDEN_CHANGE_CLASSIFICATION_KEYS:
                findings.append(match.group(1).strip())
    for index in range(len(lines) - 1):
        header = split_md_row(lines[index])
        separator = split_md_row(lines[index + 1])
        if not header or not separator or not all(
            TABLE_SEPARATOR_RE.match(cell.strip()) for cell in separator
        ):
            continue
        for cell_value in header:
            if normalize_markdown_field_label(cell_value) in FORBIDDEN_CHANGE_CLASSIFICATION_KEYS:
                findings.append(normalize_code(cell_value))
    return findings


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


def repo_relative_path(path: Path, repo_root: Path) -> str:
    """Serialize a canonical path relative to the workspace/repository root."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"canonical path不在repository root内：{path}") from exc


def lexical_repo_relative_path(path: Path, repo_root: Path) -> str:
    """Serialize a normalized lexical path without following symlinks."""
    absolute_path = Path(os.path.abspath(path))
    absolute_root = Path(os.path.abspath(repo_root))
    try:
        return absolute_path.relative_to(absolute_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"lexical path不在repository root内：{path}") from exc


def first_symlink_in_repo_path(path: Path, repo_root: Path) -> Optional[Path]:
    """Return the first symlink from repo root to path, without following it."""
    relative = Path(lexical_repo_relative_path(path, repo_root))
    current = Path(os.path.abspath(repo_root))
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return current
    return None


def require_no_symlink_in_repo_path(path: Path, repo_root: Path, where: str) -> None:
    symlink = first_symlink_in_repo_path(path, repo_root)
    if symlink is not None:
        raise ValueError(f"{where}路径链不得包含symlink：{symlink}")


def atom_plan_mapping_markdown_path(json_path: Path, repo_root: Path) -> str:
    """Return the canonical Markdown mirror path declared by mapping v5."""
    return repo_relative_path(json_path.with_suffix(".md"), repo_root)


def require_atom_plan_mapping_envelope(
    data: Dict[str, object],
    json_path: Path,
    repo_root: Path,
) -> None:
    """Reject a mapping v5 envelope that cannot identify its Markdown mirror."""
    actual_fields = set(data)
    if actual_fields != ATOM_PLAN_MAPPING_TOP_LEVEL_FIELDS:
        missing = sorted(ATOM_PLAN_MAPPING_TOP_LEVEL_FIELDS - actual_fields)
        extra = sorted(actual_fields - ATOM_PLAN_MAPPING_TOP_LEVEL_FIELDS)
        raise ValueError(
            "atom-plan-mapping v5顶层字段非法；"
            f"missing={missing}，extra={extra}"
        )
    if data.get("trace-schema") != ATOM_PLAN_MAPPING_SCHEMA:
        raise ValueError(
            f"atom-plan-mapping trace-schema必须是{ATOM_PLAN_MAPPING_SCHEMA}"
        )
    if data.get("trace-contract-version") != TRACE_CONTRACT_VERSION:
        raise ValueError(
            "atom-plan-mapping trace-contract-version必须是"
            f"{TRACE_CONTRACT_VERSION}"
        )
    expected_path = atom_plan_mapping_markdown_path(json_path, repo_root)
    if data.get("artifact-path") != expected_path:
        raise ValueError(
            "atom-plan-mapping artifact-path必须指向Markdown mirror："
            f"{expected_path}"
        )


def evidence_authority_payload(
    orchestrate_dir: Path,
    repo_root: Path,
    *,
    include_phase3: bool = True,
) -> Dict[str, object]:
    """Build the normalized Phase 2/3 evidence authority digest payload.

    Reports, Markdown mirrors, and phase traces are deliberately excluded.  The
    digest binds the source bytes, every canonical Phase 2 atom JSON document,
    and the two canonical Phase 3 semantic authorities.
    """
    phase1_trace_path = orchestrate_dir / "trace/phase-1.trace.json"
    phase1_trace = read_json(phase1_trace_path)
    source_documents = phase1_trace.get("source-documents")
    if not isinstance(source_documents, list):
        raise ValueError(f"{phase1_trace_path} source-documents必须是array")

    source_rows: List[Dict[str, str]] = []
    seen_source_documents: set[str] = set()
    for item in source_documents:
        if not isinstance(item, dict):
            raise ValueError(f"{phase1_trace_path} source-documents[]必须是object")
        source_document = normalize_code(item.get("source-document"))
        if not source_document:
            raise ValueError(f"{phase1_trace_path} source-document不得为空")
        source_path = repo_root / source_document
        canonical_source_document = lexical_repo_relative_path(
            source_path,
            repo_root,
        )
        if (
            canonical_source_document != source_document
            or source_document in seen_source_documents
        ):
            raise ValueError(
                f"{phase1_trace_path} source-document非法或重复："
                f"{source_document}"
            )
        seen_source_documents.add(source_document)
        require_no_symlink_in_repo_path(
            source_path,
            repo_root,
            f"source document {source_document}",
        )
        if not source_path.is_file():
            raise ValueError(f"source document不存在或不是普通文件：{source_document}")
        recorded_digest = normalize_code(
            item.get("sha256") or item.get("source-sha256")
        )
        if not re.fullmatch(r"[0-9a-f]{64}", recorded_digest):
            raise ValueError(f"{phase1_trace_path} {source_document} source digest非法")
        actual_digest = sha256_file(source_path)
        if recorded_digest != actual_digest:
            raise ValueError(
                f"{phase1_trace_path} {source_document} source digest已漂移"
            )
        source_rows.append({
            "source-document": canonical_source_document,
            "sha256": actual_digest,
        })
    source_rows.sort(key=lambda row: row["source-document"])

    atom_root = orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    atom_rows = [
        {
            "json-path": repo_relative_path(path, repo_root),
            "sha256": sha256_file(path),
        }
        for path in sorted(atom_root.glob("*.atoms.json"))
    ]
    payload: Dict[str, object] = {
        "source-documents": source_rows,
        "source-atoms": atom_rows,
    }
    if include_phase3:
        global_index_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
        coverage_review_path = orchestrate_dir / "phase-works/phase-3/coverage-review.json"
        payload.update({
            "global-index": {
                "json-path": repo_relative_path(global_index_path, repo_root),
                "sha256": sha256_file(global_index_path),
            },
            "coverage-review": {
                "json-path": repo_relative_path(coverage_review_path, repo_root),
                "sha256": sha256_file(coverage_review_path),
            },
        })
    else:
        payload.update({"global-index": None, "coverage-review": None})
    return payload


def evidence_authority_sha256(
    orchestrate_dir: Path,
    repo_root: Path,
    *,
    include_phase3: bool = True,
) -> str:
    """Return the canonical Phase 2/3 evidence authority digest."""
    return canonical_json_sha256(
        evidence_authority_payload(orchestrate_dir, repo_root, include_phase3=include_phase3)
    )


def require_phase3_frozen_evidence(
    orchestrate_dir: Path,
    repo_root: Path,
) -> Dict[str, str]:
    """Require the terminal Phase 3 freeze marker and return its bound digests.

    Phase 5 deliberately does not consume Phase 4 collection membership.  Its
    only admissible source authority is therefore the Phase 2/3 evidence set
    committed by a terminal, independently reviewed Phase 3 trace.  This
    helper performs the fail-closed check needed by every Phase 5 entry point.
    The local validator import is intentionally deferred until call time: this
    module is a dependency of the validator, while Phase 5 must still reuse the
    exact Phase 1/2/3 canonical checks rather than maintain a weaker duplicate.
    """

    phase1_trace_path = orchestrate_dir / "trace/phase-1.trace.json"
    phase3_trace_path = orchestrate_dir / "trace/phase-3.trace.json"
    require_no_symlink_in_repo_path(
        phase1_trace_path,
        repo_root,
        "Phase 1 trace",
    )
    require_no_symlink_in_repo_path(
        phase3_trace_path,
        repo_root,
        "Phase 3 freeze trace",
    )
    phase1_trace = read_json(phase1_trace_path)
    expected_phase1_fields = {
        "trace-schema",
        "trace-contract-version",
        "status",
        "source-documents",
        "initial-framework",
        "initial-change-plan",
        "review-gate",
    }
    if set(phase1_trace) != expected_phase1_fields:
        raise ValueError("terminal Phase 1 trace字段不符合v8契约")
    if (
        phase1_trace.get("trace-schema") != PHASE_TRACE_SCHEMAS["phase-1"]
        or phase1_trace.get("trace-contract-version") != TRACE_CONTRACT_VERSION
        or normalize_code(phase1_trace.get("status"))
        != "initial-plan-written"
    ):
        raise ValueError(
            "Phase 5要求terminal Phase 1："
            "status=initial-plan-written且使用当前trace contract"
        )
    phase1_gate = phase1_trace.get("review-gate")
    if (
        not isinstance(phase1_gate, dict)
        or set(phase1_gate)
        != {
            "status",
            "terminal-reason",
            "writer-id",
            "reviews",
            "repairs",
        }
        or normalize_code(phase1_gate.get("status")) != "passed"
        or normalize_code(phase1_gate.get("terminal-reason")) != "none"
        or not phase1_gate.get("reviews")
    ):
        raise ValueError(
            "Phase 5要求canonical Phase 1 passed review-gate"
        )
    for field, path in (
        (
            "initial-framework",
            orchestrate_dir / "phase-works/phase-1/initial-framework.json",
        ),
        (
            "initial-change-plan",
            orchestrate_dir / "phase-works/phase-1/initial-change-plan.md",
        ),
    ):
        ref = phase1_trace.get(field)
        if (
            not isinstance(ref, dict)
            or set(ref) != {"artifact-path", "sha256"}
            or ref.get("artifact-path")
            != lexical_repo_relative_path(path, repo_root)
            or not path.is_file()
            or ref.get("sha256") != sha256_file(path)
        ):
            raise ValueError(f"Phase 1 {field} authority drift")

    phase2_trace_path = orchestrate_dir / "trace/phase-2.trace.json"
    require_no_symlink_in_repo_path(
        phase2_trace_path,
        repo_root,
        "Phase 2 trace",
    )
    phase2_trace = read_json(phase2_trace_path)
    expected_phase2_fields = {
        "trace-schema",
        "trace-contract-version",
        "status",
        "work-queue-path",
        "sources",
        "phase-report-path",
    }
    if (
        set(phase2_trace) != expected_phase2_fields
        or phase2_trace.get("trace-schema")
        != PHASE_TRACE_SCHEMAS["phase-2"]
        or phase2_trace.get("trace-contract-version")
        != TRACE_CONTRACT_VERSION
        or normalize_code(phase2_trace.get("status"))
        != "source-atoms-written"
    ):
        raise ValueError(
            "Phase 5要求canonical source-atoms-written Phase 2 trace"
        )
    phase2_sources = phase2_trace.get("sources")
    if not isinstance(phase2_sources, list) or not phase2_sources:
        raise ValueError("Phase 2 trace.sources必须是非空array")
    phase2_by_source: Dict[str, Dict[str, object]] = {}
    expected_phase2_source_fields = {
        "source-document",
        "atom-json-path",
        "atom-json-sha256",
        "atom-markdown-path",
        "canonical-owner",
        "read-status",
        "atom-count",
        "delivery-directive-atom-count",
        "blockers",
    }
    for row in phase2_sources:
        if (
            not isinstance(row, dict)
            or set(row) != expected_phase2_source_fields
        ):
            raise ValueError("Phase 2 trace source row字段非法")
        source_document = normalize_code(row.get("source-document"))
        if not source_document or source_document in phase2_by_source:
            raise ValueError("Phase 2 trace source重复或为空")
        phase2_by_source[source_document] = row

    atom_root = (
        orchestrate_dir / "phase-works/phase-2/source-obligation-atoms"
    )
    require_no_symlink_in_repo_path(
        atom_root,
        repo_root,
        "Phase 2 atom authority root",
    )
    if not atom_root.is_dir():
        raise ValueError("Phase 2 atom authority root必须是directory")
    phase2_owner_ids: List[str] = []
    atom_sources: set[str] = set()
    expected_atom_top_fields = {
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
    expected_atom_fields = {
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
    for atom_path in sorted(atom_root.glob("*.atoms.json")):
        require_no_symlink_in_repo_path(
            atom_path,
            repo_root,
            "Phase 2 atom authority",
        )
        atom_data = read_json(atom_path)
        if (
            set(atom_data) != expected_atom_top_fields
            or atom_data.get("trace-schema") != SOURCE_ATOMS_SCHEMA
            or atom_data.get("trace-contract-version")
            != TRACE_CONTRACT_VERSION
        ):
            raise ValueError(f"Phase 2 atom envelope非法：{atom_path}")
        source_document = normalize_code(atom_data.get("source-document"))
        source_path = repo_root / source_document
        owner = squash(atom_data.get("canonical-owner"))
        atoms = atom_data.get("source-atoms")
        if (
            not source_document
            or source_document in atom_sources
            or not owner
            or not source_path.is_file()
            or atom_data.get("source-sha256") != sha256_file(source_path)
            or not isinstance(atoms, list)
            or not atoms
            or any(
                not isinstance(atom, dict)
                or set(atom) != expected_atom_fields
                for atom in atoms
            )
        ):
            raise ValueError(
                f"Phase 2 atom source/owner/rows非法：{atom_path}"
            )
        atom_sources.add(source_document)
        if owner not in phase2_owner_ids:
            phase2_owner_ids.append(owner)
        trace_row = phase2_by_source.get(source_document)
        directive_count = sum(
            1
            for atom in atoms
            if isinstance(atom.get("delivery-directives"), list)
            and atom.get("delivery-directives")
        )
        if (
            trace_row is None
            or trace_row.get("atom-json-path")
            != lexical_repo_relative_path(atom_path, repo_root)
            or trace_row.get("atom-json-sha256") != sha256_file(atom_path)
            or trace_row.get("canonical-owner") != owner
            or trace_row.get("atom-count") != len(atoms)
            or trace_row.get("delivery-directive-atom-count")
            != directive_count
        ):
            raise ValueError(
                f"Phase 2 trace未绑定当前atom authority：{source_document}"
            )
    if atom_sources != set(phase2_by_source):
        raise ValueError("Phase 2 trace sources与atom authorities不一致")

    phase3_trace = read_json(phase3_trace_path)
    expected_phase3_fields = {
        "trace-schema",
        "trace-contract-version",
        "decision",
        "global-atom-index-path",
        "global-atom-index-sha256",
        "coverage-review-path",
        "coverage-review-sha256",
        "review-gate",
        "issues",
    }
    if set(phase3_trace) != expected_phase3_fields:
        missing = sorted(expected_phase3_fields - set(phase3_trace))
        extra = sorted(set(phase3_trace) - expected_phase3_fields)
        raise ValueError(
            "terminal Phase 3 trace字段非法；"
            f"missing={missing}，extra={extra}"
        )
    if (
        phase3_trace.get("trace-schema") != PHASE_TRACE_SCHEMAS["phase-3"]
        or phase3_trace.get("trace-contract-version")
        != TRACE_CONTRACT_VERSION
        or normalize_code(phase3_trace.get("decision"))
        != "coverage-complete"
    ):
        raise ValueError(
            "Phase 5只接受coverage-complete的当前v8 Phase 3 freeze"
        )
    if phase3_trace.get("issues") != []:
        raise ValueError("coverage-complete Phase 3 trace要求issues=[]")

    global_index_path = (
        orchestrate_dir
        / "change-capability-anchors/obligation-atom-index.json"
    )
    coverage_review_path = (
        orchestrate_dir / "phase-works/phase-3/coverage-review.json"
    )
    for label, path, path_field, digest_field in (
        (
            "global atom index",
            global_index_path,
            "global-atom-index-path",
            "global-atom-index-sha256",
        ),
        (
            "coverage review",
            coverage_review_path,
            "coverage-review-path",
            "coverage-review-sha256",
        ),
    ):
        require_no_symlink_in_repo_path(path, repo_root, label)
        if (
            phase3_trace.get(path_field)
            != lexical_repo_relative_path(path, repo_root)
        ):
            raise ValueError(f"Phase 3 {label} path drift")
        if (
            not path.is_file()
            or phase3_trace.get(digest_field) != sha256_file(path)
        ):
            raise ValueError(f"Phase 3 {label} digest drift")

    coverage_review = read_json(coverage_review_path)
    if (
        set(coverage_review)
        != {
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
        }
        or coverage_review.get("artifact-path")
        != lexical_repo_relative_path(
            coverage_review_path.with_suffix(".md"),
            repo_root,
        )
        or coverage_review.get("trace-schema")
        != PHASE3_COVERAGE_REVIEW_SCHEMA
        or coverage_review.get("trace-contract-version")
        != TRACE_CONTRACT_VERSION
        or normalize_code(coverage_review.get("decision"))
        != "coverage-complete"
    ):
        raise ValueError(
            "Phase 3 coverage review必须是coverage-complete的当前v8 authority"
        )

    gate = phase3_trace.get("review-gate")
    if (
        not isinstance(gate, dict)
        or set(gate)
        != {
            "status",
            "terminal-reason",
            "phase-2-canonical-owner-ids",
            "phase-2-aggregate-writer-id",
            "phase-3-writer-id",
            "reviews",
            "repairs",
        }
        or normalize_code(gate.get("status")) != "passed"
        or normalize_code(gate.get("terminal-reason")) != "none"
    ):
        raise ValueError("Phase 5要求canonical Phase 3 passed review-gate")
    owner_ids = gate.get("phase-2-canonical-owner-ids")
    aggregate_writer = squash(gate.get("phase-2-aggregate-writer-id"))
    phase3_writer = squash(gate.get("phase-3-writer-id"))
    if (
        owner_ids != phase2_owner_ids
        or not aggregate_writer
        or not phase3_writer
        or len(set(phase2_owner_ids + [aggregate_writer, phase3_writer]))
        != len(phase2_owner_ids) + 2
    ):
        raise ValueError("Phase 3 producer identities或Phase 2 owners漂移")
    reviews = gate.get("reviews")
    repairs = gate.get("repairs")
    if (
        not isinstance(reviews, list)
        or not reviews
        or not isinstance(repairs, list)
        or len(repairs) != len(reviews) - 1
        or not isinstance(reviews[-1], dict)
    ):
        raise ValueError("Phase 3 passed review history不完整")
    expected_review_fields = {
        "round",
        "review-result-path",
        "review-result-sha256",
    }
    if any(
        not isinstance(review, dict)
        or set(review) != expected_review_fields
        or review.get("round") != index
        for index, review in enumerate(reviews, start=1)
    ):
        raise ValueError("Phase 3 review history字段或round非法")
    review_results: List[Dict[str, object]] = []
    for index, review in enumerate(reviews, start=1):
        review_path = bounded_review_result_path(
            orchestrate_dir,
            "phase-3",
            index,
        )
        if (
            review.get("review-result-path")
            != lexical_repo_relative_path(review_path, repo_root)
            or review.get("review-result-sha256") != sha256_file(review_path)
        ):
            raise ValueError("Phase 3 review result path或digest漂移")
        review_results.append(
            load_bounded_review_result(
                review_path,
                "phase-3",
                expected_round=index,
            )
        )
    reviewer_ids = [
        squash(review.get("reviewer-id"))
        for review in review_results
    ]
    if (
        any(not reviewer for reviewer in reviewer_ids)
        or len(reviewer_ids) != len(set(reviewer_ids))
        or set(reviewer_ids).intersection(
            set(phase2_owner_ids + [aggregate_writer, phase3_writer])
        )
    ):
        raise ValueError("Phase 3 reviewer identity不独立")
    if (
        review_results[-1].get("decision") != "passed"
        or review_results[-1].get("evidence-authority-sha256")
        != evidence_authority_sha256(orchestrate_dir, repo_root)
    ):
        raise ValueError(
            "Phase 3 terminal review必须完成双validator与directive audit，"
            "且不得保留finding"
        )

    # Reuse the canonical validators after the compact authority checks above.
    # The deferred import avoids a module-import cycle while ensuring Phase 5
    # cannot accept a digest-consistent but structurally forged Phase 1/2/3
    # generation (missing mirrors, incomplete coverage, dangling GA refs, etc).
    from validate_source_aligned_orchestrate import (  # noqa: PLC0415
        validate_phase_1,
        validate_phase_2,
        validate_phase_3,
    )

    canonical_reporter = IssueReporter()
    validate_phase_1(orchestrate_dir, repo_root, canonical_reporter)
    validate_phase_2(orchestrate_dir, repo_root, canonical_reporter)
    validate_phase_3(orchestrate_dir, repo_root, canonical_reporter)
    if canonical_reporter.error_count:
        error_rows = [
            f"{issue.rule_id}: {issue.message}"
            for issue in canonical_reporter.issues
            if issue.severity == "error"
        ]
        details = "；".join(error_rows[:8])
        if len(error_rows) > 8:
            details += f"；其余{len(error_rows) - 8}项"
        raise ValueError(
            "Phase 1/2/3 frozen evidence未通过canonical validator："
            + details
        )

    evidence_digest = evidence_authority_sha256(
        orchestrate_dir,
        repo_root,
    )
    if (
        normalize_code(
            review_results[-1].get("evidence-authority-sha256")
        )
        != evidence_digest
    ):
        raise ValueError(
            "Phase 3 terminal review未绑定当前frozen evidence authority"
        )
    return {
        "frozen-evidence-authority-sha256": evidence_digest,
        "phase-3-freeze-trace-sha256": sha256_file(phase3_trace_path),
    }


def bounded_review_result_path(
    orchestrate_dir: Path,
    phase: str,
    round_number: int,
) -> Path:
    if phase not in {"phase-1", "phase-3", "phase-5"}:
        raise ValueError(f"不支持的bounded review phase：{phase}")
    if round_number < 1 or round_number > MAX_BOUNDED_REVIEWS:
        raise ValueError(f"bounded review round非法：{round_number}")
    return (
        orchestrate_dir
        / f"phase-works/{phase}/reviews/review-round-{round_number:02d}.json"
    )


def write_bounded_review_result_exclusive(
    orchestrate_dir: Path,
    repo_root: Path,
    phase: str,
    round_number: int,
    payload: Dict[str, object],
) -> Dict[str, object]:
    """Exclusive-create one canonical review result and return its trace ref.

    Invalid bytes intentionally remain present and make the generation fail
    closed; a caller must never delete or overwrite a submitted round.
    """
    path = bounded_review_result_path(
        orchestrate_dir,
        phase,
        round_number,
    )
    lexical_repo_relative_path(path, repo_root)
    require_no_symlink_in_repo_path(
        path.parent,
        repo_root,
        f"{phase} review result parent",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o644,
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    load_bounded_review_result(
        path,
        phase,
        expected_round=round_number,
    )
    return {
        "round": round_number,
        "review-result-path": repo_relative_path(path, repo_root),
        "review-result-sha256": sha256_file(path),
    }


def load_bounded_review_result(
    path: Path,
    phase: str,
    *,
    expected_round: Optional[int] = None,
) -> Dict[str, object]:
    schemas = {
        "phase-1": PHASE1_REVIEW_RESULT_SCHEMA,
        "phase-3": PHASE3_REVIEW_RESULT_SCHEMA,
        "phase-5": PHASE5_REVIEW_RESULT_SCHEMA,
    }
    checks_by_phase = {
        "phase-1": PHASE1_REVIEW_CHECKS,
        "phase-3": PHASE3_REVIEW_CHECKS,
        "phase-5": PHASE5_REVIEW_CHECKS,
    }
    common_fields = {
        "trace-schema",
        "trace-contract-version",
        "phase",
        "round",
        "reviewer-id",
        "semantic-checks",
        "findings",
        "warnings",
        "finding-count",
        "decision",
        "language-self-check",
    }
    phase_fields = {
        "phase-1": {
            "validator-status",
            "initial-framework-sha256",
            "initial-change-plan-sha256",
        },
        "phase-3": {
            "stage",
            "phase-2-validator-status",
            "phase-3-validator-status",
            "delivery-directive-status",
            "evidence-authority-sha256",
        },
        "phase-5": {
            "validator-status",
            *PHASE5_CANDIDATE_DIGEST_FIELDS,
        },
    }
    if phase not in schemas:
        raise ValueError(f"不支持的bounded review phase：{phase}")
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"bounded review result必须是普通文件：{path}")
    data = read_json(path)
    expected_fields = common_fields | phase_fields[phase]
    if set(data) != expected_fields:
        raise ValueError(
            f"{phase} review result字段非法；"
            f"缺少={sorted(expected_fields-set(data))}，"
            f"多余={sorted(set(data)-expected_fields)}"
        )
    if data.get("trace-schema") != schemas[phase]:
        raise ValueError(f"{phase} review result schema非法")
    if data.get("trace-contract-version") != TRACE_CONTRACT_VERSION:
        raise ValueError(f"{phase} review result trace contract非法")
    if data.get("phase") != phase:
        raise ValueError(f"{phase} review result phase非法")
    round_number = data.get("round")
    if (
        not isinstance(round_number, int)
        or round_number < 1
        or round_number > MAX_BOUNDED_REVIEWS
        or (
            expected_round is not None
            and round_number != expected_round
        )
    ):
        raise ValueError(f"{phase} review result round非法")
    if path != bounded_review_result_path(
        path.parents[3],
        phase,
        round_number,
    ):
        raise ValueError(f"{phase} review result path非法：{path}")
    if not squash(data.get("reviewer-id")):
        raise ValueError(f"{phase} reviewer-id不得为空")

    semantic_checks = data.get("semantic-checks")
    expected_checks = checks_by_phase[phase]
    if not isinstance(semantic_checks, list) or len(semantic_checks) != len(
        expected_checks
    ):
        raise ValueError(f"{phase} semantic-checks数量非法")
    actual_checks: List[str] = []
    for index, row in enumerate(semantic_checks):
        if not isinstance(row, dict) or set(row) != {"check", "result"}:
            raise ValueError(f"{phase} semantic-checks[{index}]字段非法")
        actual_checks.append(normalize_code(row.get("check")))
        if row.get("result") not in {"passed", "failed"}:
            raise ValueError(f"{phase} semantic-checks[{index}].result非法")
    if tuple(actual_checks) != expected_checks:
        raise ValueError(f"{phase} semantic-checks顺序非法")

    findings = data.get("findings")
    if not isinstance(findings, list):
        raise ValueError(f"{phase} findings必须是array")
    for index, row in enumerate(findings):
        if not isinstance(row, dict) or set(row) != {
            "rule",
            "subject",
            "finding",
        }:
            raise ValueError(f"{phase} findings[{index}]字段非法")
        if (
            not squash(row.get("rule"))
            or not squash(row.get("subject"))
            or not re.search(r"[\u4e00-\u9fff]", squash(row.get("finding")))
        ):
            raise ValueError(f"{phase} findings[{index}]必须完整且使用中文说明")
    if data.get("finding-count") != len(findings):
        raise ValueError(f"{phase} finding-count与findings数量不一致")
    warnings = data.get("warnings")
    if (
        not isinstance(warnings, list)
        or any(
            not isinstance(item, str)
            or not item.strip()
            or not re.search(r"[\u4e00-\u9fff]", item)
            for item in warnings
        )
    ):
        raise ValueError(f"{phase} warnings必须是中文string array")
    if not re.search(
        r"[\u4e00-\u9fff]",
        squash(data.get("language-self-check")),
    ):
        raise ValueError(f"{phase} language-self-check必须使用中文")

    def sha(field: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", str(data.get(field, ""))):
            raise ValueError(f"{phase} {field}非法")

    if phase == "phase-1":
        if data.get("validator-status") not in {"passed", "failed"}:
            raise ValueError("Phase 1 validator-status非法")
        sha("initial-framework-sha256")
        sha("initial-change-plan-sha256")
        validators_passed = data.get("validator-status") == "passed"
    elif phase == "phase-3":
        if data.get("stage") not in {"phase-2-preflight", "phase-3-closure"}:
            raise ValueError("Phase 3 review stage非法")
        if data.get("phase-2-validator-status") not in {"passed", "failed"}:
            raise ValueError("Phase 2 validator status非法")
        if data.get("phase-3-validator-status") not in {
            "passed",
            "failed",
            "not-run",
        }:
            raise ValueError("Phase 3 validator status非法")
        if data.get("delivery-directive-status") not in {"passed", "failed"}:
            raise ValueError("delivery-directive-status非法")
        if (
            data.get("stage") == "phase-2-preflight"
            and data.get("phase-3-validator-status") != "not-run"
        ):
            raise ValueError("Phase 2 preflight要求Phase 3 validator not-run")
        if (
            data.get("stage") == "phase-3-closure"
            and data.get("phase-3-validator-status") == "not-run"
        ):
            raise ValueError("Phase 3 closure不得使用validator not-run")
        sha("evidence-authority-sha256")
        validators_passed = (
            data.get("stage") == "phase-3-closure"
            and data.get("phase-2-validator-status") == "passed"
            and data.get("phase-3-validator-status") == "passed"
            and data.get("delivery-directive-status") == "passed"
        )
    else:
        if data.get("validator-status") not in {"passed", "failed"}:
            raise ValueError("Phase 5 validator-status非法")
        for field in PHASE5_CANDIDATE_DIGEST_FIELDS:
            sha(field)
        validators_passed = data.get("validator-status") == "passed"

    decision = data.get("decision")
    if decision not in REVIEW_DECISIONS:
        raise ValueError(f"{phase} review decision非法")
    checks_passed = all(
        isinstance(row, dict) and row.get("result") == "passed"
        for row in semantic_checks
    )
    if decision == "passed":
        if findings or not checks_passed or not validators_passed:
            raise ValueError(
                f"{phase} passed要求validator/check全部通过且findings为空"
            )
    else:
        if not findings:
            raise ValueError(f"{phase} 非passed review必须包含finding")
        if decision == "repair-required" and round_number >= MAX_BOUNDED_REVIEWS:
            raise ValueError(f"{phase} 最后一轮不得要求repair")
    return data


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
