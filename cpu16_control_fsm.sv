module cpu16_control_fsm ( //GPT generated
  input  logic        clk,
  input  logic        rst,
  input  logic [15:0] ir,
  input  logic        N,
  input  logic        Z,
  input  logic        P,

  output logic        pc_we,
  output logic        ir_we,
  output logic        mar_we,
  output logic        mdr_we,
  output logic        reg_we,
  output logic        flag_we,
  output logic        mem_we,

  output logic [2:0]  reg_dst,
  output logic [1:0]  wb_sel,
  output logic [2:0]  alu_op,
  output logic [1:0]  alu_a_sel,
  output logic [2:0]  alu_b_sel,
  output logic [1:0]  pc_src_sel,
  output logic [1:0]  mar_src_sel
);

  import cpu16_isa::*;

  typedef enum logic [4:0] {
    S_RESET     = 5'd0,
    S_IF0       = 5'd1,
    S_IF1       = 5'd2,
    S_ID        = 5'd3,
    S_EX_ALU    = 5'd4,
    S_EX_EA     = 5'd5,
    S_MEM_RD0   = 5'd6,
    S_MEM_RD1   = 5'd7,
    S_WB_LD     = 5'd8,
    S_MEM_WR0   = 5'd9,
    S_EX_BR     = 5'd10,
    S_EX_JMP    = 5'd11,
    S_EX_JSR    = 5'd12,
    S_EX_TRAP   = 5'd13
  } state_t;

  state_t state, state_n;

  dec_t d;
  logic take_br;
  logic is_cmp;

  always_comb begin
    d = decode(ir);
    is_cmp  = (d.op == OP_ALU1) && (d.funct == ALU1_CMP);
    take_br = (d.nzp_mask[2] & N) | (d.nzp_mask[1] & Z) | (d.nzp_mask[0] & P);
  end

  always_ff @(posedge clk) begin
    if (rst) state <= S_RESET;
    else     state <= state_n;
  end

  always_comb begin
    pc_we       = 1'b0;
    ir_we       = 1'b0;
    mar_we      = 1'b0;
    mdr_we      = 1'b0;
    reg_we      = 1'b0;
    flag_we     = 1'b0;
    mem_we      = 1'b0;

    reg_dst     = 3'b000;
    wb_sel      = 2'b00;
    alu_op      = 3'b000;
    alu_a_sel   = 2'b00;
    alu_b_sel   = 3'b000;
    pc_src_sel  = 2'b00;
    mar_src_sel = 2'b00;

    state_n = state;

    unique case (state)
      S_RESET: begin
        pc_we      = 1'b1;
        pc_src_sel = 2'b00;
        state_n    = S_IF0;
      end

      S_IF0: begin
        mar_we      = 1'b1;
        mar_src_sel = 2'b00;
        state_n     = S_IF1;
      end

      S_IF1: begin
        ir_we      = 1'b1;
        pc_we      = 1'b1;
        pc_src_sel = 2'b01;
        state_n    = S_ID;
      end

      S_ID: begin
        unique case (d.op)
          OP_ALU0, OP_ALU1, OP_ADDI, OP_ANDI, OP_LEA: state_n = S_EX_ALU;
          OP_LD, OP_LDR, OP_ST, OP_STR:              state_n = S_EX_EA;
          OP_BR:                                     state_n = S_EX_BR;
          OP_JMP, OP_RET:                            state_n = S_EX_JMP;
          OP_JSR:                                    state_n = S_EX_JSR;
          OP_TRAP:                                   state_n = S_EX_TRAP;
          default:                                   state_n = S_IF0;
        endcase
      end

      S_EX_ALU: begin
        reg_dst = d.dr;
        reg_we  = 1'b1;
        flag_we = 1'b1;
        wb_sel  = 2'b00;

        unique case (d.op)
          OP_ALU0: begin
            alu_a_sel = 2'b00;
            alu_b_sel = 3'b000;
            alu_op    = d.funct;
            if (d.funct == ALU0_NOT || d.funct == ALU0_NEG) alu_b_sel = 3'b111;
          end

          OP_ALU1: begin
            alu_a_sel = 2'b00;
            alu_b_sel = 3'b000;
            alu_op    = d.funct;
            if (d.funct == ALU1_INC || d.funct == ALU1_DEC ||
                d.funct == ALU1_LSL1 || d.funct == ALU1_LSR1 ||
                d.funct == ALU1_ASR1) alu_b_sel = 3'b111;
            if (is_cmp) begin
              reg_we    = 1'b0;
              reg_dst   = 3'b000;
              alu_op    = 3'b001;
              alu_b_sel = 3'b000;
            end
          end

          OP_ADDI: begin
            alu_a_sel = 2'b00;
            alu_b_sel = 3'b001;
            alu_op    = 3'b000;
          end

          OP_ANDI: begin
            alu_a_sel = 2'b00;
            alu_b_sel = 3'b010;
            alu_op    = 3'b011;
          end

          OP_LEA: begin
            alu_a_sel = 2'b01;
            alu_b_sel = 3'b011;
            alu_op    = 3'b000;
          end

          default: begin end
        endcase

        state_n = S_IF0;
      end

      S_EX_EA: begin
        mar_we      = 1'b1;
        mar_src_sel = 2'b01;

        unique case (d.op)
          OP_LD, OP_ST: begin
            alu_a_sel = 2'b01;
            alu_b_sel = 3'b011;
            alu_op    = 3'b000;
          end
          OP_LDR, OP_STR: begin
            alu_a_sel = 2'b00;
            alu_b_sel = 3'b100;
            alu_op    = 3'b000;
          end
          default: begin end
        endcase

        if (d.op == OP_LD || d.op == OP_LDR) state_n = S_MEM_RD0;
        else                                  state_n = S_MEM_WR0;
      end

      S_MEM_RD0: begin
        state_n = S_MEM_RD1;
      end

      S_MEM_RD1: begin
        mdr_we  = 1'b1;
        state_n = S_WB_LD;
      end

      S_WB_LD: begin
        reg_we  = 1'b1;
        reg_dst = d.dr;
        wb_sel  = 2'b01;
        state_n = S_IF0;
      end

      S_MEM_WR0: begin
        mem_we  = 1'b1;
        state_n = S_IF0;
      end

      S_EX_BR: begin
        if (take_br) begin
          pc_we      = 1'b1;
          pc_src_sel = 2'b10;
        end
        state_n = S_IF0;
      end

      S_EX_JMP: begin
        pc_we      = 1'b1;
        pc_src_sel = 2'b11;
        state_n    = S_IF0;
      end

      S_EX_JSR: begin
        reg_we  = 1'b1;
        reg_dst = 3'b111;
        wb_sel  = 2'b10;

        pc_we = 1'b1;
        if (d.jsr_is_reg) pc_src_sel = 2'b11;
        else              pc_src_sel = 2'b10;

        state_n = S_IF0;
      end

      S_EX_TRAP: begin
        reg_we  = 1'b1;
        reg_dst = 3'b111;
        wb_sel  = 2'b10;

        pc_we      = 1'b1;
        pc_src_sel = 2'b00;
        state_n    = S_IF0;
      end

      default: begin
        state_n = S_IF0;
      end
    endcase
  end

endmodule
