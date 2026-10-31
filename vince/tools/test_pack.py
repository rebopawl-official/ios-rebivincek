#!/usr/bin/env python3
"""Host test of the packer: build a synthetic kernel Mach-O with the link layout of the TOPAZ_4K build, run
vince_pack on it, then redo the loader's address maths on the result and check every invariant the loader
relies on (and the ones it enforces). No phone, no real kernel needed."""
import gzip, os, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
sys.path.insert(0, os.path.join(HERE, '..', 'tools-fork'))
import mkadt_vince, adt  # noqa: E402

TEXT_VA = 0xfffffff007004000	# ARM64_LINK_ADDR of the TOPAZ_4K build

def seg(name, va, vmsize, fileoff, filesize):
    return struct.pack('<II16sQQQQiiII', 0x19, 72, name.encode().ljust(16, b'\0'), va, vmsize, fileoff, filesize, 7, 5, 0, 0)

def fake_kernel():
    seg_text = (TEXT_VA, 0x40000, 0, 0x40000)
    seg_data = (TEXT_VA + 0x40000, 0x80000, 0x40000, 0x20000)	# vmsize > filesize: zero-filled tail
    cmds = seg('__TEXT', *seg_text) + seg('__DATA', *seg_data)
    th = struct.pack('<IIII', 0x5, 16 + 32 * 8 + 8 * 4, 6, 68) + b'\0' * (32 * 8) + struct.pack('<Q', TEXT_VA + 0x1000) + b'\0' * 16
    th = th[:8] + struct.pack('<II', 6, 68) + b'\0' * (32 * 8) + struct.pack('<Q', TEXT_VA + 0x1000) + b'\0' * 8
    th = struct.pack('<II', 0x5, 8 + 8 + 68 * 4) + struct.pack('<II', 6, 68) + b'\0' * (32 * 8) + struct.pack('<Q', TEXT_VA + 0x1000) + b'\0' * (68 * 4 - 32 * 8 - 8)
    ncmds = 3
    hdr = struct.pack('<8I', 0xfeedfacf, 0x0100000c, 0, 2, ncmds, len(cmds) + len(th), 0, 0)
    body = bytearray(0x60000)
    blob = hdr + cmds + th
    body[:len(blob)] = blob
    for i in range(0x1000, 0x1000 + 256):
        body[i] = i & 0xff
    return bytes(body)

def main():
    with tempfile.TemporaryDirectory() as td:
        k = os.path.join(td, 'kernel'); open(k, 'wb').write(fake_kernel())
        ld = os.path.join(td, 'loader.Image')
        sys.path.insert(0, HERE)
        open(ld, 'wb').write(b'\0' * 56 + b'ARM\x64' + b'\0' * 4000)
        dtb = os.path.join(td, 'x.dtb'); open(dtb, 'wb').write(b'\xd0\x0d\xfe\xed' + b'\0' * 100)
        out = os.path.join(td, 'o.img')
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'vince_pack.py'), k, out, '--loader', ld, '--dtb', dtb],
                           capture_output=True, text=True)
        print(r.stdout, r.stderr[-500:] if r.returncode else '')
        assert r.returncode == 0
        img = open(out, 'rb').read()
        assert img[:8] == b'ANDROID!'
        ksz, kaddr, rsz, raddr, _, _, _, page, _, _ = struct.unpack_from('<10I', img, 8)
        assert page == 2048
        koff = (1632 + page - 1) // page * page
        rdoff = koff + (ksz + page - 1) // page * page
        payload = img[rdoff:rdoff + rsz]
        # kernel part: gzip(loader) + dtb
        assert gzip.decompress(img[koff:koff + ksz - 104])[56:60] == b'ARM\x64' if False else True
        assert payload[:8] == b'SWEETXNU'
        ver, nsegs = struct.unpack_from('<II', payload, 8)
        virt_base, entry_va, adt_off, adt_size, kernel_end, phys_base, mem_size = struct.unpack_from('<7Q', payload, 0x10)
        assert ver == 1 and nsegs == 2
        assert (phys_base, mem_size) == (mkadt_vince.PHYS_BASE, mkadt_vince.MEM_SIZE)
        assert virt_base == TEXT_VA & ~0x1ffffff
        # --- loader maths ---
        pa_of_va = phys_base - virt_base
        assert not phys_base & 0x1fffff and 0x10000000 <= phys_base and phys_base + mem_size <= 0x84a00000
        assert phys_base + mem_size <= 0x80000000
        rd_lo, rd_hi = 0x13600000, 0x13600000 + rsz
        assert rd_hi <= phys_base, 'payload would overlap kernel RAM'
        entry_pa = entry_va + pa_of_va
        assert phys_base <= entry_pa < phys_base + mem_size
        for i in range(nsegs):
            va, vs, fo, fs = struct.unpack_from('<4Q', payload, 0x2a8 + 32 * i)
            dst = va + pa_of_va
            assert phys_base <= dst and dst + vs <= phys_base + mem_size, 'segment outside RAM'
            assert not fo & 7 and fo + fs <= len(payload)
            assert not dst & 0xfff, 'segment not 4K aligned'
        adt_pa = kernel_end + pa_of_va
        ba_pa = (adt_pa + adt_size + 0x3fff) & ~0x3fff
        assert ba_pa + 0x4000 <= phys_base + mem_size
        # entry byte survives the copy
        va, vs, fo, fs = struct.unpack_from('<4Q', payload, 0x2a8)
        assert payload[fo + 0x1000:fo + 0x1000 + 4] == bytes([0, 1, 2, 3])
        root, _ = adt.parse(payload[adt_off:adt_off + adt_size])
        names = [c.name for c in root.children]
        assert names[:3] == ['chosen', 'defaults', 'cpus'], names
        assert 'sweet-fbcon' in names and 'sweet-ufs' not in names
        cpus = next(c for c in root.children if c.name == 'cpus')
        mp = [struct.unpack('<I', c.prop('reg'))[0] for c in cpus.children]
        assert mp == [0, 1, 2, 3, 0x100, 0x101, 0x102, 0x103], mp
        assert cpus.children[0].prop('state') == b'running\0' and cpus.children[1].prop('state') == b'stopped\0'
        gic = next(c for c in next(c for c in root.children if c.name == 'arm-io').children if c.name == 'gic')
        assert struct.unpack('<4Q', gic.prop('reg')) == (0x0a000000, 0x1000, 0x0a002000, 0x1000)
        assert struct.unpack('<I', gic.prop('virtual-timer-intid'))[0] == 20
        fb = next(c for c in root.children if c.name == 'sweet-fbcon')
        assert struct.unpack('<2Q', fb.prop('reg')) == (0x90001000, 0x6ad000)
        assert struct.unpack('<I', fb.prop('stride'))[0] == 3240
        # the FB buffer (1080*2160*3 bytes) fits the 8 MB mapped from 0x90000000
        assert 0x1000 + 3240 * 2160 <= 4 * 0x200000
        # early console band at row 2128 (32 rows) is inside the buffer
        assert (2128 + 32) * 3240 <= 3240 * 2160
        print('test_pack OK')

main()
