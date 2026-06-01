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

## Update app without removing the SD

Preferred options:

1. From PicoCalc app menu, press `u` to download the latest `robot_arm_remote.py` from this repository over Wi-Fi.
2. From the computer, connect PicoCalc by USB and run:

   ```sh
   ./tools/update_picoware_app_usb.sh
   ```

If Picoware does not expose `/picoware/apps` through MicroPython USB, then host-side USB copying to SD is not available in that firmware mode. Use the in-app Wi-Fi updater or mount the SD only for the initial install.
