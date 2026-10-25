"""Draw a schematic symbol for every RTL module -> docs/figures/symbols/<module>.svg

The symbols are generated from the module headers (rtl.py), so they always
show the real port names, directions, widths and groupings.
"""

import os

from rtl import load_all
from svgkit import Canvas, INK, MUTED

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "figures", "symbols"))
MONO = "Menlo, Consolas, monospace"
ROW, GAP, STUB, CW = 19, 9, 34, 7.0     # row pitch, group gap, stub length, char width


def rows(ports):
    """Y offsets for ports, leaving a gap between RTL groups."""
    ys, y, last = [], 0, None
    for p in ports:
        if last is not None and p.group != last:
            y += GAP
        ys.append(y)
        y += ROW
        last = p.group
    return ys, y


def label(p):
    return p.name + (f"[{p.msb}:{p.lsb}]" if p.width > 1 else "")


def draw(mod):
    ins = [p for p in mod.ports if p.dir == "in"]
    outs = [p for p in mod.ports if p.dir == "out"]
    yin, hin = rows(ins)
    yout, hout = rows(outs)
    lw = max((len(label(p)) for p in ins), default=0) * CW
    rw = max((len(label(p)) for p in outs), default=0) * CW
    params = [f"{p.name} = {p.default}" for p in mod.params]
    pw = max((len(s) for s in params), default=0) * CW + 20
    bw = max(lw + rw + 50, pw, len(mod.name) * 8.5 + 20, 170)
    head = 14 + (len(params) * 15 + 8 if params else 0)
    bh = head + max(hin, hout) + 10
    x0, y0 = STUB + 34, 44
    W, H = int(x0 + bw + STUB + 34), int(y0 + bh + 34)

    c = Canvas(W, H)
    c.text(x0 + bw / 2, y0 - 12, mod.name, size=15, weight="bold")
    c.rect(x0, y0, bw, bh, fill="#f8fafc", rx=3)
    for k, s in enumerate(params):
        c.text(x0 + bw / 2, y0 + 18 + k * 15, "#(" + s + ")" if len(params) == 1 else s,
               size=10.5, italic=True, color=MUTED, family=MONO)

    def stub(x1, x2, y, p, side):
        bus = p.width > 1
        c.wire([(x1, y), (x2, y)], sw=2.6 if bus else 1.4, arrow=False)
        if bus:
            mx = (x1 + x2) / 2
            c.raw(f'<line x1="{mx - 4:.1f}" y1="{y + 5:.1f}" x2="{mx + 4:.1f}" y2="{y - 5:.1f}" '
                  f'stroke="{INK}" stroke-width="1.2"/>')
            c.text(mx, y - 7, str(p.width), size=9, color=MUTED)

    for p, dy in zip(ins, yin):
        y = y0 + head + dy + ROW / 2 + 4
        stub(x0 - STUB, x0, y, p, "in")
        c.raw(f'<polygon points="{x0 - 9:.1f},{y - 4:.1f} {x0:.1f},{y:.1f} '
              f'{x0 - 9:.1f},{y + 4:.1f}" fill="{INK}"/>')
        if p.name == "clk":
            c.poly([(x0, y - 6), (x0 + 9, y), (x0, y + 6)], fill="none", sw=1.2)
            c.text(x0 + 13, y + 4, label(p), anchor="start", size=11, family=MONO)
        else:
            c.text(x0 + 6, y + 4, p.name, anchor="start", size=11, family=MONO)
            if p.width > 1:
                c.text(x0 + 6 + len(p.name) * CW + 1, y + 4, f"[{p.msb}:{p.lsb}]",
                       anchor="start", size=11, color=MUTED, family=MONO)
    for p, dy in zip(outs, yout):
        y = y0 + head + dy + ROW / 2 + 4
        stub(x0 + bw, x0 + bw + STUB, y, p, "out")
        c.raw(f'<polygon points="{x0 + bw + STUB - 8:.1f},{y - 4:.1f} {x0 + bw + STUB:.1f},{y:.1f} '
              f'{x0 + bw + STUB - 8:.1f},{y + 4:.1f}" fill="{INK}"/>')
        rng = f"[{p.msb}:{p.lsb}]" if p.width > 1 else ""
        c.text(x0 + bw - 6, y + 4, rng, anchor="end", size=11, color=MUTED, family=MONO)
        c.text(x0 + bw - 6 - len(rng) * CW - (1 if rng else 0), y + 4, p.name,
               anchor="end", size=11, family=MONO)
    c.text(x0 + bw / 2, y0 + bh + 20, mod.file, size=10, color=MUTED, family=MONO)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, mod in load_all().items():
        draw(mod).save(os.path.join(OUT, name + ".svg"))
        print("wrote", os.path.join("figures", "symbols", name + ".svg"))


if __name__ == "__main__":
    main()
