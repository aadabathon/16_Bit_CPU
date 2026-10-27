# Changelog

Versions follow [semantic versioning](https://semver.org): the major number changes with the microarchitecture, never with the ISA, which is frozen. Neither release is tagged yet.

## [2.0.0] — unreleased

### Added
- `adam16_pipe_core`: five-stage pipeline (IF ID EX MEM WB) running the same ISA. Full forwarding, no stalls (load data is forwarded from MEM), one bubble per taken branch or jump. `sum_array` runs in 43 cycles instead of 191; CPI 1.16 over 2000 random programs.
- `adam16_pipe_decode`, the ID-stage decoder, with its spec (`docs/tools/pipe_decode_spec.py`) checked against it for all 65536 instruction words.
- `adam16_dpram`: dual-port memory, one fetch port and one data port.
- `basys3_top` parameter `PIPELINED` (default 1) picks the core.
- Docs: [chapter 7](docs/07_pipeline.md), the pipeline, with a block diagram and a cycle-by-cycle table taken from simulation; interface sheets for the new modules.

## [1.0.0] — unreleased

### Added
- Assembler (`sw/asm.py`), instruction-set simulator (`sw/iss.py`), random program generator (`sw/randprog.py`) and a regression (`sw/regress.py`) that compares the ISS and the cores instruction by instruction.
- Directed test programs in `sw/tests/`.
- `tb/tb_program.sv` (runs any program on either core and logs retires), `tb/tb_basys3.sv` (the board demo, both cores), and a black-box `tb/tb_adam16_gate.sv` for netlists of either core.
- Clock enable `ce` on the core, `en` on the memory.
- `fpga/build.tcl`: project-free Vivado build (`make fpga`).
- `make regress`, `demo`, `gate-rtl`, `fpga`; CI runs all checks.
- Docs: [chapter 8](docs/08_verification.md), verification; LICENSE (MIT), CONTRIBUTING, this changelog.

### Changed
- Renamed the project and every module from `cpu16` to **adam16**.
- **CMP** is a true signed compare. It used to take its flags from `SR1 − SR2`, which was wrong when the subtraction overflowed.
- The register file has two read ports instead of three; `BYPASS` parameter for write-first reads.
- `basys3_top` runs everything on the 100 MHz clock and uses the step button as a clock enable, instead of clocking the core from a logic gate. The memory image path is a parameter, no longer an absolute Windows path.
- `scripts/adam16.dc` and `scripts/adam16_sim.do` take their paths and the top module from environment variables.
- `debounce` flip-flops have power-up values, so it simulates without X.

### Removed
- The committed Vivado project (with its empty block design and stale checkpoint).

## Before 1.0

The original multicycle design: `adam16_core` with its 14-state controller, the directed testbench, the Basys3 wrapper, and the documentation set (bubble diagrams generated from a spec checked against the RTL, interface sheets, timing diagrams).
