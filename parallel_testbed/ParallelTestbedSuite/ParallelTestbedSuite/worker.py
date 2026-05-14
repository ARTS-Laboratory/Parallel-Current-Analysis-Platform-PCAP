# -*- coding: utf-8 -*-
"""
Created on Thu Feb 26 21:26:35 2026

@author: malichi
"""

#worker.py
import threading
from cache import build_cache_for_folder

workers = {}

def ensure_cache_worker(folder_name: str):
    if folder_name in workers:
        t = workers[folder_name]
        if t.is_alive():
            return

    def run_once():
        print(f"[CACHE] worker started for {folder_name}")
        build_cache_for_folder(folder_name)
        print(f"[CACHE] worker finished for {folder_name}")

    t = threading.Thread(target=run_once, daemon=True)
    workers[folder_name] = t
    t.start()