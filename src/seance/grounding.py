from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .evidence import EvidencePack

HEX_TOKEN = re.compile(r"\b[0-9a-fA-F]{7,40}\b")
ISO_TOKEN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NUMBER_TOKEN = re.compile(r"\b\d{2,}\b")
CONFIDENCE = frozenset({"low", "medium", "high"})
MAX_TEXT = 600
MIN_TEXT = 8
MAX_IDS = 8

CLAIM_TEXT_LABELS = {
    "summary": "summary",
    "purpose": "purpose",
    "timeline": "timeline",
    "death_hypotheses": "death hypothesis",
    "revival_steps": "revival step",
}


@dataclass(frozen=True, slots=True)
class Claim:
    section: str
    text: str
    evidence_ids: tuple[str, ...]
    confidence: str | None = None
    dates: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Rejected:
    section: str
    reason: str


@dataclass(frozen=True, slots=True)
class GroundingResult:
    summary: Claim | None = None
    purpose: Claim | None = None
    timeline: tuple[Claim, ...] = ()
    hypotheses: tuple[Claim, ...] = ()
    revival: tuple[Claim, ...] = ()
    rejected: tuple[Rejected, ...] = ()
    received: int = 0

    @property
    def kept(self) -> int:
        items = [self.summary, self.purpose]
        return (
            sum(1 for item in items if item is not None)
            + len(self.timeline)
            + len(self.hypotheses)
            + len(self.revival)
        )

    @property
    def dropped(self) -> int:
        return len(self.rejected)


@dataclass(slots=True)
class _State:
    pack: EvidencePack
    rejected: list[Rejected] = field(default_factory=list)
    received: int = 0

    def reject(self, section: str, reason: str) -> None:
        self.rejected.append(Rejected(section=section, reason=reason))


def validate_report(payload: Any, pack: EvidencePack) -> GroundingResult:
    state = _State(pack=pack)
    if not isinstance(payload, dict):
        state.reject("report", "response is not a JSON object")
        return GroundingResult(rejected=tuple(state.rejected))

    summary = _parse_claim(payload.get("summary"), "summary", state)
    purpose = _parse_claim(payload.get("purpose"), "purpose", state)
    timeline = _parse_list(payload.get("timeline"), "timeline", state, limit=6)
    hypotheses = _parse_list(
        payload.get("death_hypotheses"), "death_hypotheses", state, limit=4, confidence=True
    )
    revival = _parse_list(payload.get("revival_steps"), "revival_steps", state, limit=5)
    return GroundingResult(
        summary=summary,
        purpose=purpose,
        timeline=timeline,
        hypotheses=hypotheses,
        revival=revival,
        rejected=tuple(state.rejected),
        received=state.received,
    )


def validate_answer(payload: Any, pack: EvidencePack) -> tuple[Claim | None, tuple[Rejected, ...]]:
    state = _State(pack=pack)
    if not isinstance(payload, dict):
        state.reject("answer", "response is not a JSON object")
        return None, tuple(state.rejected)
    raw_ids = payload.get("evidence_ids")
    text = payload.get("answer")
    claim = _parse_claim({"text": text, "evidence_ids": raw_ids}, "answer", state, allow_short=True)
    return claim, tuple(state.rejected)


def _parse_list(
    value: Any,
    section: str,
    state: _State,
    *,
    limit: int,
    confidence: bool = False,
) -> tuple[Claim, ...]:
    if value is None:
        state.reject(section, "section is missing")
        return ()
    if not isinstance(value, list):
        state.reject(section, "section is not a list")
        return ()
    claims: list[Claim] = []
    for index, item in enumerate(value):
        if index >= limit:
            state.reject(section, f"more than {limit} items")
            continue
        claim = _parse_claim(item, section, state, confidence=confidence)
        if claim is not None:
            claims.append(claim)
    return tuple(claims)


def _parse_claim(
    value: Any,
    section: str,
    state: _State,
    *,
    confidence: bool = False,
    allow_short: bool = False,
) -> Claim | None:
    state.received += 1
    if not isinstance(value, dict):
        state.reject(section, "item is not an object")
        return None
    text = value.get("text")
    if not isinstance(text, str):
        state.reject(section, "text is missing")
        return None
    text = " ".join(text.split())
    minimum = 2 if allow_short else MIN_TEXT
    if len(text) < minimum:
        state.reject(section, "text is too short")
        return None
    if len(text) > MAX_TEXT:
        state.reject(section, "text is too long")
        return None

    raw_ids = value.get("evidence_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        state.reject(section, "no evidence ids")
        return None
    if len(raw_ids) > MAX_IDS:
        state.reject(section, "too many evidence ids")
        return None
    evidence_ids: list[str] = []
    for raw in raw_ids:
        if not isinstance(raw, str):
            state.reject(section, "evidence id is not a string")
            return None
        if raw not in state.pack.by_id:
            state.reject(section, f"unknown evidence id {raw}")
            return None
        evidence_ids.append(raw)

    if section == "timeline" and not any(
        evidence_id.startswith(("C:", "F:")) for evidence_id in evidence_ids
    ):
        state.reject(section, "timeline claims must cite a commit or file")
        return None

    cited = "\n".join(state.pack.by_id[evidence_id].text for evidence_id in evidence_ids)
    quote = value.get("quote")
    if quote is not None and (not isinstance(quote, str) or quote not in cited):
        state.reject(section, "quote is not present in the cited evidence")
        return None

    unsupported = _unsupported_token(text, cited)
    if unsupported is not None:
        state.reject(section, f"unsupported number or hash: {unsupported}")
        return None

    label: str | None = None
    if confidence:
        raw_confidence = value.get("confidence")
        if not isinstance(raw_confidence, str) or raw_confidence.lower() not in CONFIDENCE:
            state.reject(section, "confidence must be low, medium or high")
            return None
        label = raw_confidence.lower()

    return Claim(
        section=section,
        text=_strip_ids(text, evidence_ids),
        evidence_ids=tuple(evidence_ids),
        confidence=label,
        dates=_dates(cited),
    )


def _unsupported_token(text: str, cited: str) -> str | None:
    haystack = cited.lower()
    for pattern in (HEX_TOKEN, ISO_TOKEN, NUMBER_TOKEN):
        for raw in pattern.findall(text):
            token = str(raw)
            if token.lower() not in haystack:
                return token
    return None


def _dates(cited: str) -> tuple[str, ...]:
    seen: list[str] = []
    for match in ISO_TOKEN.findall(cited):
        if match not in seen:
            seen.append(match)
    return tuple(sorted(seen)[:3])


def _strip_ids(text: str, evidence_ids: list[str]) -> str:
    cleaned = text
    for evidence_id in evidence_ids:
        cleaned = cleaned.replace(f"[{evidence_id}]", "")
        cleaned = cleaned.replace(evidence_id, "")
    return " ".join(cleaned.split())
