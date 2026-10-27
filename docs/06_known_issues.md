# 6. Known issues and open questions

Each entry says what happens, why, and the options for fixing it. The plan for fixing them is in [ROADMAP.md](../ROADMAP.md#phase-1-finish-and-release-v1-multicycle). Numbered entries are real defects or risks. The last section lists deliberate design choices that are easy to trip over.

## 1. `basys3_top` generates a clock from logic

```systemverilog
assign core_clk = step_pulse | rst_pulse;   // rtl/basys3_top.sv:21
```

The core and the SRAM are clocked by the OR of two debouncer outputs. Single-stepping works, but this isn't a sound clocking scheme:

- The net is driven by a logic gate instead of a dedicated clock buffer, so it can have large skew across the core's flops (hold-time risk) and can glitch.
- No clock is defined on `core_clk` in `adam16.xdc`, so none of the core's paths are timed.

**Fix:** clock everything from the 100 MHz `clk` and turn the step into a **clock enable**. Add a `ce` input to the core and the memory and guard every register update with it (`else if (ce) …`), with `ce = step_pulse | rst_pulse`. Everything is then one constrained clock domain, and the same RTL can run free with `ce = 1`.

## 2. Repository housekeeping

- `rtl/basys3_top.sv:45` loads the memory image from an absolute Windows path (`C:/Users/adams/...`). A relative path, or a path set from the Vivado project, would work on any machine.
- `tb/tb_adam16_gate.sv` (the gate-level testbench) treats any TRAP as a halt, while `tb/tb_adam16.sv` now halts only on `TRAP x025`. All the gate-level programs use only `TRAP x025`, so its results don't change. It hasn't been re-run since the control refactor, because that needs the SAED32 cell library.

## Fixed

| Was | Fix |
|---|---|
| CMP set the flags from the 16-bit `SR1 − SR2`, so it gave the wrong answer when the subtraction overflowed (`0x7FFF` vs `0x8000` set N) | CMP is now a signed three-way compare in the ALU (−1 / 0 / +1). Test T17 covers five boundary cases |
| The register file had a third read port that no state used together with the other two | Two read ports; port 1's address is muxed by `ra1_sel` (SR2, store source, or R7) |

## Design choices to be aware of

These are intentional and documented, but they surprise people coming from LC-3:

- **R0 is not hard-wired to zero.** It is cleared by reset and is otherwise a normal register.
- **LD, LDR and LEA don't set the flags.** Only ALU0, ALU1, ADDI, ANDI and CMP do.
- **TRAP is a direct jump** to `ZEXT(IR[11:0])`, with no vector table. Handlers must sit in `0x0000–0x0FFF`.
- **No halt.** After `TRAP x025` the CPU keeps fetching from `0x0025`. Only the testbench treats it as a stop.
- **Undefined opcodes (`xE`, `xF`) are 4-cycle no-ops.** There is no illegal-instruction trap.
