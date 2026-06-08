# Copyright © 2026 Mr. Hassan — https://mrhassan-dev.vercel.app/
# All rights reserved. Unauthorized use or distribution is prohibited.

import os
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QSplitter, QLabel, QMenu
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QUrl


_APP_DIR = os.path.join(os.path.expanduser("~"), ".edu_viewer")
os.makedirs(_APP_DIR, exist_ok=True)
BOOKMARKS_PATH = os.path.join(_APP_DIR, "bookmarks.json")


class WebLinksViewer(QWidget):
    def __init__(self):
        super().__init__()
        self._bookmarks: list[dict] = []
        self._load_bookmarks()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_nav_bar())
        layout.addWidget(self._build_body(), 1)

    # ── Nav bar ───────────────────────────────────────────────────────────────

    def _build_nav_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("webNavBar")
        bar.setFixedHeight(40)
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(6)

        self._btn_back = QPushButton("◀")
        self._btn_back.setFixedWidth(32)
        self._btn_back.setToolTip("Back")
        self._btn_back.clicked.connect(lambda: self._view.back())
        row.addWidget(self._btn_back)

        self._btn_fwd = QPushButton("▶")
        self._btn_fwd.setFixedWidth(32)
        self._btn_fwd.setToolTip("Forward")
        self._btn_fwd.clicked.connect(lambda: self._view.forward())
        row.addWidget(self._btn_fwd)

        btn_reload = QPushButton("↻")
        btn_reload.setFixedWidth(32)
        btn_reload.setToolTip("Reload page")
        btn_reload.clicked.connect(lambda: self._view.reload())
        row.addWidget(btn_reload)

        self._url_bar = QLineEdit()
        self._url_bar.setObjectName("urlBar")
        self._url_bar.setPlaceholderText("Enter URL and press Enter …")
        self._url_bar.returnPressed.connect(self._navigate)
        row.addWidget(self._url_bar, 1)

        btn_go = QPushButton("Go")
        btn_go.setFixedWidth(44)
        btn_go.clicked.connect(self._navigate)
        row.addWidget(btn_go)

        btn_save = QPushButton("Save Bookmark")
        btn_save.setFixedWidth(120)
        btn_save.clicked.connect(self._save_bookmark)
        row.addWidget(btn_save)

        return bar

    # ── Body (bookmark list + web view) ───────────────────────────────────────

    def _build_body(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left.setObjectName("bookmarkPanel")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)
        ll.setSpacing(4)

        lbl = QLabel("BOOKMARKS")
        lbl.setObjectName("sectionLabel")
        lbl.setFixedHeight(22)
        ll.addWidget(lbl)

        self._bm_list = QListWidget()
        self._bm_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._bm_list.customContextMenuRequested.connect(self._bm_context)
        self._bm_list.itemDoubleClicked.connect(self._load_bookmark)
        ll.addWidget(self._bm_list, 1)

        splitter.addWidget(left)

        self._view = QWebEngineView()
        self._view.urlChanged.connect(lambda url: self._url_bar.setText(url.toString()))
        splitter.addWidget(self._view)

        splitter.setSizes([200, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self._refresh_bm_list()
        return splitter

    # ── Navigation ────────────────────────────────────────────────────────────

    def _navigate(self):
        url = self._url_bar.text().strip()
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        self._view.setUrl(QUrl(url))

    # ── Bookmarks ─────────────────────────────────────────────────────────────

    def _save_bookmark(self):
        url = self._url_bar.text().strip()
        if not url or url in ("about:blank", ""):
            return
        title = self._view.title() or url[:60]
        if not any(b["url"] == url for b in self._bookmarks):
            self._bookmarks.append({"label": title, "url": url})
            self._persist()
            self._refresh_bm_list()

    def _load_bookmark(self, item: QListWidgetItem):
        url = item.data(Qt.ItemDataRole.UserRole)
        self._url_bar.setText(url)
        self._view.setUrl(QUrl(url))

    def _bm_context(self, pos):
        item = self._bm_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        act = menu.addAction("Remove Bookmark")
        if menu.exec(self._bm_list.mapToGlobal(pos)) == act:
            url = item.data(Qt.ItemDataRole.UserRole)
            self._bookmarks = [b for b in self._bookmarks if b["url"] != url]
            self._persist()
            self._refresh_bm_list()

    def _refresh_bm_list(self):
        self._bm_list.clear()
        for b in self._bookmarks:
            item = QListWidgetItem(b["label"])
            item.setData(Qt.ItemDataRole.UserRole, b["url"])
            item.setToolTip(b["url"])
            self._bm_list.addItem(item)

    def _load_bookmarks(self):
        if os.path.exists(BOOKMARKS_PATH):
            try:
                with open(BOOKMARKS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._bookmarks = data
            except (json.JSONDecodeError, OSError):
                pass

    def _persist(self):
        try:
            with open(BOOKMARKS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._bookmarks, f, indent=2, ensure_ascii=False)
        except OSError:
            pass
