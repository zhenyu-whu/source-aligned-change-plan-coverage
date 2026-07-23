#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""source-aligned v8 framework/roadmap 的严格机器契约。

本模块只验证结构、引用、图、顺序和 evidence closure；它不使用关键词判断
outcome 是否“像业务”，该语义判断属于 independent writer/reviewer。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from source_aligned_trace_lib import (
    CAPABILITY_GATE_NAMES,
    CHANGE_GATE_NAMES,
    CONSUMER_MODES,
    DELIVERY_DIRECTIVES,
    DEPENDENCY_KINDS,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
    FINAL_INTEGRATION_REVIEW_SCHEMA,
    FINAL_ROADMAP_SCHEMA,
    INITIAL_FRAMEWORK_SCHEMA,
    KEBAB_CASE_RE,
    ROADMAP_GATE_NAMES,
    TRACE_CONTRACT_VERSION,
    WORKFLOW_COMPLETION_SCHEMA,
    canonical_json_sha256,
    lexical_repo_relative_path,
    normalize_code,
    sha256_file,
)


INITIAL_FRAMEWORK_FIELDS = {
    "trace-schema",
    "trace-contract-version",
    "artifact-path",
    "delivery-semantics",
    "semantic-landscape",
    "capabilities",
    "outcome-threads",
    "changes",
    "dependency-edges",
    "guard-links",
    "change-order",
    "overlay",
    "foundation",
    "assumptions",
    "conflicts",
    "non-goals",
    "deferred",
    "language-self-check",
}
FINAL_ROADMAP_FIELDS = {
    "trace-schema",
    "trace-contract-version",
    "artifact-path",
    "semantic-landscape",
    "capabilities",
    "outcome-threads",
    "changes",
    "dependency-edges",
    "guard-links",
    "delivery-directive-resolutions",
    "change-order",
    "order-decisions",
    "prefix-reviews",
    "overlay",
    "foundation",
    "language-self-check",
}
BEHAVIOR_PROFILE_FIELDS = {
    "trigger-context",
    "normative-behavior",
    "observable-outcome-invariant",
    "important-exception-error-semantics",
    "acceptance-evidence",
}
CONSUMER_CLOSURE_FIELDS = {"mode", "ref"}
ORDER_SELECTION_BASES = {
    "current-baseline-risk-retirement",
    "explicit-source-directive",
    "foundation-first",
    "only-eligible",
    "stable-tie-break",
    "thin-observable-outcome",
}
DEPENDENCY_TERMINAL_PATHS = (
    "phase-works/phase-5/final-roadmap.json",
    "phase-works/phase-5/framework-refit-trace.json",
    "phase-works/phase-5/atom-plan-mapping.json",
    "phase-works/phase-5/capability-baseline-reconciliation.json",
    "phase-works/phase-5/final-packet-index.json",
    "trace/phase-5.trace.json",
    "change-plan.md",
)


def _exact(value: object, fields: Set[str], where: str) -> Dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{where}必须是object")
    actual = set(value)
    if actual != fields:
        raise ValueError(
            f"{where}字段必须精确为{sorted(fields)}；"
            f"缺少={sorted(fields-actual)}，多余={sorted(actual-fields)}"
        )
    return value


def _array(value: object, where: str) -> List[object]:
    if not isinstance(value, list):
        raise ValueError(f"{where}必须是array")
    return value


def _text(value: object, where: str, *, chinese: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"{where}不得为空")
    if chinese and not re.search(r"[\u4e00-\u9fff]", text):
        raise ValueError(f"{where}必须使用简体中文解释")
    return text


def _id(value: object, where: str) -> str:
    text = normalize_code(value)
    if not KEBAB_CASE_RE.fullmatch(text):
        raise ValueError(f"{where}必须是kebab-case identifier")
    return text


def _ids(value: object, where: str, *, allow_empty: bool = True) -> List[str]:
    result = [_id(item, f"{where}[{index}]") for index, item in enumerate(_array(value, where))]
    if len(result) != len(set(result)):
        raise ValueError(f"{where}不得包含重复值")
    if not allow_empty and not result:
        raise ValueError(f"{where}不得为空")
    return result


def _ga_ids(
    value: object,
    where: str,
    *,
    known_ga_ids: Optional[Set[str]],
    allow_empty: bool = True,
) -> List[str]:
    result = [normalize_code(item) for item in _array(value, where)]
    if any(not re.fullmatch(r"GA-\d{4}", item) for item in result):
        raise ValueError(f"{where}必须只包含GA-####")
    if len(result) != len(set(result)):
        raise ValueError(f"{where}不得重复")
    if not allow_empty and not result:
        raise ValueError(f"{where}不得为空")
    if known_ga_ids is not None:
        unknown = set(result) - known_ga_ids
        if unknown:
            raise ValueError(f"{where}引用未知GA：{sorted(unknown)}")
    return result


def _string_list(
    value: object,
    where: str,
    *,
    allow_empty: bool = True,
) -> List[str]:
    result = [_text(item, f"{where}[{index}]") for index, item in enumerate(_array(value, where))]
    if len(result) != len(set(result)):
        raise ValueError(f"{where}不得包含重复值")
    if not allow_empty and not result:
        raise ValueError(f"{where}不得为空")
    return result


def _load(path: Path, schema: str, fields: Set[str]) -> Dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"缺少v8 authority：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}不是合法JSON：{exc}") from exc
    data = _exact(data, fields, str(path))
    if data.get("trace-schema") != schema:
        raise ValueError(f"{path} trace-schema必须为{schema}")
    if data.get("trace-contract-version") != TRACE_CONTRACT_VERSION:
        raise ValueError(
            f"{path} trace-contract-version必须为{TRACE_CONTRACT_VERSION}；"
            f"legacy generation不允许迁移或重标"
        )
    return data


