# 7. Security

FIWARE Made Simple was designed for **teaching, research, and proofs of concept**. It favors simplicity and therefore leaves out several controls required in production. This chapter makes clear what is protected, what is not, and how to move forward.

**On this page:** [What is already configured](#what-is-already-configured) · [What is not protected](#what-is-not-protected) · [Checklist for exposed servers](#checklist-for-exposed-servers) · [Toward production](#toward-production)

---

## What is already configured

| Measure | How |
|---|---|
| Isolated context database | `mongo-db` publishes no port; only containers on the internal network can reach it |
| Authenticated history database | `mongo-db-sth` requires a user and password; anonymous access is rejected |
| Least privilege on the history | STH-Comet writes with its own user; external access uses a **read-only** user |
| Passwords outside the code | Credentials live in `.env`, which is not versioned |
| Log rotation | Each container keeps at most 3 files of 10 MB, so the disk does not fill up |

## What is not protected

| Surface | Risk |
|---|---|
| **Orion, IoT Agent, and STH-Comet APIs** (1026, 4041, 8666) | No authentication: anyone who reaches the port can read, change, and delete data, and provision devices |
| **MQTT broker** (1883, 9001) | Accepts anonymous connections: any client can publish fake measurements or send commands |
| **HTTP measurements** (7896) | Knowing the `apikey` and `device_id` is enough to send data |
| **Traffic** | Nothing is encrypted (HTTP and MQTT without TLS) |

> [!CAUTION]
> On a cloud VM with these ports open to `0.0.0.0/0`, **the platform is reachable by anyone on the internet**. Bots continuously scan well-known ports such as 1883 and 27017.

## Checklist for exposed servers

- [ ] **Change every password** in `.env` before the first start, using long, random passwords.
- [ ] **Restrict the ports in the cloud provider firewall** (*security group*) to the IPs of your institution or your home, never to `0.0.0.0/0`.
- [ ] **Do not rely on UFW for Docker ports.** Docker creates its own rules, and a published port stays reachable even when UFW blocks it. Use the provider firewall, or stop publishing the port.
- [ ] **Close what you do not use.** Remove unnecessary ports from `docker-compose.yml`, for example 7896 and 9001 if nobody uses HTTP or WebSocket.
- [ ] **Restrict the history MongoDB to the machine itself** with `STH_MONGO_BIND=127.0.0.1`, and connect through an SSH tunnel:
  ```bash
  ssh -L 27017:localhost:27017 user@server
  ```
- [ ] **Use hard-to-guess `apikeys`** instead of short values such as `TEF`.
- [ ] **Keep the system and the images up to date** ([Upgrade versions](03-installation.md#upgrade-versions)).
- [ ] **Shut down the VM** when the course or the experiment is over.

### Mosquitto authentication

To require a user and password on the broker, create a password file and adjust the configuration:

```bash
docker compose exec mosquitto mosquitto_passwd -c -b /mosquitto/data/passwd iotagent IOTA_PASSWORD
```
```bash
docker compose exec mosquitto mosquitto_passwd -b /mosquitto/data/passwd lamp001 DEVICE_PASSWORD
```

In `config/mosquitto/mosquitto.conf`, replace `allow_anonymous true` with:

```
allow_anonymous false
password_file /mosquitto/data/passwd
```

Finally, give the credentials to the IoT Agent in `docker-compose.yml` (`IOTA_MQTT_USERNAME` and `IOTA_MQTT_PASSWORD`) and to the devices: `MQTT_USER` and `MQTT_PASSWORD` in the [firmware](../examples/esp32-smart-lamp/), or `--user` and `--password` in the [simulator](../examples/python-simulator/). Restart the services with `docker compose up -d`.

## Toward production

A production platform needs, at a minimum:

| Need | Solution in the FIWARE ecosystem and beyond |
|---|---|
| Identity and authentication of users and applications | [Keyrock](https://fiware-idm.readthedocs.io/) (OAuth2) |
| API protection | [Wilma PEP Proxy](https://fiware-pep-proxy.readthedocs.io/) in front of Orion and the IoT Agent |
| Policy-based authorization | [AuthZForce](https://authzforce-ce-fiware.readthedocs.io/) (XACML) |
| Encryption | HTTPS with a reverse proxy (Nginx, Traefik) and MQTT over TLS (port 8883) |
| High availability | MongoDB *replica set* and orchestration with Kubernetes or Docker Swarm |
| Backup | Routine `mongodump` of both databases, with an off-server copy |

---

[← 6. Historical data](06-historical-data.md) · [Index](../README.md#documentation) · Next: [8. Troubleshooting →](08-troubleshooting.md)
