import gc
import json
import socket
import time
from machine import Pin, PWM

import network
import picocalc

E = "\033"
W = 53
CONFIG_PATH = "/sd/robotarm.json"
AP_SSID = "PICOCALC_ROBOT"
AP_PASSWORD = "robot12345"

TEAM = (
    "Alejandro Apodaca Cordova",
    "Gael Calderon Robles",
    "Lailah Soriano Alvarez",
    "Moises Ochoa",
)

config = {
    "move_ms": 250,
    "step": 5,
}

gpio_pairs = (
    (4, 5),    # Q1
    (21, 28),  # Q2
    (8, 9),    # Q3
)
GRIPPER_SERVO_PIN = 2

labels = ("GRIP", "BASE", "SHLD", "ELBW")
axis_names = ("Gripper", "Base motor", "Shoulder motor", "Elbow motor")
manual = [90, 90, 90, 90]
joint = 0
status = "Starting"
key_buf = bytearray(16)
gpio_pins = None
gripper_pwm = None
web_socket = None
web_ip = "192.168.4.1"
web_port = 80
last_draw_state = None


def wr(text):
    picocalc.terminal.wr(text)


def clear():
    wr("{}[2J{}[H{}[?25l".format(E, E, E))


def at(row, col):
    wr("{}[{};{}H".format(E, row, col))


def style(code):
    wr("{}[{}m".format(E, code))


def reset_style():
    wr("{}[0m".format(E))


def fit(text, width):
    text = str(text)[:width]
    return text + (" " * (width - len(text)))


def clamp(value, low, high):
    return min(max(value, low), high)


def action_words(axis, direction):
    if axis == 0:
        return "Open" if direction > 0 else "Close"
    return "Forward" if direction > 0 else "Back"


def action_label(axis, direction, html=False):
    word = action_words(axis, direction)
    left = "&larr;" if html else "<-"
    right = "&rarr;" if html else "->"
    if direction > 0:
        return "{} {}".format(word, right)
    return "{} {}".format(left, word)


def load_config():
    global joint, status
    try:
        with open(CONFIG_PATH, "r") as f:
            saved = json.load(f)
        for key in config:
            if key in saved:
                config[key] = saved[key]
        if "manual" in saved and len(saved["manual"]) >= 4:
            for i in range(4):
                manual[i] = clamp(int(saved["manual"][i]), 0, 180)
        if "selectedAxis" in saved:
            joint = clamp(int(saved["selectedAxis"]), 0, 3)
        status = "Ready"
    except Exception:
        status = "Ready"


def save_config():
    try:
        payload = dict(config)
        payload["manual"] = manual[:]
        payload["selectedAxis"] = joint
        with open(CONFIG_PATH, "w") as f:
            json.dump(payload, f)
    except Exception:
        pass


def init_gpio():
    global gpio_pins, gripper_pwm
    if gpio_pins is not None:
        return
    gripper_pwm = PWM(Pin(GRIPPER_SERVO_PIN))
    gripper_pwm.freq(50)
    gpio_pins = []
    for a, b in gpio_pairs:
        gpio_pins.append((Pin(a, Pin.OUT, value=0), Pin(b, Pin.OUT, value=0)))


def stop_gpio():
    init_gpio()
    for p1, p2 in gpio_pins:
        p1.value(0)
        p2.value(0)


def set_gripper(angle):
    init_gpio()
    angle = clamp(int(angle), 0, 180)
    duty_ns = 500000 + int((angle * 2000000) / 180)
    gripper_pwm.duty_ns(duty_ns)


def pulse_axis(axis, direction):
    init_gpio()
    if axis == 0:
        set_gripper(manual[0])
        time.sleep_ms(80)
        return
    p1, p2 = gpio_pins[axis - 1]
    p1.value(1 if direction > 0 else 0)
    p2.value(0 if direction > 0 else 1)
    time.sleep_ms(int(config["move_ms"]))
    p1.value(0)
    p2.value(0)


