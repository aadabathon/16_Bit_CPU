"""adam16 regression: every program on the ISS and on each RTL core.

    python3 sw/regress.py                         directed tests, both cores
    python3 sw/regress.py --random 200 --seed 1   200 random programs as well
    python3 sw/regress.py --cores multi sw/tests/calls.asm

For each program:
  1. assemble it (sw/asm.py);
  2. run it on the ISS (sw/iss.py) and check its ';!' expectations against the
     final state, e.g.  ;! R3 == 15   ;! M[0x0010] == 15   ;! NZP == 010
  3. run it on each core under tb/tb_program.sv and require the retire trace
     and the final registers to equal the ISS's, instruction for instruction.

Prints one line per program with the cycle count on each core, then the
totals, and exits 1 if anything failed. Work files go to build/regress/.
"""

import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from asm import AsmError, assemble_file, parse_number
from isa import disasm
from iss import Machine, load_mem
import randprog

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "build", "regress")

RTL = {
    "multi": ["adam16_isa", "adam16_alu", "adam16_regfile", "adam16_datapath",
              "adam16_control_fsm", "adam16_core", "adam16_sram"],
    "pipe": ["adam16_isa", "adam16_alu", "adam16_regfile", "adam16_pipe_decode",
             "adam16_pipe_core", "adam16_dpram"],
}
EXPECT = re.compile(r";!\s*(R[0-7]|M\[[^\]]+\]|NZP)\s*==\s*(\S+)", re.I)
DONE = re.compile(r"DONE cycles=(\d+) instret=(\d+) (.*)")


def build(core):
    exe = os.path.join(OUT, f"sim_{core}")
    srcs = [os.path.join(ROOT, "rtl", m + ".sv") for m in RTL[core]]
    srcs.append(os.path.join(ROOT, "tb", "tb_program.sv"))
    cmd = ["iverilog", "-g2012", "-o", exe] + (["-DPIPE"] if core == "pipe" else []) + srcs
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"iverilog failed for the {core} core:\n{r.stdout}{r.stderr}")
    return exe


def check_expectations(src, m):
    errors = []
    for lhs, rhs in EXPECT.findall(open(src).read()):
        lhs = lhs.upper()
        if lhs == "NZP":
            want, got = int(rhs, 2), m.nzp
            show = lambda v: f"{v:03b}"
        else:
            want = parse_number(rhs) & 0xFFFF
            got = m.r[int(lhs[1])] if lhs[0] == "R" else m.mem[parse_number(lhs[2:-1])]
            show = lambda v: f"0x{v:04X}"
        if got != want:
            errors.append(f"ISS: {lhs} = {show(got)}, expected {show(want)}")
    return errors


def first_difference(iss_lines, rtl_lines):
    for k, (a, b) in enumerate(zip(iss_lines, rtl_lines)):
        if a != b:
            pc, ir = int(a.split()[0], 16), int(a.split()[1], 16)
            return (f"retire #{k}: {disasm(ir, pc)} @ 0x{pc:04X}\n"
                    f"        iss {a}\n        rtl {b}")
    if len(iss_lines) != len(rtl_lines):
        return f"ISS retired {len(iss_lines)} instructions, RTL {len(rtl_lines)}"
    return None


