# cpu16 microarchitecture documentation

This folder describes the hardware: how `cpu16_core` is built and how it moves through each instruction cycle by cycle. The instruction set itself (encodings and semantics) is in the [top-level README](../README.md#instruction-set-reference) and [`InstructionSet.txt`](../InstructionSet.txt).

| # | Document | Covers | RTL |
|---|---|---|---|
| 1 | [System overview and port interfaces](01_system.md) | Block diagram, clocking and reset, every module's ports, memory map | `cpu16_core.sv`, `basys3_top.sv`, `debounce.sv`, `Sram.sv` |
| 2 | [Datapath](02_datapath.md) | Registers, muxes and their select codes, ALU op table, register file, flags | `cpu16_datapath.sv`, `cpu16_regfile.sv`, `cpu16_alu.sv` |
| 3 | [Control](03_control.md) | Bubble diagram, per-state register transfers, full control-signal table | `cpu16_control_fsm.sv`, `cpu16_isa.sv` |
| 4 | [Memory interface](04_memory.md) | Bus protocol, read latency, timing diagrams for ALU / load / store | `cpu16_datapath.sv`, `Sram.sv` |
| 5 | [Execution timing](05_timing.md) | Cycles per instruction class, CPI, where the cycles go, pipelining notes | all |
| 6 | [Known issues](06_known_issues.md) | Limitations and open design questions | — |

## Conventions

These hold everywhere in the RTL and in these documents.

- **One clock, rising edge.** Every register updates on `posedge clk`. There are no latches and no negative-edge logic.
- **Synchronous, active-high reset.** `rst` is sampled on the clock edge like any other input. Reset values are listed with each register.
- **Control outputs default to 0.** The FSM's `always_comb` block assigns every output 0 first, and each state only lists the outputs it *raises* or changes. The bubble diagram and the control table follow the same rule: anything not mentioned is 0.
- **Opcode decoding happens in the controller only.** The datapath slices fixed IR fields (`IR[8:6]`, `IR[5:0]`, …) but never looks at `IR[15:12]`. Every choice that depends on the opcode reaches the datapath as an explicit select signal, so the control table is the complete description of what the datapath does in each state.
- **Names.** `*_we` are write enables, `*_sel` are mux selects. `PC†` means the incremented PC, which is the value PC holds after `S_IF2`. `M[x]` is memory word `x`. Hex values are written `0x1234` in text and `16'h1234` in RTL.
- **Word addressing.** Each address holds one 16-bit word, so `PC + 1` is the next instruction.

## Figures

Every figure in [`figures/`](figures) is generated from a text source in [`figures/src/`](figures/src):

| Figure | Source | Tool |
|---|---|---|
| `control_fsm.svg` | `control_fsm.dot` | Graphviz |
| `datapath.svg`, `top_level.svg` | `datapath.py`, `top_level.py` (+ `svgkit.py`) | Python 3, standard library only |
| `timing_*.svg` | `timing_*.json` | WaveDrom |

Run `make` in `docs/figures/` to rebuild after editing a source. The waveform values come from RTL simulation of the `sum_array` program (`fpga/mem/cpu16_sum_array.mem`), not from hand calculation.
