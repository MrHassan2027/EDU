# Copyright © 2026 Mr. Hassan — https://mrhassan-dev.vercel.app/
# All rights reserved. Unauthorized use or distribution is prohibited.

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PyQt6.QtGui import QPixmap, QWheelEvent, QPainter
from PyQt6.QtCore import Qt, pyqtSignal


class ImageViewer(QWidget):
    load_error = pyqtSignal(str)

    _MIN_ZOOM = 0.05
    _MAX_ZOOM = 20.0

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._zoom = 1.0
        self._fit_mode = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._view = _ImageGraphicsView(self._scene, self._on_wheel)
        layout.addWidget(self._view, 1)
        layout.addWidget(self._build_nav())

    def _build_nav(self) -> QWidget:
        nav = QWidget()
        nav.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #0c1020, stop:1 #07091a);"
            "border-top: 1px solid #141c38;"
        )
        nav.setFixedHeight(42)
        row = QHBoxLayout(nav)
        row.setContentsMargins(10, 4, 10, 4)
        row.setSpacing(8)

        btn_ccw = QPushButton("↺  Rotate L")
        btn_ccw.setToolTip("Rotate 90° counter-clockwise")
        btn_ccw.clicked.connect(self.rotate_ccw)
        row.addWidget(btn_ccw)

        btn_cw = QPushButton("Rotate R  ↻")
        btn_cw.setToolTip("Rotate 90° clockwise")
        btn_cw.clicked.connect(self.rotate_cw)
        row.addWidget(btn_cw)

        row.addStretch()

        btn_fit = QPushButton("Fit")
        btn_fit.setFixedWidth(38)
        btn_fit.setToolTip("Fit image to window")
        btn_fit.clicked.connect(self.fit)
        row.addWidget(btn_fit)

        return nav

    # ── Public API ───────────────────────────────────────────────────────────

    def load(self, path: str):
        self._scene.clear()
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.load_error.emit(f"Cannot open: {os.path.basename(path)}")
            return
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._pixmap_item.setTransformOriginPoint(pixmap.width() / 2, pixmap.height() / 2)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self._view.resetTransform()
        self._zoom = 1.0
        self._fit_mode = True
        self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def rotate_cw(self):
        if not self._pixmap_item:
            return
        self._pixmap_item.setRotation((self._pixmap_item.rotation() + 90) % 360)
        self._update_scene_rect()
        if self._fit_mode:
            self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def rotate_ccw(self):
        if not self._pixmap_item:
            return
        self._pixmap_item.setRotation((self._pixmap_item.rotation() - 90) % 360)
        self._update_scene_rect()
        if self._fit_mode:
            self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def fit(self):
        if self._pixmap_item:
            self._view.resetTransform()
            self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self._zoom = 1.0
            self._fit_mode = True

    # ── Internal ─────────────────────────────────────────────────────────────

    def _update_scene_rect(self):
        if self._pixmap_item:
            br = self._pixmap_item.mapToScene(
                self._pixmap_item.boundingRect()
            ).boundingRect()
            self._scene.setSceneRect(br)

    def _on_wheel(self, delta: int):
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        new_zoom = self._zoom * factor
        if self._MIN_ZOOM <= new_zoom <= self._MAX_ZOOM:
            self._zoom = new_zoom
            self._fit_mode = False
            self._view.scale(factor, factor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap_item and self._fit_mode:
            self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class _ImageGraphicsView(QGraphicsView):
    def __init__(self, scene: QGraphicsScene, wheel_cb):
        super().__init__(scene)
        self._wheel_cb = wheel_cb
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("background: #07091a; border: none;")

    def wheelEvent(self, event: QWheelEvent):
        self._wheel_cb(event.angleDelta().y())
