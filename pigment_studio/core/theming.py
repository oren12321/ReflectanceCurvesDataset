MAIN_STYLE = """
QMainWindow, QWidget {
    background-color: #2b2b2a;
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
}

/* Tabs */
QTabBar::tab:west {
    background: #3a3a38;
    padding: 8px 0px;
    margin-bottom: 2px;
    min-width: 40px;
}
QTabBar::tab:top {
    background: #3a3a38;
    padding: 6px 14px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #555553;
    border-left: 2px solid #d4af37;
    border-bottom: 2px solid #d4af37;
}
QTabWidget::pane {
    border: 1px solid #3d3d3b;
}

/* Splitters */
QSplitter::handle {
    background-color: #3d3d3b;
}
QSplitter::handle:horizontal {
    width: 4px;
}
QSplitter::handle:vertical {
    height: 4px;
}

/* Text edit (log) */
QTextEdit {
    background-color: #1f1f1e;
    border: 1px solid #3d3d3b;
    color: #a0d0a0;
    font-family: 'Consolas', monospace;
    font-size: 11px;
}

/* Buttons */
QPushButton {
    padding: 6px 10px;
    background-color: #3d3d3b;
    border: 1px solid #5a5a58;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #4a4a48;
}
QPushButton:pressed {
    background-color: #2f2f2d;
}

/* Group boxes */
QGroupBox {
    border: 1px solid #3d3d3b;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 18px;
    font-weight: bold;
    color: #d4af37;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
}

/* Labels */
QLabel {
    color: #e0e0e0;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #2b2b2a;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #5a5a58;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #d4af37;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""
