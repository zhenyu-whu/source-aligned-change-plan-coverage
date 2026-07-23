#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v8 bounded review result fixtures shared by contract tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Mapping

from source_aligned_trace_lib import (
    PHASE1_REVIEW_CHECKS,
    PHASE1_REVIEW_RESULT_SCHEMA,
    PHASE3_REVIEW_CHECKS,
    PHASE3_REVIEW_RESULT_SCHEMA,
    PHASE5_REVIEW_CHECKS,
    PHASE5_REVIEW_RESULT_SCHEMA,
    TRACE_CONTRACT_VERSION,
    bounded_review_result_path,
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_review_result(
    orchestrate_dir: Path,
    repo_root: Path,
    *,
    phase: str,
    round_number: int,
    authority: Mapping[str, str],
    decision: str = "passed",
    reviewer_id: str = "",
) -> Dict[str, object]:
    passed = decision == "passed"
    schemas = {
        "phase-1": PHASE1_REVIEW_RESULT_SCHEMA,
        "phase-3": PHASE3_REVIEW_RESULT_SCHEMA,
        "phase-5": PHASE5_REVIEW_RESULT_SCHEMA,
    }
    checks = {
        "phase-1": PHASE1_REVIEW_CHECKS,
        "phase-3": PHASE3_REVIEW_CHECKS,
        "phase-5": PHASE5_REVIEW_CHECKS,
    }
    payload: Dict[str, object] = {
        "trace-schema": schemas[phase],
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "phase": phase,
        "round": round_number,
        "reviewer-id": reviewer_id or f"{phase}-reviewer-{round_number}",
        "semantic-checks": [
            {
                "check": check,
                "result": "passed" if passed else "failed",
            }
            for check in checks[phase]
        ],
        "findings": (
            []
            if passed
            else [
                {
                    "rule": "outcome-contract",
                    "subject": f"{phase}-authority",
                    "finding": "当前权威仍缺少可验证的稳定结果闭环。",
                }
            ]
        ),
        "warnings": [],
        "finding-count": 0 if passed else 1,
        "decision": decision,
        "language-self-check": "所有说明均使用简体中文。",
    }
    if phase == "phase-1":
        payload.update(
            {
                "validator-status": "passed" if passed else "failed",
                "initial-framework-sha256": authority[
                    "initial-framework-sha256"
                ],
                "initial-change-plan-sha256": authority[
                    "initial-change-plan-sha256"
                ],
            }
        )
    elif phase == "phase-3":
        payload.update(
            {
                "stage": "phase-3-closure",
                "phase-2-validator-status": "passed" if passed else "failed",
                "phase-3-validator-status": "passed" if passed else "failed",
                "delivery-directive-status": "passed" if passed else "failed",
                "evidence-authority-sha256": authority[
                    "evidence-authority-sha256"
                ],
            }
        )
    else:
        payload["validator-status"] = "passed" if passed else "failed"
        payload.update(authority)

    path = bounded_review_result_path(
        orchestrate_dir,
        phase,
        round_number,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    digest = sha256_bytes(path.read_bytes())
    return {
        "round": round_number,
        "review-result-path": path.relative_to(repo_root).as_posix(),
        "review-result-sha256": digest,
    }


def gate(
    status: str,
    reviews: list[Dict[str, object]],
    repairs: list[Dict[str, object]],
    *,
    writer_id: str,
    terminal_reason: str | None = None,
) -> Dict[str, object]:
    if terminal_reason is None:
        terminal_reason = "none" if status != "blocked" else "review-blocked"
    return {
        "status": status,
        "terminal-reason": terminal_reason,
        "writer-id": writer_id,
        "reviews": reviews,
        "repairs": repairs,
    }
