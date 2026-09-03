import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract the first well-formed JSON object from ``text``.

    Models on free/inference tiers sometimes wrap their structured answer in
    markdown (fenced code blocks, headings, surrounding prose). Rather than
    failing the whole investigation, try to locate the JSON object stubbornly:
    fenced blocks are stripped first, then a brace-balanced scan finds the
    outermost JSON object.
    """
    candidates = _split_candidates(text)
    for candidate in candidates:
        obj = _try_load(candidate)
        if obj is not None:
            return obj

    raise ValueError("No valid JSON object found in LLM output")


def _split_candidates(text: str) -> list[str]:
    stripped = text.strip()

    # Prefer JSON code-fence blocks ( ```json ... ``` ).
    fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)```", stripped, flags=re.IGNORECASE)
    if fenced:
        return [f.strip() for f in fenced]

    # Otherwise, look for brace-balanced substrings of increasing size.
    starts = [m.start() for m in re.finditer(r"\{", stripped)]
    found: list[str] = []
    for start in starts:
        end = _find_balanced_end(stripped, start)
        if end is not None:
            found.append(stripped[start : end + 1])
    return found


def _find_balanced_end(text: str, start: int) -> int | None:
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return None


def _try_load(candidate: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(parsed, dict):
        return parsed
    return None