# Copyright © 2026 Mr. Hassan — https://mrhassan-dev.vercel.app/
# All rights reserved. Unauthorized use or distribution is prohibited.

import sys
import os
import math


def resource_path(rel: str) -> str:
    """Resolve a bundled-asset path for both dev and PyInstaller --onefile."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QTabWidget, QFileDialog, QMenu, QSplitter, QColorDialog,
    QGraphicsDropShadowEffect, QMessageBox, QListView, QTreeView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence, QColor, QIcon

from scanner import scan_folder
from image_viewer import ImageViewer
from video_player import VideoPlayer
from pdf_viewer import PDFViewer
from overlay import DrawingOverlay, ContentArea


# ── Pen color presets ────────────────────────────────────────────────────────

_COLORS = [
    ("#ff4444", "Red"),
    ("#ffdd44", "Yellow"),
    ("#ffffff", "White"),
    ("#44aaff", "Blue"),
    ("#44ff88", "Green"),
]

_WIDTHS = [("S", 2), ("M", 4), ("L", 8)]

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_VIDEO_EXT = {".mp4", ".mkv", ".mov", ".avi"}


def _media_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in _IMAGE_EXT: return "images"
    if ext in _VIDEO_EXT: return "videos"
    return "pdfs"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("sectionLabel")
    lbl.setFixedHeight(22)
    return lbl


def _make_list(context_menu_cb=None) -> QListWidget:
    lw = QListWidget()
    lw.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
    lw.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    if context_menu_cb:
        lw.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        lw.customContextMenuRequested.connect(context_menu_cb)
    return lw


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Educational Media Viewer — Stream Dashboard")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.resize(1280, 780)
        self.setMinimumSize(900, 600)

        self._scan_result: dict[str, list[tuple[str, str]]] = {
            "images": [], "videos": [], "pdfs": []
        }
        self._playlist: list[str] = []
        self._queue_index: int = -1
        self._recursive: bool = True

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_header())

        body = QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_content())   # sets self._overlay, self._tabs
        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)
        body.setSizes([250, 1030])
        root_layout.addWidget(body, 1)

        root_layout.addWidget(self._build_toolbar())  # uses self._overlay

        self._setup_shortcuts()
        self._start_animations()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(50)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel("  EDUCATIONAL DASHBOARD  —  LIVE STREAMING MODE")
        title.setObjectName("headerLabel")
        layout.addWidget(title)
        layout.addStretch()

        version = QLabel("Safe Content  |  v1.0")
        version.setObjectName("versionLabel")
        layout.addWidget(version)

        self._live_dot = QLabel("● LIVE")
        self._live_dot.setStyleSheet("color: #e94560; font-weight: bold; font-size: 13px;")
        layout.addWidget(self._live_dot)

        return header

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        btn_folder = QPushButton("  Choose Folder")
        btn_folder.setFixedHeight(34)
        btn_folder.clicked.connect(self._on_choose_folder)
        layout.addWidget(btn_folder)

        # Recursive toggle row
        rec_row = QHBoxLayout()
        rec_row.setSpacing(4)
        self._btn_recursive = QPushButton("Recursive: ON")
        self._btn_recursive.setCheckable(True)
        self._btn_recursive.setChecked(True)
        self._btn_recursive.setFixedHeight(22)
        self._btn_recursive.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        self._btn_recursive.setToolTip(
            "ON = scan all subfolders\nOFF = only files directly in chosen folder"
        )
        self._btn_recursive.clicked.connect(self._toggle_recursive)
        rec_row.addWidget(self._btn_recursive)
        rec_row.addStretch()
        layout.addLayout(rec_row)

        self._folder_label = QLabel("No folder selected")
        self._folder_label.setStyleSheet("color: #384068; font-size: 11px;")
        self._folder_label.setWordWrap(True)
        layout.addWidget(self._folder_label)

        layout.addSpacing(6)

        self._img_section = _section_label("IMAGES (0)")
        layout.addWidget(self._img_section)
        self._img_list = _make_list(self._on_media_context)
        self._img_list.setMaximumHeight(140)
        self._img_list.itemDoubleClicked.connect(lambda item: self._preview_item(item, "images"))
        layout.addWidget(self._img_list)

        self._vid_section = _section_label("VIDEOS (0)")
        layout.addWidget(self._vid_section)
        self._vid_list = _make_list(self._on_media_context)
        self._vid_list.setMaximumHeight(140)
        self._vid_list.itemDoubleClicked.connect(lambda item: self._preview_item(item, "videos"))
        layout.addWidget(self._vid_list)

        self._pdf_section = _section_label("PDFs (0)")
        layout.addWidget(self._pdf_section)
        self._pdf_list = _make_list(self._on_media_context)
        self._pdf_list.setMaximumHeight(140)
        self._pdf_list.itemDoubleClicked.connect(lambda item: self._preview_item(item, "pdfs"))
        layout.addWidget(self._pdf_list)

        layout.addSpacing(6)
        layout.addWidget(_section_label("STREAM QUEUE"))

        self._queue_list = _make_list(self._on_queue_context)
        self._queue_list.itemDoubleClicked.connect(self._on_queue_double_click)
        layout.addWidget(self._queue_list, 1)

        # Queue navigation row
        nav_row = QHBoxLayout()
        nav_row.setSpacing(4)

        self._btn_q_prev = QPushButton("◀")
        self._btn_q_prev.setFixedHeight(26)
        self._btn_q_prev.setToolTip("Play previous item in queue")
        self._btn_q_prev.clicked.connect(self._queue_prev)
        nav_row.addWidget(self._btn_q_prev)

        self._btn_q_next = QPushButton("▶")
        self._btn_q_next.setFixedHeight(26)
        self._btn_q_next.setToolTip("Play next item in queue")
        self._btn_q_next.clicked.connect(self._queue_next)
        nav_row.addWidget(self._btn_q_next)

        btn_clear_queue = QPushButton("Clear")
        btn_clear_queue.setFixedHeight(26)
        btn_clear_queue.clicked.connect(self._clear_queue)
        nav_row.addWidget(btn_clear_queue)

        layout.addLayout(nav_row)

        return sidebar

    # ── Content Area (tabs + overlay) ─────────────────────────────────────────

    def _build_content(self) -> QWidget:
        self._tabs = QTabWidget()

        self._img_view = ImageViewer()
        self._vid_view = VideoPlayer()
        self._pdf_view = PDFViewer()

        self._tabs.addTab(self._img_view, "Images")
        self._tabs.addTab(self._vid_view, "Videos")
        self._tabs.addTab(self._pdf_view, "PDFs")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        self._overlay = DrawingOverlay()
        return ContentArea(self._tabs, self._overlay)

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("toolbar")
        bar.setFixedHeight(42)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(6)

        # Pen toggle
        self._btn_pen = QPushButton("✏  Pen: OFF")
        self._btn_pen.setCheckable(True)
        self._btn_pen.setToolTip("Toggle drawing overlay  (draws on Images & PDFs)")
        self._btn_pen.clicked.connect(self._toggle_pen)
        layout.addWidget(self._btn_pen)

        # Color swatches (shown only when pen is ON)
        self._color_widgets: list[QWidget] = []

        for hex_color, name in _COLORS:
            btn = QPushButton()
            btn.setFixedSize(20, 20)
            btn.setToolTip(name)
            btn.setStyleSheet(
                f"background-color:{hex_color}; border:2px solid #333355; border-radius:10px;"
            )
            btn.clicked.connect(lambda _=False, c=hex_color: self._set_pen_color(QColor(c)))
            btn.setVisible(False)
            layout.addWidget(btn)
            self._color_widgets.append(btn)

        # Custom color picker
        self._btn_custom_color = QPushButton("…")
        self._btn_custom_color.setFixedSize(24, 24)
        self._btn_custom_color.setToolTip("Pick custom color")
        self._btn_custom_color.setVisible(False)
        self._btn_custom_color.clicked.connect(self._pick_custom_color)
        layout.addWidget(self._btn_custom_color)
        self._color_widgets.append(self._btn_custom_color)

        # Width buttons
        self._width_btns: list[QPushButton] = []
        for label, px in _WIDTHS:
            btn = QPushButton(label)
            btn.setFixedSize(24, 24)
            btn.setToolTip(f"{px}px stroke width")
            btn.setCheckable(True)
            btn.setVisible(False)
            btn.clicked.connect(lambda _=False, w=px, b=btn: self._set_pen_width(w, b))
            layout.addWidget(btn)
            self._color_widgets.append(btn)
            self._width_btns.append(btn)

        # Select medium width as default
        if self._width_btns:
            self._width_btns[1].setChecked(True)

        # Clear / Undo
        self._btn_clear = QPushButton("Clear  Ctrl+L")
        self._btn_clear.setToolTip("Erase all drawings")
        self._btn_clear.clicked.connect(self._clear_canvas)
        layout.addWidget(self._btn_clear)

        layout.addStretch()

        self._status_bar = QLabel("Ready — choose a folder to begin scanning")
        self._status_bar.setStyleSheet("color: #666688; font-size: 11px;")
        layout.addWidget(self._status_bar)

        return bar

    # ── Shortcuts ─────────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self._clear_canvas)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._on_choose_folder)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self._overlay.undo)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_choose_folder(self):
        dlg = QFileDialog(self, "Select Media Folder")
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)

        # Force keyboard focus onto the folder list so typing jumps to matching names
        for view in (dlg.findChild(QListView, "listView"),
                     dlg.findChild(QTreeView, "treeView")):
            if view:
                view.setFocus()
                break

        if dlg.exec() != QFileDialog.DialogCode.Accepted:
            return
        selected = dlg.selectedFiles()
        if not selected:
            return
        folder = selected[0]
        if not folder:
            return
        try:
            folder = os.path.normpath(folder)
            mode = "recursive" if self._recursive else "top-level only"
            self._folder_label.setText(f"{os.path.basename(folder)}  [{mode}]")
            self._folder_label.setToolTip(folder)
            self._status_bar.setText(f"Scanning: {folder} …")
            QApplication.processEvents()

            result = scan_folder(folder, recursive=self._recursive)
            self._scan_result = result

            self._populate_list(self._img_list, result["images"])
            self._populate_list(self._vid_list, result["videos"])
            self._populate_list(self._pdf_list, result["pdfs"])

            self._img_section.setText(f"IMAGES ({len(result['images'])})")
            self._vid_section.setText(f"VIDEOS ({len(result['videos'])})")
            self._pdf_section.setText(f"PDFs ({len(result['pdfs'])})")

            total = sum(len(v) for v in result.values())
            self._status_bar.setText(
                f"Scan complete — {total} files  "
                f"({len(result['images'])} img  {len(result['videos'])} vid  {len(result['pdfs'])} pdf)"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Scan Error", str(exc))

    def _populate_list(self, lw: QListWidget, entries: list[tuple[str, str]]):
        """Fill a list widget. entries = [(full_path, rel_path), ...]"""
        lw.clear()
        for full, rel in entries:
            # Show relative path so the user knows WHERE the file lives
            label = rel if rel != os.path.basename(rel) else os.path.basename(rel)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, full)
            item.setToolTip(full)
            lw.addItem(item)

    def _preview_item(self, item: QListWidgetItem, media_type: str):
        tab_index = {"images": 0, "videos": 1, "pdfs": 2}[media_type]
        path = item.data(Qt.ItemDataRole.UserRole)
        self._tabs.setCurrentIndex(tab_index)
        if media_type == "images":
            self._img_view.load(path)
        elif media_type == "videos":
            self._vid_view.load(path)
        elif media_type == "pdfs":
            self._pdf_view.load(path)
        self._status_bar.setText(f"Loaded: {os.path.basename(path)}")

    def _on_tab_changed(self, index: int):
        if index != 1:
            self._vid_view.stop()

    def _on_media_context(self, pos):
        sender: QListWidget = self.sender()
        item = sender.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        action_add = menu.addAction("Add to Stream Queue")
        action = menu.exec(sender.mapToGlobal(pos))
        if action == action_add:
            self._add_to_queue(item.data(Qt.ItemDataRole.UserRole))

    def _add_to_queue(self, path: str):
        if path in self._playlist:
            return
        self._playlist.append(path)
        mtype = _media_type(path)
        badge = "[IMG]" if mtype == "images" else "[VID]" if mtype == "videos" else "[PDF]"
        item = QListWidgetItem(f"{len(self._playlist)}. {badge} {os.path.basename(path)}")
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        self._queue_list.addItem(item)

    def _on_queue_context(self, pos):
        item = self._queue_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        action_remove = menu.addAction("Remove from Queue")
        action = menu.exec(self._queue_list.mapToGlobal(pos))
        if action == action_remove:
            row = self._queue_list.row(item)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path in self._playlist:
                self._playlist.remove(path)
            self._queue_list.takeItem(row)
            # Keep _queue_index pointing at the same logical item after removal
            if row < self._queue_index:
                self._queue_index -= 1
            elif row == self._queue_index:
                self._queue_index = -1
            self._renumber_queue()

    def _renumber_queue(self):
        for i in range(self._queue_list.count()):
            item = self._queue_list.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            mtype = _media_type(path)
            badge = "[IMG]" if mtype == "images" else "[VID]" if mtype == "videos" else "[PDF]"
            item.setText(f"{i+1}. {badge} {os.path.basename(path)}")

    def _clear_queue(self):
        self._queue_list.clear()
        self._playlist.clear()
        self._queue_index = -1

    def _on_queue_double_click(self, item: QListWidgetItem):
        row = self._queue_list.row(item)
        self._play_queue_at(row)

    def _queue_next(self):
        if not self._playlist:
            return
        self._play_queue_at(self._queue_index + 1)

    def _queue_prev(self):
        if not self._playlist:
            return
        self._play_queue_at(self._queue_index - 1)

    def _play_queue_at(self, index: int):
        if not self._playlist:
            return
        index = max(0, min(index, len(self._playlist) - 1))
        self._queue_index = index

        # Highlight current row
        self._queue_list.setCurrentRow(index)

        path = self._playlist[index]
        mtype = _media_type(path)
        if mtype == "images":
            self._tabs.setCurrentIndex(0)
            self._img_view.load(path)
        elif mtype == "videos":
            self._tabs.setCurrentIndex(1)
            self._vid_view.load(path)
        else:
            self._tabs.setCurrentIndex(2)
            self._pdf_view.load(path)

        self._status_bar.setText(
            f"Queue [{index + 1}/{len(self._playlist)}]: {os.path.basename(path)}"
        )

    # ── Pen controls ──────────────────────────────────────────────────────────

    def _toggle_recursive(self, checked: bool):
        self._recursive = checked
        self._btn_recursive.setText("Recursive: ON" if checked else "Recursive: OFF")

    def _toggle_pen(self, checked: bool):
        self._overlay.set_active(checked)
        self._btn_pen.setText("✏  Pen: ON" if checked else "✏  Pen: OFF")
        for w in self._color_widgets:
            w.setVisible(checked)
        self._status_bar.setText(
            "Pen ON — draw freely; Ctrl+Z to undo, Ctrl+L to clear" if checked else "Pen OFF"
        )

    def _set_pen_color(self, color: QColor):
        self._overlay.set_color(color)
        self._status_bar.setText(f"Pen color: {color.name()}")

    def _pick_custom_color(self):
        color = QColorDialog.getColor(parent=self, title="Choose Pen Color")
        if color.isValid():
            self._set_pen_color(color)

    def _set_pen_width(self, px: int, active_btn: QPushButton):
        self._overlay.set_width(px)
        for btn in self._width_btns:
            btn.setChecked(btn is active_btn)
        self._status_bar.setText(f"Pen width: {px}px")

    def _clear_canvas(self):
        self._overlay.clear()
        self._status_bar.setText("Canvas cleared")

    def closeEvent(self, event):
        self._anim_timer.stop()
        self._vid_view.stop()
        super().closeEvent(event)

    # ── Animations ────────────────────────────────────────────────────────────

    def _start_animations(self):
        # Drop-shadow glow on the LIVE dot (real pixel glow, not just color)
        self._live_glow = QGraphicsDropShadowEffect()
        self._live_glow.setBlurRadius(14)
        self._live_glow.setColor(QColor(233, 69, 96, 200))
        self._live_glow.setOffset(0, 0)
        self._live_dot.setGraphicsEffect(self._live_glow)

        self._anim_phase = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_animations)
        self._anim_timer.start(40)  # ~25 fps — smooth but light on CPU

    def _tick_animations(self):
        self._anim_phase = (self._anim_phase + 0.13) % (2 * math.pi)
        t = (math.sin(self._anim_phase) + 1) / 2  # 0 → 1 → 0

        # Pulse LIVE dot: dark red → bright pink
        r = int(233 + t * 22)          # 233 – 255
        g = int(69  + t * 50)          # 69  – 119
        b = int(96  + t * 40)          # 96  – 136
        self._live_dot.setStyleSheet(
            f"color: rgb({r},{g},{b}); font-weight: bold; font-size: 13px;"
        )

        # Pulse the glow blur radius: 6 → 22 px
        self._live_glow.setBlurRadius(6 + t * 16)
        self._live_glow.setColor(QColor(r, g, b, int(140 + t * 115)))


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Educational Media Viewer")
    app.setWindowIcon(QIcon(resource_path("icon.ico")))

    qss_path = resource_path("style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
