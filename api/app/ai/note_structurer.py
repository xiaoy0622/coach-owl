"""Post-lesson note structurer (CO-A02).

Turns a coach's free-form jot ("did fractions, Tom struggled with common
denominators, homework: worksheet 3") into a structured candidate::

    {"topics": [...], "progress": "...", "homework": "..."}

The default path is a deterministic, network-free heuristic — it always runs and
never raises, so structuring works offline and in tests with no API key. If
``ANTHROPIC_API_KEY`` is set the heuristic result *may* be refined by a single
Anthropic call (via the already-installed ``httpx``), but we never block on it:
any error, timeout, or malformed reply falls straight back to the heuristic.

Per §1.4 (AI 铁律) this only ever returns a CANDIDATE — the caller confirms /
edits it before anything is persisted.
"""
from __future__ import annotations

import re

from app.ai import llm

# --------------------------------------------------------------------------- #
# Markers — the vocabulary the heuristic keys off. Kept deliberately broad so a
# coach can jot naturally; matching is case-insensitive on word boundaries.
# --------------------------------------------------------------------------- #
_TOPIC_MARKERS = (
    "covered",
    "worked on",
    "work on",
    "went through",
    "focused on",
    "focus on",
    "reviewed",
    "revised",
    "introduced",
    "discussed",
    "studied",
    "learned",
    "learnt",
    "practised",
    "practiced",
    "did",
    "looked at",
)
_HOMEWORK_MARKERS = (
    "homework",
    "hw",
    "for next",
    "next lesson",
    "next time",
    "to do",
    "assign",
    "worksheet",
    "exercises",
    "exercise",
    "due",
    "revise",
    "revision before",
    "complete ",
    "finish ",
    "practice ",
    "practise ",
)
_PROGRESS_MARKERS = (
    "struggl",
    "improv",
    "confiden",
    "master",
    "understood",
    "understand",
    "needs",
    "need ",
    "difficult",
    "mistake",
    "progress",
    "getting better",
    "strong",
    "weak",
    "well",
    "good ",
    "great ",
    "excellent",
    "did well",
    "doing well",
    "grasp",
)

# Explicit labelled input ("Topics: ... Progress: ... Homework: ...").
_LABEL_RE = re.compile(
    r"^\s*(topics?|progress|homework|hw)\s*[:\-]\s*(.+)$",
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"[.;\n!?]+")
_TOPIC_SPLIT = re.compile(r"\s*(?:,|/|&|\band\b|\bthen\b|\bplus\b)\s*", re.IGNORECASE)


def structure_note(raw_text: str | None) -> dict:
    """Return a candidate ``{topics, progress, homework}`` from free text.

    Never raises and never persists. The heuristic always produces a result;
    the optional LLM step only refines it when configured.
    """
    candidate = _heuristic_structure(raw_text or "")
    enhanced = _maybe_enhance_with_llm(raw_text or "", candidate)
    return enhanced or candidate


# --------------------------------------------------------------------------- #
# Deterministic heuristic (default; no network, no new dependency)
# --------------------------------------------------------------------------- #
def _heuristic_structure(raw: str) -> dict:
    raw = raw.strip()
    if not raw:
        return {"topics": [], "progress": None, "homework": None}

    labelled = _parse_labelled(raw)
    if labelled is not None:
        return labelled

    topics: list[str] = []
    progress_parts: list[str] = []
    homework_parts: list[str] = []

    for sentence in _sentences(raw):
        low = sentence.lower()
        if _has_marker(low, _HOMEWORK_MARKERS):
            homework_parts.append(_strip_homework_lead(sentence))
            continue
        extracted = _topics_from_sentence(sentence)
        if extracted:
            topics.extend(extracted)
        if _has_marker(low, _PROGRESS_MARKERS):
            progress_parts.append(sentence)
        elif not extracted:
            # Narrative with no clear role — keep it as progress context.
            progress_parts.append(sentence)

    return {
        "topics": _dedupe(topics),
        "progress": _join(progress_parts),
        "homework": _join(homework_parts),
    }


