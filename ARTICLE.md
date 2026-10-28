---
title: "I taught a local model to perform autopsies on dead repositories, then measured how often it lies"
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26)*

## What I Built

There is a specific kind of repository that nobody writes about: the one with a README that describes a product, a `package.json`, two hundred commits, and a last commit from fourteen months ago. It is not archived. It is not deleted. The author moved on and the repository keeps sitting there, describing a world that ended.

I read the theme as giving those repositories a voice. **Seance** reads the git history of an abandoned project, extracts facts that can be verified, and lets a local open-weight model write about them. The model writes prose. The code decides what is true.

```text
seance facts  <repo>    # deterministic evidence as JSON, no model
seance report <repo>    # autopsy report, optional Markdown output
seance ask    <repo>    # interactive séance, with a tone flag
```

## Demo

Real output, `qwen3:4b` running locally through Ollama, on a six-commit repository whose last commit is from August 2025:

```text
AUTOPSY: gudang-tugas
  Born : 2025-07-12 (C:16e5f46)
  Died : 2025-08-18 (C:d287690)  [last commit]
  Gap  : 14 months since the last commit
  Size : 6 commits, 2 authors, 0 tags

What it was
  A student task management platform with premium features for academic use.
  [F:README.md@2a192ca]

Timeline
  2025-07-12  Initial commit with login and registration forms [C:f719143]
  2025-07-14  Creation of README.md [C:2e6a90a]
  2025-08-18  Final commit creating SECURITY.md [C:d287690]

Cause of death (hypotheses, not facts)
  1. The deletion of the config directory in 2025-08-09 may have been a critical
     step that led to the project becoming unmanageable ... [C:91fba8f]  confidence: medium

2 claims dropped for lacking evidence.
```

The séance, on the same repository:

```text
you> When did work stop, and what was being changed at the end?
I remember the last commit was on 2025-08-18, creating SECURITY.md. Work stopped
after that, with no further changes for 14 months. [C:d287690, M:gap]

you> Which files mattered at the end?
The ghost does not remember which files mattered at the end. The evidence only
lists file counts by language at HEAD, not which files were important or mattered.
[M:languages]
```

The second answer is a refusal, and it is the feature. The tool would rather say it does not know than invent a reason.

## Code

