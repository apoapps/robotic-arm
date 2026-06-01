import gc
import json
import socket
import time
from machine import Pin

import network
import picocalc

E = "\033"
W = 53
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
CONFIG_PATH = "/sd/robotarm.json"
AP_SSID = "PICOCALC_ROBOT"
AP_PASSWORD = "robot12345"

config = {
    "move_ms": 250,
    "step": 5,
}

gpio_pairs = (
    (2, 3),    # EE: GP2 / GP3
    (4, 5),    # Q1: GP4 / GP5
    (21, 28),  # Q2: GP21 / GP28
    (8, 9),    # Q3: UART1_TX / UART1_RX as GPIO
)
gpio_pins = None

screen = 0
cursor = 0
joint = 0
manual = [90, 90, 90, 90]
status = "Ready"
key_buf = bytearray(16)
labels = ("EE", "Q1", "Q2", "Q3")
axis_names = ("Grip", "Base", "Shoulder", "Elbow")
menu_items = ("Manual", "Web", "Pins", "Save")


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


def fit(text, width):
    text = str(text)[:width]
    return text + (" " * (width - len(text)))


def line(text, selected=False):
    if selected:
        style(fg=BLACK, bg=WHITE, bold=True)
        wr(" {:<{}} ".format(("> " + text)[: W - 4], W - 4))
        reset_style()
    else:
        wr("   {}".format(text[: W - 4]))
    wr("\n")


def nav_hint(text):
    style(dim=True)
    wr(text[:W])
    wr("\n")
    reset_style()


def pill(text, fg=WHITE, bg=BLACK):
    style(fg=fg, bg=bg, bold=True)
    wr(" {} ".format(text[:16]))
    reset_style()


def field(label, value, width=15):
    style(fg=WHITE, bold=True)
    wr("{:<8}".format(label))
    reset_style()
    wr("{:<{}}\n".format(str(value)[:width], width))


def bar(value, selected=False):
    width = 22
    filled = int((clamp(value, 0, 180) * width) / 180)
    if selected:
        style(fg=BLACK, bg=WHITE, bold=True)
    else:
        style(fg=WHITE)
    wr("[")
    wr("=" * filled)
    wr(" " * (width - filled))
    wr("]")
    reset_style()


def clamp(value, low, high):
    return min(max(value, low), high)


def load_config():
    global status, manual, joint
    try:
        with open(CONFIG_PATH, "r") as f:
            saved = json.load(f)
        for key in config:
            if key in saved:
                config[key] = saved[key]
        if "manual" in saved and len(saved["manual"]) >= 4:
            manual[:] = [clamp(int(v), 0, 180) for v in saved["manual"][:4]]
        if "selectedAxis" in saved:
            joint = clamp(int(saved["selectedAxis"]), 0, 3)
        status = "Config loaded"
    except Exception:
        status = "Default config"


def init_gpio():
    global gpio_pins
    if gpio_pins is not None:
        return
    gpio_pins = []
    for a, b in gpio_pairs:
        p1 = Pin(a, Pin.OUT, value=0)
        p2 = Pin(b, Pin.OUT, value=0)
        gpio_pins.append((p1, p2))


def stop_gpio():
    init_gpio()
    for p1, p2 in gpio_pins:
        p1.value(0)
        p2.value(0)


def pulse_axis(axis, direction):
    init_gpio()
    p1, p2 = gpio_pins[axis]
    if direction > 0:
        p1.value(1)
        p2.value(0)
    else:
        p1.value(0)
        p2.value(1)
    time.sleep_ms(int(config["move_ms"]))
    p1.value(0)
    p2.value(0)


def save_config():
    global status
    try:
        payload = dict(config)
        payload["manual"] = manual[:]
        payload["selectedAxis"] = joint
        with open(CONFIG_PATH, "w") as f:
            json.dump(payload, f)
        status = "Config saved"
    except Exception as exc:
        status = "Save error {}".format(exc)[:34]


def draw_header(title):
    clear()
    style(fg=WHITE, bold=True)
    wr("+" + "-" * (W - 2) + "+")
    at(2, 1)
    wr(fit("| Proyecto final Robotica", W - 1) + "|")
    at(3, 1)
    wr(fit("| Apodaca, Calderon, Soriano, Ochoa", W - 1) + "|")
    at(4, 1)
    wr("+" + "-" * (W - 2) + "+")
    reset_style()
    at(6, 1)
    style(fg=WHITE, bold=True)
    wr(title + "\n")
    reset_style()


