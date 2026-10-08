#!/usr/bin/env python3
"""Smart Lamp simulator for FIWARE Made Simple.

Reproduces the behavior of the ESP32 firmware (examples/esp32-smart-lamp):
publishes the luminosity periodically, publishes the LED state when it changes,
and answers the on/off commands with a confirmation on /cmdexe.

Usage:
    python smart_lamp_simulator.py --broker SERVER_IP
    python smart_lamp_simulator.py --broker SERVER_IP --apikey G1KEY --device-id lamp001 --interval 2
"""
import argparse
import os
import random
import sys
import time
import uuid

import paho.mqtt.client as mqtt


def parse_args():
    p = argparse.ArgumentParser(description="Smart Lamp simulator (UltraLight 2.0 over MQTT)")
    p.add_argument("--broker", default=os.getenv("FIWARE_HOST"),
                   help="IP address or name of the FIWARE server (or the FIWARE_HOST variable)")
    p.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    p.add_argument("--apikey", default=os.getenv("APIKEY", "TEF"))
    p.add_argument("--device-id", default=os.getenv("DEVICE_ID", "lamp001"))
    p.add_argument("--interval", type=float, default=5.0, help="seconds between luminosity messages")
    p.add_argument("--user", default=os.getenv("MQTT_USER"), help="MQTT user, if the broker requires one")
    p.add_argument("--password", default=os.getenv("MQTT_PASSWORD"))
    args = p.parse_args()
    if not args.broker:
        p.error("set the server with --broker or with the FIWARE_HOST variable")
    return args


class SmartLamp:
    STATE_REPUBLISH_S = 60

    def __init__(self, args):
        self.device_id = args.device_id
        base = f"/{args.apikey}/{args.device_id}"
        self.attrs_topic = f"{base}/attrs"
        self.luminosity_topic = f"{base}/attrs/l"
        self.cmd_topic = f"{base}/cmd"
        self.cmdexe_topic = f"{base}/cmdexe"

        self.led_on = False
        self.luminosity = 50.0
        self.last_state = 0.0

        # Unique client ID: two clients with the same ID keep kicking each other off the broker
        client_id = f"sim-{args.device_id}-{uuid.uuid4().hex[:6]}"
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        if args.user:
            self.client.username_pw_set(args.user, args.password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    # ------------------------------------------------------------- MQTT
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"Could not connect to the broker: {reason_code}")
            return
        print("Connected to the broker")
        client.subscribe(self.cmd_topic)
        self.publish_state()
        self.publish_luminosity()

    def on_message(self, client, userdata, msg):
        message = msg.payload.decode("utf-8", errors="replace")
        print(f"<- {msg.topic} {message}")

        # UltraLight 2.0 format: <device_id>@<command>|<parameters>
        device, _, rest = message.partition("@")
        command = rest.split("|", 1)[0]
        if device != self.device_id:
            return

        if command in ("on", "off"):
            self.led_on = command == "on"
            print(f"   [LED] {'ON' if self.led_on else 'OFF'}")
            self.confirm(command, "ok")
            self.publish_state()
        else:
            self.confirm(command, "unknown command")

    # ------------------------------------------------------------- publishing
    def publish(self, topic, message):
        self.client.publish(topic, message)
        print(f"-> {topic} {message}")

    def publish_state(self):
        self.publish(self.attrs_topic, f"s|{'on' if self.led_on else 'off'}")
        self.last_state = time.monotonic()

    def publish_luminosity(self):
        # Random walk: changes smoothly between 0 and 100, like the light in a room
        self.luminosity = min(100.0, max(0.0, self.luminosity + random.uniform(-6, 6)))
        self.publish(self.luminosity_topic, str(round(self.luminosity)))

    def confirm(self, command, result):
        self.publish(self.cmdexe_topic, f"{self.device_id}@{command}|{result}")

    # ------------------------------------------------------------- main loop
    def run(self, broker, port, interval):
        print(f"Simulating {self.device_id} on {broker}:{port} (Ctrl+C to stop)")
        try:
            self.client.connect(broker, port, keepalive=60)
        except OSError as error:
            sys.exit(f"Could not connect to {broker}:{port}: {error}")

        self.client.loop_start()
        next_publish = time.monotonic() + interval
        try:
            while True:
                time.sleep(0.2)
                now = time.monotonic()
                if not self.client.is_connected():
                    continue
                if now >= next_publish:
                    next_publish = now + interval
                    self.publish_luminosity()
                if now - self.last_state >= self.STATE_REPUBLISH_S:
                    self.publish_state()
        except KeyboardInterrupt:
            print("\nStopping the simulator...")
        finally:
            self.client.loop_stop()
            self.client.disconnect()


if __name__ == "__main__":
    args = parse_args()
    SmartLamp(args).run(args.broker, args.port, args.interval)
