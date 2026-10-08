# Examples

Ready-to-use code for FIWARE Made Simple. All of it follows the [Smart Lamp MQTT contract](../docs/05-smart-lamp.md#mqtt-contract) and the default values of the [Postman collection](../postman/): `fiware-service` `smart`, `apikey` `TEF`, device `lamp001`, and entity `urn:ngsi-ld:Lamp:001`.

| Example | Layer | What it does |
|---|---|---|
| [esp32-smart-lamp](esp32-smart-lamp/) | IoT | ESP32 firmware: sends the LDR luminosity and runs the `on`/`off` commands with confirmation |
| [python-simulator](python-simulator/) | IoT | Same behavior as the firmware, without hardware |
| [dashboards](dashboards/) | Application | Web dashboard (Dash) and static chart (Matplotlib) of the STH-Comet history |
| [esp32-ntp](esp32-ntp/) | IoT | Date and time on the ESP32 over NTP, in the local time zone and in ISO 8601 UTC |

Before using any example, provision the device with folder **2** of the collection ([Getting started](../docs/04-getting-started.md)).

> [!IMPORTANT]
> **In a classroom**, each group must use its own `apikey` and `device_id`, both in the provisioning and in the example. See [Working in a classroom](../docs/04-getting-started.md#working-in-a-classroom).
