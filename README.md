# Circuit Agent

Local desktop application for **Circuit Agent** — an agent for analyzing and modifying KiCad circuits from datasheets.

**From Datasheets to Working Circuits.**

This repository is the native desktop client. LLM inference, Upstage document processing, DigiKey, RAG, and datasheet retrieval run on the remote API at [circuit.hiseyong.dev](https://circuit.hiseyong.dev). The GUI talks to that API and to local KiCad through replaceable client interfaces.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         QML UI                              │
│  Project │ Schematic / Analysis / Issues / Chat / PCB 3D /  │
│          │ SPICE │ Logs │ Status                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                      PySide6 Bridge
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Application Layer                        │
│  App / Project / Agent / Analysis / KiCad / Spice           │
└───────────────┬──────────────────────────────┬──────────────┘
                │                              │
                ▼                              ▼
       BackendClient                    KiCadClient
       Remote (default)                 Local (default):
       Mock available                   launch KiCad, edit
                                        .kicad_sch, preview,
                                        SPICE via kicad-cli
```

QML is presentation only. Business logic stays in Python. The GUI never calls a remote API or KiCad directly.

On project open the client sends a circuit snapshot to `POST /v1/circuit/analyze`. Chat uses `POST /v1/agent/turns`. Agent replies can include KiCad commands (applied to the schematic file) or a SPICE request (run locally, then sent back with `POST /v1/agent/turns/{id}/simulation`). After a committed edit, issues are refreshed with `POST /v1/circuit/issues/refresh`. Analysis, issues, and chat are saved next to the project as `*.circuit-agent.json`.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- macOS (primary target; Windows/Linux should remain possible)
- KiCad, including `kicad-cli` (schematic/PCB preview, netlist, and SPICE export)
- ngspice, or KiCad's bundled libngspice (for local simulation)

## Installation

```bash
uv sync
```

## Run

By default the app talks to the deployed API and launches the installed KiCad:

```bash
uv run circuit-agent
```

On launch the app starts KiCad and asks you to select or create a `.kicad_pro` file. Opening a project triggers circuit analysis.

### Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `CIRCUIT_AGENT_BACKEND` | `remote` | `remote` or `mock` |
| `CIRCUIT_AGENT_BACKEND_URL` | `https://circuit.hiseyong.dev` | API base URL |
| `CIRCUIT_AGENT_KICAD` | `local` | `local` or `mock` |
| `CIRCUIT_AGENT_KICAD_PATH` | auto-detect | KiCad app or executable |
| `CIRCUIT_AGENT_NGSPICE` | auto-detect | ngspice executable |
| `CIRCUIT_AGENT_NGSPICE_LIB` | auto-detect | libngspice shared library |

Offline / no-KiCad:

```bash
CIRCUIT_AGENT_BACKEND=mock CIRCUIT_AGENT_KICAD=mock uv run circuit-agent
```

Local API instead of the deployed server:

```bash
CIRCUIT_AGENT_BACKEND_URL=http://127.0.0.1:8000 uv run circuit-agent
```

## Test

```bash
uv run pytest
```

## Current limitations

- No KiCad IPC — the app launches KiCad and edits `.kicad_sch` on disk; it does not control the KiCad GUI over IPC
- Schematic edits are a closed opcode set: `set_value`, `set_property`, `add_component`, `remove_component`, `add_wire`, `remove_wire`, `set_net_name`, `annotate`
- PCB 3D is a still image from `kicad-cli`, not an interactive mesh viewer
- Authentication and user accounts are not implemented
- LLM, DigiKey, Upstage, and RAG live on the remote server, not in this client
