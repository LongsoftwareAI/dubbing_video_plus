"""
Video thumbnail frame extractor using FFmpeg for UI video preview cards.
"""
import os
import subprocess
import logging
from config import CACHE_DIR, FFMPEG_PATH

logger = logging.getLogger("mini_dubber.thumbnail")

def extract_video_thumbnail(video_path: str, timestamp_sec: float = 2.0) -> str:
    """
    Extracts a JPEG snapshot frame from video_path at timestamp_sec.
    Returns path to the generated preview thumbnail image file.
    """
    if not os.path.exists(video_path):
        return ""

    filename = os.path.splitext(os.path.basename(video_path))[0]
    out_jpg = os.path.join(CACHE_DIR, f"thumb_{filename}.jpg")

    cmd = [
        FFMPEG_PATH, "-y",
        "-ss", str(timestamp_sec),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        out_jpg
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(out_jpg):
            return out_jpg
    except Exception as e:
        logger.warning(f"Thumbnail extraction failed: {e}")

    return ""

def play_media_file(media_path: str):
    """Plays audio or video file smoothly without player startup/shutdown pops."""
    if not media_path or not os.path.exists(media_path):
        return
    try:
        if os.name == "nt":
            if media_path.lower().endswith(".wav"):
                import winsound
                winsound.PlaySound(media_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                os.startfile(media_path)
        else:
            subprocess.Popen(["xdg-open", media_path])
    except Exception as e:
        logger.error(f"Failed to play media file: {e}")
