import sys, os
sys.path.insert(0, "d:/tool/omivoice")
os.environ["PYTHONIOENCODING"] = "utf-8"

from test_mini_tool.core.settings_manager import load_settings
load_settings()

print(f"Cookie env: {os.environ.get('YOUTUBE_COOKIE_FILE', '(not set)')}")

from test_mini_tool.services.youtube_downloader import download_youtube_video

url = "https://www.youtube.com/watch?v=EUKbVj2iiSE"
print(f"Downloading: {url}")

try:
    path = download_youtube_video(url)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"\nSUCCESS! File: {path}")
    print(f"Size: {size_mb:.1f} MB")
except Exception as e:
    print(f"\nFAILED: {e}")
