#!/usr/bin/env python3
"""Tiny FDT with /chosen linux,initrd-start/-end (what LK adds), for the loader host test. usage: mkfdt.py START END OUT"""
import struct, sys
start, end, out = int(sys.argv[1], 0), int(sys.argv[2], 0), sys.argv[3]
strs = b'linux,initrd-start\0linux,initrd-end\0'
def pad4(b): return b + b'\0' * (-len(b) % 4)
st = struct.pack('>I', 1) + pad4(b'\0') + struct.pack('>I', 1) + pad4(b'chosen\0')
st += struct.pack('>III', 3, 4, 0) + struct.pack('>I', start) + struct.pack('>III', 3, 4, 19) + struct.pack('>I', end)
st += struct.pack('>I', 2) + struct.pack('>I', 2) + struct.pack('>I', 9)
off_st = 40 + 16
total = off_st + len(st) + len(strs)
hdr = struct.pack('>10I', 0xd00dfeed, total, off_st, off_st + len(st), 40, 17, 16, 0, len(strs), len(st))
open(out, 'wb').write(hdr + b'\0' * 16 + st + strs)
