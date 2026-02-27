import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QSplitter, QFrame, 
                             QLabel, QTextEdit, QPushButton)
from PySide6.QtCore import Qt

from spectral_tool import SpectralAnalysisWidget, SpectralData

class PigmentApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Pigment Studio | Research & Synthesis")
        self.resize(1200, 800)

        # 1. Refined "Warm Gray" Theme with thinner Tab styling
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #4a4a48; 
                color: #e0e0e0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            /* Thinner Vertical Tabs */
            QTabBar::tab:west {
                background: #3d3d3b;
                padding: 8px 0px; /* Narrower padding */
                margin-bottom: 2px;
                min-width: 30px; 
            }
            /* Thinner Horizontal Tabs */
            QTabBar::tab:top {
                background: #3d3d3b;
                padding: 4px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #636361;
                border-left: 2px solid #d4af37; /* Side highlight */
                border-bottom: 2px solid #d4af37; /* Top highlight */
            }
            QTabWidget::pane { border: 1px solid #3d3d3b; }
            
            /* Style the Splitter handle (the movable bar) */
            QSplitter::handle {
                background-color: #3d3d3b;
            }
            QSplitter::handle:horizontal { width: 4px; }
            QSplitter::handle:vertical { height: 4px; }
            
            QTextEdit {
                background-color: #2b2b2a;
                border: 1px solid #3d3d3b;
                color: #8fbc8f;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
        """)

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)

        # --- THE GLOBAL SPLITTER (Horizontal: Sidebar vs Workspace) ---
        self.global_splitter = QSplitter(Qt.Horizontal)

        # LEFT PANEL: Vertical Tabs
        self.sidebar_tabs = QTabWidget()
        self.sidebar_tabs.setTabPosition(QTabWidget.West)
        
        # Adding placeholder side screens
        self.sidebar_tabs.addTab(self.create_placeholder("Analysis Tools"), "ANL")
        self.sidebar_tabs.addTab(self.create_placeholder("Synthesis Lab"), "SYN")
        self.sidebar_tabs.addTab(self.create_placeholder("Dataset Manager"), "DAT")
        
        self.setup_sidebar()

        # RIGHT PANEL: Splitter (Vertical: Workspace vs Logs)
        self.right_splitter = QSplitter(Qt.Vertical)

        # Top: Workspace Tabs
        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.addTab(self.create_placeholder("Spectroscopy Visualization"), "Graphs")
        self.workspace_tabs.addTab(self.create_placeholder("Pigment Properties Editor"), "Editor")
        
        # Bottom: Logs
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.append("> System initialized.")
        
        # Create the shared data model
        self.shared_spectral_data = SpectralData()
        
        self.spectral_tool = SpectralAnalysisWidget(self.shared_spectral_data)
        self.workspace_tabs.addTab(self.spectral_tool, "Spectral Editor")
        self.spectral_tool.log_signal.connect(self.log_output.append)

        # In your Main Window's __init__ after creating the spectral_tool:
        self.btn_sidebar_export.clicked.connect(self.spectral_tool.handle_export)
        self.btn_sidebar_import.clicked.connect(self.spectral_tool.handle_import)

        # Assemble Right Side
        self.right_splitter.addWidget(self.workspace_tabs)
        self.right_splitter.addWidget(self.log_output)
        self.right_splitter.setStretchFactor(0, 5) 
        self.right_splitter.setStretchFactor(1, 1)

        # Assemble Global View
        self.global_splitter.addWidget(self.sidebar_tabs)
        self.global_splitter.addWidget(self.right_splitter)
        self.global_splitter.setStretchFactor(0, 2) # Sidebar stays small by default
        self.global_splitter.setStretchFactor(1, 4) # Workspace expands

        main_layout.addWidget(self.global_splitter)

    # In your Main Window class, update the Sidebar construction:
    def setup_sidebar(self):
        # Create a container for Session/File tools
        session_widget = QWidget()
        session_layout = QVBoxLayout(session_widget)
        session_layout.setContentsMargins(10, 10, 10, 10)
        session_layout.setSpacing(10)

        lbl = QLabel("SESSION CONTROL")
        lbl.setStyleSheet("font-weight: bold; color: #d4af37;")
        session_layout.addWidget(lbl)

        self.btn_sidebar_import = QPushButton("Import Session")
        self.btn_sidebar_export = QPushButton("Export Session")
        
        # Style them to look like Sidebar buttons
        sidebar_btn_style = "padding: 8px; background: #3d3d3b; border: 1px solid #5a5a58;"
        self.btn_sidebar_import.setStyleSheet(sidebar_btn_style)
        self.btn_sidebar_export.setStyleSheet(sidebar_btn_style)

        session_layout.addWidget(self.btn_sidebar_import)
        session_layout.addWidget(self.btn_sidebar_export)
        session_layout.addStretch() # Push buttons to top

        # Add to the vertical tabs
        self.sidebar_tabs.addTab(session_widget, "FILE")


    def create_placeholder(self, text):
        widget = QFrame()
        layout = QVBoxLayout(widget)
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        return widget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Hint: Use the [PySide6 Screen Geometry](https://doc.qt.io) 
    # logic if you ever need to force specific pixel densities on high-res screens.
    window = PigmentApp()
    window.show()
    sys.exit(app.exec())
