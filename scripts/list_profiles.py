#!/usr/bin/env python3
"""Liệt kê các profile submission hiện có."""

from __future__ import annotations

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "configs" / "submissions"


def parse_scalar(value: str) -> Any:
    raw = value.strip()
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw.strip("'\"")


def load_profile(path: Path) -> dict[str, Any]:
    profile: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        profile[key.strip()] = parse_scalar(value)
    return profile


def main() -> None:
    rows: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(PROFILE_DIR.glob("*.yaml")):
        rows.append((path.name, load_profile(path)))

    print("Available submission profiles:\n")
    for filename, profile in rows:
        print(f"- {profile.get('name', filename)} ({filename})")
        print(f"  description: {profile.get('description', '-')}")
        print(f"  max_model_len: {profile.get('max_model_len', '-')}")
        print(f"  gpu_memory_utilization: {profile.get('gpu_memory_utilization', '-')}")
        print()


if __name__ == "__main__":
    main()
