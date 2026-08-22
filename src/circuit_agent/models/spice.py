"""Local SPICE request/result models for the KiCad + ngspice loop."""

from __future__ import annotations

from pydantic import BaseModel

MAX_SPICE_TEXT = 80000


class SpiceRequest(BaseModel):
    """What the server asked the desktop client to simulate."""

    reason: str = ""
    analysis_type: str = "op"
    instructions: str = ""
    netlist_hints: str = ""


class SpiceResult(BaseModel):
    """Text the desktop sends back to POST /v1/agent/turns/{id}/simulation."""

    ok: bool
    analysis_type: str = "op"
    engine: str = ""
    summary: str = ""
    netlist: str = ""
    log: str = ""
    command: str = ""

    def as_text(self) -> str:
        """Format a bounded report for the remote agent."""

        lines = [
            f"[spice] analysis={self.analysis_type} engine={self.engine or '-'} ok={str(self.ok).lower()}",
        ]
        if self.command:
            lines.append(f"[command] {self.command}")
        if self.summary:
            lines.append(f"[summary] {self.summary}")
        if self.netlist:
            lines.append("[netlist]")
            lines.append(_clip(self.netlist, 12000))
        if self.log:
            lines.append("[log]")
            lines.append(_clip(self.log, MAX_SPICE_TEXT - 16000))
        return _clip("\n".join(lines), MAX_SPICE_TEXT)


def _clip(value: str, limit: int) -> str:
    text = value or ""
    if len(text) <= limit:
        return text
    hidden = len(text) - limit
    return text[:limit] + f"\n… truncated {hidden} more character(s)"
