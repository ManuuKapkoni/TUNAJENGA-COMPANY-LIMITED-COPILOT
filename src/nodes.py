from typing import List, Literal
import re
from langchain_core.documents import Document

from src.state import State
from src.llm import get_llm
from src.models import (
    RetrieveDecision,
    RelevanceDecision,
    IsSUPDecision,
    IsUSEDecision,
    RewriteDecision,
)
from src.prompts import (
    decide_retrieval_prompt,
    direct_generation_prompt,
    is_relevant_prompt,
    rag_generation_prompt,
    issup_prompt,
    revise_prompt,
    isuse_prompt,
    rewrite_for_retrieval_prompt,
)

MAX_RETRIES = 10
MAX_REWRITE_TRIES = 3



def _strip_markdown(text: str) -> str:
    if not text:
        return text

    # Headings
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)

    # Bold / italic
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_(?!\s)(.+?)(?<!\s)_(?!_)", r"\1", text)

    # Inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)

    # Bullets: keep as "• "
    text = re.sub(r"^\s*[-*+]\s+", "• ", text, flags=re.MULTILINE)

    # Collapse extra blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# -----------------------------
# 1) Decide retrieval
# -----------------------------
def decide_retrieval(state: State):
    llm = get_llm()
    should_retrieve_llm = llm.with_structured_output(RetrieveDecision)
    decision: RetrieveDecision = should_retrieve_llm.invoke(
        decide_retrieval_prompt.format_messages(question=state["question"])
    )
    return {"need_retrieval": decision.should_retrieve}


def route_after_decide(state: State) -> Literal["generate_direct", "retrieve"]:
    return "retrieve" if state["need_retrieval"] else "generate_direct"


# -----------------------------
# 2) Direct answer (no retrieval)
# -----------------------------
# def generate_direct(state: State):
#     llm = get_llm()
#     out = llm.invoke(
#         direct_generation_prompt.format_messages(question=state["question"])
#     )
#     return {"answer": out.content}
def generate_direct(state: State):
    llm = get_llm()
    out = llm.invoke(
        direct_generation_prompt.format_messages(question=state["question"])
    )
    return {"answer": _strip_markdown(out.content)}


# -----------------------------
# 3) Retrieve (FAISS)
# -----------------------------
def retrieve(state: State):
    from src.vectorstore import get_retriever

    retriever = get_retriever()
    q = state.get("retrieval_query") or state["question"]
    return {"docs": retriever.invoke(q)}


# -----------------------------
# 4) Relevance filter
# -----------------------------
def is_relevant(state: State):
    llm = get_llm()
    relevance_llm = llm.with_structured_output(RelevanceDecision)

    relevant_docs: List[Document] = []
    for doc in state.get("docs", []):
        decision: RelevanceDecision = relevance_llm.invoke(
            is_relevant_prompt.format_messages(
                question=state["question"],
                document=doc.page_content,
            )
        )
        if decision.is_relevant:
            relevant_docs.append(doc)
    return {"relevant_docs": relevant_docs}


def route_after_relevance(
    state: State,
) -> Literal["generate_from_context", "no_answer_found"]:
    if state.get("relevant_docs") and len(state["relevant_docs"]) > 0:
        return "generate_from_context"
    return "no_answer_found"


# -----------------------------
# 5) Generate from context
# -----------------------------
# def generate_from_context(state: State):
#     llm = get_llm()
#     context = "\n\n---\n\n".join(
#         [d.page_content for d in state.get("relevant_docs", [])]
#     ).strip()
#     if not context:
#         return {"answer": "No answer found.", "context": ""}
#     out = llm.invoke(
#         rag_generation_prompt.format_messages(
#             question=state["question"], context=context
#         )
#     )
#     return {"answer": out.content, "context": context}
def generate_from_context(state: State):
    llm = get_llm()
    context = "\n\n---\n\n".join(
        [d.page_content for d in state.get("relevant_docs", [])]
    ).strip()
    if not context:
        return {"answer": "No answer found.", "context": ""}
    out = llm.invoke(
        rag_generation_prompt.format_messages(
            question=state["question"], context=context
        )
    )
    return {"answer": _strip_markdown(out.content), "context": context}


def no_answer_found(state: State):
    return {"answer": "No answer found.", "context": ""}


# -----------------------------
# 6) IsSUP verify + revise loop
# -----------------------------
def is_sup(state: State):
    llm = get_llm()
    issup_llm = llm.with_structured_output(IsSUPDecision)
    decision: IsSUPDecision = issup_llm.invoke(
        issup_prompt.format_messages(
            question=state["question"],
            answer=state.get("answer", ""),
            context=state.get("context", ""),
        )
    )
    return {"issup": decision.issup, "evidence": decision.evidence}


def route_after_issup(state: State) -> Literal["accept_answer", "revise_answer"]:
    if state.get("issup") == "fully_supported":
        return "accept_answer"
    if state.get("retries", 0) >= MAX_RETRIES:
        return "accept_answer"
    return "revise_answer"


def accept_answer(state: State):
    return {}


# def revise_answer(state: State):
#     llm = get_llm()
#     out = llm.invoke(
#         revise_prompt.format_messages(
#             question=state["question"],
#             answer=state.get("answer", ""),
#             context=state.get("context", ""),
#         )
#     )
#     return {
#         "answer": out.content,
#         "retries": state.get("retries", 0) + 1,
#     }

def revise_answer(state: State):
    llm = get_llm()
    out = llm.invoke(
        revise_prompt.format_messages(
            question=state["question"],
            answer=state.get("answer", ""),
            context=state.get("context", ""),
        )
    )
    return {
        "answer": _strip_markdown(out.content),
        "retries": state.get("retries", 0) + 1,
    }

# -----------------------------
# 7) IsUSE
# -----------------------------
def is_use(state: State):
    llm = get_llm()
    isuse_llm = llm.with_structured_output(IsUSEDecision)
    decision: IsUSEDecision = isuse_llm.invoke(
        isuse_prompt.format_messages(
            question=state["question"],
            answer=state.get("answer", ""),
        )
    )
    return {"isuse": decision.isuse, "use_reason": decision.reason}


def route_after_isuse(
    state: State,
) -> Literal["END", "rewrite_question", "no_answer_found"]:
    if state.get("isuse") == "useful":
        return "END"
    if state.get("rewrite_tries", 0) >= MAX_REWRITE_TRIES:
        return "no_answer_found"
    return "rewrite_question"


# -----------------------------
# 8) Rewrite question for retrieval
# -----------------------------
def rewrite_question(state: State):
    llm = get_llm()
    rewrite_llm = llm.with_structured_output(RewriteDecision)
    decision: RewriteDecision = rewrite_llm.invoke(
        rewrite_for_retrieval_prompt.format_messages(
            question=state["question"],
            retrieval_query=state.get("retrieval_query", ""),
            answer=state.get("answer", ""),
        )
    )
    return {
        "retrieval_query": decision.retrieval_query,
        "rewrite_tries": state.get("rewrite_tries", 0) + 1,
        "docs": [],
        "relevant_docs": [],
        "context": "",
    }

