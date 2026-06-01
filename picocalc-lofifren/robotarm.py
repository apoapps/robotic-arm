import gc
import json
import socket
import time
from machine import Pin

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
    (2, 3),    # EE
    (4, 5),    # Q1
    (21, 28),  # Q2
    (8, 9),    # Q3
)

labels = ("EE", "Q1", "Q2", "Q3")
axis_names = ("Grip", "Base", "Shoulder", "Elbow")
manual = [90, 90, 90, 90]
joint = 0
status = "Starting"
key_buf = bytearray(16)
gpio_pins = None
web_socket = None
web_ip = "192.168.4.1"
web_port = 80


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


def bar(value, active=False):
    width = 20
    filled = int((clamp(value, 0, 180) * width) / 180)
    if active:
        style("30;47;1")
    wr("[{}{}]".format("=" * filled, " " * (width - filled)))
    reset_style()


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
    global gpio_pins
    if gpio_pins is not None:
        return
    gpio_pins = []
    for a, b in gpio_pairs:
        gpio_pins.append((Pin(a, Pin.OUT, value=0), Pin(b, Pin.OUT, value=0)))


def stop_gpio():
    init_gpio()
    for p1, p2 in gpio_pins:
        p1.value(0)
        p2.value(0)


def pulse_axis(axis, direction):
    init_gpio()
    p1, p2 = gpio_pins[axis]
    p1.value(1 if direction > 0 else 0)
    p2.value(0 if direction > 0 else 1)
    time.sleep_ms(int(config["move_ms"]))
    p1.value(0)
    p2.value(0)


def web_url():
    if web_port == 80:
        return "http://{}".format(web_ip)
    return "http://{}:{}".format(web_ip, web_port)


def draw():
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
        wr(" {} {:>3} ".format(label, manual[i]))
        reset_style()
        bar(manual[i], i == joint)
        wr(" {}\n".format(axis_names[i]))
    wr("\n")
    wr("UP/DOWN axis  LEFT/RIGHT pulse  1-4 axis  S stop\n")
    wr("Q exits\n")
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
            s.listen(2)
            s.settimeout(0.02)
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
        rows += """
<section id="axis{i}" class="axis{active}">
<button onclick="setAxis({i})">{label}</button>
<span>{name}</span><strong id="v{i}">{value}</strong>
<input id="r{i}" type="range" min="0" max="180" value="{value}" oninput="setVal({i},this.value)">
</section>""".format(active=active, i=i, label=labels[i], name=axis_names[i], value=manual[i])
    return """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Robot</title><style>
*{{box-sizing:border-box}}html,body{{margin:0;height:100%;overflow:hidden;font-family:Arial,sans-serif;background:#fff;color:#000}}
body{{height:100dvh;border:4px solid #000;display:grid;grid-template-rows:auto 1fr auto}}
header,footer{{padding:12px;border-bottom:4px solid #000}}footer{{border-top:4px solid #000;border-bottom:0}}
main{{min-height:0;overflow:auto;padding:12px;-webkit-overflow-scrolling:touch}}
.title{{font-size:22px;font-weight:900;text-transform:uppercase}}.team{{margin:8px 0 0 18px;padding:0;font-size:13px}}
button,input{{border:2px solid #000;border-radius:0;background:#fff;color:#000;font:inherit}}button{{padding:12px;font-weight:900}}
.grid{{display:grid;gap:10px}}.axis{{border:2px solid #000;padding:10px;display:grid;gap:8px}}.selected{{background:#000;color:#fff}}
.moves{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}}.stop{{grid-column:1/3}}.meta{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:0 0 12px}}
</style></head><body>
<header><div class="title">Proyecto final Robotica</div><ul class="team">{team}</ul></header>
<main><div class="meta"><div>Axis <b id="axisName">{axis}</b></div><div>Pulse <b>{pulse} ms</b></div><div>Status</div><b id="status">{status}</b></div>
<div class="moves"><button ontouchstart="move(-1)" onclick="move(-1)">Reverse</button><button ontouchstart="move(1)" onclick="move(1)">Forward</button><button class="stop" onclick="stopAll()">Stop</button></div>
<div class="grid">{rows}</div></main><footer>EE 2/3 | Q1 4/5 | Q2 21/28 | Q3 8/9</footer>
<script>
let busy=false,pending=null;
function api(p){{if(busy){{pending=p;return}}busy=true;fetch(p).then(r=>r.json()).then(update).catch(()=>0).finally(()=>{{busy=false;if(pending){{let x=pending;pending=null;api(x)}}}})}}
function setAxis(i){{api('/cmd?a=axis&i='+i)}}
function setVal(i,v){{document.getElementById('v'+i).textContent=v;api('/cmd?a=set&i='+i+'&v='+v)}}
function move(d){{api('/cmd?a=move&d='+d)}}
function stopAll(){{api('/cmd?a=stop')}}
function update(s){{document.getElementById('axisName').textContent=s.labels[s.joint];document.getElementById('status').textContent=s.status;for(let i=0;i<4;i++){{document.getElementById('v'+i).textContent=s.manual[i];document.getElementById('r'+i).value=s.manual[i];document.getElementById('axis'+i).className='axis'+(i===s.joint?' selected':'')}}}}
setInterval(()=>{{if(!busy)fetch('/state').then(r=>r.json()).then(update).catch(()=>0)}},500);
</script>
</body></html>""".format(team=team_html(), axis=labels[joint], pulse=config["move_ms"], status=status, rows=rows)


def json_state():
    return '{{"joint":{},"labels":["{}","{}","{}","{}"],"manual":[{},{},{},{}],"status":"{}"}}'.format(
        joint,
        labels[0],
        labels[1],
        labels[2],
        labels[3],
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


def adjust_manual(delta):
    global status
    manual[joint] = clamp(manual[joint] + (delta * int(config["step"])), 0, 180)
    try:
        pulse_axis(joint, delta)
        status = "{} {}".format(labels[joint], "FWD" if delta > 0 else "REV")
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
            adjust_manual(1 if query_int(path, "d", 1) >= 0 else -1)
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
