from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import ExitCode, InputError, ModelError, NoEvidenceError, SeanceError
from .evidence import EvidencePack, Facts, Rendered, build_evidence
from .gitreader import GitReader
from .grounding import GroundingResult, validate_answer, validate_report
from .model_client import ModelClient, ModelConfig
from .prompts import (
    ASK_SCHEMA,
    ASK_SYSTEM,
    REPORT_SCHEMA,
    REPORT_SYSTEM,
    ask_prompt,
    language_note,
    report_prompt,
    tone_note,
)
from .renderer import REFUSAL, render_answer, render_report, render_report_markdown
from .retrieval import retrieve

REPORT_BUDGET = 10_000
ASK_BUDGET = 6_000
ATTEMPTS = ((0.0, 42), (0.2, 43), (0.35, 44))


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("repo", type=Path, help="path to a local git repository")
    parser.add_argument("--max-commits", type=int, default=2000, metavar="N")
    parser.add_argument("--timeout", type=float, default=240.0, metavar="SECONDS")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--now", metavar="ISO8601", help="reference time for the silence metric")


def _model(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--allow-container", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seance",
        description="Ask an abandoned git repository what happened to it.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    facts = sub.add_parser("facts", help="print deterministic evidence as JSON")
    _common(facts)
    facts.set_defaults(handler=_cmd_facts)

    report = sub.add_parser("report", help="write an autopsy report with a local model")
    _common(report)
    _model(report)
    report.add_argument("--output", type=Path, metavar="FILE")
    report.add_argument("--lang", default="en")
    report.set_defaults(handler=_cmd_report)

    ask = sub.add_parser("ask", help="ask the repository questions")
    _common(ask)
    _model(ask)
    ask.add_argument("--tone", choices=("plain", "spooky", "warnet"), default="plain")
    ask.set_defaults(handler=_cmd_ask)

    return parser


def _now(args: argparse.Namespace) -> datetime:
    raw = getattr(args, "now", None)
    if not raw:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError(f"invalid --now value: {raw}") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _load(args: argparse.Namespace) -> tuple[Facts, EvidencePack]:
    with GitReader(args.repo, timeout=args.timeout) as reader:
        facts, pack = build_evidence(reader, max_commits=args.max_commits, now=_now(args))
    if facts.total_commits == 0:
        raise NoEvidenceError("repository has no commits")
    return facts, pack


def _client(args: argparse.Namespace) -> ModelClient:
    endpoint = args.endpoint or os.environ.get("SEANCE_OLLAMA_URL") or "http://127.0.0.1:11434"
    allow_container = bool(args.allow_container) or os.environ.get("SEANCE_IN_DOCKER") == "1"
    return ModelClient(
        ModelConfig(
            endpoint=endpoint,
            model=args.model,
            timeout=args.timeout,
            allow_container=allow_container,
        )
    )


def _cmd_facts(args: argparse.Namespace) -> ExitCode:
    facts, _ = _load(args)
    print(json.dumps(facts.as_dict(), indent=2, sort_keys=True, ensure_ascii=False))
    return ExitCode.OK


def _generate_report(
    client: ModelClient, facts: Facts, pack: EvidencePack, lang: str
) -> tuple[GroundingResult, Rendered]:
    rendered = pack.render(REPORT_BUDGET)
    prompt = report_prompt(
        facts.repo_name,
        str(rendered.payload["text"]),
        [str(item) for item in rendered.payload["evidence"]],
    )
    best: GroundingResult | None = None
    for temperature, seed in ATTEMPTS:
        raw = client.generate(
            system=REPORT_SYSTEM + language_note(lang),
            prompt=prompt,
            schema=REPORT_SCHEMA,
            temperature=temperature,
            seed=seed,
        )
        try:
            payload: Any = json.loads(raw)
        except json.JSONDecodeError:
            continue
        result = validate_report(payload, pack)
        if result.kept == 0:
            continue
        if best is None or result.kept > best.kept:
            best = result
        if result.summary is not None and result.purpose is not None:
            break
    if best is None:
        raise ModelError(
            "the model produced no grounded claims after "
            f"{len(ATTEMPTS)} attempts; nothing was printed"
        )
    return best, rendered


def _cmd_report(args: argparse.Namespace) -> ExitCode:
    if args.output is not None and args.output.exists():
        raise InputError(f"refusing to overwrite existing file: {args.output}")
    facts, pack = _load(args)
    client = _client(args)
    result, rendered = _generate_report(client, facts, pack, args.lang)
    text = render_report(facts, result, dropped_evidence=rendered.dropped, model=client.model)
    print(text)
    if args.output is not None:
        markdown = render_report_markdown(
            facts, result, dropped_evidence=rendered.dropped, model=client.model
        )
        _write_exclusive(args.output, markdown)
    return ExitCode.OK


def _cmd_ask(args: argparse.Namespace) -> ExitCode:
    facts, pack = _load(args)
    client = _client(args)
    system = ASK_SYSTEM + "\n\n" + tone_note(args.tone)
    interactive = sys.stdin.isatty()
    if interactive:
        print(f"Séance for {facts.repo_name}. Ctrl-D or 'quit' to leave.")
    while True:
        try:
            question = input("you> " if interactive else "")
        except EOFError:
            break
        question = question.strip()
        if not question:
            if not interactive:
                break
            continue
        if question in {"quit", "exit"}:
            break
        retrieved = retrieve(pack, question, limit=12)
        rendered = EvidencePack(items=retrieved.items).render(ASK_BUDGET)
        prompt = ask_prompt(
            question,
            str(rendered.payload["text"]),
            [str(item) for item in rendered.payload["evidence"]],
            args.tone,
        )
        claim = None
        for attempt, (temperature, seed) in enumerate(ATTEMPTS):
            try:
                raw = client.generate(
                    system=system,
                    prompt=prompt,
                    schema=ASK_SCHEMA,
                    temperature=temperature,
                    seed=seed,
                )
            except ModelError:
                if attempt == 0:
                    raise
                break
            try:
                payload: Any = json.loads(raw)
            except json.JSONDecodeError:
                continue
            claim, _ = validate_answer(payload, pack)
            if claim is not None:
                break
        print(render_answer(claim) if claim is not None else REFUSAL)
        if not interactive:
            break
    return ExitCode.OK


def _write_exclusive(path: Path, content: str) -> None:
    if path.exists():
        raise InputError(f"refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.write("\n")
    except FileExistsError as exc:
        raise InputError(f"refusing to overwrite existing file: {path}") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    debug = bool(getattr(args, "debug", False))
    try:
        return int(args.handler(args))
    except SeanceError as exc:
        print(f"seance: {exc}", file=sys.stderr)
        if debug:
            traceback.print_exc()
        return int(exc.exit_code)
    except KeyboardInterrupt:
        print("seance: interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"seance: internal error: {exc}", file=sys.stderr)
        if debug:
            traceback.print_exc()
        return int(ExitCode.INTERNAL)


if __name__ == "__main__":
    sys.exit(main())
