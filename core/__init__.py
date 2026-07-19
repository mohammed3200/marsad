"""marsad core — AI engine + agents + contacts data (UI-agnostic logic)."""
from .engine import AIEngine, AgentsEngine, AGENT_PROMPTS, WORKER_AGENTS
from .contacts import ContactsDB, DEPT_KEY_MAP, DEFAULT_STRUCTURE
from .exporters import export_pdf, export_excel

__all__ = [
    "AIEngine", "AgentsEngine", "AGENT_PROMPTS", "WORKER_AGENTS",
    "ContactsDB", "DEPT_KEY_MAP", "DEFAULT_STRUCTURE",
    "export_pdf", "export_excel",
]
