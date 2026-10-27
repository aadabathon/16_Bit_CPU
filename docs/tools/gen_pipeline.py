"""adam16_pipe_core block diagram -> docs/figures/pipeline.svg

Run:  python3 docs/tools/gen_pipeline.py   (or make -C docs)
Conventions as in datapath.svg: wires connect only at dots; an italic name
at a mux input connects to the net of the same name; dashed orange =
control from the decoder or the branch unit.
"""

import os

from svgkit import Canvas, CTRL, INK, MUTED, REG_FILL

W, H = 1480, 760
c = Canvas(W, H)

TOP, BOT = 92, 600                  # extent of the pipeline registers
BARS = {"IF/ID": 262, "ID/EX": 560, "EX/MEM": 1060, "MEM/WB": 1262}
BAR_W = 22
STAGES = [("IF", 30, 262), ("ID", 284, 560), ("EX", 582, 1060), ("MEM", 1082, 1262),
          ("WB", 1284, 1460)]

c.text(30, 30, "adam16_pipe_core", anchor="start", size=16, weight="bold", color=MUTED)
c.text(30, 48, "five stages, no stalls; a taken branch or a jump costs one bubble",
       anchor="start", size=11, color=MUTED)

for name, x0, x1 in STAGES:
    c.text((x0 + x1) / 2, 78, name, size=15, weight="bold")

for name, x in BARS.items():
    c.rect(x, TOP, BAR_W, BOT - TOP, fill=REG_FILL)
    c.poly([(x + 4, BOT), (x + BAR_W / 2, BOT - 8), (x + BAR_W - 4, BOT)], fill="none")
    c.text(x + BAR_W / 2, TOP - 6, name, size=10, color=MUTED)

# ---------------------------------------------------------------- memory
MY = 650
c.rect(110, MY, 1060, 80, fill="#fefce8", rx=4)
c.text(640, MY + 34, "adam16_dpram  64K x 16, two registered read ports",
       size=13, weight="bold")
c.text(640, MY + 52, "port A: fetch    port B: data (read, write)", size=10.5, color=MUTED)
# the read registers line up with IF/ID and EX/MEM: they are those registers
for x, lab in ((BARS["IF/ID"], "A rdata"), (BARS["EX/MEM"], "B rdata")):
    c.rect(x - 14, MY + 6, BAR_W + 28, 24, fill=REG_FILL)
    c.text(x + BAR_W / 2, MY + 22, lab, size=9.5)

# ---------------------------------------------------------------- IF
c.reg(48, 300, 74, 40, "f_pc", "rst 0000")
ys, out, sel = c.mux(170, 286, 30, 80, ["0", "1"])
c.wire([(122, 320), (170, ys[0])])
c.net(166, ys[1], "target")
c.ctrl_in(sel[0], sel[1], "redirect", side="below", length=24)
c.wire([out, (226, out[1]), (226, MY)])                         # imem_addr
c.text(232, 520, "imem_addr", anchor="start", size=9.5, color=MUTED)
c.dot(226, out[1])
c.rect(66, 200, 40, 26)
c.text(86, 218, "+1", size=12)
c.wire([(226, out[1]), (226, 213), (106, 213)])
c.wire([(66, 213), (40, 213), (40, 320), (48, 320)])
c.dot(226, 213)
c.wire([(226, 213), (226, 140), (BARS["IF/ID"], 140)])           # -> d_pc
c.text(244, 134, "d_pc", anchor="end", size=9.5, color=MUTED)

# ---------------------------------------------------------------- ID
ix = BARS["IF/ID"] + BAR_W
c.wire([(BARS["IF/ID"] + BAR_W / 2, MY + 6), (BARS["IF/ID"] + BAR_W / 2, 612),
        (300, 612), (300, 200), (318, 200)])
