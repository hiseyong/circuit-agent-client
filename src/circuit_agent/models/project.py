"""Minimal project and component representation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Component(BaseModel):
    """A schematic symbol instance (not a full KiCad footprint)."""

    reference: str
    value: str = ""
    part_number: str = ""
    manufacturer: str = ""
    footprint: str = ""
    datasheet: str = ""
    description: str = ""
    lib_id: str = ""
    nets: str = ""


class Project(BaseModel):
    """Stable internal project snapshot used by the desktop application."""

    name: str
    path: str = ""
    components: list[Component] = Field(default_factory=list)
    status: str = "unloaded"


def demo_project() -> Project:
    """Return the built-in demo project shown in the initial UI."""

    return Project(
        name="circuit",
        path="circuit.kicad_pro",
        status="mock",
        components=[
            Component(
                reference="U1",
                value="TPS62160",
                part_number="TPS62160",
                manufacturer="Texas Instruments",
                footprint="Package_TO_SOT_SMD:SOT-23-6",
                datasheet="https://www.ti.com/lit/ds/symlink/tps62160.pdf",
                description="3–17 V 1 A step-down converter",
                lib_id="Regulator_Switching:TPS62160",
                nets="VIN: VIN; EN: EN; GND: GND",
            ),
            Component(
                reference="R1",
                value="10k",
                footprint="Resistor_SMD:R_0603_1608Metric",
                description="Enable pull-up",
                lib_id="Device:R",
                nets="1: EN; 2: VIN",
            ),
            Component(
                reference="C1",
                value="10uF",
                footprint="Capacitor_SMD:C_0805_2012Metric",
                description="Input capacitor",
                lib_id="Device:C",
                nets="1: VIN; 2: GND",
            ),
        ],
    )
