"""adam16 instruction set: encodings shared by the assembler, the ISS and the
disassembler. Mirrors rtl/adam16_isa.sv and InstructionSet.txt.

Every instruction is one 16-bit word; memory is word-addressed.
"""

OP = dict(ALU0=0x0, ALU1=0x1, ADDI=0x2, ANDI=0x3, LD=0x4, ST=0x5, JMP=0x6,
          JSR=0x7, RET=0x8, TRAP=0x9, LDR=0xA, STR=0xB, LEA=0xC, BR=0xD)

# mnemonic -> (opcode, funct, operand form)
#   rrr: DR, SR1, SR2      rr: DR, SR1      cmp: SR1, SR2
ALU = {
    "ADD": (0, 0, "rrr"), "SUB": (0, 1, "rrr"), "NOT": (0, 2, "rr"), "AND": (0, 3, "rrr"),
    "OR": (0, 4, "rrr"), "XOR": (0, 5, "rrr"), "MOV": (0, 6, "rr"), "NEG": (0, 7, "rr"),
    "NAND": (1, 0, "rrr"), "NOR": (1, 1, "rrr"), "INC": (1, 2, "rr"), "DEC": (1, 3, "rr"),
    "LSL1": (1, 4, "rr"), "LSR1": (1, 5, "rr"), "ASR1": (1, 6, "rr"), "CMP": (1, 7, "cmp"),
}
FUNCT_NAME = {(op, fn): name for name, (op, fn, _) in ALU.items()}

HALT_WORD = 0x9025     # TRAP x025: the halt convention
NOP_WORD = 0xD000      # BR with an empty nzp mask: never taken


def mask16(x):
    return x & 0xFFFF


def sext(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def to_signed(x):
    return sext(x, 16)


def fields(ir):
    """Every field an instruction can use (cf. adam16_isa::decode)."""
    return dict(op=(ir >> 12) & 0xF, dr=(ir >> 9) & 7, sr1=(ir >> 6) & 7, sr2=(ir >> 3) & 7,
                fn=ir & 7, imm6=ir & 0x3F, off9=ir & 0x1FF, off11=ir & 0x7FF,
                tv12=ir & 0xFFF, j=(ir >> 11) & 1)


def disasm(ir, pc=None):
    """One-line disassembly; PC-relative targets are shown absolute if pc is given."""
    f = fields(ir)
    op = f["op"]

    def target(off, bits):
        rel = sext(off, bits)
        return f"0x{mask16(pc + 1 + rel):04X}" if pc is not None else f"{rel:+d}"

    if ir == HALT_WORD:
        return "HALT"
    if op in (0, 1):
        name = FUNCT_NAME[(op, f["fn"])]
        form = ALU[name][2]
        if form == "rrr":
            return f"{name} R{f['dr']}, R{f['sr1']}, R{f['sr2']}"
        if form == "rr":
            return f"{name} R{f['dr']}, R{f['sr1']}"
        return f"CMP R{f['sr1']}, R{f['sr2']}"
    if op == OP["ADDI"]:
        return f"ADDI R{f['dr']}, R{f['sr1']}, {sext(f['imm6'], 6)}"
    if op == OP["ANDI"]:
        return f"ANDI R{f['dr']}, R{f['sr1']}, {f['imm6']}"
    if op in (OP["LD"], OP["ST"], OP["LEA"]):
        name = {OP["LD"]: "LD", OP["ST"]: "ST", OP["LEA"]: "LEA"}[op]
        return f"{name} R{f['dr']}, {target(f['off9'], 9)}"
    if op in (OP["LDR"], OP["STR"]):
        name = "LDR" if op == OP["LDR"] else "STR"
        return f"{name} R{f['dr']}, R{f['sr1']}, {sext(f['imm6'], 6)}"
    if op == OP["BR"]:
        m = f["dr"]
        cond = ("n" if m & 4 else "") + ("z" if m & 2 else "") + ("p" if m & 1 else "")
        return "NOP" if m == 0 else f"BR{cond} {target(f['off9'], 9)}"
    if op == OP["JMP"]:
        return f"JMP R{f['sr1']}"
    if op == OP["JSR"]:
        return f"JSRR R{f['sr1']}" if f["j"] else f"JSR {target(f['off11'], 11)}"
    if op == OP["RET"]:
        return "RET"
    if op == OP["TRAP"]:
        return f"TRAP x{f['tv12']:03X}"
    return f".word 0x{ir:04X}  ; undefined opcode (no-op)"
