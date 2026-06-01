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
)
GRIPPER_SERVO_PIN = 2
ELBOW_ACTUATOR_PIN = 3

labels = ("GRIP", "BASE", "SHLD", "ELBW")
axis_names = ("Gripper", "Base motor", "Shoulder motor", "Elbow actuator")
axis_short_names = ("Gripper", "Base", "Shoulder", "Actuator")
pin_names = ("GP2", "GP4/5", "GP21/28", "GP3")
manual = [90, 90, 90, 90]
joint = 0
status = "Starting"
key_buf = bytearray(16)
gpio_pins = None
gripper_pwm = None
elbow_pwm = None
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


def icon_svg(name):
    paths = {
        "robot": "<path d='M12 4v3'/><path d='M8 4h8'/><rect x='5' y='7' width='14' height='11' rx='2'/><path d='M9 12h.01'/><path d='M15 12h.01'/><path d='M9 16h6'/><path d='M3 11v4'/><path d='M21 11v4'/>",
        "people": "<path d='M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2'/><circle cx='9' cy='7' r='4'/><path d='M23 21v-2a4 4 0 0 0-3-3.87'/><path d='M16 3.13a4 4 0 0 1 0 7.75'/>",
        "stop": "<rect x='6' y='6' width='12' height='12' rx='1'/>",
        "back": "<path d='M15 18l-6-6 6-6'/>",
        "forward": "<path d='M9 18l6-6-6-6'/>",
        "hand": "<path d='M18 11V7a2 2 0 0 0-4 0v4'/><path d='M14 10V6a2 2 0 0 0-4 0v7'/><path d='M10 11V8a2 2 0 0 0-4 0v6a6 6 0 0 0 6 6h2a5 5 0 0 0 5-5v-4a2 2 0 0 0-4 0v1'/>",
        "motor": "<circle cx='12' cy='12' r='8'/><circle cx='12' cy='12' r='2'/><path d='M12 4v3'/><path d='M12 17v3'/><path d='M4 12h3'/><path d='M17 12h3'/>",
        "caret": "<path d='M6 9l6 6 6-6'/>",
    }
    return "<svg class='ion' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>{}</svg>".format(paths[name])


def axis_icon(axis):
    return icon_svg("hand" if axis == 0 else "motor")


def action_button_label(axis, direction):
    icon = icon_svg("forward" if direction > 0 else "back")
    word = action_words(axis, direction)
    if direction > 0:
        return "<span>{}</span>{}".format(word, icon)
    return "{}<span>{}</span>".format(icon, word)


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
    global gpio_pins, gripper_pwm, elbow_pwm
    if gpio_pins is not None:
        return
    gripper_pwm = PWM(Pin(GRIPPER_SERVO_PIN))
    gripper_pwm.freq(50)
    elbow_pwm = PWM(Pin(ELBOW_ACTUATOR_PIN))
    elbow_pwm.freq(50)
    gpio_pins = []
    for a, b in gpio_pairs:
        gpio_pins.append((Pin(a, Pin.OUT, value=0), Pin(b, Pin.OUT, value=0)))


def stop_gpio():
    init_gpio()
    for p1, p2 in gpio_pins:
        p1.value(0)
        p2.value(0)


def set_servo(pwm, angle):
    angle = clamp(int(angle), 0, 180)
    duty_ns = 500000 + int((angle * 2000000) / 180)
    pwm.duty_ns(duty_ns)


def set_gripper(angle):
    init_gpio()
    set_servo(gripper_pwm, angle)


def set_elbow_actuator(angle):
    init_gpio()
    set_servo(elbow_pwm, angle)


