from __future__ import annotations

import os
import subprocess
from pathlib import Path

from conftest import run_cli


def _control_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return env


def test_hostile_repo_config_is_actually_live(fixtures: dict[str, Path]) -> None:
    repo = fixtures["hostile"]
    canary = repo.parent / "canary.txt"
    if canary.exists():
        canary.unlink()
    subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD"],
        cwd=str(repo),
        env=_control_env(),
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert canary.exists(), "fixture is not hostile; the canary never ran"
    canary.unlink()


def test_seance_never_runs_repository_config(fixtures: dict[str, Path]) -> None:
    repo = fixtures["hostile"]
    canary = repo.parent / "canary.txt"
    if canary.exists():
        canary.unlink()
    result = run_cli(["facts", str(repo), "--now", "2026-10-27T00:00:00Z"])
    assert result.returncode == 0, result.stderr
    assert not canary.exists(), "a git hook or filter from the target repo executed"
    assert "PWNED" not in result.stdout


def test_ansi_escape_is_stripped_from_output(fixtures: dict[str, Path]) -> None:
    result = run_cli(["facts", str(fixtures["hostile"]), "--now", "2026-10-27T00:00:00Z"])
    assert result.returncode == 0
    assert "\x1b" not in result.stdout
    assert "broken build" in result.stdout
