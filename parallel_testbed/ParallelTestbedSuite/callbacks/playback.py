# -*- coding: utf-8 -*-
"""
Created on Thu Oct 16 12:16:48 2025

@author: Malichi Flemming II
"""

from dash import Input, Output, State, ctx
from dash.exceptions import PreventUpdate

def register_playback_callbacks(app):
    @app.callback(
        Output('row-pointer', 'data'),
        Output('playback-mode', 'data'),
        Input('btn-back', 'n_clicks'),
        Input('btn-forward', 'n_clicks'),
        Input('btn-play', 'n_clicks'),
        Input('btn-pause', 'n_clicks'),
        State('row-pointer', 'data'),
        State('row-count', 'data'),
        State('window-size', 'value')
    )
    def handle_controls(back, forward, play, pause, pointer, row_count, window_size):
        triggered = ctx.triggered_id
        pointer = max(0, pointer)
        if triggered == 'btn-back':
            return max(pointer - 1, 0), 'pause'
        elif triggered == 'btn-forward':
            return min(pointer + 1, row_count-window_size), 'pause'
        elif triggered == 'btn-play':
            return pointer, 'play'
        elif triggered == 'btn-pause':
            return pointer, 'pause'
        raise PreventUpdate

    @app.callback(
        Output('row-pointer', 'data', allow_duplicate=True),
        Input('interval', 'n_intervals'),
        State('playback-mode', 'data'),
        State('row-pointer', 'data'),
        State('row-count', 'data'),
        State('window-size', 'value'),
        prevent_initial_call=True
    )
    def auto_advance(n, mode, pointer, row_count, window_size):
        if mode != 'play':
            raise PreventUpdate
        max_pointer = max(0, row_count - window_size)
        return min(pointer + 1, max_pointer)