"""Export a KiCad spice netlist and run it through ngspice / libngspice."""

from __future__ import annotations

import ctypes
import logging
import re
import subprocess
import tempfile
import threading
from pathlib import Path

from circuit_agent.kicad.client import KiCadError
from circuit_agent.kicad.paths import find_kicad_cli, find_ngspice, find_ngspice_library
from circuit_agent.models.spice import SpiceRequest, SpiceResult

logger = logging.getLogger("circuit_agent.spice")

_ANALYSIS_DEFAULTS = {
    "op": "op",
    "none": "op",
    "tran": "tran 1u 10m",
    "ac": "ac dec 10 1 1Meg",
    "dc": "op",
}

_LIB_LOCK = threading.Lock()
_LIB: ctypes.CDLL | None = None
_LIB_READY = False
_LIB_LOG: list[str] = []


def analysis_command(request: SpiceRequest) -> str:
    """Pick an ngspice analysis card from the server request."""

    for raw in (request.instructions or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("*"):
            continue
        if line.startswith("."):
            line = line[1:].strip()
        lowered = line.lower()
        if lowered == "op" or lowered.startswith(("tran ", "tran\t", "ac ", "dc ")):
            return line
    kind = (request.analysis_type or "op").strip().lower()
    return _ANALYSIS_DEFAULTS.get(kind, "op")


def prepare_spice_deck(netlist: str, request: SpiceRequest) -> str:
    """Normalize a KiCad spice export so ngspice can load it."""

    body: list[str] = []
    for raw in (netlist or "").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered in {".end", ".endc"} or lowered.startswith(".control"):
            continue
        if lowered.startswith((".save", ".probe", ".tran", ".ac", ".dc", ".op")):
            continue
        body.append(line)
    if not body:
        body.append("* empty KiCad spice export")
    if request.netlist_hints:
        body.append("* netlist hints from the agent")
        for raw in request.netlist_hints.splitlines():
            hint = raw.strip()
            if hint and not hint.startswith("*"):
                body.append(hint)
    if _needs_ground_tie(body):
        body.append("* Circuit Agent: alias schematic GND to SPICE node 0")
        body.append("Vgnd GND 0 DC 0")
    if not any(line.strip().lower() == ".end" for line in body):
        body.append(".end")
    return "\n".join(body) + "\n"


def export_spice_netlist(schematic_path: Path, cli_path: Path | None = None) -> str:
    """Run kicad-cli sch export netlist --format spice."""

    if not schematic_path.exists():
        raise KiCadError(f"Schematic not found: {schematic_path}")
    cli = cli_path or find_kicad_cli()
    if cli is None:
        raise KiCadError("kicad-cli was not found. Cannot export a SPICE netlist.")
    with tempfile.TemporaryDirectory(prefix="circuit-agent-spice-") as tmp:
        output = Path(tmp) / "circuit.cir"
        result = subprocess.run(
            [
                str(cli),
                "sch",
                "export",
                "netlist",
                "--format",
                "spice",
                "--output",
                str(output),
                str(schematic_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "kicad-cli spice export failed").strip()
            raise KiCadError(detail)
        if not output.exists():
            raise KiCadError("kicad-cli did not write a SPICE netlist.")
        return output.read_text(encoding="utf-8", errors="replace")


def simulate_schematic(schematic_path: Path, request: SpiceRequest) -> SpiceResult:
    """Export the open schematic and run the requested analysis."""

    netlist = export_spice_netlist(schematic_path)
    deck = prepare_spice_deck(netlist, request)
    command = analysis_command(request)
    return run_ngspice(deck, request, command=command)


def run_ngspice(
    deck: str,
    request: SpiceRequest,
    command: str | None = None,
) -> SpiceResult:
    """Run a prepared deck with the ngspice CLI, else KiCad's libngspice."""

    command = command or analysis_command(request)
    cli = find_ngspice()
    if cli is not None:
        return _run_cli(cli, deck, request, command)
    library = find_ngspice_library()
    if library is not None:
        return _run_library(library, deck, request, command)
    return SpiceResult(
        ok=False,
        analysis_type=request.analysis_type or "op",
        command=command,
        netlist=deck,
        summary="ngspice was not found. Install ngspice or use a KiCad build that bundles libngspice.",
        log="",
        engine="",
    )


def _run_cli(cli: Path, deck: str, request: SpiceRequest, command: str) -> SpiceResult:
    script = (
        _strip_end(deck)
        + "\n.control\nset noaskquit\n"
        + command
        + "\nprint all\nquit\n.endc\n.end\n"
    )
    with tempfile.TemporaryDirectory(prefix="circuit-agent-ngspice-") as tmp:
        cir = Path(tmp) / "circuit.cir"
        log = Path(tmp) / "ngspice.log"
        cir.write_text(script, encoding="utf-8")
        try:
            completed = subprocess.run(
                [str(cli), "-b", "-o", str(log), str(cir)],
                check=False,
                capture_output=True,
                text=True,
                timeout=45,
            )
        except subprocess.TimeoutExpired:
            return SpiceResult(
                ok=False,
                analysis_type=request.analysis_type or "op",
                engine="ngspice",
                command=command,
                netlist=deck,
                summary="ngspice timed out after 45s.",
                log="",
            )
        text = (log.read_text(encoding="utf-8", errors="replace") if log.exists() else "")
        if completed.stdout:
            text = (text + "\n" + completed.stdout).strip()
        if completed.stderr:
            text = (text + "\n" + completed.stderr).strip()
        return _result_from_log(request, command, deck, text, "ngspice", completed.returncode)


def _run_library(library: Path, deck: str, request: SpiceRequest, command: str) -> SpiceResult:
    with _LIB_LOCK:
        lib = _ensure_library(library)
        _LIB_LOG.clear()
        _command(lib, "destroy all")
        lines = [line.encode("utf-8") for line in deck.splitlines() if line.strip()]
        if not any(line.lower().strip() == b".end" for line in lines):
            lines.append(b".end")
        array = (ctypes.c_char_p * (len(lines) + 1))(*lines, None)
        circ_rc = int(lib.ngSpice_Circ(array))
        run_rc = _command(lib, command)
        _command(lib, "print all")
        text = "\n".join(_LIB_LOG)
        return _result_from_log(request, command, deck, text, "libngspice", circ_rc or run_rc)


def _ensure_library(library: Path) -> ctypes.CDLL:
    global _LIB, _LIB_READY
    if _LIB is not None and _LIB_READY:
        return _LIB
    lib = ctypes.CDLL(str(library))
    send_char = ctypes.CFUNCTYPE(
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p
    )(_send_char)
    send_stat = ctypes.CFUNCTYPE(
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p
    )(_send_stat)
    controlled_exit = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_bool,
        ctypes.c_bool,
        ctypes.c_int,
        ctypes.c_void_p,
    )(_controlled_exit)
    rc = int(lib.ngSpice_Init(send_char, send_stat, controlled_exit, None, None, None, None))
    if rc != 0:
        raise KiCadError(f"libngspice init failed ({rc}).")
    _LIB = lib
    _LIB_READY = True
    # Keep callback objects alive for the process lifetime.
    lib._circuit_agent_callbacks = (send_char, send_stat, controlled_exit)  # type: ignore[attr-defined]
    logger.info("Loaded libngspice from %s", library)
    return lib


def _command(lib: ctypes.CDLL, command: str) -> int:
    return int(lib.ngSpice_Command(command.encode("utf-8")))


def _send_char(message: bytes | None, _ident: int, _user: object) -> int:
    if message:
        _LIB_LOG.append(message.decode("utf-8", errors="replace"))
    return 0


def _send_stat(_message: bytes | None, _ident: int, _user: object) -> int:
    return 0


def _controlled_exit(
    _status: int, _immediate: bool, _quit: bool, _ident: int, _user: object
) -> int:
    return 0


def _result_from_log(
    request: SpiceRequest,
    command: str,
    deck: str,
    log: str,
    engine: str,
    returncode: int,
) -> SpiceResult:
    cleaned = _clean_log(log)
    ok = _analysis_ok(cleaned, returncode)
    if ok:
        summary = _summarize_vectors(cleaned) or f"{command} completed."
    else:
        summary = _first_error(cleaned) or f"{engine} did not produce a usable operating point."
    return SpiceResult(
        ok=ok,
        analysis_type=request.analysis_type or "op",
        engine=engine,
        command=command,
        netlist=deck,
        log=cleaned,
        summary=summary,
    )


def _analysis_ok(log: str, returncode: int) -> bool:
    lowered = log.lower()
    if "fatal error" in lowered or "error on line" in lowered:
        return False
    if re.search(r"\bv\([^)]+\)\s*=", lowered):
        return True
    if "no. of data rows" in lowered and returncode == 0:
        return True
    return returncode == 0 and bool(log.strip())


def _summarize_vectors(log: str) -> str:
    values = re.findall(r"^(?:stdout\s+)?([vViI][^ =\n]+)\s*=\s*([^\s]+)", log, flags=re.M)
    if not values:
        return ""
    preview = ", ".join(f"{name}={value}" for name, value in values[:12])
    extra = f" (+{len(values) - 12} more)" if len(values) > 12 else ""
    return f"{len(values)} vector(s): {preview}{extra}"


def _first_error(log: str) -> str:
    for line in log.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if "error" in lowered or "fatal" in lowered or "couldn't" in lowered:
            return re.sub(r"^(stdout|stderr)\s+", "", stripped)
    return ""


def _clean_log(log: str) -> str:
    cleaned: list[str] = []
    for line in (log or "").splitlines():
        text = re.sub(r"^(stdout|stderr)\s+", "", line).rstrip()
        if text:
            cleaned.append(text)
    return "\n".join(cleaned)


def _strip_end(deck: str) -> str:
    lines = [line for line in deck.splitlines() if line.strip().lower() != ".end"]
    return "\n".join(lines)


def _needs_ground_tie(lines: list[str]) -> bool:
    text = "\n".join(lines)
    if not re.search(r"\bGND\b", text):
        return False
    if re.search(r"\bGND\s+0\b|\b0\s+GND\b", text):
        return False
    return True
