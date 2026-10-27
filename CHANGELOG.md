# Changelog

## Unreleased

- **`check-requirements.sh` fixes what it can**, asking for the `sudo` password only when needed. It creates `.env` from `.env.example` with the sample passwords, adds variables missing from `.env`, sets `MONGO_VERSION=8.2` on Linux kernel 6.19 or newer, and, on Linux, installs Docker Engine and Compose, starts the Docker service, adds the user to the `docker` group, and creates a 2 GB swap file on machines with less than 2 GB of memory. Use `--check-only` for the previous behavior, which changes nothing. The script refuses to run with `sudo`.
- **Changing the passwords:** new step-by-step section in [Security](docs/07-security.md#change-the-passwords), before and after the first start, keeping the data.
- **Quick start:** `cp .env.example .env` is no longer a separate step.

## 2.0.1

Fixes found while installing on an AWS EC2 `t3.micro` with Ubuntu Server 26.04.

- **MongoDB 8.2:** MongoDB 8.0 refuses to start on Linux kernel 6.19 or newer, which includes Ubuntu 26.04 (kernel 7.0), with `MongoDB cannot start: Linux kernel versions 6.19 and newer` ([SERVER-121912](https://jira.mongodb.org/browse/SERVER-121912)). The default in `.env.example` is now 8.2, which opens the 8.0 data as is. **Existing installations:** `git pull` does not change `.env`; set `MONGO_VERSION=8.2` there.
- **`check-requirements.sh`:**
  - Checks the Linux kernel against `MONGO_VERSION`.
  - Fails on machines with less than 2 GB of memory and no swap. Previously, 908 MB (a `t3.micro`) was rejected even with swap.
  - Says when the user is not yet in the `docker` group, instead of a generic "does not respond".
  - No longer blames "another program" for the ports when Docker does not respond and it cannot tell whether the platform itself holds them.
- **Documentation:** swap setup for 1 GB machines such as the `t3.micro`, upgrade note from 2.0.0, and new troubleshooting entries for the kernel error, for health check timeouts, and for creating missing history database users without losing data.

## 2.0.0

Complete review of the platform, the documentation, and the examples. All image versions were pinned and tested together, and the platform now has automated end-to-end tests. This is also the first release under the name FIWARE Made Simple.

### Platform

- **Pinned, current versions:** Orion 4.5.0, IoT Agent UltraLight 3.7.0, STH-Comet 2.11.0, Mosquitto 2.0.22, and MongoDB 8.0. Previously, several images used `latest` and could change without notice.
- **Two databases with clear roles:** `mongo-db` for the context (Orion and the IoT Agent), with no published port, and `mongo-db-sth` for the history, with authentication, a write user, and a **read-only user** for external access.
- **Passwords and versions in `.env`**, outside `docker-compose.yml`, with clear error messages when the file is missing.
- **Health checks and startup order:** `docker compose up -d --wait` returns only when every service is ready.
- **`TEF` apikey fix:** `TEF` is the IoT Agent's internal default key. With it, messages were matched to devices of other groups by `device_id`. The default key was disabled, and `TEF` now behaves like any other `apikey`.
- **Mosquitto:** WebSocket on port 9001 now works, persistent messages got a volume, and logs show up in `docker compose logs`.
- **Log rotation** and a capped MongoDB cache, so the platform runs well on small machines.
- **Configurable history retention** through `.env` (`STH_EXPIRE_AFTER_SECONDS`).

### Postman collection

- Reorganized into numbered folders (0 to 6), with variables, documentation in every request, and automated tests.
- **STH-Comet subscription with `httpCustom`:** Orion 4.x removed the `legacy` format that STH-Comet requires.
- Service group with `resource: "/iot/d"` and `autoprovision: false`; device with `apikey`; no manual registration, since the IoT Agent creates it by itself.
- Measurement simulation over HTTP, without hardware.

### Examples

- **ESP32 firmware:** confirms commands on `/cmdexe` (previously, `on_status` stayed `PENDING` forever), publishes without blocking `delay()` calls, publishes the state only when it changes, generates a unique client ID, and supports MQTT authentication.
- **Python simulator** with the same behavior as the firmware, compatible with paho-mqtt 2.x.
- **Dashboards** (Dash and Matplotlib) configurable through arguments, displaying times in the local time zone by default.
- **NTP:** time zone set with `configTzTime`, fixing the wrong date around midnight.

### Documentation and tools

- README and eight chapters in `docs/`: concepts, architecture, requirements and installation, getting started, Smart Lamp, historical data, security, and troubleshooting.
- New architecture diagram, with the telemetry and command flows.
- `scripts/check-requirements.sh`, which checks the machine before installation, and `scripts/smoke-test.sh`, which tests the platform end to end.
- Automated testing on GitHub Actions for every change.

### Migrating from version 1

Version 1 is the original release of the project, published as FIWARE Descomplicado at [github.com/fabiocabrini/fiware](https://github.com/fabiocabrini/fiware). Version 2 uses new volume names and therefore **starts with empty databases**. The old volumes are not deleted: they remain available until you remove them.

1. **Export the history** while version 1 is still running, from the old folder:

   ```bash
   docker exec fiware-mongo-historical mongodump -u admin -p admin123 --authenticationDatabase admin --archive > history-v1.archive
   ```

2. **Stop version 1**, in the old folder and **before** updating the repository:

   ```bash
   docker compose down
   ```

3. **Clone this repository** and start version 2 by following [Requirements and installation](docs/03-installation.md).

4. **Import the history** into the new database, only the `sth_*` databases. Use the `STH_MONGO_ROOT_PASSWORD` from your `.env`:

   ```bash
   docker exec -i fiware-mongo-db-sth mongorestore -u admin -p ADMIN_PASSWORD --authenticationDatabase admin --nsInclude='sth_*.*' --archive < history-v1.archive
   ```

5. **Provision again** with folder 2 of the new collection: service group, devices, and subscription. The old subscription, in `legacy` format, does not work with Orion 4.x.

6. **Update the device firmware** to the version in `examples/esp32-smart-lamp`, which confirms the commands.

7. Once everything checks out, **remove the old volumes**:

   ```bash
   docker volume rm fiware_mongo-historical-data fiware_mongo-internal-data
   ```

## 1.x

Original release, published as FIWARE Descomplicado: Orion 3.11, MongoDB 4.4, and `latest` images for the IoT Agent, STH-Comet, and Mosquitto.