def _validate_capabilities(
    raw: object,
    *,
    final: bool,
    known_ga_ids: Optional[Set[str]],
) -> Tuple[List[Dict[str, object]], Set[str]]:
    fields = {
        "capability",
        "purpose",
        "owns",
        "excludes",
        "boundary-rationale",
        "evidence-ga-ids" if final else "source-hints",
    }
    capabilities: List[Dict[str, object]] = []
    seen: Set[str] = set()
    for index, item in enumerate(_array(raw, "capabilities")):
        row = _exact(item, fields, f"capabilities[{index}]")
        slug = _id(row.get("capability"), f"capabilities[{index}].capability")
        if slug in seen:
            raise ValueError(f"Capability重复：{slug}")
        seen.add(slug)
        for field in ("purpose", "owns", "excludes", "boundary-rationale"):
            _text(row.get(field), f"capabilities[{index}].{field}")
        if final:
            _ga_ids(
                row.get("evidence-ga-ids"),
                f"capabilities[{index}].evidence-ga-ids",
                known_ga_ids=known_ga_ids,
                allow_empty=False,
            )
        else:
            _string_list(
                row.get("source-hints"),
                f"capabilities[{index}].source-hints",
                allow_empty=False,
            )
        capabilities.append(row)
    if not capabilities:
        raise ValueError("capabilities不得为空")
    return capabilities, seen


def _validate_outcomes(
    raw: object,
    *,
    final: bool,
    known_ga_ids: Optional[Set[str]],
) -> Tuple[List[Dict[str, object]], Set[str], Set[str]]:
    common = {
        "outcome-thread-id",
        "beneficiary",
        "trigger",
        "observable-result",
        "acceptance-signal",
        "primary",
    }
    fields = common | (
        {"outcome-ga-ids", "acceptance-ga-ids", "first-realizing-change"}
        if final
        else {"source-hints"}
    )
    rows: List[Dict[str, object]] = []
    ids: Set[str] = set()
    primary: Set[str] = set()
    for index, item in enumerate(_array(raw, "outcome-threads")):
        row = _exact(item, fields, f"outcome-threads[{index}]")
        outcome_id = _id(row.get("outcome-thread-id"), f"outcome-threads[{index}].outcome-thread-id")
        if outcome_id in ids:
            raise ValueError(f"outcome thread重复：{outcome_id}")
        ids.add(outcome_id)
        for field in ("beneficiary", "trigger", "observable-result", "acceptance-signal"):
            _text(row.get(field), f"outcome-threads[{index}].{field}")
        if not isinstance(row.get("primary"), bool):
            raise ValueError(f"outcome-threads[{index}].primary必须是boolean")
        if row.get("primary"):
            primary.add(outcome_id)
        if final:
            _ga_ids(
                row.get("outcome-ga-ids"),
                f"outcome-threads[{index}].outcome-ga-ids",
                known_ga_ids=known_ga_ids,
                allow_empty=False,
            )
            _ga_ids(
                row.get("acceptance-ga-ids"),
                f"outcome-threads[{index}].acceptance-ga-ids",
                known_ga_ids=known_ga_ids,
                allow_empty=False,
            )
            _id(
                row.get("first-realizing-change"),
                f"outcome-threads[{index}].first-realizing-change",
            )
        else:
            _string_list(
                row.get("source-hints"),
                f"outcome-threads[{index}].source-hints",
                allow_empty=False,
            )
        rows.append(row)
    if not rows or not primary:
        raise ValueError("outcome-threads必须至少包含一个primary outcome")
    return rows, ids, primary


def _validate_changes(
    raw: object,
    *,
    final: bool,
    outcome_ids: Set[str],
    known_ga_ids: Optional[Set[str]],
) -> Tuple[List[Dict[str, object]], Set[str]]:
    common = {
        "change",
        "intent",
        "scope-in",
        "scope-out",
        "behavior-profile",
        "realizes-outcome-thread-ids",
        "usable-postcondition",
        "consumer-closure",
        "independent-archive",
        "split-merge-judgment",
    }
    fields = common | (
        {"outcome-ga-ids", "acceptance-ga-ids"} if final else {"source-hints"}
    )
    rows: List[Dict[str, object]] = []
    ids: Set[str] = set()
    for index, item in enumerate(_array(raw, "changes")):
        row = _exact(item, fields, f"changes[{index}]")
        slug = _id(row.get("change"), f"changes[{index}].change")
        if slug in ids:
            raise ValueError(f"Change重复：{slug}")
        ids.add(slug)
        for field in (
            "intent",
            "scope-in",
            "scope-out",
            "usable-postcondition",
            "independent-archive",
            "split-merge-judgment",
        ):
            _text(row.get(field), f"changes[{index}].{field}")
        profile = _exact(
            row.get("behavior-profile"),
            BEHAVIOR_PROFILE_FIELDS,
            f"changes[{index}].behavior-profile",
        )
        for field in BEHAVIOR_PROFILE_FIELDS:
            _text(profile.get(field), f"changes[{index}].behavior-profile.{field}")
        realized = _ids(
            row.get("realizes-outcome-thread-ids"),
            f"changes[{index}].realizes-outcome-thread-ids",
        )
        unknown = set(realized) - outcome_ids
        if unknown:
            raise ValueError(f"{slug}引用未知outcome thread：{sorted(unknown)}")
        closure = _exact(
            row.get("consumer-closure"),
            CONSUMER_CLOSURE_FIELDS,
            f"changes[{index}].consumer-closure",
        )
        mode = normalize_code(closure.get("mode"))
        if mode not in CONSUMER_MODES:
            raise ValueError(f"{slug} consumer-closure.mode非法：{mode}")
        _text(closure.get("ref"), f"changes[{index}].consumer-closure.ref")
        if final:
            _ga_ids(
                row.get("outcome-ga-ids"),
                f"changes[{index}].outcome-ga-ids",
                known_ga_ids=known_ga_ids,
            )
            _ga_ids(
                row.get("acceptance-ga-ids"),
                f"changes[{index}].acceptance-ga-ids",
                known_ga_ids=known_ga_ids,
            )
        else:
            _string_list(
                row.get("source-hints"),
                f"changes[{index}].source-hints",
                allow_empty=False,
            )
        rows.append(row)
    if not rows:
        raise ValueError("changes不得为空")
    return rows, ids


