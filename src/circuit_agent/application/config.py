"""Minimal application configuration."""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field

from circuit_agent.backend.remote_client import DEFAULT_BACKEND_URL


class AppConfig(BaseModel):
    """Runtime configuration from environment overrides."""

    backend_mode: Literal["mock", "remote"] = Field(default="mock")
    kicad_mode: Literal["mock", "local"] = Field(default="local")
    backend_url: str = Field(default=DEFAULT_BACKEND_URL)

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load config. The desktop app defaults to the deployed remote API."""

        backend = os.environ.get("CIRCUIT_AGENT_BACKEND", "remote").strip().lower()
        kicad = os.environ.get("CIRCUIT_AGENT_KICAD", "local").strip().lower()
        url = os.environ.get("CIRCUIT_AGENT_BACKEND_URL", DEFAULT_BACKEND_URL).strip()
        if backend not in {"mock", "remote"}:
            backend = "remote"
        if kicad not in {"mock", "local"}:
            kicad = "local"
        return cls(backend_mode=backend, kicad_mode=kicad, backend_url=url or DEFAULT_BACKEND_URL)
