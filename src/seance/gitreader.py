from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Self

from .errors import InputError
from .text import sanitize

GIT = "git"
LOG_CAP = 50_000
CONFIG_ARGS = [
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.pager=cat",
    "-c",
    "diff.external=",
    "-c",
    "gc.auto=0",
    "-c",
    "protocol.ext.allow=never",
    "-c",
    "core.quotePath=false",
    "-c",
    "log.showSignature=false",
]


def _clean_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "PAGER": "cat",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
            "LANG": "C",
            "TZ": "UTC",
        }
    )
    for key in ("GIT_ASKPASS", "SSH_ASKPASS", "GIT_SSH", "GIT_SSH_COMMAND", "GIT_PROXY_COMMAND"):
        env.pop(key, None)
    return env


@dataclass(frozen=True, slots=True)
class Commit:
    hash: str
    author: str
    authored_at: str
    committed_at: str
    subject: str

    @property
    def short(self) -> str:
        return self.hash[:7]

    @property
    def committed_at_dt(self) -> datetime:
        return datetime.fromisoformat(self.committed_at)

    @property
    def authored_at_dt(self) -> datetime:
        return datetime.fromisoformat(self.authored_at)

    @property
    def iso_date(self) -> str:
        return self.committed_at_dt.date().isoformat()


class GitReader:
    def __init__(self, repo: Path, *, timeout: float = 120.0) -> None:
        self._source = Path(repo)
        self._timeout = timeout
        self._temp: Path | None = None
        self._gitdir: Path | None = None
        self._env = _clean_env()

    def __enter__(self) -> Self:
        source = self._source.expanduser()
        if not source.exists():
            raise InputError(f"repository path does not exist: {source}")
        if not source.is_dir():
            raise InputError(f"not a directory: {source}")
        if not ((source / ".git").exists() or (source / "HEAD").is_file()):
            raise InputError(f"not a git repository: {source}")

        temp = Path(tempfile.mkdtemp(prefix="seance-"))
        clone = temp / "repo.git"
        command = [
            GIT,
            "--no-pager",
            *CONFIG_ARGS,
            "clone",
            "--bare",
            "--no-local",
            "--quiet",
            str(source.resolve()),
            str(clone),
        ]
        result = self._spawn(command, cwd=temp)
        if result.returncode != 0:
            shutil.rmtree(temp, ignore_errors=True)
            detail = sanitize(result.stderr.decode("utf-8", "replace"), limit=400).strip()
            raise InputError(f"git clone failed: {detail or 'unknown error'}")
        self._temp = temp
        self._gitdir = clone
        return self

    def __exit__(self, *exc: object) -> None:
        if self._temp is not None:
            shutil.rmtree(self._temp, ignore_errors=True)
        self._temp = None
        self._gitdir = None

    @property
    def source(self) -> Path:
        return self._source.expanduser().resolve()

    def _spawn(self, command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(
                command,
                cwd=str(cwd),
                env=self._env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise InputError(f"git timed out after {self._timeout:.0f}s") from exc
        except OSError as exc:
            raise InputError(f"cannot run git: {exc}") from exc

    def _run(self, *args: str, check: bool = True) -> bytes:
        if self._gitdir is None:
            raise RuntimeError("GitReader used outside its context manager")
        command = [
            GIT,
            "--no-pager",
            *CONFIG_ARGS,
            "--git-dir",
            str(self._gitdir),
            *args,
        ]
        result = self._spawn(command, cwd=self._gitdir)
        if check and result.returncode != 0:
            detail = sanitize(result.stderr.decode("utf-8", "replace"), limit=400).strip()
            raise InputError(f"git {args[0]} failed: {detail or 'unknown error'}")
        return result.stdout if check else b""

    def _try(self, *args: str) -> bytes | None:
        if self._gitdir is None:
            raise RuntimeError("GitReader used outside its context manager")
        command = [
            GIT,
            "--no-pager",
            *CONFIG_ARGS,
            "--git-dir",
            str(self._gitdir),
            *args,
        ]
        result = self._spawn(command, cwd=self._gitdir)
        if result.returncode != 0:
            return None
        return result.stdout

    def log(self, limit: int) -> list[Commit]:
        raw = self._run(
            "log",
            "--all",
            "-z",
            "--format=%H%x1f%an%x1f%aI%x1f%cI%x1f%s",
            "-n",
            str(LOG_CAP),
        )
        text = raw.decode("utf-8", "replace")
        commits: list[Commit] = []
        for record in text.split("\x00"):
            record = record.strip("\n\r ")
            if not record:
                continue
            parts = record.split("\x1f", 4)
            if len(parts) != 5:
                continue
            digest, author, authored, committed, subject = (part.strip() for part in parts)
            if len(digest) < 7:
                continue
            try:
                datetime.fromisoformat(committed)
                datetime.fromisoformat(authored)
            except ValueError:
                continue
            commits.append(
                Commit(
                    hash=digest,
                    author=sanitize(author, limit=80),
                    authored_at=authored,
                    committed_at=committed,
                    subject=sanitize(subject, limit=300),
                )
            )
        commits.sort(key=lambda commit: (commit.committed_at_dt, commit.hash), reverse=True)
        return commits[:limit]

    def total_commits(self) -> int:
        raw = self._run("rev-list", "--all", "--count")
        try:
            return int(raw.decode("ascii").strip())
        except ValueError:
            return 0

    def tags(self) -> list[str]:
        raw = self._try("for-each-ref", "--format=%(refname:short)", "refs/tags")
        if raw is None:
            return []
        return sorted(
            {sanitize(tag, limit=100) for tag in raw.decode("utf-8", "replace").splitlines() if tag}
        )

    def head_files(self) -> list[str]:
        raw = self._try("ls-tree", "-r", "--name-only", "-z", "HEAD")
        if raw is None:
            return []
        return [name for name in raw.decode("utf-8", "replace").split("\x00") if name]

    def head_hash(self) -> str | None:
        raw = self._try("rev-parse", "--verify", "HEAD")
        if raw is None:
            return None
        return raw.decode("ascii", "replace").strip() or None

    def blob(self, path: str, *, max_bytes: int) -> str | None:
        size_raw = self._try("cat-file", "-s", f"HEAD:{path}")
        if size_raw is None:
            return None
        try:
            size = int(size_raw.decode("ascii").strip())
        except ValueError:
            return None
        if size <= 0:
            return None
        data = self._try("cat-file", "blob", f"HEAD:{path}")
        if data is None:
            return None
        if b"\x00" in data[:4096]:
            return None
        return data[:max_bytes].decode("utf-8", "replace")

    def last_commit_for(self, path: str) -> tuple[str, str] | None:
        raw = self._try("log", "-1", "--format=%H%x1f%cI", "--", path)
        if raw is None:
            return None
        line = raw.decode("utf-8", "replace").strip("\n\r\x00 ")
        if not line:
            return None
        parts = line.split("\x1f")
        if len(parts) != 2:
            return None
        digest, committed = (part.strip() for part in parts)
        if len(digest) < 7:
            return None
        return digest, committed
