"""
Test assembly with OmniVoice's atempo retiming + 15ms de-clicking fade ramps.
"""
import os, sys, json, glob
import soundfile as sf
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import CACHE_DIR
from services.video_muxer import assemble_dubbed_audio, get_video_duration

JOB_DIR = os.path.join(CACHE_DIR, "job_wqOY7Y0w7pA")
TRANSCRIPT_PATH = os.path.join(JOB_DIR, "transcript_vi.json")
SEG_DIR = os.path.join(JOB_DIR, "segments")
OUTPUT_WAV = os.path.join(JOB_DIR, "test_assembled_omnivoice_standard.wav")

def main():
    if not os.path.exists(TRANSCRIPT_PATH):
        print(f"Error: {TRANSCRIPT_PATH} not found")
        return

    with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
        segments = json.load(f)

    seg_wavs = [os.path.join(SEG_DIR, f"seg_{i}.wav") for i in range(len(segments))]
    total_dur = float(segments[-1].get("end", 510.0)) + 3.0

    print(f"Assembling {len(segments)} segments into master track...")
    out = assemble_dubbed_audio(segments, seg_wavs, total_dur, OUTPUT_WAV)
    print(f"Assembled track created: {out}")

    # Check for clicks and amplitude discontinuities
    data, sr = sf.read(OUTPUT_WAV)
    if data.ndim > 1:
        data = data.mean(axis=1)

    print(f"Track sr={sr}, duration={len(data)/sr:.2f}s, samples={len(data)}")
    diff = np.abs(np.diff(data))
    big_jumps = np.where(diff > 0.15)[0]
    print(f"Large amplitude jumps (>0.15): {len(big_jumps)}")
    
    # Check max peak
    max_peak = np.max(np.abs(data))
    print(f"Max peak amplitude: {max_peak:.4f} (target: ~0.90, safe from clipping)")

if __name__ == "__main__":
    main()
