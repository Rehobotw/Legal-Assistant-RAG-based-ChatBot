"""CLI entry point for indexing raw Federal Supreme Court reports."""

import argparse

from app.services.ingestion.indexer import build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the Chroma cassation-precedent index.")
    parser.add_argument("--recreate", action="store_true", help="Replace the existing collection before indexing.")
    args = parser.parse_args()
    case_count, chunk_count = build_index(recreate=args.recreate)
    print(f"Indexed {case_count} cassation cases into {chunk_count} chunks.")


if __name__ == "__main__":
    main()
