#!/usr/bin/env python3
"""Gợi ý profile tiếp theo dựa trên kết quả portal mới nhất."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "submissions.jsonl"


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    records = load_records(RESULTS)
    if not records:
        print("No result recorded yet. Submit v1_baseline first.")
        print("Suggested profile: configs/submissions/v1_baseline.yaml")
        return

    latest = records[-1]
    profile = latest.get("profile")
    failed = latest.get("failed_count")
    penalty = latest.get("penalty")
    ttft_p95 = latest.get("ttft_p95_ms")
    tbt = latest.get("tbt_median_ms")

    print(f"Latest result: {profile}")
    print(f"score={latest.get('score')} erc={latest.get('erc')} ttft_p95_ms={ttft_p95} tbt_median_ms={tbt}")

    if failed not in {None, 0} or latest.get("status") not in {"success", "submitted"}:
        print("\nSuggested next profile: configs/submissions/v1_safe_memory.yaml")
        print("Reason: failure/crash signal; reduce memory pressure first.")
        return

    if isinstance(penalty, (int, float)) and penalty < 1:
        print("\nSuggested next step: rollback to the latest profile without penalty.")
        print("Reason: accuracy penalty strongly hurts final score.")
        return

    if isinstance(ttft_p95, (int, float)) and ttft_p95 > 5000:
        print("\nSuggested next profile: configs/submissions/v2_short_context.yaml")
        print("Reason: TTFT p95 is very high; reduce max_model_len to lower KV-cache pressure.")
        return

    if isinstance(tbt, (int, float)) and tbt > 45:
        print("\nSuggested next profile: configs/submissions/v2_high_memory.yaml")
        print("Reason: TBT is high but the run is stable; try slightly more vLLM memory.")
        return

    print("\nSuggested next step: keep current profile as a good baseline and tune one small change at a time.")


if __name__ == "__main__":
    main()
