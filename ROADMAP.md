# Roadmap

**Scope.** cpu16 stays what it is: a 16-bit, LC-3-inspired processor with its own ISA. The goal is to finish it properly. That means fixing the known issues, releasing it as an open-source v1, then building a **pipelined** version that runs the same programs. A RISC-V processor is a separate, later project (see the end); most of the tooling built here carries over to it.

**Ground rules.**
- Every step lands as a small PR with green CI (`make check`).
- The multicycle core stays as the reference. The pipeline is built *beside* it, not on top of it, so there is always a known-good core to compare against.
- Docs come first: each block gets its interface sheet and diagrams before or with its RTL, and the existing checkers keep them honest.

Sizes are relative: **S** fits in one sitting, **M** in a few, **L** is a project in itself.

---

## Phase 0: Foundation ✅ (this PR)

| | Item | Notes |
|---|---|---|
| ✅ | CI on every push and PR | `.github/workflows/ci.yml` runs `make check` |
| ✅ | Root `Makefile` | `make test`, `lint`, `check`, `wave`, `docs` |
| ✅ | RTL lint-clean under Verilator `-Wall` | Behaviour unchanged: same testbench, same FSM conformance and debounce results |
| ✅ | Remove committed editor swap files | `*.swp` now ignored |
| ✅ | This roadmap | |

---

## Phase 1: Finish and release v1 (multicycle)

### 1a. Tooling that everything after this depends on

| Size | Item | Why |
|---|---|---|
| M | **Assembler** (`sw/asm`): two-pass, labels, `.org`/`.word`, outputs `.mem`. Port the 16 tests and `sum_array` from hand-written hex to assembly. | Hand-encoding hex doesn't scale to the hundreds of hazard tests a pipeline needs |
| M | **Instruction-set simulator** (`sw/iss`): Python golden model of the ISA. Tests check final state against it instead of hand-written expectations. | One executable definition of the ISA, separate from the RTL |
| S | **Retire port** on the core (`retire_valid`, PC, IR, register write, memory write, flags) plus a testbench monitor that logs it | Lets the RTL be compared with the ISS instruction by instruction, on any core |
| M | **Random differential testing**: generate random valid programs, run them on the ISS and the RTL, and compare retire traces. Runs in CI. | Finds the bugs nobody thought to write a test for. This is the safety net for the pipeline |

### 1b. Fix the known issues ([docs/06_known_issues.md](docs/06_known_issues.md))

| Size | Item | Verified by |
|---|---|---|
| S | **CMP overflow**: implement the option you choose (decision 3 below), with tests at the overflow boundaries | ISS + directed tests |
| S | **Register file 3R → 2R**: mux port 1's address between `IR[5:3]`, `IR[11:9]` and R7, delete port 2 | Existing tests + FSM spec update + random tests |
| M | **Basys3 clock enable**: run everything on the 100 MHz clock, step = clock enable, no logic-generated clock. Constrain and time it in Vivado. | Simulation here; **you** verify on the board (demo.md press counts must not change) |
| M | **Vivado project from a Tcl script** (`fpga/build.tcl`) instead of the committed `.xpr`. Fixes: the `.xpr` points at `constraints/basys3.xdc`, but the repo has `adam16.xdc`; it has an empty block design and a stale `.dcp`; the memory image path is absolute (`C:/Users/...`). Rename `Sram.sv` → `SramSBC.sv` while at it. | **You** run it in Vivado 2025.2 and program the board |
| S | **ASIC flow paths**: `scripts/adam16.dc` and `adam16_sim.do` hard-code `/userspace/...`; take them from environment variables | You, on the machine with SAED32 |
| S | **Gate-level testbench**: re-run after the RTL changes; align its halt condition with the RTL testbench | You (needs SAED32) |
| S | **Open-source synthesis check in CI**: Yosys (`synth_xilinx`, resource counts). Today's Yosys 0.33 can't parse the struct-typed local in `cpu16_isa::decode()`; either convert with `sv2v` or restructure `decode()` | CI |

### 1c. Release v1.0

| Size | Item |
|---|---|
| S | `LICENSE` (decision 1), short `CONTRIBUTING.md`, `CHANGELOG.md` |
| S | README "quick start": clone → `make check` → program the Basys3 |
| S | Tag `v1.0.0`, GitHub release with the bitstream and the `sum_array` image |

---

## Phase 2: Pipelined core (v2)

A classic 5-stage in-order pipeline, **IF → ID → EX → MEM → WB**, running the same ISA and the same programs as v1.

**Proposed design.** This is a starting point for the spec document in 2.1, not final.

