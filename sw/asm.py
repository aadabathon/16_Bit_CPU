"""adam16 assembler.

    python3 sw/asm.py prog.asm -o prog.mem [-l prog.lst]

Syntax (case-insensitive mnemonics and registers; ';' starts a comment):

    label:  ADD   R1, R2, R3        ; ALU0: ADD SUB AND OR XOR, NOT MOV NEG (DR, SR1)
            NAND  R1, R2, R3        ; ALU1: NAND NOR, INC DEC LSL1 LSR1 ASR1 (DR, SR1)
            CMP   R1, R2            ; signed compare -> N/Z/P
            ADDI  R1, R2, -5        ; imm6: -32..31        ANDI R1, R2, 0x3F ; imm6: 0..63
            LD    R1, label         ; also ST, LEA: label -> PC-relative offset9
            LDR   R1, R2, 3         ; also STR: offset6 -32..31
            BRnz  label             ; BR / BRnzp = always; any of n, z, p
            JMP   R3   /  JSR label  /  JSRR R3  /  RET
            TRAP  x40               ; vector 0..0xFFF
            HALT                    ; = TRAP x025
            NOP                     ; = BR with an empty mask (0xD000)
            .org  0x0100            ; set the location counter
            .word 1, -2, 0xBEEF, label
            .space 8                ; 8 zero words

Numbers: 12, #12, -3, 0x1F, x1F, 0b101. A label operand is resolved
PC-relative (offset from the incremented PC); a number is used as the raw
offset. The output .mem is $readmemh format with @address lines.
"""

import argparse
import re
import sys

from isa import ALU, HALT_WORD, NOP_WORD, OP, disasm


class AsmError(Exception):
    pass


def parse_number(tok):
    t = tok.strip().lower().lstrip("#")
    neg = t.startswith("-")
    t = t.lstrip("+-")
    if t.startswith("0x"):
        v = int(t[2:], 16)
    elif t.startswith("x") and re.fullmatch(r"x[0-9a-f]+", t):
        v = int(t[1:], 16)
    elif t.startswith("0b"):
        v = int(t[2:], 2)
    elif re.fullmatch(r"\d+", t):
        v = int(t)
    else:
        raise AsmError(f"not a number: {tok!r}")
    return -v if neg else v


def is_number(tok):
    try:
        parse_number(tok)
        return True
    except AsmError:
        return False


def reg(tok):
    m = re.fullmatch(r"[rR]([0-7])", tok.strip())
    if not m:
        raise AsmError(f"expected a register R0-R7, got {tok!r}")
    return int(m.group(1))


def check_range(value, lo, hi, what):
    if not lo <= value <= hi:
        raise AsmError(f"{what} {value} out of range {lo}..{hi}")
    return value


