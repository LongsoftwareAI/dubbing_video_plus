import os
import sys
import psutil
import time

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
for p in [CURRENT_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from test_mini_tool.config import CACHE_DIR, OUTPUT_DIR

def main():
    print("=== 1. ACTIVE PYTHON PROCESSES ===", flush=True)
    py_procs = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 'create_time']):
        try:
            cmd = ' '.join(p.info['cmdline'] or [])
            if 'python' in p.info['name'].lower() and ('main.py' in cmd or 'omivoice' in cmd):
                py_procs.append({
                    'pid': p.info['pid'],
                    'cmd': cmd[:90],
                    'mem_mb': p.info['memory_info'].rss / 1024 / 1024,
                    'running_sec': time.time() - p.info['create_time']
                })
        except Exception:
            pass

    print(f"Total Python App Processes: {len(py_procs)}", flush=True)
    for proc in py_procs:
        print(f"  * PID {proc['pid']}: {proc['cmd']} | RAM: {proc['mem_mb']:.1f} MB | Uptime: {proc['running_sec']:.0f}s ({proc['running_sec']/60:.1f} mins)", flush=True)

    print("\n=== 2. RECENTLY MODIFIED FILES IN CACHE / OUTPUT (LAST 30 MINS) ===", flush=True)
    now = time.time()
    recent_files = []
    for check_dir in [CACHE_DIR, OUTPUT_DIR]:
        if not os.path.exists(check_dir):
            continue
        for root, dirs, files in os.walk(check_dir):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(fp)
                    if now - mtime < 1800: # 30 mins
                        recent_files.append((mtime, fp, os.path.getsize(fp)))
                except OSError:
                    pass

    recent_files.sort(key=lambda x: x[0], reverse=True)
    if recent_files:
        print(f"Found {len(recent_files)} files created/modified in the last 30 minutes:")
        for mtime, fp, sz in recent_files[:10]:
            ago = now - mtime
            print(f"  * [{ago:.0f}s ago] {fp} ({sz / 1024:.1f} KB)", flush=True)
    else:
        print("No files modified in the last 30 mins (System is in IDLE / waiting for user click).", flush=True)

    print("\n=== 3. GPU CUDA STATUS ===", flush=True)
    try:
        import torch
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}", flush=True)
            alloc = torch.cuda.memory_allocated(0) / 1024**3
            res = torch.cuda.memory_reserved(0) / 1024**3
            total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"VRAM: Allocated {alloc:.2f} GB / Reserved {res:.2f} GB / Total {total:.2f} GB", flush=True)
        else:
            print("CUDA is not available.", flush=True)
    except Exception as e:
        print(f"GPU check error: {e}", flush=True)

if __name__ == "__main__":
    main()
