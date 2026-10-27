# Contributing

adam16 is a finished design with a frozen ISA. Fixes, tests, documentation and tooling improvements are welcome; changes to the instruction set are not (the ISS, the assembler and both cores must keep running the same programs).

## Before you open a pull request

```bash
make check
```

It runs the directed testbench, the ISS-vs-RTL regression on both cores, the board demo, the black-box testbench, Verilator lint, and the documentation checks. CI runs the same target, so a PR needs it green. You need Icarus Verilog, Verilator, Python 3 and Graphviz.

## Changing the RTL

- **Keep lint clean.** `make lint` runs Verilator with `-Wall`. Waive a warning only where it is intended, with a `lint_off` / `lint_on` pair around the line and a comment saying why.
- **Change both cores together** if the change affects behaviour. The regression compares them with the ISS and with each other.
- **Add a test.** Put a program in `sw/tests/` with `;!` expectations (see [docs/08_verification.md](docs/08_verification.md#test-programs)). If the bug is in the pipeline, make sure the program would have failed before the fix.
- **Run more random programs** for anything touching hazards: `make regress RANDOM_N=2000`, or another `SEED=`.

## Changing the documentation

Much of `docs/` is generated or checked:

- Port and parameter tables on the interface pages are hand-written, and `make -C docs check` compares them with the RTL.
- Blocks between `<!-- BEGIN GENERATED -->` and `<!-- END GENERATED -->` are rewritten by `make -C docs`. Don't edit them by hand.
- The control FSM diagrams come from `docs/tools/fsm_spec.py`, and the pipeline decode table from `docs/tools/pipe_decode_spec.py`. Change the spec with the RTL; the check compares the two exhaustively.

Run `make -C docs` to regenerate, then `make -C docs check`.

## Style

Match the code around you: its naming, comment density and layout. In SystemVerilog that means `logic`, `always_ff` / `always_comb`, synchronous active-high reset, and one port per line in module headers (the documentation tools parse them).
