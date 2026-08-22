"""Evidence used to ground future agent reasoning."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

_KNOWN_FIELDS = {
    "source",
    "document",
    "page",
    "section",
    "content",
    "confidence",
    "metadata",
    "raw",
}


class Evidence(BaseModel):
    """A cited extract from a datasheet or other external source."""

    source: str
    document: str
    page: int | None = None
    section: str = ""
    content: str
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


def evidence_from_payload(item: dict[str, Any]) -> Evidence:
    """Map one server evidence object, keeping the original JSON."""

    nested = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    extra = {key: value for key, value in item.items() if key not in _KNOWN_FIELDS}
    return Evidence(
        source=str(item.get("source") or ""),
        document=str(item.get("document") or ""),
        page=_optional_int(item.get("page")),
        section=str(item.get("section") or ""),
        content=str(item.get("content") or ""),
        confidence=_optional_float(item.get("confidence")),
        metadata={**nested, **extra},
        raw=dict(item),
    )


def _optional_int(value: Any) -> int | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evidence_json(entry: Evidence) -> str:
    """Pretty-print the original payload, or the stored fields if none was kept."""

    if entry.raw:
        data: Any = entry.raw
    else:
        data = entry.model_dump(mode="json", exclude={"raw"}, exclude_none=True)
        if not data.get("metadata"):
            data.pop("metadata", None)
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def evidence_card(entry: Evidence) -> dict[str, Any]:
    """Fields the Issues view uses to explain one citation."""

    extras = [f"{key}: {value}" for key, value in entry.metadata.items()]
    location_parts: list[str] = []
    if entry.page is not None:
        location_parts.append(f"p.{entry.page}")
    if entry.section:
        location_parts.append(entry.section)
    return {
        "document": entry.document,
        "page": "" if entry.page is None else str(entry.page),
        "section": entry.section,
        "content": entry.content,
        "source": entry.source,
        "confidence": "" if entry.confidence is None else f"{entry.confidence:.0%}",
        "location": "  ·  ".join(location_parts),
        "extras": extras,
        "json": evidence_json(entry),
    }