c.text(306, 590, "instruction", anchor="start", size=9.5, color=MUTED)
c.rect(318, 150, 150, 90)
c.text(393, 180, "adam16_pipe_decode", size=11.5, weight="bold")
c.text(393, 198, "ra0 ra1 rd, controls,", size=9.5, color=MUTED)
c.text(393, 211, "imm (16 b)", size=9.5, color=MUTED)
c.wire([(468, 170), (BARS["ID/EX"], 170)])
c.text(512, 164, "ctrl, imm, rd", size=9.5, color=MUTED)
c.wire([(ix, 140), (BARS["ID/EX"], 140)])
c.text(512, 134, "d_pc", size=9.5, color=MUTED)

c.rect(330, 290, 130, 220, fill=REG_FILL)
c.text(395, 315, "adam16_regfile", size=11.5, weight="bold")
c.text(395, 331, "8 x 16, 2R / 1W", size=9.5, color=MUTED)
c.text(395, 344, "write-first", size=9.5, color=MUTED)
c.wire([(360, 240), (360, 290)])
c.text(366, 268, "ra0, ra1", anchor="start", size=9.5, color=MUTED)
for y, lab, net in ((380, "rd0", "e_rs0"), (484, "rd1", "e_rs1")):
    c.text(454, y + 3.5, lab, anchor="end", size=9.5)
    c.wire([(460, y), (BARS["ID/EX"], y)])
    c.text(512, y - 6, net, size=9.5, color=MUTED)
c.text(402, 532, "wa, wd, we", anchor="start", size=9.5)
c.wire([(395, 566), (395, 512)])
c.net(395, 578, "w_rd, w_value", anchor="middle")

# ---------------------------------------------------------------- EX
ex = BARS["ID/EX"] + BAR_W
fa_ys, fa_out, fa_sel = c.mux(640, 366, 32, 84, ["", "", ""])     # ys 380 408 436
fb_ys, fb_out, fb_sel = c.mux(640, 470, 32, 84, ["", "", ""])     # ys 484 512 540
for ys_ in (fa_ys, fb_ys):
    c.wire([(ex, ys_[0]), (640, ys_[0])])
    c.net(636, ys_[1], "m_value")
    c.net(636, ys_[2], "w_value")
c.text(656, 360, "forward", size=9.5, color=CTRL)
c.ctrl_in(fa_sel[0], fa_sel[1], "", side="below", length=10)
c.ctrl_in(fb_sel[0], fb_sel[1], "", side="below", length=10)
c.text(598, 580, "forward select: MEM, else WB, if its rd == ra", anchor="start",
       size=9.5, color=CTRL)

# operand selects
as_ys, as_out, as_sel = c.mux(740, 270, 30, 90, ["", "", ""])     # ys 285 315 345
c.wire([fa_out, (700, fa_out[1]), (700, as_ys[0]), (740, as_ys[0])])
c.text(686, fa_out[1] - 6, "e_a", size=9.5, color=MUTED)
c.net(736, as_ys[1], "PC+1")
c.net(736, as_ys[2], "0")
c.ctrl_in(as_sel[0], as_sel[1], "a_sel", side="below", length=14)

bs_ys, bs_out, bs_sel = c.mux(740, 440, 30, 64, ["", ""])         # ys 456 488
c.wire([fb_out, (710, fb_out[1]), (710, bs_ys[0]), (740, bs_ys[0])])
c.dot(710, fb_out[1])
c.text(690, fb_out[1] - 6, "e_b", size=9.5, color=MUTED)
c.net(736, bs_ys[1], "imm")
c.ctrl_in(bs_sel[0], bs_sel[1], "b_imm", side="below", length=14)

# ALU
ax, ay = 820, 395
c.poly([(ax, 280), (ax + 70, 330), (ax + 70, 460), (ax, 510), (ax, 415), (ax + 14, ay),
        (ax, 375)])
c.text(ax + 40, ay + 5, "ALU", size=13, weight="bold")
c.wire([as_out, (ax, as_out[1])])
c.wire([bs_out, (ax, bs_out[1])])
c.ctrl_in(ax + 35, 495, "alu_op", side="below", length=22)
c.text(ax + 35, 546, "alu_y is the result,", size=9.5, color=MUTED)
c.text(ax + 35, 559, "the data address and", size=9.5, color=MUTED)
c.text(ax + 35, 572, "the branch / jump target", size=9.5, color=MUTED)

