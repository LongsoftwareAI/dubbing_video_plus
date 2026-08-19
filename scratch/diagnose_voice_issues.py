"""Deep diagnostic of the two-voice + click/pitch issues."""
import os, sys, glob, json
import soundfile as sf
import numpy as np

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from test_mini_tool.config import CACHE_DIR

SEG_DIR = os.path.join(CACHE_DIR, "job_wqOY7Y0w7pA", "segments")

def main():
    wavs = sorted(glob.glob(os.path.join(SEG_DIR, "seg_*.wav")),
                  key=lambda w: int(os.path.basename(w).split("_")[1].split(".")[0]))
    print(f"Total segment WAVs: {len(wavs)}")

    sr_set = set()
    click_candidates = []

    for i, w in enumerate(wavs):
        data, sr = sf.read(w)
        if data.ndim > 1:
            data = data.mean(axis=1)
        sr_set.add(sr)

        # Check for clicks: large discontinuity at start or end
        if len(data) > 100:
            start_jump = abs(float(data[0]))
            end_jump = abs(float(data[-1]))
            if start_jump > 0.05 or end_jump > 0.05:
                click_candidates.append((i, start_jump, end_jump, sr, len(data)/sr))

    print(f"Sample rates found: {sr_set}")
    print(f"Segments with potential click (|start|>0.05 or |end|>0.05): {len(click_candidates)}")
    for idx, sj, ej, sr, dur in click_candidates[:8]:
        print(f"  seg_{idx}.wav: start_amp={sj:.4f}, end_amp={ej:.4f}, sr={sr}, dur={dur:.2f}s")

    # Check assembled voice track
    assembled = os.path.join(CACHE_DIR, "job_wqOY7Y0w7pA", "assembled_voice_track.wav")
    if os.path.exists(assembled):
        data, sr = sf.read(assembled)
        if data.ndim > 1:
            data = data.mean(axis=1)
        print(f"\nAssembled track: sr={sr}, duration={len(data)/sr:.2f}s, samples={len(data)}")

        # Find abrupt jumps in assembled track (potential clicks)
        diff = np.abs(np.diff(data))
        big_jumps = np.where(diff > 0.15)[0]
        print(f"Large amplitude jumps (>0.15) in assembled track: {len(big_jumps)}")
        if len(big_jumps) > 0:
            for j in big_jumps[:10]:
                t = j / sr
                print(f"  Jump at sample {j} (t={t:.3f}s): delta={diff[j]:.4f}, val_before={data[j]:.4f}, val_after={data[j+1]:.4f}")

    # Load transcript to check speaker labels
    transcript = os.path.join(CACHE_DIR, "job_wqOY7Y0w7pA", "transcript_vi.json")
    if os.path.exists(transcript):
        with open(transcript, "r", encoding="utf-8") as f:
            segs = json.load(f)
        speakers = {}
        for s in segs:
            spk = s.get("speaker", "SPEAKER_00")
            speakers[spk] = speakers.get(spk, 0) + 1
        print(f"\nSpeaker distribution: {speakers}")
        print(f"Distinct speakers: {len(speakers)}")

if __name__ == "__main__":
    main()
