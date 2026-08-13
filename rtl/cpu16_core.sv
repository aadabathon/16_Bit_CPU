module cpu16_core (
  input  logic        clk,
  input  logic        rst,
  input  logic [15:0] mem_rdata,
  output logic [15:0] mem_addr,
  output logic [15:0] mem_wdata,
  output logic        mem_we
);
  logic pc_we, ir_we, mar_we, mdr_we, reg_we, flag_we;
  logic [2:0] reg_dst;
  logic [1:0] wb_sel;
  logic [2:0] alu_op;
  logic [1:0] alu_a_sel;
  logic [2:0] alu_b_sel;
  logic [1:0] pc_src_sel;
  logic [1:0] mar_src_sel;

  logic [15:0] ir;
  logic N, Z, P;
  logic [15:0] pc;

  cpu16_control_fsm u_ctrl(
    .clk(clk),
    .rst(rst),
    .ir(ir),
    .N(N),
    .Z(Z),
    .P(P),
    .pc_we(pc_we),
    .ir_we(ir_we),
    .mar_we(mar_we),
    .mdr_we(mdr_we),
    .reg_we(reg_we),
    .flag_we(flag_we),
    .mem_we(mem_we),
    .reg_dst(reg_dst),
    .wb_sel(wb_sel),
    .alu_op(alu_op),
    .alu_a_sel(alu_a_sel),
    .alu_b_sel(alu_b_sel),
    .pc_src_sel(pc_src_sel),
    .mar_src_sel(mar_src_sel)
  );

  cpu16_datapath u_dp(
    .clk(clk),
    .rst(rst),
    .mem_rdata(mem_rdata),
    .mem_addr(mem_addr),
    .mem_wdata(mem_wdata),
    .pc_we(pc_we),
    .ir_we(ir_we),
    .mar_we(mar_we),
    .mdr_we(mdr_we),
    .reg_we(reg_we),
    .flag_we(flag_we),
    .reg_dst(reg_dst),
    .wb_sel(wb_sel),
    .alu_op(alu_op),
    .alu_a_sel(alu_a_sel),
    .alu_b_sel(alu_b_sel),
    .pc_src_sel(pc_src_sel),
    .mar_src_sel(mar_src_sel),
    .ir(ir),
    .N(N),
    .Z(Z),
    .P(P),
    .pc(pc)
  );
endmodule
