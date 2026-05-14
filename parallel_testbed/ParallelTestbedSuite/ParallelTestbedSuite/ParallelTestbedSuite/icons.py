# -*- coding: utf-8 -*-
"""
Created on Fri Feb 27 16:23:04 2026

@author: malichi
"""

#icons.py
from dash import html, dcc
import math

# ---------------------------------------------------------
# BATTERY ICON (OLD STYLE)
# ---------------------------------------------------------
def battery_icon(pct, is_charging=False, highlight=False):
    pct = max(0, min(100, pct))

    # SIMPLE COLOR RULE: green above 20%, red at or below 20%
    if pct <= 20:
        fill_color = "#FF3333"
        blink = pct <= 10
    else:
        fill_color = "#00FF00"
        blink = False

    outer_style = {
        "width": "120px",
        "height": "270px",
        "border": "4px solid black",
        "borderRadius": "10px",
        "position": "relative",
        "backgroundColor": "black",
        "overflow": "hidden",
        "display": "flex",
        "flexDirection": "row",
        "justifyContent": "flex-start",
        "alignItems": "center",
        "margin": "0 auto",
        "boxShadow": "0 0 18px rgba(0,255,170,0.25)" if highlight else "none",
        "animation": "blink 1s infinite" if blink else "none",
    }

    return html.Div(
        [
            # Top terminal
            html.Div(style={
                "position": "absolute",
                "top": "-14px",
                "left": "50%",
                "transform": "translateX(-50%)",
                "width": "30px",
                "height": "10px",
                "backgroundColor": "black",
                "border": "3px solid black",
                "borderRadius": "4px",
            }),

            # Fill bar
            html.Div(style={
                "position": "absolute",
                "bottom": "0",
                "left": "0",
                "width": "100%",
                "height": f"{pct}%",
                "backgroundColor": fill_color,
                "transition": "height 0.3s ease-in-out",
                "zIndex": "1",
            }),

           # Charging bolt
           html.Div("⚡", style={
               "position": "absolute",
               "top": "10px",
               "left": "50%",
               "transform": "translateX(-50%)",
               "fontSize": "40px",
               "color": "#FFFF33",
               "textShadow": "0px 0px 8px yellow",
               "display": "block" if is_charging else "none",
                "zIndex": "2",
           }),
           
            # Percentage text
            html.Div(
                f"{pct:.0f}%",
                style={
                    "position": "absolute",
                    "top": "50%",
                    "left": "50%",
                    "transform": "translate(-50%, -50%)",
                    "color": "white",
                    "fontWeight": "bold",
                    "fontSize": "26px",
                    "textShadow": "0px 0px 6px black",
                    "zIndex": "3",
                },
            ),
        ],
        style=outer_style,
    )


# ---------------------------------------------------------
# PACK ICON (OLD STYLE)
# ---------------------------------------------------------

