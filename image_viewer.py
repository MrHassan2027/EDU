# Copyright © 2026 Mr. Hassan — https://mrhassan-dev.vercel.app/
# All rights reserved. Unauthorized use or distribution is prohibited.

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtGui import QPixmap, QWheelEvent, QPainter
from PyQt6.QtCore import Qt


class ImageViewer(QGraphicsView):
    _MIN_ZOOM = 0.05
    _MAX_ZOOM = 20.0

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._zoom = 1.0

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("background: #07091a; border: none;")

    def load(self, path: str):
        self._scene.clear()
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.resetTransform()
        self._zoom = 1.0
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        new_zoom = self._zoom * factor
        if self._MIN_ZOOM <= new_zoom <= self._MAX_ZOOM:
            self._zoom = new_zoom
            self.scale(factor, factor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap_item and self._zoom == 1.0:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
