"""Evidence used to ground future agent reasoning."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, model_validator

_KNOWN_FIELDS = {
    "source",
    "document",
    "page",
    "section",
    "content",
    "confidence",
    "metadata",
    "raw",
    "url",
    "datasheet_url",
    "coordinate",
    "coordinates",
}


class Evidence(BaseModel):
    """A cited extract from a datasheet or other external source."""

    source: str
    document: str
    page: int | None = None
    url: str = ""
    coordinates: list[Any] = Field(default_factory=list)
    section: str = ""
    content: str
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _fill_url(self) -> Evidence:
        if not self.url:
            object.__setattr__(self, "url", evidence_url(self.metadata, self.raw))
        if not self.coordinates:
            object.__setattr__(self, "coordinates", _coordinates_payload(self.metadata, self.raw))
        return self


def evidence_from_payload(item: dict[str, Any]) -> Evidence:
    """Map one server evidence object, keeping the original JSON."""

    nested = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    extra = {key: value for key, value in item.items() if key not in _KNOWN_FIELDS}
    return Evidence(
        source=str(item.get("source") or ""),
        document=str(item.get("document") or ""),
        page=_optional_int(item.get("page")),
        url=evidence_url(item, nested),
        coordinates=_coordinates_payload(item, nested),
        section=str(item.get("section") or ""),
        content=str(item.get("content") or ""),
        confidence=_optional_float(item.get("confidence")),
        metadata={**nested, **extra},
        raw=dict(item),
    )


def evidence_url(*sources: dict[str, Any] | None) -> str:
    """Accept datasheet_url or url from the payload or nested metadata."""

    for source in sources:
        if not source:
            continue
        for key in ("datasheet_url", "url"):
            raw = str(source.get(key) or "").strip()
            if raw.startswith("https://") or raw.startswith("http://"):
                return raw
    return ""


def _coordinates_payload(*sources: dict[str, Any] | None) -> list[Any]:
    for source in sources:
        if not source:
            continue
        raw = source.get("coordinates", source.get("coordinate"))
        if raw is None or raw == "":
            continue
        return list(raw) if isinstance(raw, list) else [raw]
    return []


def parse_evidence_boxes(raw: Any) -> list[dict[str, float]]:
    """Turn API coordinate points or boxes into page-normalized highlight rects."""

    if raw is None or raw == "" or raw == []:
        return []
    if isinstance(raw, dict):
        box = _one_box(raw)
        return [box] if box else []
    if not isinstance(raw, list):
        return []
    if raw and all(_is_point(item) for item in raw):
        box = _points_to_box(raw)
        return [box] if box else []
    boxes: list[dict[str, float]] = []
    for item in raw:
        box = _one_box(item)
        if box is not None:
            boxes.append(box)
    return boxes


def _is_point(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and "x" in value
        and "y" in value
        and "w" not in value
        and "h" not in value
        and "width" not in value
        and "height" not in value
    )


def _points_to_box(points: list[Any]) -> dict[str, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    for point in points:
        if not isinstance(point, dict):
            continue
        x = _optional_float(point.get("x"))
        y = _optional_float(point.get("y"))
        if x is None or y is None:
            continue
        xs.append(x)
        ys.append(y)
    if len(xs) < 2:
        return None
    return _clamp_box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _one_box(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    if "width" in value or "w" in value or "height" in value or "h" in value:
        x = _optional_float(value.get("x"))
        y = _optional_float(value.get("y"))
        width = _optional_float(value.get("w", value.get("width")))
        height = _optional_float(value.get("h", value.get("height")))
        if None in {x, y, width, height}:
            return None
        return _clamp_box(x, y, width, height)
    if {"x1", "y1", "x2", "y2"} <= value.keys():
        x1 = _optional_float(value.get("x1"))
        y1 = _optional_float(value.get("y1"))
        x2 = _optional_float(value.get("x2"))
        y2 = _optional_float(value.get("y2"))
        if None in {x1, y1, x2, y2}:
            return None
        return _clamp_box(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
    if {"left", "top", "right", "bottom"} <= value.keys():
        left = _optional_float(value.get("left"))
        top = _optional_float(value.get("top"))
        right = _optional_float(value.get("right"))
        bottom = _optional_float(value.get("bottom"))
        if None in {left, top, right, bottom}:
            return None
        return _clamp_box(left, top, right - left, bottom - top)
    return None


def _clamp_box(x: float, y: float, width: float, height: float) -> dict[str, float] | None:
    if width <= 0 or height <= 0:
        return None
    return {
        "x": max(0.0, min(x, 1.0)),
        "y": max(0.0, min(y, 1.0)),
        "w": max(0.0, min(width, 1.0)),
        "h": max(0.0, min(height, 1.0)),
    }


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
    url = evidence_url({"url": entry.url}, entry.metadata, entry.raw)
    return {
        "document": entry.document,
        "page": "" if entry.page is None else str(entry.page),
        "pageNumber": entry.page or 0,
        "section": entry.section,
        "content": entry.content,
        "source": entry.source,
        "confidence": "" if entry.confidence is None else f"{entry.confidence:.0%}",
        "location": "  ·  ".join(location_parts),
        "url": url,
        "canOpen": bool(url),
        "coordinates": parse_evidence_boxes(entry.coordinates)
        or parse_evidence_boxes(entry.raw.get("coordinates") or entry.raw.get("coordinate")),
        "extras": extras,
        "json": evidence_json(entry),
    }
