"""Tile 55, a satellite: its signal arcs light one after another, inner, middle, outer, then again."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib import *

entry, pic = load(55)
H = [[4, 2], [5, 2]]  # an arc not lit: its blue pixels become the dark of space
STEP = 400
parts = [
    flicker(bx(44, 33, 48, 47), [H, [], []], STEP),   # middle arc, its right side
    flicker(bx(33, 46, 44, 50), [H, [], []], STEP),   # middle arc, its bottom
    flicker(bx(48, 29, 53, 49), [H, H, []], STEP),    # outer arc, its right side
    flicker(bx(44, 47, 48, 50), [H, H, []], STEP),    # outer arc, its corner
    flicker(bx(33, 50, 48, 55), [H, H, []], STEP),    # outer arc, its bottom
]
save(entry, pic, motion(parts, seconds=12))
