"""KiCad client interface.

QML never imports this module. Controllers talk to ``KiCadClient`` so a future
IPC implementation can replace the mock without changing the UI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from circuit_agent.models.project import Component, Project
from circuit_agent.models.spice import SpiceRequest, SpiceResult


class KiCadError(Exception):
    """Raised when KiCad is unavailable or a request fails."""


@dataclass
class CommandApplyResult:
    """Project snapshot after applying one or more KiCad commands."""

    project: Project
    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


class KiCadClient(ABC):
    """Application-facing KiCad API."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish a session with KiCad (or a mock)."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the session."""

    @abstractmethod
    async def open_project(self, path: str) -> Project:
        """Open an existing KiCad project and return a snapshot."""

    @abstractmethod
    async def create_project(self, path: str) -> Project:
        """Create a new KiCad project file and open it."""

    @abstractmethod
    async def get_project(self) -> Project:
        """Return the current project snapshot."""

    @abstractmethod
    async def get_components(self) -> list[Component]:
        """Return schematic components in the current project."""

    @abstractmethod
    async def get_connections(self) -> list[dict[str, Any]]:
        """Return a simplified netlist-style connection list."""

    @abstractmethod
    async def export_preview(self, project_path: str) -> str:
        """Return a local filesystem path to a schematic preview, or empty."""

    async def export_pcb_preview(self, project_path: str, view: str = "iso") -> str:
        """Return a local filesystem path to a PCB 3D render, or empty."""

        return ""

    @abstractmethod
    async def apply_commands(self, commands: list[dict[str, Any]]) -> CommandApplyResult:
        """Apply committed KiCad commands to the open schematic."""

    @abstractmethod
    async def restore_previous(self) -> CommandApplyResult:
        """Undo the last committed schematic edit."""

    async def run_spice(self, request: SpiceRequest) -> SpiceResult:
        """Export the open schematic and run a local SPICE analysis."""

        return SpiceResult(
            ok=False,
            analysis_type=request.analysis_type or "op",
            summary="SPICE is not available on this KiCad client.",
        )
