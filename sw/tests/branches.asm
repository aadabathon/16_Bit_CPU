; Every branch mask, taken and not taken. Reset leaves Z set, so the first
; BRnzp is taken. A branch that goes the wrong way lands on
; 'bad' (R3 += 0x20) or falls into an R4 += 1.
;! R3 == 9
;! R4 == 0
        BRnzp start             ; taken straight out of reset
        ADDI R4, R4, 1          ; must be skipped
start:  BRz  z1                 ; Z is still set from reset
        ADDI R4, R4, 1
z1:     INC  R3, R3             ; 1
        ADDI R1, R0, -3         ; N
        BRn  ok1
        ADDI R4, R4, 1
ok1:    BRzp bad
        INC  R3, R3             ; 2
        ADDI R1, R0, 0          ; Z
        BRz  ok2
        ADDI R4, R4, 1
ok2:    BRnp bad
        INC  R3, R3             ; 3
        ADDI R1, R0, 7          ; P
        BRp  ok3
        ADDI R4, R4, 1
ok3:    BRnz bad
        INC  R3, R3             ; 4
        BRnzp ok4
        ADDI R4, R4, 1
ok4:    NOP                     ; empty mask: never taken
        INC  R3, R3             ; 5
        ADDI R1, R0, -1
        BRnz ok5
        ADDI R4, R4, 1
ok5:    BRnp ok6
        ADDI R4, R4, 1
ok6:    INC  R3, R3             ; 6
        ADDI R1, R0, 0
        BRzp ok7
        ADDI R4, R4, 1
ok7:    INC  R3, R3             ; 7
        BR   ok8                ; BR = BRnzp
        ADDI R4, R4, 1
ok8:    INC  R3, R3             ; 8
        INC  R3, R3             ; 9
        HALT
bad:    ADDI R3, R3, 0x10
        ADDI R3, R3, 0x10
        HALT
