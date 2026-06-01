# Picoware setup

## Volume check

Do not flash a volume named `NO NAME`. In the local check on May 31, 2026, `/Volumes/NO NAME` was a 31.7 GB FAT32 SD card, not a Pico bootloader volume. It did not contain `INFO_UF2.TXT`, `INDEX.HTM`, or `CURRENT.UF2`.

Expected Pico bootloader volumes:

- `RPI-RP2` for Pico/Pico W.
- `RP2350` for Pico 2/Pico 2 W.

## Flash latest Picoware safely

Put the PicoCalc board in BOOTSEL mode first, then run one of:

```sh
./tools/flash_latest_picoware.sh Picoware-PicoCalcPico.uf2
./tools/flash_latest_picoware.sh Picoware-PicoCalcPicoW.uf2
./tools/flash_latest_picoware.sh Picoware-PicoCalcPico2.uf2
./tools/flash_latest_picoware.sh Picoware-PicoCalcPico2W.uf2
```

The script downloads the latest release from `jblanked/Picoware` and refuses to flash unless the target has Pico UF2 bootloader marker files.

Latest checked upstream during setup: Picoware `v1.8.4`, published May 30, 2026.

## Flash from SD without microUSB

The PicoCalc SD can also hold UF2 firmware files under:

```text
/firmware/UF2/
```

If the PicoCalc already has the Clockwork Pi/PicoCalc UF2 bootloader installed, use the on-device firmware menu to select one of these files from the SD. This is the method shown in JBlanked's video "No PC Needed: Flash Your PicoCalc with UF2 Files from SD Card!".

For the local SD card named `NO NAME`, the following files were copied:

```text
/firmware/UF2/Picoware-PicoCalcPico.uf2
/firmware/UF2/Picoware-PicoCalcPicoW.uf2
/firmware/UF2/Picoware-PicoCalcPico2.uf2
/firmware/UF2/Picoware-PicoCalcPico2W.uf2
/picoware/apps/robotarm.py
```

The official Picoware MicroPython `apps` folder from `v1.8.4` was also copied to:

```text
/picoware/apps/
```

Use the UF2 that matches the board installed in the PicoCalc:

- Pico without Wi-Fi: `Picoware-PicoCalcPico.uf2`
- Pico W: `Picoware-PicoCalcPicoW.uf2`
- Pico 2: `Picoware-PicoCalcPico2.uf2`
- Pico 2 W: `Picoware-PicoCalcPico2W.uf2`

Do not select a Pico 2/Pico 2 W UF2 on an original Pico/Pico W, or the reverse.

## Update app without removing the SD

Preferred options:

1. Copy `robotarm.py` or `robotarm.mpy` into `/picoware/apps`.
2. From the computer, connect PicoCalc by USB and run:

   ```sh
   ./tools/update_picoware_app_usb.sh
   ```

If Picoware does not expose `/picoware/apps` through MicroPython USB, then host-side USB copying to SD is not available in that firmware mode. Use the in-app Wi-Fi updater or mount the SD only for the initial install.
