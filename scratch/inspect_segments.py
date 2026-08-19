import os
import sys
import json

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
for p in [CURRENT_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from test_mini_tool.config import CACHE_DIR
from test_mini_tool.services.tts_service import synthesize_segment

def main():
    transcript_file = os.path.join(CACHE_DIR, 'job_wqOY7Y0w7pA', 'transcript_vi.json')
    with open(transcript_file, 'r', encoding='utf-8') as f:
        segs = json.load(f)

    print(f"Total segments: {len(segs)}")
    for i in range(28, min(36, len(segs))):
        s = segs[i]
        print(f"Seg {i}: [{s.get('start')}s - {s.get('end')}s] -> text: '{s.get('text')}' (orig: '{s.get('text_original')}')")

    # Test synthesizing seg 31
    test_wav = os.path.join(CACHE_DIR, "test_seg_31.wav")
    ref_audio = os.path.join(CACHE_DIR, 'job_wqOY7Y0w7pA', 'auto_extracted_character_voice.wav')
    print(f"\nSynthesizing Seg 31...")
    synthesize_segment(segs[31].get('text', ''), test_wav, voice="[CLONE TỰ ĐỘNG]", ref_audio_path=ref_audio)
    print(f"Seg 31 synthesized successfully! Size: {os.path.getsize(test_wav)} bytes")

if __name__ == "__main__":
    main()
