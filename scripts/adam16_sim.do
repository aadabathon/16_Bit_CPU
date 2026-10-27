#==============================================================
#  adam16 — gate-level simulation of a synthesized core
#  (Questa / ModelSim), with tb/tb_adam16_gate.sv:
#
#    vsim -c -do <repo>/scripts/adam16_sim.do
#    ADAM16_TOP=adam16_pipe_core vsim -c -do <repo>/scripts/adam16_sim.do
#
#  Environment (all optional):
#    ADAM16_TOP      adam16_core (default) or adam16_pipe_core
#    ADAM16_NETLIST  the netlist  (default netlist/<top>.mapped.v)
#    ADAM16_CELLS    Verilog models of the standard cells (default ./saed32nm.v)
#
#  The testbench only uses the core's ports and the memory, so it
#  needs no knowledge of the netlist's internal names. `make gate-rtl`
#  runs the same testbench on the RTL.
#==============================================================

proc env_or {name default} {
    if {[info exists ::env($name)] && $::env($name) ne ""} { return $::env($name) }
    return $default
}

set ROOT    [file normalize [file join [file dirname [info script]] ..]]
set TOP     [env_or ADAM16_TOP     adam16_core]
set NETLIST [env_or ADAM16_NETLIST netlist/$TOP.mapped.v]
set CELLS   [env_or ADAM16_CELLS   ./saed32nm.v]

if {$TOP eq "adam16_pipe_core"} {
    set MEM    $ROOT/rtl/adam16_dpram.sv
    set DEFINE +define+PIPE
} else {
    set MEM    $ROOT/rtl/adam16_sram.sv
    set DEFINE ""
}

vlib work
vmap work work

vlog $CELLS
vlog $NETLIST
vlog -sv $MEM
vlog -sv {*}$DEFINE $ROOT/tb/tb_adam16_gate.sv

vsim -voptargs=+acc +notimingchecks work.tb_adam16_gate
run -all
