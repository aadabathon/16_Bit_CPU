module debounce #(
  parameter int CYCLES = 200_000  // ~2 ms settle time at 100 MHz
)(
  input  logic clk,
  input  logic btn_in,
  output logic btn_clean,  // debounced level
  output logic btn_pulse   // 1-cycle pulse on debounced rising edge
);

  logic [1:0] sync;
  logic [$clog2(CYCLES+1)-1:0] cnt;
  logic stable, stable_d;

  always_ff @(posedge clk) sync <= {sync[0], btn_in};

  always_ff @(posedge clk) begin
    if (sync[1] != stable) begin
      cnt <= cnt + 1'b1;
      if (cnt == CYCLES) begin
        stable <= sync[1];
        cnt    <= '0;
      end
    end else begin
      cnt <= '0;
    end
  end

  always_ff @(posedge clk) stable_d <= stable;

  assign btn_clean = stable;
  assign btn_pulse = stable & ~stable_d;

endmodule
