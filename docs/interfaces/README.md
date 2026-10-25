# Module interfaces

One page per RTL module: what it does, its schematic symbol, every parameter and port, timing behaviour, and a ready-to-paste instantiation. Hierarchical modules also list every internal net with its driver and readers.

```
basys3_top ............................ FPGA wrapper (Basys3 board)
├── debounce        (db_rst, db_step)   button synchronizer + debouncer
├── cpu16_core      (u_cpu)             the processor
│   ├── cpu16_control_fsm  (u_ctrl)     14-state controller
│   └── cpu16_datapath     (u_dp)       PC, IR, MAR, MDR, flags, muxes
│       ├── cpu16_regfile  (rf)         8 x 16 register file
│       └── cpu16_alu      (alu0)       16-operation ALU
└── SramSBC         (imem)              64K x 16 synchronous memory

cpu16_isa  (package)                    opcode / funct enums, decode(), sign/zero extend
```

| Module | File | Clocked | In / out | Page |
|---|---|---|---|---|
| `cpu16_core` | `rtl/cpu16_core.sv` | yes | 3 / 9 | [cpu16_core](cpu16_core.md) |
| `cpu16_control_fsm` | `rtl/cpu16_control_fsm.sv` | yes | 6 / 15 | [cpu16_control_fsm](cpu16_control_fsm.md) |
| `cpu16_datapath` | `rtl/cpu16_datapath.sv` | yes | 17 / 8 | [cpu16_datapath](cpu16_datapath.md) |
| `cpu16_regfile` | `rtl/cpu16_regfile.sv` | yes | 8 / 3 | [cpu16_regfile](cpu16_regfile.md) |
| `cpu16_alu` | `rtl/cpu16_alu.sv` | no | 3 / 1 | [cpu16_alu](cpu16_alu.md) |
| `SramSBC` | `rtl/Sram.sv` | yes | 4 / 1 | [SramSBC](SramSBC.md) |
| `basys3_top` | `rtl/basys3_top.sv` | yes | 4 / 1 | [basys3_top](basys3_top.md) |
| `debounce` | `rtl/debounce.sv` | yes | 2 / 2 | [debounce](debounce.md) |
| `cpu16_isa` | `rtl/cpu16_isa.sv` | package | — | [cpu16_isa](cpu16_isa.md) |

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
