#!/usr/bin/env python3
"""Ghi một kết quả portal vào results/submissions.jsonl."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results" / "submissions.jsonl"


def optional_float(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    return float(str(value).replace(",", "."))


def optional_int(value: str | None) -> int | None:
    if value in {None, ""}:
        return None
    return int(float(str(value).replace(",", ".")))


def file_sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_log(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Tên profile, ví dụ: v1_baseline")
    parser.add_argument("--config", type=Path, help="File config dùng cho lần nộp này")
    parser.add_argument("--compose", type=Path, default=ROOT / "docker-compose.yml")
    parser.add_argument("--portal-run-id", default="")
    parser.add_argument("--status", default="submitted", help="submitted, success, crash, oom, timeout, rejected")
    parser.add_argument("--score", default=None, help="Điểm tổng. Nếu bỏ trống sẽ dùng --final-score")
    parser.add_argument("--final-score", default=None)
    parser.add_argument("--ers", default=None)
    parser.add_argument("--erc", default=None)
    parser.add_argument("--penalty", default=None)
    parser.add_argument("--passed-slo", default=None)
    parser.add_argument("--total-count", default=None)
    parser.add_argument("--ttft-p50-ms", default=None)
    parser.add_argument("--ttft-p95-ms", default=None)
    parser.add_argument("--failed-count", default=None)
    parser.add_argument("--warmup-count", default=None)
    parser.add_argument("--tbt-median-ms", default=None)
    parser.add_argument("--accuracy", default=None)
    parser.add_argument("--accuracy-drop", default=None)
    parser.add_argument("--notes", default="")
    parser.add_argument("--log-file", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    config_path = args.config.resolve() if args.config else None
    compose_path = args.compose.resolve()
    final_score = optional_float(args.final_score)
    score = optional_float(args.score)
    if score is None:
        score = final_score

    record: dict[str, Any] = {
        "submitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profile": args.profile,
        "portal_run_id": args.portal_run_id,
        "status": args.status,
        "score": score,
        "final_score": final_score,
        "ers": optional_float(args.ers),
        "erc": optional_float(args.erc),
        "penalty": optional_float(args.penalty),
        "passed_slo": optional_int(args.passed_slo),
        "total_count": optional_int(args.total_count),
        "ttft_p50_ms": optional_float(args.ttft_p50_ms),
        "ttft_p95_ms": optional_float(args.ttft_p95_ms),
        "failed_count": optional_int(args.failed_count),
        "warmup_count": optional_int(args.warmup_count),
        "tbt_median_ms": optional_float(args.tbt_median_ms),
        "accuracy": optional_float(args.accuracy),
        "accuracy_drop": optional_float(args.accuracy_drop),
        "notes": args.notes,
        "config_path": str(config_path) if config_path else None,
        "config_sha256": file_sha256(config_path),
        "compose_path": str(compose_path),
        "compose_sha256": file_sha256(compose_path),
        "portal_log": read_log(args.log_file),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"Recorded submission result in {args.output}")


if __name__ == "__main__":
    main()
