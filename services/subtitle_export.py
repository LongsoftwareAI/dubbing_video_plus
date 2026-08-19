"""
Subtitle export service — SRT / VTT generation from translated segments.
"""
import os
import logging

logger = logging.getLogger("mini_dubber.subtitles")

def _fmt_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def _fmt_vtt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def export_srt(segments: list[dict], output_path: str, dual_subs: bool = False, dual: bool = False, **kwargs) -> str:
    """Exports segments as .srt subtitle file. If dual/dual_subs, includes original + translated text."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    is_dual = bool(dual_subs or dual or kwargs.get("dual_subtitles", False))
    lines = []
    for idx, seg in enumerate(segments, 1):
        start = _fmt_srt_time(float(seg.get("start", 0.0)))
        end = _fmt_srt_time(float(seg.get("end", 0.0)))
        text = seg.get("text", "")
        if is_dual and seg.get("text_original"):
            text = f"{seg['text_original']}\n{text}"
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"Exported SRT: {output_path}")
    return output_path

def export_vtt(segments: list[dict], output_path: str, dual_subs: bool = False, dual: bool = False, **kwargs) -> str:
    """Exports segments as .vtt subtitle file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    is_dual = bool(dual_subs or dual or kwargs.get("dual_subtitles", False))
    lines = ["WEBVTT\n"]
    for idx, seg in enumerate(segments, 1):
        start = _fmt_vtt_time(float(seg.get("start", 0.0)))
        end = _fmt_vtt_time(float(seg.get("end", 0.0)))
        text = seg.get("text", "")
        if is_dual and seg.get("text_original"):
            text = f"{seg['text_original']}\n{text}"
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"Exported VTT: {output_path}")
    return output_path
