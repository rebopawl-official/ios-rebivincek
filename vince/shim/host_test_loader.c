/*
 * PC test of loader.c: run the real loader code against mmap()ed "physical" memory.
 *   host_test_loader PAYLOAD DTB EXPECT_KERNEL_MACHO
 * "Physical" addresses are the same numbers as on the phone (0x13600000 ramdisk, 0x20000000 kernel RAM).
 * The jump is replaced by a check of everything xnu would find: segments, zero-fill, boot_args, ADT, cmdline.
 */
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include "console.h"

void loader_main(uint64_t dtb, uint64_t img);

static uint8_t fb[3240 * 2160];
volatile uint8_t *host_fb_map(uintptr_t phys, uint32_t bytes) { (void)phys; (void)bytes; return fb; }

static uint8_t *payload, *kernel;
static size_t payload_len, kernel_len;
static int jumped;

static void fail(const char *m) { printf("HOST TEST FAIL: %s\n", m); exit(1); }
void host_halt(void) { printf("loader halted (fail path)\n"); exit(2); }

static uint8_t *slurp(const char *p, size_t *n)
{
	FILE *f = fopen(p, "rb");
	if (!f) { perror(p); exit(1); }
	fseek(f, 0, SEEK_END); *n = (size_t)ftell(f); fseek(f, 0, SEEK_SET);
	uint8_t *b = malloc(*n);
	if (fread(b, 1, *n, f) != *n) fail("short read");
	fclose(f);
	return b;
}

void host_jump(uint64_t entry_pa, uint64_t ba_pa)
{
	jumped = 1;
	const uint64_t *h = (const uint64_t *)(payload + 0x10);	/* virt_base, entry_va, adt_off, adt_size, kernel_end, phys_base, mem_size */
	uint64_t virt_base = h[0], entry_va = h[1], adt_off = h[2], adt_size = h[3], kernel_end = h[4], phys_base = h[5], mem_size = h[6];
	uint64_t pa_of_va = phys_base - virt_base;
	if (entry_pa != entry_va + pa_of_va) fail("entry");
	uint32_t nsegs = *(uint32_t *)(payload + 12);
	for (uint32_t i = 0; i < nsegs; i++) {
		const uint64_t *s = (const uint64_t *)(payload + 0x2a8 + 32 * i);
		const uint8_t *dst = (const uint8_t *)(s[0] + pa_of_va);
		if (memcmp(dst, payload + s[2], s[3])) fail("segment data differs");
		for (uint64_t j = s[3]; j < s[1]; j++)
			if (dst[j]) { printf("nonzero at +%llx\n", (unsigned long long)j); fail("zero-fill"); }
	}
	/* the Mach-O file itself: __TEXT file bytes appear at the segment */
	if (memcmp((const uint8_t *)(0xfffffff007004000ULL + pa_of_va), kernel, kernel_len < 0x4000 ? kernel_len : 0x4000)) fail("macho head");
	uint64_t adt_pa = kernel_end + pa_of_va;
	if (memcmp((void *)adt_pa, payload + adt_off, adt_size)) fail("ADT differs");
	const volatile uint8_t *ba = (const uint8_t *)ba_pa;
	uint16_t rev = *(uint16_t *)ba, ver = *(uint16_t *)(ba + 2);
	uint64_t vb = *(uint64_t *)(ba + 8), pb = *(uint64_t *)(ba + 16), ms = *(uint64_t *)(ba + 24), top = *(uint64_t *)(ba + 32);
	uint64_t vbase = *(uint64_t *)(ba + 40), vdisp = *(uint64_t *)(ba + 48), vrow = *(uint64_t *)(ba + 56), vw = *(uint64_t *)(ba + 64), vh = *(uint64_t *)(ba + 72), vdep = *(uint64_t *)(ba + 80);
	uint64_t dtp = *(uint64_t *)(ba + 96);
	uint32_t dtl = *(uint32_t *)(ba + 104);
	if (rev != 2 || ver != 2) fail("rev/ver");
	if (vb != virt_base || pb != phys_base || ms != mem_size) fail("virt/phys/size");
	if (top <= adt_pa + adt_size || (top & 0x3fff) || top > phys_base + mem_size) fail("topOfKernelData");
	if (vbase || vdisp || vdep || vrow != 3240 || vw != 1080 || vh != 2160) fail("video");
	if (dtp != adt_pa - pa_of_va || dtl != adt_size) fail("deviceTree");
	if (strcmp((const char *)(ba + 108), (const char *)(payload + 0x48))) fail("cmdline");
	if (*(uint64_t *)(ba + 728) != mem_size) fail("memSizeActual");
	if (ba_pa & 0x3fff) fail("boot_args alignment");
	/* the on-screen log got drawn */
	long lit = 0;
	for (size_t i = 0; i < sizeof fb; i++) lit += fb[i] != 0;
	if (lit < 5000) fail("nothing drawn on the console");
	printf("HOST TEST PASS: entry_pa=%llx boot_args=%llx top=%llx adt=%llx+%llx lit_bytes=%ld\n",
	       (unsigned long long)entry_pa, (unsigned long long)ba_pa, (unsigned long long)top,
	       (unsigned long long)adt_pa, (unsigned long long)adt_size, lit);
	exit(0);
}

int main(int argc, char **argv)
{
	if (argc != 4) { fprintf(stderr, "usage\n"); return 1; }
	payload = slurp(argv[1], &payload_len);
	uint8_t *dtb = slurp(argv[2], &(size_t){0});
	kernel = slurp(argv[3], &kernel_len);
	void *rd = mmap((void *)0x13600000, 0x1000000, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
	if (rd != (void *)0x13600000) { perror("mmap ramdisk"); return 1; }
	memcpy(rd, payload, payload_len);
	void *ram = mmap((void *)0x20000000, 0x60000000, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE | MAP_FIXED_NOREPLACE, -1, 0);
	if (ram != (void *)0x20000000) { perror("mmap ram"); return 1; }
	memset(ram, 0xAA, 0x4000000);	/* dirty the first 64 MB: the loader must zero-fill what the Mach-O leaves zero */
	void *d = mmap((void *)0x13400000, 0x100000, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
	if (d != (void *)0x13400000) { perror("mmap dtb"); return 1; }
	memcpy(d, dtb, 0x2000);	/* generated, small */
	loader_main(0x13400000, 0x10080000);
	if (!jumped) fail("loader returned without jumping");
	return 0;
}
