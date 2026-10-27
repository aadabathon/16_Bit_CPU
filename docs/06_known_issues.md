# 6. Known issues and design choices

Numbered entries are real limitations. The last section lists deliberate design choices that are easy to trip over. The ISA is frozen, so anything that would change it is out of scope.

## 1. The pipeline doesn't see a store to the next two instruction words

When a store is in EX, `adam16_pipe_core` has already fetched the two instructions after it. A store to either of those words doesn't affect them. The multicycle core and the ISS do see the new word. Self-modifying code works on the pipeline if at least three instructions separate the store from the code it changes. No program in this repository modifies its own code. ([Details](07_pipeline.md#what-the-pipeline-does-not-do).)

## 2. The pipeline's longest paths are long

The pipeline never stalls, so its EX stage carries long combinational chains: memory read register → forwarding → ALU → memory address, and flags → branch unit → fetch address ([timing](07_pipeline.md#timing)). They limit f<sub>max</sub> if the core runs free. They don't matter for the step demo, where the enable is never high on consecutive cycles. Each can be shortened by one cycle at a cost, and the [timing section](07_pipeline.md#timing) lists both options. No synthesis results are recorded here: run `make fpga` for Vivado's numbers, or `scripts/adam16.dc` for an ASIC library.

## 3. Synthesis was not run here

`fpga/build.tcl`, `scripts/adam16.dc` and `scripts/adam16_sim.do` need Vivado, Design Compiler and Questa with a cell library, none of which this repository's CI has. The RTL they read is linted and simulated in CI, and `make gate-rtl` runs the black-box gate-level testbench on the RTL of both cores. A first real run may still turn up tool-specific issues.

Yosys 0.33, the version in Ubuntu 24.04, can't parse the `adam16_isa` package (its struct-returning `decode()`, among other constructs), so there is no open-source synthesis check.

## Fixed

| Was | Fix |
|---|---|
| CMP set the flags from the 16-bit `SR1 − SR2`, so it gave the wrong answer when the subtraction overflowed (`0x7FFF` vs `0x8000` set N) | CMP is now a signed three-way compare in the ALU (−1 / 0 / +1). Test T17 and `sw/tests/cmp_signed.asm` cover the boundary cases |
| The register file had a third read port that no state used together with the other two | Two read ports; port 1's address is muxed by `ra1_sel` (SR2, store source, or R7) |
| `basys3_top` clocked the core with `step_pulse \| rst_pulse`, a clock made by a logic gate and never timed | One 100 MHz clock everywhere; the step is a clock enable (`ce` on both cores, `en` on both memories) |
| `basys3_top` read the program from an absolute Windows path | `MEM_INIT` parameter, default `adam16_sum_array.mem`, which `fpga/build.tcl` adds to the build |
| A committed Vivado project with an empty block design and a stale checkpoint | `fpga/build.tcl`, a project-free batch build (`make fpga`) |
| `tb_adam16_gate` found its halt through a netlist-internal name, and one of its tests had a 17-bit encoding | Black-box: it watches the `dbg_ir` port, works for both cores, and is checked on the RTL in CI (`make gate-rtl`) |
| `scripts/adam16.dc` and `adam16_sim.do` had fixed, machine-specific paths | Paths and the top come from environment variables (`ADAM16_TOP`, `ADAM16_LIBDIR`, …) |

## Design choices to be aware of

These are intentional and documented, but they surprise people coming from LC-3:

- **R0 is not hard-wired to zero.** It is cleared by reset and is otherwise a normal register.
- **LD, LDR and LEA don't set the flags.** Only ALU0, ALU1, ADDI, ANDI and CMP do.
- **TRAP is a direct jump** to `ZEXT(IR[11:0])`, with no vector table. Handlers must sit in `0x0000–0x0FFF`.
- **No halt.** After `TRAP x025` the CPU keeps fetching from `0x0025`. Only the testbenches and the ISS treat it as a stop.
- **Undefined opcodes (`xE`, `xF`) are no-ops.** There is no illegal-instruction trap. They take 4 cycles on the multicycle core and 1 on the pipeline.
- **The two cores' debug outputs mean different things.** On the multicycle core they show PC, IR and the ALU as they are now. On the pipeline they show the instruction retiring in WB ([`demo.md`](../demo.md)).
