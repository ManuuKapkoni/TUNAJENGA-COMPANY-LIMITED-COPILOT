import json
import sqlite3
from datetime import datetime, timezone

from src.config import get_settings


def init_db() -> None:
    path = get_settings().database_file
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS rag_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            route TEXT,
            used_web INTEGER DEFAULT 0,
            support_status TEXT,
            usefulness TEXT,
            trace_json TEXT,
            sources_json TEXT
        )
        """)
        conn.commit()


def save_audit(question: str, result: dict) -> None:
    path = get_settings().database_file

    # Extract what we can from the Self-RAG result
    answer = result.get("answer", "") or ""
    need_retrieval = bool(result.get("need_retrieval", False))
    route = "retrieve" if need_retrieval else "generate_direct"

    # Support status from IsSUP
    support_status = result.get("issup", "") or ""

    # Usefulness from IsUSE
    usefulness = result.get("isuse", "") or ""

    # Web search wasn't used in this pipeline (no Tavily node active)
    used_web = int(bool(result.get("used_web_search", False)))

    # Trace: capture the key decision steps in order
    trace = [
        {"step": "decide_retrieval", "need_retrieval": need_retrieval},
        {"step": "retrieve", "rewrite_tries": result.get("rewrite_tries", 0)},
        # {"step": "is_relevant", "relevant_docs": len(result.get("relevant_docs") or [])},
        {"step": "is_relevant", "relevant_docs": result.get("relevant_docs", 0)},
        {"step": "generate_from_context"},
        {"step": "is_sup", "issup": support_status, "evidence": result.get("evidence", [])},
        {"step": "revise_answer", "retries": result.get("retries", 0)},
        {"step": "is_use", "isuse": usefulness, "reason": result.get("use_reason", "")},
    ]

    # Sources: pull from relevant_docs metadata if present
    sources = []
    for d in result.get("relevant_docs_meta") or []:
        sources.append(
            {
                "source": d.get("source", ""),
                "page": d.get("page"),
                "title": d.get("title", ""),
            }
        )

    with sqlite3.connect(path) as conn:
        conn.execute(
            """INSERT INTO rag_audit
            (created_at, question, answer, route, used_web,
             support_status, usefulness, trace_json, sources_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                question,
                answer,
                route,
                used_web,
                support_status,
                usefulness,
                json.dumps(trace, ensure_ascii=False),
                json.dumps(sources, ensure_ascii=False),
            ),
        )
        conn.commit()


def latest_audits(limit: int = 25):
    path = get_settings().database_file
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM rag_audit ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]