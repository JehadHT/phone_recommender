from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
from vector import retrieve_with_scores


def docs_to_text(docs: Iterable[Document]) -> str:
    return "\n\n".join(f"- {doc.page_content}" for doc in docs)


def select_docs_for_rag(
    scored_docs: Sequence[tuple[Document, Optional[float]]],
    *,
    min_relevance: float,
) -> list[Document]:
    """Pick docs suitable for RAG.

    If scores are available (preferred), use a threshold.
    If scores are missing, fall back to using all docs (conservative).
    """
    if not scored_docs:
        return []

    has_scores = any(score is not None for _, score in scored_docs)
    if has_scores:
        return [
            doc
            for doc, score in scored_docs
            if (score is not None and score >= min_relevance)
        ]

    return [doc for doc, _ in scored_docs]


@dataclass(frozen=True)
class ChatResult:
    reply: str
    type: str  # "RAG" | "GENERAL"


class PhoneChatService:
    def __init__(
        self,
        *,
        model: str = "qwen2.5",
        temperature: float = 0.2,
        retrieval_k: int = 5,
        min_relevance: float = 0.35,
    ) -> None:
        self._retrieval_k = retrieval_k
        self._min_relevance = min_relevance

        llm = OllamaLLM(model=model, temperature=temperature)

        rag_prompt = ChatPromptTemplate.from_template(
            """
            you are an expert in the field of mobile phones.

            answer using only the information provided below.

            if the answer is not found in the phone data, say exactly:

            "i don't have enough information from the phone data."

            data phones:
            {context}

            Question:
            {question}
            """.strip()
        )

        general_prompt = ChatPromptTemplate.from_template(
            """
            you are a helpful assistant in the field of mobile phones.

            answer the question using your general knowledge.
            Question:
            {question}
            """.strip()
        )

        self._rag_chain = rag_prompt | llm
        self._general_chain = general_prompt | llm

    def chat(self, question: str) -> ChatResult:
        scored = retrieve_with_scores(question, k=self._retrieval_k)
        rag_docs = select_docs_for_rag(scored, min_relevance=self._min_relevance)

        if rag_docs:
            context = docs_to_text(rag_docs)
            reply = self._rag_chain.invoke({"context": context, "question": question})
            return ChatResult(reply=str(reply), type="RAG")

        reply = self._general_chain.invoke({"question": question})
        return ChatResult(reply=str(reply), type="GENERAL")
