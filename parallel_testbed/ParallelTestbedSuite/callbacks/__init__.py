# -*- coding: utf-8 -*-
"""
Created on Thu Oct 16 12:15:39 2025

@author: Malichi Flemming II
"""

from .file import register_file_callbacks
from .playback import register_playback_callbacks
from .scroll import register_scroll_callbacks
from .battery import register_battery_callbacks
from .plots import register_plot_callbacks

def register_all_callbacks(app):
    register_file_callbacks(app)
    register_playback_callbacks(app)
    register_scroll_callbacks(app)
    register_battery_callbacks(app)
    register_plot_callbacks(app)