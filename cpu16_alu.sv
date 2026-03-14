module cpu16_alu (
  input  logic        alu1_mode,
  input  logic [2:0]  op,
  input  logic [15:0] a,
  input  logic [15:0] b,
  output logic [15:0] y
);
  always_comb begin
    y = 16'h0000;
    if (!alu1_mode) begin
      unique case (op)
        3'b000: y = a + b;
        3'b001: y = a - b;
        3'b010: y = ~a;
        3'b011: y = a & b;
        3'b100: y = a | b;
        3'b101: y = a ^ b;
        3'b110: y = a;
        3'b111: y = 16'h0000 - a;
        default: y = 16'h0000;
      endcase
    end else begin
      unique case (op)
        3'b000: y = ~(a & b);
        3'b001: y = ~(a | b);
        3'b010: y = a + 16'h0001;
        3'b011: y = a - 16'h0001;
        3'b100: y = a << 1;
        3'b101: y = a >> 1;
        3'b110: y = $signed(a) >>> 1;
        3'b111: y = a - b;
        default: y = 16'h0000;
      endcase
    end
  end
endmodule
