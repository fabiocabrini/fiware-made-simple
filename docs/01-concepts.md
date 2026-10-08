# 1. Concepts

Before using the platform, it helps to understand the FIWARE vocabulary. This chapter introduces the concepts that appear throughout the rest of the documentation.

**On this page:** [FIWARE](#fiware) · [Context and NGSI-v2](#context-and-ngsi-v2) · [Entities and attributes](#entities-and-attributes) · [Multi-tenancy](#multi-tenancy-fiware-service-and-fiware-servicepath) · [IoT Agent](#iot-agent) · [Subscriptions and registrations](#subscriptions-and-registrations) · [History](#current-state-versus-history) · [Smart Data Models](#smart-data-models-and-ngsi-ld)

---

## FIWARE

[FIWARE](https://www.fiware.org/) is an open ecosystem, maintained by the FIWARE Foundation, for building smart solutions: cities, industry, agriculture, energy, and health. It is made of **Generic Enablers (GEs)**, reusable open-source components, each with a well-defined responsibility and all talking through a standard API.

The central component is the **Context Broker**. The other GEs connect to it to bring in device data (IoT Agents), keep history (STH-Comet, Cygnus, QuantumLeap), enforce security (Keyrock, Wilma), and so on.

## Context and NGSI-v2

In FIWARE, **context** is the set of information that describes the current state of the world an application cares about: the luminosity of a room, the position of a bus, the state of a lamp.

Context is handled through the **NGSI-v2** API (*Next Generation Service Interface*), a REST API with JSON. With it, applications create, query, update, and delete context information, and subscribe to notifications when something changes.

> [!NOTE]
> There is also **NGSI-LD**, the evolution standardized by ETSI and based on *Linked Data*. FIWARE Made Simple uses NGSI-v2, which is simpler for a first contact and still widely adopted. The concepts you learn here carry over directly to NGSI-LD.

## Entities and attributes

All context information is organized into **entities**. Each entity has a unique `id`, a `type`, and a set of **attributes**, and each attribute has a `type` and a `value`:

```json
{
  "id": "urn:ngsi-ld:Lamp:001",
  "type": "Lamp",
  "luminosity": { "type": "Integer", "value": 42 },
  "state":      { "type": "Text",    "value": "on" }
}
```

The `urn:ngsi-ld:<Type>:<identifier>` format for the `id` is a recommended convention that makes a future migration to NGSI-LD easier.

To consume data in applications, the `options=keyValues` parameter returns the simplified form, with names and values only: `{"id": "...", "luminosity": 42, "state": "on"}`.

## Multi-tenancy: `fiware-service` and `fiware-servicepath`

A single platform can serve several projects isolated from one another. Every request carries two headers:

| Header | Meaning | Example |
|---|---|---|
| `fiware-service` | **Tenant**: fully isolates the data (it becomes a separate database in MongoDB) | `smart` |
| `fiware-servicepath` | Hierarchical subdivision inside the tenant | `/` or `/building1/floor2` |

Entities created in one `fiware-service` do not show up in another. In a classroom, each group can use its own `fiware-service`.

## IoT Agent

Devices rarely speak NGSI-v2: they are limited in memory and power and use lightweight protocols such as MQTT. The **IoT Agent** bridges both directions:

- **From the device to Orion (southbound → northbound):** it receives compact measurements, such as `l|42`, and turns them into NGSI-v2 updates of an entity.
- **From Orion to the device (northbound → southbound):** it receives commands sent to Orion and delivers them to the device, for example `lamp001@on|`.

FIWARE Made Simple uses the **IoT Agent UltraLight 2.0**, which understands the text format `object|value|object|value` over MQTT or HTTP. Before sending data, a device must be **provisioned** at two levels:

| Concept | What it defines | How many |
|---|---|---|
| **Service group** | The group `apikey` and the default entity type | One per project or student group. The `apikey` is unique across the whole platform |
| **Device** | The `device_id`, the matching entity, its attributes, and its commands | One per physical device |

The `apikey` and the `device_id` form the device address in the MQTT topics: `/<apikey>/<device_id>/attrs`.

## Subscriptions and registrations

These are the two mechanisms that make information flow automatically from Orion:

- **Subscription**: "when attribute X of entity Y changes, **notify** URL Z". This is how STH-Comet receives each new measurement to store in the history.
- **Registration**: "attribute X of entity Y is **provided** by another component". The IoT Agent registers the commands (`on`, `off`) in Orion; when an application changes a command, Orion forwards the request to the IoT Agent, which delivers it to the device.

## Current state versus history

**Orion keeps only the latest value** of each attribute. When a new measurement arrives, the previous value is overwritten.

Analyses over time require a history component. Here, **STH-Comet** (*Short Time Historic*) receives notifications from Orion and stores a time series, with queries by count, by period, and with aggregations (minimum, maximum, sum). For long-term retention and large volumes, FIWARE offers alternatives such as **QuantumLeap** and **Cygnus**.

## Smart Data Models and NGSI-LD

[**Smart Data Models**](https://smartdatamodels.org/) are open, standardized data models for hundreds of domains: parking, air quality, street lighting, irrigation. Using an existing model instead of inventing attributes makes a solution **interoperable**: any other application that knows the model understands your data without adaptation.

The initiative is linked to the **MIMs** (*Minimal Interoperability Mechanisms*) of [Open & Agile Smart Cities](https://oascities.org/minimal-interoperability-mechanisms/), adopted by cities in many countries as the technical basis for procuring urban data platforms.

## Learn more

- [Official FIWARE tutorials](https://fiware-tutorials.readthedocs.io/)
- [NGSI-v2 API specification in Orion](https://fiware-orion.readthedocs.io/en/master/orion-api.html)
- [IoT Agent UltraLight documentation](https://fiware-iotagent-ul.readthedocs.io/)
- [Smart Data Models repository](https://github.com/smart-data-models)

---

[Index](../README.md#documentation) · Next: [2. Architecture →](02-architecture.md)
