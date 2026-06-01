# PicoCalc LofiFren setup

Use this path for Raspberry Pi Pico 2 W when Wi-Fi, BLE, USB deployment, and an on-device menu matter.

Firmware source:

- `LofiFren/PicoCalc`
- recommended UF2: `MicroPython/firmware/picocalc_v127_pico2w.uf2`

Robot app:

- copy `robotarm.py` to SD path `/py_scripts/robotarm.py`
- it appears in the LofiFren PicoCalc script menu as `py_scripts/robotarm`

The app provides:

- preset poses
- manual EE/q1/q2/q3 control
- host, port, movement time, and step settings
- saved config at `/sd/robotarm.json`
