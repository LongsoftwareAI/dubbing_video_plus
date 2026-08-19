"""Quick integration test: Demucs separation + EdgeTTS synthesis."""
import sys, os
sys.path.insert(0, "d:/tool/omivoice")

from test_mini_tool.config import CACHE_DIR
import threading

test_dir = os.path.join(CACHE_DIR, "integration_test")
os.makedirs(test_dir, exist_ok=True)

# Use the previously downloaded YouTube video
test_video = os.path.join(CACHE_DIR, "yt_downloads", "EUKbVj2iiSE.mp4")
if not os.path.exists(test_video):
    # Find any mp4 in yt_downloads
    dl_dir = os.path.join(CACHE_DIR, "yt_downloads")
    for f in os.listdir(dl_dir):
        if f.endswith(".mp4"):
            test_video = os.path.join(dl_dir, f)
            break

print(f"Test video: {test_video}")
print(f"Exists: {os.path.exists(test_video)}")

# Test 1: Demucs separation
print("\n=== Test 1: Audio Separation (Demucs) ===")
from test_mini_tool.services.audio_separator import separate_audio
try:
    vocal, bed = separate_audio(test_video, test_dir)
    print(f"Vocal: {vocal} (exists={os.path.exists(vocal)}, size={os.path.getsize(vocal) if os.path.exists(vocal) else 0})")
    print(f"Bed:   {bed} (exists={os.path.exists(bed)}, size={os.path.getsize(bed) if os.path.exists(bed) else 0})")
    print("Demucs: OK" if vocal != bed else "Demucs: FALLBACK (same file)")
except Exception as e:
    print(f"Demucs: FAILED - {e}")

# Test 2: EdgeTTS from a thread (simulating Tkinter worker thread)
print("\n=== Test 2: EdgeTTS from Thread ===")
from test_mini_tool.services.tts_service import synthesize_segment

result = [None, None]

def tts_thread():
    try:
        out = os.path.join(test_dir, "tts_test.wav")
        synthesize_segment(
            text="Xin chao, day la thu nghiem giong noi.",
            output_wav=out,
            voice="vi-VN-HoaiMyNeural",
            engine="edge-tts"
        )
        size = os.path.getsize(out) if os.path.exists(out) else 0
        result[0] = out
        result[1] = size
    except Exception as e:
        result[0] = f"FAILED: {e}"

t = threading.Thread(target=tts_thread)
t.start()
t.join(timeout=30)

if result[1] and result[1] > 100:
    print(f"EdgeTTS from thread: OK (file={result[0]}, size={result[1]} bytes)")
else:
    print(f"EdgeTTS from thread: FAILED ({result[0]})")
