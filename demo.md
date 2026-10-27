# Demoing adam16 on the Basys3

The board runs `fpga/mem/adam16_sum_array.mem` (source: `sw/tests/sum_array.asm`). The program sums the five words at `0x000B..0x000F` (1 + 2 + 3 + 4 + 5) into `R3` and stores the result, 15, at `0x0010`. You step it one clock cycle per button press and watch it on the LEDs.

Every press count on this page is checked in simulation by `make demo` (`tb/tb_basys3.sv`), for both cores.

## 1. Build and program

```bash
make fpga                    # pipelined core   -> build/fpga/pipe/basys3_top.bit
make fpga FPGA_CORE=multi    # multicycle core  -> build/fpga/multi/basys3_top.bit
```

(`make fpga` runs `vivado -mode batch -source fpga/build.tcl`; no Vivado project is needed.) Then in Vivado's **Hardware Manager**: **Open Target → Auto Connect**, **Program Device**, and pick the `.bit`.

Nothing moves on its own after programming. The core advances only when you press step.

## 2. Controls

| Control | Function |
|---|---|
| `btnC` | Reset, while held. The core restarts from address 0 with every register cleared |
| `btnU` | Step: exactly one clock cycle of the core and its memory per press (debounced, 2 ms) |
| `sw[1:0]` | What the 16 LEDs show (below). `sw[15:2]` are unused |

| `sw[1:0]` | Multicycle core (`FPGA_CORE=multi`) | Pipelined core (default) |
|---|---|---|
| `00` | PC | PC of the instruction retiring this cycle |
| `01` | IR | that instruction (`D000`, a NOP, while WB is empty) |
| `10` | ALU output (meaningful in an execute state) | its result |
| `11` | flags `{N,Z,P}` | flags after it |

Press `btnC` before you start. In the tables below, "press *n*" means *n* presses of `btnU` after reset.

## 3a. Pipelined core

**One press is one clock cycle.** Five instructions are in flight, and the LEDs show the one leaving the pipeline (WB). The first instruction comes out at press 4. After that one instruction comes out per press, except for one empty cycle after each taken branch (the bubble).

Set `sw = 10` and press to these counts to watch the running sum appear as `ADD R3, R3, R4` retires:

| Press | LEDs (`sw = 10`) | |
|---|---|---|
| 4 | `0x000B` | `LEA R1` retires: the address of the array |
| 8 | 1 | first `ADD` |
| 15 | 3 | |
| 22 | 6 | |
| 29 | 10 | |
| 36 | 15 | last `ADD` |
| 38 | `sw = 11` shows `010` (Z) | `DEC R2` reached 0 |
| 42 | `sw = 01` shows `9025` | `HALT` retires: the program is done |

Each pass of the loop takes 7 presses: six instructions plus one bubble after `BRp`. With `sw = 01` you can see the bubble as `D000`. [Chapter 7](docs/07_pipeline.md#cycle-by-cycle-sum_array) has the whole run as a table, one row per press.

## 3b. Multicycle core

**One press is one clock cycle, and an instruction takes several.** Each instruction walks the controller's states: 5 presses for ALU, branch, jump, call and TRAP instructions, 6 for a store, 8 for a load. The third press of an instruction latches it into IR, so `sw = 01` shows the instruction being executed.

The prologue (`LEA`, `ADDI`, `MOV`) takes 15 presses. Each pass of the loop takes 33. Set `sw = 10` (ALU output) and press to these counts to catch each new sum while the `ADD` is in its execute state:

| Press | LEDs (`sw = 10`) |
|---|---|
| 27 | 1 |
| 60 | 3 |
| 93 | 6 |
| 126 | 10 |
| 159 | 15 |

Then:

- Press 180: the fifth `BRp` falls through (`R2 = 0`).
- Press 186: `ST R3` has written 15 to `0x0010`.
- Press 189: `sw = 01` shows `9025`, the `HALT` (`TRAP x025`).
- Press 191: the TRAP has executed, and `sw = 00` shows PC = `0x0025`.

## 4. Program listing

| Addr | Hex | Instruction |
|---|---|---|
| `0x0000` | `C20A` | `LEA  R1, 0x000B` |
| `0x0001` | `2405` | `ADDI R2, R0, 5` |
| `0x0002` | `0606` | `MOV  R3, R0` |
| `0x0003` | `A840` | `LDR  R4, R1, 0` (loop) |
| `0x0004` | `06E0` | `ADD  R3, R3, R4` |
| `0x0005` | `1242` | `INC  R1, R1` |
| `0x0006` | `1483` | `DEC  R2, R2` |
| `0x0007` | `1087` | `CMP  R2, R0` |
| `0x0008` | `D3FA` | `BRp  0x0003` |
| `0x0009` | `5606` | `ST   R3, 0x0010` |
| `0x000A` | `9025` | `HALT` (`TRAP x025`) |
| `0x000B–0x000F` | `0001–0005` | data: 1, 2, 3, 4, 5 |

## 5. Limitations

- **No hardware halt.** `TRAP x025` jumps to `0x0025`, which holds zeros (`ADD R0, R0, R0`), so the core runs harmless no-ops from there on. Press `btnC` to start again.
- **No register or memory view.** The LEDs show only the debug word. The running sum above is how you see `R3` being computed.
- **The program is part of the bitstream.** To run another program, assemble it over the image (`python3 sw/asm.py prog.asm -o fpga/mem/adam16_sum_array.mem`) and rebuild.
