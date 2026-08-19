import sys, os
sys.path.insert(0, "d:/tool/omivoice")
from test_mini_tool.core.settings_manager import load_settings
load_settings()

cookie_path = os.environ.get("YOUTUBE_COOKIE_FILE", "")
print(f"Cookie file: {cookie_path}")
print(f"Cookie exists: {os.path.exists(cookie_path) if cookie_path else 'N/A'}")

# Show cookie content type
if cookie_path and os.path.exists(cookie_path):
    with open(cookie_path, "r", encoding="utf-8") as f:
        first_lines = f.readlines()[:5]
    print("Cookie file first 5 lines:")
    for line in first_lines:
        print(f"  {line.rstrip()}")

import yt_dlp
from test_mini_tool.config import FFMPEG_PATH

url = "https://www.youtube.com/watch?v=EUKbVj2iiSE"

# Test WITH cookie
opts = {
    "quiet": False,
    "ffmpeg_location": FFMPEG_PATH,
    "restrictfilenames": True,
}
if cookie_path and os.path.exists(cookie_path):
    opts["cookiefile"] = cookie_path

print(f"\n=== Listing formats WITH cookie ===")
try:
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        print(f"Total formats: {len(formats)}")
        for f in formats:
            vcodec = str(f.get("vcodec", "none"))
            acodec = str(f.get("acodec", "none"))
            ext = f.get("ext", "?")
            res = str(f.get("resolution", "?"))
            fid = f.get("format_id", "?")
            print(f"  {fid:10s} ext={ext:6s} res={res:12s} vcodec={vcodec:20s} acodec={acodec:15s}")
except Exception as e:
    print(f"FAILED: {e}")
