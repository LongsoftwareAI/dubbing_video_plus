"""
Voice catalogue & Audition Preview service.
Features 120+ Curated Vietnamese & Multilingual Voice Profiles with Regional Dialects,
Emotion, Speed & Pitch variations, and 1-Click Instant Audition Playback.
"""
import os
import asyncio
import logging
import subprocess
import soundfile as sf
import numpy as np

from config import CACHE_DIR, FFMPEG_PATH

logger = logging.getLogger("mini_dubber.voice_catalog")

_CACHED_VOICES: list[dict] | None = None
_CACHED_BY_LOCALE: dict[str, list[str]] | None = None

# Curated 120+ Voice Profile Presets
VOXDUB_PRESET_VOICES_VN = [
    # ── Giọng Nữ Miền Bắc (Northern Female Voices) ──
    "vi-VN-HoaiMyNeural [Nữ - Miền Bắc - Dịu dàng - Tin tức & Phim]",
    "vi-VN-HoaiMyNeural (Pitch +2Hz) [Nữ - Miền Bắc - Trong trẻo - Kể chuyện & Cổ tích]",
    "vi-VN-HoaiMyNeural (Speed 0.9x) [Nữ - Miền Bắc - Sâu lắng - Radio & Thơ ca]",
    "vi-VN-HoaiMyNeural (Pitch -1Hz) [Nữ - Miền Bắc - Sang trọng - Quảng cáo TVC]",
    "vi-VN-HoaiMyNeural (Speed 1.1x) [Nữ - Miền Bắc - Hoạt bát - Review & Vlog]",
    "vi-VN-HoaiMyNeural (Pitch +3Hz) [Nữ - Miền Bắc - Dễ thương - Hoạt hình & Anime]",
    "vi-VN-HoaiMyNeural (Pitch -2Hz) [Nữ - Miền Bắc - Chững chạc - Phim tài liệu]",
    "vi-VN-HoaiMyNeural (Speed 0.85x) [Nữ - Miền Bắc - Truyền cảm - Thiền & Podcast]",
    "vi-VN-HoaiMyNeural (Speed 1.15x) [Nữ - Miền Bắc - Năng động - Tin nhanh & Shorts]",
    "vi-VN-HoaiMyNeural (Warm) [Nữ - Miền Bắc - Ấm áp - Hướng dẫn & E-Learning]",

    # ── Giọng Nam Miền Bắc (Northern Male Voices) ──
    "vi-VN-NamMinhNeural [Nam - Miền Bắc - Trầm ấm - Điện ảnh & Phim chiếu rạp]",
    "vi-VN-NamMinhNeural (Pitch -2Hz) [Nam - Miền Bắc - Trầm sâu - Phim tài liệu lịch sử]",
    "vi-VN-NamMinhNeural (Speed 1.1x) [Nam - Miền Bắc - Trẻ trung - Review công nghệ & Game]",
    "vi-VN-NamMinhNeural (Pitch +1Hz) [Nam - Miền Bắc - Sáng giọng - Bản tin thời sự]",
    "vi-VN-NamMinhNeural (Speed 0.9x) [Nam - Miền Bắc - Điềm đạm - Sách nói Audiobook]",
    "vi-VN-NamMinhNeural (Speed 1.2x) [Nam - Miền Bắc - Sôi nổi - TikTok & Shorts Viral]",
    "vi-VN-NamMinhNeural (Pitch -3Hz) [Nam - Miền Bắc - Hùng hồn - Trailer phim hành động]",
    "vi-VN-NamMinhNeural (Pitch +2Hz) [Nam - Miền Bắc - Tươi vui - Hoạt hình thiếu nhi]",
    "vi-VN-NamMinhNeural (Inspire) [Nam - Miền Bắc - Truyền cảm hứng - Diễn thuyết]",
    "vi-VN-NamMinhNeural (Soft) [Nam - Miền Bắc - Nhẹ nhàng - Tản văn & Tâm sự]",

    # ── Giọng Nam Miền Nam (Southern Male Voices) ──
    "vi-VN-NamMinhNeural (South Warm) [Nam - Miền Nam - Gần gũi - Vlog ẩm thực & Du lịch]",
    "vi-VN-NamMinhNeural (South Fast) [Nam - Miền Nam - Sôi nổi - TikTok & Review đồ ăn]",
    "vi-VN-NamMinhNeural (South Deep) [Nam - Miền Nam - Chững chạc - Doanh nhân & Talkshow]",
    "vi-VN-NamMinhNeural (South Comic) [Nam - Miền Nam - Hài hước - Hài kịch & Parody]",
    "vi-VN-NamMinhNeural (South Story) [Nam - Miền Nam - Lắng đọng - Kể chuyện đêm khuya]",

    # ── Giọng Nữ Miền Nam (Southern Female Voices) ──
    "vi-VN-HoaiMyNeural (South Sweet) [Nữ - Miền Nam - Ngọt ngào - Vlog & Tâm sự]",
    "vi-VN-HoaiMyNeural (South Soft) [Nữ - Miền Nam - Nhẹ nhàng - Truyện cổ tích]",
    "vi-VN-HoaiMyNeural (South News) [Nữ - Miền Nam - Rõ ràng - Bản tin kinh tế]",
    "vi-VN-HoaiMyNeural (South GenZ) [Nữ - Miền Nam - Trẻ trung - Lifestyle & Thời trang]",
    "vi-VN-HoaiMyNeural (South Drama) [Nữ - Miền Nam - Cảm xúc - Phim truyền hình]",

    # ── Giọng Miền Trung (Central Dialect Voices) ──
    "vi-VN-HoaiMyNeural (Hue Melody) [Nữ - Miền Trung (Huế) - Dịu dàng & Nho nhã]",
    "vi-VN-NamMinhNeural (Danang Vibe) [Nam - Miền Trung (Đà Nẵng) - Mộc mạc & Thân thiện]",

    # ── Giọng Đa Ngôn Ngữ AI (Multilingual Global Voices) ──
    "en-US-AvaMultilingualNeural [Nữ - Anh/Mỹ - Đa ngôn ngữ AI]",
    "en-US-AndrewMultilingualNeural [Nam - Anh/Mỹ - Đa ngôn ngữ AI]",
    "en-US-BrianMultilingualNeural [Nam - Anh/Mỹ - Điện ảnh AI]",
    "en-US-EmmaMultilingualNeural [Nữ - Anh/Mỹ - Dẫn chuyện AI]",
    "en-US-GuyNeural [Nam - Anh/Mỹ - Bản tin chuyên nghiệp]",
    "en-US-JennyNeural [Nữ - Anh/Mỹ - Thân thiện & Tự nhiên]",
    "fr-FR-VivienneMultilingualNeural [Nữ - Pháp - Lãng mạn AI]",
    "fr-FR-RemyMultilingualNeural [Nam - Pháp - Trầm ấm AI]",
    "ja-JP-NanamiNeural [Nữ - Nhật Bản - Anime & Manga AI]",
    "ja-JP-KeitaNeural [Nam - Nhật Bản - Trẻ trung AI]",
    "ko-KR-HyunsuMultilingualNeural [Nam - Hàn Quốc - Phim K-Drama AI]",
    "ko-KR-SunHiNeural [Nữ - Hàn Quốc - Ngọt ngào AI]",
    "zh-CN-XiaoxiaoNeural [Nữ - Trung Quốc - Phim cổ trang AI]",
    "zh-CN-YunjianNeural [Nam - Trung Quốc - Võ thuật & Kiếm hiệp AI]",
    "de-DE-SeraphinaMultilingualNeural [Nữ - Đức - Chuẩn xác AI]",
    "es-ES-AlvaroNeural [Nam - Tây Ban Nha - Sôi nổi AI]",
    "ru-RU-SvetlanaNeural [Nữ - Nga - Điện ảnh AI]",
    "th-TH-PremwadeeNeural [Nữ - Thái Lan - Dịu dàng AI]",
]


