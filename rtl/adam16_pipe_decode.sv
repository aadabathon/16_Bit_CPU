// Instruction decode for adam16_pipe_core (ID stage). Purely combinational.
//
// Every instruction goes through the one ALU in EX, so its result, its
// memory address and its branch or jump target are all the ALU output:
//
//   a = R[ra0] | PC+1 | 0  (a_sel)          b = R[ra1] | imm  (b_imm)
//
//   ALU ops, ADDI, ANDI  R[sr1] op (R[sr2] | imm)   -> result, flags
//   LD ST LEA BR         PC+1 + SEXT(off9)          -> address / result / target
//   LDR STR              R[base] + SEXT(off6)       -> address
//   JSR                  PC+1 + SEXT(off11)         -> target  (R7 <- PC+1)
//   JMP JSRR RET         MOV R[base] (R7 for RET)   -> target
//   TRAP                 0 + ZEXT(trapvect12)       -> target  (R7 <- PC+1)
//
// The table in docs/07_pipeline.md comes from docs/tools/pipe_decode_spec.py,
// and `make -C docs check` checks this module against it for all 65536 words.
module adam16_pipe_decode (
  input  logic [15:0] ir,

  output logic [2:0]  ra0,       // read port 0: SR1 / BaseR, R7 for RET
  output logic [2:0]  ra1,       // read port 1: SR2, the source SR for ST / STR
  output logic [2:0]  rd,        // destination: DR, R7 for JSR / JSRR / TRAP
  output logic        reg_we,
  output logic        flag_we,
  output logic        mem_we,
  output logic [1:0]  wb_sel,    // 0 = ALU, 1 = PC+1 (link), 2 = load data

  output logic [3:0]  alu_op,    // {group, funct}, as adam16_alu
  output logic [1:0]  a_sel,     // 0 = R[ra0], 1 = PC+1, 2 = zero
  output logic        b_imm,     // 0 = R[ra1], 1 = imm
  output logic [15:0] imm,

  output logic [2:0]  br_mask,   // BR: IR[11:9] (n z p); 0 for everything else
  output logic        jump       // JMP JSR JSRR RET TRAP: always redirect
);

  import adam16_isa::*;

  localparam logic [3:0] ALU_ADD = 4'b0000;
  localparam logic [3:0] ALU_AND = 4'b0011;
  localparam logic [3:0] ALU_MOV = 4'b0110;

  opcode_t op;
  assign op = opcode_t'(ir[15:12]);

  always_comb begin
    ra0     = ir[8:6];
    ra1     = ir[5:3];
    rd      = ir[11:9];
    reg_we  = 1'b0;
    flag_we = 1'b0;
    mem_we  = 1'b0;
    wb_sel  = 2'd0;
    alu_op  = ALU_ADD;
    a_sel   = 2'd0;
    b_imm   = 1'b0;
    imm     = 16'h0000;
    br_mask = 3'b000;
    jump    = 1'b0;

    unique case (op)
      OP_ALU0, OP_ALU1: begin
        alu_op  = {ir[12], ir[2:0]};
        reg_we  = !(ir[12] && ir[2:0] == ALU1_CMP);   // CMP sets only the flags
        flag_we = 1'b1;
      end
      OP_ADDI: begin
        imm = sext6(ir[5:0]);  b_imm = 1'b1;  reg_we = 1'b1;  flag_we = 1'b1;
      end
      OP_ANDI: begin
        imm = zext6(ir[5:0]);  b_imm = 1'b1;  reg_we = 1'b1;  flag_we = 1'b1;
        alu_op = ALU_AND;
      end
      OP_LD, OP_LEA: begin
        imm = sext9(ir[8:0]);  b_imm = 1'b1;  a_sel = 2'd1;  reg_we = 1'b1;
        wb_sel = (op == OP_LD) ? 2'd2 : 2'd0;
      end
      OP_ST: begin
        imm = sext9(ir[8:0]);  b_imm = 1'b1;  a_sel = 2'd1;  mem_we = 1'b1;
        ra1 = ir[11:9];
      end
      OP_LDR: begin
        imm = sext6(ir[5:0]);  b_imm = 1'b1;  reg_we = 1'b1;  wb_sel = 2'd2;
      end
      OP_STR: begin
        imm = sext6(ir[5:0]);  b_imm = 1'b1;  mem_we = 1'b1;
        ra1 = ir[11:9];
      end
      OP_BR: begin
        imm = sext9(ir[8:0]);  b_imm = 1'b1;  a_sel = 2'd1;
        br_mask = ir[11:9];
      end
      OP_JMP: begin
        alu_op = ALU_MOV;  jump = 1'b1;
      end
      OP_RET: begin
        alu_op = ALU_MOV;  jump = 1'b1;  ra0 = 3'd7;
      end
      OP_JSR: begin
        jump = 1'b1;  reg_we = 1'b1;  rd = 3'd7;  wb_sel = 2'd1;
        if (ir[11]) begin                                   // JSRR BaseR
          alu_op = ALU_MOV;
        end else begin                                      // JSR off11
          imm = sext11(ir[10:0]);  b_imm = 1'b1;  a_sel = 2'd1;
        end
      end
      OP_TRAP: begin
        imm = {4'h0, ir[11:0]};  b_imm = 1'b1;  a_sel = 2'd2;
        jump = 1'b1;  reg_we = 1'b1;  rd = 3'd7;  wb_sel = 2'd1;
      end
      default: ;                                            // 0xE, 0xF: no-op
    endcase
  end

endmodule
