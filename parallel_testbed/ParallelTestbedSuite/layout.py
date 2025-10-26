# -*- coding: utf-8 -*-
"""
Created on Thu Oct 16 12:11:31 2025

@author: Malichi Flemming II
"""

from dash import html, dcc
from config import DATA_DIR, button_style
import os

layout = html.Div(style={'backgroundColor': '#1E1E2F', 'color': '#FAFAFA'}, children=[
    html.Div([
        html.Label("Select File"),
        dcc.Dropdown(id='file-dropdown', options=[
            {'label': f, 'value': f} for f in os.listdir(DATA_DIR) if f.endswith(('.csv', '.txt'))
        ], value=None, style={'width': '300px', 'color': '#000'})
    ], style={'padding': '20px'}),

   html.Div([
       html.Div(id='cycle-display', style={
            'width': '160px',
            'height': '160px',
            'borderRadius': '50%',
            'border': '6px solid #00FFAA',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center',
            'fontSize': '28px',
            'fontWeight': 'bold',
            'color': '#00FFAA',
            'marginRight': '40px',
            'boxShadow': '0 0 20px rgba(0,255,255,0.4)',
            'backgroundColor': '#1E1E2F'
        }),
        html.Div(id='battery-icons', style={'display': 'flex', 'gap': '40px'})
    ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '20px'}),

    html.Div(id='plot-grid', style={'padding': '20px'}),

    html.Div([
    dcc.Store(id='row-count', data=600),
    dcc.Store(id='row-pointer', data=0),
    dcc.Store(id='playback-mode', data='pause'),
    dcc.Store(id='scroll-mode', data='pause'),

    html.Label("Window Size"),
    dcc.Slider(id='window-size', min=10, max=2000, step=10, value=50,
               marks={i: str(i) for i in range(10, 2001, 250)},
               tooltip={"placement": "bottom", "always_visible": True}),

    html.Div([
        html.Button("⏮ Back", id="btn-back", n_clicks=0, style=button_style),
        html.Button("▶️ Play", id="btn-play", n_clicks=0, style=button_style),
        html.Button("⏸ Pause", id="btn-pause", n_clicks=0, style=button_style),
        html.Button("⏭ Forward", id="btn-forward", n_clicks=0, style=button_style),
    ], style={
        'display': 'flex', 'justifyContent': 'center', 'gap': '20px',
        'margin': '30px auto', 'padding': '20px', 'backgroundColor': '#2C2C3C',
        'borderRadius': '12px', 'boxShadow': '0 0 20px rgba(0,255,255,0.2)'
    }),

    dcc.Interval(id='interval', interval=5000, n_intervals=0),
    dcc.Interval(id='scroll-interval', interval=150, n_intervals=0),
    dcc.Interval(id='scroll-listener', interval=300, n_intervals=0),

    html.Div(id='pointer-debug', style={
        'fontSize': '20px',
        'color': '#FFD700',
        'textAlign': 'center',
        'marginTop': '10px'
    })
], style={'padding': '20px'})
              
])