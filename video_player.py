from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel, QSizePolicy
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl


def _fmt_ms(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


class VideoPlayer(QWidget):
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
        self._seek.sliderMoved.connect(self._player.setPosition)
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
        self._btn_mute.setToolTip("Mute (TikTok audio safety)")
        self._btn_mute.clicked.connect(self._on_mute)
        row.addWidget(self._btn_mute)

        vbox.addLayout(row)
        return ctrl

    # ── Slots ────────────────────────────────────────────────────────────────

    def load(self, path: str):
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()

    def stop(self):
        self._player.stop()

    def _toggle_play(self):
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_mute(self, checked: bool):
        self._audio.setMuted(checked)
        self._btn_mute.setText("🔇" if checked else "🔊")

    def _on_state(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._btn_play.setText("⏸  Pause" if playing else "▶  Play")

    def _on_position(self, pos: int):
        self._seek.setValue(pos)
        self._time_lbl.setText(f"{_fmt_ms(pos)} / {_fmt_ms(self._player.duration())}")

    def _on_duration(self, dur: int):
        self._seek.setRange(0, dur)
        self._time_lbl.setText(f"{_fmt_ms(self._player.position())} / {_fmt_ms(dur)}")
