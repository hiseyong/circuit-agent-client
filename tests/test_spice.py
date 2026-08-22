from circuit_agent.kicad.mock_client import MockKiCadClient
from circuit_agent.kicad.paths import find_ngspice_library
from circuit_agent.kicad.spice import analysis_command, prepare_spice_deck, run_ngspice
from circuit_agent.models.spice import SpiceRequest, SpiceResult
import pytest


KICAD_EXPORT = """
.title KiCad schematic
R1 VCC Net-_D1-A_ 560
Q1 GND Net-_Q1-B_ Net-_D1-K_ PN2222A
.save all
.probe alli
.end
"""


def test_prepare_spice_deck_aliases_gnd_and_drops_probes() -> None:
    deck = prepare_spice_deck(
        KICAD_EXPORT,
        SpiceRequest(netlist_hints="Vcc VCC 0 DC 5"),
    )
    assert ".save" not in deck
    assert "Vgnd GND 0 DC 0" in deck
    assert "Vcc VCC 0 DC 5" in deck
    assert deck.strip().endswith(".end")


def test_analysis_command_reads_instructions() -> None:
    assert analysis_command(SpiceRequest(analysis_type="tran")) == "tran 1u 10m"
    assert (
        analysis_command(SpiceRequest(analysis_type="op", instructions=".tran 10u 2m"))
        == "tran 10u 2m"
    )


def test_spice_result_as_text_is_bounded() -> None:
    result = SpiceResult(
        ok=True,
        analysis_type="op",
        engine="libngspice",
        command="op",
        summary="1 vector(s): v(1)=5",
        netlist="V1 1 0 5\n.end\n",
        log="v(1) = 5.000000e+00",
    )
    text = result.as_text()
    assert text.startswith("[spice] analysis=op")
    assert "v(1) = 5.000000e+00" in text


@pytest.mark.asyncio
async def test_mock_kicad_run_spice() -> None:
    client = MockKiCadClient(delay_seconds=0.0)
    await client.connect()
    result = await client.run_spice(SpiceRequest(analysis_type="op"))
    assert result.ok is True
    assert result.engine == "mock"
    assert "U1" in result.log


@pytest.mark.skipif(find_ngspice_library() is None, reason="libngspice is not installed")
def test_libngspice_operating_point_on_divider() -> None:
    deck = prepare_spice_deck(
        """
        * divider
        V1 in 0 DC 5
        R1 in out 1k
        R2 out 0 1k
        .end
        """,
        SpiceRequest(analysis_type="op"),
    )
    result = run_ngspice(deck, SpiceRequest(analysis_type="op"))
    assert result.ok is True
    assert result.engine == "libngspice"
    assert "2.5" in result.log or "2.500" in result.log
