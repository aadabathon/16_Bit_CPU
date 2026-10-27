"""Fill the generated blocks in docs/interfaces/<module>.md from the RTL.

Two kinds of block, delimited by HTML comments in the markdown:

    <!-- BEGIN GENERATED: instantiation -->  ...  <!-- END GENERATED: instantiation -->
    <!-- BEGIN GENERATED: connections -->    ...  <!-- END GENERATED: connections -->

    python3 gen_interconnect.py           rewrite the blocks
    python3 gen_interconnect.py --check   exit 1 if any block is out of date
"""

import os
import re
import sys

import mdblocks
from rtl import load_all

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.normpath(os.path.join(HERE, "..", "interfaces"))
IDENT = re.compile(r"\b[A-Za-z_]\w*\b")


def instantiation(mod):
    lines = ["```systemverilog"]
    if mod.params:
        lines.append(f"{mod.name} #(")
        w = max(len(p.name) for p in mod.params)
        for k, p in enumerate(mod.params):
            comma = "," if k < len(mod.params) - 1 else ""
            lines.append(f"  .{p.name:<{w}} ({p.default}){comma}")
        lines.append(f") u_{mod.name.lower()} (")
    else:
        lines.append(f"{mod.name} u_{mod.name.lower()} (")
    w = max(len(p.name) for p in mod.ports)
    for k, p in enumerate(mod.ports):
        comma = "," if k < len(mod.ports) - 1 else " "
        conn = f"  .{p.name:<{w}} ({p.name}){comma}"
        lines.append(f"{conn:<{2 * w + 8}} // {p.dir:<3} {p.width:>2}")
    lines += [");", "```"]
    return "\n".join(lines)


def connections(mod, mods):
    """Net table for a module that instantiates others."""
    drivers, loads, width = {}, {}, {}

    def add(table, net, who):
        table.setdefault(net, [])
        if who not in table[net]:
            table[net].append(who)

    for p in mod.ports:
        width[p.name] = p.width
        add(drivers if p.dir == "in" else loads, p.name, f"port `{p.name}`")
    for inst in mod.instances:
        sub = mods[inst.module]
        for port, expr in inst.conns.items():
            sp = sub.port(port)
            who = f"`{inst.name}.{port}`"
            if IDENT.fullmatch(expr):
                width.setdefault(expr, sp.width)
                add(drivers if sp.dir == "out" else loads, expr, who)
            else:                      # constant or expression
                add(loads, expr, who)
    for lhs, rhs in mod.assigns.items():
        if IDENT.fullmatch(rhs):
            add(loads, rhs, f"`assign {lhs}`")
            add(drivers, lhs, f"`assign` from `{rhs}`")
        else:
            add(drivers, lhs, f"`assign {lhs} = {rhs}`")
            for name in IDENT.findall(rhs):
                add(loads, name, f"`assign {lhs}`")
    for kind, text in mod.blocks:
        targets = set(re.findall(r"(\w+)(?:\[[^\]]*\])?\s*<?=(?!=)", text))
        for name in set(IDENT.findall(text)):
            if name in targets:
                add(drivers, name, f"`{kind}` logic")
            elif name in width:
                add(loads, name, f"`{kind}` logic")

    # every port, then every internal net that reaches a sub-module instance,
    # in the order the RTL connects them
    order = [p.name for p in mod.ports]
    for inst in mod.instances:
        for expr in inst.conns.values():
            if IDENT.fullmatch(expr) and expr not in order:
                order.append(expr)
    rows = ["| Net | Width | Driven by | Read by |", "|---|---|---|---|"]
    for n in order:
        drv = ", ".join(drivers.get(n, ["—"])).replace("|", "\\|")   # pipes inside cells
        rd = ", ".join(loads.get(n, ["**nothing** (unused)"])).replace("|", "\\|")
        rows.append(f"| `{n}` | {width[n]} | {drv} | {rd} |")
    return "\n".join(rows)


def module_index(mods):
    """The module table on docs/interfaces/README.md."""
    rows = ["| Module | File | Clocked | In / out | Page |", "|---|---|---|---|---|"]
    for name, mod in sorted(mods.items(), key=lambda kv: kv[1].file):
        ins = sum(p.dir == "in" for p in mod.ports)
        outs = len(mod.ports) - ins
        clocked = "yes" if any(p.name == "clk" for p in mod.ports) else "no"
        rows.append(f"| `{name}` | `{mod.file}` | {clocked} | {ins} / {outs} | [{name}]({name}.md) |")
    return "\n".join(rows)


def main():
    check = "--check" in sys.argv
    mods = load_all()
    stale = []
    if not mdblocks.update(os.path.join(PAGES, "README.md"), {"module-index": module_index(mods)}, check):
        stale.append("README")
    for name, mod in mods.items():
        path = os.path.join(PAGES, name + ".md")
        if not os.path.exists(path):
            continue
        text = open(path).read()
        blocks = {"instantiation": instantiation(mod)}
        if "BEGIN GENERATED: connections" in text:
            blocks["connections"] = connections(mod, mods)
        if not mdblocks.update(path, blocks, check):
            stale.append(name)
    if check and stale:
        print("generated blocks out of date in:", ", ".join(stale),
              "\n  run: make -C docs")
        sys.exit(1)
    print("interfaces: generated blocks " + ("up to date" if check else "written"))


if __name__ == "__main__":
    main()
