# Module interfaces

One page per RTL module: what it does, its schematic symbol, every parameter and port, timing behaviour, and a ready-to-paste instantiation. Hierarchical modules also list every internal net with its driver and readers.

```
basys3_top .............................. FPGA wrapper (Basys3 board)
├── debounce           (db_rst, db_step)  button synchronizer + debouncer
├── PIPELINED = 0:
│   ├── adam16_core    (u_cpu)            multicycle processor
│   │   ├── adam16_control_fsm (u_ctrl)   14-state controller
│   │   └── adam16_datapath    (u_dp)     PC, IR, MAR, MDR, flags, muxes
│   │       ├── adam16_regfile (rf)       8 x 16 register file, BYPASS = 0
│   │       └── adam16_alu     (alu0)     16-operation ALU
│   └── adam16_sram    (mem)              64K x 16 single-port memory
└── PIPELINED = 1:
    ├── adam16_pipe_core (u_cpu)          5-stage pipelined processor
    │   ├── adam16_pipe_decode (dec)      ID-stage decoder
    │   ├── adam16_regfile     (rf)       8 x 16 register file, BYPASS = 1
    │   └── adam16_alu         (alu)      16-operation ALU
    └── adam16_dpram   (mem)              64K x 16 dual-port memory

adam16_isa  (package)                     opcode / funct enums, decode(), sign/zero extend
```

<!-- BEGIN GENERATED: module-index -->
| Module | File | Clocked | In / out | Page |
|---|---|---|---|---|
| `adam16_alu` | `rtl/adam16_alu.sv` | no | 3 / 1 | [adam16_alu](adam16_alu.md) |
| `adam16_control_fsm` | `rtl/adam16_control_fsm.sv` | yes | 7 / 15 | [adam16_control_fsm](adam16_control_fsm.md) |
| `adam16_core` | `rtl/adam16_core.sv` | yes | 4 / 9 | [adam16_core](adam16_core.md) |
| `adam16_datapath` | `rtl/adam16_datapath.sv` | yes | 18 / 8 | [adam16_datapath](adam16_datapath.md) |
| `adam16_dpram` | `rtl/adam16_dpram.sv` | yes | 6 / 2 | [adam16_dpram](adam16_dpram.md) |
| `adam16_pipe_core` | `rtl/adam16_pipe_core.sv` | yes | 5 / 10 | [adam16_pipe_core](adam16_pipe_core.md) |
| `adam16_pipe_decode` | `rtl/adam16_pipe_decode.sv` | no | 1 / 13 | [adam16_pipe_decode](adam16_pipe_decode.md) |
| `adam16_regfile` | `rtl/adam16_regfile.sv` | yes | 8 / 2 | [adam16_regfile](adam16_regfile.md) |
| `adam16_sram` | `rtl/adam16_sram.sv` | yes | 5 / 1 | [adam16_sram](adam16_sram.md) |
| `basys3_top` | `rtl/basys3_top.sv` | yes | 4 / 1 | [basys3_top](basys3_top.md) |
| `debounce` | `rtl/debounce.sv` | yes | 2 / 2 | [debounce](debounce.md) |
<!-- END GENERATED: module-index -->

Package: [`adam16_isa`](adam16_isa.md) (`rtl/adam16_isa.sv`): opcode and funct enums, `decode()`, sign/zero extend.

## How to read a port table

Rows are in the same order as the module header in the RTL.

| Column | Meaning |
|---|---|
| **Signal** | Port name as written in the RTL |
| **Dir** | `in` or `out`, as seen from the module |
| **Width** | Bits. A bus `name[N-1:0]` has width N |
| **Type** | How the signal behaves in time (below) |
| **Reset** | Value right after a reset edge, for outputs that come from a flip-flop. `—` for inputs and combinational outputs |
| **Description** | What it carries and when it matters |

| Type | Meaning |
|---|---|
| `clock` | Rising-edge clock |
| `reset` | Synchronous, active-high reset: sampled on the rising edge like data |
| `data` | Synchronous input. It must be stable around the rising edge. If it also feeds an output through combinational logic, the description says so |
| `async` | Asynchronous input, unrelated to any clock. The module synchronizes it |
| `reg` | Output driven directly by a flip-flop. It changes only just after a rising edge and is glitch-free |
| `comb` | Output produced by combinational logic. It settles some delay after its inputs change, and can glitch while it does |

## How these pages stay correct

| Part of a page | Kept honest by |
|---|---|
| Symbol figure | Drawn from the RTL module header by `docs/tools/gen_symbols.py` |
| Instantiation template, connection table | Generated from the RTL by `docs/tools/gen_interconnect.py` (between `BEGIN/END GENERATED` markers; don't edit by hand) |
| Port and parameter tables | Hand-written; `docs/tools/check_ports.py` fails if a name, direction, width, order or default differs from the RTL |
| Control FSM bubble diagrams | Drawn from `docs/tools/fsm_spec.py`, which `tb/tb_control_fsm_spec.sv` checks against the RTL cycle by cycle |

`make -C docs` regenerates everything, and `make -C docs check` runs all the checks.
