# `adam16_isa` (package)

**Source:** `rtl/adam16_isa.sv` · **Imported by:** `adam16_control_fsm` (enums, `decode()`), `adam16_datapath` (sign/zero-extend functions)

This package holds the instruction-set encodings, so the controller and the datapath agree on them. It has no ports; its interface is the types and functions below. Compile it before any module that imports it.

`docs/tools/check_ports.py` checks that the opcode and funct values here match `docs/tools/fsm_spec.py`, the source of the control bubble diagrams.

## Types

### `instr_t`

`typedef logic [15:0] instr_t;` is a raw 16-bit instruction word.

### `opcode_t`: `IR[15:12]`

| Name | Value | | Name | Value |
|---|---|---|---|---|
| `OP_ALU0` | `4'h0` | | `OP_TRAP` | `4'h9` |
| `OP_ALU1` | `4'h1` | | `OP_LDR` | `4'hA` |
| `OP_ADDI` | `4'h2` | | `OP_STR` | `4'hB` |
| `OP_ANDI` | `4'h3` | | `OP_LEA` | `4'hC` |
| `OP_LD` | `4'h4` | | `OP_BR` | `4'hD` |
| `OP_ST` | `4'h5` | | `OP_UD_E` | `4'hE` (undefined) |
| `OP_JMP` | `4'h6` | | `OP_UD_F` | `4'hF` (undefined) |
| `OP_JSR` | `4'h7` | | | |
| `OP_RET` | `4'h8` | | | |

### `alu0_funct_t` / `alu1_funct_t`: `IR[2:0]`

| Value | `alu0_funct_t` (opcode 0) | `alu1_funct_t` (opcode 1) |
|---|---|---|
| `3'b000` | `ALU0_ADD` | `ALU1_NAND` |
| `3'b001` | `ALU0_SUB` | `ALU1_NOR` |
| `3'b010` | `ALU0_NOT` | `ALU1_INC` |
| `3'b011` | `ALU0_AND` | `ALU1_DEC` |
| `3'b100` | `ALU0_OR` | `ALU1_LSL1` |
| `3'b101` | `ALU0_XOR` | `ALU1_LSR1` |
| `3'b110` | `ALU0_MOV` | `ALU1_ASR1` |
| `3'b111` | `ALU0_NEG` | `ALU1_CMP` |

### `dec_t`: decoded instruction fields

A packed struct filled by `decode()`. Fields overlap, because each instruction format reads a different subset of the same bits.

| Field | Type | IR bits | Used as |
|---|---|---|---|
| `op` | `opcode_t` | `[15:12]` | opcode |
| `dr` | `logic [2:0]` | `[11:9]` | DR (destination) / SR (store source) |
| `sr1` | `logic [2:0]` | `[8:6]` | SR1 / BaseR |
| `sr2` | `logic [2:0]` | `[5:3]` | SR2 |
| `funct` | `logic [2:0]` | `[2:0]` | ALU0 / ALU1 operation |
| `imm6` | `logic [5:0]` | `[5:0]` | ADDI / ANDI immediate, LDR / STR offset |
| `off9` | `logic [8:0]` | `[8:0]` | LD / ST / LEA / BR offset |
| `pcoff11` | `logic [10:0]` | `[10:0]` | JSR offset |
| `trapvect12` | `logic [11:0]` | `[11:0]` | TRAP vector |
| `nzp_mask` | `logic [2:0]` | `[11:9]` | BR condition mask |
| `jsr_is_reg` | `logic` | `[11]` | JSR (0) vs JSRR (1) |

## Functions

All are `automatic` and purely combinational.

| Function | Returns | Description |
|---|---|---|
| `decode(instr_t ir)` | `dec_t` | Slices every field above out of `ir`. No validity checking |
| `sext6(logic [5:0] x)` | `logic signed [15:0]` | Sign-extend 6 → 16 bits |
| `sext9(logic [8:0] x)` | `logic signed [15:0]` | Sign-extend 9 → 16 bits |
| `sext11(logic [10:0] x)` | `logic signed [15:0]` | Sign-extend 11 → 16 bits |
| `zext6(logic [5:0] x)` | `logic [15:0]` | Zero-extend 6 → 16 bits |

The datapath builds the TRAP target `{4'b0000, IR[11:0]}` inline; there is no `zext12` function.
