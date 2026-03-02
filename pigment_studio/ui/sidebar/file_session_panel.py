import json
from typing import Callable
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt


class FileSessionPanel(QWidget):
    """
    Left sidebar "FILE" tab.
    Handles new session, import, export.
    """

    def __init__(
        self,
        parent=None,
        on_new_session: Callable[[], None] = None,
        on_import_session: Callable[[dict], None] = None,
        on_export_session: Callable[[], dict] = None,
        log_callback: Callable[[str], None] = None,
    ):
        super().__init__(parent)
        self._on_new_session = on_new_session
        self._on_import_session = on_import_session
        self._on_export_session = on_export_session
        self._log = log_callback or (lambda msg: None)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        lbl = QLabel("SESSION CONTROL")
        lbl.setStyleSheet("font-weight: bold; color: #d4af37;")
        layout.addWidget(lbl)

        self.btn_new_session = QPushButton("New Session")
        danger_style = """
            QPushButton {
                padding: 8px;
                background-color: #722f37;
                border: 1px solid #a52a2a;
                color: #ffffff;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #8b0000;
                border: 1px solid #ff4500;
            }
            QPushButton:pressed {
                background-color: #4a1a1e;
            }
        """
        self.btn_new_session.setStyleSheet(danger_style)

        self.btn_import = QPushButton("Import Session")
        self.btn_export = QPushButton("Export Session")

        self.btn_new_session.clicked.connect(self._handle_new_session)
        self.btn_import.clicked.connect(self._handle_import)
        self.btn_export.clicked.connect(self._handle_export)

        layout.addWidget(self.btn_new_session)
        layout.addWidget(self.btn_import)
        layout.addWidget(self.btn_export)
        layout.addStretch()

    def _handle_new_session(self):
        reply = QMessageBox.question(
            self,
            "Confirm New Session",
            "This will clear all current work, background layers, and targets.\n\nAre you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if self._on_new_session:
                self._on_new_session()
            self._log("> New Session Started. All data cleared.")

    def _handle_export(self):
        if not self._on_export_session:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Session", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            data = self._on_export_session()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self._log(f"> Session saved to: {path}")
        except Exception as e:
            self._log(f"> Error saving session: {e}")

    def _handle_import(self):
        if not self._on_import_session:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Session", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._on_import_session(data)
            self._log(f"> Session loaded: {path}")
        except Exception as e:
            self._log(f"> Error loading session: {e}")
