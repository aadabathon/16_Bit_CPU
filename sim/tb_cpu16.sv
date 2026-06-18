`timescale 1ns/1ps

// =============================================================================
//  tb_cpu16 — directed testbench for the 16-bit core.
//
//  Each test:
//    1. clear_memory() — zero out program memory
//    2. hand-write the test program into imem.mem[]
//    3. do_reset() — pulse rst, leaving the CPU at the start of fetch
//    4. run_until_halt() — run until the FSM enters S_EX_TRAP
//    5. check_eq() — compare register / memory state against expected
//
//  Halt detection: hierarchical reference to the FSM state. S_EX_TRAP == 5'd13.
//  Programs end with `TRAP x025`. The TB exits the run loop the instant the FSM
//  transitions INTO S_EX_TRAP, which means the TRAP's own writes (R7 <- PC,
//  PC <- vector) have not yet committed. That is intentional — it lets us
//  observe the program's final register state without TRAP clobbering R7.
// =============================================================================

module tb_cpu16;

  // -- Clock and reset --
  logic clk = 0;
  logic rst = 1;
  always #5 clk = ~clk;  // 100 MHz

  // -- Memory bus --
  logic [15:0] mem_addr, mem_wdata, mem_rdata;
  logic        mem_we;

  // -- DUT --
  cpu16_core dut (
    .clk      (clk),
    .rst      (rst),
    .mem_rdata(mem_rdata),
    .mem_addr (mem_addr),
    .mem_wdata(mem_wdata),
    .mem_we   (mem_we)
  );

  // -- Memory --
  SramSBC imem (
    .clk  (clk),
    .we   (mem_we),
    .addr (mem_addr),
    .wdata(mem_wdata),
    .rdata(mem_rdata)
  );

  // -- Halt detection (hierarchical) --
  // S_EX_TRAP is 5'd13 in cpu16_control_fsm.
  localparam logic [4:0] HALT_STATE = 5'd13;
  wire halted = (dut.u_ctrl.state == HALT_STATE);

  // -- Stats --
  int    pass_count    = 0;
  int    fail_count    = 0;
  int    test_count    = 0;
  int    total_cycles  = 0;
  string current_test  = "";

  // =====================================================
  //  Helpers
  // =====================================================
  task automatic clear_memory();
    for (int i = 0; i < 1024; i++) imem.mem[i] = 16'h0000;
  endtask

  task automatic do_reset();
    rst = 1;
    repeat (3) @(posedge clk);
    rst = 0;
    @(posedge clk);
  endtask

  task automatic run_until_halt(input int max_cycles);
    int n;
    n = 0;
    while (!halted && n < max_cycles) begin
      @(posedge clk);
      n++;
    end
    total_cycles += n;
    if (!halted) begin
      $display("  ## TIMEOUT after %0d cycles  PC=0x%04h  IR=0x%04h",
               n, dut.u_dp.pc, dut.u_dp.ir);
      fail_count++;
    end
  endtask

  task automatic check_eq(input logic [15:0] actual,
                          input logic [15:0] expected,
                          input string       label);
    if (actual === expected) begin
      pass_count++;
      $display("    PASS  %-30s 0x%04h", label, actual);
    end else begin
      fail_count++;
      $display("    FAIL  %-30s got 0x%04h expected 0x%04h",
               label, actual, expected);
    end
  endtask

  function automatic logic [15:0] reg_val(input logic [2:0] r);
    return dut.u_dp.rf.r[r];
  endfunction

  function automatic logic [15:0] mem_val(input logic [15:0] a);
    return imem.mem[a];
  endfunction

  // =====================================================
  //  Test programs
  //  All encodings per InstructionSet.txt (corrected ISA).
  // =====================================================

  // ------------------------------------------------------
  // T1: ADDI + ADD smoke test
  // ------------------------------------------------------
  task automatic test_addi_add();
    current_test = "addi_add";
    test_count++;
    $display("\n[T%0d] %s", test_count, current_test);
    clear_memory();
    imem.mem[0] = 16'h2205;  // ADDI R1, R0, 5
    imem.mem[1] = 16'h2407;  // ADDI R2, R0, 7
    imem.mem[2] = 16'h0650;  // ADD  R3, R1, R2
    imem.mem[3] = 16'h9025;  // TRAP x025
    do_reset();
    run_until_halt(200);
    check_eq(reg_val(1), 16'd5,  "R1");
    check_eq(reg_val(2), 16'd7,  "R2");
    check_eq(reg_val(3), 16'd12, "R3 = R1+R2");
  endtask

  // ------------------------------------------------------
  // T2: ALU0 opcodes (ADD/SUB/AND/OR/XOR/NOT)
  // ------------------------------------------------------
  task automatic test_alu0();
    current_test = "alu0_ops";
    test_count++;
    $display("\n[T%0d] %s", test_count, current_test);
    clear_memory();
    imem.mem[0] = 16'h2203;  // ADDI R1, R0, 3
    imem.mem[1] = 16'h2405;  // ADDI R2, R0, 5
    imem.mem[2] = 16'h0650;  // ADD  R3, R1, R2  -> 8
    imem.mem[3] = 16'h0851;  // SUB  R4, R1, R2  -> -2 (0xFFFE)
    imem.mem[4] = 16'h0A53;  // AND  R5, R1, R2  -> 1
    imem.mem[5] = 16'h0C54;  // OR   R6, R1, R2  -> 7
    imem.mem[6] = 16'h0E55;  // XOR  R7, R1, R2  -> 6
    imem.mem[7] = 16'h0042;  // NOT  R0, R1      -> 0xFFFC
    imem.mem[8] = 16'h9025;  // TRAP
    do_reset();
    run_until_halt(300);
    check_eq(reg_val(0), 16'hFFFC, "R0 = ~R1");
    check_eq(reg_val(3), 16'd8,    "R3 = R1+R2");
    check_eq(reg_val(4), 16'hFFFE, "R4 = R1-R2");
    check_eq(reg_val(5), 16'd1,    "R5 = R1&R2");
    check_eq(reg_val(6), 16'd7,    "R6 = R1|R2");
    check_eq(reg_val(7), 16'd6,    "R7 = R1^R2");
  endtask

  // ------------------------------------------------------
  // T3: ALU1 opcodes (NAND/NOR/INC/DEC/LSL)
  // ------------------------------------------------------
  task automatic test_alu1();
    current_test = "alu1_ops";
    test_count++;
    $display("\n[T%0d] %s", test_count, current_test);
    clear_memory();
    imem.mem[0] = 16'h2203;  // ADDI R1, R0, 3
    imem.mem[1] = 16'h2405;  // ADDI R2, R0, 5
    imem.mem[2] = 16'h1650;  // NAND R3, R1, R2  -> 0xFFFE
    imem.mem[3] = 16'h1851;  // NOR  R4, R1, R2  -> 0xFFF8
    imem.mem[4] = 16'h1A42;  // INC  R5, R1      -> 4
    imem.mem[5] = 16'h1C83;  // DEC  R6, R2      -> 4
    imem.mem[6] = 16'h1E44;  // LSL1 R7, R1      -> 6
    imem.mem[7] = 16'h9025;  // TRAP
    do_reset();
    run_until_halt(300);
    check_eq(reg_val(3), 16'hFFFE, "R3 = ~(R1&R2)");
    check_eq(reg_val(4), 16'hFFF8, "R4 = ~(R1|R2)");
    check_eq(reg_val(5), 16'd4,    "R5 = R1+1");
    check_eq(reg_val(6), 16'd4,    "R6 = R2-1");
    check_eq(reg_val(7), 16'd6,    "R7 = R1<<1");
  endtask

  // ------------------------------------------------------
  // T4: ANDI immediate (zero-extended)
  // ------------------------------------------------------
  task automatic test_andi();
    current_test = "andi";
    test_count++;
    $display("\n[T%0d] %s", test_count, current_test);
    clear_memory();
    imem.mem[0] = 16'h221F;  // ADDI R1, R0, 31 -> 0x1F
    imem.mem[1] = 16'h3455;  // ANDI R2, R1, 0x15
    imem.mem[2] = 16'h9025;  // TRAP
    do_reset();
    run_until_halt(200);
    check_eq(reg_val(1), 16'h001F, "R1 = 31");
    check_eq(reg_val(2), 16'h0015, "R2 = R1 & 0x15");
  endtask

  // ------------------------------------------------------
  // T5: negative ADDI immediate (sign-extension check)
  // ------------------------------------------------------
  task automatic test_negative_addi();
    current_test = "negative_addi";
    test_count++;
    $display("\n[T%0d] %s", test_count, current_test);
    clear_memory();
    imem.mem[0] = 16'h2214;  // ADDI R1, R0, 20
    imem.mem[1] = 16'h247B;  // ADDI R2, R1, -5  (imm6 = 6'b111011)
    imem.mem[2] = 16'h9025;  // TRAP
    do_reset();
    run_until_halt(200);
    check_eq(reg_val(1), 16'd20, "R1 = 20");
    check_eq(reg_val(2), 16'd15, "R2 = R1 + (-5)");
  endtask

  // ------------------------------------------------------
  // T6: CMP + BRn taken
  // ------------------------------------------------------
  task automatic test_cmp_br_taken();
    current_test = "cmp_br_taken";
    test_count++;
    $display("\n[T%0d] %s", test_count, current_test);
    clear_memory();
    imem.mem[0] = 16'h2203;  // ADDI R1, R0, 3
    imem.mem[1] = 16'h2405;  // ADDI R2, R0, 5
    imem.mem[2] = 16'h1057;  // CMP R1, R2     (3-5 = -2; N=1)
    imem.mem[3] = 16'hD802;  // BRn +2         (taken -> addr 6)
    imem.mem[4] = 16'h2619;  // ADDI R3, R0, 25  (FAIL path)
    imem.mem[5] = 16'h9025;  // TRAP
    imem.mem[6] = 16'h260B;  // ADDI R3, R0, 11  (SUCCESS path)
    imem.mem[7] = 16'h9025;  // TRAP
    do_reset();
    run_until_halt(300);
    check_eq(reg_val(3), 16'd11, "R3 (took branch)");
  endtask

  // ------------------------------------------------------
  // T7: BR not taken (fall through)
  // ------------------------------------------------------
  task automatic test_br_not_taken();
    current_test = "br_not_taken";
    test_count++;
    $display("\n[T%0d] %s", test_count, current_test);
    clear_memory();
    imem.mem[0] = 16'h2205;  // ADDI R1, R0, 5
    imem.mem[1] = 16'h2403;  // ADDI R2, R0, 3
    imem.mem[2] = 16'h1057;  // CMP R1, R2  (5-3 = +2; P=1)
    imem.mem[3] = 16'hD802;  // BRn +2  (NOT taken)
    imem.mem[4] = 16'h260B;  // ADDI R3, R0, 11 (fell through -> success)
    imem.mem[5] = 16'h9025;  // TRAP
    imem.mem[6] = 16'h2619;  // (fail path; unreached)
    imem.mem[7] = 16'h9025;
    do_reset();
    run_until_halt(300);
    check_eq(reg_val(3), 16'd11, "R3 (no branch)");
  endtask

  // ------------------------------------------------------
  // T8: LEA + LDR + STR round trip
  // ------------------------------------------------------
  task automatic test_lea_ldr_str();
    current_test = "lea_ldr_str";
    test_count++;
    $display("\n[T%0d] %s", test_count, current_test);
    clear_memory();
    imem.mem[0] = 16'hC206;  // LEA R1, +6   -> R1 = inc(PC)+6 = 1+6 = 7
    imem.mem[1] = 16'hA440;  // LDR R2, R1, 0 -> R2 = mem[7]
    imem.mem[2] = 16'hB441;  // STR R2, R1, 1 -> mem[8] = R2
    imem.mem[3] = 16'hA641;  // LDR R3, R1, 1 -> R3 = mem[8]
    imem.mem[4] = 16'h9025;  // TRAP
    imem.mem[7] = 16'hABCD;  // constant
    do_reset();
    run_until_halt(300);
    check_eq(reg_val(1), 16'h0007, "R1 (LEA target)");
    check_eq(reg_val(2), 16'hABCD, "R2 (LDR const)");
    check_eq(reg_val(3), 16'hABCD, "R3 (LDR after STR)");
    check_eq(mem_val(8), 16'hABCD, "mem[8] (STR target)");
  endtask

  // ------------------------------------------------------
  // T9: LD + ST (PC-relative)
  // ------------------------------------------------------
  task automatic test_ld_st_pcrel();
    current_test = "ld_st_pcrel";
    test_count++;
    $display("\n[T%0d] %s", test_count, current_test);
    clear_memory();
    imem.mem[0] = 16'h4205;  // LD R1, +5  -> R1 = mem[1+5]
    imem.mem[1] = 16'h5205;  // ST R1, +5  -> mem[2+5] = R1
    imem.mem[2] = 16'h4404;  // LD R2, +4  -> R2 = mem[3+4]
    imem.mem[3] = 16'h9025;  // TRAP
    imem.mem[6] = 16'hCAFE;  // constant
    do_reset();
    run_until_halt(300);
    check_eq(reg_val(1), 16'hCAFE, "R1 (LD const)");
    check_eq(mem_val(7), 16'hCAFE, "mem[7] (ST target)");
    check_eq(reg_val(2), 16'hCAFE, "R2 (LD after ST)");
  endtask

  // ------------------------------------------------------
  // T10: JSR + RET round trip
  // ------------------------------------------------------
  task automatic test_jsr_ret();
    current_test = "jsr_ret";
    test_count++;
    $display("\n[T%0d] %s", test_count, current_test);
    clear_memory();
    imem.mem[0] = 16'h220A;  // ADDI R1, R0, 10
    imem.mem[1] = 16'h7002;  // JSR +2  -> PC = 4, R7 = 2
    imem.mem[2] = 16'h2401;  // ADDI R2, R0, 1 (after return)
    imem.mem[3] = 16'h9025;  // TRAP
    imem.mem[4] = 16'h1242;  // INC R1, R1 -> 11
    imem.mem[5] = 16'h8000;  // RET -> PC = R7 = 2
    do_reset();
    run_until_halt(300);
    check_eq(reg_val(1), 16'd11, "R1 (after subroutine)");
    check_eq(reg_val(2), 16'd1,  "R2 (after return)");
    check_eq(reg_val(7), 16'd2,  "R7 (return addr saved)");
  endtask

  // ------------------------------------------------------
  // T11: JMP register
  // ------------------------------------------------------
  task automatic test_jmp();
    current_test = "jmp";
    test_count++;
    $display("\n[T%0d] %s", test_count, current_test);
    clear_memory();
    imem.mem[0] = 16'h2203;  // ADDI R1, R0, 3
    imem.mem[1] = 16'h6040;  // JMP R1   -> PC = 3
    imem.mem[2] = 16'h2401;  // (skipped)
    imem.mem[3] = 16'h2605;  // ADDI R3, R0, 5
    imem.mem[4] = 16'h9025;  // TRAP
    do_reset();
    run_until_halt(300);
    check_eq(reg_val(1), 16'd3, "R1");
    check_eq(reg_val(2), 16'd0, "R2 (skipped)");
    check_eq(reg_val(3), 16'd5, "R3 (after JMP)");
  endtask

  // ------------------------------------------------------
  // T12: array sum — LEA + LDR loop + CMP/BRp + ST
  // sum mem[0x000B..0x000F] = 1+2+3+4+5 = 15; result → mem[0x0010]
  // ------------------------------------------------------
  task automatic test_sum_array();
    current_test = "sum_array";
    test_count++;
    $display("\n[T%0d] %s", test_count, current_test);
    clear_memory();

    // Program
    imem.mem[16'h0000] = 16'hC20A;  // LEA  R1, +10    ; R1 = 0x000B
    imem.mem[16'h0001] = 16'h2405;  // ADDI R2, R0, 5  ; R2 = 5
    imem.mem[16'h0002] = 16'h0606;  // MOV  R3, R0     ; R3 = 0
    imem.mem[16'h0003] = 16'hA840;  // LDR  R4, R1, 0  ; R4 = mem[R1]
    imem.mem[16'h0004] = 16'h06E0;  // ADD  R3, R3, R4 ; R3 += R4
    imem.mem[16'h0005] = 16'h1242;  // INC  R1, R1
    imem.mem[16'h0006] = 16'h1483;  // DEC  R2, R2
    imem.mem[16'h0007] = 16'h1087;  // CMP  R2, R0
    imem.mem[16'h0008] = 16'hD3FA;  // BRp  LOOP       ; offset -6 → 0x0003
    imem.mem[16'h0009] = 16'h5606;  // ST   R3, +6     ; mem[0x0010] = R3
    imem.mem[16'h000A] = 16'h9025;  // TRAP 0x025

    // Data: [1, 2, 3, 4, 5]
    imem.mem[16'h000B] = 16'h0001;
    imem.mem[16'h000C] = 16'h0002;
    imem.mem[16'h000D] = 16'h0003;
    imem.mem[16'h000E] = 16'h0004;
    imem.mem[16'h000F] = 16'h0005;

    do_reset();
    run_until_halt(500);
    check_eq(reg_val(3),        16'd15, "R3 (sum = 1+2+3+4+5)");
    check_eq(mem_val(16'h0010), 16'd15, "mem[0x0010] (stored result)");
  endtask

  // =====================================================
  //  Main
  // =====================================================
  initial begin
    string vcd;
    if ($value$plusargs("VCD=%s", vcd)) begin
      $dumpfile(vcd);
      $dumpvars(0, tb_cpu16);
    end

    $display("================================================");
    $display(" CPU16 testbench");
    $display("================================================");

    rst = 1;
    repeat (3) @(posedge clk);

    test_addi_add();
    test_alu0();
    test_alu1();
    test_andi();
    test_negative_addi();
    test_cmp_br_taken();
    test_br_not_taken();
    test_lea_ldr_str();
    test_ld_st_pcrel();
    test_jsr_ret();
    test_jmp();
    test_sum_array();

    $display("\n================================================");
    $display(" Summary: %0d/%0d checks passed   (%0d tests, %0d cycles)",
             pass_count, pass_count + fail_count, test_count, total_cycles);
    if (fail_count == 0) $display(" ALL TESTS PASSED");
    else                 $display(" %0d FAILURES", fail_count);
    $display("================================================");

    $finish;
  end

  // Safety: kill the simulation if we wedge.
  initial begin
    #200000;
    $display("\n*** GLOBAL TIMEOUT ***");
    $finish;
  end

endmodule
