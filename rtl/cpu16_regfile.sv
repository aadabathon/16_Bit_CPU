module cpu16_regfile (
  input  logic        clk,
  input  logic        rst,

  input  logic [2:0]  ra0,
  input  logic [2:0]  ra1,
  input  logic [2:0]  ra2,
  output logic [15:0] rd0,
  output logic [15:0] rd1,
  output logic [15:0] rd2,

  input  logic        we,
  input  logic [2:0]  wa,
  input  logic [15:0] wd
);
  logic [15:0] r[0:7];

  always_ff @(posedge clk) begin
    if (rst) begin
      r[0] <= 16'h0000; r[1] <= 16'h0000; r[2] <= 16'h0000; r[3] <= 16'h0000;
      r[4] <= 16'h0000; r[5] <= 16'h0000; r[6] <= 16'h0000; r[7] <= 16'h0000;
    end else begin
      if (we) r[wa] <= wd;
    end
  end

  always_comb begin
    rd0 = r[ra0];
    rd1 = r[ra1];
    rd2 = r[ra2];
  end
endmodule
