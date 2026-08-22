module SramSBC #(
  parameter INIT_FILE = ""
) (
  input  wire        clk,
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
    if (we) mem[addr] <= wdata;
    rdata <= mem[addr];
  end

endmodule