def _parse_labelled(raw: str) -> dict | None:
    """Handle explicitly labelled notes; returns None if no labels present."""
    buckets: dict[str, list[str]] = {"topics": [], "progress": [], "homework": []}
    matched = False
    for line in raw.splitlines():
        m = _LABEL_RE.match(line)
        if not m:
            continue
        matched = True
        label = m.group(1).lower()
        value = m.group(2).strip()
        if label.startswith("topic"):
            buckets["topics"].extend(_split_topics(value))
        elif label in ("homework", "hw"):
            buckets["homework"].append(value)
        else:
            buckets["progress"].append(value)
    if not matched:
        return None
    return {
        "topics": _dedupe(buckets["topics"]),
        "progress": _join(buckets["progress"]),
        "homework": _join(buckets["homework"]),
    }


def _topics_from_sentence(sentence: str) -> list[str]:
    low = sentence.lower()
    for marker in _TOPIC_MARKERS:
        idx = low.find(marker)
        if idx == -1:
            continue
        tail = sentence[idx + len(marker) :].strip(" :-,")
        # Stop the topic list at a progress/homework clause if one follows.
        tail = re.split(
            r"\b(?:but|and (?:he|she|they)|homework|hw)\b", tail, maxsplit=1
        )[0]
        return _split_topics(tail)
    return []


# Trailing temporal fillers a coach tacks on ("...percentages today").
_TRAILING_FILLER = re.compile(
    r"\s+(today|yesterday|this (?:lesson|week|session)|in class|again)$",
    re.IGNORECASE,
)


def _split_topics(value: str) -> list[str]:
    parts = _TOPIC_SPLIT.split(value)
    out: list[str] = []
    for p in parts:
        p = p.strip(" .,:-")
        p = _TRAILING_FILLER.sub("", p).strip()
        # Drop pronoun/filler fragments that aren't real topics.
        if len(p) < 2 or p.lower() in {"he", "she", "they", "we", "it", "the"}:
            continue
        out.append(p)
    return out


def _strip_homework_lead(sentence: str) -> str:
    return re.sub(
        r"^\s*(homework|hw|to do|for next (?:lesson|time)?)\s*[:\-]?\s*",
        "",
        sentence,
        flags=re.IGNORECASE,
    ).strip()


def _sentences(raw: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(raw) if s.strip()]


def _has_marker(low: str, markers: tuple[str, ...]) -> bool:
    return any(m in low for m in markers)


def _dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for it in items:
        it = it.strip()
        if it and it not in seen:
            seen.append(it)
    return seen


def _join(parts: list[str]) -> str | None:
    cleaned = [p.strip() for p in parts if p and p.strip()]
    if not cleaned:
        return None
    return ". ".join(s.rstrip(".") for s in cleaned) + "."


# --------------------------------------------------------------------------- #
# Optional LLM refinement (best-effort; never blocks the heuristic)
# --------------------------------------------------------------------------- #
_PROMPT = (
    "You tidy a tutor's rough post-lesson note into a structured progress note. "
    "Return ONLY minified JSON with keys: topics (array of short strings), "
    "progress (string or null), homework (string or null). Do not invent facts "
    "not present in the note.\n\nNote:\n"
)


def _maybe_enhance_with_llm(raw: str, fallback: dict) -> dict | None:
    if not raw.strip() or not llm.is_available():
        return None
    try:
        obj = llm.structured_complete(_PROMPT + raw, max_tokens=512)
        return _coerce(obj)
    except Exception:
        # Any failure (no network, bad key, malformed JSON, timeout) → heuristic.
        return None


def _coerce(obj: object) -> dict:
    if not isinstance(obj, dict):
        raise ValueError("model reply is not an object")
    topics = obj.get("topics") or []
    if not isinstance(topics, list):
        topics = [str(topics)]
    progress = obj.get("progress")
    homework = obj.get("homework")
    return {
        "topics": _dedupe([str(t) for t in topics if str(t).strip()]),
        "progress": str(progress).strip() if progress else None,
        "homework": str(homework).strip() if homework else None,
    }
