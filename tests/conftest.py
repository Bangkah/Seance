from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _load_fixtures_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "make_fixtures", ROOT / "scripts" / "make_fixtures.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load scripts/make_fixtures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def fixtures(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("fixtures")
    built: dict[str, Path] = _load_fixtures_module().build_all(root)
    return built


def run_cli(
    args: list[str], *, timeout: float = 180.0, stdin_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    env: dict[str, str] = {
        key: value for key, value in os.environ.items() if not key.startswith("SEANCE_")
    }
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "seance", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=timeout,
        check=False,
        input=stdin_text,
    )


def tree_snapshot(root: Path) -> dict[str, tuple[int, int]]:
    return {
        str(path.relative_to(root)): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def json_facts(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    import json

    return json.loads(result.stdout)
