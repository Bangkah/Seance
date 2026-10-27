from __future__ import annotations

import json
from pathlib import Path

from conftest import json_facts, run_cli, tree_snapshot
from fake_ollama import FakeOllama

NOW = "2026-10-27T00:00:00Z"


def test_missing_path_is_an_input_error(tmp_path: Path) -> None:
    result = run_cli(["facts", str(tmp_path / "missing")])
    assert result.returncode == 2
    assert "seance:" in result.stderr


def test_directory_without_git_is_an_input_error(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    result = run_cli(["facts", str(plain)])
    assert result.returncode == 2


def test_empty_repository_has_no_evidence(fixtures: dict[str, Path]) -> None:
    result = run_cli(["facts", str(fixtures["empty"])])
    assert result.returncode == 4


def test_facts_prints_json(fixtures: dict[str, Path]) -> None:
    result = run_cli(["facts", str(fixtures["dead_normal"]), "--now", NOW])
    assert result.returncode == 0
    data = json_facts(result)
    assert data["repo"] == "dead-normal"
    assert data["commits"]["total"] == 5
    assert data["last_commit"]["date"] == "2021-08-14"
    assert data["gap_months"] == 62


def test_target_repository_is_untouched(fixtures: dict[str, Path]) -> None:
    repo = fixtures["dead_normal"]
    before = tree_snapshot(repo)
    result = run_cli(["facts", str(repo), "--now", NOW])
    assert result.returncode == 0
    assert tree_snapshot(repo) == before


def test_report_with_grounded_model(fixtures: dict[str, Path]) -> None:
    with FakeOllama("good") as fake:
        result = run_cli(
            [
                "report",
                str(fixtures["dead_normal"]),
                "--endpoint",
                fake.endpoint,
                "--now",
                NOW,
                "--timeout",
                "30",
            ]
        )
    assert result.returncode == 0, result.stderr
    assert "AUTOPSY: dead-normal" in result.stdout
    assert "confidence: medium" in result.stdout
    assert "claims dropped" in result.stdout
    assert len(fake.requests) >= 1
    body = fake.requests[0]
    assert body["options"]["num_ctx"] == 8192
    assert body["stream"] is False


def test_report_fails_closed_on_unknown_ids(fixtures: dict[str, Path]) -> None:
    with FakeOllama("unknown_ids") as fake:
        result = run_cli(
            ["report", str(fixtures["dead_normal"]), "--endpoint", fake.endpoint, "--now", NOW]
        )
    assert result.returncode == 3
    assert "AUTOPSY" not in result.stdout
    assert "no grounded claims" in result.stderr
    assert len(fake.requests) == 3


def test_report_fails_closed_on_garbage(fixtures: dict[str, Path]) -> None:
    with FakeOllama("garbage") as fake:
        result = run_cli(
            ["report", str(fixtures["dead_normal"]), "--endpoint", fake.endpoint, "--now", NOW]
        )
    assert result.returncode == 3
    assert "AUTOPSY" not in result.stdout


def test_endpoint_must_be_loopback(fixtures: dict[str, Path]) -> None:
    result = run_cli(
        ["report", str(fixtures["dead_normal"]), "--endpoint", "http://example.com:11434"]
    )
    assert result.returncode == 2
    assert "loopback" in result.stderr


def test_output_never_overwrites(fixtures: dict[str, Path], tmp_path: Path) -> None:
    target = tmp_path / "laporan.md"
    target.write_text("keep me", encoding="utf-8")
    with FakeOllama("good") as fake:
        result = run_cli(
            [
                "report",
                str(fixtures["dead_normal"]),
                "--endpoint",
                fake.endpoint,
                "--now",
                NOW,
                "--output",
                str(target),
            ]
        )
    assert result.returncode == 2
    assert target.read_text(encoding="utf-8") == "keep me"


def test_output_markdown_is_written(fixtures: dict[str, Path], tmp_path: Path) -> None:
    target = tmp_path / "laporan.md"
    with FakeOllama("good") as fake:
        result = run_cli(
            [
                "report",
                str(fixtures["dead_normal"]),
                "--endpoint",
                fake.endpoint,
                "--now",
                NOW,
                "--output",
                str(target),
            ]
        )
    assert result.returncode == 0, result.stderr
    content = target.read_text(encoding="utf-8")
    assert content.startswith("# Autopsy: dead-normal")
    assert "hypotheses, not facts" in content


def test_ask_answers_with_evidence(fixtures: dict[str, Path]) -> None:
    with FakeOllama("good") as fake:
        result = run_cli(
            [
                "ask",
                str(fixtures["dead_normal"]),
                "--endpoint",
                fake.endpoint,
                "--now",
                NOW,
            ],
            stdin_text="when did it stop?\n",
        )
    assert result.returncode == 0, result.stderr
    assert "[M:commits]" in result.stdout or "[C:" in result.stdout


def test_ask_refuses_without_evidence(fixtures: dict[str, Path]) -> None:
    with FakeOllama("unknown_ids") as fake:
        result = run_cli(
            ["ask", str(fixtures["dead_normal"]), "--endpoint", fake.endpoint, "--now", NOW],
            stdin_text="when did it stop?\n",
        )
    assert result.returncode == 0, result.stderr
    assert "does not remember" in result.stdout


def test_context_budget_never_exceeds_limit(fixtures: dict[str, Path]) -> None:
    with FakeOllama("good") as fake:
        result = run_cli(
            [
                "report",
                str(fixtures["many_commits"]),
                "--endpoint",
                fake.endpoint,
                "--now",
                NOW,
                "--max-commits",
                "2000",
            ]
        )
    assert result.returncode == 0, result.stderr
    prompt = fake.requests[0]["prompt"]
    payload = json.loads(prompt)
    assert len(payload["evidence"]) <= 10_000
