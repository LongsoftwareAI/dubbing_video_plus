import os, sys, time
import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import FFMPEG_PATH
import subprocess

def _atempo_chain(ratio: float) -> str:
    stages = []
    remaining = ratio
    while remaining > 2.0:
        stages.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        stages.append("atempo=0.5")
        remaining /= 0.5
    stages.append(f"atempo={remaining:.6f}")
    return ",".join(stages)

def pitch_preserving_stretch(data: np.ndarray, target_samples: int, sr: int = 24000) -> np.ndarray:
    wl = len(data)
    if target_samples <= 0 or wl == target_samples:
        return data
    ratio = wl / target_samples
    filter_str = _atempo_chain(ratio)

    arr = data.astype(np.float32, copy=False)
    proc = subprocess.Popen(
        [
            FFMPEG_PATH, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "pipe:0",
            "-af", filter_str,
            "-f", "f32le", "-ar", str(sr), "-ac", "1", "pipe:1"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate(input=arr.tobytes())
    if proc.returncode == 0 and stdout:
        out_arr = np.frombuffer(stdout, dtype=np.float32)
        if len(out_arr) < target_samples:
            pad = np.zeros(target_samples - len(out_arr), dtype=np.float32)
            return np.concatenate([out_arr, pad])
        return out_arr[:target_samples]
    indices = np.linspace(0, wl - 1, target_samples)
    return np.interp(indices, np.arange(wl), data).astype(np.float32)

def main():
    sr = 24000
    t = np.linspace(0, 2.0, int(2.0 * sr), endpoint=False)
    test_audio = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    target_samples = int(1.5 * sr)

    t0 = time.perf_counter()
    stretched = pitch_preserving_stretch(test_audio, target_samples, sr)
    elapsed = (time.perf_counter() - t0) * 1000

    print(f"Original len: {len(test_audio)}, Target: {target_samples}, Output: {len(stretched)}")
    print(f"Time taken: {elapsed:.2f}ms")
    print(f"Output range: min={stretched.min():.4f}, max={stretched.max():.4f}")

if __name__ == "__main__":
    main()
