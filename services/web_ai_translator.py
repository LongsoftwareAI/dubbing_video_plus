"""
Web AI Zero-Token & VoxDub Cách A Translation Service — Dubbing Video Plus+

Features:
1. VoxDub Cách A Engine: Formats transcript segments into structured prompts tailored for cinematic video dubbing.
2. Web AI Zero-Token Automation (Inspired by openclaw-zero-token):
   - Automates sending prompts to Web AI (Gemini, ChatGPT, Claude, DeepSeek) without paid API tokens.
   - Browser interaction & clipboard synchronization.
3. Robust Fallback Parsers: Automatically extracts translated dialogue from JSON, Markdown blocks, or numbered lists.
4. 100% Isolated Thread Execution: Runs completely separate from the core pipeline to prevent any side effects.
"""
import os
import re
import json
import time
import logging
import threading
import webbrowser
import urllib.parse
from typing import List, Dict, Callable, Optional

logger = logging.getLogger("dubbing_plus.web_ai")


# ─── 1. VOXDUB CÁCH A PROMPT BUILDER ─────────────────────────────────────────

VOXDUB_SYSTEM_PROMPT = """Bạn là chuyên gia biên kịch và dịch thuật lồng tiếng phim/video chuyên nghiệp.
Nhiệm vụ của bạn là dịch toàn bộ các câu thoại sau đây sang TIẾNG VIỆT tự nhiên, mượt mà, phù hợp với văn phong nói chuyện của nhân vật (Cinematic Dubbing Style).

QUY TẮC BẮT BUỘC:
1. Dịch chuẩn nghĩa, văn phong tự nhiên như người Việt nói chuyện trong phim.
2. GIỮ NGUYÊN cấu trúc định dạng JSON phân đoạn (id, text). KHÔNG được gộp câu hoặc làm mất ID.
3. Chỉ trả về duy nhất khối mã JSON hợp lệ (bắt đầu bằng [ và kết thúc bằng ]), không thêm lời chào hay giải thích ngoài JSON.

Dữ liệu kịch bản gốc cần dịch:
"""

def build_voxdub_prompt(segments: List[Dict], target_lang: str = "vi", style: str = "cinematic") -> str:
    """
    Builds a structured VoxDub Cách A prompt from transcript segments.
    """
    simplified_list = []
    for s in segments:
        text = s.get("text_original") or s.get("text") or ""
        simplified_list.append({
            "id": s.get("id", 0),
            "orig": text.strip()
        })

    json_str = json.dumps(simplified_list, ensure_ascii=False, indent=2)
    prompt = f"{VOXDUB_SYSTEM_PROMPT}\n{json_str}\n\nĐịnh dạng trả về mong muốn:\n[\n  {{\"id\": 0, \"text\": \"Lời dịch tiếng Việt tương ứng...\"}},\n  ...\n]"
    return prompt


def parse_voxdub_llm_response(raw_text: str, original_segments: List[Dict]) -> List[Dict]:
    """
    Parses LLM response (JSON, Markdown code blocks, or numbered lines) and maps back to original segments.
    """
    if not raw_text or not raw_text.strip():
        logger.warning("Empty response from LLM parser.")
        return original_segments

    cleaned = raw_text.strip()
    
    # 1. Try extracting from markdown code block ```json ... ```
    code_block_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", cleaned, re.DOTALL)
    if code_block_match:
        cleaned = code_block_match.group(1).strip()
    else:
        # Try finding the first '[' and last ']'
        start_idx = cleaned.find("[")
        end_idx = cleaned.rfind("]")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx:end_idx + 1]

    # 2. Try JSON parse
    id_to_translated = {}
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    iid = item.get("id")
                    t_text = item.get("text") or item.get("trans") or item.get("vietnamese") or ""
                    if iid is not None and t_text:
                        id_to_translated[int(iid)] = str(t_text).strip()
    except Exception as e:
        logger.warning(f"Standard JSON parse failed ({e}), falling back to regex extraction...")

    # 3. Regex Fallback: extract pattern {"id": X, "text": "..."}
    if not id_to_translated:
        pattern = r'\{\s*"id"\s*:\s*(\d+)\s*,\s*"(?:text|trans|vietnamese)"\s*:\s*"([^"]+)"\s*\}'
        for m in re.finditer(pattern, raw_text):
            try:
                iid = int(m.group(1))
                text_val = m.group(2).strip()
                if text_val:
                    id_to_translated[iid] = text_val
            except Exception:
                pass

    # 4. Line-by-line Numbered Fallback (e.g. 1. Lời dịch...)
    if not id_to_translated:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        num_pattern = r'^(?:\[?(\d+)\]?[\.:\-])\s*(.*)$'
        for line in lines:
            m = re.match(num_pattern, line)
            if m:
                try:
                    iid = int(m.group(1))
                    text_val = m.group(2).strip().strip('"').strip("'")
                    if text_val:
                        id_to_translated[iid] = text_val
                except Exception:
                    pass

    # Reconstruct segments list
    updated_segments = []
    for idx, seg in enumerate(original_segments):
        new_seg = dict(seg)
        orig = seg.get("text_original") or seg.get("text") or ""
        new_seg["text_original"] = orig
        
        seg_id = seg.get("id", idx)
        if seg_id in id_to_translated:
            new_seg["text"] = id_to_translated[seg_id]
        elif idx in id_to_translated:
            new_seg["text"] = id_to_translated[idx]
        else:
            new_seg["text"] = orig
            
        updated_segments.append(new_seg)

    match_count = sum(1 for s in updated_segments if s.get("text") != s.get("text_original"))
    logger.info(f"Parsed {match_count}/{len(updated_segments)} segments successfully.")
    return updated_segments


