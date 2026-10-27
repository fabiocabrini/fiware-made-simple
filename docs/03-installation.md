# 3. Requirements and installation

**On this page:** [Requirements](#requirements) · [Check your machine](#check-your-machine) · [Install Docker](#install-docker) · [Get and configure](#get-and-configure) · [Start the platform](#start-the-platform) · [Verify](#verify) · [Day-to-day operation](#day-to-day-operation) · [Upgrade versions](#upgrade-versions) · [Cloud installation](#cloud-installation)

---

## Requirements

### Hardware

| Resource | Minimum | Recommended | Classroom or shared lab |
|---|---|---|---|
| Processor | 1 x86_64 core with **AVX** | 2 cores | 2 to 4 cores |
| Memory (RAM) | 1 GB, [with swap](#machines-with-1-gb-of-memory) | 2 GB | 4 GB |
| Free disk space | 5 GB | 20 GB | 40 GB or more, depending on the history |

**Measured numbers** with the versions in this platform:

| Situation | Memory used by the containers |
|---|---|
| Idle platform | about 600 MiB |
| 20 devices sending 1 measurement per second each | about 850 MiB, with no lost messages |

The minimum configuration is enough for one person testing a few devices. For a classroom, prefer the rightmost column: memory grows with the number of devices, and the operating system needs room too.

**Disk.** The images take about **2.5 GB**. Each measurement stored in the history takes about **0.9 KB**, indexes included:

| Scenario | History per day | Per month |
|---|---|---|
| 1 sensor, one measurement every 5 s | about 16 MB | about 0.5 GB |
| 1 sensor, one measurement per second | about 80 MB | about 2.3 GB |
| 20 sensors, one measurement per second | about 1.6 GB | about 47 GB |

To limit growth, adjust the device publishing rate or enable [automatic history expiration](06-historical-data.md#retention-and-limits).

### Operating systems

| System | Status | How |
|---|---|---|
| **Ubuntu Server 26.04 LTS** (x86_64) | ✅ Recommended | [Docker Engine](#linux-ubuntu-debian-and-derivatives) |
| Ubuntu Server 18.04 to 24.04 LTS (x86_64) | ✅ Supported | [Docker Engine](#linux-ubuntu-debian-and-derivatives) |
| Debian 12 and other x86_64 Linux distributions | ✅ Supported | [Docker Engine](#linux-ubuntu-debian-and-derivatives) |
| Windows 10 or 11 (64-bit) | ✅ Supported | [Docker Desktop with WSL 2](#windows) |
| macOS on Intel | ✅ Supported | [Docker Desktop or Colima](#macos) |
| macOS on Apple Silicon (M1 to M4) | ✅ Supported, through x86_64 emulation | [Docker Desktop or Colima with Rosetta](#macos) |
| Linux on **ARM** processors: Raspberry Pi, AWS Graviton (`t4g`, `m7g`...), Oracle Ampere A1 | ❌ Not supported | The FIWARE images are published for x86_64 only |
| 32-bit systems | ❌ Not supported | |

> [!NOTE]
> Ubuntu 18.04 and 20.04 are past their standard support period, so prefer a current LTS release for new installations. On them, the system Python (3.6 and 3.8) is older than the 3.9 required by the [Python examples](../examples/); the platform itself is not affected.

### Software

| Software | Version | Notes |
|---|---|---|
| Docker Engine | 20.10 or later | Tested with 29.5 |
| Docker Compose | v2 (the `docker compose` command, with a space) | Tested with 2.33 and 5.6. Compose v1 (`docker-compose`, with a hyphen) does not work |
| Git | any recent version | To clone the repository |
| Postman | any recent version | Optional, to follow [Getting started](04-getting-started.md) |
| Python | 3.9 or later | Optional, only for the [examples](../examples/) |

### Network

- Internet access to download the images on the first installation.
- Free ports on the server: **1026, 1883, 4041, 7896, 8666, 9001, and 27017**.
- For physical devices, the ESP32 and the server must be on the same network, or the server needs a public IP with port 1883 open.

> [!NOTE]
> **AVX.** MongoDB 5.0 and later require a processor with AVX instructions. Virtually every x86 processor from the last decade has them, but some VMs (for example, the `kvm64` CPU type in Proxmox) hide this instruction set. See [Troubleshooting](08-troubleshooting.md#mongodb-restarts-in-a-loop-illegal-instruction).

## Check your machine

With the repository cloned ([Get and configure](#get-and-configure)), and whenever something does not work, run:

```bash
./scripts/check-requirements.sh
```

The script checks the operating system, architecture, AVX, the Linux kernel against the MongoDB version, memory and swap available to Docker, disk space, Docker and Compose versions, ports, and the `.env` file, and **fixes what it can**, asking for your `sudo` password only for the steps that need it:

| Problem | What the script does |
|---|---|
| `.env` missing | Creates it from `.env.example`, with the sample passwords ([change them later](07-security.md#change-the-passwords)) |
| Variables missing from `.env`, for example after a `git pull` | Adds them with the values from `.env.example` |
| `MONGO_VERSION=8.0` on Linux kernel 6.19 or newer | Changes it to `8.2` in `.env` |
| Docker not installed (Linux) | Installs Docker Engine and Compose with the [official script](#linux-ubuntu-debian-and-derivatives) |
| Docker service stopped (Linux) | Starts it and enables it on boot |
| Compose v2 plugin missing (Linux with `apt`) | Installs `docker-compose-plugin`, or `docker-compose-v2` from Ubuntu |
| User outside the `docker` group | Adds the user; then **log out and back in** |
| Less than 2 GB of memory and less than 2 GB of swap (Linux) | Brings the swap to 2 GB: creates a [2 GB swap file](#machines-with-1-gb-of-memory), or, when there is already some swap, a file with the difference (`/swapfile`, or `/swapfile-fiware` if that one exists) |

The architecture, AVX, disk space, and ports are only reported. On Windows and macOS, the script does not install Docker: follow [Install Docker](#install-docker). To only check, without changing anything:

```bash
./scripts/check-requirements.sh --check-only
```

Example on a machine that is ready:

```
System
  ✅ Linux: Ubuntu 26.04 LTS
  ✅ x86_64 architecture
  ✅ CPU with AVX instructions (required by MongoDB 5+)
  ✅ Linux kernel 7.0.0-1014-aws (MongoDB 8.2)
  ...
✅ All set. Start the platform with:  docker compose up -d --wait
```

## Install Docker

### Linux (Ubuntu, Debian, and derivatives)

`check-requirements.sh` does these steps for you. To do them by hand, use Docker's official script, which installs Docker Engine and the Compose v2 plugin:

```bash
curl -fsSL https://get.docker.com | sh
```

To use Docker without `sudo`, add your user to the `docker` group and **log out and back in**:

```bash
sudo usermod -aG docker $USER
```

The group only takes effect in a new session. Until then, `docker` commands fail with `permission denied`, even right after `check-requirements.sh` added you to the group. Do not work around it with `sudo docker compose`: the scripts in `scripts/` run without `sudo`.

Check the installation. The command is `docker compose`, with a space:

```bash
docker compose version
```

> [!WARNING]
> Do not use the `docker-compose` package from `apt`, with a hyphen. It installs Compose v1, which is discontinued and does not understand all the features used here.

### Windows

Install [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) with the WSL 2 backend and run the commands in this guide in a **WSL (Ubuntu)** terminal. The scripts in the `scripts/` folder need a Bash shell.

> [!TIP]
> Clone the repository **inside the WSL file system** (for example, in `~/fiware-made-simple`), not in `/mnt/c/...`. It is much faster and avoids permission and line-ending problems in the scripts.

### macOS

Choose one of the options:

- [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/): on Macs with Apple Silicon, enable **Use Rosetta for x86_64/amd64 emulation** in the settings.
- [Colima](https://github.com/abiosoft/colima), a lightweight command-line alternative:

  ```bash
  brew install colima docker docker-compose
  ```
  ```bash
  colima start --cpu 2 --memory 4 --vm-type vz --vz-rosetta
  ```

On Macs with Apple Silicon, tell Docker to use x86_64 images for every service, so the environment matches a server. To avoid repeating the command, add it to your `~/.zshrc` file:

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
```

## Get and configure

```bash
git clone https://github.com/fabiocabrini/fiware-made-simple.git
cd fiware-made-simple
./scripts/check-requirements.sh
```

> [!IMPORTANT]
> **If the script ends with `👉 Log out and back in`**, it installed Docker or added your user to the `docker` group, which only applies to new sessions. Close the SSH connection with `exit`, connect again, and go back to the folder with `cd fiware-made-simple` before [starting the platform](#start-the-platform). Do not use `sudo docker compose` instead.

`check-requirements.sh` creates the `.env` file from `.env.example` when it does not exist (by hand: `cp .env.example .env`). The `.env` file holds the image versions, the history database credentials, and the log levels. It is **not versioned**: it is listed in `.gitignore`.

| Variable | Purpose |
|---|---|
| `STH_MONGO_ROOT_USER` / `_PASSWORD` | History database administrator (administration only) |
| `STH_MONGO_USER` / `_PASSWORD` | User that STH-Comet uses to write |
| `STH_MONGO_READER_USER` / `_PASSWORD` | **Read-only** user for external access (Python, Compass, BI) |
| `STH_MONGO_BIND` | `0.0.0.0` publishes port 27017 to the network; `127.0.0.1` restricts it to this machine |
| `STH_EXPIRE_AFTER_SECONDS` | Deletes history values older than N seconds; `0` keeps everything ([details](06-historical-data.md#retention-and-limits)) |
| `*_VERSION` | Image versions, tested together |
| `*_LOG_LEVEL` | `DEBUG`, `INFO`, `WARN`, or `ERROR` |

> [!IMPORTANT]
> **The sample passwords are fine for a lab, not for a server exposed on a network.** The MongoDB users are created only when the database volume is created, so changing a password is simplest before the first start. To change them at any time, see [Change the passwords](07-security.md#change-the-passwords).

## Start the platform

```bash
docker compose up -d --wait
```

The `--wait` flag makes the command wait until every service is *healthy*. On the first run, downloading the images takes a few minutes; after that, the platform starts in about 20 seconds.

## Verify

Service state (all of them should show as `healthy`):

```bash
docker compose ps
```

Quick API check:

```bash
curl http://localhost:1026/version
```
```bash
curl http://localhost:4041/iot/about
```
```bash
curl http://localhost:8666/version
```

Full end-to-end test. It provisions a device, sends measurements and commands, checks the history and the database permissions, and removes everything it created at the end:

```bash
./scripts/smoke-test.sh
```

The script takes about 15 seconds, uses the `smoketest` `fiware-service` and the `smoke001` device, and does not touch your data. Run it on the platform server itself.

## Day-to-day operation

| Task | Command |
|---|---|
| Start | `docker compose up -d --wait` |
| Show the state | `docker compose ps` |
| Follow the logs of a service | `docker compose logs -f orion` |
| Restart a service | `docker compose restart iot-agent` |
| Stop (keeps the data) | `docker compose down` |

Data lives in the `fiware_mongo-db-data`, `fiware_mongo-db-sth-data`, and `fiware_mosquitto-data` volumes and survives `docker compose down`.

### Full reset

> [!CAUTION]
> Deletes **all** entities, subscriptions, devices, and the whole history. This cannot be undone.

```bash
docker compose down -v
```

On the next start, the databases are recreated empty and the history database users are created with the passwords currently in `.env`.

## Upgrade versions

The versions live in `.env`. Before upgrading, read the release notes of each component, and run `smoke-test.sh` after the change.

```bash
docker compose pull && docker compose up -d --wait
```

> [!NOTE]
> **From 2.0.0 to 2.0.1:** `git pull` does not change your `.env`. Change `MONGO_VERSION=8.0` to `MONGO_VERSION=8.2` in it and run the command above. MongoDB 8.2 opens the 8.0 data as is, so no export is needed. This change is required on Linux kernel 6.19 or newer, such as Ubuntu 26.04, where MongoDB 8.0 does not start.

> [!WARNING]
> **Do not downgrade Orion from 4.x to 3.x** on the same volume: the internal format of subscriptions changed, and Orion 3.x logs errors when reading them.

## Cloud installation

The process is the same on a VM from any provider. Choose an **Ubuntu Server LTS** image (26.04 recommended) on an **x86_64** instance with at least 2 GB of memory. Examples:

| Provider | Instance | vCPU / memory |
|---|---|---|
| AWS | `t3.small` (`t3.micro`, 1 GiB, only [with swap](#machines-with-1-gb-of-memory)) | 2 / 2 GiB |
| Microsoft Azure | `B1ms` or `B2s` | 1 / 2 GiB or 2 / 4 GiB |
| Google Cloud | `e2-small` or `e2-medium` | 2 shared / 2 or 4 GB |
| Oracle Cloud | AMD or Intel shapes (`VM.Standard.E*`) with 2 GB or more | varies |

> [!WARNING]
> Avoid **ARM** instances: AWS Graviton (`t4g`, `m7g`...) and Oracle Ampere A1, including the free tier one. The FIWARE images do not run on them.

Install Docker and open only the ports you need in the **security group** (the provider firewall):

| Port | Open it if... |
|---|---|
| 1026 | external applications will use Orion |
| 4041 | you will provision devices from your computer |
| 1883 | MQTT devices will connect |
| 7896 | devices will send measurements over HTTP |
| 8666 | external dashboards will query the history |
| 9001 | web applications will use MQTT over WebSocket |
| 27017 | you will analyze the history from outside, **restricted to your IP** |

> [!WARNING]
> Docker publishes ports directly in the system's network rules and **bypasses UFW**. A port published in `docker-compose.yml` stays reachable even if UFW blocks it. Control access through the cloud provider's firewall and read [Security](07-security.md).

### Machines with 1 GB of memory

Instances with 1 GB, such as the AWS free tier `t3.micro`, run the platform for one person testing a few devices, **but only with swap**. Without it, the two MongoDB instances compete for memory during startup, the health checks time out, and `docker compose up -d --wait` ends with `dependency failed to start`. Cloud images usually come without swap. `check-requirements.sh` creates a 2 GB swap file in this case, or completes the existing swap up to 2 GB. To create it by hand, which also survives reboots:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Check it with `free -h`: the `Swap` line must show about 2.0Gi. With 2 GB of memory or more, swap is optional.

---

[← 2. Architecture](02-architecture.md) · [Index](../README.md#documentation) · Next: [4. Getting started →](04-getting-started.md)
