"""
Model detection and life-cycle manager for test_mini_tool.
Directly inspects and reuses downloaded models and voice profiles from OmniVoice.
"""
import os
import sys
import logging
from config import DETECTED_HF_CACHE, OMNIVOICE_HF_CACHE

logger = logging.getLogger("mini_dubber.model_loader")

def get_system_status() -> dict:
    """Returns GPU status, detected cache path, and available AI modules."""
    cuda_available = False
    gpu_name = "CPU Only"
    
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    # Check installed backend engines
    has_whisper = False
    try:
        import faster_whisper
        has_whisper = True
    except Exception:
        try:
            import whisper
            has_whisper = True
        except Exception:
            pass

    has_edge_tts = False
    try:
        import edge_tts
        has_edge_tts = True
    except Exception:
        pass

    has_demucs = False
    try:
        import demucs
        has_demucs = True
    except Exception:
        pass

    has_ytdlp = False
    try:
        import yt_dlp
        has_ytdlp = True
    except Exception:
        pass

    # Check cached model folders
    cached_models = []
    if os.path.exists(DETECTED_HF_CACHE):
        for item in os.listdir(DETECTED_HF_CACHE):
            if item.startswith("models--"):
                cached_models.append(item.replace("models--", "").replace("--", "/"))

    # Scan OmniVoice saved custom voice profiles
    voices_dir = os.path.join(os.environ.get("APPDATA", ""), "OmniVoice", "voices")
    custom_voices = []
    if os.path.exists(voices_dir):
        for root, _, files in os.walk(voices_dir):
            for file in files:
                if file.endswith((".wav", ".mp3", ".flac", ".ogg", ".m4a")):
                    custom_voices.append(os.path.join(root, file))

    return {
        "cuda": cuda_available,
        "gpu_name": gpu_name,
        "hf_cache": DETECTED_HF_CACHE,
        "is_omnivoice_cache": os.path.exists(OMNIVOICE_HF_CACHE),
        "has_whisper": has_whisper,
        "has_edge_tts": has_edge_tts,
        "has_demucs": has_demucs,
        "has_ytdlp": has_ytdlp,
        "cached_models": cached_models,
        "custom_voices": custom_voices
    }
