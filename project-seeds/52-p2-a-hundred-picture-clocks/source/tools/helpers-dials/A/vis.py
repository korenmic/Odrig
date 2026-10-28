import sys, math
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
n = int(sys.argv[1]); L = float(sys.argv[2]); light = {int(c) for c in sys.argv[3]}
cands = [tuple(int(v) for v in c.split(",")) for c in sys.argv[4:]]
e, p = edit.load_work(n)
for (px, py) in cands:
    hours = []
    for hr in range(12):
        a = math.radians(hr * 30)
        dx, dy = math.sin(a), -math.cos(a)
        vis = 0
        for k in range(1, int(L * 2) + 1):
            t = k / 2
            x, y = round(px + dx * t), round(py + dy * t)
            if 0 <= x < 60 and 0 <= y < 60 and int(p[y, x]) in light:
                vis += 1
        hours.append(vis // 2)
    print((px, py), "visible px per hour 12..11:", hours, "hours with >=3:", sum(v >= 3 for v in hours))
