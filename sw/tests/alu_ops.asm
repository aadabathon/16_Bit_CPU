; Every ALU0 / ALU1 operation, and the flags each leaves behind.
;! R0 == 0xFFFC
;! R1 == 3
;! R2 == 5
;! R3 == 0xFFF8
;! R4 == 0x0006
;! R5 == 0xFFFB
;! M[0x40] == 8
;! M[0x41] == 0xFFFE
;! M[0x42] == 1
;! M[0x43] == 7
;! M[0x44] == 6
;! M[0x45] == 3
;! M[0x46] == 0xFFFD
;! M[0x47] == 0xFFFE
;! M[0x48] == 4
;! M[0x49] == 4
;! M[0x4A] == 6
;! M[0x4B] == 0x7FFF
;! M[0x4C] == 0xFFFE
;! NZP == 100
        LEA  R6, out             ; R6 = 0x0040, the result block
        ADDI R1, R0, 3
        ADDI R2, R0, 5
        ADD  R3, R1, R2
        STR  R3, R6, 0        ; 8
        SUB  R3, R1, R2
        STR  R3, R6, 1        ; -2
        AND  R3, R1, R2
        STR  R3, R6, 2        ; 1
        OR   R3, R1, R2
        STR  R3, R6, 3        ; 7
        XOR  R3, R1, R2
        STR  R3, R6, 4        ; 6
        MOV  R3, R1
        STR  R3, R6, 5        ; 3
        NEG  R3, R1
        STR  R3, R6, 6        ; -3
        NAND R3, R1, R2
        STR  R3, R6, 7        ; 0xFFFE
        INC  R3, R1
        STR  R3, R6, 8        ; 4
        DEC  R3, R2
        STR  R3, R6, 9        ; 4
        LSL1 R3, R1
        STR  R3, R6, 10        ; 6
        NOT  R4, R0              ; 0xFFFF
        LSR1 R3, R4
        STR  R3, R6, 11        ; 0x7FFF
        ADDI R4, R0, -4          ; 0xFFFC
        ASR1 R3, R4
        STR  R3, R6, 12        ; 0xFFFE
        NOT  R0, R1              ; R0 is an ordinary register: 0xFFFC
        NOR  R3, R1, R2          ; ~(3|5) = 0xFFF8
        ADDI R4, R0, 10          ; 0xFFFC + 10 = 6
        NEG  R5, R2              ; -5, sets N
        HALT
        .org 0x0040
out:    .space 13