def _validate_dependencies(
    raw: object,
    *,
    final: bool,
    changes: Set[str],
    known_ga_ids: Optional[Set[str]],
) -> Tuple[List[Dict[str, object]], Set[Tuple[str, str]]]:
    common = {
        "dependency-id",
        "prerequisite-change",
        "dependent-change",
        "kind",
        "contract-id",
        "produced-contract",
        "consumed-contract",
        "counterfactual-failure",
        "co-delivery-rejection",
    }
    fields = common | ({"evidence-ga-ids"} if final else {"source-hints"})
    rows: List[Dict[str, object]] = []
    ids: Set[str] = set()
    edges: Set[Tuple[str, str]] = set()
    for index, item in enumerate(_array(raw, "dependency-edges")):
        row = _exact(item, fields, f"dependency-edges[{index}]")
        dependency_id = _id(row.get("dependency-id"), f"dependency-edges[{index}].dependency-id")
        if dependency_id in ids:
            raise ValueError(f"dependency-id重复：{dependency_id}")
        ids.add(dependency_id)
        prerequisite = _id(
            row.get("prerequisite-change"),
            f"dependency-edges[{index}].prerequisite-change",
        )
        dependent = _id(
            row.get("dependent-change"),
            f"dependency-edges[{index}].dependent-change",
        )
        if prerequisite not in changes or dependent not in changes or prerequisite == dependent:
            raise ValueError(f"{dependency_id}端点非法：{prerequisite}->{dependent}")
        if (prerequisite, dependent) in edges:
            raise ValueError(f"dependency edge重复：{prerequisite}->{dependent}")
        edges.add((prerequisite, dependent))
        if normalize_code(row.get("kind")) not in DEPENDENCY_KINDS:
            raise ValueError(f"{dependency_id}.kind非法")
        for field in (
            "contract-id",
            "produced-contract",
            "consumed-contract",
            "counterfactual-failure",
            "co-delivery-rejection",
        ):
            _text(row.get(field), f"dependency-edges[{index}].{field}")
        if final:
            _ga_ids(
                row.get("evidence-ga-ids"),
                f"dependency-edges[{index}].evidence-ga-ids",
                known_ga_ids=known_ga_ids,
                allow_empty=False,
            )
        else:
            _string_list(
                row.get("source-hints"),
                f"dependency-edges[{index}].source-hints",
                allow_empty=False,
            )
        rows.append(row)
    return rows, edges


def _validate_guards(
    raw: object,
    *,
    final: bool,
    changes: Set[str],
    outcomes: Set[str],
    first_realizers: Mapping[str, str],
    known_ga_ids: Optional[Set[str]],
) -> List[Dict[str, object]]:
    common = {
        "guard-link-id",
        "guarding-change",
        "guarded-outcome-thread-id",
        "surface-state",
    }
    fields = common | ({"evidence-ga-ids"} if final else {"source-hints"})
    rows: List[Dict[str, object]] = []
    ids: Set[str] = set()
    guarded: Set[str] = set()
    for index, item in enumerate(_array(raw, "guard-links")):
        row = _exact(item, fields, f"guard-links[{index}]")
        guard_id = _id(row.get("guard-link-id"), f"guard-links[{index}].guard-link-id")
        if guard_id in ids:
            raise ValueError(f"guard-link-id重复：{guard_id}")
        ids.add(guard_id)
        guarding_change = _id(row.get("guarding-change"), f"guard-links[{index}].guarding-change")
        outcome_id = _id(
            row.get("guarded-outcome-thread-id"),
            f"guard-links[{index}].guarded-outcome-thread-id",
        )
        if guarding_change not in changes or outcome_id not in outcomes:
            raise ValueError(f"{guard_id}引用未知Change或outcome")
        if outcome_id in guarded:
            raise ValueError(f"同一outcome不得重复guard-link：{outcome_id}")
        guarded.add(outcome_id)
        surface_state = normalize_code(row.get("surface-state"))
        if surface_state not in {"existing", "planned"}:
            raise ValueError(f"{guard_id}.surface-state非法")
        if surface_state == "planned" and first_realizers.get(outcome_id) != guarding_change:
            raise ValueError(
                f"{guard_id} planned guard必须与{outcome_id} first-realizing Change共交付"
            )
        if final:
            _ga_ids(
                row.get("evidence-ga-ids"),
                f"guard-links[{index}].evidence-ga-ids",
                known_ga_ids=known_ga_ids,
                allow_empty=False,
            )
        else:
            _string_list(
                row.get("source-hints"),
                f"guard-links[{index}].source-hints",
                allow_empty=False,
            )
        rows.append(row)
    return rows


def _validate_overlay(
    raw: object,
    *,
    final: bool,
    changes: Set[str],
    capabilities: Set[str],
) -> Tuple[List[Dict[str, object]], Set[Tuple[str, str]]]:
    rows: List[Dict[str, object]] = []
    edges: Set[Tuple[str, str]] = set()
    for index, item in enumerate(_array(raw, "overlay")):
        row = _exact(
            item,
            {"change", "capability", "capability-impact"}
            if final
            else {"change", "capability"},
            f"overlay[{index}]",
        )
        change = _id(row.get("change"), f"overlay[{index}].change")
        capability = _id(row.get("capability"), f"overlay[{index}].capability")
        if change not in changes or capability not in capabilities:
            raise ValueError(f"overlay引用未知Change/Capability：{change}/{capability}")
        if final:
            impact = normalize_code(row.get("capability-impact"))
            if impact not in {"new", "modified"}:
                raise ValueError(f"overlay impact非法：{change}/{capability}/{impact}")
        if (change, capability) in edges:
            raise ValueError(f"overlay重复：{change}/{capability}")
        edges.add((change, capability))
        rows.append(row)
    return rows, edges


