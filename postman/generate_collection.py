"""Generates the FIWARE Made Simple Postman collection (v2.1).

Edit this file, not the JSON, to change the collection. Then regenerate it:
    python3 postman/generate_collection.py "postman/FIWARE Made Simple.postman_collection.json"
"""
import json
import sys
import uuid

FW = [
    {"key": "fiware-service", "value": "{{service}}"},
    {"key": "fiware-servicepath", "value": "{{servicepath}}"},
]
JSON_CT = [{"key": "Content-Type", "value": "application/json"}]


def test(*lines):
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": list(lines)}}]


def status(code):
    return f'pm.test("Status {code}", () => pm.response.to.have.status({code}));'


def req(name, method, url, desc, headers=None, body=None, tests=None, raw_type="json", prerequest=None):
    r = {
        "name": name,
        "request": {
            "method": method,
            "header": list(headers or []),
            "url": url,
            "description": desc.strip(),
        },
    }
    if body is not None:
        if raw_type == "json":
            raw = json.dumps(body, indent=2, ensure_ascii=False) if not isinstance(body, str) else body
            r["request"]["body"] = {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}
        else:
            r["request"]["body"] = {"mode": "raw", "raw": body, "options": {"raw": {"language": "text"}}}
    events = []
    if prerequest:
        events.append({"listen": "prerequest", "script": {"type": "text/javascript", "exec": prerequest}})
    if tests:
        events += test(*tests)
    if events:
        r["event"] = events
    return r


def folder(name, desc, items):
    return {"name": name, "description": desc.strip(), "item": items}


ORION = "http://{{url}}:1026"
IOTA = "http://{{url}}:4041"
IOTA_HTTP = "http://{{url}}:7896"
STH = "http://{{url}}:8666"
STH_ATTR = STH + "/STH/v1/contextEntities/type/{{entity_type}}/id/{{entity_id}}/attributes/luminosity"

# ---------------------------------------------------------------------------
health = folder("0. Health Check", """
Checks that the platform components are up. Run it before you start.
""", [
    req("0.1 Orion Context Broker version", "GET", ORION + "/version",
        "Returns the version and build information of the Orion Context Broker (port 1026).",
        tests=[status(200), 'pm.test("Orion responded", () => pm.expect(pm.response.json().orion.version).to.be.a("string"));']),
    req("0.2 IoT Agent UltraLight version", "GET", IOTA + "/iot/about",
        "Returns the version of the IoT Agent UltraLight 2.0 (provisioning API, port 4041).",
        tests=[status(200)]),
    req("0.3 STH-Comet version", "GET", STH + "/version",
        "Returns the version of STH-Comet (short-term history, port 8666).",
        tests=[status(200)]),
])

