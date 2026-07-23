#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""source_aligned_v8_contract 的聚焦单元测试。

所有 fixture 都位于 tempfile；不得读取或修改 repository 中现存的
openspec/orchestrate generation。
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Set


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from source_aligned_trace_lib import (  # noqa: E402
    CAPABILITY_GATE_NAMES,
    CHANGE_GATE_NAMES,
    FINAL_INTEGRATION_REVIEW_SCHEMA,
    FINAL_ROADMAP_SCHEMA,
    INITIAL_FRAMEWORK_SCHEMA,
    TRACE_CONTRACT_VERSION,
    WORKFLOW_COMPLETION_SCHEMA,
)
from source_aligned_v8_contract import (  # noqa: E402
    DEPENDENCY_TERMINAL_PATHS,
    load_final_integration_review,
    load_final_roadmap,
    load_initial_framework,
    load_workflow_completion,
    terminal_authority_payload,
    terminal_authority_sha256,
)


KNOWN_GA_IDS: Set[str] = {f"GA-{index:04d}" for index in range(1, 11)}
EVIDENCE_DIRECTIVES: Mapping[str, Sequence[str]] = {
    "GA-0006": ["explicit-precedence"],
}


def _behavior(label: str) -> Dict[str, str]:
    return {
        "trigger-context": f"{label}触发条件",
        "normative-behavior": f"{label}规范行为",
        "observable-outcome-invariant": f"{label}可观察结果",
        "important-exception-error-semantics": f"{label}错误语义",
        "acceptance-evidence": f"{label}验收证据",
    }


def _change(
    slug: str,
    outcome: str,
    outcome_ga: str,
    acceptance_ga: str,
    *,
    consumer_mode: str = "same-change-outcome",
    consumer_ref: Optional[str] = None,
) -> Dict[str, object]:
    return {
        "change": slug,
        "intent": f"交付{slug}的可观察结果",
        "scope-in": f"{slug}范围内",
        "scope-out": f"{slug}范围外",
        "behavior-profile": _behavior(slug),
        "realizes-outcome-thread-ids": [outcome],
        "usable-postcondition": f"{slug}形成可独立使用的后置条件",
        "consumer-closure": {
            "mode": consumer_mode,
            "ref": consumer_ref or outcome,
        },
        "independent-archive": f"{slug}可以独立验收和归档",
        "split-merge-judgment": f"{slug}保持最小完整结果边界",
        "outcome-ga-ids": [outcome_ga],
        "acceptance-ga-ids": [acceptance_ga],
    }


def _prefix_review(change: str, *, foundation: bool = False) -> Dict[str, str]:
    return {
        "change": change,
        "delivered-prefix-outcome": f"{change}完成后形成可观察前缀结果",
        "current-prefix-consumption": f"{change}结果存在当前消费者",
        "guard-closure": f"{change}所需guard已闭合",
        "foundation-like-assessment": (
            "valid-foundation-exception" if foundation else "not-foundation-like"
        ),
        "result": "passed",
        "reason": f"{change}通过前缀可用性检查",
    }


def _order_decision(
    position: int,
    selected: str,
    eligible: List[str],
    *,
    basis: str = "only-eligible",
) -> Dict[str, object]:
    return {
        "position": position,
        "selected-change": selected,
        "eligible-changes": eligible,
        "selection-basis": basis,
        "supporting-global-atom-ids": ["GA-0001"],
        "reason": f"第{position}位选择{selected}具有冻结证据",
    }


