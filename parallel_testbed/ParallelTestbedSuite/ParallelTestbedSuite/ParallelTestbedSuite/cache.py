# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 16:27:43 2026

@author: malichi
"""

# cache.py
import pandas as pd
from pathlib import Path
import re
import numpy as np
from engine import folder_path, ordered_lvm_files, load_lvm_file

CHUNK_SIZE = 20000
CACHE_SUBDIR = "cache"

SEGMENT_ORDER = {
    "ChargeCycle": 1,
    "ChargeWait": 2,
    "DischargeCycle": 3,
    "DischargeWait": 4,
}

CYCLE_PATTERN = re.compile(
    r".*_(ChargeCycle|ChargeWait|DischargeCycle|DischargeWait)(\d+)", re.IGNORECASE
)

_HAS_RUN_CYCLE1 = False

def ensure_dirs(folder_name: str):
    folder = folder_path(folder_name)
    (folder / CACHE_SUBDIR).mkdir(parents=True, exist_ok=True)


def parse_segment_and_cycle(path: Path):
    name = path.stem
    m = CYCLE_PATTERN.match(name)
    if not m:
        return None, None
    segment = m.group(1)
    cycle = int(m.group(2))
    segment = segment[0].upper() + segment[1:]
    return segment, cycle


def group_files_by_cycle(folder_name: str):
    files = ordered_lvm_files(folder_name)
    cycles = {}
    for f in files:
        segment, cycle = parse_segment_and_cycle(f)
        if cycle is None:
            continue
        cycles.setdefault(cycle, []).append((SEGMENT_ORDER.get(segment, 999), f))
    for c in cycles:
        cycles[c] = [p for _, p in sorted(cycles[c], key=lambda x: x[0])]
    return dict(sorted(cycles.items(), key=lambda x: x[0]))


def add_dt_per_cycle(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["cycle_id", "Timestamp"]).copy()
    df["dt_h"] = 0.0
    for cid, g in df.groupby("cycle_id", sort=True):
        ts = g["Timestamp"].astype(float)
        if ts.max() > 10000:
            dt = ts.diff().fillna(0) / 1000.0 / 3600.0
        else:
            dt = ts.diff().fillna(0) / 3600.0
        df.loc[g.index, "dt_h"] = dt
    return df


def estimate_initial_soc_cycle1(df: pd.DataFrame, capacity_ah=3.0):
    print("\n======================")
    print("DEBUG: estimate_initial_soc_cycle1")
    print("======================")

    c1 = df[df["cycle_id"] == 1].copy()
    print(f"Cycle 1 row count: {len(c1)}")

    if c1.empty:
        print("ERROR: Cycle 1 is empty.")
        return {cell: pd.Series(index=df.index, dtype=float) for cell in [1,2,3]}

    dt_h = c1["dt_h"]
    src = c1["SourceFile"].astype(str)

    # Identify segments
    is_charge_cycle    = src.str.contains("ChargeCycle")
    is_discharge_cycle = src.str.contains("DischargeCycle")

    print(f"ChargeCycle rows found: {is_charge_cycle.sum()}")
    print(f"DischargeCycle rows found: {is_discharge_cycle.sum()}")

    # Last charge row
    if not is_charge_cycle.any():
        print("ERROR: No ChargeCycle rows found in cycle 1.")
        return {cell: pd.Series(index=df.index, dtype=float) for cell in [1,2,3]}

    last_charge_idx = c1[is_charge_cycle].index[-1]
    print(f"Last ChargeCycle index: {last_charge_idx}")

    # Voltage anchor
    V1 = c1.loc[last_charge_idx, "Voltage_1"]
    V2 = c1.loc[last_charge_idx, "Voltage_2"]
    V3 = c1.loc[last_charge_idx, "Voltage_3"]
    vmax = max(V1, V2, V3)

    print(f"Anchor voltages: V1={V1}, V2={V2}, V3={V3}, vmax={vmax}")

    soc_init = {
        1: 100.0 if V1 == vmax else 100.0 * (V1 / vmax),
        2: 100.0 if V2 == vmax else 100.0 * (V2 / vmax),
        3: 100.0 if V3 == vmax else 100.0 * (V3 / vmax),
    }

    print(f"SOC anchor values: {soc_init}")

    rows = sorted(c1.index.tolist())
    last_charge_pos = rows.index(last_charge_idx)

    # Per-cell SOC containers
    soc_cell = {cell: pd.Series(index=c1.index, dtype=float) for cell in [1,2,3]}

    # Backward integration
    print("\n--- Backward Integration (Charge) ---")
    for cell in [1,2,3]:
        I = c1[f"Current_{cell}"]
        soc = soc_cell[cell]
        soc.loc[last_charge_idx] = soc_init[cell]

        for i in range(last_charge_pos - 1, -1, -1):
            idx_next = rows[i + 1]
            idx_curr = rows[i]
            ah = I.loc[idx_curr] * dt_h.loc[idx_curr]
            delta_soc = -(ah / capacity_ah) * 100.0

            soc.loc[idx_curr] = soc.loc[idx_next] + delta_soc
            # print(soc.loc(idx_curr))
        print(f"Cell {cell} backward SOC at anchor: {soc.loc[last_charge_idx]}")
    # After backward integration, reorder SOC into forward time order
    # soc = soc.sort_index()  
    
    # Forward integration
    print("\n--- Forward Integration (Discharge) ---")
    if is_discharge_cycle.any():
        first_dis_idx = c1[is_discharge_cycle].index[0]
        print(f"First DischargeCycle index: {first_dis_idx}")

        first_dis_pos = rows.index(first_dis_idx)

        for cell in [1,2,3]:
            I = c1[f"Current_{cell}"]
            soc = soc_cell[cell]

            soc.loc[first_dis_idx] = soc.loc[last_charge_idx]
            print(f"Cell {cell} discharge start SOC = {soc.loc[last_charge_idx]} at row {first_dis_idx}")

            for i in range(first_dis_pos + 1, len(rows)):
                idx_prev = rows[i - 1]
                idx_curr = rows[i]

                ah = I.loc[idx_curr] * dt_h.loc[idx_curr]
                delta_soc = (ah / capacity_ah) * 100.0

                soc.loc[idx_curr] = soc.loc[idx_prev] + delta_soc

   
    # After backward + forward integration, before "Finalizing SOC"
    # Identify last charge and first discharge indices
    charge_mask    = src.str.contains("ChargeCycle")
    wait_mask      = src.str.contains("ChargeWait")
    
    last_charge_idx = c1[charge_mask].index[-1]
    
    for cell in [1, 2, 3]:
        soc = soc_cell[cell]
    
        # 1) Force all ChargeWait rows to hold the end-of-charge SOC
        soc.loc[wait_mask] = soc.loc[last_charge_idx]    
        
    print("\n--- Finalizing SOC (ffill/bfill) ---")
    result = {}
    
    print("\n=== DEBUG: INDEX SHAPES ===")
    print("df.index tail:", c1[is_discharge_cycle].index[-10:].tolist())
    print("soc_cell indices per cell:")
    
    for cell in [1, 2, 3]:
        # Sort SOC assignments by index
        s = soc_cell[cell].sort_index()

        # Reindex FIRST so that fill happens on df.index, not s.index
        s = s.reindex(c1.index)
    
        # Identify last discharge row (in df.index space)
        last_dis_idx = c1[is_discharge_cycle].index[-1]
    
        # Ensure last discharge SOC is present
        if pd.isna(s.loc[last_dis_idx]):
            s.loc[last_dis_idx] = soc_cell[cell].dropna().iloc[-1]
    
        # Now fill safely
        s = s.ffill().bfill().clip(0, 100)

        print(f"Cell {cell} final SOC min={s.min()}, max={s.max()}")
        print(f"result = {s.iloc[-1]}")
    
        result[cell] = s
        print(f"result = {result[cell].iloc[-1]}")
    return result

def compute_soc_per_cycle(df: pd.DataFrame,
                          prev_cycle_end_soc: dict,
                          capacity_ah: float = 3.0):
    """
    Compute SOC for exactly one cycle_df (single cycle_id).
    prev_cycle_end_soc: dict {1: soc_cell1, 2: soc_cell2, 3: soc_cell3}
    Returns: (df_with_soc, updated_prev_cycle_end_soc)
    """

    # dt_h must already be present (you’re calling add_dt_per_cycle earlier)
    if "dt_h" not in df.columns:
        raise ValueError("dt_h column missing in cycle_df")

    rows = df.index.tolist()
    dt_h = df["dt_h"]

    # Ensure SOC columns exist
    for cell in [1, 2, 3]:
        if f"SOC_{cell}" not in df.columns:
            df[f"SOC_{cell}"] = np.nan

    for cell in [1, 2, 3]:
        I = df[f"Current_{cell}"]
        soc = pd.Series(index=df.index, dtype=float)

        # Start SOC = previous cycle's end SOC
        soc.loc[rows[0]] = prev_cycle_end_soc[cell]

        # Integrate forward
        for i in range(1, len(rows)):
            idx_prev = rows[i - 1]
            idx_curr = rows[i]
            ah = I.loc[idx_curr] * dt_h.loc[idx_curr]
            delta_soc = (ah / capacity_ah) * 100.0
            soc.loc[idx_curr] = soc.loc[idx_prev] + delta_soc

        soc = soc.clip(0, 100)
        df[f"SOC_{cell}"] = soc.values

        # Update for next cycle
        prev_cycle_end_soc[cell] = soc.iloc[-1]

    return df, prev_cycle_end_soc

def compute_cycle_progress_by_time_series(time_series):
    t = time_series.astype(float)
    if t.empty:
        return pd.Series(np.nan, index=time_series.index)
    t0 = float(t.iloc[0])
    t1 = float(t.iloc[-1])
    if t1 <= t0:
        # degenerate: spread 0..100 across rows
        return pd.Series(np.linspace(0.0, 100.0, num=len(t)), index=time_series.index)
    prog = (t - t0) / (t1 - t0) * 100.0
    return prog.clip(0.0, 100.0)

def compute_cycle_progress_by_soc_series(soc_series):
    s = soc_series.astype(float)
    if s.empty or s.isnull().all():
        return pd.Series(np.nan, index=soc_series.index)
    s0 = float(s.iloc[0])
    s1 = float(s.iloc[-1])
    if s1 == s0:
        return pd.Series(np.linspace(0.0, 100.0, num=len(s)), index=s.index)
    prog = (s - s0) / (s1 - s0) * 100.0
    return prog.clip(0.0, 100.0)

def compute_cycle_progress(df, prefer="soc_then_time"):
    # prefer: 'soc_then_time', 'time_then_soc', 'time_only', 'soc_only'
    if prefer == "soc_then_time":
        if "SOC_1" in df.columns and df["SOC_1"].notna().any():
            p = compute_cycle_progress_by_soc_series(df["SOC_1"])
            if p.notna().any():
                return p
        return compute_cycle_progress_by_time_series(df["Time"])
    if prefer == "time_then_soc":
        p = compute_cycle_progress_by_time_series(df["Time"])
        if p.notna().any():
            return p
        return compute_cycle_progress_by_soc_series(df.get("SOC_1", pd.Series(dtype=float)))
    if prefer == "time_only":
        return compute_cycle_progress_by_time_series(df["Time"])
    if prefer == "soc_only":
        return compute_cycle_progress_by_soc_series(df.get("SOC_1", pd.Series(dtype=float)))
    return compute_cycle_progress_by_time_series(df["Time"])

def drop_zero_measurements(df):
    volt_cols = [c for c in df.columns if "Voltage" in c.lower()]
    if not volt_cols:
        return df

    # Drop rows where ANY voltage column is < 2.45
    drop_mask = (df[volt_cols] < 2.45).any(axis=1)
    return df.loc[~drop_mask]

def build_cache_for_folder(folder_name: str):
    ensure_dirs(folder_name)
    print(f"[CACHE] rebuilding chunks for {folder_name}")

    folder = folder_path(folder_name)
    cache_root = folder / CACHE_SUBDIR

    # clear existing cache
    if cache_root.exists():
        for sub in cache_root.glob("chunk_*"):
            for f in sub.glob("*.parquet"):
                try:
                    f.unlink()
                except Exception as e:
                    print(f"[CACHE] failed to remove {f}: {e}")
    else:
        cache_root.mkdir(parents=True, exist_ok=True)

    cycles = group_files_by_cycle(folder_name)
    if not cycles:
        print(f"[CACHE] no cycles found for {folder_name}")
        return

    SMALL_GAP = 1e-6
    chunk_index = 0
    part_index = 0
    buffer = []
    buffer_rows = 0
    global_offset = 0.0

    def ordered_paths_for_cycle(paths):
        try:
            all_ordered = ordered_lvm_files(folder_name)
            path_set = set([p.resolve() for p in paths])
            ordered = [p for p in all_ordered if p.resolve() in path_set]
            return ordered if ordered else list(paths)
        except Exception:
            return list(paths)

    # -----------------------------------------
    # NEW: initialize previous cycle end SOC
    # -----------------------------------------
    prev_cycle_end_soc = {1: 100.0, 2: 100.0, 3: 100.0}
    capacity_ah = 3.0

    for cid, paths in cycles.items():
        ordered_paths = ordered_paths_for_cycle(paths)

        file_infos = []
        for p in ordered_paths:
            try:
                df = load_lvm_file(p)
            except Exception as e:
                print(f"[CACHE] failed to load {p.name}: {e}")
                continue
            if df is None or df.empty:
                print(f"[CACHE] skipping empty file {p.name}")
                continue

            if "Timestamp" not in df.columns:
                if "Time" in df.columns:
                    df["Timestamp"] = df["Time"]
                elif "dt_h" in df.columns:
                    df["Timestamp"] = df["dt_h"]
                else:
                    df["Timestamp"] = 0.0
            df["Timestamp"] = pd.to_numeric(df["Timestamp"], errors="coerce").fillna(0.0)

            file_infos.append((p, df))

        if not file_infos:
            continue

        dfs_sorted = []
        for p, df in file_infos:
            df = df.copy()
            df["cycle_id"] = cid
            df["Time"] = df["Timestamp"].astype(float) + global_offset

            try:
                file_max = float(df["Time"].max()) if len(df) > 0 else global_offset
            except Exception:
                file_max = global_offset
            prev_offset = global_offset
            global_offset = file_max + SMALL_GAP

            dfs_sorted.append(df)

            try:
                t0 = df["Time"].iloc[0]
                t1 = df["Time"].iloc[-1]
                print(f"[CACHE] file {p.name} assigned Time range {t0:.6f} - {t1:.6f} (offset {prev_offset:.6f})")
            except Exception:
                print(f"[CACHE] file {p.name} assigned Time range unknown (offset {prev_offset:.6f})")

        cycle_df = pd.concat(dfs_sorted, ignore_index=True)
        cycle_df = cycle_df.sort_values("Time", kind="mergesort", ignore_index=True)

        # -----------------------------------------
        # REQUIRED PREPROCESSING (still here)
        # -----------------------------------------
        cycle_df = add_dt_per_cycle(cycle_df)
        cycle_df = drop_zero_measurements(cycle_df)

        # ============================================================
        # >>> SOC BLOCK STARTS HERE <<<
        # ============================================================
        try:
            if cid == 1:
                # estimate_initial_soc_cycle1 returns a dict, not a DataFrame
                soc_dict = estimate_initial_soc_cycle1(cycle_df, capacity_ah)
        
                # Insert SOC columns manually
                for cell in [1, 2, 3]:
                    # Create an empty SOC column aligned to cycle_df
                    aligned = pd.Series(index=cycle_df.index, dtype=float)
                
                    # Insert SOC values at the correct positions
                    aligned.loc[soc_dict[cell].index] = soc_dict[cell].values
                
                    # Fill gaps forward/backward
                    cycle_df[f"SOC_{cell}"] = aligned.ffill().bfill()
        
                # Update previous cycle end SOC
                prev_cycle_end_soc = {
                    1: cycle_df["SOC_1"].iloc[0],
                    2: cycle_df["SOC_2"].iloc[0],
                    3: cycle_df["SOC_3"].iloc[0],
                }
                print(cycle_df["SOC_1"])  
                print(cycle_df["SOC_2"]) 
                print(cycle_df["SOC_3"]) 
                
            else:
                # Generic integrator for cycles ≥ 2
               
                cycle_df, prev_cycle_end_soc = compute_soc_per_cycle(
                    cycle_df,
                    prev_cycle_end_soc,
                    capacity_ah
                )
            print(f"{prev_cycle_end_soc=}")
            # Compute progress after SOC is available
            cycle_df["Progress"] = compute_cycle_progress(
                cycle_df,
                prefer="soc_then_time"
            )
        
        except Exception as e:
            print(f"[CACHE] compute_soc_per_cycle failed for cycle {cid}: {e}")
        # ============================================================
        # >>> SOC BLOCK ENDS HERE <<<
        # ============================================================

        # chunking: fill buffer and write CHUNK_SIZE blocks
        rows = len(cycle_df)
        start = 0
        while start < rows:
            remaining_chunk_space = CHUNK_SIZE - buffer_rows
            take = min(remaining_chunk_space, rows - start)
            slice_df = cycle_df.iloc[start:start + take]
            buffer.append(slice_df)
            buffer_rows += len(slice_df)
            start += take

            if buffer_rows >= CHUNK_SIZE:
                out = pd.concat(buffer, ignore_index=True)
                # final defensive stable sort by Time
                out = out.sort_values("Time", kind="mergesort", ignore_index=True)

                chunk_dir = cache_root / f"chunk_{chunk_index:04d}"
                chunk_dir.mkdir(parents=True, exist_ok=True)
                try:
                    out.to_parquet(chunk_dir / f"part-{part_index}.parquet", index=False)
                    # log chunk details
                    try:
                        tmin = out["Time"].iloc[0]
                        tmax = out["Time"].iloc[-1]
                    except Exception:
                        tmin = tmax = None
                    sources = out["SourceFile"].unique()[:10] if "SourceFile" in out.columns else []
                    print(f"[CACHE] wrote {chunk_dir}/part-{part_index}.parquet ({len(out)} rows) Time {tmin} - {tmax} sources={list(sources)}")
                except Exception as e:
                    print(f"[CACHE] failed to write {chunk_dir}/part-{part_index}.parquet: {e}")

                part_index += 1
                buffer = []
                buffer_rows = 0
                chunk_index += 1

    # flush any remaining buffer
    if buffer_rows > 0:
        out = pd.concat(buffer, ignore_index=True)
        out = out.sort_values("Time", kind="mergesort", ignore_index=True)
        chunk_dir = cache_root / f"chunk_{chunk_index:04d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        try:
            out.to_parquet(chunk_dir / f"part-{part_index}.parquet", index=False)
            try:
                tmin = out["Time"].iloc[0]
                tmax = out["Time"].iloc[-1]
            except Exception:
                tmin = tmax = None
            sources = out["SourceFile"].unique()[:10] if "SourceFile" in out.columns else []
            print(f"[CACHE] wrote {chunk_dir}/part-{part_index}.parquet ({len(out)} rows) Time {tmin} - {tmax} sources={list(sources)}")
        except Exception as e:
            print(f"[CACHE] failed to write {chunk_dir}/part-{part_index}.parquet: {e}")

    print(f"[CACHE] chunks built for {folder_name}")