# result for MEM: alu_y, or PC+1 (the link) for JSR / JSRR / TRAP
rs_ys, rs_out, rs_sel = c.mux(960, 380, 28, 60, ["", ""])         # ys 395 425
c.wire([(ax + 70, ay), (960, ay)])
c.text(898, ay - 6, "alu_y", anchor="start", size=9.5, color=MUTED)
c.net(956, rs_ys[1], "PC+1")
c.ctrl_in(rs_sel[0], rs_sel[1], "wb_sel", side="below", length=14)
c.wire([rs_out, (BARS["EX/MEM"], rs_out[1])])
c.text(1040, rs_out[1] - 6, "m_result", anchor="end", size=9.5, color=MUTED)

# data port and target
c.dot(912, ay)
c.wire([(912, ay), (912, MY)])
c.text(918, 612, "dmem_addr", anchor="start", size=9.5, color=MUTED)
c.wire([(710, fb_out[1]), (710, 600), (880, 600), (880, MY)])
c.text(874, 594, "dmem_wdata", anchor="end", size=9.5, color=MUTED)
c.ctrl_in(1010, MY, "dmem_we", side="above", length=26, anchor="middle")
c.wire([(912, ay), (912, 262)], arrow=False)
c.net(916, 256, "target", anchor="start")

# flags and branch unit
c.reg(790, 150, 70, 40, "N Z P", "rst 010")
c.text(825, 214, "<= flags of alu_y", size=9.5, color=MUTED)
c.text(825, 228, "when flag_we", size=9.5, color=MUTED)
c.rect(900, 130, 130, 56)
c.text(965, 152, "branch unit", size=11.5, weight="bold")
c.text(965, 170, "jump | (br_mask & NZP)", size=9.5, color=MUTED)
c.wire([(860, 170), (900, 170)])
c.ctrl_in(965, 186, "br_mask, jump", side="below", length=20)
c.wire([(965, 130), (965, 104)], color=CTRL, sw=1.3, dash="4,3")
c.text(958, 112, "redirect: IF fetches target now; the word in ID is squashed",
       anchor="end", size=10, color=CTRL)

# ---------------------------------------------------------------- MEM
mx = BARS["EX/MEM"] + BAR_W
mv_ys, mv_out, mv_sel = c.mux(1140, 395, 30, 60, ["", ""])        # ys 410 440
c.wire([(mx, rs_out[1]), (1140, mv_ys[0])])
c.wire([(BARS["EX/MEM"] + BAR_W / 2, MY + 6), (BARS["EX/MEM"] + BAR_W / 2, 620),
        (1110, 620), (1110, mv_ys[1]), (1140, mv_ys[1])])
c.text(1116, 560, "dmem_rdata", anchor="start", size=9.5, color=MUTED)
c.ctrl_in(mv_sel[0], mv_sel[1], "load", side="below", length=14)
c.wire([mv_out, (BARS["MEM/WB"], mv_out[1])])
c.dot(1210, mv_out[1])
c.wire([(1210, mv_out[1]), (1210, 262)], arrow=False)
c.net(1214, 256, "m_value", anchor="start")
c.text(1100, 236, "both forwarded to EX:", anchor="start", size=9.5, color=MUTED)

# ---------------------------------------------------------------- WB
wx = BARS["MEM/WB"] + BAR_W
c.wire([(wx, mv_out[1]), (1400, mv_out[1]), (1400, 470)])
c.dot(1340, mv_out[1])
c.wire([(1340, mv_out[1]), (1340, 262)], arrow=False)
c.net(1344, 256, "w_value", anchor="start")
c.rect(1352, 470, 96, 54)
c.text(1400, 492, "R[w_rd] <=", size=10.5)
c.text(1400, 508, "w_value", size=10.5)
c.text(1400, 546, "(the regfile's", size=9.5, color=MUTED)
c.text(1400, 560, "write port)", size=9.5, color=MUTED)

c.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", "pipeline.svg"))
