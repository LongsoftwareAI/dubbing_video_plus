"""
Standalone Speech Recognition (ASR / STT) Service.
100% independent from OmniVoice backend infrastructure.
Supports faster-whisper (CTranslate2 with CUDA/CPU), openai-whisper fallback,
selectable engines, Voice Activity Detection (VAD), word timestamps, and multi-language auto-detection.
"""
import os
import shutil
import logging
from config import DETECTED_HF_CACHE

logger = logging.getLogger("mini_dubber.asr")


def transcribe_audio(
    audio_path: str,
    model_size: str = "large-v3",
    engine: str = "auto",
    language: str = None,
    vad_filter: bool = True
) -> list[dict]:
    """
    Transcribes audio_path into timed segments completely offline & standalone:
    Supports selectable engine ('auto', 'faster-whisper', 'whisper' / 'openai-whisper').
    Returns list of dicts:
    [{"id": 0, "start": 0.0, "end": 2.5, "text": "Hello world", "speaker": "SPEAKER_00"}]
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found for ASR: {audio_path}")

    segments = []
    engine_choice = engine.lower()

    # ── Engine 1: faster-whisper (High-speed CTranslate2 engine with CUDA float16 / CPU int8) ──
    if engine_choice in ("auto", "faster-whisper", "faster_whisper", "ctranslate2"):
        try:
            from faster_whisper import WhisperModel
            use_cuda = _has_cuda()
            compute_type = "float16" if use_cuda else "int8"
            device = "cuda" if use_cuda else "cpu"

            logger.info(f"Loading faster-whisper model '{model_size}' on {device} ({compute_type})...")
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=DETECTED_HF_CACHE if os.path.exists(DETECTED_HF_CACHE) else None
            )

            raw_segments, info = model.transcribe(
                audio_path,
                language=language,
                word_timestamps=True,
                vad_filter=vad_filter,
                vad_parameters=dict(min_silence_duration_ms=500),
                beam_size=5
            )

            logger.info(f"Detected language: '{info.language}' with probability {info.language_probability:.2f}")

            for idx, seg in enumerate(raw_segments):
                text_cleaned = seg.text.strip()
                if text_cleaned:
                    segments.append({
                        "id": idx,
                        "start": round(seg.start, 3),
                        "end": round(seg.end, 3),
                        "text": text_cleaned,
                        "speaker": "SPEAKER_00"
                    })

            logger.info(f"Transcribed {len(segments)} segments using faster-whisper.")
            return segments

        except Exception as e:
            if engine_choice == "faster-whisper":
                logger.error(f"faster-whisper explicit request failed: {e}")
                raise
            logger.warning(f"faster-whisper not available: {e}. Falling back to openai-whisper.")

    # ── Engine 2: openai-whisper (Standard PyTorch Engine) ──
    try:
        import whisper
        device = "cuda" if _has_cuda() else "cpu"
        logger.info(f"Loading openai-whisper model '{model_size}' on {device}...")
        model = whisper.load_model(model_size, device=device)
        res = model.transcribe(audio_path, language=language, verbose=False)

        for idx, seg in enumerate(res.get("segments", [])):
            text_cleaned = seg.get("text", "").strip()
            if text_cleaned:
                segments.append({
                    "id": idx,
                    "start": round(seg.get("start", 0.0), 3),
                    "end": round(seg.get("end", 0.0), 3),
                    "text": text_cleaned,
                    "speaker": "SPEAKER_00"
                })

        logger.info(f"Transcribed {len(segments)} segments using openai-whisper.")
        return segments

    except Exception as e2:
        logger.error(f"Speech Recognition (ASR) failed: {e2}")
        raise RuntimeError(f"Speech Recognition (ASR) failed: {e2}")


def _has_cuda() -> bool:
    """Checks if NVIDIA CUDA GPU acceleration is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False
