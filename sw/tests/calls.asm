; JSR, JSRR (including JSRR R7), RET, nested calls through a saved R7, TRAP + RET.
;! R1 == 0x0111
;! R2 == 2
;! R3 == 0x0040
;! M[0x80] == 1
        JSR  sub_a              ; R1 |= 0x001
        LEA  R3, sub_b
        JSRR R3                 ; R1 |= 0x010
        LEA  R7, sub_c
        JSRR R7                 ; jumps to the OLD R7 (sub_c), then R7 = return address
        JSR  outer              ; nested: outer saves R7 in memory around an inner JSR
        TRAP x40                ; handler: R1 += 0x100, then RET
        LEA  R3, handler        ; R3 = 0x0040 (check value)
        HALT
sub_a:  ADDI R1, R1, 1
        RET
sub_b:  ADDI R1, R1, 0x10
        RET
sub_c:  ADDI R2, R2, 1
        RET
outer:  ST   R7, save
        JSR  inner
        LD   R7, save
        RET
inner:  ADDI R4, R0, 1
        ST   R4, flag
        ADDI R2, R2, 1
        RET
        .org 0x0040
handler: LEA R5, hbase          ; trap handler: R1 |= 0x100
        LDR  R6, R5, 0
        ADD  R1, R1, R6
        RET
hbase:  .word 0x0100
        .org 0x0080
flag:   .space 1
save:   .space 1
