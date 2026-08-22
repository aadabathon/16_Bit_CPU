// Basys3 top level: wraps cpu16_core + instruction/data memory so the raw
// mem_* bus never reaches package pins, and lets a human single-step the
// CPU with a button instead of free-running at 100 MHz.
module basys3_top (
  input  logic        clk,       // onboard 100 MHz oscillator
  input  logic        btn_rst,   // btnC
  input  logic        btn_step,  // btnU
  input  logic [15:0] sw,
  output logic [15:0] led
);

  logic rst_clean, rst_pulse;
  logic step_clean, step_pulse;

  debounce db_rst  (.clk(clk), .btn_in(btn_rst),  .btn_clean(rst_clean),  .btn_pulse(rst_pulse));
  debounce db_step (.clk(clk), .btn_in(btn_step), .btn_clean(step_clean), .btn_pulse(step_pulse));

  // The core only sees a clock edge when the user presses step (or reset,
  // so the reset value is guaranteed to actually latch on that edge).
  logic core_clk;
  assign core_clk = step_pulse | rst_pulse;

  logic [15:0] mem_addr, mem_wdata, mem_rdata;
  logic        mem_we;

  logic [15:0] dbg_pc, dbg_ir, dbg_alu_y;
  logic        dbg_n, dbg_z, dbg_p;

  cpu16_core u_cpu (
    .clk      (core_clk),
    .rst      (rst_clean),
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

  SramSBC #(
    .INIT_FILE("C:/Users/adams/Projects/16_Bit_CPU/fpga/mem/cpu16_sum_array.mem")
  ) imem (
    .clk  (core_clk),
    .we   (mem_we),
    .addr (mem_addr),
    .wdata(mem_wdata),
    .rdata(mem_rdata)
  );

  // sw[1:0] selects the debug view on the LEDs; sw[15:2] unused.
  //   00 = PC   01 = IR   10 = ALU result   11 = flags {N,Z,P}
  always_comb begin
    unique case (sw[1:0])
      2'b00:   led = dbg_pc;
      2'b01:   led = dbg_ir;
      2'b10:   led = dbg_alu_y;
      default: led = {13'b0, dbg_n, dbg_z, dbg_p};
    endcase
  end

endmodule
