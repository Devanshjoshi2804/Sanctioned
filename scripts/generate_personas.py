"""CLI: write the synthetic golden personas to a JSON file for inspection.

The engine's golden tests call ``generate_personas`` directly (so they never drift
from this artifact), but a materialised JSON file is handy for browsing the
dataset and for downstream tooling.

Usage:
    uv run python scripts/generate_personas.py --n 360
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sanctioned.samples import generate_personas

_DEFAULT_OUT = Path("packages/engine/data/personas/personas.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic borrower personas.")
    parser.add_argument("--n", type=int, default=None, help="Cap the number of personas.")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT, help="Output JSON path.")
    args = parser.parse_args(argv)

    personas = generate_personas(limit=args.n)
    payload = [persona.model_dump(mode="json") for persona in personas]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload)} personas to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
