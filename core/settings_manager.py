"""
Settings persistence — save/load user preferences and API Keys as JSON.
"""
import os
import json
import logging
from config import SETTINGS_PATH

logger = logging.getLogger("mini_dubber.settings")

_DEFAULTS = {
    "target_lang": "vi",
    "tts_voice": "vi-VN-HoaiMyNeural",
    "tts_engine": "edge-tts",
    "translation_engine": "google",
    "translate_quality": "fast",
    "timing_strategy": "smart_fit",
    "voice_match": "per_line",
    "preserve_bg": True,
    "bg_gain": 0.9,
    "voice_gain": 1.1,
    "dual_subs": False,
    "burn_subs": False,
    "export_video_format": "mp4",
    "export_audio_format": "wav",
    "export_sub_format": "srt",
    "num_speakers": 0,
    "ref_audio_path": "",
    "output_dir": "",
    "whisper_model": "large-v3",
    "demucs_separate": True,
    "auto_clone_character_voice": True,
    # API Keys & Providers
    "deepl_api_key": "",
    "microsoft_api_key": "",
    "translate_base_url": "http://localhost:11434/v1",
    "translate_model": "llama3",
    "translate_api_key": "ollama",
    "hf_token": "",
    "youtube_cookie_file": "",
}

def load_settings() -> dict:
    merged = dict(_DEFAULTS)
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            merged.update(saved)
        except Exception as e:
            logger.warning(f"Failed to load settings: {e}")

    # Set environment variables from loaded settings
    if merged.get("deepl_api_key"):
        os.environ["DEEPL_API_KEY"] = merged["deepl_api_key"]
    if merged.get("microsoft_api_key"):
        os.environ["MICROSOFT_API_KEY"] = merged["microsoft_api_key"]
    if merged.get("translate_base_url"):
        os.environ["TRANSLATE_BASE_URL"] = merged["translate_base_url"]
    if merged.get("translate_model"):
        os.environ["TRANSLATE_MODEL"] = merged["translate_model"]
    if merged.get("translate_api_key"):
        os.environ["TRANSLATE_API_KEY"] = merged["translate_api_key"]
    if merged.get("hf_token"):
        os.environ["HF_TOKEN"] = merged["hf_token"]
    if merged.get("youtube_cookie_file"):
        os.environ["YOUTUBE_COOKIE_FILE"] = merged["youtube_cookie_file"]

    return merged

def save_settings(settings: dict):
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        # Apply to current process env
        if settings.get("deepl_api_key"):
            os.environ["DEEPL_API_KEY"] = settings["deepl_api_key"]
        if settings.get("microsoft_api_key"):
            os.environ["MICROSOFT_API_KEY"] = settings["microsoft_api_key"]
        if settings.get("translate_base_url"):
            os.environ["TRANSLATE_BASE_URL"] = settings["translate_base_url"]
        if settings.get("translate_model"):
            os.environ["TRANSLATE_MODEL"] = settings["translate_model"]
        if settings.get("translate_api_key"):
            os.environ["TRANSLATE_API_KEY"] = settings["translate_api_key"]
        if settings.get("hf_token"):
            os.environ["HF_TOKEN"] = settings["hf_token"]
        if settings.get("youtube_cookie_file"):
            os.environ["YOUTUBE_COOKIE_FILE"] = settings["youtube_cookie_file"]

    except Exception as e:
        logger.warning(f"Failed to save settings: {e}")
