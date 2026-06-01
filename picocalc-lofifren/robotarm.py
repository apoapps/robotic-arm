import gc
import json
import socket
import time

import picocalc

E = "\033"
W = 53
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
CONFIG_PATH = "/sd/robotarm.json"

config = {
    "host": "192.168.4.1",
    "port": 7777,
    "move_ms": 900,
    "step": 5,
    "live": True,
}

poses = [
    ["Neutral", [90, 90, 90, 90]],
    ["Pick", [35, 82, 120, 55]],
    ["Lift", [35, 92, 82, 82]],
    ["Place", [115, 88, 108, 72]],
    ["Open", [25, 90, 90, 90]],
    ["Close", [70, 90, 90, 90]],
]

screen = 0
cursor = 0
pose_index = 0
joint = 0
manual = [90, 90, 90, 90]
status = "Ready"
key_buf = bytearray(16)
labels = ("EE", "Q1", "Q2", "Q3")
axis_names = ("End effector", "Base", "Shoulder", "Elbow")


def wr(text):
    picocalc.terminal.wr(text)


def clear():
    wr("{}[2J{}[H{}[?25l".format(E, E, E))


def at(row, col):
    wr("{}[{};{}H".format(E, row, col))


def style(fg=None, bg=None, bold=False, dim=False, rev=False):
    codes = []
    if bold:
        codes.append("1")
    if dim:
        codes.append("2")
    if rev:
        codes.append("7")
    if fg is not None:
        codes.append(str(30 + fg))
    if bg is not None:
        codes.append(str(40 + bg))
    if codes:
        wr("{}[{}m".format(E, ";".join(codes)))


def reset_style():
    wr("{}[0m".format(E))


def line(text, selected=False):
    if selected:
        style(fg=BLACK, bg=GREEN, bold=True)
        wr(" > {:<{}} ".format(text[: W - 6], W - 6))
        reset_style()
    else:
        wr("   {}".format(text[: W - 4]))
    wr("\n")


def pill(text, fg=WHITE, bg=BLUE):
    style(fg=fg, bg=bg, bold=True)
    wr(" {} ".format(text[:16]))
    reset_style()


def field(label, value, width=15):
    style(fg=CYAN, bold=True)
    wr("{:<8}".format(label))
    reset_style()
    wr("{:<{}}\n".format(str(value)[:width], width))


def bar(value, selected=False):
    width = 24
    filled = int((clamp(value, 0, 180) * width) / 180)
    if selected:
        style(fg=BLACK, bg=GREEN, bold=True)
    else:
        style(fg=GREEN)
    wr("[")
    wr("#" * filled)
    wr("-" * (width - filled))
    wr("]")
    reset_style()


def clamp(value, low, high):
    return min(max(value, low), high)


def load_config():
    global status
    try:
        with open(CONFIG_PATH, "r") as f:
            saved = json.load(f)
        for key in config:
            if key in saved:
                config[key] = saved[key]
        status = "Config loaded"
    except Exception:
        status = "Default config"


def save_config():
    global status
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f)
        status = "Config saved"
    except Exception as exc:
        status = "Save error {}".format(exc)[:34]


def command(angles):
    t = int(config["move_ms"])
    return "<BUZZ,{},{},{},{},{},{},{},{}>".format(
        int(angles[0]), int(angles[1]), int(angles[2]), int(angles[3]), t, t, t, t
    )


def send_pose(angles):
    cmd = command(angles)
    addr = socket.getaddrinfo(config["host"], int(config["port"]))[0][-1]
    s = socket.socket()
    s.settimeout(3)
    try:
        s.connect(addr)
        s.send(cmd.encode())
        s.send(b"\n")
        try:
            reply = s.recv(96)
        except OSError:
            reply = b""
    finally:
        s.close()
    if reply:
        return reply.decode("utf-8", "ignore")[:32]
    return "Sent {}".format(cmd[:20])


def draw_header(title):
    clear()
    style(fg=WHITE, bg=BLUE, bold=True)
    wr(" " * W)
    at(1, 3)
    wr(title)
    at(1, W - 15)
    wr("Yamel Robot")
    reset_style()
    at(2, 1)
    style(fg=CYAN)
    wr("-" * W)
    reset_style()
    at(4, 1)


def draw_home():
    name, angles = poses[pose_index]
    draw_header("Robot Arm Control")
    pill("PRESET", BLACK, GREEN if cursor == 0 else BLUE)
    wr("  {} ({}/{})\n".format(name, pose_index + 1, len(poses)))
    wr("   ")
    for idx, label in enumerate(labels):
        wr("{}:{}  ".format(label, angles[idx]))
    wr("\n\n")
    line("Manual axis control", cursor == 1)
    line("Connection/settings", cursor == 2)
    line("Save config", cursor == 3)
    wr("\n")
    field("Target", "{}:{}".format(config["host"], config["port"]), 30)
    field("Move", "{} ms   step {}".format(config["move_ms"], config["step"]), 30)
    style(dim=True)
    wr("< > preset   Enter send/open   M manual   S save\n")
    wr("Esc exits to menu\n")
    reset_style()
    wr(status)


