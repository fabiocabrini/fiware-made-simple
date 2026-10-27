#!/usr/bin/env bash
# Checks whether this machine meets the FIWARE Made Simple requirements and
# fixes what it can.
#
# Usage: ./scripts/check-requirements.sh               checks and fixes
#        ./scripts/check-requirements.sh --check-only  only checks, changes nothing
#
# What it fixes, asking for the sudo password only when needed:
#   - creates .env from .env.example, with the sample passwords
#     (to change them later, see docs/07-security.md#change-the-passwords)
#   - adds variables missing from .env and sets MONGO_VERSION=8.2 on kernel 6.19+
#   - on Linux: installs Docker Engine and Compose, starts the Docker service,
#     adds your user to the docker group, and, on machines with less than
#     2 GB of memory, brings the swap to 2 GB with a swap file
# Architecture, AVX, disk space, and ports are only reported.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

fix=true
case "${1:-}" in
  "") ;;
  --check-only) fix=false ;;
  -h|--help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "Unknown option: $1 (use --check-only or --help)"; exit 2 ;;
esac

if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER:-}" ]; then
  echo "Run this script without sudo: it asks for the password only for the steps that need it."
  exit 2
fi
SUDO=sudo; [ "$(id -u)" -eq 0 ] && SUDO=""
ME=$(id -un)

PORTS="1026 1883 4041 7896 8666 9001 27017"
errors=0; warnings=0; fixes=0; relogin=false
ok()    { echo "  ✅ $1"; }
warn()  { echo "  ⚠️  $1"; warnings=$((warnings+1)); }
fail()  { echo "  ❌ $1"; errors=$((errors+1)); }
fixed() { echo "  🔧 $1"; fixes=$((fixes+1)); }

OS=$(uname -s); ARCH=$(uname -m)
wsl=false; grep -qi microsoft /proc/version 2>/dev/null && wsl=true
# Linux installed on the machine or VM itself, where the script may install packages
native_linux=false; [ "$OS" = Linux ] && ! $wsl && native_linux=true
has_apt=false; command -v apt-get >/dev/null 2>&1 && has_apt=true

can_sudo() {
  [ -z "$SUDO" ] && return 0
  command -v sudo >/dev/null 2>&1 || { fail "sudo not found: the fix needs administrator rights"; return 1; }
}

# Runs a fix step quietly and shows the end of its output if it fails
run_logged() {
  local log; log=$(mktemp)
  if "$@" >"$log" 2>&1; then rm -f "$log"; return 0; fi
  tail -5 "$log" | sed 's/^/       /'; rm -f "$log"; return 1
}

# After usermod, this terminal only gets the docker group through sg
use_sg=false
dk() {
  if $use_sg; then sg docker -c "docker $(printf '%q ' "$@")"; else docker "$@"; fi
}

echo "Configuration"
if [ -f .env ]; then ok ".env file present"
elif $fix; then
  cp .env.example .env && fixed ".env created from .env.example, with the sample passwords"
else warn ".env file missing. Create it with:  cp .env.example .env"; fi

if [ -f .env ]; then
  keys() { grep -oE '^[A-Z_][A-Z0-9_]*=' "$1" | sort -u; }
  missing=$(comm -23 <(keys .env.example) <(keys .env) | tr -d '=')
  if [ -n "$missing" ]; then
    if $fix; then
      { echo; echo "# Added by check-requirements.sh from .env.example on $(date +%F)"
        for k in $missing; do grep -m1 "^$k=" .env.example; done; } >> .env
      fixed "Added to .env with the values from .env.example: $(echo $missing)"
    else warn "Variables missing from .env, copy them from .env.example: $(echo $missing)"; fi
  fi
  if grep -q 'change-this' .env; then
    warn "The .env file uses the sample passwords: fine for a lab, change them before exposing the server (docs/07-security.md#change-the-passwords)"
  fi
fi

echo "System"
case "$OS" in
  Linux)
    name=$(. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME")
    if $wsl; then ok "Windows with WSL 2 ($name)"; else ok "Linux: ${name:-unknown}"; fi ;;
  Darwin) ok "macOS $(sw_vers -productVersion 2>/dev/null)" ;;
  *) warn "Untested system: $OS. Use Linux, Windows with WSL 2, or macOS" ;;
