"""Qt list models exposed to QML.

AgentsModel  — the 11 agents + live state for the Analysis page.
ReportsModel — the field reports queued for analysis, for the Input page.
KPIs / actions stay as plain dict-lists consumed by QML Repeaters on the dashboard.
"""
from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Slot

# agent id -> Arabic display name (worker agents + chief coordinator)
AGENT_NAMES = {
    "ops":      "العمليات الميدانية",
    "quality":  "الجودة والامتثال",
    "safety":   "السلامة المهنية",
    "civil":    "الأعمال الإنشائية",
    "cost":     "التكاليف والميزانية",
    "contract": "العقود والشؤون القانونية",
    "procure":  "المشتريات والموردين",
    "supply":   "المخازن وسلاسل التوريد",
    "risk":     "إدارة المخاطر",
    "schedule": "الجدول الزمني",
    "chief":    "التنسيق المركزي",
}
_ORDER = ["ops", "quality", "safety", "civil", "cost", "contract",
          "procure", "supply", "risk", "schedule", "chief"]


class AgentsModel(QAbstractListModel):
    AgentIdRole = Qt.UserRole + 1
    NameRole    = Qt.UserRole + 2
    StateRole   = Qt.UserRole + 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._agents = [{"id": a, "name": AGENT_NAMES[a], "state": "idle"} for a in _ORDER]

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._agents)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        a = self._agents[index.row()]
        if role == self.AgentIdRole: return a["id"]
        if role == self.NameRole:    return a["name"]
        if role == self.StateRole:   return a["state"]
        return None

    def roleNames(self):
        return {
            self.AgentIdRole: b"agentId",
            self.NameRole:    b"name",
            self.StateRole:   b"state",
        }

    def set_state(self, agent_id, state):
        for row, a in enumerate(self._agents):
            if a["id"] == agent_id:
                a["state"] = state
                idx = self.index(row, 0)
                self.dataChanged.emit(idx, idx, [self.StateRole])
                break

    def reset_states(self):
        self.beginResetModel()
        for a in self._agents:
            a["state"] = "idle"
        self.endResetModel()


class ReportsModel(QAbstractListModel):
    SourceRole  = Qt.UserRole + 1
    DeptRole    = Qt.UserRole + 2
    FromRole    = Qt.UserRole + 3
    DateRole    = Qt.UserRole + 4
    ContentRole = Qt.UserRole + 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._reports = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._reports)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r = self._reports[index.row()]
        if role == self.SourceRole:  return r.get("source", "")
        if role == self.DeptRole:    return r.get("dept", "")
        if role == self.FromRole:    return r.get("from", "")
        if role == self.DateRole:    return r.get("date", "")
        if role == self.ContentRole: return r.get("content", "")
        return None

    def roleNames(self):
        return {
            self.SourceRole:  b"source",
            self.DeptRole:    b"dept",
            self.FromRole:    b"from_",
            self.DateRole:    b"date",
            self.ContentRole: b"content",
        }

    # ---- python-side helpers ----
    def reports(self):
        return list(self._reports)

    def count(self):
        return len(self._reports)

    def add(self, report: dict):
        self.beginInsertRows(QModelIndex(), len(self._reports), len(self._reports))
        self._reports.append(report)
        self.endInsertRows()

    def extend(self, reports: list):
        if not reports:
            return
        start = len(self._reports)
        self.beginInsertRows(QModelIndex(), start, start + len(reports) - 1)
        self._reports.extend(reports)
        self.endInsertRows()

    def clear(self):
        if not self._reports:
            return
        self.beginResetModel()
        self._reports = []
        self.endResetModel()

    @Slot(int)
    def remove(self, row: int):
        if 0 <= row < len(self._reports):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._reports.pop(row)
            self.endRemoveRows()
