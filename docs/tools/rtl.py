"""Read module headers, instances and assigns out of the RTL.

Handles the subset of SystemVerilog this repository uses: ANSI-style port
lists with one port per line, `parameter` lists, named port connections,
and continuous `assign` statements. Blank lines inside a port list split the
ports into groups (the symbol figures keep those groups).
"""

import os
import re
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
RTL_DIR = os.path.join(ROOT, "rtl")


@dataclass
class Port:
    name: str
    dir: str          # "in" / "out"
    width: int
    msb: int
    lsb: int
    group: int


@dataclass
class Param:
    name: str
    type: str
    default: str


@dataclass
class Instance:
    module: str
    name: str
    conns: dict       # port -> connected expression


@dataclass
class Module:
    name: str
    file: str
    params: list = field(default_factory=list)
    ports: list = field(default_factory=list)
    instances: list = field(default_factory=list)
    assigns: dict = field(default_factory=dict)   # lhs -> rhs expression
    comb_nets: set = field(default_factory=set)   # assigned inside always_comb
    reg_nets: set = field(default_factory=set)    # assigned inside always_ff
    blocks: list = field(default_factory=list)    # (kind, body text) of each always block

    def port(self, name):
        return next(p for p in self.ports if p.name == name)


COMMENT = "__comment__"


def _strip_comments(text):
    """Replace comments with a placeholder so comment-only lines (e.g. lint
    pragmas) are not mistaken for the blank lines that separate port groups."""
    text = re.sub(r"/\*.*?\*/", lambda m: "\n".join(f" {COMMENT}" for _ in m.group(0).split("\n")),
                  text, flags=re.S)
    return re.sub(r"//[^\n]*", f" {COMMENT}", text)


def _matching(text, i):
    """Index of the ')' matching the '(' at text[i]."""
    depth = 0
    in_str = False
    for j in range(i, len(text)):
        ch = text[j]
        if ch == '"':
            in_str = not in_str
        elif not in_str and ch == "(":
            depth += 1
        elif not in_str and ch == ")":
            depth -= 1
            if depth == 0:
                return j
    raise ValueError("unbalanced parentheses")


PORT_RE = re.compile(r"^\s*(input|output|inout)\s+(?:logic|wire|reg)?\s*"
                     r"(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*(\w+)")
PARAM_RE = re.compile(r"parameter\s+(?:(\w+)\s+)?(\w+)\s*=\s*([^,\n]+)")


def parse_file(path):
    raw = open(path).read()
    text = _strip_comments(raw)
    mods = []
    for m in re.finditer(r"\bmodule\s+(\w+)", text):
        name = m.group(1)
        i = m.end()
        mod = Module(name=name, file=os.path.relpath(path, ROOT))
        rest = text[i:].lstrip()
        i = len(text) - len(rest)
        if text[i] == "#":
            j = text.index("(", i)
            k = _matching(text, j)
            for pm in PARAM_RE.finditer(text[j + 1:k]):
                default = pm.group(3).replace(COMMENT, "").strip()
                mod.params.append(Param(pm.group(2), pm.group(1) or "", default))
            i = k + 1
        j = text.index("(", i)
        k = _matching(text, j)
        group = 0
        seen_port = False
        for line in text[j + 1:k].split("\n"):
            if not line.strip():
                if seen_port:
                    group += 1
                    seen_port = False
                continue
            pm = PORT_RE.match(line)
            if pm:
                d, msb, lsb, pname = pm.groups()
                msb = int(msb) if msb else 0
                lsb = int(lsb) if lsb else 0
                mod.ports.append(Port(pname, "in" if d == "input" else "out",
                                      msb - lsb + 1, msb, lsb, group))
                seen_port = True
        end = text.index("endmodule", k)
        _parse_body(mod, text[k + 1:end])
        mods.append(mod)
    return mods


def _block(body, start):
    """Text of the always block starting at body[start]: up to the `end` that
    closes its first `begin`, or up to the first ';' for a single statement."""
    semi = body.find(";", start)
    first = re.compile(r"\bbegin\b").search(body, start)
    if not first or (semi != -1 and first.start() > semi):
        return body[start: semi + 1 if semi != -1 else len(body)]
    depth = 0
    for t in re.finditer(r"\b(begin|end)\b", body[first.start():]):
        depth += 1 if t.group(1) == "begin" else -1
        if depth == 0:
            return body[start: first.start() + t.end()]
    return body[start:]


def _parse_body(mod, body):
    for am in re.finditer(r"\bassign\s+(\w+)\s*=\s*([^;]+);", body):
        mod.assigns[am.group(1)] = " ".join(am.group(2).split())
    for kind, target in (("always_comb", mod.comb_nets), ("always_ff", mod.reg_nets)):
        for bm in re.finditer(rf"\b{kind}\b", body):
            block = _block(body, bm.end())
            mod.blocks.append((kind, block))
            for lhs in re.findall(r"(\w+)(?:\[[^\]]*\])?\s*<?=(?!=)", block):
                target.add(lhs)
    # instances: <type> [#(...)] <name> ( .port(expr), ... );
    for im in re.finditer(r"\b(\w+)\s*(#\s*\()?", body):
        mtype = im.group(1)
        if mtype in ("module", "assign", "begin", "end", "if", "else", "case", "logic",
                     "input", "output", "unique", "always_ff", "always_comb", "posedge",
                     "import", "typedef", "enum", "return", "function"):
            continue
        i = im.end()
        if im.group(2):
            i = _matching(body, im.end() - 1) + 1
        nm = re.match(r"\s*(\w+)\s*\(", body[i:])
        if not nm:
            continue
        j = i + nm.end() - 1
        try:
            k = _matching(body, j)
        except ValueError:
            continue
        inner = body[j + 1:k]
        if not inner.lstrip().startswith("."):
            continue
        conns = {}
        for cm in re.finditer(r"\.(\w+)\s*\(", inner):
            a = cm.end() - 1
            b = _matching(inner, a)
            conns[cm.group(1)] = " ".join(inner[a + 1:b].split())
        mod.instances.append(Instance(mtype, nm.group(1), conns))


def load_all():
    mods = {}
    for f in sorted(os.listdir(RTL_DIR)):
        if f.endswith(".sv"):
            for m in parse_file(os.path.join(RTL_DIR, f)):
                mods[m.name] = m
    return mods


if __name__ == "__main__":
    for m in load_all().values():
        print(f"{m.name}  ({m.file})  params={[p.name for p in m.params]}")
        for p in m.ports:
            print(f"   g{p.group} {p.dir:3} {p.width:2}  {p.name}")
        for inst in m.instances:
            print(f"   inst {inst.module} {inst.name}: {len(inst.conns)} conns")
        if m.assigns:
            print("   assigns", m.assigns)
