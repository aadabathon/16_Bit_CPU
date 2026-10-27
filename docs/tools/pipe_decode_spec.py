"""adam16_pipe_decode specification.

The single source of truth for the pipelined core's decoder. From it:

    python3 pipe_decode_spec.py                  write the decode table into docs/07_pipeline.md
    python3 pipe_decode_spec.py --check          exit 1 if that table is out of date
    python3 pipe_decode_spec.py --vectors FILE   expected outputs for all 65536 words,
                                                 replayed by tb/tb_pipe_decode_spec.sv

When you change rtl/adam16_pipe_decode.sv, change this file to match, then
run `make -C docs` and `make -C docs check`.
"""

import argparse
import os
import sys

import mdblocks
from fsm_spec import F1, OP

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.normpath(os.path.join(HERE, "..", "07_pipeline.md"))

# Outputs in packing order (MSB first) for the vectors.
OUTPUTS = [
    ("ra0", 3), ("ra1", 3), ("rd", 3), ("reg_we", 1), ("flag_we", 1), ("mem_we", 1),
    ("wb_sel", 2), ("alu_op", 4), ("a_sel", 2), ("b_imm", 1), ("imm", 16),
    ("br_mask", 3), ("jump", 1),
]
WIDTH = dict(OUTPUTS)

ALU_ADD, ALU_AND, ALU_MOV = 0b0000, 0b0011, 0b0110
WB = {0: "ALU", 1: "PC+1", 2: "load"}
A = {0: "R[ra0]", 1: "PC+1", 2: "0"}


def sext(v, bits):
    v &= (1 << bits) - 1
    return (v - (1 << bits) if v >> (bits - 1) else v) & 0xFFFF


def decode(ir):
    op = ir >> 12
    dr, sr1, sr2, fn = (ir >> 9) & 7, (ir >> 6) & 7, (ir >> 3) & 7, ir & 7
    o = dict(ra0=sr1, ra1=sr2, rd=dr, reg_we=0, flag_we=0, mem_we=0, wb_sel=0,
             alu_op=ALU_ADD, a_sel=0, b_imm=0, imm=0, br_mask=0, jump=0)
    if op in (OP["ALU0"], OP["ALU1"]):
        o.update(alu_op=(op << 3) | fn, flag_we=1,
                 reg_we=0 if (op == OP["ALU1"] and fn == F1["CMP"]) else 1)
    elif op == OP["ADDI"]:
        o.update(imm=sext(ir, 6), b_imm=1, reg_we=1, flag_we=1)
    elif op == OP["ANDI"]:
        o.update(imm=ir & 0x3F, b_imm=1, reg_we=1, flag_we=1, alu_op=ALU_AND)
    elif op in (OP["LD"], OP["LEA"]):
        o.update(imm=sext(ir, 9), b_imm=1, a_sel=1, reg_we=1, wb_sel=2 if op == OP["LD"] else 0)
    elif op == OP["ST"]:
        o.update(imm=sext(ir, 9), b_imm=1, a_sel=1, mem_we=1, ra1=dr)
    elif op == OP["LDR"]:
        o.update(imm=sext(ir, 6), b_imm=1, reg_we=1, wb_sel=2)
    elif op == OP["STR"]:
        o.update(imm=sext(ir, 6), b_imm=1, mem_we=1, ra1=dr)
    elif op == OP["BR"]:
        o.update(imm=sext(ir, 9), b_imm=1, a_sel=1, br_mask=dr)
    elif op == OP["JMP"]:
        o.update(alu_op=ALU_MOV, jump=1)
    elif op == OP["RET"]:
        o.update(alu_op=ALU_MOV, jump=1, ra0=7)
    elif op == OP["JSR"]:
        o.update(jump=1, reg_we=1, rd=7, wb_sel=1)
        if ir & 0x800:
            o.update(alu_op=ALU_MOV)
        else:
            o.update(imm=sext(ir, 11), b_imm=1, a_sel=1)
    elif op == OP["TRAP"]:
        o.update(imm=ir & 0xFFF, b_imm=1, a_sel=2, jump=1, reg_we=1, rd=7, wb_sel=1)
    return o


def pack(o):
    v = 0
    for name, w in OUTPUTS:
        assert 0 <= o[name] < (1 << w), (name, o[name])
        v = (v << w) | o[name]
    return v


