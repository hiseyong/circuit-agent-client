"""QAbstractListModel adapters that expose domain objects to QML."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from circuit_agent.models.agent import ChatMessage
from circuit_agent.models.analysis import CircuitRevision
from circuit_agent.models.evidence import Evidence, evidence_card
from circuit_agent.models.issue import CircuitIssue
from circuit_agent.models.project import Component


class ChatListModel(QAbstractListModel):
    RoleRole = Qt.ItemDataRole.UserRole + 1
    ContentRole = Qt.ItemDataRole.UserRole + 2
    TimestampRole = Qt.ItemDataRole.UserRole + 3
    LevelRole = Qt.ItemDataRole.UserRole + 4

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[ChatMessage] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == self.RoleRole:
            return item.role.value
        if role == self.ContentRole:
            return item.content
        if role == self.TimestampRole:
            return item.timestamp.strftime("%H:%M:%S")
        if role == self.LevelRole:
            return item.level
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.RoleRole: b"role",
            self.ContentRole: b"content",
            self.TimestampRole: b"timestamp",
            self.LevelRole: b"level",
        }

    def append(self, message: ChatMessage) -> None:
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(message)
        self.endInsertRows()

    def reset_from(self, messages: list[ChatMessage]) -> None:
        self.beginResetModel()
        self._items = list(messages)
        self.endResetModel()

    def snapshot(self) -> list[ChatMessage]:
        return list(self._items)


class ComponentListModel(QAbstractListModel):
    ReferenceRole = Qt.ItemDataRole.UserRole + 1
    ValueRole = Qt.ItemDataRole.UserRole + 2
    PartNumberRole = Qt.ItemDataRole.UserRole + 3
    ManufacturerRole = Qt.ItemDataRole.UserRole + 4
    FootprintRole = Qt.ItemDataRole.UserRole + 5
    DatasheetRole = Qt.ItemDataRole.UserRole + 6
    DescriptionRole = Qt.ItemDataRole.UserRole + 7
    LibIdRole = Qt.ItemDataRole.UserRole + 8
    NetsRole = Qt.ItemDataRole.UserRole + 9

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[Component] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == self.ReferenceRole:
            return item.reference
        if role == self.ValueRole:
            return item.value
        if role == self.PartNumberRole:
            return item.part_number
        if role == self.ManufacturerRole:
            return item.manufacturer
        if role == self.FootprintRole:
            return item.footprint
        if role == self.DatasheetRole:
            return item.datasheet
        if role == self.DescriptionRole:
            return item.description
        if role == self.LibIdRole:
            return item.lib_id
        if role == self.NetsRole:
            return item.nets
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.ReferenceRole: b"reference",
            self.ValueRole: b"value",
            self.PartNumberRole: b"partNumber",
            self.ManufacturerRole: b"manufacturer",
            self.FootprintRole: b"footprint",
            self.DatasheetRole: b"datasheet",
            self.DescriptionRole: b"description",
            self.LibIdRole: b"libId",
            self.NetsRole: b"nets",
        }

    def reset_from(self, components: list[Component]) -> None:
        self.beginResetModel()
        self._items = list(components)
        self.endResetModel()

    def find(self, reference: str) -> Component | None:
        for item in self._items:
            if item.reference == reference:
                return item
        return None


class EvidenceListModel(QAbstractListModel):
    SourceRole = Qt.ItemDataRole.UserRole + 1
    DocumentRole = Qt.ItemDataRole.UserRole + 2
    PageRole = Qt.ItemDataRole.UserRole + 3
    SectionRole = Qt.ItemDataRole.UserRole + 4
    ContentRole = Qt.ItemDataRole.UserRole + 5
    ConfidenceRole = Qt.ItemDataRole.UserRole + 6

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[Evidence] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == self.SourceRole:
            return item.source
        if role == self.DocumentRole:
            return item.document
        if role == self.PageRole:
            return item.page if item.page is not None else ""
        if role == self.SectionRole:
            return item.section
        if role == self.ContentRole:
            return item.content
        if role == self.ConfidenceRole:
            return "" if item.confidence is None else f"{item.confidence:.0%}"
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.SourceRole: b"source",
            self.DocumentRole: b"document",
            self.PageRole: b"page",
            self.SectionRole: b"section",
            self.ContentRole: b"content",
            self.ConfidenceRole: b"confidence",
        }

    def reset_from(self, evidence: list[Evidence]) -> None:
        self.beginResetModel()
        self._items = list(evidence)
        self.endResetModel()


class IssueListModel(QAbstractListModel):
    SeverityRole = Qt.ItemDataRole.UserRole + 1
    TitleRole = Qt.ItemDataRole.UserRole + 2
    DescriptionRole = Qt.ItemDataRole.UserRole + 3
    ReferenceRole = Qt.ItemDataRole.UserRole + 4
    SourceRole = Qt.ItemDataRole.UserRole + 5
    EvidenceRole = Qt.ItemDataRole.UserRole + 6

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[CircuitIssue] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == self.SeverityRole:
            return item.severity.value
        if role == self.TitleRole:
            return item.title
        if role == self.DescriptionRole:
            return item.description
        if role == self.ReferenceRole:
            return item.reference
        if role == self.SourceRole:
            return item.source
        if role == self.EvidenceRole:
            return [evidence_card(entry) for entry in item.evidence]
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.SeverityRole: b"severity",
            self.TitleRole: b"title",
            self.DescriptionRole: b"description",
            self.ReferenceRole: b"reference",
            self.SourceRole: b"source",
            self.EvidenceRole: b"evidence",
        }

    def reset_from(self, issues: list[CircuitIssue]) -> None:
        self.beginResetModel()
        self._items = list(issues)
        self.endResetModel()

    def at(self, row: int) -> CircuitIssue | None:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def remove_at(self, row: int) -> CircuitIssue | None:
        issue = self.at(row)
        if issue is None:
            return None
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._items[row]
        self.endRemoveRows()
        return issue

    def append(self, issue: CircuitIssue) -> None:
        if self.contains(issue):
            return
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(issue)
        self.endInsertRows()

    def contains(self, issue: CircuitIssue) -> bool:
        return any(_same_issue(item, issue) for item in self._items)

    def snapshot(self) -> list[CircuitIssue]:
        return list(self._items)


def _same_issue(left: CircuitIssue, right: CircuitIssue) -> bool:
    return left.reference == right.reference and left.title == right.title


class HistoryListModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    KindRole = Qt.ItemDataRole.UserRole + 2
    TitleRole = Qt.ItemDataRole.UserRole + 3
    SummaryRole = Qt.ItemDataRole.UserRole + 4
    StatusRole = Qt.ItemDataRole.UserRole + 5
    TimestampRole = Qt.ItemDataRole.UserRole + 6
    PendingRole = Qt.ItemDataRole.UserRole + 7

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[CircuitRevision] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == self.IdRole:
            return item.id
        if role == self.KindRole:
            return item.kind.value
        if role == self.TitleRole:
            return item.title
        if role == self.SummaryRole:
            return item.summary
        if role == self.StatusRole:
            return item.status.value
        if role == self.TimestampRole:
            return item.timestamp.strftime("%H:%M:%S")
        if role == self.PendingRole:
            return item.status.value == "pending"
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.IdRole: b"revisionId",
            self.KindRole: b"kind",
            self.TitleRole: b"title",
            self.SummaryRole: b"summary",
            self.StatusRole: b"status",
            self.TimestampRole: b"timestamp",
            self.PendingRole: b"pending",
        }

    def reset_from(self, revisions: list[CircuitRevision]) -> None:
        self.beginResetModel()
        self._items = list(revisions)
        self.endResetModel()

    def append(self, revision: CircuitRevision) -> None:
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(revision)
        self.endInsertRows()

    def find(self, revision_id: str) -> CircuitRevision | None:
        for item in self._items:
            if item.id == revision_id:
                return item
        return None

    def pending_count(self) -> int:
        return sum(1 for item in self._items if item.status.value == "pending")

    def snapshot(self) -> list[CircuitRevision]:
        return list(self._items)

    def notify_row(self, revision_id: str) -> None:
        for row, item in enumerate(self._items):
            if item.id == revision_id:
                index = self.index(row)
                self.dataChanged.emit(index, index)
                return


class LogListModel(QAbstractListModel):
    TimestampRole = Qt.ItemDataRole.UserRole + 1
    LevelRole = Qt.ItemDataRole.UserRole + 2
    MessageRole = Qt.ItemDataRole.UserRole + 3
    LineRole = Qt.ItemDataRole.UserRole + 4

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[tuple[datetime, str, str]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        timestamp, level, message = self._items[index.row()]
        time_text = timestamp.strftime("%H:%M:%S")
        if role == self.TimestampRole:
            return time_text
        if role == self.LevelRole:
            return level
        if role == self.MessageRole:
            return message
        if role == self.LineRole:
            if level in {"WARNING", "ERROR"}:
                return f"[{time_text}] {level} {message}"
            return f"[{time_text}] {message}"
        return None

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802
        return {
            self.TimestampRole: b"timestamp",
            self.LevelRole: b"level",
            self.MessageRole: b"message",
            self.LineRole: b"line",
        }

    def append(self, level: str, message: str) -> None:
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append((datetime.now(), level, message))
        self.endInsertRows()

    def plain_text(self) -> str:
        lines: list[str] = []
        for timestamp, level, message in self._items:
            time_text = timestamp.strftime("%H:%M:%S")
            if level in {"WARNING", "ERROR"}:
                lines.append(f"[{time_text}] {level} {message}")
            else:
                lines.append(f"[{time_text}] {message}")
        return "\n".join(lines)
