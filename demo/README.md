# Demo artifacts

Real output from real repositories, produced on 27 October 2026 with
`qwen3:4b` on Ollama 0.40.11, Docker image `seance:dev`.

| File | Repository | Commits | Wall time |
| --- | --- | --- | --- |
| `gudang-tugas.md` | `gudang-tugas`, last commit 2025-08-18 | 6 | 13.2 s |
| `soul-of-waifu.md` | `Soul-of-Waifu`, last commit 2026-04-05 | 232 | 16.8 s |
| `devops-daily.md` | `devops-daily`, last commit 2026-10-06 | 2,006 total, 2,000 analysed (cap reached) | 30.3 s |

Commands, verbatim:

```bash
docker run --rm -e SEANCE_OLLAMA_URL=http://host.docker.internal:11434 \
  -v /repos:/repos:ro -v "$PWD/demo:/demo" seance:dev \
  report /repos/gudang-tugas --output /demo/gudang-tugas.md \
  --now 2026-10-27T00:00:00Z
```

`--now` is pinned so the silence metric is reproducible. The same command with
`soul-of-waifu` and `devops-daily` produced the other two files.

## Ask transcripts

```
$ printf 'When did work stop, and what was being changed at the end?' \
    | seance ask /repos/gudang-tugas --tone spooky
I remember the last commit was on 2025-08-18, creating SECURITY.md. Work stopped
after that, with no further changes for 14 months. [C:d287690, M:gap]
```

```
$ printf 'What was the project for, and who worked on it?' | seance ask /repos/devops-daily
The project is DevOps Daily, a community-driven platform for DevOps professionals.
It was built by The-DevOps-Daily organization. [F:README.md@eeda668]
```

```
$ printf 'Why did the author stop working on it?' | seance ask /repos/Soul-of-Waifu --tone spooky
I don't remember why the author stopped working on it. The only evidence I have
is that Jofi was the sole author in history. [M:authors]
```

```
$ printf 'Which files mattered at the end?' | seance ask /repos/gudang-tugas
The ghost does not remember which files mattered at the end. The evidence only
lists file counts by language at HEAD, not which files were important or mattered.
[M:languages]
```

The last two are refusals. They are the behaviour the whole design is for: the
tool would rather say it does not know than invent a story.

## Claim audit, 30 claims

Every claim from the three reports and the four answers, checked by hand against
`git log`, `git show` and the cited evidence.

Verdicts: **OK** = the cited evidence says this. **INFERRED** = the evidence is
real and the conclusion is a reading of it, labelled as a hypothesis or a
suggestion. **WRONG** = the evidence does not support it.

| # | Claim (abridged) | Source | Evidence | Verdict |
| --- | --- | --- | --- | --- |
| 1 | student task platform with premium features | gudang-tugas | `F:README.md@2a192ca` | OK |
| 2 | web app, payment verification, two roles | gudang-tugas | `F:README.md@2a192ca` | OK |
| 3 | initial commit adds login/register forms | gudang-tugas | `C:f719143` | OK |
| 4 | README created | gudang-tugas | `C:2e6a90a` | OK |
| 5 | final commit creates SECURITY.md | gudang-tugas | `C:d287690` | OK |
| 6 | deleting config dir made it unmanageable | gudang-tugas | `C:91fba8f` | INFERRED |
| 7 | SECURITY.md was the last thing, then silence | gudang-tugas | `C:d287690` | INFERRED |
| 8 | update README with current status | gudang-tugas | `M:languages` | INFERRED |
| 9 | community DevOps content platform | devops-daily | `F:README.md@eeda668` | OK |
| 10 | Next.js/React/TypeScript site for devops-daily.com | devops-daily | `F:README.md@eeda668`, `C:9bd684d` | OK |
| 11 | initial commit merges command ideas | devops-daily | `M:first_commit` | OK |
| 12 | old comments removed on 2026-02-13 | devops-daily | `C:3d0b2bd` | OK |
| 13 | last commit clarifies continuous deployment | devops-daily | `C:35b8aed` | OK |
| 14 | inactive 0 months, recent cessation | devops-daily | `M:gap` | INFERRED |
| 15 | last commit was a technical fix | devops-daily | `C:35b8aed` | INFERRED |
| 16 | **the final commit removed old comments** | devops-daily | `C:3d0b2bd` | **WRONG** |
| 17 | **reintroduce a CI workflow that was removed** | devops-daily | `C:12a48d2` | **WRONG** |
| 18 | fix broken links, add a link checker | devops-daily | `C:27c6161` | INFERRED |
| 19 | offline AI roleplay engine | soul-of-waifu | `F:README.md@38c833e` | OK |
| 20 | uncensored, Live2D/VRM, long-term memory | soul-of-waifu | `F:README.md@38c833e` | OK |
| 21 | initial commit on 2023-09-02 | soul-of-waifu | `C:3b76d6c` | OK |
| 22 | README v2.3.0 on 2026-04-01 | soul-of-waifu | `C:38c833e` | OK |
| 23 | last commit adds FUNDING.yml on 2026-04-05 | soul-of-waifu | `C:27d171a` | OK |
| 24 | FUNDING.yml means a shift to funding | soul-of-waifu | `C:27d171a` | INFERRED |
| 25 | no tags, so never officially released | soul-of-waifu | `F:README.md@38c833e` | INFERRED |
| 26 | **add a FUNDING.yml file** | soul-of-waifu | `C:27d171a` | **WRONG** |
| 27 | stopped 2025-08-18, 14 months of silence | ask | `C:d287690`, `M:gap` | OK |
| 28 | **built by The-DevOps-Daily organization** | ask | `F:README.md@eeda668` | **WRONG** |
| 29 | refusal: only Jofi authored it | ask | `M:authors` | OK |
| 30 | refusal: only file counts by language exist | ask | `M:languages` | OK |

**Result: 18 OK, 8 INFERRED, 4 WRONG.**

The four wrong claims were not caught by the validator. All four cite real ids,
real dates and real commit text; they are wrong because the model misread the
evidence. Claim 16 called a February commit "the final commit" when the final
commit is from October. Claim 17 said a workflow "was removed" when the cited
commit adds it. Claim 26 suggests adding a file that is already there. Claim 28
invented an organisation name that the README never mentions.

This is the honest limit of structural grounding: it makes an invented hash or
number impossible, and it cannot make a wrong sentence impossible. Any tool that
claims otherwise is measuring something else.

## Not here

A terminal recording (asciinema/GIF) is recorded by hand from exactly the
commands above, because this environment cannot capture a TTY. The text above is
copied from real runs, not written by hand.
