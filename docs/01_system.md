# 1. System overview and port interfaces

![Top-level block diagram](figures/top_level.svg)

There are two cores for the same frozen ISA. They give the same results, and the regression checks that instruction by instruction ([verification](08_verification.md)).

| Core | Structure | Memory | Cycles per instruction |
|---|---|---|---|
| [`adam16_core`](interfaces/adam16_core.md) | Multicycle: a 14-state controller (`adam16_control_fsm`) drives a datapath (`adam16_datapath`) holding PC, IR, MAR, MDR, the register file, the ALU and the flags | one single-port synchronous RAM (`adam16_sram`) for instructions and data | 5, 6 (store), 8 (load) |
| [`adam16_pipe_core`](interfaces/adam16_pipe_core.md) | Five-stage pipeline: IF ID EX MEM WB with full forwarding and no stalls ([chapter 7](07_pipeline.md)) | one dual-port synchronous RAM (`adam16_dpram`): port A fetches, port B reads and writes data | 1, plus 1 after a taken branch or a jump |

Chapters 2 to 5 describe the multicycle core, and chapter 7 the pipelined one. Memory sits outside either core. In simulation and in the ASIC flow a testbench wires a core straight to its memory. On the Basys3 board, `basys3_top` adds button debouncing, single-stepping and an LED debug view, and its `PIPELINED` parameter picks the core.

## Clocking and reset

Each core has one clock, `clk`, and a clock enable, `ce`. A core advances one cycle on each rising edge of `clk` with `ce = 1` and holds otherwise; its memory's `en` takes the same signal.

| | Simulation / ASIC flow | Basys3 (`basys3_top`) |
|---|---|---|
| Clock | `clk`, free-running, `ce = 1` | the 100 MHz board clock, for everything |
| Advance | every edge | `ce = en = step`: a one-cycle pulse per debounced press of btnU, so one cycle per press |
| Reset | `rst`, held for ≥ 1 clock edge | `rst` = the debounced level of btnC |

The reset is synchronous and active high, and it ignores `ce`. One edge with `rst = 1` gives:

| State element | Reset value |
|---|---|
| Multicycle: FSM state | `S_IF0` |
| Multicycle: PC, IR, MAR, MDR | `0x0000` |
| Pipelined: fetch PC; every stage empty | `0x0000`; valid bits 0 |
| R0–R7 | `0x0000` |
| N Z P | `0 1 0`. Exactly one flag is always set, so `BRnzp` is unconditional from the first instruction. |
| Memory contents | Not reset. Loaded from `INIT_FILE` at simulation start / FPGA configuration. |

## Memory map

The address space is a single 64K-word space shared by instructions and data. There is no memory-mapped I/O.

| Address | Use |
|---|---|
| `0x0000` | Reset vector: the first instruction fetched |
| `0x0000–0x0FFF` | The only region `TRAP` can reach (`PC ← ZEXT(IR[11:0])`, a direct jump) |
| `0x0025` | `TRAP x025` is the HALT convention the testbenches and the ISS stop on |
| `0x0000–0xFFFF` | Unified instruction + data memory |

## Port interfaces

Every module has its own interface sheet in [`interfaces/`](interfaces/README.md), with a schematic symbol, port table, timing notes and instantiation template.

| Module | Role |
|---|---|
| [`adam16_core`](interfaces/adam16_core.md) | Multicycle processor: one memory port + debug outputs |
| [`adam16_control_fsm`](interfaces/adam16_control_fsm.md) | Multicycle controller |
| [`adam16_datapath`](interfaces/adam16_datapath.md) | Multicycle registers, muxes, flags |
| [`adam16_pipe_core`](interfaces/adam16_pipe_core.md) | Pipelined processor: fetch and data ports + debug outputs |
| [`adam16_pipe_decode`](interfaces/adam16_pipe_decode.md) | Pipelined decoder (ID stage) |
| [`adam16_regfile`](interfaces/adam16_regfile.md) | 8 × 16 register file, both cores |
| [`adam16_alu`](interfaces/adam16_alu.md) | 16-operation ALU, both cores |
| [`adam16_sram`](interfaces/adam16_sram.md) | 64K × 16 single-port synchronous memory |
| [`adam16_dpram`](interfaces/adam16_dpram.md) | 64K × 16 dual-port synchronous memory |
| [`basys3_top`](interfaces/basys3_top.md) | Basys3 wrapper |
| [`debounce`](interfaces/debounce.md) | Button synchronizer + debouncer |
| [`adam16_isa`](interfaces/adam16_isa.md) | Package: encodings and helpers |
