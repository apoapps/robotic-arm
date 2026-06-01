import gc
import socket
import time
from machine import Pin

import network
import picocalc

E = "\033"
W = 53
AP_SSID = "PICOCALC_ROBOT"
AP_PASSWORD = "robot12345"
PORT = 80

labels = ("EE", "Q1", "Q2", "Q3")
names = ("Grip", "Base", "Shoulder", "Elbow")
gpio_pairs = (
    (2, 3),
    (4, 5),
    (21, 28),
    (8, 9),
)

manual = [90, 90, 90, 90]
selected = 0
pulse_ms = 250
status = "Ready"
pins = []


def wr(text):
    picocalc.terminal.wr(text)


def clear():
    wr("{}[2J{}[H{}[?25l".format(E, E, E))


def fit(text, width):
    text = str(text)[:width]
    return text + (" " * (width - len(text)))


def draw(ip="192.168.4.1"):
    clear()
    wr("+" + "-" * (W - 2) + "+\n")
    wr(fit("| Proyecto final Robotica", W - 1) + "|\n")
    wr(fit("| Apodaca, Calderon, Soriano, Ochoa", W - 1) + "|\n")
    wr("+" + "-" * (W - 2) + "+\n\n")
    wr("Robot Web\n")
    wr("SSID  {}\n".format(AP_SSID))
    wr("PASS  {}\n".format(AP_PASSWORD))
    wr("URL   http://{}\n\n".format(ip))
    wr("Axis  {} {}\n".format(labels[selected], names[selected]))
    wr("Pulse {} ms\n".format(pulse_ms))
    wr("Status {}\n\n".format(status))
    wr("Safari -> connect to Wi-Fi -> open URL\n")
    wr("Q exits\n")


def init_gpio():
    global pins
    if pins:
        return
    for a, b in gpio_pairs:
        p1 = Pin(a, Pin.OUT, value=0)
        p2 = Pin(b, Pin.OUT, value=0)
        pins.append((p1, p2))


def stop_all():
    init_gpio()
    for p1, p2 in pins:
        p1.value(0)
        p2.value(0)


def pulse(axis, direction):
    init_gpio()
    p1, p2 = pins[axis]
    if direction > 0:
        p1.value(1)
        p2.value(0)
    else:
        p1.value(0)
        p2.value(1)
    time.sleep_ms(pulse_ms)
    p1.value(0)
    p2.value(0)


def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    try:
        ap.config(essid=AP_SSID, password=AP_PASSWORD)
    except Exception:
        ap.config(ssid=AP_SSID, password=AP_PASSWORD)
    for _ in range(20):
        if ap.active():
            break
        time.sleep_ms(250)
    return ap


def html():
    rows = ""
    for i in range(4):
        active = " selected" if i == selected else ""
        rows += """
        <section class="axis{active}">
          <button onclick="setAxis({i})">{label}</button>
          <span>{name}</span>
          <strong>{value}</strong>
          <input type="range" min="0" max="180" value="{value}" onchange="setVal({i},this.value)">
        </section>
        """.format(active=active, i=i, label=labels[i], name=names[i], value=manual[i])
    return """<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Robot</title>
<style>
*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:Arial,sans-serif;background:#fff;color:#000}
body{border:4px solid #000}header,footer{padding:12px;border-bottom:4px solid #000}footer{border-top:4px solid #000;border-bottom:0}
main{padding:12px}.title{font-size:24px;font-weight:900;text-transform:uppercase}.team{font-size:12px;text-transform:uppercase}
button,input,select{border:2px solid #000;border-radius:0;background:#fff;color:#000;font:inherit}
button{padding:12px;font-weight:900}.grid{display:grid;gap:10px}.axis{border:2px solid #000;padding:10px;display:grid;gap:8px}
.selected{background:#000;color:#fff}.selected button,.selected input{border-color:#fff}.moves{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}
.stop{grid-column:1/3}.bar{width:100%}.meta{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}
</style>
</head>
<body>
<header><div class="title">Proyecto final Robotica</div><div class="team">Apodaca, Calderon, Soriano, Ochoa</div></header>
<main>
<div class="meta"><div>Axis <b>{axis}</b></div><div>Pulse <b>{pulse} ms</b></div><div>Status</div><b>{status}</b></div>
<div class="moves"><button onclick="move(-1)">Reverse</button><button onclick="move(1)">Forward</button><button class="stop" onclick="stopAll()">Stop</button></div>
<div class="grid">{rows}</div>
</main>
<footer>EE 2/3 | Q1 4/5 | Q2 21/28 | Q3 8/9</footer>
<script>
function go(path){{fetch(path).then(()=>location.reload())}}
function setAxis(i){{go('/axis?i='+i)}}
function setVal(i,v){{go('/set?i='+i+'&v='+v)}}
function move(d){{go('/move?d='+d)}}
function stopAll(){{go('/stop')}}
</script>
</body>
</html>""".format(axis=labels[selected], pulse=pulse_ms, status=status, rows=rows)


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


def handle(path):
    global selected, status
    if path.startswith("/axis"):
        selected = max(0, min(3, query_int(path, "i", selected)))
        status = "Axis {}".format(labels[selected])
    elif path.startswith("/set"):
        i = max(0, min(3, query_int(path, "i", selected)))
        v = max(0, min(180, query_int(path, "v", manual[i])))
        manual[i] = v
        selected = i
        status = "{} {}".format(labels[i], v)
    elif path.startswith("/move"):
        d = query_int(path, "d", 1)
        pulse(selected, 1 if d >= 0 else -1)
        manual[selected] = max(0, min(180, manual[selected] + (5 if d >= 0 else -5)))
        status = "{} {}".format(labels[selected], "FWD" if d >= 0 else "REV")
    elif path.startswith("/stop"):
        stop_all()
        status = "Stopped"


def serve():
    global status
    ap = start_ap()
    ip = ap.ifconfig()[0]
    draw(ip)
    addr = socket.getaddrinfo("0.0.0.0", PORT)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(2)
    status = "Web ready"
    draw(ip)
    while True:
        try:
            client, _ = s.accept()
            req = client.recv(512).decode("utf-8", "ignore")
            first = req.split("\r\n")[0]
            parts = first.split(" ")
            path = parts[1] if len(parts) > 1 else "/"
            handle(path)
            body = html()
            client.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n")
            client.send(body)
            client.close()
            draw(ip)
        except KeyboardInterrupt:
            break
        except Exception as exc:
            status = "Web error {}".format(exc)[:28]
            draw(ip)
    stop_all()
    try:
        s.close()
    except Exception:
        pass


def main_menu():
    try:
        serve()
    finally:
        stop_all()
        gc.collect()


main_executed = False
