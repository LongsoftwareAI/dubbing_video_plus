"""
Audio separation service using Demucs / FFmpeg.
Separates original video audio into vocals (for ASR) and background bed (for mixing).
"""
import os
import sys
import subprocess
import logging
from test_mini_tool.config import CACHE_DIR, FFMPEG_PATH

logger = logging.getLogger("mini_dubber.audio_separator")

# Use the same Python interpreter to invoke demucs as a module
_PYTHON = sys.executable


def separate_audio(video_path: str, output_dir: str = None) -> tuple[str, str]:
    """
    Extracts audio from video_path and separates it into:
    - vocal_path: wav file containing speech only (or mono audio for ASR)
    - bed_path: wav file containing background music/ambience stem
    Returns (vocal_path, bed_path)
    """
    if output_dir is None:
        output_dir = os.path.join(CACHE_DIR, "sep_" + os.path.basename(video_path))
    os.makedirs(output_dir, exist_ok=True)

    extracted_wav = os.path.join(output_dir, "original_audio.wav")

    # Step 1: Extract 48kHz audio from video using FFmpeg
    cmd_extract = [
        FFMPEG_PATH, "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "2",
        extracted_wav
    ]
    try:
        subprocess.run(cmd_extract, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        logger.error(f"FFmpeg extraction failed: {e}")
        raise RuntimeError(f"Failed to extract audio from {video_path}")

    # Step 2: Demucs audio separation via python -m demucs
    try:
        cmd_demucs = [
            _PYTHON, "-m", "demucs",
            "--two-stems", "vocals",
            "-n", "htdemucs",
            "-o", output_dir,
            extracted_wav
        ]
        res = subprocess.run(
            cmd_demucs,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600  # 10 minute timeout for long videos
        )

        # Demucs outputs to <output_dir>/htdemucs/original_audio/vocals.wav and no_vocals.wav
        demucs_vocal = os.path.join(output_dir, "htdemucs", "original_audio", "vocals.wav")
        demucs_bed = os.path.join(output_dir, "htdemucs", "original_audio", "no_vocals.wav")

        if os.path.exists(demucs_vocal) and os.path.exists(demucs_bed):
            logger.info("Successfully separated audio using Demucs.")
            return demucs_vocal, demucs_bed
        else:
            logger.warning("Demucs ran but output files not found. stderr: %s", res.stderr[-500:] if res.stderr else "(none)")
    except Exception as demucs_err:
        logger.warning(f"Demucs separation skipped or failed: {demucs_err}. Falling back to full audio bed.")

    # Fallback: Use original audio for both vocals and bed
    return extracted_wav, extracted_wav
