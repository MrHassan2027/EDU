# EduMediaViewer

A desktop media viewer for educators and live-streamers. Scan a folder and browse all your images, videos, PDFs, and websites — all in one dark-themed window.

![Screenshot](screenshot.png)

---

## Features

| Feature | Details |
|---------|---------|
| **Image Viewer** | Pan, zoom (scroll wheel), rotate left/right, fit to window |
| **Video Player** | Play/pause, seek bar, speed control (0.25× – 2×), volume slider, mute |
| **PDF Viewer** | Page navigation, zoom in/out, click the page number to jump to any page |
| **Web Browser** | Browse websites inside the app — no external browser needed. Save bookmarks |
| **Folder Scanner** | Recursive or single-level scan. Nested folder tree for quick filtering |
| **Search** | Filter images, videos, or PDFs by filename instantly |
| **Drawing Overlay** | Draw over any content with pen or eraser. Choose color and stroke size. Undo/redo |
| **Stream Queue** | Queue files for a presentation. Drag to reorder. Auto-plays the next video |

---

## Download

**[⬇ Download EduMediaViewer\_v1.0.0.zip](https://github.com/MrHassan2027/EDU/releases/tag/v1.0.0)**

Windows — no Python installation needed.

1. Download and extract the zip
2. Open the `EduMediaViewer` folder
3. Run `EduMediaViewer.exe`

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+O` | Open folder |
| `Ctrl+Z` | Undo drawing |
| `Ctrl+Y` | Redo drawing |
| `Ctrl+L` | Clear canvas |
| `Space` | Play / Pause video |
| `← →` | Seek video ±5 s &nbsp;/&nbsp; PDF previous/next page |
| `↑ ↓` | Volume up / down |
| `Ctrl+← →` | Previous / next image in list |
| `Ctrl++` / `Ctrl+-` | Zoom PDF in / out |

---

## Run from Source

```bash
pip install -r requirements.txt
python main.py
```

Requires **Python 3.10+** on Windows.

---

## License

Copyright © 2026 **Mr. Hassan** — [mrhassan-dev.vercel.app](https://mrhassan-dev.vercel.app/)

All rights reserved. Unauthorized use or distribution is prohibited.
