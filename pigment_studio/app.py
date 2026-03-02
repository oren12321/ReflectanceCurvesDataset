import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import PigmentStudioMainWindow


def main():
    app = QApplication(sys.argv)
    window = PigmentStudioMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
