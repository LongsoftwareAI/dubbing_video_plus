"""
Test OmniVoice bed_mix_filter string with FFmpeg.
"""
import sys, os
sys.path.insert(0, "d:/tool/omivoice")
from test_mini_tool.config import FFMPEG_PATH
import subprocess

ff = FFMPEG_PATH
print(f"Testing FFmpeg amix normalize support with: {ff}")

cmd = [ff, "-hide_banner", "-h", "filter=amix"]
res = subprocess.run(cmd, capture_output=True, text=True)
has_norm = "normalize" in res.stdout
print(f"amix normalize=0 supported: {has_norm}")
