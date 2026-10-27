`timescale 1ns/1ps

// =============================================================================
//  tb_adam16_gate — black-box testbench for a synthesized (gate-level) core.
//
//  Synthesis flattens the design: the register file, the FSM state and the
//  pipeline registers are no longer reachable by name. So this testbench only
//  uses the core's ports. Each program stores its results to memory, which is
//  outside the core and always observable, and a run ends when the core's
//  dbg_ir port shows HALT (TRAP x025):
//    adam16_core       dbg_ir is IR: HALT is latched only after every earlier
//                      instruction has finished.
//    adam16_pipe_core  dbg_ir is the instruction in WB: every earlier
//                      instruction has retired.
//
//  Compile with -DPIPE for adam16_pipe_core + adam16_dpram, without it for
//  adam16_core + adam16_sram. The same file runs against the RTL in
//  `make gate-rtl`, which proves the testbench before it meets a netlist.
//  Gate-level run: scripts/adam16_sim.do.
// =============================================================================

module tb_adam16_gate;

  logic clk = 0;
  logic rst = 1;
  always #5 clk = ~clk;

  logic [15:0] dbg_ir;

`ifdef PIPE
  logic [15:0] imem_addr, imem_rdata, dmem_addr, dmem_wdata, dmem_rdata;
  logic        dmem_we;

  adam16_pipe_core dut (
    .clk(clk), .rst(rst), .ce(1'b1),
    .imem_addr(imem_addr), .imem_rdata(imem_rdata),
    .dmem_addr(dmem_addr), .dmem_wdata(dmem_wdata), .dmem_we(dmem_we),
    .dmem_rdata(dmem_rdata),
    .dbg_pc(), .dbg_ir(dbg_ir), .dbg_alu_y(), .dbg_n(), .dbg_z(), .dbg_p()
  );

  adam16_dpram mem (
    .clk(clk), .en(1'b1),
    .a_addr(imem_addr), .a_rdata(imem_rdata),
    .b_addr(dmem_addr), .b_we(dmem_we), .b_wdata(dmem_wdata), .b_rdata(dmem_rdata)
  );
`else
  logic [15:0] mem_addr, mem_wdata, mem_rdata;
  logic        mem_we;

  adam16_core dut (
    .clk(clk), .rst(rst), .ce(1'b1),
    .mem_rdata(mem_rdata), .mem_addr(mem_addr), .mem_wdata(mem_wdata), .mem_we(mem_we),
    .dbg_pc(), .dbg_ir(dbg_ir), .dbg_alu_y(), .dbg_n(), .dbg_z(), .dbg_p()
  );

  adam16_sram mem (
    .clk(clk), .en(1'b1), .we(mem_we), .addr(mem_addr), .wdata(mem_wdata), .rdata(mem_rdata)
  );
`endif

  wire halted = (dbg_ir === 16'h9025);

  int    pass_count = 0, fail_count = 0, test_count = 0, total_cycles = 0;

  // ---------------------------------------------------------------- helpers
  task automatic start(input string name);
    test_count++;
    $display("\n[T%0d] %s", test_count, name);
    for (int i = 0; i < 1024; i++) mem.mem[i] = 16'h0000;
  endtask

  // Reset with both clock edges inside it, released on a falling edge, so
  // flops in any cell library start from a known value.
  task automatic run(input int max_cycles);
    int n;
    rst = 1;
    @(posedge clk);
    @(negedge clk);
    rst = 0;
    n = 0;
    while (!halted && n < max_cycles) begin
      @(posedge clk);
      #1;
      n++;
    end
    total_cycles += n;
    if (!halted) begin
      $display("    FAIL  no HALT within %0d cycles (dbg_ir = 0x%04h)", n, dbg_ir);
      fail_count++;
    end
  endtask

  task automatic check(input logic [15:0] addr, input logic [15:0] expected, input string what);
    if (mem.mem[addr] === expected) begin
      pass_count++;
      $display("    PASS  M[0x%04h] = 0x%04h  %s", addr, mem.mem[addr], what);
    end else begin
      fail_count++;
      $display("    FAIL  M[0x%04h] = 0x%04h, expected 0x%04h  %s",
               addr, mem.mem[addr], expected, what);
    end
  endtask

  // ---------------------------------------------------------------- tests
  initial begin
    $display("================================================");
`ifdef PIPE
    $display(" adam16_pipe_core black-box test (ports + memory only)");
`else
    $display(" adam16_core black-box test (ports + memory only)");
`endif
    $display("================================================");

    start("ADDI, ADD with forwarding, ST");
    mem.mem[0] = 16'h2205;   // ADDI R1, R0, 5
    mem.mem[1] = 16'h2407;   // ADDI R2, R0, 7
    mem.mem[2] = 16'h0650;   // ADD  R3, R1, R2       R3 = 12
    mem.mem[3] = 16'h561C;   // ST   R3, 0x0020
    mem.mem[4] = 16'h9025;   // HALT
    run(200);
    check(16'h0020, 16'd12, "R1 + R2");

    start("LEA, LDR, STR round trip");
    mem.mem[0] = 16'hC206;   // LEA  R1, 0x0007
    mem.mem[1] = 16'hA440;   // LDR  R2, R1, 0
    mem.mem[2] = 16'hB441;   // STR  R2, R1, 1        M[8] = M[7]
    mem.mem[3] = 16'h9025;   // HALT
    mem.mem[7] = 16'hABCD;
    run(200);
    check(16'h0008, 16'hABCD, "copied by LDR / STR");

    start("LD, ST (PC-relative)");
    mem.mem[0] = 16'h4205;   // LD   R1, 0x0006
    mem.mem[1] = 16'h5205;   // ST   R1, 0x0007
    mem.mem[2] = 16'h9025;   // HALT
    mem.mem[6] = 16'hCAFE;
    run(200);
    check(16'h0007, 16'hCAFE, "copied by LD / ST");

    start("JSR, signed CMP, branches");
    mem.mem[0] = 16'h4207;   // LD   R1, 0x0008       0x7FFF
    mem.mem[1] = 16'h4407;   // LD   R2, 0x0009       0x8000
    mem.mem[2] = 16'h7007;   // JSR  0x000A
    mem.mem[3] = 16'h1057;   // CMP  R1, R2           +32767 > -32768: P
    mem.mem[4] = 16'hD201;   // BRp  0x0006
    mem.mem[5] = 16'h2DFF;   // ADDI R6, R7, -1       skipped
    mem.mem[6] = 16'h5E04;   // ST   R7, 0x000B       R7 = 3 (return address)
    mem.mem[7] = 16'h9025;   // HALT
    mem.mem[8] = 16'h7FFF;
    mem.mem[9] = 16'h8000;
    mem.mem[10] = 16'h8000;  // RET
    run(300);
    check(16'h000B, 16'h0003, "R7 from JSR, branch taken");

    start("sum_array (fpga/mem/adam16_sum_array.mem)");
    mem.mem[16'h0000] = 16'hC20A;  // LEA  R1, 0x000B
    mem.mem[16'h0001] = 16'h2405;  // ADDI R2, R0, 5
    mem.mem[16'h0002] = 16'h0606;  // MOV  R3, R0
    mem.mem[16'h0003] = 16'hA840;  // LDR  R4, R1, 0     loop
    mem.mem[16'h0004] = 16'h06E0;  // ADD  R3, R3, R4
    mem.mem[16'h0005] = 16'h1242;  // INC  R1, R1
    mem.mem[16'h0006] = 16'h1483;  // DEC  R2, R2
    mem.mem[16'h0007] = 16'h1087;  // CMP  R2, R0
    mem.mem[16'h0008] = 16'hD3FA;  // BRp  loop
    mem.mem[16'h0009] = 16'h5606;  // ST   R3, 0x0010
    mem.mem[16'h000A] = 16'h9025;  // HALT
    for (int i = 0; i < 5; i++) mem.mem[16'h000B + i] = 16'(i + 1);
    run(500);
    check(16'h0010, 16'd15, "1 + 2 + 3 + 4 + 5");

    $display("\n================================================");
    $display(" Summary: %0d/%0d checks passed   (%0d tests, %0d cycles)",
             pass_count, pass_count + fail_count, test_count, total_cycles);
    if (fail_count == 0) $display(" ALL BLACK-BOX TESTS PASSED");
    else                 $display(" %0d FAILURES", fail_count);
    $display("================================================");
    $finish;
  end

  initial begin
    #200000;
    $display("\n*** GLOBAL TIMEOUT ***");
    $finish;
  end

endmodule
