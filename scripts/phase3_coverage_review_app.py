#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the Phase 3 coverage normalization review app.

The generated HTML is a reviewer-facing aid. It renders the normalized Phase 3
coverage artifacts as linked views: source coverage, source-to-global mapping,
risk queue, and global atom registry. It does not perform semantic coverage
review, duplicate resolution, or ownership decisions.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from source_aligned_trace_lib import line_ranges_label, range_covered_by


TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CANONICAL_RANGE_RE = re.compile(r"^L([1-9]\d*)-L([1-9]\d*)$")
LEGACY_RANGE_RE = re.compile(r"^L?(\d+)(?:\s*-\s*L?(\d+))?$", re.IGNORECASE)
GA_RE = re.compile(r"GA-\d{4}")


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


def table_rows(path: Path, required_headers: Sequence[str]) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    required = {name.lower() for name in required_headers}
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


def source_path_to_coverage_name(source_path: str) -> str:
    without_suffix = str(Path(source_path).with_suffix(""))
    return without_suffix.replace("/", "--") + ".coverage.md"


def parse_global_atoms(orchestrate_dir: Path, warnings: List[str]) -> List[Dict[str, object]]:
    json_path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.json"
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        atoms: List[Dict[str, object]] = []
        for row in data.get("global-atoms", []):
            if not isinstance(row, dict):
                warnings.append(f"{json_path.name}: invalid global-atoms row")
                continue
            atoms.append(
                {
                    "globalAtomId": normalize_code(str(row.get("global-atom-id", ""))),
                    "sourceDocument": normalize_code(str(row.get("source-document", ""))),
                    "lines": normalize_code(str(row.get("lines", ""))),
                    "ranges": row.get("line-ranges", []),
                    "atomType": squash(row.get("atom-type", "")),
                    "sourceFact": squash(row.get("source-fact", "")),
                    "normativity": squash(row.get("normativity", "")),
                    "coverageStatus": squash(row.get("coverage-status", "")),
                    "artifactProjection": squash(row.get("artifact-projection", "")),
                    "ownerChange": normalize_code(str(row.get("owner-change", ""))),
                    "ownerCapability": normalize_code(str(row.get("owner-capability", ""))),
                    "sourceAtomOrigins": normalize_code(str(row.get("source-atom-origins", ""))),
                    "atomRelation": normalize_code(str(row.get("atom-relation", ""))),
                    "proposeUse": squash(row.get("propose-use", "")),
                    "evidenceNeed": squash(row.get("evidence-need", "")),
                    "reviewJudgment": squash(row.get("review-judgment", "")),
                }
            )
        return atoms

    path = orchestrate_dir / "change-capability-anchors/obligation-atom-index.md"
    warnings.append(f"{path.name}: JSON trace missing; fallback to Markdown global atom index")
    rows = table_rows(
        path,
        [
            "global atom id",
            "source document",
            "lines",
            "atom type",
            "source fact",
            "coverage status",
            "artifact projection",
        ],
    )
    atoms: List[Dict[str, object]] = []
    for row in rows:
        ranges, range_warnings = parse_ranges(row.get("lines", ""))
        atom_id = normalize_code(row.get("global atom id", ""))
        for warning in range_warnings:
            warnings.append(f"{path.name}:{atom_id}: {warning}")
        atoms.append(
            {
                "globalAtomId": atom_id,
                "sourceDocument": normalize_code(row.get("source document", "")),
                "lines": normalize_code(row.get("lines", "")),
                "ranges": ranges,
                "atomType": squash(row.get("atom type", "")),
                "sourceFact": squash(row.get("source fact", "")),
                "normativity": squash(row.get("normativity", "")),
                "coverageStatus": squash(row.get("coverage status", "")),
                "artifactProjection": squash(row.get("artifact projection", "")),
                "ownerChange": normalize_code(row.get("owner change", "")),
                "ownerCapability": normalize_code(row.get("owner capability", "")),
                "sourceAtomOrigins": normalize_code(row.get("source atom origins", "")),
                "atomRelation": normalize_code(row.get("atom relation", "")),
                "proposeUse": squash(row.get("propose use", "")),
                "evidenceNeed": squash(row.get("evidence need", "")),
                "reviewJudgment": squash(row.get("review judgment", "")),
            }
        )
    return atoms


def parse_mapping(orchestrate_dir: Path, warnings: Optional[List[str]] = None) -> List[Dict[str, str]]:
    json_path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.json"
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        output: List[Dict[str, str]] = []
        for row in data.get("rows", []):
            if not isinstance(row, dict):
                continue
            relation = (
                row.get("global-atom-id")
                or row.get("global-relation")
                or row.get("non-coverage-status")
                or row.get("blocker")
                or ""
            )
            output.append(
                {
                    "sourceDocument": normalize_code(str(row.get("source-document", ""))),
                    "sourceAtomId": normalize_code(str(row.get("source-atom-id", ""))),
                    "lines": normalize_code(str(row.get("lines", ""))),
                    "candidateStatus": squash(row.get("candidate-status", "")),
                    "candidateArtifactProjection": squash(row.get("candidate-artifact-projection", "")),
                    "candidateOwnerChange": normalize_code(str(row.get("candidate-owner-change", ""))),
                    "candidateOwnerCapability": normalize_code(str(row.get("candidate-owner-capability", ""))),
                    "globalAtomIdOrRelation": normalize_code(str(relation)),
                    "globalCoverageStatus": squash(row.get("global-coverage-status", "")),
                    "globalArtifactProjection": squash(row.get("global-artifact-projection", "")),
                    "reviewDecision": squash(row.get("review-decision", "")),
                    "reason": squash(row.get("reason", "")),
                }
            )
        return output

    path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-to-global-atom-map.md"
    if warnings is not None:
        warnings.append(f"{path.name}: JSON trace missing; fallback to Markdown source-to-global map")
    rows = table_rows(
        path,
        [
            "source document",
            "source atom id",
            "lines",
            "global atom id or relation",
            "global coverage status",
            "review decision",
        ],
    )
    output: List[Dict[str, str]] = []
    for row in rows:
        output.append(
            {
                "sourceDocument": normalize_code(row.get("source document", "")),
                "sourceAtomId": normalize_code(row.get("source atom id", "")),
                "lines": normalize_code(row.get("lines", "")),
                "candidateStatus": squash(row.get("candidate status", "")),
                "candidateArtifactProjection": squash(row.get("candidate artifact projection", "")),
                "candidateOwnerChange": normalize_code(row.get("candidate owner change", "")),
                "candidateOwnerCapability": normalize_code(row.get("candidate owner capability", "")),
                "globalAtomIdOrRelation": normalize_code(row.get("global atom id or relation", "")),
                "globalCoverageStatus": squash(row.get("global coverage status", "")),
                "globalArtifactProjection": squash(row.get("global artifact projection", "")),
                "reviewDecision": squash(row.get("review decision", "")),
                "reason": squash(row.get("reason", "")),
            }
        )
    return output


def parse_duplicate_review(orchestrate_dir: Path) -> List[Dict[str, str]]:
    path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/duplicate-ownership-review.md"
    rows = table_rows(
        path,
        [
            "candidate id",
            "source ranges or source atoms",
            "candidate type",
            "resolution",
            "phase 5 placement needed?",
        ],
    )
    if not rows:
        rows = table_rows(
            path,
            [
                "candidate id",
                "source ranges or source atoms",
                "candidate type",
                "resolution",
                "phase 4 placement needed?",
            ],
        )
    output: List[Dict[str, str]] = []
    for row in rows:
        output.append(
            {
                "candidateId": normalize_code(row.get("candidate id", "")),
                "sourceRangesOrAtoms": squash(row.get("source ranges or source atoms", "")),
                "candidateType": squash(row.get("candidate type", "")),
                "equivalentObligation": squash(row.get("equivalent obligation?", "")),
                "resolution": squash(row.get("resolution", "")),
                "globalAtomIdOrRelation": normalize_code(row.get("global atom id or relation", "")),
                "phase5PlacementNeeded": squash(row.get("phase 5 placement needed?", row.get("phase 4 placement needed?", ""))),
                "reason": squash(row.get("reason", "")),
            }
        )
    return output


