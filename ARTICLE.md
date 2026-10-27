# I taught a local model to perform autopsies on dead repositories, then measured how often it lies

There is a specific kind of repository that nobody writes about: the one with a
README that describes a product, a `package.json`, two hundred commits, and a
last commit from fourteen months ago. It is not archived. It is not deleted. It
is just... not being worked on. The author moved on and the repository keeps
sitting there, describing a world that ended.

I wanted to ask those repositories what happened. And I wanted the answer to be
checkable, because the obvious way to build this — paste commit messages into a
local model and ask "why did this die?" — produces confident fiction.

So I built **Seance**. It reads the history of an abandoned repository, extracts
facts that can be verified, and lets a local open-weight model write about them.
The model writes prose. The code decides what is true.

## Three commands

```
seance facts  <repo>    # deterministic evidence as JSON, no model
seance report <repo>    # autopsy report, optional Markdown output
seance ask    <repo>    # interactive séance, with a tone flag
```

Real output, `qwen3:4b` running locally through Ollama, a six-commit repository
that died in August 2025:

```
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

And the part I care about more, the séance:

```
you> Why did the author stop working on it?

I don't remember why the author stopped working on it. The only evidence I have
is that Jofi was the sole author in history. [M:authors]
```

That is a refusal, and it is the feature. The tool would rather say it does not
know than invent a reason.

## The design bet: model speaks, code verifies

Before the model sees anything, the code builds an evidence pack. Every item has
an id it generated:

- `C:<hash>` — a commit, with author, date and subject
- `F:<path>@<hash>` — a file, at a specific commit, with a short excerpt
- `M:<name>` — a measured metric: counts, dates, authors, tags, languages, the
  month a dependency manifest was last touched

The pack is sent as JSON data, never as instructions, and the model must answer
with JSON matching a schema. Then a validator reads the answer and rejects a
claim when:

- it cites an id that does not exist in the pack
- it cites no id at all
- it quotes something that is not in the cited evidence
- it contains a hash, date or number that does not appear in that evidence

Rejected claims are removed and counted, and the count is printed. Three attempts
with different sampling, then the command exits with code 3 and prints nothing
rather than half a report. The whole thing fails closed.

The rule is deliberately structural. I am not asking the model whether it is
confident, and I am not asking a second model to grade the first. I am asking:
*can the sentence you wrote be traced to something this repository actually
contains?*

## Making it safe to point at a stranger's repository

An autopsy tool reads a repository you have not looked at. Repositories can
contain instructions for git itself. `.git/config` can point `core.fsmonitor`,
`core.pager` or `diff.external` at a script, and any tool that quietly runs
`git log` in that directory will execute it.

Seance never touches the working directory. It does a bare clone with
`git clone --bare --no-local` into a temporary directory and reads only that
clone. Git runs without a shell, with system and global config disabled,
`GIT_TERMINAL_PROMPT=0`, `--no-ext-diff`, `--no-textconv`, no pager, and a
scrubbed environment. Nothing from the repository is executed.

The test suite has a hostile fixture that points all three config keys at a
canary script, plus a fake Ollama that lies — unknown ids, fake quotes, broken
JSON. The tests assert that the canary never runs, that the source repository is
byte-identical before and after, and that ungrounded output never reaches the
terminal.

## What it got wrong

This is the part I would want to read in someone else's post.

I took 30 claims from three real reports and checked every one by hand against
`git log`, `git show` and the cited evidence. **18 were fully supported, 8 were
defensible inferences, and 4 were wrong.**

All four cited real ids, real dates and real commit text. The validator passed
them because they were traceable. They were false because the model misread the
evidence:

1. It called a February commit "the final commit" when the last commit is from
   October.
2. It said a CI workflow "was removed", pointing at the commit that adds it.
3. It suggested adding a `FUNDING.yml` file that the last commit had already
   added.
4. It named an organisation that the cited README never mentions.

This is the honest limit of structural grounding. It makes an invented hash or
number impossible. It cannot make a wrong sentence impossible. Any tool that
claims otherwise is measuring something else.

The other thing it gets wrong is timing. I also ran it on a repository that is
only three weeks old, and it printed "Gap: 0 months" and then a hypothesis about
long inactivity. It works when the silence is real.

## Numbers, measured not promised

Windows 11 laptop, Docker Desktop, Python 3.12.16, git 2.47.3 in the image,
Ollama 0.40.11 with `qwen3:4b` on the host. Wall times include container start.

| What | Repository | Result |
| --- | --- | --- |
| `facts` | 2,006 commits (2,000 analysed, cap) | 14.2 s |
| `report` | 2,006 commits | 30.3 s, 70 evidence items omitted from the 10,000-character budget |
| `report` | 232 commits | 16.8 s |
| `report` | 6 commits | 13.2 s |
| tests | 49 tests | 21.0 s, 72% coverage |

I expected the two-thousand-commit case to be slow. It is not: the evidence pack
is budgeted by characters, not by commit count, so the model sees a bounded
prompt and the git work is the only thing that scales.

## What I would do next

- A semantic check that catches the four failures above. Structural grounding is
  necessary and not sufficient; the next step is asking whether the claim's
  subject matches the cited commit's subject, which is a much narrower question
  than "is this true".
- Deterministic handling of `0 months` repositories: refuse with "this repository
  is not dead yet" instead of producing a low-confidence hypothesis.
- More manifests and a real dependency analysis, which needs parsing rather than
  file names.

## Links

- Code: https://github.com/Bangkah/Seance (MIT, Python 3.12, Docker image and CI
  included)
- Real reports and the full 30-claim audit: `demo/README.md` in the repository
- Model: `qwen3:4b` via Ollama, locally. No API keys, no data leaves the machine.

The repository was created on 27 October 2026 for this challenge; the design
notes, PRD and every commit are in the history.

## Prize categories

- **Best Use of Entire**

Model output is generated from repository text and may be wrong. Verify before
trusting. The repository text itself stays on your machine.