def pulse_axis(axis, direction):
    init_gpio()
    if axis == 0:
        set_gripper(manual[0])
        time.sleep_ms(80)
        return
    if axis == 3:
        set_elbow_actuator(manual[3])
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
        wr("{} {:<7} {:<8} {:>3} ".format(label, pin_names[i], axis_short_names[i], manual[i]))
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
        rows += """
<section id="axis{i}" class="axis{active}">
<button class="pick" onclick="setAxis({i})">{axis_icon}<span>{label}</span></button>
<div><span>{name}</span><strong id="v{i}">{value}</strong></div>
<div class="pair"><button onpointerdown="holdAxis({i},-1);return false" onpointerup="releaseHold()" onpointercancel="releaseHold()" onpointerleave="releaseHold()">{neg}</button><button onpointerdown="holdAxis({i},1);return false" onpointerup="releaseHold()" onpointercancel="releaseHold()" onpointerleave="releaseHold()">{pos}</button></div>
</section>""".format(active=active, i=i, label=labels[i], name=axis_names[i], value=manual[i], neg=action_button_label(i, -1), pos=action_button_label(i, 1), axis_icon=axis_icon(i))
    return """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>Robot</title><style>
*{{box-sizing:border-box;-webkit-tap-highlight-color:transparent}}html,body{{margin:0;height:100%;overflow:hidden;font-family:Arial,sans-serif;background:#fff;color:#000;touch-action:pan-y;overscroll-behavior:none;-webkit-text-size-adjust:100%}}
body{{height:100dvh;display:grid;grid-template-rows:auto 1fr auto}}
header,footer{{padding:12px;border-bottom:2px solid #000}}footer{{border-top:2px solid #000;border-bottom:0;font-size:12px}}
main{{min-height:0;overflow:auto;padding:12px;-webkit-overflow-scrolling:touch}}
.brand{{display:grid;grid-template-columns:38px 1fr auto;gap:10px;align-items:center}}.logo{{width:38px;height:38px;border:2px solid #000;display:grid;place-items:center}}
.title{{font-size:18px;font-weight:900;text-transform:uppercase;line-height:1.1}}.sub{{font-size:12px;margin-top:2px}}
.ion{{width:22px;height:22px;vertical-align:-5px}}details{{position:relative}}summary{{list-style:none;border:2px solid #000;padding:9px;display:flex;gap:6px;align-items:center;font-weight:900}}summary::-webkit-details-marker{{display:none}}
.team{{position:absolute;right:0;top:44px;z-index:4;width:235px;margin:0;padding:10px 10px 10px 24px;background:#fff;border:2px solid #000;font-size:13px;line-height:1.4}}
button{{border:2px solid #000;border-radius:0;background:#fff;color:#000;font:inherit;padding:14px 10px;font-weight:900;min-height:48px;display:flex;align-items:center;justify-content:center;gap:8px;touch-action:none;user-select:none;-webkit-user-select:none}}
button:active{{background:#000;color:#fff}}
.grid{{display:grid;gap:10px}}.axis{{border:2px solid #000;padding:10px;display:grid;grid-template-columns:76px 1fr;gap:8px;align-items:center}}
.axis .pair{{grid-column:1/3}}.axis strong{{float:right}}.pick{{padding:8px;min-height:48px;flex-direction:column;gap:2px;font-size:12px}}.selected{{background:#000;color:#fff}}.selected button{{border-color:#fff}}
.moves,.pair{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0}}.moves button{{font-size:18px;min-height:64px}}.panic{{width:86px;height:86px;border-radius:999px;background:#c00;color:#fff;border:4px solid #000;margin:14px auto 4px;font-size:13px;flex-direction:column}}.panic:active{{background:#900;color:#fff}}.meta{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:0 0 12px;font-size:14px}}
</style></head><body>
<header><div class="brand"><div class="logo">{robot}</div><div><div class="title">Proyecto final Robotica</div><div class="sub">PicoCalc Robot Arm</div></div><details><summary>{people}<span>Team</span>{caret}</summary><ul class="team">{team}</ul></details></div></header>
<main><div class="meta"><div>Selected <b id="axisName">{axis}</b></div><div>Pulse <b>{pulse} ms</b></div><div>Status</div><b id="status">{status}</b></div>
<div class="moves"><button id="leftBtn" onpointerdown="holdMove(-1);return false" onpointerup="releaseHold()" onpointercancel="releaseHold()" onpointerleave="releaseHold()">{left}</button><button id="rightBtn" onpointerdown="holdMove(1);return false" onpointerup="releaseHold()" onpointercancel="releaseHold()" onpointerleave="releaseHold()">{right}</button></div>
<div class="grid">{rows}</div><button class="panic" onclick="stopAll()">{stop}<span>Stop</span></button></main><footer>Grip GP2 | Actuator GP3 | Base 4/5 | Shoulder 21/28</footer>
<script>
let busy=false,pending=null,holdTimer=null;
function api(p){{if(busy){{pending=p;return}}busy=true;fetch(p).then(r=>r.json()).then(update).catch(()=>0).finally(()=>{{busy=false;if(pending){{let x=pending;pending=null;api(x)}}}})}}
function setAxis(i){{api('/cmd?a=axis&i='+i)}}
function move(d){{api('/cmd?a=move&d='+d)}}
function moveAxis(i,d){{api('/cmd?a=move&i='+i+'&d='+d)}}
function repeat(p){{api(p);holdTimer=setInterval(()=>api(p),360)}}
function holdMove(d){{releaseHold(false);repeat('/cmd?a=move&d='+d)}}
function holdAxis(i,d){{releaseHold(false);repeat('/cmd?a=move&i='+i+'&d='+d)}}
function releaseHold(sendStop=true){{if(holdTimer){{clearInterval(holdTimer);holdTimer=null}}if(sendStop)api('/cmd?a=stop')}}
function stopAll(){{releaseHold(false);api('/cmd?a=stop')}}
function update(s){{document.getElementById('axisName').textContent=s.names[s.joint];document.getElementById('status').textContent=s.status;document.getElementById('leftBtn').innerHTML=s.joint===0?'{back} <span>Close</span>':'{back} <span>Back</span>';document.getElementById('rightBtn').innerHTML=s.joint===0?'<span>Open</span> {forward}':'<span>Forward</span> {forward}';for(let i=0;i<4;i++){{document.getElementById('v'+i).textContent=s.manual[i];document.getElementById('axis'+i).className='axis'+(i===s.joint?' selected':'')}}}}
document.addEventListener('contextmenu',e=>e.preventDefault());
setInterval(()=>{{if(!busy)fetch('/state').then(r=>r.json()).then(update).catch(()=>0)}},2000);
</script>
</body></html>""".format(team=team_html(), axis=axis_names[joint], pulse=config["move_ms"], status=status, rows=rows, left=action_button_label(joint, -1), right=action_button_label(joint, 1), robot=icon_svg("robot"), people=icon_svg("people"), caret=icon_svg("caret"), stop=icon_svg("stop"), back=icon_svg("back"), forward=icon_svg("forward"))


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