# ---------------------------------------------------------------------------
sensor = "urn:ngsi-ld:Sensor:001"
orion = folder("1. Orion Context Broker (NGSI-v2)", f"""
Basic operations on entities directly in Orion, with no physical device.

Orion stores only the **current state** of each entity. The history lives in STH-Comet (folder 5).

Every request uses the `fiware-service` header (tenant, which becomes the `orion-<service>` database in MongoDB) and the `fiware-servicepath` header (a subdivision inside the tenant).
""", [
    req("1.1 Create entity", "POST", ORION + "/v2/entities",
        f"""Creates the entity `{sensor}` of type `Sensor` with the `temperature` and `humidity` attributes.

In NGSI-v2 every attribute has a `type` and a `value`. Use the `Number` type for numbers.""",
        headers=JSON_CT + FW,
        body={"id": sensor, "type": "Sensor",
              "temperature": {"type": "Number", "value": 23.5},
              "humidity": {"type": "Number", "value": 60}},
        tests=[status(201)]),
    req("1.2 List entities", "GET", ORION + "/v2/entities",
        "Lists all the entities of the given `fiware-service` (20 by default; use `?limit=` and `?offset=` to paginate).",
        headers=FW, tests=[status(200)]),
    req("1.3 Get entity (keyValues)", "GET", ORION + f"/v2/entities/{sensor}?options=keyValues",
        "Returns the entity in the simplified `keyValues` format (name: value only), which is easier to consume in applications.",
        headers=FW,
        tests=[status(200), 'pm.test("temperature present", () => pm.expect(pm.response.json()).to.have.property("temperature"));']),
    req("1.4 Update attributes (PATCH)", "PATCH", ORION + f"/v2/entities/{sensor}/attrs",
        "Updates **existing** attributes. PATCH fails if an attribute does not exist; to add new attributes, use `POST /attrs`.",
        headers=JSON_CT + FW,
        body={"temperature": {"type": "Number", "value": 35},
              "humidity": {"type": "Number", "value": 40}},
        tests=[status(204)]),
    req("1.5 Update a single attribute value", "PUT", ORION + f"/v2/entities/{sensor}/attrs/temperature/value",
        "Replaces only the value of `temperature`. The body is the raw value, sent with `Content-Type: text/plain`.",
        headers=[{"key": "Content-Type", "value": "text/plain"}] + FW,
        body="38", raw_type="text", tests=[status(204)]),
    req("1.6 Filter entities (q)", "GET", ORION + "/v2/entities?type=Sensor&q=temperature>30&options=keyValues",
        "Filtered query: entities of type `Sensor` with `temperature` greater than 30. Other operators: `==`, `!=`, `<`, `<=`, `>=`, `..` (range), and `;` (logical AND).",
        headers=FW,
        tests=[status(200), 'pm.test("filter returned the entity", () => pm.expect(pm.response.json().length).to.be.above(0));']),
    req("1.7 Delete entity", "DELETE", ORION + f"/v2/entities/{sensor}",
        "Deletes the sample entity.", headers=FW, tests=[status(204)]),
])

