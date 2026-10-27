; JMP through a register; undefined opcodes 0xE / 0xF do nothing.
;! R1 == 2
;! R2 == 0
        LEA  R4, there
        JMP  R4
        ADDI R2, R2, 1          ; skipped
there:  INC  R1, R1
        .word 0xE123            ; undefined: no effect
        .word 0xFFFF            ; undefined: no effect
        INC  R1, R1
        HALT
