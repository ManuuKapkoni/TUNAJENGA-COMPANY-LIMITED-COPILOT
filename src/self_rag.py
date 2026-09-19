from src.graph import app as _graph_app


def ask(question: str, thread_id: str = "default") -> dict:
    initial_state = {
        "question": question,
        "retrieval_query": question,
        "rewrite_tries": 0,
        "need_retrieval": False,
        "docs": [],
        "relevant_docs": [],
        "context": "",
        "answer": "",
        "issup": "no_support",
        "evidence": [],
        "retries": 0,
        "isuse": "not_useful",
        "use_reason": "",
    }

    result = _graph_app.invoke(
        initial_state,
        config={
            "recursion_limit": 80,
            "configurable": {"thread_id": thread_id},
        },
    )

    relevant_docs = result.get("relevant_docs") or []
    sources = []
    for d in relevant_docs:
        meta = getattr(d, "metadata", {}) or {}
        sources.append({
            "source": meta.get("source", ""),
            "page": meta.get("page"),
            "title": meta.get("title", ""),
        })

    return {
        "question": result.get("question", question),
        "answer": result.get("answer", ""),
        "need_retrieval": bool(result.get("need_retrieval", False)),
        "retrieval_query": result.get("retrieval_query", ""),
        "rewrite_tries": int(result.get("rewrite_tries", 0)),
        "retries": int(result.get("retries", 0)),
        "relevant_docs": len(relevant_docs),
        "issup": result.get("issup") or None,
        "isuse": result.get("isuse") or None,
        "use_reason": result.get("use_reason", ""),
        "evidence": result.get("evidence") or [],
        "sources": sources,
    }


def run_self_rag(question: str, thread_id: str = "default") -> dict:
    return ask(question, thread_id)


if __name__ == "__main__":
    import json
    out = ask("Who is the founder of TUNAJENGA?")
    print(json.dumps(out, indent=2, default=str))




# def ask(question: str, thread_id: str = "default") -> dict:
#     initial_state = {
#         "question": question,
#         "retrieval_query": question,
#         "rewrite_tries": 0,
#         "need_retrieval": False,
#         "docs": [],
#         "relevant_docs": [],
#         "context": "",
#         "answer": "",
#         "issup": "no_support",
#         "evidence": [],
#         "retries": 0,
#         "isuse": "not_useful",
#         "use_reason": "",
#     }
#     result = app.invoke(
#         initial_state,
#         config={
#             "recursion_limit": 80,
#             "configurable": {"thread_id": thread_id},
#         },
#     )
#     return {
#         "question": result.get("question", question),
#         "answer": result.get("answer", ""),
#         "need_retrieval": bool(result.get("need_retrieval", False)),
#         "retrieval_query": result.get("retrieval_query", ""),
#         "rewrite_tries": int(result.get("rewrite_tries", 0)),
#         "retries": int(result.get("retries", 0)),
#         "relevant_docs": len(result.get("relevant_docs") or []),
#         "issup": result.get("issup"),
#         "isuse": result.get("isuse"),
#         "use_reason": result.get("use_reason", ""),
#         "evidence": result.get("evidence") or [],
#     }


# # FastAPI / external callers use this name
# def run_self_rag(question: str, thread_id: str = "default") -> dict:
#     return ask(question, thread_id)


# if __name__ == "__main__":
#     import json
#     print(json.dumps(ask("Who is the founder of TUNAJENGA?"), indent=2))

