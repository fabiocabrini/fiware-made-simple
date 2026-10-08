# 4. Getting started

This guided path uses the **Postman collection** to walk through the whole platform: create entities, provision the Smart Lamp, send measurements, trigger commands, and query the history. No hardware is needed.

**On this page:** [Import the collection](#import-the-collection) · [Set the variables](#set-the-variables) · [Guided path](#guided-path) · [Working in a classroom](#working-in-a-classroom) · [Run everything at once](#run-everything-at-once)

---

## Import the collection

1. Install [Postman](https://www.postman.com/downloads/).
2. Click **Import** and select the [`postman/FIWARE Made Simple.postman_collection.json`](../postman/) file.
3. The collection appears in the sidebar, organized in folders numbered 0 to 6.

Each request explains what it does and why in its **Docs** tab.

> [!TIP]
> Use **Postman Desktop**. The web version of Postman only reaches `localhost` or local network IPs through the [Postman Desktop Agent](https://learning.postman.com/docs/getting-started/basics/about-postman-agent/); without it, requests fail with a connection error.

## Set the variables

Open the collection, go to the **Variables** tab, and set at least `url`:

| Variable | Default value | Meaning |
|---|---|---|
| `url` | `localhost` | IP address or name of the server running the platform |
| `service` | `smart` | `fiware-service` (tenant) |
| `servicepath` | `/` | `fiware-servicepath` |
| `apikey` | `TEF` | Service group API key, used in the MQTT topics |
| `device_id` | `lamp001` | Device identifier |
| `entity_id` | `urn:ngsi-ld:Lamp:001` | Entity id in Orion |
| `entity_type` | `Lamp` | Entity type |
| `sth_notify_url` | `http://sth-comet:8666/notify` | **Internal** URL that Orion uses to notify STH-Comet. Do not change it |
| `lastN` | `30` | Number of values returned by the history (maximum 100) |
| `subscription_id` | *(automatic)* | Filled in when the subscription is created |

## Guided path

| Folder | Run it | Goal |
|---|---|---|
| **0. Health Check** | Every time you start | Confirm that Orion, the IoT Agent, and STH-Comet are up |
| **1. Orion Context Broker** | Optional | Practice NGSI-v2: create, query, filter, update, and delete an entity |
| **2. Provisioning** | **Only once** | Create the service group, provision the Smart Lamp, and create the history subscription |
| **3. Simulate the device** | As often as you like | Send random measurements over HTTP, as if it were the ESP32 |
| **4. Commands** | As often as you like | Turn the lamp on and off and follow the execution status |
| **5. History** | After a few measurements | Query the latest values, a period, and aggregations |
| **6. Cleanup** | When you are done | Remove the subscription, history, device, entity, and service group |

### What to look for at each step

- **After 2.1 (service group):** the group is created with `autoprovision: false`. Messages from devices that are not provisioned yet are discarded, so it does not matter if the ESP32 is already on.
- **After 2.3 (provisioning):** request 2.5 shows the *registration* that the IoT Agent created by itself in Orion. It is what makes the commands reach the device.
- **After 3.1 (measurement):** in 3.2, `luminosity` shows up as a **number**, not text. The IoT Agent converts the value according to the `Integer` type declared during provisioning.
- **After 4.1 (turn on):** in 4.3, `on_status` stays `PENDING`. Without a real device to confirm the execution, it stays that way. With the ESP32, it changes to `OK` (see [Smart Lamp PoC](05-smart-lamp.md)).
- **After several measurements:** in 5.1, the subscription `timesSent` field grows with every notification, and `lastSuccessCode` should be `200`.

> [!TIP]
> The creation requests (2.1, 2.3, and 2.6) **should not be repeated**. Repeating 2.1 or 2.3 returns `409 Conflict`. Repeating 2.6 creates a second subscription, and every measurement is then stored twice in the history.

## Working in a classroom

When several students share the same server, **each group must use its own `service` and its own `apikey`**. The `device_id` and the `entity_id` can be the same across groups:

| Group | `service` | `apikey` | `device_id` | `entity_id` |
|---|---|---|---|---|
| 1 | `group1` | `G1KEY` | `lamp001` | `urn:ngsi-ld:Lamp:001` |
| 2 | `group2` | `G2KEY` | `lamp001` | `urn:ngsi-ld:Lamp:001` |

Each group uses the same values in its firmware or simulator (`APIKEY` and `DEVICE_ID`).

> [!IMPORTANT]
> Device MQTT and HTTP messages do not carry the `fiware-service`: the IoT Agent finds the group **by the `apikey`**. That is why the `apikey` is unique across the whole platform. If step 2.1 returns **`409`** in a new `service`, another group already uses that `apikey`: choose another one.

## Run everything at once

Postman's **Run collection** button runs all the folders in sequence and shows the result of the automated tests of each request. You can do the same from the command line with [Newman](https://github.com/postmanlabs/newman), without installing Node.js:

```bash
docker run --rm --network host -v "$PWD/postman:/etc/newman" postman/newman:6-alpine run "FIWARE Made Simple.postman_collection.json" --env-var service=test --env-var apikey=TEST --delay-request 300
```

The command uses `service=test` and `apikey=TEST` so it does not touch your data. The `--network host` option works on Linux; on macOS and Windows, replace it with `--env-var url=host.docker.internal`.

---

[← 3. Requirements and installation](03-installation.md) · [Index](../README.md#documentation) · Next: [5. Smart Lamp PoC →](05-smart-lamp.md)
