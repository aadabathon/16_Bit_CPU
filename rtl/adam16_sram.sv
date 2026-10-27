// 64K x 16 single-port memory with a registered (synchronous) read.
// Nothing happens on a clock edge unless en = 1 (connect it to the core's ce).
// When it does: rdata <= mem[addr] (the old contents during a write), and
// mem[addr] <= wdata if we = 1.
module adam16_sram #(
  parameter INIT_FILE = ""
) (
  input  wire        clk,
  input  wire        en,
  input  wire        we,
  input  wire [15:0] addr,
  input  wire [15:0] wdata,
  output reg  [15:0] rdata
);
  reg [15:0] mem [0:65535];

  initial begin
    if (INIT_FILE != "") $readmemh(INIT_FILE, mem);
  end

  always @(posedge clk) begin
    if (en) begin
      if (we) mem[addr] <= wdata;
      rdata <= mem[addr];
    end
  end

endmodule
