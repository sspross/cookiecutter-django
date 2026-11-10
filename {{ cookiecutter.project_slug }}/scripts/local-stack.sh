#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

HEALTHY_TIMEOUT_SECONDS=180
LOGIN_USERNAME=admin
LOGIN_PASSWORD=admin
FIRST_PORT=8000
LAST_PORT=8099

# Two worktrees with the same folder name must not share a stack.
stack_name() {
	local path_hash
	path_hash=$(pwd -P | cksum | cut -d ' ' -f 1)
	printf '{{ cookiecutter.project_slug }}-%08x\n' "$path_hash"
}

export COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(stack_name)
# Read during interpolation by every compose command, also those that publish nothing.
export WEB_PORT="$FIRST_PORT"
# Read by compose.yaml during interpolation, even when a .env sets it empty.
export POSTGRES_PASSWORD=local

fail() {
	echo "error: $*" >&2
	exit 1
}

compose() {
	docker compose -f compose.yaml -f compose.local.yaml "$@"
}

show_stack_state() {
	compose ps --all >&2
	compose logs --tail 30 >&2
}

published_port() {
	local address
	address=$(compose port web 8000 2>/dev/null) || return 0
	case "${address##*:}" in
		"" | 0 | *[!0-9]*) ;;
		*) echo "${address##*:}" ;;
	esac
}

# A connection succeeds when anything listens, a Docker port or any other process.
port_is_taken() {
	(exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null || (exec 3<>"/dev/tcp/::1/$1") 2>/dev/null
}

lowest_free_port_from() {
	local port=$1
	while [ "$port" -le "$LAST_PORT" ]; do
		if ! port_is_taken "$port"; then
			echo "$port"
			return 0
		fi
		port=$((port + 1))
	done
	return 1
}

# Returns 1 only when the port was taken after it was picked; any other failure exits.
start_on_port() {
	local output
	WEB_PORT=$1
	# Not `tee /dev/stderr`: reopening stderr truncates it when it is a regular file.
	if output=$(compose up --detach --no-build 2>&1 | tee >(cat >&2)); then
		return 0
	fi
	case "$output" in
		*"address already in use"* | *"port is already allocated"*)
			echo "Port $WEB_PORT was taken meanwhile, trying the next one." >&2
			return 1
			;;
	esac
	show_stack_state
	fail "the stack did not start. Logs: make logs"
}

start_stack() {
	local port
	port=$(published_port)
	if [ -n "$port" ]; then
		start_on_port "$port" || fail "port $port of this running stack was taken"
		return
	fi
	port=$FIRST_PORT
	while port=$(lowest_free_port_from "$port"); do
		start_on_port "$port" && return
		port=$((port + 1))
	done
	fail "no free port between $FIRST_PORT and $LAST_PORT"
}

web_state() {
	local container
	container=$(compose ps -q web)
	if [ -z "$container" ]; then
		echo missing
		return
	fi
	# A crashing web keeps restarting, so its health alone would stay "starting".
	docker inspect -f '{% raw %}{{if eq .State.Health.Status "healthy"}}healthy{{else if gt .RestartCount 0}}crashed{{else}}{{.State.Health.Status}}{{end}}{% endraw %}' "$container"
}

wait_until_web_is_healthy() {
	local state
	SECONDS=0
	while [ "$SECONDS" -lt "$HEALTHY_TIMEOUT_SECONDS" ]; do
		state=$(web_state)
		case "$state" in
			healthy) return 0 ;;
			unhealthy | crashed | missing) break ;;
		esac
		sleep 1
	done
	show_stack_state
	fail "web did not become healthy (last state: $state). Logs: make logs"
}

ensure_local_superuser() {
	compose exec -T web uv run python manage.py shell -c "
from django.contrib.auth import get_user_model

user, _ = get_user_model().objects.get_or_create(username='$LOGIN_USERNAME')
user.is_active = True
user.is_staff = True
user.is_superuser = True
# A new hash would end the sessions already logged in as this user.
if not user.check_password('$LOGIN_PASSWORD'):
    user.set_password('$LOGIN_PASSWORD')
user.save()
"
}

# Every rebuild leaves the replaced image untagged, more than 1 GB of new layers each.
remove_replaced_images() {
	docker image prune --force --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME" >/dev/null
}

destroy() {
	compose down --volumes --remove-orphans
	# Each stack builds its own image, so it would stay behind after the worktree is gone.
	if docker image inspect "$COMPOSE_PROJECT_NAME" >/dev/null 2>&1; then
		docker image rm "$COMPOSE_PROJECT_NAME"
	fi
}

up() {
	local doctor_output
	if ! doctor_output=$(./scripts/doctor.sh); then
		echo "$doctor_output" >&2
		fail "this machine cannot run the stack"
	fi
	# Built first, so the port is picked as late as possible.
	compose build
	start_stack
	remove_replaced_images
	wait_until_web_is_healthy
	ensure_local_superuser
	echo ""
	echo "Ready: http://localhost:$WEB_PORT"
	echo "Login: $LOGIN_USERNAME / $LOGIN_PASSWORD"
}

case "${1:-}" in
	up) up ;;
	down) compose down ;;
	destroy) destroy ;;
	logs) compose logs --follow ;;
	*) fail "usage: $0 up|down|destroy|logs" ;;
esac