# --------------------------------------------------------------------------
# The table in docs/07_pipeline.md: one row per instruction form
# --------------------------------------------------------------------------
ROWS = [
    # (instruction, example word, registers read, what EX computes)
    ("ADD SUB AND OR XOR NAND NOR", 0x0000 | (1 << 9) | (2 << 6) | (3 << 3), "SR1, SR2", "R[SR1] op R[SR2]"),
    ("NOT MOV NEG INC DEC LSL1 LSR1 ASR1", 0x1002 | (1 << 9) | (2 << 6), "SR1", "op R[SR1]"),
    ("CMP", 0x1007 | (2 << 6) | (3 << 3), "SR1, SR2", "-1 / 0 / +1: flags only"),
    ("ADDI", 0x2000 | (1 << 9) | (2 << 6), "SR1", "R[SR1] + imm"),
    ("ANDI", 0x3000 | (1 << 9) | (2 << 6), "SR1", "R[SR1] & imm"),
    ("LD", 0x4000 | (1 << 9), "—", "address"),
    ("ST", 0x5000 | (1 << 9), "SR (data)", "address"),
    ("LDR", 0xA000 | (1 << 9) | (2 << 6), "Base", "address"),
    ("STR", 0xB000 | (1 << 9) | (2 << 6), "Base, SR (data)", "address"),
    ("LEA", 0xC000 | (1 << 9), "—", "result"),
    ("BR", 0xD000 | (5 << 9), "—", "target, taken if IR[11:9] & NZP"),
    ("JMP", 0x6000 | (2 << 6), "Base", "target"),
    ("RET", 0x8000, "R7", "target"),
    ("JSR", 0x7000, "—", "target; R7 <- PC+1"),
    ("JSRR", 0x7800 | (2 << 6), "Base", "target (old R7); R7 <- PC+1"),
    ("TRAP", 0x9000, "—", "target; R7 <- PC+1"),
    ("undefined 0xE, 0xF", 0xE000, "—", "nothing"),
]

IMM = {OP["ADDI"]: "SEXT(imm6)", OP["LDR"]: "SEXT(off6)", OP["STR"]: "SEXT(off6)",
       OP["ANDI"]: "ZEXT(imm6)", OP["LD"]: "SEXT(off9)", OP["ST"]: "SEXT(off9)",
       OP["LEA"]: "SEXT(off9)", OP["BR"]: "SEXT(off9)", OP["JSR"]: "SEXT(off11)",
       OP["TRAP"]: "ZEXT(tv12)"}
ALU_NAME = {ALU_ADD: "ADD", ALU_AND: "AND", ALU_MOV: "MOV"}


def decode_table():
    """One row per instruction form. Every 0/1 and select value is decode()'s."""
    rows = ["| Instruction | Reads | rd | reg_we | flag_we | mem_we | wb_sel | alu_op | a | b "
            "| br_mask | jump | ALU output is |", "|" + "---|" * 13]
    for name, ir, reads, what in ROWS:
        o = decode(ir)
        op = ir >> 12
        if not o["reg_we"]:
            rd = "·"
        else:
            rd = "R7" if op in (OP["JSR"], OP["TRAP"]) else "DR"
        alu = "{IR[12], funct}" if op in (OP["ALU0"], OP["ALU1"]) else ALU_NAME[o["alu_op"]]
        row = [name, reads, rd, o["reg_we"], o["flag_we"], o["mem_we"],
               WB[o["wb_sel"]] if o["reg_we"] else "·", alu, A[o["a_sel"]],
               IMM[op] if o["b_imm"] else "R[ra1]",
               "IR[11:9]" if op == OP["BR"] else 0, o["jump"], what]
        rows.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(rows)


def write_vectors(path):
    with open(path, "w") as f:
        for ir in range(1 << 16):
            f.write(f"{pack(decode(ir)):011x}\n")
    return 1 << 16


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--vectors")
    args = ap.parse_args()
    if args.vectors:
        n = write_vectors(args.vectors)
        print(f"wrote {n} decode vectors to {args.vectors}")
        return
    ok = mdblocks.update(PAGE, {"pipe-decode": decode_table()}, args.check)
    if args.check and not ok:
        print("generated blocks out of date in: 07_pipeline\n  run: make -C docs")
        sys.exit(1)
    print("07_pipeline: decode table " + ("up to date" if args.check else "written"))


if __name__ == "__main__":
    main()