# ---------------------------------------------------------------------------
NOTIFY = {
    "description": "Notify STH-Comet of all luminosity changes",
    "subject": {
        "entities": [{"id": "{{entity_id}}", "type": "{{entity_type}}"}],
        "condition": {"attrs": ["luminosity"]},
    },
    "notification": {
        "httpCustom": {
            "url": "{{sth_notify_url}}",
            "json": {
                "contextResponses": [{
                    "contextElement": {
                        "id": "${id}",
                        "type": "${type}",
                        "isPattern": "false",
                        "attributes": [{"name": "luminosity", "type": "Integer", "value": "${luminosity}"}],
                    },
                    "statusCode": {"code": "200", "reasonPhrase": "OK"},
                }]
            },
        },
        "attrs": ["luminosity"],
    },
}
provisioning = folder("2. Provisioning (run once)", """
The IoT Agent UltraLight 2.0 translates device messages (MQTT or HTTP) into NGSI-v2 in Orion and forwards Orion commands to the devices.

Order: create the **service group** once per `fiware-service`, provision each **device**, and create the **subscription** that feeds the history in STH-Comet.
""", [
    req("2.1 Create service group", "POST", IOTA + "/iot/services",
        """Creates the service group with the API key `{{apikey}}`.

- `apikey`: identifies the group in the MQTT topics (`/<apikey>/<device_id>/attrs`).
- `resource`: path used by HTTP measurements (port 7896). It must be `/iot/d`.
- `entity_type`: default type of the entities created for the devices of this group.
- `autoprovision: false`: messages from devices that are **not provisioned** are discarded. Without it, a device that is powered on before step 2.3 makes the IoT Agent create a "ghost" device with the wrong entity name, and provisioning starts to fail.

The `apikey` is unique across the whole platform: if another group already uses it, even in another `fiware-service`, this step returns 409. Choose another `apikey`.

There is no need to set `cbroker`: the IoT Agent already knows Orion through the `IOTA_CB_HOST` variable in docker-compose.

Run it **only once**: running it again returns 409 (`DUPLICATE_GROUP`).""",
        headers=JSON_CT + FW,
        body={"services": [{"apikey": "{{apikey}}", "resource": "/iot/d", "entity_type": "{{entity_type}}",
                            "autoprovision": False}]},
        tests=[status(201)]),
    req("2.2 List service groups", "GET", IOTA + "/iot/services",
        "Lists the service groups of the `fiware-service`.", headers=FW,
        tests=[status(200), 'pm.test("at least one group exists", () => pm.expect(pm.response.json().count).to.be.above(0));']),
    req("2.3 Provision the Smart Lamp", "POST", IOTA + "/iot/devices",
        """Provisions the device `{{device_id}}`, which becomes the entity `{{entity_id}}` in Orion.

- `apikey`: **required**. Without it, IoT Agent 3.x does not match measurements to this device.
- `transport`: `MQTT` makes commands go through the MQTT broker.
- `commands`: accepted commands (`on`, `off`). The IoT Agent automatically creates in Orion the *registration* that forwards the commands to it; there is no manual step.
- `attributes`: maps the short `object_id` sent by the device (`s`, `l`) to the attribute name in Orion (`state`, `luminosity`).""",
        headers=JSON_CT + FW,
        body={"devices": [{
            "device_id": "{{device_id}}",
            "apikey": "{{apikey}}",
            "entity_name": "{{entity_id}}",
            "entity_type": "{{entity_type}}",
            "protocol": "PDI-IoTA-UltraLight",
            "transport": "MQTT",
            "commands": [{"name": "on", "type": "command"}, {"name": "off", "type": "command"}],
            "attributes": [{"object_id": "s", "name": "state", "type": "Text"},
                           {"object_id": "l", "name": "luminosity", "type": "Integer"}],
        }]},
        tests=[status(201)]),
    req("2.4 List devices", "GET", IOTA + "/iot/devices",
        "Lists the devices provisioned in the `fiware-service`.", headers=FW,
        tests=[status(200), 'pm.test("device provisioned", () => pm.expect(pm.response.json().devices.map(d => d.device_id)).to.include(pm.variables.get("device_id")));']),
    req("2.5 Get the command registration", "GET", ORION + "/v2/registrations",
        "Shows the registration created automatically by the IoT Agent: it is what makes Orion forward the `on`/`off` commands to the IoT Agent.",
        headers=FW,
        tests=[status(200), 'pm.test("registration created by the IoT Agent", () => pm.expect(JSON.stringify(pm.response.json())).to.include(pm.variables.get("entity_id")));']),
    req("2.6 Create subscription to STH-Comet", "POST", ORION + "/v2/subscriptions",
        """Notifies STH-Comet of every change of `luminosity`.

**Why `httpCustom`?** STH-Comet only understands notifications in the old NGSIv1 format, and Orion 4.x removed `"attrsFormat": "legacy"`. With `httpCustom` the NGSIv1 payload is built explicitly; Orion replaces `${id}`, `${type}`, and `${luminosity}` with the real values (Postman leaves them alone, because its variables use double braces).

**Internal URL:** `{{sth_notify_url}}` (`http://sth-comet:8666/notify`). The notification is sent by the Orion container, which reaches STH-Comet by its service name on the Docker network. Do not use the public IP.

To store another attribute (for example, `state`), create **another subscription** with the same body, replacing `luminosity` with the new attribute. Do not put two attributes in the same subscription: every notification would carry both, and an attribute that did not change would be stored again, duplicated.

Run it **only once**: each run creates a new subscription, and the history starts receiving duplicated values.""",
        headers=JSON_CT + FW, body=NOTIFY,
        tests=[status(201),
               'const loc = pm.response.headers.get("Location");',
               'if (loc) pm.collectionVariables.set("subscription_id", loc.split("/").pop());']),
])

