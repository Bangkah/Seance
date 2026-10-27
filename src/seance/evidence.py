from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .gitreader import Commit, GitReader

MANIFESTS = frozenset(
    {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "package.json",
        "go.mod",
        "Cargo.toml",
        "Gemfile",
        "composer.json",
        "pom.xml",
        "build.gradle",
        "Pipfile",
    }
)
README_NAMES = frozenset({"readme", "readme.md", "readme.rst", "readme.txt", "readme.markdown"})
KEYWORDS = re.compile(
    r"\b(deprecat\w*|broken|break\w*|abandon\w*|todo|fixme|hack|unmaintain\w*|"
    r"remove[ds]?|drop\w*|stale|dead|eol|legacy|wip)\b",
    re.IGNORECASE,
)
EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".h": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cs": "C#",
    ".sh": "Shell",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".md": "Markdown",
}
MAX_README_CHARS = 1_800


@dataclass(frozen=True, slots=True)
class Evidence:
    id: str
    kind: str
    text: str


@dataclass(frozen=True, slots=True)
class Manifest:
    path: str
    commit: str
    changed_at: str


@dataclass(frozen=True, slots=True)
class Facts:
    repo_name: str
    as_of: str
    total_commits: int
    analyzed_commits: int
    capped: bool
    first: Commit | None
    last: Commit | None
    authors: tuple[str, ...]
    tags: tuple[str, ...]
    manifests: tuple[Manifest, ...]
    languages: tuple[tuple[str, int], ...]
    gap_months: int | None
    span_days: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo_name,
            "as_of": self.as_of,
            "commits": {
                "total": self.total_commits,
                "analyzed": self.analyzed_commits,
                "capped": self.capped,
            },
            "first_commit": _commit_dict(self.first),
            "last_commit": _commit_dict(self.last),
            "authors": list(self.authors),
            "tags": list(self.tags),
            "manifests": [
                {"path": item.path, "commit": item.commit, "changed_at": item.changed_at}
                for item in self.manifests
            ],
            "languages": [{"name": name, "files": files} for name, files in self.languages],
            "gap_months": self.gap_months,
            "span_days": self.span_days,
        }


def _commit_dict(commit: Commit | None) -> dict[str, Any] | None:
    if commit is None:
        return None
    return {
        "hash": commit.hash,
        "short": commit.short,
        "author": commit.author,
        "date": commit.iso_date,
        "committed_at": commit.committed_at,
        "subject": commit.subject,
    }


@dataclass(frozen=True, slots=True)
class Rendered:
    payload: dict[str, Any]
    included: tuple[str, ...]
    dropped: int


@dataclass(frozen=True, slots=True)
class EvidencePack:
    items: tuple[Evidence, ...]

    @property
    def by_id(self) -> dict[str, Evidence]:
        return {item.id: item for item in self.items}

    def get(self, evidence_id: str) -> Evidence | None:
        for item in self.items:
            if item.id == evidence_id:
                return item
        return None

    def render(self, budget: int) -> Rendered:
        included: list[str] = []
        lines: list[str] = []
        used = 0
        dropped = 0
        for item in self.items:
            cost = len(item.id) + len(item.text) + 8
            if used + cost > budget:
                dropped += 1
                continue
            used += cost
            included.append(item.id)
            lines.append(f"[{item.id}] {item.text}")
        payload: dict[str, Any] = {"evidence": included, "text": "\n".join(lines)}
        return Rendered(payload=payload, included=tuple(included), dropped=dropped)


def build_evidence(
    reader: GitReader,
    *,
    max_commits: int,
    now: datetime,
    readme_chars: int = MAX_README_CHARS,
) -> tuple[Facts, EvidencePack]:
    total = reader.total_commits()
    commits = reader.log(max_commits)
    first = commits[-1] if commits else None
    last = commits[0] if commits else None
    authors = tuple(sorted({commit.author for commit in commits}))
    tags = tuple(reader.tags())

    head_files = sorted(reader.head_files())
    manifest_paths = sorted(path for path in head_files if path.rsplit("/", 1)[-1] in MANIFESTS)
    readme_path = next(
        (path for path in head_files if "/" not in path and path.lower() in README_NAMES),
        None,
    )

    manifests: list[Manifest] = []
    for path in manifest_paths:
        last_change = reader.last_commit_for(path)
        if last_change is None:
            continue
        manifests.append(Manifest(path=path, commit=last_change[0][:7], changed_at=last_change[1]))

    languages = _languages(head_files)
    gap_months = _gap_months(last, now) if last is not None else None
    span_days = (
        (last.committed_at_dt - first.committed_at_dt).days
        if first is not None and last is not None
        else None
    )

    facts = Facts(
        repo_name=_repo_name(reader),
        as_of=now.astimezone(UTC).isoformat(),
        total_commits=total,
        analyzed_commits=len(commits),
        capped=total > len(commits),
        first=first,
        last=last,
        authors=authors,
        tags=tags,
        manifests=tuple(manifests),
        languages=languages,
        gap_months=gap_months,
        span_days=span_days,
    )
    items = _items(facts, commits, reader, readme_path, readme_chars)
    return facts, EvidencePack(items=tuple(items))


