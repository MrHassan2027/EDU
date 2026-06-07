import fitz
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGraphicsView, QGraphicsScene
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QWheelEvent, QShortcut, QKeySequence
from PyQt6.QtCore import Qt

# Render PDF pages at this DPI multiplier — high enough for sharp text at any zoom.
_RENDER_DPI = 3.0


class PDFViewer(QWidget):
    def __init__(self):
        super().__init__()
        self._doc: fitz.Document | None = None
        self._page_num = 0
        self._view_scale = 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._scene = QGraphicsScene(self)
        self._view = _PDFGraphicsView(self._scene, self._wheel_zoom)
        layout.addWidget(self._view, 1)

        layout.addWidget(self._build_nav())

        QShortcut(QKeySequence(Qt.Key.Key_Left),  self).activated.connect(self._prev_page)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self).activated.connect(self._next_page)
        QShortcut(QKeySequence("Ctrl++"),         self).activated.connect(lambda: self._step_zoom(1.25))
        QShortcut(QKeySequence("Ctrl+-"),         self).activated.connect(lambda: self._step_zoom(1 / 1.25))

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

        self._btn_prev = QPushButton("◀  Prev")
        self._btn_prev.setEnabled(False)
        self._btn_prev.clicked.connect(self._prev_page)
        row.addWidget(self._btn_prev)

        self._btn_next = QPushButton("Next  ▶")
        self._btn_next.setEnabled(False)
        self._btn_next.clicked.connect(self._next_page)
        row.addWidget(self._btn_next)

        row.addStretch()

        self._page_lbl = QLabel("No document")
        self._page_lbl.setStyleSheet("color: #c0c0c0;")
        row.addWidget(self._page_lbl)

        row.addStretch()

        btn_fit = QPushButton("Fit")
        btn_fit.setFixedWidth(38)
        btn_fit.setToolTip("Fit page to window")
        btn_fit.clicked.connect(self._fit_to_view)
        row.addWidget(btn_fit)

        btn_out = QPushButton("−")
        btn_out.setFixedWidth(32)
        btn_out.clicked.connect(lambda: self._step_zoom(1 / 1.25))
        row.addWidget(btn_out)

        self._zoom_lbl = QLabel("100%")
        self._zoom_lbl.setStyleSheet("color: #c0c0c0;")
        self._zoom_lbl.setFixedWidth(48)
        self._zoom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self._zoom_lbl)

        btn_in = QPushButton("+")
        btn_in.setFixedWidth(32)
        btn_in.clicked.connect(lambda: self._step_zoom(1.25))
        row.addWidget(btn_in)

        return nav

    # ── Public API ───────────────────────────────────────────────────────────

    def load(self, path: str):
        if self._doc:
            self._doc.close()
        self._doc = fitz.open(path)
        self._page_num = 0
        self._view.resetTransform()
        self._view_scale = 1.0
        self._render_page()
        self._fit_to_view()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _render_page(self):
        """Re-rasterise the current page at _RENDER_DPI. Does NOT touch the view transform."""
        if not self._doc:
            return
        page = self._doc[self._page_num]
        mat = fitz.Matrix(_RENDER_DPI, _RENDER_DPI)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = QImage(pix.samples_ptr, pix.width, pix.height,
                     pix.stride, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img)

        self._scene.clear()
        item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(item.boundingRect())

        total = len(self._doc)
        self._page_lbl.setText(f"Page {self._page_num + 1} / {total}")
        self._btn_prev.setEnabled(self._page_num > 0)
        self._btn_next.setEnabled(self._page_num < total - 1)

    def _fit_to_view(self):
        """Scale the view so the page fills the viewport (reset zoom tracking)."""
        self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        # Measure actual scale after fitInView so _view_scale stays accurate
        self._view_scale = self._view.transform().m11() / _RENDER_DPI
        self._zoom_lbl.setText(f"{int(self._view_scale * 100)}%")

    def _step_zoom(self, factor: float):
        self._view.scale(factor, factor)
        self._view_scale *= factor
        self._zoom_lbl.setText(f"{int(self._view_scale * 100)}%")

    def _prev_page(self):
        if self._doc and self._page_num > 0:
            self._page_num -= 1
            current_scale = self._view.transform().m11()
            self._render_page()
            self._fit_to_view()
            # restore previous zoom level
            ratio = current_scale / self._view.transform().m11()
            if abs(ratio - 1.0) > 0.01:
                self._view.scale(ratio, ratio)
                self._view_scale *= ratio
                self._zoom_lbl.setText(f"{int(self._view_scale * 100)}%")

    def _next_page(self):
        if self._doc and self._page_num < len(self._doc) - 1:
            self._page_num += 1
            current_scale = self._view.transform().m11()
            self._render_page()
            self._fit_to_view()
            ratio = current_scale / self._view.transform().m11()
            if abs(ratio - 1.0) > 0.01:
                self._view.scale(ratio, ratio)
                self._view_scale *= ratio
                self._zoom_lbl.setText(f"{int(self._view_scale * 100)}%")

    def _wheel_zoom(self, delta: int):
        self._step_zoom(1.15 if delta > 0 else 1 / 1.15)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._doc:
            self._fit_to_view()


class _PDFGraphicsView(QGraphicsView):
    def __init__(self, scene: QGraphicsScene, wheel_cb):
        super().__init__(scene)
        self._wheel_cb = wheel_cb
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setStyleSheet("background: #07091a; border: none;")

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._wheel_cb(event.angleDelta().y())
        else:
            super().wheelEvent(event)
