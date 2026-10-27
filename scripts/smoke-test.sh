#!/usr/bin/env bash
# End-to-end test of FIWARE Made Simple.
#
# Run it on the server where the platform is running, from any folder:
#   ./scripts/smoke-test.sh
#
# Uses the fiware-service "smoketest" and the device "smoke001" (your data is not
# touched), checks the flows below and, at the end, removes everything it created:
#   1. health of every service
#   2. IoT Agent provisioning (service group + device with commands)
#   3. history:    Orion -> STH-Comet subscription
#   4. telemetry:  MQTT -> IoT Agent -> Orion
#   5. command:    Orion -> IoT Agent -> MQTT -> "device" -> cmdexe -> Orion
#   6. STH-Comet:  history query
#   7. MongoDB:    exposed ports and user permissions

set -uo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo ".env file not found. Create it with:  ./scripts/check-requirements.sh"
  exit 1
fi
set -a; source .env; set +a

if ! curl -sf -o /dev/null http://localhost:1026/version; then
  echo "The platform does not respond on localhost:1026. Start it with:  docker compose up -d --wait"
  exit 1
fi

SERVICE=smoketest
APIKEY=SMOKE
DEVICE=smoke001
ENTITY=urn:ngsi-ld:Lamp:smoke001
H=(-H "fiware-service: $SERVICE" -H "fiware-servicepath: /")
JSON=(-H "Content-Type: application/json")

pass=0; fail=0
ok()   { echo "  ✅ $1"; pass=$((pass+1)); }
nok()  { echo "  ❌ $1"; fail=$((fail+1)); }
check() { if eval "$2"; then ok "$1"; else nok "$1"; fi; }
mqtt_pub()  { docker compose exec -T mosquitto mosquitto_pub -t "$1" -m "$2"; }
mongo_sth() { docker compose exec -T mongo-db-sth mongosh --quiet "$@"; }
mongo_err() { mongo_sth "$@" 2>&1 || true; }   # output of a command that is expected to fail
published() { local p; p=$(docker compose port "$1" 27017 2>/dev/null); [[ $p =~ :[1-9] ]]; }
luminosity() { curl -s "${H[@]}" "http://localhost:1026/v2/entities/$ENTITY/attrs/luminosity/value"; }

cleanup() {
  for id in $(curl -s "${H[@]}" "http://localhost:1026/v2/subscriptions" | grep -o '"id":"[0-9a-f]\{24\}"' | cut -d'"' -f4); do
    curl -s -o /dev/null -X DELETE "${H[@]}" "http://localhost:1026/v2/subscriptions/$id"
  done
  curl -s -o /dev/null -X DELETE "${H[@]}" "http://localhost:4041/iot/devices/$DEVICE"
  curl -s -o /dev/null -X DELETE "${H[@]}" "http://localhost:4041/iot/services/?resource=/iot/d&apikey=$APIKEY"
  curl -s -o /dev/null -X DELETE "${H[@]}" "http://localhost:1026/v2/entities/$ENTITY"
  curl -s -o /dev/null -X DELETE "${H[@]}" "http://localhost:8666/STH/v1/contextEntities/type/Lamp/id/$ENTITY"
}
trap 'echo; echo "Interrupted: removing what was created..."; cleanup; exit 130' INT TERM

echo "1. Service health"
ORION=$(curl -s "http://localhost:1026/version" | grep -o '"version" *: *"[0-9.]*"' | grep -o '[0-9][0-9.]*')
check "Orion $ORION :1026" "[ -n '$ORION' ]"
check "IoT Agent    :4041" "curl -sf http://localhost:4041/iot/about >/dev/null"
check "STH-Comet    :8666" "curl -sf http://localhost:8666/version >/dev/null"
for s in $(docker compose config --services); do
  state=$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q "$s")" 2>/dev/null)
  check "$s healthy" "[ '$state' = healthy ]"
done

cleanup

echo "2. Provisioning"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${H[@]}" "${JSON[@]}" "http://localhost:4041/iot/services" -d '{
  "services": [{ "apikey": "'$APIKEY'", "resource": "/iot/d", "entity_type": "Lamp", "autoprovision": false }]
}')
check "service group created (201)" "[ $code = 201 ]"

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${H[@]}" "${JSON[@]}" "http://localhost:4041/iot/devices" -d '{
  "devices": [{
    "device_id": "'$DEVICE'", "apikey": "'$APIKEY'",
    "entity_name": "'$ENTITY'", "entity_type": "Lamp",
    "protocol": "PDI-IoTA-UltraLight", "transport": "MQTT",
    "commands":   [{ "name": "on", "type": "command" }, { "name": "off", "type": "command" }],
    "attributes": [{ "object_id": "s", "name": "state", "type": "Text" },
                   { "object_id": "l", "name": "luminosity", "type": "Integer" }]
  }]
}')
check "device provisioned (201)" "[ $code = 201 ]"
regs=$(curl -s "${H[@]}" "http://localhost:1026/v2/registrations")
check "command registration created by the IoT Agent" "echo '$regs' | grep -q '$ENTITY'"

