

import tkinter
import tkinter.font

SCROLL_STEP = 100
CHROME_PX = 100
HSTEP, VSTEP = 13, 18
WIDTH, HEIGHT = 800, 600
INPUT_WIDTH_PX = 200

FONTS = {}


def get_font(size, weight, slant):
    key = (size, weight, slant)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=slant)
        FONTS[key] = font
    return FONTS[key]
