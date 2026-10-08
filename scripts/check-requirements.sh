#!/usr/bin/env bash
# Checks whether this machine meets the FIWARE Made Simple requirements.
#
# Usage: ./scripts/check-requirements.sh
#
# Changes nothing: it only inspects the system and Docker and tells you what to fix.

set -uo pipefail
cd "$(dirname "$0")/.."

PORTS="1026 1883 4041 7896 8666 9001 27017"
errors=0; warnings=0
ok()    { echo "  ✅ $1"; }
warn()  { echo "  ⚠️  $1"; warnings=$((warnings+1)); }
fail()  { echo "  ❌ $1"; errors=$((errors+1)); }

OS=$(uname -s); ARCH=$(uname -m)

echo "System"
case "$OS" in
  Linux)
    name=$(. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME")
    if grep -qi microsoft /proc/version 2>/dev/null; then ok "Windows with WSL 2 ($name)"; else ok "Linux: ${name:-unknown}"; fi ;;
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

cpus=$( (nproc || sysctl -n hw.ncpu) 2>/dev/null )
if [ "${cpus:-0}" -ge 2 ]; then ok "$cpus CPU cores"; else warn "${cpus:-?} CPU core: it works, but 2 or more are recommended"; fi

free_kb=$(df -Pk . | awk 'NR==2 {print $4}')
free_gb=$((free_kb / 1024 / 1024))
if [ "$free_gb" -ge 10 ]; then ok "$free_gb GB of free disk space"
elif [ "$free_gb" -ge 5 ]; then warn "$free_gb GB of free disk space: enough to start, 10 GB or more are recommended"
else fail "$free_gb GB of free disk space: at least 5 GB are required (images and data)"; fi

echo "Docker"
if ! command -v docker >/dev/null 2>&1; then
  fail "Docker not found. See docs/03-installation.md#install-docker"
elif ! docker info >/dev/null 2>&1; then
  fail "Docker is installed but does not respond. Start the service (or Docker Desktop/Colima) and check your user permissions"
else
  ok "Docker Engine $(docker version --format '{{.Server.Version}}' 2>/dev/null)"
  compose=$(docker compose version --short 2>/dev/null)
  if [ -n "$compose" ]; then ok "Docker Compose $compose"
  else fail "Docker Compose v2 plugin missing (the command is 'docker compose', with a space)"; fi

  mem_mb=$(( $(docker info --format '{{.MemTotal}}' 2>/dev/null || echo 0) / 1024 / 1024 ))
  if [ "$mem_mb" -ge 1900 ]; then ok "$mem_mb MB of memory available to Docker"
  elif [ "$mem_mb" -ge 950 ]; then warn "$mem_mb MB of memory for Docker: enough for a few devices; 2 GB or more are recommended"
  else fail "$mem_mb MB of memory for Docker: at least 1 GB is required"; fi
fi

echo "Ports"
in_use() {
  if command -v ss >/dev/null 2>&1; then ss -ltnH 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$1\$"
  elif command -v lsof >/dev/null 2>&1; then lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
  else return 1; fi
}
platform=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c '^fiware-' || true)
busy=""
for p in $PORTS; do in_use "$p" && busy="$busy $p"; done
if [ -z "$busy" ]; then ok "Free ports:$(printf ' %s' $PORTS)"
elif [ "$platform" -gt 0 ]; then ok "Ports in use by the platform itself, which is already running:$busy"
else fail "Ports taken by another program:$busy. See docs/08-troubleshooting.md#port-is-already-allocated"; fi

echo "Configuration"
if [ -f .env ]; then
  ok ".env file present"
  grep -q 'change-this' .env && warn "The .env file still uses the sample passwords: change them before exposing the server on a network"
else
  warn ".env file missing. Create it with:  cp .env.example .env"
fi

echo
if [ $errors -gt 0 ]; then echo "❌ $errors problem(s) prevent the installation. Fix them and run this script again."; exit 1
elif [ $warnings -gt 0 ]; then echo "⚠️  Ready to install, with $warnings warning(s)."
else echo "✅ All set. Start the platform with:  docker compose up -d --wait"; fi
