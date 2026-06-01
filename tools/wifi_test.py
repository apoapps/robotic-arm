#!/usr/bin/env python3
import argparse
import socket


def main():
    parser = argparse.ArgumentParser(description="Send a neutral command to the robot arm controller over Wi-Fi TCP.")
    parser.add_argument("--host", required=True, help="Robot IP, for example 192.168.4.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--command", default="<BUZZ,90,90,90,90,1000,1000,1000,1000>")
    args = parser.parse_args()

    with socket.create_connection((args.host, args.port), timeout=5) as conn:
        conn.sendall(args.command.encode("utf-8") + b"\n")
        print(conn.recv(256).decode("utf-8", "replace").strip())


if __name__ == "__main__":
    main()
