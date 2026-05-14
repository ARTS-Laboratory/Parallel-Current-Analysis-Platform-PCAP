# -*- coding: utf-8 -*-
"""
Created on Tue Mar  3 11:21:03 2026

@author: malichi
"""

from pathlib import Path
import pandas as pd
from engine import folder_path

folder_name = "test2"
folder = folder_path(folder_name)

cache_dir = folder / "cache"
chunks = sorted(cache_dir.glob("chunk_*"))
dfs=[]
if not chunks:
    print("No chunk folders found.")
else:
    for ch in chunks[:5]:  # inspect first 5 chunks
        parts = sorted(ch.glob("part-*.parquet"))
        if not parts:
            print(ch.name, "→ no parquet files")
            continue

        # pick the first available part file
        part_file = parts[0]
        try:
            df = pd.read_parquet(part_file)
        except Exception as e:
            print(ch.name, "→ failed to read parquet", part_file.name, ":", e)
            continue

        # prefer Time, fall back to Timestamp or dt_h, else show columns
        if "Time" in df.columns:
            time_vals = df["Time"].head().tolist()
            print(ch.name, "→ first 5 Time values:", time_vals)
        elif "Timestamp" in df.columns:
            time_vals = df["Timestamp"].head().tolist()
            print(ch.name, "→ first 5 Timestamp values (no Time column):", time_vals)
        elif "dt_h" in df.columns:
            time_vals = df["dt_h"].head().tolist()
            print(ch.name, "→ first 5 dt_h values (no Time column):", time_vals)
        else:
            print(ch.name, "→ no Time-like column; columns:", list(df.columns)[:20])
        dfs.append(df)