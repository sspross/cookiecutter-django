#!/bin/bash
# Drives the local stack commands of a generated project as a black box.
# Run it from the generated project's root.
set -u

project=$(pwd)
workdir=$(mktemp -d)
copy="$workdir/copy/$(basename "$project")"
cookies="$workdir/cookies"
blocker_pid=""

cleanup() {
	if [ -n "$blocker_pid" ]; then
		kill "$blocker_pid" 2>/dev/null
	fi
	if [ -d "$copy" ]; then
		(cd "$copy" && make destroy >/dev/null 2>&1)
	fi
	(cd "$project" && make destroy >/dev/null 2>&1)
	if [ -f "$workdir/.env" ]; then
		mv "$workdir/.env" "$project/.env"
	fi
	rm -rf "$workdir"
}
trap cleanup EXIT

fail() {
	echo "FAILED: $*" >&2
	exit 1
}

port_is_free() {
	curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$1/"
	[ $? -eq 7 ]
}

up() {
	local log="$workdir/up.log"
	(cd "$1" && make up >"$log" 2>&1) || fail "make up exited non-zero:
$(cat "$log")"
	url=$(grep -o 'http://localhost:[0-9]*' "$log" | head -n 1)
	port=${url##*:}
	[ -n "$port" ] || fail "make up printed no URL:
$(cat "$log")"
	grep -q 'admin / admin' "$log" || fail "make up did not print the login:
$(cat "$log")"
	echo "make up: a URL and the login"
}

http_status() {
	curl -s -o /dev/null -w '%{http_code}' -b "$cookies" "$1"
}

log_in() {
	local token result
	curl -s -c "$cookies" -b "$cookies" -o "$workdir/login.html" "$1/accounts/login/"
	token=$(grep -o 'name="csrfmiddlewaretoken" value="[^"]*"' "$workdir/login.html" | sed 's/.*value="//; s/"$//')
	[ -n "$token" ] || fail "no CSRF token on $1/accounts/login/"
	result=$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' -c "$cookies" -b "$cookies" \
		--data-urlencode "csrfmiddlewaretoken=$token" \
		--data-urlencode "username=admin" \
		--data-urlencode "password=admin" \
		"$1/accounts/login/")
	[ "$result" = "302 $1/" ] || fail "login with admin / admin on $1 answered '$result'"
	echo "login: admin / admin"
}

expect_admin_status() {
	local status
	status=$(http_status "$1/admin/")
	[ "$status" = "$2" ] || fail "$1/admin/ answered $status, expected $2 ($3)"
	echo "$3: /admin/ $status"
}

session_cookie_names() {
	awk '$6 ~ /^sessionid/ { print $6 }' "$cookies" | sort
}

cookie_value() {
	awk -v name="$1" '$6 == name { print $7 }' "$cookies"
}

block_port() {
	python3 -m http.server "$1" --bind 127.0.0.1 >/dev/null 2>&1 &
	blocker_pid=$!
	for _ in $(seq 1 50); do
		port_is_free "$1" || return 0
		sleep 0.1
	done
	fail "could not block port $1"
}

[ -f .env ] || fail "needs the generated project's .env"
mv .env "$workdir/.env"

up "$project"
first_url="$url"
first_port="$port"
status=$(http_status "$first_url/healthz")
[ "$status" = "200" ] || fail "$first_url/healthz answered $status"
echo "healthz: 200"
log_in "$first_url"
expect_admin_status "$first_url" 200 "logged in"
first_session_name=$(session_cookie_names)

up "$project"
[ "$port" = "$first_port" ] || fail "a second make up moved the running stack from port $first_port to $port"
expect_admin_status "$first_url" 200 "second make up on a running stack keeps port and session"

mkdir -p "$copy"
tar -C "$project" --exclude ./.venv --exclude ./core/frontend/node_modules --exclude ./.git -cf - . | tar -C "$copy" -xf -
up "$copy"
second_url="$url"
second_port="$port"
[ "$second_port" != "$first_port" ] || fail "the copy got the first stack's port $first_port"
echo "copy runs on another port"
log_in "$second_url"
second_session_name=$(session_cookie_names | grep -v -x "$first_session_name")
[ -n "$second_session_name" ] || fail "the copy uses the first stack's session cookie name $first_session_name"
status=$(curl -s -o /dev/null -w '%{http_code}' -b "$second_session_name=$(cookie_value "$first_session_name")" "$second_url/admin/")
[ "$status" = "302" ] || fail "the copy accepted the first stack's session ($status), so it shares its data"
echo "copy has its own data: first stack's session unknown there"
expect_admin_status "$first_url" 200 "logging in on the copy keeps the session on the first stack"

(cd "$copy" && make destroy >/dev/null 2>&1) || fail "make destroy in the copy exited non-zero"
expect_admin_status "$first_url" 200 "make destroy in the copy leaves the first stack alone"

mv "$workdir/.env" .env
make down >/dev/null 2>&1 || fail "make down exited non-zero"
block_port "$first_port"
up "$project"
[ "$port" != "$first_port" ] || fail "make up took port $first_port, which another process holds"
status=$(http_status "$url/healthz")
[ "$status" = "200" ] || fail "$url/healthz answered $status"
echo "port held by another process: make up took another port"
expect_admin_status "$url" 200 "session survives make down and a port change, with .env"
kill "$blocker_pid" 2>/dev/null
blocker_pid=""

make destroy >/dev/null 2>&1 || fail "make destroy exited non-zero"
up "$project"
expect_admin_status "$url" 302 "session gone after make destroy"
echo "local stack smoke test passed"
