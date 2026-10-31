/*
 * vince XNU loader entry: arm64 Linux Image header so the Qualcomm LK treats the
 * loader like a kernel. LK enters at EL1, MMU/D-cache off, x0 = DTB pointer.
 *
 * Adapted from the boot shim of ios-sweet / ios-topaz (MIT licence); see NOTICE.md.
 * Position independent: it runs wherever LK puts it.
 */
	.section .text.head, "ax"
	.globl _head
_head:
	b	_start			/* code0 */
	.long	0			/* code1 */
	.quad	0x80000			/* text_offset: same as the stock vince kernel */
	.quad	_end			/* image_size (linked at 0) */
	.quad	0xa			/* flags: LE, 4K pages, place anywhere */
	.quad	0			/* res2 */
	.quad	0			/* res3 */
	.quad	0			/* res4 */
	.ascii	"ARM\x64"		/* magic */
	.long	0			/* res5 */

	.text
	.globl _start
_start:
	msr	daifset, #0xf
	mov	x19, x0			/* DTB pointer from LK */
	msr	spsel, #1
	adrp	x1, _stack_top
	add	x1, x1, :lo12:_stack_top
	mov	sp, x1
	adr	x1, vectors
	msr	vbar_el1, x1
	isb
	/* zero .bss */
	adrp	x1, _bss_start
	add	x1, x1, :lo12:_bss_start
	adrp	x2, _bss_end
	add	x2, x2, :lo12:_bss_end
1:	cmp	x1, x2
	b.hs	2f
	str	xzr, [x1], #8
	b	1b
2:	mov	x0, x19
	adr	x1, _head		/* where we actually run (MMU is off) */
	bl	loader_main
3:	wfe
	b	3b

/*
 * Exception vectors: any exception in the loader ends in an on-screen report.
 */
.macro vent slot
	.balign	0x80
	stp	x29, x30, [sp, #-16]!
	mov	x29, #\slot
	b	exc_common
.endm

	.balign	0x800
	.globl vectors
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
	stp	x2, x3, [sp, #16]
	mov	x0, x29
	mov	x1, sp
	bl	exc_handler
4:	wfe
	b	4b
