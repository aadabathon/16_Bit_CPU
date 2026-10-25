# Regenerate every figure in this directory from its source in src/.
#   make            rebuild out-of-date figures
#   make -B         rebuild everything
# Needs: graphviz (dot), python3, and the WaveDrom CLI (npm i -g wavedrom-cli).

WAVEDROM ?= wavedrom-cli

SVGS = control_fsm.svg datapath.svg top_level.svg \
       timing_alu.svg timing_load.svg timing_store.svg

all: $(SVGS)

control_fsm.svg: src/control_fsm.dot
	dot -Tsvg $< -o $@

datapath.svg: src/datapath.py src/svgkit.py
	cd src && python3 datapath.py

top_level.svg: src/top_level.py src/svgkit.py
	cd src && python3 top_level.py

timing_%.svg: src/timing_%.json src/wavedrom_bg.py
	$(WAVEDROM) -i $< -s $@
	python3 src/wavedrom_bg.py $@

.PHONY: all