def draw_status():
    wr("\n")
    style(fg=WHITE, bold=True)
    wr("STATUS ")
    reset_style()
    wr(str(status)[: W - 8])


def draw_home():
    draw_header("Robot")
    pill("PINS")
    wr("  ")
    pill("{}ms".format(config["move_ms"]))
    wr("\n")
    wr("\n")
    for idx, item in enumerate(menu_items):
        line("{}. {}".format(idx + 1, item), cursor == idx)
    wr("\n")
    nav_hint("UP/DOWN  ENTER  1-4  Q")
    draw_status()


def launch_web():
    global status
    try:
        serve_web()
        status = "Web closed"
    except Exception as exc:
        status = "Web error {}".format(exc)[:34]


def start_ap():
    try:
        network.country("US")
    except Exception:
        pass
    ap = network.WLAN(network.AP_IF)
    try:
        ap.active(False)
        time.sleep_ms(300)
    except Exception:
        pass
    try:
        ap.config(essid=AP_SSID, password=AP_PASSWORD, channel=6, authmode=3)
    except Exception:
        try:
            ap.config(ssid=AP_SSID, password=AP_PASSWORD, channel=6)
        except Exception:
            ap.config(essid=AP_SSID, password=AP_PASSWORD)
    ap.active(True)
    for _ in range(20):
        if ap.active():
            break
        time.sleep_ms(250)
    return ap


def draw_web(ip):
    draw_header("Web")
    field("SSID", AP_SSID, 35)
    field("PASS", AP_PASSWORD, 35)
    field("URL", "http://{}".format(ip), 35)
    wr("\n")
    nav_hint("Safari -> Wi-Fi -> URL")
    nav_hint("Q / Back exits")
    draw_status()


def web_html():
    rows = ""
    for i in range(4):
        active = " selected" if i == joint else ""
        rows += """
<section class="axis{active}">
<button onclick="setAxis({i})">{label}</button>
<span>{name}</span><strong>{value}</strong>
<input type="range" min="0" max="180" value="{value}" onchange="setVal({i},this.value)">
</section>""".format(active=active, i=i, label=labels[i], name=axis_names[i], value=manual[i])
    return """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Robot</title><style>
*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:Arial,sans-serif;background:#fff;color:#000}
body{border:4px solid #000}header,footer{padding:12px;border-bottom:4px solid #000}footer{border-top:4px solid #000;border-bottom:0}
main{padding:12px}.title{font-size:24px;font-weight:900;text-transform:uppercase}.team{font-size:12px;text-transform:uppercase}
button,input{border:2px solid #000;border-radius:0;background:#fff;color:#000;font:inherit}button{padding:12px;font-weight:900}
.grid{display:grid;gap:10px}.axis{border:2px solid #000;padding:10px;display:grid;gap:8px}.selected{background:#000;color:#fff}
.moves{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}.stop{grid-column:1/3}.meta{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}
</style></head><body>
<header><div class="title">Proyecto final Robotica</div><div class="team">Apodaca, Calderon, Soriano, Ochoa</div></header>
<main><div class="meta"><div>Axis <b>{axis}</b></div><div>Pulse <b>{pulse} ms</b></div><div>Status</div><b>{status}</b></div>
<div class="moves"><button onclick="move(-1)">Reverse</button><button onclick="move(1)">Forward</button><button class="stop" onclick="stopAll()">Stop</button></div>
<div class="grid">{rows}</div></main><footer>EE 2/3 | Q1 4/5 | Q2 21/28 | Q3 8/9</footer>
<script>function go(p){{fetch(p).then(()=>location.reload())}}function setAxis(i){{go('/axis?i='+i)}}function setVal(i,v){{go('/set?i='+i+'&v='+v)}}function move(d){{go('/move?d='+d)}}function stopAll(){{go('/stop')}}</script>
</body></html>""".format(axis=labels[joint], pulse=config["move_ms"], status=status, rows=rows)


def query_int(path, name, default):
    token = name + "="
    pos = path.find(token)
    if pos < 0:
        return default
    pos += len(token)
    end = path.find("&", pos)
    if end < 0:
        end = len(path)
    try:
        return int(path[pos:end])
    except Exception:
        return default


