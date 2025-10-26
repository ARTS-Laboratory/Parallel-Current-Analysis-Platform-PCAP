# -*- coding: utf-8 -*-
"""
Created on Thu Oct 16 12:17:41 2025

@author: Malichi Flemming II
"""

from dash import Input, Output, State
from dash.exceptions import PreventUpdate

def register_scroll_callbacks(app):
    app.clientside_callback(
        """
        function(n) {
            if (typeof window.latestScrollMode === 'string') {
                return window.latestScrollMode;
            }
            return 'pause';
        }
        """,
        Output('scroll-mode', 'data'),
        Input('scroll-listener', 'n_intervals'),
        prevent_initial_call=True
    )

    @app.callback(
        Output('row-pointer', 'data', allow_duplicate=True),
        Input('scroll-interval', 'n_intervals'),
        State('scroll-mode', 'data'),
        State('row-pointer', 'data'),
        State('row-count', 'data'),
        State('window-size', 'value'),
        prevent_initial_call=True
    )
    def scroll_while_holding(n, mode, pointer, row_count, window_size):
        if mode == 'back':
            return max(pointer - 1, 0)
        elif mode == 'forward':
            return min(pointer + 1, row_count - window_size)
        raise PreventUpdate
        
    @app.callback(Output('pointer-debug', 'children'), Input('row-pointer', 'data'))
    def show_pointer(pointer):
        return f"🔢 Row pointer: {pointer}"
