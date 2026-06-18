# cpu16

A 16-bit soft-core processor written in SystemVerilog. Loosely inspired by LC-3 with several intentional departures: two ALU opcode groups giving 16 distinct ALU operations, flags not set by load instructions, and a TRAP mechanism for software-defined system calls. The design targets synchronous single-port SRAM and is controlled by a multi-cycle Moore FSM.

---

## Architecture at a Glance

| Property | Value |
|---|---|
| Data width | 16 bits |
| Address space | 64 K words (word-addressed; each address holds one 16-bit word) |
| Registers | R0–R7 (R7 is the link register for JSR / TRAP) |
| Condition flags | N (negative), Z (zero), P (positive) |
| Instruction width | 16 bits, fixed |
| Opcode field | 4 bits |
| Fetch latency | 3 cycles (synchronous SRAM with 1-cycle read latency) |
| ALU / branch throughput | 5 cycles |
| ST / STR throughput | 6 cycles |
| LD / LDR throughput | 8 cycles |

---

## Module Hierarchy

```
cpu16_core
├── cpu16_control_fsm   (14-state Moore FSM; derives all control signals from IR + N/Z/P)
│   └── [imports] cpu16_isa
└── cpu16_datapath      (PC, IR, MAR, MDR; ALU; register file wiring)
    ├── cpu16_regfile   (8 × 16-bit, 3 read ports / 1 write port)
    └── cpu16_alu       (combinational; two-group operation select)
    └── [imports] cpu16_isa

cpu16_isa               (package: opcode enum, dec_t struct, decode(), sext/zext helpers)
SramSBC                 (65536 × 16-bit synchronous SRAM — used in simulation only)
```

### Memory Interface

`cpu16_core` drives a simple synchronous bus. Connect it to any SRAM that presents read data on the cycle after `mem_addr` is stable.

| Signal | Direction | Width | Description |
|---|---|---|---|
| `mem_addr` | out | 16 | Address driven by the MAR register |
| `mem_rdata` | in | 16 | Read data (must be stable one cycle after address) |
| `mem_wdata` | out | 16 | Write data (store source register) |
| `mem_we` | out | 1 | Write enable |

---

## Instruction Set Reference

### General Encoding

```
 15    12 11    9  8     6  5     3  2     0
┌────────┬───────┬────────┬────────┬────────┐
│ opcode │  DR   │  SR1   │  SR2   │ funct  │  ← ALU instructions
└────────┴───────┴────────┴────────┴────────┘

┌────────┬───────┬────────┬──────────────────┐
│ opcode │  DR   │  SR1   │      imm6        │  ← ADDI / ANDI
└────────┴───────┴────────┴──────────────────┘

┌────────┬───────┬──────────────────────────┐
│ opcode │ DR/SR │          Offset9         │  ← LD / ST / BRx / LEA
└────────┴───────┴──────────────────────────┘

┌────────┬───┬───────────────────────────────┐
│ opcode │ j │         PCoffset11            │  ← JSR (j=0) / JSRR (j=1)
└────────┴───┴───────────────────────────────┘

┌────────┬──────────────────────────────────┐
│ opcode │          TrapVector12            │  ← TRAP
└────────┴──────────────────────────────────┘
```

**BaseR** (for JMP, LDR, STR, JSRR) always occupies bits [8:6] — the same slot as SR1 — so the SR1 read port is reused with no extra mux.

---

### ALU Group 0 — opcode `0000`

All ALU0 operations write condition flags {N, Z, P}.

