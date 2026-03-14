module cpu16_datapath (
  input  logic        clk,
  input  logic        rst,

  input  logic [15:0] mem_rdata,
  output logic [15:0] mem_addr,
  output logic [15:0] mem_wdata,

  input  logic        pc_we,
  input  logic        ir_we,
  input  logic        mar_we,
  input  logic        mdr_we,
  input  logic        reg_we,
  input  logic        flag_we,
  input  logic [2:0]  reg_dst,
  input  logic [1:0]  wb_sel,
  input  logic [2:0]  alu_op,
  input  logic [1:0]  alu_a_sel,
  input  logic [2:0]  alu_b_sel,
  input  logic [1:0]  pc_src_sel,
  input  logic [1:0]  mar_src_sel,

  output logic [15:0] ir,
  output logic        N,
  output logic        Z,
  output logic        P,
  output logic [15:0] pc
);

  import cpu16_isa::*;

  logic [15:0] mar, mdr;

  logic [2:0]  ra0, ra1, ra2;
  logic [15:0] rd0, rd1, rd2;

  logic [15:0] alu_a, alu_b, alu_y;
  logic        alu1_mode;

  logic [15:0] wb_data;
  logic [15:0] pc_next;
  logic [15:0] mar_next;

  logic [3:0]  op;
  logic [2:0]  funct;
  logic [5:0]  imm6;
  logic [8:0]  off9;
  logic [10:0] pcoff11;
  logic [11:0] trapvect12;

  assign op         = ir[15:12];
  assign funct      = ir[2:0];
  assign imm6       = ir[5:0];
  assign off9       = ir[8:0];
  assign pcoff11    = ir[10:0];
  assign trapvect12 = ir[11:0];

  cpu16_regfile rf(
    .clk(clk), .rst(rst),
    .ra0(ra0), .ra1(ra1), .ra2(ra2),
    .rd0(rd0), .rd1(rd1), .rd2(rd2),
    .we(reg_we), .wa(reg_dst), .wd(wb_data)
  );

  always_comb begin
    ra0 = ir[8:6];
    ra1 = ir[5:3];
    if (op == OP_RET) ra2 = 3'b111;
    else              ra2 = ir[11:9];
  end

  always_comb begin
    unique case (alu_a_sel)
      2'b00: alu_a = rd0;
      2'b01: alu_a = pc;
      default: alu_a = 16'h0000;
    endcase

    unique case (alu_b_sel)
      3'b000: alu_b = rd1;
      3'b001: alu_b = sext6(imm6);
      3'b010: alu_b = zext6(imm6);
      3'b011: alu_b = sext9(off9);
      3'b100: alu_b = sext6(imm6);
      default: alu_b = 16'h0000;
    endcase

    alu1_mode = (op == OP_ALU1);
    if (alu1_mode && (funct == ALU1_CMP)) alu1_mode = 1'b0;
  end

  cpu16_alu alu0(
    .alu1_mode(alu1_mode),
    .op(alu_op),
    .a(alu_a),
    .b(alu_b),
    .y(alu_y)
  );

  always_comb begin
    unique case (wb_sel)
      2'b00: wb_data = alu_y;
      2'b01: wb_data = mdr;
      2'b10: wb_data = pc;
      default: wb_data = 16'h0000;
    endcase
  end

  always_comb begin
    unique case (pc_src_sel)
      2'b00: pc_next = (op == OP_TRAP) ? {4'b0000, trapvect12} : 16'h0000;
      2'b01: pc_next = pc + 16'h0001;
      2'b10: begin
        if ((op == OP_JSR) && (ir[11] == 1'b0)) pc_next = pc + sext11(pcoff11);
        else                                     pc_next = pc + sext9(off9);
      end
      2'b11: pc_next = (op == OP_RET) ? rd2 : rd0;
      default: pc_next = pc;
    endcase
  end

  always_comb begin
    unique case (mar_src_sel)
      2'b00: mar_next = pc;
      2'b01: mar_next = alu_y;
      default: mar_next = mar;
    endcase
  end

  always_ff @(posedge clk) begin
    if (rst) begin
      pc  <= 16'h0000;
      ir  <= 16'h0000;
      mar <= 16'h0000;
      mdr <= 16'h0000;
      N   <= 1'b0;
      Z   <= 1'b0;
      P   <= 1'b0;
    end else begin
      if (pc_we)  pc  <= pc_next;
      if (ir_we)  ir  <= mem_rdata;
      if (mar_we) mar <= mar_next;
      if (mdr_we) mdr <= mem_rdata;

      if (flag_we) begin
        N <= wb_data[15];
        Z <= (wb_data == 16'h0000);
        P <= (~wb_data[15]) & (wb_data != 16'h0000);
      end
    end
  end

  assign mem_addr  = mar;
  assign mem_wdata = rd2;

endmodule
  