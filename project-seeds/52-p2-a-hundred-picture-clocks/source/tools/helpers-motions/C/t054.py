"""Tile 54, a radio mast: its arcs light one after another, inner, middle, outer, then again."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib import *

entry, pic = load(54)
H = [[6, 5], [7, 5]]  # an arc not lit: its light pixels become the sky
STEP = 400
parts = [
    flicker(bx(19, 9, 23, 22), [H, [], []], STEP),   # middle arc, left
    flicker(bx(41, 9, 44, 22), [H, [], []], STEP),   # middle arc, right
    flicker(bx(13, 12, 19, 26), [H, H, []], STEP),   # outer arc, left
    flicker(bx(19, 22, 20, 26), [H, H, []], STEP),   # outer arc, left, its foot
    flicker(bx(44, 5, 50, 26), [H, H, []], STEP),    # outer arc, right
]
save(entry, pic, motion(parts, seconds=12))
