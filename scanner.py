# Copyright © 2026 Mr. Hassan — https://mrhassan-dev.vercel.app/
# All rights reserved. Unauthorized use or distribution is prohibited.

import os

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_EXT = {".mp4", ".mkv", ".mov", ".avi"}
PDF_EXT   = {".pdf"}


def scan_folder(path: str, recursive: bool = True) -> dict:
    """
    Scan *path* for media files.

    Returns a dict where each value is a list of (full_path, rel_path) tuples
    so the caller can display a meaningful relative label while keeping the
    absolute path for loading.

    recursive=False: only the immediate children of *path* (no subdirs).
    """
    result: dict[str, list[tuple[str, str]]] = {
        "images": [], "videos": [], "pdfs": []
    }

    if not os.path.isdir(path):
        return result

    _SKIP_NAMES = {"thumbs.db", "desktop.ini", ".ds_store", "ehthumbs.db"}

    if recursive:
        walk_iter = os.walk(path, followlinks=False)
    else:
        # Yield only the root directory, no subdirs
        try:
            entries = os.listdir(path)
        except PermissionError:
            return result
        walk_iter = [(path, [], entries)]

    for root, _dirs, files in walk_iter:
        for name in files:
            if name.startswith(".") or name.lower() in _SKIP_NAMES:
                continue
            ext = os.path.splitext(name)[1].lower()
            full = os.path.join(root, name)
            rel  = os.path.relpath(full, path)   # e.g. "subfolder\img.png" or "img.png"
            if ext in IMAGE_EXT:
                result["images"].append((full, rel))
            elif ext in VIDEO_EXT:
                result["videos"].append((full, rel))
            elif ext in PDF_EXT:
                result["pdfs"].append((full, rel))

    for key in result:
        result[key].sort(key=lambda t: t[1].lower())

    return result