def _validate_foundation(
    raw: object,
    *,
    final: bool,
    change_order: Sequence[str],
    changes_by_id: Mapping[str, Dict[str, object]],
    primary_outcomes: Set[str],
    overlay_edges: Set[Tuple[str, str]],
    known_ga_ids: Optional[Set[str]],
) -> Optional[str]:
    if raw is None:
        return None
    fields = {
        "change",
        "first-consumer-change",
        "evidence-ga-ids" if final else "source-hints",
    }
    row = _exact(raw, fields, "foundation")
    foundation = _id(row.get("change"), "foundation.change")
    consumer = _id(row.get("first-consumer-change"), "foundation.first-consumer-change")
    if len(change_order) < 2 or change_order[0] != foundation or change_order[1] != consumer:
        raise ValueError("foundation必须位于首位并由紧邻的first consumer直接消费")
    if foundation not in changes_by_id or consumer not in changes_by_id:
        raise ValueError("foundation引用未知Change")
    foundation_change = changes_by_id[foundation]
    consumer_change = changes_by_id[consumer]
    if foundation_change.get("realizes-outcome-thread-ids") != []:
        raise ValueError("foundation不得realize outcome thread")
    closure = foundation_change.get("consumer-closure")
    if not isinstance(closure, dict) or closure.get("mode") != "foundation-first-outcome" or closure.get("ref") != consumer:
        raise ValueError("foundation consumer closure必须直接指向紧邻first consumer")
    if not set(consumer_change.get("realizes-outcome-thread-ids", [])) & primary_outcomes:
        raise ValueError("foundation first consumer必须realize primary outcome")
    if any(change == foundation for change, _ in overlay_edges):
        raise ValueError("foundation不得拥有Capability overlay")
    if final:
        _ga_ids(
            row.get("evidence-ga-ids"),
            "foundation.evidence-ga-ids",
            known_ga_ids=known_ga_ids,
            allow_empty=False,
        )
    else:
        _string_list(
            row.get("source-hints"),
            "foundation.source-hints",
            allow_empty=False,
        )
    return foundation


def _validate_common(
    data: Dict[str, object],
    *,
    final: bool,
    known_ga_ids: Optional[Set[str]],
) -> Dict[str, object]:
    capabilities, capability_ids = _validate_capabilities(
        data.get("capabilities"),
        final=final,
        known_ga_ids=known_ga_ids,
    )
    outcomes, outcome_ids, primary_outcomes = _validate_outcomes(
        data.get("outcome-threads"),
        final=final,
        known_ga_ids=known_ga_ids,
    )
    changes, change_ids = _validate_changes(
        data.get("changes"),
        final=final,
        outcome_ids=outcome_ids,
        known_ga_ids=known_ga_ids,
    )
    order = _ids(data.get("change-order"), "change-order", allow_empty=False)
    if set(order) != change_ids or len(order) != len(changes):
        raise ValueError("change-order必须恰好覆盖全部Change")
    positions = {change: index for index, change in enumerate(order)}
    changes_by_id = {str(row["change"]): row for row in changes}
    for slug, row in changes_by_id.items():
        closure = row["consumer-closure"]
        mode = normalize_code(closure.get("mode"))
        ref = normalize_code(closure.get("ref"))
        realized = set(row.get("realizes-outcome-thread-ids", []))
        if mode == "same-change-outcome" and ref not in realized:
            raise ValueError(
                f"{slug} same-change-outcome closure必须引用同Change实现的outcome thread"
            )
        if mode == "foundation-first-outcome" and ref not in change_ids:
            raise ValueError(
                f"{slug} foundation-first-outcome closure必须引用Change"
            )
    first_realizers: Dict[str, str] = {}
    for outcome_id in outcome_ids:
        realizing = [
            change
            for change in order
            if outcome_id in changes_by_id[change].get("realizes-outcome-thread-ids", [])
        ]
        if not realizing:
            raise ValueError(f"outcome thread未被任何Change实现：{outcome_id}")
        first_realizers[outcome_id] = realizing[0]
    if final:
        for row in outcomes:
            outcome_id = str(row["outcome-thread-id"])
            if row.get("first-realizing-change") != first_realizers[outcome_id]:
                raise ValueError(f"{outcome_id}.first-realizing-change与change-order不一致")
    dependencies, dependency_edges = _validate_dependencies(
        data.get("dependency-edges"),
        final=final,
        changes=change_ids,
        known_ga_ids=known_ga_ids,
    )
    guards = _validate_guards(
        data.get("guard-links"),
        final=final,
        changes=change_ids,
        outcomes=outcome_ids,
        first_realizers=first_realizers,
        known_ga_ids=known_ga_ids,
    )
    overlay, overlay_edges = _validate_overlay(
        data.get("overlay"),
        final=final,
        changes=change_ids,
        capabilities=capability_ids,
    )
    foundation = _validate_foundation(
        data.get("foundation"),
        final=final,
        change_order=order,
        changes_by_id=changes_by_id,
        primary_outcomes=primary_outcomes,
        overlay_edges=overlay_edges,
        known_ga_ids=known_ga_ids,
    )
    for prerequisite, dependent in dependency_edges:
        if foundation in {prerequisite, dependent}:
            raise ValueError(
                "foundation不得作为hard dependency的prerequisite或dependent："
                f"{prerequisite}->{dependent}"
            )
        if positions[prerequisite] >= positions[dependent]:
            raise ValueError(f"hard dependency必须指向后方Change：{prerequisite}->{dependent}")
    for slug, row in changes_by_id.items():
        if slug == foundation:
            continue
        if not row.get("realizes-outcome-thread-ids"):
            raise ValueError(f"非foundation Change必须realize outcome thread：{slug}")
        closure = row.get("consumer-closure")
        if not isinstance(closure, dict) or closure.get("mode") not in {
            "same-change-outcome",
            "existing-baseline",
        }:
            raise ValueError(f"非foundation Change缺少当前consumer closure：{slug}")
        if not any(change == slug for change, _ in overlay_edges):
            raise ValueError(f"非foundation Change必须推进至少一个Capability：{slug}")
        if final:
            _ga_ids(
                row.get("outcome-ga-ids"),
                f"{slug}.outcome-ga-ids",
                known_ga_ids=known_ga_ids,
                allow_empty=False,
            )
            _ga_ids(
                row.get("acceptance-ga-ids"),
                f"{slug}.acceptance-ga-ids",
                known_ga_ids=known_ga_ids,
                allow_empty=False,
            )
    if foundation is None and not set(changes_by_id[order[0]].get("realizes-outcome-thread-ids", [])) & primary_outcomes:
        raise ValueError("无foundation时roadmap首项必须realize primary outcome")
    return {
        "capabilities": capabilities,
        "capability-ids": capability_ids,
        "outcomes": outcomes,
        "outcome-ids": outcome_ids,
        "primary-outcomes": primary_outcomes,
        "changes": changes,
        "change-ids": change_ids,
        "changes-by-id": changes_by_id,
        "change-order": order,
        "positions": positions,
        "dependencies": dependencies,
        "dependency-edges": dependency_edges,
        "guards": guards,
        "overlay": overlay,
        "overlay-edges": overlay_edges,
        "foundation": foundation,
        "first-realizers": first_realizers,
    }