# ---------------------------------------------------------------------------
simulate = folder("3. Simulate the device (no hardware)", """
Sends measurements as if it were the ESP32, using the HTTP interface of the IoT Agent (port 7896).

The real ESP32 publishes the same content over MQTT:
- `/<apikey>/<device_id>/attrs` with `s|on|l|42` (several attributes), or
- `/<apikey>/<device_id>/attrs/l` with `42` (a single attribute).
""", [
    req("3.1 Send measurement (UltraLight over HTTP)", "POST", IOTA_HTTP + "/iot/d?k={{apikey}}&i={{device_id}}",
        """Sends `state` and a random `luminosity` (0 to 100) in the UltraLight 2.0 format: `object|value|object|value`.

Run it several times to build up history in STH-Comet (the subscription from step 2.6 must exist).""",
        headers=[{"key": "Content-Type", "value": "text/plain"}],
        body="s|off|l|{{luminosity}}", raw_type="text",
        prerequest=['pm.variables.set("luminosity", Math.floor(Math.random() * 101));'],
        tests=[status(200)]),
    req("3.2 Read luminosity in Orion", "GET", ORION + "/v2/entities/{{entity_id}}/attrs/luminosity",
        "Reads the current value of `luminosity` in Orion.", headers=FW + [{"key": "Accept", "value": "application/json"}],
        tests=[status(200), 'pm.test("luminosity is a number", () => pm.expect(pm.response.json().value).to.be.a("number"));']),
    req("3.3 Read state in Orion", "GET", ORION + "/v2/entities/{{entity_id}}/attrs/state",
        "Reads the current value of `state` (LED state reported by the device).",
        headers=FW + [{"key": "Accept", "value": "application/json"}],
        tests=[status(200)]),
])

# ---------------------------------------------------------------------------
commands = folder("4. Commands", """
Commands follow this path: application → Orion → (registration) → IoT Agent → MQTT `/<apikey>/<device_id>/cmd` → device.

The device must confirm by publishing on `/<apikey>/<device_id>/cmdexe` (for example, `lamp001@on|ok`). Until it confirms, `on_status` stays `PENDING`; then it becomes `OK` and `on_info` receives the text sent.
""", [
    req("4.1 Turn the Smart Lamp on", "PATCH", ORION + "/v2/entities/{{entity_id}}/attrs",
        "Sends the `on` command. The device receives the message `{{device_id}}@on|` on the `/{{apikey}}/{{device_id}}/cmd` topic.",
        headers=JSON_CT + FW, body={"on": {"type": "command", "value": ""}}, tests=[status(204)]),
    req("4.2 Turn the Smart Lamp off", "PATCH", ORION + "/v2/entities/{{entity_id}}/attrs",
        "Sends the `off` command. The device receives `{{device_id}}@off|`.",
        headers=JSON_CT + FW, body={"off": {"type": "command", "value": ""}}, tests=[status(204)]),
    req("4.3 Check command status", "GET", ORION + "/v2/entities/{{entity_id}}?attrs=on_status,on_info,off_status,off_info&options=keyValues",
        "Shows the execution status of the commands: `PENDING` (waiting for the device), `OK` (confirmed via `cmdexe`), or `ERROR`.",
        headers=FW,
        tests=[status(200), 'pm.test("command status present", () => pm.expect(pm.response.json()).to.have.property("on_status"));']),
])

# ---------------------------------------------------------------------------
history = folder("5. History (STH-Comet)", """
STH-Comet builds the history from **notifications** sent by Orion. The subscription tells Orion: "when `luminosity` changes, let STH-Comet know".

The subscription is created in step 2.6; here you follow the notifications and query the history.
""", [
    req("5.1 List subscriptions", "GET", ORION + "/v2/subscriptions",
        "Lists the subscriptions. Under `notification`, check `timesSent` (notifications sent), `lastSuccessCode` (should be 200), and `lastFailureReason` (reason for the last failure).",
        headers=FW,
        tests=[status(200),
               'const s = pm.response.json().find(s => s.id === pm.collectionVariables.get("subscription_id"));',
               'if (s) pm.test("subscription active", () => pm.expect(s.status).to.eql("active"));']),
    req("5.2 History: last N values", "GET", STH_ATTR + "?lastN={{lastN}}",
        "Returns the last `{{lastN}}` raw values of `luminosity` (maximum 100) with the time they were received (`recvTime`, in UTC).",
        headers=FW,
        tests=[status(200),
               'const values = pm.response.json().contextResponses[0].contextElement.attributes[0].values;',
               'pm.test("history has values", () => pm.expect(values.length).to.be.above(0));']),
    req("5.3 History: paginated by period", "GET", STH_ATTR + "?hLimit=100&hOffset=0&dateFrom={{dateFrom}}",
        """Values since `dateFrom` (ISO 8601, UTC), in pages of `hLimit` items (maximum 100) starting at `hOffset`. Use `dateTo` to set the end of the period.

The pre-request script sets `dateFrom` to one hour ago.""",
        headers=FW,
        prerequest=['pm.variables.set("dateFrom", new Date(Date.now() - 3600 * 1000).toISOString());'],
        tests=[status(200)]),
    req("5.4 Aggregated history (maximum per minute)", "GET", STH_ATTR + "?aggrMethod=max&aggrPeriod=minute",
        """Aggregation computed by STH-Comet for numeric attributes.

- `aggrMethod`: `max`, `min`, `sum`, `sum2`, or `occur` (count of text values).
- `aggrPeriod`: `minute`, `hour`, or `day` (the resolutions computed by default).""",
        headers=FW, tests=[status(200)]),
])

