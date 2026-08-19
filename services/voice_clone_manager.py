"""
Voice Cloning & Persona Profile Manager for Mini Video Dubber.
Mirrors OmniVoice voice profile architecture (.ovsvoice persona bundle, reference sample extraction,
multi-speaker automatic clone assignment, and zero-shot voice cloning integration).
"""
import os
import json
import time
import shutil
import logging
import subprocess
import soundfile as sf
import numpy as np

from test_mini_tool.config import DATA_DIR, FFMPEG_PATH

logger = logging.getLogger("mini_dubber.voice_clone")

VOICES_DB_DIR = os.path.join(DATA_DIR, "voices")
VOICES_JSON_PATH = os.path.join(VOICES_DB_DIR, "profiles.json")

os.makedirs(VOICES_DB_DIR, exist_ok=True)


def _load_db() -> list[dict]:
    if not os.path.exists(VOICES_JSON_PATH):
        default_profiles = [
            {
                "id": "clone_viet_bac_nu",
                "name": "Thanh Trúc (Nữ Hà Nội - Truyền cảm)",
                "gender": "Nữ",
                "dialect": "Miền Bắc",
                "ref_audio_path": "",
                "description": "Giọng nữ thanh lịch, chuẩn phát âm Hà Nội, phù hợp đọc sách và tin tức",
                "created_at": time.strftime("%Y-%m-%d %H:%M")
            },
            {
                "id": "clone_viet_nam_nam",
                "name": "Hoàng Nam (Nam Sài Gòn - Trầm ấm)",
                "gender": "Nam",
                "dialect": "Miền Nam",
                "ref_audio_path": "",
                "description": "Giọng nam miền Nam tự nhiên, phong cách Vlog và Review công nghệ",
                "created_at": time.strftime("%Y-%m-%d %H:%M")
            }
        ]
        _save_db(default_profiles)
        return default_profiles

    try:
        with open(VOICES_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read profiles.json: {e}")
        return []


def _save_db(profiles: list[dict]):
    os.makedirs(VOICES_DB_DIR, exist_ok=True)
    with open(VOICES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)


def get_all_clone_profiles() -> list[dict]:
    """Returns all saved cloned voice profiles."""
    return _load_db()


def get_clone_profile_by_id(profile_id: str) -> dict | None:
    for p in _load_db():
        if p["id"] == profile_id or p["name"] == profile_id:
            return p
    return None


def create_clone_profile(
    name: str,
    raw_audio_path: str,
    gender: str = "Nam",
    dialect: str = "Miền Bắc",
    description: str = ""
) -> dict:
    """
    Creates and processes a new clone voice profile:
    Normalizes audio into 24kHz Mono WAV, trims silence, and saves into voice library.
    """
    profiles = _load_db()
    clean_id = "clone_" + str(int(time.time() * 1000))[-8:]

    dest_wav = os.path.join(VOICES_DB_DIR, f"{clean_id}.wav")

    # Process and normalize audio sample using FFmpeg
    if raw_audio_path and os.path.exists(raw_audio_path):
        cmd = [
            FFMPEG_PATH, "-y",
            "-i", raw_audio_path,
            "-af", "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-45dB,loudnorm=I=-16:TP=-1.5:LRA=11",
            "-acodec", "pcm_s16le",
            "-ar", "24000",
            "-ac", "1",
            dest_wav
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as err:
            logger.warning(f"Loudnorm processing fallback: {err}")
            shutil.copy2(raw_audio_path, dest_wav)
    else:
        _generate_sample_wav(dest_wav)

    profile = {
        "id": clean_id,
        "name": name.strip() or f"Giọng Clone #{len(profiles) + 1}",
        "gender": gender,
        "dialect": dialect,
        "ref_audio_path": dest_wav,
        "description": description.strip() or "Hồ sơ giọng đọc nhân bản AI",
        "created_at": time.strftime("%Y-%m-%d %H:%M")
    }

    profiles.insert(0, profile)
    _save_db(profiles)
    logger.info(f"Created new voice profile: {profile['name']} -> {dest_wav}")
    return profile


def delete_clone_profile(profile_id: str) -> bool:
    profiles = _load_db()
    target = None
    for p in profiles:
        if p["id"] == profile_id:
            target = p
            break
    if not target:
        return False

    profiles.remove(target)
    _save_db(profiles)

    if target.get("ref_audio_path") and os.path.exists(target["ref_audio_path"]):
        try:
            os.remove(target["ref_audio_path"])
        except OSError:
            pass
    return True


def extract_voice_from_vocals(vocals_wav_path: str, name: str = "Giọng Trích Xuất Từ Video") -> dict | None:
    """Automatically extracts a clean 5-10s voice reference from Demucs vocals.wav."""
    if not os.path.exists(vocals_wav_path):
        return None

    out_clip = os.path.join(VOICES_DB_DIR, f"extracted_{int(time.time())}.wav")
    cmd = [
        FFMPEG_PATH, "-y",
        "-ss", "00:00:03",
        "-t", "8",
        "-i", vocals_wav_path,
        "-acodec", "pcm_s16le",
        "-ar", "24000",
        "-ac", "1",
        out_clip
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return create_clone_profile(
            name=name,
            raw_audio_path=out_clip,
            gender="Tự động",
            dialect="Chuẩn",
            description="Trích xuất trực tiếp từ video gốc"
        )
    except Exception as e:
        logger.error(f"Auto voice extraction error: {e}")
        return None


def extract_all_speakers_from_job(vocals_wav_path: str, segments: list[dict], prefix: str = "Nhân vật") -> dict[str, str]:
    """
    Extracts clean reference audio for EVERY distinct speaker in the video.
    Returns mapping {speaker_id: cloned_voice_label} to auto-assign in dubbing.
    """
    if not os.path.exists(vocals_wav_path) or not segments:
        return {}

    speaker_map = {}
    speakers = sorted(list(set(seg.get("speaker", "SPEAKER_00") for seg in segments)))

    for spk in speakers:
        # Find best segment for this speaker (duration between 4s and 12s)
        spk_segs = [s for s in segments if s.get("speaker") == spk]
        best_seg = None
        best_dur = 0.0
        for s in spk_segs:
            dur = float(s.get("end", 0.0)) - float(s.get("start", 0.0))
            if dur > best_dur:
                best_dur = dur
                best_seg = s

        if not best_seg:
            continue

        start_s = max(0.0, float(best_seg.get("start", 0.0)))
        dur_s = min(10.0, max(4.0, float(best_seg.get("end", start_s + 4.0)) - start_s))

        out_clip = os.path.join(VOICES_DB_DIR, f"extracted_{spk}_{int(time.time())}.wav")
        cmd = [
            FFMPEG_PATH, "-y",
            "-ss", f"{start_s:.2f}",
            "-t", f"{dur_s:.2f}",
            "-i", vocals_wav_path,
            "-acodec", "pcm_s16le",
            "-ar", "24000",
            "-ac", "1",
            out_clip
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            voice_name = f"{prefix} {spk} (Video Clone)"
            create_clone_profile(
                name=voice_name,
                raw_audio_path=out_clip,
                gender="Tự động",
                dialect="Theo Video",
                description=f"Giọng nhân vật {spk} tự động trích xuất từ video"
            )
            speaker_map[spk] = f"[CLONE] {voice_name}"
        except Exception as e:
            logger.warning(f"Extraction failed for {spk}: {e}")

    return speaker_map


def _generate_sample_wav(dest_wav: str, duration_sec: float = 6.0, sample_rate: int = 24000):
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
    tone = np.sin(2 * np.pi * 330 * t) * 0.2
    audio = (tone * 32767).astype(np.int16)
    sf.write(dest_wav, audio, sample_rate)
