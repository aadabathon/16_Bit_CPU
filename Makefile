# adam16 — top-level build
#
#   make test     RTL testbench (Icarus Verilog)
#   make lint     Verilator lint, all warnings on
#   make docs     regenerate the documentation figures and tables
#   make check    everything CI runs: test + lint + docs checks
#   make wave     testbench with a VCD dump (build/adam16.vcd) for GTKWave
#   make clean
#
# Needs: iverilog, verilator, python3, graphviz.

BUILD := build

CORE_RTL := rtl/adam16_isa.sv rtl/adam16_alu.sv rtl/adam16_regfile.sv \
            rtl/adam16_datapath.sv rtl/adam16_control_fsm.sv rtl/adam16_core.sv
FPGA_RTL := rtl/adam16_sram.sv rtl/debounce.sv rtl/basys3_top.sv

# PINCONNECTEMPTY: outputs deliberately left open with `.port()`.
LINT_FLAGS := --lint-only -Wall -Wno-PINCONNECTEMPTY

all: check

test:
	@mkdir -p $(BUILD)
	@rm -f $(BUILD)/adam16_tb $(BUILD)/tb_adam16.log   # a failed compile must not reuse an old binary
	iverilog -g2012 -o $(BUILD)/adam16_tb $(CORE_RTL) rtl/adam16_sram.sv tb/tb_adam16.sv 2>&1 | grep -v "sorry:" || true
	vvp $(BUILD)/adam16_tb | tee $(BUILD)/tb_adam16.log | grep -E "^\[T|FAIL|TIMEOUT|Summary|ALL TESTS|FAILURES"
	@grep -q "ALL TESTS PASSED" $(BUILD)/tb_adam16.log

wave:
	@mkdir -p $(BUILD)
	iverilog -g2012 -o $(BUILD)/adam16_tb $(CORE_RTL) rtl/adam16_sram.sv tb/tb_adam16.sv 2>&1 | grep -v "sorry:" || true
	vvp $(BUILD)/adam16_tb +VCD=$(BUILD)/adam16.vcd > /dev/null
	@echo "wrote $(BUILD)/adam16.vcd"

lint:
	verilator $(LINT_FLAGS) --top-module adam16_core $(CORE_RTL)
	verilator $(LINT_FLAGS) --top-module basys3_top $(CORE_RTL) $(FPGA_RTL)
	@echo "lint: clean"

docs:
	$(MAKE) -C docs

check: test lint
	$(MAKE) -C docs check

clean:
	rm -rf $(BUILD)

.PHONY: all test wave lint docs check clean
