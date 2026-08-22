"""HTTP client for the Circuit Agent API at circuit.hiseyong.dev."""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any

import httpx

from circuit_agent.backend.client import BackendClient, BackendError
from circuit_agent.models.agent import AgentReply
from circuit_agent.models.analysis import (
    CircuitAnalysis,
    CircuitRevision,
    CircuitSnapshot,
    RevisionKind,
    RevisionStatus,
    render_project_state,
)
from circuit_agent.models.evidence import Evidence, evidence_from_payload
from circuit_agent.models.issue import (
    CircuitIssue,
    IssueChange,
    IssueRefreshResult,
    IssueSeverity,
)
from circuit_agent.kicad.commands import normalize_commands
from circuit_agent.models.project import Component

DEFAULT_BACKEND_URL = "https://circuit.hiseyong.dev"
REQUEST_TIMEOUT_SECONDS = 300.0
ANALYZE_TIMEOUT_SECONDS = REQUEST_TIMEOUT_SECONDS
ANALYZE_ATTEMPTS = 4
RETRY_WAIT_SECONDS = 2.0
HEALTH_TIMEOUT_SECONDS = 10.0
KEEPALIVE_IDLE_SECONDS = 30


def request_timeout(seconds: float = REQUEST_TIMEOUT_SECONDS) -> httpx.Timeout:
    """Wait as long as nginx proxy_read_timeout (300s). Connect can fail faster."""

    return httpx.Timeout(connect=30.0, read=seconds, write=seconds, pool=seconds)


