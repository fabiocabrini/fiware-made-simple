# 2. Architecture

FIWARE Made Simple is organized into three layers. The **IoT** layer senses and acts on the physical world, the **Back-end** processes and stores the information, and the **Application** layer consumes and controls the data.

**On this page:** [Overview](#overview) · [Layers](#layers) · [Components](#components) · [Telemetry flow](#telemetry-flow) · [Command flow](#command-flow) · [Databases](#databases) · [Network and ports](#network-and-ports)

---

## Overview

<p align="center">
  <img src="img/architecture.svg" alt="FIWARE Made Simple architecture" width="100%">
</p>

**How to read the diagram:**

- Each arrow starts at **whoever initiates the connection**.
- The line style shows the protocol: solid for HTTP/NGSI-v2, dashed for MQTT, and dotted for MongoDB.
- Numbers (1–6) show the **telemetry** flow; letters (A–E) show the **command** flow.

## Layers

| Layer | Responsibility | Examples |
|---|---|---|
| **Application** | Consume information, present results, and make decisions | Dashboards, web and mobile apps, AI models, Postman |
| **Back-end** | Integrate devices, keep the current context, store the history | Orion, IoT Agent, STH-Comet, Mosquitto, MongoDB |
| **IoT** | Sense the environment and perform actions | ESP32, sensors, actuators, simulators |

The Application layer never talks to the devices directly: everything goes through Orion. That is what lets you replace a sensor, or its protocol, without changing the applications.

## Components

| Service | Image | Role |
|---|---|---|
| `orion` | `fiware/orion:4.5.0` | Context Broker: stores the **current state** of the entities and exposes the NGSI-v2 API |
| `iot-agent` | `fiware/iotagent-ul:3.7.0` | Translates UltraLight 2.0 (MQTT or HTTP) into NGSI-v2 and forwards commands |
| `sth-comet` | `telefonicaiot/fiware-sth-comet:2.11.0` | Receives notifications from Orion and stores the **history** |
| `mosquitto` | `eclipse-mosquitto:2.0.22` | MQTT broker between the devices and the IoT Agent |
| `mongo-db` | `mongo:8.0` | Database of Orion and the IoT Agent (context, subscriptions, devices) |
| `mongo-db-sth` | `mongo:8.0` | Dedicated history database, with authentication |

Orion, the IoT Agent, and STH-Comet are FIWARE **Generic Enablers**. Mosquitto and MongoDB are complementary third-party components.

## Telemetry flow

The path of a measurement, from the sensor to the chart:

| Step | From → To | What happens |
|---|---|---|
| **1** | ESP32 → Mosquitto | The device publishes `42` on the `/TEF/lamp001/attrs/l` topic (or `s\|on\|l\|42` on `/TEF/lamp001/attrs`) |
| **2** | Mosquitto → IoT Agent | The broker delivers the message to the IoT Agent, which subscribes to `/+/+/attrs` and `/+/+/attrs/+` |
| **3** | IoT Agent → Orion | The IoT Agent identifies the device by `apikey` + `device_id`, converts the value to the declared type, and updates `luminosity` in the entity |
| **4** | Orion → STH-Comet | The subscription triggers a notification to `http://sth-comet:8666/notify` |
| **5** | STH-Comet → MongoDB | The value is stored with the time it was received in the `sth_smart` database |
| **6** | Dashboard → STH-Comet | The application queries the history, for example the last 30 values |

Devices that do not use MQTT can send the same content over HTTP to port **7896** of the IoT Agent, skipping steps 1 and 2.

## Command flow

The path of an action, from the application to the actuator:

| Step | From → To | What happens |
|---|---|---|
| **A** | Application → Orion | `PATCH /v2/entities/urn:ngsi-ld:Lamp:001/attrs` with the `on` command |
| **B** | Orion → IoT Agent | The *registration* created during provisioning makes Orion forward the command |
| **C** | IoT Agent → Mosquitto → ESP32 | The IoT Agent publishes `lamp001@on\|` on `/TEF/lamp001/cmd`; the device turns the LED on |
| **D** | ESP32 → Mosquitto → IoT Agent | The device confirms on `/TEF/lamp001/cmdexe` with `lamp001@on\|ok` |
| **E** | IoT Agent → Orion | `on_status` changes from `PENDING` to `OK`, and `on_info` receives the response |

Without step D, the command reaches the device, but Orion never learns that it was executed, and `on_status` stays `PENDING` forever.

## Databases

The platform uses **two MongoDB instances**, with different roles and exposure levels:

| | `mongo-db` (context) | `mongo-db-sth` (history) |
|---|---|---|
| **Used by** | Orion and the IoT Agent | STH-Comet |
| **Contents** | Current state, subscriptions, registrations, service groups, devices | Time series and aggregations |
| **Databases** | `orion-<service>`, `iotagentul` | `sth_<service>` |
| **Authentication** | No | Yes (`sth` to write, `reader` to query) |
| **External access** | No: internal Docker network only | Yes: port 27017 |

Why two databases? The history is the data that researchers and students want to analyze with Python, Compass, or BI tools, so it is exposed with credentials and a read-only user. The operational data of Orion and the IoT Agent, which includes the device `apikeys`, stays isolated on the internal network, with no published port.

## Network and ports

The containers share the internal Docker network and reach each other by **service name**: `orion:1026`, `iot-agent:4041`, `sth-comet:8666`, `mosquitto:1883`, `mongo-db:27017`, and `mongo-db-sth:27017`. That is why the STH-Comet subscription uses `http://sth-comet:8666/notify` and not the server IP: the notification is sent by the Orion container.

Ports published on the host:

| Port | Service | Use |
|---|---|---|
| 1026 | Orion | NGSI-v2 API for the applications |
| 4041 | IoT Agent | Provisioning API |
| 7896 | IoT Agent | UltraLight measurements over HTTP |
| 8666 | STH-Comet | History queries |
| 1883 | Mosquitto | MQTT for the devices |
| 9001 | Mosquitto | MQTT over WebSocket (web applications) |
| 27017 | MongoDB (history) | Authenticated external access to the history |

---

[← 1. Concepts](01-concepts.md) · [Index](../README.md#documentation) · Next: [3. Requirements and installation →](03-installation.md)