def parse_coverage_review(orchestrate_dir: Path) -> Dict[str, object]:
    path = orchestrate_dir / "phase-works/phase-3/coverage-review.md"
    source_rows = table_rows(
        path,
        [
            "source document",
            "review file",
            "atom coverage summary",
            "review judgment",
        ],
    )
    metric_rows = table_rows(path, ["metric", "value", "evidence", "interpretation"])
    handoff_rows = table_rows(
        path,
        [
            "handoff item",
            "source ranges or atoms",
            "current candidate owners",
            "why phase 5 must decide",
        ],
    )
    if not handoff_rows:
        handoff_rows = table_rows(
            path,
            [
                "handoff item",
                "source ranges or atoms",
                "current candidate owners",
                "why phase 4 must decide",
            ],
        )
    decision = ""
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("Decision:"):
                decision = line.strip()
    return {
        "sourceRows": [
            {
                "sourceDocument": normalize_code(row.get("source document", "")),
                "reviewFile": normalize_code(row.get("review file", "")),
                "atomCoverageSummary": squash(row.get("atom coverage summary", "")),
                "missingObligationAtoms": squash(row.get("missing obligation atoms", "")),
                "duplicateOwnershipFindings": squash(row.get("duplicate/ownership findings", "")),
                "nonAtomRanges": squash(row.get("non-atom ranges", "")),
                "readScope": squash(row.get("read scope", "")),
                "reviewJudgment": squash(row.get("review judgment", "")),
            }
            for row in source_rows
        ],
        "metrics": [
            {
                "metric": squash(row.get("metric", "")),
                "value": squash(row.get("value", "")),
                "evidence": squash(row.get("evidence", "")),
                "interpretation": squash(row.get("interpretation", "")),
            }
            for row in metric_rows
        ],
        "handoffs": [
            {
                "handoffItem": normalize_code(row.get("handoff item", "")),
                "sourceRangesOrAtoms": squash(row.get("source ranges or atoms", "")),
                "currentCandidateOwners": squash(row.get("current candidate owners", "")),
                "currentArtifactProjection": squash(row.get("current artifact projection", "")),
                "whyPhase5MustDecide": squash(row.get("why phase 5 must decide", row.get("why phase 4 must decide", ""))),
                "requiredPlanRefitConsideration": squash(row.get("required plan refit consideration", "")),
            }
            for row in handoff_rows
        ],
        "decision": decision,
    }


def parse_coverage_file(path: Path, warnings: List[str]) -> Dict[str, object]:
    effective_rows = table_rows(
        path,
        [
            "global atom id",
            "source atom origins",
            "lines",
            "coverage status",
            "artifact projection",
            "source fact",
        ],
    )
    section_rows = table_rows(
        path,
        [
            "source section or range",
            "expected atom type",
            "global atom ids",
            "coverage judgment",
            "reason",
        ],
    )
    non_atom_rows = table_rows(
        path,
        [
            "candidate range",
            "read scope",
            "semantic classification",
            "production obligation?",
            "reason",
        ],
    )
    duplicate_rows = table_rows(
        path,
        [
            "source ranges or atoms",
            "candidate duplicate/conflict",
            "resolution",
            "global atom id or relation",
            "review judgment",
        ],
    )

    effective: List[Dict[str, object]] = []
    for row in effective_rows:
        atom_id = normalize_code(row.get("global atom id", ""))
        ranges, range_warnings = parse_ranges(row.get("lines", ""))
        for warning in range_warnings:
            warnings.append(f"{path.name}:{atom_id}: {warning}")
        effective.append(
            {
                "globalAtomId": atom_id,
                "sourceAtomOrigins": normalize_code(row.get("source atom origins", "")),
                "lines": normalize_code(row.get("lines", "")),
                "ranges": ranges,
                "atomType": squash(row.get("atom type", "")),
                "coverageStatus": squash(row.get("coverage status", "")),
                "artifactProjection": squash(row.get("artifact projection", "")),
                "ownerChange": normalize_code(row.get("candidate / owner change", "")),
                "ownerCapability": normalize_code(row.get("candidate / owner capability", "")),
                "sourceFact": squash(row.get("source fact", "")),
            }
        )

    return {
        "effectiveAtoms": effective,
        "sectionCoverage": [
            {
                "sourceSectionOrRange": squash(row.get("source section or range", "")),
                "expectedAtomType": squash(row.get("expected atom type", "")),
                "globalAtomIds": normalize_code(row.get("global atom ids", "")),
                "coverageJudgment": squash(row.get("coverage judgment", "")),
                "reason": squash(row.get("reason", "")),
            }
            for row in section_rows
        ],
        "nonAtomRanges": [
            {
                "candidateRange": squash(row.get("candidate range", "")),
                "readScope": squash(row.get("read scope", "")),
                "semanticClassification": squash(row.get("semantic classification", "")),
                "productionObligation": squash(row.get("production obligation?", "")),
                "reason": squash(row.get("reason", "")),
            }
            for row in non_atom_rows
        ],
        "duplicateOwnership": [
            {
                "sourceRangesOrAtoms": squash(row.get("source ranges or atoms", "")),
                "candidateDuplicateConflict": squash(row.get("candidate duplicate/conflict", "")),
                "resolution": squash(row.get("resolution", "")),
                "globalAtomIdOrRelation": normalize_code(row.get("global atom id or relation", "")),
                "reviewJudgment": squash(row.get("review judgment", "")),
            }
            for row in duplicate_rows
        ],
    }


def json_line_ranges_label(value: object) -> str:
    if not isinstance(value, list):
        return ""
    ranges = [
        {"start": item.get("start"), "end": item.get("end")}
        for item in value
        if isinstance(item, dict) and isinstance(item.get("start"), int) and isinstance(item.get("end"), int)
    ]
    return line_ranges_label(ranges)


def parse_remainder_review(orchestrate_dir: Path, warnings: List[str]) -> Dict[str, object]:
    path = orchestrate_dir / "phase-works/phase-3/phase-3-trace/source-remainder-review.json"
    if not path.exists():
        warnings.append(f"{path.name}: JSON trace missing; fallback to per-source Non-Atom Range Review tables")
        return {"auditByDoc": {}, "rowsByDoc": {}, "rowCount": 0}
    data = json.loads(path.read_text(encoding="utf-8"))
    review_ranges_by_doc: Dict[str, List[Dict[str, int]]] = defaultdict(list)
    rows_by_doc: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for row in data.get("rows", []):
        if not isinstance(row, dict):
            continue
        source_document = normalize_code(str(row.get("source-document", "")))
        ranges = row.get("line-ranges", [])
        if isinstance(ranges, list):
            review_ranges_by_doc[source_document].extend(
                [
                    {"start": item.get("start"), "end": item.get("end")}
                    for item in ranges
                    if isinstance(item, dict)
                    and isinstance(item.get("start"), int)
                    and isinstance(item.get("end"), int)
                ]
            )
        rows_by_doc[source_document].append(
            {
                "sourceDocument": source_document,
                "lines": normalize_code(str(row.get("lines", ""))) or json_line_ranges_label(ranges),
                "ranges": ranges if isinstance(ranges, list) else [],
                "howFound": squash(row.get("how-found", "")),
                "readScope": squash(row.get("read-scope", "")),
                "semanticClassification": squash(row.get("semantic-classification", "")),
                "productionObligation": squash(row.get("production-obligation", "")),
                "linkedGlobalAtomIds": row.get("linked-global-atom-ids", []),
                "nonCoverageStatus": squash(row.get("non-coverage-status", "")),
                "blocker": squash(row.get("blocker", "")),
                "reason": squash(row.get("reason", "")),
            }
        )

    audit_by_doc: Dict[str, Dict[str, object]] = {}
    for item in data.get("audit-documents", []):
        if not isinstance(item, dict):
            continue
        source_document = normalize_code(str(item.get("source-document", "")))
        candidates: List[Dict[str, object]] = []
        for candidate in item.get("candidate-uncovered-ranges", []):
            if not isinstance(candidate, dict):
                continue
            ranges = candidate.get("line-ranges", [])
            valid_ranges = [
                {"start": row.get("start"), "end": row.get("end")}
                for row in ranges
                if isinstance(row, dict) and isinstance(row.get("start"), int) and isinstance(row.get("end"), int)
            ] if isinstance(ranges, list) else []
            reviewed = all(range_covered_by(row, review_ranges_by_doc.get(source_document, [])) for row in valid_ranges)
            candidates.append(
                {
                    "lines": normalize_code(str(candidate.get("lines", ""))) or line_ranges_label(valid_ranges),
                    "ranges": valid_ranges,
                    "reviewed": reviewed,
                }
            )
        audit_by_doc[source_document] = {
            "lineCount": item.get("line-count", 0),
            "candidateUncoveredRanges": candidates,
            "evidenceRanges": item.get("evidence-ranges", []),
        }
    return {
        "auditByDoc": audit_by_doc,
        "rowsByDoc": dict(rows_by_doc),
        "rowCount": sum(len(rows) for rows in rows_by_doc.values()),
    }


