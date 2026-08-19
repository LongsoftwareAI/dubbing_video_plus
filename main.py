"""
Entry point for launching Mini Video Dubber Desktop App.
Usage:
    python test_mini_tool/main.py
"""
import os
import sys
import tkinter as tk

# Ensure current directory and root repo directory are in python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from ui.app_window import MiniDubberApp

def main():
    root = tk.Tk()
    app = MiniDubberApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
