# Copyright © 2026 Mr. Hassan — https://mrhassan-dev.vercel.app/
# All rights reserved. Unauthorized use or distribution is prohibited.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel, QComboBox
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence


def _fmt_ms(ms: int) -> str:
    s = ms // 1000
    h, remainder = divmod(s, 3600)
    m, s = divmod(remainder, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


_SPEEDS = [0.25, 0.5, 1.0, 1.5, 2.0]


class VideoPlayer(QWidget):
    playback_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet("background: #04060f;")
        layout.addWidget(self._video_widget, 1)

        self._player = QMediaPlayer()
        self._audio = QAudioOutput()
        self._audio.setVolume(0.8)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video_widget)

        layout.addWidget(self._build_controls())

        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.playbackStateChanged.connect(self._on_state)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(self._on_player_error)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(250)
        self._poll_timer.timeout.connect(self._poll_position)

        # Keyboard shortcuts (WidgetWithChildrenShortcut = only fire when this widget is focused)
        for key, fn in [
            (Qt.Key.Key_Space,  self._toggle_play),
            (Qt.Key.Key_Left,   lambda: self._seek_by(-5000)),
            (Qt.Key.Key_Right,  lambda: self._seek_by(5000)),
            (Qt.Key.Key_Up,     self._vol_up),
            (Qt.Key.Key_Down,   self._vol_down),
        ]:
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(fn)

    def _build_controls(self) -> QWidget:
        ctrl = QWidget()
        ctrl.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #0c1020, stop:1 #07091a);"
            "border-top: 1px solid #141c38;"
        )
        ctrl.setFixedHeight(72)
        vbox = QVBoxLayout(ctrl)
        vbox.setContentsMargins(10, 6, 10, 6)
        vbox.setSpacing(4)

        # Seek bar
        self._seek = QSlider(Qt.Orientation.Horizontal)
        self._seek.setRange(0, 0)
        self._seek.sliderMoved.connect(self._on_seek_moved)
        vbox.addWidget(self._seek)

        # Button row
        row = QHBoxLayout()
        row.setSpacing(8)

        self._btn_play = QPushButton("▶  Play")
        self._btn_play.setFixedWidth(100)
        self._btn_play.clicked.connect(self._toggle_play)
        row.addWidget(self._btn_play)

        self._time_lbl = QLabel("0:00 / 0:00")
        self._time_lbl.setStyleSheet("color: #888888; font-size: 12px;")
        row.addWidget(self._time_lbl)

        row.addStretch()

        # Speed control
        speed_lbl = QLabel("Speed:")
        speed_lbl.setStyleSheet("color: #888888;")
        row.addWidget(speed_lbl)

        self._speed_box = QComboBox()
        self._speed_box.addItems(["0.25×", "0.5×", "1×", "1.5×", "2×"])
        self._speed_box.setCurrentIndex(2)
        self._speed_box.setFixedWidth(64)
        self._speed_box.setToolTip("Playback speed  (keyboard: no shortcut)")
        self._speed_box.currentIndexChanged.connect(self._on_speed_changed)
        row.addWidget(self._speed_box)

        mute_lbl = QLabel("Vol:")
        mute_lbl.setStyleSheet("color: #888888;")
        row.addWidget(mute_lbl)

        self._vol = QSlider(Qt.Orientation.Horizontal)
        self._vol.setRange(0, 100)
        self._vol.setValue(80)
        self._vol.setFixedWidth(90)
        self._vol.valueChanged.connect(lambda v: self._audio.setVolume(v / 100.0))
        row.addWidget(self._vol)

        self._btn_mute = QPushButton("🔊")
        self._btn_mute.setCheckable(True)
        self._btn_mute.setFixedWidth(36)
        self._btn_mute.setToolTip("Mute / Unmute")
        self._btn_mute.clicked.connect(self._on_mute)
        row.addWidget(self._btn_mute)

        vbox.addLayout(row)
        return ctrl

    # ── Slots ────────────────────────────────────────────────────────────────

    def load(self, path: str):
        if self._btn_mute.isChecked():
            self._btn_mute.setChecked(False)
            self._btn_mute.setText("🔊")
            self._audio.setMuted(False)
        self._speed_box.setCurrentIndex(2)  # reset to 1×
        self._player.setPlaybackRate(1.0)
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()

    def stop(self):
        self._poll_timer.stop()
        self._player.stop()
        self._btn_play.setText("▶  Play")
        self._time_lbl.setText("0:00 / 0:00")
        self._seek.setValue(0)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _toggle_play(self):
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _seek_by(self, ms: int):
        dur = self._player.duration()
        pos = max(0, min(dur, self._player.position() + ms))
        self._player.setPosition(pos)
        self._time_lbl.setText(f"{_fmt_ms(pos)} / {_fmt_ms(dur)}")

    def _vol_up(self):
        self._vol.setValue(min(100, self._vol.value() + 10))

    def _vol_down(self):
        self._vol.setValue(max(0, self._vol.value() - 10))

    def _on_speed_changed(self, index: int):
        self._player.setPlaybackRate(_SPEEDS[index])

    def _on_mute(self, checked: bool):
        self._audio.setMuted(checked)
        self._btn_mute.setText("🔇" if checked else "🔊")

    def _on_state(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._btn_play.setText("⏸  Pause" if playing else "▶  Play")
        if playing:
            self._poll_timer.start()
        else:
            self._poll_timer.stop()

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.playback_finished.emit()

    def _on_player_error(self, _error, error_string: str):
        self._poll_timer.stop()
        self._time_lbl.setText(f"Error: {error_string[:50]}")

    def _on_position(self, pos: int):
        self._seek.blockSignals(True)
        self._seek.setValue(pos)
        self._seek.blockSignals(False)
        self._time_lbl.setText(f"{_fmt_ms(pos)} / {_fmt_ms(self._player.duration())}")

    def _on_duration(self, dur: int):
        self._seek.setRange(0, dur)
        self._time_lbl.setText(f"{_fmt_ms(self._player.position())} / {_fmt_ms(dur)}")

    def _poll_position(self):
        dur = self._player.duration()
        if dur > 0:
            pos = self._player.position()
            self._seek.blockSignals(True)
            self._seek.setValue(pos)
            self._seek.blockSignals(False)
            self._time_lbl.setText(f"{_fmt_ms(pos)} / {_fmt_ms(dur)}")

    def _on_seek_moved(self, pos: int):
        self._player.setPosition(pos)
        self._time_lbl.setText(f"{_fmt_ms(pos)} / {_fmt_ms(self._player.duration())}")
