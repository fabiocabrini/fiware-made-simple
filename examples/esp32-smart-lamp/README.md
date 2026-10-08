# ESP32 firmware · Smart Lamp

Firmware for the **ESP32 DevKit V1** that measures luminosity with an LDR module and turns the onboard LED on and off through FIWARE commands. The circuit and the full MQTT contract are in [Smart Lamp PoC](../../docs/05-smart-lamp.md).

## Behavior

| Event | Publishing |
|---|---|
| When it connects to the broker | state (`s\|off`) and luminosity |
| Every 5 seconds | luminosity on `/TEF/lamp001/attrs/l` |
| When it receives `lamp001@on\|` or `lamp001@off\|` | turns the LED on/off, confirms on `/TEF/lamp001/cmdexe` (`lamp001@on\|ok`), and publishes the new state |
| Every 60 seconds | republishes the state, so Orion recovers if a message gets lost |

The main loop does not use `delay()`: the ESP32 handles commands immediately, even between two publications. If the broker connection drops, it tries to reconnect every 2 seconds.

## How to flash

1. Install the [Arduino IDE](https://www.arduino.cc/en/software) and ESP32 support: in *Preferences › Additional boards manager URLs*, add `https://espressif.github.io/arduino-esp32/package_esp32_index.json` and install **esp32 by Espressif Systems** in the *Boards Manager*.
2. Install the **PubSubClient** library (Nick O'Leary) in the *Library Manager*.
3. Open [`smart_lamp/smart_lamp.ino`](smart_lamp/smart_lamp.ino) and adjust the **Configuration** block:

   | Constant | Value |
   |---|---|
   | `WIFI_SSID`, `WIFI_PASSWORD` | Your Wi-Fi network (2.4 GHz) |
   | `MQTT_BROKER` | IP of the server running the platform |
   | `APIKEY`, `DEVICE_ID` | The same values used in provisioning (steps 2.1 and 2.3 of the collection) |
   | `MQTT_USER`, `MQTT_PASSWORD` | Only if Mosquitto requires authentication ([Security](../../docs/07-security.md#mosquitto-authentication)) |

4. Select the **DOIT ESP32 DEVKIT V1** board and the serial port, then click **Upload**.
5. Open the **Serial Monitor** at 115200 baud to follow the messages sent (`->`) and received (`<-`).

From the command line, with [arduino-cli](https://arduino.github.io/arduino-cli/):

```bash
arduino-cli compile --fqbn esp32:esp32:esp32doit-devkit-v1 smart_lamp
```

## Checking

- Request **3.2** of the collection: `luminosity` changes every 5 seconds.
- Requests **4.1** and **4.2**: the LED turns on and off.
- Request **4.3**: `on_status` and `off_status` show `OK`, and `on_info` shows `ok`.

> [!TIP]
> If the luminosity **goes up** when you cover the sensor, your LDR module has an inverted output. In `publishLuminosity()`, replace `map(reading, 0, 4095, 0, 100)` with `map(reading, 0, 4095, 100, 0)`.
