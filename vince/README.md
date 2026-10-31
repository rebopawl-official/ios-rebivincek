# vince: XNU на Redmi 5 Plus (M3b)

Тут завантажувач, який запускає XNU на vince, пакувальник образу і три патчі XNU для цього телефона.
Нічого не прошивається: усе йде через `fastboot boot`.

## Крок A. Перевірка завантажувача без XNU (1 хвилина)

Образ `vince-m3b-loadertest.img` (лежить окремо від zip) запускає замість XNU «несправжнє ядро», яке перевіряє
все, що завантажувач обіцяє XNU: копіювання сегментів, обнулення, `boot_args`, Apple Device Tree, командний рядок.

    fastboot boot vince-m3b-loadertest.img

На екрані має бути `FAKE XNU reached (loader test)` і внизу зеленим `LOADER TEST PASSED`.
Якщо є червоні рядки `!!`, сфотографуй екран.

## Крок B. Справжнє ядро

1. Розпакуй zip у корінь форка і запуш (гілка `vince`):

        cd ios-rebivincek && unzip -o ../vince-m3b.zip && git add -A && git commit -m "vince: M3b" && git push

   Push запускає збірку сам (Actions, `xnu`, приблизно 8 хвилин з кешем, перший раз довше).
   Крок «Check that the vince patches were applied» зупинить збірку, якщо патч не ліг на код.
2. Коли збірка зелена, скачай артефакт `xnu-kernel`, у ньому `kernel.development.sweet`.
3. Склей образ (потрібен лише Python 3):

        python3 vince/tools/vince_pack.py kernel.development.sweet vince-xnu.img

4. `fastboot boot vince-xnu.img` і сфотографуй екран.

Якщо збірка червона: відкрий запуск, крок `Build`, скопіюй рядки з `error:` і надішли мені.

## Що буде на екрані

- Спершу текст завантажувача (зелений `JUMP ...`). Це означає, що ядро скопійоване і йому передали керування.
- Далі XNU стирає екран і друкує свій журнал (`SWEET EARLY n: ...`, потім ядерні повідомлення).
- Якщо після `JUMP` лишився текст завантажувача і внизу зліва білий прямокутник, XNU стартував, але зупинився дуже рано.
  Якщо білого прямокутника немає, зупинка ще до першої інструкції ядра.

## Склад

- `shim/`: завантажувач (`loader.c`), збірка `build.sh`, тест на ПК `host_test_loader.c`.
- `fakexnu/`: несправжнє ядро для кроку A.
- `tools/mkadt_vince.py`: Device Tree для vince. `tools/vince_pack.py`: склеює ядро з Actions у образ.
  `tools/test_pack.py`: перевірка пакувальника на синтетичному ядрі.
- `prebuilt/`: зібраний `loader.Image`, `stock-appended.dtb`, `fakexnu.macho`.
- `../xnu/patches/0960..0962`: прапор `VINCE`, GICv2 із завантажувальним ядром 0, 24-бітна консоль.
- `../.github/workflows/xnu.yml`: збірка з `TOPAZ_4K=1` і `VINCE=1`.

Командний рядок ядра за замовчуванням `debug=0xc serial=3 cpus=1 keepsyms=1`; змінити можна прапором `--cmdline`.
