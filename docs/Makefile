# Documentation build and checks. Run from the repository root:
#
#   make -C docs          regenerate every figure and generated table
#   make -C docs check    prove the docs match the RTL (no files are changed)
#
# Needs: python3, graphviz (dot, neato), iverilog (pipeview and `check`),
# and the WaveDrom CLI for the timing diagrams (npm i -g wavedrom-cli).

PY       ?= python3
WAVEDROM ?= wavedrom-cli
BUILD    := ../build

TIMING := figures/timing_alu.svg figures/timing_load.svg figures/timing_store.svg

all: fsm decode pipeview symbols blocks figures/pipeline.svg figures/datapath.svg figures/top_level.svg \
     figures/debounce_fsm.svg $(TIMING)

# Control FSM bubble diagrams + the tables in 03_control.md, from tools/fsm_spec.py
fsm:
	$(PY) tools/gen_fsm.py

# The pipelined core's decode table in 07_pipeline.md, from tools/pipe_decode_spec.py
decode:
	$(PY) tools/pipe_decode_spec.py

# The cycle-by-cycle table in 07_pipeline.md, from a simulation of the RTL
pipeview:
	$(PY) tools/gen_pipeview.py

# Module symbols from the RTL headers
symbols:
	$(PY) tools/gen_symbols.py

# Instantiation templates and connection tables in interfaces/*.md
blocks:
	$(PY) tools/gen_interconnect.py

figures/datapath.svg: tools/gen_datapath.py tools/svgkit.py
	$(PY) tools/gen_datapath.py

figures/pipeline.svg: tools/gen_pipeline.py tools/svgkit.py
	$(PY) tools/gen_pipeline.py

figures/top_level.svg: tools/gen_top_level.py tools/svgkit.py
	$(PY) tools/gen_top_level.py

figures/debounce_fsm.svg: figures/src/debounce_fsm.dot
	neato -n2 -Tsvg $< -o $@

figures/timing_%.svg: figures/src/timing_%.json tools/wavedrom_bg.py
	$(WAVEDROM) -i $< -s $@
	$(PY) tools/wavedrom_bg.py $@

# ---------------------------------------------------------------- checks
check: check-ports check-blocks check-fsm check-decode check-links

check-ports:
	$(PY) tools/check_ports.py

check-blocks:
	$(PY) tools/gen_interconnect.py --check
	$(PY) tools/gen_fsm.py --check
	$(PY) tools/pipe_decode_spec.py --check
	$(PY) tools/gen_pipeview.py --check

check-fsm:
	@mkdir -p $(BUILD)
	@rm -f $(BUILD)/fsm_spec_tb $(BUILD)/fsm_spec.log   # a failed compile must not reuse an old binary
	$(PY) tools/gen_fsm.py --vectors $(BUILD)/fsm_vectors.txt
	iverilog -g2012 -o $(BUILD)/fsm_spec_tb ../rtl/adam16_isa.sv \
	    ../rtl/adam16_control_fsm.sv ../tb/tb_control_fsm_spec.sv 2>&1 | grep -v "sorry:" || true
	vvp $(BUILD)/fsm_spec_tb +VECTORS=$(BUILD)/fsm_vectors.txt | tee $(BUILD)/fsm_spec.log
	@grep -q "RTL MATCHES SPEC" $(BUILD)/fsm_spec.log

check-decode:
	@mkdir -p $(BUILD)
	@rm -f $(BUILD)/pipe_decode_tb $(BUILD)/pipe_decode.log
	$(PY) tools/pipe_decode_spec.py --vectors $(BUILD)/pipe_decode_vectors.txt
	iverilog -g2012 -o $(BUILD)/pipe_decode_tb ../rtl/adam16_isa.sv \
	    ../rtl/adam16_pipe_decode.sv ../tb/tb_pipe_decode_spec.sv 2>&1 | grep -v "sorry:" || true
	vvp $(BUILD)/pipe_decode_tb +VECTORS=$(BUILD)/pipe_decode_vectors.txt | tee $(BUILD)/pipe_decode.log
	@grep -q "RTL MATCHES SPEC" $(BUILD)/pipe_decode.log

check-links:
	$(PY) tools/check_links.py

.PHONY: all fsm decode pipeview symbols blocks check check-ports check-blocks check-fsm check-decode check-links
