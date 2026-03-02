from typing import Dict, Any
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QSplitter,
    QTabWidget,
)
from PySide6.QtCore import Qt

from core.theming import MAIN_STYLE
from core.plugins import PluginManager
from core.data import SpectralData
from ui.log_panel import LogPanel
from ui.sidebar.file_session_panel import FileSessionPanel
from plugins.spectral.spectral_plugin import SpectralPlugin

import sys
import ctypes

def enable_windows_dark_title_bar(hwnd):
    if sys.platform != "win32":
        return  # Do nothing on macOS/Linux

    try:
        import ctypes
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20  # Windows 10 1809+

        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )
    except Exception:
        pass

class PigmentStudioMainWindow(QMainWindow):
    """
    Main application window.
    Layout:
      - Left: sidebar tabs (FILE, future)
      - Right: vertical splitter:
          - Top: workspace tabs (plugins)
          - Bottom: log panel
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pigment Studio | Research & Synthesis")
        self.resize(1280, 820)

        self.spectral_data = SpectralData()
        self.plugin_manager = PluginManager()
        self._plugins = []

        self.sidebar_tabs: QTabWidget
        self.workspace_tabs: QTabWidget
        self.log_panel: LogPanel

        self._apply_styles()
        self._setup_ui()
        self._register_plugins()
        self._populate_workspace_tabs()
        
        hwnd = int(self.winId())
        enable_windows_dark_title_bar(hwnd)
        self.show()

    def _apply_styles(self):
        self.setStyleSheet(MAIN_STYLE)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)

        self.global_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.global_splitter)

        self.sidebar_tabs = QTabWidget()
        self.sidebar_tabs.setTabPosition(QTabWidget.West)

        self.right_splitter = QSplitter(Qt.Vertical)
        self.workspace_tabs = QTabWidget()
        self.log_panel = LogPanel()

        self.right_splitter.addWidget(self.workspace_tabs)
        self.right_splitter.addWidget(self.log_panel)
        self.right_splitter.setStretchFactor(0, 5)
        self.right_splitter.setStretchFactor(1, 2)

        self.global_splitter.addWidget(self.sidebar_tabs)
        self.global_splitter.addWidget(self.right_splitter)
        self.global_splitter.setStretchFactor(0, 1)
        self.global_splitter.setStretchFactor(1, 4)

        file_panel = FileSessionPanel(
            on_new_session=self._handle_new_session,
            on_import_session=self._handle_import_session,
            on_export_session=self._handle_export_session,
            log_callback=self.log_panel.append,
        )
        self.sidebar_tabs.addTab(file_panel, "FILE")

    def _register_plugins(self):
        spectral_plugin = SpectralPlugin(self.spectral_data)
        self.plugin_manager.register_plugin(spectral_plugin)
        self._plugins.append(spectral_plugin)

    def _populate_workspace_tabs(self):
        for plugin in self.plugin_manager.get_plugins():
            widget = plugin.create_workspace_widget(self)
            self.workspace_tabs.addTab(widget, plugin.get_name())
            log_signal = plugin.get_log_signal()
            if log_signal is not None:
                log_signal.connect(self.log_panel.append)

    def _handle_new_session(self):
        for plugin in self._plugins:
            plugin.on_new_session()

    def _handle_export_session(self) -> Dict[str, Any]:
        session_data: Dict[str, Any] = {}
        for plugin in self._plugins:
            session_data[plugin.get_name()] = plugin.export_session()
        return session_data

    def _handle_import_session(self, data: Dict[str, Any]):
        for plugin in self._plugins:
            name = plugin.get_name()
            if name in data:
                plugin.import_session(data[name])
