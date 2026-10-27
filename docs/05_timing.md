# 5. Execution timing

This chapter covers the multicycle core, `adam16_core`. Exactly one instruction is in flight at a time, and it walks the FSM from `S_IF0` back to `S_IF0`. It covers what that costs and where the cycles go. The last section compares the pipelined core, `adam16_pipe_core` ([chapter 7](07_pipeline.md)).

## Cycles per instruction class

| Class | Instructions | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | Cycles |
|---|---|---|---|---|---|---|---|---|---|---|
| ALU / immediate | ALU0, ALU1, ADDI, ANDI, LEA | IF0 | IF1 | IF2 | ID | EX_ALU | | | | **5** |
| Branch (taken or not) | BRnzp | IF0 | IF1 | IF2 | ID | EX_BR | | | | **5** |
| Jump / return | JMP, RET | IF0 | IF1 | IF2 | ID | EX_JMP | | | | **5** |
| Call | JSR, JSRR | IF0 | IF1 | IF2 | ID | EX_JSR | | | | **5** |
| Trap | TRAP | IF0 | IF1 | IF2 | ID | EX_TRAP | | | | **5** |
| Store | ST, STR | IF0 | IF1 | IF2 | ID | EX_EA | MEM_WR0 | | | **6** |
| Load | LD, LDR | IF0 | IF1 | IF2 | ID | EX_EA | MEM_RD0 | MEM_RD1 | WB_LD | **8** |
| Undefined | `xE`, `xF` | IF0 | IF1 | IF2 | ID | | | | | **4** |

A taken branch costs the same as an untaken one. With only one instruction in flight there is nothing to flush.

## Example: `sum_array`

The demo program (`fpga/mem/adam16_sum_array.mem`, testbench T12) runs 35 instructions in **191 cycles**, so **CPI = 5.46**. Simulation confirms it: `TRAP` finishes in cycle 190, counting from 0.

| Part | Instructions | Cycles |
|---|---|---|
| Prologue: LEA, ADDI, MOV | 3 | 3 × 5 = 15 |
| Loop body × 5: LDR (8) + ADD, INC, DEC, CMP, BRp (5 each) | 30 | 5 × 33 = 165 |
| ST | 1 | 6 |
| TRAP | 1 | 5 |
| **Total** | **35** | **191** |

At a clock frequency *f*, throughput is *f* / CPI instructions per second.

## Where the cycles go

Of the 191 cycles in `sum_array`:

| Phase | Cycles | Share |
|---|---|---|
| Fetch (`S_IF0–2`), 3 per instruction | 105 | 55 % |
| Decode (`S_ID`), 1 per instruction | 35 | 18 % |
| Execute / memory / write-back | 51 | 27 % |

Almost three quarters of the time goes to getting the instruction and deciding what it is. Three changes would recover most of that without pipelining. These are **analysis only**: none is implemented, and the cycle counts come from counting states, not from simulation.

| | Change | Saves | Cost |
|---|---|---|---|
| A | **Merge `S_ID` into the first execute state.** IR is valid in the cycle after `S_IF2`, and the execute states already decode IR for their outputs. So that cycle can do the work *and* choose the next state. | 1 cycle on every instruction | Bigger output decode in one state. No new timing paths: everything is still a function of (state, IR, flags) |
| B | **Mux the memory address** (`mem_addr = PC` in fetch, `alu_y` in the address cycle, MAR otherwise) instead of always going through MAR. | 1 cycle of fetch on every instruction, plus 1 more on each load and store | `mem_addr` stops being a flop output. For loads and stores, register read → ALU → memory address must fit in one cycle, which may lower f<sub>max</sub> |
| C | **Write load data straight into the register file** from `mem_rdata`, skipping MDR and `S_WB_LD`. | 1 cycle per load | Memory output → write-back mux → register file in one cycle |

With all three: ALU-class instructions take 3 cycles, stores 3 and loads 4. `sum_array` would take about 29 × 3 + 5 × 4 + 1 × 3 = **110 cycles (CPI ≈ 3.1)**.

Beyond that the memory itself is the limit. With one single-port memory and one instruction at a time, fetch and execute can't overlap. Making them overlap is exactly what pipelining does.

## The pipelined core

`adam16_pipe_core` overlaps fetch, decode, execute, memory and write-back ([chapter 7](07_pipeline.md)). Every instruction takes one cycle, plus one after a taken branch or a jump, and nothing stalls. Measured in simulation (`make regress`):

| Program | Instructions | Multicycle cycles | Pipelined cycles | Speed-up |
|---|---|---|---|---|
| `sum_array` | 35 | 191 | 43 | 4.4 × |
| directed tests (`sw/tests/*.asm`, 10 programs) | 218 | 1165 | 294 | 4.0 × |
| 2000 random programs | 409 722 | 2 275 451 | 477 105 | 4.8 × |

Instruction counts include the final HALT. Cycle counts run from reset until HALT retires, so the pipeline's numbers include its four-cycle fill for each program, which weighs heavily in the short directed tests.

For `sum_array` the 43 cycles are 4 to fill the pipeline, 35 retiring instructions, and 4 bubbles after the four taken `BRp`. The load-use pair in the loop (`LDR R4` → `ADD R3, R3, R4`) costs nothing, because the load's data is forwarded from MEM. The [cycle-by-cycle table](07_pipeline.md#cycle-by-cycle-sum_array) shows every stage of every cycle.

The three single-cycle savings above (A, B, C) remain unimplemented for the multicycle core, which is kept as the simple, easy-to-follow version.
