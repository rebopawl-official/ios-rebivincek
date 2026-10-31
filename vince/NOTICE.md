# Notice

The loader (`shim/`), the fake kernel (`fakexnu/`) and the packer (`tools/`) are written for the Redmi 5 Plus
(vince, MSM8953). Their structure follows the boot shim and the payload format of
[ios-sweet](https://github.com/dipa-studio/ios-sweet) and [ios-topaz](https://github.com/MakrSas/ios-topaz)
(both MIT): the arm64 Image-header trick, the position-independent link, the payload layout of
`tools/mkpayload.py` and the xnu hand-over contract of `shim/loader.c`.

`shim/font.h` comes from ios-topaz, which generated it from the kbd project's console font; check kbd's licence
terms before redistributing the source.

`prebuilt/stock-appended.dtb` is the device tree that Xiaomi's kernel for this phone carries (GPL, from the
stock boot image of the owner's own phone). It is appended to the loader so that LK accepts the image.

No Apple code is included here. The patches in `xnu/patches/` are changes to xnu (APSL) in the same form as
the other patches of this repository.