def make_risk_queue(
    duplicate_rows: Sequence[Dict[str, str]],
    handoff_rows: Sequence[Dict[str, str]],
    mapping_rows: Sequence[Dict[str, str]],
) -> List[Dict[str, str]]:
    risks: List[Dict[str, str]] = []
    seen: set[str] = set()

    def add_risk(key: str, severity: int, risk_type: str, title: str, evidence: str, resolution: str, reason: str) -> None:
        if key in seen:
            return
        seen.add(key)
        risks.append(
            {
                "key": key,
                "severity": str(severity),
                "riskType": risk_type,
                "title": title,
                "evidence": evidence,
                "resolution": resolution,
                "reason": reason,
            }
        )

    for row in duplicate_rows:
        candidate_type = row.get("candidateType", "")
        severity = 40
        if "blocked" in row.get("resolution", "").lower() or "conflict" in candidate_type:
            severity = 100
        elif row.get("phase5PlacementNeeded", "").lower() == "yes":
            severity = 70
        elif "broad" in candidate_type:
            severity = 80
        elif "duplicate" in candidate_type:
            severity = 55
        add_risk(
            f"dup:{row.get('candidateId', '')}",
            severity,
            candidate_type or "duplicate/ownership",
            row.get("candidateId", "") or row.get("globalAtomIdOrRelation", ""),
            row.get("sourceRangesOrAtoms", ""),
            row.get("resolution", ""),
            row.get("reason", ""),
        )

    for row in handoff_rows:
        add_risk(
            f"handoff:{row.get('handoffItem', '')}",
            65,
            "phase-5-refit-handoff",
            row.get("handoffItem", ""),
            row.get("sourceRangesOrAtoms", ""),
            row.get("currentCandidateOwners", ""),
            row.get("whyPhase5MustDecide", ""),
        )

    for row in mapping_rows:
        relation = row.get("globalAtomIdOrRelation", "")
        decision = row.get("reviewDecision", "")
        status = row.get("globalCoverageStatus", "")
        if "blocked" in status or "unresolved" in status:
            severity = 100
        elif "phase-5" in status or "phase-5" in decision or "phase-5" in relation or "phase-4" in status or "phase-4" in decision or "phase-4" in relation:
            severity = 60
        elif "split" in relation:
            severity = 72
        else:
            continue
        key = f"map:{row.get('sourceDocument', '')}:{row.get('sourceAtomId', '')}"
        add_risk(
            key,
            severity,
            status or decision,
            row.get("sourceAtomId", ""),
            f"{row.get('sourceDocument', '')} {row.get('lines', '')}",
            relation,
            row.get("reason", ""),
        )

    risks.sort(key=lambda item: (-int(item["severity"]), item["riskType"], item["title"]))
    return risks


