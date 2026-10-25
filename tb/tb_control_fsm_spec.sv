`timescale 1ns/1ps

// =============================================================================
//  tb_control_fsm_spec — conformance check: cpu16_control_fsm vs. its spec.
//
//  The spec is docs/tools/fsm_spec.py, the same data the control bubble
//  diagrams are drawn from. gen_fsm.py --vectors expands it into one line per
//  clock cycle for every opcode x IR[11:9] x funct x {N,Z,P} combination
//  (IR[8:3] random):
//
//      ir  nzp  cycle  state_code  packed_outputs        (hex hex dec dec hex)
//
//  cycle 0 is the cycle right after a synchronous reset (S_IF0); the last line
//  of each instruction is the S_IF0 it returns to. IR and the flags are held
//  constant for the whole instruction, which is what the real datapath does
//  from S_ID until the next S_IF2.
//
//  Run (from the repository root):  make -C docs check
// =============================================================================

module tb_control_fsm_spec;

  logic        clk = 0, rst = 1;
  logic [15:0] ir;
  logic        N, Z, P;

  logic        pc_we, ir_we, mar_we, mdr_we, reg_we, flag_we, mem_we;
  logic [2:0]  reg_dst;
  logic        ra2_sel;
  logic [1:0]  wb_sel;
  logic [3:0]  alu_op;
  logic [1:0]  alu_a_sel;
  logic [2:0]  alu_b_sel;
  logic [2:0]  pc_src_sel;
  logic [1:0]  mar_src_sel;

  cpu16_control_fsm dut (
    .clk(clk), .rst(rst), .ir(ir), .N(N), .Z(Z), .P(P),
    .pc_we(pc_we), .ir_we(ir_we), .mar_we(mar_we), .mdr_we(mdr_we),
    .reg_we(reg_we), .flag_we(flag_we), .mem_we(mem_we),
    .reg_dst(reg_dst), .ra2_sel(ra2_sel), .wb_sel(wb_sel), .alu_op(alu_op),
    .alu_a_sel(alu_a_sel), .alu_b_sel(alu_b_sel),
    .pc_src_sel(pc_src_sel), .mar_src_sel(mar_src_sel)
  );

  // Packing order must match OUTPUTS in docs/tools/fsm_spec.py (MSB first).
  wire [26:0] outs = {pc_we, ir_we, mar_we, mdr_we, reg_we, flag_we, mem_we,
                      reg_dst, ra2_sel, wb_sel, alu_op, alu_a_sel, alu_b_sel,
                      pc_src_sel, mar_src_sel};

  task automatic tick();
    #5 clk = 1;
    #5 clk = 0;
  endtask

  task automatic show_fields(input string tag, input logic [26:0] o);
    $display("      %s pc_we=%b ir_we=%b mar_we=%b mdr_we=%b reg_we=%b flag_we=%b mem_we=%b",
             tag, o[26], o[25], o[24], o[23], o[22], o[21], o[20]);
    $display("      %s reg_dst=%b ra2_sel=%b wb_sel=%b alu_op=%b alu_a_sel=%b alu_b_sel=%b pc_src_sel=%b mar_src_sel=%b",
             tag, o[19:17], o[16], o[15:14], o[13:10], o[9:8], o[7:5], o[4:2], o[1:0]);
  endtask

  initial begin
    string       path;
    int          fd, n_cycles, n_instr, n_fail;
    logic [15:0] v_ir;
    logic [2:0]  v_nzp;
    int          v_cyc, v_state;
    logic [26:0] v_outs;

    n_cycles = 0; n_instr = 0; n_fail = 0;
    if (!$value$plusargs("VECTORS=%s", path)) path = "build/fsm_vectors.txt";
    fd = $fopen(path, "r");
    if (fd == 0) begin
      $display("ERROR: cannot open %s (run gen_fsm.py --vectors first)", path);
      $finish;
    end

    while ($fscanf(fd, "%h %h %d %d %h\n", v_ir, v_nzp, v_cyc, v_state, v_outs) == 5) begin
      if (v_cyc == 0) begin
        ir = v_ir;
        {N, Z, P} = v_nzp;
        rst = 1; tick(); rst = 0;      // one synchronous reset edge -> S_IF0
        n_instr++;
      end else begin
        tick();
      end
      #1;
      n_cycles++;
      if (dut.state !== v_state[4:0] || outs !== v_outs) begin
        n_fail++;
        if (n_fail <= 10) begin
          $display("  MISMATCH ir=%h NZP=%b cycle %0d: state got %0d expected %0d",
                   v_ir, v_nzp, v_cyc, dut.state, v_state);
          show_fields("got     ", outs);
          show_fields("expected", v_outs);
        end
      end
    end
    $fclose(fd);

    $display("================================================");
    $display(" cpu16_control_fsm vs docs/tools/fsm_spec.py");
    $display(" %0d instructions, %0d cycles checked, %0d mismatches",
             n_instr, n_cycles, n_fail);
    if (n_instr == 0)      $display(" ERROR: no vectors read");
    else if (n_fail == 0)  $display(" RTL MATCHES SPEC");
    else                   $display(" RTL DOES NOT MATCH SPEC");
    $display("================================================");
    $finish;
  end

endmodule