def load_initial_framework(path: Path) -> Tuple[Dict[str, object], Dict[str, object]]:
    data = _load(path, INITIAL_FRAMEWORK_SCHEMA, INITIAL_FRAMEWORK_FIELDS)
    _text(data.get("artifact-path"), "initial-framework.artifact-path")
    landscape = _array(data.get("semantic-landscape"), "semantic-landscape")
    for index, item in enumerate(landscape):
        row = _exact(
            item,
            {
                "semantic-area",
                "source-backed-understanding",
                "planning-relevance",
                "source-hints",
            },
            f"semantic-landscape[{index}]",
        )
        for field in (
            "semantic-area",
            "source-backed-understanding",
            "planning-relevance",
        ):
            _text(row.get(field), f"semantic-landscape[{index}].{field}")
        _string_list(
            row.get("source-hints"),
            f"semantic-landscape[{index}].source-hints",
            allow_empty=False,
        )
    parsed = _validate_common(data, final=False, known_ga_ids=None)
    for index, item in enumerate(_array(data.get("delivery-semantics"), "delivery-semantics")):
        row = _exact(
            item,
            {
                "source-backed-statement",
                "delivery-directive",
                "affected-outcome-thread-ids",
                "planning-effect",
                "source-hint",
            },
            f"delivery-semantics[{index}]",
        )
        directive = normalize_code(row.get("delivery-directive"))
        if directive not in {*DELIVERY_DIRECTIVES, "none"}:
            raise ValueError(f"delivery-semantics[{index}].delivery-directive非法")
        _text(row.get("source-backed-statement"), f"delivery-semantics[{index}].source-backed-statement")
        _text(row.get("planning-effect"), f"delivery-semantics[{index}].planning-effect")
        _text(row.get("source-hint"), f"delivery-semantics[{index}].source-hint")
        affected = _ids(
            row.get("affected-outcome-thread-ids"),
            f"delivery-semantics[{index}].affected-outcome-thread-ids",
        )
        unknown = set(affected) - parsed["outcome-ids"]
        if unknown:
            raise ValueError(
                f"delivery-semantics[{index}]引用未知outcome thread：{sorted(unknown)}"
            )
    for field in ("assumptions", "conflicts", "non-goals", "deferred"):
        _string_list(data.get(field), field)
    _text(data.get("language-self-check"), "language-self-check", chinese=True)
    return data, parsed


