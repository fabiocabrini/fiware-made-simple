# Python simulator · Smart Lamp

Simulates the Smart Lamp without hardware, with the same behavior as the [ESP32 firmware](../esp32-smart-lamp/):
- sends the luminosity periodically;
- publishes the LED state when it changes;
- confirms the `on`/`off` commands on `/cmdexe`.

The luminosity changes smoothly, like the light in a room, which produces realistic charts in the history.

## Installation

Requires Python 3.9 or later. On Ubuntu and Debian, first install virtual environment support with `sudo apt install python3-venv`.

```bash
python3 -m venv .venv            # Windows: py -m venv .venv
```
```bash
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```
```bash
pip install -r requirements.txt
```

## Usage

```bash
python smart_lamp_simulator.py --broker SERVER_IP
```

| Option | Default | Description |
|---|---|---|
| `--broker` | `FIWARE_HOST` variable | IP address or name of the server |
| `--port` | `1883` | MQTT port |
| `--apikey` | `TEF` | Service group `apikey` |
| `--device-id` | `lamp001` | Provisioned `device_id` |
| `--interval` | `5` | Seconds between luminosity messages |
| `--user`, `--password` | | Credentials, if Mosquitto requires authentication |

Sample output when a command arrives:

```
-> /TEF/lamp001/attrs/l 47
<- /TEF/lamp001/cmd lamp001@on|
   [LED] ON
-> /TEF/lamp001/cmdexe lamp001@on|ok
-> /TEF/lamp001/attrs s|on
```

Stop it with `Ctrl+C`.

> [!TIP]
> To simulate several devices, provision one device for each and open one terminal per simulator, each with its own `--device-id`.
