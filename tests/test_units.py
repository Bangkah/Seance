from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from conftest import run_cli

from seance.cli import main
from seance.errors import InputError
from seance.evidence import Evidence, EvidencePack, Facts
from seance.gitreader import Commit
from seance.grounding import Claim, GroundingResult
from seance.model_client import ModelConfig
from seance.prompts import language_note, report_prompt, tone_note
from seance.renderer import DISCLAIMER, REFUSAL, render_answer, render_report
from seance.retrieval import retrieve
from seance.text import sanitize

CONTROL = "\x1b[31mred\x1b[0m"


def _claim(text: str, dates: tuple[str, ...] = ()) -> Claim:
    return Claim(section="timeline", text=text, evidence_ids=("M:commits",), dates=dates)


def _facts() -> Facts:
    first = Commit(
        hash="a" * 40,
        author="Ada",
        authored_at="2019-03-02T10:00:00+00:00",
        committed_at="2019-03-02T10:00:00+00:00",
        subject="initial",
    )
    last = Commit(
        hash="b" * 40,
        author="Ada",
        authored_at="2021-08-14T10:00:00+00:00",
        committed_at="2021-08-14T10:00:00+00:00",
        subject="deprecated",
    )
    return Facts(
        repo_name="demo",
        as_of="2026-10-27T00:00:00+00:00",
        total_commits=2,
        analyzed_commits=2,
        capped=False,
        first=first,
        last=last,
        authors=("Ada",),
        tags=(),
        manifests=(),
        languages=(("Python", 3),),
        gap_months=62,
        span_days=896,
    )


def test_sanitize_strips_controls_and_bidi() -> None:
    cleaned = sanitize(CONTROL)
    assert "\x1b" not in cleaned
    assert "red" in cleaned
    assert sanitize("a\u202eb") == "a b"
    assert sanitize("x" * 20, limit=5).endswith("...")


def test_retrieval_prefers_matching_evidence() -> None:
    pack = EvidencePack(
        items=(
            Evidence("M:commits", "metric", "42 commits in total."),
            Evidence("C:aaa1111", "commit", "Commit aaa1111: initial import"),
            Evidence("C:bbb2222", "commit", "Commit bbb2222: rotate logs"),
        )
    )
    result = retrieve(pack, "when did the initial import happen?")
    assert result.items[0].id == "C:aaa1111"
    assert result.scores[0][1] > 0


def test_retrieval_falls_back_when_nothing_matches() -> None:
    pack = EvidencePack(items=(Evidence("M:commits", "metric", "42 commits in total."),))
    result = retrieve(pack, "zzzz")
    assert len(result.items) == 1


def test_renderer_orders_timeline_and_strips_dates() -> None:
    result = GroundingResult(
        summary=_claim("A small utility."),
        purpose=_claim("It handled one narrow job."),
        timeline=(
            _claim("2021-08-14: Later work.", ("2021-08-14",)),
            _claim("2019-03-02: Earlier work.", ("2019-03-02",)),
        ),
        revival=(_claim("Read the last commits."),),
    )
    text = render_report(_facts(), result, dropped_evidence=3, model="qwen3:4b")
    earlier = text.index("2019-03-02  Earlier work.")
    later = text.index("2021-08-14  Later work.")
    assert earlier < later
    assert "3 evidence items omitted" in text
    assert DISCLAIMER in text


def test_renderer_refusal_is_fixed_text() -> None:
    assert render_answer(None) == REFUSAL


def test_timeline_requires_commit_or_file() -> None:
    from seance.grounding import validate_report

    pack = EvidencePack(
        items=(
            Evidence("M:gap", "metric", "Last commit 2026-04-05, silence 6 months."),
            Evidence("C:abc1234", "commit", "Commit abc1234 on 2026-04-05: Create FUNDING.yml"),
        )
    )
    payload = {
        "summary": "A small offline roleplay engine.",
        "purpose": "Run characters locally with memory.",
        "timeline": [
            {"text": "2026-04-05 the project stopped for 6 months.", "evidence_ids": ["M:gap"]},
            {"text": "FUNDING.yml was added at the end.", "evidence_ids": ["C:abc1234"]},
        ],
        "death_hypotheses": [
            {
                "text": "Work moved elsewhere after the last change.",
                "evidence_ids": ["M:gap"],
                "confidence": "low",
            }
        ],
        "revival_steps": [
            {"text": "Read the last commit and continue it.", "evidence_ids": ["C:abc1234"]}
        ],
    }
    result = validate_report(payload, pack)
    assert len(result.timeline) == 1
    assert result.timeline[0].evidence_ids == ("C:abc1234",)
    assert any(r.reason == "timeline claims must cite a commit or file" for r in result.rejected)


def test_endpoint_validation() -> None:
    assert (
        ModelConfig(endpoint="http://127.0.0.1:11434").generate_url()
        == "http://127.0.0.1:11434/api/generate"
    )
    assert (
        ModelConfig(endpoint="http://[::1]:11434").generate_url()
        == "http://[::1]:11434/api/generate"
    )
    assert (
        ModelConfig(endpoint="http://ollama:11434", allow_container=True).generate_url()
        == "http://ollama:11434/api/generate"
    )
    with pytest.raises(InputError):
        ModelConfig(endpoint="http://example.com:11434").generate_url()
    with pytest.raises(InputError):
        ModelConfig(endpoint="http://ollama:11434").generate_url()
    with pytest.raises(InputError):
        ModelConfig(endpoint="http://user:pass@localhost:11434").generate_url()
    with pytest.raises(InputError):
        ModelConfig(endpoint="file:///tmp/socket").generate_url()


def test_prompt_payload_is_json_data() -> None:
    payload = json.loads(report_prompt("demo", "[M:commits] 42 commits", ["M:commits"]))
    assert payload["repository"] == "demo"
    assert payload["evidence_ids"] == ["M:commits"]
    assert language_note("en") == ""
    assert "Indonesian" in language_note("id")
    assert "ghost" in tone_note("spooky")
    assert "plainly" in tone_note("plain")


def test_main_in_process(fixtures: dict[str, Path], capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["facts", str(fixtures["dead_normal"]), "--now", "2026-10-27T00:00:00Z"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["commits"]["total"] == 5


def test_main_returns_input_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["facts", str(tmp_path / "missing")])
    assert code == 2
    assert "seance:" in capsys.readouterr().err


def test_invalid_now_is_rejected(fixtures: dict[str, Path]) -> None:
    result = run_cli(["facts", str(fixtures["dead_normal"]), "--now", "not-a-date"])
    assert result.returncode == 2
    assert "invalid --now" in result.stderr


def test_utc_helpers() -> None:
    assert datetime(2026, 10, 27, tzinfo=UTC).year == 2026
