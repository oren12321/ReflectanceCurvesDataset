from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QPoint

class DarkTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent
        self._drag_pos = None

        self.setFixedHeight(36)
        self.setStyleSheet("""
            background-color: #1f242b;
            border-bottom: 1px solid #2d3239;
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        # Title text
        self.title = QLabel("Pigment Studio")
        self.title.setStyleSheet("color: #e6e9ef; font-size: 13px;")
        layout.addWidget(self.title)

        layout.addStretch()

        # Window buttons
        self.btn_min = QPushButton("—")
        self.btn_max = QPushButton("□")
        self.btn_close = QPushButton("✕")

        for b in (self.btn_min, self.btn_max, self.btn_close):
            b.setFixedSize(34, 26)
            b.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #e6e9ef;
                    border: none;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #3a4250;
                    border: 1px solid #4ea3ff;
                    border-radius: 4px;
                }
                QPushButton:pressed {
                    background-color: #242a31;
                }
            """)

        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(self.btn_close)

        # Connect actions
        self.btn_min.clicked.connect(parent.showMinimized)
        self.btn_max.clicked.connect(self._toggle_max_restore)
        self.btn_close.clicked.connect(parent.close)

    def _toggle_max_restore(self):
        if self._parent.isMaximized():
            self._parent.showNormal()
        else:
            self._parent.showMaximized()

    # --- Window dragging ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            diff = event.globalPosition().toPoint() - self._drag_pos
            self._parent.move(self._parent.pos() + diff)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseDoubleClickEvent(self, event):
        self._toggle_max_restore()
