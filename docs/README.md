# adam16 microarchitecture documentation

This folder describes the hardware: how the two cores are built (the multicycle `adam16_core` and the five-stage `adam16_pipe_core`), what every module's interface is, how each moves through an instruction cycle by cycle, and how all of it is verified. The instruction set itself (encodings and semantics) is in the [top-level README](../README.md#instruction-set-reference) and [`InstructionSet.txt`](../InstructionSet.txt).

## Reference

| | Covers |
|---|---|
| [**Module interfaces**](interfaces/README.md) | One sheet per module: schematic symbol, parameters, port table (direction, width, type, reset value), timing, connections, instantiation template |
| [**Control FSM bubble diagrams**](03_control.md#bubble-diagrams) | Overview plus four detail diagrams with every arc as *condition / outputs*, the state table, and the control-signal table |
| [**Pipeline diagram and decode table**](07_pipeline.md) | The pipelined core's block diagram, its decoder table, and a cycle-by-cycle table of every stage, taken from simulation |
| [**Debounce bubble diagram**](interfaces/debounce.md#state-machine) | The design's only other state machine |

## Narrative

| # | Document | Covers |
|---|---|---|
| 1 | [System overview](01_system.md) | The two cores, block diagram, clocking and reset, memory map |
| 2 | [Datapath](02_datapath.md) | Multicycle core: datapath diagram, registers, every mux and its select codes, flags, register file |
| 3 | [Control](03_control.md) | Multicycle core: bubble diagrams, states, decode, control-signal table, Moore vs Mealy |
| 4 | [Memory interface](04_memory.md) | Bus protocol, read latency, timing diagrams for ALU / load / store |
| 5 | [Execution timing](05_timing.md) | Cycles per instruction class, CPI, where the cycles go, multicycle vs pipelined |
| 6 | [Known issues](06_known_issues.md) | Limitations, what was fixed, design choices |
| 7 | [The pipelined core](07_pipeline.md) | Stages, memory, forwarding, branches, decode, cycle-by-cycle example, critical paths |
| 8 | [Verification](08_verification.md) | ISS, retire traces, directed and random programs, conformance checks, gate level |

## Conventions

These hold everywhere in the RTL and in these documents.

- **One clock, rising edge.** Every register updates on `posedge clk`. There are no latches and no negative-edge logic.
- **Synchronous, active-high reset.** `rst` is sampled on the clock edge like any other input.
- **Control outputs default to 0.** The FSM's `always_comb` block assigns every output 0 first, and each state only changes the outputs it needs. The bubble diagrams and the control table follow the same rule: anything not listed is 0.
- **Opcode decoding happens in one place.** In the multicycle core that is the controller: the datapath slices fixed IR fields (`IR[8:6]`, `IR[5:0]`, …) but never looks at `IR[15:12]`, and every opcode-dependent choice reaches it as an explicit select signal. In the pipelined core it is `adam16_pipe_decode`, in ID.
- **Names.** `*_we` are write enables, `*_sel` are mux selects. `PC†` is the incremented PC, which is the value PC holds after `S_IF2`. `M[x]` is memory word `x`. Hex is written `0x1234` in text and `16'h1234` in RTL.
- **Word addressing.** Each address holds one 16-bit word, so `PC + 1` is the next instruction.

## Keeping the docs true

Most of what describes the hardware is generated from the RTL, or checked against it:

| What | Source of truth | How |
|---|---|---|
| Control FSM diagrams and tables | [`tools/fsm_spec.py`](tools/fsm_spec.py) | `tb/tb_control_fsm_spec.sv` replays the spec against the RTL: every opcode × field × flag combination, every cycle |
| Pipeline decode table | [`tools/pipe_decode_spec.py`](tools/pipe_decode_spec.py) | `tb/tb_pipe_decode_spec.sv` compares the decoder with the spec for all 65536 instruction words |
| Pipeline cycle-by-cycle table | RTL simulation | `tools/gen_pipeview.py` runs `sum_array` on the pipelined core and tabulates every stage |
| Module symbols | RTL module headers | `tools/gen_symbols.py` |
| Instantiation templates, connection tables | RTL headers and instances | `tools/gen_interconnect.py` |
| Port and parameter tables (hand-written) | RTL module headers | `tools/check_ports.py` checks names, directions, widths, order, defaults |
| Opcode / funct encodings in the spec | `rtl/adam16_isa.sv` | `tools/check_ports.py` |
| Links and images | — | `tools/check_links.py` |
| Datapath, pipeline, top-level, debounce, timing figures | hand-placed sources in `tools/` and `figures/src/` | redrawn by `make`. Timing values come from RTL simulation of `sum_array` |

```bash
make -C docs          # regenerate every figure and generated block
make -C docs check    # fail if anything disagrees with the RTL
```

You need `python3`, Graphviz (`dot`, `neato`), Icarus Verilog (for `check` and the pipeline table), and the WaveDrom CLI (`npm i -g wavedrom-cli`) for the timing diagrams. When you change the RTL:

1. Run `make -C docs check` and read what it reports.
2. For an FSM change, edit `tools/fsm_spec.py` to match the RTL; for a pipeline decoder change, `tools/pipe_decode_spec.py`.
3. For port changes, edit the port table on the interface page.
4. Run `make -C docs` to redraw everything, then `make -C docs check` again.