# ---------------------------------------------------------------------------
cleanup = folder("6. Cleanup", """
Removes everything that was created, in reverse order. Careful: it deletes the data of the configured `fiware-service`.
""", [
    req("6.1 Delete subscription", "DELETE", ORION + "/v2/subscriptions/{{subscription_id}}",
        "Deletes the subscription created in 2.6 (its id was saved automatically in the `subscription_id` variable). If needed, copy the id from 5.1.",
        headers=FW, tests=[status(204)]),
    req("6.2 Delete history in STH-Comet", "DELETE",
        STH + "/STH/v1/contextEntities/type/{{entity_type}}/id/{{entity_id}}",
        "Deletes the whole history of the entity in STH-Comet.", headers=FW, tests=[status(204)]),
    req("6.3 Delete device in the IoT Agent", "DELETE", IOTA + "/iot/devices/{{device_id}}",
        "Removes the device from the IoT Agent. The entity in Orion still exists (step 6.4).",
        headers=FW, tests=[status(204)]),
    req("6.4 Delete entity in Orion", "DELETE", ORION + "/v2/entities/{{entity_id}}",
        "Removes the Smart Lamp entity from Orion.", headers=FW, tests=[status(204)]),
    req("6.5 Delete service group", "DELETE", IOTA + "/iot/services/?resource=/iot/d&apikey={{apikey}}",
        "Removes the service group. Do this only if no other device uses this API key.",
        headers=FW, tests=[status(204)]),
])

collection = {
    "info": {
        "_postman_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "github.com/fabiocabrini/fiware-made-simple/postman")),
        "name": "FIWARE Made Simple",
        "description": """Collection of **FIWARE Made Simple** (https://github.com/fabiocabrini/fiware-made-simple) for the Smart Lamp PoC.

**Before you start:** in the *Variables* tab of this collection, set `url` to the IP address or name of the server where the platform is running.

**Suggested path:**
0. Health Check
1. Orion Context Broker (optional, no device)
2. Provisioning: service group, device, and subscription (once)
3. Simulate the device, or power on the ESP32
4. Commands
5. History in STH-Comet
6. Cleanup

Tested with Orion 4.5.0, IoT Agent UltraLight 3.7.0, and STH-Comet 2.11.0.""",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "item": [health, orion, provisioning, simulate, commands, history, cleanup],
    "variable": [
        {"key": "url", "value": "localhost", "description": "IP address or name of the platform server"},
        {"key": "service", "value": "smart", "description": "fiware-service (tenant)"},
        {"key": "servicepath", "value": "/", "description": "fiware-servicepath"},
        {"key": "apikey", "value": "TEF", "description": "API key of the service group"},
        {"key": "device_id", "value": "lamp001", "description": "Device identifier in the IoT Agent and in the MQTT topics"},
        {"key": "entity_id", "value": "urn:ngsi-ld:Lamp:001", "description": "Entity id in Orion"},
        {"key": "entity_type", "value": "Lamp", "description": "Entity type in Orion"},
        {"key": "sth_notify_url", "value": "http://sth-comet:8666/notify", "description": "INTERNAL URL (Docker network) used by Orion to notify STH-Comet"},
        {"key": "lastN", "value": "30", "description": "Number of values returned by the history (maximum 100)"},
        {"key": "subscription_id", "value": "", "description": "Filled in automatically in 2.6"},
    ],
}

with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)
    f.write("\n")
