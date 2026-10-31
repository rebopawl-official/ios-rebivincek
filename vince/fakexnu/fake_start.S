/*
 * Stand-in for the XNU entry point, used only to test the vince loader on the phone: entered
 * exactly like xnu (MMU and caches off, EL1, x0 = physical address of boot_args).
 * Position independent flat blob; mkfake_macho.py wraps it in a Mach-O at the kernel's link address.
 */
	.section .text.start, "ax"
	.globl _start
_start:
	msr	daifset, #0xf
	mov	x19, x0
	adr	x1, _stack_top
	mov	sp, x1
	adr	x1, vectors
	msr	vbar_el1, x1
	isb
	adr	x1, _head
	mov	x0, x19
	bl	fake_main
1:	wfe
	b	1b

	.globl _head
_head:
	nop

.macro vent slot
	.balign	0x80
	stp	x29, x30, [sp, #-16]!
	mov	x29, #\slot
	b	exc_common
.endm
	.balign	0x800
vectors:
	vent 0
	vent 1
	vent 2
	vent 3
	vent 4
	vent 5
	vent 6
	vent 7
	vent 8
	vent 9
	vent 10
	vent 11
	vent 12
	vent 13
	vent 14
	vent 15
exc_common:
	sub	sp, sp, #(30 * 8)
	stp	x0, x1, [sp, #0]
	mov	x0, x29
	mov	x1, sp
	bl	exc_handler
2:	wfe
	b	2b
