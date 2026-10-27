"""adam16_datapath block diagram -> docs/figures/datapath.svg

Run:  python3 docs/tools/gen_datapath.py   (or make -C docs)
Conventions: wires connect only at dots; an italic name at a mux input
connects to the net of the same name; dashed orange = control from the FSM;
solid orange = status to the FSM.
"""

import os

from svgkit import Canvas, INK, MUTED, CTRL

c = Canvas(1340, 900)

# ---------------------------------------------------------------- frame
c.rect(170, 20, 1150, 865, fill="none", stroke=MUTED, sw=1.2, rx=6, dash="6,4")
c.text(185, 42, "adam16_datapath", anchor="start", size=15, weight="bold", color=MUTED)

# ---------------------------------------------------------------- SRAM (outside)
c.rect(30, 320, 110, 240, fill="#fefce8", rx=4)
c.text(85, 345, "adam16_sram", size=13, weight="bold")
c.text(85, 362, "64K x 16", size=10, color=MUTED)
c.text(85, 376, "sync read", size=10, color=MUTED)
c.text(132, 399, "addr", anchor="end", size=10)
c.text(132, 434, "wdata", anchor="end", size=10)
c.text(132, 524, "rdata", anchor="end", size=10)
c.ctrl_in(85, 320, "mem_we", side="above", length=40)

# ---------------------------------------------------------------- MAR + mux
c.reg(230, 375, 80, 40, "MAR", "rst 0000")
mys, mout, msel = c.mux(345, 360, 30, 70, ["0", "1"], flip=True)
c.wire([mout, (310, mout[1])])
c.wire([(230, 395), (140, 395)])                       # mem_addr
c.text(176, 389, "mem_addr", anchor="start", size=9.5, color=MUTED)
c.net(380, mys[0], "PC", anchor="start")
c.ctrl_in(270, 375, "mar_we", side="above", length=20)
c.ctrl_in(msel[0], msel[1], "mar_src_sel", side="below", length=18)

# ---------------------------------------------------------------- mem_wdata
c.wire([(226, 430), (140, 430)])
c.net(229, 430, "rd2", anchor="start")
c.text(176, 424, "mem_wdata", anchor="start", size=9.5, color=MUTED)

# ---------------------------------------------------------------- mem_rdata -> IR, MDR
c.wire([(140, 520), (190, 520)], arrow=False)
c.text(176, 512, "mem_rdata", anchor="start", size=9.5, color=MUTED)
c.dot(190, 520)
c.wire([(190, 520), (230, 520)])
c.wire([(190, 520), (190, 760), (230, 760)])

c.reg(230, 500, 80, 40, "IR", "rst 0000")
c.ctrl_in(270, 500, "ir_we", side="above", length=20)
c.reg(230, 740, 80, 40, "MDR", "rst 0000")
c.ctrl_in(270, 740, "mdr_we", side="above", length=20)

# IR -> field/extend block, and IR -> control
c.wire([(310, 520), (380, 520)])
c.dot(338, 520)
c.status_out(338, 520, 338, 585, "ir[15:0]", dy=14)
c.text(338, 612, "to control", size=9.5, color=CTRL)

# ---------------------------------------------------------------- IR field / extend block
EX_X, EX_Y, EX_W, EX_H = 380, 460, 150, 285
c.rect(EX_X, EX_Y, EX_W, EX_H, rx=3)
c.text(EX_X + EX_W / 2, EX_Y + 16, "IR fields / extend", size=11, weight="bold")
fields = [  # (y, label inside block, net name or None)
    (490, "IR[8:6]   SR1/BaseR", None),
    (520, "IR[5:3]   SR2", None),
    (548, "IR[11:9]  DR/SR", None),
    (640, "SEXT(IR[5:0])", "sext6"),
    (662, "ZEXT(IR[5:0])", "zext6"),
    (684, "SEXT(IR[8:0])", "sext9"),
    (706, "SEXT(IR[10:0])", "sext11"),
    (728, "ZEXT(IR[11:0])", "zext12"),
]
for y, lab, net in fields:
    c.text(EX_X + EX_W - 6, y + 3.5, lab, anchor="end", size=9.5,
           family="Menlo, Consolas, monospace")
    if net:
        c.wire([(EX_X + EX_W, y), (EX_X + EX_W + 14, y)])
        c.net(EX_X + EX_W + 17, y, net, anchor="start", size=9.5)
# note: field slicing is pure wiring; the extenders are the only logic here

