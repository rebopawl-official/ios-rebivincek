/*
 * Minimal flattened-device-tree reader (see fdt.h). Byte loads only: with
 * the MMU off every access is Device memory and must be naturally aligned.
 */
#include "fdt.h"

uint32_t fdt_be32(const uint8_t *p)
{
	return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

uint32_t fdt_totalsize(const uint8_t *fdt)
{
	return (fdt && fdt_be32(fdt) == 0xd00dfeedU) ? fdt_be32(fdt + 4) : 0;
}

static int comp_count(const char *path)
{
	int c = 0;
	const char *p = path;
	while (*p) {
		while (*p == '/')
			p++;
		if (!*p)
			break;
		c++;
		while (*p && *p != '/')
			p++;
	}
	return c;
}

static int comp_at(const char *path, int k, const char **s, int *n)
{
	const char *p = path;
	for (int i = 0;; i++) {
		while (*p == '/')
			p++;
		if (!*p)
			return 0;
		const char *st = p;
		while (*p && *p != '/')
			p++;
		if (i == k) {
			*s = st;
			*n = (int)(p - st);
			return 1;
		}
	}
}

static int name_matches(const char *node, const char *comp, int n)
{
	for (int i = 0; i < n; i++)
		if (node[i] != comp[i])
			return 0;
	return node[n] == 0 || node[n] == '@';
}

static int streq(const char *a, const char *b)
{
	while (*a && *a == *b)
		a++, b++;
	return *a == *b;
}

const uint8_t *fdt_prop(const uint8_t *fdt, const char *path, const char *prop, uint32_t *plen)
{
	uint32_t total = fdt_totalsize(fdt);
	if (!total)
		return 0;
	uint32_t off_struct = fdt_be32(fdt + 8), off_str = fdt_be32(fdt + 12), sz_struct = fdt_be32(fdt + 36);
	if (off_struct >= total || sz_struct > total - off_struct || off_str >= total)
		return 0;
	const uint8_t *p = fdt + off_struct;
	const uint8_t *end = p + sz_struct;
	const char *strs = (const char *)fdt + off_str;
	int ncomp = comp_count(path);
	int depth = 0;
	uint64_t ok = 0;	/* bit d: the node stack at depth d matches `path` */

	while (p + 4 <= end) {
		uint32_t tok = fdt_be32(p);
		p += 4;
		if (tok == 1) {		/* BEGIN_NODE */
			const char *name = (const char *)p;
			uint32_t l = 0;
			while (p + l < end && name[l])
				l++;
			p += (l + 1 + 3) & ~3U;
			depth++;
			if (depth >= 62)
				return 0;
			if (depth == 1) {
				ok = 1ULL << 1;
			} else {
				const char *cs;
				int cn;
				if (depth - 1 <= ncomp && ((ok >> (depth - 1)) & 1) &&
				    comp_at(path, depth - 2, &cs, &cn) && name_matches(name, cs, cn))
					ok |= 1ULL << depth;
				else
					ok &= ~(1ULL << depth);
			}
		} else if (tok == 2) {	/* END_NODE */
			ok &= ~(1ULL << depth);
			depth--;
			if (depth < 0)
				return 0;
		} else if (tok == 3) {	/* PROP */
			if (p + 8 > end)
				return 0;
			uint32_t len = fdt_be32(p), nameoff = fdt_be32(p + 4);
			const uint8_t *val = p + 8;
			if (((ok >> depth) & 1) && depth - 1 == ncomp && nameoff < total - off_str &&
			    streq(strs + nameoff, prop)) {
				*plen = len;
				return val;
			}
			p = val + ((len + 3) & ~3U);
		} else if (tok == 4) {	/* NOP */
			continue;
		} else {		/* END or garbage */
			break;
		}
	}
	return 0;
}
