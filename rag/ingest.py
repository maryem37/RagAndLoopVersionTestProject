from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class IngestStats:
    documents_loaded: int
    chunks_indexed: int
    persist_dir: Path
    collection: str


def _iter_txt_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*.txt")):
        if p.is_file():
            yield p


def _stable_id(text: str, metadata: Dict) -> str:
    h = hashlib.sha1()
    h.update(text.encode("utf-8", errors="ignore"))
    h.update(b"\x1e")
    h.update(json.dumps(metadata, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()


def _load_user_stories(user_stories_dir: Path):
    from langchain_core.documents import Document

    docs: List[Document] = []
    for fp in _iter_txt_files(user_stories_dir):
        try:
            text = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = fp.read_text(encoding="utf-8", errors="replace")

        text = text.strip()
        if not text:
            continue
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "dataset": "z13880060_user_stories",
                    "source": str(fp.as_posix()),
                    "type": "user_story",
                },
            )
        )
    return docs


def _load_gui_java_junit_csv(csv_path: Path):
    from langchain_core.documents import Document

    if not csv_path.exists():
        return []

    docs: List[Document] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            metadata = {}
            try:
                metadata_json = row.get("metadata_json")
                if metadata_json:
                    metadata = json.loads(metadata_json)
            except Exception:
                metadata = {}

            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "dataset": "z14234731_e2egit",
                        "source": str(csv_path.as_posix()),
                        "type": "e2egit",
                        "doc_id": row.get("doc_id"),
                        **metadata,
                    },
                )
            )
    return docs


def _get_text_splitter(chunk_size: int, chunk_overlap: int):
    import importlib

    RecursiveCharacterTextSplitter = None
    for module_name in ("langchain_text_splitters", "langchain.text_splitter"):
        try:
            mod = importlib.import_module(module_name)
            RecursiveCharacterTextSplitter = getattr(mod, "RecursiveCharacterTextSplitter", None)
            if RecursiveCharacterTextSplitter is not None:
                break
        except Exception:
            continue

    if RecursiveCharacterTextSplitter is None:
        raise ImportError(
            "Could not import RecursiveCharacterTextSplitter. Install/upgrade LangChain dependencies. "
            "Expected `langchain_text_splitters` to be available."
        )

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )


def _get_embeddings(model_name: str):
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=model_name)
    except Exception:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=model_name)


def ingest_to_chroma(
    user_stories_dir: Path,
    e2egit_csv_path: Path,
    persist_dir: Path,
    collection: str = "tier3_rag",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    chunk_size: int = 1200,
    chunk_overlap: int = 150,
    batch_size: int = 256,
) -> IngestStats:
    """Ingest Zenodo txt user stories + gui_java_junit.csv into Chroma."""

    user_stories_dir = Path(user_stories_dir)
    e2egit_csv_path = Path(e2egit_csv_path)
    persist_dir = Path(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    docs = []
    if user_stories_dir.exists():
        docs.extend(_load_user_stories(user_stories_dir))

    docs.extend(_load_gui_java_junit_csv(e2egit_csv_path))

    splitter = _get_text_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(docs)

    # Build stable IDs for Chroma.
    ids = [_stable_id(c.page_content, c.metadata) for c in chunks]

    embeddings = _get_embeddings(embedding_model)

    try:
        from langchain_chroma import Chroma  # type: ignore
    except Exception:
        from langchain_community.vectorstores import Chroma

    vs = Chroma(
        collection_name=collection,
        persist_directory=str(persist_dir),
        embedding_function=embeddings,
    )

    # Add in batches to reduce peak memory.
    total = 0
    for i in range(0, len(chunks), batch_size):
        batch_docs = chunks[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]
        vs.add_documents(batch_docs, ids=batch_ids)
        total += len(batch_docs)

    return IngestStats(
        documents_loaded=len(docs),
        chunks_indexed=total,
        persist_dir=persist_dir,
        collection=collection,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Ingest Tier-3 corpora into Chroma (creates chroma_db/)")
    parser.add_argument(
        "--user-stories-dir",
        type=Path,
        default=Path("corpus/tier3_zenodo/z13880060_user_stories/raw"),
    )
    parser.add_argument(
        "--e2egit-csv",
        type=Path,
        default=Path("corpus/tier3_zenodo/z14234731_e2egit/gui_java_junit.csv"),
    )
    parser.add_argument("--persist-dir", type=Path, default=Path("chroma_db"))
    parser.add_argument("--collection", type=str, default="tier3_rag")
    parser.add_argument(
        "--model",
        type=str,
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Embedding model name",
    )
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--chunk-overlap", type=int, default=150)
    parser.add_argument("--batch-size", type=int, default=256)

    args = parser.parse_args(argv)

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


if __name__ == "__main__":
    raise SystemExit(main())
