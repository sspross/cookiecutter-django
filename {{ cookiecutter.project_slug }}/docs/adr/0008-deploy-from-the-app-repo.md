# Deploy from the app repo

This repo owns its production deployment on a docker host: the manifest
`compose.prod.yaml`, an image per commit on GHCR, and a `deploy` workflow run
by a button on `main`, which drives the host's docker daemon over SSH from a
GitHub-hosted runner. The repository's Actions variables and secrets are the
production environment. With a separate infra repo owning the deploy, a
release is a tag here, a pin bump there and a manual run with the operator's
credentials, and every change to an environment variable takes two pull
requests. The deploy belongs to the app: the compose file mirrors the app's
topology, the secrets are the app's, and the person merging a change is the
one who wants to ship it.

Whoever runs the host provides a contract and nothing else: SSH access as a
user in the `docker` group, a reverse proxy on the `ingress` network, and
named volumes nothing prunes. README.md "Docker host, deployed from this repo"
lists it.

The cost: the deploy credential in the repository (`DEPLOY_SSH_PRIVATE_KEY`,
or the `TS_OAUTH_*` pair) is the key to the host. Whoever holds it reaches the
docker daemon, which is root-equivalent there. `compose.prod.yaml` also has to
follow `compose.yaml` when the topology changes (ADR-0004).

The flow: `docs/OPERATIONS.md` "Deploy flow".
