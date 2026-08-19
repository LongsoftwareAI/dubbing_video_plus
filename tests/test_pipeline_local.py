"""
Local tests for test_mini_tool video dubbing pipeline.
"""
import os
import unittest
import numpy as np
import soundfile as sf

from test_mini_tool.config import DETECTED_HF_CACHE, CACHE_DIR
from test_mini_tool.core.model_loader import get_system_status
from test_mini_tool.services.translation_service import translate_text, translate_segments
from test_mini_tool.services.tts_service import synthesize_segment
from test_mini_tool.services.video_muxer import assemble_dubbed_audio

class TestMiniDubber(unittest.TestCase):
    def test_system_status(self):
        status = get_system_status()
        self.assertIn("cuda", status)
        self.assertIn("hf_cache", status)
        self.assertTrue(os.path.exists(status["hf_cache"]))

    def test_translation(self):
        segs = [{"id": 0, "start": 0.0, "end": 2.0, "text": "Hello world", "speaker": "SPEAKER_00"}]
        res = translate_segments(segs, target_lang="vi", engine="google")
        self.assertEqual(len(res), 1)
        self.assertIn("text", res[0])

    def test_tts_and_assembly(self):
        out_wav = os.path.join(CACHE_DIR, "test_seg_0.wav")
        synthesize_segment("Xin chào thế giới", out_wav, voice="vi-VN-HoaiMyNeural", engine="edge-tts")
        self.assertTrue(os.path.exists(out_wav))

        segs = [{"id": 0, "start": 0.0, "end": 2.0, "text": "Xin chào thế giới"}]
        voice_track = os.path.join(CACHE_DIR, "test_voice_full.wav")
        assemble_dubbed_audio(segs, [out_wav], total_duration=3.0, output_voice_wav=voice_track)
        self.assertTrue(os.path.exists(voice_track))

if __name__ == "__main__":
    unittest.main()
