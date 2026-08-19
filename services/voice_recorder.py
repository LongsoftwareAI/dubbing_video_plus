"""
In-App Microphone Voice Recording Service for Voice Cloning.
Records clean 24kHz Mono WAV audio directly from user's microphone.
"""
import os
import time
import threading
import logging
import soundfile as sf
import numpy as np

from config import CACHE_DIR

logger = logging.getLogger("mini_dubber.recorder")

_RECORDING = False
_RECORDED_FRAMES = []
_RECORD_STREAM = None


def start_recording(callback_status=None):
    """Starts recording audio from default input microphone in background thread."""
    global _RECORDING, _RECORDED_FRAMES, _RECORD_STREAM
    if _RECORDING:
        return

    try:
        import sounddevice as sd
    except ImportError:
        if callback_status:
            callback_status(False, "Chưa cài đặt thư viện sounddevice.")
        return

    _RECORDED_FRAMES = []
    _RECORDING = True

    sample_rate = 24000
    channels = 1

    def _audio_callback(indata, frames, time_info, status):
        if _RECORDING:
            _RECORDED_FRAMES.append(indata.copy())

    try:
        _RECORD_STREAM = sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            callback=_audio_callback
        )
        _RECORD_STREAM.start()
        logger.info("Microphone recording started.")
        if callback_status:
            callback_status(True, "Đang thu âm qua Micro...")
    except Exception as e:
        _RECORDING = False
        logger.error(f"Failed to start recording: {e}")
        if callback_status:
            callback_status(False, f"Lỗi thu âm: {e}")


def stop_recording(output_wav_path: str = None) -> str:
    """Stops recording and saves captured audio to 24kHz Mono WAV."""
    global _RECORDING, _RECORDED_FRAMES, _RECORD_STREAM
    if not _RECORDING and not _RECORDED_FRAMES:
        return ""

    _RECORDING = False
    if _RECORD_STREAM:
        try:
            _RECORD_STREAM.stop()
            _RECORD_STREAM.close()
        except Exception:
            pass
        _RECORD_STREAM = None

    if not _RECORDED_FRAMES:
        return ""

    if not output_wav_path:
        os.makedirs(CACHE_DIR, exist_ok=True)
        output_wav_path = os.path.join(CACHE_DIR, f"mic_rec_{int(time.time())}.wav")

    audio_data = np.concatenate(_RECORDED_FRAMES, axis=0)

    # Normalize audio volume
    max_val = np.abs(audio_data).max()
    if max_val > 0:
        audio_data = audio_data / max_val * 0.95

    sf.write(output_wav_path, audio_data, 24000)
    logger.info(f"Saved mic recording to: {output_wav_path} (len: {len(audio_data)/24000:.2f}s)")
    return output_wav_path


def is_recording() -> bool:
    return _RECORDING
