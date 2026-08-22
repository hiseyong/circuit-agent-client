"""Minimal offline-first application configuration."""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Runtime configuration. No API keys or network endpoints are required."""

    backend_mode: Literal["mock"] = Field(default="mock")
    kicad_mode: Literal["mock", "local"] = Field(default="local")

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load config from optional environment overrides."""

        backend = os.environ.get("CIRCUIT_AGENT_BACKEND", "mock").strip().lower()
        kicad = os.environ.get("CIRCUIT_AGENT_KICAD", "local").strip().lower()
        if backend != "mock":
            backend = "mock"
        if kicad not in {"mock", "local"}:
            kicad = "local"
        return cls(backend_mode=backend, kicad_mode=kicad)
