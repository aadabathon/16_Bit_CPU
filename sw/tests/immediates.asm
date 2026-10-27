; ADDI is sign-extended (-32..31), ANDI zero-extended (0..63).
;! R1 == 31
;! R2 == 0xFFE0
;! R3 == 0xFFFF
;! R4 == 0x003F
;! R5 == 0x0015
;! R6 == 0
;! NZP == 010
        ADDI R1, R0, 31
        ADDI R2, R0, -32
        ADDI R3, R0, -1
        ANDI R4, R3, 63
        ADDI R5, R0, 31
        ANDI R5, R5, 0x15
        ANDI R6, R3, 0          ; 0 -> Z
        HALT