def run_program(src, sims, max_instr):
    """Returns (name, {core: cycles}, instret, [errors])."""
    name = os.path.splitext(os.path.basename(src))[0]
    base = os.path.join(OUT, name)
    try:
        a = assemble_file(src)
    except AsmError as e:
        return name, {}, 0, [f"assembler: {e}"]
    with open(base + ".mem", "w") as f:
        f.write("\n".join(a.mem_lines()) + "\n")
    with open(base + ".lst", "w") as f:
        f.write("\n".join(a.listing()) + "\n")

    m = Machine(load_mem(base + ".mem"))
    try:
        trace = m.run(max_instr)
    except RuntimeError as e:
        return name, {}, 0, [f"ISS: {e}"]
    iss_lines = [rt.line() for rt in trace]
    with open(base + ".iss", "w") as f:
        f.write("".join(s + "\n" for s in iss_lines))
    errors = check_expectations(src, m)
    want_regs = " ".join(f"R{i}={v:04x}" for i, v in enumerate(m.r))

    cycles = {}
    for core, exe in sims.items():
        tr = f"{base}.{core}"
        r = subprocess.run(["vvp", "-n", exe, f"+MEM={base}.mem", f"+TRACE={tr}",
                            f"+MAXCYC={20 * max_instr}"], capture_output=True, text=True)
        done = DONE.search(r.stdout)
        if r.returncode or not done or "TIMEOUT" in r.stdout:
            errors.append(f"{core}: simulation did not finish\n{r.stdout[-400:]}{r.stderr[-400:]}")
            continue
        cycles[core] = int(done.group(1))
        diff = first_difference(iss_lines, open(tr).read().splitlines())
        if diff:
            errors.append(f"{core}: trace differs from the ISS at {diff}")
        elif done.group(3).strip() != want_regs:
            errors.append(f"{core}: final registers {done.group(3).strip()}\n"
                          f"        ISS        {want_regs}")
    return name, cycles, len(trace), errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("programs", nargs="*", help=".asm files (default: sw/tests/*.asm)")
    ap.add_argument("--cores", default="multi,pipe", help="comma-separated: multi, pipe")
    ap.add_argument("--random", type=int, default=0, metavar="N", help="add N random programs")
    ap.add_argument("--seed", type=int, default=1, help="seed of the first random program")
    ap.add_argument("--length", type=int, default=120, help="random program length")
    ap.add_argument("--no-directed", action="store_true", help="skip sw/tests/*.asm")
    ap.add_argument("--max-instr", type=int, default=20000)
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 2)
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    progs = list(args.programs)
    if not progs and not args.no_directed:
        tests = os.path.join(ROOT, "sw", "tests")
        progs = sorted(os.path.join(tests, f) for f in os.listdir(tests) if f.endswith(".asm"))
    for k in range(args.random):
        seed = args.seed + k
        path = os.path.join(OUT, f"rand{seed:05d}.asm")
        with open(path, "w") as f:
            f.write(randprog.generate(seed, args.length))
        progs.append(path)

    cores = [c.strip() for c in args.cores.split(",") if c.strip()]
    for c in cores:
        if c not in RTL:
            sys.exit(f"unknown core {c!r}; choose from {', '.join(RTL)}")
    sims = {c: build(c) for c in cores}

    with ThreadPoolExecutor(args.jobs) as pool:
        results = list(pool.map(lambda p: run_program(p, sims, args.max_instr), progs))

    failed, total_i, total_c = 0, 0, {c: 0 for c in cores}
    head = f"{'program':<14}{'instr':>7}" + "".join(f"{c + ' cyc':>12}{'CPI':>6}" for c in cores)
    print(head)
    for name, cycles, instret, errors in results:
        quiet = name.startswith("rand") and not errors
        if not errors:
            total_i += instret
            for c in cores:
                total_c[c] += cycles[c]
        if not quiet:
            row = f"{name:<14}{instret:>7}"
            for c in cores:
                cyc = cycles.get(c)
                row += f"{cyc:>12}{cyc / max(instret, 1):>6.2f}" if cyc else f"{'-':>12}{'':>6}"
            print(row + ("" if not errors else "   FAIL"))
        for e in errors:
            print("    " + e.replace("\n", "\n    "))
        failed += bool(errors)
    n_rand = sum(os.path.basename(p).startswith("rand") for p in progs)
    if n_rand:
        print(f"({n_rand} random programs, seeds {args.seed}..{args.seed + args.random - 1}; "
              f"only failures are listed)")
    row = f"{'total':<14}{total_i:>7}"
    for c in cores:
        row += f"{total_c[c]:>12}{total_c[c] / max(total_i, 1):>6.2f}"
    print(row)
    if failed:
        print(f"REGRESSION FAILED: {failed} of {len(results)} programs")
        sys.exit(1)
    print(f"REGRESSION PASSED: {len(results)} programs on {', '.join(cores)}")


if __name__ == "__main__":
    main()
