# PicoCalc LofiFren setup

Use this path for Raspberry Pi Pico 2 W when Wi-Fi, BLE, USB deployment, and an on-device menu matter.

Firmware source:

- `LofiFren/PicoCalc`
- recommended UF2: `MicroPython/firmware/picocalc_v127_pico2w.uf2`

Robot app:

- copy `robotarm.py` to SD path `/py_scripts/robotarm.py`
- copy `robotweb.py` to SD path `/py_scripts/robotweb.py`
- patch `/modules/py_run.py` so both `find_py_files` and `run_script` use `/sd/py_scripts`
- it appears in the LofiFren PicoCalc script menu as `robotarm`
- USB update helper: `tools/update_lofifren_app_usb.sh`

The app provides:

- preset poses
- manual EE/q1/q2/q3 control
- host, port, movement time, and step settings
- saved config at `/sd/robotarm.json`

Web AP app:

- open `robotweb` from the PicoCalc script menu
- connect Safari device to Wi-Fi `PICOCALC_ROBOT`
- password: `robot12345`
- open `http://192.168.4.1`
- controls the same GPIO H-bridge pins: EE GP2/GP3, Q1 GP4/GP5, Q2 GP21/GP28, Q3 GP8/GP9

Current tested device patch:

- `find_py_files(base_path="/sd/py_scripts")`
- `relative_path = full_path[len("/sd/py_scripts/"):-3]`
- `run_script(script_path, base_path="/sd/py_scripts")`
