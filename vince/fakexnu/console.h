#pragma once
#include <stdint.h>

#define CON_MAXCOLS 64
#define CON_MAXROWS 66

/*
 * Text console that mirrors every line to up to four framebuffer targets
 * (the bootloader's splash buffer may be at an address and pixel format we
 * only learn after reading the display controller). Lines are kept in RAM
 * and redrawn on a new target. Pixels are written as 0x00RRGGBB, stored as
 * bytes B,G,R(,A) for 3- and 4-byte formats.
 */
void con_init(void);
/* Add a framebuffer and draw the whole log on it. Returns 0 on success. */
int con_add_target(uintptr_t base, uint32_t w, uint32_t h, uint32_t stride, uint32_t bpp);
/* Append a line; returns its index. */
int con_line(const char *s, uint32_t color);
/* Replace an existing line and redraw it. */
void con_set(int idx, const char *s, uint32_t color);
int con_targets(void);

#ifdef HOST
volatile uint8_t *host_fb_map(uintptr_t phys, uint32_t bytes);
#endif
