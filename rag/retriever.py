from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class RetrievedChunk:
    content: str
    source: str
    score: Optional[float] = None


def load_retriever(
    persist_dir: Path = Path("chroma_db"),
    collection: str = "tier3_rag",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
):
    """Return a LangChain retriever for an existing Chroma DB."""

    persist_dir = Path(persist_dir)

    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
    except Exception:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(model_name=embedding_model)

    try:
        from langchain_chroma import Chroma  # type: ignore
    except Exception:
        from langchain_community.vectorstores import Chroma

    vs = Chroma(
        collection_name=collection,
        persist_directory=str(persist_dir),
        embedding_function=embeddings,
    )
    return vs.as_retriever(search_kwargs={"k": 5})


def query(
    text: str,
    persist_dir: Path = Path("chroma_db"),
    collection: str = "tier3_rag",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    k: int = 5,
) -> List[RetrievedChunk]:
    retriever = load_retriever(persist_dir=persist_dir, collection=collection, embedding_model=embedding_model)
    retriever.search_kwargs["k"] = k

    docs = retriever.invoke(text)
    out: List[RetrievedChunk] = []
    for d in docs:
        src = str(d.metadata.get("source") or d.metadata.get("source_table") or "")
        out.append(RetrievedChunk(content=d.page_content, source=src))
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Query the local Chroma RAG index")
    parser.add_argument("query", type=str)
    parser.add_argument("--persist-dir", type=Path, default=Path("chroma_db"))
    parser.add_argument("--collection", type=str, default="tier3_rag")
    parser.add_argument("--model", type=str, default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--k", type=int, default=5)

    args = parser.parse_args(argv)

    results = query(
        args.query,
        persist_dir=args.persist_dir,
        collection=args.collection,
        embedding_model=args.model,
        k=args.k,
    )

    for i, r in enumerate(results, start=1):
        print(f"[{i}] source={r.source}\n{r.content[:600]}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
