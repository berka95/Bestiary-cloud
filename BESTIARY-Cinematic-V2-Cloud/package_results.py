"""Copy deliverables without provider response files or intermediate media."""
import os
import shutil
from pathlib import Path

SOURCE = Path(os.environ["BESTIARY_OUTPUT"])
DOWNLOAD = Path("mobile-download")
EPISODE_FILES = ("episode.json", "storyboard.md", "research.json")
LANG_FILES = ("cover.jpg", "subtitles.srt", "upload.txt", "upload.json", "timeline.json", "qa.json")
EXPORTS = {"en":"YouTube_Shorts_EN.mp4","id":"Facebook_Reels_ID.mp4"}

for episode in SOURCE.glob("*/episode.json"):
    source = episode.parent
    target = DOWNLOAD / source.name
    for name in EPISODE_FILES:
        item = source / name
        if item.is_file():
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target / name)
    for lang, filename in EXPORTS.items():
        if not (source / lang / filename).is_file():
            continue
        (target / lang).mkdir(parents=True, exist_ok=True)
        for name in (*LANG_FILES, filename):
            shutil.copy2(source / lang / name, target / lang / name)
