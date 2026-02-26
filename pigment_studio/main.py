import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QSplitter, QFrame, 
                             QPushButton, QTextEdit, QLabel)
from PySide6.QtCore import Qt

class PigmentApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Pigment & Medium Analysis Studio")
        self.resize(1100, 700)

        # 1. Apply the "Warm Medium Gray" Theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #4a4a48; 
                color: #e0e0e0;
                font-family: 'Segoe UI', sans-serif;
            }
            QTabWidget::pane { border: 1px solid #5a5a58; }
            QTabBar::tab {
                background: #3d3d3b;
                padding: 10px 15px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background: #636361;
                border-left: 3px solid #d4af37; /* Gold accent for "warmth" */
            }
            QTextEdit {
                background-color: #2b2b2a;
                border: none;
                color: #a0ffa0; /* Log green */
                font-family: 'Consolas', monospace;
            }
        """)

        # Main Layout Container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(2)

        # --- LEFT PANEL: Vertical Tabs ---
        self.sidebar_tabs = QTabWidget()
        self.sidebar_tabs.setTabPosition(QTabWidget.West) # Vertical tabs
        self.sidebar_tabs.setFixedWidth(200)
        
        # Placeholder Sidebar Screens
        self.sidebar_tabs.addTab(self.create_placeholder("Toolbox A"), "Analysis")
        self.sidebar_tabs.addTab(self.create_placeholder("Toolbox B"), "Synthesis")
        self.sidebar_tabs.addTab(self.create_placeholder("Settings"), "Database")

        # --- RIGHT PANEL: Splitter (Workspace + Logs) ---
        right_splitter = QSplitter(Qt.Vertical)

        # Top Section: Workspace Tabs
        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.addTab(self.create_placeholder("Graph View"), "Spectroscopy")
        self.workspace_tabs.addTab(self.create_placeholder("Dataset Table"), "Pigment Matrix")
        
        # Bottom Section: Logs
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("System Logs...")
        self.log_output.append("Application started: Ready for pigment analysis.")

        # Add to splitter
        right_splitter.addWidget(self.workspace_tabs)
        right_splitter.addWidget(self.log_output)
        right_splitter.setStretchFactor(0, 4) # Workspace is 4x larger than Logs
        right_splitter.setStretchFactor(1, 1)

        # Final Assembly
        main_layout.addWidget(self.sidebar_tabs)
        main_layout.addWidget(right_splitter)

    def create_placeholder(self, text):
        """Helper to create an empty container for your future widgets"""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(f"Container: {text}"))
        layout.addStretch()
        return widget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PigmentApp()
    window.show()
    sys.exit(app.exec())
