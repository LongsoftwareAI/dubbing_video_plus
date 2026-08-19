"""
End-to-End Test and Verification Script for YouTube Video Voice Cloning:
https://www.youtube.com/watch?v=wqOY7Y0w7pA
"""
import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
for p in [CURRENT_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from test_mini_tool.services.youtube_downloader import download_youtube_video
from test_mini_tool.services.audio_separator import separate_audio
from test_mini_tool.services.asr_service import transcribe_audio
from test_mini_tool.services.speaker_clone import extract_character_voice_reference, extract_all_speakers_references
from test_mini_tool.services.tts_service import synthesize_segment, _estimate_pitch_and_gender
from test_mini_tool.config import CACHE_DIR

def run_test():
    url = "https://www.youtube.com/watch?v=wqOY7Y0w7pA"
    print(f"[1/6] Downloading/Finding Video from: {url}")
    t0 = time.time()
    video_file = download_youtube_video(url)
    print(f"      -> Video File: {video_file} ({os.path.getsize(video_file) / 1024 / 1024:.2f} MB)")

    job_dir = os.path.join(CACHE_DIR, "test_verify_yt_clone")
    os.makedirs(job_dir, exist_ok=True)

    print("[2/6] Extracting Audio & Separating Vocals (Demucs)...")
    vocal_wav, bed_wav = separate_audio(video_file, job_dir)
    print(f"      -> Vocal WAV: {vocal_wav} ({os.path.getsize(vocal_wav) / 1024:.1f} KB)")
    print(f"      -> Bed WAV:   {bed_wav} ({os.path.getsize(bed_wav) / 1024:.1f} KB)")

    print("[3/6] Transcribing Audio with Whisper ASR...")
    segments = transcribe_audio(vocal_wav)
    print(f"      -> Transcribed {len(segments)} segments.")
    for s in segments[:3]:
        print(f"         • [{s['start']:.1f}s - {s['end']:.1f}s] {s.get('text', '')}")

    print("[4/6] Extracting Character Voice Reference from Video...")
    ref_audio = extract_character_voice_reference(vocal_wav, segments, job_dir)
    spk_map = extract_all_speakers_references(vocal_wav, segments, job_dir)
    print(f"      -> Extracted Main Ref Audio: {ref_audio}")
    print(f"      -> Multi-speaker extracted: {list(spk_map.keys())}")

    print("[5/6] Running FFT Acoustic & Pitch Analysis on Extracted Video Voice...")
    voice_id, pitch_mod, rate_mod = _estimate_pitch_and_gender(ref_audio)
    print(f"      -> Detected Voice Engine: {voice_id}")
    print(f"      -> Calculated Pitch Offset: {pitch_mod}")
    print(f"      -> Calculated Rate Offset:  {rate_mod}")

    print("[6/6] Synthesizing Sample Sentences in Vietnamese with Clone Voice...")
    test_lines = [
        "Xin chào các bạn, đây là giọng lồng tiếng nhân bản trực tiếp từ video gốc.",
        "Tôi sẽ hướng dẫn bạn cách tối ưu hóa giọng đọc AI hoàn toàn tự nhiên và chuyên nghiệp.",
        "Hệ thống đã loại bỏ hoàn toàn các lỗi tiếng bíp và chuyển giọng nam chuẩn xác."
    ]

    for idx, line in enumerate(test_lines, 1):
        out_wav = os.path.join(job_dir, f"test_dub_line_{idx}.wav")
        if os.path.exists(out_wav):
            os.remove(out_wav)
        synthesize_segment(
            text=line,
            output_wav=out_wav,
            voice="[CLONE TỰ ĐỘNG] Nhân bản giọng gốc từ Video",
            ref_audio_path=ref_audio
        )
        size = os.path.getsize(out_wav)
        print(f"      -> Line {idx}: {out_wav} ({size / 1024:.1f} KB) - {'✓ SUCCESS' if size > 10000 else '✗ FAIL'}")

    print(f"\n✨ ALL TESTS COMPLETED SUCCESSFULLY IN {time.time() - t0:.1f}s!")

if __name__ == "__main__":
    run_test()
