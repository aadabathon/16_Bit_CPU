"""adam16_control_fsm specification.

This file is the single source of truth for the control state machine's
documentation. From it, gen_fsm.py draws every control bubble diagram and
writes test vectors that tb/tb_control_fsm_spec.sv replays against the RTL,
so the diagrams are checked against rtl/adam16_control_fsm.sv cycle by cycle.

When you change the FSM RTL, change this file to match, then run
`make -C docs` (redraw) and `make -C docs check` (prove RTL == spec).

Notation (ECE551 style): every arc is `condition / outputs`. The outputs on
an arc are the values the FSM drives while it is in the arc's source state
and that condition holds; on the clock edge it moves to the arc's target.
Any output not listed is at its default (0). Listing an output at its
default value marks it as significant (drawn in grey in the diagrams).
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

# --------------------------------------------------------------------------
# Encodings (mirror rtl/adam16_isa.sv)
# --------------------------------------------------------------------------
OP = dict(ALU0=0x0, ALU1=0x1, ADDI=0x2, ANDI=0x3, LD=0x4, ST=0x5, JMP=0x6,
          JSR=0x7, RET=0x8, TRAP=0x9, LDR=0xA, STR=0xB, LEA=0xC, BR=0xD,
          UD_E=0xE, UD_F=0xF)
F0 = dict(ADD=0, SUB=1, NOT=2, AND=3, OR=4, XOR=5, MOV=6, NEG=7)
F1 = dict(NAND=0, NOR=1, INC=2, DEC=3, LSL1=4, LSR1=5, ASR1=6, CMP=7)


# --------------------------------------------------------------------------
# SM inputs: the FSM sees ir[15:0] and the flags N, Z, P
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class In:
    ir: int
    n: int
    z: int
    p: int

    @property
    def op(self):        # IR[15:12]
        return (self.ir >> 12) & 0xF

    @property
    def fn(self):        # IR[2:0]  ALU funct
        return self.ir & 0x7

    @property
    def dr(self):        # IR[11:9] DR / SR / nzp mask
        return (self.ir >> 9) & 0x7

    @property
    def j(self):         # IR[11]   JSR (0) vs JSRR (1)
        return (self.ir >> 11) & 0x1

    @property
    def take_br(self):
        m = self.dr
        return bool((m & 4 and self.n) or (m & 2 and self.z) or (m & 1 and self.p))


INPUT_NOTES = [
    ("op", "IR[15:12]"),
    ("fn", "IR[2:0]"),
    ("DR", "IR[11:9]"),
    ("j", "IR[11]"),
    ("take_br", "(IR[11]&N) | (IR[10]&Z) | (IR[9]&P)"),
]

# --------------------------------------------------------------------------
# SM outputs, in packing order (MSB first) for the conformance vectors
# --------------------------------------------------------------------------
OUTPUTS = [
    ("pc_we", 1), ("ir_we", 1), ("mar_we", 1), ("mdr_we", 1),
    ("reg_we", 1), ("flag_we", 1), ("mem_we", 1),
    ("reg_dst", 3), ("ra1_sel", 2), ("wb_sel", 2), ("alu_op", 4),
    ("alu_a_sel", 2), ("alu_b_sel", 3), ("pc_src_sel", 3), ("mar_src_sel", 2),
]
WIDTH = dict(OUTPUTS)
DEFAULTS = {name: 0 for name, _ in OUTPUTS}

# Meaning of each select code, shown next to the value in the diagrams.
CODE_NAMES = {
    "pc_src_sel": {0: "PC+1", 1: "PC+off9", 2: "PC+off11", 3: "BaseR", 4: "R7", 5: "tv12"},
    "mar_src_sel": {0: "PC", 1: "alu_y"},
    "alu_a_sel": {0: "rd0", 1: "PC"},
    "alu_b_sel": {0: "rd1", 1: "sext6", 2: "zext6", 3: "sext9", 4: "sext6", 7: "0"},
    "wb_sel": {0: "alu_y", 1: "MDR", 2: "PC"},
    "ra1_sel": {0: "IR[5:3]", 1: "IR[11:9]", 2: "R7"},
    "reg_dst": {7: "R7"},
    "alu_op": {0: "ADD", 3: "AND", 15: "CMP"},
}


@dataclass(frozen=True)
class Expr:
    """An output value or condition that depends on the SM inputs."""
    text: str
    fn: Callable[[In], int]


DR = Expr("DR", lambda i: i.dr)
ALU_OP_0 = Expr("{0,fn}", lambda i: 0b0000 | i.fn)
ALU_OP_1 = Expr("{1,fn}", lambda i: 0b1000 | i.fn)


SHOW = {"UD_E": "xE", "UD_F": "xF"}   # display names for the undefined opcodes


def op_in(*names):
    codes = {OP[n] for n in names}
    shown = [SHOW.get(n, n) for n in names]
    text = "op = " + shown[0] if len(shown) == 1 else "op ∈ {" + ", ".join(shown) + "}"
    return Expr(text, lambda i, c=frozenset(codes): i.op in c)


def alu(opname, *fns):
    table = F0 if opname == "ALU0" else F1
    codes = frozenset(table[f] for f in fns)
    fset = fns[0] if len(fns) == 1 else "{" + ", ".join(fns) + "}"
    rel = "=" if len(fns) == 1 else "∈"
    return Expr(f"op = {opname}, fn {rel} {fset}",
                lambda i, c=codes, o=OP[opname]: i.op == o and i.fn in c)


TAKE = Expr("take_br", lambda i: i.take_br)
NOT_TAKE = Expr("!take_br", lambda i: not i.take_br)
J0 = Expr("j = 0  (JSR)", lambda i: i.j == 0)
J1 = Expr("j = 1  (JSRR)", lambda i: i.j == 1)


# --------------------------------------------------------------------------
# States and arcs
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class State:
    name: str
    code: int
    phase: str
    rtl: str          # register transfer on the closing edge (bubble text)
    detail: str = ""  # longer wording for the state table (defaults to rtl)


STATES = [
    State("S_IF0", 0, "fetch", "MAR ← PC"),
    State("S_IF1", 1, "fetch", "wait (SRAM read)", "— (memory reads M[MAR])"),
    State("S_IF2", 2, "fetch", "IR ← M[MAR]\nPC ← PC + 1"),
    State("S_ID", 3, "decode", "decode IR"),
    State("S_EX_ALU", 4, "execute", "DR ← A op B\nNZP ← result",
          "DR ← A op B; N Z P ← f(result). CMP writes flags only; LEA writes DR only"),
    State("S_EX_EA", 5, "execute", "MAR ← EA",
          "MAR ← EA: PC† + SEXT(off9) for LD/ST, BaseR + SEXT(off6) for LDR/STR"),
    State("S_MEM_RD0", 6, "memory", "wait (SRAM read)", "— (memory reads M[MAR])"),
    State("S_MEM_RD1", 7, "memory", "MDR ← M[MAR]"),
    State("S_WB_LD", 8, "memory", "DR ← MDR"),
    State("S_MEM_WR0", 9, "memory", "M[MAR] ← SR"),
    State("S_EX_BR", 10, "execute", "if take_br:\nPC ← PC + off9",
          "if take_br: PC ← PC† + SEXT(off9)"),
    State("S_EX_JMP", 11, "execute", "PC ← BaseR\nor R7 (RET)", "PC ← BaseR (JMP) or R7 (RET)"),
    State("S_EX_JSR", 12, "execute", "R7 ← PC\nPC ← PC + off11\nor BaseR",
          "R7 ← PC†; PC ← PC† + SEXT(off11) (JSR) or BaseR (JSRR)"),
    State("S_EX_TRAP", 13, "execute", "R7 ← PC\nPC ← ZEXT(tv12)", "R7 ← PC†; PC ← ZEXT(IR[11:0])"),
]
STATE = {s.name: s for s in STATES}
RESET_STATE = "S_IF0"


@dataclass(frozen=True)
class Arc:
    src: str
    dst: str
    when: Optional[Expr] = None          # None: unconditional
    out: dict = field(default_factory=dict)
    brief: str = ""                      # label on the overview diagram


# Outputs shared by several arcs
WRITE_DR = {"reg_we": 1, "flag_we": 1, "reg_dst": DR, "wb_sel": 0}
LINK_R7 = {"pc_we": 1, "reg_we": 1, "reg_dst": 7, "wb_sel": 2}
EA_PCREL = {"mar_we": 1, "mar_src_sel": 1, "alu_op": 0, "alu_a_sel": 1, "alu_b_sel": 3}
EA_BASE = {"mar_we": 1, "mar_src_sel": 1, "alu_op": 0, "alu_a_sel": 0, "alu_b_sel": 4}

ARCS = [
    # ---- fetch ------------------------------------------------------------
    Arc("S_IF0", "S_IF1", out={"mar_we": 1, "mar_src_sel": 0}),
    Arc("S_IF1", "S_IF2"),
    Arc("S_IF2", "S_ID", out={"ir_we": 1, "pc_we": 1, "pc_src_sel": 0}),

    # ---- decode -----------------------------------------------------------
    Arc("S_ID", "S_EX_ALU", op_in("ALU0", "ALU1", "ADDI", "ANDI", "LEA"),
        brief="ALU0, ALU1,\nADDI, ANDI, LEA"),
    Arc("S_ID", "S_EX_EA", op_in("LD", "LDR", "ST", "STR"), brief="LD, LDR,\nST, STR"),
    Arc("S_ID", "S_EX_BR", op_in("BR"), brief="BR"),
    Arc("S_ID", "S_EX_JMP", op_in("JMP", "RET"), brief="JMP, RET"),
    Arc("S_ID", "S_EX_JSR", op_in("JSR"), brief="JSR"),
    Arc("S_ID", "S_EX_TRAP", op_in("TRAP"), brief="TRAP"),
    Arc("S_ID", "S_IF0", op_in("UD_E", "UD_F"), brief="xE, xF\n(undefined)"),

    # ---- ALU class --------------------------------------------------------
    Arc("S_EX_ALU", "S_IF0", alu("ALU0", "ADD", "SUB", "AND", "OR", "XOR", "MOV"),
        {**WRITE_DR, "alu_op": ALU_OP_0, "alu_a_sel": 0, "alu_b_sel": 0, "ra1_sel": 0}),
    Arc("S_EX_ALU", "S_IF0", alu("ALU0", "NOT", "NEG"),
        {**WRITE_DR, "alu_op": ALU_OP_0, "alu_a_sel": 0, "alu_b_sel": 7}),
    Arc("S_EX_ALU", "S_IF0", alu("ALU1", "NAND", "NOR"),
        {**WRITE_DR, "alu_op": ALU_OP_1, "alu_a_sel": 0, "alu_b_sel": 0, "ra1_sel": 0}),
    Arc("S_EX_ALU", "S_IF0", alu("ALU1", "INC", "DEC", "LSL1", "LSR1", "ASR1"),
        {**WRITE_DR, "alu_op": ALU_OP_1, "alu_a_sel": 0, "alu_b_sel": 7}),
    Arc("S_EX_ALU", "S_IF0", alu("ALU1", "CMP"),
        {"flag_we": 1, "reg_dst": DR, "wb_sel": 0, "alu_op": 15, "alu_a_sel": 0,
         "alu_b_sel": 0, "ra1_sel": 0}),
    Arc("S_EX_ALU", "S_IF0", op_in("ADDI"),
        {**WRITE_DR, "alu_op": 0, "alu_a_sel": 0, "alu_b_sel": 1}),
    Arc("S_EX_ALU", "S_IF0", op_in("ANDI"),
        {**WRITE_DR, "alu_op": 3, "alu_a_sel": 0, "alu_b_sel": 2}),
    Arc("S_EX_ALU", "S_IF0", op_in("LEA"),
        {"reg_we": 1, "reg_dst": DR, "wb_sel": 0, "alu_op": 0, "alu_a_sel": 1,
         "alu_b_sel": 3}),

    # ---- load / store -----------------------------------------------------
    Arc("S_EX_EA", "S_MEM_RD0", op_in("LD"), EA_PCREL, brief="LD"),
    Arc("S_EX_EA", "S_MEM_RD0", op_in("LDR"), EA_BASE, brief="LDR"),
    Arc("S_EX_EA", "S_MEM_WR0", op_in("ST"), EA_PCREL, brief="ST"),
    Arc("S_EX_EA", "S_MEM_WR0", op_in("STR"), EA_BASE, brief="STR"),
    Arc("S_MEM_RD0", "S_MEM_RD1"),
    Arc("S_MEM_RD1", "S_WB_LD", out={"mdr_we": 1}),
    Arc("S_WB_LD", "S_IF0", out={"reg_we": 1, "reg_dst": DR, "wb_sel": 1}),
    Arc("S_MEM_WR0", "S_IF0", out={"mem_we": 1, "ra1_sel": 1}),

    # ---- control flow -----------------------------------------------------
    Arc("S_EX_BR", "S_IF0", TAKE, {"pc_we": 1, "pc_src_sel": 1}),
    Arc("S_EX_BR", "S_IF0", NOT_TAKE, {}),
    Arc("S_EX_JMP", "S_IF0", op_in("JMP"), {"pc_we": 1, "pc_src_sel": 3}),
    Arc("S_EX_JMP", "S_IF0", op_in("RET"), {"pc_we": 1, "ra1_sel": 2, "pc_src_sel": 4}),
    Arc("S_EX_JSR", "S_IF0", J0, {**LINK_R7, "pc_src_sel": 2}),
    Arc("S_EX_JSR", "S_IF0", J1, {**LINK_R7, "pc_src_sel": 3}),
    Arc("S_EX_TRAP", "S_IF0", out={**LINK_R7, "pc_src_sel": 5}),
]


# --------------------------------------------------------------------------
# Executable model
# --------------------------------------------------------------------------
def value(v, inp):
    return v.fn(inp) if isinstance(v, Expr) else v


def step(state, inp):
    """Return (outputs dict, next state) for one cycle. Exactly one arc must match."""
    hits = [a for a in ARCS if a.src == state and (a.when is None or a.when.fn(inp))]
    if len(hits) != 1:
        raise ValueError(f"{state} ir={inp.ir:04x}: {len(hits)} arcs match "
                         f"({[a.when.text if a.when else 'always' for a in hits]})")
    arc = hits[0]
    outs = dict(DEFAULTS)
    outs.update({k: value(v, inp) for k, v in arc.out.items()})
    return outs, arc.dst


def pack(outs):
    word = 0
    for name, width in OUTPUTS:
        assert 0 <= outs[name] < (1 << width), (name, outs[name])
        word = (word << width) | outs[name]
    return word


def instruction_trace(inp):
    """States and outputs, one per cycle, for one instruction starting at reset."""
    trace, state = [], RESET_STATE
    while True:
        outs, nxt = step(state, inp)
        trace.append((state, outs))
        state = nxt
        if state == RESET_STATE:
            return trace
        if len(trace) > 16:
            raise RuntimeError("instruction never returns to fetch")
