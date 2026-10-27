# Roadmap: final status

adam16 is finished. This page records what was planned, what was done, and where the result differs from the plan. The ISA is frozen; the RTL is not expected to change again.

## Decisions

| # | Decision | Chosen |
|---|---|---|
| 1 | License | **MIT** ([LICENSE](LICENSE)) |
| 2 | Project name | **adam16** everywhere: RTL, scripts, constraints, docs |
| 3 | CMP | **True signed comparison** of SR1 and SR2, no encoding change |
| 4 | Cores | **Keep both**: the multicycle core as the simple reference, the pipeline beside it |
| 5 | ISA | **Frozen**, so the same programs run on the ISS and both cores |
| 6 | ASIC flow | Keep the Design Compiler / Questa scripts working, with paths from environment variables |

## Phase 0: Foundation ✅

| Item | Result |
|---|---|
| CI on every push and PR | `.github/workflows/ci.yml` runs `make check` |
| Root `Makefile` | `test`, `regress`, `demo`, `gate-rtl`, `lint`, `docs`, `check`, `wave`, `fpga` |
| Verilator `-Wall` clean | Every top and configuration |

## Phase 1: Finish the multicycle core ✅

| Item | Result |
|---|---|
| Assembler | `sw/asm.py`: two passes, labels, `.org` / `.word` / `.space`, `HALT`, `NOP`, range checks, listing |
| Instruction-set simulator | `sw/iss.py`, the golden model, written from `InstructionSet.txt` |
| Retire trace | Same format from the ISS and from `tb/tb_program.sv` for both cores. The plan said a retire *port*; it became internal signals (pipeline) and a testbench reconstruction (multicycle), so neither core gained ports that synthesis would keep |
| Random differential testing in CI | `sw/randprog.py` + `sw/regress.py`: 200 random programs per CI run, 2000 checked during development |
| CMP overflow | Fixed: signed three-way compare in the ALU |
| Register file 3R → 2R | Done, with the FSM spec and diagrams updated |
| Basys3 clock enable | Done: one 100 MHz clock, the step is a clock enable. `make demo` checks every press count in `demo.md` in simulation, for both cores |
| Vivado from a Tcl script | `fpga/build.tcl`, project-free; the old `.xpr`, empty block design and stale checkpoint are gone; the memory image path is relative |
| ASIC flow paths | `scripts/adam16.dc` and `scripts/adam16_sim.do` take the top, library and netlist from environment variables, for either core |
| Gate-level testbench | Rewritten black-box (ports and memory only), for either core, and run on the RTL in CI (`make gate-rtl`) |
| Open-source synthesis check | **Dropped.** Yosys 0.33 can't parse the ISA package, and converting it wasn't worth it for a finished design |
| LICENSE, CONTRIBUTING, CHANGELOG, README quick start | Done |

## Phase 2: Pipelined core ✅

| Item | Result |
|---|---|
| Spec and docs | [docs/07_pipeline.md](docs/07_pipeline.md): block diagram, stages, hazards, decode table, a cycle-by-cycle table taken from simulation, critical paths; interface sheets for the three new modules |
| Dual-port memory, separate fetch / data ports | `adam16_dpram`; `basys3_top` builds either core (`PIPELINED`) |
| Forwarding and register-file bypass | MEM → EX and WB → EX, write-first register file |
| Load-use | **No stall.** The plan expected one. The data port's address goes out in EX, so the loaded word is ready in MEM and is forwarded like an ALU result |
| Control hazards | Resolved in EX with the fetch redirected in the same cycle: **one** bubble per taken branch or jump, against the two planned |
| Directed hazard tests + random differential testing | `sw/tests/hazards.asm`, `squash.asm` and the rest; random programs on both cores in CI |
| Decoder | `adam16_pipe_decode`, checked against its spec for all 65536 instruction words |
| Measured | `sum_array`: **43 cycles** (the plan estimated about 50) against 191; 2000 random programs: CPI 1.16 against 5.55 |
| Optional branch prediction | Not done. With one bubble per taken branch there is little left to win |

## Left for you

These need tools or hardware this repository's CI doesn't have:

1. **Board:** `make fpga`, program the Basys3, and walk through [`demo.md`](demo.md). Look at `build/fpga/pipe/timing.rpt` for the pipeline's real timing.
2. **ASIC:** run `scripts/adam16.dc` for each core with SAED32, then `scripts/adam16_sim.do` on the netlists, then place and route.
3. **Release:** after merging, tag `v1.0.0` (the multicycle core, with the fixes) and `v2.0.0` (the pipeline), or a single `v2.0.0` for both, and attach the bitstreams.
