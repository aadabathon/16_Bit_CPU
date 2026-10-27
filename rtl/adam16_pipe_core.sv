// adam16, 5-stage pipeline: IF ID EX MEM WB. Same ISA and the same results as
// adam16_core (the regression compares them instruction by instruction), in
// about a fifth of the cycles.
//
//   IF   imem_addr = the next PC. The memory's read register is the IF/ID
//        instruction register.
//   ID   decode (adam16_pipe_decode); read the register file, which is
//        write-first, so a value being written in WB needs no forwarding.
//   EX   forward operands from MEM and WB; run the ALU, whose output is the
//        result, the data address and the branch / jump target; present the
//        address and store data to the data port; update N Z P; resolve the
//        branch. A taken branch or a jump redirects fetch in this same cycle
//        and squashes the one instruction in ID: one bubble.
//   MEM  load data arrives from the data port's read register, in time to be
//        forwarded to the next instruction, now in EX.
//   WB   write the register file.
//
// Nothing ever stalls. Every memory access happens on the edge that ends EX,
// in program order. The fetch port does not see stores to the next two
// instruction words (no self-modifying code there).
module adam16_pipe_core (
  input  logic        clk,
  input  logic        rst,
  input  logic        ce,          // clock enable: 1 = advance on this edge

  output logic [15:0] imem_addr,   // to the fetch port (registered read)
  input  logic [15:0] imem_rdata,

  output logic [15:0] dmem_addr,   // to the data port (registered read)
  output logic [15:0] dmem_wdata,
  output logic        dmem_we,
  input  logic [15:0] dmem_rdata,

  output logic [15:0] dbg_pc,      // the instruction retiring (in WB)
  output logic [15:0] dbg_ir,      //   NOP (0xD000) for a bubble
  output logic [15:0] dbg_alu_y,   //   its result
  output logic        dbg_n,       //   the flags after it
  output logic        dbg_z,
  output logic        dbg_p
);

  // ================================================================== IF
  logic [15:0] f_pc;               // next sequential fetch address
  logic        redirect;           // from EX: taken branch or jump
  logic [15:0] target;

  assign imem_addr = redirect ? target : f_pc;

  // IF/ID. The instruction word itself is imem_rdata.
  logic        d_valid;
  logic [15:0] d_pc;

  always_ff @(posedge clk) begin
    if (rst) begin
      f_pc    <= 16'h0000;
      d_pc    <= 16'h0000;
      d_valid <= 1'b0;
    end else if (ce) begin
      f_pc    <= imem_addr + 16'd1;
      d_pc    <= imem_addr;
      d_valid <= 1'b1;
    end
  end

  // ================================================================== ID
  logic [15:0] d_ir;
  logic [2:0]  d_ra0, d_ra1, d_rd;
  logic        d_reg_we, d_flag_we, d_mem_we, d_b_imm, d_jump;
  logic [1:0]  d_wb_sel, d_a_sel;
  logic [3:0]  d_alu_op;
  logic [15:0] d_imm;
  logic [2:0]  d_br_mask;
  logic [15:0] d_rs0, d_rs1;

  assign d_ir = imem_rdata;

  adam16_pipe_decode dec (
    .ir     (d_ir),
    .ra0    (d_ra0),
    .ra1    (d_ra1),
    .rd     (d_rd),
    .reg_we (d_reg_we),
    .flag_we(d_flag_we),
    .mem_we (d_mem_we),
    .wb_sel (d_wb_sel),
    .alu_op (d_alu_op),
    .a_sel  (d_a_sel),
    .b_imm  (d_b_imm),
    .imm    (d_imm),
    .br_mask(d_br_mask),
    .jump   (d_jump)
  );

  // WB stage signals, declared here for the register file's write port
  logic        w_valid, w_reg_we;
  logic [2:0]  w_rd;
  logic [15:0] w_value;
  logic        rf_we;

  assign rf_we = w_valid && w_reg_we;

  adam16_regfile #(
    .BYPASS(1'b1)
  ) rf (
    .clk(clk),
    .rst(rst),
    .ce (ce),
    .ra0(d_ra0),
    .ra1(d_ra1),
    .rd0(d_rs0),
    .rd1(d_rs1),
    .we (rf_we),
    .wa (w_rd),
    .wd (w_value)
  );

  // ID/EX
  logic        e_valid;
  logic [15:0] e_pc, e_ir;
  logic [2:0]  e_ra0, e_ra1, e_rd;
  logic        e_reg_we, e_flag_we, e_mem_we, e_b_imm, e_jump;
  logic [1:0]  e_wb_sel, e_a_sel;
  logic [3:0]  e_alu_op;
  logic [15:0] e_imm, e_rs0, e_rs1;
  logic [2:0]  e_br_mask;

  always_ff @(posedge clk) begin
    if (rst)     e_valid <= 1'b0;
    else if (ce) e_valid <= d_valid && !redirect;   // squash the word behind a redirect
  end

  always_ff @(posedge clk) begin
    if (ce) begin
      e_pc      <= d_pc;       e_ir      <= d_ir;
      e_ra0     <= d_ra0;      e_ra1     <= d_ra1;      e_rd     <= d_rd;
      e_reg_we  <= d_reg_we;   e_flag_we <= d_flag_we;  e_mem_we <= d_mem_we;
      e_wb_sel  <= d_wb_sel;   e_alu_op  <= d_alu_op;   e_a_sel  <= d_a_sel;
      e_b_imm   <= d_b_imm;    e_imm     <= d_imm;
      e_br_mask <= d_br_mask;  e_jump    <= d_jump;
      e_rs0     <= d_rs0;      e_rs1     <= d_rs1;
    end
  end

  // ================================================================== EX
  logic        m_valid, m_reg_we;
  logic [2:0]  m_rd;
  logic [15:0] m_value;            // MEM's result: the load data for a load

  // Forwarding: the youngest older instruction that writes the register wins.
  logic [15:0] e_a, e_b;
  always_comb begin
    if      (m_valid && m_reg_we && m_rd == e_ra0) e_a = m_value;
    else if (w_valid && w_reg_we && w_rd == e_ra0) e_a = w_value;
    else                                           e_a = e_rs0;
    if      (m_valid && m_reg_we && m_rd == e_ra1) e_b = m_value;
    else if (w_valid && w_reg_we && w_rd == e_ra1) e_b = w_value;
    else                                           e_b = e_rs1;
  end

  logic [15:0] e_pc1, alu_a, alu_b, alu_y;
  assign e_pc1 = e_pc + 16'd1;

  always_comb begin
    unique case (e_a_sel)
      2'd1:    alu_a = e_pc1;
      2'd2:    alu_a = 16'h0000;
      default: alu_a = e_a;
    endcase
  end
  assign alu_b = e_b_imm ? e_imm : e_b;

  adam16_alu alu (
    .op(e_alu_op),
    .a (alu_a),
    .b (alu_b),
    .y (alu_y)
  );

  // Condition codes. They change at the end of EX, so a branch right after
  // the instruction that sets them already sees the new values.
  logic N, Z, P;
  logic [2:0] e_nzp;               // the flags after the instruction in EX
  assign e_nzp = (e_valid && e_flag_we)
               ? {alu_y[15], alu_y == 16'h0000, !alu_y[15] && alu_y != 16'h0000}
               : {N, Z, P};

  always_ff @(posedge clk) begin
    if (rst)     {N, Z, P} <= 3'b010;
    else if (ce) {N, Z, P} <= e_nzp;
  end

  assign redirect = e_valid && (e_jump || (e_br_mask & {N, Z, P}) != 3'b000);
  assign target   = alu_y;

  assign dmem_addr  = alu_y;
  assign dmem_wdata = e_b;
  assign dmem_we    = e_valid && e_mem_we;

  // EX/MEM
  logic [15:0] m_pc, m_ir, m_result, m_mem_addr, m_mem_data;
  logic        m_load, m_mem_we;
  logic [2:0]  m_nzp;

  always_ff @(posedge clk) begin
    if (rst)     m_valid <= 1'b0;
    else if (ce) m_valid <= e_valid;
  end

  always_ff @(posedge clk) begin
    if (ce) begin
      m_pc       <= e_pc;      m_ir     <= e_ir;
      m_reg_we   <= e_reg_we;  m_rd     <= e_rd;
      m_result   <= (e_wb_sel == 2'd1) ? e_pc1 : alu_y;
      m_load     <= (e_wb_sel == 2'd2);
      m_mem_we   <= e_mem_we;  m_mem_addr <= dmem_addr;  m_mem_data <= dmem_wdata;
      m_nzp      <= e_nzp;
    end
  end

  // ================================================================== MEM
  assign m_value = m_load ? dmem_rdata : m_result;

  // MEM/WB
  logic [15:0] w_pc, w_ir, w_mem_addr, w_mem_data;
  logic        w_mem_we;
  logic [2:0]  w_nzp;

  always_ff @(posedge clk) begin
    if (rst)     w_valid <= 1'b0;
    else if (ce) w_valid <= m_valid;
  end

  always_ff @(posedge clk) begin
    if (ce) begin
      w_pc     <= m_pc;      w_ir       <= m_ir;
      w_reg_we <= m_reg_we;  w_rd       <= m_rd;      w_value    <= m_value;
      w_mem_we <= m_mem_we;  w_mem_addr <= m_mem_addr; w_mem_data <= m_mem_data;
      w_nzp    <= m_nzp;
    end
  end

  // ================================================================== WB
  // The register file write is rf_we / w_rd / w_value, above.

  // Retire record of the instruction in WB, in the format of sw/iss.py.
  // Read by tb/tb_program.sv; synthesis drops what nothing else uses.
  /* verilator lint_off UNUSEDSIGNAL */
  logic        rt_valid, rt_reg_we, rt_mem_we;
  logic [15:0] rt_pc, rt_ir, rt_reg_data, rt_mem_addr, rt_mem_data;
  logic [2:0]  rt_reg_addr, rt_nzp;
  /* verilator lint_on UNUSEDSIGNAL */

  assign rt_valid    = w_valid;
  assign rt_pc       = w_pc;
  assign rt_ir       = w_ir;
  assign rt_reg_we   = w_reg_we;
  assign rt_reg_addr = w_reg_we ? w_rd : 3'd0;
  assign rt_reg_data = w_reg_we ? w_value : 16'h0000;
  assign rt_mem_we   = w_mem_we;
  assign rt_mem_addr = w_mem_we ? w_mem_addr : 16'h0000;
  assign rt_mem_data = w_mem_we ? w_mem_data : 16'h0000;
  assign rt_nzp      = w_nzp;

  assign dbg_pc    = w_pc;
  assign dbg_ir    = w_valid ? w_ir : 16'hD000;
  assign dbg_alu_y = w_value;
  assign dbg_n     = w_nzp[2];
  assign dbg_z     = w_nzp[1];
  assign dbg_p     = w_nzp[0];

endmodule