class Assembler:
    def __init__(self):
        self.labels = {}
        self.words = {}          # address -> (word, source line, line number)

    # ---- pass 1: addresses of labels -------------------------------------
    def lines(self, text):
        for n, raw in enumerate(text.splitlines(), 1):
            line = raw.split(";", 1)[0].strip()
            label = None
            m = re.match(r"([A-Za-z_][\w.]*)\s*:\s*(.*)", line)
            if m:
                label, line = m.group(1), m.group(2).strip()
            if not line and not label:
                continue
            parts = line.split(None, 1)
            mnem = parts[0] if parts else ""
            rest = parts[1] if len(parts) > 1 else ""
            ops = [o.strip() for o in rest.split(",")] if rest.strip() else []
            yield n, raw.rstrip(), label, mnem.upper(), ops

    def size(self, mnem, ops):
        if mnem == ".WORD":
            return len(ops)
        if mnem == ".SPACE":
            return parse_number(ops[0])
        return 0 if mnem in ("", ".ORG") else 1

    def pass1(self, text):
        loc = 0
        for n, raw, label, mnem, ops in self.lines(text):
            try:
                if label:
                    if label in self.labels:
                        raise AsmError(f"label {label!r} defined twice")
                    self.labels[label] = loc
                if mnem == ".ORG":
                    loc = parse_number(ops[0])
                else:
                    loc += self.size(mnem, ops)
            except AsmError as e:
                raise AsmError(f"line {n}: {e}") from None

    # ---- pass 2: encode ----------------------------------------------------
    def value(self, tok):
        if is_number(tok):
            return parse_number(tok)
        if tok in self.labels:
            return self.labels[tok]
        raise AsmError(f"unknown label {tok!r}")

    def pcrel(self, tok, pc, bits):
        if is_number(tok):
            off = parse_number(tok)
        elif tok in self.labels:
            off = self.labels[tok] - (pc + 1)
        else:
            raise AsmError(f"unknown label {tok!r}")
        lim = 1 << (bits - 1)
        check_range(off, -lim, lim - 1, f"offset to {tok!r} is")
        return off & ((1 << bits) - 1)

    def encode(self, mnem, ops, pc):
        def need(k):
            if len(ops) != k:
                raise AsmError(f"{mnem} takes {k} operand(s), got {len(ops)}")

        if mnem in ALU:
            op, fn, form = ALU[mnem]
            if form == "rrr":
                need(3)
                return (op << 12) | (reg(ops[0]) << 9) | (reg(ops[1]) << 6) | (reg(ops[2]) << 3) | fn
            if form == "rr":
                need(2)
                return (op << 12) | (reg(ops[0]) << 9) | (reg(ops[1]) << 6) | fn
            need(2)
            return (op << 12) | (reg(ops[0]) << 6) | (reg(ops[1]) << 3) | fn
        if mnem in ("ADDI", "ANDI"):
            need(3)
            imm = parse_number(ops[2])
            if mnem == "ADDI":
                check_range(imm, -32, 31, "ADDI immediate")
            else:
                check_range(imm, 0, 63, "ANDI immediate")
            return (OP[mnem] << 12) | (reg(ops[0]) << 9) | (reg(ops[1]) << 6) | (imm & 0x3F)
        if mnem in ("LD", "ST", "LEA"):
            need(2)
            return (OP[mnem] << 12) | (reg(ops[0]) << 9) | self.pcrel(ops[1], pc, 9)
        if mnem in ("LDR", "STR"):
            need(3)
            off = check_range(parse_number(ops[2]), -32, 31, f"{mnem} offset")
            return (OP[mnem] << 12) | (reg(ops[0]) << 9) | (reg(ops[1]) << 6) | (off & 0x3F)
        m = re.fullmatch(r"BR([NZP]*)", mnem)
        if m:
            need(1)
            cond = m.group(1) or "NZP"
            mask = (4 if "N" in cond else 0) | (2 if "Z" in cond else 0) | (1 if "P" in cond else 0)
            return (OP["BR"] << 12) | (mask << 9) | self.pcrel(ops[0], pc, 9)
        if mnem == "JMP":
            need(1)
            return (OP["JMP"] << 12) | (reg(ops[0]) << 6)
        if mnem == "JSR":
            need(1)
            return (OP["JSR"] << 12) | self.pcrel(ops[0], pc, 11)
        if mnem == "JSRR":
            need(1)
            return (OP["JSR"] << 12) | (1 << 11) | (reg(ops[0]) << 6)
        if mnem == "RET":
            need(0)
            return OP["RET"] << 12
        if mnem == "TRAP":
            need(1)
            return (OP["TRAP"] << 12) | check_range(self.value(ops[0]), 0, 0xFFF, "TRAP vector")
        if mnem == "HALT":
            need(0)
            return HALT_WORD
        if mnem == "NOP":
            need(0)
            return NOP_WORD
        raise AsmError(f"unknown mnemonic {mnem!r}")

    def put(self, addr, word, raw, n):
        if not 0 <= addr <= 0xFFFF:
            raise AsmError(f"address 0x{addr:X} outside memory")
        if addr in self.words:
            raise AsmError(f"address 0x{addr:04X} written twice")
        self.words[addr] = (word & 0xFFFF, raw, n)

    def pass2(self, text):
        loc = 0
        for n, raw, label, mnem, ops in self.lines(text):
            try:
                if mnem in ("", ):
                    continue
                if mnem == ".ORG":
                    loc = parse_number(ops[0])
                elif mnem == ".WORD":
                    for k, o in enumerate(ops):
                        v = self.value(o)
                        check_range(v, -0x8000, 0xFFFF, ".word value")
                        self.put(loc, v, raw if k == 0 else "", n)
                        loc += 1
                elif mnem == ".SPACE":
                    for _ in range(parse_number(ops[0])):
                        self.put(loc, 0, "", n)
                        loc += 1
                else:
                    self.put(loc, self.encode(mnem, ops, loc), raw, n)
                    loc += 1
            except AsmError as e:
                raise AsmError(f"line {n}: {e}\n    {raw.strip()}") from None

    def assemble(self, text):
        self.pass1(text)
        self.pass2(text)
        return self

    # ---- output ------------------------------------------------------------
    def mem_lines(self):
        out, nxt = [], None
        for addr in sorted(self.words):
            word, raw, _ = self.words[addr]
            if addr != nxt:
                out.append(f"@{addr:04X}")
            src = raw.strip()
            out.append(f"{word:04X}" + (f"  // {addr:04X}: {src}" if src else ""))
            nxt = addr + 1
        return out

    def listing(self):
        out = []
        for addr in sorted(self.words):
            word, raw, n = self.words[addr]
            out.append(f"{addr:04X}  {word:04X}  {disasm(word, addr):<28} {raw.strip()}")
        return out


def assemble_file(path):
    return Assembler().assemble(open(path).read())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("source")
    ap.add_argument("-o", "--output", help=".mem file to write")
    ap.add_argument("-l", "--listing", help="listing file to write")
    args = ap.parse_args()
    try:
        a = assemble_file(args.source)
    except AsmError as e:
        sys.exit(f"{args.source}: {e}")
    out = args.output or re.sub(r"\.\w+$", "", args.source) + ".mem"
    with open(out, "w") as f:
        f.write(f"// assembled from {args.source}\n" + "\n".join(a.mem_lines()) + "\n")
    if args.listing:
        with open(args.listing, "w") as f:
            f.write("\n".join(a.listing()) + "\n")
    print(f"{args.source}: {len(a.words)} words -> {out}")


if __name__ == "__main__":
    main()
