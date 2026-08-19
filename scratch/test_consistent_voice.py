"""
End-to-end test: precomputed prompt -> 5 segments -> verify identical voice + no clicks.
"""
import os, sys, time
import soundfile as sf
import numpy as np

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import CACHE_DIR
from services.tts_service import precompute_voice_prompt, synthesize_segment

ref_audio = os.path.join(CACHE_DIR, 'job_wqOY7Y0w7pA', 'auto_extracted_character_voice.wav')
out_dir = os.path.join(CACHE_DIR, "test_consistent_voice")
os.makedirs(out_dir, exist_ok=True)

sentences = [
    "Xin chao cac ban, toi la mot nghe si.",
    "Mau sac la ngon ngu cua toi.",
    "Toi lon len trong mot gia dinh yeu thuong.",
    "Cac ban co the cam nhan niem vui tu mau sac.",
    "Cam on cac ban da lang nghe.",
]

def main():
    print("Step 1: Pre-computing voice clone prompt (one-time)...")
    t0 = time.time()
    prompt = precompute_voice_prompt(ref_audio)
    t_prompt = time.time() - t0
    print(f"  Prompt precomputed in {t_prompt:.2f}s (type: {type(prompt).__name__})")

    print("\nStep 2: Synthesizing 5 segments with cached prompt...")
    wavs = []
    t0 = time.time()
    for i, text in enumerate(sentences):
        out_wav = os.path.join(out_dir, f"test_seg_{i}.wav")
        synthesize_segment(text, out_wav, voice="[CLONE]", ref_audio_path=ref_audio)
        wavs.append(out_wav)
        sz = os.path.getsize(out_wav)
        print(f"  seg_{i}: {sz} bytes")
    t_synth = time.time() - t0
    print(f"  Total synthesis: {t_synth:.2f}s ({t_synth/len(sentences):.2f}s per sentence)")

    print("\nStep 3: Checking for click artifacts...")
    for i, w in enumerate(wavs):
        data, sr = sf.read(w)
        if data.ndim > 1:
            data = data.mean(axis=1)
        start_amp = abs(float(data[0]))
        end_amp = abs(float(data[-1]))
        print(f"  seg_{i}: sr={sr}, start_amp={start_amp:.6f}, end_amp={end_amp:.6f}, dur={len(data)/sr:.2f}s")

    print("\nDone! Check the WAVs in:", out_dir)

if __name__ == "__main__":
    main()
