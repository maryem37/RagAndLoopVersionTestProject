from __future__ import annotations

import csv
import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


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


def _make_unique_ids(ids: Sequence[str]) -> List[str]:
    """
    Ensure IDs are unique within a single Chroma upsert.

    GivenWhenThen contains some duplicated records/chunks. Chroma rejects
    duplicate IDs in the same upsert payload, so we keep the base hash and
    append a deterministic suffix only for repeated occurrences.
    """
    seen: Dict[str, int] = {}
    unique_ids: List[str] = []

    for base_id in ids:
        occurrence = seen.get(base_id, 0)
        if occurrence == 0:
            unique_ids.append(base_id)
        else:
            unique_ids.append(f"{base_id}:{occurrence + 1}")
        seen[base_id] = occurrence + 1

    return unique_ids


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


def _load_givenwhenthen_json(
    json_path: Path,
    max_records: Optional[int] = None,
):
    """
    Load the GivenWhenThen JSON dataset and turn it into retrievable documents.

    One dataset record can produce:
      - a feature/spec document
      - a step definitions document
      - one document per linked system code file
    """
    from langchain_core.documents import Document

    if not json_path.exists():
        return []

    with json_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict):
        records = raw.get("records") or raw.get("items") or raw.get("data") or []
    elif isinstance(raw, list):
        records = raw
    else:
        records = []

    if max_records is not None:
        records = records[: max(0, int(max_records))]

    docs: List[Document] = []
    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            continue

        repository = str(record.get("repository") or "").strip()
        language = str(record.get("language") or "").strip()
        feature_file = str(record.get("feature_file") or "").strip()
        feature_content = str(record.get("feature_content") or "").strip()
        step_file = str(record.get("step_definitions_file") or "").strip()
        step_content = str(record.get("step_definitions_content") or "").strip()
        repo_path = str(record.get("normalized_repo_path") or "").strip()

        base_metadata: Dict[str, Any] = {
            "dataset": "GivenWhenThen",
            "source": str(json_path.as_posix()),
            "record_index": idx,
            "repository": repository,
            "language": language,
            "normalized_repo_path": repo_path,
        }

        if feature_content:
            feature_text_parts = []
            if repository:
                feature_text_parts.append(f"Repository: {repository}")
            if language:
                feature_text_parts.append(f"Language: {language}")
            if feature_file:
                feature_text_parts.append(f"Feature file: {feature_file}")
            feature_text_parts.append("Feature content:")
            feature_text_parts.append(feature_content)

            docs.append(
                Document(
                    page_content="\n\n".join(feature_text_parts),
                    metadata={
                        **base_metadata,
                        "source": f"{json_path.as_posix()}::{feature_file or f'record-{idx}'}",
                        "type": "feature",
                        "feature_file": feature_file,
                        "doc_id": f"gwt:{idx}:feature",
                    },
                )
            )

        if step_content:
            step_text_parts = []
            if repository:
                step_text_parts.append(f"Repository: {repository}")
            if language:
                step_text_parts.append(f"Language: {language}")
            if step_file:
                step_text_parts.append(f"Step definitions file: {step_file}")
            if feature_file:
                step_text_parts.append(f"Related feature file: {feature_file}")
            step_text_parts.append("Step definitions content:")
            step_text_parts.append(step_content)

            docs.append(
                Document(
                    page_content="\n\n".join(step_text_parts),
                    metadata={
                        **base_metadata,
                        "source": f"{json_path.as_posix()}::{step_file or feature_file or f'record-{idx}:steps'}",
                        "type": "step_definitions",
                        "feature_file": feature_file,
                        "step_definitions_file": step_file,
                        "doc_id": f"gwt:{idx}:steps",
                    },
                )
            )

        for code_idx, code_file in enumerate(record.get("system_code_files") or []):
            if not isinstance(code_file, dict):
                continue
            code_content = str(code_file.get("content") or "").strip()
            if not code_content:
                continue

            code_name = str(code_file.get("name") or "").strip()
            code_path = str(code_file.get("path") or "").strip()
            code_text_parts = []
            if repository:
                code_text_parts.append(f"Repository: {repository}")
            if language:
                code_text_parts.append(f"Language: {language}")
            if code_name:
                code_text_parts.append(f"Code file: {code_name}")
            if code_path:
                code_text_parts.append(f"Code path: {code_path}")
            if feature_file:
                code_text_parts.append(f"Related feature file: {feature_file}")
            code_text_parts.append("System code:")
            code_text_parts.append(code_content)

            docs.append(
                Document(
                    page_content="\n\n".join(code_text_parts),
                    metadata={
                        **base_metadata,
                        "source": code_path or f"{json_path.as_posix()}::code::{code_name or code_idx}",
                        "type": "system_code",
                        "feature_file": feature_file,
                        "code_name": code_name,
                        "code_path": code_path,
                        "doc_id": f"gwt:{idx}:code:{code_idx}",
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
    persist_dir: Path,
    user_stories_dir: Optional[Path] = None,
    e2egit_csv_path: Optional[Path] = None,
    givenwhenthen_json_path: Optional[Path] = None,
    max_records: Optional[int] = None,
    collection: str = "tier3_rag",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    chunk_size: int = 1200,
    chunk_overlap: int = 150,
    batch_size: int = 256,
) -> IngestStats:
    """Ingest project corpora into Chroma."""

    user_stories_dir = Path(user_stories_dir) if user_stories_dir else None
    e2egit_csv_path = Path(e2egit_csv_path) if e2egit_csv_path else None
    givenwhenthen_json_path = Path(givenwhenthen_json_path) if givenwhenthen_json_path else None
    persist_dir = Path(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    start_ts = time.time()
    docs = []
    if user_stories_dir and user_stories_dir.exists():
        docs.extend(_load_user_stories(user_stories_dir))

    if e2egit_csv_path:
        docs.extend(_load_gui_java_junit_csv(e2egit_csv_path))

    if givenwhenthen_json_path and givenwhenthen_json_path.exists():
        print(
            f"[RAG] Loading GivenWhenThen dataset from {givenwhenthen_json_path}"
            + (f" (max_records={max_records})" if max_records else ""),
            flush=True,
        )
        docs.extend(
            _load_givenwhenthen_json(
                givenwhenthen_json_path,
                max_records=max_records,
            )
        )

    if not docs:
        print("[RAG] No documents found to ingest.", flush=True)
        return IngestStats(
            documents_loaded=0,
            chunks_indexed=0,
            persist_dir=persist_dir,
            collection=collection,
        )

    print(f"[RAG] Loaded {len(docs)} source documents", flush=True)
    splitter = _get_text_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    print(
        f"[RAG] Splitting documents into chunks (chunk_size={chunk_size}, overlap={chunk_overlap})",
        flush=True,
    )
    chunks = splitter.split_documents(docs)
    print(f"[RAG] Prepared {len(chunks)} chunks", flush=True)

    # Build stable IDs for Chroma.
    ids = _make_unique_ids(
        [_stable_id(c.page_content, c.metadata) for c in chunks]
    )

    print(f"[RAG] Loading embedding model: {embedding_model}", flush=True)
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
    total_batches = max(1, math.ceil(len(chunks) / batch_size))
    print(
        f"[RAG] Writing embeddings to {persist_dir} in {total_batches} batches "
        f"(batch_size={batch_size})",
        flush=True,
    )
    for i in range(0, len(chunks), batch_size):
        batch_docs = chunks[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]
        batch_no = (i // batch_size) + 1
        vs.add_documents(batch_docs, ids=batch_ids)
        total += len(batch_docs)
        elapsed = time.time() - start_ts
        print(
            f"[RAG] Batch {batch_no}/{total_batches} complete "
            f"({total}/{len(chunks)} chunks, elapsed {elapsed:.1f}s)",
            flush=True,
        )

    total_elapsed = time.time() - start_ts
    print(
        f"[RAG] Ingest complete: {total} chunks indexed in {total_elapsed:.1f}s",
        flush=True,
    )

    return IngestStats(
        documents_loaded=len(docs),
        chunks_indexed=total,
        persist_dir=persist_dir,
        collection=collection,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Ingest local corpora into Chroma (creates chroma_db/)")
    parser.add_argument(
        "--user-stories-dir",
        type=Path,
        default=None,
        help="Optional legacy folder of .txt user stories",
    )
    parser.add_argument(
        "--e2egit-csv",
        type=Path,
        default=None,
        help="Optional legacy CSV corpus",
    )
    parser.add_argument(
        "--givenwhenthen-json",
        type=Path,
        default=Path("data/raw/GivenWhenThen.json"),
        help="Primary JSON corpus for RAG",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Optional limit for GivenWhenThen records, useful for testing smaller ingests",
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
        givenwhenthen_json_path=args.givenwhenthen_json,
        max_records=args.max_records,
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