def web_url():
    if web_port == 80:
        return "http://{}".format(web_ip)
    return "http://{}:{}".format(web_ip, web_port)


def draw(force=False):
    global last_draw_state
    state = (joint, manual[0], manual[1], manual[2], manual[3], status, web_port, web_ip)
    if not force and state == last_draw_state:
        return
    last_draw_state = state
    clear()
    style("37;1")
    wr("+" + "-" * (W - 2) + "+")
    at(2, 1)
    wr(fit("| Proyecto final Robotica", W - 1) + "|")
    at(3, 1)
    wr(fit("| " + TEAM[0], W - 1) + "|")
    at(4, 1)
    wr(fit("| " + TEAM[1], W - 1) + "|")
    at(5, 1)
    wr(fit("| " + TEAM[2], W - 1) + "|")
    at(6, 1)
    wr(fit("| " + TEAM[3], W - 1) + "|")
    at(7, 1)
    wr("+" + "-" * (W - 2) + "+")
    reset_style()
    at(9, 1)
    style("37;1")
    wr("Controller\n")
    reset_style()
    wr("Wi-Fi  {}\n".format(AP_SSID))
    wr("Pass   {}\n".format(AP_PASSWORD))
    wr("URL    {}\n\n".format(web_url()))
    for i, label in enumerate(labels):
        if i == joint:
            style("30;47;1")
            wr(">")
        else:
            wr(" ")
        wr(" {} {:<14} {:>3} ".format(label, axis_names[i], manual[i]))
        reset_style()
        wr("   [{}]  [{}]\n".format(action_label(i, -1), action_label(i, 1)))
    wr("\n")
    wr("UP/DOWN axis   LEFT <- Close/Back   RIGHT Open/Forward ->\n")
    wr("1-4 direct       S stop            Q exit\n")
    style("37;1")
    wr("STATUS ")
    reset_style()
    wr(str(status)[: W - 8])


def read_key():
    n = picocalc.terminal.readinto(key_buf)
    if not n:
        return None
    data = bytes(key_buf[:n])
    if data in (b"\x1b", b"\x1b\x1b", b"\x08", b"\x7f", b"q", b"Q"):
        return "esc"
    if data in (b"s", b"S", b"\r", b"\n"):
        return "stop"
    if data.endswith(b"[A"):
        return "up"
    if data.endswith(b"[B"):
        return "down"
    if data.endswith(b"[C") or data in (b"+", b"="):
        return "right"
    if data.endswith(b"[D") or data in (b"-", b"_"):
        return "left"
    if data in (b"1", b"2", b"3", b"4"):
        return data.decode()
    return None


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


def bind_web_socket():
    global web_port
    last_error = None
    for port in (80, 8080, 8000):
        try:
            s = socket.socket()
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(socket.getaddrinfo("0.0.0.0", port)[0][-1])
            s.listen(1)
            s.settimeout(0.1)
            web_port = port
            return s
        except OSError as exc:
            last_error = exc
            try:
                s.close()
            except Exception:
                pass
    raise last_error


def start_web():
    global web_socket, web_ip, status
    ap = start_ap()
    web_ip = ap.ifconfig()[0]
    web_socket = bind_web_socket()
    status = "Web ready"


def team_html():
    out = ""
    for name in TEAM:
        out += "<li>{}</li>".format(name)
    return out


