# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 16:27:03 2026

@author: malichi
"""
# engine.py
from pathlib import Path
import pandas as pd
import re
import os
import glob

BASE_DIR = Path(r"C:\Users\malic\Desktop\ParallelTestbedSuite")

CHUNK_SIZE = 20000

def load_chunk(folder, chunk_index):
    chunk_dir = os.path.join(BASE_DIR, folder, "cache", f"chunk_{chunk_index:04d}")
    print(chunk_index)
    if not os.path.exists(chunk_dir):
        print("CHUNK DIR DOES NOT EXIST:", chunk_dir)
        return None

    pattern = os.path.join(chunk_dir, "part-*.parquet")
    files = glob.glob(pattern)

    print("LOADING CHUNK:", chunk_index)
    print("DIR:", chunk_dir)
    print("PATTERN:", pattern)
    print("FILES FOUND:", files)

    if not files:
        return None

    dfs = [pd.read_parquet(f) for f in files]
    return pd.concat(dfs, ignore_index=True)

def get_playback_window(folder, pointer, window_size):
    """Return (window_df, window_base) centered on pointer using 3-chunk architecture."""
    if pointer is None:
        return None, 0

    # Determine which chunk the pointer is in
    chunk_index = pointer // CHUNK_SIZE

    # Load chunk N-1, N, N+1
    df_prev = load_chunk(folder, chunk_index - 1)
    df_curr = load_chunk(folder, chunk_index)
    df_next = load_chunk(folder, chunk_index + 1)

    # Combine available chunks
    dfs = [d for d in (df_prev, df_curr, df_next) if d is not None]
    if not dfs:
        return None, 0

    # Determine the global index of the first row in the concatenated df
    if df_prev is not None:
        concat_base = (chunk_index - 1) * CHUNK_SIZE
        prev_len = df_prev.shape[0]
    else:
        concat_base = chunk_index * CHUNK_SIZE
        prev_len = 0

    df = pd.concat(dfs, ignore_index=True)

    # Compute pointer inside the concatenated df
    local_pointer = prev_len + (pointer % CHUNK_SIZE)

    # Slice window centered on local_pointer
    half = int(window_size) // 2
    lo = max(0, local_pointer - half)
    hi = min(len(df), lo + int(window_size))
    lo = max(0, hi - int(window_size))

    window_df = df.iloc[lo:hi].reset_index(drop=True)
    window_base = concat_base + lo
    return window_df, int(window_base)

def folder_path(folder_name: str) -> Path:
    p = Path(folder_name)
    if p.is_absolute():
        return p
    return BASE_DIR / folder_name

def list_raw_lvm(folder_name: str):
    folder = folder_path(folder_name)
    if not folder.exists():
        print(f"[ENGINE] folder does not exist: {folder}")
        return []
    return list(folder.glob("*.lvm"))

SEGMENT_ORDER = {
    "ChargeCycle": 1,
    "ChargeWait": 2,
    "DischargeCycle": 3,
    "DischargeWait": 4,
}

CYCLE_PATTERN = re.compile(
    r".*_(ChargeCycle|ChargeWait|DischargeCycle|DischargeWait)(\d+)", re.IGNORECASE
)

def ordered_lvm_files(folder_name: str):
    files = list_raw_lvm(folder_name)

    def parse_key(path: Path):
        name = path.stem
        m = CYCLE_PATTERN.match(name)
        if not m:
            return (999999, 999999)
        segment = m.group(1)
        cycle = int(m.group(2))
        segment = segment[0].upper() + segment[1:]
        return (cycle, SEGMENT_ORDER.get(segment, 999))

    return sorted(files, key=parse_key)

def load_lvm_file(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, sep="\t", engine="python")
        df["SourceFile"] = path.name
        return df
    except Exception as e:
        print(f"[ENGINE] Failed to load {path}: {e}")
        return pd.DataFrame()
