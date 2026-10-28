import sys; sys.path.insert(0, r'C:/Users/koren/src/Odrig/scratch/clocks52/tools'); import edit, numpy

PLAIN = edit.DIAL
SECS = edit.DIAL_WITH_SECONDS

def f(left, top, width, height, font, pattern, digits, colons=None, blink=True, offset=0):
    return {"left": left, "top": top, "width": width, "height": height, "font": font, "pattern": pattern,
            "digits": digits, "colons": digits if colons is None else colons, "blink": blink, "offset": offset}

def clock(fields):
    secs = any(c in fl["pattern"] for fl in fields for c in "Ss")
    return dict(SECS if secs else PLAIN, fields=fields)

TILES = {}
def tile(n):
    def deco(fn):
        TILES[n] = fn
        return fn
    return deco

@tile(21)
def t21(p):
    edit.replace_box(p, (18, 25, 54, 42), {1, 2, 4}, 0)
    edit.replace_box(p, (18, 42, 46, 43), {1, 2, 4}, 0)
    return [f(18, 30, 33, 10, "medium", "Ih:Mm", 4)]

@tile(22)
def t22(p):
    edit.fill_box(p, (14, 24, 51, 42), 0)
    return [f(16, 28, 33, 10, "medium", "Ih:Mm", 5)]

@tile(23)
def t23(p):
    edit.fill_box(p, (18, 22, 54, 40), 0)
    return [f(17, 26, 33, 10, "medium", "Ih:Mm", 6)]

@tile(24)
def t24(p):
    # left flap interior x 10..26, right flap x 38..53
    edit.replace_box(p, (10, 24, 27, 42), {0, 2, 3, 4, 5, 6, 7}, 1)
    edit.replace_box(p, (38, 23, 54, 41), {0, 2, 3, 4, 5, 6, 7}, 1)
    edit.fill_box(p, (10, 32, 27, 33), 0)
    edit.fill_box(p, (38, 31, 54, 32), 0)
    return [f(10, 27, 17, 10, "medium", "Hh", 7, blink=False), f(39, 26, 15, 10, "medium", "Mm", 7, blink=False)]

@tile(25)
def t25(p):
    edit.replace_box(p, (6, 18, 12, 42), {5, 6, 7}, 4)
    edit.replace_box(p, (5, 24, 6, 42), {5, 6, 7}, 4)
    edit.replace_box(p, (20, 18, 30, 40), {5, 7}, 4)
    edit.replace_box(p, (21, 18, 30, 40), {6}, 4)
    edit.replace_box(p, (34, 18, 44, 39), {5, 6, 7}, 4)
    edit.replace_box(p, (48, 18, 57, 40), {5, 6, 7}, 4)
    return [f(5, 26, 8, 10, "medium", "H", 5, blink=False), f(20, 25, 10, 10, "medium", "h", 5, blink=False),
            f(34, 24, 10, 10, "medium", "M", 5, blink=False), f(48, 23, 10, 10, "medium", "m", 5, blink=False)]

@tile(26)
def t26(p):
    edit.replace_box(p, (6, 18, 56, 39), {2, 4, 6, 7}, 1)
    return [f(6, 22, 48, 14, "large", "Ih:Mm", 6)]

@tile(27)
def t27(p):
    edit.fill_box(p, (19, 28, 41, 37), 7)
    return [f(18, 29, 23, 7, "small", "Ih:Mm", 1)]

@tile(28)
def t28(p):
    edit.fill_box(p, (19, 31, 40, 40), 0)
    edit.fill_box(p, (26, 30, 37, 31), 0)
    return [f(18, 31, 23, 7, "small", "Ih:Mm", 7)]

@tile(29)
def t29(p):
    edit.replace_box(p, (19, 20, 33, 43), {3, 4, 5, 6, 7}, 1)
    edit.replace_box(p, (19, 22, 33, 43), {2}, 1)
    return [f(18, 20, 15, 10, "medium", "Hh", 7, blink=False), f(18, 32, 15, 10, "medium", "Mm", 7, blink=False)]

@tile(30)
def t30(p):
    edit.replace_box(p, (16, 27, 49, 37), {1, 2, 3, 6, 7}, 0)
    return [f(18, 27, 29, 10, "medium", "Ih:Mm", 7)]

@tile(51)
def t51(p):
    edit.fill_box(p, (10, 41, 54, 51), 0)
    return [f(13, 42, 39, 7, "small", "Hh:Mm:Ss", 5)]