def _base_roadmap() -> Dict[str, object]:
    """两个 outcome Change、一个 hard dependency 和一个显式 precedence。"""
    return {
        "trace-schema": FINAL_ROADMAP_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "artifact-path": "openspec/orchestrate/change-plan.md",
        "semantic-landscape": [],
        "capabilities": [
            {
                "capability": "report-delivery",
                "purpose": "向当前消费者交付可观察报告",
                "owns": "报告生成、读取与通知行为",
                "excludes": "不拥有无关基础设施",
                "boundary-rationale": "以稳定业务职责划定边界",
                "evidence-ga-ids": ["GA-0001"],
            }
        ],
        "outcome-threads": [
            {
                "outcome-thread-id": "reader-gets-report",
                "beneficiary": "报告读者",
                "trigger": "读者请求报告",
                "observable-result": "读者获得可读取报告",
                "acceptance-signal": "报告可被读取并验证",
                "primary": True,
                "outcome-ga-ids": ["GA-0001"],
                "acceptance-ga-ids": ["GA-0002"],
                "first-realizing-change": "ship-report",
            },
            {
                "outcome-thread-id": "reader-gets-notice",
                "beneficiary": "报告订阅者",
                "trigger": "报告已经生成",
                "observable-result": "订阅者收到可验证通知",
                "acceptance-signal": "通知链接指向可读取报告",
                "primary": False,
                "outcome-ga-ids": ["GA-0003"],
                "acceptance-ga-ids": ["GA-0004"],
                "first-realizing-change": "notify-reader",
            },
        ],
        "changes": [
            _change("ship-report", "reader-gets-report", "GA-0001", "GA-0002"),
            _change("notify-reader", "reader-gets-notice", "GA-0003", "GA-0004"),
        ],
        "dependency-edges": [
            {
                "dependency-id": "report-before-notice",
                "prerequisite-change": "ship-report",
                "dependent-change": "notify-reader",
                "kind": "behavior-availability",
                "contract-id": "readable-report",
                "produced-contract": "ship-report产生稳定的可读取报告",
                "consumed-contract": "notify-reader消费稳定报告链接",
                "counterfactual-failure": "没有报告时通知无法指向可用结果",
                "co-delivery-rejection": "两个结果可独立验收且来源要求分步交付",
                "evidence-ga-ids": ["GA-0005"],
            }
        ],
        "guard-links": [],
        "delivery-directive-resolutions": [
            {
                "global-atom-id": "GA-0006",
                "delivery-directive": "explicit-precedence",
                "effect": "orders",
                "affected-changes": ["ship-report", "notify-reader"],
                "scope-label": "报告交付里程碑",
                "ordering-relations": [
                    {
                        "before-change": "ship-report",
                        "after-change": "notify-reader",
                    }
                ],
                "reason": "冻结来源明确要求先交付报告再发送通知",
            }
        ],
        "change-order": ["ship-report", "notify-reader"],
        "order-decisions": [
            _order_decision(1, "ship-report", ["ship-report"]),
            _order_decision(2, "notify-reader", ["notify-reader"]),
        ],
        "prefix-reviews": [
            _prefix_review("ship-report"),
            _prefix_review("notify-reader"),
        ],
        "overlay": [
            {
                "change": "ship-report",
                "capability": "report-delivery",
                "capability-impact": "new",
            },
            {
                "change": "notify-reader",
                "capability": "report-delivery",
                "capability-impact": "modified",
            },
        ],
        "foundation": None,
        "language-self-check": "所有解释字段均使用简体中文。",
    }


def _foundation_roadmap() -> Dict[str, object]:
    data = _base_roadmap()
    foundation = _change(
        "establish-base",
        "reader-gets-report",
        "GA-0001",
        "GA-0002",
        consumer_mode="foundation-first-outcome",
        consumer_ref="ship-report",
    )
    foundation["realizes-outcome-thread-ids"] = []
    foundation["outcome-ga-ids"] = []
    foundation["acceptance-ga-ids"] = []
    foundation["intent"] = "建立不含业务结果的最小基础"
    foundation["usable-postcondition"] = "紧邻的首个业务结果可以直接消费该基础"
    data["changes"] = [foundation, *data["changes"]]
    data["change-order"] = ["establish-base", "ship-report", "notify-reader"]
    data["order-decisions"] = [
        _order_decision(
            1,
            "establish-base",
            ["establish-base", "ship-report"],
            basis="foundation-first",
        ),
        _order_decision(2, "ship-report", ["ship-report"]),
        _order_decision(3, "notify-reader", ["notify-reader"]),
    ]
    data["prefix-reviews"] = [
        _prefix_review("establish-base", foundation=True),
        _prefix_review("ship-report"),
        _prefix_review("notify-reader"),
    ]
    data["foundation"] = {
        "change": "establish-base",
        "first-consumer-change": "ship-report",
        "evidence-ga-ids": ["GA-0001"],
    }
    return data


