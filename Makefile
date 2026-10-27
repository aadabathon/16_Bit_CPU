# adam16 — top-level build
#
#   make test      directed testbench, multicycle core (Icarus Verilog)
#   make regress   every sw/tests program + RANDOM_N random programs on the ISS
#                  and both cores, retire traces compared (SEED=, RANDOM_N=, CORES=)
#   make demo      the Basys3 demo in simulation, both cores (checks demo.md)
#   make gate-rtl  the black-box gate-level testbench, run on the RTL of both cores
#   make lint      Verilator lint, all warnings on, every top and configuration
#   make docs      regenerate the documentation figures and tables
#   make check     everything CI runs: all of the above + the docs checks
#   make wave      directed testbench with a VCD dump (build/adam16.vcd)
#   make fpga      Basys3 bitstream with Vivado (FPGA_CORE=pipe or multi)
#   make clean
#
# Needs: iverilog, verilator, python3, graphviz. `make fpga` needs Vivado.

BUILD := build
PY    := python3

ISA_RTL   := rtl/adam16_isa.sv rtl/adam16_alu.sv rtl/adam16_regfile.sv
MULTI_RTL := $(ISA_RTL) rtl/adam16_datapath.sv rtl/adam16_control_fsm.sv rtl/adam16_core.sv
PIPE_RTL  := $(ISA_RTL) rtl/adam16_pipe_decode.sv rtl/adam16_pipe_core.sv
ALL_RTL   := $(MULTI_RTL) rtl/adam16_pipe_decode.sv rtl/adam16_pipe_core.sv \
             rtl/adam16_sram.sv rtl/adam16_dpram.sv rtl/debounce.sv rtl/basys3_top.sv

CORES     ?= multi,pipe
SEED      ?= 1
RANDOM_N  ?= 200
FPGA_CORE ?= pipe

# PINCONNECTEMPTY: outputs deliberately left open with `.port()`.
LINT_FLAGS := --lint-only -Wall -Wno-PINCONNECTEMPTY
# iverilog's "sorry: ... not supported" notes are harmless; hide them.
QUIET      := 2>&1 | grep -v "sorry:" || true

all: check

test:
	@mkdir -p $(BUILD)
	@rm -f $(BUILD)/adam16_tb $(BUILD)/tb_adam16.log   # a failed compile must not reuse an old binary
	iverilog -g2012 -o $(BUILD)/adam16_tb $(MULTI_RTL) rtl/adam16_sram.sv tb/tb_adam16.sv $(QUIET)
	vvp $(BUILD)/adam16_tb | tee $(BUILD)/tb_adam16.log | grep -E "^\[T|FAIL|TIMEOUT|Summary|ALL TESTS|FAILURES"
	@grep -q "ALL TESTS PASSED" $(BUILD)/tb_adam16.log

wave:
	@mkdir -p $(BUILD)
	iverilog -g2012 -o $(BUILD)/adam16_tb $(MULTI_RTL) rtl/adam16_sram.sv tb/tb_adam16.sv $(QUIET)
	vvp $(BUILD)/adam16_tb +VCD=$(BUILD)/adam16.vcd > /dev/null
	@echo "wrote $(BUILD)/adam16.vcd"

regress:
	$(PY) sw/regress.py --cores $(CORES) --random $(RANDOM_N) --seed $(SEED)

demo:
	@mkdir -p $(BUILD)
	@rm -f $(BUILD)/tb_basys3 $(BUILD)/tb_basys3.log
	iverilog -g2012 -o $(BUILD)/tb_basys3 $(ALL_RTL) tb/tb_basys3.sv $(QUIET)
	vvp $(BUILD)/tb_basys3 | tee $(BUILD)/tb_basys3.log
	@grep -q "DEMO MATCHES" $(BUILD)/tb_basys3.log

gate-rtl:
	@mkdir -p $(BUILD)
	@rm -f $(BUILD)/gate_multi $(BUILD)/gate_pipe $(BUILD)/gate_*.log
	iverilog -g2012 -o $(BUILD)/gate_multi $(MULTI_RTL) rtl/adam16_sram.sv tb/tb_adam16_gate.sv $(QUIET)
	iverilog -g2012 -DPIPE -o $(BUILD)/gate_pipe $(PIPE_RTL) rtl/adam16_dpram.sv tb/tb_adam16_gate.sv $(QUIET)
	vvp $(BUILD)/gate_multi | tee $(BUILD)/gate_multi.log | grep -E "black-box|FAIL|Summary|ALL"
	vvp $(BUILD)/gate_pipe  | tee $(BUILD)/gate_pipe.log  | grep -E "black-box|FAIL|Summary|ALL"
	@grep -q "ALL BLACK-BOX TESTS PASSED" $(BUILD)/gate_multi.log
	@grep -q "ALL BLACK-BOX TESTS PASSED" $(BUILD)/gate_pipe.log

lint:
	verilator $(LINT_FLAGS) --top-module adam16_core $(MULTI_RTL)
	verilator $(LINT_FLAGS) --top-module adam16_pipe_core $(PIPE_RTL)
	verilator $(LINT_FLAGS) --top-module adam16_dpram rtl/adam16_dpram.sv
	verilator $(LINT_FLAGS) --top-module basys3_top -GPIPELINED="1'b0" $(ALL_RTL)
	verilator $(LINT_FLAGS) --top-module basys3_top -GPIPELINED="1'b1" $(ALL_RTL)
	@echo "lint: clean"

docs:
	$(MAKE) -C docs

check: test lint regress demo gate-rtl
	$(MAKE) -C docs check

fpga:
	vivado -mode batch -nojournal -log $(BUILD)/vivado_$(FPGA_CORE).log \
	    -source fpga/build.tcl -tclargs $(FPGA_CORE)

clean:
	rm -rf $(BUILD)

.PHONY: all test wave regress demo gate-rtl lint docs check fpga clean
