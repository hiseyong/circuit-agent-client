"""Evidence used to ground future agent reasoning."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """A cited extract from a datasheet or other external source."""

    source: str
    document: str
    page: int | None = None
    section: str = ""
    content: str
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
