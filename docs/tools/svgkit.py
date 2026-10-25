"""Tiny SVG drawing helpers shared by the hand-placed block diagrams.

No third-party dependencies. Coordinates are absolute pixels; every figure
script builds a Canvas, draws into it, and writes one .svg file.
"""

from xml.sax.saxutils import escape

INK = "#1e293b"      # data wires, outlines, text
CTRL = "#c2410c"     # control signals from / status to the FSM
REG_FILL = "#dbeafe"  # sequential elements
MUX_FILL = "#f1f5f9"  # muxes
COMB_FILL = "#ffffff"  # combinational blocks
MUTED = "#64748b"
FONT = "Helvetica, Arial, sans-serif"


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.items = []

    # ---------- primitives ----------
    def raw(self, s):
        self.items.append(s)

    def text(self, x, y, s, anchor="middle", size=12, weight="normal",
             color=INK, italic=False, family=FONT):
        style = "font-style:italic;" if italic else ""
        self.raw(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
                 f'font-family="{family}" font-size="{size}" font-weight="{weight}" '
                 f'fill="{color}" style="{style}">{escape(s)}</text>')

    def rect(self, x, y, w, h, fill=COMB_FILL, stroke=INK, sw=1.4, rx=0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def poly(self, pts, fill=COMB_FILL, stroke=INK, sw=1.4):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.raw(f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def wire(self, pts, color=INK, sw=1.6, arrow=True, dash=None):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        m = ' marker-end="url(#arr)"' if arrow and color == INK else (
            ' marker-end="url(#arrc)"' if arrow else "")
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.raw(f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{sw}" '
                 f'stroke-linejoin="round"{d}{m}/>')

    def dot(self, x, y, color=INK):
        self.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}"/>')

    # ---------- composite parts ----------
    def reg(self, x, y, w, h, name, sub=None):
        """Edge-triggered register: filled box with a clock wedge."""
        self.rect(x, y, w, h, fill=REG_FILL)
        self.poly([(x + w / 2 - 7, y + h), (x + w / 2, y + h - 8), (x + w / 2 + 7, y + h)],
                  fill="none")
        self.text(x + w / 2, y + h / 2 + 4 - (5 if sub else 0), name, size=13, weight="bold")
        if sub:
            self.text(x + w / 2, y + h / 2 + 11, sub, size=9.5, color=MUTED)

    def mux(self, x, y, w, h, labels, flip=False):
        """Trapezoid mux. Inputs on the wide side (left, or right if flip).
        Returns (input_ys, output_xy, select_xy)."""
        inset = min(h * 0.18, 16)
        if not flip:
            pts = [(x, y), (x + w, y + inset), (x + w, y + h - inset), (x, y + h)]
        else:
            pts = [(x, y + inset), (x + w, y), (x + w, y + h), (x, y + h - inset)]
        self.poly(pts, fill=MUX_FILL)
        n = len(labels)
        ys = [y + (i + 0.5) * h / n for i in range(n)]
        for yy, lab in zip(ys, labels):
            if not flip:
                self.text(x + 4, yy + 3.5, lab, anchor="start", size=9.5, color=MUTED)
            else:
                self.text(x + w - 4, yy + 3.5, lab, anchor="end", size=9.5, color=MUTED)
        out = (x + w, y + h / 2) if not flip else (x, y + h / 2)
        sel = (x + w / 2, y + h - inset / 2)
        return ys, out, sel

    def ctrl_in(self, x, y, label, side="below", length=22, anchor=None):
        """Dashed control signal arriving from the FSM, pointing at (x, y)."""
        if side == "below":
            self.wire([(x, y + length), (x, y + 2)], color=CTRL, sw=1.3, dash="4,3")
            self.text(x, y + length + 11, label, size=10.5, color=CTRL,
                      anchor=anchor or "middle", family="Menlo, Consolas, monospace")
        elif side == "above":
            self.wire([(x, y - length), (x, y - 2)], color=CTRL, sw=1.3, dash="4,3")
            self.text(x, y - length - 4, label, size=10.5, color=CTRL,
                      anchor=anchor or "middle", family="Menlo, Consolas, monospace")
        elif side == "left":
            self.wire([(x - length, y), (x - 2, y)], color=CTRL, sw=1.3, dash="4,3")
            self.text(x - length - 4, y + 4, label, size=10.5, color=CTRL,
                      anchor=anchor or "end", family="Menlo, Consolas, monospace")

    def status_out(self, x0, y0, x1, y1, label, anchor="middle", dx=0, dy=0):
        """Solid status signal from the datapath to the FSM."""
        self.wire([(x0, y0), (x1, y1)], color=CTRL, sw=1.6)
        self.text(x1 + dx, y1 + dy, label, size=10.5, color=CTRL, anchor=anchor,
                  family="Menlo, Consolas, monospace")

    def net(self, x, y, label, anchor="end", size=10.5):
        """Named-net label: connects by name to the wire of the same name."""
        self.text(x, y + 3.5, label, anchor=anchor, size=size, italic=True,
                  family="Menlo, Consolas, monospace")

    # ---------- output ----------
    def svg(self):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}">\n'
                '<defs>'
                f'<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
                f'fill="{INK}"/></marker>'
                f'<marker id="arrc" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
                f'fill="{CTRL}"/></marker>'
                '</defs>\n'
                f'<rect width="100%" height="100%" fill="white"/>\n')
        return head + "\n".join(self.items) + "\n</svg>\n"

    def save(self, path):
        with open(path, "w") as f:
            f.write(self.svg())
