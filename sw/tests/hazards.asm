; Pipeline hazard patterns. Every value is computed from the one produced
; just before it, at distance 1, 2 and 3, on both ALU inputs, through loads,
; stores, flags and R7. Correct on any in-order core.
;! R1 == 2
;! R2 == 4
;! R3 == 8
;! R4 == 16
;! R5 == 0x0070
;! R6 == 7
;! M[0x70] == 16
;! M[0x71] == 17
;! M[0x72] == 34
;! R0 == 16
;! R7 == 0x001A
        ADDI R1, R0, 1
        ADD  R1, R1, R1         ; distance 1, both operands: 2
        ADD  R2, R1, R1         ; 4
        NOP
        ADD  R3, R2, R2         ; distance 2: 8
        NOP
        NOP
        ADD  R4, R3, R3         ; distance 3: 16
        LEA  R5, buf            ; base used right away
        STR  R4, R5, 0          ; store data and base both just produced
        LDR  R6, R5, 0          ; load right after a store to the same address
        INC  R6, R6             ; load-use, distance 1: 17
        STR  R6, R5, 1
        LDR  R6, R5, 1          ; 17
        ADD  R6, R6, R6         ; load-use: 34
        STR  R6, R5, 2          ; store of a just-computed value
        LDR  R6, R5, 0          ; 16
        NOP
        ADDI R6, R6, -9         ; load-use, distance 2: 7
        CMP  R6, R4             ; 7 < 16 -> N
        BRn  f1                 ; branch right after the flag producer
        ADDI R6, R6, 0x10       ; skipped
f1:     LDR  R0, R5, 0          ; loads don't set flags...
        BRn  f2                 ; ...so this still sees N from the CMP
        ADDI R6, R6, 0x10       ; skipped
f2:     JSR  sub                ; JSR then immediate RET in the callee
        HALT
sub:    RET
        .org 0x0070
buf:    .space 3
