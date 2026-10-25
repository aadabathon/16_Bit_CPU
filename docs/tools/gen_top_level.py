"""System / top-level block diagram -> docs/figures/top_level.svg

Run:  python3 docs/tools/gen_top_level.py  (or make -C docs)
"""

import os

from svgkit import Canvas, INK, MUTED, CTRL, REG_FILL

MONO = "Menlo, Consolas, monospace"
c = Canvas(1240, 640)

# ---------------------------------------------------------------- basys3_top frame
c.rect(60, 20, 1080, 600, fill="none", stroke=MUTED, sw=1.2, rx=6, dash="6,4")
c.text(75, 42, "basys3_top  (FPGA only; simulation instantiates cpu16_core + SramSBC directly)",
       anchor="start", size=13, weight="bold", color=MUTED)

# ---------------------------------------------------------------- board inputs
for y, nm, pin in [(95, "clk", "W5, 100 MHz"), (175, "btn_rst", "btnC"),
                   (250, "btn_step", "btnU"), (560, "sw[15:0]", "")]:
    c.text(8, y - 6, nm, anchor="start", size=11, family=MONO)
    if pin:
        c.text(8, y + 14, pin, anchor="start", size=9, color=MUTED)
c.wire([(8, 95), (105, 95)], arrow=False)
c.dot(105, 95)
c.wire([(105, 95), (105, 165), (120, 165)])
c.wire([(105, 165), (105, 240), (120, 240)])
c.wire([(8, 175), (120, 175)])
c.wire([(8, 250), (120, 250)])

# ---------------------------------------------------------------- debouncers
for y, nm in [(150, "db_rst"), (225, "db_step")]:
    c.rect(120, y, 120, 50, rx=3)
    c.text(180, y + 20, "debounce", size=11, weight="bold")
    c.text(180, y + 36, nm + "  (~2 ms)", size=9.5, color=MUTED)
c.text(124, 168, "clk", anchor="start", size=8.5, color=MUTED)
c.text(124, 243, "clk", anchor="start", size=8.5, color=MUTED)

# rst_clean -> core rst ; rst_pulse, step_pulse -> OR
c.wire([(240, 160), (395, 160)])
c.text(300, 154, "rst_clean", size=10, italic=True)
c.wire([(240, 188), (275, 188), (275, 206), (300, 206)])
c.text(243, 183, "rst_pulse", anchor="start", size=9, italic=True)
c.wire([(240, 255), (275, 255), (275, 226), (300, 226)])
c.text(243, 268, "step_pulse", anchor="start", size=9, italic=True)
# OR gate
c.raw('<path d="M300,198 Q315,216 300,234 Q330,234 345,216 Q330,198 300,198 Z" '
      f'fill="white" stroke="{INK}" stroke-width="1.4"/>')
c.wire([(345, 216), (395, 216)])
c.text(370, 209, "core_clk", size=10, italic=True)
c.dot(360, 216)
c.wire([(360, 216), (360, 600), (905, 600), (905, 330), (930, 330)])
c.text(300, 300, "derived clock:", size=9.5, color=CTRL)
c.text(300, 313, "one edge per press", size=9.5, color=CTRL)
c.text(300, 326, "(see known issues)", size=9.5, color=CTRL)

# ---------------------------------------------------------------- cpu16_core
c.rect(395, 70, 470, 420, fill="#f8fafc", rx=6)
c.text(410, 92, "cpu16_core", anchor="start", size=14, weight="bold")
c.text(399, 164, "rst", anchor="start", size=9.5)
c.text(399, 220, "clk", anchor="start", size=9.5)