def _base_initial_framework() -> Dict[str, object]:
    data = _base_roadmap()
    data["trace-schema"] = INITIAL_FRAMEWORK_SCHEMA
    data["artifact-path"] = (
        "openspec/orchestrate/phase-works/phase-1/initial-change-plan.md"
    )
    data["delivery-semantics"] = []
    for capability in data["capabilities"]:
        capability.pop("evidence-ga-ids")
        capability["source-hints"] = ["source.md:1"]
    for outcome in data["outcome-threads"]:
        outcome.pop("outcome-ga-ids")
        outcome.pop("acceptance-ga-ids")
        outcome.pop("first-realizing-change")
        outcome["source-hints"] = ["source.md:1"]
    for change in data["changes"]:
        change.pop("outcome-ga-ids")
        change.pop("acceptance-ga-ids")
        change["source-hints"] = ["source.md:1"]
    for dependency in data["dependency-edges"]:
        dependency.pop("evidence-ga-ids")
        dependency["source-hints"] = ["source.md:1"]
    data["overlay"] = [
        {
            "change": row["change"],
            "capability": row["capability"],
        }
        for row in data["overlay"]
    ]
    data.pop("delivery-directive-resolutions")
    data.pop("order-decisions")
    data.pop("prefix-reviews")
    data["assumptions"] = []
    data["conflicts"] = []
    data["non-goals"] = []
    data["deferred"] = []
    return data


def _write_json(directory: Path, name: str, value: object) -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _load_roadmap(directory: Path, data: Dict[str, object]) -> Dict[str, object]:
    path = _write_json(directory, "final-roadmap.json", data)
    _, parsed = load_final_roadmap(
        path,
        known_ga_ids=KNOWN_GA_IDS,
        evidence_directives=EVIDENCE_DIRECTIVES,
    )
    return parsed


class ChangeAndFoundationContractTests(unittest.TestCase):
    def test_valid_ordinary_changes_have_outcome_consumer_and_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            parsed = _load_roadmap(Path(raw), _base_roadmap())

        self.assertEqual(parsed["foundation"], None)
        self.assertEqual(
            parsed["overlay-edges"],
            {
                ("ship-report", "report-delivery"),
                ("notify-reader", "report-delivery"),
            },
        )

    def test_ordinary_change_without_outcome_is_rejected(self) -> None:
        data = _base_roadmap()
        data["changes"][1]["realizes-outcome-thread-ids"] = []
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "outcome thread"):
                _load_roadmap(Path(raw), data)

    def test_ordinary_change_without_current_consumer_is_rejected(self) -> None:
        data = _base_roadmap()
        data["changes"][1]["consumer-closure"] = {
            "mode": "foundation-first-outcome",
            "ref": "ship-report",
        }
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "consumer closure"):
                _load_roadmap(Path(raw), data)

    def test_ordinary_change_without_direct_capability_overlay_is_rejected(self) -> None:
        data = _base_roadmap()
        data["overlay"] = [data["overlay"][0]]
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "推进至少一个Capability"):
                _load_roadmap(Path(raw), data)

    def test_valid_foundation_is_first_and_immediately_consumed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            parsed = _load_roadmap(Path(raw), _foundation_roadmap())

        self.assertEqual(parsed["foundation"], "establish-base")
        self.assertNotIn(
            ("establish-base", "report-delivery"),
            parsed["overlay-edges"],
        )

    def test_foundation_with_non_adjacent_declared_consumer_is_rejected(self) -> None:
        data = _foundation_roadmap()
        data["foundation"]["first-consumer-change"] = "notify-reader"
        data["changes"][0]["consumer-closure"]["ref"] = "notify-reader"
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "紧邻"):
                _load_roadmap(Path(raw), data)

    def test_foundation_with_outcome_is_rejected(self) -> None:
        data = _foundation_roadmap()
        data["changes"][0]["realizes-outcome-thread-ids"] = ["reader-gets-report"]
        data["outcome-threads"][0]["first-realizing-change"] = "establish-base"
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "foundation不得realize"):
                _load_roadmap(Path(raw), data)

    def test_foundation_with_capability_overlay_is_rejected(self) -> None:
        data = _foundation_roadmap()
        data["overlay"].insert(
            0,
            {
                "change": "establish-base",
                "capability": "report-delivery",
                "capability-impact": "new",
            },
        )
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "foundation不得拥有"):
                _load_roadmap(Path(raw), data)


