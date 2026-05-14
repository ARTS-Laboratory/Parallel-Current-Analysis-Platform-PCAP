# -*- coding: utf-8 -*-
"""
Created on Thu Oct 16 12:11:31 2025

@author: malichi
"""

#layout.py
from dash import html, dcc
from icons import battery_icon, pack_icon, cycle_icon
import os
from pathlib import Path

# This MUST match your actual data root
BASE_DIR = Path("ParallelTestbedSuite")

def get_test_folders():
    if not BASE_DIR.exists():
        return []
    return [
        f.name
        for f in BASE_DIR.iterdir()
        if f.is_dir() and "test" in f.name.lower()
    ]
def serve_layout():
    test_folders = get_test_folders()
    return html.Div(
        [

            # TOP BAR (leave dropdown un-opinionated)
            html.Div(
                [
                html.H1(
                    "Parallel Testbed Suite",
                    style={"color": "black", "textAlign": "center", "marginCenter": "20px"}
                ),
                
                    html.Label(
                        "Select Folder:",
                        style={"color": "#00FFAA", "marginRight": "8px"},
                    ),
                    dcc.Dropdown(
                        id="file-dropdown",
                        options=[{"label": "Select a folder...", "value": ""}]
                                + [{"label": f, "value": f} for f in test_folders],
                        value="",                     # start on placeholder
                        clearable=False,
                        persistence=False,            # <-- THIS IS THE FIX
                        style={"width": "320px"},
                    ),
                ],
                className="top-bar",
            ),


            # ------------------------------------------------------------
            # TABS (PACK + B1 + B2 + B3) + CYCLE ICON
            # ------------------------------------------------------------
            html.Div(
                [
                    # PACK TAB
                    html.Div(
                        id="tab-pack",
                        n_clicks=0,
                        className="battery-tile",
                        children=[
                            pack_icon(0, 0, 0, 0),
                            html.Div("PACK", className="battery-label"),
                        ],
                    ),

                    # BATTERY 1 TAB
                    html.Div(
                        id="tab-batt1",
                        n_clicks=0,
                        className="battery-tile",
                        children=[
                            battery_icon(0),
                            html.Div("Battery 1", className="battery-label"),
                        ],
                    ),

                    # BATTERY 2 TAB
                    html.Div(
                        id="tab-batt2",
                        n_clicks=0,
                        className="battery-tile",
                        children=[
                            battery_icon(0),
                            html.Div("Battery 2", className="battery-label"),
                        ],
                    ),

                    # BATTERY 3 TAB
                    html.Div(
                        id="tab-batt3",
                        n_clicks=0,
                        className="battery-tile",
                        children=[
                            battery_icon(0),
                            html.Div("Battery 3", className="battery-label"),
                        ],
                    ),

                    # CYCLE ICON (not a tab)
                    html.Div(
                        id="cycle-icon",
                        className="cycle-tile",   # <-- CRITICAL
                        children=[
                            cycle_icon(0),
                            html.Div("Cycle", className="cycle-label"),
                        ],
                    ),
                ],
                className="battery-row",
            ),

            # ------------------------------------------------------------
            # PLAYBACK CONTROLS (Scrub-aware UI)
            # ------------------------------------------------------------
            html.Div(
                [
                    html.Button("⏮", id="cycle-prev", n_clicks=0,
                                className="ctrl-btn", type="button"),
            
                    html.Button("<<", id="btn-back", n_clicks=0,
                                className="ctrl-btn", type="button"),
            
                    html.Button("Play", id="btn-play", n_clicks=0,
                                className="ctrl-btn", type="button"),
            
                    html.Button("Pause", id="btn-pause", n_clicks=0,
                                className="ctrl-btn", type="button"),
            
                    html.Button(">>", id="btn-forward", n_clicks=0,
                                className="ctrl-btn", type="button"),
            
                    html.Button("⏭", id="cycle-next", n_clicks=0,
                                className="ctrl-btn", type="button"),
                ],
                className="control-bar"
            ),
        
            html.Div(id="debug-ping", style={"display":"none"}),

            # ------------------------------------------------------------
            # WINDOW SIZE DROPDOWN
            # ------------------------------------------------------------
            html.Div(
                [
                    html.Label("Window Size:", style={"color": "#00FFAA", "marginRight": "8px"}),
                    dcc.Dropdown(
                        id="window-size",
                        options=[
                            {"label": "200 rows", "value": 200},
                            {"label": "500 rows", "value": 500},
                            {"label": "1000 rows", "value": 1000},
                            {"label": "2000 rows", "value": 2000},
                            {"label": "5000 rows", "value": 5000},
                            {"label": "10000 rows", "value": 10000},
                            {"label": "20000 rows (max)", "value": 20000},
                        ],
                        value=200,
                        clearable=False,
                        style={"width": "200px"},
                    ),
                    # add near your Window Size dropdown
                    # dcc.Checklist(
                    #     id="auto-scale-toggle",
                    #     options=[{"label": "Auto scale window", "value": "on"}],
                    #     value=["on"],  # default enabled; set [] to default off
                    #     style={"color": "#00FFAA", "marginLeft": "12px"}
                    # ),
                    # keep the dropdown id="window-size" and the store id="window-size-store"
                ],
                className="controls-row",
            ),

            # ------------------------------------------------------------
            # STORES
            # ------------------------------------------------------------
            dcc.Store(id="folder-store"),
            dcc.Store(id="data-ready", data=False),
            dcc.Store(id="tab-selector", data="all"),
            dcc.Store(id="row-count"),
            dcc.Store(id="row-pointer", data=0),
            dcc.Store(id="playback-mode", data={"initialized": False, "playing": False}),
            dcc.Store(id="window-size-store", data=200),
            dcc.Store(id="window-df"),
            dcc.Store(id="max-rows"),
            dcc.Store(id="data-meta", data={}),

            # ------------------------------------------------------------
            # INTERVAL TIMER
            # ------------------------------------------------------------
            dcc.Interval(id="playback-interval", interval=2000, n_intervals=0),

            # ------------------------------------------------------------
            # PLOTS
            # ------------------------------------------------------------
            html.Div(
                [
                    dcc.Graph(id="plot-voltage", style={"height": "300px"}),
                    html.Hr(),
                    dcc.Graph(id="plot-current", style={"height": "300px"}),
                    html.Hr(),
                    dcc.Graph(id="plot-temp", style={"height": "300px"}),
                    html.Hr(),
                    dcc.Graph(id="plot-strain", style={"height": "300px"}),
                ],
                className="plots-wrap",
            ),
        ]
    )