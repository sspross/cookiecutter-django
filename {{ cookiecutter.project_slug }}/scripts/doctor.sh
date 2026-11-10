#!/bin/bash
set -u

cd "$(dirname "$0")/.."

MINIMUM_COMPOSE_VERSION=2.24.4
MINIMUM_ENGINE_VERSION=25.0.0
PROBE_IMAGE=python:3.13-slim
PROBE_NAME="doctor-probe-$$"
PUBLISH_TIMEOUT_SECONDS=20
LOW_MEMORY_MB=1024
LOW_DISK_MB=10240

mode=${1:-all}
failed=0
engine_version=""

pass() {
	[ "$mode" = fast ] || echo "PASS  $1"
}

warn() {
	echo "WARN  $1"
}

fail() {
	echo "FAIL  $1"
	shift
	printf '      %s\n' "$@"
	failed=1
}

remove_probes() {
	docker rm --force "$PROBE_NAME" >/dev/null 2>&1
	docker image rm "$PROBE_NAME" >/dev/null 2>&1
}

version_number() {
	local version major minor patch _
	version=${1#v}
	version=${version%%[!0-9.]*}
	IFS=. read -r major minor patch _ <<-EOF
		$version
	EOF
	echo $((10#${major:-0} * 1000000 + 10#${minor:-0} * 1000 + 10#${patch:-0}))
}

version_is_at_least() {
	[ "$(version_number "$1")" -ge "$(version_number "$2")" ]
}

check_daemon() {
	if ! command -v docker >/dev/null 2>&1; then
		fail "Docker is not installed" "fix: install Docker Engine or Docker Desktop, with the compose plugin"
		return 1
	fi
	local output
	if output=$(docker version --format '{% raw %}{{.Server.Version}}{% endraw %}' 2>&1); then
		engine_version=$(printf '%s\n' "$output" | tail -n 1)
		pass "Docker daemon reachable without sudo"
		return 0
	fi
	case "$output" in
		*"permission denied"*)
			fail "Docker daemon not reachable without sudo" \
				"fix: sudo usermod -aG docker \$USER, then log in again so the group applies"
			;;
		*)
			fail "Docker daemon not reachable" \
				"fix: start Docker (Linux: sudo systemctl start docker, macOS: open the Docker app)" \
				"$(printf '%s\n' "$output" | tail -n 1)"
			;;
	esac
	return 1
}

check_compose_version() {
	local version
	if ! version=$(docker compose version --short 2>/dev/null); then
		fail "Docker Compose plugin missing" "fix: install the compose plugin, $MINIMUM_COMPOSE_VERSION or newer"
	elif version_is_at_least "$version" "$MINIMUM_COMPOSE_VERSION"; then
		pass "Compose $version ($MINIMUM_COMPOSE_VERSION or newer)"
	else
		fail "Compose $version is older than $MINIMUM_COMPOSE_VERSION" \
			"fix: update the compose plugin. compose.local.yaml needs !override, !reset and optional env files"
	fi
}

check_engine_version() {
	if version_is_at_least "$engine_version" "$MINIMUM_ENGINE_VERSION"; then
		pass "Engine $engine_version (${MINIMUM_ENGINE_VERSION%%.*} or newer)"
	else
		fail "Engine $engine_version is older than ${MINIMUM_ENGINE_VERSION%%.*}" \
			"fix: update Docker. Older engines ignore the healthcheck start_interval, so make up waits much longer"
	fi
}

check_lockfile() {
	if [ -f "$1" ]; then
		pass "$1 exists"
	else
		fail "$1 is missing, the image build installs from it" "fix: $2"
	fi
}

# Renaming and hard-linking files of a lower layer is what dpkg does during apt-get install.
# It fails when Docker's data directory is on btrfs and the containerd overlayfs snapshotter is on.
check_build() {
	local dockerfile output
	dockerfile="FROM $PROBE_IMAGE
RUN python -c \"import os; os.link('/etc/debian_version', '/etc/linked'); os.rename('/etc/debian_version', '/etc/renamed'); open('/etc/issue', 'a').write('probe')\""
	if output=$(printf '%s\n' "$dockerfile" | docker build --no-cache --tag "$PROBE_NAME" - 2>&1); then
		pass "Image build can change files of a base layer"
		return
	fi
	fail "Image build probe failed" \
		"$(printf '%s\n' "$output" | tail -n 5)" \
		"fix: when the error is not about the network and Docker's data directory is on btrfs," \
		"put this into /etc/docker/daemon.json and run: sudo systemctl restart docker" \
		'{"features": {"containerd-snapshotter": false}, "storage-driver": "btrfs"}' \
		"Existing images and volumes are hidden after the restart."
}

host_gets_200_from_port() {
	(exec 3<>"/dev/tcp/127.0.0.1/$1" && printf 'GET / HTTP/1.0\r\n\r\n' >&3 && head -n 1 <&3 | grep -q ' 200 ') 2>/dev/null
}

# Leaves the probe container running for check_resources.
check_published_port() {
	local output address port
	if ! output=$(docker run --detach --rm --name "$PROBE_NAME" --publish 127.0.0.1::8000 "$PROBE_IMAGE" python -m http.server 8000 2>&1); then
		fail "Publish probe: the container did not start" \
			"$(printf '%s\n' "$output" | tail -n 3)" \
			"fix: Docker must be able to pull and run $PROBE_IMAGE"
		return 1
	fi
	address=$(docker port "$PROBE_NAME" 8000 | head -n 1)
	port=${address##*:}
	SECONDS=0
	while [ "$SECONDS" -lt "$PUBLISH_TIMEOUT_SECONDS" ]; do
		if host_gets_200_from_port "$port"; then
			pass "Published port reachable from the host on 127.0.0.1"
			return 0
		fi
		sleep 1
	done
	fail "Published port 127.0.0.1:$port did not answer from the host" \
		"fix: check firewall and VPN rules for ports that Docker publishes on 127.0.0.1." \
		"With Docker in a VM or on a remote host, its localhost ports must be forwarded to this machine."
	return 1
}

# Read inside a container, because on macOS Docker's memory and disk are those of its VM.
check_resources() {
	local memory_mb disk_mb
	memory_mb=$(docker exec "$PROBE_NAME" awk '/^MemAvailable:/ { print int($2 / 1024) }' /proc/meminfo 2>/dev/null)
	disk_mb=$(docker exec "$PROBE_NAME" df -Pm / 2>/dev/null | awk 'NR == 2 { print $4 }')
	if [ "${memory_mb:-0}" -lt "$LOW_MEMORY_MB" ]; then
		warn "Free memory for Docker is ${memory_mb:-unknown} MB, another stack gets tight below $LOW_MEMORY_MB MB"
	else
		pass "Free memory for Docker: $memory_mb MB"
	fi
	if [ "${disk_mb:-0}" -lt "$LOW_DISK_MB" ]; then
		warn "Free disk for Docker is ${disk_mb:-unknown} MB, image builds get tight below $LOW_DISK_MB MB"
	else
		pass "Free disk for Docker: $disk_mb MB"
	fi
}

case "$mode" in
	all | fast) ;;
	*)
		echo "usage: $0 [fast]" >&2
		exit 2
		;;
esac

daemon_reachable=false
if check_daemon; then
	daemon_reachable=true
	check_compose_version
	check_engine_version
fi
check_lockfile uv.lock "uv sync"
check_lockfile core/frontend/package-lock.json "make frontend.install"

if [ "$mode" = all ] && [ "$daemon_reachable" = true ]; then
	trap remove_probes EXIT
	check_build
	if check_published_port; then
		check_resources
	fi
fi

exit "$failed"