# ---------------------------------------------------------------- register file
RF_X, RF_Y, RF_W, RF_H = 640, 460, 130, 240
c.rect(RF_X, RF_Y, RF_W, RF_H, fill="#eef2ff")
c.text(RF_X + RF_W / 2, RF_Y + 20, "adam16_regfile", size=12, weight="bold")
c.text(RF_X + RF_W / 2, RF_Y + 35, "8 x 16, 3R / 1W", size=9.5, color=MUTED)
c.text(RF_X + RF_W / 2, RF_Y + 48, "async read, sync write", size=9.5, color=MUTED)
c.text(RF_X + RF_W / 2, RF_Y + RF_H - 34, "rst: R0-R7 = 0", size=9.5, color=MUTED)
for y, nm in [(490, "ra0"), (520, "ra1"), (560, "ra2"), (650, "wd")]:
    c.text(RF_X + 6, y + 3.5, nm, anchor="start", size=10)
for y, nm in [(520, "rd0"), (560, "rd1")]:
    c.text(RF_X + RF_W - 6, y + 3.5, nm, anchor="end", size=10)
c.text(RF_X + 35, RF_Y + RF_H - 8, "wa", size=10)
c.text(RF_X + RF_W - 30, RF_Y + RF_H - 8, "rd2", size=10)
c.wire([(EX_X + EX_W, 490), (RF_X, 490)])
c.wire([(EX_X + EX_W, 520), (RF_X, 520)])
# ra2 mux
rys, rout, rsel = c.mux(578, 535, 22, 50, ["0", "1"])
c.wire([(EX_X + EX_W, 548), (578, 548)])
c.text(574, rys[1] + 3.5, "3'b111", anchor="end", size=9.5, family="Menlo, Consolas, monospace")
c.wire([rout, (RF_X, rout[1])])
c.ctrl_in(rsel[0], rsel[1], "ra2_sel", side="below", length=16)
c.ctrl_in(RF_X + 35, RF_Y + RF_H, "reg_dst", side="below", length=20)
c.ctrl_in(RF_X + RF_W / 2, RF_Y, "reg_we", side="above", length=20)

# ---------------------------------------------------------------- ALU A / B muxes
ays, aout, asel = c.mux(810, 445, 30, 105, ["0", "1", "2,3"])
bys, bout, bsel = c.mux(810, 560, 30, 165, ["0", "1", "2", "3", "4", "5-7"])
# rd0 -> alu_a[0]
c.wire([(RF_X + RF_W, 520), (790, 520), (790, ays[0]), (810, ays[0])])
c.net(806, ays[1], "PC")
c.text(806, ays[2] + 3.5, "16'h0", anchor="end", size=9.5, family="Menlo, Consolas, monospace")
# rd1 -> alu_b[0]
c.wire([(RF_X + RF_W, 560), (795, 560), (795, bys[0]), (810, bys[0])])
for y, nm in zip(bys[1:], ["sext6", "zext6", "sext9", "sext6", "16'h0"]):
    c.net(806, y, nm)
# rd2 out (to mem_wdata and PC mux input 4)
c.wire([(RF_X + RF_W - 30, RF_Y + RF_H), (RF_X + RF_W - 30, RF_Y + RF_H + 30)], arrow=False)
c.net(RF_X + RF_W - 30, RF_Y + RF_H + 42, "rd2", anchor="middle")
c.ctrl_in(asel[0], 445 + 3, "alu_a_sel", side="above", length=20)
c.ctrl_in(bsel[0], bsel[1], "alu_b_sel", side="below", length=16)

# ---------------------------------------------------------------- ALU
AX = 890
ay_in, by_in = aout[1], bout[1]
top, bot = ay_in - 40, by_in + 40
mid = (ay_in + by_in) / 2
c.poly([(AX, top), (AX + 80, top + 45), (AX + 80, bot - 45), (AX, bot),
        (AX, mid + 18), (AX + 16, mid), (AX, mid - 18)])
c.text(AX + 52, mid - 4, "ALU", size=14, weight="bold")
c.text(AX + 52, mid + 12, "16 ops", size=9.5, color=MUTED)
c.text(AX + 8, ay_in + 4, "a", anchor="start", size=10)
c.text(AX + 8, by_in + 4, "b", anchor="start", size=10)
c.wire([aout, (AX, ay_in)])
c.wire([bout, (AX, by_in)])
c.ctrl_in(AX + 40, bot - 22, "alu_op[3:0]", side="below", length=34)
ALU_OUT = (AX + 80, mid)

# ---------------------------------------------------------------- write-back mux
wys, wout, wsel = c.mux(1060, mid - 20, 30, 120, ["0", "1", "2"])
c.wire([ALU_OUT, (1060, wys[0])])
c.text(988, mid - 7, "alu_y", size=10.5, italic=True)
c.dot(1010, mid)
c.net(1056, wys[2], "PC")
c.ctrl_in(wsel[0], wsel[1], "wb_sel", side="below", length=16)
# alu_y -> MAR mux input 1 (top channel) + debug
c.wire([(1010, mid), (1010, 330), (420, 330), (420, mys[1]), (375, mys[1])])
c.text(715, 324, "alu_y  (effective address -> MAR)", size=10, color=MUTED)