def handle_web(path):
    global joint, status
    if path.startswith("/axis"):
        joint = clamp(query_int(path, "i", joint), 0, 3)
        status = "Axis {}".format(labels[joint])
    elif path.startswith("/set"):
        i = clamp(query_int(path, "i", joint), 0, 3)
        manual[i] = clamp(query_int(path, "v", manual[i]), 0, 180)
        joint = i
        status = "{} {}".format(labels[i], manual[i])
    elif path.startswith("/move"):
        d = query_int(path, "d", 1)
        adjust_manual(1 if d >= 0 else -1)
    elif path.startswith("/stop"):
        stop_gpio()
        status = "Outputs stopped"


def serve_web():
    global status
    ap = start_ap()
    ip = ap.ifconfig()[0]
    status = "Web ready"
    draw_web(ip)
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(socket.getaddrinfo("0.0.0.0", 80)[0][-1])
    s.listen(2)
    s.settimeout(0.25)
    while True:
        try:
            if read_key() == "esc":
                break
            client, _ = s.accept()
            req = client.recv(512).decode("utf-8", "ignore")
            first = req.split("\r\n")[0].split(" ")
            path = first[1] if len(first) > 1 else "/"
            handle_web(path)
            body = web_html()
            client.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n")
            client.send(body)
            client.close()
            draw_web(ip)
        except OSError:
            pass
    stop_gpio()
    s.close()


def draw_manual():
    draw_header("Manual")
    pill("{} {}".format(labels[joint], axis_names[joint]))
    wr("\n\n")
    for idx, label in enumerate(labels):
        if joint == idx:
            style(fg=BLACK, bg=WHITE, bold=True)
            mark = ">"
        else:
            mark = " "
        wr("{} {} {:>3} ".format(mark, label, manual[idx]))
        reset_style()
        bar(manual[idx], joint == idx)
        wr(" {}\n".format(axis_names[idx]))
    wr("\n")
    nav_hint("UP/DOWN axis   LEFT/RIGHT pulse")
    nav_hint("1-4 axis      S stop      ESC")
    draw_status()


def draw_help():
    draw_header("Pins")
    field("EE", "GP2 / GP3", 35)
    field("Q1", "GP4 / GP5", 35)
    field("Q2", "GP21 / GP28", 35)
    field("Q3", "GP8 / GP9", 35)
    wr("\n")
    nav_hint("GND common. External motor power.")
    nav_hint("ESC")
    draw_status()


def draw():
    if screen == 0:
        draw_home()
    elif screen == 1:
        draw_manual()
    elif screen == 2:
        draw_help()
    else:
        draw_help()


def read_key():
    n = picocalc.terminal.readinto(key_buf)
    if not n:
        return None
    data = bytes(key_buf[:n])
    if data in (b"\x1b", b"\x1b\x1b", b"\x08", b"\x7f", b"q", b"Q"):
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
    if data in (b"p", b"P"):
        return "presets"
    if data in (b"c", b"C"):
        return "connection"
    if data in (b"?", b"/"):
        return "help"
    if data in (b"1", b"2", b"3", b"4"):
        return data.decode()
    if data in (b"5",):
        return "5"
    return None


def send_current():
    global status
    stop_gpio()
    status = "Outputs stopped"


def adjust_manual(delta):
    global status
    manual[joint] = clamp(manual[joint] + (delta * int(config["step"])), 0, 180)
    try:
        pulse_axis(joint, delta)
        status_text = "{} {}".format(labels[joint], "FWD" if delta > 0 else "REV")
    except Exception as exc:
        status_text = "Pin error {}".format(exc)
    status = status_text[:34]


def loop():
    global screen, cursor, joint, status
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
                cursor = (cursor - 1) % len(menu_items)
            elif key == "down":
                cursor = (cursor + 1) % len(menu_items)
            elif key == "enter":
                if cursor == 0:
                    screen = 1
                    status = "Manual"
                elif cursor == 1:
                    launch_web()
                elif cursor == 2:
                    screen = 2
                    status = "Pins"
                elif cursor == 3:
                    save_config()
            elif key == "1":
                screen = 1
                status = "Manual"
            elif key == "2":
                launch_web()
            elif key == "3":
                screen = 2
                status = "Pins"
            elif key == "4" or key == "send":
                save_config()
        elif screen == 1:
            if key == "esc":
                screen = 0
                cursor = 0
            elif key == "manual":
                status = "Manual"
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
                stop_gpio()
                status = "Outputs stopped"
            elif key in ("enter", "send"):
                send_current()
        elif screen == 2:
            if key == "esc":
                screen = 0
                cursor = 1
        else:
            if key == "esc":
                screen = 0
                cursor = 3
        draw()


def main_menu():
    try:
        loop()
    finally:
        gc.collect()


main_executed = False
