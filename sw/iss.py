"""adam16 instruction-set simulator: the golden model of the ISA.

    python3 sw/iss.py prog.mem [--trace out.txt] [--max-instr N]

Runs from reset (PC = 0, R0-R7 = 0, N Z P = 0 1 0, memory = image, else 0)
until it fetches TRAP x025 (HALT), which is not executed. Every executed
instruction is one retire record, in the same format the RTL testbench
writes, so traces can be compared line by line:

    pc ir  reg_we reg_addr reg_data  mem_we mem_addr mem_data  nzp

Unused fields are zero. nzp is the flag state after the instruction.
"""

import argparse
import sys

from isa import HALT_WORD, fields, mask16, sext, to_signed


def load_mem(path):
    mem = [0] * 65536
    addr = 0
    for line in open(path):
        line = line.split("//")[0].strip()
        if not line:
            continue
        for tok in line.split():
            if tok.startswith("@"):
                addr = int(tok[1:], 16)
            else:
                mem[addr] = int(tok, 16) & 0xFFFF
                addr += 1
    return mem


def flags_of(value):
    """N Z P for a 16-bit result, as a 3-bit number."""
    value = mask16(value)
    if value == 0:
        return 0b010
    return 0b100 if value & 0x8000 else 0b001


def alu(op, fn, a, b):
    if op == 0:
        return mask16([a + b, a - b, ~a, a & b, a | b, a ^ b, a, -a][fn])
    if fn == 7:                                   # CMP: signed three-way compare
        sa, sb = to_signed(a), to_signed(b)
        return 0xFFFF if sa < sb else (0 if sa == sb else 1)
    return mask16([~(a & b), ~(a | b), a + 1, a - 1, a << 1, a >> 1,
                   (to_signed(a) >> 1), None][fn])


class Retire:
    __slots__ = ("pc", "ir", "reg_we", "reg_addr", "reg_data", "mem_we", "mem_addr",
                 "mem_data", "nzp")

    def __init__(self, pc, ir):
        self.pc, self.ir = pc, ir
        self.reg_we = self.reg_addr = self.reg_data = 0
        self.mem_we = self.mem_addr = self.mem_data = 0
        self.nzp = 0

    def line(self):
        return (f"{self.pc:04x} {self.ir:04x} {self.reg_we} {self.reg_addr} {self.reg_data:04x} "
                f"{self.mem_we} {self.mem_addr:04x} {self.mem_data:04x} {self.nzp:03b}")


class Machine:
    def __init__(self, mem):
        self.mem = list(mem)
        self.r = [0] * 8
        self.pc = 0
        self.nzp = 0b010
        self.halted = False

    def write_reg(self, rt, rd, value, set_flags):
        value = mask16(value)
        self.r[rd] = value
        rt.reg_we, rt.reg_addr, rt.reg_data = 1, rd, value
        if set_flags:
            self.nzp = flags_of(value)

    def step(self):
        """Execute one instruction; returns its Retire record, or None at HALT."""
        ir = self.mem[self.pc]
        if ir == HALT_WORD:
            self.halted = True
            return None
        f = fields(ir)
        pc1 = mask16(self.pc + 1)
        rt = Retire(self.pc, ir)
        nxt = pc1
        op = f["op"]
        a, b = self.r[f["sr1"]], self.r[f["sr2"]]
        if op in (0, 1):
            y = alu(op, f["fn"], a, b)
            if op == 1 and f["fn"] == 7:                       # CMP: flags only
                self.nzp = flags_of(y)
            else:
                self.write_reg(rt, f["dr"], y, True)
        elif op == 2:                                          # ADDI
            self.write_reg(rt, f["dr"], a + sext(f["imm6"], 6), True)
        elif op == 3:                                          # ANDI
            self.write_reg(rt, f["dr"], a & f["imm6"], True)
        elif op in (4, 5, 0xA, 0xB):                           # LD ST LDR STR
            if op in (4, 5):
                addr = mask16(pc1 + sext(f["off9"], 9))
            else:
                addr = mask16(a + sext(f["imm6"], 6))
            if op in (4, 0xA):
                self.write_reg(rt, f["dr"], self.mem[addr], False)
            else:
                data = self.r[f["dr"]]
                self.mem[addr] = data
                rt.mem_we, rt.mem_addr, rt.mem_data = 1, addr, data
        elif op == 0xC:                                        # LEA
            self.write_reg(rt, f["dr"], pc1 + sext(f["off9"], 9), False)
        elif op == 0xD:                                        # BR
            if f["dr"] & self.nzp:
                nxt = mask16(pc1 + sext(f["off9"], 9))
        elif op == 6:                                          # JMP
            nxt = a
        elif op == 7:                                          # JSR / JSRR
            target = a if f["j"] else mask16(pc1 + sext(f["off11"], 11))
            self.write_reg(rt, 7, pc1, False)
            nxt = target
        elif op == 8:                                          # RET
            nxt = self.r[7]
        elif op == 9:                                          # TRAP
            self.write_reg(rt, 7, pc1, False)
            nxt = f["tv12"]
        # opcodes 0xE, 0xF: undefined, no effect
        rt.nzp = self.nzp
        self.pc = nxt
        return rt

    def run(self, max_instr=100000):
        trace = []
        while len(trace) < max_instr:
            rt = self.step()
            if rt is None:
                return trace
            trace.append(rt)
        raise RuntimeError(f"no HALT within {max_instr} instructions (PC=0x{self.pc:04X})")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mem")
    ap.add_argument("--trace", help="write the retire trace here")
    ap.add_argument("--max-instr", type=int, default=100000)
    args = ap.parse_args()
    m = Machine(load_mem(args.mem))
    try:
        trace = m.run(args.max_instr)
    except RuntimeError as e:
        sys.exit(str(e))
    if args.trace:
        with open(args.trace, "w") as f:
            f.write("".join(rt.line() + "\n" for rt in trace))
    regs = " ".join(f"R{i}={v:04x}" for i, v in enumerate(m.r))
    print(f"{len(trace)} instructions; {regs} NZP={m.nzp:03b}")


if __name__ == "__main__":
    main()
