from pathlib import Path

from circuit_agent.kicad.symbol_library import (
    SymbolLibraryIndex,
    load_symbol,
    split_lib_id,
)


def test_split_lib_id() -> None:
    assert split_lib_id("device:battery") == ("device", "battery")
    assert split_lib_id("Device:C_Polarized_US") == ("Device", "C_Polarized_US")
    assert split_lib_id("Battery") == ("", "Battery")
    assert split_lib_id("  ") == ("", "")


def test_index_lookup_is_case_insensitive(tmp_path: Path) -> None:
    lib = tmp_path / "Device.kicad_sym"
    lib.write_text(
        """(kicad_symbol_lib
	(symbol "Battery"
		(symbol "Battery_1_1"
			(pin passive line (at 0 5.08 270) (length 2.54) (name "+") (number "1"))
		)
	)
	(symbol "Battery_Cell"
		(pin passive line (at 0 0 0) (length 1.27) (name "~") (number "1"))
	)
)
""",
        encoding="utf-8",
    )
    index = SymbolLibraryIndex()
    index.add_file("Device", lib)
    resolved = index.lookup("device:battery")
    assert resolved is not None
    assert resolved.lib_id == "Device:Battery"
    assert resolved.body.startswith('(symbol "Device:Battery"')
    assert "Battery_Cell" not in resolved.body
    assert index.lookup("Device:Battery_Cell") is not None
    assert index.lookup("Device:Missing") is None


def test_load_symbol_reads_project_table(tmp_path: Path) -> None:
    lib = tmp_path / "Power.kicad_sym"
    lib.write_text(
        '(kicad_symbol_lib\n\t(symbol "GND"\n\t\t(property "Reference" "#PWR")\n\t)\n)\n',
        encoding="utf-8",
    )
    (tmp_path / "sym-lib-table").write_text(
        f'(sym_lib_table\n\t(lib (name "power") (type "KiCad") (uri "{lib}") (options "") (descr ""))\n)\n',
        encoding="utf-8",
    )
    schematic = tmp_path / "board.kicad_sch"
    schematic.write_text("(kicad_sch)\n", encoding="utf-8")
    resolved = load_symbol("POWER:gnd", schematic)
    assert resolved is not None
    assert resolved.lib_id == "power:GND"
    assert '(symbol "power:GND"' in resolved.body
