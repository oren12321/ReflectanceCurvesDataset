from typing import Any, Dict, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from core.plugins import PluginBase
from core.data import SpectralData
from spectral_controller.controller import SpectralController
from plugins.spectral.spectral_widget import SpectralAnalysisWidget


class SpectralPlugin(PluginBase):
    """
    Plugin wrapper for the spectral editor.
    No QObject inheritance — avoids metaclass conflict.
    """

    def __init__(self, spectral_data: SpectralData):
        self._data = spectral_data
        self._controller = SpectralController(self._data)
        self._widget: Optional[SpectralAnalysisWidget] = None

    def get_name(self) -> str:
        return "Spectral Editor"

    def create_workspace_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        if self._widget is None:
            self._widget = SpectralAnalysisWidget(self._controller, parent)
        return self._widget

    def on_new_session(self):
        self._data.reset_all()
        if self._widget is not None:
            self._widget.combo_active_bg.clear()
            self._widget.refresh_bg_artists()
            self._widget.combo_illuminant.setCurrentIndex(0)
            self._widget.update_view()

    def export_session(self) -> Dict[str, Any]:
        return self._data.to_dict()

    def import_session(self, data: Dict[str, Any]):
        self._data.from_dict(data)
        if self._widget is not None:
            self._widget.combo_active_bg.clear()
            for layer in self._data.bg_layers:
                self._widget.combo_active_bg.addItem(layer["name"])

            idx = self._widget.combo_illuminant.findText(
                self._data.illuminant_key,
                Qt.MatchContains | Qt.MatchCaseSensitive,
            )
            if idx >= 0:
                self._widget.combo_illuminant.setCurrentIndex(idx)

            self._widget.refresh_bg_artists()
            self._widget.update_view()

    def get_log_signal(self):
        if self._widget is None:
            return None
        return self._widget.log_signal
