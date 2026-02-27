import sys
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QSplitter, QFrame, 
                             QLabel, QTextEdit, QPushButton, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from spectral_tool import SpectralAnalysisWidget, SpectralData

class PigmentApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pigment Studio | Research & Synthesis")
        self.resize(1200, 800)

        # Shared Project Data
        self.shared_spectral_data = SpectralData()

        self.apply_styles()
        self.setup_ui()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #4a4a48; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; font-size: 12px; }
            QTabBar::tab:west { background: #3d3d3b; padding: 8px 0px; margin-bottom: 2px; min-width: 30px; }
            QTabBar::tab:top { background: #3d3d3b; padding: 4px 12px; margin-right: 2px; }
            QTabBar::tab:selected { background: #636361; border-left: 2px solid #d4af37; border-bottom: 2px solid #d4af37; }
            QTabWidget::pane { border: 1px solid #3d3d3b; }
            QSplitter::handle { background-color: #3d3d3b; }
            QSplitter::handle:horizontal { width: 4px; }
            QSplitter::handle:vertical { height: 4px; }
            QTextEdit { background-color: #2b2b2a; border: 1px solid #3d3d3b; color: #8fbc8f; font-family: 'Consolas', monospace; font-size: 11px; }
        """)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)

        self.global_splitter = QSplitter(Qt.Horizontal)

        # Left: Sidebar
        self.sidebar_tabs = QTabWidget()
        self.sidebar_tabs.setTabPosition(QTabWidget.West)
        self.setup_sidebar_file_tab()

        # Right: Workspace + Logs
        self.right_splitter = QSplitter(Qt.Vertical)
        self.workspace_tabs = QTabWidget()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.append("> System initialized.")

        # Tools
        self.spectral_tool = SpectralAnalysisWidget(self.shared_spectral_data)
        self.workspace_tabs.addTab(self.spectral_tool, "Spectral Editor")
        self.spectral_tool.log_signal.connect(self.log_output.append)

        # Assembly
        self.right_splitter.addWidget(self.workspace_tabs)
        self.right_splitter.addWidget(self.log_output)
        self.right_splitter.setStretchFactor(0, 5)
        self.global_splitter.addWidget(self.sidebar_tabs)
        self.global_splitter.addWidget(self.right_splitter)
        self.global_splitter.setStretchFactor(0, 1)
        self.global_splitter.setStretchFactor(1, 4)
        main_layout.addWidget(self.global_splitter)

    def setup_sidebar_file_tab(self):
        session_widget = QWidget()
        layout = QVBoxLayout(session_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        lbl = QLabel("SESSION CONTROL")
        lbl.setStyleSheet("font-weight: bold; color: #d4af37;")
        layout.addWidget(lbl)

        self.btn_new_session = QPushButton("New Session")
        # Professional "Danger" style: Dark red background with a subtle highlight
        danger_style = """
            QPushButton {
                padding: 8px;
                background-color: #722f37; /* Wine Red */
                border: 1px solid #a52a2a;
                color: #ffffff;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #8b0000; /* Darker Red on hover */
                border: 1px solid #ff4500;
            }
            QPushButton:pressed {
                background-color: #4a1a1e;
            }
        """
        self.btn_new_session.setStyleSheet(danger_style)
        
        self.btn_sidebar_import = QPushButton("Import Session")
        self.btn_sidebar_export = QPushButton("Export Session")
        
        style = "padding: 8px; background: #3d3d3b; border: 1px solid #5a5a58;"
        self.btn_sidebar_import.setStyleSheet(style)
        self.btn_sidebar_export.setStyleSheet(style)

        self.btn_new_session.clicked.connect(self.handle_new_session)
        self.btn_sidebar_import.clicked.connect(self.handle_session_import)
        self.btn_sidebar_export.clicked.connect(self.handle_session_export)

        layout.addWidget(self.btn_new_session)
        layout.addWidget(self.btn_sidebar_import)
        layout.addWidget(self.btn_sidebar_export)
        layout.addStretch()
        self.sidebar_tabs.addTab(session_widget, "FILE")

    def handle_new_session(self):
        # 1. Show Aggressive Warning Dialog
        reply = QMessageBox.question(
            self, "Confirm New Session",
            "This will clear all current work, background layers, and targets. \n\nAre you sure?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 2. Reset the shared data model
            self.shared_spectral_data.reset_all() # We will define this in SpectralData
            
            # 3. Force UI Updates
            self.spectral_tool.refresh_bg_artists() # Clears images
            self.spectral_tool.combo_active_bg.clear() # Clears dropdown
            self.spectral_tool.update_view() # Resets graph & target labels
            
            self.log_output.append("> New Session Started. All data cleared.")

    def handle_session_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Session", "", "JSON (*.json)")
        if path:
            with open(path, 'w') as f:
                json.dump(self.shared_spectral_data.to_dict(), f, indent=4)
            self.log_output.append(f"> Session saved to: {path}")
            
    def handle_session_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Session", "", "JSON (*.json)")
        if path:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                self.shared_spectral_data.from_dict(data)
                
                # REFRESH BOTH THE CURVE AND THE BACKGROUND IMAGES
                self.spectral_tool.combo_active_bg.clear()
                for layer in self.shared_spectral_data.bg_layers:
                    self.spectral_tool.combo_active_bg.addItem(layer["name"])
                
                self.spectral_tool.refresh_bg_artists()
                self.spectral_tool.update_view()
                        
                self.log_output.append(f"> Session loaded: {path}")
            except Exception as e:
                self.log_output.append(f"> Error loading session: {e}")

    def create_placeholder(self, text):
        widget = QFrame()
        layout = QVBoxLayout(widget)
        lbl = QLabel(text); lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        return widget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PigmentApp()
    window.show()
    sys.exit(app.exec())