| Topic | Proposal | Why |
|---|---|---|
| Memory | Split instruction and data ports on one **true dual-port** block RAM (the Basys3 BRAM supports this): port A fetches, port B serves loads and stores | Removes the fetch/memory structural hazard; still one unified memory, so programs don't change |
| Fetch | The BRAM's registered output *is* the IF/ID instruction register; next-PC drives the address directly | Synchronous BRAM read latency is absorbed by the pipeline, unlike the 3-cycle fetch today |
| Register file | 2 read ports (from 1b) + write-first bypass, so WB→ID needs no stall | Classic |
| Data hazards | Forward EX/MEM and MEM/WB results into EX; 1-cycle stall for load-use | Classic |
| Flags (N/Z/P) | Update at the end of EX. Branches resolve in EX, so `CMP` → `BRx` needs no special forwarding: the flags are already written when the branch reaches EX. Wrong-path instructions never reach EX, so they never write flags | The ISA's hidden-register hazard becomes free |
| Control hazards | Predict not-taken; BR/JMP/JSR/RET/TRAP resolve in EX and flush 2 instructions when taken. JSR/TRAP write R7 in WB like any other result | Simple and correct first. Branch prediction is an optional extra |
| Observability | Same retire port as v1; performance counters (cycles, retired, stalls, flushes) | Differential testing against the ISS and v1; measured CPI |

**Estimated payoff.** `sum_array` takes 191 cycles today (CPI 5.46). Counting stages for the design above gives about 50 cycles (CPI ≈ 1.5): the loop pays one load-use stall and, when taken, a 2-cycle branch flush per iteration. That is an estimate to be replaced by a measurement in 2.7.

| Step | Size | Item |
|---|---|---|
| 2.1 | M | **Pipeline spec** in `docs/`: stage diagram, per-stage register contents, hazard and forwarding tables, flush/stall rules, interface sheets for the new modules. Review it before any RTL |
| 2.2 | M | Dual-port memory model + core with separate instruction/data ports; Basys3 top that can build either core |
| 2.3 | M | Pipeline with **no** hazard handling; tests use NOP-padded programs. Proves the stages and the datapath |
| 2.4 | M | Forwarding (EX/MEM, MEM/WB → EX) + register-file bypass |
| 2.5 | S | Load-use stall |
| 2.6 | M | Control hazards: flush on taken branches and jumps, R7 linking |
| 2.7 | M | Directed hazard tests (every producer/consumer distance 1–3, loads, flags, R7) + random differential testing against the ISS and v1 in CI; CPI report |
| 2.8 | M | Basys3: 100 MHz timing closure, resource report, demo update; tag `v2.0.0` |
| 2.9 | S | Optional: resolve branches in ID (1-bubble penalty) or add a small predictor, measured against 2.7's CPI baseline |

The three multicycle speed-ups (A–C) analysed in [execution timing](docs/05_timing.md#where-the-cycles-go) are superseded by the pipeline, so they are not planned for v1.

---

## Decisions I need from you

| # | Decision | Options | My recommendation |
|---|---|---|---|
| 1 | **License** | MIT · Apache-2.0 · Solderpad 2.1 (Apache-based, written for hardware; used by lowRISC / OpenHW) · CERN-OHL-P/W/S | **MIT** if you want the simplest, best-known terms. **Apache-2.0 / Solderpad** if you want an explicit patent grant |
| 2 | **Project name** | `cpu16` (README, RTL) vs `adam16` (scripts, constraints, Vivado project) | Pick one before the v1 tag. The repo name and docs should match |
| 3 | **CMP fix** | (a) CMP sets N/Z/P from the true signed comparison of SR1 and SR2; no encoding change, SUB unchanged · (b) add a V flag and new branch conditions; encoding change · (c) document the limitation | **(a)**: fixes the real-world case (signed compares) without touching the encoding |
| 4 | **Pipeline vs multicycle** | Keep both cores (recommended) · replace the multicycle core | **Keep both**: v1 is the reference model and the simple teaching design |
| 5 | **ISA freeze** | Freeze the ISA at v1 (with the CMP fix) · allow changes for v2 (e.g. drop RET as an alias of `JMP R7`, add HALT or immediate shifts) | **Freeze** for v2, so the same binaries run on both cores and differential testing stays trivial. Collect ISA ideas for the RISC-V project instead |
| 6 | **ASIC flow** | Keep maintaining the DC/ICC2 scripts (you have SAED32) · add an open flow later (Yosys + OpenROAD on sky130) · drop it | Keep yours working (paths fix in 1b); revisit an open flow after v2 |

---

## Phase 3: After v2 — the RISC-V project (separate repo)

What carries over directly:
- **Repo skeleton**: `Makefile` targets, CI, lint-clean policy.
- **Docs tooling**: interface sheets with RTL-generated symbols and checked port tables; spec-driven FSM bubble diagrams with an RTL conformance testbench.
- **Verification approach**: retire port + golden-model differential testing. For RISC-V the golden model is Spike, plus the official `riscv-arch-test` suite, and later `riscv-formal`.
- **The pipeline** itself: the hazard design from Phase 2 maps almost one-to-one onto RV32I.

A good first milestone there: RV32I, 5-stage, passing `riscv-arch-test` in simulation and running on the same Basys3.