c.rect(425, 120, 150, 330, fill="white", rx=4)
c.text(500, 145, "cpu16_control_fsm", size=11.5, weight="bold")
c.text(500, 162, "14-state FSM", size=9.5, color=MUTED)
c.rect(445, 180, 110, 34, fill=REG_FILL)
c.text(500, 201, "state[4:0]", size=10.5, family=MONO)
c.text(500, 240, "next-state logic", size=9.5, color=MUTED)
c.text(500, 254, "output logic", size=9.5, color=MUTED)
c.text(500, 268, "f(state, IR, N, Z, P)", size=9.5, color=MUTED, family=MONO)

c.rect(705, 120, 140, 330, fill="white", rx=4)
c.text(775, 145, "cpu16_datapath", size=11.5, weight="bold")
for i, nm in enumerate(["PC  IR  MAR  MDR", "regfile 8x16", "ALU", "N Z P flags"]):
    c.text(775, 175 + i * 18, nm, size=9.5, color=MUTED)

# control bus FSM -> datapath
ctrl = ["pc_we", "ir_we", "mar_we", "mdr_we", "reg_we", "flag_we", "reg_dst[2:0]",
        "ra2_sel", "wb_sel[1:0]", "alu_op[3:0]", "alu_a_sel[1:0]", "alu_b_sel[2:0]",
        "pc_src_sel[2:0]", "mar_src_sel[1:0]"]
c.wire([(575, 205), (705, 205)], color=CTRL, sw=3)
for i, nm in enumerate(ctrl):
    c.text(640, 222 + i * 12.5, nm, size=9, color=CTRL, family=MONO)
c.text(640, 199, "control (14)", size=9.5, weight="bold", color=CTRL)
# status datapath -> FSM
c.wire([(705, 420), (575, 420)], color=CTRL, sw=3)
c.text(640, 414, "ir[15:0], N, Z, P", size=9.5, weight="bold", color=CTRL)

# ---------------------------------------------------------------- memory bus
c.rect(930, 120, 170, 230, fill="#fefce8", rx=4)
c.text(1015, 145, "SramSBC", size=13, weight="bold")
c.text(1015, 162, "64K x 16, sync read", size=9.5, color=MUTED)
c.text(1015, 176, "INIT_FILE = .mem image", size=9.5, color=MUTED)
for y, nm in [(205, "addr"), (240, "wdata"), (275, "we"), (305, "rdata"), (330, "clk")]:
    c.text(936, y + 4, nm, anchor="start", size=10)
c.wire([(845, 205), (930, 205)])
c.text(887, 199, "mem_addr", size=9.5, italic=True)
c.wire([(845, 240), (930, 240)])
c.text(887, 234, "mem_wdata", size=9.5, italic=True)
c.wire([(500, 120), (500, 100), (885, 100), (885, 275), (930, 275)], color=CTRL, sw=1.6)
c.text(700, 94, "mem_we (from FSM)", size=9.5, color=CTRL)
c.wire([(930, 305), (845, 305)])
c.text(887, 299, "mem_rdata", size=9.5, italic=True)

# ---------------------------------------------------------------- debug / LEDs
c.text(775, 505, "dbg_pc, dbg_ir, dbg_alu_y, dbg_n/z/p", size=9.5, color=MUTED, italic=True)
ys, out, sel = c.mux(990, 405, 96, 140,
                     ["00  PC", "01  IR", "10  alu_y", "11  {0,N,Z,P}"])
# debug bus from the core, tapped into each mux input
c.wire([(775, 450), (775, 475), (960, 475)], arrow=False)
c.dot(960, 475)
c.wire([(960, ys[0]), (960, ys[-1])], arrow=False)
for y in ys:
    c.wire([(960, y), (990, y)])
c.text(870, 469, "dbg_* bus", size=9.5, italic=True)
c.wire([(8, 560), (sel[0], 560), (sel[0], sel[1] + 2)])
c.text(sel[0] + 6, 576, "sw[1:0]", anchor="start", size=9.5, family=MONO)
c.wire([out, (1230, out[1])])
c.text(1225, out[1] - 8, "led[15:0]", anchor="end", size=11, family=MONO)

c.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", "top_level.svg"))
