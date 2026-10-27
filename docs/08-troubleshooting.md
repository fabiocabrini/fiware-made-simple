# 8. Troubleshooting

Always start with the general diagnosis, then look for your symptom in the list below.

```bash
./scripts/check-requirements.sh
```
```bash
docker compose ps
```
```bash
./scripts/smoke-test.sh
```

The first command checks the machine and Docker. The second shows which services are not `healthy`. The third shows where in the flow the failure happens.

**Symptoms:** [Service is not healthy](#a-service-is-not-healthy) · [MongoDB restarts in a loop](#mongodb-restarts-in-a-loop-illegal-instruction) · [MongoDB and Linux kernel 6.19+](#mongodb-cannot-start-linux-kernel-619-and-newer) · [Health check timeout on 1 GB machines](#health-check-exceeded-timeout-on-a-1-gb-machine) · [Port in use](#port-is-already-allocated) · [Docker permission denied](#permission-denied-when-using-docker) · [Subscription rejected](#subscription-rejected-invalid-attrsformat) · [Empty history](#the-history-stays-empty) · [Entity does not update](#the-entity-does-not-receive-measurements) · [409 when creating the service group](#409-conflict-when-creating-the-service-group) · [Data stopped after upgrading](#the-lamp-stopped-sending-data-after-the-upgrade) · [Command stuck in PENDING](#command-stays-pending) · [409 when provisioning the device](#409-conflict-when-provisioning-the-device) · [ESP32 does not connect](#the-esp32-does-not-connect-to-the-broker) · [MongoDB access denied](#authentication-failed-on-the-history-mongodb) · [Mac with Apple Silicon](#platform-warning-on-a-mac-with-apple-silicon)

---

### A service is not `healthy`

Check the service logs:

```bash
docker compose logs --tail 50 orion
```

Dependent services only start after MongoDB and Orion. If one of them fails, the others keep waiting, so fix the service at the bottom of the chain first.

### MongoDB restarts in a loop (`Illegal instruction`)

MongoDB 5.0 and later require **AVX** instructions on the processor. Check the machine:

```bash
grep -o -m1 avx /proc/cpuinfo
```

If there is no output, the processor or the VM does not expose AVX. On hypervisors such as Proxmox or VirtualBox, set the CPU type to `host`. On very old processors, there is no workaround with current MongoDB versions.

### `MongoDB cannot start: Linux kernel 6.19 and newer`

```
"msg":"MongoDB cannot start: Linux kernel versions 6.19 and newer has a known incompatibility with this version of MongoDB. See https://jira.mongodb.org/browse/SERVER-121912"
```

`docker compose up -d --wait` ends with `dependency mongo-db failed to start`, and both MongoDB containers stay in `Restarting`. MongoDB 8.0 refuses to start on Linux kernel 6.19 or newer, which includes Ubuntu 26.04 (kernel 7.0). Check the kernel with `uname -r`. Use MongoDB 8.2, the default since version 2.0.1, in `.env`:

```bash
sed -i 's/^MONGO_VERSION=.*/MONGO_VERSION=8.2/' .env
docker compose up -d --wait
```

MongoDB 8.2 opens the data written by 8.0, so the volumes are kept. If the containers were created before the change and the history database users do not exist (`Authentication failed` in the STH-Comet log), see [Authentication failed](#authentication-failed-on-the-history-mongodb).

### `Health check exceeded timeout` on a 1 GB machine

On machines with 1 GB of memory and no swap, such as the AWS `t3.micro`, the two MongoDB instances fill the memory during startup. `docker inspect fiware-mongo-db` shows `Health check exceeded timeout (5s)`, and `free -m` shows almost no free memory. Add swap as described in [Machines with 1 GB of memory](03-installation.md#machines-with-1-gb-of-memory), or use an instance with 2 GB.

If the first start ran out of memory, the history database may have been created without its users, because they are created only on the first start. STH-Comet then restarts in a loop with `AuthenticationFailed`. See [users missing](#the-history-database-users-are-missing) to create them without losing data.

### `port is already allocated`

Another program already uses the port, possibly another MongoDB or Mosquitto installed directly on the system. Find out which one:

```bash
sudo ss -ltnp | grep -E ':(1026|1883|4041|7896|8666|9001|27017)\b'
```

Stop the conflicting service, or change the published port in `docker-compose.yml`, for example `"27018:27017"`.

### `permission denied` when using Docker

Your user is not in the `docker` group:

```bash
sudo usermod -aG docker $USER
```

Then log out and back in: the group only applies to new sessions. Avoid `sudo docker compose` as a workaround: the scripts in `scripts/` run without `sudo` and report Docker as not responding.

### Subscription rejected: `invalid attrsFormat`

```json
{ "error": "BadRequest", "description": "invalid attrsFormat, accepted values: normalized, ..." }
```

The subscription uses `"attrsFormat": "legacy"`, which Orion 4.x no longer accepts. Use the `httpCustom` format described in [Historical data](06-historical-data.md#the-subscription) or request 2.6 of the collection.

### The history stays empty

Follow the chain backward:

1. **Is the entity changing?** Query it in Orion. If it is not, see [The entity does not receive measurements](#the-entity-does-not-receive-measurements).
2. **Does the subscription exist, and is it active?** In `GET /v2/subscriptions`, check `status: active` and whether `timesSent` grows.
3. **Do the notifications reach STH-Comet?** `lastSuccessCode` should be `200`. A `lastFailureReason` pointing to a connection or name resolution failure means the URL is wrong: use `http://sth-comet:8666/notify`, never the public IP or `localhost`.
4. **Is the query right?** The type, id, and attribute name in the STH-Comet URL, and the `fiware-service` and `fiware-servicepath` headers, must match the entity exactly.

### The entity does not receive measurements

- Check the topic names: `/<apikey>/<device_id>/attrs`, with the **leading slash**, and an `apikey` that matches the service group.
- Check the IoT Agent logs (`docker compose logs --tail 30 iot-agent`). `Device not found for topic` or `not provisioned due autoprovision` mean that the `apikey` + `device_id` pair in the topic does not match any provisioned device. Check both values in the firmware and in the provisioning, and make sure the device was provisioned **with the `apikey` field**.
- Watch the broker to see whether the messages arrive:

  ```bash
  docker compose exec mosquitto mosquitto_sub -t '#' -v
  ```

### `409 Conflict` when creating the service group

If the `fiware-service` is new and step 2.1 still returns `409` (`DUPLICATE_GROUP`), **another group already uses that `apikey`**. The `apikey` is unique across the whole platform, because it is how the IoT Agent finds the group each message belongs to. Choose another one ([Working in a classroom](04-getting-started.md#working-in-a-classroom)).

### The lamp stopped sending data after the upgrade

The provisioning was done in the previous version's format: a service group with an empty `resource`, or a device without the `apikey` field. The current version no longer accepts the implicit matching that the `TEF` `apikey` used to do in those cases. Delete the old device and service group and run folder **2** of the collection again:

```bash
curl -X DELETE -H 'fiware-service: smart' -H 'fiware-servicepath: /' http://localhost:4041/iot/devices/lamp001
```
```bash
curl -X DELETE -H 'fiware-service: smart' -H 'fiware-servicepath: /' 'http://localhost:4041/iot/services/?resource=&apikey=TEF'
```

The history is not affected. See also the [migration guide](../CHANGELOG.md#migrating-from-version-1).

### Command stays `PENDING`

The command reached the IoT Agent, but the device did not confirm it. Check that:

- the device is subscribed to `/<apikey>/<device_id>/cmd` and receives `lamp001@on|`;
- the firmware publishes the confirmation on `/<apikey>/<device_id>/cmdexe`, in the `lamp001@on|ok` format.

Details in [MQTT contract](05-smart-lamp.md#mqtt-contract).

### `409 Conflict` when provisioning the device

The device (`DUPLICATE_DEVICE_ID`) already exists. List it with `GET /iot/devices` and, if you want to recreate it, delete it first.

### The ESP32 does not connect to the broker

- The firmware must use the **server IP**, not `localhost`.
- Port 1883 must be open in the cloud provider firewall.
- Institutional networks often block port 1883. Try using your phone as a hotspot.
- Each device needs a **unique MQTT client ID**: two clients with the same ID keep kicking each other off.

### `Authentication failed` on the history MongoDB

- Check the user, password, and `?authSource=admin` in the URI.
- The users are created **only on the first start**. If you changed the passwords in `.env` after that, they do not apply. Change them in the database itself as described in [Change the passwords](07-security.md#change-the-passwords), or do a [full reset](03-installation.md#full-reset).

#### The history database users are missing

STH-Comet restarts in a loop with `AuthenticationFailed`, and the `mongo-db-sth` log shows `Failed to authenticate` for the `sth` user. This happens when the first start was interrupted, for example by lack of memory, before the users were created. Create them with the administrator user, keeping the data:

```bash
docker compose exec mongo-db-sth sh -c 'mongosh --quiet -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin /docker-entrypoint-initdb.d/init-users.js'
```
```bash
docker compose up -d --wait
```

`User "sth@admin" already exists` means the users were already there: the cause is a different password in `.env`, described above.

### Platform warning on a Mac with Apple Silicon

```
WARNING: The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8)
```

The FIWARE images are published for x86_64 only, and Docker runs them through emulation. The warning is expected and harmless **if Rosetta emulation is enabled**: in Docker Desktop, under *Settings › General*; in Colima, with `--vz-rosetta`. Without it, the containers fail with `exec format error` or become very slow. To use x86_64 images for every service and get rid of the warning:

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
```

See [Installation on macOS](03-installation.md#macos).

---

Could not find your problem? Open an *issue* in the repository with the output of `docker compose ps`, the result of `smoke-test.sh`, and the logs of the service involved.

[← 7. Security](07-security.md) · [Index](../README.md#documentation)
