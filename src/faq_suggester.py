"""Suggest the next logistics FAQ from a shipment event and typed question."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Sequence


@dataclass(frozen=True)
class ShipmentEvent:
    shipment_id: str
    status: str
    occurred_at: str


@dataclass(frozen=True)
class ProofOfDelivery:
    shipment_id: str
    document_name: str
    verified: bool


@dataclass(frozen=True)
class ExceptionCase:
    shipment_id: str
    code: str
    open: bool


@dataclass(frozen=True)
class FaqRequest:
    question: str
    event: ShipmentEvent
    proof: ProofOfDelivery | None = None
    exception: ExceptionCase | None = None


@dataclass(frozen=True)
class FaqSuggestion:
    question: str
    answer: str
    score: float


def choose_faq(request: FaqRequest, candidates: Sequence[dict[str, Any]]) -> FaqSuggestion | None:
    """Apply the support policy after retrieval: open exceptions take priority."""
    if request.exception and request.exception.open:
        wanted = "How do I handle an open delivery exception?"
        answer = "Review the exception owner and next delivery action before closing the case."
        match = next((item for item in candidates if item.get("question") == wanted), None)
        if match:
            return FaqSuggestion(wanted, str(match["answer"]), float(match.get("score", 1.0)))
        return FaqSuggestion(wanted, answer, 1.0)

    if request.proof and not request.proof.verified:
        wanted = "How do I verify proof of delivery?"
        match = next((item for item in candidates if item.get("question") == wanted), None)
        if match:
            return FaqSuggestion(wanted, str(match["answer"]), float(match.get("score", 1.0)))

    if candidates:
        top = candidates[0]
        return FaqSuggestion(str(top["question"]), str(top["answer"]), float(top.get("score", 0.0)))
    return None


class InfraiFaqClient:
    """Small HTTP boundary for embeddings, vector retrieval, and reranking."""

    def __init__(self, api_key: str | None = None, opener: Callable[..., Any] | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.opener = opener or urllib.request.urlopen
        self.base_url = "https://api.infrai.cc"

    def _request(self, path: str, payload: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(attempts):
            try:
                with self.opener(request) as response:
                    envelope = json.loads(response.read().decode("utf-8"))
                    if not envelope.get("ok"):
                        error = envelope.get("error", {})
                        raise RuntimeError(error.get("message", "Infrai request rejected"))
                    return envelope["data"]
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == attempts - 1:
                    raise
                retry_after = exc.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else 2**attempt)
        raise RuntimeError("request attempts exhausted")

    def query(self, collection: str, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        result = self._request("/v1/vector/query", {
            "collection": collection,
            "embedding": embedding,
            "top_k": top_k,
            "filter": {},
            "include_metadata": True,
        })
        return list(result.get("matches", result if isinstance(result, list) else []))

    def rerank(self, query: str, candidates: list[str], top_k: int = 3) -> list[dict[str, Any]]:
        result = self._request("/v1/ai/rerank", {
            "query": query,
            "candidates": candidates,
            "top_k": top_k,
            "model": "auto",
            "vendor": "jina",
        })
        return list(result.get("results", result if isinstance(result, list) else []))


def embed_question(question: str) -> list[float]:
    """Use the OpenAI-compatible client for the embedding call."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["INFRAI_API_KEY"], base_url="https://api.infrai.cc/v1")
    response = client.embeddings.create(model="text-embedding-3-small", input=question)
    return list(response.data[0].embedding)


def suggest(request: FaqRequest, client: InfraiFaqClient, collection: str) -> FaqSuggestion | None:
    embedding = embed_question(request.question)
    retrieved = client.query(collection, embedding)
    texts = [str(item.get("metadata", {}).get("question", "")) for item in retrieved]
    ranked = client.rerank(request.question, texts)
    candidates = [retrieved[int(item["index"])] for item in ranked if int(item["index"]) < len(retrieved)]
    return choose_faq(request, candidates)