def keepalive_socket_options() -> list[tuple[int, int, int]]:
    """Probe idle HTTP connections so a silent LLM wait is not dropped at ~60s."""

    options: list[tuple[int, int, int]] = [
        (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
    ]
    idle = getattr(socket, "TCP_KEEPIDLE", None) or getattr(socket, "TCP_KEEPALIVE", None)
    if idle is not None:
        options.append((socket.IPPROTO_TCP, idle, KEEPALIVE_IDLE_SECONDS))
    if hasattr(socket, "TCP_KEEPINTVL"):
        options.append((socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10))
    if hasattr(socket, "TCP_KEEPCNT"):
        options.append((socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3))
    return options


def make_async_client(base_url: str, timeout: httpx.Timeout | float) -> httpx.AsyncClient:
    """HTTP client for long-running analyze/turn calls."""

    return httpx.AsyncClient(
        base_url=base_url,
        timeout=timeout,
        transport=httpx.AsyncHTTPTransport(
            retries=0,
            socket_options=keepalive_socket_options(),
        ),
    )


_RETRYABLE_STATUS = {502, 503, 504, 520, 522, 524}

logger = logging.getLogger("circuit_agent.backend")


def is_retryable_analyze_error(exc: BaseException) -> bool:
    """Proxy drops (Cloudflare/nginx) are worth retrying — the origin may cache."""

    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS
    return isinstance(
        exc,
        (
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
        ),
    )


def _clip(value: str, limit: int) -> str:
    return (value or "")[:limit]


def component_payload(component: Component) -> dict[str, str]:
    return {
        "reference": _clip(component.reference, 100) or "?",
        "value": _clip(component.value, 500),
        "part_number": _clip(component.part_number, 500),
        "manufacturer": _clip(component.manufacturer, 500),
        "footprint": _clip(component.footprint, 1000),
        "datasheet": _clip(component.datasheet, 2000),
        "description": _clip(component.description, 2000),
        "lib_id": _clip(component.lib_id, 1000),
        "nets": _clip(component.nets, 10000),
    }


def analyze_payload(snapshot: CircuitSnapshot) -> dict[str, Any]:
    """Build POST /v1/circuit/analyze JSON from a local project snapshot."""

    body: dict[str, Any] = {
        "project_name": _clip(snapshot.project_name, 500) or "Untitled",
        "project_path": _clip(snapshot.project_path, 2000),
        "components": [component_payload(item) for item in snapshot.components],
        "connections": [
            {"name": _clip(net.name, 500), "pins": list(net.pins)}
            for net in snapshot.connections
        ],
    }
    if snapshot.project_id:
        body["project_id"] = snapshot.project_id
    return body


def issue_payload(issue: CircuitIssue) -> dict[str, Any]:
    """Map a local CircuitIssue to the server Issue schema."""

    evidence: list[dict[str, Any]] = []
    for item in issue.evidence:
        entry: dict[str, Any] = {
            "source": _clip(item.source, 500) or "Datasheet",
            "document": _clip(item.document, 500) or _clip(item.source, 500) or "Unknown",
            "section": _clip(item.section, 500),
            "content": item.content or "",
        }
        if item.page is not None and item.page >= 1:
            entry["page"] = item.page
        if item.url:
            entry["datasheet_url"] = item.url
        if item.confidence is not None:
            entry["confidence"] = item.confidence
        if item.metadata:
            entry["metadata"] = dict(item.metadata)
        evidence.append(entry)
    return {
        "severity": issue.severity.value,
        "title": issue.title or "Issue",
        "description": issue.description or "",
        "source": issue.source or "Schematic review",
        "reference": issue.reference,
        "evidence": evidence,
    }


def issues_from_response(raw_issues: Any) -> list[CircuitIssue]:
    """Map Issue JSON objects to CircuitIssue models."""

    issues: list[CircuitIssue] = []
    for raw in raw_issues or []:
        if not isinstance(raw, dict):
            continue
        evidence = [
            evidence_from_payload(item)
            for item in raw.get("evidence") or []
            if isinstance(item, dict)
        ]
        severity_raw = str(raw.get("severity") or "info")
        try:
            severity = IssueSeverity(severity_raw)
        except ValueError:
            severity = IssueSeverity.INFO
        issues.append(
            CircuitIssue(
                severity=severity,
                title=str(raw.get("title") or "Issue"),
                description=str(raw.get("description") or ""),
                reference=str(raw.get("reference") or ""),
                source=str(raw.get("source") or ""),
                evidence=evidence,
            )
        )
    return issues


def analysis_from_response(data: dict[str, Any]) -> CircuitAnalysis:
    """Map AnalyzeResponse JSON to the desktop CircuitAnalysis model."""

    purpose = str(data.get("purpose") or "")
    summary = str(data.get("summary") or "")
    return CircuitAnalysis(
        purpose=purpose,
        summary=summary,
        project_id=str(data.get("project_id") or ""),
        issues=issues_from_response(data.get("issues")),
        revisions=[
            CircuitRevision(
                kind=RevisionKind.ANALYSIS,
                title="Circuit analysis",
                summary=purpose or "Server analysis received",
                status=RevisionStatus.INFO,
            )
        ],
    )


def refresh_payload(
    snapshot: CircuitSnapshot,
    previous_issues: list[CircuitIssue],
) -> dict[str, Any]:
    """Build POST /v1/circuit/issues/refresh JSON."""

    body: dict[str, Any] = {
        "project_name": _clip(snapshot.project_name, 500),
        "components": [component_payload(item) for item in snapshot.components[:500]],
        "connections": [
            {"name": _clip(net.name, 500), "pins": list(net.pins)}
            for net in snapshot.connections[:5000]
        ],
        "previous_issues": [issue_payload(item) for item in previous_issues[:200]],
    }
    if snapshot.project_id:
        body["project_id"] = snapshot.project_id
    return body


def refresh_from_response(data: dict[str, Any]) -> IssueRefreshResult:
    """Map IssueRefreshResponse JSON to IssueRefreshResult."""

    changes: list[IssueChange] = []
    for raw in data.get("changes") or []:
        if not isinstance(raw, dict):
            continue
        action = str(raw.get("action") or "kept")
        if action not in {"kept", "removed", "added"}:
            action = "kept"
        parsed = issues_from_response([raw.get("issue") or {}])
        if not parsed:
            continue
        previous_index = raw.get("previous_index")
        if previous_index is not None:
            try:
                previous_index = int(previous_index)
            except (TypeError, ValueError):
                previous_index = None
        changes.append(
            IssueChange(
                action=action,
                issue=parsed[0],
                reason=str(raw.get("reason") or ""),
                previous_index=previous_index,
            )
        )
    return IssueRefreshResult(
        project_id=str(data.get("project_id") or ""),
        summary=str(data.get("summary") or ""),
        issues=issues_from_response(data.get("issues")),
        changes=changes,
    )


def turn_payload(
    project_id: str,
    prompt: str,
    snapshot: CircuitSnapshot,
    simulation_results_text: str | None = None,
) -> dict[str, Any]:
    """Build POST /v1/agent/turns JSON."""

    components_text, connections_text = render_project_state(snapshot)
    state: dict[str, Any] = {
        "components_text": components_text[:500000],
        "connections_text": connections_text[:500000],
        "components": [component_payload(item) for item in snapshot.components],
        "connections": [
            {"name": _clip(net.name, 500), "pins": list(net.pins)}
            for net in snapshot.connections
        ],
    }
    if simulation_results_text:
        state["simulation_results_text"] = simulation_results_text[:500000]
    return {
        "project_id": project_id,
        "prompt": prompt[:50000],
        "project_state": state,
    }


def reply_from_turn(data: dict[str, Any]) -> AgentReply:
    """Map TurnResponse JSON to AgentReply."""

    commands = data.get("kicad_commands") or []
    spice = data.get("spice_request") or {}
    if not isinstance(spice, dict):
        spice = {}
    return AgentReply(
        content=str(data.get("plain_text") or data.get("error") or ""),
        turn_id=str(data.get("turn_id") or ""),
        status=str(data.get("status") or "completed"),
        output_kind=str(data.get("output_kind") or "text"),
        kicad_commands=normalize_commands(commands),
        spice_reason=str(spice.get("reason") or ""),
        spice_analysis_type=str(spice.get("analysis_type") or ""),
        spice_instructions=str(spice.get("instructions") or ""),
        spice_netlist_hints=str(spice.get("netlist_hints") or ""),
        error=data.get("error"),
    )


def format_kicad_commands(commands: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for command in commands:
        parts = [str(command.get("op") or "?")]
        if command.get("reference"):
            parts.append(str(command["reference"]))
        if command.get("value"):
            parts.append(str(command["value"]))
        if command.get("lib_id"):
            parts.append(str(command["lib_id"]))
        if command.get("from_pin") or command.get("to_pin"):
            parts.append(f"{command.get('from_pin', '')}->{command.get('to_pin', '')}")
        if command.get("property_name"):
            parts.append(f"{command['property_name']}={command.get('property_value', '')}")
        lines.append(" ".join(parts).strip())
    return "\n".join(lines)


class RemoteBackendClient(BackendClient):
    """Talk to the deployed Circuit Agent API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BACKEND_URL,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = request_timeout(timeout)
        logger.info(
            "Remote backend %s (read timeout %ss, no turn retries)",
            self.base_url,
            self.timeout.read,
        )

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=HEALTH_TIMEOUT_SECONDS
            ) as client:
                response = await client.get("/health")
                response.raise_for_status()
        except httpx.HTTPError:
            return False
        payload = response.json()
        return bool(payload.get("ok"))

    async def send_message(self, message: str) -> AgentReply:
        raise BackendError("Chat requires a project id. Open a project and wait for analysis.")

    async def send_turn(
        self,
        project_id: str,
        prompt: str,
        snapshot: CircuitSnapshot,
        simulation_results_text: str | None = None,
    ) -> AgentReply:
        if not project_id:
            raise BackendError("Analyze the project before chatting.")
        if not prompt or not prompt.strip():
            raise BackendError("Message must not be empty.")
        payload = turn_payload(project_id, prompt.strip(), snapshot, simulation_results_text)
        return await self._request_turn("POST", "/v1/agent/turns", payload)

    async def submit_simulation(self, turn_id: str, simulation_results_text: str) -> AgentReply:
        if not turn_id:
            raise BackendError("Missing turn id for simulation feedback.")
        payload = {"simulation_results_text": simulation_results_text[:500000]}
        return await self._request_turn(
            "POST", f"/v1/agent/turns/{turn_id}/simulation", payload
        )

    async def _request_turn(self, method: str, path: str, payload: dict[str, Any]) -> AgentReply:
        # Never retry turns. A retry closes the first POST (nginx 499) while the
        # origin is still generating a reply, then starts a second LLM job.
        try:
            async with make_async_client(self.base_url, self.timeout) as client:
                response = await client.request(method, path, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise self._map_http_error(exc, "Agent turn") from exc
        data = response.json()
        if not isinstance(data, dict):
            raise BackendError("Turn response was not a JSON object.")
        return reply_from_turn(data)

    async def analyze_circuit(self, snapshot: CircuitSnapshot) -> CircuitAnalysis:
        payload = analyze_payload(snapshot)
        last_error: BaseException | None = None
        for attempt in range(1, ANALYZE_ATTEMPTS + 1):
            try:
                return await self._post_analyze(payload)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= ANALYZE_ATTEMPTS or not is_retryable_analyze_error(exc):
                    break
                logger.warning(
                    "Analyze dropped on attempt %s/%s (%s). Retrying so cached datasheets can finish.",
                    attempt,
                    ANALYZE_ATTEMPTS,
                    exc,
                )
                await asyncio.sleep(RETRY_WAIT_SECONDS)
        assert last_error is not None
        raise self._map_http_error(last_error) from last_error

    async def refresh_issues(
        self,
        snapshot: CircuitSnapshot,
        previous_issues: list[CircuitIssue],
    ) -> IssueRefreshResult:
        payload = refresh_payload(snapshot, previous_issues)
        last_error: BaseException | None = None
        for attempt in range(1, ANALYZE_ATTEMPTS + 1):
            try:
                return await self._post_refresh(payload)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= ANALYZE_ATTEMPTS or not is_retryable_analyze_error(exc):
                    break
                logger.warning(
                    "Issue refresh dropped on attempt %s/%s (%s). Retrying.",
                    attempt,
                    ANALYZE_ATTEMPTS,
                    exc,
                )
                await asyncio.sleep(RETRY_WAIT_SECONDS)
        assert last_error is not None
        raise self._map_http_error(last_error, "Issue refresh") from last_error

    async def _post_analyze(self, payload: dict[str, Any]) -> CircuitAnalysis:
        data = await self._post_json("/v1/circuit/analyze", payload, "Analyze")
        return analysis_from_response(data)

    async def _post_refresh(self, payload: dict[str, Any]) -> IssueRefreshResult:
        data = await self._post_json("/v1/circuit/issues/refresh", payload, "Issue refresh")
        return refresh_from_response(data)

    async def _post_json(self, path: str, payload: dict[str, Any], action: str) -> dict[str, Any]:
        async with make_async_client(self.base_url, self.timeout) as client:
            response = await client.post(path, json=payload)
            response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise BackendError(f"{action} response was not a JSON object.")
        return data

    @staticmethod
    def _map_http_error(exc: httpx.HTTPError, action: str = "Analyze") -> BackendError:
        if isinstance(exc, httpx.HTTPStatusError):
            detail = (exc.response.text or str(exc))[:400]
            return BackendError(f"{action} failed ({exc.response.status_code}): {detail}")
        return BackendError(
            f"{action} request failed before a response arrived ({exc}). "
            "The server may still be working; wait and retry once instead of spamming chat."
        )
