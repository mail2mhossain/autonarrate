from PySide6.QtWidgets import QFrame
from PySide6.QtGui import QPainter, QPen
from PySide6.QtCore import Qt

class RectFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Optional: set minimum size or other properties

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen(Qt.white, 1)  # Red rectangle, 3px thick
        painter.setPen(pen)
        # Draw rectangle inside the frame's bounds, leaving a margin
        margin = 5
        painter.drawRect(margin, margin, self.width()-2*margin, self.height()-2*margin)