echo "3. History: Orion -> STH-Comet subscription (internal URL, httpCustom)"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${H[@]}" "${JSON[@]}" "http://localhost:1026/v2/subscriptions" -d '{
  "description": "Smoke test luminosity to STH-Comet",
  "subject": { "entities": [{ "id": "'$ENTITY'", "type": "Lamp" }], "condition": { "attrs": ["luminosity"] } },
  "notification": {
    "httpCustom": { "url": "http://sth-comet:8666/notify", "json": { "contextResponses": [{
      "contextElement": { "id": "${id}", "type": "${type}", "isPattern": "false",
        "attributes": [{ "name": "luminosity", "type": "Integer", "value": "${luminosity}" }] },
      "statusCode": { "code": "200", "reasonPhrase": "OK" } }] } },
    "attrs": ["luminosity"]
  }
}')
check "subscription created (201)" "[ $code = 201 ]"

echo "4. Telemetry: MQTT -> IoT Agent -> Orion"
mqtt_pub "/$APIKEY/$DEVICE/attrs" "s|off|l|42"; sleep 1
mqtt_pub "/$APIKEY/$DEVICE/attrs/l" "55"; sleep 1
mqtt_pub "/$APIKEY/$DEVICE/attrs/l" "61"; sleep 2
ent=$(curl -s "${H[@]}" "http://localhost:1026/v2/entities/$ENTITY?options=keyValues")
echo "     entity: $ent"
check "luminosity = 61 in Orion" "echo '$ent' | grep -q '\"luminosity\":61'"
check "state = off in Orion"     "echo '$ent' | grep -q '\"state\":\"off\"'"
# Isolation: messages with another apikey (including "TEF", the IoT Agent
# default key) must not reach this device
mqtt_pub "/TEF/$DEVICE/attrs/l" "7"; mqtt_pub "/OTHER/$DEVICE/attrs/l" "8"; sleep 2
check "messages with another apikey (TEF, OTHER) are ignored" "[ \"\$(luminosity)\" = 61 ]"
ndev=$(curl -s "${H[@]}" "http://localhost:4041/iot/devices" | grep -o '"device_id"' | wc -l | tr -d ' ')
check "no device created by autoprovisioning" "[ $ndev = 1 ]"

echo "5. Command: Orion -> IoT Agent -> MQTT -> device -> cmdexe"
tmp=$(mktemp)
docker compose exec -T mosquitto mosquitto_sub -t "/$APIKEY/$DEVICE/cmd" -C 1 -W 10 > "$tmp" &
sub=$!; sleep 1
code=$(curl -s -o /dev/null -w '%{http_code}' -X PATCH "${H[@]}" "${JSON[@]}" "http://localhost:1026/v2/entities/$ENTITY/attrs" \
  -d '{ "on": { "type": "command", "value": "" } }')
check "command PATCH accepted (204)" "[ $code = 204 ]"
wait $sub; cmd=$(cat "$tmp"); rm -f "$tmp"
echo "     received on the /cmd topic: $cmd"
check "device received '$DEVICE@on|'" "[ '$cmd' = '$DEVICE@on|' ]"
st=$(curl -s "${H[@]}" "http://localhost:1026/v2/entities/$ENTITY/attrs/on_status/value")
check "on_status = PENDING before confirmation" "echo '$st' | grep -q PENDING"
mqtt_pub "/$APIKEY/$DEVICE/cmdexe" "$DEVICE@on|done"; sleep 2
st=$(curl -s "${H[@]}" "http://localhost:1026/v2/entities/$ENTITY/attrs/on_status/value")
info=$(curl -s "${H[@]}" "http://localhost:1026/v2/entities/$ENTITY/attrs/on_info/value")
check "on_status = OK after cmdexe" "echo '$st' | grep -q OK"
check "on_info = done"             "echo '$info' | grep -q done"

echo "6. STH-Comet: history query"
hist=$(curl -s "${H[@]}" "http://localhost:8666/STH/v1/contextEntities/type/Lamp/id/$ENTITY/attributes/luminosity?lastN=10")
vals=$(echo "$hist" | grep -o '"attrValue":[^,}]*' | cut -d: -f2 | tr '\n' ' ')
echo "     values in the history: $vals"
check "STH stored 42, 55 and 61" "[ '$vals' = '42 55 61 ' ]"

echo "7. MongoDB"
R_CRED="$STH_MONGO_READER_USER:$STH_MONGO_READER_PASSWORD"
R_URI="mongodb://$R_CRED@host.docker.internal:27017/?authSource=admin"   # from outside, through the published port
R_LOCAL="mongodb://$R_CRED@localhost:27017/?authSource=admin"            # from inside the container
check "mongo-db (context) has no port published on the host" "! published mongo-db"
check "mongo-db-sth (history) published on port 27017" "published mongo-db-sth"
check "mongo-db-sth rejects anonymous access" \
  "mongo_err --eval 'db.getSiblingDB(\"sth_$SERVICE\").getCollectionNames()' | grep -q 'requires authentication'"
check "reader user reads the history through the published port" \
  "docker run --rm --add-host=host.docker.internal:host-gateway mongo:$MONGO_VERSION mongosh --quiet '$R_URI' \
     --eval 'db.getSiblingDB(\"sth_$SERVICE\").getCollectionNames().length' 2>/dev/null | grep -q '^[1-9]'"
check "reader user can NOT write" \
  "mongo_err '$R_LOCAL' --eval 'db.getSiblingDB(\"sth_$SERVICE\").x.insertOne({a:1})' | grep -q 'not authorized'"

cleanup
echo
echo "Result: $pass OK, $fail failure(s)"
[ $fail -eq 0 ]
