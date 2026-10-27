# Basys3 bitstream for adam16, without a Vivado project. From the repository root:
#
#   vivado -mode batch -source fpga/build.tcl                   # pipelined core
#   vivado -mode batch -source fpga/build.tcl -tclargs multi    # multicycle core
#
# (or `make fpga`, `make fpga FPGA_CORE=multi`). Writes build/fpga/<core>/:
# basys3_top.bit, utilization.rpt, timing.rpt, and post-route.dcp.
#
# The program is fpga/mem/adam16_sum_array.mem, read into block RAM at
# configuration. To run another program, assemble it (sw/asm.py) over that
# file, or change MEM_INIT below, and rebuild.

set core [expr {[llength $argv] > 0 ? [lindex $argv 0] : "pipe"}]
if {$core ni {pipe multi}} {
    error "core must be 'pipe' or 'multi', not '$core'"
}
set pipelined [expr {$core eq "pipe" ? 1 : 0}]

set root [file normalize [file join [file dirname [info script]] ..]]
set out  [file join $root build fpga $core]
file mkdir $out
set part xc7a35tcpg236-1

read_verilog -sv [list \
    $root/rtl/adam16_isa.sv \
    $root/rtl/adam16_alu.sv \
    $root/rtl/adam16_regfile.sv \
    $root/rtl/adam16_datapath.sv \
    $root/rtl/adam16_control_fsm.sv \
    $root/rtl/adam16_core.sv \
    $root/rtl/adam16_pipe_decode.sv \
    $root/rtl/adam16_pipe_core.sv \
    $root/rtl/adam16_sram.sv \
    $root/rtl/adam16_dpram.sv \
    $root/rtl/debounce.sv \
    $root/rtl/basys3_top.sv]
read_mem $root/fpga/mem/adam16_sum_array.mem
read_xdc $root/fpga/constraints/adam16.xdc

synth_design -top basys3_top -part $part \
    -generic "PIPELINED=1'b$pipelined" \
    -generic {MEM_INIT=adam16_sum_array.mem}
opt_design
place_design
phys_opt_design
route_design

report_utilization    -file $out/utilization.rpt
report_timing_summary -file $out/timing.rpt
write_checkpoint -force $out/post-route.dcp
write_bitstream  -force $out/basys3_top.bit

set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
puts "adam16 ($core core): wrote $out/basys3_top.bit, worst setup slack $wns ns"
