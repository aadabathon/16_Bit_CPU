; LD / ST / LDR / STR / LEA, with negative offsets. Loads and LEA leave the flags alone.
;! R1 == 0x0050
;! R2 == 0xABCD
;! R3 == 0xABCD
;! R4 == 0x1234
;! R5 == 0x1234
;! M[0x51] == 0xABCD
;! M[0x4F] == 0x1234
;! M[0x60] == 0xABCD
;! NZP == 100
        ADDI R7, R0, -1         ; sets N; nothing below may change the flags
        LEA  R1, tbl            ; 0x0050, flags unchanged
        LDR  R2, R1, 0          ; 0xABCD
        STR  R2, R1, 1          ; M[0x51]
        LDR  R3, R1, 1
        LD   R4, k              ; 0x1234
        STR  R4, R1, -1         ; M[0x4F]
        LDR  R5, R1, -1
        ST   R3, dst            ; M[0x60]
        HALT
k:      .word 0x1234
        .org 0x0050
tbl:    .word 0xABCD
        .org 0x0060
dst:    .space 1
