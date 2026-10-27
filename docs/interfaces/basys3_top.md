# `basys3_top`

**Source:** `rtl/basys3_top.sv` · **Top level for:** the Basys3 build (`fpga/build.tcl`), `tb_basys3` · **Contains:** `debounce` (`db_rst`, `db_step`); `adam16_pipe_core` + `adam16_dpram` or `adam16_core` + `adam16_sram` (`u_cpu`, `u_mem`)

The FPGA wrapper for the Digilent Basys3. It keeps the memory on-chip, lets a person single-step the CPU with a button, and shows one of four debug words on the 16 LEDs. `PIPELINED` chooses the core. Pin assignments are in `fpga/constraints/adam16.xdc`. How to use it: [`demo.md`](../../demo.md), which `make demo` checks in simulation for both cores.

![basys3_top symbol](../figures/symbols/basys3_top.svg)

## Parameters

| Name | Type | Default | Description |
|---|---|---|---|
| `PIPELINED` | bit | `1'b1` | `1`: `adam16_pipe_core` with `adam16_dpram`. `0`: `adam16_core` with `adam16_sram` |
| `DEBOUNCE_CYCLES` | int | `200_000` | Debouncer settle time in `clk` cycles (2 ms at 100 MHz). Testbenches shorten it |
| `MEM_INIT` | string | `"adam16_sum_array.mem"` | Program image for the memory's `INIT_FILE`. `fpga/build.tcl` adds `fpga/mem/adam16_sum_array.mem` to the build, so the bare file name is found |

## Ports

| Signal | Dir | Width | Type | Reset | Description |
|---|---|---|---|---|---|
| `clk` | in | 1 | clock | — | 100 MHz oscillator, pin W5. Clocks everything: debouncers, core and memory |
| `btn_rst` | in | 1 | async | — | btnC (U18). Its debounced level is the core's synchronous `rst`; the core stays in reset while it is held |
| `btn_step` | in | 1 | async | — | btnU (T18). Each debounced press raises the core's `ce` and the memory's `en` for one `clk` cycle: one core cycle per press |
| `sw` | in | 16 | async | — | Slide switches. `sw[1:0]` picks the LED view (`00` PC, `01` IR, `10` ALU output / result, `11` `{13'b0,N,Z,P}`); `sw[15:2]` unused. Feeds the LED mux directly, with no synchronizer (it only drives LEDs) |
| `led` | out | 16 | comb | — | Debug word selected by `sw[1:0]`. What each view means differs per core: see [`demo.md`](../../demo.md) |

## Clocking

One clock domain. The step button doesn't make a clock edge; it enables one: every register in the core and the memory updates only on an edge where `step = 1`, and `step` is a single-cycle pulse per press. Reset doesn't need an edge from the button, because it is synchronous to the free-running `clk`.

Every timing path is therefore an ordinary single-cycle path at 100 MHz. Since the enable can't be 1 on two cycles in a row, a path that misses 10 ns still works in the step demo. The real limit, if the core is ever run free with `ce = 1`, is in `build/fpga/<core>/timing.rpt` after `make fpga`.

## Connections

Every port and every internal net. Generated from the RTL. Each core and memory pair sits in its own generate block (`g_pipe`, `g_multi`), so both appear.

<!-- BEGIN GENERATED: connections -->
| Net | Width | Driven by | Read by |
|---|---|---|---|
| `clk` | 1 | port `clk` | `db_rst.clk`, `db_step.clk`, `u_cpu.clk`, `u_mem.clk` |
| `btn_rst` | 1 | port `btn_rst` | `db_rst.btn_in` |
| `btn_step` | 1 | port `btn_step` | `db_step.btn_in` |
| `sw` | 16 | port `sw` | `always_comb` logic |
| `led` | 16 | `always_comb` logic | port `led` |
| `rst` | 1 | `db_rst.btn_clean` | `u_cpu.rst` |
| `step` | 1 | `db_step.btn_pulse` | `u_cpu.ce`, `u_mem.en` |
| `imem_addr` | 16 | `u_cpu.imem_addr` | `u_mem.a_addr` |
| `imem_rdata` | 16 | `u_mem.a_rdata` | `u_cpu.imem_rdata` |
| `dmem_addr` | 16 | `u_cpu.dmem_addr` | `u_mem.b_addr` |
| `dmem_wdata` | 16 | `u_cpu.dmem_wdata` | `u_mem.b_wdata` |
| `dmem_we` | 1 | `u_cpu.dmem_we` | `u_mem.b_we` |
| `dmem_rdata` | 16 | `u_mem.b_rdata` | `u_cpu.dmem_rdata` |
| `dbg_pc` | 16 | `u_cpu.dbg_pc` | `always_comb` logic |
| `dbg_ir` | 16 | `u_cpu.dbg_ir` | `always_comb` logic |
| `dbg_alu_y` | 16 | `u_cpu.dbg_alu_y` | `always_comb` logic |
| `dbg_n` | 1 | `u_cpu.dbg_n` | `always_comb` logic |
| `dbg_z` | 1 | `u_cpu.dbg_z` | `always_comb` logic |
| `dbg_p` | 1 | `u_cpu.dbg_p` | `always_comb` logic |
| `mem_rdata` | 16 | `u_mem.rdata` | `u_cpu.mem_rdata` |
| `mem_addr` | 16 | `u_cpu.mem_addr` | `u_mem.addr` |
| `mem_wdata` | 16 | `u_cpu.mem_wdata` | `u_mem.wdata` |
| `mem_we` | 1 | `u_cpu.mem_we` | `u_mem.we` |
<!-- END GENERATED: connections -->

## Instantiation

<!-- BEGIN GENERATED: instantiation -->
```systemverilog
basys3_top #(
  .PIPELINED       (1'b1),
  .DEBOUNCE_CYCLES (200_000),
  .MEM_INIT        ("adam16_sum_array.mem")
) u_basys3_top (
  .clk      (clk),       // in   1
  .btn_rst  (btn_rst),   // in   1
  .btn_step (btn_step),  // in   1
  .sw       (sw),        // in  16
  .led      (led)        // out 16
);
```
<!-- END GENERATED: instantiation -->
