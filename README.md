# Seance

Talk to a repository that has been dead for years.

Seance is a local command-line tool that reads the git history of an abandoned
project, extracts evidence that can be checked, and lets a local open-weight model
speak about that evidence. The model writes prose. The code decides what is true.

Built for **Hacktoberfest 2026, Open-Source AI Challenge Week 4 — "Ghost in the
Machine"**. The project was started on 27 October 2026 and is new code; nothing
was carried over from an earlier repository.

## What it does

```
AUTOPSY: gudang-tugas
  Born : 2025-07-12 (C:16e5f46)
  Died : 2025-08-18 (C:d287690)  [last commit]
  Gap  : 14 months since the last commit
  Size : 6 commits, 2 authors, 0 tags

What it was
  A student task management platform with premium features for academic use.
  [F:README.md@2a192ca]

Cause of death (hypotheses, not facts)
  1. The deletion of the config directory in 2025-08-09 may have been a critical
     step ... [C:91fba8f]  confidence: medium

2 claims dropped for lacking evidence.
```

Every claim carries an evidence id that the code generated. `C:` is a commit,
`F:` a file at a specific commit, `M:` a measured metric. The model may only cite
ids that exist, and may only write numbers, dates and hashes that appear in the
evidence it cites. Anything else is dropped and counted.

It also runs a séance: ask the repository questions and get answers that name
their evidence, or a fixed refusal when the evidence does not support one.

```
$ seance ask ~/old-project --tone spooky
you> When did work stop, and what was being changed at the end?
I remember the last commit was on 2025-08-18, creating SECURITY.md. Work stopped
after that, with no further changes for 14 months. [C:d287690, M:gap]
```

## Three commands

| Command | What it needs | What it prints |
| --- | --- | --- |
| `seance facts <repo>` | git only | Deterministic evidence as JSON. No model, no network. |
| `seance report <repo>` | git + Ollama | Autopsy report, optionally to a Markdown file. |
| `seance ask <repo>` | git + Ollama | Interactive séance over the extracted evidence. |

Common options: `--max-commits` (default 2000), `--timeout`, `--now` (reference
time for the silence metric, useful for reproducible output), `--debug`.
`report` adds `--output`, `--model`, `--endpoint`, `--lang`.
`ask` adds `--tone plain|spooky|warnet`.

Exit codes: `0` success, `2` bad input, `3` model unreachable or output not
grounded, `4` not enough evidence, `5` internal error.

## Run it with Docker

```bash
docker build -t seance .

# evidence only, no model, repository mounted read-only
docker run --rm -v "$PWD/my-old-repo:/repo:ro" seance facts /repo

# with an Ollama running on your host
docker run --rm -e SEANCE_OLLAMA_URL=http://host.docker.internal:11434 \
  -v "$PWD/my-old-repo:/repo:ro" seance report /repo --allow-container
```

Or run the CLI and the model together. The compose file mounts the Seance
directory at `/work`, so a repository you want to autopsy goes inside it:

```bash
cp -r ~/my-old-repo ./my-old-repo
docker compose run --rm seance report /work/my-old-repo
```

The container is the supported development and test environment (Python 3.12 +
git). `--allow-container` exists because a loopback-only endpoint cannot reach a
model that lives outside the container; it is off by default and only widens the
allowlist to `host.docker.internal` and the compose service name `ollama`.

## Run it natively

