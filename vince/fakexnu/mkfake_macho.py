#!/usr/bin/env python3
"""Wrap the flat fake-kernel blob in a Mach-O laid out like the TOPAZ_4K xnu: header page at the link address,
code from +0x1000, zero-filled tail (vmsize > filesize). usage: mkfake_macho.py blob out"""
import struct, sys
TEXT_VA = 0xfffffff007004000
blob = open(sys.argv[1], 'rb').read()
filesize = 0x1000 + len(blob)
vmsize = 0x10000
assert filesize <= vmsize - 0x1000
seg = struct.pack('<II16sQQQQiiII', 0x19, 72, b'__TEXT'.ljust(16, b'\0'), TEXT_VA, vmsize, 0, filesize, 7, 5, 0, 0)
state = struct.pack('<II', 6, 68) + b'\0' * (32 * 8) + struct.pack('<Q', TEXT_VA + 0x1000) + b'\0' * (68 * 4 - 32 * 8 - 8)
th = struct.pack('<II', 0x5, 8 + len(state)) + state
hdr = struct.pack('<8I', 0xfeedfacf, 0x0100000c, 0, 2, 2, len(seg) + len(th), 0, 0)
head = hdr + seg + th
assert len(head) <= 0x1000
open(sys.argv[2], 'wb').write(head.ljust(0x1000, b'\0') + blob)
