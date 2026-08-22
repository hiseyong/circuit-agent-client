"""Load KiCad library symbols so schematic edits can embed real graphics."""

from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from circuit_agent.kicad.paths import find_global_sym_lib_table, find_symbol_dir

_LIB_ENTRY_RE = re.compile(
    r'\(lib\s+\(name\s+"([^"]+)"\)\s+\(type\s+"[^"]*"\)\s+\(uri\s+"([^"]+)"\)',
    re.DOTALL,
)
_ENV_RE = re.compile(r"\$\{([^}]+)\}")
_SYMBOL_HEAD_RE = re.compile(r'\(symbol\s+"([^"]+)"')

_LOCK = threading.Lock()
_GLOBAL_INDEX: SymbolLibraryIndex | None = None


@dataclass(frozen=True)
class ResolvedSymbol:
    """A library symbol rewritten for a schematic ``lib_symbols`` cache."""

    lib_id: str
    body: str


class SymbolLibraryIndex:
    """Map ``Library:Symbol`` ids onto ``.kicad_sym`` files."""

    def __init__(self) -> None:
        self._files: dict[str, Path] = {}
        self._nick_by_lower: dict[str, str] = {}
        self._cache: dict[Path, tuple[str, str]] = {}

    def add_table(self, table_path: Path, symbol_dir: Path | None = None) -> None:
        if not table_path.is_file():
            return
        text = table_path.read_text(encoding="utf-8", errors="replace")
        for nickname, uri in _LIB_ENTRY_RE.findall(text):
            resolved = _expand_uri(uri, symbol_dir)
            if resolved.is_file():
                self.add_file(nickname, resolved)

    def add_file(self, nickname: str, path: Path) -> None:
        if not nickname or not path.is_file():
            return
        self._files[nickname] = path
        self._nick_by_lower[nickname.lower()] = nickname

    def add_directory(self, symbol_dir: Path) -> None:
        if not symbol_dir.is_dir():
            return
        for path in sorted(symbol_dir.glob("*.kicad_sym")):
            if path.stem.lower() not in self._nick_by_lower:
                self.add_file(path.stem, path)

    def lookup(self, lib_id: str) -> ResolvedSymbol | None:
        nickname, symbol_name = split_lib_id(lib_id)
        if not symbol_name:
            return None
        if not nickname:
            nickname = "Device"
        canonical_nick = self._nick_by_lower.get(nickname.lower())
        if canonical_nick is None:
            return None
        path = self._files.get(canonical_nick)
        if path is None:
            return None
        extracted = self._extract(path, symbol_name)
        if extracted is None:
            return None
        actual_name, block = extracted
        lib_id_canonical = f"{canonical_nick}:{actual_name}"
        return ResolvedSymbol(lib_id=lib_id_canonical, body=_rewrite_symbol_name(block, lib_id_canonical))

    def _extract(self, path: Path, symbol_name: str) -> tuple[str, str] | None:
        text, lowered = self._file(path)
        needle = f'(symbol "{symbol_name.lower()}"'
        start = 0
        while True:
            idx = lowered.find(needle, start)
            if idx < 0:
                return None
            match = _SYMBOL_HEAD_RE.match(text, idx)
            if match is None:
                start = idx + 1
                continue
            actual = match.group(1)
            if actual.lower() != symbol_name.lower():
                start = idx + 1
                continue
            close = _matching_paren(text, idx)
            return actual, text[idx : close + 1]

    def _file(self, path: Path) -> tuple[str, str]:
        cached = self._cache.get(path)
        if cached is not None:
            return cached
        text = path.read_text(encoding="utf-8", errors="replace")
        pair = (text, text.lower())
        self._cache[path] = pair
        return pair


def split_lib_id(lib_id: str) -> tuple[str, str]:
    text = (lib_id or "").strip()
    if not text:
        return "", ""
    if ":" not in text:
        return "", text
    nickname, name = text.split(":", 1)
    return nickname.strip(), name.strip()


def load_symbol(lib_id: str, schematic_path: Path | None = None) -> ResolvedSymbol | None:
    """Resolve ``lib_id`` from the project table, then the global KiCad libraries."""

    wanted = (lib_id or "").strip()
    if not wanted:
        return None
    if schematic_path is not None:
        local = index_for_schematic(schematic_path)
        found = local.lookup(wanted)
        if found is not None:
            return found
    return global_index().lookup(wanted)


def global_index() -> SymbolLibraryIndex:
    global _GLOBAL_INDEX
    with _LOCK:
        if _GLOBAL_INDEX is None:
            _GLOBAL_INDEX = _build_global_index()
        return _GLOBAL_INDEX


def index_for_schematic(schematic_path: Path) -> SymbolLibraryIndex:
    index = SymbolLibraryIndex()
    table = schematic_path.parent / "sym-lib-table"
    if table.is_file():
        index.add_table(table, schematic_path.parent)
    return index


def _build_global_index() -> SymbolLibraryIndex:
    index = SymbolLibraryIndex()
    symbol_dir = find_symbol_dir()
    table = find_global_sym_lib_table()
    if table is not None:
        index.add_table(table, symbol_dir)
    if symbol_dir is not None:
        index.add_directory(symbol_dir)
    return index


def _expand_uri(uri: str, symbol_dir: Path | None) -> Path:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        env = os.environ.get(name, "").strip()
        if env:
            return env
        if symbol_dir is not None and (name.endswith("_SYMBOL_DIR") or name == "KICAD_SYMBOL_DIR"):
            return str(symbol_dir)
        return match.group(0)

    expanded = os.path.expanduser(_ENV_RE.sub(replace, uri.strip()))
    return Path(expanded)


def _rewrite_symbol_name(block: str, lib_id: str) -> str:
    return _SYMBOL_HEAD_RE.sub(f'(symbol "{lib_id}"', block, count=1)


def _matching_paren(text: str, open_index: int) -> int:
    depth = 0
    in_string = False
    i = open_index
    length = len(text)
    while i < length:
        char = text[i]
        if in_string:
            if char == "\\":
                i += 2
                continue
            if char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced parentheses in symbol library")
