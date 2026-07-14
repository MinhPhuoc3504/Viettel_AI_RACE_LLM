#!/usr/bin/env python3
"""Sinh bảng tổng hợp tiếng Việt từ results/submissions.jsonl."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "results" / "submissions.jsonl"
DEFAULT_OUTPUT = ROOT / "results" / "LEADERBOARD_NOTES.md"


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: JSONL không hợp lệ: {exc}") from exc
    return records


def cell(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        if value.is_integer() or abs(value) >= 1000:
            return f"{value:.0f}"
        return f"{value:.4g}"
    return str(value).replace("\n", " ").replace("|", "\\|")


def risk_note(record: dict[str, Any]) -> str:
    notes: list[str] = []
    failed = record.get("failed_count")
    penalty = record.get("penalty")
    ttft_p95 = record.get("ttft_p95_ms")
    tbt = record.get("tbt_median_ms")

    if failed not in {None, 0}:
        notes.append("có request fail")
    if isinstance(penalty, (int, float)) and penalty < 1:
        notes.append("bị penalty")
    if isinstance(ttft_p95, (int, float)) and ttft_p95 > 1500:
        notes.append("TTFT p95 cao")
    if isinstance(tbt, (int, float)) and tbt > 45:
        notes.append("TBT cao")
    if not notes:
        notes.append("ổn định")
    return ", ".join(notes)


def render(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Kết Quả Các Lần Nộp",
        "",
        "File này được sinh từ `results/submissions.jsonl`.",
        "",
    ]

    if not records:
        lines.extend([
            "Chưa có kết quả submission nào được ghi lại.",
            "",
            "Sau khi portal trả kết quả, dùng `python scripts/record_submission.py ...` để ghi lại.",
            "",
        ])
        return "\n".join(lines)

    scored = [r for r in records if isinstance(r.get("score"), (int, float))]
    if scored:
        best = max(scored, key=lambda r: r["score"])
        lines.extend([
            f"Điểm tốt nhất hiện tại: **{cell(best.get('score'))}** từ profile `{cell(best.get('profile'))}`.",
            "",
        ])

    latest = records[-1]
    lines.extend([
        f"Lần nộp mới nhất: `{cell(latest.get('profile'))}` - {risk_note(latest)}.",
        "",
        "| Thời gian UTC | Profile | Trạng thái | Score | ERC | Passed SLO | TTFT p50 | TTFT p95 | TBT median | Fail | Penalty | Ghi chú |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ])
    for record in records:
        lines.append(
            "| "
            + " | ".join(
                [
                    cell(record.get("submitted_at")),
                    f"`{cell(record.get('profile'))}`",
                    cell(record.get("status")),
                    cell(record.get("score")),
                    cell(record.get("erc")),
                    cell(record.get("passed_slo")),
                    cell(record.get("ttft_p50_ms")),
                    cell(record.get("ttft_p95_ms")),
                    cell(record.get("tbt_median_ms")),
                    cell(record.get("failed_count")),
                    cell(record.get("penalty")),
                    cell(record.get("notes")),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    records = load_records(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(records), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
