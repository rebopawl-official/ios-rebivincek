#pragma once
#include <stdint.h>

/*
 * Find property `prop` of the node at `path` (e.g. "/chosen", "/memory",
 * "/soc/qcom,gcc"). A path component matches a node name with or without
 * its "@unit" suffix. Returns a pointer to the raw (big-endian) value and
 * its length, or 0. Reads bytes only, so it is safe on Device memory.
 */
const uint8_t *fdt_prop(const uint8_t *fdt, const char *path, const char *prop, uint32_t *plen);
uint32_t fdt_be32(const uint8_t *p);
uint32_t fdt_totalsize(const uint8_t *fdt);