| Mnemonic | funct | Operation |
|---|---|---|
| `ADD DR, SR1, SR2` | `000` | DR ← SR1 + SR2 |
| `SUB DR, SR1, SR2` | `001` | DR ← SR1 − SR2 |
| `NOT DR, SR1` | `010` | DR ← ~SR1 |
| `AND DR, SR1, SR2` | `011` | DR ← SR1 & SR2 |
| `OR  DR, SR1, SR2` | `100` | DR ← SR1 \| SR2 |
| `XOR DR, SR1, SR2` | `101` | DR ← SR1 ^ SR2 |
| `MOV DR, SR1` | `110` | DR ← SR1 |
| `NEG DR, SR1` | `111` | DR ← 0 − SR1 (two's complement negate) |

### ALU Group 1 — opcode `0001`

All ALU1 operations that produce a result write condition flags. CMP writes flags only (no register writeback).

| Mnemonic | funct | Operation |
|---|---|---|
| `NAND DR, SR1, SR2` | `000` | DR ← ~(SR1 & SR2) |
| `NOR  DR, SR1, SR2` | `001` | DR ← ~(SR1 \| SR2) |
| `INC  DR, SR1` | `010` | DR ← SR1 + 1 |
| `DEC  DR, SR1` | `011` | DR ← SR1 − 1 |
| `LSL1 DR, SR1` | `100` | DR ← SR1 << 1 |
| `LSR1 DR, SR1` | `101` | DR ← SR1 >> 1 (logical, fills 0) |
| `ASR1 DR, SR1` | `110` | DR ← SR1 >>> 1 (arithmetic, fills MSB) |
| `CMP  SR1, SR2` | `111` | flags ← sign(SR1 − SR2) ; no writeback |

### Immediate Instructions

| Mnemonic | Opcode | Operation |
|---|---|---|
| `ADDI DR, SR1, imm6` | `0010` | DR ← SR1 + SEXT(imm6) ; imm6 range −32..+31 |
| `ANDI DR, SR1, imm6` | `0011` | DR ← SR1 & ZEXT(imm6) ; imm6 range 0..63 |

### Memory Instructions

† **PC†** denotes the incremented PC — the address of the instruction immediately following the one being executed. Memory is word-addressed.

| Mnemonic | Opcode | Operation |
|---|---|---|
| `LD  DR, off9`         | `0100` | DR ← mem\[PC† + SEXT(off9)\] |
| `ST  SR, off9`         | `0101` | mem\[PC† + SEXT(off9)\] ← SR |
| `LDR DR, BaseR, off6`  | `1010` | DR ← mem\[BaseR + SEXT(off6)\] |
| `STR SR, BaseR, off6`  | `1011` | mem\[BaseR + SEXT(off6)\] ← SR |
| `LEA DR, off9`         | `1100` | DR ← PC† + SEXT(off9) (address only; **no flag write**) |

> **Flag note:** LD, LDR, and LEA do **not** modify condition flags. This is an intentional departure from LC-3, where LD/LDR do set flags.

### Control-Flow Instructions

| Mnemonic | Opcode | Operation |
|---|---|---|
| `BRx  off9`   | `1101` | if (nzp\_mask & {N,Z,P} ≠ 0) PC ← PC† + SEXT(off9) |
| `JMP  BaseR`  | `0110` | PC ← BaseR |
| `JSR  off11`  | `0111` (bit 11 = 0) | R7 ← PC† ; PC ← PC† + SEXT(off11) |
| `JSRR BaseR`  | `0111` (bit 11 = 1) | R7 ← PC† ; PC ← BaseR |
| `RET`         | `1000` | PC ← R7 |
| `TRAP tvect12`| `1001` | R7 ← PC† ; PC ← ZEXT(tvect12) |

**BRx condition codes** — IR[11:9] selects which flags trigger the branch:

| Mnemonic | IR[11:9] | Branches when |
|---|---|---|
| `BRn` | `100` | N = 1 (result was negative) |
| `BRz` | `010` | Z = 1 (result was zero) |
| `BRp` | `001` | P = 1 (result was positive) |
| `BRnz` | `110` | N = 1 or Z = 1 (result ≤ 0) |
| `BRnp` | `101` | N = 1 or P = 1 (result ≠ 0) |
| `BRzp` | `011` | Z = 1 or P = 1 (result ≥ 0) |
| `BR` / `BRnzp` | `111` | always (unconditional) |

### Undefined Opcodes

Opcodes `1110` and `1111` are reserved. The FSM silently returns to fetch on encountering them (equivalent to a NOP).

---

## Microarchitecture

### FSM State Diagram

Every instruction begins at **S\_IF0**. The fetch phase takes exactly 3 cycles to absorb the synchronous SRAM read latency.

```
                              ┌─────────────────────── S_EX_ALU  ──────────────────────────┐
                              │  (ALU0/ALU1/ADDI/ANDI/LEA)                                  │
S_IF0 → S_IF1 → S_IF2 → S_ID ┤                                                             ├→ S_IF0
                              │  (LD/LDR)  ─ S_EX_EA → S_MEM_RD0 → S_MEM_RD1 → S_WB_LD ──┤
                              │  (ST/STR)  ─ S_EX_EA → S_MEM_WR0 ────────────────────────┤
                              │  (BRx)     ─ S_EX_BR ──────────────────────────────────────┤
                              │  (JMP/RET) ─ S_EX_JMP ─────────────────────────────────────┤
                              │  (JSR)     ─ S_EX_JSR ─────────────────────────────────────┤
                              └  (TRAP)    ─ S_EX_TRAP ────────────────────────────────────┘
```

| Instruction class | Total cycles |
|---|---|
| ALU, ADDI, ANDI, LEA, BRx, JMP, JSR, TRAP | **5** |
| ST / STR | **6** |
| LD / LDR | **8** |

### Datapath Highlights

- **3-read-port register file**: SR1 / BaseR is always IR[8:6]; SR2 is IR[5:3]; the third port supplies store data (IR[11:9]) or R7 (RET).
- **ALU B-side mux** (5 sources): SR2 register, SEXT(imm6), ZEXT(imm6), SEXT(off9), SEXT(off6).
- **Writeback mux** (3 sources): ALU result, MDR (loads), PC (JSR / TRAP link address saved to R7).
- Condition flags are written from the writeback data bus, so `flag_we` is combinationally valid in the same cycle as the writeback.

---

## File Structure

```
16BitCpu/
├── cpu16_isa.sv           — ISA package: opcode enum, dec_t, decode(), sext/zext helpers
├── cpu16_alu.sv           — Combinational ALU (ALU0 and ALU1 groups, pure logic)
├── cpu16_regfile.sv       — 8 × 16-bit synchronous register file (3R / 1W)
├── cpu16_datapath.sv      — PC, IR, MAR, MDR; ALU and regfile interconnect
├── cpu16_control_fsm.sv   — 14-state Moore FSM; all control signal generation
├── cpu16_core.sv          — Top-level: wires control and datapath together
├── Sram.sv                — Synchronous 65536 × 16-bit SRAM model (simulation only)
├── InstructionSet.txt     — Informal ISA specification notes
└── sim/
    └── tb_cpu16.sv        — Directed testbench: 12 test programs
```

---

## Running the Testbench

### Icarus Verilog (iverilog)

```bash
iverilog -g2012 -o sim/cpu16_tb \
    cpu16_isa.sv cpu16_alu.sv cpu16_regfile.sv \
    cpu16_datapath.sv cpu16_control_fsm.sv cpu16_core.sv \
    Sram.sv sim/tb_cpu16.sv

vvp sim/cpu16_tb
```

To capture a VCD waveform for GTKWave:

```bash
vvp sim/cpu16_tb +VCD=cpu16.vcd
gtkwave cpu16.vcd
```

### Expected Output

```
================================================
 CPU16 testbench
================================================

[T1] addi_add
    PASS  R1                             0x0005
    PASS  R2                             0x0007
    PASS  R3 = R1+R2                     0x000c
...
[T12] sum_array
    PASS  R3 (sum = 1+2+3+4+5)          0x000f
    PASS  mem[0x0010] (stored result)    0x000f
================================================
 Summary: 35/35 checks passed   (12 tests, N cycles)
 ALL TESTS PASSED
================================================
```

---

## Example Program: Array Sum

This program sums five values stored in memory and writes the result back. It exercises LEA (address computation), LDR (base+offset load), ALU1 (INC / DEC), CMP + BRp (conditional loop), and ST (PC-relative store).

### Assembly

```
; sum_array — sum mem[0x000B..0x000F], store result at mem[0x0010]
;
; Register map:
;   R0 = 0 (always zero after reset)
;   R1 = array pointer  (walks 0x000B → 0x0010)
;   R2 = iteration counter (counts down from 5)
;   R3 = running accumulator
;   R4 = scratch (current element)

        LEA  R1, +10       ; 0x0000 — R1 = PC†(1) + 10 = 0x000B  (array base)
        ADDI R2, R0,  5    ; 0x0001 — R2 = 5  (element count)
        MOV  R3, R0        ; 0x0002 — R3 = 0  (clear accumulator)
LOOP:
        LDR  R4, R1,  0    ; 0x0003 — R4 = mem[R1 + 0]
        ADD  R3, R3, R4    ; 0x0004 — R3 += R4
        INC  R1, R1        ; 0x0005 — R1++
        DEC  R2, R2        ; 0x0006 — R2--
        CMP  R2, R0        ; 0x0007 — flags ← sign(R2 − 0)
        BRp  LOOP          ; 0x0008 — if R2 > 0, jump to LOOP
        ST   R3, +6        ; 0x0009 — mem[PC†(0xA) + 6] = mem[0x0010] = R3
        TRAP 0x025         ; 0x000A — halt
; Data (one word each):
        DW   0x0001        ; 0x000B
        DW   0x0002        ; 0x000C
        DW   0x0003        ; 0x000D
        DW   0x0004        ; 0x000E
        DW   0x0005        ; 0x000F
```

### Machine Code

| Address | Encoding | Instruction | Notes |
|---|---|---|---|
| `0x0000` | `0xC20A` | `LEA  R1, +10`    | 1100\_001\_000001010 |
| `0x0001` | `0x2405` | `ADDI R2, R0, 5`  | 0010\_010\_000\_000101 |
| `0x0002` | `0x0606` | `MOV  R3, R0`     | 0000\_011\_000\_000\_110 |
| `0x0003` | `0xA840` | `LDR  R4, R1, 0`  | 1010\_100\_001\_000000 |
| `0x0004` | `0x06E0` | `ADD  R3, R3, R4` | 0000\_011\_011\_100\_000 |
| `0x0005` | `0x1242` | `INC  R1, R1`     | 0001\_001\_001\_000\_010 |
| `0x0006` | `0x1483` | `DEC  R2, R2`     | 0001\_010\_010\_000\_011 |
| `0x0007` | `0x1087` | `CMP  R2, R0`     | 0001\_000\_010\_000\_111 |
| `0x0008` | `0xD3FA` | `BRp  −6`         | 1101\_001\_111111010; target = 0x0009 + (−6) = 0x0003 |
| `0x0009` | `0x5606` | `ST   R3, +6`     | 0101\_011\_000000110; target = 0x000A + 6 = 0x0010 |
| `0x000A` | `0x9025` | `TRAP 0x025`      | halt |
| `0x000B` | `0x0001` | *(data)* | |
| `0x000C` | `0x0002` | *(data)* | |
| `0x000D` | `0x0003` | *(data)* | |
| `0x000E` | `0x0004` | *(data)* | |
| `0x000F` | `0x0005` | *(data)* | |

### Execution Trace

| Cycle | R1 | R2 | R3 | Action |
|---|---|---|---|---|
| init | 0x000B | 5 | 0 | after LEA / ADDI / MOV |
| iter 1 | 0x000C | 4 | 1 | loaded 1, accumulated |
| iter 2 | 0x000D | 3 | 3 | loaded 2, accumulated |
| iter 3 | 0x000E | 2 | 6 | loaded 3, accumulated |
| iter 4 | 0x000F | 1 | 10 | loaded 4, accumulated |
| iter 5 | 0x0010 | 0 | **15** | loaded 5; CMP sets Z, BRp not taken |
| done | — | — | **15** | ST writes 0x000F to mem[0x0010] |

### Running This Example

The example is already included as **T12** in `sim/tb_cpu16.sv`. Run the testbench with the commands above. To load the program onto a different simulator, initialize memory with the encoding table above (16 words starting at address `0x0000`).
