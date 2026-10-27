"""The pipeline occupancy table in docs/07_pipeline.md, taken from the RTL.

Assembles sw/tests/sum_array.asm, runs it on adam16_pipe_core under
tb/tb_program.sv with +PIPEVIEW, and tabulates what each stage holds in
every cycle until HALT retires.

    python3 gen_pipeview.py           rewrite the table
    python3 gen_pipeview.py --check   exit 1 if the table is out of date

Needs iverilog.
"""

import os
import subprocess
import sys

import mdblocks
from rtl import ROOT

sys.path.insert(0, os.path.join(ROOT, "sw"))
from asm import assemble_file          # noqa: E402
from isa import HALT_WORD, disasm      # noqa: E402

PAGE = os.path.join(ROOT, "docs", "07_pipeline.md")
PROGRAM = os.path.join(ROOT, "sw", "tests", "sum_array.asm")
OUT = os.path.join(ROOT, "build", "pipeview")
RTL = ["adam16_isa", "adam16_alu", "adam16_regfile", "adam16_pipe_decode",
       "adam16_pipe_core", "adam16_dpram"]


def run():
    os.makedirs(OUT, exist_ok=True)
    a = assemble_file(PROGRAM)
    mem = os.path.join(OUT, "sum_array.mem")
    with open(mem, "w") as f:
        f.write("\n".join(a.mem_lines()) + "\n")
    sim = os.path.join(OUT, "sim")
    srcs = [os.path.join(ROOT, "rtl", m + ".sv") for m in RTL]
    subprocess.run(["iverilog", "-g2012", "-DPIPE", "-o", sim] + srcs +
                   [os.path.join(ROOT, "tb", "tb_program.sv")],
                   check=True, capture_output=True)
    view = os.path.join(OUT, "pipeview.txt")
    r = subprocess.run(["vvp", "-n", sim, f"+MEM={mem}", f"+TRACE={os.path.join(OUT, 'trace')}",
                        f"+PIPEVIEW={view}"], check=True, capture_output=True, text=True)
    cycles = int(r.stdout.split("DONE cycles=")[1].split()[0])
    return [line.split() for line in open(view).read().splitlines()[:cycles]]


def cell(valid, pc, ir, squashed=False):
    if valid != "1":
        return "·"
    pc, ir = int(pc, 16), int(ir, 16)
    text = f"{pc:02X} {disasm(ir, pc)}"
    return f"~~{text}~~" if squashed else text


def table():
    rows = run()
    out = ["| Cycle | IF (address) | ID | EX | MEM | WB |", "|---|---|---|---|---|---|"]
    for n, f in enumerate(rows, 1):
        addr, redirect = int(f[0], 16), f[1] == "1"
        fetch = f"{addr:02X}" + (" ← target" if redirect else "")
        ex = cell(*f[5:8])
        if redirect:
            ex += " **→ redirect**"
        wb = cell(*f[11:14])
        if f[11] == "1" and int(f[13], 16) == HALT_WORD:
            wb += " (retires: end)"
        out.append(f"| {n} | {fetch} | {cell(*f[2:5], squashed=redirect)} | {ex} | "
                   f"{cell(*f[8:11])} | {wb} |")
    return "\n".join(out)


def main():
    check = "--check" in sys.argv
    ok = mdblocks.update(PAGE, {"pipeview": table()}, check)
    if check and not ok:
        print("generated blocks out of date in: 07_pipeline (pipeview)\n  run: make -C docs")
        sys.exit(1)
    print("07_pipeline: pipeline view " + ("up to date" if check else "written"))


if __name__ == "__main__":
    main()
