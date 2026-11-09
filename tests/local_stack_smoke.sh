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
	local output
	output=$(cd "$1" && make up 2>&1) || fail "make up exited non-zero:
$output"
	url=$(printf '%s\n' "$output" | grep -o 'http://localhost:[0-9]*' | head -n 1)
	[ "$url" = "http://localhost:$2" ] || fail "make up printed '$url', expected http://localhost:$2:
$output"
	printf '%s\n' "$output" | grep -q 'admin / admin' || fail "make up did not print the login:
$output"
	echo "make up: $url"
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
	echo "login on $1: admin / admin"
}

expect_admin_status() {
	local status
	status=$(http_status "$1/admin/")
	[ "$status" = "$2" ] || fail "$1/admin/ answered $status, expected $2 ($3)"
	echo "$3: /admin/ $status"
}

session_cookie_value() {
	awk -v name="$1" '$6 == name { print $7 }' "$cookies"
}

for port in 8000 8001; do
	port_is_free "$port" || fail "port $port must be free for this test"
done
[ -f .env ] || fail "needs the generated project's .env"
mv .env "$workdir/.env"

up "$project" 8000
first_url="$url"
status=$(http_status "$first_url/healthz")
[ "$status" = "200" ] || fail "$first_url/healthz answered $status"
echo "healthz: 200"
log_in "$first_url"
expect_admin_status "$first_url" 200 "logged in"

up "$project" 8000
expect_admin_status "$first_url" 200 "second make up on a running stack keeps port and session"

mkdir -p "$copy"
tar -C "$project" --exclude ./.venv --exclude ./core/frontend/node_modules --exclude ./.git -cf - . | tar -C "$copy" -xf -
up "$copy" 8001
second_url="$url"
status=$(curl -s -o /dev/null -w '%{http_code}' -b "sessionid_8001=$(session_cookie_value sessionid_8000)" "$second_url/admin/")
[ "$status" = "302" ] || fail "the copy accepted the first stack's session ($status), so it shares its data"
echo "copy has its own data: first stack's session unknown there"
log_in "$second_url"
expect_admin_status "$first_url" 200 "logging in on 8001 keeps the session on 8000"
(cd "$copy" && make destroy >/dev/null 2>&1) || fail "make destroy in the copy exited non-zero"
expect_admin_status "$first_url" 200 "make destroy in the copy leaves the first stack alone"

mv "$workdir/.env" .env
make down >/dev/null 2>&1 || fail "make down exited non-zero"
up "$project" 8000
expect_admin_status "$first_url" 200 "session survives make down, with .env"

make destroy >/dev/null 2>&1 || fail "make destroy exited non-zero"
up "$project" 8000
expect_admin_status "$first_url" 302 "session gone after make destroy"

make down >/dev/null 2>&1 || fail "make down exited non-zero"
python3 -m http.server 8000 --bind 127.0.0.1 >/dev/null 2>&1 &
blocker_pid=$!
for _ in $(seq 1 50); do
	port_is_free 8000 || break
	sleep 0.1
done
port_is_free 8000 && fail "could not block port 8000"
up "$project" 8001
status=$(http_status "$url/healthz")
[ "$status" = "200" ] || fail "$url/healthz answered $status"
echo "port 8000 held by another process: make up took 8001"