esac

case "$ARCH" in
  x86_64|amd64) ok "x86_64 architecture" ;;
  arm64|aarch64)
    if [ "$OS" = Darwin ]; then
      if [ "${DOCKER_DEFAULT_PLATFORM:-}" = linux/amd64 ]; then
        ok "Apple Silicon with DOCKER_DEFAULT_PLATFORM=linux/amd64 (x86_64 emulation)"
      else
        warn "Apple Silicon: enable Rosetta emulation in Docker and run  export DOCKER_DEFAULT_PLATFORM=linux/amd64"
      fi
    else
      fail "ARM processor ($ARCH) on Linux is not supported: the FIWARE images are published for x86_64 only"
    fi ;;
  *) fail "Unsupported architecture: $ARCH" ;;
esac

if [ "$OS" = Linux ] && [[ $ARCH =~ ^(x86_64|amd64)$ ]]; then
  if grep -qw avx /proc/cpuinfo 2>/dev/null; then ok "CPU with AVX instructions (required by MongoDB 5+)"
  else fail "CPU without AVX: MongoDB 5+ will not start. On VMs, set the CPU type to 'host'"; fi
elif [ "$OS" = Darwin ] && [ "$ARCH" = x86_64 ]; then
  if sysctl -n machdep.cpu.features machdep.cpu.leaf7_features 2>/dev/null | grep -qi avx; then ok "CPU with AVX instructions"
  else fail "CPU without AVX: MongoDB 5+ will not start"; fi
fi

mongo=$(grep -h '^MONGO_VERSION=' .env .env.example 2>/dev/null | head -1 | cut -d= -f2)
if [ "$OS" = Linux ]; then
  kernel=$(uname -r)
  IFS=. read -r kmaj kmin _ <<< "${kernel%%-*}"
  if [ "${kmaj:-0}" -gt 6 ] || { [ "${kmaj:-0}" -eq 6 ] && [ "${kmin:-0}" -ge 19 ]; }; then
    if [[ $mongo == 8.0* ]] && $fix && [ -f .env ]; then
      sed -i 's/^MONGO_VERSION=.*/MONGO_VERSION=8.2/' .env
      fixed "Linux kernel $kernel: MongoDB 8.0 does not start on kernel 6.19 or newer. MONGO_VERSION changed from $mongo to 8.2 in .env"
    elif [[ $mongo == 8.0* ]]; then
      fail "Linux kernel $kernel with MONGO_VERSION=$mongo: MongoDB 8.0 does not start on kernel 6.19 or newer. Set MONGO_VERSION=8.2 in .env"
    else ok "Linux kernel $kernel (MongoDB $mongo)"; fi
  else ok "Linux kernel $kernel"; fi
fi

cpus=$( (nproc || sysctl -n hw.ncpu) 2>/dev/null )
if [ "${cpus:-0}" -ge 2 ]; then ok "$cpus CPU cores"; else warn "${cpus:-?} CPU core: it works, but 2 or more are recommended"; fi

free_kb=$(df -Pk . | awk 'NR==2 {print $4}')
free_gb=$((free_kb / 1024 / 1024))
if [ "$free_gb" -ge 10 ]; then ok "$free_gb GB of free disk space"
elif [ "$free_gb" -ge 5 ]; then warn "$free_gb GB of free disk space: enough to start, 10 GB or more are recommended"
else fail "$free_gb GB of free disk space: at least 5 GB are required (images and data)"; fi

echo "Docker"
install_docker() {
  if ! command -v curl >/dev/null 2>&1; then
    $has_apt || { fail "curl not found and apt-get is not available to install it"; return 1; }
    run_logged $SUDO apt-get update -qq && run_logged $SUDO apt-get install -y -qq curl ca-certificates || return 1
  fi
  echo "  ⏳ Installing Docker Engine and Compose with the official script (get.docker.com)..."
  run_logged sh -c "curl -fsSL https://get.docker.com | $SUDO sh"
}