def web_html():
    rows = ""
    for i in range(4):
        active = " selected" if i == joint else ""
        neg = action_label(i, -1, True)
        pos = action_label(i, 1, True)
        rows += """
<section id="axis{i}" class="axis{active}">
<button class="pick" onclick="setAxis({i})">{label}</button>
<div><span>{name}</span><strong id="v{i}">{value}</strong></div>
<div class="pair"><button onclick="moveAxis({i},-1)">{neg}</button><button onclick="moveAxis({i},1)">{pos}</button></div>
</section>""".format(active=active, i=i, label=labels[i], name=axis_names[i], value=manual[i], neg=neg, pos=pos)
    return """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Robot</title><style>
*{{box-sizing:border-box}}html,body{{margin:0;height:100%;overflow:hidden;font-family:Arial,sans-serif;background:#fff;color:#000}}
body{{height:100dvh;border:4px solid #000;display:grid;grid-template-rows:auto 1fr auto}}
header,footer{{padding:12px;border-bottom:4px solid #000}}footer{{border-top:4px solid #000;border-bottom:0}}
main{{min-height:0;overflow:auto;padding:12px;-webkit-overflow-scrolling:touch}}
.title{{font-size:22px;font-weight:900;text-transform:uppercase}}.team{{margin:8px 0 0 18px;padding:0;font-size:13px}}
button{{border:2px solid #000;border-radius:0;background:#fff;color:#000;font:inherit;padding:14px 10px;font-weight:900;min-height:48px}}
.grid{{display:grid;gap:10px}}.axis{{border:2px solid #000;padding:10px;display:grid;grid-template-columns:70px 1fr;gap:8px;align-items:center}}
.axis .pair{{grid-column:1/3}}.axis strong{{float:right}}.pick{{padding:10px;min-height:44px}}.selected{{background:#000;color:#fff}}.selected button{{border-color:#fff}}
.moves,.pair{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0}}.moves button{{font-size:20px;min-height:64px}}.stop{{grid-column:1/3;font-size:16px!important;min-height:48px!important}}.meta{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:0 0 12px}}
</style></head><body>
<header><div class="title">Proyecto final Robotica</div><ul class="team">{team}</ul></header>
<main><div class="meta"><div>Selected <b id="axisName">{axis}</b></div><div>Pulse <b>{pulse} ms</b></div><div>Status</div><b id="status">{status}</b></div>
<div class="moves"><button id="leftBtn" onclick="move(-1)">{left}</button><button id="rightBtn" onclick="move(1)">{right}</button><button class="stop" onclick="stopAll()">Stop</button></div>
<div class="grid">{rows}</div></main><footer>Grip servo GP2 | Base 4/5 | Shoulder 21/28 | Elbow 8/9</footer>
<script>
let busy=false,pending=null;
function api(p){{if(busy){{pending=p;return}}busy=true;fetch(p).then(r=>r.json()).then(update).catch(()=>0).finally(()=>{{busy=false;if(pending){{let x=pending;pending=null;api(x)}}}})}}
function setAxis(i){{api('/cmd?a=axis&i='+i)}}
function move(d){{api('/cmd?a=move&d='+d)}}
function moveAxis(i,d){{api('/cmd?a=move&i='+i+'&d='+d)}}
function stopAll(){{api('/cmd?a=stop')}}
function update(s){{document.getElementById('axisName').textContent=s.names[s.joint];document.getElementById('status').textContent=s.status;document.getElementById('leftBtn').innerHTML=s.joint===0?'&larr; Close':'&larr; Back';document.getElementById('rightBtn').innerHTML=s.joint===0?'Open &rarr;':'Forward &rarr;';for(let i=0;i<4;i++){{document.getElementById('v'+i).textContent=s.manual[i];document.getElementById('axis'+i).className='axis'+(i===s.joint?' selected':'')}}}}
setInterval(()=>{{if(!busy)fetch('/state').then(r=>r.json()).then(update).catch(()=>0)}},2000);
</script>
</body></html>""".format(team=team_html(), axis=axis_names[joint], pulse=config["move_ms"], status=status, rows=rows, left=action_label(joint, -1, True), right=action_label(joint, 1, True))


def json_state():
    return '{{"joint":{},"labels":["{}","{}","{}","{}"],"names":["{}","{}","{}","{}"],"manual":[{},{},{},{}],"status":"{}"}}'.format(
        joint,
        labels[0],
        labels[1],
        labels[2],
        labels[3],
        axis_names[0],
        axis_names[1],
        axis_names[2],
        axis_names[3],
        manual[0],
        manual[1],
        manual[2],
        manual[3],
        str(status).replace('"', "'"),
    )


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


