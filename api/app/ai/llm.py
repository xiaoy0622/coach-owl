"""Single encapsulated LLM client (CO-A01).

This is the ONLY place the Anthropic Claude HTTP call lives. Every AI feature
(note structurer, smart-import parser, ...) routes through here so there is one
spot to swap models, add retries, or change vendors.

Design rules, per §1.4 (AI 铁律) and the "always works offline" philosophy:

* No API key configured -> :class:`LLMUnavailableError` is raised. Callers MUST catch
  it and fall back to their deterministic heuristic. They never 500.
* Any transport/parse failure (timeout, bad key, malformed JSON, non-2xx) is
  re-raised as :class:`LLMUnavailableError` so callers have one exception to catch.
* We reuse the already-installed ``httpx`` rather than pulling in the official
  ``anthropic`` SDK: note_structurer already proved the raw Messages API call,
  it keeps the dependency surface (and supply chain) small, and the call is a
  single POST. No new dependency is justified.
* Every call emits one structured log line (model + token usage when the API
  returns it) as a lightweight cost marker.
"""
from __future__ import annotations

import json
import logging

from app.core.config import settings

logger = logging.getLogger("coachowl.ai.llm")

_ANTHROPIC_VERSION = "2023-06-01"


class LLMUnavailableError(RuntimeError):
    """Raised when the LLM cannot be used (no key) or a call failed.

    Callers catch this and degrade to their deterministic heuristic.
    """


def is_available() -> bool:
    """True when an API key is configured. Cheap pre-check for callers."""
    return bool(settings.anthropic_api_key)


def complete(
    prompt: str,
    *,
    system: str | None = None,
    max_tokens: int | None = None,
) -> str:
    """Send ``prompt`` to Claude and return the concatenated text reply.

    Raises :class:`LLMUnavailableError` when there is no API key or the call fails
    for any reason. Never raises anything else.
    """
    api_key = settings.anthropic_api_key
    if not api_key:
        raise LLMUnavailableError("no ANTHROPIC_API_KEY configured")

    model = settings.anthropic_model
    body: dict = {
        "model": model,
        "max_tokens": max_tokens or settings.anthropic_max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    try:
        import httpx

        resp = httpx.post(
            f"{settings.anthropic_base_url.rstrip('/')}/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json=body,
            timeout=settings.anthropic_timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 - any failure -> one typed signal
        logger.warning("llm.call failed model=%s err=%s", model, exc)
        raise LLMUnavailableError(str(exc)) from exc

    text = "".join(
        block.get("text", "")
        for block in data.get("content", [])
        if block.get("type") == "text"
    )
    usage = data.get("usage") or {}
    # One structured log line per call as a cost marker.
    logger.info(
        "llm.call model=%s in_tokens=%s out_tokens=%s reply_chars=%d",
        model,
        usage.get("input_tokens"),
        usage.get("output_tokens"),
        len(text),
    )
    if not text.strip():
        raise LLMUnavailableError("empty reply from model")
    return text


def structured_complete(
    prompt: str,
    *,
    system: str | None = None,
    max_tokens: int | None = None,
) -> dict | list:
    """Like :func:`complete` but parse the reply as a JSON object/array.

    Tolerates the model wrapping JSON in prose or code fences by extracting the
    outermost ``{...}`` / ``[...]``. Raises :class:`LLMUnavailableError` if no JSON
    value can be parsed.
    """
    text = complete(prompt, system=system, max_tokens=max_tokens)
    try:
        return json.loads(_extract_json(text))
    except (ValueError, json.JSONDecodeError) as exc:
        raise LLMUnavailableError(f"could not parse JSON from reply: {exc}") from exc


def _extract_json(text: str) -> str:
    """Return the outermost JSON object or array substring from ``text``."""
    candidates: list[tuple[int, int]] = []
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            candidates.append((start, end + 1))
    if not candidates:
        raise ValueError("no JSON value in model reply")
    # Prefer whichever bracket type appears first in the text.
    start, end = min(candidates, key=lambda se: se[0])
    return text[start:end]
