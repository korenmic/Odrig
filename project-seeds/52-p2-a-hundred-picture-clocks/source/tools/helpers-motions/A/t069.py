import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions/A")
from hg import *

entry, pic = load(69)
# The egg rocks on the table about its foot. Only the egg's own colours (5, 6, 7) turn, so
# the table, whose colours are those of the egg's marks (3, 4), stays still. The marks are
# drawn in the wall's colour 2, which a turn draws where a still pixel's place has gone, so
# they move with the egg; two recolourings after the swing give them back their orange
# (the lit side) and brown (the shaded side).
marks = []
egg = pic.copy()
for y in range(5, 49):
    # the egg's span on this row; the band's row takes the span of the rows about it
    xs = [x for x in range(60) for r in (y - 1, y, y + 1) if egg[r, x] >= 5]
    if xs:
        for x in range(min(xs) + 1, max(xs)):
            if pic[y, x] <= 4:
                marks.append((x, y))
                pic[y, x] = 2
# the egg's brown outline pixels above the table (3, 4) become the wall's 2 as well, so
# that none stays behind when the egg moves
for y in range(3, 49):
    for x in range(60):
        if pic[y, x] in (3, 4):
            pic[y, x] = 2
print("marks x", min(x for x, _ in marks), max(x for x, _ in marks), "y", min(y for _, y in marks), max(y for _, y in marks))
parts = [
    swing(bx(4, 3, 56, 57), [5, 6, 7], 2, px(29, 55), 3, 3),
    flicker(bx(14, 29, 34, 43), [[[2, 4]], [[2, 4]]], 6000),
    flicker(bx(34, 29, 44, 43), [[[2, 3]], [[2, 3]]], 6000),
]
save(entry, pic, motion(parts))
