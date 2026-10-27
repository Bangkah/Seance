from __future__ import annotations

BIDI = frozenset("\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")
ALLOWED_CONTROLS = frozenset("\n\t")


def sanitize(value: str, *, limit: int | None = None) -> str:
    cleaned: list[str] = []
    for char in value.replace("\r\n", "\n").replace("\r", "\n"):
        if char in BIDI:
            cleaned.append(" ")
            continue
        if char in ALLOWED_CONTROLS:
            cleaned.append(char)
            continue
        if ord(char) < 0x20 or 0x7F <= ord(char) <= 0x9F:
            cleaned.append(" ")
            continue
        cleaned.append(char)
    out = "".join(cleaned)
    if limit is not None and len(out) > limit:
        out = out[:limit] + "..."
    return out


def one_line(value: str, *, limit: int | None = None) -> str:
    return sanitize(" ".join(value.split()), limit=limit)
