// op = {group, funct}: op[3]=0 selects ALU0 ops, op[3]=1 selects ALU1 ops.
module cpu16_alu (
  input  logic [3:0]  op,
  input  logic [15:0] a,
  input  logic [15:0] b,
  output logic [15:0] y
);
  always_comb begin
    y = 16'h0000;
    if (!op[3]) begin
      unique case (op[2:0])
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
      unique case (op[2:0])
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
