// 64K x 16 dual-port memory with registered (synchronous) reads, for the
// pipelined core: port A fetches instructions, port B reads and writes data.
// Nothing happens on a clock edge unless en = 1 (connect it to the core's ce).
// When it does:
//   a_rdata <= mem[a_addr]
//   b_rdata <= mem[b_addr]        (the old contents during a write)
//   mem[b_addr] <= b_wdata        if b_we = 1
// If port A reads the word port B writes on the same edge, it gets the old word.
// Maps onto one true dual-port block RAM per 16 KB on an FPGA.
module adam16_dpram #(
  parameter INIT_FILE = ""
) (
  input  wire        clk,
  input  wire        en,

  input  wire [15:0] a_addr,
  output reg  [15:0] a_rdata,

  input  wire [15:0] b_addr,
  input  wire        b_we,
  input  wire [15:0] b_wdata,
  output reg  [15:0] b_rdata
);
  reg [15:0] mem [0:65535];

  initial begin
    if (INIT_FILE != "") $readmemh(INIT_FILE, mem);
  end

  always @(posedge clk) begin
    if (en) a_rdata <= mem[a_addr];
  end

  always @(posedge clk) begin
    if (en) begin
      if (b_we) mem[b_addr] <= b_wdata;
      b_rdata <= mem[b_addr];
    end
  end

endmodule
