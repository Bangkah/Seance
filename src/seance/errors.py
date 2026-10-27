from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    INPUT = 2
    MODEL = 3
    NO_EVIDENCE = 4
    INTERNAL = 5


class SeanceError(Exception):
    exit_code: ExitCode = ExitCode.INTERNAL


class InputError(SeanceError):
    exit_code = ExitCode.INPUT


class ModelError(SeanceError):
    exit_code = ExitCode.MODEL


class NoEvidenceError(SeanceError):
    exit_code = ExitCode.NO_EVIDENCE
