module control_fsm (
  input  wire        clk,
  input  wire        rst,
  input  wire [15:0] ir,
  input  wire        z_flag,

  output reg         pc_we,
  output reg  [1:0]  pc_sel,
  output reg         ir_we,

  output reg         mem_we,
  output reg         reg_we,
  output reg         mdr_we,

  output reg         wb_sel,
  output reg  [3:0]  alu_op,
  output reg         alu_a_sel,
  output reg  [1:0]  alu_b_sel,
  output reg         addr_sel
);

  localparam S_IF0      = 4'd0;
  localparam S_IF1      = 4'd1;
  localparam S_ID       = 4'd2;
  localparam S_EX_R     = 4'd3;
  localparam S_EX_ADDI  = 4'd4;
  localparam S_EX_ADDR  = 4'd5;
  localparam S_MEM_RD0  = 4'd6;
  localparam S_MEM_RD1  = 4'd7;
  localparam S_WB_LD    = 4'd8;
  localparam S_MEM_WR0  = 4'd9;
  localparam S_WB_ALU   = 4'd10;
  localparam S_EX_BR    = 4'd11;
  localparam S_EX_JMP   = 4'd12;
  localparam S_HALT     = 4'd13;

  reg [3:0] state, nstate;

  wire [3:0] opcode = ir[15:12];

  localparam OP_ALUR  = 4'h0;
  localparam OP_ADDI  = 4'h1;
  localparam OP_LD    = 4'h4;
  localparam OP_ST    = 4'h5;
  localparam OP_BEQ   = 4'h6;
  localparam OP_BNE   = 4'h7;
  localparam OP_JMP   = 4'h8;
  localparam OP_HALT  = 4'hF;

  always @(posedge clk) begin
    if (rst) state <= S_IF0;
    else state <= nstate;
  end

  always @(*) begin
    pc_we    = 1'b0;
    pc_sel   = 2'd0;
    ir_we    = 1'b0;

    mem_we   = 1'b0;
    reg_we   = 1'b0;
    mdr_we   = 1'b0;

    wb_sel   = 1'b0;

    alu_op   = 4'd0;
    alu_a_sel= 1'b0;
    alu_b_sel= 2'd0;

    addr_sel = 1'b0;

    nstate   = state;

    case (state)
      S_IF0: begin
        addr_sel = 1'b0;
        nstate   = S_IF1;
      end

      S_IF1: begin
        ir_we    = 1'b1;
        pc_we    = 1'b1;
        pc_sel   = 2'd0;
        nstate   = S_ID;
      end

      S_ID: begin
        case (opcode)
          OP_ALUR: nstate = S_EX_R;
          OP_ADDI: nstate = S_EX_ADDI;
          OP_LD:   nstate = S_EX_ADDR;
          OP_ST:   nstate = S_EX_ADDR;
          OP_BEQ:  nstate = S_EX_BR;
          OP_BNE:  nstate = S_EX_BR;
          OP_JMP:  nstate = S_EX_JMP;
          OP_HALT: nstate = S_HALT;
          default: nstate = S_HALT;
        endcase
      end

      S_EX_R: begin
        alu_a_sel = 1'b0;
        alu_b_sel = 2'd0;
        alu_op    = {1'b0, ir[2:0]};
        nstate    = S_WB_ALU;
      end

      S_EX_ADDI: begin
        alu_a_sel = 1'b0;
        alu_b_sel = 2'd1;
        alu_op    = 4'h0;
        nstate    = S_WB_ALU;
      end

      S_EX_ADDR: begin
        alu_a_sel = 1'b0;
        alu_b_sel = 2'd1;
        alu_op    = 4'h0;
        if (opcode == OP_LD) nstate = S_MEM_RD0;
        else nstate = S_MEM_WR0;
      end

      S_MEM_RD0: begin
        addr_sel = 1'b1;
        nstate   = S_MEM_RD1;
      end

      S_MEM_RD1: begin
        mdr_we   = 1'b1;
        nstate   = S_WB_LD;
      end

      S_WB_LD: begin
        reg_we = 1'b1;
        wb_sel = 1'b1;
        nstate = S_IF0;
      end

      S_MEM_WR0: begin
        addr_sel = 1'b1;
        mem_we   = 1'b1;
        nstate   = S_IF0;
      end

      S_WB_ALU: begin
        reg_we = 1'b1;
        wb_sel = 1'b0;
        nstate = S_IF0;
      end

      S_EX_BR: begin
        alu_a_sel = 1'b0;
        alu_b_sel = 2'd0;
        alu_op    = 4'h8;
        if (opcode == OP_BEQ) begin
          if (z_flag) begin pc_we = 1'b1; pc_sel = 2'd1; end
        end else begin
          if (!z_flag) begin pc_we = 1'b1; pc_sel = 2'd1; end
        end
        nstate = S_IF0;
      end

      S_EX_JMP: begin
        pc_we  = 1'b1;
        pc_sel = 2'd2;
        nstate = S_IF0;
      end

      S_HALT: begin
        nstate = S_HALT;
      end

      default: begin
        nstate = S_HALT;
      end
    endcase
  end

endmodule
