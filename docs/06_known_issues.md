# 6. Known issues and open questions

Each entry says what happens, why, and the options for fixing it. The plan for fixing them is in [ROADMAP.md](../ROADMAP.md#phase-1-finish-and-release-v1-multicycle). Numbered entries are real defects or risks. The last section lists deliberate design choices that are easy to trip over.

## 1. CMP gives the wrong answer when the subtraction overflows

CMP sets the flags from the 16-bit result of `SR1 − SR2`. When the true difference doesn't fit in 16 bits, the sign of the truncated result is wrong.

*Verified in simulation:* `CMP` with `R1 = 0x7FFF` (32767) and `R2 = 0x8000` (−32768) sets **N**, saying R1 < R2. The real answer is P.

The ISA has no overflow (V) or carry (C) flag, so software can't detect this case either. The same applies to SUB followed by a branch. Options:

- **Make CMP a real comparison.** Have CMP set N/Z/P from the signed comparison (`SR1 < SR2`, `==`, `>`) instead of from the truncated difference. This needs no ISA encoding change; the flags just need a separate source when the opcode is CMP. Unsigned comparisons would still be unsupported.
- **Add V (and C) flags** plus branch conditions that use them. This is the usual approach, but `BRx` only has three condition bits, so the encoding has to change.
- **Document it** as "CMP is only valid when |SR1 − SR2| < 2<sup>15</sup>".

## 2. `basys3_top` generates a clock from logic

```systemverilog
assign core_clk = step_pulse | rst_pulse;   // rtl/basys3_top.sv:21
```

The core and the SRAM are clocked by the OR of two debouncer outputs. Single-stepping works, but this isn't a sound clocking scheme:

- The net is driven by a logic gate instead of a dedicated clock buffer, so it can have large skew across the core's flops (hold-time risk) and can glitch.
- No clock is defined on `core_clk` in `adam16.xdc`, so none of the core's paths are timed.

**Fix:** clock everything from the 100 MHz `clk` and turn the step into a **clock enable**. Add a `ce` input to the core and the memory and guard every register update with it (`else if (ce) …`), with `ce = step_pulse | rst_pulse`. Everything is then one constrained clock domain, and the same RTL can run free with `ce = 1`.

## 3. The register file has one more read port than any instruction uses

The register file has three read ports, but no state ever uses more than two:

| Reads in one cycle | Where |
|---|---|
| `rd0` + `rd1` | two-operand ALU ops, CMP |
| `rd0` | ADDI, ANDI, LDR/STR address, JMP, JSRR |
| `rd2` | ST/STR data (`S_MEM_WR0`), RET (R7) |

Port 1's address could be muxed between `IR[5:3]`, `IR[11:9]` and `3'b111`, and port 2 deleted. That saves one 16-bit 8:1 read mux (ASIC) or one copy of the distributed-RAM register file (FPGA). Two ports are still enough for a pipeline that reads BaseR and the store data together in ID.

## 4. Repository housekeeping

- `rtl/basys3_top.sv:45` loads the memory image from an absolute Windows path (`C:/Users/adams/...`). A relative path, or a path set from the Vivado project, would work on any machine.
- `tb/tb_cpu16_gate.sv` (the gate-level testbench) treats any TRAP as a halt, while `tb/tb_cpu16.sv` now halts only on `TRAP x025`. All the gate-level programs use only `TRAP x025`, so its results don't change. It hasn't been re-run since the control refactor, because that needs the SAED32 cell library.

## Design choices to be aware of

These are intentional and documented, but they surprise people coming from LC-3:

- **R0 is not hard-wired to zero.** It is cleared by reset and is otherwise a normal register.
- **LD, LDR and LEA don't set the flags.** Only ALU0, ALU1, ADDI, ANDI and CMP do.
- **TRAP is a direct jump** to `ZEXT(IR[11:0])`, with no vector table. Handlers must sit in `0x0000–0x0FFF`.
- **No halt.** After `TRAP x025` the CPU keeps fetching from `0x0025`. Only the testbench treats it as a stop.
- **Undefined opcodes (`xE`, `xF`) are 4-cycle no-ops.** There is no illegal-instruction trap.