def adjust_manual(delta, axis=None):
    global status, joint
    if axis is not None:
        joint = clamp(axis, 0, 3)
    manual[joint] = clamp(manual[joint] + (delta * int(config["step"])), 0, 180)
    try:
        pulse_axis(joint, delta)
        status = "{} {}".format(axis_names[joint], action_words(joint, delta))
    except Exception as exc:
        status = "Pin error {}".format(exc)[:34]
    save_config()


def handle_web(path):
    global joint, status
    if path.startswith("/cmd"):
        action = path_value(path, "a", "")
        if action == "axis":
            joint = clamp(query_int(path, "i", joint), 0, 3)
            status = "Axis {}".format(labels[joint])
        elif action == "set":
            i = clamp(query_int(path, "i", joint), 0, 3)
            manual[i] = clamp(query_int(path, "v", manual[i]), 0, 180)
            joint = i
            status = "{} {}".format(labels[i], manual[i])
            save_config()
        elif action == "move":
            adjust_manual(1 if query_int(path, "d", 1) >= 0 else -1, query_int(path, "i", joint))
        elif action == "stop":
            stop_gpio()
            status = "Outputs stopped"
        return "json", json_state()
    if path.startswith("/state"):
        return "json", json_state()
    if path.startswith("/axis"):
        joint = clamp(query_int(path, "i", joint), 0, 3)
        status = "Axis {}".format(labels[joint])
    elif path.startswith("/set"):
        i = clamp(query_int(path, "i", joint), 0, 3)
        manual[i] = clamp(query_int(path, "v", manual[i]), 0, 180)
        joint = i
        status = "{} {}".format(labels[i], manual[i])
        save_config()
    elif path.startswith("/move"):
        adjust_manual(1 if query_int(path, "d", 1) >= 0 else -1)
    elif path.startswith("/stop"):
        stop_gpio()
        status = "Outputs stopped"
    return "html", web_html()


def path_value(path, name, default):
    token = name + "="
    pos = path.find(token)
    if pos < 0:
        return default
    pos += len(token)
    end = path.find("&", pos)
    if end < 0:
        end = len(path)
    return path[pos:end]


def poll_web():
    if web_socket is None:
        return False
    try:
        client, _ = web_socket.accept()
    except OSError:
        return False
    try:
        req = client.recv(512).decode("utf-8", "ignore")
        first = req.split("\r\n")[0].split(" ")
        path = first[1] if len(first) > 1 else "/"
        kind, body = handle_web(path)
        if kind == "json":
            client.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n")
        else:
            client.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n")
        client.send(body)
    except Exception:
        try:
            client.close()
        except Exception:
            pass
        return False
    client.close()
    return True


def loop():
    global joint, status
    load_config()
    try:
        start_web()
    except Exception as exc:
        status = "Web error {}".format(exc)[:34]
    draw()
    while True:
        redraw = poll_web()
        key = read_key()
        if key:
            if key == "esc":
                break
            if key == "up":
                joint = (joint - 1) % 4
                status = "Axis {}".format(labels[joint])
            elif key == "down":
                joint = (joint + 1) % 4
                status = "Axis {}".format(labels[joint])
            elif key == "left":
                adjust_manual(-1)
            elif key == "right":
                adjust_manual(1)
            elif key == "stop":
                stop_gpio()
                status = "Outputs stopped"
            elif key in ("1", "2", "3", "4"):
                joint = int(key) - 1
                status = "Axis {}".format(labels[joint])
            redraw = True
        if redraw:
            draw()
        time.sleep_ms(20)
    stop_gpio()
    if web_socket:
        web_socket.close()
    clear()


def main_menu():
    try:
        loop()
    finally:
        stop_gpio()
        gc.collect()


main_executed = False
