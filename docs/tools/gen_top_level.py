"""System / top-level block diagram -> docs/figures/top_level.svg

Run:  python3 docs/tools/gen_top_level.py  (or make -C docs)
"""

import os

from svgkit import Canvas, CTRL, MUTED, REG_FILL

MONO = "Menlo, Consolas, monospace"
c = Canvas(1240, 600)

# ---------------------------------------------------------------- basys3_top frame
c.rect(60, 20, 1080, 560, fill="none", stroke=MUTED, sw=1.2, rx=6, dash="6,4")
c.text(75, 42, "basys3_top #(PIPELINED, DEBOUNCE_CYCLES, MEM_INIT)", anchor="start",
       size=13, weight="bold", color=MUTED)
c.text(75, 58, "simulation and ASIC flows use a core and its memory directly, without this wrapper",
       anchor="start", size=10, color=MUTED)

# ---------------------------------------------------------------- board inputs
for y, nm, pin in [(110, "btn_rst", "btnC"), (190, "btn_step", "btnU"),
                   (520, "sw[15:0]", ""), (555, "clk", "W5, 100 MHz")]:
    c.text(8, y - 6, nm, anchor="start", size=11, family=MONO)
    if pin:
        c.text(8, y + 14, pin, anchor="start", size=9, color=MUTED)
c.wire([(8, 110), (120, 110)])
c.wire([(8, 190), (120, 190)])

# the one clock: debouncers, core, memory
c.wire([(8, 555), (100, 555), (100, 130), (120, 130)])
c.dot(100, 210)
c.wire([(100, 210), (120, 210)])
c.dot(100, 555)
c.wire([(100, 555), (560, 555), (560, 470)])
c.dot(560, 555)
c.wire([(560, 555), (950, 555), (950, 420)])
c.text(330, 549, "clk: everything runs on the board clock", size=10, color=MUTED)

# ---------------------------------------------------------------- debouncers
for y, nm in [(95, "db_rst"), (175, "db_step")]:
    c.rect(120, y, 130, 50, rx=3)
    c.text(185, y + 20, "debounce", size=11, weight="bold")
    c.text(185, y + 36, nm + "  (2 ms)", size=9.5, color=MUTED)

c.wire([(250, 110), (420, 110), (420, 160), (440, 160)])
c.text(330, 104, "rst (debounced level)", size=10, italic=True)
c.wire([(250, 200), (330, 200), (330, 230), (440, 230)], color=CTRL, sw=1.6)
c.text(258, 222, "step", anchor="start", size=10, italic=True, color=CTRL)
c.text(258, 250, "1-cycle pulse", anchor="start", size=9.5, color=CTRL)
c.text(258, 263, "per press", anchor="start", size=9.5, color=CTRL)
c.dot(330, 230, color=CTRL)
c.wire([(330, 230), (330, 300), (390, 300), (390, 500), (900, 500), (900, 400), (930, 400)],
       color=CTRL, sw=1.6)
c.text(650, 494, "en = step", size=10, color=CTRL)

# ---------------------------------------------------------------- core
c.rect(440, 80, 360, 390, fill="#f8fafc", rx=6)
c.text(455, 102, "u_cpu", anchor="start", size=14, weight="bold")
c.text(444, 164, "rst", anchor="start", size=9.5)
c.text(444, 234, "ce", anchor="start", size=9.5, color=CTRL)
c.text(556, 462, "clk", anchor="end", size=9.5)

c.rect(480, 120, 300, 130, fill="white", rx=4)
c.text(630, 142, "PIPELINED = 1:  adam16_pipe_core", size=11.5, weight="bold")
for i, s in enumerate(["IF  ID  EX  MEM  WB, forwarding, no stalls",
                       "adam16_pipe_decode, regfile (write-first), ALU",
                       "about 1.2 cycles per instruction"]):
    c.text(630, 166 + i * 17, s, size=9.5, color=MUTED)

c.rect(480, 270, 300, 130, fill="white", rx=4)
c.text(630, 292, "PIPELINED = 0:  adam16_core", size=11.5, weight="bold")
for i, s in enumerate(["adam16_control_fsm (14 states)",
                       "adam16_datapath: PC IR MAR MDR, regfile, ALU",
                       "5 to 8 cycles per instruction"]):
    c.text(630, 316 + i * 17, s, size=9.5, color=MUTED)
c.text(630, 428, "same ISA, same results, same debug outputs", size=10, color=MUTED)

# ---------------------------------------------------------------- memory
c.rect(930, 120, 180, 300, fill="#fefce8", rx=4)
c.text(1020, 142, "u_mem", size=14, weight="bold")
c.text(1020, 166, "adam16_dpram (pipe)", size=10.5)
c.text(1020, 181, "port A fetch, port B data", size=9.5, color=MUTED)
c.text(1020, 205, "adam16_sram (multi)", size=10.5)
c.text(1020, 220, "one port", size=9.5, color=MUTED)
c.text(1020, 244, "64K x 16, registered read", size=9.5, color=MUTED)
c.text(1020, 258, "INIT_FILE = MEM_INIT", size=9.5, color=MUTED)
c.text(936, 404, "en", anchor="start", size=9.5, color=CTRL)
c.text(946, 416, "clk", anchor="end", size=9.5)

for y, s in [(190, "imem_addr / imem_rdata"), (260, "dmem_* / mem_*")]:
    c.wire([(800, y), (930, y)])
    c.wire([(930, y + 16), (800, y + 16)])
    c.text(865, y - 6, s, size=9.5, italic=True)

# ---------------------------------------------------------------- debug / LEDs
ys, out, sel = c.mux(990, 430, 112, 104, ["00 PC", "01 IR", "10 result", "11 {N,Z,P}"])
c.wire([(800, 380), (850, 380), (850, 470), (960, 470)], arrow=False)
c.text(806, 374, "dbg_*", anchor="start", size=9.5, italic=True)
c.dot(960, 470)
c.wire([(960, ys[0]), (960, ys[-1])], arrow=False)
for y in ys:
    c.wire([(960, y), (990, y)])
c.wire([(8, 520), (300, 520), (300, 538), (sel[0], 538), (sel[0], sel[1] + 2)])
c.text(sel[0] + 6, 552, "sw[1:0]", anchor="start", size=9.5, family=MONO)
c.wire([out, (1230, out[1])])
c.text(1225, out[1] - 8, "led[15:0]", anchor="end", size=11, family=MONO)

c.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", "top_level.svg"))
