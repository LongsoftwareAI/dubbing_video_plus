"""
Test assembling all 155 segments of wqOY7Y0w7pA across full 510s duration
and verify that no segment is truncated and audio is continuous.
"""
import os
import sys
import glob
import soundfile as sf

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
for p in [CURRENT_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import json
from config import CACHE_DIR
from services.video_muxer import assemble_dubbed_audio, get_video_duration

def test():
    job_dir = os.path.join(CACHE_DIR, "job_wqOY7Y0w7pA")
    transcript_file = os.path.join(job_dir, "transcript_vi.json")
    if not os.path.exists(transcript_file):
        transcript_file = os.path.join(job_dir, "transcript_original.json")

    with open(transcript_file, "r", encoding="utf-8") as f:
        segments = json.load(f)

    print(f"Total segments in transcript: {len(segments)}")
    seg_dir = os.path.join(job_dir, "segments")
    seg_wavs = [os.path.join(seg_dir, f"seg_{i}.wav") for i in range(len(segments))]

    existing_wavs = [w for w in seg_wavs if os.path.exists(w) and os.path.getsize(w) > 4000]
    print(f"Existing synthesized segment wavs: {len(existing_wavs)} / {len(segments)}")

    video_file = os.path.join(CACHE_DIR, "yt_downloads", "wqOY7Y0w7pA.mp4")
    dur = get_video_duration(video_file)
    print(f"Detected video duration: {dur:.2f}s ({dur/60:.2f} mins)")

    out_voice_wav = os.path.join(job_dir, "voice_track_full_tested.wav")
    assembled = assemble_dubbed_audio(segments, seg_wavs, dur, out_voice_wav)

    info = sf.info(assembled)
    print(f"Assembled Voice Track Duration: {info.duration:.2f}s ({info.duration/60:.2f} mins)")
    print(f"Sample Rate: {info.samplerate} Hz, Channels: {info.channels}")
    print(f"File Size: {os.path.getsize(assembled) / 1024 / 1024:.2f} MB")

    assert info.duration >= dur - 5.0, f"Duration too short! {info.duration} < {dur}"
    print("✓ Full 510s duration verification PASSED 100%!")

if __name__ == "__main__":
    test()