def pack_icon(soc, voltage, current, temp, highlight=False, vshift=52):
    """
    Pack icon with optional vertical shift.
    - soc, voltage, current, temp: numeric values
    - highlight: bool to apply highlight styling
    - vshift: pixels to move the pack content down (positive moves down)
    """
    soc = max(0, min(100, soc))
    fill_color = "#00FF00" if soc > 20 else "#FF3333"

    outer_style = {
        "top": "40px",
        "position": "relative",
        "padding": "4px",
        "minHeight": "200px",            # keep the same height behavior as before
        "width": "160px",
        "backgroundColor": "#000",
        "border": "3px solid #00FFAA" if highlight else "2px solid #333",
        "borderRadius": "12px",
        "boxShadow": "0 0 18px rgba(0,255,170,0.25)" if highlight else "none",
        "overflow": "visible",
        "boxSizing": "border-box",
    }

    # wrapper that will be shifted vertically; absolute children remain positioned relative to this wrapper
    inner_wrapper_style = {
        "position": "relative",
        "transform": f"translateY({vshift}px)" if vshift else "none",
        "width": "100%",
        "height": "100%",
    }

    # fill bar (absolute, anchored to bottom of wrapper)
    fill_bar = html.Div(style={
        "position": "absolute",
        "bottom": "0",
        "left": "0",
        "width": "100%",
        "height": f"{soc}%",
        "backgroundColor": fill_color,
        "transition": "height 0.3s ease-in-out",
        "zIndex": "1",
    })

    # terminals (absolute)
    term_left = html.Div(style={
        "position": "absolute",
        "top": "-70px",
        "left": "25%",
        "transform": "translateX(-50%)",
        "width": "40px",
        "height": "12px",
        "backgroundColor": "#111",
        "border": "3px solid #00FFAA" if highlight else "2px solid #333",
        "borderRadius": "4px",
        "zIndex": "3",
    })
    term_right = html.Div(style={
        "position": "absolute",
        "top": "-70px",
        "left": "75%",
        "transform": "translateX(-50%)",
        "width": "40px",
        "height": "12px",
        "backgroundColor": "#111",
        "border": "3px solid #00FFAA" if highlight else "2px solid #333",
        "borderRadius": "4px",
        "zIndex": "3",
    })

    # text block (kept relative so it moves with the wrapper)
    text_block = html.Div(
        [
            html.Div("PACK SUMMARY"),
            html.Div(f"Voltage: {voltage:.2f} V"),
            html.Div(f"Current: {current:.2f} A"),
            html.Div(f"Temp: {temp:.1f} °C"),
            html.Div(f"SOC: {soc:.1f} %"),
        ],
        style={
            "position": "absolute",
            "zIndex": "2",
            "display": "flex",
            "flexDirection": "column",
            "gap": "4px",
            "padding": "0",
            "color": "white",
            "textShadow": "0px 0px 6px black",
            "fontWeight": "bold",
            "width": "100%",
            "alignItems": "center",
        },
    )

    # assemble: inner wrapper contains absolute elements and text; outer container keeps original sizing
    inner = html.Div(
        [
            fill_bar,
            term_left,
            term_right,
            text_block,
        ],
        style=inner_wrapper_style,
    )

    return html.Div([inner], style=outer_style)


# ---------------------------------------------------------
# CYCLE ICON (unchanged)
# ---------------------------------------------------------

# Map segment name to ring color

_SEGMENT_COLOR = {
    "Charge": "#00C853",
    "ChargeCycle": "#00C853",
    "ChargeWait": "#000000",
    "Wait": "#000000",
    "Discharge": "#D50000",
    "DischargeCycle": "#D50000",
}

def cycle_icon(segment=None, cycle=None, progress=None, size=160, animate=False):

    seg = (segment or "").strip()
    color = _SEGMENT_COLOR.get(seg, "#888888")
    label = str(cycle) if cycle is not None else "--"

    # Progress normalization
    try:
        p = max(0.0, min(100.0, float(progress))) if progress is not None else 0.0
    except Exception:
        p = 0.0

    ring_width = 16
    radius = 80
    circumference = 2 * math.pi * radius
    dashoffset = circumference * (1 - p / 100)

    svg = f"""
    <svg 
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 200 200"
        width="200"
        height="200"
        preserveAspectRatio="xMidYMid meet">

      <!-- Background ring -->
      <circle cx='100' cy='100' r='{radius}'
              stroke='#111' stroke-width='{ring_width}' fill='none'/>

      <!-- Mid ring -->
      <circle cx='100' cy='100' r='{radius}'
              stroke='#444' stroke-width='{ring_width}' fill='none'/>

      <!-- Progress ring -->
      <circle cx='100' cy='100' r='{radius}'
              stroke='{color}' stroke-width='{ring_width}'
              stroke-linecap='round'
              stroke-dasharray='{circumference}'
              stroke-dashoffset='{dashoffset}'
              transform='rotate(-90 100 100)'
              fill='none'/>

      <!-- Center text -->
      <text x='50%' y='50%' dominant-baseline='middle'
            text-anchor='middle'
            font-family='Arial' font-weight='700'
            fill='#FFFFFF'
            font-size='48px'>{label}</text>

    </svg>
    """


    # Encode as data URI
    svg = svg.replace("#", "%23").replace("\n", "")
    src = f"data:image/svg+xml;utf8,{svg}"

    # Return as <img> so Dash 3.x will render it
    return html.Img(
        src=src,
        style={
            "width": f"{size}px",
            "height": f"{size}px",
            "objectFit": "contain",
            "flexShrink": "0",
        }
    )