# 0009 - Google login next to password login, allowlist in env vars

## Context

Most people who get access to a project already have a Google account, usually
a Google Workspace account on a company domain, sometimes a private one.
Creating each account in the admin and handing out a password does not scale,
and the first production superuser used to need a fragile `createsuperuser`
one-off command. Some people still have no Google account, so a password
account has to remain possible.

## Decision

**"Sign in with Google" sits next to the username and password form.** Django's
own `LoginView` and `LogoutView` stay the login and logout views, and an
account created in the admin with a password logs in as before.

**Google login is django-allauth with its Google provider, and only that part
of allauth is mounted.** The two views of the redirect flow
(`/accounts/google/login/` and its callback) are mounted when
`GOOGLE_OAUTH_CLIENT_ID` is set, and not at all otherwise. allauth's own login,
signup, password reset and email pages are not mounted. Every outcome that is
not a login redirects to the login page with a message, so no allauth template
is ever rendered. The provider is configured in settings, not as a `SocialApp`
row, so there is no `django.contrib.sites` setup.

**The SSO allowlist lives in env vars.** `SSO_ALLOWED_DOMAINS` matches Google's
`hd` claim, never the email suffix. `SSO_ALLOWED_EMAILS` matches single
verified emails. The rule runs on every Google login, in the social account
adapter (`users/sso.py`). It gates Google login only; the admin stays the gate
for password accounts.

**Superusers come from a third, independent list.** Every allowed Google login
of an email in `SSO_SUPERUSER_EMAILS` makes its user superuser and staff, new
or existing. Being on that list does not allow a login; the allowlist alone
decides that. A login never demotes: removing an email from the list leaves
the user's rights alone, and taking them away stays the admin's job.
`SSO_ALLOWED_EMAILS` and `SSO_SUPERUSER_EMAILS` both default to the author
email, so a fresh project lets the author in as superuser with no config.

**A Google login links to an existing user with the same email** instead of
creating a second one. This is safe because Google verifies the email and an
unverified one is rejected first.

**A user created by Google login gets its full email as username.** The
email is unique, so `anna@company.com` and `anna@gmail.com` never clash.

## Consequences

- Production needs no `createsuperuser`: the author's first Google login
  creates the first superuser. `createsuperuser` stays the fallback without
  Google credentials.
- The template ships no seed fixture and no default password. Local
  development without Google credentials uses `createsuperuser`.
- Removing someone from the allowlist blocks their next login, not their open
  session. Deactivating the user in the admin ends both.
- A Google login that links to an existing user keeps its password. allauth
  would make that password unusable, because nobody verified the address;
  that guards against an attacker who signed up with a victim's email and set
  the password. Here users only come from the admin, `createsuperuser` or
  Google login, so the adapter marks the linked email as verified first
  (allauth's `EmailAddress`), and such a user can use both logins.
- Changing the allowlist is a config change and a restart, not a data change.
  Adding an email to `SSO_SUPERUSER_EMAILS` takes effect on that user's next
  Google login; removing one needs the admin to take the rights away.
- Setting `SSO_ALLOWED_EMAILS` replaces its default, so the author email has
  to stay in the list to keep Google login for the author.

## Alternatives considered

- **social-auth-app-django.** Its built-in domain whitelist checks only the
  email suffix, not `hd`, so a custom pipeline step would be needed anyway.
  allauth is the more widely used of the two.
- **A hand-written OIDC flow.** More security-critical code of our own to
  maintain than an adapter hook on a maintained library.
- **SSO only, no password login.** Locks out people without a Google account
  and makes a Google outage an outage of the app.
- **An allowlist in the database, edited in the admin.** Needs its own UI and
  migrations for a list that changes rarely; env vars are configured like
  every other setting.
