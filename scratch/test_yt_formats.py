import sys
import os
import yt_dlp

sys.path.insert(0, 'd:/tool/omivoice/backend')
from backend.services.ffmpeg_utils import find_ffmpeg

ff = find_ffmpeg()
print(f"FFmpeg path: {ff}")

url = "https://www.youtube.com/watch?v=EUKbVj2iiSE"

# Check available formats
ydl_opts = {
    "quiet": False,
    "ffmpeg_location": ff,
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        print(f"\nTotal formats available: {len(formats)}")
        for f in formats:
            print(f"ID: {f.get('format_id'):10s} EXT: {f.get('ext'):6s} RES: {str(f.get('resolution')):12s} VCODEC: {str(f.get('vcodec')):15s} ACODEC: {str(f.get('acodec')):15s}")
except Exception as e:
    print(f"\nExtract info failed: {e}")
