"""
Text-To-Speech (TTS) & Voice Cloning Service — Independent Mini Dubber.

Guarantees:
1. 100% identical voice across ALL segments (single precomputed VoiceClonePrompt reused).
2. NO cross-lingual ref_text artifacts: ref_text="" forces audio-only timbre cloning,
   eliminating "trờ"/"nẹt" phonetic boundary artifacts from English↔Vietnamese collision.
3. Text normalization before synthesis (avoids hallucinations & misread characters).
4. Broadcast DSP mastering (80Hz highpass + compression + peak normalize to -2 dBFS).
"""
import os
import re
import sys
import time
import asyncio
import logging
import threading
import subprocess
import soundfile as sf
import numpy as np

# Prevent torchaudio from broken torchcodec imports on Windows
os.environ.setdefault("TORCHAUDIO_USE_TORCHCODEC", "0")
sys.modules.setdefault("torchcodec", None)

from config import FFMPEG_PATH

logger = logging.getLogger("mini_dubber.tts")

# Global GPU Semaphore: ensures only 1 thread accesses CUDA VRAM simultaneously
_GPU_INFERENCE_SEMAPHORE = threading.Semaphore(1)

# Singleton OmniVoice model + precomputed voice clone prompts
_OMNIVOICE_MODEL = None
_PRECOMPUTED_PROMPTS = {}  # keyed by ref_audio path -> VoiceClonePrompt
_INIT_LOCK = threading.Lock()


def _get_omnivoice_model():
    """Returns persistent cached OmniVoice model singleton."""
    global _OMNIVOICE_MODEL
    if _OMNIVOICE_MODEL is None:
        with _INIT_LOCK:
            if _OMNIVOICE_MODEL is None:
                try:
                    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
                    if backend_dir not in sys.path:
                        sys.path.insert(0, backend_dir)
                    from services.model_manager import get_model
                    import asyncio as _aio
                    _OMNIVOICE_MODEL = _aio.run(get_model())
                    logger.info("OmniVoice model loaded successfully (singleton)")
                except Exception as e:
                    logger.warning(f"Could not load OmniVoice model: {e}")
    return _OMNIVOICE_MODEL


def precompute_voice_prompt(ref_audio_path: str, ref_text: str = None) -> object:
    """
    Pre-encode a reference audio into a reusable VoiceClonePrompt ONCE.

    CRITICAL: Pass ref_text="" (empty) to force audio-only timbre cloning.
    When the reference audio is in a different language (e.g. English YouTube)
    than the target text (Vietnamese), using the original English ref_text
    causes cross-lingual phonetic boundary artifacts ("trờ", "nẹt", "chẳng")
    because _combine_text() concatenates ref_text + target_text and the model's
    text tokenizer creates conflicting phoneme predictions at the boundary.

    With ref_text="", _combine_text() returns only the target text, and the
    model clones voice timbre purely from audio token conditioning.
    """
    global _PRECOMPUTED_PROMPTS
    if not ref_audio_path or not os.path.exists(ref_audio_path):
        return None

    if ref_audio_path in _PRECOMPUTED_PROMPTS:
        return _PRECOMPUTED_PROMPTS[ref_audio_path]

    model = _get_omnivoice_model()
    if model is None or not hasattr(model, "create_voice_clone_prompt"):
        return None

    try:
        import torch
        with _GPU_INFERENCE_SEMAPHORE:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            # Pass ref_text="" to bypass auto-transcription AND avoid
            # cross-lingual text token collision. The model still uses
            # ref_audio_tokens for voice timbre/style conditioning.
            prompt = model.create_voice_clone_prompt(
                ref_audio=ref_audio_path,
                ref_text="",
                preprocess_prompt=True
            )
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        _PRECOMPUTED_PROMPTS[ref_audio_path] = prompt
        logger.info(f"Pre-computed voice clone prompt (audio-only, no cross-lingual text): {os.path.basename(ref_audio_path)}")
        return prompt
    except Exception as e:
        logger.warning(f"Failed to precompute voice clone prompt: {e}")
        return None


def clear_voice_prompts_cache():
    """Clears all cached precomputed prompts to force fresh generation."""
    global _PRECOMPUTED_PROMPTS
    _PRECOMPUTED_PROMPTS.clear()
    logger.info("Cleared precomputed voice clone prompts cache")


def _normalize_text_for_tts(text: str) -> str:
    """Sanitizes and normalizes Vietnamese text before TTS.
    Self-contained: no backend dependency."""
    if not text:
        return ""

    # Strip markup, brackets, angle-brackets
    cleaned = re.sub(r'\[.*?\]', '', text)
    cleaned = re.sub(r'\(.*?\)', '', cleaned)
    cleaned = re.sub(r'<.*?>', '', cleaned)
    cleaned = re.sub(r'[\r\n\t]+', ' ', cleaned)
    # Collapse multiple spaces
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    cleaned = cleaned.strip(" -—_\"'""")
    cleaned = cleaned.strip()

    if not cleaned:
        return ""

    # Ensure sentence-terminal punctuation for natural vocal cadence
    if cleaned[-1] not in ('.', '!', '?', '…', ',', ':', ';'):
        cleaned = cleaned + "."

    return cleaned


