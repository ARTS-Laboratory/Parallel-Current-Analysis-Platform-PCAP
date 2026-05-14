# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 16:28:18 2026

@author: malichi
"""

# callbacks.py
import os
import dash
import time
import shutil
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from worker import ensure_cache_worker
from dash.exceptions import PreventUpdate
from icons import battery_icon, pack_icon, cycle_icon
from dash import Input, Output, State, html, callback_context
from engine import folder_path, get_playback_window, ordered_lvm_files, load_lvm_file


print(">>> USING CALLBACKS FILE:", os.path.abspath(__file__))

CACHE_SUBDIR = "cache"


# ------------------------------------------------------------
# Chunk metadata (reads cache chunk dirs and builds index)
# ------------------------------------------------------------
def load_chunk_metadata(folder_name: str):
    folder = folder_path(folder_name)
    cache_root = folder / CACHE_SUBDIR

    chunk_dirs = sorted(cache_root.glob("chunk_*"))
    #print(f"{chunk_dirs=}")
    if not chunk_dirs:
        return [], [], [], {}

    chunk_row_counts = []
    cumulative_offsets = []
    cycle_index = {}

    total = 0
    for chunk_dir in chunk_dirs:
        parts = sorted(chunk_dir.glob("*.parquet"))
        if not parts:
            chunk_row_counts.append(0)
            cumulative_offsets.append(total)
            continue

        # read only cycle_id column for indexing
        df = pd.read_parquet(parts[0], columns=["cycle_id"])
        n = len(df)
        chunk_row_counts.append(n)
        cumulative_offsets.append(total)

        for i, cid in enumerate(df["cycle_id"].values):
            if cid not in cycle_index:
                cycle_index[cid] = total + i

        total += n

    return chunk_dirs, chunk_row_counts, cumulative_offsets, cycle_index


# ------------------------------------------------------------
# Pointer row loader (single-row read)
# ------------------------------------------------------------
def load_pointer_row(folder_name: str, pointer: int):
    chunk_dirs, chunk_rows, offsets, _ = load_chunk_metadata(folder_name)
    if not chunk_dirs:
        return None

    # find last offset <= pointer
    chunk_idx = 0
    for i, off in enumerate(offsets):
        if pointer >= off:
            chunk_idx = i

    parts = sorted(chunk_dirs[chunk_idx].glob("*.parquet"))
    if not parts:
        return None

    df = pd.read_parquet(parts[0])
    local_idx = pointer - offsets[chunk_idx]
    local_idx = max(0, min(len(df) - 1, local_idx))
    return df.iloc[local_idx]


# ------------------------------------------------------------
# Plot helpers
# ------------------------------------------------------------
def empty_plot():
    fig = go.Figure()
    fig.update_layout(
        uirevision=True, 
        xaxis={"visible": False},
        yaxis={"visible": False},
        paper_bgcolor="black",
        plot_bgcolor="black",
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return fig


def make_voltage_pack(df):
    fig = go.Figure()
    voltage_cols = [c for c in df.columns if c.lower().startswith("voltage")]
    for i, col in enumerate(voltage_cols):
        fig.add_trace(go.Scattergl(
            x=df["Time"],
            y=df[col],
            mode="lines",
            name=col,
            line=dict(width=4, color=["#00FFAA", "#FFAA00", "#AA00FF", "#00AAFF"][i % 4]),
        ))
    fig.update_layout(uirevision=True, paper_bgcolor="black", plot_bgcolor="black", font=dict(color="white"), margin=dict(l=40, r=20, t=20, b=40),  legend=dict(orientation="h"))
   
    # FIXED Y‑AXIS RANGE
    fig.update_yaxes(
        title_text="Voltage (V)",
        range=[2.4, 4.4],
        tickmode="linear",
        dtick=(4.4 - 2.4) / 5,   # 5 intervals
        showgrid=True,
    )
    
    fig.update_xaxes(
        showticklabels=False,
        ticks="",
    )
    return fig


def make_current_pack(df):
    fig = go.Figure()
    current_cols = [c for c in df.columns if c.lower().startswith("current")]
    for i, col in enumerate(current_cols):
        fig.add_trace(go.Scattergl(
            x=df["Time"],
            y=df[col],
            mode="lines",
            name=col,
            line=dict(width=4, color=["#00FFAA", "#FFAA00", "#AA00FF", "#00AAFF"][i % 4]),
        ))
    fig.update_layout(uirevision=True, paper_bgcolor="black", plot_bgcolor="black", font=dict(color="white"), margin=dict(l=40, r=20, t=20, b=40), legend=dict(orientation="h"))

    # FIXED Y‑AXIS RANGE
    fig.update_yaxes(
        title_text="Current (A)",
        range=[-10, 10],
        tickmode="linear",
        dtick=(10 - -10) / 8,   
        showgrid=True,
    )
    
    fig.update_xaxes(
        showticklabels=False,
        ticks="",
    )
    return fig


def make_temp_pack(df):
    fig = go.Figure()
    temp_cols = [c for c in df.columns if c.lower().startswith("temp")]
    for i, col in enumerate(temp_cols):
        fig.add_trace(go.Scattergl(
            x=df["Time"],
            y=df[col],
            mode="lines",
            name=col,
            line=dict(width=4, color=["#00FFAA", "#FFAA00", "#AA00FF", "#00AAFF"][i % 4]),
        ))
    fig.update_layout(uirevision=True, paper_bgcolor="black", plot_bgcolor="black", font=dict(color="white"), margin=dict(l=40, r=20, t=20, b=40), legend=dict(orientation="h"))

    # FIXED Y‑AXIS RANGE
    fig.update_yaxes(
        title_text="Temperature (°C)",
        range=[30, 40],
        tickmode="linear",
        dtick=(40 - 30) / 8,   
        showgrid=True,
    )
    
    fig.update_xaxes(
        showticklabels=False,
        ticks="",
    )
    return fig

def make_strain_pack(df):
    fig = go.Figure()
    strain_cols = [c for c in df.columns if c.lower().startswith("strain")]
    for i, col in enumerate(strain_cols):
        fig.add_trace(go.Scattergl(
            x=df["Time"],
            y=df[col] * 1000000,
            mode="lines",
            name=col,
            line=dict(width=4, color=["#00FFAA", "#FFAA00", "#AA00FF", "#00AAFF"][i % 4]),
        ))
    fig.update_layout(uirevision=True, paper_bgcolor="black", plot_bgcolor="black", font=dict(color="white"), margin=dict(l=40, r=20, t=20, b=40), legend=dict(orientation="h"))

    # FIXED Y‑AXIS RANGE
    fig.update_yaxes(
        title_text="Strain (µε)",
        range=[-250, 625],
        tickmode="linear",
        dtick=(625 - -250) / 8,  
        showgrid=True,
    )
    
    fig.update_xaxes(
        title_text="Time (s)",
    )
    return fig

def make_voltage_cell(df, cell):
    fig = go.Figure()
    col = f"Voltage_{cell}"
    if col in df.columns:
        fig.add_trace(go.Scattergl(x=df["Time"], y=df[col], mode="lines", line=dict(color="#00FFAA", width=5), name=f"Cell {cell} Voltage"))
    fig.update_layout(uirevision=True, paper_bgcolor="black", plot_bgcolor="black", font=dict(color="white"), margin=dict(l=40, r=20, t=20, b=40), legend=dict(orientation="h"))

    # FIXED Y‑AXIS RANGE
    fig.update_yaxes(
        title_text="Voltage (V)",
        range=[2.4, 4.4],
        tickmode="linear",
        dtick=(4.4 - 2.4) / 5,  
        showgrid=True,
    )
    
    fig.update_xaxes(
        showticklabels=False,
        ticks="",
    )
    return fig

def make_current_cell(df, cell):
    fig = go.Figure()
    col = f"Current_{cell}"
    if col in df.columns:
        fig.add_trace(go.Scattergl(x=df["Time"], y=df[col], mode="lines", line=dict(color="#FFAA00", width=5), name=f"Cell {cell} Current"))
    fig.update_layout(uirevision=True, paper_bgcolor="black", plot_bgcolor="black", font=dict(color="white"), margin=dict(l=40, r=20, t=20, b=40), legend=dict(orientation="h"))

    # FIXED Y‑AXIS RANGE
    fig.update_yaxes(
        title_text="Current (A)",
        range=[-4, 4],
        tickmode="linear",
        dtick=(4 - -4) / 8,   
        showgrid=True,
    )
    
    fig.update_xaxes(
        showticklabels=False,
        ticks="",
    )
    return fig

def make_temp_cell(df, cell):
    fig = go.Figure()
    col = f"Temp_{cell}"
    if col in df.columns:
        fig.add_trace(go.Scattergl(x=df["Time"], y=df[col], mode="lines", line=dict(color="#FF3333", width=5), name=f"Cell {cell} Temp"))
    fig.update_layout(uirevision=True, paper_bgcolor="black", plot_bgcolor="black", font=dict(color="white"), margin=dict(l=40, r=20, t=20, b=40), legend=dict(orientation="h"))

    # FIXED Y‑AXIS RANGE
    fig.update_yaxes(
        title_text="Temperature (°C)",
        range=[30, 40],
        tickmode="linear",
        dtick=(40 - 30) / 8,   
        showgrid=True,
    )
    
    fig.update_xaxes(
        showticklabels=False,
        ticks="",
    )
    return fig

def make_strain_cell(df, cell):
    fig = go.Figure()
    col = f"Strain_{cell}"
    if col in df.columns:
        fig.add_trace(go.Scattergl(x=df["Time"], y=df[col] * 1000000, mode="lines", line=dict(color="#33AAFF", width=5), name=f"Cell {cell} Strain"))
    fig.update_layout(uirevision=True, paper_bgcolor="black", plot_bgcolor="black", font=dict(color="white"), margin=dict(l=40, r=20, t=20, b=40), legend=dict(orientation="h"))

    # FIXED Y‑AXIS RANGE
    fig.update_yaxes(
        title_text="Strain (µε)",
        range=[-250, 625],
        tickmode="linear",
        dtick=(625 - -250) / 8,
        showgrid=True,
    )
    
    fig.update_xaxes(
        title_text="Time (s)",
    )
    return fig

def add_pointer(fig, df, local_idx, ycol):
    """Add a single-point pointer marker to a figure."""
    if ycol not in df.columns:
        return fig

    # Extract the point
    x = df["Time"].iloc[local_idx]
    y = df[ycol].iloc[local_idx]

    # Remove old pointer traces
    fig.data = tuple(t for t in fig.data if t.name != "pointer")

    # Add new pointer trace (SVG, 1 point)
    fig.add_trace(go.Scattergl(
        x=[x],
        y=[y],
        mode="markers",
        name="pointer",
        marker=dict(
            size=14,
            color="white",
            line=dict(width=2, color="black"),
        ),
        showlegend=False,
        hoverinfo="skip",
    ))
        
    return fig

# ------------------------------------------------------------
# Register callbacks
# ------------------------------------------------------------
def register_callbacks(app):
    print(">>> REGISTER_CALLBACKS CALLED")

    # ---------------------------
    # Debug: single debug-ping callback (consolidated)
    # ---------------------------
    @app.callback(
        Output("debug-ping", "children"),
        Input("btn-play", "n_clicks"),
        Input("btn-pause", "n_clicks"),
        Input("btn-back", "n_clicks"),
        Input("btn-forward", "n_clicks"),
        Input("cycle-prev", "n_clicks"),
        Input("cycle-next", "n_clicks"),
        State("file-dropdown", "value"),
        State("folder-store", "data"),
        prevent_initial_call=False,
    )
    def debug_ping(play, pause, back, forward, cprev, cnext, dropdown, folder_store):
        ctx = callback_context.triggered_id
        print("DEBUG PING fired; ctx=", ctx, "values:", dict(play=play, pause=pause, back=back, forward=forward, cprev=cprev, cnext=cnext, dropdown=dropdown, folder_store=folder_store))
        return f"ping {ctx}"

    # --------------------------------------------------------
    # STARTUP: first Play click initializes cache + worker
    # --------------------------------------------------------
    @app.callback(
        Output("folder-store", "data"),
        Output("data-ready", "data"),
        Input("btn-play", "n_clicks"),
        State("folder-store", "data"),
        State("file-dropdown", "value"),
        prevent_initial_call=True,
    )
    def force_startup(play_clicks, folder_name, selected_folder):
        # guard: if already initialized, do nothing
        if folder_name:
            raise PreventUpdate

        if not play_clicks:
            raise PreventUpdate

        if not selected_folder:
            print(">>> PLAY CLICKED WITH NO FOLDER SELECTED")
            raise PreventUpdate

        folder_name = selected_folder
        print(">>> FORCE STARTUP VIA PLAY")
        print(">>> folder_name =", folder_name)

        # DELETE CACHE ON STARTUP
        folder = folder_path(folder_name)
        cache_root = folder / CACHE_SUBDIR
        if cache_root.exists():
            shutil.rmtree(cache_root)
        cache_root.mkdir(exist_ok=True)

        # STEP 1 — ORDER FILES
        files = ordered_lvm_files(folder_name)

        # STEP 2 — GLOBAL STRAIN MIN/MAX
        mins = []
        maxs = []
        for f in files:
            df = load_lvm_file(f)
            if "Strain_1" in df:
                mins.append(df["Strain_1"].min())
                maxs.append(df["Strain_1"].max())

        if mins and maxs:
            (cache_root / "strain_minmax.txt").write_text(f"{min(mins)},{max(maxs)}")

        # STEP 3 — START WORKER (do not write ready.flag yet)
        ensure_cache_worker(folder_name)
    
        # STEP 4 — wait briefly for the first chunk to appear, then write ready.flag
        # This prevents data-ready from being set True before any chunk exists.
        first_chunk_dir = cache_root / f"chunk_{0:04d}"
        poll_timeout = 15.0   # seconds to wait for first chunk (tunable)
        poll_interval = 0.25  # seconds between checks
        waited = 0.0
    
        print(f">>> waiting up to {poll_timeout}s for first chunk at {first_chunk_dir}")
        while waited < poll_timeout:
            if first_chunk_dir.exists() and any(first_chunk_dir.glob("part-*.parquet")):
                # first chunk is present; mark ready and return True
                try:
                    (cache_root / "ready.flag").write_text("ready")
                    print(">>> first chunk detected; wrote ready.flag")
                except Exception as e:
                    print(">>> failed to write ready.flag:", e)
                return folder_name, True
    
            time.sleep(poll_interval)
            waited += poll_interval
    
        # timed out waiting for first chunk — worker still running in background
        # return folder_name and False so UI knows data is not yet ready
        print(f">>> timed out ({poll_timeout}s) waiting for first chunk; worker continues in background")
        return folder_name, False
    
    # --------------------------------------------------------
    # ROW COUNT
    # --------------------------------------------------------
    @app.callback(
        Output("row-count", "data"),
        Input("data-ready", "data"),
        State("folder-store", "data"),
        prevent_initial_call=False,
    )
    def compute_row_count(ready, folder_name):
        if not ready or not folder_name:
            print("DEBUG row count not ready")
            raise PreventUpdate
        print(f'loading chunk metadata{folder_name}')
        _, chunk_rows, _, _ = load_chunk_metadata(folder_name)
        total = sum(chunk_rows)
        print(">>> ROW COUNT =", total)
        return total

    # --------------------------------------------------------
    # Sync row-count -> max-rows (pointer_master expects max-rows)
    # --------------------------------------------------------
    @app.callback(
        Output("max-rows", "data"),
        Input("row-count", "data"),
        prevent_initial_call=False,
    )
    def sync_max_rows(row_count):
        if row_count is None:
            raise PreventUpdate
        return int(row_count)

    # --------------------------------------------------------
    # PLAYBACK MASTER
    # --------------------------------------------------------
    @app.callback(
        Output("row-pointer", "data"),
        Output("playback-mode", "data"),
        Output("playback-interval", "interval"),
        Input("btn-play", "n_clicks"),
        Input("btn-pause", "n_clicks"),
        Input("btn-back", "n_clicks"),
        Input("btn-forward", "n_clicks"),
        Input("cycle-prev", "n_clicks"),
        Input("cycle-next", "n_clicks"),
        Input("playback-interval", "n_intervals"),
        State("row-pointer", "data"),
        State("playback-mode", "data"),
        State("max-rows", "data"),
        State("window-df", "data"),
        prevent_initial_call=True,
    )
    def pointer_master(play, pause, back, forward, cycle_prev, cycle_next,
                       n_intervals, pointer, playback_mode, max_rows, window_payload):
    
        ctx = callback_context.triggered_id
        now = time.time()
    
        # -------------------------
        # NORMALIZE POINTER + MAX_ROWS
        # -------------------------
        try:
            pointer = int(pointer or 0)
        except:
            pointer = 0
    
        max_rows = int(max_rows or 0)
        pointer = max(0, min(pointer, max_rows - 1))
    
        # -------------------------
        # SAFE INIT OF PLAYBACK_MODE
        # -------------------------
        if playback_mode is None or not isinstance(playback_mode, dict):
            playback_mode = {}
    
        playback_mode.setdefault("initialized", False)
        playback_mode.setdefault("playing", False)
        playback_mode.setdefault("scrub", None)
        playback_mode.setdefault("forward_streak", 0)
        playback_mode.setdefault("back_streak", 0)
    
        # -------------------------
        # CONSTANTS
        # -------------------------
        BASE_INTERVAL = 2000  # ms
        MIN_INTERVAL = 10    # ms (max speed)
    
        # -------------------------
        # PLAY
        # -------------------------
        if ctx == "btn-play":
            playback_mode["initialized"] = True
            playback_mode["playing"] = True
            playback_mode["scrub"] = None
            playback_mode["forward_streak"] = 0
            playback_mode["back_streak"] = 0
            return pointer, playback_mode, BASE_INTERVAL
    
        # -------------------------
        # PAUSE
        # -------------------------
        if ctx == "btn-pause":
            playback_mode["playing"] = False
            playback_mode["scrub"] = None
            playback_mode["forward_streak"] = 0
            playback_mode["back_streak"] = 0
            return pointer, playback_mode, BASE_INTERVAL
    
        # -------------------------
        # FORWARD SCRUB (CLICK)
        # -------------------------
        if ctx == "btn-forward":
            playback_mode["playing"] = False
            playback_mode["scrub"] = "forward"
    
            playback_mode["forward_streak"] += 1
            playback_mode["back_streak"] = 0
    
            speed = 2 ** playback_mode["forward_streak"]
            interval_ms = max(MIN_INTERVAL, BASE_INTERVAL // speed)
    
            pointer = min(pointer + 1, max_rows - 1)
    
            return pointer, playback_mode, interval_ms
    
        # -------------------------
        # BACK SCRUB (CLICK)
        # -------------------------
        if ctx == "btn-back":
            playback_mode["playing"] = False
            playback_mode["scrub"] = "back"
    
            playback_mode["back_streak"] += 1
            playback_mode["forward_streak"] = 0
    
            speed = 2 ** playback_mode["back_streak"]
            interval_ms = max(MIN_INTERVAL, BASE_INTERVAL // speed)
    
            pointer = max(pointer - 1, 0)
    
            return pointer, playback_mode, interval_ms
    
        # -------------------------
        # CYCLE PREV / NEXT
        # -------------------------
        if ctx in ("cycle-prev", "cycle-next"):
            playback_mode["playing"] = False
            playback_mode["scrub"] = None
            playback_mode["forward_streak"] = 0
            playback_mode["back_streak"] = 0
    
            df = None
            window_base = 0
            if window_payload:
                try:
                    df = pd.DataFrame(window_payload.get("records", []))
                    window_base = int(window_payload.get("window_base", 0))
                except:
                    pass
    
            if df is None or df.empty or "cycle_id" not in df.columns:
                return pointer, playback_mode, BASE_INTERVAL
    
            local_idx = max(0, min(pointer - window_base, len(df) - 1))
            current_cycle = df.loc[local_idx, "cycle_id"]
    
            if ctx == "cycle-prev":
                prev_cycles = df[df["cycle_id"] < current_cycle]["cycle_id"].unique()
                if len(prev_cycles) > 0:
                    target = prev_cycles[-1]
                    pointer = window_base + int(df.index[df["cycle_id"] == target][0])
                else:
                    pointer = 0
    
            else:  # cycle-next
                next_cycles = df[df["cycle_id"] > current_cycle]["cycle_id"].unique()
                if len(next_cycles) > 0:
                    target = next_cycles[0]
                    pointer = window_base + int(df.index[df["cycle_id"] == target][0])
    
            return pointer, playback_mode, BASE_INTERVAL
    
        # -------------------------
        # INTERVAL TICK (CONTINUOUS SCRUB)
        # -------------------------
        if ctx == "playback-interval":
    
            # normal playback
            if playback_mode["playing"]:
                pointer = min(pointer + 1, max_rows - 1)
                return pointer, playback_mode, BASE_INTERVAL
    
            # forward scrub
            if playback_mode["scrub"] == "forward":
                speed = 2 ** playback_mode["forward_streak"]
                interval_ms = max(MIN_INTERVAL, BASE_INTERVAL // speed)
                pointer = min(pointer + 1, max_rows - 1)
                return pointer, playback_mode, interval_ms
    
            # backward scrub
            if playback_mode["scrub"] == "back":
                speed = 2 ** playback_mode["back_streak"]
                interval_ms = max(MIN_INTERVAL, BASE_INTERVAL // speed)
                pointer = max(pointer - 1, 0)
                return pointer, playback_mode, interval_ms
    
            raise PreventUpdate
    
        # -------------------------
        # DEFAULT
        # -------------------------
        raise PreventUpdate

    @app.callback(
        Output("btn-forward", "className"),
        Output("btn-back", "className"),
        Output("btn-play", "className"),
        Output("btn-pause", "className"),
        Input("playback-mode", "data"),
    )
    def update_button_states(mode):
        if mode is None:
            return "ctrl-btn", "ctrl-btn", "ctrl-btn", "ctrl-btn"
    
        scrub = mode.get("scrub")
        playing = mode.get("playing")
    
        forward_cls = "ctrl-btn active" if scrub == "forward" else "ctrl-btn"
        back_cls = "ctrl-btn active" if scrub == "back" else "ctrl-btn"
        play_cls = "ctrl-btn active" if playing else "ctrl-btn"
        pause_cls = "ctrl-btn active" if not playing and scrub is None else "ctrl-btn"
    
        return forward_cls, back_cls, play_cls, pause_cls

    # --------------------------------------------------------
    # TAB SELECTOR
    # --------------------------------------------------------
    @app.callback(
        Output("tab-selector", "data"),
        Input("tab-pack", "n_clicks"),
        Input("tab-batt1", "n_clicks"),
        Input("tab-batt2", "n_clicks"),
        Input("tab-batt3", "n_clicks"),
        prevent_initial_call=True,
    )
    def select_tab(pack, b1, b2, b3):
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update

        clicked = ctx.triggered[0]["prop_id"].split(".")[0]

        if clicked == "tab-pack":
            return "pack"
        if clicked == "tab-batt1":
            return "batt1"
        if clicked == "tab-batt2":
            return "batt2"
        if clicked == "tab-batt3":
            return "batt3"

        return dash.no_update

    # --------------------------------------------------------
    # ICONS INSIDE TABS (battery-tile + highlight)
    # --------------------------------------------------------
    @app.callback(
        Output("tab-pack", "children"),
        Output("tab-pack", "className"),
        Output("tab-batt1", "children"),
        Output("tab-batt1", "className"),
        Output("tab-batt2", "children"),
        Output("tab-batt2", "className"),
        Output("tab-batt3", "children"),
        Output("tab-batt3", "className"),
        Output("cycle-icon", "children"),
        Output("cycle-icon", "className"),
        Input("data-ready", "data"),
        Input("row-pointer", "data"),
        Input("tab-selector", "data"),
        State("folder-store", "data"),
    )
    def update_icons(data_ready, pointer, tab, folder_name):
    
        # EMPTY CHILDREN (NOT FULL TILES)
        empty_pack_children = [pack_icon(0, 0, 0, 0), html.Div("PACK", className="battery-label")]
        empty_b1_children = [battery_icon(0), html.Div("Battery 1", className="battery-label")]
        empty_b2_children = [battery_icon(0), html.Div("Battery 2", className="battery-label")]
        empty_b3_children = [battery_icon(0), html.Div("Battery 3", className="battery-label")]
    
        # helper to infer segment from row if explicit segment not present
        def infer_segment_from_row(r):
            # check common column names first
            for key in ("Segment", "segment", "cycle_segment", "CycleSegment"):
                if key in r and r[key] not in (None, ""):
                    return str(r[key])
            # fallback heuristics using Current and SOC
            cur = r.get("Current", None)
            if cur is not None:
                try:
                    cur = float(cur)
                    if cur > 0.0:
                        return "ChargeCycle"
                    if cur < 0.0:
                        return "DischargeCycle"
                except Exception:
                    pass
            # if SOC is stable and near constant, treat as wait
            socs = [r.get("SOC_1"), r.get("SOC_2"), r.get("SOC_3")]
            try:
                soc_vals = [float(x) for x in socs if x is not None]
                if soc_vals:
                    if max(soc_vals) - min(soc_vals) < 0.01:
                        return "ChargeWait"
            except Exception:
                pass
            return "ChargeCycle"
    
        # helper to obtain progress value for the current row
        def extract_progress_from_row(r):
            # prefer an explicit Progress column
            if "Progress" in r and r["Progress"] is not None:
                try:
                    p = float(r["Progress"])
                    return max(0.0, min(100.0, p))
                except Exception:
                    pass
            # fallback: if Time and cycle start/end are present on the row, compute fraction
            if "Time" in r and "cycle_start" in r and "cycle_end" in r:
                try:
                    t = float(r["Time"])
                    t0 = float(r["cycle_start"])
                    t1 = float(r["cycle_end"])
                    if t1 > t0:
                        p = (t - t0) / (t1 - t0) * 100.0
                        return max(0.0, min(100.0, p))
                except Exception:
                    pass
            # last resort: no progress available
            return None
    
        if not data_ready or not folder_name:
            return (
                empty_pack_children, "battery-tile",
                empty_b1_children, "battery-tile",
                empty_b2_children, "battery-tile",
                empty_b3_children, "battery-tile",
                cycle_icon(None, None, progress=None, size=56, animate=False),
            )
    
        print("STATUS data is ready")
        row = load_pointer_row(folder_name, pointer or 0)
        if row is None:
            return (
                empty_pack_children, "battery-tile",
                empty_b1_children, "battery-tile",
                empty_b2_children, "battery-tile",
                empty_b3_children, "battery-tile",
                cycle_icon(None, None, progress=None, size=56, animate=False),
            )
        segment = infer_segment_from_row(row)
        # CHILDREN ONLY — NOT FULL TILES
        pack_children = [
            pack_icon(min(row["SOC_1"], row["SOC_2"], row["SOC_3"]), row["Voltage"], row["Current"], row["Temp"]),
            html.Div("PACK", className="battery-label"),
        ]
        b1_children = [battery_icon(row["SOC_1"], True if segment == "ChargeCycle" else False), html.Div("Battery 1", className="battery-label")]
        b2_children = [battery_icon(row["SOC_2"], True if segment == "ChargeCycle" else False), html.Div("Battery 2", className="battery-label")]
        b3_children = [battery_icon(row["SOC_3"], True if segment == "ChargeCycle" else False), html.Div("Battery 3", className="battery-label")]
        
        # determine cycle id, segment, progress, and animate flag
        cycle_id = row.get("cycle_id", None)
        try:
            cycle_label = int(cycle_id) if cycle_id is not None else "--"
        except Exception:
            cycle_label = str(cycle_id)
    
        
        progress = extract_progress_from_row(row)
        animate = False if (segment and "wait" in segment.lower()) else True
        cycle_children = [cycle_icon(segment, cycle_label, progress=progress, size=200, animate=animate), html.Div("Cycle", className="cycle-label")]
        return (
            pack_children, ("battery-tile highlight" if tab == "pack" else "battery-tile"),
            b1_children, ("battery-tile highlight" if tab == "batt1" else "battery-tile"),
            b2_children, ("battery-tile highlight" if tab == "batt2" else "battery-tile"),
            b3_children, ("battery-tile highlight" if tab == "batt3" else "battery-tile"),
            cycle_children, html.Div("Cycle", className="cycle-label")
        )
    
    # --------------------------------------------------------
    # Window builder (single writer of window-df)
    # --------------------------------------------------------
    @app.callback(
        Output("window-df", "data"),
        Input("row-pointer", "data"),
        State("window-size-store", "data"),
        State("folder-store", "data"),
        prevent_initial_call=False,
    )
    def build_window(pointer, window_size, folder_name):
        if not folder_name or pointer is None:
            raise PreventUpdate

        window_size = int(window_size or 200)
        print(f"{window_size=}")
        try:
            df_window, window_base = get_playback_window(folder_name, int(pointer), window_size)
        except Exception as e:
            print("build_window: engine.get_playback_window failed:", e)
            raise PreventUpdate

        if df_window is None or df_window.empty:
            raise PreventUpdate

        payload = {"records": df_window.to_dict("records"), "window_base": int(window_base)}
        print("WINDOW BUILT size=", len(df_window), "window_base=", window_base)
        print("DEBUG build_window payload keys:", list(payload.keys()))
        print("DEBUG build_window records:", len(payload.get("records", [])), "window_base:", payload.get("window_base"))
        
        return payload

    # --------------------------------------------------------
    # PLOTS (consume window-df)
    # --------------------------------------------------------
    @app.callback(
        Output("plot-voltage", "figure"),
        Output("plot-current", "figure"),
        Output("plot-temp", "figure"),
        Output("plot-strain", "figure"),
        Input("row-pointer", "data"),
        Input("tab-selector", "data"),
        Input("window-df", "data"),
        State("folder-store", "data"),
        State("window-size-store", "data"),
    )
    def update_plots(pointer, tab, window_payload, folder_name, window_size):
    
        # Debug
        print("DEBUG update_plots called; pointer=", pointer, "tab=", tab)
    
        # No folder selected
        if not folder_name:
            return empty_plot(), empty_plot(), empty_plot(), empty_plot()
    
        # No window payload
        if not window_payload:
            return empty_plot(), empty_plot(), empty_plot(), empty_plot()
    
        records = window_payload.get("records", [])
        window_base = int(window_payload.get("window_base", 0))
    
        if not records:
            return empty_plot(), empty_plot(), empty_plot(), empty_plot()
    
        # Build dataframe
        df = pd.DataFrame(records)
        
        # Compute local index
        local_idx = int(pointer or 0) - window_base
        local_idx = max(0, min(local_idx, len(df) - 1))
    
        # PACK TAB ---------------------------------------------------------
        if tab == "pack":
            fig_v = make_voltage_pack(df)
            fig_c = make_current_pack(df)
            fig_t = make_temp_pack(df)
            fig_s = make_strain_pack(df)
    
            # Pointer uses the first matching column
            voltage_cols = [c for c in df.columns if c.lower().startswith("voltage")]
            current_cols = [c for c in df.columns if c.lower().startswith("current")]
            temp_cols    = [c for c in df.columns if c.lower().startswith("temp")]
            strain_cols  = [c for c in df.columns if c.lower().startswith("strain")]
    
            if voltage_cols:
                fig_v = add_pointer(fig_v, df, local_idx, voltage_cols[0])
            if current_cols:
                fig_c = add_pointer(fig_c, df, local_idx, current_cols[0])
            if temp_cols:
                fig_t = add_pointer(fig_t, df, local_idx, temp_cols[0])
            if strain_cols:
                fig_s = add_pointer(fig_s, df, local_idx, strain_cols[0])
    
            return fig_v, fig_c, fig_t, fig_s
    
        # BATTERY TABS -----------------------------------------------------
        if tab in ("batt1", "batt2", "batt3"):
            cell = int(tab[-1])
    
            fig_v = make_voltage_cell(df, cell)
            fig_c = make_current_cell(df, cell)
            fig_t = make_temp_cell(df, cell)
            fig_s = make_strain_cell(df, cell)
    
            fig_v = add_pointer(fig_v, df, local_idx, f"Voltage_{cell}")
            fig_c = add_pointer(fig_c, df, local_idx, f"Current_{cell}")
            fig_t = add_pointer(fig_t, df, local_idx, f"Temp_{cell}")
            fig_s = add_pointer(fig_s, df, local_idx, f"Strain_{cell}")
    
            return fig_v, fig_c, fig_t, fig_s
    
        # FALLBACK ---------------------------------------------------------
        return empty_plot(), empty_plot(), empty_plot(), empty_plot()

    # --------------------------------------------------------
    # Single writer for window-size-store 
    # --------------------------------------------------------
    @app.callback(
        Output("window-size-store", "data"),
        Input("window-size", "value"),
        State("window-size-store", "data"),
        prevent_initial_call=False,
    )
    def window_size_controller(dropdown_value, current_store):
        try:
            return int(dropdown_value)
        except Exception:
            return int(current_store or 200)

    print(">>> CALLBACKS REGISTERED")