def build_data(repo_root: Path, orchestrate_dir: Path) -> Dict[str, object]:
    warnings: List[str] = []
    manifest_path = orchestrate_dir / "phase-works/phase-3/source-doc-manifest.md"
    manifest_rows = table_rows(
        manifest_path,
        [
            "source document",
            "classification",
            "phase 2 atom file",
            "review file",
            "effective atom ranges",
            "reason",
        ],
    )
    global_atoms = parse_global_atoms(orchestrate_dir, warnings)
    mapping_rows = parse_mapping(orchestrate_dir, warnings)
    duplicate_rows = parse_duplicate_review(orchestrate_dir)
    coverage_review = parse_coverage_review(orchestrate_dir)
    handoff_rows = coverage_review.get("handoffs", [])
    remainder_review = parse_remainder_review(orchestrate_dir, warnings)

    global_by_doc: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    global_by_id: Dict[str, Dict[str, object]] = {}
    for atom in global_atoms:
        global_by_doc[str(atom.get("sourceDocument", ""))].append(atom)
        global_by_id[str(atom.get("globalAtomId", ""))] = atom

    mapping_by_doc: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in mapping_rows:
        mapping_by_doc[row["sourceDocument"]].append(row)

    review_summary_by_doc = {
        str(row.get("sourceDocument", "")): row for row in coverage_review.get("sourceRows", [])
    }

    docs: List[Dict[str, object]] = []
    for row in manifest_rows:
        source_document = normalize_code(row.get("source document", ""))
        review_file = normalize_code(row.get("review file", ""))
        review_path = repo_root / review_file if review_file else (
            orchestrate_dir / "phase-works/phase-3/source-doc-coverage" / source_path_to_coverage_name(source_document)
        )
        source_path = repo_root / source_document
        if source_path.exists():
            source_lines = source_path.read_text(encoding="utf-8").splitlines()
        else:
            source_lines = []
            warnings.append(f"missing source document: {source_document}")

        coverage = parse_coverage_file(review_path, warnings)
        summary = review_summary_by_doc.get(source_document, {})
        doc_global_atoms = coverage["effectiveAtoms"] or global_by_doc.get(source_document, [])
        status_counts = Counter(str(atom.get("coverageStatus", "")) for atom in doc_global_atoms)
        projection_counts = Counter(str(atom.get("artifactProjection", "")) for atom in doc_global_atoms)
        section_counts = Counter(
            str(section.get("coverageJudgment", "")) for section in coverage["sectionCoverage"]  # type: ignore[index]
        )

        docs.append(
            {
                "path": source_document,
                "classification": squash(row.get("classification", "")),
                "phase2AtomFile": normalize_code(row.get("phase 2 atom file", "")),
                "reviewFile": review_file,
                "effectiveAtomRanges": squash(row.get("effective atom ranges", "")),
                "missingObligationAtomRanges": squash(row.get("missing obligation atom ranges", "")),
                "nonAtomRangesSummary": squash(row.get("non-atom ranges", "")),
                "readScope": squash(row.get("read scope", "")),
                "reason": squash(row.get("reason", "")),
                "reviewJudgment": squash(summary.get("reviewJudgment", "")),
                "atomCoverageSummary": squash(summary.get("atomCoverageSummary", "")),
                "duplicateOwnershipFindings": squash(summary.get("duplicateOwnershipFindings", "")),
                "lineCount": len(source_lines),
                "headings": parse_headings(source_lines),
                "lines": source_lines,
                "effectiveAtoms": doc_global_atoms,
                "sectionCoverage": coverage["sectionCoverage"],
                "nonAtomRanges": coverage["nonAtomRanges"],
                "remainderAudit": remainder_review["auditByDoc"].get(source_document, {}),
                "remainderRows": remainder_review["rowsByDoc"].get(source_document, []),
                "duplicateOwnership": coverage["duplicateOwnership"],
                "mappingRows": mapping_by_doc.get(source_document, []),
                "statusCounts": dict(sorted(status_counts.items())),
                "projectionCounts": dict(sorted(projection_counts.items())),
                "sectionJudgmentCounts": dict(sorted(section_counts.items())),
            }
        )

    status_counts = Counter(str(atom.get("coverageStatus", "")) for atom in global_atoms)
    projection_counts = Counter(str(atom.get("artifactProjection", "")) for atom in global_atoms)
    owner_counts = Counter(str(atom.get("ownerChange", "")) for atom in global_atoms)
    risk_queue = make_risk_queue(duplicate_rows, handoff_rows, mapping_rows)  # type: ignore[arg-type]

    return {
        "meta": {
            "manifest": str(manifest_path),
            "sourceCount": len(docs),
            "globalAtomCount": len(global_atoms),
            "mappingRowCount": len(mapping_rows),
            "remainderReviewRowCount": remainder_review["rowCount"],
            "riskCount": len(risk_queue),
            "phase5HandoffCount": len(handoff_rows),
            "decision": coverage_review.get("decision", ""),
            "statusCounts": dict(sorted(status_counts.items())),
            "projectionCounts": dict(sorted(projection_counts.items())),
            "ownerCountsTop": dict(owner_counts.most_common(12)),
            "warnings": warnings,
        },
        "docs": docs,
        "globalAtoms": global_atoms,
        "mappingRows": mapping_rows,
        "riskQueue": risk_queue,
        "metrics": coverage_review.get("metrics", []),
        "handoffs": handoff_rows,
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
  <title>Phase 3 Coverage Review</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f3ed;
      --panel: #fffefa;
      --panel-soft: #faf8f1;
      --ink: #202420;
      --muted: #666f68;
      --line: #ddd6c7;
      --line-strong: #bdb5a5;
      --green: #1f7668;
      --green-soft: #dcece6;
      --blue: #255f92;
      --blue-soft: #e3edf6;
      --amber: #a05d00;
      --amber-soft: #fff0d3;
      --red: #a13b35;
      --red-soft: #f8dfda;
      --violet: #5f568d;
      --violet-soft: #ece7f4;
      --shadow: 0 12px 28px rgba(36, 34, 28, 0.08);
      --mono: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
      --sans: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      min-width: 1180px;
      height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font-family: var(--sans);
      letter-spacing: 0;
      overflow: hidden;
    }}

    button, input, select {{ font: inherit; }}

    .shell {{
      display: grid;
      grid-template-rows: auto 1fr;
      height: 100vh;
    }}

    .topbar {{
      display: grid;
      grid-template-columns: minmax(280px, 1fr) auto;
      gap: 16px;
      align-items: center;
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
      z-index: 4;
    }}

    .brand h1 {{
      margin: 0;
      font-size: 18px;
      line-height: 1.25;
      font-weight: 780;
    }}

    .brand p {{
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }}

    .stats {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}

    .stat {{
      min-width: 84px;
      border: 1px solid var(--line);
      background: var(--panel-soft);
      padding: 7px 9px;
    }}

    .stat strong {{
      display: block;
      font-family: var(--mono);
      font-size: 16px;
      line-height: 1.1;
    }}

    .stat span {{
      display: block;
      margin-top: 3px;
      color: var(--muted);
      font-size: 10px;
      white-space: nowrap;
    }}

    .nav {{
      display: flex;
      gap: 6px;
      padding: 10px 18px 0;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }}

    .tab {{
      border: 1px solid var(--line);
      border-bottom: 0;
      background: var(--panel-soft);
      color: var(--muted);
      padding: 8px 12px;
      cursor: pointer;
      font-size: 13px;
    }}

    .tab.active {{
      background: var(--bg);
      color: var(--ink);
      box-shadow: inset 0 3px 0 var(--green);
      font-weight: 700;
    }}

    .view {{
      display: none;
      min-height: 0;
      height: 100%;
    }}

    .view.active {{
      display: grid;
    }}

    #sourceView {{
      grid-template-columns: 310px minmax(520px, 1fr) 430px;
    }}

    #mappingView,
    #riskView,
    #registryView {{
      grid-template-rows: auto 1fr;
    }}

    .sidebar,
    .right-panel,
    .table-panel {{
      min-height: 0;
      overflow: hidden;
      border-color: var(--line);
      background: var(--panel);
    }}

    .sidebar {{
      border-right: 1px solid var(--line);
      display: grid;
      grid-template-rows: auto 1fr auto;
    }}

    .right-panel {{
      border-left: 1px solid var(--line);
      display: grid;
      grid-template-rows: auto auto 1fr;
    }}

    .filter-box {{
      padding: 12px;
      border-bottom: 1px solid var(--line);
      background: var(--panel-soft);
    }}

    .filter-box input,
    .filter-box select,
    .toolbar input,
    .toolbar select {{
      width: 100%;
      height: 34px;
      border: 1px solid var(--line-strong);
      background: #fff;
      padding: 7px 9px;
      color: var(--ink);
      outline: none;
      border-radius: 3px;
    }}

    .filter-box input:focus,
    .filter-box select:focus,
    .toolbar input:focus,
    .toolbar select:focus {{
      border-color: var(--green);
      box-shadow: 0 0 0 3px var(--green-soft);
    }}

    .doc-tree,
    .outline,
    .source-scroll,
    .right-scroll,
    .table-scroll {{
      min-height: 0;
      overflow: auto;
    }}

    .doc-tree {{
      padding: 8px 10px 14px;
    }}

    .tree-row {{
      width: 100%;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
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

    .tree-row:hover {{ background: var(--panel-soft); }}

    .tree-row.active {{
      border-left-color: var(--green);
      background: var(--green-soft);
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

    .folder-badge,
    .mini-badge {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--green);
      font-family: var(--mono);
      font-size: 10px;
      padding: 1px 4px;
      white-space: nowrap;
    }}

    .tree-path,
    .folder-name {{
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-family: var(--mono);
      font-size: 12px;
    }}

    .tree-count {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--muted);
      font-family: var(--mono);
      font-size: 11px;
      padding: 2px 5px;
    }}

    .outline {{
      max-height: 190px;
      padding: 12px;
      border-top: 1px solid var(--line);
      background: var(--panel-soft);
    }}

    .section-label {{
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 11px;
      font-weight: 760;
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

    .source-main {{
      min-width: 0;
      min-height: 0;
      display: grid;
      grid-template-rows: auto 1fr;
    }}

    .doc-header {{
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      padding: 14px 18px;
      box-shadow: var(--shadow);
      z-index: 2;
    }}

    .doc-path {{
      margin: 0;
      font-family: var(--mono);
      font-size: 17px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }}

    .doc-meta {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }}

    .doc-pills {{
      display: flex;
      gap: 7px;
      flex-wrap: wrap;
      margin-top: 10px;
    }}

    .pill {{
      border: 1px solid var(--line);
      background: var(--panel-soft);
      color: var(--muted);
      min-height: 25px;
      padding: 4px 7px;
      font-size: 11px;
      white-space: nowrap;
    }}

    .pill strong {{
      color: var(--ink);
      font-family: var(--mono);
      margin-right: 5px;
    }}

    .pill.warn {{ background: var(--amber-soft); color: var(--amber); border-color: #e0bd7a; }}
    .pill.good {{ background: var(--green-soft); color: var(--green); border-color: #9cc9bf; }}
    .pill.bad {{ background: var(--red-soft); color: var(--red); border-color: #dda5a0; }}

    .source-scroll {{
      background:
        linear-gradient(90deg, rgba(31, 118, 104, 0.07) 0, rgba(31, 118, 104, 0.07) 72px, transparent 72px),
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
      grid-template-columns: 54px minmax(0, 1fr) 166px;
      gap: 10px;
      min-height: 24px;
      border-left: 3px solid transparent;
      padding: 1px 6px 1px 0;
    }}

    .source-line.has-ga {{
      background: rgba(31, 118, 104, 0.055);
      border-left-color: rgba(31, 118, 104, 0.55);
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
    }}

    .line-tag {{
      border: 1px solid rgba(31, 118, 104, 0.32);
      background: #fff;
      color: var(--green);
      max-width: 154px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      padding: 1px 5px;
      font-size: 10px;
      cursor: pointer;
    }}

    .line-tag.active {{
      border-color: var(--amber);
      color: var(--amber);
      background: var(--amber-soft);
    }}

    .right-head {{
      padding: 14px 16px 10px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}

    .right-head h2 {{
      margin: 0;
      font-size: 16px;
      line-height: 1.3;
    }}

    .right-head p {{
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }}

    .segment {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0;
      padding: 10px 12px;
      background: var(--panel-soft);
      border-bottom: 1px solid var(--line);
    }}

    .segment button {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--muted);
      padding: 7px 4px;
      cursor: pointer;
      font-size: 11px;
    }}

    .segment button.active {{
      background: var(--green-soft);
      color: var(--green);
      font-weight: 700;
    }}

    .right-scroll {{
      padding: 12px 12px 120px;
      background: var(--bg);
    }}

    .card {{
      border: 1px solid var(--line);
      border-left: 4px solid var(--green);
      background: var(--panel);
      padding: 11px;
      margin-bottom: 10px;
      cursor: pointer;
    }}

    .card:hover {{
      border-color: var(--line-strong);
      box-shadow: 0 8px 18px rgba(36, 34, 28, 0.07);
    }}

    .card.active {{
      border-left-color: var(--amber);
      box-shadow: 0 0 0 3px var(--amber-soft);
    }}

    .card-top {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      margin-bottom: 8px;
    }}

    .code {{
      font-family: var(--mono);
      font-size: 12px;
      font-weight: 760;
      overflow-wrap: anywhere;
    }}

    .lines {{
      color: var(--amber);
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 760;
      white-space: nowrap;
    }}

    .summary {{
      margin: 0 0 9px;
      font-size: 13px;
      line-height: 1.48;
    }}

    .fields {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
    }}

    .field {{
      border: 1px solid var(--line);
      background: var(--panel-soft);
      padding: 6px;
      min-width: 0;
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
      line-height: 1.32;
      font-weight: 680;
    }}

    .toolbar {{
      display: grid;
      grid-template-columns: minmax(260px, 1fr) 190px 190px 190px;
      gap: 10px;
      padding: 12px 18px;
      background: var(--panel-soft);
      border-bottom: 1px solid var(--line);
    }}

    .table-scroll {{
      padding: 14px 18px 120px;
    }}

    table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      font-size: 12px;
    }}

    th, td {{
      border-bottom: 1px solid var(--line);
      border-right: 1px solid var(--line);
      padding: 8px;
      vertical-align: top;
      text-align: left;
      line-height: 1.4;
    }}

    th {{
      position: sticky;
      top: 0;
      background: #f0ede4;
      z-index: 1;
      color: var(--muted);
      font-size: 11px;
      font-weight: 780;
    }}

    tr:hover td {{ background: var(--panel-soft); }}

    .table-code {{
      font-family: var(--mono);
      font-size: 11px;
      overflow-wrap: anywhere;
    }}

    .risk-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}

    .risk-card {{
      border: 1px solid var(--line);
      border-left: 5px solid var(--amber);
      background: var(--panel);
      padding: 12px;
      min-width: 0;
    }}

    .risk-card.high {{ border-left-color: var(--red); }}
    .risk-card.medium {{ border-left-color: var(--amber); }}
    .risk-card.low {{ border-left-color: var(--blue); }}

    .risk-title {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
    }}

    .risk-title strong {{
      font-family: var(--mono);
      font-size: 12px;
      overflow-wrap: anywhere;
    }}

    .risk-type {{
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
    }}

    .empty {{
      border: 1px dashed var(--line-strong);
      color: var(--muted);
      background: var(--panel-soft);
      padding: 14px;
      font-size: 13px;
      line-height: 1.45;
    }}

    .warning-box {{
      border: 1px solid var(--red);
      background: var(--red-soft);
      color: var(--red);
      padding: 9px 10px;
      margin-bottom: 10px;
      font-size: 12px;
      line-height: 1.45;
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div>
      <header class="topbar">
        <div class="brand">
          <h1>Phase 3 Coverage Normalization Review</h1>
          <p>审阅 source coverage、Source Atom → Global Atom 映射、风险队列和全局 GA registry。</p>
        </div>
        <div class="stats">
          <div class="stat"><strong id="statDocs">0</strong><span>source docs</span></div>
          <div class="stat"><strong id="statAtoms">0</strong><span>global atoms</span></div>
          <div class="stat"><strong id="statMap">0</strong><span>mapped rows</span></div>
          <div class="stat"><strong id="statRisks">0</strong><span>risk items</span></div>
          <div class="stat"><strong id="statWarn">0</strong><span>warnings</span></div>
        </div>
      </header>
      <nav class="nav">
        <button class="tab active" data-view="sourceView">Source Coverage</button>
        <button class="tab" data-view="mappingView">Source → Global</button>
        <button class="tab" data-view="riskView">Risk Queue</button>
        <button class="tab" data-view="registryView">Global Registry</button>
      </nav>
    </div>

    <section id="sourceView" class="view active">
      <aside class="sidebar">
        <div class="filter-box">
          <input id="docSearch" type="search" placeholder="过滤 source doc / judgment" />
        </div>
        <div class="doc-tree" id="docTree"></div>
        <div class="outline" id="outline"></div>
      </aside>
      <main class="source-main">
        <header class="doc-header">
          <h2 class="doc-path" id="docPath"></h2>
          <div class="doc-meta" id="docMeta"></div>
          <div class="doc-pills" id="docPills"></div>
        </header>
        <div class="source-scroll" id="sourceScroll">
          <div class="source-lines" id="sourceLines"></div>
        </div>
      </main>
      <aside class="right-panel">
        <div class="right-head">
          <h2>Coverage Verdict</h2>
          <p>查看本 source doc 的 GA 覆盖、section 判断、非 atom range 和归属复核。</p>
        </div>
        <div class="segment">
          <button class="detail-tab active" data-detail="atoms">GA Atoms</button>
          <button class="detail-tab" data-detail="sections">Sections</button>
          <button class="detail-tab" data-detail="remainders">Remainders</button>
          <button class="detail-tab" data-detail="duplicates">Review</button>
        </div>
        <div class="right-scroll" id="detailPanel"></div>
      </aside>
    </section>

    <section id="mappingView" class="view">
      <div class="toolbar">
        <input id="mappingSearch" type="search" placeholder="搜索 source atom / GA / reason" />
        <select id="mappingStatus"><option value="">Coverage Status</option></select>
        <select id="mappingDecision"><option value="">Review Decision</option></select>
        <select id="mappingProjection"><option value="">Projection</option></select>
      </div>
      <div class="table-scroll"><table id="mappingTable"></table></div>
    </section>

    <section id="riskView" class="view">
      <div class="toolbar">
        <input id="riskSearch" type="search" placeholder="搜索风险项 / evidence / reason" />
        <select id="riskType"><option value="">Risk Type</option></select>
        <select id="riskLevel"><option value="">Severity</option><option value="high">high</option><option value="medium">medium</option><option value="low">low</option></select>
        <select id="riskSource"><option value="">Source Filter</option><option value="phase-5">phase-5</option><option value="broad">broad</option><option value="duplicate">duplicate</option></select>
      </div>
      <div class="table-scroll"><div id="riskList" class="risk-grid"></div></div>
    </section>

    <section id="registryView" class="view">
      <div class="toolbar">
        <input id="registrySearch" type="search" placeholder="搜索 GA / source fact / owner / source document" />
        <select id="registryStatus"><option value="">Coverage Status</option></select>
        <select id="registryProjection"><option value="">Projection</option></select>
        <select id="registryOwner"><option value="">Owner Change</option></select>
      </div>
      <div class="table-scroll"><table id="registryTable"></table></div>
    </section>
  </div>

  <script id="review-data" type="application/json">{payload}</script>
  <script>
    const data = JSON.parse(document.getElementById('review-data').textContent);
    const state = {{
      view: 'sourceView',
      docIndex: 0,
      selectedGa: null,
      detail: 'atoms',
      docFilter: '',
      mappingSearch: '',
      mappingStatus: '',
      mappingDecision: '',
      mappingProjection: '',
      riskSearch: '',
      riskType: '',
      riskLevel: '',
      riskSource: '',
      registrySearch: '',
      registryStatus: '',
      registryProjection: '',
      registryOwner: '',
    }};

    const el = {{
      statDocs: document.getElementById('statDocs'),
      statAtoms: document.getElementById('statAtoms'),
      statMap: document.getElementById('statMap'),
      statRisks: document.getElementById('statRisks'),
      statWarn: document.getElementById('statWarn'),
      docSearch: document.getElementById('docSearch'),
      docTree: document.getElementById('docTree'),
      outline: document.getElementById('outline'),
      docPath: document.getElementById('docPath'),
      docMeta: document.getElementById('docMeta'),
      docPills: document.getElementById('docPills'),
      sourceScroll: document.getElementById('sourceScroll'),
      sourceLines: document.getElementById('sourceLines'),
      detailPanel: document.getElementById('detailPanel'),
      mappingSearch: document.getElementById('mappingSearch'),
      mappingStatus: document.getElementById('mappingStatus'),
      mappingDecision: document.getElementById('mappingDecision'),
      mappingProjection: document.getElementById('mappingProjection'),
      mappingTable: document.getElementById('mappingTable'),
      riskSearch: document.getElementById('riskSearch'),
      riskType: document.getElementById('riskType'),
      riskLevel: document.getElementById('riskLevel'),
      riskSource: document.getElementById('riskSource'),
      riskList: document.getElementById('riskList'),
      registrySearch: document.getElementById('registrySearch'),
      registryStatus: document.getElementById('registryStatus'),
      registryProjection: document.getElementById('registryProjection'),
      registryOwner: document.getElementById('registryOwner'),
      registryTable: document.getElementById('registryTable'),
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

    function gaStart(atom) {{
      if (!atom.ranges || atom.ranges.length === 0) return 999999;
      return Math.min(...atom.ranges.map((range) => range.start));
    }}

    function gaCoversLine(atom, lineNumber) {{
      return (atom.ranges || []).some((range) => lineNumber >= range.start && lineNumber <= range.end);
    }}

    function matchesText(row, filter) {{
      if (!filter) return true;
      return Object.values(row).join(' ').toLowerCase().includes(filter.toLowerCase());
    }}

    function uniqueValues(rows, key) {{
      return [...new Set(rows.map((row) => row[key]).filter(Boolean))].sort();
    }}

    function fillSelect(select, values, label) {{
      const current = select.value;
      select.innerHTML = `<option value="">${{escapeHtml(label)}}</option>` + values.map((value) => `<option value="${{escapeHtml(value)}}">${{escapeHtml(value)}}</option>`).join('');
      select.value = values.includes(current) ? current : '';
    }}

    function renderStats() {{
      el.statDocs.textContent = data.meta.sourceCount;
      el.statAtoms.textContent = data.meta.globalAtomCount;
      el.statMap.textContent = data.meta.mappingRowCount;
      el.statRisks.textContent = data.meta.riskCount;
      el.statWarn.textContent = data.meta.warnings.length;
    }}

    function filteredDocs() {{
      const filter = state.docFilter.trim().toLowerCase();
      if (!filter) return data.docs;
      return data.docs.filter((doc) => [
        doc.path,
        doc.classification,
        doc.reviewJudgment,
        doc.atomCoverageSummary,
        doc.reason,
      ].join(' ').toLowerCase().includes(filter));
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
        children.push({{ type: 'doc', name: parts[parts.length - 1], path: doc.path, doc, index: data.docs.indexOf(doc) }});
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
        const phase5 = (node.doc.reviewJudgment === 'phase-5-refit-required' || node.doc.reviewJudgment === 'phase-4-refit-required') ? ' warn' : '';
        return `
          <button class="tree-row${{active}}" data-doc-index="${{node.index}}" style="padding-left:${{8 + depth * 14}}px">
            <span class="tree-path" title="${{escapeHtml(node.path)}}">${{escapeHtml(node.name)}}</span>
            <span class="tree-count${{phase5}}">${{node.doc.effectiveAtoms.length}}</span>
          </button>
        `;
      }}).join('');
    }}

    function renderDocTree() {{
      const docs = filteredDocs();
      if (!docs.length) {{
        el.docTree.innerHTML = '<div class="empty">没有匹配的 source doc。</div>';
        return;
      }}
      el.docTree.innerHTML = renderTreeNodes(buildPathTree(docs));
      el.docTree.querySelectorAll('[data-doc-index]').forEach((button) => {{
        button.addEventListener('click', () => {{
          state.docIndex = Number(button.dataset.docIndex);
          state.selectedGa = null;
          renderSourceView(true);
        }});
      }});
    }}

    function renderOutline(doc) {{
      if (!doc.headings.length) {{
        el.outline.innerHTML = '<p class="section-label">目录</p><div class="empty">该文档没有 Markdown heading。</div>';
        return;
      }}
      el.outline.innerHTML = `<p class="section-label">目录</p>` + doc.headings.map((heading) => `
        <button data-line="${{heading.line}}" style="padding-left:${{(heading.level - 1) * 12}}px">L${{heading.line}} · ${{escapeHtml(heading.title)}}</button>
      `).join('');
      el.outline.querySelectorAll('[data-line]').forEach((button) => {{
        button.addEventListener('click', () => scrollToLine(Number(button.dataset.line)));
      }});
    }}

    function renderDocHeader(doc) {{
      el.docPath.textContent = doc.path;
      el.docMeta.textContent = `${{doc.classification || 'unclassified'}} · ${{doc.atomCoverageSummary || doc.reason || '无摘要'}}`;
      const direct = doc.statusCounts.direct || 0;
      const phase5 = (doc.statusCounts['phase-5-refit-required'] || 0) + (doc.statusCounts['phase-4-refit-required'] || 0);
      const contextual = doc.statusCounts.contextual || 0;
      const judgmentClass = (doc.reviewJudgment === 'phase-5-refit-required' || doc.reviewJudgment === 'phase-4-refit-required') ? 'warn' : (doc.reviewJudgment === 'blocked' ? 'bad' : 'good');
      el.docPills.innerHTML = `
        <span class="pill"><strong>${{doc.lineCount}}</strong>lines</span>
        <span class="pill"><strong>${{doc.effectiveAtoms.length}}</strong>GA atoms</span>
        <span class="pill good"><strong>${{direct}}</strong>direct</span>
        <span class="pill warn"><strong>${{phase5}}</strong>phase5</span>
        <span class="pill"><strong>${{contextual}}</strong>context</span>
        <span class="pill ${{judgmentClass}}"><strong>${{escapeHtml(doc.reviewJudgment || 'n/a')}}</strong>judgment</span>
      `;
    }}

    function renderSourceLines(doc) {{
      if (!doc.lines.length) {{
        el.sourceLines.innerHTML = '<div class="empty">无法读取该 source doc 原文。</div>';
        return;
      }}
      el.sourceLines.innerHTML = doc.lines.map((line, index) => {{
        const lineNumber = index + 1;
        const atoms = doc.effectiveAtoms.filter((atom) => gaCoversLine(atom, lineNumber));
        const selected = state.selectedGa && atoms.some((atom) => atom.globalAtomId === state.selectedGa);
        const className = ['source-line', atoms.length ? 'has-ga' : '', selected ? 'active-line' : ''].filter(Boolean).join(' ');
        const tags = atoms.slice(0, 4).map((atom) => {{
          const active = atom.globalAtomId === state.selectedGa ? ' active' : '';
          return `<button class="line-tag${{active}}" data-ga="${{escapeHtml(atom.globalAtomId)}}" title="${{escapeHtml(atom.sourceFact)}}">${{escapeHtml(atom.globalAtomId)}}</button>`;
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
      el.sourceLines.querySelectorAll('[data-ga]').forEach((button) => {{
        button.addEventListener('click', () => selectGa(button.dataset.ga, true));
      }});
    }}

    function renderGaCards(doc) {{
      const atoms = [...doc.effectiveAtoms].sort((a, b) => gaStart(a) - gaStart(b) || a.globalAtomId.localeCompare(b.globalAtomId));
      if (!atoms.length) return '<div class="empty">该文档没有 effective GA atom。</div>';
      return atoms.map((atom) => {{
        const active = atom.globalAtomId === state.selectedGa ? ' active' : '';
        return `
          <article class="card${{active}}" data-ga="${{escapeHtml(atom.globalAtomId)}}">
            <div class="card-top"><div class="code">${{escapeHtml(atom.globalAtomId)}}</div><div class="lines">${{escapeHtml(atom.lines)}}</div></div>
            <p class="summary">${{escapeHtml(atom.sourceFact || '无 Source Fact')}}</p>
            <div class="fields">
              <div class="field"><span>Status</span><strong>${{escapeHtml(atom.coverageStatus)}}</strong></div>
              <div class="field"><span>Projection</span><strong>${{escapeHtml(atom.artifactProjection)}}</strong></div>
              <div class="field"><span>Owner</span><strong>${{escapeHtml(atom.ownerChange || 'none')}}</strong></div>
              <div class="field"><span>Capability</span><strong>${{escapeHtml(atom.ownerCapability || 'none')}}</strong></div>
            </div>
          </article>
        `;
      }}).join('');
    }}

    function renderSectionCards(doc) {{
      if (!doc.sectionCoverage.length) return '<div class="empty">没有 Source Obligation Coverage 表。</div>';
      return doc.sectionCoverage.map((row) => `
        <article class="card">
          <div class="card-top"><div class="code">${{escapeHtml(row.sourceSectionOrRange)}}</div><span class="mini-badge">${{escapeHtml(row.coverageJudgment)}}</span></div>
          <p class="summary">${{escapeHtml(row.reason)}}</p>
          <div class="fields">
            <div class="field"><span>Expected</span><strong>${{escapeHtml(row.expectedAtomType)}}</strong></div>
            <div class="field"><span>Global Atoms</span><strong>${{escapeHtml(row.globalAtomIds)}}</strong></div>
          </div>
        </article>
      `).join('');
    }}

    function renderRemainderCards(doc) {{
      const auditRanges = (doc.remainderAudit && doc.remainderAudit.candidateUncoveredRanges) || [];
      const auditCards = auditRanges.map((row) => `
        <article class="card">
          <div class="card-top"><div class="code">${{escapeHtml(row.lines)}}</div><span class="mini-badge ${{row.reviewed ? 'good' : 'bad'}}">${{row.reviewed ? 'reviewed' : 'missing review'}}</span></div>
          <p class="summary">Phase 3 line-range audit 发现的候选未覆盖段。</p>
        </article>
      `).join('');
      const traceRows = (doc.remainderRows || []).map((row) => `
        <article class="card">
          <div class="card-top"><div class="code">${{escapeHtml(row.lines)}}</div><span class="mini-badge">${{escapeHtml(row.semanticClassification)}}</span></div>
          <p class="summary">${{escapeHtml(row.reason)}}</p>
          <div class="fields">
            <div class="field"><span>How Found</span><strong>${{escapeHtml(row.howFound)}}</strong></div>
            <div class="field"><span>Production?</span><strong>${{escapeHtml(row.productionObligation)}}</strong></div>
            <div class="field"><span>Outcome</span><strong>${{escapeHtml((row.linkedGlobalAtomIds || []).join(', ') || row.nonCoverageStatus || row.blocker || 'none')}}</strong></div>
          </div>
        </article>
      `).join('');
      const mirrorRows = doc.nonAtomRanges.map((row) => `
        <article class="card">
          <div class="card-top"><div class="code">${{escapeHtml(row.candidateRange)}}</div><span class="mini-badge">${{escapeHtml(row.semanticClassification)}}</span></div>
          <p class="summary">${{escapeHtml(row.reason)}}</p>
          <div class="fields">
            <div class="field"><span>Read Scope</span><strong>${{escapeHtml(row.readScope)}}</strong></div>
            <div class="field"><span>Production?</span><strong>${{escapeHtml(row.productionObligation)}}</strong></div>
          </div>
        </article>
      `).join('');
      const content = auditCards + traceRows + mirrorRows;
      if (!content) return '<div class="empty">没有 source remainder review 记录。</div>';
      return content;
    }}

    function renderDuplicateCards(doc) {{
      if (!doc.duplicateOwnership.length) return '<div class="empty">没有 Duplicate and Ownership Review 表。</div>';
      return doc.duplicateOwnership.map((row) => `
        <article class="card">
          <div class="card-top"><div class="code">${{escapeHtml(row.sourceRangesOrAtoms)}}</div><span class="mini-badge">${{escapeHtml(row.candidateDuplicateConflict)}}</span></div>
          <p class="summary">${{escapeHtml(row.reviewJudgment)}}</p>
          <div class="fields">
            <div class="field"><span>Resolution</span><strong>${{escapeHtml(row.resolution)}}</strong></div>
            <div class="field"><span>GA / Relation</span><strong>${{escapeHtml(row.globalAtomIdOrRelation)}}</strong></div>
          </div>
        </article>
      `).join('');
    }}

    function renderDetailPanel(doc) {{
      const warnings = data.meta.warnings.length ? `<div class="warning-box">存在 ${{data.meta.warnings.length}} 条机械解析警告。请检查 HTML 数据中的 warnings。</div>` : '';
      let content = '';
      if (state.detail === 'atoms') content = renderGaCards(doc);
      if (state.detail === 'sections') content = renderSectionCards(doc);
      if (state.detail === 'remainders') content = renderRemainderCards(doc);
      if (state.detail === 'duplicates') content = renderDuplicateCards(doc);
      el.detailPanel.innerHTML = warnings + content;
      el.detailPanel.querySelectorAll('[data-ga]').forEach((card) => {{
        card.addEventListener('click', () => selectGa(card.dataset.ga, true));
      }});
    }}

    function scrollToLine(lineNumber) {{
      const row = el.sourceLines.querySelector(`[data-line="${{lineNumber}}"]`);
      if (!row) return;
      row.scrollIntoView({{ block: 'center', behavior: 'smooth' }});
    }}

    function selectGa(gaId, shouldScroll) {{
      state.selectedGa = gaId;
      const doc = currentDoc();
      const atom = doc.effectiveAtoms.find((candidate) => candidate.globalAtomId === gaId);
      renderSourceLines(doc);
      renderDetailPanel(doc);
      if (shouldScroll && atom) scrollToLine(gaStart(atom));
    }}

    function renderSourceView(resetScroll = false) {{
      const doc = currentDoc();
      renderDocTree();
      renderOutline(doc);
      renderDocHeader(doc);
      renderSourceLines(doc);
      renderDetailPanel(doc);
      if (resetScroll) el.sourceScroll.scrollTop = 0;
    }}

    function renderTable(table, columns, rows) {{
      if (!rows.length) {{
        table.innerHTML = '<tbody><tr><td><div class="empty">没有匹配记录。</div></td></tr></tbody>';
        return;
      }}
      table.innerHTML = `
        <thead><tr>${{columns.map((col) => `<th>${{escapeHtml(col.label)}}</th>`).join('')}}</tr></thead>
        <tbody>
          ${{rows.map((row) => `<tr>${{columns.map((col) => `<td class="${{col.code ? 'table-code' : ''}}">${{escapeHtml(row[col.key] || '')}}</td>`).join('')}}</tr>`).join('')}}
        </tbody>
      `;
    }}

    function renderMapping() {{
      let rows = data.mappingRows.filter((row) => matchesText(row, state.mappingSearch));
      if (state.mappingStatus) rows = rows.filter((row) => row.globalCoverageStatus === state.mappingStatus);
      if (state.mappingDecision) rows = rows.filter((row) => row.reviewDecision === state.mappingDecision);
      if (state.mappingProjection) rows = rows.filter((row) => row.globalArtifactProjection === state.mappingProjection);
      renderTable(el.mappingTable, [
        {{ key: 'sourceDocument', label: 'Source Document', code: true }},
        {{ key: 'sourceAtomId', label: 'Source Atom', code: true }},
        {{ key: 'lines', label: 'Lines', code: true }},
        {{ key: 'globalAtomIdOrRelation', label: 'GA / Relation', code: true }},
        {{ key: 'globalCoverageStatus', label: 'Status' }},
        {{ key: 'globalArtifactProjection', label: 'Projection' }},
        {{ key: 'reviewDecision', label: 'Decision' }},
        {{ key: 'reason', label: 'Reason' }},
      ], rows);
    }}

    function riskLevel(row) {{
      const score = Number(row.severity || 0);
      if (score >= 80) return 'high';
      if (score >= 60) return 'medium';
      return 'low';
    }}

    function renderRisks() {{
      let rows = data.riskQueue.filter((row) => matchesText(row, state.riskSearch));
      if (state.riskType) rows = rows.filter((row) => row.riskType === state.riskType);
      if (state.riskLevel) rows = rows.filter((row) => riskLevel(row) === state.riskLevel);
      if (state.riskSource) rows = rows.filter((row) => Object.values(row).join(' ').toLowerCase().includes(state.riskSource));
      if (!rows.length) {{
        el.riskList.innerHTML = '<div class="empty">没有匹配的风险项。</div>';
        return;
      }}
      el.riskList.innerHTML = rows.map((row) => `
        <article class="risk-card ${{riskLevel(row)}}">
          <div class="risk-title"><strong>${{escapeHtml(row.title)}}</strong><span class="risk-type">${{escapeHtml(row.riskType)}} · ${{riskLevel(row)}}</span></div>
          <p class="summary">${{escapeHtml(row.reason)}}</p>
          <div class="fields">
            <div class="field"><span>Evidence</span><strong>${{escapeHtml(row.evidence)}}</strong></div>
            <div class="field"><span>Resolution</span><strong>${{escapeHtml(row.resolution)}}</strong></div>
          </div>
        </article>
      `).join('');
    }}

    function renderRegistry() {{
      let rows = data.globalAtoms.filter((row) => matchesText(row, state.registrySearch));
      if (state.registryStatus) rows = rows.filter((row) => row.coverageStatus === state.registryStatus);
      if (state.registryProjection) rows = rows.filter((row) => row.artifactProjection === state.registryProjection);
      if (state.registryOwner) rows = rows.filter((row) => row.ownerChange === state.registryOwner);
      renderTable(el.registryTable, [
        {{ key: 'globalAtomId', label: 'GA', code: true }},
        {{ key: 'sourceDocument', label: 'Source', code: true }},
        {{ key: 'lines', label: 'Lines', code: true }},
        {{ key: 'coverageStatus', label: 'Status' }},
        {{ key: 'artifactProjection', label: 'Projection' }},
        {{ key: 'ownerChange', label: 'Owner', code: true }},
        {{ key: 'ownerCapability', label: 'Capability', code: true }},
        {{ key: 'sourceFact', label: 'Source Fact' }},
        {{ key: 'reviewJudgment', label: 'Review Judgment' }},
      ], rows);
    }}

    function setupControls() {{
      fillSelect(el.mappingStatus, uniqueValues(data.mappingRows, 'globalCoverageStatus'), 'Coverage Status');
      fillSelect(el.mappingDecision, uniqueValues(data.mappingRows, 'reviewDecision'), 'Review Decision');
      fillSelect(el.mappingProjection, uniqueValues(data.mappingRows, 'globalArtifactProjection'), 'Projection');
      fillSelect(el.riskType, uniqueValues(data.riskQueue, 'riskType'), 'Risk Type');
      fillSelect(el.registryStatus, uniqueValues(data.globalAtoms, 'coverageStatus'), 'Coverage Status');
      fillSelect(el.registryProjection, uniqueValues(data.globalAtoms, 'artifactProjection'), 'Projection');
      fillSelect(el.registryOwner, uniqueValues(data.globalAtoms, 'ownerChange').slice(0, 80), 'Owner Change');
    }}

    function renderActiveView() {{
      if (state.view === 'sourceView') renderSourceView(false);
      if (state.view === 'mappingView') renderMapping();
      if (state.view === 'riskView') renderRisks();
      if (state.view === 'registryView') renderRegistry();
    }}

    document.querySelectorAll('.tab').forEach((button) => {{
      button.addEventListener('click', () => {{
        state.view = button.dataset.view;
        document.querySelectorAll('.tab').forEach((tab) => tab.classList.toggle('active', tab === button));
        document.querySelectorAll('.view').forEach((view) => view.classList.toggle('active', view.id === state.view));
        renderActiveView();
      }});
    }});

    document.querySelectorAll('.detail-tab').forEach((button) => {{
      button.addEventListener('click', () => {{
        state.detail = button.dataset.detail;
        document.querySelectorAll('.detail-tab').forEach((tab) => tab.classList.toggle('active', tab === button));
        renderDetailPanel(currentDoc());
      }});
    }});

    el.docSearch.addEventListener('input', (event) => {{ state.docFilter = event.target.value; renderDocTree(); }});
    el.mappingSearch.addEventListener('input', (event) => {{ state.mappingSearch = event.target.value; renderMapping(); }});
    el.mappingStatus.addEventListener('change', (event) => {{ state.mappingStatus = event.target.value; renderMapping(); }});
    el.mappingDecision.addEventListener('change', (event) => {{ state.mappingDecision = event.target.value; renderMapping(); }});
    el.mappingProjection.addEventListener('change', (event) => {{ state.mappingProjection = event.target.value; renderMapping(); }});
    el.riskSearch.addEventListener('input', (event) => {{ state.riskSearch = event.target.value; renderRisks(); }});
    el.riskType.addEventListener('change', (event) => {{ state.riskType = event.target.value; renderRisks(); }});
    el.riskLevel.addEventListener('change', (event) => {{ state.riskLevel = event.target.value; renderRisks(); }});
    el.riskSource.addEventListener('change', (event) => {{ state.riskSource = event.target.value; renderRisks(); }});
    el.registrySearch.addEventListener('input', (event) => {{ state.registrySearch = event.target.value; renderRegistry(); }});
    el.registryStatus.addEventListener('change', (event) => {{ state.registryStatus = event.target.value; renderRegistry(); }});
    el.registryProjection.addEventListener('change', (event) => {{ state.registryProjection = event.target.value; renderRegistry(); }});
    el.registryOwner.addEventListener('change', (event) => {{ state.registryOwner = event.target.value; renderRegistry(); }});

    renderStats();
    setupControls();
    renderSourceView(true);
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
        help="Output HTML path. Defaults to phase-works/phase-3/coverage-review-app/index.html.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    orchestrate_dir = args.orchestrate_dir
    if not orchestrate_dir.is_absolute():
        orchestrate_dir = repo_root / orchestrate_dir
    orchestrate_dir = orchestrate_dir.resolve()

    output = args.output
    if output is None:
        output = orchestrate_dir / "phase-works/phase-3/coverage-review-app/index.html"
    elif not output.is_absolute():
        output = repo_root / output
    output = output.resolve()

    data = build_data(repo_root, orchestrate_dir)
    write_text(output, render_html(data))

    meta = data["meta"]
    warning_count = len(meta["warnings"])  # type: ignore[index]
    print(
        "generated Phase 3 review app: "
        f"{output} ({meta['sourceCount']} source docs, "
        f"{meta['globalAtomCount']} global atoms, {meta['riskCount']} risk items, "
        f"{warning_count} warnings)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
