# -*- coding: utf-8 -*-
"""
Created on Thu Oct  2 21:01:43 2025

@author: Malichi Flemming II
"""

from dash import Dash
from layout import layout
from callbacks import register_all_callbacks

app = Dash(__name__, assets_folder='assets')
app.title = "Point-by-Point Dashboard"
app.layout = layout

register_all_callbacks(app)

if __name__ == '__main__':
    app.run(debug=True)
