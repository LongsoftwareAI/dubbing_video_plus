"""
Check amplitude transitions at segment boundaries (where clicks/pops occur).
"""
import os, sys, json
import soundfile as sf
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from test_mini_tool.config import CACHE_DIR

JOB_DIR = os.path.join(CACHE_DIR, "job_wqOY7Y0w7pA")
TRANSCRIPT_PATH = os.path.join(JOB_DIR, "transcript_vi.json")
OUTPUT_WAV = os.path.join(JOB_DIR, "test_assembled_omnivoice_standard.wav")

def main():
    with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
        segments = json.load(f)

    data, sr = sf.read(OUTPUT_WAV)
    if data.ndim > 1:
        data = data.mean(axis=1)

    boundary_clicks = 0
    for i, seg in enumerate(segments):
        start_s = float(seg.get("start", 0.0))
        start_idx = int(start_s * sr)

        # Check sample right before start vs at start
        if start_idx > 0 and start_idx < len(data):
            diff = abs(data[start_idx] - data[start_idx - 1])
            if diff > 0.05:
                print(f"Seg {i} start at {start_s:.2f}s has jump: {diff:.4f}")
                boundary_clicks += 1

    print(f"Total boundary clicks (|diff| > 0.05 at segment start): {boundary_clicks}/{len(segments)}")

if __name__ == "__main__":
    main()
