_textbox = None
_screen = 0
_cursor = 0
_status = "Ready"

CONFIG_FILE = "/sd/picoware/robotarm.cfg"

_cfg = {
    "host": "192.168.4.1",
    "port": 7777,
    "move_ms": 900,
    "step": 5,
}

_poses = [
    ["Neutral", [90, 90, 90, 90]],
    ["Pick", [35, 82, 120, 55]],
    ["Lift", [35, 92, 82, 82]],
    ["Place", [115, 88, 108, 72]],
    ["Open", [25, 90, 90, 90]],
    ["Close", [70, 90, 90, 90]],
]

_pose_index = 0
_manual = [90, 90, 90, 90]
_joint = 0


def _clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def _read_config():
    global _status
    try:
        with open(CONFIG_FILE, "r") as f:
            for line in f:
                if "=" not in line:
                    continue
                key, value = line.strip().split("=", 1)
                if key == "host":
                    _cfg["host"] = value
                elif key in ("port", "move_ms", "step"):
                    _cfg[key] = int(value)
        _status = "Config loaded"
    except Exception:
        _status = "Default config"


def _save_config():
    global _status
    try:
        with open(CONFIG_FILE, "w") as f:
            f.write("host={}\n".format(_cfg["host"]))
            f.write("port={}\n".format(_cfg["port"]))
            f.write("move_ms={}\n".format(_cfg["move_ms"]))
            f.write("step={}\n".format(_cfg["step"]))
        _status = "Saved"
    except Exception as exc:
        _status = "Save err {}".format(exc)[:28]


def _command(angles):
    t = _cfg["move_ms"]
    return "<BUZZ,{},{},{},{},{},{},{},{}>".format(
        angles[0], angles[1], angles[2], angles[3], t, t, t, t
    )


def _send(angles):
    import socket

    cmd = _command(angles)
    addr = socket.getaddrinfo(_cfg["host"], _cfg["port"])[0][-1]
    sock = socket.socket()
    sock.settimeout(3)
    try:
        sock.connect(addr)
        sock.send(cmd.encode())
        sock.send(b"\n")
        try:
            reply = sock.recv(96)
        except OSError:
            reply = b""
    finally:
        sock.close()
    if reply:
        return reply.decode("utf-8", "ignore")[:30]
    return "Sent"


def _line(label, selected=False):
    return ("> " if selected else "  ") + label


def _draw_home():
    name, angles = _poses[_pose_index]
    text = [
        "Robot Arm",
        "",
        _line("Pose: {}".format(name), _cursor == 0),
        "  EE {} q1 {} q2 {} q3 {}".format(angles[0], angles[1], angles[2], angles[3]),
        _line("Manual mode", _cursor == 1),
        _line("Settings", _cursor == 2),
        _line("Save config", _cursor == 3),
        "",
        "UP/DOWN move  CENTER select",
        "LEFT/BACK exit",
        _status,
    ]
    _textbox.set_text("\n".join(text))


def _draw_manual():
    labels = ("EE", "q1", "q2", "q3")
    text = ["Manual", ""]
    for i in range(4):
        text.append(_line("{}: {}".format(labels[i], _manual[i]), _joint == i))
    text += [
        "",
        "UP/DOWN adjust {}".format(_cfg["step"]),
        "LEFT/RIGHT joint",
        "CENTER send  BACK home",
        _status,
    ]
    _textbox.set_text("\n".join(text))


def _draw_settings():
    rows = (
        "Host {}".format(_cfg["host"]),
        "Port {}".format(_cfg["port"]),
        "Move ms {}".format(_cfg["move_ms"]),
        "Step {}".format(_cfg["step"]),
    )
    text = ["Settings", ""]
    for i, row in enumerate(rows):
        text.append(_line(row, _cursor == i))
    text += [
        "",
        "UP/DOWN value",
        "LEFT/RIGHT field",
        "CENTER save  BACK home",
        _status,
    ]
    _textbox.set_text("\n".join(text))


