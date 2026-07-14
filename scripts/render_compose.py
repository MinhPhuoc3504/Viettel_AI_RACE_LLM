#!/usr/bin/env python3
"""Render a BTC submission docker-compose.yml from a submission profile."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "submissions" / "v1_baseline.yaml"
DEFAULT_OUTPUT = ROOT / "docker-compose.yml"


def parse_scalar(value: str) -> Any:
    raw = value.strip()
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw.strip("'\"")


def load_profile(path: Path) -> dict[str, Any]:
    profile: dict[str, Any] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"{path}:{line_no}: expected 'key: value'")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"{path}:{line_no}: empty key")
        profile[key] = parse_scalar(value)
    return profile


def require(profile: dict[str, Any], key: str) -> Any:
    if key not in profile or profile[key] in {"", None}:
        raise ValueError(f"missing required profile key: {key}")
    return profile[key]


def render(profile: dict[str, Any]) -> str:
    command = [
        f"--model={require(profile, 'model_path')}",
        f"--served-model-name={require(profile, 'served_model_name')}",
        f"--host={require(profile, 'host')}",
        f"--port={require(profile, 'port')}",
        f"--max-model-len={require(profile, 'max_model_len')}",
        f"--gpu-memory-utilization={require(profile, 'gpu_memory_utilization')}",
        f"--tensor-parallel-size={require(profile, 'tensor_parallel_size')}",
    ]

    if bool(profile.get("enable_prefix_caching", False)):
        command.append("--enable-prefix-caching")

    command_block = "\n".join(f"      - {arg}" for arg in command)

    return f"""services:
  model:
    image: {require(profile, 'image')}

    entrypoint:
      - python3
      - -m
      - vllm.entrypoints.openai.api_server

    command:
{command_block}

    ports:
      - \"{require(profile, 'port')}:{require(profile, 'port')}\"

    shm_size: \"{require(profile, 'shm_size')}\"

    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    config_path = args.config.resolve()
    output_path = args.output.resolve()
    profile = load_profile(config_path)
    output_path.write_text(render(profile), encoding="utf-8")
    print(f"Rendered {output_path} from {config_path}")


if __name__ == "__main__":
    main()

