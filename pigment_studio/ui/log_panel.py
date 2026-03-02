from PySide6.QtWidgets import QTextEdit


class LogPanel(QTextEdit):
    """Simple log panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.append("> System initialized.")