Requirements: Python 3.12, git, and [Ollama](https://ollama.com) with an
open-weight model, for example `ollama pull qwen3:4b`.

```bash
pip install -e .
seance facts ~/old-project
seance report ~/old-project --output autopsy.md
seance ask ~/old-project --tone spooky
```

The only network endpoint Seance will talk to is `localhost`, `127.0.0.1` or
`::1`, on `/api/generate`. Proxy environment variables are ignored for that
connection.

## How it stays honest

1. **Read-only, no execution.** The target repository is cloned with
   `git clone --bare --no-local` into a temporary directory, and only that clone
   is read. No checkout, no submodules, no code from the repository is ever run.
   Git is invoked without a shell, with system and global config disabled,
   `GIT_TERMINAL_PROMPT=0`, `--no-ext-diff`, `--no-textconv` and no pager.
2. **The code owns the facts.** First and last commit, counts, dates, authors,
   tags, languages, dependency manifests and the date each manifest was last
   touched are computed from git, never written by the model.
3. **The model only writes prose.** It receives the evidence pack as JSON data
   (never as instructions) and must return JSON matching a schema.
4. **A validator rejects what it cannot prove.** Unknown ids, empty id lists,
   fabricated quotes, and numbers, dates or hashes that do not appear in the
   cited evidence are rejected. Rejected claims are removed and counted.
5. **Fail closed.** Three attempts with different sampling, then the command
   exits with code 3 and prints nothing rather than half a report.

The tests include a deliberately hostile repository whose `.git/config` points
`core.fsmonitor`, `core.pager` and `diff.external` at a canary script, plus a
fake Ollama that lies (unknown ids, fake quotes, broken JSON). The suite asserts
the canary never runs, the target repository is byte-identical before and after,
and ungrounded output never reaches the terminal.

## Measured, not promised

All numbers below were measured on 27 October 2026 on the development laptop:
Windows 11, Docker Desktop, Python 3.12.16, git 2.47.3 (inside the image),
Ollama 0.40.11 with `qwen3:4b` on the host. Wall times include container
start-up, so they are pessimistic.

| What | Repository | Result |
| --- | --- | --- |
| `facts` | 2,006 commits (2,000 analysed, cap reached) | 14.2 s |
| `report` | 2,006 commits (2,000 analysed) | 30.3 s, 70 evidence items omitted from the 10,000-character budget, 0 claims dropped |
| `report` | 6 commits | 13.2 s, 2 claims dropped |
| `report` | 232 commits | 16.8 s |
| test suite | 49 tests | 21.0 s in-container, 72% coverage |

The 120-second target was a hypothesis; two thousand commits came in far below
it. These are single runs on one machine, not a benchmark.

## What went wrong, and what this does not do

- **Structural grounding is not semantic truth.** I audited 30 claims from three
  real reports by hand against `git log` and the cited evidence: 18 were fully
  supported, 8 were defensible inferences, and **4 were wrong**. All four cited
  real ids, real dates and real commit text; the model misread them. One called a
  February commit "the final commit" when the last commit is from October. One
  said a CI workflow "was removed" when the cited commit adds it. The validator
  makes an invented hash or number impossible; it cannot make a wrong sentence
  impossible. The audit is in [`demo/README.md`](demo/README.md).
- **A repository that is only three weeks old is not dead.** On that repository
  the tool printed "Gap: 0 months" and then a hypothesis about "inactivity for
  months". It works when the silence is real.
- Recognised dependency manifests: `pyproject.toml`, `setup.py`, `setup.cfg`,
  `requirements.txt`, `Pipfile`, `package.json`, `go.mod`, `Cargo.toml`,
  `Gemfile`, `composer.json`, `pom.xml`, `build.gradle`.
- No code is analysed beyond file names, manifests and commit messages.
- No security or CVE analysis: that would need an external database.
- Reports are model output. Verify before trusting.

## Development

```bash
docker build -t seance:dev .
docker run --rm -v "$PWD:/work" -w /work -e PYTHONPATH=/work/src \
  --entrypoint sh seance:dev -c "python -m pytest --cov=seance && ruff check . && mypy && bandit -q -r src -c pyproject.toml"
```

Fixtures are generated by `scripts/make_fixtures.py` with fixed dates and authors,
so hashes are reproducible. `demo/` holds real output from real repositories.

## License

MIT. See [LICENSE](LICENSE).

Model output is generated from repository text and may be wrong. The repository
text itself stays on your machine.
