import sys
import os
import yt_dlp

sys.path.insert(0, 'd:/tool/omivoice/backend')
from backend.services.ffmpeg_utils import find_ffmpeg

ff = find_ffmpeg()
print(f"FFmpeg path: {ff}")

url = "https://www.youtube.com/watch?v=EUKbVj2iiSE"
out_dir = "d:/tool/omivoice/test_mini_tool/cache/test_dl"
os.makedirs(out_dir, exist_ok=True)

outtmpl = os.path.join(out_dir, "%(id)s_%(title).50s.%(ext)s")

ydl_opts = {
    "outtmpl": outtmpl,
    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "merge_output_format": "mp4",
    "quiet": False,
    "ffmpeg_location": ff,
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        print(f"\nDOWNLOAD SUCCESS! File: {filename}")
except Exception as e:
        print(f"\nDOWNLOAD FAILED: {e}")
