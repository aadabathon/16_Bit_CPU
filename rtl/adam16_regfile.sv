// 8 x 16 register file: two asynchronous read ports, one synchronous write port.
// BYPASS = 1 makes a read of the register being written return the new value
// in the same cycle (write-first), which the pipelined core needs. The
// multicycle core must use BYPASS = 0: its write data is computed from its own
// read data in the same cycle, so a bypass would form a combinational loop.
module adam16_regfile #(
  parameter bit BYPASS = 1'b0
) (
  input  logic        clk,
  input  logic        rst,
  input  logic        ce,

  input  logic [2:0]  ra0,
  input  logic [2:0]  ra1,
  output logic [15:0] rd0,
  output logic [15:0] rd1,

  input  logic        we,
  input  logic [2:0]  wa,
  input  logic [15:0] wd
);
  logic [15:0] r[0:7];

  always_ff @(posedge clk) begin
    if (rst) begin
      r[0] <= 16'h0000; r[1] <= 16'h0000; r[2] <= 16'h0000; r[3] <= 16'h0000;
      r[4] <= 16'h0000; r[5] <= 16'h0000; r[6] <= 16'h0000; r[7] <= 16'h0000;
    end else if (ce) begin
      if (we) r[wa] <= wd;
    end
  end

  always_comb begin
    rd0 = (BYPASS && we && wa == ra0) ? wd : r[ra0];
    rd1 = (BYPASS && we && wa == ra1) ? wd : r[ra1];
  end
endmodule