if ! command -v docker >/dev/null 2>&1; then
  if $fix && $native_linux; then
    if can_sudo && install_docker; then fixed "Docker Engine $(docker --version | awk '{print $3}' | tr -d ,) installed"
    else fail "Could not install Docker. See docs/03-installation.md#install-docker"; fi
  elif $wsl; then
    fail "Docker not found. Install Docker Desktop on Windows with the WSL 2 backend (docs/03-installation.md#windows)"
  elif [ "$OS" = Darwin ]; then
    fail "Docker not found. Install Docker Desktop or Colima (docs/03-installation.md#macos)"
  else
    fail "Docker not found. See docs/03-installation.md#install-docker"
  fi
fi

docker_ok=false
if command -v docker >/dev/null 2>&1; then
  docker_err=$(dk info 2>&1 >/dev/null); docker_rc=$?

  # The service is stopped: start it and enable it on boot
  if [ $docker_rc -ne 0 ] && [[ $docker_err != *"permission denied"* ]] && $fix && $native_linux \
     && command -v systemctl >/dev/null 2>&1 && can_sudo; then
    if run_logged $SUDO systemctl enable --now docker; then
      fixed "Docker service started and enabled on boot"
      docker_err=$(dk info 2>&1 >/dev/null); docker_rc=$?
    fi
  fi

  # The user is not in the docker group, or the terminal was opened before joining it
  if [ $docker_rc -ne 0 ] && [[ $docker_err == *"permission denied"* ]] && $fix && [ "$OS" = Linux ]; then
    if ! id -nG "$ME" | grep -qw docker; then
      can_sudo && run_logged $SUDO usermod -aG docker "$ME" && fixed "User $ME added to the docker group"
    fi
    if id -nG "$ME" | grep -qw docker && command -v sg >/dev/null 2>&1; then
      use_sg=true; relogin=true
      docker_err=$(dk info 2>&1 >/dev/null); docker_rc=$?
    fi
  fi

  if [ $docker_rc -ne 0 ]; then
    if [[ $docker_err == *"permission denied"* ]]; then
      fail "Your user cannot use Docker yet. Run  sudo usermod -aG docker \$USER  then log out and back in (no sudo in the docker commands)"
    else
      fail "Docker is installed but does not respond. Start the service (or Docker Desktop/Colima)"
    fi
  else
    docker_ok=true
    ok "Docker Engine $(dk version --format '{{.Server.Version}}' 2>/dev/null)"
    $relogin && warn "The docker group only applies to new sessions: log out and back in before using docker (or run  newgrp docker)"

    compose=$(dk compose version --short 2>/dev/null)
    if [ -z "$compose" ] && $fix && $native_linux && $has_apt && can_sudo; then
      # docker-compose-plugin comes from Docker's repository, docker-compose-v2 from Ubuntu's
      run_logged $SUDO apt-get update -qq
      if run_logged $SUDO apt-get install -y -qq docker-compose-plugin \
         || run_logged $SUDO apt-get install -y -qq docker-compose-v2; then
        compose=$(dk compose version --short 2>/dev/null)
        [ -n "$compose" ] && fixed "Docker Compose $compose installed"
      fi
    elif [ -n "$compose" ]; then ok "Docker Compose $compose"; fi
    [ -z "$compose" ] && fail "Docker Compose v2 plugin missing (the command is 'docker compose', with a space)"

    mem_mb=$(( $(dk info --format '{{.MemTotal}}' 2>/dev/null || echo 0) / 1024 / 1024 ))
    # Linux only: on Docker Desktop and Colima the swap belongs to the Docker VM
    swap_mb=-1
    [ "$OS" = Linux ] && swap_mb=$(awk '/^SwapTotal:/ {print int($2/1024)}' /proc/meminfo)

    # Less than 2 GB of memory: bring the swap to 2 GB, adding a file for what is missing
    # (a 2 GB swap file shows up as 2047 MB, hence the margin)
    if [ "$mem_mb" -ge 850 ] && [ "$mem_mb" -lt 1900 ] && [ "$swap_mb" -ge 0 ] && [ "$swap_mb" -lt 1900 ] \
       && $fix && $native_linux; then
      add_mb=$((2048 - swap_mb))
      swapfile=/swapfile; [ -e $swapfile ] && swapfile=/swapfile-fiware
      root_free_mb=$(( $(df -Pk / | awk 'NR==2 {print $4}') / 1024 ))
      if [ -e $swapfile ]; then
        fail "$mem_mb MB of memory and $swap_mb MB of swap, but /swapfile and /swapfile-fiware already exist. Check them with  swapon --show"
      elif [ "$root_free_mb" -lt $((add_mb + 5120)) ]; then
        fail "$mem_mb MB of memory and $swap_mb MB of swap, and only $((root_free_mb / 1024)) GB free on / for $add_mb MB more of swap plus the platform"
      elif can_sudo; then
        if [ "$(stat -f -c %T / 2>/dev/null)" = btrfs ]; then
          make_file() { run_logged $SUDO btrfs filesystem mkswapfile --size "${add_mb}M" $swapfile; }
        else
          make_file() {
            { run_logged $SUDO fallocate -l "${add_mb}M" $swapfile || run_logged $SUDO dd if=/dev/zero of=$swapfile bs=1M count=$add_mb; } \
              && run_logged $SUDO chmod 600 $swapfile && run_logged $SUDO mkswap $swapfile
          }
        fi
        if make_file && run_logged $SUDO swapon $swapfile; then
          grep -q "^$swapfile " /etc/fstab || echo "$swapfile none swap sw 0 0" | $SUDO tee -a /etc/fstab >/dev/null
          old_swap_mb=$swap_mb
          swap_mb=$(awk '/^SwapTotal:/ {print int($2/1024)}' /proc/meminfo)
          if [ "$old_swap_mb" -eq 0 ]; then fixed "2 GB swap file created at $swapfile, also active after reboots"
          else fixed "Swap increased from $old_swap_mb MB to $swap_mb MB with a $add_mb MB file at $swapfile, also active after reboots"; fi
        fi
      fi
    fi

    if [ "$mem_mb" -ge 1900 ]; then ok "$mem_mb MB of memory available to Docker"
    elif [ "$mem_mb" -lt 850 ]; then fail "$mem_mb MB of memory for Docker: at least 1 GB is required"
    elif [ "$swap_mb" -eq 0 ]; then
      fail "$mem_mb MB of memory and no swap: MongoDB will not become healthy. Add swap (docs/03-installation.md#machines-with-1-gb-of-memory) or use 2 GB"
    elif [ "$swap_mb" -gt 0 ]; then warn "$mem_mb MB of memory plus $swap_mb MB of swap: enough for a few devices; 2 GB or more are recommended"
    else warn "$mem_mb MB of memory for Docker: enough for a few devices; 2 GB or more are recommended"; fi
  fi
