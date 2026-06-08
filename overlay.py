# Copyright © 2026 Mr. Hassan — https://mrhassan-dev.vercel.app/
# All rights reserved. Unauthorized use or distribution is prohibited.

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QPainterPath, QColor, QCursor
from PyQt6.QtCore import Qt, QPointF


class DrawingOverlay(QWidget):
    """Transparent drawing canvas that floats above the media viewer."""

    DEFAULT_COLOR = QColor("#ff4444")
    DEFAULT_WIDTH = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setMouseTracking(True)

        # Each stroke: (points, color, width, is_erase)
        self._strokes: list[tuple[list[QPointF], QColor, int, bool]] = []
        self._redo_stack: list[tuple[list[QPointF], QColor, int, bool]] = []
        self._current: list[QPointF] = []
        self._active = False
        self._eraser = False
        self._color = self.DEFAULT_COLOR
        self._width = self.DEFAULT_WIDTH

    # ── Public API ───────────────────────────────────────────────────────────

    def set_active(self, active: bool):
        self._active = active
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not active)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor if active else Qt.CursorShape.ArrowCursor))
        self.update()

    def set_eraser(self, enabled: bool):
        self._eraser = enabled

    def set_color(self, color: QColor):
        self._color = color
        self._eraser = False

    def set_width(self, width: int):
        self._width = width

    def clear(self):
        self._strokes.clear()
        self._current.clear()
        self._redo_stack.clear()
        self.update()

    def undo(self):
        if self._strokes:
            self._redo_stack.append(self._strokes.pop())
            self.update()

    def redo(self):
        if self._redo_stack:
            self._strokes.append(self._redo_stack.pop())
            self.update()

    # ── Mouse events ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._current = [event.position()]
            self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._current:
            self._current.append(event.position())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._current:
            self._strokes.append(
                (list(self._current), QColor(self._color), self._width, self._eraser)
            )
            self._redo_stack.clear()
            self._current.clear()
            self.update()

    # ── Rendering ────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for points, color, width, is_erase in self._strokes:
            if is_erase:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            else:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            self._paint_stroke(painter, points, color, width)

        if self._current:
            if self._eraser:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            else:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            self._paint_stroke(painter, self._current, self._color, self._width)

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if self._active:
            painter.setPen(QPen(QColor(233, 69, 96, 60), 2))
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

    @staticmethod
    def _paint_stroke(painter: QPainter, points: list[QPointF], color: QColor, width: int):
        if not points:
            return
        pen = QPen(color, width, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        if len(points) == 1:
            r = width / 2
            painter.setBrush(color)
            painter.drawEllipse(points[0], r, r)
            return

        path = QPainterPath()
        path.moveTo(points[0])

        for i in range(1, len(points) - 1):
            mid = QPointF(
                (points[i].x() + points[i - 1].x()) / 2,
                (points[i].y() + points[i - 1].y()) / 2,
            )
            path.quadTo(points[i - 1], mid)

        path.lineTo(points[-1])
        painter.drawPath(path)


# ── Container that keeps overlay perfectly sized over the tab content ────────

class ContentArea(QWidget):
    """Holds QTabWidget + DrawingOverlay stacked; keeps overlay geometry in sync."""

    def __init__(self, tabs, overlay: DrawingOverlay):
        super().__init__()
        self._tabs = tabs
        self._overlay = overlay
        tabs.setParent(self)
        overlay.setParent(self)
        overlay.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._tabs.setGeometry(0, 0, w, h)
        bar_h = self._tabs.tabBar().height()
        self._overlay.setGeometry(0, bar_h, w, h - bar_h)
        self._overlay.raise_()
