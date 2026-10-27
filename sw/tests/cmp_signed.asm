; CMP is a signed compare, correct where SR1 - SR2 overflows.
; Each compare that sets the expected flag increments R3.
;! R3 == 8
        LD   R1, big            ; 0x7FFF
        LD   R2, small          ; 0x8000
        ADDI R5, R0, 1
        ADDI R6, R0, -1
        CMP  R1, R2             ; 32767 > -32768
        BRnz s1
        INC  R3, R3
s1:     CMP  R2, R1             ; -32768 < 32767
        BRzp s2
        INC  R3, R3
s2:     CMP  R2, R2             ; equal
        BRnp s3
        INC  R3, R3
s3:     CMP  R6, R5             ; -1 < 1
        BRzp s4
        INC  R3, R3
s4:     CMP  R2, R5             ; -32768 < 1 (R2 - R5 overflows to +)
        BRzp s5
        INC  R3, R3
s5:     CMP  R1, R6             ; 32767 > -1 (R1 - R6 overflows to -)
        BRnz s6
        INC  R3, R3
s6:     CMP  R0, R0             ; 0 == 0
        BRnp s7
        INC  R3, R3
s7:     CMP  R5, R0             ; 1 > 0
        BRnz s8
        INC  R3, R3
s8:     HALT
big:    .word 0x7FFF
small:  .word 0x8000
