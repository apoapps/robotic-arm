# PicoCalc LofiFren setup

Use this path for Raspberry Pi Pico 2 W when Wi-Fi, BLE, USB deployment, and an on-device menu matter.

Firmware source:

- `LofiFren/PicoCalc`
- recommended UF2: `MicroPython/firmware/picocalc_v127_pico2w.uf2`

Robot app:

- copy `robotarm.py` to SD path `/py_scripts/robotarm.py`
- patch `/modules/py_run.py` so both `find_py_files` and `run_script` use `/sd/py_scripts`
- it appears in the LofiFren PicoCalc script menu as `robotarm`
- USB update helper: `tools/update_lofifren_app_usb.sh`

The app provides:

- preset poses
- manual EE/q1/q2/q3 control
- host, port, movement time, and step settings
- saved config at `/sd/robotarm.json`

Current tested device patch:

- `find_py_files(base_path="/sd/py_scripts")`
- `relative_path = full_path[len("/sd/py_scripts/"):-3]`
- `run_script(script_path, base_path="/sd/py_scripts")`
