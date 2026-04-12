from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ExtractStats:
    table: str
    rows_written: int
    out_csv: Path


def _list_tables(conn: sqlite3.Connection) -> List[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r[0] for r in cur.fetchall()]


def _score_table_name(name: str) -> int:
    n = name.lower()
    score = 0
    for token, points in (
        ("gui", 5),
        ("java", 4),
        ("junit", 6),
        ("test", 2),
        ("gherkin", 2),
        ("cucumber", 2),
        ("scenario", 1),
        ("feature", 1),
        ("step", 1),
    ):
        if token in n:
            score += points
    return score


def _pick_best_table(conn: sqlite3.Connection, preferred: Optional[str]) -> str:
    tables = _list_tables(conn)
    if not tables:
        raise RuntimeError("No tables found in SQLite DB.")

    if preferred:
        if preferred not in tables:
            raise RuntimeError(
                f"Requested table '{preferred}' not found. Available tables: {tables[:50]}"
            )
        return preferred

    scored = sorted(((t, _score_table_name(t)) for t in tables), key=lambda x: x[1], reverse=True)
    best_name, best_score = scored[0]
    if best_score == 0:
        # Fall back to the largest table by row count (best-effort).
        # NOTE: COUNT(*) can be expensive, so we try a light heuristic first.
        # Prefer tables containing 'sample'/'data'/'record' when scores are tied at 0.
        fallback_tokens = ("sample", "data", "record", "row", "item")
        token_tables = [t for t in tables if any(tok in t.lower() for tok in fallback_tokens)]
        return token_tables[0] if token_tables else best_name
    return best_name


def _table_columns(conn: sqlite3.Connection, table: str) -> List[Tuple[str, str]]:
    cur = conn.execute(f'PRAGMA table_info("{table}")')
    # rows: cid, name, type, notnull, dflt_value, pk
    return [(r[1], (r[2] or "").upper()) for r in cur.fetchall()]


def _is_text_affinity(declared_type: str) -> bool:
    t = declared_type.upper()
    if not t:
        return True
    return any(x in t for x in ("CHAR", "CLOB", "TEXT", "VARCHAR"))


def _choose_text_columns(columns: Sequence[Tuple[str, str]]) -> List[str]:
    names = [c[0] for c in columns]
    preferred = [
        "text",
        "content",
        "body",
        "message",
        "prompt",
        "completion",
        "gherkin",
        "scenario",
        "feature",
        "steps",
        "junit",
    ]
    picked = [n for n in names if n.lower() in preferred]
    if picked:
        return picked

    # Otherwise include all declared text-like columns.
    return [name for (name, dtype) in columns if _is_text_affinity(dtype)]


def _first_present(keys: Sequence[str], mapping: Dict[str, Any]) -> Optional[Any]:
    lowered = {k.lower(): k for k in mapping.keys()}
    for k in keys:
        if k in lowered:
            return mapping.get(lowered[k])
    return None


def _row_to_doc(row: Dict[str, Any], text_columns: Sequence[str], table: str, row_index: int) -> Tuple[str, str, Dict[str, Any]]:
    doc_id = _first_present(
        ("id", "uuid", "guid", "pk", "sha", "hash", "commit", "commit_hash"),
        row,
    )
    if doc_id is None:
        doc_id = f"{table}:{row_index}"

    # Build text.
    parts: List[str] = []
    for col in text_columns:
        val = row.get(col)
        if val is None:
            continue
        if isinstance(val, bytes):
            try:
                val = val.decode("utf-8", errors="replace")
            except Exception:
                val = repr(val)
        if not isinstance(val, str):
            val = str(val)
        val = val.strip()
        if not val:
            continue
        parts.append(f"{col}: {val}" if len(text_columns) > 1 else val)

    text = "\n\n".join(parts).strip()

    # Minimal metadata. Keep it small.
    metadata: Dict[str, Any] = {
        "source": "E2EGit.db",
        "source_table": table,
    }

    # Include a few scalar fields as metadata (best-effort).
    for key in ("service", "path", "file", "filename", "language", "framework", "test_type"):
        v = _first_present((key,), row)
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            metadata[key] = v

    return str(doc_id), text, metadata


def extract_e2egit_to_csv(
    db_path: Path,
    out_csv_path: Path,
    table: Optional[str] = None,
    limit: Optional[int] = None,
) -> ExtractStats:
    """Extract text-ish records from E2EGit.db and write gui_java_junit.csv.

    The DB schema can vary; this function picks a best-effort table and
    concatenates useful text columns into a single `text` field suitable
    for RAG ingestion.
    """

    db_path = Path(db_path)
    out_csv_path = Path(out_csv_path)

    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    out_csv_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        chosen_table = _pick_best_table(conn, table)
        columns = _table_columns(conn, chosen_table)
        text_cols = _choose_text_columns(columns)
        if not text_cols:
            raise RuntimeError(
                f"No text-like columns found in table '{chosen_table}'. Columns: {[c[0] for c in columns]}"
            )

        col_names = [c[0] for c in columns]
        select_cols = ", ".join([f'"{c}"' for c in col_names])
        sql = f'SELECT {select_cols} FROM "{chosen_table}"'
        if limit is not None:
            sql += f" LIMIT {int(limit)}"

        cur = conn.execute(sql)

        rows_written = 0
        with out_csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["doc_id", "text", "source", "metadata_json"],
                quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()

            fetch_size = 1000
            row_index = 0
            while True:
                batch = cur.fetchmany(fetch_size)
                if not batch:
                    break
                for r in batch:
                    row_index += 1
                    row_dict = dict(r)
                    doc_id, text, metadata = _row_to_doc(row_dict, text_cols, chosen_table, row_index)
                    if not text:
                        continue
                    writer.writerow(
                        {
                            "doc_id": doc_id,
                            "text": text,
                            "source": "E2EGit.db",
                            "metadata_json": json.dumps(metadata, ensure_ascii=False),
                        }
                    )
                    rows_written += 1

        return ExtractStats(table=chosen_table, rows_written=rows_written, out_csv=out_csv_path)
    finally:
        conn.close()


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Extract E2EGit.db -> gui_java_junit.csv (auto-generated)")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("corpus/tier3_zenodo/z14234731_e2egit/E2EGit.db"),
        help="Path to E2EGit.db",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("corpus/tier3_zenodo/z14234731_e2egit/gui_java_junit.csv"),
        help="Output CSV path (generated)",
    )
    parser.add_argument("--table", type=str, default=None, help="Optional SQLite table name to extract")
    parser.add_argument("--limit", type=int, default=None, help="Optional LIMIT (debug)")

    args = parser.parse_args(argv)

    stats = extract_e2egit_to_csv(args.db, args.out, table=args.table, limit=args.limit)
    print(f"Wrote {stats.rows_written} rows to {stats.out_csv} (table: {stats.table})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