def _draw():
    if _screen == 0:
        _draw_home()
    elif _screen == 1:
        _draw_manual()
    else:
        _draw_settings()


def _edit_setting(delta):
    key = ("host", "port", "move_ms", "step")[_cursor]
    if key == "host":
        hosts = ("192.168.4.1", "192.168.1.100", "10.0.0.1", "robot.local")
        idx = 0
        try:
            idx = hosts.index(_cfg["host"])
        except ValueError:
            pass
        _cfg["host"] = hosts[(idx + delta) % len(hosts)]
    elif key == "port":
        _cfg["port"] = _clamp(_cfg["port"] + delta, 1, 65535)
    elif key == "move_ms":
        _cfg["move_ms"] = _clamp(_cfg["move_ms"] + (delta * 100), 100, 5000)
    elif key == "step":
        _cfg["step"] = _clamp(_cfg["step"] + delta, 1, 30)


def start(view_manager):
    from picoware.gui.textbox import TextBox

    global _textbox, _screen, _cursor, _status
    _screen = 0
    _cursor = 0
    _status = "Ready"
    _read_config()
    _textbox = TextBox(
        view_manager.draw,
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
    )
    _draw()
    return True


def run(view_manager):
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_CENTER,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_UP,
    )

    global _screen, _cursor, _pose_index, _joint, _status

    if not _textbox:
        return

    inp = view_manager.input_manager
    button = inp.button

    if button is None:
        return

    inp.reset()

    if _screen == 0:
        if button == BUTTON_BACK or button == BUTTON_LEFT:
            view_manager.back()
            return
        if button == BUTTON_UP:
            _cursor = (_cursor - 1) % 4
        elif button == BUTTON_DOWN:
            _cursor = (_cursor + 1) % 4
        elif button == BUTTON_RIGHT and _cursor == 0:
            _pose_index = (_pose_index + 1) % len(_poses)
        elif button == BUTTON_LEFT and _cursor == 0:
            _pose_index = (_pose_index - 1) % len(_poses)
        elif button == BUTTON_CENTER:
            if _cursor == 0:
                try:
                    _status = _send(_poses[_pose_index][1])
                except Exception as exc:
                    _status = "Err {}".format(exc)[:30]
            elif _cursor == 1:
                _screen = 1
                _status = "Manual"
            elif _cursor == 2:
                _screen = 2
                _cursor = 0
                _status = "Settings"
            elif _cursor == 3:
                _save_config()
    elif _screen == 1:
        if button == BUTTON_BACK:
            _screen = 0
            _cursor = 1
        elif button == BUTTON_LEFT:
            _joint = (_joint - 1) % 4
        elif button == BUTTON_RIGHT:
            _joint = (_joint + 1) % 4
        elif button == BUTTON_UP:
            _manual[_joint] = _clamp(_manual[_joint] + _cfg["step"], 0, 180)
        elif button == BUTTON_DOWN:
            _manual[_joint] = _clamp(_manual[_joint] - _cfg["step"], 0, 180)
        elif button == BUTTON_CENTER:
            try:
                _status = _send(_manual)
            except Exception as exc:
                _status = "Err {}".format(exc)[:30]
    else:
        if button == BUTTON_BACK:
            _screen = 0
            _cursor = 2
        elif button == BUTTON_LEFT:
            _cursor = (_cursor - 1) % 4
        elif button == BUTTON_RIGHT:
            _cursor = (_cursor + 1) % 4
        elif button == BUTTON_UP:
            _edit_setting(1)
        elif button == BUTTON_DOWN:
            _edit_setting(-1)
        elif button == BUTTON_CENTER:
            _save_config()

    _draw()


def stop(view_manager):
    from gc import collect

    global _textbox
    if _textbox:
        del _textbox
        _textbox = None
    collect()
