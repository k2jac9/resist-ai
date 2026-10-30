"""Opt-in live smoke probe. Missing credentials or rejected output return nonzero."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Support python scripts/smoke_nebius.py from a checked-out repository.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
from src.research_review import review_descriptors  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smiles", default="CCO", help="Software test structure, not a proposed treatment")
    parser.add_argument("--output", type=Path, help="Save the evidence record to this local JSON file")
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    _, raw = review_descriptors(args.smiles, use_model=True)
    record = json.loads(raw)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw + "\n", encoding="utf-8")
    # Receipt metadata includes neither API key nor prompt text.
    print(raw)
    return 0 if record["model_status"] == "response_received" else 2


if __name__ == "__main__":
    raise SystemExit(main())