def draw_manual():
    draw_header("Manual Axis Control")
    style(dim=True)
    wr("Axis: ")
    reset_style()
    pill("{} {}".format(labels[joint], axis_names[joint]), BLACK, GREEN)
    wr("  ")
    pill("LIVE {}".format("ON" if config.get("live", True) else "OFF"), BLACK, YELLOW)
    wr("\n\n")
    for idx, label in enumerate(labels):
        if joint == idx:
            style(fg=GREEN, bold=True)
            wr(">")
        else:
            wr(" ")
        reset_style()
        wr(" {} {:>3} ".format(label, manual[idx]))
        bar(manual[idx], joint == idx)
        wr("  {}\n".format(axis_names[idx]))
    wr("\n")
    style(dim=True)
    wr("1-4 axis  Up/Down axis  Left/Right angle +/-{}\n".format(config["step"]))
    wr("+/- angle  S/Enter send  L live  H neutral  Esc home\n")
    reset_style()
    wr(status)


def draw_settings():
    draw_header("Settings")
    rows = [
        "Host {}".format(config["host"]),
        "Port {}".format(config["port"]),
        "Move ms {}".format(config["move_ms"]),
        "Step {}".format(config["step"]),
        "Live {}".format("on" if config.get("live", True) else "off"),
    ]
    for idx, row in enumerate(rows):
        line(row, cursor == idx)
    wr("\n")
    style(dim=True)
    wr("Left/Right field  Up/Down value  Enter save\nEsc home\n")
    reset_style()
    wr(status)


def draw():
    if screen == 0:
        draw_home()
    elif screen == 1:
        draw_manual()
    else:
        draw_settings()


def read_key():
    n = picocalc.terminal.readinto(key_buf)
    if not n:
        return None
    data = bytes(key_buf[:n])
    if data in (b"\x1b", b"q", b"Q"):
        return "esc"
    if data in (b"\r", b"\n"):
        return "enter"
    if data.endswith(b"[A"):
        return "up"
    if data.endswith(b"[B"):
        return "down"
    if data.endswith(b"[C"):
        return "right"
    if data.endswith(b"[D"):
        return "left"
    if data in (b"+", b"="):
        return "plus"
    if data in (b"-", b"_"):
        return "minus"
    if data in (b"s", b"S"):
        return "send"
    if data in (b"m", b"M"):
        return "manual"
    if data in (b"l", b"L"):
        return "live"
    if data in (b"h", b"H"):
        return "home"
    if data in (b"1", b"2", b"3", b"4"):
        return data.decode()
    return None


def edit_setting(delta):
    hosts = ("192.168.4.1", "192.168.1.100", "10.0.0.1", "robot.local")
    if cursor == 0:
        try:
            idx = hosts.index(config["host"])
        except ValueError:
            idx = 0
        config["host"] = hosts[(idx + delta) % len(hosts)]
    elif cursor == 1:
        config["port"] = clamp(int(config["port"]) + delta, 1, 65535)
    elif cursor == 2:
        config["move_ms"] = clamp(int(config["move_ms"]) + delta * 100, 100, 5000)
    elif cursor == 3:
        config["step"] = clamp(int(config["step"]) + delta, 1, 30)
    else:
        config["live"] = not config.get("live", True)


def send_current():
    global status
    try:
        status = send_pose(manual)
    except Exception as exc:
        status = "Send error {}".format(exc)[:34]


def adjust_manual(delta):
    manual[joint] = clamp(manual[joint] + (delta * int(config["step"])), 0, 180)
    if config.get("live", True):
        send_current()
    else:
        global status
        status = "{} -> {}".format(labels[joint], manual[joint])


def loop():
    global screen, cursor, pose_index, joint, status
    load_config()
    draw()
    while True:
        key = read_key()
        if key is None:
            time.sleep_ms(25)
            continue

        if screen == 0:
            if key == "esc":
                clear()
                return
            if key == "up":
                cursor = (cursor - 1) % 4
            elif key == "down":
                cursor = (cursor + 1) % 4
            elif key == "left" and cursor == 0:
                pose_index = (pose_index - 1) % len(poses)
            elif key == "right" and cursor == 0:
                pose_index = (pose_index + 1) % len(poses)
            elif key == "enter":
                if cursor == 0:
                    try:
                        status = send_pose(poses[pose_index][1])
                    except Exception as exc:
                        status = "Send error {}".format(exc)[:34]
                elif cursor == 1:
                    screen = 1
                    status = "Manual"
                elif cursor == 2:
                    screen = 2
                    cursor = 0
                    status = "Settings"
                else:
                    save_config()
            elif key == "manual":
                screen = 1
                status = "Manual"
            elif key == "send":
                save_config()
        elif screen == 1:
            if key == "esc":
                screen = 0
                cursor = 1
            elif key == "left":
                adjust_manual(-1)
            elif key == "right":
                adjust_manual(1)
            elif key == "up":
                joint = (joint - 1) % 4
            elif key == "down":
                joint = (joint + 1) % 4
            elif key == "plus":
                adjust_manual(1)
            elif key == "minus":
                adjust_manual(-1)
            elif key in ("1", "2", "3", "4"):
                joint = int(key) - 1
                status = "Axis {}".format(labels[joint])
            elif key == "home":
                manual[:] = [90, 90, 90, 90]
                send_current()
            elif key == "live":
                config["live"] = not config.get("live", True)
                status = "Live {}".format("on" if config["live"] else "off")
            elif key in ("enter", "send"):
                send_current()
        else:
            if key == "esc":
                screen = 0
                cursor = 2
            elif key == "left":
                cursor = (cursor - 1) % 5
            elif key == "right":
                cursor = (cursor + 1) % 5
            elif key == "up":
                edit_setting(1)
            elif key == "down":
                edit_setting(-1)
            elif key == "enter":
                save_config()
        draw()


def main_menu():
    try:
        loop()
    finally:
        gc.collect()


main_executed = False