class InitialOverlayContractTests(unittest.TestCase):
    def test_initial_overlay_has_only_change_and_capability(self) -> None:
        data = _base_initial_framework()
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "initial-framework.json", data)
            _, parsed = load_initial_framework(path)

        self.assertEqual(
            parsed["overlay-edges"],
            {
                ("ship-report", "report-delivery"),
                ("notify-reader", "report-delivery"),
            },
        )
        self.assertNotIn("capability-impact", parsed["overlay"][0])

    def test_initial_overlay_rejects_baseline_derived_capability_impact(self) -> None:
        data = _base_initial_framework()
        data["overlay"][0]["capability-impact"] = "new"
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "initial-framework.json", data)
            with self.assertRaisesRegex(ValueError, "字段必须精确"):
                load_initial_framework(path)

    def test_final_overlay_still_requires_capability_impact(self) -> None:
        data = _base_roadmap()
        data["overlay"][0].pop("capability-impact")
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "字段必须精确"):
                _load_roadmap(Path(raw), data)


class GuardAndDependencyContractTests(unittest.TestCase):
    def test_planned_guard_co_delivered_with_first_outcome_change_passes(self) -> None:
        data = _base_roadmap()
        data["guard-links"] = [
            {
                "guard-link-id": "notice-access-guard",
                "guarding-change": "notify-reader",
                "guarded-outcome-thread-id": "reader-gets-notice",
                "surface-state": "planned",
                "evidence-ga-ids": ["GA-0007"],
            }
        ]
        with tempfile.TemporaryDirectory() as raw:
            parsed = _load_roadmap(Path(raw), data)

        self.assertEqual(parsed["guards"][0]["guarding-change"], "notify-reader")

    def test_planned_guard_separated_from_first_outcome_change_is_rejected(self) -> None:
        data = _base_roadmap()
        data["guard-links"] = [
            {
                "guard-link-id": "notice-access-guard",
                "guarding-change": "ship-report",
                "guarded-outcome-thread-id": "reader-gets-notice",
                "surface-state": "planned",
                "evidence-ga-ids": ["GA-0007"],
            }
        ]
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "first-realizing Change共交付"):
                _load_roadmap(Path(raw), data)

    def test_hard_dependency_with_typed_contract_and_evidence_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            parsed = _load_roadmap(Path(raw), _base_roadmap())

        self.assertEqual(
            parsed["dependency-edges"],
            {("ship-report", "notify-reader")},
        )

    def test_hard_dependency_without_evidence_is_rejected(self) -> None:
        data = _base_roadmap()
        data["dependency-edges"][0]["evidence-ga-ids"] = []
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "evidence-ga-ids不得为空"):
                _load_roadmap(Path(raw), data)

    def test_hard_dependency_requires_a_supported_kind(self) -> None:
        data = _base_roadmap()
        data["dependency-edges"][0]["kind"] = "architectural-layering"
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "kind非法"):
                _load_roadmap(Path(raw), data)

    def test_hard_dependency_that_points_backward_is_rejected(self) -> None:
        data = _base_roadmap()
        data["change-order"] = ["notify-reader", "ship-report"]
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "hard dependency必须指向后方"):
                _load_roadmap(Path(raw), data)

    def test_foundation_cannot_be_hard_dependency_prerequisite(self) -> None:
        data = _foundation_roadmap()
        dependency = data["dependency-edges"][0]
        dependency["prerequisite-change"] = "establish-base"
        dependency["dependent-change"] = "ship-report"
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(
                ValueError,
                "foundation不得作为hard dependency",
            ):
                _load_roadmap(Path(raw), data)

    def test_foundation_cannot_be_hard_dependency_dependent(self) -> None:
        data = _foundation_roadmap()
        dependency = data["dependency-edges"][0]
        dependency["prerequisite-change"] = "ship-report"
        dependency["dependent-change"] = "establish-base"
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(
                ValueError,
                "foundation不得作为hard dependency",
            ):
                _load_roadmap(Path(raw), data)


