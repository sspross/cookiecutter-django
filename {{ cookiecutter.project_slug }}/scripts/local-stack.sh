#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

HEALTHY_TIMEOUT_SECONDS=180
LOGIN_USERNAME=admin
LOGIN_PASSWORD=admin

stack_name() {
	echo "{{ cookiecutter.project_slug }}-local"
}

export COMPOSE_PROJECT_NAME
COMPOSE_PROJECT_NAME=$(stack_name)
export WEB_PORT="${WEB_PORT:-8000}"
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

up() {
	command -v docker >/dev/null 2>&1 || fail "make up needs Docker with the compose plugin"
	compose build
	if ! compose up --detach --no-build; then
		show_stack_state
		fail "the stack did not start. Logs: make logs"
	fi
	wait_until_web_is_healthy
	ensure_local_superuser
	echo ""
	echo "Ready: http://localhost:$WEB_PORT"
	echo "Login: $LOGIN_USERNAME / $LOGIN_PASSWORD"
}

case "${1:-}" in
	up) up ;;
	down) compose down ;;
	destroy) compose down --volumes --remove-orphans ;;
	logs) compose logs --follow ;;
	*) fail "usage: $0 up|down|destroy|logs" ;;
esac
