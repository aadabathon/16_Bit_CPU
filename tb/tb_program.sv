`timescale 1ns/1ps

// =============================================================================
//  tb_program — run one program image on a core and log its retire trace.
//
//    +MEM=<file.mem>      program image ($readmemh); all other words are 0
//    +TRACE=<file>        retire trace, one line per instruction (format below)
//    +MAXCYC=<n>          give up after n cycles (default 200000)
//
//  Compile with -DPIPE for the pipelined core, without it for the multicycle
//  core. The run ends when TRAP x025 (HALT) retires; HALT itself is not
//  logged. Each line is what one instruction did, in the same format as
//  sw/iss.py:
//
//      pc ir  reg_we reg_addr reg_data  mem_we mem_addr mem_data  nzp
//
//  Unused fields are zero; nzp is the flag state after the instruction.
//  The last line of stdout is "DONE cycles=<n> instret=<n> R0=.. R7=..".
// =============================================================================

module tb_program;

  logic clk = 0;
  logic rst = 1;
  always #5 clk = ~clk;

  // ---- retire probe: filled in per core below ----
  logic        rt_valid;
  logic [15:0] rt_pc, rt_ir;
  logic        rt_reg_we;
  logic [2:0]  rt_reg_addr;
  logic [15:0] rt_reg_data;
  logic        rt_mem_we;
  logic [15:0] rt_mem_addr, rt_mem_data;
  logic [2:0]  rt_nzp;

`ifdef PIPE
  logic [15:0] imem_addr, imem_rdata, dmem_addr, dmem_wdata, dmem_rdata;
  logic        dmem_we;

  adam16_pipe_core dut (
    .clk(clk), .rst(rst), .ce(1'b1),
    .imem_addr(imem_addr), .imem_rdata(imem_rdata),
    .dmem_addr(dmem_addr), .dmem_wdata(dmem_wdata), .dmem_we(dmem_we),
    .dmem_rdata(dmem_rdata),
    .dbg_pc(), .dbg_ir(), .dbg_alu_y(), .dbg_n(), .dbg_z(), .dbg_p()
  );

  adam16_dpram mem (
    .clk(clk), .en(1'b1),
    .a_addr(imem_addr), .a_rdata(imem_rdata),
    .b_addr(dmem_addr), .b_we(dmem_we), .b_wdata(dmem_wdata), .b_rdata(dmem_rdata)
  );

  // The pipeline carries every retire field down to WB itself.
  assign rt_valid    = dut.rt_valid;
  assign rt_pc       = dut.rt_pc;
  assign rt_ir       = dut.rt_ir;
  assign rt_reg_we   = dut.rt_reg_we;
  assign rt_reg_addr = dut.rt_reg_addr;
  assign rt_reg_data = dut.rt_reg_data;
  assign rt_mem_we   = dut.rt_mem_we;
  assign rt_mem_addr = dut.rt_mem_addr;
  assign rt_mem_data = dut.rt_mem_data;
  assign rt_nzp      = dut.rt_nzp;

  function automatic logic [15:0] reg_val(input int r);
    return dut.rf.r[r];
  endfunction
`else
  logic [15:0] mem_addr, mem_wdata, mem_rdata;
  logic        mem_we;

  adam16_core dut (
    .clk(clk), .rst(rst), .ce(1'b1),
    .mem_rdata(mem_rdata), .mem_addr(mem_addr), .mem_wdata(mem_wdata), .mem_we(mem_we),
    .dbg_pc(), .dbg_ir(), .dbg_alu_y(), .dbg_n(), .dbg_z(), .dbg_p()
  );

  adam16_sram mem (
    .clk(clk), .en(1'b1), .we(mem_we), .addr(mem_addr), .wdata(mem_wdata), .rdata(mem_rdata)
  );

  // The multicycle core retires an instruction in the cycle whose closing
  // edge takes the FSM back to S_IF0. PC already holds PC+1 by then.
  logic [15:0] wb;
  assign wb          = dut.u_dp.wb_data;
  assign rt_valid    = (dut.u_ctrl.state_n == 5'd0);
  assign rt_pc       = dut.u_dp.pc - 16'd1;
  assign rt_ir       = dut.u_dp.ir;
  assign rt_reg_we   = dut.reg_we;
  assign rt_reg_addr = dut.reg_we ? dut.reg_dst : 3'd0;
  assign rt_reg_data = dut.reg_we ? wb : 16'h0000;
  assign rt_mem_we   = dut.mem_we;
  assign rt_mem_addr = dut.mem_we ? mem_addr : 16'h0000;
  assign rt_mem_data = dut.mem_we ? mem_wdata : 16'h0000;
  assign rt_nzp      = dut.flag_we ? {wb[15], wb == 16'h0, !wb[15] && wb != 16'h0}
                                   : {dut.N, dut.Z, dut.P};

  function automatic logic [15:0] reg_val(input int r);
    return dut.u_dp.rf.r[r];
  endfunction
`endif

  initial begin
    string mem_file, trace_file;
    int    fd, cycles, instret, maxcyc;
    logic  done;

    if (!$value$plusargs("MEM=%s", mem_file)) begin
      $display("ERROR: +MEM=<file> required");
      $finish;
    end
    if (!$value$plusargs("TRACE=%s", trace_file)) trace_file = "trace.txt";
    if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 200000;

    for (int i = 0; i < 65536; i++) mem.mem[i] = 16'h0000;
    $readmemh(mem_file, mem.mem);
    fd = $fopen(trace_file, "w");

    rst = 1;
    repeat (2) @(posedge clk);
    #1 rst = 0;

    cycles = 0; instret = 0; done = 0;
    while (!done && cycles < maxcyc) begin
      @(negedge clk);                         // sample the cycle's retire signals
      if (rt_valid) begin
        if (rt_ir == 16'h9025) done = 1;     // HALT: stop, don't log
        else begin
          $fdisplay(fd, "%04h %04h %0d %0d %04h %0d %04h %04h %03b",
                    rt_pc, rt_ir, rt_reg_we, rt_reg_addr, rt_reg_data,
                    rt_mem_we, rt_mem_addr, rt_mem_data, rt_nzp);
          instret++;
        end
      end
      cycles++;
      @(posedge clk);
    end
    $fclose(fd);
    if (!done) $display("TIMEOUT after %0d cycles", cycles);
    $display("DONE cycles=%0d instret=%0d R0=%04h R1=%04h R2=%04h R3=%04h R4=%04h R5=%04h R6=%04h R7=%04h",
             cycles, instret, reg_val(0), reg_val(1), reg_val(2), reg_val(3),
             reg_val(4), reg_val(5), reg_val(6), reg_val(7));
    $finish;
  end

endmodule
