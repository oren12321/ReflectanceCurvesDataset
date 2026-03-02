from PySide6.QtWidgets import QDialog, QRubberBand, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QPoint, QRect, QSize


class CropDialog(QDialog):
    """
    Modal dialog to select a rectangular region from an image.
    Returns the cropped QImage.
    """

    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Color Blob Area")
        self.setModal(True)

        self.label = QLabel(self)
        self.pixmap = QPixmap(image_path)

        if self.pixmap.width() > 1000 or self.pixmap.height() > 800:
            self.pixmap = self.pixmap.scaled(
                1000, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

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
        self.accept()

    def get_cropped_image(self):
        return self.pixmap.copy(self.selected_rect).toImage()
