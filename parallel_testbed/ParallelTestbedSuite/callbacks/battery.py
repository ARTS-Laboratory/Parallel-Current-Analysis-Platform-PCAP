# -*- coding: utf-8 -*-
"""
Created on Thu Oct 16 12:18:08 2025

@author: Malichi Flemming II
"""

import os
import pandas as pd
from dash import Input, Output, html
from dash.exceptions import PreventUpdate
from config import DATA_DIR

def register_battery_callbacks(app):
    @app.callback(
        Output('battery-icons', 'children'),
        Input('file-dropdown', 'value'),
        Input('row-pointer', 'data'),
        Input('window-size', 'value')
    )
    def update_battery_icons(filename, pointer, window_size):
        if not filename:
            raise PreventUpdate
        path = os.path.join(DATA_DIR, filename)
        df = pd.read_csv(path)
        end = min(max(pointer + window_size, 0), len(df))
        df_window = df.iloc[pointer:end]
        latest = df_window.iloc[-1]

        soc_cols = [col for col in df.columns if 'SOC' in col or 'COC' in col]
        current_col = next((col for col in df.columns if 'Current' in col), None)

        icons = []
        for col in soc_cols:
            soc = latest[col]
            charging = latest[current_col] > 0 if current_col else False
            fill_color = '#32CD32' if charging else '#FF4B4B'
            icons.append(html.Div([
                html.Div(style={
                    'width': '100px', 'height': '200px', 'border': '4px solid #FAFAFA',
                    'borderRadius': '10px', 'position': 'relative',
                    'overflow': 'hidden', 'backgroundColor': '#1E1E2F'
                }, children=[
                    html.Div(style={
                        'position': 'absolute', 'bottom': '0', 'width': '100%',
                        'height': f'{soc}%', 'backgroundColor': fill_color,
                        'transition': 'height 0.5s ease-in-out'
                    }),
                    html.Div(f"{int(soc)}%", style={
                        'position': 'absolute', 'top': '50%', 'left': '50%',
                        'transform': 'translate(-50%, -50%)', 'color': '#FAFAFA',
                        'fontWeight': 'bold', 'fontSize': '24px'
                    })
                ]),
                html.Div(col, style={'textAlign': 'center', 'marginTop': '8px'})
            ], style={'textAlign': 'center'}))
        return icons