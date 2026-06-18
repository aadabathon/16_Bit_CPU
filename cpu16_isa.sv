package cpu16_isa;

  typedef logic [15:0] instr_t;

  typedef enum logic [3:0] {
    OP_ALU0  = 4'h0,
    OP_ALU1  = 4'h1,
    OP_ADDI  = 4'h2,
    OP_ANDI  = 4'h3,
    OP_LD    = 4'h4,
    OP_ST    = 4'h5,
    OP_JMP   = 4'h6,
    OP_JSR   = 4'h7,
    OP_RET   = 4'h8,
    OP_TRAP  = 4'h9,
    OP_LDR   = 4'hA,
    OP_STR   = 4'hB,
    OP_LEA   = 4'hC,
    OP_BR    = 4'hD,
    OP_UD_E  = 4'hE,
    OP_UD_F  = 4'hF
  } opcode_t;

  typedef enum logic [2:0] {
    ALU0_ADD = 3'b000,
    ALU0_SUB = 3'b001,
    ALU0_NOT = 3'b010,
    ALU0_AND = 3'b011,
    ALU0_OR  = 3'b100,
    ALU0_XOR = 3'b101,
    ALU0_MOV = 3'b110,
    ALU0_NEG = 3'b111
  } alu0_funct_t;

  typedef enum logic [2:0] {
    ALU1_NAND = 3'b000,
    ALU1_NOR  = 3'b001,
    ALU1_INC  = 3'b010,
    ALU1_DEC  = 3'b011,
    ALU1_LSL1 = 3'b100,
    ALU1_LSR1 = 3'b101,
    ALU1_ASR1 = 3'b110,
    ALU1_CMP  = 3'b111
  } alu1_funct_t;

  typedef struct packed {
    opcode_t op;
    logic [2:0] dr;
    logic [2:0] sr1;
    logic [2:0] sr2;
    logic [2:0] funct;
    logic [5:0] imm6;
    logic [8:0] off9;
    logic [10:0] pcoff11;
    logic [11:0] trapvect12;
    logic [2:0] nzp_mask;
    logic jsr_is_reg;
  } dec_t;

  function automatic dec_t decode(input instr_t ir);
    dec_t d;
    d.op         = opcode_t'(ir[15:12]);
    d.dr         = ir[11:9];
    d.sr1        = ir[8:6];
    d.sr2        = ir[5:3];
    d.funct      = ir[2:0];
    d.imm6       = ir[5:0];
    d.off9       = ir[8:0];
    d.pcoff11    = ir[10:0];
    d.trapvect12 = ir[11:0];
    d.nzp_mask   = ir[11:9];
    d.jsr_is_reg = ir[11];
    return d;
  endfunction

  function automatic logic signed [15:0] sext6(input logic [5:0] x);
    return {{10{x[5]}}, x};
  endfunction

  function automatic logic signed [15:0] sext9(input logic [8:0] x);
    return {{7{x[8]}}, x};
  endfunction

  function automatic logic signed [15:0] sext11(input logic [10:0] x);
    return {{5{x[10]}}, x};
  endfunction

  function automatic logic [15:0] zext6(input logic [5:0] x);
    return {10'b0, x};
  endfunction

endpackage