class DirectiveOrderAndPrefixContractTests(unittest.TestCase):
    def test_delivery_directives_are_resolved_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            parsed = _load_roadmap(Path(raw), _base_roadmap())

        self.assertEqual(
            parsed["directive-edges"],
            {("ship-report", "notify-reader")},
        )

    def test_missing_delivery_directive_resolution_is_rejected(self) -> None:
        data = _base_roadmap()
        data["delivery-directive-resolutions"] = []
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "恰好覆盖冻结evidence"):
                _load_roadmap(Path(raw), data)

    def test_delivery_directive_order_conflict_is_rejected(self) -> None:
        data = _base_roadmap()
        relation = data["delivery-directive-resolutions"][0]["ordering-relations"][0]
        relation["before-change"] = "notify-reader"
        relation["after-change"] = "ship-report"
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "违反source delivery directive"):
                _load_roadmap(Path(raw), data)

    def test_explicit_precedence_requires_nonempty_ordering_relations(self) -> None:
        data = _base_roadmap()
        data["delivery-directive-resolutions"][0]["ordering-relations"] = []
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "必须产生非空ordering-relations"):
                _load_roadmap(Path(raw), data)

    def test_milestone_scope_rejects_orders_effect(self) -> None:
        data = _base_roadmap()
        resolution = data["delivery-directive-resolutions"][0]
        resolution["delivery-directive"] = "milestone-scope"
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "milestone-scope effect非法"):
                _load_roadmap(Path(raw), data)

    def test_explicit_deferred_defers_requires_nonempty_ordering_relations(self) -> None:
        data = _base_roadmap()
        resolution = data["delivery-directive-resolutions"][0]
        resolution["delivery-directive"] = "explicit-deferred"
        resolution["effect"] = "defers"
        resolution["ordering-relations"] = []
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(
                ValueError,
                "explicit-deferred defers必须产生非空ordering-relations",
            ):
                path = _write_json(Path(raw), "final-roadmap.json", data)
                load_final_roadmap(
                    path,
                    known_ga_ids=KNOWN_GA_IDS,
                    evidence_directives={"GA-0006": ["explicit-deferred"]},
                )

    def test_explicit_deferred_defers_enters_ordering_graph(self) -> None:
        data = _base_roadmap()
        resolution = data["delivery-directive-resolutions"][0]
        resolution["delivery-directive"] = "explicit-deferred"
        resolution["effect"] = "defers"
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "final-roadmap.json", data)
            _, parsed = load_final_roadmap(
                path,
                known_ga_ids=KNOWN_GA_IDS,
                evidence_directives={"GA-0006": ["explicit-deferred"]},
            )

        self.assertEqual(
            parsed["directive-edges"],
            {("ship-report", "notify-reader")},
        )

    def test_explicit_deferred_no_order_effect_allows_no_relations(self) -> None:
        data = _base_roadmap()
        resolution = data["delivery-directive-resolutions"][0]
        resolution["delivery-directive"] = "explicit-deferred"
        resolution["effect"] = "no-order-effect"
        resolution["ordering-relations"] = []
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "final-roadmap.json", data)
            _, parsed = load_final_roadmap(
                path,
                known_ga_ids=KNOWN_GA_IDS,
                evidence_directives={"GA-0006": ["explicit-deferred"]},
            )

        self.assertEqual(parsed["directive-edges"], set())

    def test_ordering_relation_endpoints_must_be_affected_changes(self) -> None:
        data = _base_roadmap()
        data["delivery-directive-resolutions"][0]["affected-changes"] = [
            "ship-report"
        ]
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(
                ValueError,
                "端点必须包含在affected-changes",
            ):
                _load_roadmap(Path(raw), data)

    def test_order_decision_eligible_set_must_match_dependency_graph(self) -> None:
        data = _base_roadmap()
        data["order-decisions"][0]["eligible-changes"] = [
            "notify-reader",
            "ship-report",
        ]
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "eligible set drift"):
                _load_roadmap(Path(raw), data)

    def test_order_decision_must_select_change_order_item(self) -> None:
        data = _base_roadmap()
        data["order-decisions"][0]["selected-change"] = "notify-reader"
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "selected Change非法"):
                _load_roadmap(Path(raw), data)

    def test_prefix_review_must_cover_order_and_pass(self) -> None:
        data = _base_roadmap()
        data["prefix-reviews"][1]["result"] = "failed"
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "必须passed"):
                _load_roadmap(Path(raw), data)

    def test_ordinary_prefix_cannot_claim_foundation_exception(self) -> None:
        data = _base_roadmap()
        data["prefix-reviews"][0][
            "foundation-like-assessment"
        ] = "valid-foundation-exception"
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "与foundation authority不一致"):
                _load_roadmap(Path(raw), data)

    def test_foundation_prefix_must_claim_foundation_exception(self) -> None:
        data = _foundation_roadmap()
        data["prefix-reviews"][0]["foundation-like-assessment"] = "not-foundation-like"
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "与foundation authority不一致"):
                _load_roadmap(Path(raw), data)


