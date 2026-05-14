# -*- coding: utf-8 -*-
"""
Created on Thu Oct  2 21:01:43 2025

@author: malichi
"""

import dash
from dash import Dash
from layout import serve_layout
from callbacks import register_callbacks
# import os
# print("CWD:", os.getcwd())
# print("Files in assets:", os.listdir("assets"))
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Parallel Testbed Suite"
app.layout = serve_layout()
def walk(component):
    ids = []
    if hasattr(component, "id") and component.id is not None:
        ids.append(component.id)
    if hasattr(component, "children"):
        children = component.children
        if isinstance(children, list):
            for c in children:
                ids.extend(walk(c))
        elif children is not None:
            ids.extend(walk(children))
    return ids

print(">>> LAYOUT IDS:", walk(app.layout))

register_callbacks(app)
print("\n=== CALLBACK MAP ===")
for cid, cdef in app.callback_map.items():
    print(f"\nCallback ID: {cid}")
    print("  Outputs:", cdef["output"])
    print("  Inputs:", cdef["inputs"])
    print("  State:", cdef["state"])
    print("  allow_duplicate:", cdef.get("allow_duplicate"))
if __name__ == "__main__":
    app.run(debug=False)