// Basys3 top level: one adam16 core and its memory, single-stepped with a
// button, with a debug word on the 16 LEDs.
//
// Everything runs on the 100 MHz board clock. The step button does not make
// a clock: each debounced press raises the core's clock enable for exactly
// one cycle, so the core and its memory advance one cycle per press. Reset is
// the debounced reset button, synchronous, and works whatever the enable.
module basys3_top #(
  parameter bit PIPELINED       = 1'b1,                  // 1: adam16_pipe_core, 0: adam16_core
  parameter int DEBOUNCE_CYCLES = 200_000,               // 2 ms at 100 MHz
  parameter     MEM_INIT        = "adam16_sum_array.mem"  // program image ($readmemh)
) (
  input  logic        clk,       // onboard 100 MHz oscillator
  input  logic        btn_rst,   // btnC
  input  logic        btn_step,  // btnU
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [15:0] sw,        // only sw[1:0] (LED view select) is used
  /* verilator lint_on UNUSEDSIGNAL */
  output logic [15:0] led
);

  logic rst, step;

  debounce #(.CYCLES(DEBOUNCE_CYCLES)) db_rst  (.clk(clk), .btn_in(btn_rst),  .btn_clean(rst), .btn_pulse());
  debounce #(.CYCLES(DEBOUNCE_CYCLES)) db_step (.clk(clk), .btn_in(btn_step), .btn_clean(),    .btn_pulse(step));

  logic [15:0] dbg_pc, dbg_ir, dbg_alu_y;
  logic        dbg_n, dbg_z, dbg_p;

  if (PIPELINED) begin : g_pipe
    logic [15:0] imem_addr, imem_rdata, dmem_addr, dmem_wdata, dmem_rdata;
    logic        dmem_we;

    adam16_pipe_core u_cpu (
      .clk       (clk),
      .rst       (rst),
      .ce        (step),
      .imem_addr (imem_addr),
      .imem_rdata(imem_rdata),
      .dmem_addr (dmem_addr),
      .dmem_wdata(dmem_wdata),
      .dmem_we   (dmem_we),
      .dmem_rdata(dmem_rdata),
      .dbg_pc    (dbg_pc),
      .dbg_ir    (dbg_ir),
      .dbg_alu_y (dbg_alu_y),
      .dbg_n     (dbg_n),
      .dbg_z     (dbg_z),
      .dbg_p     (dbg_p)
    );

    adam16_dpram #(
      .INIT_FILE(MEM_INIT)
    ) u_mem (
      .clk    (clk),
      .en     (step),
      .a_addr (imem_addr),
      .a_rdata(imem_rdata),
      .b_addr (dmem_addr),
      .b_we   (dmem_we),
      .b_wdata(dmem_wdata),
      .b_rdata(dmem_rdata)
    );
  end else begin : g_multi
    logic [15:0] mem_addr, mem_wdata, mem_rdata;
    logic        mem_we;

    adam16_core u_cpu (
      .clk      (clk),
      .rst      (rst),
      .ce       (step),
      .mem_rdata(mem_rdata),
      .mem_addr (mem_addr),
      .mem_wdata(mem_wdata),
      .mem_we   (mem_we),
      .dbg_pc   (dbg_pc),
      .dbg_ir   (dbg_ir),
      .dbg_alu_y(dbg_alu_y),
      .dbg_n    (dbg_n),
      .dbg_z    (dbg_z),
      .dbg_p    (dbg_p)
    );

    adam16_sram #(
      .INIT_FILE(MEM_INIT)
    ) u_mem (
      .clk  (clk),
      .en   (step),
      .we   (mem_we),
      .addr (mem_addr),
      .wdata(mem_wdata),
      .rdata(mem_rdata)
    );
  end

  // sw[1:0] selects the debug view on the LEDs; sw[15:2] unused.
  //   00 = PC   01 = IR   10 = ALU output / result   11 = flags {N,Z,P}
  always_comb begin
    unique case (sw[1:0])
      2'b00:   led = dbg_pc;
      2'b01:   led = dbg_ir;
      2'b10:   led = dbg_alu_y;
      default: led = {13'b0, dbg_n, dbg_z, dbg_p};
    endcase
  end

endmodule