@tile(52)
def t52(p):
    edit.replace_box(p, (11, 34, 53, 46), {1, 2, 3, 4, 5, 6, 7}, 0)
    return [f(13, 36, 39, 7, "small", "Hh:Mm:Ss", 7)]

@tile(53)
def t53(p):
    edit.replace_box(p, (10, 34, 51, 43), {0, 2, 3, 4, 5, 6, 7}, 1)
    edit.replace_box(p, (14, 30, 51, 34), {0, 2, 3, 4, 5, 6, 7}, 1)
    return [f(11, 35, 39, 7, "small", "Hh:Mm:Ss", 6)]

@tile(60)
def t60(p):
    edit.fill_box(p, (31, 24, 54, 34), 1)
    edit.fill_box(p, (31, 34, 54, 42), 1)
    edit.fill_box(p, (31, 44, 54, 51), 0)
    return [f(29, 24, 25, 7, "small", "Hh:Mm", 6, offset=0), f(29, 34, 25, 7, "small", "Hh:Mm", 6, offset=-7),
            f(29, 44, 25, 7, "small", "Hh:Mm", 6, offset=-2)]

@tile(64)
def t64(p):
    edit.fill_box(p, (12, 27, 46, 43), 1)
    return [f(15, 30, 29, 10, "medium", "Ih:Mm", 7)]

@tile(66)
def t66(p):
    edit.replace_box(p, (14, 27, 52, 44), {1, 2, 4, 6}, 0)
    return [f(18, 31, 31, 10, "medium", "Mm:Ss", 6)]

@tile(67)
def t67(p):
    edit.replace_box(p, (11, 29, 48, 44), {1, 2, 4}, 0)
    return [f(14, 31, 31, 10, "medium", "Mm:Ss", 4)]

@tile(75)
def t75(p):
    edit.fill_box(p, (18, 28, 45, 38), 7)
    return [f(19, 30, 25, 7, "small", "Mm:Ss", 1)]

@tile(81)
def t81(p):
    edit.fill_box(p, (19, 19, 42, 27), 6)
    return [f(19, 19, 23, 7, "small", "Ih:Mm", 3)]

@tile(83)
def t83(p):
    edit.replace_box(p, (16, 39, 42, 50), {1, 2, 3, 5}, 0)
    return [f(16, 39, 25, 10, "medium", "m:Ss", 5)]

@tile(84)
def t84(p):
    edit.replace_box(p, (24, 40, 38, 52), {1, 2, 6}, 0)
    return [f(24, 41, 14, 10, "medium", "Ss", 6, blink=False)]

@tile(85)
def t85(p):
    edit.replace_box(p, (17, 30, 45, 43), {1, 2}, 0)
    return [f(16, 31, 30, 10, "medium", "Ih:Mm", 2)]

@tile(86)
def t86(p):
    edit.fill_box(p, (20, 22, 41, 31), 0)
    return [f(21, 24, 19, 5, "tiny", "Hh:Mm", 7)]

@tile(89)
def t89(p):
    edit.replace_box(p, (23, 24, 52, 41), {0, 2, 3, 4, 5, 7}, 1)
    return [f(22, 28, 30, 10, "medium", "Hh:Mm", 7)]

@tile(97)
def t97(p):
    edit.fill_box(p, (23, 25, 49, 28), 2)
    edit.fill_box(p, (22, 28, 48, 41), 3)
    return [f(19, 28, 29, 10, "medium", "Ih:Mm", 6)]

@tile(98)
def t98(p):
    edit.replace_box(p, (25, 30, 48, 43), {3, 5, 6, 7}, 4)
    edit.replace_box(p, (25, 29, 48, 30), {4}, 3)
    return [f(25, 32, 23, 7, "small", "Ih:Mm", 7)]

@tile(99)
def t99(p):
    edit.fill_box(p, (19, 33, 43, 43), 2)
    return [f(19, 34, 23, 7, "small", "Ih:Mm", 7)]

@tile(100)
def t100(p):
    edit.replace_box(p, (21, 24, 40, 33), {1, 2, 3, 4, 5, 6, 7}, 0)
    return [f(19, 25, 23, 7, "small", "Ih:Mm", 7)]

if __name__ == "__main__":
    show = "-q" not in sys.argv
    for n in [int(a) for a in sys.argv[1:] if a != "-q"]:
        entry, p = edit.load(n)
        fields = TILES[n](p)
        path = edit.write(entry, p, clock=clock(fields))
        print("wrote", path)
