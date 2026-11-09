#!/bin/bash
# Drives the local stack commands of a generated project as a black box.
# Run it from the generated project's root.
set -u

expected_url="http://localhost:${WEB_PORT:-8000}"
workdir=$(mktemp -d)
cookies="$workdir/cookies"

cleanup() {
	make destroy >/dev/null 2>&1
	if [ -f "$workdir/.env" ]; then
		mv "$workdir/.env" .env
	fi
	rm -rf "$workdir"
}
trap cleanup EXIT

fail() {
	echo "FAILED: $*" >&2
	exit 1
}

up() {
	local output
	output=$(make up 2>&1) || fail "make up exited non-zero:
$output"
	url=$(printf '%s\n' "$output" | grep -o 'http://localhost:[0-9]*' | head -n 1)
	[ "$url" = "$expected_url" ] || fail "make up printed '$url', expected $expected_url:
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
	curl -s -c "$cookies" -b "$cookies" -o "$workdir/login.html" "$url/accounts/login/"
	token=$(grep -o 'name="csrfmiddlewaretoken" value="[^"]*"' "$workdir/login.html" | sed 's/.*value="//; s/"$//')
	[ -n "$token" ] || fail "no CSRF token on $url/accounts/login/"
	result=$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' -c "$cookies" -b "$cookies" \
		--data-urlencode "csrfmiddlewaretoken=$token" \
		--data-urlencode "username=admin" \
		--data-urlencode "password=admin" \
		"$url/accounts/login/")
	[ "$result" = "302 $url/" ] || fail "login with admin / admin answered '$result'"
	echo "login: admin / admin"
}

expect_admin_status() {
	local status
	status=$(http_status "$url/admin/")
	[ "$status" = "$1" ] || fail "$url/admin/ answered $status, expected $1 ($2)"
	echo "$2: /admin/ $status"
}

[ -f .env ] || fail "needs the generated project's .env"
mv .env "$workdir/.env"
up
status=$(http_status "$url/healthz")
[ "$status" = "200" ] || fail "$url/healthz answered $status"
echo "healthz: 200"
log_in
expect_admin_status 200 "logged in"

mv "$workdir/.env" .env
make down >/dev/null 2>&1 || fail "make down exited non-zero"
up
expect_admin_status 200 "session survives make down, with .env"

make destroy >/dev/null 2>&1 || fail "make destroy exited non-zero"
up
expect_admin_status 302 "session gone after make destroy"
