_textbox = None
_pose_index = 0
_status = "Ready"

HOST = "192.168.4.1"
PORT = 7777

POSES = (
    ("Neutral", (90, 90, 90, 90)),
    ("Pick", (35, 82, 120, 55)),
    ("Lift", (35, 92, 82, 82)),
    ("Place", (115, 88, 108, 72)),
    ("Open", (25, 90, 90, 90)),
    ("Close", (70, 90, 90, 90)),
)


def _command(angles):
    return "<BUZZ,{},{},{},{},900,900,900,900>".format(
        angles[0], angles[1], angles[2], angles[3]
    )


def _send(angles):
    import socket

    cmd = _command(angles)
    addr = socket.getaddrinfo(HOST, PORT)[0][-1]
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
        return reply.decode("utf-8", "ignore")[:40]
    return "Sent"


def _draw():
    global _textbox
    name, angles = POSES[_pose_index]
    text = (
        "Robot Arm\n\n"
        "IP: {}\n"
        "Pose: {}\n"
        "EE {}  q1 {}\n"
        "q2 {}  q3 {}\n\n"
        "UP/DOWN: pose\n"
        "CENTER: send\n"
        "BACK: exit\n\n"
        "{}"
    ).format(HOST, name, angles[0], angles[1], angles[2], angles[3], _status)
    _textbox.set_text(text)


def start(view_manager):
    from picoware.gui.textbox import TextBox

    global _textbox, _pose_index, _status

    _pose_index = 0
    _status = "Ready"
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
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER, BUTTON_DOWN, BUTTON_UP

    global _pose_index, _status

    if not _textbox:
        return

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
    elif button == BUTTON_UP:
        inp.reset()
        _pose_index = (_pose_index - 1) % len(POSES)
        _status = "Ready"
        _draw()
    elif button == BUTTON_DOWN:
        inp.reset()
        _pose_index = (_pose_index + 1) % len(POSES)
        _status = "Ready"
        _draw()
    elif button == BUTTON_CENTER:
        inp.reset()
        try:
            _status = _send(POSES[_pose_index][1])
        except Exception as exc:
            _status = "Error: {}".format(exc)[:40]
        _draw()


def stop(view_manager):
    from gc import collect

    global _textbox
    if _textbox:
        del _textbox
        _textbox = None
    collect()
