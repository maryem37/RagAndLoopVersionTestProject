from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence


def _cmd_extract_e2egit(args: argparse.Namespace) -> int:
    from rag.extract_e2egit import extract_e2egit_to_csv

    stats = extract_e2egit_to_csv(
        db_path=args.db,
        out_csv_path=args.out,
        table=args.table,
        limit=args.limit,
    )
    print(f"Wrote {stats.rows_written} rows to {stats.out_csv} (table: {stats.table})")
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    from rag.ingest import ingest_to_chroma

    stats = ingest_to_chroma(
        user_stories_dir=args.user_stories_dir,
        e2egit_csv_path=args.e2egit_csv,
        persist_dir=args.persist_dir,
        collection=args.collection,
        embedding_model=args.model,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        batch_size=args.batch_size,
    )

    print(
        f"Loaded {stats.documents_loaded} docs; indexed {stats.chunks_indexed} chunks into {stats.persist_dir} (collection: {stats.collection})"
    )
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    from rag.retriever import query

    results = query(
        args.query,
        persist_dir=args.persist_dir,
        collection=args.collection,
        embedding_model=args.model,
        k=args.k,
    )

    for i, r in enumerate(results, start=1):
        print(f"[{i}] source={r.source}\n{r.content[:900]}\n")
    return 0


def _cmd_demo_gherkin(args: argparse.Namespace) -> int:
    """Preserves the original demo behavior, but behind an explicit subcommand.

    This keeps `extract-e2egit` and `ingest` usable without requiring `.env` / HF token.
    """

    from loguru import logger

    from agents.gherkin_generator import GherkinGeneratorAgent
    from graph.state import TestAutomationState

    user_story_file = Path(args.user_story_file)
    if not user_story_file.exists():
        raise FileNotFoundError(f"File not found: {user_story_file}")

    user_story_text = user_story_file.read_text(encoding="utf-8")

    state = TestAutomationState(
        user_story=user_story_text,
        swagger_spec={},
    )

    logger.info("Starting Gherkin Generator demo")
    agent = GherkinGeneratorAgent()
    updated_state = agent.generate(state)

    if updated_state.gherkin_files:
        logger.info(f"Generated {len(updated_state.gherkin_files)} feature file(s)")
        for f in updated_state.gherkin_files:
            print(f"- {f}")
    else:
        logger.warning("No Gherkin files were generated")

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python main.py",
        description="Project CLI (RAG extraction/ingest/query + existing demo commands)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- RAG commands ---
    ex = sub.add_parser("extract-e2egit", help="Generate gui_java_junit.csv from E2EGit.db")
    ex.add_argument(
        "--db",
        type=Path,
        default=Path("corpus/tier3_zenodo/z14234731_e2egit/E2EGit.db"),
        help="Path to E2EGit.db",
    )
    ex.add_argument(
        "--out",
        type=Path,
        default=Path("corpus/tier3_zenodo/z14234731_e2egit/gui_java_junit.csv"),
        help="Output CSV path (generated)",
    )
    ex.add_argument("--table", type=str, default=None, help="Optional SQLite table name to extract")
    ex.add_argument("--limit", type=int, default=None, help="Optional LIMIT (debug)")
    ex.set_defaults(func=_cmd_extract_e2egit)

    ing = sub.add_parser("ingest", help="Build chroma_db/ from corpora")
    ing.add_argument(
        "--user-stories-dir",
        type=Path,
        default=Path("corpus/tier3_zenodo/z13880060_user_stories/raw"),
    )
    ing.add_argument(
        "--e2egit-csv",
        type=Path,
        default=Path("corpus/tier3_zenodo/z14234731_e2egit/gui_java_junit.csv"),
    )
    ing.add_argument("--persist-dir", type=Path, default=Path("chroma_db"))
    ing.add_argument("--collection", type=str, default="tier3_rag")
    ing.add_argument(
        "--model",
        type=str,
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Embedding model name",
    )
    ing.add_argument("--chunk-size", type=int, default=1200)
    ing.add_argument("--chunk-overlap", type=int, default=150)
    ing.add_argument("--batch-size", type=int, default=256)
    ing.set_defaults(func=_cmd_ingest)

    q = sub.add_parser("query", help="Query the local RAG index")
    q.add_argument("query", type=str)
    q.add_argument("--persist-dir", type=Path, default=Path("chroma_db"))
    q.add_argument("--collection", type=str, default="tier3_rag")
    q.add_argument("--model", type=str, default="sentence-transformers/all-MiniLM-L6-v2")
    q.add_argument("--k", type=int, default=5)
    q.set_defaults(func=_cmd_query)

    # --- Existing demo preserved ---
    demo = sub.add_parser("demo-gherkin", help="Run the original gherkin generation demo")
    demo.add_argument(
        "--user-story-file",
        type=str,
        default="examples/comprehensive_user_story.md",
    )
    demo.set_defaults(func=_cmd_demo_gherkin)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
