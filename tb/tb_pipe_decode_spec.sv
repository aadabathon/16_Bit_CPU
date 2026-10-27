`timescale 1ns/1ps

// =============================================================================
//  tb_pipe_decode_spec — exhaustive check: adam16_pipe_decode vs. its spec.
//
//  The spec is docs/tools/pipe_decode_spec.py, the same data the decode
//  table in docs/07_pipeline.md comes from. `--vectors` writes one line per
//  instruction word, 0x0000 to 0xFFFF in order: the expected outputs packed
//  MSB first in the order of OUTPUTS there (41 bits, hex).
//
//  Run (from the repository root):  make -C docs check
// =============================================================================

module tb_pipe_decode_spec;

  logic [15:0] ir;
  logic [2:0]  ra0, ra1, rd, br_mask;
  logic        reg_we, flag_we, mem_we, b_imm, jump;
  logic [1:0]  wb_sel, a_sel;
  logic [3:0]  alu_op;
  logic [15:0] imm;

  adam16_pipe_decode dut (
    .ir(ir), .ra0(ra0), .ra1(ra1), .rd(rd), .reg_we(reg_we), .flag_we(flag_we),
    .mem_we(mem_we), .wb_sel(wb_sel), .alu_op(alu_op), .a_sel(a_sel), .b_imm(b_imm),
    .imm(imm), .br_mask(br_mask), .jump(jump)
  );

  // Packing order must match OUTPUTS in docs/tools/pipe_decode_spec.py.
  wire [40:0] outs = {ra0, ra1, rd, reg_we, flag_we, mem_we, wb_sel, alu_op,
                      a_sel, b_imm, imm, br_mask, jump};

  logic [40:0] expected [0:65535];

  initial begin
    string path;
    int    n_fail;

    if (!$value$plusargs("VECTORS=%s", path)) path = "build/pipe_decode_vectors.txt";
    for (int i = 0; i < 65536; i++) expected[i] = 'x;
    $readmemh(path, expected);

    n_fail = 0;
    for (int i = 0; i < 65536; i++) begin
      ir = i[15:0];
      #1;
      if (outs !== expected[i]) begin
        n_fail++;
        if (n_fail <= 10)
          $display("  MISMATCH ir=%h: got %h expected %h", ir, outs, expected[i]);
      end
    end

    $display("================================================");
    $display(" adam16_pipe_decode vs docs/tools/pipe_decode_spec.py");
    $display(" 65536 instruction words checked, %0d mismatches", n_fail);
    if (n_fail == 0) $display(" RTL MATCHES SPEC");
    else             $display(" RTL DOES NOT MATCH SPEC");
    $display("================================================");
    $finish;
  end

endmodule