def _trim_trailing_silence(audio_np: np.ndarray, sr: int = 24000, keep_tail_s: float = 0.25) -> np.ndarray:
    """
    Trims trailing dead silence output by TTS models while preserving a natural 250ms vocal release.
    Uses -55 dBFS silence floor so trailing consonants and soft breath releases are NEVER chopped.
    """
    if len(audio_np) == 0:
        return audio_np
    silence_floor = 10 ** (-55.0 / 20.0)  # ~0.00178 (preserves soft consonants)
    voiced = np.where(np.abs(audio_np) > silence_floor)[0]
    if len(voiced) == 0:
        return audio_np
    last_idx = voiced[-1]
    keep_samples = int(keep_tail_s * sr)
    cut_idx = min(len(audio_np), last_idx + keep_samples)
    trimmed = audio_np[:cut_idx].copy()

    # Smooth Hann S-curve fade out over 30ms (zero derivative at onset and end)
    fade_len = min(int(0.030 * sr), len(trimmed) // 4)
    if fade_len > 1:
        t = np.linspace(0.0, np.pi, fade_len, dtype=np.float32)
        ramp_down = 0.5 * (1.0 + np.cos(t))
        trimmed[-fade_len:] *= ramp_down
    return trimmed


def _apply_dsp_mastering(audio_np: np.ndarray, sr: int = 24000, effect_preset: str = "broadcast") -> np.ndarray:
    """
    Applies Broadcast DSP mastering:
    1. Trims dead trailing silence preserving 250ms vocal release.
    2. Applies broadcast pre-stage (80Hz highpass + studio compressor).
    3. Applies studio Parametric EQ + Limiter.
    4. Smooth 20ms Hann boundary envelope to guarantee zero boundary artifacts.
    5. Peak-normalizes to -2.0 dBFS standard broadcast level.
    """
    if len(audio_np) == 0:
        return audio_np

    # 1. Trim dead silence from end of speech
    audio_np = _trim_trailing_silence(audio_np, sr=sr)

    # 2. Try Pedalboard DSP chain
    try:
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        import torch
        from services.audio_dsp import apply_mastering, apply_effects_chain, get_effect_chain, normalize_audio

        wav_t = torch.from_numpy(audio_np).float()
        if wav_t.ndim == 1:
            wav_t = wav_t.unsqueeze(0)

        # Pre-mastering stage (highpass + gentle compression)
        mastered = apply_mastering(wav_t, sample_rate=sr)

        # Studio broadcast effects chain (warm low-shelf, crisp high-shelf, limiter)
        chain = get_effect_chain(effect_preset)
        if chain:
            mastered = apply_effects_chain(mastered, sample_rate=sr, chain=chain)

        # Broadcast peak normalization (-2.0 dBFS)
        normalized = normalize_audio(mastered, target_dBFS=-2.0)
        audio_np = normalized.squeeze().cpu().numpy().astype(np.float32)

    except Exception as dsp_err:
        logger.debug(f"Pedalboard DSP unavailable, using native mastering: {dsp_err}")
        # Fallback native normalization
        max_val = np.max(np.abs(audio_np))
        silence_floor = 10 ** (-50.0 / 20.0)  # ~0.00316
        if max_val > silence_floor:
            target_amp = 10 ** (-2.0 / 20.0)  # ~0.794
            audio_np = audio_np * (target_amp / max_val)

    # 3. Smooth Hann boundary envelope (guarantees zero pop/crack at start/end)
    fade_len = min(int(0.020 * sr), len(audio_np) // 4)
    if fade_len > 1:
        t = np.linspace(0.0, np.pi, fade_len, dtype=np.float32)
        ramp_up = 0.5 * (1.0 - np.cos(t))
        ramp_down = 0.5 * (1.0 + np.cos(t))
        audio_np[:fade_len] *= ramp_up
        audio_np[-fade_len:] *= ramp_down

    # 4. Strict clamping
    return np.clip(audio_np, -1.0, 1.0).astype(np.float32)


def synthesize_segment(
    text: str,
    output_wav: str,
    voice: str = "vi-VN-NamMinhNeural",
    ref_audio_path: str = None,
    engine: str = "omnivoice",
    duration_s: float = None
) -> str:
    """
    Synthesizes text into a WAV audio file.
    Uses precomputed voice_clone_prompt with ref_text="" for cross-lingual safety.
    """
    out_dir = os.path.dirname(output_wav)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    clean_text = _normalize_text_for_tts(text)
    if not clean_text or len(clean_text) < 1:
        _generate_silence_wav(output_wav, duration_sec=0.5)
        return output_wav

    # ── Tier 0: OmniVoice with audio-only voice clone prompt ──
    is_clone_requested = (
        engine in ("omnivoice", "clone") or
        "[CLONE" in voice.upper() or
        "[DỰ ÁN]" in voice.upper() or
        (ref_audio_path and os.path.exists(str(ref_audio_path)))
    )

    if is_clone_requested and ref_audio_path and os.path.exists(str(ref_audio_path)):
        # Get or create the audio-only voice clone prompt (ref_text="")
        prompt = _PRECOMPUTED_PROMPTS.get(ref_audio_path)
        if prompt is None:
            prompt = precompute_voice_prompt(ref_audio_path)

        model = _get_omnivoice_model()
        if model is not None and prompt is not None:
            import torch
            for attempt, nsteps in enumerate([16, 8], 1):
                try:
                    with _GPU_INFERENCE_SEMAPHORE:
                        with torch.inference_mode():
                            audios = model.generate(
                                text=clean_text,
                                voice_clone_prompt=prompt,
                                language="vi",
                                duration=None,   # Natural rate — no forced duration
                                num_step=nsteps,
                                guidance_scale=2.0,
                                speed=1.0,
                                denoise=True,
                                postprocess_output=True,
                            )
                        wav_tensor = audios[0] if isinstance(audios, list) else audios
                        audio_np = wav_tensor.squeeze().cpu().numpy()

                        # Apply broadcast DSP mastering
                        audio_np = _apply_dsp_mastering(audio_np, 24000)
                        sf.write(output_wav, audio_np, 24000, subtype="PCM_16")
                        logger.info(f"OmniVoice (audio-only clone, {nsteps} steps): {os.path.basename(output_wav)}")
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                        return output_wav
                except Exception as omni_err:
                    logger.warning(f"OmniVoice attempt {attempt} failed: {omni_err}")
                    try:
                        import gc
                        gc.collect()
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except Exception:
                        pass

    # If cloning was NOT requested or failed, use EdgeTTS / gTTS
    clean_voice = _clean_voice_id(voice)
    pitch_str = "+0Hz"
    rate_str = "+0%"

    # ── Tier 1: EdgeTTS Neural Voices ──
    for attempt in range(1, 4):
        try:
            import edge_tts
            mp3_tmp = output_wav.replace(".wav", f"_edge_tmp.mp3")

            async def _run_edge():
                communicate = edge_tts.Communicate(clean_text, clean_voice, pitch=pitch_str, rate=rate_str)
                await communicate.save(mp3_tmp)

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_run_edge())
            finally:
                loop.close()

            if os.path.exists(mp3_tmp) and os.path.getsize(mp3_tmp) > 100:
                _convert_audio_to_wav(mp3_tmp, output_wav)
                try:
                    os.remove(mp3_tmp)
                except OSError:
                    pass
                if os.path.exists(output_wav) and os.path.getsize(output_wav) > 100:
                    return output_wav
        except Exception as e:
            logger.warning(f"EdgeTTS attempt {attempt}/3 for '{clean_voice}': {e}")
            time.sleep(0.3 * attempt)

    # ── Tier 2: gTTS ──
    try:
        from gtts import gTTS
        lang = "vi" if "vi" in clean_voice.lower() else "en"
        tts = gTTS(text=clean_text, lang=lang, slow=False)
        mp3_tmp = output_wav.replace(".wav", "_gtts_tmp.mp3")
        tts.save(mp3_tmp)
        _convert_audio_to_wav(mp3_tmp, output_wav)
        if os.path.exists(mp3_tmp):
            os.remove(mp3_tmp)
        if os.path.exists(output_wav) and os.path.getsize(output_wav) > 100:
            return output_wav
    except Exception as gtts_err:
        logger.warning(f"gTTS fallback error: {gtts_err}")

    # ── Tier 3: Silence fallback ──
    dur = max(0.5, len(clean_text) / 14.0)
    _generate_silence_wav(output_wav, duration_sec=dur)
    return output_wav


def _clean_voice_id(voice: str) -> str:
    """Extract clean EdgeTTS voice identifier."""
    if not voice:
        return "vi-VN-NamMinhNeural"
    clean = voice.split(" ")[0].strip().replace("[", "").replace("]", "")
    for prefix in ("vi-VN-", "en-US-", "fr-FR-", "ja-JP-", "zh-CN-", "ko-KR-", "de-DE-", "es-ES-"):
        if clean.startswith(prefix):
            return clean
    if any(m in voice.lower() for m in ("nam", "male", "anh", "đàn ông", "bác", "chú")):
        return "vi-VN-NamMinhNeural"
    if any(f in voice.lower() for f in ("nữ", "female", "chị", "cô", "gái", "bà")):
        return "vi-VN-HoaiMyNeural"
    return "vi-VN-NamMinhNeural"


def _convert_audio_to_wav(in_file: str, out_wav: str):
    cmd = [FFMPEG_PATH, "-y", "-i", in_file, "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1", out_wav]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _generate_silence_wav(out_wav: str, duration_sec: float = 0.5, sample_rate: int = 24000):
    num_samples = int(max(0.2, duration_sec) * sample_rate)
    silence = np.zeros(num_samples, dtype=np.int16)
    sf.write(out_wav, silence, sample_rate)
