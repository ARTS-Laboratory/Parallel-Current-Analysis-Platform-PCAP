# -*- coding: utf-8 -*-
"""
Created on Thu Oct 16 12:16:27 2025

@author: Malichi Flemming II
"""

import os
import pandas as pd
from dash import Input, Output
from config import DATA_DIR

def register_file_callbacks(app):
    @app.callback(Output('cycle-display', 'children'),
              Input('file-dropdown', 'value'),
              Input('row-pointer', 'data'),
                  Input('window-size', 'value'))
    def update_cycle_display(filename, pointer, window_size):
        if not filename:
            return "N/A"
        path = os.path.join(DATA_DIR, filename)
        df = pd.read_csv(path)
        pointer = max(0, pointer)
        end = min(max(pointer + window_size, 0), len(df))
        cycle = df.loc[end - 1, 'Cycle_1'] if 'Cycle_1' in df.columns else end - 1
        return f"{cycle}"