{% embed https://github.com/Bangkah/Seance %}

MIT, Python 3.12, Docker image and CI included. Real reports and the full 30-claim audit are in `demo/README.md`. The repository was created on 27 October 2026 for this challenge. Some design patterns come from my earlier entry, TidyMind (a loopback-only model client, bounded retries with varied sampling, terminal-safe output); the code in this repository was written this week.

## How I Built It

**Open-source AI used:** `qwen3:4b` through Ollama 0.40.11, running locally. The runtime has no third-party Python dependencies; git is the only external tool.

### The design bet: model speaks, code verifies

Before the model sees anything, the code builds an evidence pack. Every item has an id the code generated:

- `C:<hash>`: a commit, with author, date and subject
- `F:<path>@<hash>`: a file at a specific commit, with a short excerpt
- `M:<name>`: a measured metric: counts, dates, authors, tags, languages, the month a dependency manifest was last touched

The pack is sent as JSON data, never as instructions, and the model must answer with JSON matching a schema. Then a validator rejects a claim when:

- it cites an id that does not exist in the pack, or cites no id at all
- it quotes something that is not in the cited evidence
- it contains a hash, date or number that does not appear in that evidence

Rejected claims are removed and counted, and the count is printed. After three attempts with different sampling, the command exits with code 3 and prints nothing rather than half a report.

The rule is deliberately structural. I am not asking the model whether it is confident, and I am not asking a second model to grade the first. I am asking: *can the sentence you wrote be traced to something this repository actually contains?*

### Safe to point at a stranger's repository

Repositories can contain instructions for git itself. `.git/config` can point `core.fsmonitor`, `core.pager` or `diff.external` at a script, and any tool that quietly runs `git log` in that directory will execute it.

Seance never touches the working directory. It makes a bare clone with `git clone --bare --no-local` into a temporary directory and reads only that clone. Git runs without a shell, with system and global config disabled, no terminal prompts, no pager, `--no-ext-diff`, `--no-textconv`, and a scrubbed environment.

The test suite has a hostile fixture that points those config keys at a canary script, plus a control test that proves the fixture really is hostile by running plain git against it. A fake Ollama that lies (unknown ids, fake quotes, broken JSON) checks that ungrounded output never reaches the terminal, and a snapshot check confirms the source repository is unchanged.

### What it got wrong

I took 30 claims (26 from three real reports and 4 from `ask` answers) and checked every one by hand against `git log`, `git show` and the cited evidence. **18 were fully supported, 8 were defensible inferences, and 4 were wrong.**

All four cited real ids, real dates and real commit text. The validator passed them because they were traceable. They were false because the model misread the evidence:

1. It called a February commit "the final commit" when the last commit is from October.
2. It said a CI workflow "was removed", pointing at the commit that adds it.
3. It suggested adding a `FUNDING.yml` file that the last commit had already added.
4. It named an organisation that the cited README never mentions.

This is the honest limit of structural grounding. It makes an invented hash or number impossible. It cannot make a wrong sentence impossible.

It also misjudges timing: on a repository that is only three weeks old it printed "Gap: 0 months" and then a hypothesis about long inactivity. It works when the silence is real.

### Numbers, measured

Windows 11 laptop, Docker Desktop, Python 3.12.16, git 2.47.3 in the image, Ollama 0.40.11 with `qwen3:4b` on the host. Wall times include container start.

| What | Repository | Result |
| --- | --- | --- |
| `facts` | 2,006 commits (2,000 analysed, cap) | 14.2 s |
| `report` | 2,006 commits | 30.3 s, 70 evidence items omitted from the 10,000-character budget |
| `report` | 232 commits | 16.8 s |
| `report` | 6 commits | 13.2 s |
| tests | 49 tests | 21.0 s, 72% coverage |

The two-thousand-commit case is not slow because the evidence pack is budgeted by characters, not by commit count: the model sees a bounded prompt and the git work is the only thing that scales.

### What I would do next

- A semantic check for the four failures above: whether a claim's subject matches the cited commit's subject, which is a much narrower question than "is this true".
- Deterministic handling of `0 months` repositories: refuse with "this repository is not dead yet" instead of producing a low-confidence hypothesis.
- More manifests and a real dependency analysis, which needs parsing rather than file names.

## Why Does Open Innovation Matter?

A repository's history is not always safe to send to someone else's server. Old commits can contain client names, internal paths, and secrets that were once committed and later removed. With an open-weight model running on my own machine, the history is read by a bare clone in a temporary directory and the only network connection the tool makes is to the Ollama endpoint, which is loopback unless you explicitly pass `--allow-container`. I did not run it with the network disconnected, so I am not claiming that.

Running the model myself also made the verification loop cheap. The retry logic and the 30-claim audit needed many runs, and none of them cost anything or hit a quota. The model is a command-line option on `report` and `ask` (`--model`), so a different local model can be tried without changing the code, though I only evaluated `qwen3:4b`.

## The Spirit of It

The moment that landed was not a report. It was a refusal.

I asked an abandoned project why its author stopped working on it. It answered:

> I don't remember why the author stopped working on it. The only evidence I have is that Jofi was the sole author in history.

It had every ingredient for a story like the ones I had been half-expecting all week: a lone author, six months of silence, a last commit that only adds a funding file. It could have said burnout, or money, or a rewrite. Instead it said it did not know, and showed me the one fact it did have. That is the ghost I wanted: one that refuses to invent the ending.

*Model output is generated from repository text and may be wrong. Verify before trusting.*
