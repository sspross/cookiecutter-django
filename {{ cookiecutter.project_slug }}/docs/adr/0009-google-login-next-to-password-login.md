# Google login next to password login, allowlist in env vars

"Sign in with Google" sits next to the username and password form, on Django's
own `LoginView`. Most people who get access already have a Google account, and
creating each account in the admin with a password does not scale. The
password form stays because some people have no Google account, and it keeps a
Google outage from being an outage of the app.

Google login is django-allauth with its Google provider, and only the two
views of the redirect flow are mounted. social-auth-app-django's domain
whitelist checks the email suffix and not Google's `hd` claim, and a
hand-written OIDC flow is more security-critical code of our own than an
adapter hook.

The SSO allowlist lives in env vars: `SSO_ALLOWED_DOMAINS` matches the `hd`
claim, never the email suffix, because a private Google account can carry a
verified `name@company.com` address; `SSO_ALLOWED_EMAILS` matches single
verified emails. A database allowlist would need its own UI and migrations for
a list that changes rarely. Changing the list is a config change and a
restart, and it blocks the next login, not an open session.

Superusers come from a third, independent list, `SSO_SUPERUSER_EMAILS`. It
never allows a login by itself, and a login never demotes, so taking rights
away stays the admin's job.

A Google login links to an existing user with the same email instead of
creating a second one. That is safe because Google verified the email and an
unverified one is rejected first.

How it is wired: `docs/ARCHITECTURE.md` "Google login". The rule in
production: `docs/OPERATIONS.md` "SSO allowlist".
