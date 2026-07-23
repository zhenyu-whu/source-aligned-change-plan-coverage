#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish the v7 workflow completion marker after an independent final review."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from render_source_aligned_orchestrate import render_final_integration_review
from source_aligned_trace_lib import (
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA,
    FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
    FINAL_INTEGRATION_REVIEW_SCHEMA,
    MANIFEST_SCHEMA,
    PHASE_TRACE_SCHEMAS,
    TRACE_CONTRACT_VERSION,
    WORKFLOW_COMPLETION_SCHEMA,
    IssueReporter,
    normalize_code,
    read_json,
    repo_relative_path,
    sha256_file,
    write_json,
)
from source_aligned_v7_contract import (
    load_final_integration_review,
    terminal_authority_sha256,
)
from validate_source_aligned_orchestrate import (
    expected_manifest_artifacts,
    validate,
    validate_final_integration_review_candidate,
    validate_manifest,
    validate_phase_1,
    validate_phase_2,
    validate_phase_3,
    validate_phase_4,
    validate_phase_5,
)


def rel(path: Path, repo_root: Path) -> str:
    return repo_relative_path(path, repo_root)


def _attempt_path(orchestrate_dir: Path) -> Path:
    return (
        orchestrate_dir
        / FINAL_INTEGRATION_REVIEW_ATTEMPT_RELATIVE_PATH
    )


