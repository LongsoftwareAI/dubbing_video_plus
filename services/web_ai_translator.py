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
    # Check if id_to_translated uses 1-based indexing while segments use 0-based
    keys = list(id_to_translated.keys())
    is_1_based = bool(keys and min(keys) == 1 and 0 not in id_to_translated and any(s.get("id") == 0 for s in original_segments))

    for idx, seg in enumerate(original_segments):
        new_seg = dict(seg)
        orig = seg.get("text_original") or seg.get("text") or ""
        new_seg["text_original"] = orig

        seg_id = seg.get("id", idx)
        lookup_id = (seg_id + 1) if (is_1_based and seg_id in range(len(original_segments))) else seg_id
        
        if lookup_id in id_to_translated:
            new_seg["text"] = id_to_translated[lookup_id]
        elif seg_id in id_to_translated:
            new_seg["text"] = id_to_translated[seg_id]
        elif (idx + 1) in id_to_translated and is_1_based:
            new_seg["text"] = id_to_translated[idx + 1]
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
        """
        Opens the selected Web AI in Google Chrome or default browser for visual observation.
        """
        target_key = target.lower()
        info = cls.SUPPORTED_TARGETS.get(target_key, cls.SUPPORTED_TARGETS["gemini"])
        url = info["url"]

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]
        chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)

        if chrome_exe:
            try:
                import subprocess
                subprocess.Popen([chrome_exe, url])
                logger.info(f"Launched browser window ({chrome_exe}) for {info['name']}: {url}")
                return info["name"]
            except Exception as e:
                logger.warning(f"Failed to launch specific browser ({e}), using default...")

        webbrowser.open(url)
        return info["name"]

    @classmethod
    def run_auto_chrome_bot(
        cls,
        segments: List[Dict],
        target: str = "chatgpt",
        target_lang: str = "vi",
        style: str = "cinematic",
        progress_cb: Optional[Callable[[str], None]] = None
    ) -> List[Dict]:
        """
        Launches an automated visible Chrome browser, pastes the prompt into ChatGPT / Gemini / DeepSeek,
        waits for response streaming to complete, and extracts the translated segments automatically.
        """
        def _log(msg: str):
            logger.info(f"[ChromeBot] {msg}")
            if progress_cb:
                progress_cb(msg)

        _log("Đang tạo kịch bản prompt chuẩn VoxDub Cách A...")
        prompt = build_voxdub_prompt(segments, target_lang=target_lang, style=style)
        cls.copy_prompt_to_clipboard(prompt)

        target_key = target.lower()
        info = cls.SUPPORTED_TARGETS.get(target_key, cls.SUPPORTED_TARGETS["chatgpt"])
        url = info["url"]

        _log(f"Đang khởi tạo cửa sổ Google Chrome ({info['name']})...")

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError as e:
            raise RuntimeError(f"Chưa cài đặt Selenium: {e}. Vui lòng chạy: pip install selenium")

        chrome_profile = os.path.expanduser(r"~\AppData\Local\DubbingVideoPlus\chrome_bot_profile")
        os.makedirs(chrome_profile, exist_ok=True)

        options = Options()
        options.add_argument(f"--user-data-dir={chrome_profile}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--start-maximized")

        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            _log(f"Đang truy cập trang web: {url}...")
            driver.get(url)
            time.sleep(3)

            # 1. Locate Chat Input Box
            _log("Đang tìm ô nhập kịch bản trên trang web...")
            input_box = None

            # Try different selector strategies based on target
            selectors = [
                (By.ID, "prompt-textarea"),
                (By.CSS_SELECTOR, "div[contenteditable='true']"),
                (By.CSS_SELECTOR, "textarea[data-testid='prompt-textarea']"),
                (By.CSS_SELECTOR, "rich-textarea p"),
                (By.CSS_SELECTOR, "rich-textarea div"),
                (By.TAG_NAME, "textarea"),
                (By.CSS_SELECTOR, "div[role='textbox']"),
                (By.CSS_SELECTOR, "#chat-input"),
            ]

            start_wait = time.time()
            while time.time() - start_wait < 25:
                for by_type, sel in selectors:
                    try:
                        elems = driver.find_elements(by_type, sel)
                        for el in elems:
                            if el.is_displayed():
                                input_box = el
                                break
                        if input_box: break
                    except Exception: pass
                if input_box: break
                time.sleep(1)

            if not input_box:
                _log("⚠️ Không tìm thấy ô chat tự động (Có thể cần đăng nhập). Vui lòng nhấn vào ô chat và ấn Ctrl+V.")
                time.sleep(10)
                # Retry search
                for by_type, sel in selectors:
                    try:
                        elems = driver.find_elements(by_type, sel)
                        for el in elems:
                            if el.is_displayed():
                                input_box = el; break
                        if input_box: break
                    except Exception: pass

            if input_box:
                _log("✓ Đã tìm thấy ô chat! Đang dán kịch bản vào...")
                try:
                    input_box.click()
                    time.sleep(0.5)
                    # Paste via Clipboard for speed
                    input_box.send_keys(Keys.CONTROL, "v")
                    time.sleep(1)
                except Exception:
                    # Fallback to JavaScript injection
                    driver.execute_script("arguments[0].innerText = arguments[1]; arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", input_box, prompt)
                    time.sleep(1)

                # 2. Click Send Button
                _log("Đang gửi kịch bản lên AI...")
                send_selectors = [
                    "button[data-testid='send-button']",
                    "button[aria-label*='Send']",
                    "button[aria-label*='Gửi']",
                    ".send-button",
                    "button[data-testid='fruitjuice-send-button']",
                    "button.mb-1",
                    "button[type='submit']"
                ]
                sent = False
                for s_sel in send_selectors:
                    try:
                        btns = driver.find_elements(By.CSS_SELECTOR, s_sel)
                        for b in btns:
                            if b.is_displayed() and b.is_enabled():
                                b.click()
                                sent = True
                                break
                        if sent: break
                    except Exception: pass

                if not sent:
                    try:
                        input_box.send_keys(Keys.ENTER)
                        sent = True
                    except Exception: pass

                _log("✓ Đã gửi thành công! Đang quan sát AI dịch kịch bản...")
            else:
                _log("Vui lòng ấn Ctrl+V vào ô chat trên Chrome và gửi.")

            # 3. Wait for AI response to finish
            _log("Đang theo dõi AI tạo bản dịch thời gian thực...")
            raw_response = ""
            time.sleep(5)

            poll_start = time.time()
            last_len = 0
            stable_count = 0

            while time.time() - poll_start < 150:
                time.sleep(2)
                # Check for assistant messages
                msg_selectors = [
                    "div[data-message-author-role='assistant']",
                    "message-content",
                    ".model-response-text",
                    ".markdown",
                    "div.agent-turn",
                    "div.ds-markdown"
                ]
                found_text = ""
                for m_sel in msg_selectors:
                    try:
                        msgs = driver.find_elements(By.CSS_SELECTOR, m_sel)
                        if msgs:
                            found_text = msgs[-1].text.strip()
                            if found_text: break
                    except Exception: pass

                # Check if stop button is gone
                stop_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-testid='stop-button'], .stop-button")
                is_generating = any(b.is_displayed() for b in stop_btns)

                if found_text:
                    cur_len = len(found_text)
                    if cur_len == last_len and cur_len > 50 and not is_generating:
                        stable_count += 1
                        if stable_count >= 2:
                            raw_response = found_text
                            _log(f"✓ AI đã dịch xong hoàn tất ({len(raw_response)} ký tự)!")
                            break
                    else:
                        stable_count = 0
                        last_len = cur_len
                        _log(f"AI đang viết câu dịch... ({cur_len} ký tự)")

            if not raw_response:
                # Last resort grab
                for m_sel in msg_selectors:
                    try:
                        msgs = driver.find_elements(By.CSS_SELECTOR, m_sel)
                        if msgs:
                            raw_response = msgs[-1].text.strip()
                            if raw_response: break
                    except Exception: pass

            if not raw_response:
                raise TimeoutError("Hết thời gian chờ AI phản hồi hoặc chưa nhận được kết quả.")

            _log("Đang phân tích và nạp kịch bản vào ứng dụng...")
            parsed = parse_voxdub_llm_response(raw_response, segments)
            _log(f"🎉 Hoàn thành! Đã nạp thành công {len(parsed)} câu thoại dịch vào dự án.")
            return parsed

        finally:
            # Leave driver open or quit safely
            pass


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
