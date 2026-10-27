; sum_array: sum mem[0x000B..0x000F] = 1+2+3+4+5 = 15, store the result at 0x0010.
; Same program as fpga/mem/adam16_sum_array.mem and testbench T12.
;   R1 = array pointer, R2 = count, R3 = running sum, R4 = current element
;! R3 == 15
;! M[0x0010] == 15
;! R1 == 0x0010
;! R2 == 0

        LEA  R1, data       ; R1 = 0x000B
        ADDI R2, R0, 5
        MOV  R3, R0         ; R3 = 0
loop:   LDR  R4, R1, 0
        ADD  R3, R3, R4
        INC  R1, R1
        DEC  R2, R2
        CMP  R2, R0
        BRp  loop
        ST   R3, result
        HALT
data:   .word 1, 2, 3, 4, 5
result: .space 1
