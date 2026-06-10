# Copyright © 2026 Mr. Hassan — https://mrhassan-dev.vercel.app/
# All rights reserved. Unauthorized use or distribution is prohibited.

import sys
import os
import json
import math  # used by animation tick


def resource_path(rel: str) -> str:
    """Resolve a bundled-asset path for both dev and PyInstaller --onefile."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QLineEdit,
    QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QTabWidget, QFileDialog, QMenu, QSplitter, QColorDialog,
    QGraphicsDropShadowEffect, QMessageBox, QListView, QTreeView,
    QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence, QColor, QIcon

from scanner import scan_folder, IMAGE_EXT, VIDEO_EXT

_SESSION_PATH = os.path.join(os.path.expanduser("~"), ".edu_viewer", "session.json")
from image_viewer import ImageViewer
from video_player import VideoPlayer
from pdf_viewer import PDFViewer
from overlay import DrawingOverlay, ContentArea
from web_links import WebLinksViewer


# ── Pen color presets ────────────────────────────────────────────────────────

_COLORS = [
    ("#ff4444", "Red"),
    ("#ffdd44", "Yellow"),
    ("#ffffff", "White"),
    ("#44aaff", "Blue"),
    ("#44ff88", "Green"),
]

_WIDTHS = [("S", 2), ("M", 4), ("L", 8)]


def _media_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXT: return "images"
    if ext in VIDEO_EXT: return "videos"
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


def _search_box(placeholder: str) -> QLineEdit:
    le = QLineEdit()
    le.setPlaceholderText(placeholder)
    le.setFixedHeight(22)
    le.setStyleSheet(
        "background: #050714; color: #5868a0; border: 1px solid #0e1630;"
        "border-radius: 3px; padding: 1px 6px; font-size: 11px;"
    )
    le.setClearButtonEnabled(True)
    return le


class _ScanWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, path: str, recursive: bool):
        super().__init__()
        self._path = path
        self._recursive = recursive

    def run(self):
        self.finished.emit(scan_folder(self._path, recursive=self._recursive))


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
        self._current_filter_folder: str = ""
        self._scan_worker: _ScanWorker | None = None
        self._last_folder: str = ""

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_header())

        body = QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_content())
        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)
        body.setSizes([250, 1030])
        root_layout.addWidget(body, 1)

        root_layout.addWidget(self._build_toolbar())

        self._setup_shortcuts()
        self._start_animations()

        # Connect viewer signals
        self._img_view.load_error.connect(self._status_bar.setText)
        self._vid_view.playback_finished.connect(self._on_video_finished)

        self._restore_session()

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
        btn_folder.setObjectName("btnChooseFolder")
        btn_folder.setFixedHeight(34)
        btn_folder.clicked.connect(self._on_choose_folder)
        layout.addWidget(btn_folder)

        # Recursive toggle row
        rec_row = QHBoxLayout()
        rec_row.setSpacing(4)
        self._btn_recursive = QPushButton("Recursive: ON")
        self._btn_recursive.setObjectName("btnRecursive")
        self._btn_recursive.setCheckable(True)
        self._btn_recursive.setChecked(True)
        self._btn_recursive.setFixedHeight(22)
        self._btn_recursive.setStyleSheet("")
        self._btn_recursive.setToolTip(
            "ON = scan all subfolders\nOFF = only files directly in chosen folder"
        )
        self._btn_recursive.clicked.connect(self._toggle_recursive)
        rec_row.addWidget(self._btn_recursive)
        rec_row.addStretch()
        layout.addLayout(rec_row)

        self._folder_tree = QTreeWidget()
        self._folder_tree.setObjectName("folderTree")
        self._folder_tree.setHeaderHidden(True)
        self._folder_tree.setIndentation(14)
        self._folder_tree.setMaximumHeight(160)
        self._folder_tree.setVisible(False)
        self._folder_tree.itemClicked.connect(self._on_tree_selection)
        layout.addWidget(self._folder_tree)

        self._folder_label = QLabel("No folder selected")
        self._folder_label.setStyleSheet("color: #384068; font-size: 11px;")
        self._folder_label.setWordWrap(True)
        layout.addWidget(self._folder_label)

        layout.addSpacing(6)

        self._img_section = _section_label("IMAGES (0)")
        layout.addWidget(self._img_section)
        self._img_search = _search_box("Filter images…")
        self._img_search.textChanged.connect(lambda t: self._filter_list(self._img_list, t))
        layout.addWidget(self._img_search)
        self._img_list = _make_list(self._on_media_context)
        self._img_list.setMaximumHeight(120)
        self._img_list.itemDoubleClicked.connect(lambda item: self._preview_item(item, "images"))
        layout.addWidget(self._img_list)

        self._vid_section = _section_label("VIDEOS (0)")
        layout.addWidget(self._vid_section)
        self._vid_search = _search_box("Filter videos…")
        self._vid_search.textChanged.connect(lambda t: self._filter_list(self._vid_list, t))
        layout.addWidget(self._vid_search)
        self._vid_list = _make_list(self._on_media_context)
        self._vid_list.setMaximumHeight(120)
        self._vid_list.itemDoubleClicked.connect(lambda item: self._preview_item(item, "videos"))
        layout.addWidget(self._vid_list)

        self._pdf_section = _section_label("PDFs (0)")
        layout.addWidget(self._pdf_section)
        self._pdf_search = _search_box("Filter PDFs…")
        self._pdf_search.textChanged.connect(lambda t: self._filter_list(self._pdf_list, t))
        layout.addWidget(self._pdf_search)
        self._pdf_list = _make_list(self._on_media_context)
        self._pdf_list.setMaximumHeight(120)
        self._pdf_list.itemDoubleClicked.connect(lambda item: self._preview_item(item, "pdfs"))
        layout.addWidget(self._pdf_list)

        layout.addSpacing(6)
        layout.addWidget(_section_label("STREAM QUEUE"))

        self._queue_list = _make_list(self._on_queue_context)
        self._queue_list.itemDoubleClicked.connect(self._on_queue_double_click)
        self._queue_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._queue_list.model().rowsMoved.connect(self._on_queue_reordered)
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

        btn_save_q = QPushButton("Save")
        btn_save_q.setFixedHeight(26)
        btn_save_q.setToolTip("Save queue to file")
        btn_save_q.clicked.connect(self._save_queue)
        nav_row.addWidget(btn_save_q)

        btn_load_q = QPushButton("Load")
        btn_load_q.setFixedHeight(26)
        btn_load_q.setToolTip("Load queue from file")
        btn_load_q.clicked.connect(self._load_queue)
        nav_row.addWidget(btn_load_q)

        layout.addLayout(nav_row)

        return sidebar

    # ── Content Area (tabs + overlay) ─────────────────────────────────────────

    def _build_content(self) -> QWidget:
        self._tabs = QTabWidget()

        self._img_view = ImageViewer()
        self._vid_view = VideoPlayer()
        self._pdf_view = PDFViewer()
        self._web_view = WebLinksViewer()

        self._tabs.addTab(self._img_view, "Images")
        self._tabs.addTab(self._vid_view, "Videos")
        self._tabs.addTab(self._pdf_view, "PDFs")
        self._tabs.addTab(self._web_view, "Web Links")
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

        # Eraser (shown when pen is ON)
        self._btn_eraser = QPushButton("⬜ Eraser")
        self._btn_eraser.setCheckable(True)
        self._btn_eraser.setToolTip("Erase drawn strokes")
        self._btn_eraser.setVisible(False)
        self._btn_eraser.clicked.connect(self._toggle_eraser)
        layout.addWidget(self._btn_eraser)

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
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self._overlay.redo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(self._overlay.redo)
        # Image navigation: Ctrl+Left/Right to avoid conflicts with video/PDF arrows
        QShortcut(QKeySequence("Ctrl+Left"),  self).activated.connect(lambda: self._navigate_image(-1))
        QShortcut(QKeySequence("Ctrl+Right"), self).activated.connect(lambda: self._navigate_image(1))

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_choose_folder(self):
        dlg = QFileDialog(self, "Select Media Folder")
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)

        for view in (dlg.findChild(QListView, "listView"),
                     dlg.findChild(QTreeView, "treeView")):
            if view:
                view.setFocus()
                break

        if dlg.exec() != QFileDialog.DialogCode.Accepted:
            return
        selected = dlg.selectedFiles()
        if not selected or not selected[0]:
            return

        folder = os.path.normpath(selected[0])
        self._last_folder = folder
        mode = "recursive" if self._recursive else "top-level only"
        self._folder_label.setText(f"{os.path.basename(folder)}  [{mode}]")
        self._folder_label.setToolTip(folder)
        self._status_bar.setText(f"Scanning: {folder} …")

        # Cancel any previous scan still running
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.finished.disconnect()
            self._scan_worker.quit()

        self._scan_worker = _ScanWorker(folder, self._recursive)
        self._scan_worker.finished.connect(self._on_scan_done)
        self._scan_worker.start()

    def _on_scan_done(self, result: dict):
        self._scan_result = result
        self._current_filter_folder = ""
        self._build_folder_tree(result)

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

    def _populate_list(self, lw: QListWidget, entries: list[tuple[str, str]], folder_filter: str = ""):
        lw.setUpdatesEnabled(False)
        lw.clear()
        for full, rel in entries:
            if folder_filter:
                norm_rel = os.path.normpath(rel)
                norm_filter = os.path.normpath(folder_filter)
                if not norm_rel.startswith(norm_filter + os.sep):
                    continue
            label = rel if rel != os.path.basename(rel) else os.path.basename(rel)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, full)
            item.setToolTip(full)
            lw.addItem(item)
        lw.setUpdatesEnabled(True)

    @staticmethod
    def _filter_list(lw: QListWidget, text: str):
        text = text.lower()
        for i in range(lw.count()):
            item = lw.item(i)
            item.setHidden(bool(text) and text not in item.text().lower())

    def _build_folder_tree(self, scan_result: dict):
        self._folder_tree.clear()
        folders: set[str] = set()
        for entries in scan_result.values():
            for _full, rel in entries:
                parts = os.path.normpath(rel).split(os.sep)
                for depth in range(1, len(parts)):
                    folders.add(os.sep.join(parts[:depth]))
        if not folders:
            self._folder_tree.setVisible(False)
            return
        root_item = QTreeWidgetItem(self._folder_tree, ["All Files"])
        root_item.setData(0, Qt.ItemDataRole.UserRole, "")
        node_map: dict[str, QTreeWidgetItem] = {}
        for folder in sorted(folders):
            parts = folder.split(os.sep)
            parent = root_item
            for depth, part in enumerate(parts):
                key = os.sep.join(parts[:depth + 1])
                if key not in node_map:
                    child = QTreeWidgetItem(parent, [part])
                    child.setData(0, Qt.ItemDataRole.UserRole, key)
                    node_map[key] = child
                parent = node_map[key]
        self._folder_tree.expandAll()
        self._folder_tree.setCurrentItem(root_item)
        self._folder_tree.setVisible(True)

    def _on_tree_selection(self, item: QTreeWidgetItem, _col: int):
        folder_filter = item.data(0, Qt.ItemDataRole.UserRole)
        self._current_filter_folder = folder_filter
        result = self._scan_result
        self._populate_list(self._img_list, result["images"], folder_filter)
        self._populate_list(self._vid_list, result["videos"], folder_filter)
        self._populate_list(self._pdf_list, result["pdfs"], folder_filter)
        self._img_section.setText(f"IMAGES ({self._img_list.count()})")
        self._vid_section.setText(f"VIDEOS ({self._vid_list.count()})")
        self._pdf_section.setText(f"PDFs ({self._pdf_list.count()})")

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

    def _navigate_image(self, delta: int):
        if self._tabs.currentIndex() != 0:
            return
        current = self._img_list.currentRow()
        count = self._img_list.count()
        if count == 0:
            return
        next_row = max(0, min(count - 1, current + delta))
        self._img_list.setCurrentRow(next_row)
        self._preview_item(self._img_list.currentItem(), "images")

    def _on_tab_changed(self, index: int):
        if index != 1:
            self._vid_view.stop()

    def _on_video_finished(self):
        if self._queue_index >= 0 and self._queue_index < len(self._playlist) - 1:
            self._queue_next()

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
            if row < self._queue_index:
                self._queue_index -= 1
            elif row == self._queue_index:
                self._queue_index = -1
            self._renumber_queue()

    def _on_queue_reordered(self, *_args):
        self._playlist = [
            self._queue_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._queue_list.count())
        ]
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

    def _save_queue(self):
        if not self._playlist:
            self._status_bar.setText("Queue is empty — nothing to save")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Queue", "", "Playlist files (*.txt);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self._playlist))
            self._status_bar.setText(f"Queue saved: {os.path.basename(path)}")
        except OSError as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    def _load_queue(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Queue", "", "Playlist files (*.txt);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                paths = [ln.strip() for ln in f if ln.strip()]
            added = 0
            for p in paths:
                if os.path.exists(p):
                    self._add_to_queue(p)
                    added += 1
            self._status_bar.setText(f"Loaded {added} items from queue file")
        except OSError as exc:
            QMessageBox.critical(self, "Load Error", str(exc))

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

    # ── Pen / Eraser controls ─────────────────────────────────────────────────

    def _toggle_recursive(self, checked: bool):
        self._recursive = checked
        self._btn_recursive.setText("Recursive: ON" if checked else "Recursive: OFF")

    def _toggle_pen(self, checked: bool):
        self._overlay.set_active(checked)
        self._btn_pen.setText("✏  Pen: ON" if checked else "✏  Pen: OFF")
        self._btn_eraser.setVisible(checked)
        if not checked:
            self._btn_eraser.setChecked(False)
            self._overlay.set_eraser(False)
        for w in self._color_widgets:
            w.setVisible(checked)
        self._status_bar.setText(
            "Pen ON — draw freely; Ctrl+Z undo, Ctrl+Y redo, Ctrl+L clear" if checked else "Pen OFF"
        )

    def _toggle_eraser(self, checked: bool):
        self._overlay.set_eraser(checked)
        self._btn_eraser.setText("⬜ Eraser: ON" if checked else "⬜ Eraser")
        self._status_bar.setText("Eraser ON — drag to erase" if checked else "Pen mode")

    def _set_pen_color(self, color: QColor):
        self._overlay.set_color(color)
        self._btn_eraser.setChecked(False)
        self._overlay.set_eraser(False)
        self._btn_eraser.setText("⬜ Eraser")
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

    # ── Session persistence ───────────────────────────────────────────────────

    def _save_session(self):
        data = {
            "folder": self._last_folder,
            "recursive": self._recursive,
            "tab": self._tabs.currentIndex(),
            "queue": list(self._playlist),
        }
        try:
            os.makedirs(os.path.dirname(_SESSION_PATH), exist_ok=True)
            with open(_SESSION_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _restore_session(self):
        if not os.path.exists(_SESSION_PATH):
            return
        try:
            with open(_SESSION_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        recursive = data.get("recursive", True)
        self._recursive = recursive
        self._btn_recursive.setChecked(recursive)
        self._btn_recursive.setText("Recursive: ON" if recursive else "Recursive: OFF")

        tab = data.get("tab", 0)
        if 0 <= tab < self._tabs.count():
            self._tabs.setCurrentIndex(tab)

        for path in data.get("queue", []):
            if os.path.exists(path):
                self._add_to_queue(path)

        folder = data.get("folder", "")
        if folder and os.path.isdir(folder):
            self._last_folder = folder
            mode = "recursive" if recursive else "top-level only"
            self._folder_label.setText(f"{os.path.basename(folder)}  [{mode}]")
            self._folder_label.setToolTip(folder)
            self._status_bar.setText(f"Restoring: {folder} …")
            self._scan_worker = _ScanWorker(folder, recursive)
            self._scan_worker.finished.connect(self._on_scan_done)
            self._scan_worker.start()

    def closeEvent(self, event):
        self._save_session()
        self._anim_timer.stop()
        self._vid_view.stop()
        super().closeEvent(event)

    # ── Animations ────────────────────────────────────────────────────────────

    def _start_animations(self):
        self._live_glow = QGraphicsDropShadowEffect()
        self._live_glow.setBlurRadius(14)
        self._live_glow.setColor(QColor(233, 69, 96, 200))
        self._live_glow.setOffset(0, 0)
        self._live_dot.setGraphicsEffect(self._live_glow)

        self._anim_phase = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_animations)
        self._anim_timer.start(40)

    def _tick_animations(self):
        self._anim_phase = (self._anim_phase + 0.13) % (2 * math.pi)
        t = (math.sin(self._anim_phase) + 1) / 2

        r = int(233 + t * 22)
        g = int(69  + t * 50)
        b = int(96  + t * 40)
        self._live_dot.setStyleSheet(
            f"color: rgb({r},{g},{b}); font-weight: bold; font-size: 13px;"
        )
        self._live_glow.setBlurRadius(6 + t * 16)
        self._live_glow.setColor(QColor(r, g, b, int(140 + t * 115)))


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Educational Media Viewer")
    app.setWindowIcon(QIcon(resource_path("icon.ico")))

    qss_path = resource_path("style.qss")
    if os.path.exists(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        except OSError as exc:
            print(f"Warning: could not load stylesheet: {exc}")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
