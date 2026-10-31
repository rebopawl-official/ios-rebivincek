ENTRY(_start)
SECTIONS
{
	. = 0;
	.text : { *(.text.start) *(.text*) }
	.rodata : { *(.rodata*) }
	.data : { *(.data*) }
	_file_end = .;
	.bss : { *(.bss*) *(COMMON) }
	. = 0xf000;
	_stack_top = .;
	/DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) *(.got*) *(.plt*) *(.rela*) }
}
