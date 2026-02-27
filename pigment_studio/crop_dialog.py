from PySide6.QtWidgets import QDialog, QRubberBand, QFileDialog, QLabel
from PySide6.QtGui import QPixmap, QPalette
from PySide6.QtCore import Qt, QPoint, QRect, QSize

class CropDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Color Blob Area")
        self.setModal(True)
        
        self.label = QLabel(self)
        self.pixmap = QPixmap(image_path)
        # Scale down if image is too large for screen
        if self.pixmap.width() > 1000 or self.pixmap.height() > 800:
            self.pixmap = self.pixmap.scaled(1000, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.label.setPixmap(self.pixmap)
        self.setFixedSize(self.pixmap.size())
        
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self.origin = QPoint()
        self.selected_rect = QRect()

    def mousePressEvent(self, event):
        self.origin = event.pos()
        self.rubber_band.setGeometry(QRect(self.origin, QSize()))
        self.rubber_band.show()

    def mouseMoveEvent(self, event):
        self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        self.selected_rect = self.rubber_band.geometry()
        self.accept() # Close and return result

    def get_cropped_image(self):
        return self.pixmap.copy(self.selected_rect).toImage()
