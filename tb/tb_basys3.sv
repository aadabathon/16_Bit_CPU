`timescale 1ns/1ps

// =============================================================================
//  tb_basys3 — the board demo in simulation, for both cores.
//
//  Two basys3_top instances (PIPELINED = 0 and 1) load the demo image
//  fpga/mem/adam16_sum_array.mem and share the buttons and switches. The
//  testbench presses reset, then presses step and checks the LEDs at the
//  press counts demo.md gives, so the demo instructions are tested.
//  The debouncers are shortened to DB cycles.
//
//  Run from the repository root:  make demo
// =============================================================================

module tb_basys3;

  localparam int DB = 4;

  logic        clk = 0;
  logic        btn_rst = 0, btn_step = 0;
  logic [15:0] sw = 16'h0000;
  logic [15:0] led_multi, led_pipe;

  always #5 clk = ~clk;

  basys3_top #(.PIPELINED(1'b0), .DEBOUNCE_CYCLES(DB), .MEM_INIT("fpga/mem/adam16_sum_array.mem"))
    board_multi (.clk(clk), .btn_rst(btn_rst), .btn_step(btn_step), .sw(sw), .led(led_multi));
  basys3_top #(.PIPELINED(1'b1), .DEBOUNCE_CYCLES(DB), .MEM_INIT("fpga/mem/adam16_sum_array.mem"))
    board_pipe  (.clk(clk), .btn_rst(btn_rst), .btn_step(btn_step), .sw(sw), .led(led_pipe));

  int presses = 0, n_pass = 0, n_fail = 0;

  task automatic hold(input int cycles);
    repeat (cycles) @(posedge clk);
  endtask

  task automatic press_reset();
    btn_rst = 1; hold(3 * DB + 10);
    btn_rst = 0; hold(3 * DB + 10);
    presses = 0;
  endtask

  task automatic press_step(input int count);
    while (presses < count) begin
      btn_step = 1; hold(DB + 10);
      btn_step = 0; hold(DB + 10);
      presses++;
    end
  endtask

  task automatic check(input string board, input logic [15:0] led, input logic [1:0] view,
                       input logic [15:0] expected, input string what);
    if (led === expected) begin
      n_pass++;
      $display("  PASS  %-5s press %3d  sw=%b  LEDs 0x%04h  %s", board, presses, view, led, what);
    end else begin
      n_fail++;
      $display("  FAIL  %-5s press %3d  sw=%b  LEDs 0x%04h, expected 0x%04h  %s",
               board, presses, view, led, expected, what);
    end
  endtask

  task automatic look(input string board, input int at, input logic [1:0] view,
                      input logic [15:0] expected, input string what);
    press_step(at);
    sw[1:0] = view;
    #1;
    check(board, board == "multi" ? led_multi : led_pipe, view, expected, what);
  endtask

  initial begin
    $display("basys3_top demo: sum_array, both cores");

    // ---- multicycle core (demo.md, PIPELINED = 0) ----
    press_reset();
    look("multi", 0,   2'b00, 16'h0000, "PC after reset");
    look("multi", 27,  2'b10, 16'd1,    "ALU: sum 1");
    look("multi", 60,  2'b10, 16'd3,    "ALU: sum 3");
    look("multi", 93,  2'b10, 16'd6,    "ALU: sum 6");
    look("multi", 126, 2'b10, 16'd10,   "ALU: sum 10");
    look("multi", 159, 2'b10, 16'd15,   "ALU: sum 15");
    look("multi", 189, 2'b01, 16'h9025, "IR: HALT fetched");
    look("multi", 191, 2'b00, 16'h0025, "PC: TRAP x025 done");

    // ---- pipelined core (demo.md, PIPELINED = 1) ----
    press_reset();
    look("pipe", 0,  2'b01, 16'hD000, "IR: WB empty after reset (NOP)");
    look("pipe", 4,  2'b00, 16'h0000, "PC: LEA retiring");
    look("pipe", 4,  2'b10, 16'h000B, "result: R1 = 0x000B");
    look("pipe", 8,  2'b10, 16'd1,    "result: sum 1");
    look("pipe", 15, 2'b10, 16'd3,    "result: sum 3");
    look("pipe", 22, 2'b10, 16'd6,    "result: sum 6");
    look("pipe", 29, 2'b10, 16'd10,   "result: sum 10");
    look("pipe", 36, 2'b10, 16'd15,   "result: sum 15");
    look("pipe", 38, 2'b11, 16'h0002, "flags: Z after the last DEC R2");
    look("pipe", 42, 2'b01, 16'h9025, "IR: HALT retiring");

    $display("%0d passed, %0d failed", n_pass, n_fail);
    if (n_fail == 0) $display("DEMO MATCHES");
    else             $display("DEMO DOES NOT MATCH");
    $finish;
  end

endmodule
