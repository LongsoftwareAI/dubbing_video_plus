"""
Automatic Speaker Voice Extraction and Zero-Shot Reference Audio Generation.
Extracts clean 5-15s vocal clips for each character/speaker from the Demucs vocals track
to clone the exact character voice in the new language ("same speaker, new language").
"""
import os
import logging
import soundfile as sf
import numpy as np

logger = logging.getLogger("mini_dubber.speaker_clone")

MIN_REF_DURATION_S = 3.5
MAX_REF_DURATION_S = 15.0


def _align_and_trim_reference(clip_data: np.ndarray, sr: int, rough_text: str, out_wav_path: str) -> tuple[str, str]:
    """
    Refines reference audio clip and transcript:
    1. Uses Whisper to accurately transcribe the vocal slice with word-level timestamps.
    2. Trims trailing audio to the exact end of the last complete word.
    3. Smooths boundary envelopes with 20ms Hann window.
    4. Saves 16-bit PCM WAV and matching .txt transcript.
    """
    try:
        from faster_whisper import WhisperModel
        asr = WhisperModel("base", device="cpu", compute_type="int8")
        
        # Temporary raw file for ASR alignment
        tmp_raw = out_wav_path.replace(".wav", "_raw_tmp.wav")
        sf.write(tmp_raw, clip_data, sr, subtype="PCM_16")
        
        segments, _ = asr.transcribe(tmp_raw, word_timestamps=True)
        words = []
        for s in segments:
            if s.words:
                words.extend(s.words)
        
        try:
            if os.path.exists(tmp_raw):
                os.remove(tmp_raw)
        except Exception:
            pass

        if words:
            # Cut at the exact end of the last complete word + 100ms natural vocal decay
            last_word = words[-1]
            end_sample = int(min(len(clip_data), (last_word.end + 0.10) * sr))
            trimmed_data = clip_data[:end_sample].copy()
            clean_text = " ".join([w.word.strip() for w in words]).strip()
        else:
            trimmed_data = clip_data.copy()
            clean_text = rough_text.strip()

    except Exception as e:
        logger.debug(f"Reference ASR refinement fallback: {e}")
        trimmed_data = clip_data.copy()
        clean_text = rough_text.strip()

    # Smooth 20ms Hann boundary envelope
    fade_len = min(int(0.020 * sr), len(trimmed_data) // 4)
    if fade_len > 1:
        t = np.linspace(0.0, np.pi, fade_len, dtype=np.float32)
        trimmed_data[:fade_len] *= 0.5 * (1.0 - np.cos(t))
        trimmed_data[-fade_len:] *= 0.5 * (1.0 + np.cos(t))

    # Peak normalize
    max_val = np.abs(trimmed_data).max()
    if max_val > 0.003:
        trimmed_data = (trimmed_data / max_val) * 0.92

    sf.write(out_wav_path, trimmed_data, sr, subtype="PCM_16")
    
    # Save accompanying text file for instant zero-shot prompt creation
    txt_path = os.path.splitext(out_wav_path)[0] + ".txt"
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(clean_text)
    except Exception:
        pass

    return out_wav_path, clean_text


def extract_character_voice_reference(vocals_path: str, segments: list[dict], output_dir: str) -> str:
    """
    Extracts the cleanest 5-10s speech passage of the main character from vocals_path.
    Aligns audio and transcript at word boundaries for studio-grade voice cloning.
    """
    if not vocals_path or not os.path.exists(vocals_path) or not segments:
        logger.warning("Vocal track or segments missing for voice extraction.")
        return ""

    os.makedirs(output_dir, exist_ok=True)
    out_ref_wav = os.path.join(output_dir, "auto_extracted_character_voice.wav")

    try:
        data, sr = sf.read(vocals_path)
        if data.ndim > 1:
            data = data.mean(axis=1)

        best_seg = None
        best_dur = 0.0

        for seg in segments:
            dur = float(seg.get("end", 0)) - float(seg.get("start", 0))
            if dur > best_dur and MIN_REF_DURATION_S <= dur <= MAX_REF_DURATION_S:
                best_dur = dur
                best_seg = seg

        if not best_seg:
            best_seg = max(segments, key=lambda s: float(s.get("end", 0)) - float(s.get("start", 0)))
            best_dur = float(best_seg.get("end", 0)) - float(best_seg.get("start", 0))

        start_s = max(0.0, float(best_seg["start"]))
        dur_s = min(MAX_REF_DURATION_S, max(MIN_REF_DURATION_S, float(best_seg["end"]) - start_s))
        start_sample = int(start_s * sr)
        end_sample = min(len(data), start_sample + int(dur_s * sr))
        clip_data = data[start_sample:end_sample].astype(np.float32)

        rough_text = best_seg.get("text_original", best_seg.get("text", ""))
        ref_path, clean_text = _align_and_trim_reference(clip_data, sr, rough_text, out_ref_wav)
        logger.info(f"Extracted studio voice reference ({len(clip_data)/sr:.1f}s): {ref_path}")
        return ref_path

    except Exception as e:
        logger.error(f"Failed to extract character voice reference: {e}")
        return ""


def extract_all_speakers_references(vocals_path: str, segments: list[dict], output_dir: str) -> dict[str, dict]:
    """
    Extracts the cleanest 5-12s audio sample for EVERY distinct speaker in this project.
    Returns:
    {
        "SPEAKER_00": {
            "ref_audio": "/path/to/ref_voice_SPEAKER_00.wav",
            "ref_text": "...",
            "duration": 6.8,
            "sample_text": "...",
            "label": "[DỰ ÁN] Giọng gốc SPEAKER_00"
        },
        ...
    }
    """
    if not vocals_path or not os.path.exists(vocals_path) or not segments:
        return {}

    os.makedirs(output_dir, exist_ok=True)
    results = {}

    try:
        data, sr = sf.read(vocals_path)
        if data.ndim > 1:
            data = data.mean(axis=1)
        data = np.array(data, dtype=np.float32, copy=True)

        speakers = sorted(list(set(seg.get("speaker", "SPEAKER_00") for seg in segments)))

        for spk in speakers:
            spk_segs = [s for s in segments if s.get("speaker", "SPEAKER_00") == spk]
            if not spk_segs:
                continue

            # Find longest clean single segment for this speaker
            best_seg = None
            best_dur = 0.0
            for s in spk_segs:
                dur = float(s.get("end", 0)) - float(s.get("start", 0))
                if dur > best_dur:
                    best_dur = dur
                    best_seg = s

            if not best_seg:
                continue

            start_s = max(0.0, float(best_seg.get("start", 0.0)))
            dur_s = min(MAX_REF_DURATION_S, max(MIN_REF_DURATION_S, float(best_seg.get("end", start_s + 4.0)) - start_s))

            start_sample = int(start_s * sr)
            end_sample = min(len(data), start_sample + int(dur_s * sr))
            clip_data = data[start_sample:end_sample].copy()

            out_spk_wav = os.path.join(output_dir, f"ref_voice_{spk}.wav")
            rough_text = best_seg.get("text_original", best_seg.get("text", ""))
            ref_path, clean_text = _align_and_trim_reference(clip_data, sr, rough_text, out_spk_wav)

            results[spk] = {
                "ref_audio": out_spk_wav,
                "ref_text": clean_text,
                "duration": len(clip_data) / sr,
                "sample_text": clean_text or rough_text,
                "label": f"[DỰ ÁN] Giọng gốc {spk} ({len(clip_data)/sr:.1f}s)"
            }
            logger.info(f"Extracted studio voice reference for {spk}: {out_spk_wav}")

        return results

    except Exception as e:
        logger.error(f"Multi-speaker reference extraction failed: {e}")
        return {}
