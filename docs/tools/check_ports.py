"""Check the hand-written interface pages against the RTL.

For every module in rtl/ there must be docs/interfaces/<module>.md whose
"## Ports" table lists exactly the module's ports, in header order, with the
right direction and width, and whose "## Parameters" table (if the module has
parameters) lists the parameters with their defaults. Also checks that the
opcode and funct encodings in fsm_spec.py match rtl/cpu16_isa.sv.

    python3 check_ports.py        exit 1 on any mismatch
"""

import os
import re
import sys

import fsm_spec
from rtl import RTL_DIR, load_all

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.normpath(os.path.join(HERE, "..", "interfaces"))


def table_after(text, heading):
    """Rows (list of cell lists) of the first table under `## heading`."""
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return None
    rows = []
    for line in m.group(1).splitlines():
        if line.startswith("|") and not re.match(r"^\|[\s\-|:]+\|$", line):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip()[1:-1])]
            rows.append(cells)
    return rows[1:] if rows else []     # drop the header row


def code(cell):
    m = re.fullmatch(r"`([^`]+)`", cell)
    return m.group(1) if m else cell


def check_module(mod, problems):
    path = os.path.join(PAGES, mod.name + ".md")
    if not os.path.exists(path):
        problems.append(f"{mod.name}: no page docs/interfaces/{mod.name}.md")
        return
    text = open(path).read()
    rows = table_after(text, "Ports")
    if rows is None:
        problems.append(f"{mod.name}: page has no '## Ports' section")
        return
    doc = [(code(r[0]), r[1], r[2]) for r in rows]
    rtl = [(p.name, p.dir, str(p.width)) for p in mod.ports]
    if doc != rtl:
        dn, rn = [d[0] for d in doc], [r[0] for r in rtl]
        for n in rn:
            if n not in dn:
                problems.append(f"{mod.name}: port `{n}` missing from the table")
        for n in dn:
            if n not in rn:
                problems.append(f"{mod.name}: table lists `{n}`, which the RTL does not have")
        for d in doc:
            r = next((r for r in rtl if r[0] == d[0]), None)
            if r and r != d:
                problems.append(f"{mod.name}: `{d[0]}` is {r[1]} {r[2]} in RTL, "
                                f"table says {d[1]} {d[2]}")
        if sorted(dn) == sorted(rn) and dn != rn:
            problems.append(f"{mod.name}: rows not in RTL header order")
    if mod.params:
        prows = table_after(text, "Parameters") or []
        doc_p = [(code(r[0]), code(r[2])) for r in prows]
        rtl_p = [(p.name, p.default) for p in mod.params]
        if doc_p != rtl_p:
            problems.append(f"{mod.name}: parameters table {doc_p} != RTL {rtl_p}")
    sym = f"../figures/symbols/{mod.name}.svg"
    if sym not in text:
        problems.append(f"{mod.name}: page does not show its symbol ({sym})")


def check_isa(problems):
    src = open(os.path.join(RTL_DIR, "cpu16_isa.sv")).read()
    enc = {n: int(v, 16) for n, v in re.findall(r"\b(OP_\w+|ALU[01]_\w+)\s*=\s*\d+'[hb]([0-9A-Fa-f]+)", src)
           if n.startswith("OP_")}
    enc.update({n: int(v, 2) for n, v in re.findall(r"\b(ALU[01]_\w+)\s*=\s*3'b([01]+)", src)})
    for name, val in fsm_spec.OP.items():
        if enc.get("OP_" + name) != val:
            problems.append(f"fsm_spec OP[{name}]={val:#x} but cpu16_isa.sv has {enc.get('OP_' + name)}")
    for prefix, table in (("ALU0_", fsm_spec.F0), ("ALU1_", fsm_spec.F1)):
        for name, val in table.items():
            if enc.get(prefix + name) != val:
                problems.append(f"fsm_spec {prefix}{name}={val} but cpu16_isa.sv has "
                                f"{enc.get(prefix + name)}")


def main():
    problems = []
    mods = load_all()
    for mod in mods.values():
        check_module(mod, problems)
    for f in os.listdir(PAGES):
        name = f[:-3]
        if f.endswith(".md") and f != "README.md" and name not in mods and name != "cpu16_isa":
            problems.append(f"docs/interfaces/{f}: no RTL module named {name}")
    check_isa(problems)
    if problems:
        print("interface pages do NOT match the RTL:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print(f"interfaces: {len(mods)} modules, every port table matches the RTL; "
          f"fsm_spec encodings match cpu16_isa.sv")


if __name__ == "__main__":
    main()
