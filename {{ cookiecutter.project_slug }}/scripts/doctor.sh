#!/bin/bash
set -u

cd "$(dirname "$0")/.."

MINIMUM_COMPOSE_VERSION=2.24.4
MINIMUM_ENGINE_VERSION=25.0.0

failed=0
engine_version=""

pass() {
	echo "PASS  $1"
}

fail() {
	echo "FAIL  $1"
	shift
	printf '      %s\n' "$@"
	failed=1
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

if check_daemon; then
	check_compose_version
	check_engine_version
fi
check_lockfile uv.lock "uv sync"
check_lockfile core/frontend/package-lock.json "make frontend.install"

exit "$failed"
