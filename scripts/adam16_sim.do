#--- Paths ----------------------------------------------------
set NETLIST ../../synth/work/netlist/cpu16_core.mapped.v
set SRAM    /userspace/ashebani/RTL_sandbox/16_Bit_CPU/rtl/Sram.sv
set TB ../../tb/tb_cpu16_gate.sv

#--- Work library ---------------------------------------------
vlib work
vmap work work

#--- Compile (cell models FIRST, then netlist, SRAM, TB) ------
set CELLS ./saed32nm_plain.v      
vlog     $NETLIST
vlog -sv $SRAM
vlog -sv $TB

#--- Elaborate + load (no -L needed; cells are in work now) ---
vsim -voptargs=+acc +notimingchecks work.tb_cpu16_gate

add wave -r /*
run -all
