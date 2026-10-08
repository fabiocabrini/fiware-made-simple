# ESP32 · Date and time over NTP

Synchronizes the ESP32 clock with an NTP server and prints, every second, the local time and the UTC instant in ISO 8601 format, the same format used by Orion and STH-Comet:

```
Local: 2026-10-07 18:15:03  |  UTC (ISO 8601): 2026-10-07T22:15:03Z
```

The time zone is set in POSIX format with `configTzTime`. The default is `UTC0`; the code includes examples for New York, Los Angeles, London, Berlin, and São Paulo.

## When to use it

The IoT Agent already records when each measurement arrives (the `TimeInstant` attribute), so the Smart Lamp does not need NTP. It is useful when the device itself needs to know the time: scheduling actions, logging events locally, or showing the time on a display.

## How to flash

Open [`esp32_ntp/esp32_ntp.ino`](esp32_ntp/esp32_ntp.ino), set `WIFI_SSID`, `WIFI_PASSWORD` and, if you want, `NTP_SERVER` and `TIME_ZONE`, and flash it with the Arduino IDE (**DOIT ESP32 DEVKIT V1** board). No additional library is needed.
