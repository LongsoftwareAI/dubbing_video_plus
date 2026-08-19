"""
Source Control & GitHub Backup Helper — Dubbing Video Plus+
Allows 1-click Git initialization, commit, and push to user's remote GitHub repository.
"""
import os
import subprocess
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd, cwd=CURRENT_DIR):
    print(f"[*] Chạy lệnh: {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd, text=True)
    return res.returncode == 0

def setup_and_push_github(remote_url=None):
    print("=" * 60)
    print("   🚀 DUBBING VIDEO PLUS+ — GITHUB BACKUP & SYNC")
    print("=" * 60)
    
    # 1. Check if git is installed
    if not run_cmd("git --version"):
        print("[!] Lỗi: Máy tính chưa cài đặt Git. Vui lòng cài Git từ https://git-scm.com/")
        return

    # 2. Check or initialize git repo in test_mini_tool
    git_dir = os.path.join(CURRENT_DIR, ".git")
    if not os.path.exists(git_dir):
        print("[+] Đang khởi tạo Git repository cho Dubbing Video Plus+...")
        run_cmd("git init")
        run_cmd("git branch -M main")

    # 3. Add files and commit
    print("[+] Đang chuẩn bị các file mã nguồn...")
    run_cmd("git add .")
    run_cmd('git commit -m "feat: initial commit for Dubbing Video Plus+"')

    # 4. Set remote origin if provided
    if not remote_url:
        print("\n" + "-" * 60)
        remote_url = input("👉 Nhập URL GitHub repository của bạn (Ví dụ: https://github.com/username/dubbing-video-plus.git): ").strip()

    if remote_url:
        run_cmd(f"git remote remove origin")
        run_cmd(f"git remote add origin {remote_url}")
        print(f"[+] Đang đẩy mã nguồn lên GitHub ({remote_url})...")
        success = run_cmd("git push -u origin main --force")
        if success:
            print("\n🎉 ĐÃ BACKUP & ĐẨY CODE LÊN GITHUB THÀNH CÔNG!")
        else:
            print("\n[!] Không thể push code. Vui lòng kiểm tra quyền truy cập GitHub token/SSH.")
    else:
        print("[i] Đã lưu commit cục bộ (Local Git Commit). Bạn có thể push sau bất kỳ lúc nào!")

if __name__ == "__main__":
    remote = sys.argv[1] if len(sys.argv) > 1 else None
    setup_and_push_github(remote)
