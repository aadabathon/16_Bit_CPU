"""Random adam16 test programs for differential testing (ISS vs RTL).

    python3 sw/randprog.py --seed 7 [--length 120] [-o prog.asm]

Every program halts: control flow only goes forward, except counted loops
whose counter nothing else in the body writes. Stores only reach the data
block, so no program modifies its own code. Layout:

    0x0000        BR main
    0x0001-0x003F data block (random words); R6 = 0x0020 points at its middle
    0x0040        TRAP x040 handler: random ALU / memory ops, RET
    0x0050        subroutine:       random ALU / memory ops, RET
    0x0060        main: random instructions, HALT

Operands are biased towards the registers written in the last few
instructions, so most programs are dense with pipeline hazards.
"""

import argparse
import random

from isa import ALU

DATA_BASE = 0x0020       # R6 holds this for the whole program
DATA_LO, DATA_HI = 0x0001, 0x003F
HANDLER, SUB, MAIN = 0x0040, 0x0050, 0x0060
BODY_MAX = 14            # handler and subroutine: at most 14 ops + RET

ALU_OPS = sorted(ALU)
DESTS = [0, 1, 2, 3, 4, 5, 7]      # R6 is the data pointer
DESTS_NO_R7 = [0, 1, 2, 3, 4, 5]   # handler / subroutine must keep R7


class Gen:
    def __init__(self, seed):
        self.rnd = random.Random(seed)
        self.recent = []                 # registers written lately, newest last
        self.labels = 0

    def label(self):
        self.labels += 1
        return f"L{self.labels}"

    def src(self):
        """A source register, usually one just written."""
        if self.recent and self.rnd.random() < 0.6:
            return self.rnd.choice(self.recent[-3:])
        return self.rnd.randrange(8)

    def wrote(self, r):
        self.recent = (self.recent + [r])[-4:]

    def data_off(self):
        return self.rnd.randint(DATA_LO - DATA_BASE, DATA_HI - DATA_BASE)

    # ---- straight-line operations (no control flow) ------------------------
    def simple(self, dests):
        r = self.rnd
        d = r.choice(dests)
        k = r.random()
        if k < 0.45:
            name = r.choice(ALU_OPS)
            form = ALU[name][2]
            if form == "cmp":
                return f"CMP  R{self.src()}, R{self.src()}"
            self.wrote(d)
            if form == "rr":
                return f"{name:<4} R{d}, R{self.src()}"
            return f"{name:<4} R{d}, R{self.src()}, R{self.src()}"
        if k < 0.60:
            self.wrote(d)
            if r.random() < 0.5:
                return f"ADDI R{d}, R{self.src()}, {r.randint(-32, 31)}"
            return f"ANDI R{d}, R{self.src()}, {r.randint(0, 63)}"
        if k < 0.75:
            self.wrote(d)
            return f"LDR  R{d}, R6, {self.data_off()}"
        if k < 0.88:
            return f"STR  R{self.src()}, R6, {self.data_off()}"
        if k < 0.92:
            self.wrote(d)
            return f"LD   R{d}, d{r.randint(DATA_LO, DATA_HI):02X}"
        if k < 0.96:
            return f"ST   R{self.src()}, d{r.randint(DATA_LO, DATA_HI):02X}"
        if k < 0.98:
            return "NOP"
        return f".word 0x{r.choice((0xE, 0xF)) << 12 | r.randrange(0x1000):04X}   ; undefined"

    def body(self, n, dests):
        return [self.simple(dests) for _ in range(n)]

    # ---- main --------------------------------------------------------------
    def main(self, length):
        r = self.rnd
        out = ["LEA  R6, d20"]
        for reg in DESTS:                      # interesting starting values
            out.append(f"LDR  R{reg}, R6, {self.data_off()}")
        self.recent = []
        while len(out) < length:
            k = r.random()
            if k < 0.62:
                out.append(self.simple(DESTS))
            elif k < 0.72:                     # forward branch over 0-3 ops
                skip = r.randint(0, 3)
                mask = r.choice(["", "n", "z", "p", "nz", "np", "zp", "nzp"])
                lab = self.label()
                out.append(f"BR{mask:<3} {lab}" if mask else f"NOP")
                out += self.body(skip, DESTS)
                if mask:
                    out.append(f"{lab}:")
            elif k < 0.78:
                out.append("JSR  sub")
            elif k < 0.82:
                d = r.choice(DESTS)
                out.append(f"LEA  R{d}, sub")
                self.wrote(d)
                out.append(f"JSRR R{d}")
            elif k < 0.86:
                out.append("TRAP x040")
            elif k < 0.90:                     # JMP forward through a register
                d = r.choice(DESTS)
                lab = self.label()
                out += [f"LEA  R{d}, {lab}", f"JMP  R{d}"]
                out += self.body(r.randint(0, 2), DESTS)
                out.append(f"{lab}:")
                self.wrote(d)
            else:                              # counted loop
                c = r.choice(DESTS_NO_R7)
                lab = self.label()
                others = [x for x in DESTS if x != c]
                out += [f"ANDI R{c}, R{c}, 0", f"ADDI R{c}, R{c}, {r.randint(1, 4)}", f"{lab}:"]
                self.wrote(c)
                out += self.body(r.randint(1, 4), others)
                out += [f"DEC  R{c}, R{c}", f"BRp  {lab}"]
                self.wrote(c)
        out.append("HALT")
        return out

    def program(self, length):
        r = self.rnd
        lines = ["        BR   main", "        .org 0x0001"]
        for a in range(DATA_LO, DATA_HI + 1):
            lines.append(f"d{a:02X}:    .word 0x{r.randrange(0x10000):04X}")
        self.recent = []
        lines += [f"        .org 0x{HANDLER:04X}", "handler:"]
        lines += ["        " + s for s in self.body(r.randint(0, BODY_MAX), DESTS_NO_R7)]
        lines += ["        RET", f"        .org 0x{SUB:04X}", "sub:"]
        self.recent = [7]                      # the callee often reads R7 at once
        lines += ["        " + s for s in self.body(r.randint(0, BODY_MAX), DESTS_NO_R7)]
        lines += ["        RET", f"        .org 0x{MAIN:04X}", "main:"]
        for s in self.main(length):
            lines.append(s if s.endswith(":") else "        " + s)
        return "\n".join(lines) + "\n"


def generate(seed, length=120):
    return f"; random program, seed {seed}\n" + Gen(seed).program(length)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--length", type=int, default=120)
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    text = generate(args.seed, args.length)
    if args.output:
        open(args.output, "w").write(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
