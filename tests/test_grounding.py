from __future__ import annotations

from typing import Any

from seance.evidence import Evidence, EvidencePack
from seance.grounding import validate_answer, validate_report

PACK = EvidencePack(
    items=(
        Evidence("M:commits", "metric", "42 commits in total."),
        Evidence(
            "C:abc1234",
            "commit",
            "Commit abc1234 by Ada on 2019-03-02: initial import",
        ),
    )
)


def _report(summary: dict[str, Any]) -> Any:
    return {
        "summary": summary,
        "purpose": {"text": "It handled one narrow job.", "evidence_ids": ["C:abc1234"]},
        "timeline": [],
        "death_hypotheses": [],
        "revival_steps": [],
    }


def test_valid_claim_is_kept() -> None:
    result = validate_report(
        _report({"text": "A small utility.", "evidence_ids": ["M:commits"]}), PACK
    )
    assert result.summary is not None
    assert result.summary.evidence_ids == ("M:commits",)
    assert result.dropped == 0


def test_unknown_evidence_id_is_rejected() -> None:
    result = validate_report(
        _report({"text": "A small utility.", "evidence_ids": ["C:deadbee"]}), PACK
    )
    assert result.summary is None
    assert any("unknown evidence id" in item.reason for item in result.rejected)


def test_missing_evidence_ids_are_rejected() -> None:
    result = validate_report(_report({"text": "A small utility.", "evidence_ids": []}), PACK)
    assert result.summary is None
    assert any("no evidence ids" in item.reason for item in result.rejected)


def test_fabricated_quote_is_rejected() -> None:
    result = validate_report(
        _report(
            {
                "text": "The project was a log rotator.",
                "evidence_ids": ["C:abc1234"],
                "quote": "log rotator",
            }
        ),
        PACK,
    )
    assert result.summary is None
    assert any("quote" in item.reason for item in result.rejected)


def test_real_quote_is_kept() -> None:
    result = validate_report(
        _report(
            {
                "text": "The first commit was an import.",
                "evidence_ids": ["C:abc1234"],
                "quote": "initial import",
            }
        ),
        PACK,
    )
    assert result.summary is not None


def test_unsupported_number_is_rejected() -> None:
    result = validate_report(
        _report({"text": "The project was dead for 9999 months.", "evidence_ids": ["M:commits"]}),
        PACK,
    )
    assert result.summary is None
    assert any("unsupported number" in item.reason for item in result.rejected)


def test_number_present_in_cited_evidence_is_kept() -> None:
    result = validate_report(
        _report({"text": "The history holds 42 commits.", "evidence_ids": ["M:commits"]}),
        PACK,
    )
    assert result.summary is not None


def test_invalid_confidence_is_rejected() -> None:
    result = validate_report(
        {
            "summary": {"text": "A small utility.", "evidence_ids": ["M:commits"]},
            "purpose": {"text": "It handled one narrow job.", "evidence_ids": ["C:abc1234"]},
            "timeline": [],
            "death_hypotheses": [
                {
                    "text": "Work stopped when the team moved on.",
                    "evidence_ids": ["M:commits"],
                    "confidence": "certain",
                }
            ],
            "revival_steps": [],
        },
        PACK,
    )
    assert result.hypotheses == ()
    assert any("confidence" in item.reason for item in result.rejected)


def test_extra_list_items_are_counted_as_dropped() -> None:
    items = [
        {"text": "A milestone happened here.", "evidence_ids": ["C:abc1234"]} for _ in range(8)
    ]
    result = validate_report(
        {
            "summary": {"text": "A small utility.", "evidence_ids": ["M:commits"]},
            "purpose": {"text": "It handled one narrow job.", "evidence_ids": ["C:abc1234"]},
            "timeline": items,
            "death_hypotheses": [],
            "revival_steps": [],
        },
        PACK,
    )
    assert len(result.timeline) == 6
    assert result.dropped == 2


def test_timeline_dates_come_from_evidence() -> None:
    result = validate_report(
        {
            "summary": {"text": "A small utility.", "evidence_ids": ["M:commits"]},
            "purpose": {"text": "It handled one narrow job.", "evidence_ids": ["C:abc1234"]},
            "timeline": [{"text": "The import happens.", "evidence_ids": ["C:abc1234"]}],
            "death_hypotheses": [],
            "revival_steps": [],
        },
        PACK,
    )
    assert result.timeline[0].dates == ("2019-03-02",)


def test_answer_without_valid_evidence_returns_none() -> None:
    claim, rejected = validate_answer(
        {"answer": "It ended in a specific year.", "evidence_ids": ["C:deadbee"]}, PACK
    )
    assert claim is None
    assert rejected


def test_answer_with_valid_evidence_is_kept() -> None:
    claim, rejected = validate_answer(
        {"answer": "It ended quietly.", "evidence_ids": ["M:commits"]}, PACK
    )
    assert claim is not None
    assert rejected == ()
