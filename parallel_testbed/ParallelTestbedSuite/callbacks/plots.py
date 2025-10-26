# -*- coding: utf-8 -*-
"""
Created on Thu Oct 16 12:18:30 2025

@author: Malichi Flemming II
"""

import os
import pandas as pd
from dash import Input, Output
from dash.exceptions import PreventUpdate
from config import DATA_DIR
from utils.helpers import make_plot
from dash import html, dcc

def register_plot_callbacks(app):
    @app.callback(
        Output('plot-grid', 'children'),
        Input('file-dropdown', 'value'),
        Input('row-pointer', 'data'),
        Input('window-size', 'value')
    )
    def update_plots(filename, pointer, window_size):
        if not filename:
            raise PreventUpdate
        path = os.path.join(DATA_DIR, filename)
        df = pd.read_csv(path)
        end = min(pointer + window_size, len(df))
        df_window = df.iloc[pointer:end]

        numeric_cols = df.select_dtypes(include='number').columns
        target_keywords = ['Current', 'Voltage', 'Strain', 'Temp']
        filtered_cols = [col for col in numeric_cols if any(key in col for key in target_keywords)]
        filtered_cols = [col for col in filtered_cols if not col.startswith('Cycle') or col == 'Cycle_1']

        plots = []
        for i in range(0, len(filtered_cols), 4):
            chunk = filtered_cols[i:i+4]
            grid = html.Div([
                html.Div([
                    dcc.Graph(figure=make_plot(df_window, col), style={'height': '300px'})
                ]) for col in chunk
            ], style={
                'display': 'grid',
                'gridTemplateColumns': '1fr 1fr',
                'gap': '20px'
            })
            plots.append(html.Div([grid], style={
                'backgroundColor': '#2C2C3C',
                'padding': '20px',
                'borderRadius': '12px',
                'border': '2px solid #00BFFF',
                'marginBottom': '20px'
            }))
        return plots