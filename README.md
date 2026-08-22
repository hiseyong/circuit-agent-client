# Circuit Agent

Local desktop application for **Circuit Agent** — an agent for creating and modifying augmented circuit diagrams based on datasheets.

**From Datasheets to Working Circuits.**

This repository is only the native desktop client. LLM inference, Upstage document processing, DigiKey, RAG, datasheet retrieval, and circuit analysis will live on a remote server later. The GUI talks to those systems through replaceable client interfaces.

## Architecture

```
┌──────────────────────────────────────────────────┐
│                  QML UI                          │
│  Project │ Schematic / Issues(+evidence) / Chat │ Status │ Logs │
└──────────────────────┬───────────────────────────┘
                       │
                  PySide6 Bridge
                       │
┌──────────────────────▼───────────────────────────┐
│              Application Layer                   │
│  App / Project / Agent / KiCad controllers       │
└───────────────┬──────────────────────┬───────────┘
                │                      │
                ▼                      ▼
       BackendClient            KiCadClient
       (Mock today)             Local launch +
                                project open
```

QML is presentation only. Business logic stays in Python. The GUI never calls a remote API or KiCad directly.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- macOS (primary target; Windows/Linux should remain possible)
- KiCad (default mode launches the installed app; typically `/Applications/KiCad/KiCad.app`)

## Installation

```bash
uv sync
```

## Run

```bash
uv run circuit-agent
```

On launch the app starts KiCad and asks you to select a `.kicad_pro` file. That project is then opened in KiCad.

To skip launching KiCad:

```bash
CIRCUIT_AGENT_KICAD=mock uv run circuit-agent
```

A custom KiCad location can be set with `CIRCUIT_AGENT_KICAD_PATH`.

## Test

```bash
uv run pytest
```

## Current limitations

The following are **not implemented**. External functionality is mocked:

- LLM inference
- Remote backend
- DigiKey API / MCP
- Upstage document processing
- RAG / datasheet retrieval and parsing
- SPICE / circuit simulation
- FMEA and automatic circuit design or modification
- Real KiCad IPC (the app launches KiCad and opens a project file; it does not talk to KiCad over IPC yet)
- Authentication and user accounts