def load_final_roadmap(
    path: Path,
    *,
    known_ga_ids: Optional[Set[str]] = None,
    evidence_directives: Optional[Mapping[str, Sequence[str]]] = None,
) -> Tuple[Dict[str, object], Dict[str, object]]:
    data = _load(path, FINAL_ROADMAP_SCHEMA, FINAL_ROADMAP_FIELDS)
    for index, item in enumerate(
        _array(data.get("semantic-landscape"), "semantic-landscape")
    ):
        row = _exact(
            item,
            {
                "semantic-area",
                "source-backed-understanding",
                "planning-relevance",
                "evidence-ga-ids",
            },
            f"semantic-landscape[{index}]",
        )
        for field in (
            "semantic-area",
            "source-backed-understanding",
            "planning-relevance",
        ):
            _text(row.get(field), f"semantic-landscape[{index}].{field}")
        _ga_ids(
            row.get("evidence-ga-ids"),
            f"semantic-landscape[{index}].evidence-ga-ids",
            known_ga_ids=known_ga_ids,
            allow_empty=False,
        )
    _text(data.get("artifact-path"), "final-roadmap.artifact-path")
    _text(data.get("language-self-check"), "language-self-check", chinese=True)
    parsed = _validate_common(data, final=True, known_ga_ids=known_ga_ids)
    order = parsed["change-order"]
    positions = parsed["positions"]

    resolution_pairs: Set[Tuple[str, str]] = set()
    directive_edges: Set[Tuple[str, str]] = set()
    for index, item in enumerate(
        _array(data.get("delivery-directive-resolutions"), "delivery-directive-resolutions")
    ):
        row = _exact(
            item,
            {
                "global-atom-id",
                "delivery-directive",
                "effect",
                "affected-changes",
                "scope-label",
                "ordering-relations",
                "reason",
            },
            f"delivery-directive-resolutions[{index}]",
        )
        ga = normalize_code(row.get("global-atom-id"))
        directive = normalize_code(row.get("delivery-directive"))
        if not re.fullmatch(r"GA-\d{4}", ga) or (
            known_ga_ids is not None and ga not in known_ga_ids
        ):
            raise ValueError(f"directive resolution引用未知GA：{ga}")
        if directive not in DELIVERY_DIRECTIVES:
            raise ValueError(f"directive resolution枚举非法：{directive}")
        if (ga, directive) in resolution_pairs:
            raise ValueError(f"directive resolution重复：{ga}/{directive}")
        resolution_pairs.add((ga, directive))
        if normalize_code(row.get("effect")) not in {
            "defers",
            "no-order-effect",
            "orders",
            "scopes",
        }:
            raise ValueError(f"directive resolution effect非法：{ga}/{directive}")
        effect = normalize_code(row.get("effect"))
        affected = _ids(
            row.get("affected-changes"),
            f"delivery-directive-resolutions[{index}].affected-changes",
        )
        if set(affected) - parsed["change-ids"]:
            raise ValueError(f"directive resolution引用未知Change：{ga}/{directive}")
        _text(row.get("scope-label"), f"delivery-directive-resolutions[{index}].scope-label")
        _text(row.get("reason"), f"delivery-directive-resolutions[{index}].reason", chinese=True)
        resolution_edges: Set[Tuple[str, str]] = set()
        for rel_index, relation in enumerate(
            _array(row.get("ordering-relations"), f"delivery-directive-resolutions[{index}].ordering-relations")
        ):
            relation_row = _exact(
                relation,
                {"before-change", "after-change"},
                f"delivery-directive-resolutions[{index}].ordering-relations[{rel_index}]",
            )
            before = _id(relation_row.get("before-change"), "before-change")
            after = _id(relation_row.get("after-change"), "after-change")
            if before not in parsed["change-ids"] or after not in parsed["change-ids"] or before == after:
                raise ValueError(f"directive ordering relation非法：{before}->{after}")
            if before not in affected or after not in affected:
                raise ValueError(
                    f"{ga} ordering relation端点必须包含在affected-changes："
                    f"{before}->{after}"
                )
            if positions[before] >= positions[after]:
                raise ValueError(f"roadmap违反source delivery directive：{before}->{after}")
            if (before, after) in resolution_edges:
                raise ValueError(f"{ga} ordering relation重复：{before}->{after}")
            resolution_edges.add((before, after))
        ordering_relations = row.get("ordering-relations")
        if directive == "explicit-precedence" and (
            effect != "orders" or not ordering_relations
        ):
            raise ValueError(
                f"{ga} explicit-precedence必须产生非空ordering-relations"
            )
        if directive == "milestone-scope" and effect not in {
            "scopes",
            "no-order-effect",
        }:
            raise ValueError(f"{ga} milestone-scope effect非法：{effect}")
        if directive == "explicit-deferred" and effect not in {
            "defers",
            "no-order-effect",
        }:
            raise ValueError(f"{ga} explicit-deferred effect非法：{effect}")
        if (
            directive == "explicit-deferred"
            and effect == "defers"
            and not ordering_relations
        ):
            raise ValueError(
                f"{ga} explicit-deferred defers必须产生非空ordering-relations"
            )
        if effect in {"scopes", "no-order-effect"} and ordering_relations:
            raise ValueError(
                f"{ga} {effect} directive resolution不得携带ordering-relations"
            )
        directive_edges.update(resolution_edges)
    if evidence_directives is not None:
        expected = {
            (ga, directive)
            for ga, directives in evidence_directives.items()
            for directive in directives
        }
        if resolution_pairs != expected:
            raise ValueError(
                "delivery directive resolution必须恰好覆盖冻结evidence；"
                f"缺少={sorted(expected-resolution_pairs)}，多余={sorted(resolution_pairs-expected)}"
            )

    graph_edges = set(parsed["dependency-edges"]) | directive_edges
    decisions = _array(data.get("order-decisions"), "order-decisions")
    if len(decisions) != len(order):
        raise ValueError("order-decisions必须逐位置覆盖change-order")
    selected: Set[str] = set()
    for index, item in enumerate(decisions):
        row = _exact(
            item,
            {
                "position",
                "selected-change",
                "eligible-changes",
                "selection-basis",
                "supporting-global-atom-ids",
                "reason",
            },
            f"order-decisions[{index}]",
        )
        if row.get("position") != index + 1:
            raise ValueError(f"order-decisions[{index}].position非法")
        expected_eligible = sorted(
            change
            for change in parsed["change-ids"] - selected
            if all(prerequisite in selected for prerequisite, dependent in graph_edges if dependent == change)
        )
        eligible = _ids(row.get("eligible-changes"), f"order-decisions[{index}].eligible-changes")
        if eligible != expected_eligible:
            raise ValueError(
                f"order-decisions[{index}] eligible set drift；"
                f"expected={expected_eligible} actual={eligible}"
            )
        selected_change = _id(row.get("selected-change"), f"order-decisions[{index}].selected-change")
        if selected_change != order[index] or selected_change not in eligible:
            raise ValueError(f"order-decisions[{index}] selected Change非法")
        basis = normalize_code(row.get("selection-basis"))
        if basis not in ORDER_SELECTION_BASES:
            raise ValueError(f"order-decisions[{index}].selection-basis非法")
        supporting = _ga_ids(
            row.get("supporting-global-atom-ids"),
            f"order-decisions[{index}].supporting-global-atom-ids",
            known_ga_ids=known_ga_ids,
        )
        if basis == "foundation-first" and (
            index != 0 or selected_change != parsed["foundation"]
        ):
            raise ValueError("foundation-first只能选择唯一foundation首项")
        if selected_change == parsed["foundation"] and basis != "foundation-first":
            raise ValueError("foundation首项必须使用foundation-first selection basis")
        if basis == "only-eligible" and len(eligible) != 1:
            raise ValueError("only-eligible要求当前只有一个eligible Change")
        if basis == "explicit-source-directive" and not supporting:
            raise ValueError("explicit-source-directive必须引用source-backed GA")
        _text(row.get("reason"), f"order-decisions[{index}].reason", chinese=True)
        selected.add(selected_change)

    prefix_rows = _array(data.get("prefix-reviews"), "prefix-reviews")
    if len(prefix_rows) != len(order):
        raise ValueError("prefix-reviews必须逐Change覆盖roadmap")
    for index, item in enumerate(prefix_rows):
        row = _exact(
            item,
            {
                "change",
                "delivered-prefix-outcome",
                "current-prefix-consumption",
                "guard-closure",
                "foundation-like-assessment",
                "result",
                "reason",
            },
            f"prefix-reviews[{index}]",
        )
        if row.get("change") != order[index]:
            raise ValueError(f"prefix-reviews[{index}] Change顺序漂移")
        for field in ("delivered-prefix-outcome", "current-prefix-consumption", "guard-closure"):
            _text(row.get(field), f"prefix-reviews[{index}].{field}")
        if normalize_code(row.get("foundation-like-assessment")) not in {
            "not-foundation-like",
            "valid-foundation-exception",
        }:
            raise ValueError(f"prefix-reviews[{index}].foundation-like-assessment非法")
        expected_assessment = (
            "valid-foundation-exception"
            if row.get("change") == parsed["foundation"]
            else "not-foundation-like"
        )
        if row.get("foundation-like-assessment") != expected_assessment:
            raise ValueError(
                f"prefix-reviews[{index}] foundation-like assessment与foundation authority不一致"
            )
        if row.get("result") != "passed":
            raise ValueError(f"prefix-reviews[{index}]必须passed")
        _text(row.get("reason"), f"prefix-reviews[{index}].reason", chinese=True)
    parsed["directive-edges"] = directive_edges
    return data, parsed


