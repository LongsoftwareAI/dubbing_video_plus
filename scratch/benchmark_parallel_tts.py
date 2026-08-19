"""
Benchmark Sequential vs Concurrent Parallel TTS Synthesis
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
for p in [CURRENT_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import CACHE_DIR
from services.tts_service import synthesize_segment

test_sentences = [
    "Xin chào các bạn, đây là thử nghiệm tối ưu hóa tốc độ.",
    "Hệ thống lồng tiếng AI chạy song song đa luồng siêu tốc.",
    "Thời gian xử lý giọng đọc giảm từ 5 phút xuống còn vài chục giây.",
    "Âm thanh đầu ra vẫn đảm bảo chuẩn chất lượng phòng thu 24kHz.",
    "Khả năng mở rộng cho video dài hàng giờ với hiệu năng vượt trội.",
    "Mỗi câu thoại được xử lý độc lập và ghép nối mượt mà.",
    "Không còn tình trạng chờ đợi lâu khi xuất video.",
    "Tự động giải phóng bộ nhớ đệm và tối ưu hóa tài nguyên phần cứng."
]

def benchmark():
    out_dir = os.path.join(CACHE_DIR, "bench_parallel")
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Sequential Benchmark
    print("1. Testing Sequential Synthesis (1 by 1)...")
    t0 = time.time()
    for idx, text in enumerate(test_sentences):
        wav = os.path.join(out_dir, f"seq_{idx}.wav")
        synthesize_segment(text, wav, voice="vi-VN-NamMinhNeural")
    t_seq = time.time() - t0
    print(f"   Sequential Time for {len(test_sentences)} sentences: {t_seq:.2f}s ({t_seq/len(test_sentences):.2f}s per sentence)")
    
    # 2. Parallel Benchmark (ThreadPool 6 workers)
    print("\n2. Testing Parallel Concurrent Synthesis (6 Workers)...")
    t0 = time.time()
    def _worker(item):
        idx, text = item
        wav = os.path.join(out_dir, f"par_{idx}.wav")
        synthesize_segment(text, wav, voice="vi-VN-NamMinhNeural")
        return idx
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(_worker, (idx, text)) for idx, text in enumerate(test_sentences)]
        for f in as_completed(futures):
            f.result()
    t_par = time.time() - t0
    print(f"   Parallel Time for {len(test_sentences)} sentences: {t_par:.2f}s ({t_par/len(test_sentences):.2f}s per sentence)")
    print(f"\n🚀 SPEEDUP: {t_seq / t_par:.1f}x FASTER!")

if __name__ == "__main__":
    benchmark()
