"""
Configuration, path resolution, and model detection for test_mini_tool.
100% Standalone & Independent: Runs cleanly even if OmniVoice is completely deleted.
"""
import os
import sys
import shutil

# Ensure test_mini_tool directory is always in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)

for p in [CURRENT_DIR, PARENT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Standalone App Data and Cache directories (inside local test_mini_tool/workspace)
APP_NAME = "DubbingVideoPlus"
APP_DISPLAY_NAME = "Dubbing Video Plus+"
DATA_DIR = os.path.join(CURRENT_DIR, "workspace")
OUTPUT_DIR = os.path.join(DATA_DIR, "outputs")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
DOWNLOADS_DIR = os.path.join(DATA_DIR, "downloads")
STANDALONE_HF_CACHE = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME, "hf_cache")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
PROJECTS_INDEX = os.path.join(DATA_DIR, "projects.json")

# Locate FFmpeg & FFprobe executables natively
def _find_standalone_binary(name: str) -> str:
    # 1. Check direct env or which
    p = os.environ.get(f"{name.upper()}_PATH") or shutil.which(name)
    if p and os.path.exists(p):
        return p
    # 2. Check local app bin directory
    local_bin = os.path.join(DATA_DIR, "bin", f"{name}.exe")
    if os.path.exists(local_bin):
        return local_bin
    # 3. Check AppData local tools
    appdata_tool = os.path.join(os.environ.get("LOCALAPPDATA", ""), "OmniVoice", "bin", f"{name}.exe")
    if os.path.exists(appdata_tool):
        return appdata_tool
    # 4. Check imageio_ffmpeg
    if name == "ffmpeg":
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and os.path.exists(exe):
                return exe
        except Exception:
            pass
    return name

FFMPEG_PATH = _find_standalone_binary("ffmpeg")
FFPROBE_PATH = _find_standalone_binary("ffprobe")
if FFPROBE_PATH == "ffprobe" and FFMPEG_PATH != "ffmpeg":
    candidate = FFMPEG_PATH.replace("ffmpeg.exe", "ffprobe.exe").replace("ffmpeg", "ffprobe")
    if os.path.exists(candidate):
        FFPROBE_PATH = candidate

# Scan for HuggingFace model caches (checks OmniVoice cache if present, else standard user cache)
OMNIVOICE_HF_CACHE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "OmniVoice", "hf_cache")
USER_HF_CACHE = os.path.expanduser("~/.cache/huggingface/hub")
OMNIVOICE_DATA_DIR = os.path.join(os.environ.get("APPDATA", ""), "OmniVoice")
OMNIVOICE_VOICES_DIR = os.path.join(OMNIVOICE_DATA_DIR, "voices")

if os.path.exists(OMNIVOICE_HF_CACHE):
    DETECTED_HF_CACHE = OMNIVOICE_HF_CACHE
elif os.path.exists(USER_HF_CACHE):
    DETECTED_HF_CACHE = USER_HF_CACHE
else:
    DETECTED_HF_CACHE = STANDALONE_HF_CACHE

os.environ["HF_HOME"] = DETECTED_HF_CACHE
os.environ["HF_HUB_CACHE"] = DETECTED_HF_CACHE

# Ensure directories exist
for d in [DATA_DIR, OUTPUT_DIR, CACHE_DIR, DOWNLOADS_DIR, STANDALONE_HF_CACHE]:
    os.makedirs(d, exist_ok=True)

# Default options
DEFAULT_ASR_MODEL = "large-v3"
DEFAULT_TARGET_LANG = "vi"
DEFAULT_TTS_VOICE = "vi-VN-NamMinhNeural"
DEFAULT_TTS_ENGINE = "edge-tts"
DEFAULT_TRANSLATION_ENGINE = "google"
DEFAULT_BED_GAIN = 0.35
DEFAULT_VOICE_GAIN = 1.2

# ASR Models and Engines
ASR_ENGINES = ["faster-whisper (Khuyên dùng)", "openai-whisper (PyTorch)"]
ASR_MODELS = ["tiny", "base", "small", "medium", "large-v3"]

# Timing strategies
TIMING_STRATEGIES = ["smart_fit", "concise", "stretch_video", "strict_slot"]
# Voice match modes
VOICE_MATCH_MODES = ["auto", "exact", "gender_only"]
# Translate quality presets
TRANSLATE_QUALITY = ["cinematic", "literal", "concise"]
# Export formats
EXPORT_VIDEO_FORMATS = ["mp4", "mkv", "mov", "webm"]
EXPORT_AUDIO_FORMATS = ["wav", "mp3", "m4a", "flac"]
EXPORT_SUBTITLE_FORMATS = ["srt", "vtt", "txt"]