def _repo_name(reader: GitReader) -> str:
    source = reader.source
    return source.name or str(source)


def _languages(head_files: list[str]) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for path in head_files:
        name = path.rsplit("/", 1)[-1]
        if "." not in name:
            continue
        suffix = "." + name.rsplit(".", 1)[-1].lower()
        language = EXTENSIONS.get(suffix)
        if language is None:
            continue
        counts[language] = counts.get(language, 0) + 1
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return tuple(ordered[:5])


def _gap_months(last: Commit | None, now: datetime) -> int | None:
    if last is None:
        return None
    last_dt = last.committed_at_dt
    naive_now = now.astimezone(UTC)
    months = (naive_now.year - last_dt.year) * 12 + (naive_now.month - last_dt.month)
    if naive_now.day < last_dt.day:
        months -= 1
    return max(months, 0)


def _items(
    facts: Facts,
    commits: list[Commit],
    reader: GitReader,
    readme_path: str | None,
    readme_chars: int,
) -> list[Evidence]:
    items: list[Evidence] = []
    seen: set[str] = set()

    def add(evidence: Evidence) -> None:
        if evidence.id in seen:
            return
        seen.add(evidence.id)
        items.append(evidence)

    add(Evidence("M:commits", "metric", f"{facts.total_commits} commits in total."))
    if facts.first is not None:
        add(
            Evidence(
                "M:first_commit",
                "metric",
                f"First commit {facts.first.short} on {facts.first.iso_date} "
                f"by {facts.first.author}.",
            )
        )
    if facts.last is not None:
        add(
            Evidence(
                "M:last_commit",
                "metric",
                f"Last commit {facts.last.short} on {facts.last.iso_date} by {facts.last.author}.",
            )
        )
    if facts.gap_months is not None:
        add(
            Evidence(
                "M:gap",
                "metric",
                f"{facts.gap_months} months since the last commit, measured on {facts.as_of[:10]}.",
            )
        )
    add(
        Evidence(
            "M:authors",
            "metric",
            f"{len(facts.authors)} author names in history: {', '.join(facts.authors[:12])}.",
        )
    )
    add(
        Evidence(
            "M:tags",
            "metric",
            f"{len(facts.tags)} tags: {', '.join(facts.tags[:12])}." if facts.tags else "0 tags.",
        )
    )
    if facts.languages:
        rendered = ", ".join(f"{name} ({count} files)" for name, count in facts.languages)
        add(Evidence("M:languages", "metric", f"Files by language at HEAD: {rendered}."))
    if facts.manifests:
        rendered = ", ".join(item.path for item in facts.manifests)
        add(Evidence("M:manifests", "metric", f"Dependency manifests at HEAD: {rendered}."))

    for commit in (facts.first, facts.last):
        if commit is not None:
            add(_commit_evidence(commit))

    if readme_path is not None:
        text = reader.blob(readme_path, max_bytes=readme_chars * 4)
        if text:
            anchor = reader.last_commit_for(readme_path)
            digest = anchor[0][:7] if anchor is not None else "working"
            excerpt = text[:readme_chars]
            add(
                Evidence(
                    f"F:{readme_path}@{digest}",
                    "readme",
                    f"README {readme_path} (excerpt):\n{excerpt}",
                )
            )

    for manifest in facts.manifests:
        add(
            Evidence(
                f"F:{manifest.path}@{manifest.commit}",
                "file",
                f"{manifest.path} was last changed in {manifest.commit} "
                f"on {manifest.changed_at[:10]}.",
            )
        )

    for commit in commits:
        if KEYWORDS.search(commit.subject):
            add(_commit_evidence(commit))

    for commit in commits[:30]:
        add(_commit_evidence(commit))

    return items


def _commit_evidence(commit: Commit) -> Evidence:
    return Evidence(
        f"C:{commit.short}",
        "commit",
        f"Commit {commit.short} by {commit.author} on {commit.iso_date}: {commit.subject}",
    )