def _attempt_result_path(orchestrate_dir: Path) -> Path:
    return (
        orchestrate_dir
        / FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_RELATIVE_PATH
    )


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _exclusive_write_json(
    path: Path,
    data: Dict[str, object],
) -> None:
    """Atomically create a JSON authority without replacing an existing one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, raw_staging = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    staging = Path(raw_staging)
    payload = (
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    try:
        with os.fdopen(file_descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(staging, path)
        except FileExistsError as exc:
            raise ValueError(
                f"one-shot authority已存在，不得替换：{path}"
            ) from exc
    finally:
        if staging.exists():
            staging.unlink()


def _load_attempt(
    orchestrate_dir: Path,
    repo_root: Path,
) -> Dict[str, object]:
    path = _attempt_path(orchestrate_dir)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"final review attempt authority非法：{path}")
    data = read_json(path)
    expected_fields = {
        "trace-schema",
        "trace-contract-version",
        "status",
        "final-integration-review-path",
        "final-integration-review-sha256",
    }
    if set(data) != expected_fields:
        raise ValueError("final review attempt authority字段不符合契约")
    if data.get("trace-schema") != FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA:
        raise ValueError("final review attempt authority schema非法")
    if data.get("trace-contract-version") != TRACE_CONTRACT_VERSION:
        raise ValueError("final review attempt authority contract非法")
    if data.get("status") != "submitted":
        raise ValueError("final review attempt authority status非法")
    review_path = orchestrate_dir / "final-integration-review.json"
    if data.get("final-integration-review-path") != rel(
        review_path,
        repo_root,
    ):
        raise ValueError("final review attempt review path drift")
    if not _is_sha256(data.get("final-integration-review-sha256")):
        raise ValueError("final review attempt review digest非法")
    return data


def _assert_review_matches_attempt(
    orchestrate_dir: Path,
    attempt: Dict[str, object],
) -> None:
    review_path = orchestrate_dir / "final-integration-review.json"
    if review_path.is_symlink() or not review_path.is_file():
        raise ValueError(
            "one-shot final integration review提交后缺失或不是普通文件"
        )
    if sha256_file(review_path) != attempt.get(
        "final-integration-review-sha256"
    ):
        raise ValueError(
            "one-shot final integration review提交后发生替换或digest drift"
        )


def _terminal_digest_or_none(
    orchestrate_dir: Path,
    repo_root: Path,
) -> Optional[str]:
    try:
        return terminal_authority_sha256(orchestrate_dir, repo_root)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _terminalize_attempt(
    orchestrate_dir: Path,
    repo_root: Path,
    *,
    status: str,
    terminal_digest: Optional[str],
    issues: Sequence[str],
) -> None:
    if status not in {"passed", "blocked"}:
        raise ValueError("final review attempt result status非法")
    normalized_issues = [
        str(item).strip() for item in issues if str(item).strip()
    ]
    if status == "passed":
        if not _is_sha256(terminal_digest):
            raise ValueError(
                "passed final review attempt必须绑定terminal authority digest"
            )
        if normalized_issues:
            raise ValueError(
                "passed final review attempt不得包含issues"
            )
    elif not normalized_issues:
        raise ValueError(
            "blocked final review attempt必须包含issues"
        )
    if terminal_digest is not None and not _is_sha256(terminal_digest):
        raise ValueError("final review attempt terminal digest非法")
    attempt_path = _attempt_path(orchestrate_dir)
    _exclusive_write_json(
        _attempt_result_path(orchestrate_dir),
        {
            "trace-schema": (
                FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA
            ),
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": status,
            "final-integration-review-attempt-path": rel(
                attempt_path,
                repo_root,
            ),
            "final-integration-review-attempt-sha256": sha256_file(
                attempt_path
            ),
            "terminal-authority-sha256": terminal_digest,
            "issues": normalized_issues,
        },
    )


def _record_or_resume_attempt(
    orchestrate_dir: Path,
    repo_root: Path,
) -> Dict[str, object]:
    """Record the submitted bytes before any semantic prevalidation."""
    review_path = orchestrate_dir / "final-integration-review.json"
    attempt_path = _attempt_path(orchestrate_dir)
    result_path = _attempt_result_path(orchestrate_dir)
    if result_path.exists() or result_path.is_symlink():
        raise ValueError(
            "当前generation的one-shot final integration attempt已终态化；"
            "不得替换review或重试"
        )
    if attempt_path.exists() or attempt_path.is_symlink():
        attempt = _load_attempt(orchestrate_dir, repo_root)
        try:
            _assert_review_matches_attempt(orchestrate_dir, attempt)
        except ValueError as exc:
            _terminalize_attempt(
                orchestrate_dir,
                repo_root,
                status="blocked",
                terminal_digest=_terminal_digest_or_none(
                    orchestrate_dir,
                    repo_root,
                ),
                issues=[str(exc)],
            )
            raise
        return attempt
    if not review_path.is_file():
        raise ValueError(
            "finalizer要求现有普通文件final-integration-review.json"
        )
    _exclusive_write_json(
        attempt_path,
        {
            "trace-schema": FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
            "trace-contract-version": TRACE_CONTRACT_VERSION,
            "status": "submitted",
            "final-integration-review-path": rel(
                review_path,
                repo_root,
            ),
            "final-integration-review-sha256": sha256_file(review_path),
        },
    )
    attempt = _load_attempt(orchestrate_dir, repo_root)
    try:
        _assert_review_matches_attempt(orchestrate_dir, attempt)
    except ValueError as exc:
        _terminalize_attempt(
            orchestrate_dir,
            repo_root,
            status="blocked",
            terminal_digest=_terminal_digest_or_none(
                orchestrate_dir,
                repo_root,
            ),
            issues=[str(exc)],
        )
        raise
    return attempt


def _phase_status(orchestrate_dir: Path, phase: str) -> str:
    path = orchestrate_dir / f"trace/{phase}.trace.json"
    data = read_json(path)
    return normalize_code(data.get("status") or data.get("decision"))


def _pre_completion_validation(
    orchestrate_dir: Path,
    repo_root: Path,
) -> None:
    """Validate the pending manifest, Phase 1–5 and one-shot final review."""
    reporter = IssueReporter()
    manifest_path = orchestrate_dir / "trace/manifest.json"
    if not manifest_path.is_file():
        reporter.error(
            "finalizer-pending-manifest",
            manifest_path,
            "finalizer要求现有合法manifest v3且workflow-status=pending",
        )
    validate_manifest(
        orchestrate_dir,
        repo_root,
        reporter,
        include_workflow_artifacts=False,
        required_workflow_status="pending",
    )
    validate_phase_1(orchestrate_dir, repo_root, reporter)
    validate_phase_2(orchestrate_dir, repo_root, reporter)
    validate_phase_3(orchestrate_dir, repo_root, reporter)
    validate_phase_4(orchestrate_dir, repo_root, reporter)
    validate_phase_5(
        orchestrate_dir,
        repo_root,
        reporter,
        complete=True,
    )
    validate_final_integration_review_candidate(
        orchestrate_dir,
        repo_root,
        reporter,
    )
    if reporter.error_count:
        messages = "; ".join(
            f"{item.rule_id}: {item.message}" for item in reporter.issues
        )
        raise ValueError(f"finalizer pre-completion validation failed: {messages}")


def _assert_one_shot_finalize_state(orchestrate_dir: Path) -> None:
    """A generation gets exactly one integration finalization attempt."""
    review_path = orchestrate_dir / "final-integration-review.json"
    review_md_path = orchestrate_dir / "final-integration-review.md"
    attempt_result_path = _attempt_result_path(orchestrate_dir)
    completion_path = (
        orchestrate_dir / "trace/workflow-completion.trace.json"
    )
    stale = [
        path
        for path in (
            attempt_result_path,
            review_md_path,
            completion_path,
        )
        if path.exists() or path.is_symlink()
    ]
    if stale:
        raise ValueError(
            "当前generation已执行过one-shot final integration gate；"
            "不得重复finalize：" + ", ".join(str(path) for path in stale)
        )
    if not review_path.is_file():
        raise ValueError(
            "finalizer要求现有final-integration-review.json"
        )


def _manifest_payload(
    orchestrate_dir: Path,
    repo_root: Path,
    *,
    workflow_status: str,
    completion_staging_path: Path,
) -> Dict[str, object]:
    artifact_specs = expected_manifest_artifacts(orchestrate_dir, repo_root)
    completion_path = (
        orchestrate_dir / "trace/workflow-completion.trace.json"
    )
    artifact_specs[rel(completion_path, repo_root)] = (
        WORKFLOW_COMPLETION_SCHEMA,
        "workflow",
        "control",
        "workflow-completion",
    )
    attempt_path = _attempt_path(orchestrate_dir)
    artifact_specs[rel(attempt_path, repo_root)] = (
        FINAL_INTEGRATION_REVIEW_ATTEMPT_SCHEMA,
        "workflow",
        "control",
        "final-integration-review-attempt",
    )
    attempt_result_path = _attempt_result_path(orchestrate_dir)
    artifact_specs[rel(attempt_result_path, repo_root)] = (
        FINAL_INTEGRATION_REVIEW_ATTEMPT_RESULT_SCHEMA,
        "workflow",
        "control",
        "final-integration-review-attempt-result",
    )
    rows: List[Dict[str, object]] = []
    for artifact_path in sorted(artifact_specs):
        schema, phase, authority, role = artifact_specs[artifact_path]
        physical = (
            completion_staging_path
            if artifact_path == rel(completion_path, repo_root)
            else repo_root / artifact_path
        )
        if not physical.is_file():
            raise ValueError(f"manifest canonical artifact缺失：{physical}")
        rows.append(
            {
                "json-path": artifact_path,
                "trace-schema": schema,
                "sha256": sha256_file(physical),
                "phase": phase,
                "role": role,
                "authority": authority,
            }
        )
    return {
        "trace-schema": MANIFEST_SCHEMA,
        "trace-contract-version": TRACE_CONTRACT_VERSION,
        "authority": "control",
        "orchestrate-dir": rel(orchestrate_dir, repo_root),
        "phase-statuses": {
            phase: _phase_status(orchestrate_dir, phase)
            for phase in PHASE_TRACE_SCHEMAS
        },
        "workflow-status": workflow_status,
        "artifacts": rows,
    }


def _publish_with_rollback(
    entries: Sequence[Tuple[Path, Path]],
    transaction_root: Path,
    validate_published,
) -> None:
    backup_root = transaction_root / "backup"
    failed_root = transaction_root / "failed"
    backup_root.mkdir()
    failed_root.mkdir()
    applied: List[Tuple[Path, Optional[Path]]] = []
    try:
        for index, (staged, target) in enumerate(entries):
            if not staged.is_file() or staged.is_symlink():
                raise ValueError(f"workflow staging artifact非法：{staged}")
            if target.is_symlink():
                raise ValueError(f"workflow publish target不得为symlink：{target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            backup: Optional[Path] = None
            if target.exists():
                backup = backup_root / f"{index:02d}"
                os.replace(target, backup)
            try:
                os.replace(staged, target)
            except Exception:
                if backup is not None and backup.exists() and not target.exists():
                    os.replace(backup, target)
                raise
            applied.append((target, backup))
        validate_published()
    except Exception:
        for index, (target, backup) in reversed(list(enumerate(applied))):
            if target.exists() or target.is_symlink():
                os.replace(target, failed_root / f"{index:02d}")
            if backup is not None and backup.exists():
                os.replace(backup, target)
        raise
    finally:
        shutil.rmtree(transaction_root, ignore_errors=True)


def finalize(orchestrate_dir: Path, repo_root: Path) -> None:
    _assert_one_shot_finalize_state(orchestrate_dir)
    attempt = _record_or_resume_attempt(orchestrate_dir, repo_root)
    try:
        _assert_review_matches_attempt(orchestrate_dir, attempt)
        _pre_completion_validation(orchestrate_dir, repo_root)
        _assert_review_matches_attempt(orchestrate_dir, attempt)
        review_path = orchestrate_dir / "final-integration-review.json"
        terminal_digest = terminal_authority_sha256(
            orchestrate_dir,
            repo_root,
        )
        review = load_final_integration_review(
            review_path,
            expected_terminal_digest=terminal_digest,
        )
        _assert_review_matches_attempt(orchestrate_dir, attempt)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _terminalize_attempt(
            orchestrate_dir,
            repo_root,
            status="blocked",
            terminal_digest=_terminal_digest_or_none(
                orchestrate_dir,
                repo_root,
            ),
            issues=[str(exc)],
        )
        raise
    workflow_status = (
        "integration-passed"
        if review.get("status") == "passed"
        else "blocked"
    )
    completion_status = workflow_status
    issues = (
        []
        if workflow_status == "integration-passed"
        else [str(item) for item in review.get("findings", [])]
    )
    _terminalize_attempt(
        orchestrate_dir,
        repo_root,
        status=(
            "passed"
            if workflow_status == "integration-passed"
            else "blocked"
        ),
        terminal_digest=terminal_digest,
        issues=issues,
    )
    transaction_root = Path(
        tempfile.mkdtemp(prefix=".workflow-finalize-", dir=orchestrate_dir)
    )
    stage = transaction_root / "stage"
    stage.mkdir()
    try:
        review_md = stage / "final-integration-review.md"
        review_md.write_text(
            render_final_integration_review(orchestrate_dir, review_path),
            encoding="utf-8",
        )
        completion = stage / "workflow-completion.trace.json"
        write_json(
            completion,
            {
                "trace-schema": WORKFLOW_COMPLETION_SCHEMA,
                "trace-contract-version": TRACE_CONTRACT_VERSION,
                "status": completion_status,
                "terminal-authority-sha256": terminal_digest,
                "final-integration-review-path": rel(
                    review_path,
                    repo_root,
                ),
                "final-integration-review-sha256": sha256_file(
                    review_path
                ),
                "issues": issues,
            },
        )
        manifest = stage / "manifest.json"
        write_json(
            manifest,
            _manifest_payload(
                orchestrate_dir,
                repo_root,
                workflow_status=workflow_status,
                completion_staging_path=completion,
            ),
        )
        entries = (
            (
                review_md,
                orchestrate_dir / "final-integration-review.md",
            ),
            (
                completion,
                orchestrate_dir / "trace/workflow-completion.trace.json",
            ),
            (manifest, orchestrate_dir / "trace/manifest.json"),
        )

        def validate_final() -> None:
            result = validate(
                orchestrate_dir,
                repo_root,
                "all",
                workflow_status == "integration-passed",
            )
            if not result["ok"]:
                messages = "; ".join(
                    f"{item['rule_id']}: {item['message']}"
                    for item in result["issues"]
                )
                raise ValueError(
                    f"workflow completion post-publish validation failed: {messages}"
                )

        _publish_with_rollback(entries, transaction_root, validate_final)
    except Exception:
        shutil.rmtree(transaction_root, ignore_errors=True)
        raise


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="校验final integration review并原子发布workflow completion。",
    )
    parser.add_argument(
        "--orchestrate-dir",
        type=Path,
        default=Path("openspec/orchestrate"),
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="写入review mirror、completion与manifest commit marker",
    )
    args = parser.parse_args(argv)
    try:
        if args.write:
            finalize(args.orchestrate_dir, args.workspace_root)
        else:
            _assert_one_shot_finalize_state(args.orchestrate_dir)
            review_path = (
                args.orchestrate_dir
                / "final-integration-review.json"
            )
            if review_path.is_symlink() or not review_path.is_file():
                raise ValueError(
                    "finalizer要求现有普通文件"
                    "final-integration-review.json"
                )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("Workflow final integration contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
