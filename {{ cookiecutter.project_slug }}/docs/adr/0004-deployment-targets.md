# Two deployment targets over one deployment contract

Generated projects land on Appliku or on a docker-compose compatible host (a
plain Docker host, Dokploy, Coolify). The template ships one contract the app
owns (one image, the process scripts `web.sh`, `worker.sh` and `release.sh`,
the `/healthz` probe, settings read from environment variables only) and two
manifests that consume it, `appliku.yml` and `compose.yaml`. Two independent
deployment descriptions would drift apart; this confines the difference to
what is per platform, and moving between targets is a manifest swap.

Migrations and one-shot tasks belong in `release.sh`, never in `web.sh`: it
runs once per deploy, before web and worker start, on every target.

Host provisioning, the reverse proxy and TLS termination are outside the
template.

The cost: the manifests have to stay coherent. Adding a process or a backing
service means editing `appliku.yml`, `compose.yaml` and `compose.prod.yaml`
(ADR-0008) in the same pull request, and a project that uses only one of them
will not notice the others rotting.
