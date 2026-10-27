from __future__ import annotations

import re
from dataclasses import dataclass

from .evidence import Evidence, EvidencePack

TOKEN = re.compile(r"[a-z0-9_]{2,}")
STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "was",
        "were",
        "why",
        "what",
        "who",
        "when",
        "how",
        "did",
        "does",
        "this",
        "that",
        "with",
        "from",
        "have",
        "has",
        "been",
        "are",
        "you",
        "your",
        "about",
        "into",
        "its",
        "it",
        "of",
        "to",
        "in",
        "on",
        "is",
        "or",
        "an",
        "as",
        "at",
        "by",
        "be",
    }
)


def tokens(text: str) -> list[str]:
    return [token for token in TOKEN.findall(text.lower()) if token not in STOPWORDS]


@dataclass(frozen=True, slots=True)
class Retrieved:
    question: str
    items: tuple[Evidence, ...]
    scores: tuple[tuple[str, int], ...]


def retrieve(pack: EvidencePack, question: str, *, limit: int = 12) -> Retrieved:
    query = tokens(question)
    scored: list[tuple[int, str, Evidence]] = []
    for item in pack.items:
        haystack = item.text.lower()
        score = sum(haystack.count(token) for token in query)
        if token_match(item.id, query):
            score += 3
        scored.append((score, item.id, item))
    scored.sort(key=lambda entry: (-entry[0], entry[1]))
    if not scored:
        return Retrieved(question=question, items=(), scores=())
    picked = [entry for entry in scored if entry[0] > 0][:limit]
    if not picked:
        picked = scored[: min(limit, len(scored))]
    return Retrieved(
        question=question,
        items=tuple(entry[2] for entry in picked),
        scores=tuple((entry[2].id, entry[0]) for entry in picked),
    )


def token_match(evidence_id: str, query: list[str]) -> bool:
    if not query:
        return False
    lowered = evidence_id.lower()
    return any(token in lowered for token in query)
