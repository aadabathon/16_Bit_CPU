# Demoing the CPU16 on Basys3

This walks through a live hardware demo of `basys3_top`, using the preloaded
program in `fpga/mem/cpu16_sum_array.mem` (same program as
`tb_cpu16.sv:test_sum_array()`), which sums the five words at
`mem[0x000B..0x000F]` (1+2+3+4+5) and stores the result (15) in `R3` and
`mem[0x0010]`.

## 1. Program the board

1. In Vivado, generate the bitstream against `basys3_top` (top module set,
   `debounce.sv` and `basys3_top.sv` added to `sources_1`).
2. Open **Hardware Manager** → **Open Target** → **Auto Connect** (board
   connected via USB, powered on).
3. **Program Device**, select the generated `.bit`, program.
4. The board is now idle, sitting in `S_IF0`, waiting on `btnU`. Nothing
   will happen on its own — that's expected, this design has no free-run
   clock.

## 2. Controls

| Control | Function |
|---|---|
| `btnC` | Reset. Clears PC/IR/MAR/MDR/flags and forces one clock edge, so the reset value actually latches. |
| `btnU` | Step. Advances the CPU (and memory) by exactly one clock edge. |
| `sw[1:0]` | Selects what the 16 LEDs display (see below). `sw[15:2]` unused. |
| `led[15:0]` | Shows the selected debug word. |

`sw[1:0]` view select:

| `sw[1:0]` | LEDs show |
|---|---|
| `00` | Program Counter (`PC`) |
| `01` | Instruction Register (`IR`) — the raw fetched opcode |
| `10` | ALU result (combinational — only meaningful during an execute state) |
| `11` | Flags, packed as `{13'b0, N, Z, P}` |

Press `btnC` once before starting. Each `btnU` press is debounced (~2ms),
so one physical press = one step, no double-stepping.

## 3. What "one step" actually means

**A step is one clock edge, not one instruction.** The CPU is a multi-cycle
design — each instruction takes 5 to 8 steps to complete, moving through
internal states (fetch → decode → execute). Concretely, per instruction
type:

| Instruction type | Steps to complete |
|---|---|
| ALU / immediate / LEA / branch / JMP / JSR / TRAP | 5 |
| ST / STR | 6 |
| LD / LDR | 8 |

Within any instruction, **the 3rd press latches its opcode into IR** — from
then until 2 presses into the *next* instruction, `sw=01` shows that
instruction's raw encoding. This is the most reliable way to know where you
are if you lose count: switch to IR view and compare against the program
listing (§5) instead of counting blind.

For ALU-type instructions specifically, **the 4th press lands the FSM in
its execute state** — `sw=10` (ALU result) is valid from that press until
the 5th press commits it to the register file and moves on.

## 4. The demo script

### Prologue (15 presses)

Press `btnC`, then `btnU` 15 times. This runs:
- `LEA R1, +10` → `R1 = 0x000B` (base of the data array)
- `ADDI R2, R0, 5` → `R2 = 5` (loop counter)
- `MOV R3, R0` → `R3 = 0` (accumulator)

You're now sitting at the top of the loop (about to fetch `LDR R4, R1, 0`).

### The payoff: watch the sum accumulate

The loop body is `LDR R4,R1,0 / ADD R3,R3,R4 / INC R1,R1 / DEC R2,R2 / CMP
R2,R0 / BRp LOOP` — 33 presses per full pass, 5 passes total. Set `sw=10`
(ALU result) and press `btnU` to the following cumulative counts to catch
the accumulator mid-loop, right after it computes the new sum (before it's
written back):

| Press # (from reset) | Sum shown on LEDs |
|---|---|
| 27 | 1 |
| 60 | 3 |
| 93 | 6 |
| 126 | 10 |
| 159 | 15 |

That's the visual proof it works: `1 → 3 → 6 → 10 → 15`, the running sum of
1+2+3+4+5, live on the LEDs.

(If you'd rather just watch continuously: press `btnU` steadily and glance
at `sw=10` periodically — the ALU result will visibly hold at each new sum
value for a few presses before the CPU moves off to the next loop
housekeeping instruction.)

### Finish (up to press 191)

- Press 180: fifth pass exits the loop (`CMP` sees `R2=0`, `BRp` falls
  through).
- Press 186: `ST R3, +6` completes — `mem[0x0010]` now holds 15. (Not
  directly visible on LEDs — see §6.)
- Press 189: `sw=01` (IR) reads `9025` — the `TRAP` opcode is fetched.
- Press 191: `TRAP` commits (`R7 <- PC`, `PC <- 0x0025`).

## 5. Program listing (for cross-checking IR)

| Addr | Hex | Instruction |
|---|---|---|
| 0x0000 | `C20A` | `LEA  R1, +10` |
| 0x0001 | `2405` | `ADDI R2, R0, 5` |
| 0x0002 | `0606` | `MOV  R3, R0` |
| 0x0003 | `A840` | `LDR  R4, R1, 0`  *(loop top)* |
| 0x0004 | `06E0` | `ADD  R3, R3, R4` |
| 0x0005 | `1242` | `INC  R1, R1` |
| 0x0006 | `1483` | `DEC  R2, R2` |
| 0x0007 | `1087` | `CMP  R2, R0` |
| 0x0008 | `D3FA` | `BRp  LOOP` (-6 → 0x0003) |
| 0x0009 | `5606` | `ST   R3, +6` → `mem[0x0010]` |
| 0x000A | `9025` | `TRAP 0x025` |
| 0x000B..0x000F | `0001..0005` | data: `1,2,3,4,5` |

## 6. Known limitations of this demo

- **No hardware halt.** After `TRAP`, the CPU jumps to `PC=0x0025`, which is
  empty (zeroed) memory — it'll just keep fetching harmless `ADD`
  no-ops forever. There's no indicator that the program is "done" beyond
  recognizing `IR=9025` yourself. Press `btnC` to restart the demo.
- **No register or memory-content probe.** The debug mux only exposes
  PC/IR/ALU-result/flags, not register file or SRAM contents directly. The
  accumulator trace in §4 is how you confirm `R3` is computed correctly
  without a dedicated register view; final memory/register state can't be
  read back from the board itself. Adding a register-select probe (e.g.
  routing `rf.r[sw[2:0]]` out through the same LED mux) would be a natural
  follow-up if you want post-hoc verification without re-deriving it from
  the ALU trace.
- **Reprogramming = only way to change the program.** The image is baked
  into the bitstream via `$readmemh` at synthesis time
  (`fpga/mem/cpu16_sum_array.mem`). Loading a different program means
  editing that file and re-running synthesis/implementation/bitgen.