# MDR -> wb mux input 1 (bottom channel)
c.wire([(310, 760), (340, 760), (340, 860), (1035, 860), (1035, wys[1]), (1060, wys[1])])
c.text(690, 854, "MDR  (load data -> write-back)", size=10, color=MUTED)

# wb_data -> flags and back to regfile wd
c.wire([wout, (1180, wout[1])])
c.dot(1120, wout[1])
c.text(1145, wout[1] - 7, "wb_data", size=10.5, italic=True)
c.wire([(1120, wout[1]), (1120, 820), (615, 820), (615, 650), (RF_X, 650)])
c.text(870, 814, "wb_data  (register write-back)", size=10, color=MUTED)

# ---------------------------------------------------------------- flags
FX, FY = 1180, wout[1] - 45
c.rect(FX, FY, 115, 100, fill="#dbeafe")
c.text(FX + 57, FY + 20, "N Z P", size=13, weight="bold")
c.text(FX + 57, FY + 38, "N = wb[15]", size=9.5, family="Menlo, Consolas, monospace")
c.text(FX + 57, FY + 52, "Z = (wb == 0)", size=9.5, family="Menlo, Consolas, monospace")
c.text(FX + 57, FY + 66, "P = !N & !Z", size=9.5, family="Menlo, Consolas, monospace")
c.text(FX + 57, FY + 82, "rst N Z P = 0 1 0", size=9, color=MUTED)
c.poly([(FX + 50, FY + 100), (FX + 57, FY + 92), (FX + 64, FY + 100)], fill="none")
c.ctrl_in(FX + 57, FY, "flag_we", side="above", length=20)
c.status_out(FX + 95, FY + 100, FX + 95, FY + 135, "N, Z, P", dy=14)
c.text(FX + 95, FY + 162, "to control", size=9.5, color=CTRL)

# ---------------------------------------------------------------- PC section
pys, pout, psel = c.mux(580, 70, 30, 180,
                        ["0", "1", "2", "3", "4", "5"])
for y, lab in zip(pys[:3], ["PC + 1", "PC + sext9", "PC + sext11"]):
    c.rect(440, y - 11, 100, 22, rx=3)
    c.text(490, y + 4, lab, size=10, family="Menlo, Consolas, monospace")
    c.wire([(540, y), (580, y)])
for y, nm in zip(pys[3:], ["rd0", "rd2", "zext12"]):
    c.net(576, y, nm)
c.reg(650, pout[1] - 20, 80, 40, "PC", "rst 0000")
c.wire([pout, (650, pout[1])])
c.ctrl_in(690, pout[1] - 20, "pc_we", side="above", length=20)
c.ctrl_in(psel[0], psel[1], "pc_src_sel", side="below", length=18)
# PC feedback to the adders
c.wire([(730, pout[1]), (770, pout[1])], arrow=False)
c.dot(770, pout[1])
c.wire([(770, pout[1]), (770, 52), (415, 52), (415, pys[2])], arrow=False)
for y in pys[:3]:
    c.dot(415, y)
    c.wire([(415, y), (440, y)])
c.wire([(770, pout[1]), (820, pout[1])], arrow=False)
c.net(824, pout[1], "PC", anchor="start")
c.text(824, pout[1] + 18, "-> MAR mux 0, ALU a 1, wb mux 2", anchor="start", size=9.5, color=MUTED)

# ---------------------------------------------------------------- legend
LX, LY = 1010, 70
c.rect(LX, LY, 290, 130, fill="white", stroke=MUTED, sw=1, rx=4)
c.text(LX + 12, LY + 20, "Legend", anchor="start", size=11, weight="bold")
c.rect(LX + 12, LY + 30, 26, 16, fill="#dbeafe")
c.text(LX + 46, LY + 42, "register (posedge clk, sync rst)", anchor="start", size=10)
c.wire([(LX + 12, LY + 62), (LX + 38, LY + 62)], color=CTRL, sw=1.3, dash="4,3")
c.text(LX + 46, LY + 66, "control from adam16_control_fsm", anchor="start", size=10)
c.wire([(LX + 12, LY + 84), (LX + 38, LY + 84)], color=CTRL, sw=1.6)
c.text(LX + 46, LY + 88, "status to adam16_control_fsm", anchor="start", size=10)
c.dot(LX + 25, LY + 106)
c.text(LX + 46, LY + 110, "wires connect only at dots;", anchor="start", size=10)
c.text(LX + 46, LY + 123, "italic names connect by name", anchor="start", size=10, italic=True)

c.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", "datapath.svg"))