def terminal_authority_payload(orchestrate_dir: Path, repo_root: Path) -> Dict[str, object]:
    artifacts: List[Dict[str, str]] = []
    for relative in DEPENDENCY_TERMINAL_PATHS:
        path = orchestrate_dir / relative
        if not path.is_file():
            raise ValueError(f"terminal authority缺失：{path}")
        artifacts.append(
            {
                "artifact-path": lexical_repo_relative_path(path, repo_root),
                "sha256": sha256_file(path),
            }
        )
    return {"artifacts": artifacts}


def terminal_authority_sha256(orchestrate_dir: Path, repo_root: Path) -> str:
    return canonical_json_sha256(terminal_authority_payload(orchestrate_dir, repo_root))


def load_final_integration_review(
    path: Path,
    *,
    expected_terminal_digest: str,
) -> Dict[str, object]:
    fields = {
        "trace-schema",
        "trace-contract-version",
        "status",
        "reviewer-id",
        "terminal-authority-sha256",
        "reviewed-artifacts",
        "capability-results",
        "change-results",
        "outcome-thread-results",
        "dependency-edge-results",
        "dependency-set-result",
        "guard-link-results",
        "occurrence-chain-result",
        "findings",
        "language-self-check",
    }
    data = _load(path, FINAL_INTEGRATION_REVIEW_SCHEMA, fields)
    if data.get("status") not in {"passed", "blocked"}:
        raise ValueError("final integration review status非法")
    _text(data.get("reviewer-id"), "final integration reviewer-id")
    if data.get("terminal-authority-sha256") != expected_terminal_digest:
        raise ValueError("final integration review terminal authority digest已过期")
    reviewed = _array(data.get("reviewed-artifacts"), "reviewed-artifacts")
    for index, item in enumerate(reviewed):
        row = _exact(
            item,
            {"artifact-path", "sha256"},
            f"reviewed-artifacts[{index}]",
        )
        _text(row.get("artifact-path"), f"reviewed-artifacts[{index}].artifact-path")
        if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256", ""))):
            raise ValueError(f"reviewed-artifacts[{index}].sha256非法")

    def unit_results(
        field: str,
        id_field: str,
        *,
        gates: Optional[Sequence[str]] = None,
    ) -> None:
        seen: Set[str] = set()
        for index, item in enumerate(_array(data.get(field), field)):
            expected_fields = {
                id_field,
                "result",
                "evidence-ga-ids",
                "note",
            }
            if gates is not None:
                expected_fields.add("gate-results")
            row = _exact(item, expected_fields, f"{field}[{index}]")
            unit_id = _id(row.get(id_field), f"{field}[{index}].{id_field}")
            if unit_id in seen:
                raise ValueError(f"{field}重复：{unit_id}")
            seen.add(unit_id)
            if row.get("result") not in {"passed", "failed"}:
                raise ValueError(f"{field}[{index}].result非法")
            _ga_ids(
                row.get("evidence-ga-ids"),
                f"{field}[{index}].evidence-ga-ids",
                known_ga_ids=None,
                allow_empty=False,
            )
            _text(row.get("note"), f"{field}[{index}].note", chinese=True)
            if gates is not None:
                validate_gate_rows(
                    row.get("gate-results"),
                    gates,
                    f"{field}[{index}].gate-results",
                    known_ga_ids=None,
                )
                if row.get("result") == "passed" and any(
                    isinstance(gate, dict) and gate.get("result") != "passed"
                    for gate in row.get("gate-results", [])
                ):
                    raise ValueError(
                        f"{field}[{index}] passed不得包含failed gate"
                    )

    unit_results(
        "capability-results",
        "capability",
        gates=CAPABILITY_GATE_NAMES,
    )
    unit_results(
        "change-results",
        "change",
        gates=CHANGE_GATE_NAMES,
    )
    unit_results("outcome-thread-results", "outcome-thread-id")
    unit_results("dependency-edge-results", "dependency-id")
    unit_results("guard-link-results", "guard-link-id")
    dependency_set = _exact(
        data.get("dependency-set-result"),
        {"result", "note", "evidence-ga-ids"},
        "dependency-set-result",
    )
    if dependency_set.get("result") not in {"passed", "failed"}:
        raise ValueError("dependency-set-result.result非法")
    _text(
        dependency_set.get("note"),
        "dependency-set-result.note",
        chinese=True,
    )
    _ga_ids(
        dependency_set.get("evidence-ga-ids"),
        "dependency-set-result.evidence-ga-ids",
        known_ga_ids=None,
        allow_empty=False,
    )
    occurrence = _exact(
        data.get("occurrence-chain-result"),
        {"result", "note", "evidence-ga-ids"},
        "occurrence-chain-result",
    )
    if occurrence.get("result") not in {"passed", "failed"}:
        raise ValueError("occurrence-chain-result.result非法")
    _text(occurrence.get("note"), "occurrence-chain-result.note", chinese=True)
    _ga_ids(
        occurrence.get("evidence-ga-ids"),
        "occurrence-chain-result.evidence-ga-ids",
        known_ga_ids=None,
        allow_empty=False,
    )
    _array(data.get("findings"), "findings")
    _text(data.get("language-self-check"), "language-self-check", chinese=True)
    if data.get("status") == "passed" and data.get("findings"):
        raise ValueError("passed final integration review不得包含findings")
    if data.get("status") == "blocked" and not data.get("findings"):
        raise ValueError("blocked final integration review必须包含findings")
    if data.get("status") == "passed":
        for field in (
            "capability-results",
            "change-results",
            "outcome-thread-results",
            "dependency-edge-results",
            "guard-link-results",
        ):
            if any(
                isinstance(row, dict) and row.get("result") != "passed"
                for row in data.get(field, [])
            ):
                raise ValueError(f"passed final integration review含failed {field}")
        if occurrence.get("result") != "passed":
            raise ValueError("passed final integration review要求occurrence chain passed")
        if dependency_set.get("result") != "passed":
            raise ValueError(
                "passed final integration review要求dependency set completeness passed"
            )
    return data


