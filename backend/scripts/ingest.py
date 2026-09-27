"""CLI entry point for indexing raw Federal Supreme Court reports."""

import argparse
import sys
from pathlib import Path

# When this file is invoked directly, Python puts ``scripts/`` (rather than
# the backend directory) on ``sys.path``.  Add the project root so the
# ``app`` package can be imported with the documented command:
# ``python scripts/ingest.py --recreate``.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ingestion.indexer import build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the Chroma cassation-precedent index.")
    parser.add_argument("--recreate", action="store_true", help="Replace the existing collection before indexing.")
    args = parser.parse_args()
    case_count, chunk_count = build_index(recreate=args.recreate)
    print(f"Indexed {case_count} cassation cases into {chunk_count} chunks.")


if __name__ == "__main__":
    main()
