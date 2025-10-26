# -*- coding: utf-8 -*-
"""
Created on Thu Oct 16 12:20:40 2025

@author: Malichi Flemming II
"""

import plotly.graph_objects as go
from config import type_colors

def make_plot(df_window, col):
    fig = go.Figure()

    # Match color based on type
    color = next((type_colors[key] for key in type_colors if key.lower() in col.lower()), '#888')

    fig.add_trace(go.Scatter(
        x=df_window.index,
        y=df_window[col],
        mode='lines+markers',
        name=col,
        line=dict(color=color, width=2),
        marker=dict(size=6)
    ))

    # Add cycle markers if available
    if 'Cycle_1' in df_window.columns:
        cycle_changes = df_window['Cycle_1'].ne(df_window['Cycle_1'].shift()).cumsum()
        cycle_starts = df_window.groupby(cycle_changes).head(1).index
        for idx in cycle_starts:
            fig.add_vline(
                x=idx,
                line=dict(color="white", width=2),
                annotation_text=f"Cycle {df_window.loc[idx, 'Cycle_1']}",
                annotation_position="top left",
                annotation=dict(bgcolor="rgba(0,0,0,0.6)", font=dict(color="white"))
            )

    fig.update_layout(
        margin=dict(t=30, b=20, l=10, r=10),
        height=300,
        title=col,
        plot_bgcolor="#1E1E2F",
        paper_bgcolor="#1E1E2F",
        font=dict(color="#FAFAFA")
    )
    return fig