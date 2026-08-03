"""Analysis worker — runs the agent fleet off the UI thread.

Lives on a QThread. Wraps AgentsEngine.run_all and re-emits its per-agent /
progress / log callbacks as Qt signals so the UI updates only via the main
thread's event loop. The worker never touches QML objects directly.
"""
import logging

from PySide6.QtCore import QObject, Signal, Slot, QThread

from core.errors import friendly_error

# NB: the class below declares a `log` Signal — name the module logger
# something else so it isn't shadowed on the instance.
_log = logging.getLogger(__name__)


class AnalysisWorker(QObject):
    agentState = Signal(str, str)   # (agent_id, "running"|"done"|"error")
    progress   = Signal(int)        # 0..100
    log        = Signal(str)
    finished   = Signal("QVariant")  # the full results dict
    failed     = Signal(str)

    def __init__(self, engine, reports):
        super().__init__()
        self._engine  = engine       # AgentsEngine
        self._reports = reports      # list[dict]

    @Slot()
    def run(self):
        try:
            self._engine.log = lambda m: self.log.emit(str(m))
            results = self._engine.run_all(
                self._reports,
                progress_cb=lambda p: self.progress.emit(int(p)),
                agent_cb=lambda aid, state: self.agentState.emit(aid, state),
                should_stop=lambda: QThread.currentThread().isInterruptionRequested(),
            )
            self.finished.emit(results)
        except Exception as e:  # noqa: BLE001 — surface any failure to the UI
            _log.warning("analysis worker failed: %s", e, exc_info=True)
            self.failed.emit(friendly_error(str(e)))
