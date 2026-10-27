# 8. Verification

`make check` runs everything below except the gate-level run of a real netlist, and CI runs it on every push. Each layer catches a different kind of mistake.

| Layer | What it checks | Run |
|---|---|---|
| **Differential regression** | Every program in `sw/tests/` plus 200 random programs, on the ISS and on both cores. The retire traces must match instruction for instruction, and each directed program's expectations must hold | `make regress` |
| Directed testbench | `tb/tb_adam16.sv`: 17 tests, 47 checks on the multicycle core, including registers the programs don't store | `make test` |
| FSM conformance | `adam16_control_fsm` against `docs/tools/fsm_spec.py`, the source of the bubble diagrams: every opcode × field × flag combination, every cycle (8192 instructions) | `make -C docs check` |
| Decoder conformance | `adam16_pipe_decode` against `docs/tools/pipe_decode_spec.py`, the source of the decode table: all 65536 instruction words | `make -C docs check` |
| Board demo | `tb/tb_basys3.sv`: `basys3_top` with each core, buttons pressed as [`demo.md`](../demo.md) says, LEDs checked at the press counts it gives | `make demo` |
| Black-box testbench | `tb/tb_adam16_gate.sv` on the RTL of each core. It uses only ports and memory, so it can run unchanged on a netlist | `make gate-rtl` |
| Lint | Verilator `-Wall`, both cores and `basys3_top` with each core | `make lint` |
| Documentation | Port tables, generated blocks and links match the RTL | `make -C docs check` |

## The ISS and the retire trace

`sw/iss.py` is the golden model of the ISA: a few lines of Python per instruction, written from `InstructionSet.txt` and not from the RTL. It runs a program from reset until it fetches `TRAP x025` (HALT) and records one line per executed instruction:

```
pc   ir   reg_we reg_addr reg_data  mem_we mem_addr mem_data  nzp
0004 06e0 1      3        0001      0      0000     0000      001
```

Fields an instruction doesn't use are zero; `nzp` is the flags after it. `tb/tb_program.sv` writes the same record from the RTL as each instruction retires:

- **Pipelined core:** the core carries every field down to WB itself (`rt_*` signals, see [chapter 7](07_pipeline.md#retire-record)).
- **Multicycle core:** the testbench rebuilds the record from the FSM and the datapath in the cycle whose edge returns the FSM to `S_IF0`.

`sw/regress.py` compares the records line by line and reports the first difference with a disassembly:

```
alu_ops   FAIL
    multi: trace differs from the ISS at retire #29: ASR1 R3, R4 @ 0x001D
            iss 001d 1706 1 3 fffe 0 0000 0000 100
            rtl 001d 1706 1 3 7ffe 0 0000 0000 001
```

It also compares the final registers, and fails a run that doesn't reach HALT within 8 cycles per instruction.

## Test programs

`sw/tests/*.asm` are written in the assembler's syntax (`sw/asm.py` documents it). Lines starting `;!` are expectations, checked against the ISS's final state, so they test the ISS and the program as well as the RTL:

```
;! R3 == 15
;! M[0x0010] == 15
;! NZP == 001
```

| Program | Covers |
|---|---|
| `alu_ops` | All 16 ALU operations, R0 as an ordinary register, flags |
| `immediates` | ADDI's sign extension and ANDI's zero extension, at their limits |
| `cmp_signed` | Signed CMP, including the cases where `SR1 − SR2` overflows |
| `branches` | Every `n z p` mask, taken and not taken, NOP, the reset flags |
| `memory` | LD, ST, LDR, STR with negative offsets, LEA; loads leave the flags alone |
| `calls` | JSR, JSRR (including `JSRR R7`), RET, nested calls through a saved R7, TRAP |
| `jumps_undef` | JMP, undefined opcodes 0xE and 0xF |
| `hazards` | Back-to-back dependences at distance 1, 2, 3; load-use; store after load; CMP → BR; JSR → RET |
| `squash` | The instruction behind each kind of taken branch or jump would write a register, flags or memory; none may happen |
| `sum_array` | The demo program |

`sw/randprog.py` generates random programs that always halt: control flow only goes forward, except counted loops whose counter nothing else in the loop writes; stores only reach a data block, so no program changes its own code. Operands favour registers written in the last few instructions, so most programs are dense with hazards. Each program calls a subroutine, a TRAP handler, jumps through registers and runs short loops. `make regress SEED=… RANDOM_N=…` picks the programs. A failing program's files stay in `build/regress/` (`.asm`, `.lst`, `.iss`, `.multi`, `.pipe`) for debugging.

## Does the regression catch real bugs?

During development, bugs were planted in the RTL one at a time, and the regression run against each. Every one was caught:

| Planted bug | Directed programs that fail | Random programs that fail (seeds 1–150) |
|---|---|---|
| `ASR1` shifts in a 0 (multicycle ALU) | `alu_ops` | 64 |
| No MEM → EX forwarding (operand a) | 9 of 10 | 149 |
| No WB → EX forwarding (operand b) | `calls`, `hazards` | 145 |
| WB forwarding takes priority over MEM | `hazards` | 130 |
| Load data not forwarded from MEM (the stale ALU value instead) | `sum_array`, `hazards`, `memory`, `calls`, `cmp_signed`, `squash` | 150 |
| Instruction behind a redirect not squashed | `squash`, `branches`, `calls`, `hazards`, `jumps_undef`, `sum_array` | 150 |
| Forwarding from a squashed instruction | `calls` | 91 |
| Register file not write-first | 8 of 10 | 150 |
| A squashed instruction still sets the flags | `squash`, `branches`, `calls`, `hazards` | 149 |
| A squashed store still writes memory | `squash` (it reads the word back) | 10 |

A wrong store that no later instruction reads is invisible to the comparison, because memory isn't compared at the end. `squash.asm` reads back the words its shadow stores target for that reason.

## Gate level

`scripts/adam16.dc` synthesizes either core with Design Compiler, and `scripts/adam16_sim.do` simulates the netlist in Questa with `tb/tb_adam16_gate.sv`:

```bash
ADAM16_TOP=adam16_pipe_core dc_shell -f scripts/adam16.dc | tee synth.log
ADAM16_TOP=adam16_pipe_core ADAM16_CELLS=<cell models>.v vsim -c -do scripts/adam16_sim.do
```

The testbench only uses the core's ports and the memory outside it, so the netlist's internal names don't matter. It ends each program when `dbg_ir` shows HALT, then checks the words the program stored. `make gate-rtl` runs it on the RTL in CI, so a failure on a netlist points at the netlist, not the testbench.
