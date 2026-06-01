#!/usr/bin/env python3
import argparse
import time

import serial


def main():
    parser = argparse.ArgumentParser(description="Send a neutral command to the robot arm controller over USB serial.")
    parser.add_argument("--port", required=True, help="Serial port, for example /dev/tty.usbmodem1101")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--command", default="<BUZZ,90,90,90,90,1000,1000,1000,1000>")
    args = parser.parse_args()

    with serial.Serial(args.port, args.baud, timeout=3) as conn:
        time.sleep(2)
        conn.reset_input_buffer()
        conn.write(args.command.encode("utf-8") + b"\n")
        conn.flush()
        print(conn.readline().decode("utf-8", "replace").strip())


if __name__ == "__main__":
    main()