# ─── 2. ZERO-TOKEN WEB AI AUTOMATION CONTROLLER ─────────────────────────────

class WebAIAutomationEngine:
    """
    Manages Zero-Token Web AI sessions and automated clipboard / browser workflows.
    """
    SUPPORTED_TARGETS = {
        "gemini": {
            "name": "Google Gemini Web",
            "url": "https://gemini.google.com/app",
            "desc": "Miễn phí, tốc độ phản hồi cực nhanh, văn phong tiếng Việt rất mượt mà."
        },
        "chatgpt": {
            "name": "ChatGPT Web (OpenAI)",
            "url": "https://chatgpt.com",
            "desc": "Mô hình GPT-4o / GPT-4o-mini miễn phí qua giao diện web."
        },
        "claude": {
            "name": "Claude AI Web (Anthropic)",
            "url": "https://claude.ai/new",
            "desc": "Khả năng dịch văn học và ngữ cảnh sâu sắc."
        },
        "deepseek": {
            "name": "DeepSeek Chat Web",
            "url": "https://chat.deepseek.com",
            "desc": "Mô hình DeepSeek-V3 / R1 thông minh và miễn phí."
        }
    }

    @staticmethod
    def copy_prompt_to_clipboard(prompt_text: str) -> bool:
        """Copies generated prompt to system clipboard."""
        try:
            import tkinter as tk
            r = tk.Tk()
            r.withdraw()
            r.clipboard_clear()
            r.clipboard_append(prompt_text)
            r.update()
            r.destroy()
            return True
        except Exception as e:
            logger.error(f"Clipboard copy failed: {e}")
            return False

    @staticmethod
    def get_clipboard_text() -> str:
        """Reads current text from system clipboard."""
        try:
            import tkinter as tk
            r = tk.Tk()
            r.withdraw()
            text = r.clipboard_get()
            r.destroy()
            return text or ""
        except Exception as e:
            logger.error(f"Clipboard get failed: {e}")
            return ""

    @classmethod
    def open_web_ai(cls, target: str = "gemini") -> str:
        """Opens the selected Web AI in user's default browser."""
        target_key = target.lower()
        info = cls.SUPPORTED_TARGETS.get(target_key, cls.SUPPORTED_TARGETS["gemini"])
        webbrowser.open(info["url"])
        return info["name"]


# ─── 3. ASYNC TRANSLATION WORKER (ISOLATED THREAD) ───────────────────────────

def translate_segments_voxdub_async(
    segments: List[Dict],
    on_success: Callable[[List[Dict]], None],
    on_error: Callable[[str], None],
    target_lang: str = "vi",
    style: str = "cinematic"
):
    """
    Asynchronous helper to format segments and prepare VoxDub Cách A batch.
    """
    def _worker():
        try:
            prompt = build_voxdub_prompt(segments, target_lang=target_lang, style=style)
            WebAIAutomationEngine.copy_prompt_to_clipboard(prompt)
            on_success(segments)
        except Exception as e:
            on_error(str(e))

    threading.Thread(target=_worker, daemon=True).start()