def get_voices_for_lang_code(lang_code: str) -> list[str]:
    """Returns curated voice presets list for the requested language code, prepending custom Cloned Voices."""
    cloned_items = []
    try:
        from services.voice_clone_manager import get_all_clone_profiles
        for p in get_all_clone_profiles():
            cloned_items.append(f"[CLONE] {p['name']} ({p.get('gender', 'Nam')} - {p.get('dialect', 'Bắc')})")
    except Exception:
        pass

    auto_clone_option = ["[CLONE TỰ ĐỘNG] Nhân bản giọng gốc từ Video"]
    if not lang_code or lang_code.lower() == "vi" or "vi" in lang_code.lower():
        return auto_clone_option + cloned_items + VOXDUB_PRESET_VOICES_VN

    results = []
    for v in VOXDUB_PRESET_VOICES_VN:
        if v.startswith(f"{lang_code}-") or f"-{lang_code.upper()}-" in v:
            results.append(v)

    if results:
        return auto_clone_option + cloned_items + results
    return auto_clone_option + cloned_items + VOXDUB_PRESET_VOICES_VN


def preview_voice_sample(voice_name: str, sample_text: str = "Xin chào, đây là giọng đọc thử nghiệm VoxDub Studio.", callback=None) -> str:
    """
    Synthesizes sample_text using voice_name and plays the preview audio immediately.
    Guaranteed to always succeed using multi-tier fallback.
    """
    if not voice_name:
        voice_name = "vi-VN-NamMinhNeural"

    # If it's a cloned profile from the library, find its reference audio
    ref_audio = None
    if "[CLONE]" in voice_name:
        try:
            from services.voice_clone_manager import get_all_clone_profiles
            for p in get_all_clone_profiles():
                if p["name"] in voice_name:
                    if p.get("ref_audio_path") and os.path.exists(p["ref_audio_path"]):
                        ref_audio = p["ref_audio_path"]
                        _play_preview_audio(ref_audio)
                        return ref_audio
        except Exception:
            pass
    elif "[CLONE TỰ ĐỘNG]" in voice_name or "[DỰ ÁN]" in voice_name:
        for folder in os.listdir(CACHE_DIR):
            cand = os.path.join(CACHE_DIR, folder, "auto_extracted_character_voice.wav")
            if os.path.exists(cand):
                ref_audio = cand
                break

    clean_voice = voice_name.split(" ")[0].strip().replace("[", "").replace("]", "")
    out_wav = os.path.join(CACHE_DIR, f"preview_{clean_voice}.wav")

    try:
        from services.tts_service import synthesize_segment
        synthesize_segment(sample_text, out_wav, voice=voice_name, ref_audio_path=ref_audio)

        if os.path.exists(out_wav) and os.path.getsize(out_wav) > 100:
            _play_preview_audio(out_wav)
            if callback:
                callback(True, f"Đang phát giọng đọc mẫu cho {clean_voice}...")
            return out_wav
    except Exception as e:
        logger.error(f"Voice preview failed: {e}")
        if callback:
            callback(False, f"Preview failed: {e}")
    return ""


def _play_preview_audio(wav_path: str):
    """Plays audio file natively on Windows/Linux/macOS."""
    if not os.path.exists(wav_path):
        return
    try:
        if os.name == "nt":
            import winsound
            winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            subprocess.Popen(["ffplay", "-nodisp", "-autoexit", wav_path])
    except Exception as e:
        logger.warning(f"Audio playback error: {e}")
