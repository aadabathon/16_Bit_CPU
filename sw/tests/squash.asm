; The instruction right behind a taken branch or a jump is fetched by the
; pipeline and must then vanish: no register, flag or memory write.
; Each shadow instruction below would change something if it ran. A wrong
; store never retires, so the program reads its target back at the end.
;! R1 == 0x0040
;! R2 == 5
;! R3 == 0
;! R5 == 0
;! R6 == 0
;! M[0x40] == 0
;! M[0x41] == 5
;! NZP == 001
        LEA  R1, buf            ; R1 = 0x0040
        ADDI R2, R0, 5          ; P
        BRp  t1                 ; taken
        STR  R2, R1, 0          ; shadow: store
t1:     BRnzp t2
        ADDI R3, R0, -1         ; shadow: register and flags (N)
t2:     LEA  R4, t3
        JMP  R4
        CMP  R0, R2             ; shadow: flags only (N)
t3:     JSR  sub
        ST   R2, buf2           ; runs after the RET
        LDR  R6, R1, 0          ; read back: a squashed store would show here
        HALT
sub:    RET
        ADDI R5, R0, 1          ; shadow of RET: never runs
        .org 0x0040
buf:    .space 1
buf2:   .space 1
