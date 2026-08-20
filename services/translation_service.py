"""
Translation service supporting offline NLLB-200 / Argos, free online Google / MyMemory,
API keys (DeepL / Microsoft), and local/remote LLM (OpenAI / Ollama / LM Studio).
"""
import logging
import os

logger = logging.getLogger("mini_dubber.translation")

TRANSLATION_PROVIDERS = {
    "google": "Google Translate (Online, Nhanh & Ổn định)",
    "deepl": "DeepL Translate (Online API Key)",
    "nllb": "NLLB-200 Meta (Local Offline, 200 Languages)",
    "argos": "Argos Translate (Local Offline)",
    "microsoft": "Microsoft Translator (Online API Key)",
    "mymemory": "MyMemory (Online, Miễn phí)",
    "openai": "LLM / Ollama (OpenAI-compatible Local API)",
}

def translate_segments(segments: list[dict], target_lang: str = "vi", engine: str = "google") -> list[dict]:
    """
    Translates transcript segments directly and cleanly using requested translation engine.
    Fast, reliable, and non-blocking with automatic fallback to Google Translate.
    """
    translated_segments = []
    
    for seg in segments:
        text_orig = seg.get("text", "")
        if not text_orig.strip():
            translated = ""
        else:
            translated = translate_text(text_orig, target_lang=target_lang, engine=engine)
            
        new_seg = dict(seg)
        new_seg["text_original"] = text_orig
        new_seg["text"] = translated if translated else text_orig
        translated_segments.append(new_seg)

    logger.info(f"Translated {len(translated_segments)} segments to '{target_lang}' using {engine}.")
    return translated_segments

def translate_text(text: str, target_lang: str = "vi", engine: str = "google") -> str:
    """
    Single string translation dispatcher covering all OmniVoice providers.
    """
    if not text.strip():
        return text

    eng = engine.lower()

    # 1. Google Translate (deep_translator)
    if eng == "google":
        try:
            from deep_translator import GoogleTranslator
            return GoogleTranslator(source="auto", target=target_lang).translate(text)
        except Exception as e:
            logger.warning(f"Google translate error: {e}")

    # 2. MyMemory
    elif eng == "mymemory":
        try:
            from deep_translator import MyMemoryTranslator
            return MyMemoryTranslator(source="auto", target=target_lang).translate(text)
        except Exception as e:
            logger.warning(f"MyMemory translate error: {e}")

    # 3. DeepL
    elif eng == "deepl":
        try:
            from deep_translator import DeeplTranslator
            api_key = os.environ.get("DEEPL_API_KEY", "")
            if api_key:
                return DeeplTranslator(api_key=api_key, source="auto", target=target_lang).translate(text)
            logger.warning("DEEPL_API_KEY not set.")
        except Exception as e:
            logger.warning(f"DeepL translate error: {e}")

    # 4. Microsoft Translator
    elif eng == "microsoft":
        try:
            from deep_translator import MicrosoftTranslator
            api_key = os.environ.get("MICROSOFT_API_KEY", "")
            if api_key:
                return MicrosoftTranslator(api_key=api_key, target=target_lang).translate(text)
            logger.warning("MICROSOFT_API_KEY not set.")
        except Exception as e:
            logger.warning(f"Microsoft translate error: {e}")

    # 5. Argos Translate (Offline)
    elif eng == "argos":
        try:
            import argostranslate.translate
            return argostranslate.translate.translate(text, "en", target_lang)
        except Exception as e:
            logger.warning(f"Argos translate error: {e}")

    # 6. NLLB-200 (Meta Transformers Model)
    elif eng == "nllb":
        try:
            from transformers import pipeline
            translator = pipeline("translation", model="facebook/nllb-200-distilled-600M")
            res = translator(text, max_length=512)
            return res[0]["translation_text"]
        except Exception as e:
            logger.warning(f"NLLB translate error: {e}")

    # 7. LLM / Ollama (OpenAI-compatible)
    elif eng in ("openai", "llm", "ollama"):
        try:
            import urllib.request
            import json
            base_url = os.environ.get("TRANSLATE_BASE_URL", "http://localhost:11434/v1")
            api_key = os.environ.get("TRANSLATE_API_KEY", "ollama")
            model_name = os.environ.get("TRANSLATE_MODEL", "llama3")
            
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": f"You are a cinematic dubbing translator. Translate the text to target language code '{target_lang}'. Reply ONLY with the target language translation text."},
                    {"role": "user", "content": text}
                ]
            }
            req = urllib.request.Request(f"{base_url}/chat/completions", data=json.dumps(payload).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"LLM translate error: {e}")

    # Fallback to Google if specific engine fails
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception:
        return text


def generate_manual_translate_pending_file(segments: list[dict], target_lang: str, job_dir: str) -> str:
    """
    VoxDub Manual Translation Workflow: Generates a structured TRANSLATE_PENDING.txt prompt
    file in the job directory, allowing users to copy transcript JSON to ChatGPT / Gemini
    and paste the translated JSON without needing API keys.
    """
    import json
    pending_txt_path = os.path.join(job_dir, "TRANSLATE_PENDING.txt")
    orig_json_path = os.path.join(job_dir, "transcript_original.json")

    # Save original transcript JSON
    with open(orig_json_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    prompt_instructions = (
        "=== VOXDUB HƯỚNG DẪN DỊCH BẢN THOẠI BẰNG CHATGPT / GEMINI ===\n\n"
        "Bước 1: Mở file 'transcript_original.json' trong cùng thư mục này và copy toàn bộ nội dung.\n"
        "Bước 2: Mở ChatGPT (https://chatgpt.com) hoặc Gemini (https://gemini.google.com) dán câu lệnh bên dưới:\n\n"
        f"--- BẮT ĐẦU CÂU LỆNH PROMPT ---\n"
        f"Hãy đóng vai là biên dịch viên phim chuyên nghiệp. Dịch toàn bộ mảng JSON kịch bản thoại dưới đây sang '{target_lang}'.\n"
        f"Yêu cầu:\n"
        f"1. Giữ nguyên toàn bộ cấu trúc JSON, mốc 'start', 'end', và 'speaker'.\n"
        f"2. Thay đổi giá trị của trường 'text' thành câu tiếng Việt tự nhiên, phù hợp thoại phim.\n"
        f"3. Chỉ trả về mã JSON hợp lệ, không kèm lời dẫn giải.\n\n"
        f"[DÁN NỘI DUNG MẢNG JSON TỪ transcript_original.json VÀO ĐÂY]\n"
        f"--- KẾT THÚC CÂU LỆNH PROMPT ---\n\n"
        "Bước 3: Sao chép mã JSON kết quả từ AI và lưu vào file 'transcript_vi.json' trong thư mục dự án.\n"
        "Bước 4: Quay lại ứng dụng VoxDub Studio và bấm 'Đã dịch xong, tiếp tục'.\n"
    )

    with open(pending_txt_path, "w", encoding="utf-8") as f:
        f.write(prompt_instructions)

    logger.info(f"Generated TRANSLATE_PENDING.txt prompt guide at: {pending_txt_path}")
    return pending_txt_path

