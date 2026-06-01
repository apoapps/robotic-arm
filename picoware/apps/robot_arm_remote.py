import socket
import time

DEFAULT_HOST = "192.168.4.1"
DEFAULT_PORT = 7777
UPDATE_URL = "https://raw.githubusercontent.com/apoapps/robotic-arm/main/picoware/apps/robot_arm_remote.py"
APP_PATH = "/picoware/apps/robot_arm_remote.py"

POSES = {
    "1": ("Neutral", [90, 90, 90, 90]),
    "2": ("Recoger", [35, 82, 120, 55]),
    "3": ("Levantar", [35, 92, 82, 82]),
    "4": ("Entregar", [115, 88, 108, 72]),
    "5": ("Abrir gripper", [25, 90, 90, 90]),
    "6": ("Cerrar gripper", [70, 90, 90, 90]),
}


def build_command(angles, move_ms=900, instruction="BUZZ"):
    times = [move_ms, move_ms, move_ms, move_ms]
    values = [instruction] + [str(int(a)) for a in angles] + [str(int(t)) for t in times]
    return "<{}>".format(",".join(values))


def send_command(host, port, command):
    addr = socket.getaddrinfo(host, port)[0][-1]
    sock = socket.socket()
    sock.settimeout(4)
    try:
        sock.connect(addr)
        sock.send(command.encode("utf-8"))
        sock.send(b"\n")
        try:
            reply = sock.recv(160)
        except OSError:
            reply = b""
    finally:
        sock.close()
    return reply.decode("utf-8", "ignore")


def ask_int(prompt, default, low=0, high=180):
    raw = input("{} [{}]: ".format(prompt, default)).strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        print("Valor invalido.")
        return default
    if value < low:
        return low
    if value > high:
        return high
    return value


def manual_pose(current):
    labels = ["Gripper", "Base q1", "Hombro q2", "Codo q3"]
    next_pose = current[:]
    for index, label in enumerate(labels):
        next_pose[index] = ask_int(label, current[index])
    return next_pose


def print_menu(current):
    print("")
    print("Robot Arm Remote")
    print("Pose actual: EE={} q1={} q2={} q3={}".format(*current))
    for key in sorted(POSES):
        print("{} - {}".format(key, POSES[key][0]))
    print("m - Manual")
    print("h - Home neutral")
    print("u - Actualizar app")
    print("q - Salir")


def self_update():
    print("Actualizando desde GitHub...")
    try:
        import mip

        mip.install(UPDATE_URL, target="/picoware/apps")
        print("Actualizacion completa. Reinicia la app.")
        return
    except Exception as exc:
        print("mip no pudo actualizar:", exc)

    try:
        try:
            import urequests as requests
        except ImportError:
            import requests

        response = requests.get(UPDATE_URL)
        try:
            if getattr(response, "status_code", 200) != 200:
                print("HTTP error:", response.status_code)
                return
            with open(APP_PATH, "w") as out_file:
                out_file.write(response.text)
            print("Actualizacion completa. Reinicia la app.")
        finally:
            response.close()
    except Exception as exc:
        print("No se pudo actualizar por Wi-Fi:", exc)
        print("Usa USB: ./tools/update_picoware_app_usb.sh")


def main():
    host = input("IP del robot [{}]: ".format(DEFAULT_HOST)).strip() or DEFAULT_HOST
    port_raw = input("Puerto [{}]: ".format(DEFAULT_PORT)).strip()
    port = int(port_raw) if port_raw else DEFAULT_PORT
    current = [90, 90, 90, 90]

    while True:
        print_menu(current)
        choice = input("> ").strip().lower()
        if choice == "q":
            break
        if choice == "u":
            self_update()
            continue
        if choice == "m":
            current = manual_pose(current)
        elif choice == "h":
            current = [90, 90, 90, 90]
        elif choice in POSES:
            current = POSES[choice][1][:]
        else:
            print("Opcion no valida.")
            continue

        command = build_command(current)
        print("Enviando:", command)
        try:
            reply = send_command(host, port, command)
            print("Respuesta:", reply or "(sin respuesta)")
        except Exception as exc:
            print("Error de conexion:", exc)
        time.sleep(0.2)


main()