fi

echo "Ports"
in_use() {
  if command -v ss >/dev/null 2>&1; then ss -ltnH 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$1\$"
  elif command -v lsof >/dev/null 2>&1; then lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
  else return 1; fi
}
platform=$(dk ps --format '{{.Names}}' 2>/dev/null | grep -c '^fiware-' || true)
busy=""
for p in $PORTS; do in_use "$p" && busy="$busy $p"; done
if [ -z "$busy" ]; then ok "Free ports:$(printf ' %s' $PORTS)"
elif [ "$platform" -gt 0 ]; then ok "Ports in use by the platform itself, which is already running:$busy"
elif ! $docker_ok; then warn "Ports in use:$busy. Docker does not respond, so it is not possible to tell whether the platform itself holds them"
else fail "Ports taken by another program:$busy. See docs/08-troubleshooting.md#port-is-already-allocated"; fi

echo
[ $fixes -gt 0 ] && echo "🔧 $fixes fix(es) applied."
if [ $errors -gt 0 ]; then echo "❌ $errors problem(s) prevent the installation. Fix them and run this script again."; exit 1; fi
if $relogin; then
  echo "👉 Log out and back in (for example,  exit  and reconnect over SSH), then start the platform with:  docker compose up -d --wait"
elif [ $warnings -gt 0 ]; then echo "⚠️  Ready to install, with $warnings warning(s). Start the platform with:  docker compose up -d --wait"
else echo "✅ All set. Start the platform with:  docker compose up -d --wait"; fi
