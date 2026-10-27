# cpu16 — top-level build
#
#   make test     RTL testbench (Icarus Verilog)
#   make lint     Verilator lint, all warnings on
#   make docs     regenerate the documentation figures and tables
#   make check    everything CI runs: test + lint + docs checks
#   make wave     testbench with a VCD dump (build/cpu16.vcd) for GTKWave
#   make clean
#
# Needs: iverilog, verilator, python3, graphviz.

BUILD := build

CORE_RTL := rtl/cpu16_isa.sv rtl/cpu16_alu.sv rtl/cpu16_regfile.sv \
            rtl/cpu16_datapath.sv rtl/cpu16_control_fsm.sv rtl/cpu16_core.sv
FPGA_RTL := rtl/Sram.sv rtl/debounce.sv rtl/basys3_top.sv

# PINCONNECTEMPTY: outputs deliberately left open with `.port()`.
# DECLFILENAME: rtl/Sram.sv holds module SramSBC; drop this once it is renamed (see ROADMAP.md).
LINT_FLAGS := --lint-only -Wall -Wno-PINCONNECTEMPTY -Wno-DECLFILENAME

all: check

test:
	@mkdir -p $(BUILD)
	@rm -f $(BUILD)/cpu16_tb $(BUILD)/tb_cpu16.log   # a failed compile must not reuse an old binary
	iverilog -g2012 -o $(BUILD)/cpu16_tb $(CORE_RTL) rtl/Sram.sv tb/tb_cpu16.sv 2>&1 | grep -v "sorry:" || true
	vvp $(BUILD)/cpu16_tb | tee $(BUILD)/tb_cpu16.log | grep -E "^\[T|FAIL|TIMEOUT|Summary|ALL TESTS|FAILURES"
	@grep -q "ALL TESTS PASSED" $(BUILD)/tb_cpu16.log

wave:
	@mkdir -p $(BUILD)
	iverilog -g2012 -o $(BUILD)/cpu16_tb $(CORE_RTL) rtl/Sram.sv tb/tb_cpu16.sv 2>&1 | grep -v "sorry:" || true
	vvp $(BUILD)/cpu16_tb +VCD=$(BUILD)/cpu16.vcd > /dev/null
	@echo "wrote $(BUILD)/cpu16.vcd"

lint:
	verilator $(LINT_FLAGS) --top-module cpu16_core $(CORE_RTL)
	verilator $(LINT_FLAGS) --top-module basys3_top $(CORE_RTL) $(FPGA_RTL)
	@echo "lint: clean"

docs:
	$(MAKE) -C docs

check: test lint
	$(MAKE) -C docs check

clean:
	rm -rf $(BUILD)

.PHONY: all test wave lint docs check clean