def load_final_integration_review_attempt(
    path: Path,
    *,
    review_path: Path,
    repo_root: Path,
) -> Dict[str, object]:
    fields = {
        "trace-schema",
        "trace-contract-version",
        "status",
        "final-integration-review-path",
        "final-integration-review-sha256",
    }
    if path.is_symlink():
        raise ValueError("final integration review attempt不得为symlink")
    if review_path.is_symlink() or not review_path.is_file():
        raise ValueError(
            "attempt绑定的final integration review必须是普通文件"
        )
    data = _load(
        path,
        FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
        fields,
    )
    if data.get("status") != "submitted":
        raise ValueError("final integration review attempt status非法")
    expected_review_path = lexical_repo_relative_path(
        review_path,
        repo_root,
    )
    if (
        normalize_code(data.get("final-integration-review-path"))
        != expected_review_path
    ):
        raise ValueError("final integration review attempt path drift")
    if (
        data.get("final-integration-review-sha256")
        != sha256_file(review_path)
    ):
        raise ValueError("final integration review attempt digest drift")
    return data


def load_final_integration_review_attempt_result(
    path: Path,
    *,
    attempt_path: Path,
    repo_root: Path,
    expected_terminal_digest: Optional[str] = None,
) -> Dict[str, object]:
    fields = {
        "trace-schema",
        "trace-contract-version",
        "status",
        "final-integration-review-attempt-path",
        "final-integration-review-attempt-sha256",
        "terminal-authority-sha256",
        "issues",
    }
    if path.is_symlink():
        raise ValueError(
            "final integration review attempt result不得为symlink"
        )
    if attempt_path.is_symlink() or not attempt_path.is_file():
        raise ValueError(
            "attempt result绑定的attempt authority必须是普通文件"
        )
    data = _load(
        path,
        FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA,
        fields,
    )
    status = normalize_code(data.get("status"))
    if status not in {"passed", "blocked"}:
        raise ValueError(
            "final integration review attempt result status非法"
        )
    expected_attempt_path = lexical_repo_relative_path(
        attempt_path,
        repo_root,
    )
    if (
        normalize_code(
            data.get("final-integration-review-attempt-path")
        )
        != expected_attempt_path
    ):
        raise ValueError(
            "final integration review attempt result path drift"
        )
    if (
        data.get("final-integration-review-attempt-sha256")
        != sha256_file(attempt_path)
    ):
        raise ValueError(
            "final integration review attempt result digest drift"
        )
    terminal_digest = data.get("terminal-authority-sha256")
    if terminal_digest is not None and not re.fullmatch(
        r"[0-9a-f]{64}",
        str(terminal_digest),
    ):
        raise ValueError(
            "final integration review attempt result terminal digest非法"
        )
    raw_issues = _array(
        data.get("issues"),
        "final integration review attempt result issues",
    )
    if any(
        not isinstance(item, str) or not item.strip()
        for item in raw_issues
    ):
        raise ValueError(
            "final integration review attempt result issues"
            "只能包含非空string"
        )
    issues = [item.strip() for item in raw_issues]
    if status == "passed":
        if terminal_digest is None:
            raise ValueError(
                "passed final integration review attempt result"
                "必须绑定terminal digest"
            )
        if issues:
            raise ValueError(
                "passed final integration review attempt result"
                "不得包含issues"
            )
    elif not issues:
        raise ValueError(
            "blocked final integration review attempt result"
            "必须包含issues"
        )
    if (
        terminal_digest is not None
        and expected_terminal_digest is not None
        and terminal_digest != expected_terminal_digest
    ):
        raise ValueError(
            "final integration review attempt result terminal digest drift"
        )
    return data


def load_workflow_completion(
    path: Path,
    *,
    review_path: Path,
    expected_terminal_digest: str,
    repo_root: Optional[Path] = None,
) -> Dict[str, object]:
    fields = {
        "trace-schema",
        "trace-contract-version",
        "status",
        "terminal-authority-sha256",
        "final-integration-review-path",
        "final-integration-review-sha256",
        "issues",
    }
    data = _load(path, WORKFLOW_COMPLETION_SCHEMA, fields)
    if data.get("status") not in {"integration-passed", "blocked"}:
        raise ValueError("workflow completion status非法")
    if data.get("terminal-authority-sha256") != expected_terminal_digest:
        raise ValueError("workflow completion terminal authority digest已过期")
    if data.get("final-integration-review-sha256") != sha256_file(review_path):
        raise ValueError("workflow completion final review digest drift")
    actual_review_path = normalize_code(data.get("final-integration-review-path"))
    if repo_root is not None:
        expected_review_path = lexical_repo_relative_path(review_path, repo_root)
        if actual_review_path != expected_review_path:
            raise ValueError("workflow completion final review path drift")
    else:
        _text(actual_review_path, "workflow completion final review path")
    if not isinstance(data.get("issues"), list):
        raise ValueError("workflow completion issues必须是array")
    if data.get("status") == "integration-passed" and data.get("issues"):
        raise ValueError("integration-passed completion不得包含issues")
    if data.get("status") == "blocked" and not data.get("issues"):
        raise ValueError("blocked completion必须包含issues")
    return data


def validate_gate_rows(
    raw: object,
    expected_gates: Sequence[str],
    where: str,
    *,
    known_ga_ids: Optional[Set[str]],
) -> None:
    rows = _array(raw, where)
    if len(rows) != len(expected_gates):
        raise ValueError(f"{where}必须完整覆盖固定gate")
    actual: List[str] = []
    for index, item in enumerate(rows):
        row = _exact(
            item,
            {"gate", "result", "note", "evidence-ga-ids"},
            f"{where}[{index}]",
        )
        actual.append(normalize_code(row.get("gate")))
        if row.get("result") not in {"passed", "failed"}:
            raise ValueError(f"{where}[{index}].result非法")
        _text(row.get("note"), f"{where}[{index}].note", chinese=True)
        _ga_ids(
            row.get("evidence-ga-ids"),
            f"{where}[{index}].evidence-ga-ids",
            known_ga_ids=known_ga_ids,
            allow_empty=False,
        )
    if tuple(actual) != tuple(expected_gates):
        raise ValueError(f"{where} gate顺序非法：{actual}")


__all__ = [
    "CHANGE_GATE_NAMES",
    "DEPENDENCY_TERMINAL_PATHS",
    "ROADMAP_GATE_NAMES",
    "load_final_integration_review_attempt",
    "load_final_integration_review_attempt_result",
    "load_final_integration_review",
    "load_final_roadmap",
    "load_initial_framework",
    "load_workflow_completion",
    "terminal_authority_payload",
    "terminal_authority_sha256",
    "validate_gate_rows",
]
