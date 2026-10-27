from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from conftest import run_cli

from seance.evidence import build_evidence
from seance.gitreader import GitReader

NOW = datetime(2026, 10, 27, tzinfo=UTC)


def facts_for(path: Path, max_commits: int = 2000) -> tuple[object, object]:
    with GitReader(path) as reader:
        facts, pack = build_evidence(reader, max_commits=max_commits, now=NOW)
    return facts, pack


def test_facts_are_deterministic(fixtures: dict[str, Path]) -> None:
    first_facts, first_pack = facts_for(fixtures["dead_normal"])
    second_facts, second_pack = facts_for(fixtures["dead_normal"])
    assert first_facts.as_dict() == second_facts.as_dict()  # type: ignore[attr-defined]
    assert [item.id for item in first_pack.items] == [  # type: ignore[attr-defined]
        item.id
        for item in second_pack.items  # type: ignore[attr-defined]
    ]


def test_cli_output_is_byte_identical(fixtures: dict[str, Path]) -> None:
    args = ["facts", str(fixtures["dead_normal"]), "--now", "2026-10-27T00:00:00Z"]
    first = run_cli(args)
    second = run_cli(args)
    assert first.returncode == 0
    assert first.stdout == second.stdout
    json.loads(first.stdout)


def test_dead_normal_metrics(fixtures: dict[str, Path]) -> None:
    facts, pack = facts_for(fixtures["dead_normal"])
    assert facts.total_commits == 5  # type: ignore[attr-defined]
    assert facts.first.iso_date == "2019-03-02"  # type: ignore[attr-defined]
    assert facts.last.iso_date == "2021-08-14"  # type: ignore[attr-defined]
    assert facts.gap_months == 62  # type: ignore[attr-defined]
    assert facts.authors == ("Ada Lovelace", "Bob Stone")  # type: ignore[attr-defined]
    assert "v0.4" in facts.tags  # type: ignore[attr-defined]
    assert any(item.path == "requirements.txt" for item in facts.manifests)  # type: ignore[attr-defined]
    ids = {item.id for item in pack.items}  # type: ignore[attr-defined]
    assert "M:commits" in ids
    assert f"C:{facts.last.short}" in ids  # type: ignore[attr-defined]
    assert any(item_id.startswith("F:README.md@") for item_id in ids)


def test_evidence_ids_are_unique_and_ordered(fixtures: dict[str, Path]) -> None:
    _, pack = facts_for(fixtures["many_commits"])
    ids = [item.id for item in pack.items]  # type: ignore[attr-defined]
    assert len(ids) == len(set(ids))
    assert ids[0].startswith("M:")


def test_many_commits_is_capped(fixtures: dict[str, Path]) -> None:
    facts, _ = facts_for(fixtures["many_commits"], max_commits=10)
    assert facts.total_commits == 60  # type: ignore[attr-defined]
    assert facts.analyzed_commits == 10  # type: ignore[attr-defined]
    assert facts.capped is True  # type: ignore[attr-defined]


def test_binary_and_non_utf8_do_not_crash(fixtures: dict[str, Path]) -> None:
    facts, pack = facts_for(fixtures["binary_and_encoding"])
    assert facts.total_commits == 2  # type: ignore[attr-defined]
    assert any(item.path == "package.json" for item in facts.manifests)  # type: ignore[attr-defined]
    languages = dict(facts.languages)  # type: ignore[attr-defined]
    assert languages.get("JavaScript") == 1
    assert all(item.text for item in pack.items)  # type: ignore[attr-defined]


def test_repository_without_manifest(fixtures: dict[str, Path]) -> None:
    facts, _ = facts_for(fixtures["no_manifest"])
    assert facts.manifests == ()  # type: ignore[attr-defined]
    assert facts.languages == ()  # type: ignore[attr-defined]


def test_readme_excerpt_is_evidence(fixtures: dict[str, Path]) -> None:
    _, pack = facts_for(fixtures["dead_normal"])
    readme = [item for item in pack.items if item.kind == "readme"]  # type: ignore[attr-defined]
    assert readme
    assert "logrot" in readme[0].text
    assert readme[0].text.startswith("README README.md (excerpt):")
