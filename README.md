# adam16

[![CI](https://github.com/aadabathon/16_Bit_CPU/actions/workflows/ci.yml/badge.svg)](https://github.com/aadabathon/16_Bit_CPU/actions/workflows/ci.yml)

A 16-bit processor in SystemVerilog, with two implementations of one frozen instruction set:

- **`adam16_core`**: multicycle. A 14-state controller and a classic datapath on one single-port memory, 5–8 cycles per instruction.
- **`adam16_pipe_core`**: five-stage pipeline (IF ID EX MEM WB) on one dual-port memory. Full forwarding, no stalls, one bubble per taken branch: about 1.2 cycles per instruction.

The ISA is loosely based on LC-3, with deliberate departures: two ALU opcode groups giving 16 operations, a signed CMP, loads that leave the flags alone, and TRAP as a direct jump. The repository also has an assembler, an instruction-set simulator, a regression that runs every program on the ISS and both cores and compares them instruction by instruction, a Basys3 FPGA build, and Design Compiler scripts.

**Documentation:** [`docs/`](docs/README.md) has block diagrams, bubble diagrams, an interface sheet for every module, the pipeline chapter and the verification plan. Most of it is generated from the RTL or checked against it by `make check`.

---

## Quick start

You need Icarus Verilog, Verilator, Python 3 and Graphviz. On Ubuntu: `sudo apt install iverilog verilator graphviz`.

```bash
make check                                   # everything CI runs

python3 sw/asm.py sw/tests/sum_array.asm -o build/sum.mem -l build/sum.lst
python3 sw/iss.py build/sum.mem              # instruction count and final registers
python3 sw/regress.py sw/tests/sum_array.asm # ISS vs both cores: 191 vs 43 cycles
```

| Command | What it does |
|---|---|
| `make test` | Directed testbench on the multicycle core (`tb/tb_adam16.sv`, 47 checks) |
| `make regress` | Every program in `sw/tests/` plus 200 random programs, on the ISS and both cores; retire traces compared (`SEED=`, `RANDOM_N=`, `CORES=`) |
| `make demo` | The Basys3 demo in simulation for both cores: checks the press counts in [`demo.md`](demo.md) |
| `make gate-rtl` | The black-box gate-level testbench, run on the RTL of both cores |
| `make lint` | Verilator, all warnings, every top and configuration |
| `make check` | All of the above plus the documentation checks. CI runs it on every push |
| `make docs` | Regenerate the documentation figures and tables (the timing diagrams also need the WaveDrom CLI) |
| `make wave` | Directed testbench with a VCD dump at `build/adam16.vcd`, for GTKWave |
| `make fpga` | Basys3 bitstream with Vivado (`FPGA_CORE=pipe` or `multi`) |

Icarus prints some `sorry: constant selects in always_* processes` notes; they are harmless, and the Makefile filters them out.

---

## Architecture at a glance

| Property | Value |
|---|---|
| Data width | 16 bits |
| Address space | 64 K words, word-addressed, instructions and data in one space |
| Registers | R0–R7 (R7 is the link register for JSR / TRAP; R0 is an ordinary register) |
| Condition flags | N, Z, P; exactly one is set; reset leaves Z |
| Instructions | 16 bits, fixed fields, 4-bit opcode, 14 opcodes + 2 reserved |

| | `adam16_core` | `adam16_pipe_core` |
|---|---|---|
| Organization | multicycle FSM + datapath | 5-stage pipeline |
| Memory | `adam16_sram`: 1 port, registered read | `adam16_dpram`: fetch port + data port, registered reads |
| ALU, branch, jump, call, TRAP | 5 cycles | 1 cycle (+1 if it redirects) |
| Store / load | 6 / 8 cycles | 1 cycle |
| `sum_array` (35 instructions) | 191 cycles | 43 cycles |
| 2000 random programs | CPI 5.55 | CPI 1.16 |

```
basys3_top                     FPGA wrapper: debounced buttons, single-step clock enable, LED view
├── PIPELINED = 1 (default)
│   ├── adam16_pipe_core       5-stage pipeline
│   │   ├── adam16_pipe_decode    ID-stage decoder
│   │   ├── adam16_regfile        8 x 16, 2R / 1W, write-first (BYPASS = 1)
│   │   └── adam16_alu            16 operations
│   └── adam16_dpram           64K x 16, dual port
└── PIPELINED = 0
    ├── adam16_core            multicycle
    │   ├── adam16_control_fsm    14-state controller; the only opcode decoder
    │   └── adam16_datapath       PC, IR, MAR, MDR, flags, muxes
    │       ├── adam16_regfile    8 x 16, 2R / 1W (BYPASS = 0)
    │       └── adam16_alu
    └── adam16_sram            64K x 16, single port

adam16_isa                     package: opcode / funct enums, decode(), sign / zero extend
```

![adam16_pipe_core block diagram](docs/figures/pipeline.svg)

Both cores have a clock enable (`ce`), a synchronous active-high reset, and the same debug outputs. The pipeline is described in [docs/07_pipeline.md](docs/07_pipeline.md), the multicycle core in [docs/02_datapath.md](docs/02_datapath.md) and [docs/03_control.md](docs/03_control.md).

---

## Instruction Set Reference

### General Encoding

```
 15    12 11    9  8     6  5     3  2     0
┌────────┬───────┬────────┬────────┬────────┐
│ opcode │  DR   │  SR1   │  SR2   │ funct  │  ← ALU instructions
└────────┴───────┴────────┴────────┴────────┘

┌────────┬───────┬────────┬──────────────────┐
│ opcode │  DR   │  SR1   │      imm6        │  ← ADDI / ANDI
└────────┴───────┴────────┴──────────────────┘

┌────────┬───────┬──────────────────────────┐
│ opcode │ DR/SR │          Offset9         │  ← LD / ST / BRx / LEA
└────────┴───────┴──────────────────────────┘

┌────────┬───┬───────────────────────────────┐
│ opcode │ j │         PCoffset11            │  ← JSR (j=0) / JSRR (j=1)
└────────┴───┴───────────────────────────────┘

┌────────┬──────────────────────────────────┐
│ opcode │          TrapVector12            │  ← TRAP
└────────┴──────────────────────────────────┘
```

**BaseR** (for JMP, LDR, STR, JSRR) always occupies bits [8:6] — the same slot as SR1 — so the SR1 read port is reused with no extra mux.

---

### ALU Group 0 — opcode `0000`

All ALU0 operations write condition flags {N, Z, P}.

| Mnemonic | funct | Operation |
|---|---|---|
| `ADD DR, SR1, SR2` | `000` | DR ← SR1 + SR2 |
| `SUB DR, SR1, SR2` | `001` | DR ← SR1 − SR2 |
| `NOT DR, SR1` | `010` | DR ← ~SR1 |
| `AND DR, SR1, SR2` | `011` | DR ← SR1 & SR2 |
| `OR  DR, SR1, SR2` | `100` | DR ← SR1 \| SR2 |
| `XOR DR, SR1, SR2` | `101` | DR ← SR1 ^ SR2 |
| `MOV DR, SR1` | `110` | DR ← SR1 |
| `NEG DR, SR1` | `111` | DR ← 0 − SR1 (two's complement negate) |

### ALU Group 1 — opcode `0001`

All ALU1 operations that produce a result write condition flags. CMP writes flags only (no register writeback). It is a true signed comparison, so it is correct even where `SR1 − SR2` would overflow (e.g. `0x7FFF` vs `0x8000` gives P).

| Mnemonic | funct | Operation |
|---|---|---|
| `NAND DR, SR1, SR2` | `000` | DR ← ~(SR1 & SR2) |
| `NOR  DR, SR1, SR2` | `001` | DR ← ~(SR1 \| SR2) |
| `INC  DR, SR1` | `010` | DR ← SR1 + 1 |
| `DEC  DR, SR1` | `011` | DR ← SR1 − 1 |
| `LSL1 DR, SR1` | `100` | DR ← SR1 << 1 |
| `LSR1 DR, SR1` | `101` | DR ← SR1 >> 1 (logical, fills 0) |
| `ASR1 DR, SR1` | `110` | DR ← SR1 >>> 1 (arithmetic, fills MSB) |
| `CMP  SR1, SR2` | `111` | signed compare: N if SR1 < SR2, Z if equal, P if SR1 > SR2 ; no writeback |

### Immediate Instructions

| Mnemonic | Opcode | Operation |
|---|---|---|
| `ADDI DR, SR1, imm6` | `0010` | DR ← SR1 + SEXT(imm6) ; imm6 range −32..+31 |
| `ANDI DR, SR1, imm6` | `0011` | DR ← SR1 & ZEXT(imm6) ; imm6 range 0..63 |

### Memory Instructions

† **PC†** denotes the incremented PC — the address of the instruction immediately following the one being executed. Memory is word-addressed.

| Mnemonic | Opcode | Operation |
|---|---|---|
| `LD  DR, off9`         | `0100` | DR ← mem\[PC† + SEXT(off9)\] |
| `ST  SR, off9`         | `0101` | mem\[PC† + SEXT(off9)\] ← SR |
| `LDR DR, BaseR, off6`  | `1010` | DR ← mem\[BaseR + SEXT(off6)\] |
| `STR SR, BaseR, off6`  | `1011` | mem\[BaseR + SEXT(off6)\] ← SR |
| `LEA DR, off9`         | `1100` | DR ← PC† + SEXT(off9) (address only; **no flag write**) |

> **Flag note:** LD, LDR, and LEA do **not** modify condition flags. This is an intentional departure from LC-3, where LD/LDR do set flags.

### Control-Flow Instructions

| Mnemonic | Opcode | Operation |
|---|---|---|
| `BRx  off9`   | `1101` | if (nzp\_mask & {N,Z,P} ≠ 0) PC ← PC† + SEXT(off9) |
| `JMP  BaseR`  | `0110` | PC ← BaseR |
| `JSR  off11`  | `0111` (bit 11 = 0) | R7 ← PC† ; PC ← PC† + SEXT(off11) |
| `JSRR BaseR`  | `0111` (bit 11 = 1) | R7 ← PC† ; PC ← BaseR |
| `RET`         | `1000` | PC ← R7 |
| `TRAP tvect12`| `1001` | R7 ← PC† ; PC ← ZEXT(tvect12) |

> **TRAP note:** TRAP is a *direct* jump — the vector is the handler address itself, not an index into a vector table as in LC-3. Handlers therefore live in `0x0000–0x0FFF`. `TRAP x025` is the HALT convention: the testbenches, the ISS and the assembler's `HALT` use it, but the hardware just jumps to `0x0025`.

**BRx condition codes** — IR[11:9] selects which flags trigger the branch:

| Mnemonic | IR[11:9] | Branches when |
|---|---|---|
| `BRn` | `100` | N = 1 (result was negative) |
| `BRz` | `010` | Z = 1 (result was zero) |
| `BRp` | `001` | P = 1 (result was positive) |
| `BRnz` | `110` | N = 1 or Z = 1 (result ≤ 0) |
| `BRnp` | `101` | N = 1 or P = 1 (result ≠ 0) |
| `BRzp` | `011` | Z = 1 or P = 1 (result ≥ 0) |
| `BR` / `BRnzp` | `111` | always (unconditional) |
| `NOP` | `000` | never (the assembler's `NOP`, `0xD000`) |

Reset leaves the flags at **Z = 1** (N = P = 0), so exactly one flag is always set and `BRnzp` is unconditional even before the first flag-setting instruction.

### Undefined Opcodes

Opcodes `1110` and `1111` are reserved. Both cores treat them as no-ops.

---

## Software

| Tool | What it does |
|---|---|
| [`sw/asm.py`](sw/asm.py) | Two-pass assembler: labels, `.org`, `.word`, `.space`, `HALT`, `NOP`, PC-relative label operands, range checks. Writes a `$readmemh` image and a listing |
| [`sw/iss.py`](sw/iss.py) | Instruction-set simulator: the golden model. Writes a retire trace in the same format as the RTL testbench |
| [`sw/regress.py`](sw/regress.py) | Assembles, runs the ISS, checks each test's `;!` expectations, runs both cores, compares traces and final registers |
| [`sw/randprog.py`](sw/randprog.py) | Random programs that always halt, dense with pipeline hazards |
| [`sw/tests/`](sw/tests) | Directed programs: every operation, branch mask, call form, memory mode, signed CMP, hazard patterns, squashing |

The assembler's syntax is in the docstring at the top of `sw/asm.py`. An example, the program the FPGA demo runs:

```asm
; sum_array: sum mem[0x000B..0x000F] = 1+2+3+4+5 = 15, store the result at 0x0010.
;! R3 == 15
;! M[0x0010] == 15

        LEA  R1, data       ; R1 = 0x000B
        ADDI R2, R0, 5
        MOV  R3, R0         ; R3 = 0
loop:   LDR  R4, R1, 0
        ADD  R3, R3, R4
        INC  R1, R1
        DEC  R2, R2
        CMP  R2, R0
        BRp  loop
        ST   R3, result
        HALT
data:   .word 1, 2, 3, 4, 5
result: .space 1
```

---

## Verification

`make check` runs it all, and CI runs `make check` on every push. Details are in [docs/08_verification.md](docs/08_verification.md).

- **Differential:** the ISS and both cores run the same programs, and every retired instruction must match: PC, instruction, register write, memory write, flags. 10 directed programs and 200 random ones per run. 2000 random programs pass.
- **Exhaustive conformance:** the multicycle controller against the spec its bubble diagrams are drawn from (8192 instruction / flag cases, every cycle), and the pipeline decoder against its spec (all 65536 instruction words).
- **Directed:** 47 checks in `tb/tb_adam16.sv`; the board demo in `tb/tb_basys3.sv`; a black-box testbench for netlists, `tb/tb_adam16_gate.sv`, proven on the RTL.
- **Lint:** Verilator `-Wall` on every top and configuration, with no warnings.

Planted bugs (missing forwarding paths, no squash, wrong forwarding priority, a broken shifter, …) were each caught by the regression.

---

## FPGA and ASIC

- **Basys3:** `make fpga` (or `vivado -mode batch -source fpga/build.tcl`) builds the bitstream without a project. One 100 MHz clock; the step button is a clock enable. Walkthrough: [`demo.md`](demo.md).
- **ASIC:** `scripts/adam16.dc` synthesizes either core with Design Compiler (`ADAM16_TOP=adam16_pipe_core`, library path from `ADAM16_LIBDIR`), and `scripts/adam16_sim.do` runs the netlist in Questa with the black-box testbench. The memory stays outside the core.

Neither flow runs in CI ([known issues](docs/06_known_issues.md#3-synthesis-was-not-run-here)).

---

## Repository layout

```
16_Bit_CPU/
├── rtl/                     SystemVerilog: both cores, memories, Basys3 wrapper
├── tb/                      Testbenches: directed, program runner, conformance, board, gate level
├── sw/                      Assembler, ISS, regression, random programs, test programs
├── docs/                    Documentation, figures, and the tools that generate and check them
├── fpga/                    build.tcl, constraints, the demo's memory image
├── scripts/                 Design Compiler and gate-level simulation scripts
├── .github/workflows/ci.yml CI: make check
├── Makefile
├── InstructionSet.txt       The ISA as originally specified
├── demo.md                  Basys3 walkthrough
├── ROADMAP.md               What was planned, and what was done
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE                  MIT
```

## License

MIT. See [LICENSE](LICENSE).
