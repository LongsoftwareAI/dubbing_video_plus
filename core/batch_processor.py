"""
Batch video dubbing automation processor.
Scans folders, manages processing queues, and handles unattended execution.
"""
import os
import re
import threading
import logging
from typing import Callable, Optional

from test_mini_tool.config import OUTPUT_DIR, DEFAULT_TARGET_LANG
from test_mini_tool.core.dub_engine import process_video_dubbing

logger = logging.getLogger("mini_dubber.batch")

SUPPORTED_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}

class BatchProcessor:
    def __init__(self):
        self.is_running = False
        self.should_stop = False
        self._thread: Optional[threading.Thread] = None

    def scan_folder(self, folder_path: str) -> list[str]:
        """Scans input directory for supported video files."""
        if not os.path.exists(folder_path):
            return []
        
        video_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in SUPPORTED_EXTS:
                    video_files.append(os.path.join(root, file))
        return sorted(video_files)

    def start_batch(
        self,
        file_list: list[str],
        target_lang: str = DEFAULT_TARGET_LANG,
        tts_voice: str = "vi-VN-HoaiMyNeural",
        output_folder: str = OUTPUT_DIR,
        on_progress: Optional[Callable[[int, int, str, float], None]] = None,
        on_complete: Optional[Callable[[list[str]], None]] = None
    ):
        """Starts batch execution in a background thread."""
        if self.is_running:
            logger.warning("Batch process already running.")
            return

        self.is_running = True
        self.should_stop = False

        def _worker():
            results = []
            total = len(file_list)

            for idx, video_path in enumerate(file_list):
                if self.should_stop:
                    logger.info("Batch processing stopped by user.")
                    break

                from datetime import datetime
                video_name = os.path.basename(video_path)
                clean_title = re.sub(r'[\\/*?:"<>|]', '_', os.path.splitext(video_name)[0]).strip() or "video"
                timestamp_str = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
                out_path = os.path.join(output_folder, f"{timestamp_str}_{clean_title}.mp4")

                def _item_prog(pct: float, msg: str):
                    if on_progress:
                        on_progress(idx + 1, total, video_name, pct)

                try:
                    res = process_video_dubbing(
                        video_path=video_path,
                        target_lang=target_lang,
                        tts_voice=tts_voice,
                        output_path=out_path,
                        progress_callback=_item_prog
                    )
                    results.append(res)
                except Exception as e:
                    logger.error(f"Error processing {video_name}: {e}")

            self.is_running = False
            if on_complete:
                on_complete(results)

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def stop_batch(self):
        """Signals batch processor to stop."""
        self.should_stop = True