class TerminalDigestContractTests(unittest.TestCase):
    def _terminal_tree(self, root: Path) -> Path:
        orchestrate = root / "openspec" / "orchestrate"
        for index, relative in enumerate(DEPENDENCY_TERMINAL_PATHS, start=1):
            path = orchestrate / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"terminal-artifact-{index}\n".encode("utf-8"))
        return orchestrate

    def test_terminal_digest_uses_exact_fixed_seven_path_payload(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate = self._terminal_tree(root)
            payload = terminal_authority_payload(orchestrate, root)
            digest = terminal_authority_sha256(orchestrate, root)
            expected_rows = []
            for relative in DEPENDENCY_TERMINAL_PATHS:
                content = (orchestrate / relative).read_bytes()
                expected_rows.append(
                    {
                        "artifact-path": f"openspec/orchestrate/{relative}",
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                )
            expected_payload = {"artifacts": expected_rows}
            expected_digest = hashlib.sha256(
                json.dumps(
                    expected_payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()

        self.assertEqual(len(payload["artifacts"]), 7)
        self.assertEqual(payload, expected_payload)
        self.assertEqual(digest, expected_digest)

    def test_terminal_digest_changes_when_authority_changes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate = self._terminal_tree(root)
            before = terminal_authority_sha256(orchestrate, root)
            (orchestrate / "change-plan.md").write_text(
                "changed terminal authority\n",
                encoding="utf-8",
            )
            after = terminal_authority_sha256(orchestrate, root)

        self.assertNotEqual(before, after)

    def test_terminal_digest_rejects_missing_fixed_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            orchestrate = self._terminal_tree(root)
            (orchestrate / "trace" / "phase-5.trace.json").unlink()
            with self.assertRaisesRegex(ValueError, "terminal authority缺失"):
                terminal_authority_sha256(orchestrate, root)


def _gate_results(gates: Sequence[str]) -> List[Dict[str, object]]:
    return [
        {
            "gate": gate,
            "result": "passed",
            "note": f"{gate}具有冻结证据并通过审查",
            "evidence-ga-ids": ["GA-0001"],
        }
        for gate in gates
    ]


def _review(digest: str, *, status: str = "passed") -> Dict[str, object]:
    return {
        "trace-schema": FINAL_INTEGRATION_REVIEW_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "status": status,
        "reviewer-id": "fresh-reviewer-1",
        "terminal-authority-sha256": digest,
        "reviewed-artifacts": [
            {
                "artifact-path": "openspec/orchestrate/change-plan.md",
                "sha256": "0" * 64,
            }
        ],
        "capability-results": [
            {
                "capability": "report-delivery",
                "result": "passed",
                "evidence-ga-ids": ["GA-0001"],
                "note": "Capability边界与直接推进关系通过审查",
                "gate-results": _gate_results(CAPABILITY_GATE_NAMES),
            }
        ],
        "change-results": [
            {
                "change": "ship-report",
                "result": "passed",
                "evidence-ga-ids": ["GA-0001"],
                "note": "Change结果、消费者和验收闭环通过审查",
                "gate-results": _gate_results(CHANGE_GATE_NAMES),
            }
        ],
        "outcome-thread-results": [
            {
                "outcome-thread-id": "reader-gets-report",
                "result": "passed",
                "evidence-ga-ids": ["GA-0001"],
                "note": "Outcome thread可观察且可验收",
            }
        ],
        "dependency-edge-results": [
            {
                "dependency-id": "report-before-notice",
                "result": "passed",
                "evidence-ga-ids": ["GA-0005"],
                "note": "依赖边具有稳定产出与消费关系",
            }
        ],
        "dependency-set-result": {
            "result": "passed",
            "evidence-ga-ids": ["GA-0001", "GA-0005"],
            "note": "逐Change消费者闭包未发现遗漏的hard dependency边",
        },
        "guard-link-results": [
            {
                "guard-link-id": "notice-access-guard",
                "result": "passed",
                "evidence-ga-ids": ["GA-0007"],
                "note": "Guard与首次受保护结果共同交付",
            }
        ],
        "occurrence-chain-result": {
            "result": "passed",
            "note": "所有 occurrence 分配链均一致",
            "evidence-ga-ids": ["GA-0001"],
        },
        "findings": [] if status == "passed" else [{"finding": "存在阻断问题"}],
        "language-self-check": "所有审查说明均使用简体中文。",
    }


def _completion(
    digest: str,
    review_path: Path,
    *,
    status: str = "integration-passed",
    review_repo_path: str = "openspec/orchestrate/final-integration-review.json",
) -> Dict[str, object]:
    return {
        "trace-schema": WORKFLOW_COMPLETION_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "status": status,
        "terminal-authority-sha256": digest,
        "final-integration-review-path": review_repo_path,
        "final-integration-review-sha256": hashlib.sha256(
            review_path.read_bytes()
        ).hexdigest(),
        "issues": [] if status == "integration-passed" else ["终态审查阻断"],
    }


class FinalReviewAndCompletionContractTests(unittest.TestCase):
    DIGEST = "a" * 64

    def test_valid_passed_final_review_and_completion_load(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo_root = Path(raw)
            directory = repo_root / "openspec" / "orchestrate"
            review_path = _write_json(
                directory,
                "final-integration-review.json",
                _review(self.DIGEST),
            )
            review = load_final_integration_review(
                review_path,
                expected_terminal_digest=self.DIGEST,
            )
            completion_path = _write_json(
                directory,
                "workflow-completion.trace.json",
                _completion(self.DIGEST, review_path),
            )
            completion = load_workflow_completion(
                completion_path,
                review_path=review_path,
                expected_terminal_digest=self.DIGEST,
                repo_root=repo_root,
            )

        self.assertEqual(review["status"], "passed")
        self.assertEqual(completion["status"], "integration-passed")

    def test_final_review_rejects_extra_top_level_field(self) -> None:
        data = _review(self.DIGEST)
        data["unexpected"] = True
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "review.json", data)
            with self.assertRaisesRegex(ValueError, "多余"):
                load_final_integration_review(
                    path,
                    expected_terminal_digest=self.DIGEST,
                )

    def test_final_review_rejects_extra_occurrence_chain_field(self) -> None:
        data = _review(self.DIGEST)
        data["occurrence-chain-result"]["unexpected"] = True
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "review.json", data)
            with self.assertRaisesRegex(ValueError, "occurrence-chain-result字段"):
                load_final_integration_review(
                    path,
                    expected_terminal_digest=self.DIGEST,
                )

    def test_final_review_rejects_malformed_reviewed_artifact_digest(self) -> None:
        data = _review(self.DIGEST)
        data["reviewed-artifacts"][0]["sha256"] = "not-a-digest"
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "review.json", data)
            with self.assertRaisesRegex(ValueError, "sha256非法"):
                load_final_integration_review(
                    path,
                    expected_terminal_digest=self.DIGEST,
                )

    def test_final_review_rejects_duplicate_unit_results(self) -> None:
        data = _review(self.DIGEST)
        data["capability-results"].append(
            copy.deepcopy(data["capability-results"][0])
        )
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "review.json", data)
            with self.assertRaisesRegex(ValueError, "capability-results重复"):
                load_final_integration_review(
                    path,
                    expected_terminal_digest=self.DIGEST,
                )

    def test_final_review_requires_complete_ordered_change_gates(self) -> None:
        data = _review(self.DIGEST)
        data["change-results"][0]["gate-results"].pop()
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "review.json", data)
            with self.assertRaisesRegex(ValueError, "完整覆盖固定gate"):
                load_final_integration_review(
                    path,
                    expected_terminal_digest=self.DIGEST,
                )

    def test_passed_unit_rejects_failed_gate(self) -> None:
        data = _review(self.DIGEST)
        data["change-results"][0]["gate-results"][0]["result"] = "failed"
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "review.json", data)
            with self.assertRaisesRegex(ValueError, "passed不得包含failed gate"):
                load_final_integration_review(
                    path,
                    expected_terminal_digest=self.DIGEST,
                )

    def test_passed_final_review_rejects_failed_unit_result(self) -> None:
        data = _review(self.DIGEST)
        data["outcome-thread-results"][0]["result"] = "failed"
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "review.json", data)
            with self.assertRaisesRegex(ValueError, "含failed outcome-thread-results"):
                load_final_integration_review(
                    path,
                    expected_terminal_digest=self.DIGEST,
                )

    def test_passed_final_review_requires_passed_occurrence_chain(self) -> None:
        data = _review(self.DIGEST)
        data["occurrence-chain-result"]["result"] = "failed"
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "review.json", data)
            with self.assertRaisesRegex(ValueError, "occurrence chain passed"):
                load_final_integration_review(
                    path,
                    expected_terminal_digest=self.DIGEST,
                )

    def test_passed_final_review_rejects_findings(self) -> None:
        data = _review(self.DIGEST)
        data["findings"] = [{"finding": "不应被忽略"}]
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(Path(raw), "review.json", data)
            with self.assertRaisesRegex(ValueError, "不得包含findings"):
                load_final_integration_review(
                    path,
                    expected_terminal_digest=self.DIGEST,
                )

    def test_final_review_rejects_stale_terminal_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = _write_json(
                Path(raw),
                "review.json",
                _review("b" * 64),
            )
            with self.assertRaisesRegex(ValueError, "digest已过期"):
                load_final_integration_review(
                    path,
                    expected_terminal_digest=self.DIGEST,
                )

    def test_completion_rejects_extra_field(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            review_path = _write_json(
                directory,
                "review.json",
                _review(self.DIGEST),
            )
            data = _completion(self.DIGEST, review_path)
            data["unexpected"] = True
            completion_path = _write_json(directory, "completion.json", data)
            with self.assertRaisesRegex(ValueError, "多余"):
                load_workflow_completion(
                    completion_path,
                    review_path=review_path,
                    expected_terminal_digest=self.DIGEST,
                )

    def test_completion_rejects_review_digest_drift(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            review_path = _write_json(
                directory,
                "review.json",
                _review(self.DIGEST),
            )
            data = _completion(self.DIGEST, review_path)
            data["final-integration-review-sha256"] = "0" * 64
            completion_path = _write_json(directory, "completion.json", data)
            with self.assertRaisesRegex(ValueError, "review digest drift"):
                load_workflow_completion(
                    completion_path,
                    review_path=review_path,
                    expected_terminal_digest=self.DIGEST,
                )

    def test_completion_rejects_review_path_drift_against_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo_root = Path(raw)
            directory = repo_root / "openspec" / "orchestrate"
            review_path = _write_json(
                directory,
                "final-integration-review.json",
                _review(self.DIGEST),
            )
            data = _completion(
                self.DIGEST,
                review_path,
                review_repo_path="openspec/orchestrate/other-review.json",
            )
            completion_path = _write_json(
                directory,
                "workflow-completion.trace.json",
                data,
            )
            with self.assertRaisesRegex(ValueError, "final review path drift"):
                load_workflow_completion(
                    completion_path,
                    review_path=review_path,
                    expected_terminal_digest=self.DIGEST,
                    repo_root=repo_root,
                )

    def test_integration_passed_completion_rejects_issues(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            review_path = _write_json(
                directory,
                "review.json",
                _review(self.DIGEST),
            )
            data = _completion(self.DIGEST, review_path)
            data["issues"] = ["不应被忽略"]
            completion_path = _write_json(directory, "completion.json", data)
            with self.assertRaisesRegex(ValueError, "不得包含issues"):
                load_workflow_completion(
                    completion_path,
                    review_path=review_path,
                    expected_terminal_digest=self.DIGEST,
                )


if __name__ == "__main__":
    unittest.main()
