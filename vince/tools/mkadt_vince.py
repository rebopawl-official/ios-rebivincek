#!/usr/bin/env python3
"""Apple Device Tree for the Redmi 5 Plus (vince, MSM8953) that the SWEET xnu boots with.

Same contract as tools/mkadt.py (topaz) but for this phone: eight Cortex-A53 (MPIDR 0-3 and
0x100-0x103, boot CPU 0), a GICv2, the LK splash buffer as 24 bpp framebuffer console, and
none of the topaz hardware nodes (display, wlan, UFS) whose drivers would poke addresses that
do not exist here. Every address comes from this phone's live device tree and the measurements
in vince-facts.md.

  mkadt_vince.py OUT.adt [--dump]
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))	# tools/adt.py and tools/mkadt.py of the fork
sys.path.insert(0, os.path.join(HERE, '..', 'tools-fork'))
import adt  # noqa: E402
from mkadt import node, u32, u64, cstr, d22ap_product, BOOT_MANIFEST_HASH  # noqa: E402

# Kernel-managed RAM. One contiguous range that is plain RAM on this phone (measured in M2:
# 0x10000000-0x849fffff is cacheable RAM) and below 0x80000000, because the early framebuffer
# mapping of start.s takes L1 slot 2 (0x80000000-0xbfffffff). LK puts the loader at 0x10080000
# and the payload ramdisk at 0x13600000, both below this range.
PHYS_BASE = 0x20000000
MEM_SIZE = 0x60000000	# 1.5 GiB: 0x20000000 - 0x7fffffff
# /arm-io children are relative to this; it must not be 0 (serial_init bails)
SOC_BASE = 0x01000000
# GICv2 (qcom,msm-qgic2): distributor and CPU interface, one 4 KiB page each (device tree: reg
# <0x0b000000 0x1000>, <0x0b002000 0x1000>)
GICD, GICD_SIZE = 0x0b000000, 0x1000
GICC, GICC_SIZE = 0x0b002000, 0x1000
TIMEBASE = 19200000
VTIMER_INTID = 20	# Qualcomm PPI numbering on this SoC: virtual timer INTID 20 (measured in M2)
# Splash buffer LK leaves lit: 1080x2160, packed 24 bpp (bytes B,G,R), stride 3240
FB, FB_SIZE = 0x90001000, 0x6ad000
FB_W, FB_H, FB_STRIDE = 1080, 2160, 3240
SWEET_ECID = 0x56494e4345000001  # 'VINCE' + 1, synthetic


def build(seed=None):
    seed = seed if seed is not None else os.urandom(64)
    phandle = iter(range(1, 1000))
    ph = lambda: ('AAPL,phandle', u32(next(phandle)))

    chosen = node('chosen', [
        ph(),
        ('dram-base', u64(PHYS_BASE)),
        ('dram-size', u64(MEM_SIZE)),
        ('random-seed', seed),
        ('debug-enabled', u32(1)),
        ('firmware-version', cstr('vince-loader')),
        ('system-firmware-version', cstr('vince-loader')),
        ('boot-manifest-hash', BOOT_MANIFEST_HASH),
        ('crypto-hash-method', cstr('sha2-384')),
        ('display-scale', u32(3)),
        ('unique-chip-id', struct.pack('<Q', SWEET_ECID)),
        ('chip-id', u32(0x8015)),
        ('certificate-production-status', u32(0)),
        ('effective-production-status-ap', u32(0)),
        ('certificate-security-mode', u32(1)),
        ('effective-security-mode-sep', u32(1)),
    ], [node('memory-map', [ph()]),
        node('asmb', [ph(), ('lp-sip0', u64(0x6f)), ('lp-sip1', u32(1))])])

    # Eight Cortex-A53: cluster 0 = MPIDR 0x0-0x3, cluster 1 = 0x100-0x103. One homogeneous
    # SMP cluster for the scheduler (cluster-type 0). Only cpu0 is "running"; the kernel
    # boot-arg cpus=N selects how many are used (N=1 for the first boots).
    cpu_nodes = []
    for core in range(8):
        mpidr = (0x100 if core >= 4 else 0) | (core & 3)
        cpu_nodes.append(node(f'cpu{core}', [
            ph(),
            ('device_type', cstr('cpu')),
            # names the built-in IOKit personality matches (KernelConfigTables.cpp)
            ('compatible', cstr('qcom,kryo260') + cstr('qcom,kryo470') + cstr('ARM,v8')),
            ('reg', u32(mpidr)),		# MPIDR Aff1:Aff0, not the logical ID
            ('cpu-id', u32(core)),
            ('cluster-id', u32(0)),
            ('cluster-type', u32(0)),	# CLUSTER_TYPE_SMP
            ('die-cluster-id', u32(0)),
            ('cluster-core-id', u32(core)),
            ('l2-cache-id', u32(core >> 2)),	# one 512 KiB L2 per cluster (measured)
            ('l2-cache-size', u32(0x80000)),
            ('l3-cache-id', u32(0)),
            ('state', cstr('running' if core == 0 else 'stopped')),
            ('timebase-frequency', u32(TIMEBASE)),
            ('clock-frequency', u32(2016000000)),
            ('bus-frequency', u32(100000000)),
            ('memory-frequency', u32(933000000)),
            ('peripheral-frequency', u32(TIMEBASE)),
            ('fixed-frequency', u32(TIMEBASE)),
        ]))
    cpus = node('cpus', [ph(), ('#address-cells', u32(1)), ('#size-cells', u32(0))], cpu_nodes)

    gic = node('gic', [
        ph(),
        ('compatible', cstr('arm,gic-v2') + cstr('qcom,msm-qgic2')),
        ('interrupt-controller', b''),
        ('virtual-timer-intid', u32(VTIMER_INTID)),
        # <gicd base, gicd size, gicc base, gicc size> relative to SOC_BASE (pe_fiq.c, VINCE branch)
        ('reg', u64(GICD - SOC_BASE, GICD_SIZE, GICC - SOC_BASE, GICC_SIZE)),
    ])
    arm_io = node('arm-io', [
        ph(),
        ('device_type', cstr('sweet-io')),
        ('compatible', cstr('sweet-io') + cstr('arm-io')),
        ('#address-cells', u32(2)),
        ('#size-cells', u32(2)),
        ('ranges', u64(0, SOC_BASE, 0x100000000 - SOC_BASE)),
    ], [gic,
        # No hardware: watchdogd checks IODeviceTree:/arm-io/wdt for no-pmu.
        node('wdt', [ph(), ('no-pmu', u32(1))])])
    # Deliberately absent: disp0 (SweetFramebuffer drives topaz's MDP), wlan, sweet-ufs.

    fbcon = node('sweet-fbcon', [
        ph(),
        ('reg', u64(FB, FB_SIZE)),
        ('width', u32(FB_W)),
        ('height', u32(FB_H)),
        ('stride', u32(FB_STRIDE)),
    ])

    defaults = node('defaults', [ph(), ('no-effaceable-storage', u32(1))])
    buttons = node('buttons', [
        ph(),
        ('button-names', cstr('volup') + cstr('voldown') + cstr('hold')),
        ('home-button-type', u32(2)),
        ('opposed-power-vol-buttons', u32(1)),
    ])

    product_props = d22ap_product()
    if product_props:
        product_props = [(k, cstr('sRGB') if k == 'artwork-display-gamut' else v) for k, v in product_props]
    product = [node('product', [ph()] + product_props)] if product_props else []

    return node('device-tree', [
        ph(),
        ('compatible', cstr('D22AP') + cstr('iPhone10,3') + cstr('xiaomi,vince') + cstr('xiaomi,sweet') +
         cstr('qcom,msm8953') + cstr('AppleARM')),
        ('model', cstr('iPhone10,3')),
        ('target-type', cstr('D22')),
        ('target-sub-type', cstr('D22AP')),
        ('manufacturer', cstr('Apple Inc.')),
        ('#address-cells', u32(2)),
        ('#size-cells', u32(2)),
    ], [chosen, defaults, cpus, arm_io, fbcon, buttons] + product)


if __name__ == '__main__':
    root = build()
    blob = adt.serialize(root)
    open(sys.argv[1], 'wb').write(blob)
    if '--dump' in sys.argv:
        adt.dump(adt.parse(blob)[0])
    print(f'{sys.argv[1]}: {len(blob)} bytes', file=sys.stderr)
