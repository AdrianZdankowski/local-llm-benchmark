"""Write a VagueBench `evaluate.py` config from the endpoint environment variables.

Usage: python harness/vaguebench/vaguebench_config.py <out_config.json>

Environment:
  BENCH_BASE_URL  model under test, OpenAI-compatible (required)
  BENCH_MODEL     model name at BENCH_BASE_URL (default "local")
  JUDGE_BASE_URL  LLM judge, OpenAI-compatible; must support response_format JSON (required)
  JUDGE_MODEL     model name at JUDGE_BASE_URL (required)
  VAGUEBENCH_MAX_TURNS  max clarification turns (default 5 = repo default; the paper uses 10)

evaluate.py reads the API keys from BENCH_API_KEY / JUDGE_API_KEY. They must be non-empty;
any dummy value works for llama-server.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    config = {
        "target": {"model": os.environ.get("BENCH_MODEL", "local"),
                   "base_url": os.environ["BENCH_BASE_URL"], "api_key_env": "BENCH_API_KEY",
                   "temperature": 0.0, "timeout": 600, "max_retries": 2, "json_mode": False},
        # No separate "simulator" block: the judge also plays the simulated user (repo default).
        "judge": {"model": os.environ["JUDGE_MODEL"],
                  "base_url": os.environ["JUDGE_BASE_URL"], "api_key_env": "JUDGE_API_KEY",
                  "temperature": 0.1, "timeout": 300, "max_retries": 2, "json_mode": True},
        "max_clarification_turns": int(os.environ.get("VAGUEBENCH_MAX_TURNS", "5")),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
